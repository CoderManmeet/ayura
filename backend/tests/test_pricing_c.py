"""
Phase C (Ayura): owner-set shipping and the Cash on Delivery fee.

Covers `store.pricing.quote()` with the new switches and `payment_method`, the checkout quote
endpoint, placing a COD order with the fee (and refusing it when the total the customer saw is
no longer right), Razorpay never seeing the fee, placed orders never moving when settings
change, the owner "Store settings" endpoint, and the fee row in the order email.

Fails before Phase C (the settings fields, `quote(payment_method=...)`, `quote_order` and the
endpoints do not exist) and passes after it.
"""

from decimal import Decimal

import pytest

from addon.models import ConfigSettings
from core.jobs import run_due_jobs
from core.models import AuditLog
from store.models import CartOrder
from store.money_mirror import assert_mirrors
from store.pricing import PricingConfig, quote, quote_order
from tests.test_payments import draft, order_entity, razorpay_keys, start  # noqa: F401  (fixture re-export)
from tests.test_pricing import make_candle

API = "/api/v1/"


@pytest.fixture
def serum(vendor, config_settings):
    return make_candle(vendor, "Serum", 79900, stock=20)


def set_config(**values):
    row = ConfigSettings.objects.get()
    for name, value in values.items():
        setattr(row, name, value)
    row.save()
    return row


# --------------------------------------------------------------------------- quote()

@pytest.mark.django_db
def test_with_the_fee_off_cash_on_delivery_costs_the_same(serum):
    config = PricingConfig(cod_fee_enabled=False, cod_fee_paise=4900)
    online = quote([(serum, 1)], config=config)
    cod = quote([(serum, 1)], config=config, payment_method="cod")
    assert cod.total_paise == online.total_paise == 79900 + 7900
    assert cod.cod_fee_paise == 0 and cod.payment_method == "COD"


@pytest.mark.django_db
def test_the_fee_is_added_only_for_cod_never_discounted_and_never_counts_towards_free_shipping(serum, vendor):
    from store.models import Coupon

    config = PricingConfig(cod_fee_enabled=True, cod_fee_paise=4900)
    online = quote([(serum, 1)], config=config)
    cod = quote([(serum, 1)], config=config, payment_method="COD")
    assert (online.cod_fee_paise, cod.cod_fee_paise) == (0, 4900)
    assert cod.total_paise == online.total_paise + 4900
    assert cod.as_dict()["cod_fee_if_cod_paise"] == online.as_dict()["cod_fee_if_cod_paise"] == 4900

    # A 100% coupon takes the goods to zero; the fee (and shipping) are still owed.
    Coupon.objects.create(vendor=vendor, code="ALL", discount=100, active=True)
    free_goods = quote([(serum, 1)], coupon_code="ALL", config=config, payment_method="COD")
    assert (free_goods.discount_paise, free_goods.total_paise) == (79900, 7900 + 4900)

    # Rs 950 of goods + Rs 49 fee would pass Rs 999, but the fee never counts towards it.
    near = make_candle(vendor, "Near", 95000, stock=5)
    assert quote([(near, 1)], config=config, payment_method="COD").shipping_paise == 7900

    # No lines: nothing is charged at all.
    assert quote([], config=config, payment_method="COD").total_paise == 0


@pytest.mark.django_db
def test_shipping_off_means_free_and_free_shipping_off_means_always_charged(serum):
    off = quote([(serum, 1)], config=PricingConfig(shipping_enabled=False))
    assert (off.shipping_paise, off.amount_to_free_shipping_paise, off.free_shipping) == (0, 0, True)

    always = quote([(serum, 2)], config=PricingConfig(free_shipping_enabled=False))  # Rs 1,598, above Rs 999
    assert (always.shipping_paise, always.amount_to_free_shipping_paise) == (7900, 0)
    assert always.as_dict()["free_shipping_enabled"] is False

    default = quote([(serum, 1)], config=PricingConfig())
    assert (default.shipping_paise, default.amount_to_free_shipping_paise) == (7900, 99900 - 79900)


# --------------------------------------------------------------------------- checkout

@pytest.mark.django_db
def test_checkout_shows_both_totals_and_the_edited_threshold_applies_on_the_next_quote(api, serum):
    order = draft(api, serum)
    assert order.total_paise == 79900 + 7900

    set_config(cod_fee_enabled=True, cod_fee_paise=4900, free_shipping_threshold_paise=50000)
    body = api.post(f"{API}payments/quote/{order.oid}/").json()
    assert body["draft"] is True
    assert (body["online"]["shipping_paise"], body["online"]["total_paise"]) == (0, 79900)
    assert (body["cod"]["cod_fee_paise"], body["cod"]["total_paise"]) == (4900, 79900 + 4900)

    order.refresh_from_db()
    assert (order.total_paise, order.cod_fee_paise) == (79900, 0)  # the draft now stores the online price
    assert_mirrors(order)
    row = AuditLog.objects.get(action="order.repriced", object_id=str(order.pk))
    assert (row.before["total_paise"], row.after["total_paise"]) == (87800, 79900)

    set_config(cod_enabled=False)
    assert api.post(f"{API}payments/quote/{order.oid}/").json()["cod"] is None


@pytest.mark.django_db
def test_placing_cod_stores_the_fee_and_razorpay_never_sees_it(api, serum, razorpay_keys, mailoutbox):
    set_config(cod_fee_enabled=True, cod_fee_paise=4900)
    methods = api.get(f"{API}payments/methods/").json()
    assert (methods["cod"], methods["cod_fee_paise"]) == (True, 4900)

    # Online: the Razorpay amount is the online total, without the fee.
    online_order = draft(api, serum, cart_id="online-cart")
    api.post(f"{API}payments/quote/{online_order.oid}/")
    online_order.refresh_from_db()
    response, call = start(api, online_order)
    assert response.status_code == 200
    assert call.call_args.kwargs["json"]["amount"] == 79900 + 7900

    # COD: the shown total is accepted, stored with the fee, and the fee appears in the email.
    order = draft(api, serum, cart_id="cod-cart", email="b@example.com", mobile="9000000001")
    shown = api.post(f"{API}payments/quote/{order.oid}/").json()["cod"]["total_paise"]
    placed = api.post(f"{API}payments/cod/{order.oid}/", {"expected_total_paise": shown}, format="json")
    assert placed.status_code == 200
    assert (placed.json()["total_paise"], placed.json()["cod_fee_paise"]) == (79900 + 7900 + 4900, 4900)
    order.refresh_from_db()
    assert (order.payment_status, order.cod_fee_paise, order.total_paise) == ("pending", 4900, 92700)
    assert order.initial_total_paise - order.saved_paise == order.total_paise
    assert order.total == Decimal("927.00")
    assert_mirrors(order)

    # A Razorpay order is never created for a COD order.
    refused = api.post(f"{API}payments/razorpay/start/{order.oid}/")
    assert refused.status_code == 400

    run_due_jobs()
    mail = next(m for m in mailoutbox if "We have your order" in m.subject and m.to == ["b@example.com"])
    assert "Cash on Delivery fee: ₹49" in mail.body and "₹927" in mail.body


@pytest.mark.django_db
def test_cod_is_refused_when_the_total_is_not_the_one_the_customer_saw(api, serum):
    order = draft(api, serum)
    shown = api.post(f"{API}payments/quote/{order.oid}/").json()["cod"]["total_paise"]
    assert shown == 87800  # fee off

    set_config(cod_fee_enabled=True, cod_fee_paise=4900)  # the owner switches the fee on meanwhile
    response = api.post(f"{API}payments/cod/{order.oid}/", {"expected_total_paise": shown}, format="json")
    assert response.status_code == 409
    assert response.json()["cod"]["total_paise"] == 87800 + 4900
    order.refresh_from_db()
    assert (order.payment_status, order.cod_fee_paise, order.total_paise) == ("processing", 0, 87800)

    # A client-sent total is never used as money, and a float is refused.
    assert api.post(f"{API}payments/cod/{order.oid}/", {"expected_total_paise": 927.0}, format="json").status_code == 400
    ok = api.post(f"{API}payments/cod/{order.oid}/", {"expected_total_paise": 92700, "total_paise": 1}, format="json")
    assert ok.status_code == 200
    order.refresh_from_db()
    assert order.total_paise == 92700


@pytest.mark.django_db
def test_a_placed_order_never_changes_when_the_settings_change(api, serum):
    set_config(cod_fee_enabled=True, cod_fee_paise=4900)
    order = draft(api, serum)
    api.post(f"{API}payments/cod/{order.oid}/")
    order.refresh_from_db()
    before = (order.total_paise, order.cod_fee_paise, order.shipping_amount_paise)
    assert before == (92700, 4900, 7900)

    set_config(cod_fee_paise=9900, shipping_flat_paise=12000, shipping_enabled=False)
    body = api.post(f"{API}payments/quote/{order.oid}/").json()
    assert body["draft"] is False and body["total_paise"] == 92700
    api.post(f"{API}payments/cod/{order.oid}/")  # pressing again changes nothing
    order.refresh_from_db()
    assert (order.total_paise, order.cod_fee_paise, order.shipping_amount_paise) == before
    _items, requoted, _customer = quote_order(order, payment_method="COD")
    assert requoted.total_paise != order.total_paise  # today's price differs; the order kept its own


@pytest.mark.django_db
def test_cod_switched_off_by_the_owner_is_neither_offered_nor_accepted(api, serum):
    set_config(cod_enabled=False, cod_fee_enabled=True, cod_fee_paise=4900)
    methods = api.get(f"{API}payments/methods/").json()
    assert (methods["cod"], methods["cod_fee_paise"]) == (False, 0)
    order = draft(api, serum)
    assert api.post(f"{API}payments/cod/{order.oid}/").status_code == 403
    order.refresh_from_db()
    assert order.payment_status == "processing"


# --------------------------------------------------------------------------- owner settings

@pytest.mark.django_db
def test_owner_store_settings_are_staff_only_validated_and_audited(api, auth, staff, customer, config_settings):
    url = f"{API}owner/settings/"
    assert api.get(url).status_code == 401
    assert auth(customer).patch(url, {"cod_fee": "49"}, format="json").status_code == 403

    owner = auth(staff)
    current = owner.get(url).json()
    assert (current["shipping_flat_paise"], current["cod_fee_enabled"], current["cod_enabled"]) == (7900, False, True)

    assert owner.patch(url, {"cod_fee": 49.0}, format="json").status_code == 400        # never a float
    assert owner.patch(url, {"cod_fee_enabled": True}, format="json").json()["message"].startswith(
        "Enter the Cash on Delivery fee")                                               # on, but no amount
    assert owner.patch(url, {"shipping_flat": "0"}, format="json").status_code == 400  # shipping on at Rs 0
    assert owner.patch(url, {"cod_fee": "-5"}, format="json").status_code == 400

    saved = owner.patch(url, {"cod_fee_enabled": True, "cod_fee": "49", "free_shipping_threshold": "1499.50",
                              "maker_name": "Ayura"}, format="json")
    assert saved.status_code == 200
    body = saved.json()
    assert (body["cod_fee_enabled"], body["cod_fee_paise"], body["free_shipping_threshold_paise"], body["maker_name"]) == \
        (True, 4900, 149950, "Ayura")
    row = AuditLog.objects.get(action="settings.updated")
    assert row.actor_id == staff.pk
    assert (row.before["cod_fee_paise"], row.after["cod_fee_paise"]) == (0, 4900)

    # Switching shipping off needs no amount, and the public settings follow.
    assert owner.patch(url, {"shipping_enabled": False}, format="json").status_code == 200
    public = api.get(f"{API}addon/").json()
    assert (public["shipping_enabled"], public["cod_fee_paise"]) == (False, 4900)
    assert CartOrder.objects.count() == 0
