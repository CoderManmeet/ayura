"""
Customer support threads (Phase F, Ayura).

A customer reports a problem (damaged, leaking, anything else), optionally with photos, and
the owner answers from the admin area. One `Query` is one conversation; `QueryMessage` rows are
what was said, in order; `QueryPhoto` rows are the pictures attached to a message.

Shape of the thing:

  * A query is addressed by its random `ref`, never by its database id, so a reference a
    customer sees (or a link they are sent) reveals nothing about anyone else's.
  * A query may belong to a signed-in `user`, or to a guest identified only by the `email` they
    gave. Both are kept: a guest who later creates an account keeps their threads.
  * MESSAGES ARE APPEND-ONLY (core.models.AppendOnlyModel). What was said in a support thread is
    a record of what the store told a customer; it is never edited or quietly removed.
  * The two unread flags are independent, so the owner's inbox count and the customer's
    "new reply" badge cannot overwrite each other.

Nothing here decides anything legal. The grievance-officer details the e-commerce rules
require are owner-entered fields on `addon.ConfigSettings` and are shown only once the owner
has filled them in (ROADMAP L4).
"""

from django.conf import settings
from django.db import models
from django.utils import timezone

from shortuuid.django_fields import ShortUUIDField

from core.models import AppendOnlyModel

STATUS_OPEN = "OPEN"
STATUS_ANSWERED = "ANSWERED"
STATUS_CLOSED = "CLOSED"
STATUS_CHOICES = (
    (STATUS_OPEN, "Open"),
    (STATUS_ANSWERED, "Answered"),
    (STATUS_CLOSED, "Closed"),
)

AUTHOR_CUSTOMER = "CUSTOMER"
AUTHOR_OWNER = "OWNER"
AUTHOR_CHOICES = (
    (AUTHOR_CUSTOMER, "Customer"),
    (AUTHOR_OWNER, "Owner"),
)


def support_photo_path(instance, filename):
    """Photos live under their query's reference, so a thread's files are easy to find."""
    return f"support/{instance.message.query.ref}/{filename}"


class Query(models.Model):
    """One support conversation."""

    # What the customer sees and what a link carries. Lower-case letters only, like an order's
    # oid, so it can be read out over the phone without ambiguity.
    ref = ShortUUIDField(length=10, max_length=25, alphabet="abcdefghijklmnopqrstuvxyz", unique=True)

    # The account, when the customer was signed in. A guest's thread has no user and is
    # identified by the email they gave.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name="support_queries")
    email = models.EmailField(max_length=254)
    # E.164 (+91XXXXXXXXXX), from core.phone. Blank when the customer gave no number.
    phone_e164 = models.CharField(max_length=20, blank=True, default="")
    # The order being asked about, when there is one. SET_NULL so deleting an order (which the
    # store does not do) could never take the conversation with it.
    order = models.ForeignKey("store.CartOrder", on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="support_queries")

    subject = models.CharField(max_length=200)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True)

    # Who has not read the latest message. The owner's inbox counts `owner_unread`; the
    # customer's thread shows a badge from `customer_unread`.
    owner_unread = models.BooleanField(default=True)
    customer_unread = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    # When the newest message arrived, whoever wrote it: what the inbox sorts by.
    last_message_at = models.DateTimeField(default=timezone.now, db_index=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_message_at", "-id"]
        verbose_name_plural = "Queries"
        indexes = [models.Index(fields=["status", "last_message_at"])]

    def __str__(self):
        return f"{self.ref} {self.subject[:40]}"


class QueryMessage(AppendOnlyModel):
    """One message in a thread. Append-only: a sent message is never edited or deleted."""

    query = models.ForeignKey(Query, on_delete=models.CASCADE, related_name="messages")
    author = models.CharField(max_length=10, choices=AUTHOR_CHOICES)
    body = models.TextField()
    # The staff user who wrote an OWNER message. Null for a customer's message (the customer is
    # on the query itself) and for anything written by the system.
    author_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="+")
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.query_id} {self.author} {self.created_at:%Y-%m-%d %H:%M}"


class QueryPhoto(models.Model):
    """
    A picture attached to a message: at most SUPPORT_MAX_PHOTOS_PER_MESSAGE of them.

    The count, the file type and the size are checked in `support.services` before anything is
    stored, so a refused upload writes neither a row nor a file.
    """

    message = models.ForeignKey(QueryMessage, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to=support_photo_path)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"photo for message {self.message_id}"
