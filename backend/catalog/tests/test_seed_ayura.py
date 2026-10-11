"""
Phase A (Ayura): the placeholder catalogue command `seed_ayura`.

Fails before Phase A (the command does not exist: CommandError "Unknown command") and passes
after it.
"""

import re

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from catalog.models import ProductVariant
from inventory.models import Batch
from inventory.services import available_qty
from store.models import Category, Coupon, Product

API = "/api/v1/"


@pytest.mark.django_db
def test_seed_ayura_refuses_to_run_outside_debug(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command("seed_ayura")
    assert Product.objects.count() == 0


@pytest.mark.django_db
def test_seed_ayura_creates_the_placeholder_catalogue_and_is_idempotent(settings, api):
    settings.DEBUG = True
    call_command("seed_ayura")
    call_command("seed_ayura")

    assert sorted(Category.objects.values_list("slug", flat=True)) == ["bodycare", "face", "haircare", "lips", "skincare"]
    # Phase B: Face and Lips sit inside Skincare.
    assert {c.slug: (c.parent.slug if c.parent else None) for c in Category.objects.all()} == {
        "skincare": None, "face": "skincare", "lips": "skincare", "haircare": None, "bodycare": None}
    assert Product.objects.count() == 8
    assert ProductVariant.objects.count() == 15
    assert Batch.objects.count() == 15
    assert Coupon.objects.filter(code="WELCOME10").count() == 1

    for product in Product.objects.all():
        assert product.category is not None
        variants = list(product.variants.order_by("price_paise"))
        assert variants[0].is_default and all(not v.is_default for v in variants[1:])
        assert all(v.options == {"Size": v.name} for v in variants)
        assert all(available_qty(v) == 20 for v in variants)
        assert all(v.mrp_paise > v.price_paise for v in variants)
        # Phase B: every size declares its net quantity, matching its label.
        assert all(v.net_quantity_label == v.name for v in variants)
        assert product.benefit_line and product.how_to_use and product.cautions

    # Opening batches carry a best-before date, so FEFO has something to order by.
    assert not Batch.objects.filter(best_before__isnull=True).exists()

    body = api.get(f"{API}products/face-serum/").json()
    assert [v["name"] for v in body["variants"]] == ["30 ml", "50 ml"]
    assert body["available_qty"] == 40


@pytest.mark.django_db
def test_seeded_copy_makes_no_banned_claim(settings):
    from catalog.management.commands.seed_ayura import BANNED_CLAIM_WORDS

    settings.DEBUG = True
    call_command("seed_ayura", "--no-pictures")

    texts = []
    for product in Product.objects.all():
        texts += [product.title, product.description or "", product.benefit_line, product.how_to_use,
                  product.cautions, product.ingredients]
    texts += list(ProductVariant.objects.values_list("name", flat=True))
    texts += list(Category.objects.values_list("title", flat=True))
    blob = " ".join(texts).lower()

    found = [word for word in BANNED_CLAIM_WORDS if re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", blob)]
    assert found == []
    # Every seeded description says it is placeholder copy.
    assert all("[PLACEHOLDER COPY]" in (p.description or "") for p in Product.objects.all())


@pytest.mark.django_db
def test_seed_ayura_draws_a_placeholder_picture_unless_told_not_to(settings):
    settings.DEBUG = True
    call_command("seed_ayura")
    product = Product.objects.get(slug="face-serum")
    assert product.image and product.image.name != "product.jpg"
    with product.image.open("rb") as handle:
        assert handle.read(3) == b"\xff\xd8\xff"  # a JPEG


@pytest.mark.django_db
def test_seed_ayura_without_pictures_leaves_the_default_image(settings):
    settings.DEBUG = True
    call_command("seed_ayura", "--no-pictures")
    assert Product.objects.get(slug="face-serum").image.name == "product.jpg"
