"""
Checkout payment endpoints (Phase G3): Razorpay and Cash on Delivery, plus the guest
"create an account" link.

An order is addressed by its random `oid` so guests can pay; an order that belongs to a
registered buyer is only usable by that buyer or staff (core.permissions.ensure_order_access).
The amount is always the order's stored `total_paise`; nothing about money is read from the request.

Phase C (Ayura): checkout first re-prices the draft (`CheckoutQuoteView`), so what the customer
sees, what is stored and what Razorpay is asked for are the same number, and it shows the Cash on
Delivery total next to it. Placing a COD order re-prices the draft WITH the COD fee in the same
transaction that places it. If the browser says which total it showed (`expected_total_paise`)
and the server's figure differs, the order is not placed and the new figures come back, so a
customer is never charged an amount they were not shown.
"""

import logging

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from core.audit import record, snapshot
from core.jobs import enqueue
from core.permissions import ensure_order_access
from store import payments
from store.account_claim import ClaimError, claim_account
from store.emails import ACCOUNT_INVITE_JOB, queue_order_email
from store.models import CartOrder
from store.order_state import OrderStateError, StockUnavailable, place_cod_order
from store.payments import PaymentError
from store.pricing import (PAYMENT_METHOD_COD, PricingError, apply_quote_to_order, get_pricing_config,
                           quote_order, record_redemption)

logger = logging.getLogger(__name__)


def _order_for(request, order_oid):
    order = CartOrder.objects.filter(oid=order_oid).first()
    if order is None:
        return None
    ensure_order_access(request, order)
    return order


DRAFT_PAYMENT_STATUSES = ("initiated", "processing")
REPRICE_AUDIT_FIELDS = ("sub_total_paise", "saved_paise", "shipping_amount_paise", "cod_fee_paise", "total_paise",
                        "coupon_code")
QUOTE_KEYS = ("subtotal_paise", "discount_paise", "shipping_paise", "cod_fee_paise", "total_paise", "coupon_code",
              "coupon_message", "free_shipping", "payment_method")


def _is_draft(order):
    return order.payment_status in DRAFT_PAYMENT_STATUSES and order.order_status != "Cancelled"


def cod_offered(config=None):
    """Cash on Delivery is offered only when the project enables it AND the owner has it on."""
    config = config or get_pricing_config()
    return payments.is_enabled(payments.COD) and config.cod_enabled


def _summary(priced):
    data = priced.as_dict()
    return {key: data[key] for key in QUOTE_KEYS}


def _reprice(order, payment_method, reason):
    """
    Re-price a locked order draft for `payment_method` and store the result. Audited when any
    amount changed. Must run inside transaction.atomic() with the order row locked.
    Returns the quote. Raises PricingError when the order can no longer be priced.
    """
    before = snapshot(order, REPRICE_AUDIT_FIELDS)
    order_items, priced, customer = quote_order(order, payment_method=payment_method, lock_coupon=True)
    apply_quote_to_order(order, order_items, priced)
    record_redemption(order, priced, customer)
    after = snapshot(order, REPRICE_AUDIT_FIELDS)
    if after != before:
        record("order.repriced", order, before=before, after=after, reason=reason)
    return priced


def _expected_total(request):
    """The total the browser showed, as integer paise, or None when it did not say."""
    raw = request.data.get("expected_total_paise")
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool) or isinstance(raw, float):
        raise ValueError("expected_total_paise must be a whole number of paise.")
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        raise ValueError("expected_total_paise must be a whole number of paise.")


def _clear_cart(order):
    from store.views import _clear_cart_for_order

    _clear_cart_for_order(order)


class PaymentMethodsView(APIView):
    """Which payment methods checkout should offer. Contains nothing secret."""

    permission_classes = (AllowAny,)

    def get(self, request, *args, **kwargs):
        from store.payments.razorpay import is_configured

        config = get_pricing_config()
        return Response({
            "razorpay": payments.is_enabled(payments.RAZORPAY),
            "razorpay_configured": is_configured(),
            "cod": cod_offered(config),
            # What a Cash on Delivery order pays on top (0 when there is no fee). Phase C.
            "cod_fee_paise": config.cod_fee_if_cod_paise if cod_offered(config) else 0,
        })


class CheckoutQuoteView(APIView):
    """
    POST payments/quote/<order_oid>/   (Phase C)

    Re-prices an unpaid order draft with today's shipping settings and returns both totals the
    checkout page shows: `online` (what is stored on the order, and what Razorpay will be asked
    for) and `cod` (the same order placed as Cash on Delivery, fee included; null when COD is not
    offered). A placed order is never re-priced: its stored figures come back as `online`.
    """

    permission_classes = (AllowAny,)
    throttle_scope = "checkout"

    def post(self, request, order_oid, *args, **kwargs):
        order = _order_for(request, order_oid)
        if order is None:
            return Response({"message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        config = get_pricing_config()
        if not _is_draft(order):
            return Response({"draft": False, "online": None, "cod": None, "total_paise": order.total_paise,
                             "cod_fee_paise": order.cod_fee_paise})
        try:
            with transaction.atomic():
                order = CartOrder.objects.select_for_update().get(pk=order.pk)
                online = _reprice(order, payment_method="", reason="checkout opened")
                cod = None
                if cod_offered(config):
                    _items, cod_quote, _customer = quote_order(order, payment_method=PAYMENT_METHOD_COD)
                    cod = _summary(cod_quote)
        except PricingError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"draft": True, "online": _summary(online), "cod": cod})


class RazorpayStartView(APIView):
    """Create the Razorpay order for this order's stored total and return the checkout options."""

    permission_classes = (AllowAny,)
    throttle_scope = "checkout"

    def post(self, request, order_oid, *args, **kwargs):
        order = _order_for(request, order_oid)
        if order is None:
            return Response({"message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        if order.cod_fee_paise:
            # A Razorpay order is only ever created from the online (no COD fee) price.
            return Response({"message": "This order was placed as Cash on Delivery."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            options = payments.get_provider(payments.RAZORPAY).create_payment(order)
        except PaymentError as exc:
            return Response({"message": exc.message}, status=exc.status)
        return Response({"options": options, "order_oid": order.oid})


class RazorpayReturnView(APIView):
    """
    The browser is back from Razorpay Checkout. Verifies the signature and answers
    "confirming": the order is NOT marked paid here. The page then polls the order until the
    webhook (or the reconcile job) confirms the payment.
    """

    permission_classes = (AllowAny,)
    throttle_scope = "checkout"

    def post(self, request, *args, **kwargs):
        order = _order_for(request, request.data.get("order_oid"))
        if order is None:
            return Response({"message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            payments.get_provider(payments.RAZORPAY).verify_return(order, request.data)
        except PaymentError as exc:
            return Response({"message": exc.message}, status=exc.status)
        if order.payment_status != "paid":
            queue_order_email(order, "placed")
        return Response({"message": "confirming", "order_oid": order.oid, "payment_status": order.payment_status})


class RazorpayWebhookView(APIView):
    """
    Razorpay's server-to-server notification. Unauthenticated by design: the signature over
    the RAW body is the authentication. This is the only request that marks an order paid.
    """

    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_scope = "webhook"

    def post(self, request, *args, **kwargs):
        if not payments.is_enabled(payments.RAZORPAY):
            return Response({"message": "not enabled"}, status=status.HTTP_403_FORBIDDEN)
        raw_body = request._request.body  # the exact bytes Razorpay signed; never the parsed data
        from store.payments.razorpay import RazorpayProvider

        code, result = RazorpayProvider().handle_webhook(raw_body, request.headers)
        return Response({"result": result}, status=code)


class PlaceCodOrderView(APIView):
    """
    Place the order as Cash on Delivery. Nothing is charged online; the stock is kept for the
    order. The draft is re-priced with the COD fee (Phase C) in the same transaction, and the
    order is refused (409, with the new figures) when that total is not the one the customer saw.
    """

    permission_classes = (AllowAny,)
    throttle_scope = "checkout"

    def post(self, request, order_oid, *args, **kwargs):
        if not cod_offered():
            return Response({"message": "Cash on Delivery is not available."}, status=status.HTTP_403_FORBIDDEN)
        order = _order_for(request, order_oid)
        if order is None:
            return Response({"message": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            expected = _expected_total(request)
        except ValueError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with transaction.atomic():
                order = CartOrder.objects.select_for_update().get(pk=order.pk)
                if _is_draft(order):
                    priced = _reprice(order, payment_method=PAYMENT_METHOD_COD, reason="placed as cash on delivery")
                    if expected is not None and expected != priced.total_paise:
                        transaction.set_rollback(True)
                        return Response({
                            "message": "The total for Cash on Delivery has changed. Please check it before placing the order.",
                            "total_changed": True,
                            "cod": _summary(priced),
                        }, status=status.HTTP_409_CONFLICT)
                order = place_cod_order(order)
        except PricingError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except StockUnavailable as exc:
            return Response({"message": str(exc)}, status=status.HTTP_409_CONFLICT)
        except OrderStateError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        _clear_cart(order)
        if order.buyer_id:
            from store.views import send_notification

            send_notification(user=order.buyer, order=order)
        queue_order_email(order, "placed")
        return Response({"message": "Order placed", "order_oid": order.oid, "payment_status": order.payment_status,
                         "total_paise": order.total_paise, "cod_fee_paise": order.cod_fee_paise})


class AccountInviteView(APIView):
    """
    A guest asks for a "create your account" link for their order. The link only ever goes to
    the email address on the order. The answer is the same whether or not anything was sent.
    """

    permission_classes = (AllowAny,)
    throttle_scope = "otp"

    def post(self, request, *args, **kwargs):
        order = CartOrder.objects.filter(oid=request.data.get("order_oid")).first()
        if order is not None and order.buyer_id is None and order.email \
                and order.payment_status in ("paid", "pending"):
            enqueue(ACCOUNT_INVITE_JOB, {"order_id": order.pk}, dedupe_key=f"account-invite:{order.pk}")
        return Response({"message": "If this order can be linked to an account, we have emailed a link to the address on the order."})


class AccountClaimView(APIView):
    """Use the emailed link: set a password, create the account, attach that email's guest orders."""

    permission_classes = (AllowAny,)
    throttle_scope = "otp"

    def post(self, request, *args, **kwargs):
        try:
            user, created, attached = claim_account(request.data.get("token"), str(request.data.get("password") or ""))
        except ClaimError as exc:
            return Response({"message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if created:
            message = "Your account is ready. Sign in with your email and the password you just chose."
        else:
            message = "You already have an account with this email. Your order has been added to it; please sign in."
        return Response({"message": message, "created": created, "orders_attached": attached, "email": user.email})
