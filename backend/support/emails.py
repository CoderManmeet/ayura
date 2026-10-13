"""
Support emails, sent in the background through core.jobs (Phase F, Ayura).

    queue_customer_ack(query)            "we have your message", with the link to the thread
    queue_customer_reply_notice(query)   "we have answered you", with the same link
    queue_owner_new_query_notice(query)  tells the owner a query came in

Each one is enqueued with a dedupe key, so a retried request or a double click sends one email.
The thread itself NEVER depends on any of this: a store with no email provider configured still
has a working support inbox, and the customer still has their thread and their link.

Bodies carry the subject and the thread link. A message body is never logged (CLAUDE.md §3), and
the owner notice carries no customer message text to a third-party mailbox beyond the subject.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from core.jobs import enqueue, job

logger = logging.getLogger(__name__)

CUSTOMER_JOB = "support.send_customer_email"
OWNER_JOB = "support.send_owner_notice"

KIND_ACK = "ack"
KIND_REPLY = "reply"
CUSTOMER_KINDS = (KIND_ACK, KIND_REPLY)


def queue_customer_ack(query):
    """One acknowledgement per query."""
    return enqueue(CUSTOMER_JOB, {"query_id": query.pk, "kind": KIND_ACK},
                   dedupe_key=f"support-ack:{query.pk}")


def queue_customer_reply_notice(query, message):
    """One notice per owner reply (keyed by the message, so every reply is announced once)."""
    return enqueue(CUSTOMER_JOB, {"query_id": query.pk, "kind": KIND_REPLY, "message_id": message.pk},
                   dedupe_key=f"support-reply:{message.pk}")


def queue_owner_new_query_notice(query):
    """Tell the owner. Does nothing at all unless SUPPORT_NOTIFY_EMAILS is set."""
    if not settings.SUPPORT_NOTIFY_EMAILS:
        return None, False
    return enqueue(OWNER_JOB, {"query_id": query.pk}, dedupe_key=f"support-owner-notice:{query.pk}")


def _send(to, subject, context):
    text_body = render_to_string("email/support_update.txt", context)
    html_body = render_to_string("email/support_update.html", context)
    message = EmailMultiAlternatives(subject=subject, from_email=settings.FROM_EMAIL, to=list(to), body=text_body)
    message.attach_alternative(html_body, "text/html")
    message.send()


def build_customer_email(query, kind):
    """Return (subject, context) for one email to the customer."""
    from support.links import build_thread_link

    store = settings.STORE_NAME
    order_line = f" about order {query.order.oid}" if query.order_id else ""
    if kind == KIND_ACK:
        subject = f"We have your message ({query.ref})"
        intro = (f"Thank you for writing to {store}{order_line}. We have your message and will come back to "
                 "you as soon as we can. You can read the whole conversation, and add anything you forgot, "
                 "using the link below.")
    else:
        subject = f"We have answered you ({query.ref})"
        intro = (f"We have replied to your message{order_line}. Open the conversation below to read it, and "
                 "write back on the same thread if it is not sorted out.")
    return subject, {
        "store_name": store,
        "greeting_name": query.user.full_name if query.user_id and query.user.full_name else "",
        "reference": query.ref,
        "subject_line": query.subject,
        "intro": intro,
        "action_url": build_thread_link(query),
        "action_label": "Open the conversation",
        "link_hours": settings.SUPPORT_LINK_HOURS,
        "messages": [],
    }


@job(CUSTOMER_JOB)
def send_customer_email_job(payload):
    """
    Deliver one email to the customer. Idempotent through the dedupe key on enqueue; a retry
    after a mail-server error re-sends, which is intended (the previous attempt did not go out).
    """
    from support.models import Query

    query = Query.objects.filter(pk=payload.get("query_id")).select_related("user", "order").first()
    kind = payload.get("kind")
    if query is None or kind not in CUSTOMER_KINDS or not query.email:
        return
    subject, context = build_customer_email(query, kind)
    _send([query.email], subject, context)
    logger.info("support email %s sent for query %s", kind, query.ref)


@job(OWNER_JOB)
def send_owner_notice_job(payload):
    """Tell the owner a query came in. The customer's words stay in the admin area."""
    from support.models import Query

    query = Query.objects.filter(pk=payload.get("query_id")).select_related("order").first()
    if query is None or not settings.SUPPORT_NOTIFY_EMAILS:
        return
    order_line = f" about order {query.order.oid}" if query.order_id else ""
    context = {
        "store_name": settings.STORE_NAME,
        "greeting_name": "",
        "reference": query.ref,
        "subject_line": query.subject,
        "intro": (f"A customer has sent a support query{order_line}. Open it in the admin area to read it "
                  "and reply."),
        "action_url": f"{settings.SITE_URL}/admin-area/owner/support/{query.ref}/",
        "action_label": "Open in the admin area",
        "link_hours": 0,
        "messages": [],
    }
    _send(settings.SUPPORT_NOTIFY_EMAILS, f"New support query ({query.ref})", context)
    logger.info("owner notified of support query %s", query.ref)
