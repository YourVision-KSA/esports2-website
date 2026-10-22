"""Door-staff check-in page (/staff/checkin/): look up first (no write), then confirm.
Single-use atomicity is covered in test_invitations.py; these tests cover the page flow."""

import pytest
from django.contrib.auth.models import Group, User
from django.core.management import call_command

from core.content import CONTENT
from core.models import AuditLog
from invitations.models import Invitation

pytestmark = pytest.mark.django_db


@pytest.fixture
def door_client(client):
    call_command("setup_roles")
    user = User.objects.create_user("door1", password="x", is_staff=True)
    user.groups.add(Group.objects.get(name="door"))
    client.login(username="door1", password="x")
    return client


def make_invitation(status=Invitation.Status.SENT, **kwargs):
    defaults = dict(guest_name="د. سارة القحطاني", organization="الجامعة العربية المفتوحة")
    defaults.update(kwargs)
    return Invitation.objects.create(status=status, **defaults)


def test_lookup_shows_guest_and_writes_nothing(door_client):
    inv = make_invitation()
    body = door_client.post(
        "/staff/checkin/", {"action": "lookup", "token": inv.token}
    ).content.decode()
    inv.refresh_from_db()
    assert inv.status == Invitation.Status.SENT  # ID check happens before any write
    assert not AuditLog.objects.filter(action="invitation.checkin").exists()
    assert inv.guest_name in body and CONTENT["STAFF_VERIFY_ID"] in body
    assert CONTENT["STAFF_CONFIRM_CHECKIN"] in body


def test_lookup_accepts_full_invite_url(door_client):
    inv = make_invitation()
    body = door_client.post(
        "/staff/checkin/", {"action": "lookup", "token": f"https://x.sa/invite/{inv.token}/"}
    ).content.decode()
    assert inv.guest_name in body and CONTENT["STAFF_CONFIRM_CHECKIN"] in body


def test_confirm_checks_in_once(door_client):
    inv = make_invitation()
    first = door_client.post("/staff/checkin/", {"action": "confirm", "token": inv.token})
    assert CONTENT["CHECKIN_OK"] in first.content.decode()
    inv.refresh_from_db()
    assert inv.status == Invitation.Status.CHECKED_IN
    second = door_client.post("/staff/checkin/", {"action": "confirm", "token": inv.token})
    body = second.content.decode()
    assert "guest-already" in body and "door1" in body  # who checked them in


@pytest.mark.parametrize("status", [Invitation.Status.CREATED, Invitation.Status.REVOKED])
def test_unsent_or_revoked_invitations_are_invalid(door_client, status):
    inv = make_invitation(status=status)
    body = door_client.post(
        "/staff/checkin/", {"action": "lookup", "token": inv.token}
    ).content.decode()
    assert CONTENT["CHECKIN_INVALID"] in body
    assert inv.guest_name not in body  # nothing about the guest is shown


def test_unknown_token_is_invalid(door_client):
    body = door_client.post(
        "/staff/checkin/", {"action": "lookup", "token": "nope"}
    ).content.decode()
    assert CONTENT["CHECKIN_INVALID"] in body


def test_success_is_not_styled_as_an_error(door_client):
    inv = make_invitation()
    body = door_client.post(
        "/staff/checkin/", {"action": "confirm", "token": inv.token}
    ).content.decode()
    assert "guest-ok" in body and 'class="error"' not in body


def test_search_shows_arabic_status_labels(door_client):
    make_invitation()
    make_invitation(guest_name="أ. فهد الدوسري", status=Invitation.Status.CHECKED_IN)
    body = door_client.get("/staff/checkin/", {"q": "د"}).content.decode()
    assert CONTENT["INVITE_STATUS"]["sent"] in body
    assert CONTENT["INVITE_STATUS"]["checked_in"] in body
    assert ">Sent<" not in body


def test_requires_door_permission(client):
    User.objects.create_user("nobody", password="x", is_staff=True)
    client.login(username="nobody", password="x")
    assert client.get("/staff/checkin/").status_code == 403


def test_scanner_markup_and_no_autostart_while_a_guest_awaits_confirmation(door_client):
    """The camera scanner (frontend/src/scanner.js) fills the lookup form; it must not
    auto-restart on the page that is waiting for the ID check + confirm."""
    body = door_client.get("/staff/checkin/").content.decode()
    assert "data-scanner" in body and 'id="lookup-form"' in body
    assert 'data-autostart="1"' in body  # empty page: carry on scanning
    assert CONTENT["STAFF_SCAN_START"] in body

    inv = make_invitation()
    body = door_client.post(
        "/staff/checkin/", {"action": "lookup", "token": inv.token}
    ).content.decode()
    assert 'data-autostart="0"' in body

    body = door_client.post(
        "/staff/checkin/", {"action": "confirm", "token": inv.token}
    ).content.decode()
    assert 'data-autostart="1"' in body  # next guest
