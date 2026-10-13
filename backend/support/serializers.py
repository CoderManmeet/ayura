"""
What a support thread looks like over the API (Phase F, Ayura).

Two shapes, deliberately different:

  * the CUSTOMER's view: their own messages and the owner's replies, the photos, the status.
    It never carries the other customer-identifying fields of a thread it does not own, because
    a customer only ever receives their own thread.
  * the OWNER's view: the same conversation plus who the customer is and which order it is
    about, so she can act on it.

Neither shape contains a user object: `core.display_name` decides what a person is called, and
a support thread shows the name the customer gave on the order, not an email address.
"""

from support.models import AUTHOR_OWNER, Query


def photo_rows(message, request=None):
    rows = []
    for photo in message.photos.all():
        try:
            url = photo.image.url
        except ValueError:                      # a row whose file went missing
            continue
        rows.append({"id": photo.pk, "url": request.build_absolute_uri(url) if request is not None else url})
    return rows


def message_row(message, request=None):
    return {
        "id": message.pk,
        "author": message.author,
        "body": message.body,
        "created_at": message.created_at,
        "photos": photo_rows(message, request),
    }


def _messages(query, request=None):
    ordered = query.messages.prefetch_related("photos").order_by("created_at", "id")
    return [message_row(message, request) for message in ordered]


def customer_thread(query, request=None):
    """The thread as its own customer sees it."""
    return {
        "ref": query.ref,
        "subject": query.subject,
        "status": query.status,
        "order_oid": query.order.oid if query.order_id else "",
        "created_at": query.created_at,
        "last_message_at": query.last_message_at,
        "has_new_reply": bool(query.customer_unread),
        "messages": _messages(query, request),
    }


def customer_summary(query):
    """One line per thread on the customer's own list."""
    last = query.messages.order_by("-created_at", "-id").first()
    return {
        "ref": query.ref,
        "subject": query.subject,
        "status": query.status,
        "order_oid": query.order.oid if query.order_id else "",
        "created_at": query.created_at,
        "last_message_at": query.last_message_at,
        "has_new_reply": bool(query.customer_unread),
        "answered": bool(last is not None and last.author == AUTHOR_OWNER),
        "message_count": query.messages.count(),
    }


def owner_summary(query):
    """One row in the owner's inbox."""
    return {
        "ref": query.ref,
        "subject": query.subject,
        "status": query.status,
        "unread": bool(query.owner_unread),
        "customer_name": query.user.full_name if query.user_id and query.user.full_name else "",
        "email": query.email,
        "phone_e164": query.phone_e164,
        "has_account": query.user_id is not None,
        "order_oid": query.order.oid if query.order_id else "",
        "created_at": query.created_at,
        "last_message_at": query.last_message_at,
        "message_count": query.messages.count(),
    }


def owner_thread(query, request=None):
    """The whole thread for the admin area."""
    data = owner_summary(query)
    data["messages"] = _messages(query, request)
    data["closed_at"] = query.closed_at
    return data


def inbox_queryset():
    return Query.objects.select_related("user", "order").prefetch_related("messages")
