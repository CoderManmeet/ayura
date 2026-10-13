"""
Phase E tests (Ayura): a kit sold as one item, made of other variants' stock.

A kit holds no stock of its own. What it can sell is the scarcest of its components; buying
one holds every component, all or nothing; cancelling gives every component back; dispatch
takes each component exactly once. Its price is the owner's, never the sum of the parts
(ROADMAP Z7), and a kit never contains another kit or a sample.

Every test here fails before Phase E: `ProductVariant.is_kit`, `catalog.KitComponent`,
`inventory.services.kit_available_qty` / `reserve_kit` and the owner kit endpoints did not
exist, and a kit variant with no stock of its own was simply sold out.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import connection, transaction
from django.db.utils import IntegrityError
from django.test import TransactionTestCase
from django.utils import timezone

from catalog.models import KitComponent, ProductVariant
from inventory.models import ReservationStatus, StockMovement, StockReservation
from inventory.models import Batch, MovementKind
from inventory.services import (
    InsufficientStock,
    InvalidMovement,
    available_qty,
    available_qty_map,
    consume_for_order,
    hold_for_order,
    kit_available_qty,
    on_hand_qty,
    receive_production,
    release_cart_line,
    release_for_order,
    reserve,
    reserve_kit,
)

API = "/api/v1/"


# --------------------------------------------------------------------------- helpers

def make_batch(variant, code, qty, best_before_days=365, made_days_ago=0):
    today = timezone.localdate()
    batch = Batch.objects.create(
        batch_code=code,
        variant=variant,
        manufactured_on=today - timedelta(days=made_days_ago),
        best_before=(today + timedelta(days=best_before_days)) if best_before_days is not None else None,
        quantity_produced=qty,
        cost_per_unit_paise=1000,
    )
    receive_production(variant, batch, qty)
    return batch


def add_variant(product, sku, name, price_paise=10000, **extra):
    return ProductVariant.objects.create(
        product=product, sku=sku, name=name, price_paise=price_paise,
        net_quantity=Decimal("50"), net_quantity_unit="g", **extra,
    )


@pytest.fixture
def components(product):
    """
    Two sellable sizes with their own stock: the cleanser (8 units) and the serum (3 units).

    The product fixture's own default variant keeps its opening stock and is left alone, so a
    test can tell a component's hold apart from an ordinary line's.
    """
    cleanser = add_variant(product, "SKU-CLEANSER", "Cleanser 50 g", price_paise=30000)
    serum = add_variant(product, "SKU-SERUM", "Serum 30 ml", price_paise=50000)
    make_batch(cleanser, "CLEAN-1", 8)
    make_batch(serum, "SERUM-1", 3)
    return cleanser, serum


@pytest.fixture
def kit(product, components):
    """
    The "Face routine" kit: 1 cleanser + 1 serum, priced at 699 by the owner.

    699 is less than the 800 the parts cost separately, which is the point of a kit and is
    only possible because the price is the owner's own (ROADMAP Z7).
    """
    cleanser, serum = components
    kit_variant = add_variant(product, "SKU-KIT-FACE", "Face routine", price_paise=69900, is_kit=True)
    KitComponent.objects.create(kit_variant=kit_variant, component_variant=cleanser, qty=1)
    KitComponent.objects.create(kit_variant=kit_variant, component_variant=serum, qty=1)
    return kit_variant


# --------------------------------------------------------------------------- availability

@pytest.mark.django_db
def test_kit_availability_tracks_its_scarcest_component(kit, components):
    cleanser, serum = components
    assert available_qty(cleanser) == 8
    assert available_qty(serum) == 3
    # The serum is the bottleneck, so three kits and no more.
    assert available_qty(kit) == 3
    assert kit_available_qty(kit) == 3

    # Make the serum scarcer still and the kit follows it down, without touching the cleanser.
    reserve(serum, 2, cart_id="someone-else")
    assert available_qty(kit) == 1
    assert available_qty(cleanser) == 8


@pytest.mark.django_db
def test_a_kit_needing_two_of_a_component_divides_by_the_quantity(kit, components):
    cleanser, serum = components
    KitComponent.objects.filter(kit_variant=kit, component_variant=cleanser).update(qty=3)
    make_batch(serum, "SERUM-2", 20)                 # the serum is no longer the bottleneck
    assert available_qty(serum) == 23
    # 8 cleansers, 3 per kit: two kits, with two cleansers left over and unsellable as a kit.
    assert available_qty(kit) == 2


@pytest.mark.django_db
def test_a_kit_holds_no_stock_of_its_own(kit):
    """The kit variant has no ledger movements at all; its availability is still real."""
    assert on_hand_qty(kit) == 0
    assert StockMovement.objects.filter(variant=kit).count() == 0
    assert available_qty(kit) == 3


@pytest.mark.django_db
def test_a_kit_with_nothing_in_it_yet_is_sold_out(product):
    empty = add_variant(product, "SKU-KIT-EMPTY", "Empty kit", is_kit=True)
    assert available_qty(empty) == 0
    with pytest.raises(InsufficientStock):
        reserve_kit(empty, 1, cart_id="c1")


@pytest.mark.django_db
def test_a_kit_with_a_sold_out_component_is_sold_out(kit, components):
    from catalog.display import stock_status

    cleanser, serum = components
    reserve(serum, 3, cart_id="all-the-serum")       # every serum is gone
    assert available_qty(serum) == 0
    assert available_qty(kit) == 0
    assert stock_status(kit) == {"state": "sold_out", "label": "Sold out", "left": 0}
    # The cleanser itself is still perfectly sellable on its own.
    assert stock_status(cleanser)["state"] == "in_stock"


@pytest.mark.django_db
def test_an_expired_component_batch_leaves_the_kit_sold_out(product, kit, components):
    """A kit cannot be assembled out of stock that may not be dispatched (ROADMAP Z1)."""
    cleanser, serum = components
    # A third part whose only stock went off last week. The ledger is append-only, so this is
    # a new size rather than an edit of the serum's history.
    toner = add_variant(product, "SKU-TONER", "Toner 100 ml", price_paise=20000)
    make_batch(toner, "TONER-OLD", 5, best_before_days=-2)
    KitComponent.objects.create(kit_variant=kit, component_variant=toner, qty=1)

    # Expired stock still counts as on hand, exactly as it does for an ordinary size, so the
    # refusal comes from allocation rather than from the count.
    assert on_hand_qty(toner) == 5
    with pytest.raises(InsufficientStock):
        reserve_kit(kit, 1, cart_id="c1")
    # Neither of the two good components was left held behind.
    assert StockReservation.objects.count() == 0
    assert available_qty(cleanser) == 8
    assert available_qty(serum) == 3


@pytest.mark.django_db
def test_available_qty_map_and_available_qty_agree_about_kits(kit, components):
    cleanser, serum = components
    mapped = available_qty_map([kit, cleanser, serum])
    assert mapped[kit.pk] == available_qty(kit) == 3
    assert mapped[cleanser.pk] == 8
    assert mapped[serum.pk] == 3

    reserve(serum, 2, cart_id="c1")
    assert available_qty_map([kit])[kit.pk] == available_qty(kit) == 1


# --------------------------------------------------------------------------- reserving

@pytest.mark.django_db
def test_reserving_a_kit_holds_every_component(kit, components):
    cleanser, serum = components
    reservations = reserve_kit(kit, 2, cart_id="c1")

    assert sorted(r.variant_id for r in reservations) == sorted([cleanser.pk, serum.pk])
    assert all(r.kit_variant_id == kit.pk for r in reservations)
    assert {r.variant_id: r.quantity for r in reservations} == {cleanser.pk: 2, serum.pk: 2}
    assert available_qty(cleanser) == 6
    assert available_qty(serum) == 1
    assert available_qty(kit) == 1
    # The kit itself is never the subject of a hold: it has no stock to hold.
    assert StockReservation.objects.filter(variant=kit).count() == 0


@pytest.mark.django_db
def test_a_kit_short_of_one_component_holds_nothing_at_all(kit, components):
    """All or nothing: the cleanser is not left held while the serum is short."""
    cleanser, serum = components
    with pytest.raises(InsufficientStock) as exc:
        reserve_kit(kit, 4, cart_id="c1")

    # The error names the KIT and what the shopper can have of it, not a component they have
    # never heard of.
    assert exc.value.variant == kit
    assert exc.value.requested == 4
    assert exc.value.available == 3
    assert StockReservation.objects.count() == 0
    assert available_qty(cleanser) == 8
    assert available_qty(serum) == 3


@pytest.mark.django_db
def test_the_kit_variant_itself_can_never_be_reserved(kit):
    with pytest.raises(InvalidMovement):
        reserve(kit, 1, cart_id="c1")
    assert StockReservation.objects.count() == 0


@pytest.mark.django_db
def test_releasing_a_kit_cart_line_returns_every_component_and_nothing_else(kit, components, product):
    cleanser, serum = components
    plain = ProductVariant.objects.get(product=product, is_default=True)

    reserve_kit(kit, 1, cart_id="c1")
    reserve(cleanser, 2, cart_id="c1")               # the same cleanser, bought on its own too
    reserve(plain, 1, cart_id="c1")
    assert available_qty(cleanser) == 5

    release_cart_line("c1", kit)

    assert available_qty(cleanser) == 6              # the kit's one came back, the two stayed
    assert available_qty(serum) == 3
    assert available_qty(plain) == 9
    assert StockReservation.objects.filter(status=ReservationStatus.ACTIVE).count() == 2
    assert StockReservation.objects.filter(status=ReservationStatus.RELEASED).count() == 2


@pytest.mark.django_db
def test_releasing_a_plain_line_leaves_the_same_components_kit_hold_alone(kit, components):
    """
    The other direction: the cleanser is in the cart twice, once alone and once inside the kit.

    Dropping the plain cleanser line must not quietly dismantle the kit the shopper is also
    buying, even though both holds are for the same size in the same cart.
    """
    cleanser, serum = components
    reserve_kit(kit, 1, cart_id="c1")
    reserve(cleanser, 2, cart_id="c1")
    assert available_qty(cleanser) == 5

    release_cart_line("c1", cleanser)

    assert available_qty(cleanser) == 7              # the two came back, the kit's one stayed
    assert available_qty(kit) == 2
    held = StockReservation.objects.filter(status=ReservationStatus.ACTIVE)
    assert {(h.variant_id, h.kit_variant_id, h.quantity) for h in held} == {
        (cleanser.pk, kit.pk, 1), (serum.pk, kit.pk, 1),
    }


@pytest.mark.django_db
def test_changing_the_quantity_of_a_kit_line_replaces_the_holds(api, product, kit, components):
    cleanser, serum = components
    for qty in (1, 3, 2):
        response = api.post(f"{API}cart-view/", {"product": product.id, "user": "undefined", "qty": qty,
                                                 "variant": kit.pk, "country": "India", "cart_id": "cart-kit-1"})
        assert response.status_code in (200, 201), response.content

    active = StockReservation.objects.filter(status=ReservationStatus.ACTIVE)
    assert active.count() == 2                       # one per component, not six
    assert {r.quantity for r in active} == {2}
    assert available_qty(cleanser) == 6
    assert available_qty(serum) == 1


@pytest.mark.django_db
def test_adding_more_kits_than_the_scarcest_component_allows_is_refused(api, product, kit, components):
    cleanser, serum = components
    response = api.post(f"{API}cart-view/", {"product": product.id, "user": "undefined", "qty": 4,
                                             "variant": kit.pk, "country": "India", "cart_id": "cart-kit-2"})
    assert response.status_code == 400
    assert "Only 3 left" in str(response.content)
    assert StockReservation.objects.count() == 0
    assert available_qty(cleanser) == 8


# --------------------------------------------------------------------------- order lifecycle

@pytest.mark.django_db
def test_checking_out_a_kit_puts_the_component_holds_on_the_kits_order_line(api, product, kit, components):
    from store.models import CartOrder

    cleanser, serum = components
    api.post(f"{API}cart-view/", {"product": product.id, "user": "undefined", "qty": 2, "variant": kit.pk,
                                  "country": "India", "cart_id": "cart-kit-3"})
    api.post(f"{API}create-order/", {"full_name": "Asha Rao", "email": "asha@example.com", "mobile": "9876543210",
                                     "address": "12 MG Road", "city": "Ludhiana", "state": "Punjab",
                                     "country": "India", "pincode": "141001", "cart_id": "cart-kit-3"})
    order = CartOrder.objects.get(idempotency_key="cart-kit-3")
    item = order.orderitem.get()

    assert item.variant_id == kit.pk                 # one line, the kit, at the kit's price
    assert item.qty == 2
    holds = StockReservation.objects.filter(order=order, status=ReservationStatus.ACTIVE)
    assert holds.count() == 2
    # Both component holds belong to the kit's line, not to lines of their own.
    assert {hold.order_item_id for hold in holds} == {item.pk}
    assert {hold.kit_variant_id for hold in holds} == {kit.pk}
    assert available_qty(kit) == 1


@pytest.mark.django_db
def test_cancelling_a_kit_order_returns_every_component(kit, components, make_order):
    cleanser, serum = components
    order = make_order()
    reserve_kit(kit, 2, cart_id="c1", order=order)
    assert available_qty(cleanser) == 6
    assert available_qty(serum) == 1

    release_for_order(order, reason="customer changed mind")

    assert available_qty(cleanser) == 8
    assert available_qty(serum) == 3
    assert available_qty(kit) == 3
    assert on_hand_qty(cleanser) == 8                # nothing physically moved
    assert on_hand_qty(serum) == 3


@pytest.mark.django_db
def test_dispatching_a_kit_consumes_each_component_exactly_once(kit, components, make_order, product):
    from store.models import CartOrderItem

    cleanser, serum = components
    order = make_order(payment_status="paid")
    item = CartOrderItem.objects.create(order=order, product=product, variant=kit, qty=2,
                                        price=Decimal("699.00"), sub_total=Decimal("1398.00"),
                                        total=Decimal("1398.00"))
    reserve_kit(kit, 2, cart_id="c1", order=order, order_item=item)

    movements = consume_for_order(order)

    assert len(movements) == 2
    assert {m.variant_id: -m.quantity for m in movements} == {cleanser.pk: 2, serum.pk: 2}
    assert all(m.kind == MovementKind.SALE_OUT for m in movements)
    assert on_hand_qty(cleanser) == 6
    assert on_hand_qty(serum) == 1
    assert on_hand_qty(kit) == 0                     # the kit itself never moves

    # Dispatching again must not take the stock a second time.
    assert consume_for_order(order) == []
    assert on_hand_qty(cleanser) == 6
    assert on_hand_qty(serum) == 1


@pytest.mark.django_db
def test_paying_after_the_hold_lapsed_re_reserves_the_whole_kit(kit, components, make_order, product):
    from store.models import CartOrderItem

    cleanser, serum = components
    order = make_order(payment_status="paid")
    item = CartOrderItem.objects.create(order=order, product=product, variant=kit, qty=1,
                                        price=Decimal("699.00"), sub_total=Decimal("699.00"),
                                        total=Decimal("699.00"))
    reserve_kit(kit, 1, cart_id="c1", order=order, order_item=item)
    # The customer took their time: the checkout holds lapsed before the payment landed.
    StockReservation.objects.filter(order=order).update(expires_at=timezone.now() - timedelta(minutes=1))

    assert hold_for_order(order) == []               # no shortfall: the stock is still there

    live = StockReservation.objects.filter(order=order, status=ReservationStatus.ACTIVE,
                                           expires_at__gt=timezone.now())
    assert {r.variant_id: r.quantity for r in live} == {cleanser.pk: 1, serum.pk: 1}
    assert available_qty(cleanser) == 7
    assert available_qty(serum) == 2

    # Running it again must not stack a second set of holds on the same line.
    assert hold_for_order(order) == []
    assert StockReservation.objects.filter(order=order, status=ReservationStatus.ACTIVE,
                                           expires_at__gt=timezone.now()).count() == 2


@pytest.mark.django_db
def test_a_paid_kit_order_whose_component_is_gone_is_reported_not_silently_dropped(kit, components, make_order,
                                                                                   product):
    from store.models import CartOrderItem

    cleanser, serum = components
    order = make_order(payment_status="paid")
    item = CartOrderItem.objects.create(order=order, product=product, variant=kit, qty=2,
                                        price=Decimal("699.00"), sub_total=Decimal("1398.00"),
                                        total=Decimal("1398.00"))
    reserve_kit(kit, 2, cart_id="c1", order=order, order_item=item)
    StockReservation.objects.filter(order=order).update(expires_at=timezone.now() - timedelta(minutes=1))
    # While the payment was in flight, someone else took all the serum.
    reserve(serum, 3, cart_id="someone-else")

    shortfalls = hold_for_order(order)

    assert [(shortfall_item.pk, missing) for shortfall_item, missing in shortfalls] == [(item.pk, 2)]
    # The payment has been taken, so nothing raises: the owner is told instead.
    assert order.payment_status == "paid"


# --------------------------------------------------------------------------- kit rules (Z7)

@pytest.mark.django_db
def test_a_kit_cannot_contain_itself(kit):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            KitComponent.objects.create(kit_variant=kit, component_variant=kit, qty=1)


@pytest.mark.django_db
def test_a_component_cannot_be_listed_twice_in_the_same_kit(kit, components):
    cleanser, _serum = components
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            KitComponent.objects.create(kit_variant=kit, component_variant=cleanser, qty=2)


@pytest.mark.django_db
def test_the_owner_cannot_put_a_kit_or_a_sample_inside_a_kit(auth, staff, product, kit, components):
    client = auth(staff)
    other_kit = add_variant(product, "SKU-KIT-2", "Hair routine", is_kit=True)
    sample = add_variant(product, "SKU-SAMPLE", "5 g sample", price_paise=0, is_sample=True)

    nested = client.post(f"{API}owner/kits/{kit.pk}/components/", {"component_variant_id": other_kit.pk, "qty": 1})
    assert nested.status_code == 400
    assert "another kit" in nested.json()["message"]

    gift = client.post(f"{API}owner/kits/{kit.pk}/components/", {"component_variant_id": sample.pk, "qty": 1})
    assert gift.status_code == 400
    assert "given away" in gift.json()["message"]

    itself = client.post(f"{API}owner/kits/{kit.pk}/components/", {"component_variant_id": kit.pk, "qty": 1})
    assert itself.status_code == 400
    assert "contain itself" in itself.json()["message"]

    assert KitComponent.objects.filter(kit_variant=kit).count() == 2


@pytest.mark.django_db
def test_a_size_cannot_be_a_kit_and_a_sample_at_once(auth, staff, product):
    client = auth(staff)
    response = client.post(
        f"{API}owner/products/{product.pid}/variants/",
        {"label": "Both", "net_quantity": "50", "net_quantity_unit": "g", "price": "100",
         "weight_grams": "100", "is_kit": True, "is_sample": True},
    )
    assert response.status_code == 400
    assert "not both" in str(response.content)
    assert not ProductVariant.objects.filter(product=product, name="Both").exists()


@pytest.mark.django_db
def test_stock_cannot_be_booked_against_a_kit(auth, staff, kit):
    """A kit has no stock of its own, so a batch against it would be a number nothing can sell."""
    client = auth(staff)
    response = client.post(f"{API}owner/variants/{kit.pk}/stock/", {"quantity": "10"})
    assert response.status_code == 400
    assert "no stock of its own" in response.json()["message"]
    assert on_hand_qty(kit) == 0


@pytest.mark.django_db
def test_adding_a_kit_size_never_takes_over_the_placeholder_size(auth, staff, vendor, config_settings):
    """
    A product made in the old form starts with a stocked placeholder called "Default".

    A real size takes that placeholder over and keeps its stock. A kit must not: its stock
    lives in its components, so adopting the placeholder would strand those units.
    """
    from store.models import Product

    client = auth(staff)
    product = Product.objects.create(title="Gift Set", price=Decimal("10.00"), shipping_amount=Decimal("0.00"),
                                     stock_qty=5, status="published", vendor=vendor)
    placeholder = ProductVariant.objects.get(product=product, is_default=True)
    assert placeholder.name == "Default"

    response = client.post(f"{API}owner/products/{product.pid}/variants/",
                           {"label": "Festive kit", "net_quantity": "100", "net_quantity_unit": "g",
                            "price": "999", "weight_grams": "400", "is_kit": True})
    assert response.status_code == 201

    placeholder.refresh_from_db()
    assert placeholder.name == "Default"             # untouched, and still holding its stock
    assert placeholder.is_kit is False
    kit_variant = ProductVariant.objects.get(product=product, name="Festive kit")
    assert kit_variant.is_kit is True
    assert kit_variant.is_default is False
    assert on_hand_qty(kit_variant) == 0


@pytest.mark.django_db
def test_the_kit_price_is_the_owners_and_is_never_the_sum_of_the_parts(kit, components):
    cleanser, serum = components
    assert kit.price_paise == 69900
    assert cleanser.price_paise + serum.price_paise == 80000
    # Changing a component's price does not move the kit's price (ROADMAP Z7).
    cleanser.price_paise = 40000
    cleanser.save(update_fields=["price_paise"])
    kit.refresh_from_db()
    assert kit.price_paise == 69900


# --------------------------------------------------------------------------- what the shopper sees

@pytest.mark.django_db
def test_the_product_page_lists_what_is_inside_a_kit_and_never_a_component_price(api, product, kit):
    response = api.get(f"{API}products/{product.slug}/")
    assert response.status_code == 200
    variants = {v["sku"]: v for v in response.json()["variants"]}

    kit_row = variants["SKU-KIT-FACE"]
    assert kit_row["is_kit"] is True
    assert kit_row["available_qty"] == 3
    assert kit_row["stock"]["label"] == "Only 3 left"
    assert [part["variant"] for part in kit_row["kit_contents"]] == ["Cleanser 50 g", "Serum 30 ml"]
    assert all(part["qty"] == 1 for part in kit_row["kit_contents"])
    # The parts are described, never priced: the kit has one price of its own.
    assert not any("price" in key for part in kit_row["kit_contents"] for key in part)

    assert variants["SKU-CLEANSER"]["is_kit"] is False
    assert variants["SKU-CLEANSER"]["kit_contents"] == []


# --------------------------------------------------------------------------- owner kit builder

@pytest.mark.django_db
def test_the_owner_builds_a_kit_and_sees_what_is_holding_it_back(auth, staff, product, components):
    cleanser, serum = components
    client = auth(staff)
    kit_variant = add_variant(product, "SKU-KIT-BUILD", "Build me", price_paise=50000, is_kit=True)

    created = client.post(f"{API}owner/kits/{kit_variant.pk}/components/",
                          {"component_variant_id": cleanser.pk, "qty": 2})
    assert created.status_code == 201
    assert created.json()["available"] == 4          # 8 cleansers, 2 per kit

    client.post(f"{API}owner/kits/{kit_variant.pk}/components/", {"component_variant_id": serum.pk, "qty": 1})

    listing = client.get(f"{API}owner/kits/").json()
    row = next(k for k in listing["kits"] if k["variant_id"] == kit_variant.pk)
    assert row["available"] == 3                     # the serum is the bottleneck
    assert row["price"] == "₹500.00"
    assert {c["sku"]: c["kits_possible"] for c in row["components"]} == {"SKU-CLEANSER": 4, "SKU-SERUM": 3}
    # Neither the kit itself nor the sample-free candidate list offers a kit as a component.
    assert kit_variant.pk not in [c["variant_id"] for c in listing["candidates"]]


@pytest.mark.django_db
def test_the_owner_changes_a_quantity_and_removes_a_part_with_an_audit_trail(auth, staff, kit, components):
    from core.models import AuditLog

    cleanser, serum = components
    client = auth(staff)
    part = KitComponent.objects.get(kit_variant=kit, component_variant=cleanser)

    changed = client.patch(f"{API}owner/kit-components/{part.pk}/", {"qty": 4})
    assert changed.status_code == 200
    assert changed.json()["available"] == 2          # 8 cleansers, 4 per kit
    assert AuditLog.objects.filter(action="kit.component_updated").latest("id").after["qty"] == 4

    removed = client.delete(f"{API}owner/kit-components/{part.pk}/")
    assert removed.status_code == 200
    assert removed.json()["available"] == 3          # only the serum is left to limit it
    assert AuditLog.objects.filter(action="kit.component_removed").latest("id").before["qty"] == 4
    assert KitComponent.objects.filter(kit_variant=kit).count() == 1


@pytest.mark.django_db
def test_adding_the_same_part_twice_is_refused_with_a_reason(auth, staff, kit, components):
    cleanser, _serum = components
    client = auth(staff)
    response = client.post(f"{API}owner/kits/{kit.pk}/components/",
                           {"component_variant_id": cleanser.pk, "qty": 1})
    assert response.status_code == 400
    assert "already in this kit" in response.json()["message"]


@pytest.mark.django_db
def test_a_part_can_only_be_added_to_a_size_that_is_a_kit(auth, staff, components, product):
    cleanser, serum = components
    client = auth(staff)
    response = client.post(f"{API}owner/kits/{cleanser.pk}/components/",
                           {"component_variant_id": serum.pk, "qty": 1})
    assert response.status_code == 400
    assert "not a kit" in response.json()["message"]


@pytest.mark.django_db
def test_the_kit_builder_is_closed_to_customers(api, auth, customer, kit, components):
    cleanser, _serum = components
    assert api.get(f"{API}owner/kits/").status_code in (401, 403)
    assert auth(customer).get(f"{API}owner/kits/").status_code == 403
    assert auth(customer).post(f"{API}owner/kits/{kit.pk}/components/",
                               {"component_variant_id": cleanser.pk, "qty": 1}).status_code == 403


# --------------------------------------------------------------------------- concurrency

class ConcurrentKitCheckoutTest(TransactionTestCase):
    """
    Two shoppers, one serum left, one of them buying it inside a kit: exactly one must win.

    This needs real row locking, so it is skipped on SQLite (where select_for_update is a
    no-op) rather than passing for the wrong reason.
    """

    reset_sequences = True

    def _build(self):
        from store.models import Product
        from userauths.models import User
        from vendor.models import Vendor

        owner = User.objects.create_user(email="kit-owner@example.com", username="kit-owner", password="x")
        shop = Vendor.objects.create(user=owner, name="Shop", slug="kit-shop")
        product = Product.objects.create(title="Face Routine", price=Decimal("10.00"),
                                         shipping_amount=Decimal("0.00"), stock_qty=0,
                                         status="published", vendor=shop)
        cleanser = add_variant(product, "RACE-CLEANSER", "Cleanser", price_paise=30000)
        serum = add_variant(product, "RACE-SERUM", "Serum", price_paise=50000)
        make_batch(cleanser, "RACE-C1", 5)
        make_batch(serum, "RACE-S1", 1)              # the last serum in the building
        kit = add_variant(product, "RACE-KIT", "Face routine", price_paise=69900, is_kit=True)
        KitComponent.objects.create(kit_variant=kit, component_variant=cleanser, qty=1)
        KitComponent.objects.create(kit_variant=kit, component_variant=serum, qty=1)
        return kit, cleanser, serum

    def test_two_shoppers_racing_for_the_last_component_cannot_both_get_it(self):
        if connection.vendor != "postgresql":
            self.skipTest(f"needs PostgreSQL row locking; running on {connection.vendor}")

        import threading

        kit, cleanser, serum = self._build()
        self.assertEqual(kit_available_qty(kit), 1)

        results = []
        barrier = threading.Barrier(2)

        def attempt(cart_id, buy_the_kit):
            barrier.wait()
            try:
                with transaction.atomic():
                    if buy_the_kit:
                        reserve_kit(kit, 1, cart_id=cart_id)
                    else:
                        reserve(serum, 1, cart_id=cart_id)
                results.append("ok")
            except InsufficientStock:
                results.append("rejected")
            finally:
                connection.close()

        threads = [
            threading.Thread(target=attempt, args=("race-kit", True)),
            threading.Thread(target=attempt, args=("race-serum", False)),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(sorted(results), ["ok", "rejected"])
        self.assertEqual(available_qty(serum), 0)
        self.assertEqual(kit_available_qty(kit), 0)
        # The loser left nothing held behind: either one serum hold (the direct buyer) or one
        # serum plus one cleanser (the kit buyer), never a stray cleanser on its own.
        holds = StockReservation.objects.filter(status=ReservationStatus.ACTIVE)
        self.assertEqual(holds.filter(variant=serum).count(), 1)
        self.assertIn(holds.filter(variant=cleanser).count(), (0, 1))
        self.assertEqual(holds.filter(variant=cleanser).count(), 1 if "race-kit" in
                         list(holds.values_list("cart_id", flat=True)) else 0)

    def test_two_shoppers_racing_for_the_last_kit_cannot_both_get_it(self):
        if connection.vendor != "postgresql":
            self.skipTest(f"needs PostgreSQL row locking; running on {connection.vendor}")

        import threading

        kit, cleanser, serum = self._build()

        results = []
        barrier = threading.Barrier(2)

        def attempt(cart_id):
            barrier.wait()
            try:
                with transaction.atomic():
                    reserve_kit(kit, 1, cart_id=cart_id)
                results.append("ok")
            except InsufficientStock:
                results.append("rejected")
            finally:
                connection.close()

        threads = [threading.Thread(target=attempt, args=(f"race-kit-{i}",)) for i in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(sorted(results), ["ok", "rejected"])
        self.assertEqual(kit_available_qty(kit), 0)
        # The loser rolled back completely: the winner's two holds are all there are.
        self.assertEqual(StockReservation.objects.filter(status=ReservationStatus.ACTIVE).count(), 2)
        self.assertEqual(available_qty(cleanser), 4)
