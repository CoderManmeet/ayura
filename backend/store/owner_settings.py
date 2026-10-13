"""
Owner (staff) store settings (Phase C, Ayura).

    GET   owner/settings/    shipping, free shipping, Cash on Delivery, the COD fee, the
                             store-wide label details shown on product pages (Phase B) and the
                             grievance-officer details (Phase F)
    PATCH owner/settings/    change any of them

The grievance-officer fields are the OWNER'S OWN TEXT and are blank until she types them. The
storefront shows that block only once the name is filled in, so this code never publishes a
legal statement on her behalf. Whether those details are required of this business, and in what
wording, is a question for her professional (ROADMAP L4).

Money arrives as rupees in TEXT ("79" or "79.50") and is stored as integer paise through
core.money; a JSON number is refused (rule 6). Every change is audited as `settings.updated`
with the signed-in staff user (rule 9). A change applies to the next price worked out: an order
that has been placed keeps the figures it was placed with.

Staff only: core.permissions.IsStaffOwner.
"""

import logging

from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from addon.models import ConfigSettings
from core.audit import record, snapshot
from core.permissions import IsStaffOwner
from store.owner_catalogue import OwnerInputError, _bool, _positive_int, _rupees_to_paise, _text

logger = logging.getLogger(__name__)

SWITCHES = ("shipping_enabled", "free_shipping_enabled", "cod_enabled", "cod_fee_enabled")
# request key (rupees) -> model field (paise), with the label used in messages
AMOUNTS = (
    ("shipping_flat", "shipping_flat_paise", "Shipping charge"),
    ("free_shipping_threshold", "free_shipping_threshold_paise", "Free shipping from"),
    ("cod_fee", "cod_fee_paise", "Cash on Delivery fee"),
)
LABEL_FIELDS = (("maker_name", 200), ("maker_address", 2000), ("country_of_origin", 100),
                ("consumer_care_contact", 2000),
                # Grievance officer (Phase F). The owner's own words, blank by default; the
                # storefront shows the block only once the name is filled in (ROADMAP L4).
                ("grievance_officer_name", 200), ("grievance_officer_designation", 200),
                ("grievance_officer_email", 254), ("grievance_officer_phone", 40),
                ("grievance_officer_address", 2000))
COUNTS = (("grievance_response_days", "Grievance response time"),)
AUDIT_FIELDS = (SWITCHES + tuple(field for _key, field, _label in AMOUNTS)
                + tuple(name for name, _max in LABEL_FIELDS)
                + tuple(name for name, _label in COUNTS))


def _settings_row():
    row = ConfigSettings.objects.select_for_update().order_by("id").first()
    if row is None:
        row = ConfigSettings.objects.create()
    return row


def _payload(row):
    data = {name: bool(getattr(row, name)) for name in SWITCHES}
    data.update({field: int(getattr(row, field)) for _key, field, _label in AMOUNTS})
    data.update({name: getattr(row, name) for name, _max in LABEL_FIELDS})
    data.update({name: int(getattr(row, name) or 0) for name, _label in COUNTS})
    return data


def _check(row):
    """Settings that make no sense together are refused, with a message the owner can act on."""
    if row.shipping_enabled and row.shipping_flat_paise <= 0:
        raise OwnerInputError("Enter the shipping charge, or switch shipping off to ship every order free.")
    if row.shipping_enabled and row.free_shipping_enabled and row.free_shipping_threshold_paise <= 0:
        raise OwnerInputError("Enter the order amount from which shipping is free, or switch free shipping off.")
    if row.cod_fee_enabled and row.cod_fee_paise <= 0:
        raise OwnerInputError("Enter the Cash on Delivery fee, or switch the fee off.")


class OwnerSettingsView(APIView):
    permission_classes = (IsStaffOwner,)

    def get(self, request, *args, **kwargs):
        with transaction.atomic():
            row = _settings_row()
        return Response(_payload(row))

    def patch(self, request, *args, **kwargs):
        data = request.data
        with transaction.atomic():
            row = _settings_row()
            before = snapshot(row, AUDIT_FIELDS)
            try:
                for name in SWITCHES:
                    if name in data:
                        setattr(row, name, _bool(data.get(name)))
                for key, field, label in AMOUNTS:
                    if key in data:
                        setattr(row, field, _rupees_to_paise(data.get(key), label, required=True))
                for name, max_length in LABEL_FIELDS:
                    if name in data:
                        setattr(row, name, _text(data, name, max_length=max_length) or "")
                for name, label in COUNTS:
                    if name in data:
                        setattr(row, name, _positive_int(data.get(name), label, allow_zero=True) or 0)
                _check(row)
            except OwnerInputError as exc:
                transaction.set_rollback(True)
                return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            row.save()
            after = snapshot(row, AUDIT_FIELDS)
            if after != before:
                record("settings.updated", row, before=before, after=after, actor=request.user)
        return Response(_payload(row))
