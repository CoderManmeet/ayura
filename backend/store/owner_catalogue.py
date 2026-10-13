"""
Owner (staff) endpoints for running the personal-care catalogue (Phase B, Ayura).

    GET   owner/categories/                 every category, with its parent
    POST  owner/categories/                 {title, parent, active}
    PATCH owner/categories/<id>/            {title, parent, active}
    GET   owner/products/<pid>/             details, sizes, and each size's batches
    PATCH owner/products/<pid>/             {category, benefit_line, ingredients, how_to_use, cautions}
    POST  owner/products/<pid>/variants/    add a size
    PATCH owner/variants/<id>/              change a size (price, MRP, net quantity, active, default)
    POST  owner/variants/<id>/stock/        receive stock: a new batch, booked into the ledger
    PATCH owner/batches/<id>/               {best_before, production_notes}

Rules kept here:
  * Money arrives as rupees in TEXT ("449" or "449.50") and is stored as integer paise through
    core.money. A JSON number is refused, so no float ever touches a price (rule 6).
  * Stock only ever changes through inventory.services.receive_production (the ledger).
  * Every change is audited with the signed-in staff user (rule 9); price changes also write
    PriceHistory through the existing catalogue signals.
  * Product copy is checked against catalog.claims and any words found are returned as
    warnings. Saving is never blocked by them (ROADMAP-AYURA Z4).

Staff only: core.permissions.IsStaffOwner.
"""

import logging
from datetime import date

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.text import slugify
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.claims import CLAIM_WARNING_WORDS, claim_warnings
from catalog.models import NET_QUANTITY_UNITS, ProductVariant
from core.audit import record, snapshot
from core.money import MoneyError, to_paise
from core.permissions import IsStaffOwner
from inventory.models import Batch
from inventory.services import available_qty_map, batch_on_hand, on_hand_qty, receive_production
from store.models import Category, Product

logger = logging.getLogger(__name__)

BENEFIT_LINE_MAX = 120
VARIANT_AUDIT_FIELDS = ("name", "options", "net_quantity", "net_quantity_unit", "price_paise", "mrp_paise",
                        "weight_grams", "is_default", "active", "is_sample", "is_kit")
DETAIL_FIELDS = ("category", "benefit_line", "ingredients", "how_to_use", "cautions")
UNIT_VALUES = {value for value, _label in NET_QUANTITY_UNITS}


class OwnerInputError(Exception):
    """A value the owner typed cannot be used. The message is shown to them as it is."""


def _error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"message": message}, status=code)


# --------------------------------------------------------------------------- parsing helpers

def _text(data, name, max_length=None, required=False):
    value = data.get(name)
    if value is None:
        if required:
            raise OwnerInputError(f"{name.replace('_', ' ').capitalize()} is required.")
        return None
    value = str(value).strip()
    if required and not value:
        raise OwnerInputError(f"{name.replace('_', ' ').capitalize()} is required.")
    if max_length is not None and len(value) > max_length:
        raise OwnerInputError(f"{name.replace('_', ' ').capitalize()} can be at most {max_length} characters.")
    return value


def _rupees_to_paise(value, label, required=False):
    """'449' or '449.50' -> paise. Blank -> None (or an error when required). Never a float."""
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise OwnerInputError(f"{label} is required.")
        return None
    if isinstance(value, float):
        raise OwnerInputError(f"{label}: send the amount as text, for example \"449\" or \"449.50\".")
    try:
        paise = to_paise(value)
    except MoneyError:
        raise OwnerInputError(f"{label} must be an amount in rupees, for example 449 or 449.50.")
    if paise < 0:
        raise OwnerInputError(f"{label} cannot be negative.")
    return paise


def _positive_int(value, label, required=False, allow_zero=False):
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise OwnerInputError(f"{label} is required.")
        return None
    if isinstance(value, bool) or isinstance(value, float):
        raise OwnerInputError(f"{label} must be a whole number.")
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        raise OwnerInputError(f"{label} must be a whole number.")
    if number < 0 or (number == 0 and not allow_zero):
        raise OwnerInputError(f"{label} must be more than 0.")
    return number


def _date(value, label, required=False):
    if value in (None, ""):
        if required:
            raise OwnerInputError(f"{label} is required.")
        return None
    if isinstance(value, date):
        return value
    parsed = parse_date(str(value).strip())
    if parsed is None:
        raise OwnerInputError(f"{label} must be a date (YYYY-MM-DD).")
    return parsed


def _bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


# --------------------------------------------------------------------------- payloads

def _category_payload(category):
    return {
        "id": category.pk,
        "title": category.title,
        "slug": category.slug,
        "active": category.active,
        "parent": category.parent_id,
        "product_count": category.product_count(),
    }


def _batch_payload(batch, today):
    return {
        "id": batch.pk,
        "batch_code": batch.batch_code,
        "manufactured_on": batch.manufactured_on.isoformat() if batch.manufactured_on else None,
        "best_before": batch.best_before.isoformat() if batch.best_before else None,
        "expired": bool(batch.best_before and batch.best_before < today),
        "quantity_produced": batch.quantity_produced,
        "remaining": batch_on_hand(batch),
        "cost_per_unit_paise": int(batch.cost_per_unit_paise),
        "production_notes": batch.production_notes,
    }


def _variant_payload(variant, available, today):
    return {
        "id": variant.pk,
        "sku": variant.sku,
        "name": variant.name,
        "options": variant.options,
        "net_quantity": variant.net_quantity,
        "net_quantity_unit": variant.net_quantity_unit,
        # Phase D: a sample is given away with orders and never appears in the shop.
        "is_sample": variant.is_sample,
        # Phase E: a kit is sold as one item and draws its stock from its components.
        "is_kit": variant.is_kit,
        "price_paise": int(variant.price_paise),
        "mrp_paise": int(variant.mrp_paise) if variant.mrp_paise is not None else None,
        "weight_grams": variant.weight_grams,
        "is_default": variant.is_default,
        "active": variant.active,
        "on_hand": on_hand_qty(variant),
        "available": available.get(variant.pk, 0),
        "batches": [_batch_payload(batch, today) for batch in variant.batches.order_by("best_before", "manufactured_on", "id")],
    }


def _product_payload(product):
    variants = list(product.variants.order_by("-is_default", "price_paise", "id"))
    available = available_qty_map(variants)
    today = timezone.localdate()
    return {
        "id": product.pk,
        "pid": product.pid,
        "title": product.title,
        "slug": product.slug,
        "status": product.status,
        "image": product.image.url if product.image else None,
        "category": product.category_id,
        "benefit_line": product.benefit_line,
        "ingredients": product.ingredients,
        "how_to_use": product.how_to_use,
        "cautions": product.cautions,
        "warnings": claim_warnings(product.benefit_line, product.description, product.how_to_use, product.cautions),
        "variants": [_variant_payload(variant, available, today) for variant in variants],
        "claim_words": list(CLAIM_WARNING_WORDS),
        "benefit_line_max": BENEFIT_LINE_MAX,
    }


# --------------------------------------------------------------------------- categories

def _unique_category_slug(title, exclude_pk=None):
    base = slugify(title)[:45] or "category"
    candidate, n = base, 1
    while Category.objects.filter(slug=candidate).exclude(pk=exclude_pk).exists():
        n += 1
        candidate = f"{base}-{n}"
    return candidate


def _parent_from(data, category=None):
    """The parent named in the request ('' or null for none). Refuses a loop."""
    if "parent" not in data:
        return category.parent if category is not None else None
    raw = data.get("parent")
    if raw in (None, "", "null", 0, "0"):
        return None
    parent = Category.objects.filter(pk=_positive_int(raw, "Parent category")).first()
    if parent is None:
        raise OwnerInputError("That parent category does not exist.")
    if category is not None and category.would_create_cycle(parent):
        raise OwnerInputError("A category cannot be placed inside itself or inside one of its own sub-categories.")
    return parent


class OwnerCategoryListView(APIView):
    permission_classes = (IsStaffOwner,)

    def get(self, request, *args, **kwargs):
        rows = Category.objects.select_related("parent").order_by("title")
        return Response([_category_payload(category) for category in rows])

    def post(self, request, *args, **kwargs):
        try:
            title = _text(request.data, "title", max_length=100, required=True)
            parent = _parent_from(request.data)
        except OwnerInputError as exc:
            return _error(str(exc))
        active = _bool(request.data.get("active", True))
        with transaction.atomic():
            category = Category.objects.create(title=title, parent=parent, active=active,
                                               slug=_unique_category_slug(title))
            record("category.created", category, before=None,
                   after=snapshot(category, ("title", "slug", "parent", "active")), actor=request.user)
        return Response(_category_payload(category), status=status.HTTP_201_CREATED)


class OwnerCategoryDetailView(APIView):
    permission_classes = (IsStaffOwner,)

    def patch(self, request, category_id, *args, **kwargs):
        category = get_object_or_404(Category, pk=category_id)
        fields = ("title", "slug", "parent", "active")
        before = snapshot(category, fields)
        try:
            if "title" in request.data:
                category.title = _text(request.data, "title", max_length=100, required=True)
            category.parent = _parent_from(request.data, category)
        except OwnerInputError as exc:
            return _error(str(exc))
        if "active" in request.data:
            category.active = _bool(request.data.get("active"))
        with transaction.atomic():
            category.save()
            after = snapshot(category, fields)
            if after != before:
                record("category.updated", category, before=before, after=after, actor=request.user)
        return Response(_category_payload(category))


# --------------------------------------------------------------------------- products

class OwnerProductView(APIView):
    permission_classes = (IsStaffOwner,)

    def get(self, request, pid, *args, **kwargs):
        product = get_object_or_404(Product, pid=pid)
        return Response(_product_payload(product))

    def patch(self, request, pid, *args, **kwargs):
        product = get_object_or_404(Product, pid=pid)
        before = snapshot(product, DETAIL_FIELDS)
        try:
            for name in ("benefit_line", "ingredients", "how_to_use", "cautions"):
                if name in request.data:
                    value = _text(request.data, name, max_length=BENEFIT_LINE_MAX if name == "benefit_line" else 5000)
                    setattr(product, name, value or "")
            if "category" in request.data:
                raw = request.data.get("category")
                if raw in (None, "", "null"):
                    product.category = None
                else:
                    category = Category.objects.filter(pk=_positive_int(raw, "Category")).first()
                    if category is None:
                        raise OwnerInputError("That category does not exist.")
                    product.category = category
        except OwnerInputError as exc:
            return _error(str(exc))

        with transaction.atomic():
            product.save(update_fields=list(DETAIL_FIELDS))
            after = snapshot(product, DETAIL_FIELDS)
            if after != before:
                record("product.details_updated", product, before=before, after=after, actor=request.user)
        return Response(_product_payload(product))


# --------------------------------------------------------------------------- sizes (variants)

def _unique_variant_sku(product, label, exclude_pk=None):
    base = f"{product.sku}-{slugify(label).upper()}".strip("-")[:56] or f"{product.sku}-SIZE"
    candidate, n = base, 1
    while ProductVariant.objects.filter(sku=candidate).exclude(pk=exclude_pk).exists():
        n += 1
        candidate = f"{base}-{n}"
    return candidate


def _apply_variant_fields(variant, data, creating):
    """Copy the owner's values onto `variant`. Raises OwnerInputError on a bad value."""
    if creating or "label" in data:
        label = _text(data, "label", max_length=100, required=True)
        variant.name = label
        options = dict(variant.options or {})
        options["Size"] = label
        variant.options = options
    if creating or "price" in data:
        variant.price_paise = _rupees_to_paise(data.get("price"), "Price", required=True)
    if creating or "mrp" in data:
        variant.mrp_paise = _rupees_to_paise(data.get("mrp"), "MRP")
    if variant.mrp_paise is not None and variant.price_paise > variant.mrp_paise:
        raise OwnerInputError("The price cannot be higher than the MRP.")
    if creating or "net_quantity" in data or "net_quantity_unit" in data:
        quantity = _positive_int(data.get("net_quantity"), "Net quantity")
        unit = str(data.get("net_quantity_unit") or "").strip().lower()
        if quantity is None:
            unit = ""
        elif unit not in UNIT_VALUES:
            raise OwnerInputError("Choose the net quantity unit: g or ml.")
        variant.net_quantity = quantity
        variant.net_quantity_unit = unit
    if creating or "weight_grams" in data:
        variant.weight_grams = _positive_int(data.get("weight_grams"), "Shipping weight")
    if creating or "is_sample" in data:
        variant.is_sample = _bool(data.get("is_sample"))
    if creating or "is_kit" in data:
        variant.is_kit = _bool(data.get("is_kit"))
    if variant.is_sample and variant.is_default:
        raise OwnerInputError("A sample cannot be the product's main size.")
    if variant.is_sample and variant.is_kit:
        raise OwnerInputError("A size is either a kit or a sample, not both.")
    if "sku" in data and str(data.get("sku") or "").strip():
        sku = _text(data, "sku", max_length=64)
        if ProductVariant.objects.filter(sku=sku).exclude(pk=variant.pk).exists():
            raise OwnerInputError("Another size already uses that SKU.")
        variant.sku = sku


class OwnerVariantCreateView(APIView):
    """
    Add a size. A product created from the dashboard starts with one placeholder size called
    "Default" (it may hold the opening stock typed when the product was made); the first real
    size takes over that placeholder, so its stock is kept.
    """

    permission_classes = (IsStaffOwner,)

    def post(self, request, pid, *args, **kwargs):
        product = get_object_or_404(Product, pid=pid)
        wants_sample = _bool(request.data.get("is_sample", False))
        # A kit draws its stock from other sizes (Phase E), so like a sample it is never the
        # product's main size and never takes over the placeholder, which may hold the opening
        # stock typed when the product was made.
        wants_kit = _bool(request.data.get("is_kit", False))
        stands_alone = wants_sample or wants_kit
        with transaction.atomic():
            variants = list(ProductVariant.objects.select_for_update().filter(product=product))
            if wants_sample and not any(not v.is_sample for v in variants):
                return _error("Add a size people can buy before adding a sample of it.")
            placeholder = None
            if not stands_alone and len(variants) == 1 and variants[0].name == "Default" and not variants[0].options:
                placeholder = variants[0]
            # A kit is the main size only when it is the product's only one (a gift-set product);
            # a sample never is, and the rule above means a sample is never the first size.
            variant = placeholder or ProductVariant(
                product=product, is_default=not variants and not wants_sample, active=True)
            before = snapshot(placeholder, VARIANT_AUDIT_FIELDS) if placeholder else None
            try:
                _apply_variant_fields(variant, request.data, creating=True)
            except OwnerInputError as exc:
                transaction.set_rollback(True)
                return _error(str(exc))
            if placeholder is None and not variant.sku:
                variant.sku = _unique_variant_sku(product, variant.name)
            try:
                variant.save()
            except IntegrityError:
                transaction.set_rollback(True)
                return _error("That size could not be saved. Its SKU may already be in use.")
            record("variant.created" if placeholder is None else "variant.updated", variant, before=before,
                   after=snapshot(variant, VARIANT_AUDIT_FIELDS),
                   reason="first size replaces the placeholder" if placeholder else "", actor=request.user)
        product.refresh_from_db()
        return Response(_product_payload(product), status=status.HTTP_201_CREATED)


class OwnerVariantDetailView(APIView):
    """Change a size. Sizes are switched off (`active: false`), never deleted: orders refer to them."""

    permission_classes = (IsStaffOwner,)

    def patch(self, request, variant_id, *args, **kwargs):
        with transaction.atomic():
            variant = get_object_or_404(ProductVariant.objects.select_for_update(), pk=variant_id)
            before = snapshot(variant, VARIANT_AUDIT_FIELDS)
            try:
                _apply_variant_fields(variant, request.data, creating=False)
                make_default = _bool(request.data.get("make_default", False))
                if make_default and variant.is_sample:
                    raise OwnerInputError("A sample cannot be the product's main size.")
                if "active" in request.data:
                    active = _bool(request.data.get("active"))
                    if not active and variant.is_default and not make_default:
                        raise OwnerInputError("This is the product's main size. Make another size the main one first.")
                    variant.active = active
                if make_default and not variant.active:
                    raise OwnerInputError("Switch this size on before making it the main one.")
            except OwnerInputError as exc:
                transaction.set_rollback(True)
                return _error(str(exc))

            if make_default and not variant.is_default:
                current = ProductVariant.objects.select_for_update().filter(product=variant.product, is_default=True).first()
                if current is not None:
                    current_before = snapshot(current, VARIANT_AUDIT_FIELDS)
                    current.is_default = False
                    current.save(update_fields=["is_default", "updated_at"])
                    record("variant.updated", current, before=current_before,
                           after=snapshot(current, VARIANT_AUDIT_FIELDS), reason="another size made the main one",
                           actor=request.user)
                variant.is_default = True
            variant.save()
            after = snapshot(variant, VARIANT_AUDIT_FIELDS)
            if after != before:
                record("variant.updated", variant, before=before, after=after, actor=request.user)
        product = Product.objects.get(pk=variant.product_id)
        return Response(_product_payload(product))


# --------------------------------------------------------------------------- stock and batches

def _next_batch_code(variant, made_on):
    base = f"{variant.sku}-{made_on:%Y%m%d}"[:60]
    candidate, n = base, 1
    while Batch.objects.filter(batch_code=candidate).exists():
        n += 1
        candidate = f"{base}-{n}"[:64]
    return candidate


class OwnerReceiveStockView(APIView):
    """Receive a made batch of one size: creates the batch and books its quantity into the ledger."""

    permission_classes = (IsStaffOwner,)

    def post(self, request, variant_id, *args, **kwargs):
        variant = get_object_or_404(ProductVariant, pk=variant_id)
        if variant.is_kit:
            # A kit holds no stock of its own (Phase E): booking a batch against it would be a
            # number nothing can ever sell. Make more of its components instead.
            return _error("A kit has no stock of its own. Add stock to the sizes that go inside it.")
        data = request.data
        try:
            quantity = _positive_int(data.get("quantity"), "Quantity", required=True)
            made_on = _date(data.get("manufactured_on"), "Made on") or timezone.localdate()
            best_before = _date(data.get("best_before"), "Use by")
            if best_before is not None and best_before <= made_on:
                raise OwnerInputError("The use-by date must be after the date it was made.")
            if made_on > timezone.localdate():
                raise OwnerInputError("The date it was made cannot be in the future.")
            cost = _rupees_to_paise(data.get("cost_per_unit"), "Cost per unit") or 0
            notes = _text(data, "production_notes", max_length=1000) or ""
            code = _text(data, "batch_code", max_length=64) or ""
            if code and Batch.objects.filter(batch_code=code).exists():
                raise OwnerInputError("A batch with that code already exists.")
        except OwnerInputError as exc:
            return _error(str(exc))

        with transaction.atomic():
            batch = Batch.objects.create(
                batch_code=code or _next_batch_code(variant, made_on), variant=variant,
                manufactured_on=made_on, best_before=best_before, quantity_produced=quantity,
                cost_per_unit_paise=cost, production_notes=notes,
            )
            receive_production(variant, batch, quantity, reason="Stock added in the admin area", actor=request.user)
        product = Product.objects.get(pk=variant.product_id)
        return Response(_product_payload(product), status=status.HTTP_201_CREATED)


class OwnerBatchDetailView(APIView):
    """Correct a batch's use-by date or notes. The quantity is ledger history and never edited."""

    permission_classes = (IsStaffOwner,)

    def patch(self, request, batch_id, *args, **kwargs):
        fields = ("best_before", "production_notes")
        with transaction.atomic():
            batch = get_object_or_404(Batch.objects.select_for_update(), pk=batch_id)
            before = snapshot(batch, fields)
            try:
                if "best_before" in request.data:
                    best_before = _date(request.data.get("best_before"), "Use by")
                    if best_before is not None and best_before <= batch.manufactured_on:
                        raise OwnerInputError("The use-by date must be after the date it was made.")
                    batch.best_before = best_before
                if "production_notes" in request.data:
                    batch.production_notes = _text(request.data, "production_notes", max_length=1000) or ""
            except OwnerInputError as exc:
                transaction.set_rollback(True)
                return _error(str(exc))
            batch.save(update_fields=list(fields))
            after = snapshot(batch, fields)
            if after != before:
                record("batch.updated", batch, before=before, after=after, actor=request.user)
        product = Product.objects.get(pk=batch.variant.product_id)
        return Response(_product_payload(product))
