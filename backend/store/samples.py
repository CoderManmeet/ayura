"""
Gift samples on an order (Phase D, Ayura).

The owner decides, per order, whether to put free samples in the parcel and which ones. A
sample is a hidden variant of a real product (`ProductVariant.is_sample`, ROADMAP Z2), so the
stock that goes out is tracked like any other stock:

  * adding a sample holds its stock immediately, through the ledger;
  * dispatching the order turns that hold into a SAMPLE_OUT movement, exactly once, so a gift
    is never counted as a sale;
  * cancelling the order releases the hold, like any other hold on that order.

Nothing here ever touches money. `store.pricing.quote()` does not know samples exist, so
adding or removing one cannot change what the customer pays.

The customer is NEVER told (ROADMAP Y19): no order page, no email and no API answer a customer
can reach mentions samples. That is why `sample_decision` is kept out of the customer's order
serializer and only the owner's one adds it back.
"""

import logging

from django.db import IntegrityError, transaction

from catalog.models import ProductVariant
from core.audit import record, snapshot
from inventory.services import InsufficientStock, PAID_HOLD_DAYS, release, reserve
from inventory.models import ReservationStatus, StockReservation
from store.models import SAMPLE_ADDED, SAMPLE_NONE, SAMPLE_UNDECIDED, CartOrder, CartOrderItem, OrderSample

logger = logging.getLogger(__name__)

# A sample is added to an order the owner is about to pack, so its hold must not be handed
# back by the reservation-expiry job while the parcel is waiting. Pinned like a paid order's.
SAMPLE_HOLD_MINUTES = PAID_HOLD_DAYS * 24 * 60


class SampleError(Exception):
    """A sample cannot be added or removed. The message is shown to the owner as it is."""


def sample_variants():
    """Every variant the owner may give away, newest product first."""
    return (ProductVariant.objects.filter(is_sample=True, active=True)
            .select_related("product").order_by("product__title", "name"))


def _order_is_open(order):
    """A cancelled or finished order is never changed here."""
    if order.order_status == "Cancelled" or order.payment_status in ("cancelled", "expired"):
        raise SampleError("This order has been cancelled.")
    if order.orderitem.filter(delivery_status__in=["Shipped", "Arrived", "Delivered"]).exists():
        raise SampleError("This order has already been sent. Samples cannot be changed now.")


@transaction.atomic
def add_sample(order, variant, qty=1, actor=None):
    """
    Put `qty` of a sample variant in this order's parcel and hold its stock.

    Raises SampleError (and writes nothing) when the order is closed, the variant is not a
    sample, the quantity is wrong, the sample is already on the order, or the stock has gone.
    """
    order = CartOrder.objects.select_for_update().get(pk=order.pk)
    _order_is_open(order)

    if not getattr(variant, "is_sample", False):
        raise SampleError("Only a sample size can be given away. Mark the size as a sample first.")
    if not variant.active:
        raise SampleError("That sample is switched off.")
    try:
        qty = int(qty)
    except (TypeError, ValueError):
        raise SampleError("Quantity must be a whole number.")
    if qty < 1:
        raise SampleError("Quantity must be at least 1.")

    try:
        sample = OrderSample.objects.create(order=order, variant=variant, qty=qty, added_by=actor)
    except IntegrityError:
        raise SampleError("That sample is already on this order. Remove it first to change the quantity.")

    try:
        reserve(variant, qty, order=order, sample=sample, ttl_minutes=SAMPLE_HOLD_MINUTES)
    except InsufficientStock as exc:
        raise SampleError(f"Only {exc.available} of that sample left.")

    before = {"sample_decision": order.sample_decision}
    if order.sample_decision != SAMPLE_ADDED:
        order.sample_decision = SAMPLE_ADDED
        order.save(update_fields=["sample_decision"])
    record("order.sample_added", order, before=before,
           after={"sample_decision": order.sample_decision, "variant": variant.sku, "qty": qty},
           reason="free sample added to the parcel", actor=actor)
    return sample


@transaction.atomic
def remove_sample(sample, actor=None):
    """Take a sample off an order and give its held stock back. Safe to call twice."""
    order = CartOrder.objects.select_for_update().get(pk=sample.order_id)
    _order_is_open(order)

    holds = list(StockReservation.objects.filter(sample=sample, status=ReservationStatus.ACTIVE))
    if holds:
        release(holds, reason="free sample removed from the order")
    consumed = StockReservation.objects.filter(sample=sample, status=ReservationStatus.CONSUMED).exists()
    if consumed:
        raise SampleError("That sample has already left with the parcel.")

    variant_sku, qty = sample.variant.sku, sample.qty
    sample.delete()

    before = {"sample_decision": order.sample_decision}
    if not OrderSample.objects.filter(order=order).exists() and order.sample_decision == SAMPLE_ADDED:
        order.sample_decision = SAMPLE_UNDECIDED
        order.save(update_fields=["sample_decision"])
    record("order.sample_removed", order, before=before,
           after={"sample_decision": order.sample_decision, "variant": variant_sku, "qty": qty},
           reason="free sample removed", actor=actor)
    return order


@transaction.atomic
def decide_no_samples(order, actor=None):
    """Record that this order goes out without samples, so it stops showing as undecided."""
    order = CartOrder.objects.select_for_update().get(pk=order.pk)
    _order_is_open(order)
    if OrderSample.objects.filter(order=order).exists():
        raise SampleError("Remove the samples on this order first.")
    before = {"sample_decision": order.sample_decision}
    if order.sample_decision != SAMPLE_NONE:
        order.sample_decision = SAMPLE_NONE
        order.save(update_fields=["sample_decision"])
        record("order.sample_decision", order, before=before, after={"sample_decision": SAMPLE_NONE},
               reason="no samples with this order", actor=actor)
    return order


# --------------------------------------------------------------------------- the report

def _identity(order):
    """How one customer is recognised across orders: account first, then email, then phone."""
    if order.buyer_id:
        return ("user", str(order.buyer_id))
    if (order.email or "").strip():
        return ("email", order.email.strip().lower())
    if (order.phone_e164 or "").strip():
        return ("phone", order.phone_e164.strip())
    return None


def _alive(order):
    return order.order_status != "Cancelled" and order.payment_status not in ("cancelled", "expired", "initiated")


def conversion_report():
    """
    Did the free samples lead to sales? (ROADMAP D.)

    For every sample that has gone out: how many orders carried it, and how many of those
    customers LATER placed a living order containing a full-size variant of the same product.
    The same customer is recognised by account, or failing that by the email or phone on the
    order. Buying something else does not count.

    Returns a list of rows, each with the sample, the orders that carried it, and the orders
    that followed. Counting only; nothing is written.
    """
    samples = list(
        OrderSample.objects.select_related("order", "variant", "variant__product").order_by("added_at", "id")
    )
    if not samples:
        return []

    product_ids = {sample.variant.product_id for sample in samples}

    # Every living order line of a full-size variant of those products, with its buyer identity.
    purchases = {}
    lines = (
        CartOrderItem.objects.filter(variant__product_id__in=product_ids, variant__is_sample=False)
        .select_related("order", "variant")
    )
    for line in lines:
        order = line.order
        if not _alive(order):
            continue
        identity = _identity(order)
        if identity is None:
            continue
        purchases.setdefault((identity, line.variant.product_id), []).append(order)

    rows = {}
    for sample in samples:
        key = sample.variant_id
        row = rows.setdefault(key, {
            "variant": sample.variant,
            "product": sample.variant.product,
            "given_orders": [],
            "converted": [],
        })
        if not _alive(sample.order):
            continue
        row["given_orders"].append(sample.order)

        identity = _identity(sample.order)
        if identity is None:
            continue
        later = [
            order for order in purchases.get((identity, sample.variant.product_id), [])
            if order.pk != sample.order_id and order.date > sample.order.date
        ]
        if later:
            row["converted"].append({"sample_order": sample.order, "then_bought": sorted(later, key=lambda o: o.date)})

    result = []
    for row in rows.values():
        given = len(row["given_orders"])
        converted = len(row["converted"])
        result.append({
            "variant": row["variant"],
            "product": row["product"],
            "given": given,
            "converted": converted,
            "conversion_percent": round(converted * 100 / given) if given else 0,
            "conversions": row["converted"],
        })
    result.sort(key=lambda entry: (-entry["given"], entry["product"].title))
    return result
