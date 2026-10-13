"""
Owner (staff) kit builder (Phase E, Ayura).

    GET    owner/kits/                          every kit, what is in it, and what may be added
    POST   owner/kits/<variant_id>/components/  {component_variant_id, qty} put a part in a kit
    PATCH  owner/kit-components/<id>/           {qty} change how many of that part go in
    DELETE owner/kit-components/<id>/           take the part out

A kit is a variant with `is_kit` ticked on the product's "Sizes & stock" screen. It holds no
stock of its own: what it can sell is the scarcest of its components, and selling one holds
every component through the stock ledger (inventory.services.reserve_kit).

The kit's PRICE is whatever the owner set on the kit size. It is never added up from the
components (ROADMAP Z7), so a kit can be cheaper than buying the parts separately.

Rules kept here: a kit never contains another kit or a sample, never contains itself, each part
appears once, and the quantity is at least 1. Every change is audited (rule 9).

Staff only: core.permissions.IsStaffOwner.
"""

import logging

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import KitComponent, ProductVariant
from core.audit import record, snapshot
from core.money import format_inr
from core.permissions import IsStaffOwner
from inventory.services import available_qty, kit_available_qty
from store.owner_catalogue import OwnerInputError, _positive_int

logger = logging.getLogger(__name__)

AUDIT_FIELDS = ("kit_variant", "component_variant", "qty")


def _error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"message": message}, status=code)


def _variant_label(variant):
    return f"{variant.product.title} {variant.name}".strip()


def _component_row(part):
    component = part.component_variant
    return {
        "id": part.pk,
        "component_variant_id": component.pk,
        "sku": component.sku,
        "name": _variant_label(component),
        "net_quantity": component.net_quantity_label,
        "qty": part.qty,
        "available": available_qty(component),
        # How many kits this one part alone would allow, so the owner can see what is holding
        # the kit back without doing the arithmetic.
        "kits_possible": available_qty(component) // part.qty if part.qty else 0,
        "active": component.active,
    }


def _kit_row(kit):
    parts = kit.kit_parts()
    rows = [_component_row(part) for part in parts]
    return {
        "variant_id": kit.pk,
        "sku": kit.sku,
        "name": _variant_label(kit),
        "product": kit.product.title,
        "product_pid": kit.product.pid,
        "price": format_inr(int(kit.price_paise)),
        "price_paise": int(kit.price_paise),
        "active": kit.active,
        "available": kit_available_qty(kit),
        # What the parts would cost bought separately: shown to the owner only, so she can see
        # what she is giving away. It is never used to price the kit (ROADMAP Z7).
        "parts_total": sum(int(part.component_variant.price_paise) * part.qty for part in parts),
        "parts_total_label": format_inr(sum(int(part.component_variant.price_paise) * part.qty for part in parts)),
        "components": rows,
    }


def _kits():
    return (ProductVariant.objects.filter(is_kit=True)
            .select_related("product").order_by("product__title", "name"))


def _candidates():
    """Variants that may go into a kit: a real sellable size, never a kit or a sample."""
    return (ProductVariant.objects.filter(is_kit=False, is_sample=False, active=True)
            .select_related("product").order_by("product__title", "name"))


def _check_component(kit, component):
    if component.pk == kit.pk:
        raise OwnerInputError("A kit cannot contain itself.")
    if component.is_kit:
        raise OwnerInputError("A kit cannot contain another kit.")
    if component.is_sample:
        raise OwnerInputError("A sample is given away, not sold inside a kit.")


class OwnerKitListView(APIView):
    """Every kit with what is inside it, plus the sizes that may be added to one."""

    permission_classes = (IsStaffOwner,)

    def get(self, request, *args, **kwargs):
        return Response({
            "kits": [_kit_row(kit) for kit in _kits()],
            "candidates": [
                {
                    "variant_id": variant.pk,
                    "sku": variant.sku,
                    "name": _variant_label(variant),
                    "net_quantity": variant.net_quantity_label,
                    "available": available_qty(variant),
                }
                for variant in _candidates()
            ],
        })


class OwnerKitComponentCreateView(APIView):
    """Put a part in a kit."""

    permission_classes = (IsStaffOwner,)

    def post(self, request, variant_id, *args, **kwargs):
        kit = get_object_or_404(ProductVariant.objects.select_related("product"), pk=variant_id)
        if not kit.is_kit:
            return _error('That size is not a kit. Tick "Kit" on it first, on the product\'s sizes screen.')
        component = ProductVariant.objects.filter(pk=request.data.get("component_variant_id")).select_related("product").first()
        if component is None:
            return _error("That size does not exist.")
        try:
            _check_component(kit, component)
            qty = _positive_int(request.data.get("qty", 1), "Quantity", required=True)
        except OwnerInputError as exc:
            return _error(str(exc))

        try:
            with transaction.atomic():
                part = KitComponent.objects.create(kit_variant=kit, component_variant=component, qty=qty)
                record("kit.component_added", kit, before=None, after=snapshot(part, AUDIT_FIELDS),
                       reason=f"{qty} x {component.sku} added to {kit.sku}", actor=request.user)
        except IntegrityError:
            return _error("That size is already in this kit. Change its quantity instead.")
        return Response(_kit_row(ProductVariant.objects.get(pk=kit.pk)), status=status.HTTP_201_CREATED)


class OwnerKitComponentDetailView(APIView):
    """Change how many of a part go in, or take it out."""

    permission_classes = (IsStaffOwner,)

    def patch(self, request, component_id, *args, **kwargs):
        part = get_object_or_404(KitComponent.objects.select_related("kit_variant", "component_variant"), pk=component_id)
        try:
            qty = _positive_int(request.data.get("qty"), "Quantity", required=True)
        except OwnerInputError as exc:
            return _error(str(exc))
        with transaction.atomic():
            before = snapshot(part, AUDIT_FIELDS)
            part.qty = qty
            part.save(update_fields=["qty"])
            after = snapshot(part, AUDIT_FIELDS)
            if after != before:
                record("kit.component_updated", part.kit_variant, before=before, after=after,
                       reason=f"{part.component_variant.sku} quantity changed", actor=request.user)
        return Response(_kit_row(ProductVariant.objects.get(pk=part.kit_variant_id)))

    def delete(self, request, component_id, *args, **kwargs):
        part = get_object_or_404(KitComponent.objects.select_related("kit_variant", "component_variant"), pk=component_id)
        kit_id = part.kit_variant_id
        with transaction.atomic():
            before = snapshot(part, AUDIT_FIELDS)
            record("kit.component_removed", part.kit_variant, before=before, after=None,
                   reason=f"{part.component_variant.sku} taken out of {part.kit_variant.sku}", actor=request.user)
            part.delete()
        return Response(_kit_row(ProductVariant.objects.get(pk=kit_id)))
