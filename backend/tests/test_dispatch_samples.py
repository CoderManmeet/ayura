"""
Phase D (Ayura): dispatch checks, free samples, expiry and batch lookup.

Covers the owner seeing which batch each line goes out from (with expired and undated ones
flagged, never blocked), gift samples that are held, dispatched as SAMPLE_OUT exactly once and
never charged or shown to the customer, the samples conversion report, writing stock off
through the ledger, and the recall lookup.

Fails before Phase D (store.samples, store.owner_dispatch, the sample fields and the endpoints
do not exist) and passes after it.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from catalog.models import ProductVariant
from core.models import AuditLog
from inventory.models import Batch, MovementKind, ReservationStatus, StockMovement, StockReservation
from inventory.services import available_qty, on_hand_qty, receive_production, reserve
from store.models import SAMPLE_ADDED, SAMPLE_NONE, CartOrder, OrderSample
from store.order_state import advance_order_delivery, cancel_order
from tests.test_payments import draft
from tests.test_pricing import add_stock, make_candle

API = "/api/v1/"


@pytest.fixture
def scrub(vendor, config_settings):
    """A sellable product with stock: Face Scrub 100 g."""
    return make_candle(vendor, "Face Scrub", 54900, stock=20)


def make_sample(sellable_variant, name="10 ml sample", stock=10):
    """A hidden giveaway size of the same product, with its own SKU and its own stock."""
    sample = ProductVariant.objects.create(
        product=sellable_variant.product, name=name, sku=f"SAMPLE-{sellable_variant.sku}",
        price_paise=0, mrp_paise=None, is_default=False, active=True, is_sample=True,
        options={"Size": name},
    )
    if stock:
        add_stock(sample, stock)
    return sample


def dated_batch(variant, days_from_today, qty=5):
    """A batch of `variant` whose use-by date is `days_from_today` away (negative = expired)."""
    today = timezone.localdate()
    batch = Batch.objects.create(
        batch_code=f"B{variant.sku}-{days_from_today}-{Batch.objects.count()}", variant=variant,
        manufactured_on=today - timedelta(days=200),
        best_before=today + timedelta(days=days_from_today),
        quantity_produced=qty, cost_per_unit_paise=0,
    )
    receive_production(variant, batch, qty)
    return batch


# --------------------------------------------------------------------- shelf life (Z1)

def test_the_shipped_shelf_life_default_is_zero_days(shipped_setting):
    """
    ROADMAP Z1: out of the box, only an ALREADY EXPIRED batch is held back.

    Read with no .env loaded at all (see the `shipped_setting` fixture), so a value in anyone's
    own `backend/.env` cannot hide a change to the default the store ships with. An earlier
    version of this test did not isolate .env and so only ever read the local value; it was
    found when the owner's own .env still carried the Phase C value of 30.
    """
    assert shipped_setting("MIN_SHELF_LIFE_ON_DISPATCH_DAYS") == "0"


def test_a_local_env_file_cannot_disguise_a_shipped_default(shipped_setting):
    """
    The isolation the test above relies on is itself load-bearing, so it is checked.

    With the variable set in the environment the subprocess reports THAT value; with it unset
    and no .env loaded it reports the shipped 0. If `DJANGO_ENV_FILE` ever stopped working, the
    test above would quietly go back to reporting whatever the local .env says.
    """
    assert shipped_setting("MIN_SHELF_LIFE_ON_DISPATCH_DAYS",
                           extra_env={"MIN_SHELF_LIFE_ON_DISPATCH_DAYS": "45"}) == "45"
    assert shipped_setting("MIN_SHELF_LIFE_ON_DISPATCH_DAYS") == "0"


@pytest.mark.django_db
def test_only_an_expired_batch_is_held_back_from_allocation(settings, vendor, config_settings):
    settings.MIN_SHELF_LIFE_ON_DISPATCH_DAYS = 0  # ROADMAP Z1; proven above to be the default

    variant = make_candle(vendor, "Serum", 44900, stock=0)
    expired = dated_batch(variant, -1, qty=4)
    soon = dated_batch(variant, 3, qty=5)
    undated = add_stock(variant, 6)

    # 11 units are on hand, but the 4 expired ones can never be sold.
    assert on_hand_qty(variant) == 15
    assert available_qty(variant) == 15          # availability counts physical stock
    holds = reserve(variant, 11)                 # everything that may be allocated
    taken = {hold.batch_id for hold in holds}
    assert expired.pk not in taken
    assert taken == {soon.pk, undated.pk}        # a date 3 days away is still fine at 0 days

    # Nothing is left to allocate, although the expired units are still physically there.
    with pytest.raises(Exception):
        reserve(variant, 1)


# --------------------------------------------------------------------- dispatch checks

@pytest.mark.django_db
def test_handle_orders_flags_expired_and_undated_batches_without_blocking(api, auth, staff, vendor, config_settings, settings):
    settings.MIN_SHELF_LIFE_ON_DISPATCH_DAYS = 0
    variant = make_candle(vendor, "Body Butter", 44900, stock=0)
    dated_batch(variant, -2, qty=5)              # expired: allocated to nothing
    undated = add_stock(variant, 5)              # no use-by date: sells normally
    order = draft(api, variant, qty=2, cart_id="d-1")
    api.post(f"{API}payments/cod/{order.oid}/")

    owner = auth(staff)
    body = owner.get(f"{API}owner/orders/{order.oid}/dispatch/").json()
    line = body["lines"][0]
    assert line["qty"] == 2
    assert [row["batch_code"] for row in line["batches"]] == [undated.batch_code]
    assert line["has_undated"] is True and line["has_expired"] is False
    assert body["any_undated"] is True

    # The owner records the missing date from here (the Phase B batch endpoint), and the flag clears.
    use_by = (timezone.localdate() + timedelta(days=120)).isoformat()
    assert owner.patch(f"{API}owner/batches/{undated.pk}/", {"best_before": use_by}, format="json").status_code == 200
    body = owner.get(f"{API}owner/orders/{order.oid}/dispatch/").json()
    assert body["lines"][0]["batches"][0]["best_before"] == use_by
    assert body["any_undated"] is False
    assert AuditLog.objects.filter(action="batch.updated").exists()

    # An undated batch never stopped the parcel going out.
    owner.post(f"{API}owner/orders/{order.oid}/action/", {"action": "confirm_cod"})
    shipped = owner.post(f"{API}owner/orders/{order.oid}/action/", {"action": "set_delivery", "status": "Shipped"})
    assert shipped.status_code == 200


@pytest.mark.django_db
def test_a_line_whose_batch_expired_after_allocation_is_shown_as_expired(api, auth, staff, vendor, config_settings, settings):
    settings.MIN_SHELF_LIFE_ON_DISPATCH_DAYS = 0
    variant = make_candle(vendor, "Hair Oil", 29900, stock=0)
    batch = dated_batch(variant, 10, qty=5)
    order = draft(api, variant, qty=1, cart_id="d-2")
    api.post(f"{API}payments/cod/{order.oid}/")

    # Time passes and the allocated batch goes out of date before the parcel is sent.
    Batch.objects.filter(pk=batch.pk).update(best_before=timezone.localdate() - timedelta(days=1))

    body = auth(staff).get(f"{API}owner/orders/{order.oid}/dispatch/").json()
    assert body["lines"][0]["batches"][0]["expired"] is True
    assert body["any_expired"] is True


# --------------------------------------------------------------------- gift samples

@pytest.mark.django_db
def test_samples_are_held_dispatched_once_as_sample_out_and_never_charged(api, auth, staff, vendor, config_settings):
    scrub = make_candle(vendor, "Face Scrub", 54900, stock=10)
    sample = make_sample(scrub, stock=4)
    order = draft(api, scrub, qty=1, cart_id="s-1")
    api.post(f"{API}payments/cod/{order.oid}/")
    order.refresh_from_db()
    total_before = order.total_paise

    owner = auth(staff)
    url = f"{API}owner/orders/{order.oid}/samples/"
    added = owner.post(url, {"action": "add", "variant_id": sample.pk, "qty": 2}, format="json")
    assert added.status_code == 200
    assert added.json()["samples"][0]["qty"] == 2
    assert added.json()["sample_decision"] == SAMPLE_ADDED

    order.refresh_from_db()
    assert order.total_paise == total_before          # a gift never changes what is owed
    assert available_qty(sample) == 2                 # 2 of 4 are now held
    assert on_hand_qty(sample) == 4

    # Dispatch: the sample leaves as SAMPLE_OUT, exactly once, and is never a sale.
    owner.post(f"{API}owner/orders/{order.oid}/action/", {"action": "confirm_cod"})
    owner.post(f"{API}owner/orders/{order.oid}/action/", {"action": "set_delivery", "status": "Shipped"})
    owner.post(f"{API}owner/orders/{order.oid}/action/", {"action": "set_delivery", "status": "Delivered"})

    moves = StockMovement.objects.filter(variant=sample).order_by("id")
    assert [move.kind for move in moves] == [MovementKind.PRODUCTION_IN, MovementKind.SAMPLE_OUT]
    assert on_hand_qty(sample) == 2
    assert not StockMovement.objects.filter(variant=sample, kind=MovementKind.SALE_OUT).exists()
    # The bought line left as a sale, as always.
    assert StockMovement.objects.filter(variant=scrub, kind=MovementKind.SALE_OUT).count() == 1

    order.refresh_from_db()
    assert order.total_paise == total_before


@pytest.mark.django_db
def test_a_sample_can_be_removed_and_cannot_be_added_to_a_cancelled_order(api, auth, staff, vendor, config_settings):
    scrub = make_candle(vendor, "Face Scrub", 54900, stock=10)
    sample = make_sample(scrub, stock=3)
    order = draft(api, scrub, qty=1, cart_id="s-2")
    api.post(f"{API}payments/cod/{order.oid}/")
    owner = auth(staff)
    url = f"{API}owner/orders/{order.oid}/samples/"

    owner.post(url, {"action": "add", "variant_id": sample.pk, "qty": 1}, format="json")
    assert available_qty(sample) == 2
    sample_id = OrderSample.objects.get(order=order).pk

    # The same sample twice is refused; the quantity is changed by removing and adding again.
    again = owner.post(url, {"action": "add", "variant_id": sample.pk, "qty": 1}, format="json")
    assert again.status_code == 400 and "already on this order" in again.json()["message"]

    removed = owner.post(url, {"action": "remove", "sample_id": sample_id}, format="json")
    assert removed.status_code == 200 and removed.json()["samples"] == []
    assert available_qty(sample) == 3                 # the hold came back
    assert OrderSample.objects.count() == 0

    # "No samples" is a decision the owner records.
    none = owner.post(url, {"action": "none"}, format="json")
    assert none.status_code == 200 and none.json()["sample_decision"] == SAMPLE_NONE

    # More than there are is refused, and writes nothing.
    too_many = owner.post(url, {"action": "add", "variant_id": sample.pk, "qty": 99}, format="json")
    assert too_many.status_code == 400 and "Only 3" in too_many.json()["message"]
    assert OrderSample.objects.count() == 0

    # A cancelled order takes no samples.
    cancel_order(order, actor=staff)
    refused = owner.post(url, {"action": "add", "variant_id": sample.pk, "qty": 1}, format="json")
    assert refused.status_code == 400 and "cancelled" in refused.json()["message"]
    assert OrderSample.objects.count() == 0


@pytest.mark.django_db
def test_cancelling_an_order_gives_a_sample_hold_back(api, auth, staff, vendor, config_settings):
    scrub = make_candle(vendor, "Face Scrub", 54900, stock=10)
    sample = make_sample(scrub, stock=3)
    order = draft(api, scrub, qty=1, cart_id="s-3")
    api.post(f"{API}payments/cod/{order.oid}/")
    auth(staff).post(f"{API}owner/orders/{order.oid}/samples/",
                     {"action": "add", "variant_id": sample.pk, "qty": 2}, format="json")
    assert available_qty(sample) == 1

    cancel_order(order, actor=staff)
    assert available_qty(sample) == 3
    assert not StockReservation.objects.filter(sample__order=order, status=ReservationStatus.ACTIVE).exists()


@pytest.mark.django_db
def test_a_sample_is_invisible_to_the_shop_and_to_the_customer(api, auth, customer, staff, vendor, config_settings):
    scrub = make_candle(vendor, "Face Scrub", 54900, stock=10)
    sample = make_sample(scrub, stock=3)

    # Not in the shop, not in the size picker, and not addable to a cart.
    listing = api.get(f"{API}products/").json()
    body = api.get(f"{API}products/{scrub.product.slug}/").json()
    assert sample.sku not in str(listing)
    assert [v["sku"] for v in body["variants"]] == [scrub.sku]
    refused = api.post(f"{API}cart-view/", {"product": scrub.product_id, "variant": sample.pk, "qty": 1,
                                            "user": "undefined", "country": "India", "cart_id": "s-4"})
    assert refused.status_code == 400

    # The owner adds one to a signed-in customer's order...
    order = draft(auth(customer), scrub, qty=1, cart_id="s-5", user_id=customer.id)
    api.post(f"{API}payments/cod/{order.oid}/")
    auth(staff).post(f"{API}owner/orders/{order.oid}/samples/",
                     {"action": "add", "variant_id": sample.pk, "qty": 1}, format="json")

    # ...and the customer is never told, anywhere (ROADMAP Y19).
    for payload in (api.get(f"{API}checkout/{order.oid}/").json(),
                    auth(customer).get(f"{API}customer/order/detail/{customer.id}/{order.oid}/").json(),
                    auth(customer).get(f"{API}customer/orders/{customer.id}/").json()):
        text = str(payload).lower()
        assert "sample" not in text
        assert sample.sku.lower() not in text

    # The owner's own view does say so.
    owner_order = auth(staff).get(f"{API}owner/orders/{order.oid}/").json()
    assert owner_order["sample_decision"] == SAMPLE_ADDED


@pytest.mark.django_db
def test_the_samples_report_counts_only_people_who_came_back_for_that_product(
        api, auth, staff, customer, vendor, config_settings):
    scrub = make_candle(vendor, "Face Scrub", 54900, stock=30)
    oil = make_candle(vendor, "Hair Oil", 29900, stock=30)
    sample = make_sample(scrub, stock=10)
    owner = auth(staff)

    def place(cart_id, email, qty_variant, **extra):
        variant, qty = qty_variant
        order = draft(api, variant, qty=qty, cart_id=cart_id, email=email, **extra)
        api.post(f"{API}payments/cod/{order.oid}/")
        return CartOrder.objects.get(pk=order.pk)

    # Asha gets a Face Scrub sample, then buys Face Scrub later: converted.
    asha_first = place("r-1", "asha@example.com", (oil, 1), mobile="9000000011")
    owner.post(f"{API}owner/orders/{asha_first.oid}/samples/",
               {"action": "add", "variant_id": sample.pk, "qty": 1}, format="json")
    asha_later = place("r-2", "asha@example.com", (scrub, 1), mobile="9000000011")

    # Bina gets the same sample and only ever buys Hair Oil: not converted.
    bina_first = place("r-3", "bina@example.com", (oil, 1), mobile="9000000012")
    owner.post(f"{API}owner/orders/{bina_first.oid}/samples/",
               {"action": "add", "variant_id": sample.pk, "qty": 1}, format="json")
    place("r-4", "bina@example.com", (oil, 2), mobile="9000000012")

    # The follow-up orders must come after the sample orders.
    CartOrder.objects.filter(pk__in=[asha_first.pk, bina_first.pk]).update(date=timezone.now() - timedelta(days=30))

    report = owner.get(f"{API}owner/samples-report/").json()["rows"]
    assert len(report) == 1
    row = report[0]
    assert (row["sku"], row["given"], row["converted"], row["conversion_percent"]) == (sample.sku, 2, 1, 50)
    assert row["conversions"][0]["sample_order"] == asha_first.oid
    assert [entry["oid"] for entry in row["conversions"][0]["then_bought"]] == [asha_later.oid]
    assert customer.pk  # fixture used, no signed-in customer needed for the email match


# --------------------------------------------------------------------- expiry and write-off

@pytest.mark.django_db
def test_the_expiry_screen_lists_expired_due_soon_and_undated_stock(api, auth, staff, vendor, config_settings):
    variant = make_candle(vendor, "Body Oil", 39900, stock=0)
    expired = dated_batch(variant, -5, qty=3)
    soon = dated_batch(variant, 10, qty=4)
    dated_batch(variant, 900, qty=5)             # far away: not listed
    undated = add_stock(variant, 6)

    body = auth(staff).get(f"{API}owner/expiry/").json()
    assert [row["batch_code"] for row in body["expired"]] == [expired.batch_code]
    assert [row["batch_code"] for row in body["expiring_soon"]] == [soon.batch_code]
    assert [row["batch_code"] for row in body["undated"]] == [undated.batch_code]
    assert body["expired"][0]["on_hand"] == 3


@pytest.mark.django_db
def test_writing_stock_off_goes_through_the_ledger_and_never_touches_held_stock(
        api, auth, staff, vendor, config_settings, settings):
    settings.MIN_SHELF_LIFE_ON_DISPATCH_DAYS = 0
    variant = make_candle(vendor, "Shampoo", 34900, stock=0)
    batch = dated_batch(variant, 100, qty=6)
    order = draft(api, variant, qty=2, cart_id="w-1")   # 2 units held for a customer
    api.post(f"{API}payments/cod/{order.oid}/")
    owner = auth(staff)
    url = f"{API}owner/batches/{batch.pk}/write-off/"

    assert owner.post(url, {"quantity": 2}, format="json").status_code == 400          # no reason
    assert owner.post(url, {"quantity": 2.5, "reason": "x"}, format="json").status_code == 400
    too_many = owner.post(url, {"quantity": 6, "reason": "past its date"}, format="json")
    assert too_many.status_code == 400 and "Only 4" in too_many.json()["message"]
    assert on_hand_qty(variant) == 6

    done = owner.post(url, {"quantity": 4, "reason": "past its date"}, format="json")  # the 2 held units stay
    assert done.status_code == 200 and done.json()["on_hand"] == 2
    movement = StockMovement.objects.get(variant=variant, kind=MovementKind.DAMAGE_OUT)
    assert movement.quantity == -4 and movement.reason == "past its date"
    assert on_hand_qty(variant) == 2
    assert AuditLog.objects.filter(action="stock.movement").exists()


# --------------------------------------------------------------------- recall lookup

@pytest.mark.django_db
def test_batch_lookup_lists_exactly_the_orders_that_got_that_batch(api, auth, staff, vendor, config_settings):
    scrub = make_candle(vendor, "Face Scrub", 54900, stock=0)
    first = dated_batch(scrub, 100, qty=2)
    second = dated_batch(scrub, 200, qty=5)
    sample = make_sample(scrub, stock=0)
    sample_batch = dated_batch(sample, 150, qty=3)
    owner = auth(staff)

    # Order A takes the whole of the first batch (FEFO) and is sent.
    order_a = draft(api, scrub, qty=2, cart_id="b-1")
    api.post(f"{API}payments/cod/{order_a.oid}/")
    owner.post(f"{API}owner/orders/{order_a.oid}/samples/",
               {"action": "add", "variant_id": sample.pk, "qty": 1}, format="json")
    owner.post(f"{API}owner/orders/{order_a.oid}/action/", {"action": "confirm_cod"})
    owner.post(f"{API}owner/orders/{order_a.oid}/action/", {"action": "set_delivery", "status": "Shipped"})

    # Order B takes from the second batch and has not been sent yet.
    order_b = draft(api, scrub, qty=1, cart_id="b-2", email="b@example.com", mobile="9000000013")
    api.post(f"{API}payments/cod/{order_b.oid}/")

    found = owner.get(f"{API}owner/batch-lookup/", {"code": first.batch_code}).json()
    assert found["found"] is True
    assert [row["oid"] for row in found["orders"]] == [order_a.oid]
    assert found["orders"][0]["quantity"] == 2 and found["orders"][0]["dispatched"] is True
    assert found["orders"][0]["sample_only"] is False

    other = owner.get(f"{API}owner/batch-lookup/", {"code": second.batch_code}).json()
    assert [row["oid"] for row in other["orders"]] == [order_b.oid]
    assert other["orders"][0]["dispatched"] is False      # still only on hold

    # The sample's own batch points at the order that received it, as a sample.
    gift = owner.get(f"{API}owner/batch-lookup/", {"code": sample_batch.batch_code}).json()
    assert [row["oid"] for row in gift["orders"]] == [order_a.oid]
    assert gift["orders"][0]["sample_only"] is True

    assert owner.get(f"{API}owner/batch-lookup/", {"code": "NOPE-123"}).json()["found"] is False
    assert owner.get(f"{API}owner/batch-lookup/").status_code == 400


# --------------------------------------------------------------------- access

@pytest.mark.django_db
def test_every_phase_d_endpoint_is_staff_only(api, auth, customer, vendor, config_settings):
    variant = make_candle(vendor, "Serum", 44900, stock=5)
    batch = Batch.objects.filter(variant=variant).first()
    order = draft(api, variant, qty=1, cart_id="acc-1")

    gets = [f"{API}owner/orders/{order.oid}/dispatch/", f"{API}owner/expiry/",
            f"{API}owner/batch-lookup/?code=x", f"{API}owner/samples-report/"]
    posts = [f"{API}owner/orders/{order.oid}/samples/", f"{API}owner/batches/{batch.pk}/write-off/"]

    for url in gets:
        assert api.get(url).status_code == 401, url
        assert auth(customer).get(url).status_code == 403, url
    for url in posts:
        assert api.post(url, {}, format="json").status_code == 401, url
        assert auth(customer).post(url, {}, format="json").status_code == 403, url
    assert OrderSample.objects.count() == 0
