"""
Owner (staff) endpoints for dispatch checks, gift samples, expiry and batch lookup
(Phase D, Ayura).

    GET    owner/orders/<oid>/dispatch/     which batch each line will go out from, with its
                                            use-by date flagged, plus this order's gift samples
    POST   owner/orders/<oid>/samples/      {"action": "add"|"remove"|"none", ...}
    GET    owner/expiry/                    batches with stock that are expired, due soon, or
                                            have no use-by date recorded
    POST   owner/batches/<id>/write-off/    {"quantity", "reason"} -> a DAMAGE_OUT movement
    GET    owner/batch-lookup/?code=...     every order that received stock from one batch
    GET    owner/samples-report/            did the free samples lead to sales?

Nothing here blocks a dispatch (ROADMAP Y12): an expired or undated batch is FLAGGED, and the
owner decides. Stock only ever moves through inventory.services, and every change is audited.

Staff only: core.permissions.IsStaffOwner.
"""

import logging

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import ProductVariant
from core.money import format_inr
from core.permissions import IsStaffOwner
from inventory.models import Batch, ReservationStatus
from inventory.services import (
    InsufficientStock,
    InvalidMovement,
    batch_on_hand,
    batch_reserved_qty,
    batches_nearing_expiry,
    expired_unsold_batches,
    order_batches,
    orders_from_batch,
    undated_batches_with_stock,
    write_off_batch,
)
from store.models import CartOrder, OrderSample
from store.samples import SampleError, add_sample, conversion_report, decide_no_samples, remove_sample, sample_variants

logger = logging.getLogger(__name__)


def _error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"message": message}, status=code)


def _batch_row(batch, quantity=None, today=None):
    """One batch, with the two things that matter before a parcel goes out: date and flag."""
    today = today or timezone.localdate()
    expired = bool(batch.best_before and batch.best_before < today)
    return {
        "id": batch.pk,
        "batch_code": batch.batch_code,
        "manufactured_on": batch.manufactured_on.isoformat() if batch.manufactured_on else None,
        "best_before": batch.best_before.isoformat() if batch.best_before else None,
        "expired": expired,
        "undated": batch.best_before is None,
        "quantity": quantity,
        "remaining": batch_on_hand(batch),
        "variant": batch.variant.sku,
        "product": batch.variant.product.title,
    }


class OwnerOrderDispatchView(APIView):
    """What is actually in the parcel: the batches allocated to each line, and the samples."""

    permission_classes = (IsStaffOwner,)

    def get(self, request, order_oid, *args, **kwargs):
        order = get_object_or_404(CartOrder, oid=order_oid)
        today = timezone.localdate()
        allocated = order_batches(order)

        lines = []
        for item in order.orderitem.select_related("product", "variant").order_by("id"):
            rows = [
                _batch_row(entry["batch"], quantity=entry["quantity"], today=today)
                for entry in allocated.get(item.pk, []) if entry["batch"] is not None
            ]
            lines.append({
                "order_item_id": item.pk,
                "title": item.product.title,
                "variant": item.variant.name if item.variant_id else "",
                "qty": item.qty,
                "delivery_status": item.delivery_status,
                "batches": rows,
                "has_expired": any(row["expired"] for row in rows),
                "has_undated": any(row["undated"] for row in rows),
            })

        samples = [
            {
                "id": sample.pk,
                "variant_id": sample.variant_id,
                "sku": sample.variant.sku,
                "name": f"{sample.variant.product.title} {sample.variant.name}".strip(),
                "qty": sample.qty,
            }
            for sample in order.samples.select_related("variant", "variant__product").order_by("id")
        ]
        options = [
            {
                "variant_id": variant.pk,
                "sku": variant.sku,
                "name": f"{variant.product.title} {variant.name}".strip(),
                "available": variant.available_qty,
            }
            for variant in sample_variants()
        ]
        return Response({
            "oid": order.oid,
            "lines": lines,
            "samples": samples,
            "sample_decision": order.sample_decision,
            "sample_options": options,
            "any_expired": any(line["has_expired"] for line in lines),
            "any_undated": any(line["has_undated"] for line in lines),
        })


class OwnerOrderSamplesView(APIView):
    """
    POST {"action": ...} on one order's gift samples:

      add     {"variant_id": 7, "qty": 1}   hold that sample's stock for this parcel
      remove  {"sample_id": 3}              take it off and give the stock back
      none    this order goes out without samples

    The customer is never told about any of this (ROADMAP Y19).
    """

    permission_classes = (IsStaffOwner,)

    def post(self, request, order_oid, *args, **kwargs):
        order = get_object_or_404(CartOrder, oid=order_oid)
        action = str(request.data.get("action") or "")
        try:
            if action == "add":
                variant = ProductVariant.objects.filter(pk=request.data.get("variant_id")).first()
                if variant is None:
                    return _error("That sample does not exist.")
                add_sample(order, variant, qty=request.data.get("qty", 1), actor=request.user)
            elif action == "remove":
                sample = OrderSample.objects.filter(pk=request.data.get("sample_id"), order=order).first()
                if sample is None:
                    return _error("That sample is not on this order.")
                remove_sample(sample, actor=request.user)
            elif action == "none":
                decide_no_samples(order, actor=request.user)
            else:
                return _error("Unknown action.")
        except SampleError as exc:
            return _error(str(exc))
        return OwnerOrderDispatchView().get(request, order_oid)


class OwnerExpiryView(APIView):
    """
    Stock that needs the owner's attention: already expired, expiring within
    `EXPIRY_ALERT_DAYS`, or sitting in the store with no use-by date recorded at all.
    """

    permission_classes = (IsStaffOwner,)

    def get(self, request, *args, **kwargs):
        today = timezone.localdate()

        def rows(pairs):
            return [
                {**_batch_row(batch, today=today), "held": batch_reserved_qty(batch), "on_hand": remaining}
                for batch, remaining in pairs
            ]

        return Response({
            "expired": rows(expired_unsold_batches()),
            "expiring_soon": rows(batches_nearing_expiry()),
            "undated": rows(undated_batches_with_stock()),
        })


class OwnerBatchWriteOffView(APIView):
    """
    Take stock out of a batch for good (expired, damaged, spilled).

    A write-off is a DAMAGE_OUT movement in the ledger, never an edit: the batch keeps its
    whole history. Stock that is held for a customer's order cannot be written off; cancel
    that order first.
    """

    permission_classes = (IsStaffOwner,)

    def post(self, request, batch_id, *args, **kwargs):
        batch = get_object_or_404(Batch, pk=batch_id)
        reason = str(request.data.get("reason") or "").strip()
        if not reason:
            return _error("Say why this stock is being written off.")
        raw = request.data.get("quantity")
        if isinstance(raw, float) or isinstance(raw, bool):
            return _error("Quantity must be a whole number.")
        try:
            quantity = int(str(raw).strip())
        except (TypeError, ValueError):
            return _error("Quantity must be a whole number.")
        try:
            write_off_batch(batch, quantity, reason=reason, actor=request.user)
        except InsufficientStock as exc:
            return _error(f"Only {exc.available} unit(s) of that batch can be written off; the rest is on hand for an order.")
        except InvalidMovement as exc:
            return _error(str(exc))
        return Response({**_batch_row(batch), "held": batch_reserved_qty(batch), "on_hand": batch_on_hand(batch)})


class OwnerBatchLookupView(APIView):
    """
    The recall question: who received stock from this batch?

    `?code=` is matched exactly first, then as "contains", so a partly remembered code still
    finds the batch. Lists orders that physically received stock (SALE_OUT or SAMPLE_OUT) and
    orders that are holding it but have not been sent yet.
    """

    permission_classes = (IsStaffOwner,)

    def get(self, request, *args, **kwargs):
        code = str(request.GET.get("code") or "").strip()
        if not code:
            return _error("Type a batch code to look up.")
        batch = Batch.objects.filter(batch_code__iexact=code).first()
        if batch is None:
            matches = list(Batch.objects.filter(batch_code__icontains=code[:64])[:2])
            if len(matches) != 1:
                return Response({"found": False, "code": code, "orders": [],
                                 "message": "No batch with that code." if not matches
                                 else "More than one batch matches. Type the full code."},
                                status=status.HTTP_200_OK)
            batch = matches[0]

        orders = [
            {
                "oid": row["order"].oid,
                "date": row["order"].date.isoformat(),
                "full_name": row["order"].full_name,
                "quantity": row["quantity"],
                "sample_only": row["sample_only"],
                "dispatched": row["dispatched"],
                "order_status": row["order"].order_status,
                "payment_status": row["order"].payment_status,
            }
            for row in orders_from_batch(batch)
        ]
        return Response({"found": True, "batch": _batch_row(batch), "orders": orders})


class OwnerSamplesReportView(APIView):
    """Per sample: how many orders carried it, and how many of those customers came back."""

    permission_classes = (IsStaffOwner,)

    def get(self, request, *args, **kwargs):
        rows = []
        for entry in conversion_report():
            rows.append({
                "variant_id": entry["variant"].pk,
                "sku": entry["variant"].sku,
                "sample": f"{entry['product'].title} {entry['variant'].name}".strip(),
                "product": entry["product"].title,
                "product_slug": entry["product"].slug,
                "given": entry["given"],
                "converted": entry["converted"],
                "conversion_percent": entry["conversion_percent"],
                "conversions": [
                    {
                        "sample_order": conversion["sample_order"].oid,
                        "then_bought": [
                            {"oid": order.oid, "date": order.date.isoformat(), "total": format_inr(int(order.total_paise))}
                            for order in conversion["then_bought"]
                        ],
                    }
                    for conversion in entry["conversions"]
                ],
            })
        return Response({"rows": rows})
