"""
Guest links to a support thread (Phase F, Ayura).

A guest has no account, so there is nothing to sign in to. They reach their own thread with a
signed, time-limited token (django.core.signing), exactly as a guest reaches the "create an
account" flow in G3: nothing is stored, the signature cannot be forged, and the link stops
working after SUPPORT_LINK_HOURS.

The token names ONE query. It opens that thread and no other, so a leaked link exposes one
conversation rather than an account.
"""

import logging

from django.conf import settings
from django.core import signing

logger = logging.getLogger(__name__)

SALT = "support.thread.v1"


class ThreadLinkError(Exception):
    """The link is invalid or has expired."""


def make_token(query):
    return signing.dumps({"ref": query.ref}, salt=SALT)


def read_token(token):
    """Return the query the token names, or raise ThreadLinkError."""
    from support.models import Query

    try:
        data = signing.loads(str(token or ""), salt=SALT, max_age=settings.SUPPORT_LINK_HOURS * 3600)
    except signing.SignatureExpired:
        raise ThreadLinkError("This link has expired. Ask for a new one from your order page.")
    except signing.BadSignature:
        raise ThreadLinkError("This link is not valid.")
    if not isinstance(data, dict) or not data.get("ref"):
        raise ThreadLinkError("This link is not valid.")
    query = Query.objects.filter(ref=data["ref"]).first()
    if query is None:
        raise ThreadLinkError("This link is not valid.")
    return query


def build_thread_link(query):
    return f"{settings.SITE_URL}/support/thread?token={make_token(query)}"
