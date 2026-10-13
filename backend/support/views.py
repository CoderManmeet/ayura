"""
Customer-facing support endpoints (Phase F, Ayura).

    POST   support/queries/            start a thread (signed in or as a guest)
    GET    support/queries/mine/       my own threads            (signed in)
    GET    support/queries/<ref>/      read one thread           (owner of it, or a signed link)
    POST   support/queries/<ref>/      reply on that thread      (same access)
    GET    support/thread/?token=...   read the thread a signed link names
    POST   support/thread/             reply on it, by token alone
    POST   support/find/               order id + email -> a link to that order's thread

Who may read a thread:

  * the signed-in customer it belongs to (matched by account, or by the account's email for a
    thread opened as a guest before the account existed);
  * anyone holding a valid signed link for that one thread (support.links);
  * staff, who have their own screens but are never locked out.

Everyone else gets 403, including another signed-in customer. The thread reference alone is
NOT access: it is shown to the customer and read out over the phone, so it is treated as an
identifier, not a password.

Every endpoint here is public by declaration (`AllowAny`) and rate-limited under the `support`
scope, because a guest must be able to report a problem without an account.
"""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import ensure_order_access
from store.models import CartOrder
from support import emails as support_emails
from support.links import ThreadLinkError, build_thread_link, read_token
from support.models import Query
from support.serializers import customer_summary, customer_thread
from support.services import (
    SupportError,
    add_customer_message,
    customer_can_read,
    mark_read_by_customer,
    open_query,
    queries_for_user,
)

logger = logging.getLogger(__name__)


def _error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"message": message}, status=code)


def _photos(request):
    """Every file sent as `photos` (the browser may repeat the field name)."""
    files = request.FILES
    if hasattr(files, "getlist"):
        return files.getlist("photos")
    return [files["photos"]] if "photos" in files else []


def _token_of(request):
    """The signed link's token, from the query string or the body."""
    return (request.query_params.get("token") or request.data.get("token") or "").strip()


def _reachable(request, ref):
    """
    (query, how) for a thread this caller may read, or (None, reason) when they may not.

    `how` is "account", "link" or "staff", so a caller can be told which door they came in by.
    """
    token = _token_of(request)
    if token:
        try:
            query = read_token(token)
        except ThreadLinkError as exc:
            return None, str(exc)
        if query.ref != ref:
            return None, "This link is not valid for that conversation."
        return query, "link"

    query = Query.objects.filter(ref=ref).select_related("user", "order").first()
    if query is None:
        # Same answer whether the thread does not exist or is not the caller's: a missing
        # thread and someone else's thread must be indistinguishable from outside.
        return None, "You do not have access to this conversation."
    if customer_can_read(query, request.user):
        return query, "staff" if request.user.is_staff else "account"
    return None, "You do not have access to this conversation."


class SupportQueryCreateView(APIView):
    """
    Start a thread. Accepts multipart (with photos) or JSON.

    A signed-in customer's thread is attached to their account and the reply address defaults
    to the account's email. A guest must give an email, which is where the link is sent.
    """

    permission_classes = (AllowAny,)
    throttle_scope = "support"

    def post(self, request, *args, **kwargs):
        data = request.data
        user = request.user if request.user.is_authenticated else None

        order = None
        order_oid = str(data.get("order_oid") or "").strip()
        if order_oid:
            order = CartOrder.objects.filter(oid=order_oid).first()
            if order is None:
                return _error("We cannot find that order.")
            # A guest knows the order's random oid; a signed-in customer must own it.
            ensure_order_access(request, order)

        email = data.get("email")
        if not email and user is not None:
            email = user.email
        if not email and order is not None:
            email = order.email
        phone = data.get("phone") or (order.mobile if order is not None else "") or (
            getattr(user, "phone", "") if user is not None else "")

        try:
            query, _message = open_query(
                subject=data.get("subject"),
                body=data.get("body"),
                email=email,
                phone=phone,
                order=order,
                user=user,
                photos=_photos(request),
                actor=user,
            )
        except SupportError as exc:
            return _error(str(exc))

        # Email is a courtesy on top of the thread, never a dependency of it.
        support_emails.queue_customer_ack(query)
        support_emails.queue_owner_new_query_notice(query)

        body = customer_thread(query, request)
        # A guest has no account to sign in to, so they are handed their own link.
        if user is None:
            body["link"] = build_thread_link(query)
        return Response(body, status=status.HTTP_201_CREATED)


class SupportMyQueriesView(APIView):
    """Every thread of the signed-in customer, newest activity first."""

    permission_classes = (IsAuthenticated,)
    throttle_scope = "support"

    def get(self, request, *args, **kwargs):
        rows = queries_for_user(request.user).select_related("order").order_by("-last_message_at", "-id")
        return Response({
            "queries": [customer_summary(query) for query in rows],
            "new_replies": sum(1 for query in rows if query.customer_unread),
        })


class SupportThreadView(APIView):
    """Read one thread, or write back on it."""

    permission_classes = (AllowAny,)
    throttle_scope = "support"

    def get(self, request, ref, *args, **kwargs):
        query, how = _reachable(request, ref)
        if query is None:
            return _error(how, status.HTTP_403_FORBIDDEN)
        # Reading it clears the customer's "new reply" badge; the owner has her own screens.
        if how != "staff":
            mark_read_by_customer(query)
        return Response(customer_thread(query, request))

    def post(self, request, ref, *args, **kwargs):
        query, how = _reachable(request, ref)
        if query is None:
            return _error(how, status.HTTP_403_FORBIDDEN)
        try:
            add_customer_message(
                query, request.data.get("body"), photos=_photos(request),
                actor=request.user if request.user.is_authenticated else None,
            )
        except SupportError as exc:
            return _error(str(exc))
        query.refresh_from_db()
        return Response(customer_thread(query, request), status=status.HTTP_201_CREATED)


class SupportThreadByLinkView(APIView):
    """
    Read or write the thread a signed link names, without naming it in the address.

        GET  support/thread/?token=...
        POST support/thread/        {token, body}

    The link a guest is given carries only the token, so the page that opens it does not know
    which thread it is until the server says. That means a link cannot be edited into somebody
    else's conversation: there is no reference in it to change.
    """

    permission_classes = (AllowAny,)
    throttle_scope = "support"

    def _query(self, request):
        return read_token(_token_of(request))

    def get(self, request, *args, **kwargs):
        try:
            query = self._query(request)
        except ThreadLinkError as exc:
            return _error(str(exc), status.HTTP_403_FORBIDDEN)
        mark_read_by_customer(query)
        return Response(customer_thread(query, request))

    def post(self, request, *args, **kwargs):
        try:
            query = self._query(request)
        except ThreadLinkError as exc:
            return _error(str(exc), status.HTTP_403_FORBIDDEN)
        try:
            add_customer_message(query, request.data.get("body"), photos=_photos(request),
                                 actor=request.user if request.user.is_authenticated else None)
        except SupportError as exc:
            return _error(str(exc))
        query.refresh_from_db()
        return Response(customer_thread(query, request), status=status.HTTP_201_CREATED)


class SupportFindView(APIView):
    """
    A guest who lost their link: order id plus the email on that order gives it back.

    The bar is the same as the guest order page's (store's orders are addressable by their
    random oid), with the order's own email required on top. The answer never says which half
    was wrong, so this cannot be used to test whether an address shops here.
    """

    permission_classes = (AllowAny,)
    throttle_scope = "support"

    NOT_FOUND = "We cannot find a conversation for that order and email address."

    def post(self, request, *args, **kwargs):
        oid = str(request.data.get("order_oid") or "").strip()
        email = str(request.data.get("email") or "").strip().lower()
        if not oid or not email:
            return _error("Please give both your order number and the email address you ordered with.")

        order = CartOrder.objects.filter(oid=oid).first()
        if order is None or (order.email or "").strip().lower() != email:
            return _error(self.NOT_FOUND, status.HTTP_404_NOT_FOUND)
        query = (Query.objects.filter(order=order, email__iexact=email)
                 .order_by("-last_message_at", "-id").first())
        if query is None:
            return _error(self.NOT_FOUND, status.HTTP_404_NOT_FOUND)
        return Response({"ref": query.ref, "link": build_thread_link(query)})


class SupportOrderQueriesView(APIView):
    """
    The threads already opened about one order, so the order page can say "you have already
    reported this" instead of inviting a second identical query.
    """

    permission_classes = (AllowAny,)
    throttle_scope = "support"

    def get(self, request, order_oid, *args, **kwargs):
        order = get_object_or_404(CartOrder, oid=order_oid)
        ensure_order_access(request, order)
        rows = Query.objects.filter(order=order).select_related("order").order_by("-last_message_at", "-id")
        if request.user.is_authenticated and not request.user.is_staff:
            # A signed-in customer sees only their own threads about the order; a guest reading
            # by oid sees the guest threads on it, which is the same bar as the order page.
            rows = [query for query in rows if customer_can_read(query, request.user)]
        return Response({"queries": [customer_summary(query) for query in rows]})
