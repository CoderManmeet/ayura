"""
Ayura phase B: the personal-care catalogue.

Categories inside categories, sizes with a net quantity, owner screens for sizes and stock,
the benefit line and care information, the claim-word warning, and store-wide product
information. Fails before phase B (the owner endpoints, fields and `catalog.claims` do not
exist) and passes after it.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from catalog.claims import claim_warnings
from catalog.models import PriceHistory, ProductVariant
from core.models import AuditLog
from inventory.models import Batch, MovementKind, StockMovement
from inventory.services import available_qty, on_hand_qty
from store.models import Category, Product

API = "/api/v1/"


@pytest.fixture
def fresh_product(vendor, config_settings):
    """A product as the dashboard creates it: one placeholder size 'Default', no opening stock."""
    return Product.objects.create(title="Face Serum", price=Decimal("449.00"), old_price=Decimal("499.00"),
                                  stock_qty=0, status="published", vendor=vendor)


def add_size(client, product, **values):
    payload = {"label": "30 ml", "price": "449", "mrp": "499", "net_quantity": "30", "net_quantity_unit": "ml"}
    payload.update(values)
    return client.post(f"{API}owner/products/{product.pid}/variants/", payload, format="json")


# ------------------------------------------------------------------ categories

@pytest.mark.django_db
def test_categories_nest_and_the_shop_filter_includes_sub_categories(api, auth, staff, vendor, config_settings):
    owner = auth(staff)
    skincare = owner.post(f"{API}owner/categories/", {"title": "Skincare"}, format="json").json()
    face = owner.post(f"{API}owner/categories/", {"title": "Face", "parent": skincare["id"]}, format="json").json()
    serums = owner.post(f"{API}owner/categories/", {"title": "Serums", "parent": face["id"]}, format="json").json()
    hair = owner.post(f"{API}owner/categories/", {"title": "Haircare"}, format="json").json()
    assert (skincare["slug"], face["slug"], serums["parent"]) == ("skincare", "face", face["id"])

    serum = Product.objects.create(title="Face Serum", price=Decimal("449.00"), status="published", vendor=vendor,
                                   category_id=serums["id"])
    oil = Product.objects.create(title="Hair Oil", price=Decimal("299.00"), status="published", vendor=vendor,
                                 category_id=hair["id"])

    def titles(slug):
        return sorted(p["title"] for p in api.get(f"{API}products/", {"category": slug}).json())

    assert titles("skincare") == ["Face Serum"]          # two levels down still counts
    assert titles("face") == ["Face Serum"]
    assert titles("haircare") == ["Hair Oil"]
    assert titles("no-such-category") == []              # unknown shows nothing, not everything
    assert sorted(p["title"] for p in api.get(f"{API}products/").json()) == ["Face Serum", "Hair Oil"]

    public = {c["slug"]: c for c in api.get(f"{API}category/").json()}
    assert public["serums"]["parent"] == face["id"] and public["skincare"]["parent"] is None

    # A switched-off category is gone from the shop and its filter shows nothing.
    owner.patch(f"{API}owner/categories/{face['id']}/", {"active": False}, format="json")
    assert "face" not in {c["slug"] for c in api.get(f"{API}category/").json()}
    assert titles("face") == []
    assert serum.pk and oil.pk
    assert AuditLog.objects.filter(action="category.created").count() == 4
    assert AuditLog.objects.filter(action="category.updated", actor=staff).exists()


@pytest.mark.django_db
def test_a_category_cannot_be_put_inside_itself(auth, staff):
    owner = auth(staff)
    top = owner.post(f"{API}owner/categories/", {"title": "Skincare"}, format="json").json()
    child = owner.post(f"{API}owner/categories/", {"title": "Face", "parent": top["id"]}, format="json").json()
    assert owner.patch(f"{API}owner/categories/{top['id']}/", {"parent": top["id"]}, format="json").status_code == 400
    response = owner.patch(f"{API}owner/categories/{top['id']}/", {"parent": child["id"]}, format="json")
    assert response.status_code == 400 and "inside itself" in response.json()["message"]
    assert Category.objects.get(pk=top["id"]).parent_id is None


# ------------------------------------------------------------------ sizes

@pytest.mark.django_db
def test_owner_adds_sizes_and_the_first_one_replaces_the_placeholder(api, auth, staff, fresh_product):
    owner = auth(staff)
    assert list(fresh_product.variants.values_list("name", flat=True)) == ["Default"]

    response = add_size(owner, fresh_product)
    assert response.status_code == 201
    response = add_size(owner, fresh_product, label="100 ml", price="999.50", mrp="1099", net_quantity="100")
    assert response.status_code == 201

    variants = list(fresh_product.variants.order_by("price_paise"))
    assert [(v.name, v.price_paise, v.mrp_paise, v.net_quantity_label, v.is_default) for v in variants] == [
        ("30 ml", 44900, 49900, "30 ml", True), ("100 ml", 99950, 109900, "100 ml", False)]
    assert variants[0].options == {"Size": "30 ml"}

    # Every new price was recorded with the staff user as the actor.
    assert PriceHistory.objects.filter(variant=variants[1], actor=staff).exists()
    assert AuditLog.objects.filter(action="variant.created", actor=staff).count() == 1
    assert AuditLog.objects.filter(action="variant.updated", actor=staff).count() == 1  # the placeholder

    # The shopper sees both sizes with their net quantity.
    body = api.get(f"{API}products/{fresh_product.slug}/").json()
    assert [(v["name"], v["net_quantity"], v["net_quantity_unit"]) for v in body["variants"]] == [
        ("30 ml", 30, "ml"), ("100 ml", 100, "ml")]


@pytest.mark.django_db
def test_size_values_are_checked_and_money_never_arrives_as_a_float(auth, staff, fresh_product):
    owner = auth(staff)
    assert add_size(owner, fresh_product, price=449.5).status_code == 400              # a JSON number
    assert add_size(owner, fresh_product, price="abc").status_code == 400
    assert add_size(owner, fresh_product, price="600", mrp="500").json()["message"] == \
        "The price cannot be higher than the MRP."
    assert add_size(owner, fresh_product, net_quantity_unit="litre").status_code == 400
    assert add_size(owner, fresh_product, label="").status_code == 400
    # Nothing was written by any refused request.
    assert list(fresh_product.variants.values_list("name", flat=True)) == ["Default"]


@pytest.mark.django_db
def test_a_size_gets_an_sku_or_keeps_the_one_the_owner_typed(auth, staff, fresh_product):
    owner = auth(staff)
    add_size(owner, fresh_product)                                    # takes over the placeholder's SKU
    add_size(owner, fresh_product, label="100 ml", price="999", mrp="1099", net_quantity="100")
    add_size(owner, fresh_product, label="50 ml", price="649", mrp="699", net_quantity="50", sku="AY-SERUM-50")
    skus = dict(fresh_product.variants.values_list("name", "sku"))
    assert skus["30 ml"] == fresh_product.sku
    assert skus["100 ml"] == f"{fresh_product.sku}-100-ML"
    assert skus["50 ml"] == "AY-SERUM-50"
    # An SKU already in use is refused with the reason, and nothing changes.
    large = fresh_product.variants.get(name="100 ml")
    refused = owner.patch(f"{API}owner/variants/{large.pk}/", {"sku": "AY-SERUM-50"}, format="json")
    assert refused.status_code == 400 and "already uses that SKU" in refused.json()["message"]
    large.refresh_from_db()
    assert large.sku == f"{fresh_product.sku}-100-ML"


@pytest.mark.django_db
def test_the_main_size_cannot_be_switched_off_until_another_is_main(auth, staff, fresh_product):
    owner = auth(staff)
    add_size(owner, fresh_product)
    add_size(owner, fresh_product, label="100 ml", price="999", mrp="1099", net_quantity="100")
    small = fresh_product.variants.get(name="30 ml")
    large = fresh_product.variants.get(name="100 ml")

    refused = owner.patch(f"{API}owner/variants/{small.pk}/", {"active": False}, format="json")
    assert refused.status_code == 400
    assert owner.patch(f"{API}owner/variants/{large.pk}/", {"make_default": True}, format="json").status_code == 200
    assert owner.patch(f"{API}owner/variants/{small.pk}/", {"active": False}, format="json").status_code == 200

    small.refresh_from_db(); large.refresh_from_db(); fresh_product.refresh_from_db()
    assert (small.active, small.is_default, large.is_default) == (False, False, True)
    # The legacy product price follows the new main size (ROADMAP A5).
    assert fresh_product.price == Decimal("999.00")


@pytest.mark.django_db
def test_changing_a_price_writes_history_and_an_audit_row(auth, staff, fresh_product):
    owner = auth(staff)
    add_size(owner, fresh_product)
    variant = fresh_product.variants.get(name="30 ml")
    rows_before = PriceHistory.objects.filter(variant=variant).count()
    response = owner.patch(f"{API}owner/variants/{variant.pk}/", {"price": "429"}, format="json")
    assert response.status_code == 200
    variant.refresh_from_db()
    assert variant.price_paise == 42900
    assert PriceHistory.objects.filter(variant=variant).count() == rows_before + 1
    row = AuditLog.objects.filter(action="variant.updated", object_id=str(variant.pk)).latest("id")
    assert (row.before["price_paise"], row.after["price_paise"], row.actor_id) == (44900, 42900, staff.pk)


# ------------------------------------------------------------------ stock

@pytest.mark.django_db
def test_receiving_stock_books_a_batch_into_the_ledger(auth, staff, fresh_product):
    owner = auth(staff)
    add_size(owner, fresh_product)
    variant = fresh_product.variants.get(name="30 ml")
    today = timezone.localdate()

    response = owner.post(f"{API}owner/variants/{variant.pk}/stock/", {
        "quantity": "12", "manufactured_on": today.isoformat(),
        "best_before": (today + timedelta(days=180)).isoformat(), "cost_per_unit": "85.50",
    }, format="json")
    assert response.status_code == 201
    assert on_hand_qty(variant) == 12 and available_qty(variant) == 12

    batch = Batch.objects.get(variant=variant)
    assert (batch.quantity_produced, batch.cost_per_unit_paise, batch.best_before) == (12, 8550, today + timedelta(days=180))
    movement = StockMovement.objects.get(batch=batch)
    assert (movement.kind, movement.quantity, movement.actor_id) == (MovementKind.PRODUCTION_IN, 12, staff.pk)

    sizes = {v["name"]: v for v in response.json()["variants"]}
    assert sizes["30 ml"]["on_hand"] == 12 and sizes["30 ml"]["batches"][0]["remaining"] == 12

    # Undated stock is allowed (ROADMAP Y12); bad values are refused and write nothing.
    assert owner.post(f"{API}owner/variants/{variant.pk}/stock/", {"quantity": "3"}, format="json").status_code == 201
    assert on_hand_qty(variant) == 15
    for bad in ({"quantity": "0"}, {"quantity": "2", "best_before": today.isoformat()},
                {"quantity": "2", "manufactured_on": (today + timedelta(days=1)).isoformat()},
                {"quantity": "2", "cost_per_unit": 12.5}):
        assert owner.post(f"{API}owner/variants/{variant.pk}/stock/", bad, format="json").status_code == 400
    assert on_hand_qty(variant) == 15 and Batch.objects.filter(variant=variant).count() == 2


@pytest.mark.django_db
def test_a_batch_use_by_date_can_be_added_later_and_is_audited(auth, staff, fresh_product):
    owner = auth(staff)
    add_size(owner, fresh_product)
    variant = fresh_product.variants.get(name="30 ml")
    owner.post(f"{API}owner/variants/{variant.pk}/stock/", {"quantity": "5"}, format="json")
    batch = Batch.objects.get(variant=variant)
    assert batch.best_before is None

    use_by = (timezone.localdate() + timedelta(days=90)).isoformat()
    response = owner.patch(f"{API}owner/batches/{batch.pk}/", {"best_before": use_by}, format="json")
    assert response.status_code == 200
    batch.refresh_from_db()
    assert batch.best_before.isoformat() == use_by
    row = AuditLog.objects.get(action="batch.updated", object_id=str(batch.pk))
    assert (row.before["best_before"], row.after["best_before"], row.actor_id) == (None, use_by, staff.pk)
    assert on_hand_qty(variant) == 5  # editing a batch never moves stock


# ------------------------------------------------------------------ product details and warnings

@pytest.mark.django_db
def test_details_save_and_risky_words_are_warned_about_not_blocked(api, auth, staff, fresh_product):
    owner = auth(staff)
    response = owner.patch(f"{API}owner/products/{fresh_product.pid}/", {
        "benefit_line": "Cures acne overnight",
        "ingredients": "Aqua, glycerin",
        "how_to_use": "Apply two drops to clean skin.",
        "cautions": "For external use only. Patch test before first use.",
    }, format="json")
    assert response.status_code == 200
    assert response.json()["warnings"] == ["cures", "acne"]
    fresh_product.refresh_from_db()
    assert fresh_product.benefit_line == "Cures acne overnight"  # saved anyway: a warning, not a block
    assert AuditLog.objects.filter(action="product.details_updated", actor=staff).exists()

    too_long = owner.patch(f"{API}owner/products/{fresh_product.pid}/", {"benefit_line": "x" * 121}, format="json")
    assert too_long.status_code == 400

    body = api.get(f"{API}products/{fresh_product.slug}/").json()
    assert (body["ingredients"], body["how_to_use"]) == ("Aqua, glycerin", "Apply two drops to clean skin.")
    assert body["cautions"].startswith("For external use only")


def test_claim_warnings_match_whole_words_only():
    assert claim_warnings("For oily skin. Helps cleanse.") == []
    assert claim_warnings("Treats dandruff", "100% natural") == ["treats", "100%", "natural", "dandruff"]
    assert claim_warnings("A curious scent", "treaty") == []


@pytest.mark.django_db
def test_store_wide_product_information_is_public(api, config_settings):
    config_settings.maker_name = "Ayura"
    config_settings.country_of_origin = "India"
    config_settings.save()
    body = api.get(f"{API}addon/").json()
    assert (body["maker_name"], body["country_of_origin"], body["maker_address"]) == ("Ayura", "India", "")


# ------------------------------------------------------------------ access

@pytest.mark.django_db
def test_owner_catalogue_endpoints_are_staff_only(api, auth, customer, fresh_product):
    variant = fresh_product.variants.get()
    batch_free_urls = [
        ("get", f"{API}owner/categories/"), ("post", f"{API}owner/categories/"),
        ("get", f"{API}owner/products/{fresh_product.pid}/"), ("patch", f"{API}owner/products/{fresh_product.pid}/"),
        ("post", f"{API}owner/products/{fresh_product.pid}/variants/"), ("patch", f"{API}owner/variants/{variant.pk}/"),
        ("post", f"{API}owner/variants/{variant.pk}/stock/"),
    ]
    for method, url in batch_free_urls:
        assert getattr(api, method)(url, {}, format="json").status_code == 401, url
        assert getattr(auth(customer), method)(url, {}, format="json").status_code == 403, url
    assert ProductVariant.objects.filter(product=fresh_product).count() == 1
