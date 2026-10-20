"""Invitation critical tests (docs/testing.md → Invitations / check-in)."""

import pytest
from django.contrib.auth.models import User

from conftest import run_concurrently
from core.models import OutboxEmail
from invitations import services
from invitations.models import Invitation

pytestmark = pytest.mark.django_db


@pytest.fixture
def door_user(db):
    return User.objects.create_user("door1", password="x", is_staff=True)


def make_invitation(status=Invitation.Status.SENT, **kwargs):
    defaults = dict(guest_name="ضيف", contact_email="vip@example.com")
    defaults.update(kwargs)
    return Invitation.objects.create(status=status, **defaults)


@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
def test_checkin_single_use_concurrent(door_user):
    invitation = make_invitation()
    results = run_concurrently(
        lambda: services.check_in(invitation.token, door_user),
        lambda: services.check_in(invitation.token, door_user),
    )
    outcomes = sorted(r[0] for r, exc in results if exc is None)
    assert outcomes == [services.CheckInResult.ALREADY, services.CheckInResult.OK]
    invitation.refresh_from_db()
    assert invitation.status == Invitation.Status.CHECKED_IN


def test_checkin_requires_sent_status(door_user):
    for status in (
        Invitation.Status.CREATED,
        Invitation.Status.REVOKED,
        Invitation.Status.CHECKED_IN,
    ):
        invitation = make_invitation(status=status)
        result, _ = services.check_in(invitation.token, door_user)
        expected = (
            services.CheckInResult.ALREADY
            if status == Invitation.Status.CHECKED_IN
            else services.CheckInResult.INVALID
        )
        assert result == expected


def test_invite_page_uniform_404(client, db):
    revoked = make_invitation(status=Invitation.Status.REVOKED)
    r_unknown = client.get("/invite/totally-unknown-token-000/")
    r_revoked = client.get(f"/invite/{revoked.token}/")
    assert r_unknown.status_code == r_revoked.status_code == 404
    assert r_unknown.content == r_revoked.content


def test_invitation_mark_sent_queues_outbox(admin_user):
    from django.contrib.admin.sites import site

    from invitations.admin import InvitationAdmin

    invitation = make_invitation(status=Invitation.Status.CREATED)
    model_admin = InvitationAdmin(Invitation, site)

    class Req:
        user = admin_user
        _messages = None

    model_admin.message_user = lambda *a, **k: None
    model_admin.mark_sent(Req(), Invitation.objects.all())
    invitation.refresh_from_db()
    assert invitation.status == Invitation.Status.SENT
    email = OutboxEmail.objects.get()
    assert invitation.token in email.body_text
