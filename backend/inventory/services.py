"""
Stock services. Every read and write of stock goes through this module.

Rules enforced here:
  * On-hand stock is the sum of `StockMovement.quantity`. Nothing stores a stock count.
  * Available = on-hand minus ACTIVE reservations.
  * Allocation is FEFO by default (first expiry first out), FIFO when configured.
  * A batch whose best_before falls inside MIN_SHELF_LIFE_ON_DISPATCH_DAYS is never
    auto-allocated, and an expired batch is never allocated at all. For Ayura that setting
    defaults to 0 (ROADMAP Z1): a batch with no date, or any date still in the future, is
    allocated normally, and only an expired one is held back.
  * Allocation locks the variant row, so two concurrent checkouts for the last unit
    cannot both succeed (real row locking requires PostgreSQL).
  * A KIT (Phase E, Ayura) holds no stock of its own. What it can sell is the scarcest of its
    components, and selling one holds every component through this module, all or nothing.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.audit import get_actor, record
from inventory.models import (
    Batch,
    Channel,
    MovementKind,
    OUTBOUND_KINDS,
    INBOUND_KINDS,
    ReservationStatus,
    StockMovement,
    StockReservation,
)

logger = logging.getLogger(__name__)


class StockError(Exception):
    """Base class for stock problems."""


class InsufficientStock(StockError):
    def __init__(self, variant, requested, available):
        self.variant = variant
        self.requested = requested
        self.available = available
        super().__init__(f"Only {available} of {variant.sku} available, {requested} requested.")


class InvalidMovement(StockError):
    pass


# --------------------------------------------------------------------------- reads

def on_hand_qty(variant):
    """Physical stock of a variant across all batches, from the ledger."""
    return StockMovement.objects.filter(variant=variant).aggregate(total=Sum("quantity"))["total"] or 0


def batch_on_hand(batch):
    """Physical stock remaining in one batch, from the ledger."""
    return StockMovement.objects.filter(batch=batch).aggregate(total=Sum("quantity"))["total"] or 0


def reserved_qty(variant):
    """Units currently held by ACTIVE, unexpired reservations."""
    return (
        StockReservation.objects.filter(
            variant=variant, status=ReservationStatus.ACTIVE, expires_at__gt=timezone.now()
        ).aggregate(total=Sum("quantity"))["total"]
        or 0
    )


def batch_reserved_qty(batch):
    return (
        StockReservation.objects.filter(
            batch=batch, status=ReservationStatus.ACTIVE, expires_at__gt=timezone.now()
        ).aggregate(total=Sum("quantity"))["total"]
        or 0
    )


def kit_available_qty(kit_variant, component_available=None):
    """
    How many of this kit can still be sold: the scarcest component decides (Phase E, Ayura).

    A kit with no components can sell nothing, so it shows as sold out until the owner says
    what is in it. `component_available` is an optional {variant_id: available} map, so a
    listing page can work this out without asking the ledger again per component.
    """
    from catalog.models import KitComponent

    parts = list(KitComponent.objects.filter(kit_variant=kit_variant).select_related("component_variant"))
    if not parts:
        return 0
    possible = []
    for part in parts:
        if component_available is not None and part.component_variant_id in component_available:
            free = component_available[part.component_variant_id]
        else:
            free = available_qty(part.component_variant)
        possible.append(free // part.qty)
    return max(min(possible), 0)


def available_qty(variant):
    """What a shopper may still buy. A kit is limited by its scarcest component."""
    if getattr(variant, "is_kit", False):
        return kit_available_qty(variant)
    return max(on_hand_qty(variant) - reserved_qty(variant), 0)


def available_qty_map(variants):
    """
    `available_qty` for many variants in TWO queries instead of two per variant.

    A listing page asks for the stock of every size of every product; one query each turns a
    page into hundreds of round trips to the database. This asks once for the ledger totals and
    once for the live holds, and returns {variant_id: units available}. The arithmetic is the
    same as `available_qty`, so the two can never disagree.
    """
    from catalog.models import KitComponent, ProductVariant

    ids = [variant.pk if hasattr(variant, "pk") else int(variant) for variant in variants]
    if not ids:
        return {}

    # Kits have no stock of their own, so ask the ledger about their components instead and
    # work the kits out from those (Phase E). One extra query, not one per component.
    kit_ids = set(ProductVariant.objects.filter(pk__in=ids, is_kit=True).values_list("pk", flat=True))
    parts_by_kit = {}
    if kit_ids:
        for part in KitComponent.objects.filter(kit_variant_id__in=kit_ids):
            parts_by_kit.setdefault(part.kit_variant_id, []).append(part)
        ids = list(ids) + [part.component_variant_id for parts in parts_by_kit.values() for part in parts]

    on_hand = {
        row["variant"]: row["total"] or 0
        for row in StockMovement.objects.filter(variant_id__in=ids).values("variant").annotate(total=Sum("quantity"))
    }
    reserved = {
        row["variant"]: row["total"] or 0
        for row in StockReservation.objects.filter(
            variant_id__in=ids, status=ReservationStatus.ACTIVE, expires_at__gt=timezone.now()
        ).values("variant").annotate(total=Sum("quantity"))
    }
    stock = {pk: max(on_hand.get(pk, 0) - reserved.get(pk, 0), 0) for pk in ids}
    for kit_id in kit_ids:
        parts = parts_by_kit.get(kit_id, [])
        stock[kit_id] = min((stock.get(p.component_variant_id, 0) // p.qty for p in parts), default=0)
    return stock


def min_shelf_life_cutoff():
    """Batches expiring on or before this date must not be auto-allocated."""
    days = settings.MIN_SHELF_LIFE_ON_DISPATCH_DAYS
    return timezone.localdate() + timedelta(days=days)


def allocatable_batches(variant, strategy=None):
    """
    Batches this variant may be allocated from, in allocation order.

    Excludes batches that are expired or inside the minimum-shelf-life window, and
    batches with nothing left after existing reservations.
    """
    strategy = (strategy or settings.STOCK_ALLOCATION_STRATEGY).upper()
    queryset = Batch.objects.filter(variant=variant)

    cutoff = min_shelf_life_cutoff()
    queryset = queryset.filter(best_before__isnull=True) | queryset.filter(best_before__gt=cutoff)

    if strategy == "FIFO":
        ordered = queryset.order_by("manufactured_on", "id")
    else:  # FEFO: soonest expiry first; batches with no expiry go last.
        ordered = queryset.extra(select={"_bb_null": "best_before IS NULL"}).order_by(
            "_bb_null", "best_before", "manufactured_on", "id"
        )

    result = []
    for batch in ordered:
        free = batch_on_hand(batch) - batch_reserved_qty(batch)
        if free > 0:
            result.append((batch, free))
    return result


# --------------------------------------------------------------------------- writes

def record_movement(variant, kind, quantity, batch=None, channel=Channel.WEBSITE, reason="",
                    reference_type="", reference_id="", actor=None, actor_label=None):
    """
    Append one movement to the ledger.

    `quantity` is signed. Inbound kinds must be positive, outbound kinds negative;
    ADJUSTMENT may be either. Zero is never a movement.
    """
    if quantity == 0:
        raise InvalidMovement("A stock movement cannot be zero.")
    if kind in INBOUND_KINDS and quantity < 0:
        raise InvalidMovement(f"{kind} must be a positive quantity.")
    if kind in OUTBOUND_KINDS and quantity > 0:
        raise InvalidMovement(f"{kind} must be a negative quantity.")
    if kind in (MovementKind.PRODUCTION_IN,) and batch is None:
        raise InvalidMovement("Production must be recorded against a batch.")
    if batch is not None and batch.variant_id != variant.pk:
        raise InvalidMovement("Batch belongs to a different variant.")

    ctx_actor, ctx_label = get_actor()
    movement = StockMovement.objects.create(
        variant=variant,
        batch=batch,
        kind=kind,
        quantity=quantity,
        channel=channel,
        reason=reason[:255],
        reference_type=reference_type[:50],
        reference_id=str(reference_id)[:64],
        actor=actor if actor is not None else ctx_actor,
        actor_label=(actor_label or ctx_label)[:100],
    )
    record(
        "stock.movement",
        movement,
        before=None,
        after={
            "variant": variant.sku,
            "batch": batch.batch_code if batch else None,
            "kind": kind,
            "quantity": quantity,
            "channel": channel,
        },
        reason=reason,
    )
    return movement


def receive_production(variant, batch, quantity, reason="Production received", actor=None):
    """Book a finished production run into stock."""
    return record_movement(
        variant, MovementKind.PRODUCTION_IN, abs(int(quantity)), batch=batch,
        channel=Channel.MANUAL, reason=reason, reference_type="batch", reference_id=batch.pk, actor=actor,
    )


@transaction.atomic
def reserve(variant, quantity, cart_id="", order=None, order_item=None, ttl_minutes=None, strategy=None,
            sample=None, kit_variant=None):
    """
    Hold `quantity` units of `variant`, splitting across batches in FEFO (or FIFO) order.

    Returns the list of StockReservation rows created. Raises InsufficientStock and rolls
    back if the full quantity cannot be held. The variant row is locked for the duration,
    so concurrent callers are serialised.

    `sample` marks the hold as a gift sample going out with an order (Phase D, Ayura) rather
    than as something the customer bought; it leaves the ledger as SAMPLE_OUT, never SALE_OUT.

    `kit_variant` marks the hold as a component held because that kit was bought (Phase E).
    A kit itself is never reserved here: it has no stock. Use `reserve_kit`.
    """
    quantity = int(quantity)
    if quantity < 1:
        raise InvalidMovement("Reserved quantity must be at least 1.")
    if getattr(variant, "is_kit", False):
        raise InvalidMovement(f"{variant.sku} is a kit and holds no stock of its own; reserve its components.")

    from catalog.models import ProductVariant

    # Lock the variant row so two checkouts cannot both take the last unit.
    variant = ProductVariant.objects.select_for_update().get(pk=variant.pk)

    expire_due_reservations()

    available = available_qty(variant)
    if available < quantity:
        raise InsufficientStock(variant, quantity, available)

    expires_at = timezone.now() + timedelta(minutes=ttl_minutes or settings.STOCK_RESERVATION_TTL_MINUTES)

    remaining = quantity
    reservations = []
    for batch, free in allocatable_batches(variant, strategy=strategy):
        if remaining <= 0:
            break
        take = min(free, remaining)
        reservations.append(
            StockReservation.objects.create(
                variant=variant, batch=batch, quantity=take, cart_id=cart_id or "",
                order=order, order_item=order_item, sample=sample, kit_variant=kit_variant,
                expires_at=expires_at,
            )
        )
        remaining -= take

    if remaining > 0:
        # Stock exists on hand but is not allocatable (expired or inside the shelf-life window).
        raise InsufficientStock(variant, quantity, quantity - remaining)

    return reservations


@transaction.atomic
def reserve_kit(kit_variant, quantity, cart_id="", order=None, order_item=None, ttl_minutes=None):
    """
    Hold every component of `quantity` kits, all or nothing (Phase E, Ayura).

    Each component is reserved through `reserve`, so allocation is still FEFO and still locks
    the component's row. Components are taken in a fixed order (by id), so two shoppers buying
    overlapping kits can never deadlock against each other. If any component is short, the
    whole thing rolls back and InsufficientStock names the KIT, which is what the shopper asked
    for, not the component they have never heard of.
    """
    from catalog.models import KitComponent

    quantity = int(quantity)
    if quantity < 1:
        raise InvalidMovement("Reserved quantity must be at least 1.")
    parts = list(
        KitComponent.objects.filter(kit_variant=kit_variant)
        .select_related("component_variant").order_by("component_variant_id")
    )
    if not parts:
        raise InsufficientStock(kit_variant, quantity, 0)

    reservations = []
    for part in parts:
        try:
            reservations += reserve(
                part.component_variant, quantity * part.qty, cart_id=cart_id, order=order,
                order_item=order_item, ttl_minutes=ttl_minutes, kit_variant=kit_variant,
            )
        except InsufficientStock:
            # Report what the shopper can actually have of the kit, not of one component.
            raise InsufficientStock(kit_variant, quantity, kit_available_qty(kit_variant))
    return reservations


@transaction.atomic
def release_cart_line(cart_id, variant, reason="cart line replaced"):
    """
    Release only this cart's holds for one line.

    For a kit that means the component holds booked for that kit, and nothing else: the same
    component may also be in the cart on its own, or inside another kit, and those stay (Phase E).
    """
    holds = StockReservation.objects.filter(cart_id=cart_id, status=ReservationStatus.ACTIVE)
    if getattr(variant, "is_kit", False):
        holds = holds.filter(kit_variant=variant)
    else:
        holds = holds.filter(variant=variant, kit_variant__isnull=True)
    holds = list(holds)
    return release(holds, reason=reason) if holds else 0


@transaction.atomic
def release(reservations, reason="released"):
    """Give held stock back. Only ACTIVE reservations change."""
    if isinstance(reservations, StockReservation):
        reservations = [reservations]
    count = 0
    for reservation in reservations:
        updated = StockReservation.objects.filter(pk=reservation.pk, status=ReservationStatus.ACTIVE).update(
            status=ReservationStatus.RELEASED, resolved_at=timezone.now()
        )
        count += updated
    if count:
        logger.info("released %s stock reservation(s): %s", count, reason)
    return count


@transaction.atomic
def release_for_cart(cart_id, reason="cart released"):
    reservations = StockReservation.objects.filter(cart_id=cart_id, status=ReservationStatus.ACTIVE)
    return release(list(reservations), reason=reason)


@transaction.atomic
def release_for_order(order, reason="order cancelled"):
    reservations = StockReservation.objects.filter(order=order, status=ReservationStatus.ACTIVE)
    return release(list(reservations), reason=reason)


@transaction.atomic
def attach_reservations_to_order(cart_id, order, item_by_variant=None):
    """Move a cart's holds onto the order created from it."""
    item_by_variant = item_by_variant or {}
    moved = 0
    for reservation in StockReservation.objects.filter(cart_id=cart_id, status=ReservationStatus.ACTIVE):
        reservation.order = order
        # A component held for a kit belongs to the KIT's order line, not to a line of its own.
        reservation.order_item = item_by_variant.get(reservation.kit_variant_id or reservation.variant_id)
        reservation.save(update_fields=["order", "order_item"])
        moved += 1
    return moved


# A paid order's holds must outlive the checkout TTL: they are only ever resolved by dispatch
# (consume_for_order) or by cancellation (release_for_order).
PAID_HOLD_DAYS = 3650


@transaction.atomic
def hold_for_order(order, reason="order paid"):
    """
    Secure the stock of an order that has just been paid for.

    * Holds that are still ACTIVE are pinned so the reservation-expiry job never returns
      them to the shelf.
    * If a hold already lapsed (the customer paid after the checkout TTL), the shortfall is
      reserved again, as long as the stock is still there.

    Idempotent. Returns a list of (order_item, missing_qty) for lines that could not be fully
    held, so the caller can flag the order for the owner; it never raises for a shortfall,
    because the customer's payment has already been taken.
    """
    from store.models import CartOrderItem

    pinned_until = timezone.now() + timedelta(days=PAID_HOLD_DAYS)
    StockReservation.objects.filter(
        order=order, status=ReservationStatus.ACTIVE, expires_at__gt=timezone.now()
    ).update(expires_at=pinned_until)

    shortfalls = []
    for item in CartOrderItem.objects.filter(order=order).select_related("variant"):
        if item.variant_id is None or item.qty < 1:
            continue
        missing = item.qty - _held_for_item(order, item)
        if missing <= 0:
            continue
        try:
            with transaction.atomic():
                if item.variant.is_kit:
                    reserve_kit(item.variant, missing, order=order, order_item=item,
                                ttl_minutes=PAID_HOLD_DAYS * 24 * 60)
                else:
                    reserve(item.variant, missing, order=order, order_item=item,
                            ttl_minutes=PAID_HOLD_DAYS * 24 * 60)
        except InsufficientStock:
            shortfalls.append((item, missing))
            logger.warning("order %s paid but %s unit(s) of %s could not be held", order.pk, missing, item.variant.sku)
    if not shortfalls:
        logger.info("stock secured for paid order %s: %s", order.pk, reason)
    return shortfalls


def _held_for_item(order, item):
    """
    How many units of this order line are already held (live or already consumed).

    A kit line is measured in KITS: each component is counted in its own right and the line is
    only as held as its scarcest component (Phase E).
    """
    from catalog.models import KitComponent

    base = (
        StockReservation.objects.filter(
            order=order, status__in=[ReservationStatus.ACTIVE, ReservationStatus.CONSUMED],
        ).filter(sample__isnull=True)  # a gift sample never counts towards a bought line
        .exclude(status=ReservationStatus.ACTIVE, expires_at__lte=timezone.now())
    )
    if not item.variant.is_kit:
        return base.filter(variant=item.variant, kit_variant__isnull=True).aggregate(
            total=Sum("quantity"))["total"] or 0

    parts = list(KitComponent.objects.filter(kit_variant=item.variant))
    if not parts:
        return 0
    held = base.filter(kit_variant=item.variant)
    per_component = {
        row["variant"]: row["total"] or 0
        for row in held.values("variant").annotate(total=Sum("quantity"))
    }
    return min((per_component.get(part.component_variant_id, 0) // part.qty for part in parts), default=0)


@transaction.atomic
def consume_for_order(order, channel=Channel.WEBSITE, reason="dispatched"):
    """
    Turn an order's holds into SALE_OUT movements: stock physically leaves.

    Idempotent: reservations already CONSUMED are skipped, so calling this twice for the
    same order never decrements stock twice. Gift-sample holds are left alone here.
    """
    reservations = list(
        StockReservation.objects.select_for_update()
        .filter(order=order, status=ReservationStatus.ACTIVE)
        # A gift sample's hold leaves as SAMPLE_OUT in consume_samples_for_order, never as a
        # sale. Without this it would be consumed here first and counted as revenue (Phase D).
        .filter(sample__isnull=True)
    )
    movements = []
    for reservation in reservations:
        updated = StockReservation.objects.filter(pk=reservation.pk, status=ReservationStatus.ACTIVE).update(
            status=ReservationStatus.CONSUMED, resolved_at=timezone.now()
        )
        if not updated:
            continue
        movements.append(
            record_movement(
                reservation.variant,
                MovementKind.SALE_OUT,
                -reservation.quantity,
                batch=reservation.batch,
                channel=channel,
                reason=reason,
                reference_type="order",
                reference_id=order.pk,
            )
        )
    return movements


@transaction.atomic
def expire_due_reservations():
    """Return stock held by reservations whose time is up. Returns the count."""
    return StockReservation.objects.filter(
        status=ReservationStatus.ACTIVE, expires_at__lte=timezone.now()
    ).update(status=ReservationStatus.EXPIRED, resolved_at=timezone.now())


# --------------------------------------------------------------------------- reporting

@transaction.atomic
def consume_samples_for_order(order, channel=Channel.WEBSITE, reason="samples dispatched"):
    """
    Turn an order's gift-sample holds into SAMPLE_OUT movements (Phase D, Ayura).

    Sample reservations are the ones tied to the order through `sample` rather than an order
    line. Idempotent in the same way as `consume_for_order`: a reservation already CONSUMED is
    skipped, so dispatching twice never takes the stock twice.
    """
    reservations = list(
        StockReservation.objects.select_for_update().filter(
            sample__order=order, status=ReservationStatus.ACTIVE
        )
    )
    movements = []
    for reservation in reservations:
        updated = StockReservation.objects.filter(pk=reservation.pk, status=ReservationStatus.ACTIVE).update(
            status=ReservationStatus.CONSUMED, resolved_at=timezone.now()
        )
        if not updated:
            continue
        movements.append(
            record_movement(
                reservation.variant,
                MovementKind.SAMPLE_OUT,
                -reservation.quantity,
                batch=reservation.batch,
                channel=channel,
                reason=reason,
                reference_type="order",
                reference_id=order.pk,
            )
        )
    return movements


@transaction.atomic
def write_off_batch(batch, quantity, reason, actor=None, channel=Channel.MANUAL):
    """
    Take stock out of a batch for good: expired, damaged or spilled (Phase D, Ayura).

    A write-off is a DAMAGE_OUT movement, never an edit of anything: the ledger keeps the whole
    story. Refuses more than the batch physically has left, and refuses stock that is currently
    held for a customer (that order must be cancelled first).
    """
    quantity = int(quantity)
    if quantity < 1:
        raise InvalidMovement("Write off at least 1 unit.")
    on_hand = batch_on_hand(batch)
    held = batch_reserved_qty(batch)
    free = on_hand - held
    if quantity > free:
        raise InsufficientStock(batch.variant, quantity, max(free, 0))
    return record_movement(
        batch.variant, MovementKind.DAMAGE_OUT, -quantity, batch=batch, channel=channel,
        reason=reason[:255], reference_type="batch", reference_id=batch.pk, actor=actor,
    )


def order_batches(order):
    """
    Which batch each line of an order is taking its stock from (Phase D, Ayura).

    Reads the order's own reservations and movements, so it reports what was really allocated
    (FEFO at the time), never a fresh guess. Returns
    {order_item_id: [{batch, quantity, status}]}, newest allocation last.
    """
    rows = {}
    reservations = (
        StockReservation.objects.filter(order=order)
        .exclude(status__in=[ReservationStatus.RELEASED, ReservationStatus.EXPIRED])
        .select_related("batch", "variant")
        .order_by("id")
    )
    for reservation in reservations:
        if reservation.order_item_id is None:
            continue
        rows.setdefault(reservation.order_item_id, []).append(
            {"batch": reservation.batch, "quantity": reservation.quantity, "status": reservation.status}
        )
    return rows


def orders_from_batch(batch):
    """
    Every order that received stock from this batch (Phase D, Ayura): the recall question.

    Built from the ledger, so it lists what physically left (SALE_OUT and SAMPLE_OUT), and from
    the live holds, so an order that is packed but not yet dispatched is listed too.
    Returns a list of {order, quantity, kind} with the newest first.
    """
    from store.models import CartOrder

    found = {}
    movements = StockMovement.objects.filter(
        batch=batch, kind__in=[MovementKind.SALE_OUT, MovementKind.SAMPLE_OUT], reference_type="order"
    )
    for movement in movements:
        try:
            order_id = int(movement.reference_id)
        except (TypeError, ValueError):
            continue
        entry = found.setdefault(order_id, {"order_id": order_id, "quantity": 0, "kinds": set(), "dispatched": True})
        entry["quantity"] += abs(movement.quantity)
        entry["kinds"].add(movement.kind)

    holds = StockReservation.objects.filter(batch=batch, status=ReservationStatus.ACTIVE).exclude(order__isnull=True)
    for hold in holds:
        entry = found.setdefault(hold.order_id, {"order_id": hold.order_id, "quantity": 0, "kinds": set(), "dispatched": False})
        entry["quantity"] += hold.quantity
        entry["kinds"].add(MovementKind.SAMPLE_OUT if hold.sample_id else MovementKind.SALE_OUT)
        # Stock still on hold has not physically left yet, whatever else this order has sent.
        entry["dispatched"] = False

    orders = {order.pk: order for order in CartOrder.objects.filter(pk__in=found.keys())}
    result = []
    for order_id, entry in found.items():
        order = orders.get(order_id)
        if order is None:
            continue
        result.append({
            "order": order,
            "quantity": entry["quantity"],
            "sample_only": entry["kinds"] == {MovementKind.SAMPLE_OUT},
            "dispatched": entry["dispatched"],
        })
    result.sort(key=lambda row: row["order"].date, reverse=True)
    return result


def undated_batches_with_stock():
    """Batches that still have stock and no use-by date recorded (Phase D, Ayura)."""
    result = []
    for batch in Batch.objects.filter(best_before__isnull=True):
        remaining = batch_on_hand(batch)
        if remaining > 0:
            result.append((batch, remaining))
    return result


def batches_nearing_expiry(days=None):
    """Batches with stock left that expire within `days` (default EXPIRY_ALERT_DAYS)."""
    days = days if days is not None else settings.EXPIRY_ALERT_DAYS
    today = timezone.localdate()
    horizon = today + timedelta(days=days)
    result = []
    for batch in Batch.objects.filter(best_before__isnull=False, best_before__gte=today, best_before__lte=horizon):
        remaining = batch_on_hand(batch)
        if remaining > 0:
            result.append((batch, remaining))
    return result


def expired_unsold_batches():
    """Batches already past best_before that still have stock on hand."""
    today = timezone.localdate()
    result = []
    for batch in Batch.objects.filter(best_before__isnull=False, best_before__lt=today):
        remaining = batch_on_hand(batch)
        if remaining > 0:
            result.append((batch, remaining))
    return result


def reconcile_batch(batch):
    """
    Consistency check used by tests and the owner dashboard:
    produced - sold - written off + returned == on hand.
    """
    movements = StockMovement.objects.filter(batch=batch)
    produced = movements.filter(kind=MovementKind.PRODUCTION_IN).aggregate(t=Sum("quantity"))["t"] or 0
    returned = movements.filter(kind__in=[MovementKind.RETURN_IN, MovementKind.RTO_IN]).aggregate(t=Sum("quantity"))["t"] or 0
    sold = movements.filter(kind=MovementKind.SALE_OUT).aggregate(t=Sum("quantity"))["t"] or 0
    damaged = movements.filter(kind=MovementKind.DAMAGE_OUT).aggregate(t=Sum("quantity"))["t"] or 0
    adjusted = movements.filter(kind=MovementKind.ADJUSTMENT).aggregate(t=Sum("quantity"))["t"] or 0
    return {
        "produced": produced,
        "returned": returned,
        "sold": sold,
        "damaged": damaged,
        "adjusted": adjusted,
        "on_hand": batch_on_hand(batch),
        "balances": produced + returned + sold + damaged + adjusted == batch_on_hand(batch),
    }