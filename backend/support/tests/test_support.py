"""
Phase F tests (Ayura): customer support queries.

A customer reports a problem, optionally with photos; the owner answers from the admin area.
What is proven here is mostly about ACCESS and about what is refused:

  * a customer can never read another customer's thread (403);
  * a guest's signed link opens its own thread and nothing else, and expires;
  * a file that is not really a picture is refused, and nothing is stored;
  * an owner's reply marks the thread ANSWERED and the customer sees it.

Every test here fails before Phase F: the `support` app, its models, services, links and
endpoints did not exist, and `support/tests` was not in pytest.ini's testpaths.
"""

import io
import json
from datetime import timedelta
from unittest import mock

import pytest
from django.core import signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from core.models import AuditLog
from support import links
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
from support.services import SupportError, add_owner_message, check_photos, open_query

API = "/api/v1/"


# --------------------------------------------------------------------------- helpers

def a_photo(name="leak.jpg", size=(40, 40), fmt="JPEG"):
    """A real picture, made with Pillow, so a passing upload test proves a real image passed."""
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", size, (200, 180, 140)).save(buffer, format=fmt)
    buffer.seek(0)
    content_type = "image/png" if fmt == "PNG" else "image/jpeg"
    return SimpleUploadedFile(name, buffer.read(), content_type=content_type)


def not_a_photo(name="invoice.jpg"):
    """A PDF wearing a .jpg name and an image content type: the shape of a real attack."""
    return SimpleUploadedFile(name, b"%PDF-1.4\n1 0 obj\n<< >>\nendobj\ntrailer\n%%EOF\n",
                              content_type="image/jpeg")


def open_one(client, **extra):
    payload = {"subject": "Leaking bottle", "body": "The serum arrived leaking.",
               "email": "asha@example.com"}
    payload.update(extra)
    return client.post(f"{API}support/queries/", payload)


@pytest.fixture
def query(db):
    """A guest's open query with one customer message."""
    created, _message = open_query("Leaking bottle", "The serum arrived leaking.", "asha@example.com")
    return created


@pytest.fixture
def order_for(db, make_order):
    """order_for(user=None, email=...) -> an order a query can be attached to."""

    def _make(buyer=None, email="asha@example.com"):
        order = make_order(buyer=buyer)
        order.email = email
        order.save()
        return order

    return _make


# --------------------------------------------------------------------------- opening a thread

@pytest.mark.django_db
def test_a_guest_opens_a_thread_and_is_given_its_own_link(api):
    response = open_one(api)
    assert response.status_code == 201
    body = response.json()

    assert body["status"] == STATUS_OPEN
    assert body["subject"] == "Leaking bottle"
    assert len(body["messages"]) == 1
    assert body["messages"][0]["author"] == AUTHOR_CUSTOMER
    assert body["messages"][0]["body"] == "The serum arrived leaking."
    # A guest has no account to sign in to, so the link is how they come back. The reference is
    # inside the signed token, not spelled out in the URL.
    assert body["link"].startswith("http")
    assert "/support/thread?token=" in body["link"]
    token = body["link"].split("token=")[1]
    assert links.read_token(token).ref == body["ref"]

    query = Query.objects.get(ref=body["ref"])
    assert query.user_id is None
    assert query.email == "asha@example.com"
    assert query.owner_unread is True            # it lands in the owner's inbox
    assert query.customer_unread is False


@pytest.mark.django_db
def test_a_signed_in_customer_gets_a_thread_on_their_account_and_no_link(auth, customer):
    response = open_one(auth(customer), email="")
    assert response.status_code == 201
    body = response.json()

    query = Query.objects.get(ref=body["ref"])
    assert query.user_id == customer.pk
    assert query.email == customer.email.lower()  # the account's address, not one they retyped
    assert "link" not in body                     # they sign in instead


@pytest.mark.django_db
def test_a_thread_can_be_about_an_order(api, order_for):
    order = order_for()
    response = open_one(api, order_oid=order.oid)
    assert response.status_code == 201
    assert response.json()["order_oid"] == order.oid
    query = Query.objects.get(ref=response.json()["ref"])
    assert query.order_id == order.pk
    # The phone comes off the order when the customer did not retype it.
    assert query.phone_e164 == "+919876543210"


@pytest.mark.django_db
def test_a_thread_cannot_be_attached_to_someone_elses_order(auth, customer, other_customer, order_for):
    order = order_for(buyer=other_customer)
    response = open_one(auth(customer), order_oid=order.oid)
    assert response.status_code == 403
    assert Query.objects.count() == 0


@pytest.mark.django_db
def test_an_unknown_order_is_refused_and_nothing_is_created(api):
    response = open_one(api, order_oid="not-an-order")
    assert response.status_code == 400
    assert "cannot find that order" in response.json()["message"]
    assert Query.objects.count() == 0


@pytest.mark.django_db
@pytest.mark.parametrize("missing,expected", [
    ({"subject": ""}, "subject"),
    ({"body": "   "}, "what happened"),
    ({"email": ""}, "email address"),
])
def test_an_incomplete_message_is_refused_with_a_reason(api, missing, expected):
    response = open_one(api, **missing)
    assert response.status_code == 400
    assert expected in response.json()["message"]
    assert Query.objects.count() == 0


@pytest.mark.django_db
def test_opening_a_thread_is_audited(api, customer, auth):
    open_one(auth(customer), email="")
    row = AuditLog.objects.filter(action="support.query_opened").latest("id")
    assert row.after["status"] == STATUS_OPEN
    assert row.actor_id == customer.pk


# --------------------------------------------------------------------------- photos

@pytest.mark.django_db
def test_photos_are_stored_with_the_message(api):
    response = api.post(f"{API}support/queries/", {
        "subject": "Leaking bottle", "body": "Photos attached.", "email": "asha@example.com",
        "photos": [a_photo("one.jpg"), a_photo("two.png", fmt="PNG")],
    }, format="multipart")
    assert response.status_code == 201
    photos = response.json()["messages"][0]["photos"]
    assert len(photos) == 2
    assert all(photo["url"] for photo in photos)
    assert QueryPhoto.objects.count() == 2


@pytest.mark.django_db
def test_a_file_that_is_not_an_image_is_refused_and_nothing_is_stored(api):
    response = api.post(f"{API}support/queries/", {
        "subject": "Leaking bottle", "body": "Here is my invoice.", "email": "asha@example.com",
        "photos": [not_a_photo()],
    }, format="multipart")
    assert response.status_code == 400
    assert "not a photo" in response.json()["message"]
    # The whole upload is refused: no thread, no message, no photo row.
    assert Query.objects.count() == 0
    assert QueryMessage.objects.count() == 0
    assert QueryPhoto.objects.count() == 0


@pytest.mark.django_db
def test_one_bad_photo_refuses_the_whole_message(api):
    response = api.post(f"{API}support/queries/", {
        "subject": "Leaking bottle", "body": "Two photos.", "email": "asha@example.com",
        "photos": [a_photo("good.jpg"), not_a_photo("bad.jpg")],
    }, format="multipart")
    assert response.status_code == 400
    assert Query.objects.count() == 0
    assert QueryPhoto.objects.count() == 0        # the good one was not kept either


@pytest.mark.django_db
def test_more_than_three_photos_are_refused(api, settings):
    assert settings.SUPPORT_MAX_PHOTOS_PER_MESSAGE == 3
    response = api.post(f"{API}support/queries/", {
        "subject": "Leaking bottle", "body": "Lots of photos.", "email": "asha@example.com",
        "photos": [a_photo(f"{n}.jpg") for n in range(4)],
    }, format="multipart")
    assert response.status_code == 400
    assert "at most 3 photos" in response.json()["message"]
    assert Query.objects.count() == 0


@pytest.mark.django_db
def test_a_photo_over_the_size_limit_is_refused(settings):
    settings.SUPPORT_PHOTO_MAX_MB = 1
    big = a_photo("huge.jpg")
    big.size = 2 * 1024 * 1024                     # as the upload handler would report it
    with pytest.raises(SupportError) as exc:
        check_photos([big])
    assert "under 1 MB" in str(exc.value)


@pytest.mark.django_db
def test_an_empty_file_is_refused():
    empty = SimpleUploadedFile("nothing.jpg", b"", content_type="image/jpeg")
    with pytest.raises(SupportError) as exc:
        check_photos([empty])
    assert "empty" in str(exc.value)


def test_the_shipped_photo_and_link_limits(shipped_setting):
    """
    The limits a fresh install runs with, read in a clean interpreter with NO .env loaded, so
    nobody's own `backend/.env` can hide a change to the shipped defaults (see the
    `shipped_setting` fixture in conftest.py).
    """
    assert shipped_setting("SUPPORT_MAX_PHOTOS_PER_MESSAGE") == "3"
    assert shipped_setting("SUPPORT_PHOTO_MAX_MB") == "5"
    assert shipped_setting("SUPPORT_LINK_HOURS") == "720"
    # Blank by default: a fresh install emails nobody when a query comes in (F16).
    assert shipped_setting("SUPPORT_NOTIFY_EMAILS") == "[]"
    # And the support throttle really is configured, at its documented rate (F18).
    assert shipped_setting("REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']['support']") == "20/min"


# --------------------------------------------------------------------------- who may read a thread

@pytest.mark.django_db
def test_a_customer_cannot_read_another_customers_thread(auth, customer, other_customer):
    mine = open_query("Mine", "My problem.", customer.email, user=customer)[0]

    assert auth(customer).get(f"{API}support/queries/{mine.ref}/").status_code == 200
    stranger = auth(other_customer).get(f"{API}support/queries/{mine.ref}/")
    assert stranger.status_code == 403
    assert "do not have access" in stranger.json()["message"]


@pytest.mark.django_db
def test_a_customer_cannot_write_on_another_customers_thread(auth, customer, other_customer):
    mine = open_query("Mine", "My problem.", customer.email, user=customer)[0]
    response = auth(other_customer).post(f"{API}support/queries/{mine.ref}/", {"body": "me too"})
    assert response.status_code == 403
    assert mine.messages.count() == 1


@pytest.mark.django_db
def test_the_reference_alone_opens_nothing(api, query):
    """The ref is read out over the phone and printed in emails: it is an identifier, not a key."""
    response = api.get(f"{API}support/queries/{query.ref}/")
    assert response.status_code == 403


@pytest.mark.django_db
def test_a_missing_thread_and_someone_elses_thread_answer_alike(api, customer):
    """Probing must not reveal which references exist."""
    mine = open_query("Mine", "My problem.", customer.email, user=customer)[0]
    missing = api.get(f"{API}support/queries/zzzzzzzzzz/")
    existing = api.get(f"{API}support/queries/{mine.ref}/")
    assert missing.status_code == existing.status_code == 403
    assert missing.json() == existing.json()


@pytest.mark.django_db
def test_staff_may_read_any_thread(auth, staff, query):
    assert auth(staff).get(f"{API}support/queries/{query.ref}/").status_code == 200


@pytest.mark.django_db
def test_a_guest_who_later_creates_an_account_keeps_their_threads(auth, customer):
    """A guest thread opened with the account's email belongs to that account (the G3 pattern)."""
    guest = open_query("Before the account", "Opened as a guest.", customer.email)[0]
    assert guest.user_id is None

    mine = auth(customer).get(f"{API}support/queries/mine/").json()
    assert [row["ref"] for row in mine["queries"]] == [guest.ref]
    assert auth(customer).get(f"{API}support/queries/{guest.ref}/").status_code == 200


@pytest.mark.django_db
def test_my_threads_lists_only_my_own(auth, customer, other_customer):
    mine = open_query("Mine", "x", customer.email, user=customer)[0]
    open_query("Theirs", "y", other_customer.email, user=other_customer)

    body = auth(customer).get(f"{API}support/queries/mine/").json()
    assert [row["ref"] for row in body["queries"]] == [mine.ref]


@pytest.mark.django_db
def test_my_threads_needs_an_account(api):
    assert api.get(f"{API}support/queries/mine/").status_code in (401, 403)


# --------------------------------------------------------------------------- the guest link

@pytest.mark.django_db
def test_a_guest_link_opens_its_own_thread(api, query):
    token = links.make_token(query)
    response = api.get(f"{API}support/queries/{query.ref}/?token={token}")
    assert response.status_code == 200
    assert response.json()["ref"] == query.ref


@pytest.mark.django_db
def test_a_guest_link_opens_no_other_thread(api, query):
    other = open_query("Someone else", "Their problem.", "other@example.com")[0]
    token = links.make_token(query)

    response = api.get(f"{API}support/queries/{other.ref}/?token={token}")
    assert response.status_code == 403
    assert "not valid for that conversation" in response.json()["message"]


@pytest.mark.django_db
def test_a_guest_link_expires(api, query, settings):
    settings.SUPPORT_LINK_HOURS = 720
    token = links.make_token(query)
    # Sign the same payload 31 days ago: the signature is good, the age is not.
    old = timezone.now() - timedelta(days=31)
    with mock.patch.object(signing.TimestampSigner, "timestamp", return_value=signing.b62_encode(int(old.timestamp()))):
        expired = links.make_token(query)

    assert api.get(f"{API}support/queries/{query.ref}/?token={token}").status_code == 200
    response = api.get(f"{API}support/queries/{query.ref}/?token={expired}")
    assert response.status_code == 403
    assert "expired" in response.json()["message"]


@pytest.mark.django_db
def test_a_tampered_link_is_refused(api, query):
    token = links.make_token(query)
    response = api.get(f"{API}support/queries/{query.ref}/?token={token[:-2]}xx")
    assert response.status_code == 403
    assert "not valid" in response.json()["message"]


@pytest.mark.django_db
def test_a_guest_can_reply_on_their_own_link(api, query):
    token = links.make_token(query)
    response = api.post(f"{API}support/queries/{query.ref}/", {"body": "It is still leaking.", "token": token})
    assert response.status_code == 201
    assert [m["body"] for m in response.json()["messages"]][-1] == "It is still leaking."
    assert query.messages.count() == 2


@pytest.mark.django_db
def test_a_guest_finds_their_thread_again_with_the_order_number_and_email(api, order_for):
    order = order_for(email="asha@example.com")
    opened = open_query("Leaking", "x", "asha@example.com", order=order)[0]

    response = api.post(f"{API}support/find/", {"order_oid": order.oid, "email": "ASHA@example.com"})
    assert response.status_code == 200
    assert response.json()["ref"] == opened.ref
    assert "token=" in response.json()["link"]


@pytest.mark.django_db
def test_finding_a_thread_needs_the_right_email_and_says_nothing_either_way(api, order_for):
    order = order_for(email="asha@example.com")
    open_query("Leaking", "x", "asha@example.com", order=order)[0]

    wrong_email = api.post(f"{API}support/find/", {"order_oid": order.oid, "email": "someone@else.com"})
    wrong_order = api.post(f"{API}support/find/", {"order_oid": "nope", "email": "asha@example.com"})
    assert wrong_email.status_code == wrong_order.status_code == 404
    # The same answer either way: this cannot be used to test whether an address shops here.
    assert wrong_email.json() == wrong_order.json()


# --------------------------------------------------------------------------- the owner answers

@pytest.mark.django_db
def test_an_owner_reply_marks_the_thread_answered_and_the_customer_sees_it(auth, staff, customer):
    mine = open_query("Leaking", "The serum arrived leaking.", customer.email, user=customer)[0]

    reply = auth(staff).post(f"{API}owner/support/{mine.ref}/",
                             {"body": "So sorry. We are sending a replacement today."})
    assert reply.status_code == 201
    assert reply.json()["status"] == STATUS_ANSWERED

    mine.refresh_from_db()
    assert mine.status == STATUS_ANSWERED
    assert mine.customer_unread is True
    assert mine.owner_unread is False

    seen = auth(customer).get(f"{API}support/queries/{mine.ref}/").json()
    assert seen["status"] == STATUS_ANSWERED
    assert seen["messages"][-1]["author"] == AUTHOR_OWNER
    assert "sending a replacement" in seen["messages"][-1]["body"]
    # Reading it clears the customer's badge.
    mine.refresh_from_db()
    assert mine.customer_unread is False


@pytest.mark.django_db
def test_an_owner_reply_records_who_answered_and_is_audited(auth, staff, query):
    auth(staff).post(f"{API}owner/support/{query.ref}/", {"body": "On its way."})
    message = QueryMessage.objects.filter(query=query, author=AUTHOR_OWNER).latest("id")
    assert message.author_user_id == staff.pk
    row = AuditLog.objects.filter(action="support.owner_replied").latest("id")
    assert row.actor_id == staff.pk
    assert row.before["status"] == STATUS_OPEN
    assert row.after["status"] == STATUS_ANSWERED


@pytest.mark.django_db
def test_the_owner_can_close_as_she_replies(auth, staff, query):
    response = auth(staff).post(f"{API}owner/support/{query.ref}/", {"body": "Replacement delivered.", "close": True})
    assert response.status_code == 201
    assert response.json()["status"] == STATUS_CLOSED
    query.refresh_from_db()
    assert query.status == STATUS_CLOSED
    assert query.closed_at is not None


@pytest.mark.django_db
def test_a_customer_writing_back_reopens_a_closed_thread(auth, staff, customer):
    mine = open_query("Leaking", "x", customer.email, user=customer)[0]
    auth(staff).post(f"{API}owner/support/{mine.ref}/", {"body": "Sorted, I hope.", "close": True})
    mine.refresh_from_db()
    assert mine.status == STATUS_CLOSED

    again = auth(customer).post(f"{API}support/queries/{mine.ref}/", {"body": "It is still leaking."})
    assert again.status_code == 201
    assert again.json()["status"] == STATUS_OPEN

    mine.refresh_from_db()
    assert mine.status == STATUS_OPEN
    assert mine.owner_unread is True              # it is back in the owner's inbox
    assert mine.closed_at is None
    row = AuditLog.objects.filter(action="support.customer_replied").latest("id")
    assert "reopened" in row.reason


@pytest.mark.django_db
def test_the_owner_closes_and_reopens_without_replying(auth, staff, query):
    closed = auth(staff).post(f"{API}owner/support/{query.ref}/close/", {"reason": "duplicate of another query"})
    assert closed.status_code == 200
    assert closed.json()["status"] == STATUS_CLOSED
    assert AuditLog.objects.filter(action="support.closed").latest("id").reason == "duplicate of another query"
    # Closing an already-closed thread changes nothing and writes no second audit row.
    before = AuditLog.objects.filter(action="support.closed").count()
    auth(staff).post(f"{API}owner/support/{query.ref}/close/", {})
    assert AuditLog.objects.filter(action="support.closed").count() == before

    reopened = auth(staff).post(f"{API}owner/support/{query.ref}/close/", {"action": "reopen"})
    assert reopened.json()["status"] == STATUS_OPEN
    assert AuditLog.objects.filter(action="support.reopened").exists()


@pytest.mark.django_db
def test_an_empty_owner_reply_is_refused(auth, staff, query):
    response = auth(staff).post(f"{API}owner/support/{query.ref}/", {"body": "   "})
    assert response.status_code == 400
    assert query.messages.filter(author=AUTHOR_OWNER).count() == 0


# --------------------------------------------------------------------------- the owner's inbox

@pytest.mark.django_db
def test_the_inbox_counts_what_needs_answering(auth, staff, customer):
    waiting = open_query("Waiting", "x", customer.email, user=customer)[0]
    answered = open_query("Answered", "y", customer.email, user=customer)[0]
    add_owner_message(answered, "Replied.", actor=staff)
    done = open_query("Done", "z", customer.email, user=customer)[0]
    add_owner_message(done, "Replied and closed.", actor=staff, close=True)

    body = auth(staff).get(f"{API}owner/support/").json()
    assert body["counts"] == {"open": 1, "answered": 1, "closed": 1, "unread": 1}
    # The default view is what still needs her: the closed one is out of the way.
    refs = [row["ref"] for row in body["queries"]]
    assert waiting.ref in refs and answered.ref in refs and done.ref not in refs
    # Unread first.
    assert refs[0] == waiting.ref

    closed_view = auth(staff).get(f"{API}owner/support/?status=closed").json()
    assert [row["ref"] for row in closed_view["queries"]] == [done.ref]


@pytest.mark.django_db
def test_opening_a_thread_in_the_admin_area_clears_its_unread_flag(auth, staff, query):
    assert query.owner_unread is True
    assert auth(staff).get(f"{API}owner/support/{query.ref}/").status_code == 200
    query.refresh_from_db()
    assert query.owner_unread is False
    # A staff read through the customer endpoint does NOT clear the customer's badge.
    assert auth(staff).get(f"{API}owner/support/").json()["counts"]["unread"] == 0


@pytest.mark.django_db
def test_the_inbox_shows_who_is_asking_and_about_which_order(auth, staff, order_for, customer):
    order = order_for(buyer=customer, email=customer.email)
    opened = open_query("Leaking", "x", customer.email, order=order, user=customer)[0]

    row = next(r for r in auth(staff).get(f"{API}owner/support/").json()["queries"] if r["ref"] == opened.ref)
    assert row["order_oid"] == order.oid
    assert row["email"] == customer.email.lower()
    assert row["has_account"] is True
    assert row["message_count"] == 1


@pytest.mark.django_db
def test_the_support_inbox_is_closed_to_customers(api, auth, customer, query):
    assert api.get(f"{API}owner/support/").status_code in (401, 403)
    assert auth(customer).get(f"{API}owner/support/").status_code == 403
    assert auth(customer).get(f"{API}owner/support/{query.ref}/").status_code == 403
    assert auth(customer).post(f"{API}owner/support/{query.ref}/", {"body": "hi"}).status_code == 403
    assert auth(customer).post(f"{API}owner/support/{query.ref}/close/", {}).status_code == 403
    # None of that wrote anything.
    assert query.messages.count() == 1


# --------------------------------------------------------------------------- messages are a record

@pytest.mark.django_db
def test_messages_are_append_only(query):
    from core.models import AppendOnlyError

    message = query.messages.first()
    message.body = "something else"
    with pytest.raises(AppendOnlyError):
        message.save()
    with pytest.raises(AppendOnlyError):
        QueryMessage.objects.all().delete()


# --------------------------------------------------------------------------- email is a courtesy

@pytest.mark.django_db
def test_opening_a_thread_queues_one_acknowledgement(api):
    from core.models import Job

    body = open_one(api).json()
    jobs = Job.objects.filter(name="support.send_customer_email")
    assert jobs.count() == 1
    assert jobs.first().payload["kind"] == "ack"
    assert jobs.first().dedupe_key.endswith(str(Query.objects.get(ref=body["ref"]).pk))


@pytest.mark.django_db
def test_each_owner_reply_is_announced_exactly_once(auth, staff, query):
    from core.models import Job

    auth(staff).post(f"{API}owner/support/{query.ref}/", {"body": "First reply."})
    auth(staff).post(f"{API}owner/support/{query.ref}/", {"body": "Second reply."})
    notices = Job.objects.filter(name="support.send_customer_email", payload__kind="reply")
    assert notices.count() == 2
    assert len({job.dedupe_key for job in notices}) == 2


@pytest.mark.django_db
def test_the_owner_is_told_only_when_an_address_is_configured(api, settings):
    from core.models import Job

    assert settings.SUPPORT_NOTIFY_EMAILS == []
    open_one(api)
    assert Job.objects.filter(name="support.send_owner_notice").count() == 0

    settings.SUPPORT_NOTIFY_EMAILS = ["owner@example.com"]
    open_one(api, subject="Another one")
    assert Job.objects.filter(name="support.send_owner_notice").count() == 1


@pytest.mark.django_db
def test_the_thread_works_with_no_email_provider_at_all(api, auth, staff, settings):
    """
    The acknowledgement job failing must never cost the customer their thread.

    The email backend is replaced with one that always raises, the queued jobs are run, and the
    conversation is still there and still answerable.
    """
    from core.jobs import run_due_jobs

    settings.EMAIL_BACKEND = "django.core.mail.backends.dummy.EmailBackend"
    body = open_one(api).json()
    with mock.patch("support.emails._send", side_effect=OSError("no mail server")):
        ok, failed = run_due_jobs()
    assert failed >= 1 and ok == 0

    query = Query.objects.get(ref=body["ref"])
    assert query.status == STATUS_OPEN
    assert query.messages.count() == 1
    assert auth(staff).post(f"{API}owner/support/{query.ref}/", {"body": "We can still answer."}).status_code == 201


@pytest.mark.django_db
def test_the_customer_email_carries_the_thread_link_and_no_message_text(query):
    from support.emails import KIND_ACK, build_customer_email

    subject, context = build_customer_email(query, KIND_ACK)
    assert query.ref in subject
    assert context["reference"] == query.ref
    # The link carries the thread in a signed token, so it opens this conversation and no other.
    assert links.read_token(context["action_url"].split("token=")[1]).pk == query.pk
    assert context["subject_line"] == query.subject
    # The body of what the customer wrote stays in the admin area, not in an email trail.
    assert "arrived leaking" not in json.dumps(context)


# --------------------------------------------------------------------------- the throttle

@pytest.mark.django_db
def test_every_support_endpoint_declares_the_support_throttle_scope():
    """
    The scope is what the rate is configured against, so each view must name it: a view that
    forgot would fall back to the far looser anonymous limit.
    """
    from django.conf import settings as django_settings

    from support import owner_views, views

    assert django_settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["support"] == "20/min"
    for view in (views.SupportQueryCreateView, views.SupportMyQueriesView, views.SupportThreadView,
                 views.SupportFindView, views.SupportOrderQueriesView):
        assert view.throttle_scope == "support", view.__name__
    # The owner's own screens are staff-only and sit under the ordinary signed-in user limit.
    assert not hasattr(owner_views.OwnerSupportListView, "throttle_scope")


@pytest.mark.django_db
def test_opening_threads_is_rate_limited(api):
    """
    The limit really bites. DRF reads the configured rates onto the throttle class at import
    time, so the rate is patched there rather than in settings, which that class would ignore.
    """
    from rest_framework.throttling import ScopedRateThrottle

    with mock.patch.dict(ScopedRateThrottle.THROTTLE_RATES, {"support": "3/min"}, clear=False):
        codes = [open_one(api, subject=f"Problem {n}").status_code for n in range(5)]

    assert codes[:3] == [201, 201, 201]
    assert codes[3:] == [429, 429]
    # The refused requests created nothing.
    assert Query.objects.count() == 3


# --------------------------------------------------------------------------- the order's own threads

@pytest.mark.django_db
def test_an_order_lists_the_threads_opened_about_it(auth, customer, order_for):
    order = order_for(buyer=customer, email=customer.email)
    opened = open_query("Leaking", "x", customer.email, order=order, user=customer)[0]
    open_query("Another order", "y", customer.email, user=customer)

    body = auth(customer).get(f"{API}support/orders/{order.oid}/queries/").json()
    assert [row["ref"] for row in body["queries"]] == [opened.ref]


@pytest.mark.django_db
def test_another_customer_cannot_list_an_orders_threads(auth, other_customer, customer, order_for):
    order = order_for(buyer=customer, email=customer.email)
    open_query("Leaking", "x", customer.email, order=order, user=customer)
    assert auth(other_customer).get(f"{API}support/orders/{order.oid}/queries/").status_code == 403


# --------------------------------------------------------------------------- grievance officer (L4)

@pytest.mark.django_db
def test_the_grievance_block_is_empty_until_the_owner_fills_it_in(api, config_settings):
    """
    Phase F publishes no legal wording. Every grievance field ships blank, so the storefront has
    nothing to show until the owner types her own (ROADMAP L4).
    """
    body = api.get(f"{API}addon/").json()
    row = body[0] if isinstance(body, list) else body
    for field in ("grievance_officer_name", "grievance_officer_designation", "grievance_officer_email",
                  "grievance_officer_phone", "grievance_officer_address"):
        assert row[field] == ""
    assert row["grievance_response_days"] == 0


@pytest.mark.django_db
def test_the_owner_sets_the_grievance_details_and_the_change_is_audited(auth, staff, config_settings):
    client = auth(staff)
    response = client.patch(f"{API}owner/settings/", {
        "grievance_officer_name": "Manmeet Singh",
        "grievance_officer_designation": "Proprietor",
        "grievance_officer_email": "grievance@example.com",
        "grievance_officer_phone": "+91 98765 43210",
        "grievance_response_days": "2",
    })
    assert response.status_code == 200
    assert response.json()["grievance_officer_name"] == "Manmeet Singh"
    assert response.json()["grievance_response_days"] == 2

    row = AuditLog.objects.filter(action="settings.updated").latest("id")
    assert row.before["grievance_officer_name"] == ""
    assert row.after["grievance_officer_name"] == "Manmeet Singh"
    assert row.actor_id == staff.pk

    # It is public once set: that is the point of publishing it.
    public = api_row(client, f"{API}addon/")
    assert public["grievance_officer_email"] == "grievance@example.com"


def api_row(client, url):
    body = client.get(url).json()
    return body[0] if isinstance(body, list) else body


@pytest.mark.django_db
def test_a_customer_cannot_set_the_grievance_details(auth, customer, config_settings):
    response = auth(customer).patch(f"{API}owner/settings/", {"grievance_officer_name": "Someone Else"})
    assert response.status_code == 403
    config_settings.refresh_from_db()
    assert config_settings.grievance_officer_name == ""
