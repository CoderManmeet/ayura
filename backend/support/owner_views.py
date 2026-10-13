"""
Owner (staff) support inbox (Phase F, Ayura).

    GET  owner/support/              the inbox: every thread, with the unread count
    GET  owner/support/<ref>/        one thread (opening it clears its unread flag)
    POST owner/support/<ref>/        {body, close} reply, optionally closing as you answer
    POST owner/support/<ref>/close/  close without replying, or reopen

A reply moves the thread to ANSWERED and the customer is told (one email per reply). Closing is
never the end of the conversation: a customer who writes back reopens the thread, so a problem
that was not really solved comes back to the inbox.

Every change is audited with the signed-in staff user (rule 9).
Staff only: core.permissions.IsStaffOwner.
"""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.permissions import IsStaffOwner
from support import emails as support_emails
from support.models import STATUS_ANSWERED, STATUS_CLOSED, STATUS_OPEN, Query
from support.serializers import inbox_queryset, owner_summary, owner_thread
from support.services import (
    SupportError,
    add_owner_message,
    close_query,
    inbox_counts,
    mark_read_by_owner,
    reopen_query,
)

logger = logging.getLogger(__name__)

STATUS_FILTERS = {"open": STATUS_OPEN, "answered": STATUS_ANSWERED, "closed": STATUS_CLOSED}


def _error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"message": message}, status=code)


def _photos(request):
    files = request.FILES
    if hasattr(files, "getlist"):
        return files.getlist("photos")
    return [files["photos"]] if "photos" in files else []


class OwnerSupportListView(APIView):
    """The inbox. `?status=open|answered|closed` narrows it; unread threads come first."""

    permission_classes = (IsStaffOwner,)

    def get(self, request, *args, **kwargs):
        rows = inbox_queryset()
        wanted = str(request.query_params.get("status") or "").strip().lower()
        if wanted in STATUS_FILTERS:
            rows = rows.filter(status=STATUS_FILTERS[wanted])
        elif wanted == "" or wanted == "live":
            # The default view is what still needs the owner: closed threads are out of the way.
            rows = rows.exclude(status=STATUS_CLOSED)
        rows = rows.order_by("-owner_unread", "-last_message_at", "-id")
        return Response({"queries": [owner_summary(query) for query in rows], "counts": inbox_counts()})


class OwnerSupportThreadView(APIView):
    """Read a thread, or answer it."""

    permission_classes = (IsStaffOwner,)

    def get(self, request, ref, *args, **kwargs):
        query = get_object_or_404(inbox_queryset(), ref=ref)
        mark_read_by_owner(query)
        return Response(owner_thread(query, request))

    def post(self, request, ref, *args, **kwargs):
        query = get_object_or_404(Query.objects.select_related("user", "order"), ref=ref)
        close = str(request.data.get("close") or "").strip().lower() in ("1", "true", "yes", "on")
        try:
            message = add_owner_message(query, request.data.get("body"), actor=request.user,
                                        close=close, photos=_photos(request))
        except SupportError as exc:
            return _error(str(exc))

        # The customer is told there is a reply; the thread already holds it either way.
        support_emails.queue_customer_reply_notice(query, message)
        query.refresh_from_db()
        return Response(owner_thread(query, request), status=status.HTTP_201_CREATED)


class OwnerSupportCloseView(APIView):
    """Close a thread without replying, or put a closed one back in the inbox."""

    permission_classes = (IsStaffOwner,)

    def post(self, request, ref, *args, **kwargs):
        query = get_object_or_404(Query.objects.select_related("user", "order"), ref=ref)
        action = str(request.data.get("action") or "close").strip().lower()
        reason = str(request.data.get("reason") or "").strip()[:255]
        if action == "reopen":
            reopen_query(query, actor=request.user, reason=reason)
        elif action == "close":
            close_query(query, actor=request.user, reason=reason)
        else:
            return _error('Unknown action. Use "close" or "reopen".')
        query.refresh_from_db()
        return Response(owner_thread(query, request))
