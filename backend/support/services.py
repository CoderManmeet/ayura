"""
Support thread services (Phase F, Ayura). Every write to a thread goes through this module.

Rules enforced here:
  * A message has a body or at least one photo. An empty message is not a message.
  * At most SUPPORT_MAX_PHOTOS_PER_MESSAGE photos, each no larger than SUPPORT_PHOTO_MAX_MB, and
    each one really a picture: the bytes are opened and verified, not trusted for having an
    image name or content type. A refused upload stores NOTHING, not a row and not a file.
  * An owner's reply moves the thread to ANSWERED (or CLOSED, if she closes it as she replies).
  * A customer's reply to a closed thread REOPENS it, so an answer that did not solve the
    problem never gets lost.
  * Every state change is audited with actor, before and after (rule 9).

Nothing here sends email. The caller queues that through `support.emails`, so a thread works
with no email provider configured at all.
"""

import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.audit import record, snapshot
from core.phone import try_to_e164
from support.models import (
    AUTHOR_CUSTOMER,
    AUTHOR_OWNER,
    STATUS_ANSWERED,
    STATUS_CLOSED,
    STATUS_OPEN,
    Query,
    QueryMessage,
    QueryPhoto,
)

logger = logging.getLogger(__name__)

SUBJECT_MAX = 200
BODY_MAX = 4000

# What the audit trail watches on a query.
AUDIT_FIELDS = ("status", "subject", "email", "order", "owner_unread", "customer_unread")


class SupportError(Exception):
    """Something the customer or the owner typed cannot be accepted. The message is shown to them."""


def max_photos():
    return int(getattr(settings, "SUPPORT_MAX_PHOTOS_PER_MESSAGE", 3))


def max_photo_bytes():
    return int(getattr(settings, "SUPPORT_PHOTO_MAX_MB", 5)) * 1024 * 1024


def clean_subject(value):
    subject = " ".join(str(value or "").split())
    if not subject:
        raise SupportError("Please give your message a subject.")
    return subject[:SUBJECT_MAX]


def clean_body(value, required=True):
    body = str(value or "").strip()
    if not body and required:
        raise SupportError("Please tell us what happened.")
    if len(body) > BODY_MAX:
        raise SupportError(f"Please keep your message under {BODY_MAX} characters.")
    return body


def clean_email(value):
    email = str(value or "").strip().lower()
    if not email or "@" not in email or email.startswith("@") or email.endswith("@"):
        raise SupportError("Please give an email address we can reply to.")
    if len(email) > 254:
        raise SupportError("That email address is too long.")
    return email


def check_photos(files):
    """
    Refuse the whole upload unless every file is a real picture within the limits.

    Returns the list of files to store. Checking happens before anything is written, so a
    refused upload leaves no half-finished message behind.
    """
    files = [f for f in (files or []) if f is not None]
    if not files:
        return []
    if len(files) > max_photos():
        raise SupportError(f"Please attach at most {max_photos()} photos to one message.")
    limit = max_photo_bytes()
    for upload in files:
        size = getattr(upload, "size", None) or 0
        if size <= 0:
            raise SupportError("One of those files is empty.")
        if size > limit:
            raise SupportError(f"Each photo must be under {max_photo_bytes() // (1024 * 1024)} MB.")
        _verify_is_image(upload)
    return files


def _verify_is_image(upload):
    """
    Open the bytes with Pillow. A PDF renamed .jpg, or an executable sent with an image content
    type, fails here: the file's own name and the content type the browser claims are never
    trusted.
    """
    from PIL import Image, UnidentifiedImageError

    try:
        upload.seek(0)
        with Image.open(upload) as picture:
            picture.verify()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
        name = getattr(upload, "name", "that file")
        raise SupportError(f"{name} is not a photo. Please attach a JPEG or PNG picture.")
    finally:
        try:
            upload.seek(0)
        except (OSError, ValueError):
            pass


def _store_photos(message, files):
    return [QueryPhoto.objects.create(message=message, image=upload) for upload in files]


def _touch(query, **changes):
    for name, value in changes.items():
        setattr(query, name, value)
    query.last_message_at = timezone.now()
    query.save()


@transaction.atomic
def open_query(subject, body, email, phone="", order=None, user=None, photos=None, actor=None):
    """
    Start a thread. Returns (query, message).

    The photos are checked before the query row exists, so a refused photo means no empty
    thread is created either.
    """
    subject = clean_subject(subject)
    body = clean_body(body)
    email = clean_email(email)
    files = check_photos(photos)

    query = Query.objects.create(
        user=user if (user is not None and getattr(user, "is_authenticated", False)) else None,
        email=email,
        phone_e164=try_to_e164(phone) or "",
        order=order,
        subject=subject,
        status=STATUS_OPEN,
        owner_unread=True,
        customer_unread=False,
    )
    message = QueryMessage.objects.create(query=query, author=AUTHOR_CUSTOMER, body=body)
    _store_photos(message, files)
    record("support.query_opened", query, before=None, after=snapshot(query, AUDIT_FIELDS),
           reason=f"{len(files)} photo(s)" if files else "", actor=actor)
    logger.info("support query %s opened with %s photo(s)", query.ref, len(files))
    return query, message


@transaction.atomic
def add_customer_message(query, body, photos=None, actor=None):
    """A customer replies. A closed thread reopens, so an unresolved problem is never lost."""
    body = clean_body(body)
    files = check_photos(photos)

    before = snapshot(query, AUDIT_FIELDS)
    message = QueryMessage.objects.create(query=query, author=AUTHOR_CUSTOMER, body=body)
    _store_photos(message, files)
    reopened = query.status == STATUS_CLOSED
    _touch(query, status=STATUS_OPEN, owner_unread=True, customer_unread=False,
           closed_at=None if reopened else query.closed_at)
    record("support.customer_replied", query, before=before, after=snapshot(query, AUDIT_FIELDS),
           reason="reopened a closed query" if reopened else "", actor=actor)
    logger.info("support query %s: customer replied%s", query.ref, " (reopened)" if reopened else "")
    return message


@transaction.atomic
def add_owner_message(query, body, actor, close=False, photos=None):
    """
    The owner answers. The thread becomes ANSWERED, or CLOSED when she closes it as she replies.

    `actor` is the staff user and is stored on the message as well as in the audit row, so the
    thread itself shows who answered.
    """
    body = clean_body(body)
    files = check_photos(photos)

    before = snapshot(query, AUDIT_FIELDS)
    message = QueryMessage.objects.create(query=query, author=AUTHOR_OWNER, body=body,
                                          author_user=actor if getattr(actor, "pk", None) else None)
    _store_photos(message, files)
    now = timezone.now()
    _touch(query, status=STATUS_CLOSED if close else STATUS_ANSWERED, owner_unread=False,
           customer_unread=True, closed_at=now if close else query.closed_at)
    record("support.owner_replied", query, before=before, after=snapshot(query, AUDIT_FIELDS),
           reason="closed with the reply" if close else "", actor=actor)
    logger.info("support query %s answered by the owner%s", query.ref, " and closed" if close else "")
    return message


@transaction.atomic
def close_query(query, actor, reason=""):
    """Close a thread without replying. Idempotent: closing a closed thread changes nothing."""
    if query.status == STATUS_CLOSED:
        return query
    before = snapshot(query, AUDIT_FIELDS)
    query.status = STATUS_CLOSED
    query.owner_unread = False
    query.closed_at = timezone.now()
    query.save()
    record("support.closed", query, before=before, after=snapshot(query, AUDIT_FIELDS),
           reason=reason, actor=actor)
    logger.info("support query %s closed", query.ref)
    return query


@transaction.atomic
def reopen_query(query, actor, reason=""):
    """Put a closed thread back in the inbox."""
    if query.status != STATUS_CLOSED:
        return query
    before = snapshot(query, AUDIT_FIELDS)
    query.status = STATUS_OPEN
    query.owner_unread = True
    query.closed_at = None
    query.save()
    record("support.reopened", query, before=before, after=snapshot(query, AUDIT_FIELDS),
           reason=reason, actor=actor)
    return query


def mark_read_by_owner(query):
    """Opening a thread in the admin area clears its inbox flag. Not audited: reading is not a change."""
    if query.owner_unread:
        Query.objects.filter(pk=query.pk).update(owner_unread=False)
        query.owner_unread = False
    return query


def mark_read_by_customer(query):
    if query.customer_unread:
        Query.objects.filter(pk=query.pk).update(customer_unread=False)
        query.customer_unread = False
    return query


def inbox_counts():
    """{open, answered, closed, unread} for the owner's sidebar badge."""
    return {
        "open": Query.objects.filter(status=STATUS_OPEN).count(),
        "answered": Query.objects.filter(status=STATUS_ANSWERED).count(),
        "closed": Query.objects.filter(status=STATUS_CLOSED).count(),
        "unread": Query.objects.filter(owner_unread=True).count(),
    }


def queries_for_user(user):
    """
    Every thread this account may read: the ones it opened, plus guest threads it opened with
    the same email before the account existed (the G3 account-link pattern).
    """
    from django.db.models import Q as Lookup

    email = str(getattr(user, "email", "") or "").strip().lower()
    lookup = Lookup(user=user)
    if email:
        lookup = lookup | Lookup(user__isnull=True, email__iexact=email)
    return Query.objects.filter(lookup).distinct()


def customer_can_read(query, user):
    """A signed-in customer may read their own thread and nobody else's. Staff may read any."""
    if not (user is not None and getattr(user, "is_authenticated", False)):
        return False
    if user.is_staff:
        return True
    if query.user_id is not None:
        return query.user_id == user.pk
    account_email = str(getattr(user, "email", "") or "").strip().lower()
    return bool(account_email) and query.email.lower() == account_email
