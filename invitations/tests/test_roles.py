"""Staff role boundaries (audit 2026-11-13, finding 2 — High).

Door staff get exactly what check-in needs: /staff/checkin/ (name + organisation for the
ID check), nothing in the Django admin, no VIP contact details. Invitation state changes
happen only through audited services. Referees likewise see only what result entry needs.
"""

import pytest
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import override_settings

from conftest import fill_confirmed
from core.models import AuditLog
from invitations import services
from invitations.models import Invitation

pytestmark = pytest.mark.django_db

EMAIL, PHONE = "vip.private@example.com", "0551230000"


@pytest.fixture
def roles():
    call_command("setup_roles", stdout=open("/dev/null", "w"))


def login_as(client, role):
    user = User.objects.create_user(f"{role}1", password="x", is_staff=True)
    user.groups.add(Group.objects.get(name=role))
    client.force_login(user)
    return user


@pytest.fixture
def invitation():
    return Invitation.objects.create(
        guest_name="د. سارة",
        organization="الاتحاد",
        contact_email=EMAIL,
        contact_phone=PHONE,
        status=Invitation.Status.CHECKED_IN,
    )


# ---------------------------------------------------------------- door role


def test_door_role_has_only_the_checkin_permission(roles):
    perms = set(Group.objects.get(name="door").permissions.values_list("codename", flat=True))
    assert perms == {"checkin_invitation"}


@pytest.mark.parametrize(
    "url",
    [
        "/staff/invitations/invitation/",
        "/staff/invitations/invitation/{pk}/change/",
        "/staff/registration/player/",
        "/staff/voting/ballot/",
        "/staff/core/siteconfig/",
    ],
)
def test_door_cannot_open_admin_pages(client, roles, invitation, url):
    login_as(client, "door")
    assert client.get(url.format(pk=invitation.pk)).status_code == 403


def test_door_cannot_rearm_a_used_qr_code_in_the_admin(client, roles, invitation):
    login_as(client, "door")
    client.post(
        f"/staff/invitations/invitation/{invitation.pk}/change/",
        {"guest_name": "x", "status": "sent", "contact_email": "", "contact_phone": ""},
    )
    invitation.refresh_from_db()
    assert invitation.status == Invitation.Status.CHECKED_IN


def test_invitation_admin_stays_closed_even_if_a_group_is_misconfigured(client, invitation):
    """Defence in depth: someone later re-adds view/change_invitation to a staff group."""
    from django.contrib.auth.models import Permission

    user = User.objects.create_user("helper", password="x", is_staff=True)
    user.user_permissions.set(
        Permission.objects.filter(codename__in=["view_invitation", "change_invitation"])
    )
    client.force_login(user)
    assert client.get("/staff/invitations/invitation/").status_code == 403
    page = client.get(f"/staff/invitations/invitation/{invitation.pk}/change/")
    assert page.status_code in (302, 403) and EMAIL not in page.content.decode()


def test_door_checkin_flow_still_works_and_shows_no_contact_details(client, roles):
    door = login_as(client, "door")
    inv = Invitation.objects.create(
        guest_name="ضيف", contact_email=EMAIL, contact_phone=PHONE, status=Invitation.Status.SENT
    )
    lookup = client.post("/staff/checkin/", {"action": "lookup", "token": inv.token})
    search = client.get("/staff/checkin/", {"q": "ضيف"})
    for response in (lookup, search):
        assert response.status_code == 200
        body = response.content.decode()
        assert "ضيف" in body
        assert EMAIL not in body and PHONE not in body
    client.post("/staff/checkin/", {"action": "confirm", "token": inv.token})
    inv.refresh_from_db()
    assert inv.status == Invitation.Status.CHECKED_IN and inv.checked_in_by == door
    assert AuditLog.objects.filter(action="invitation.checkin", actor=door).exists()


def test_checkin_page_refuses_staff_without_the_checkin_permission(client, roles):
    login_as(client, "referee")
    assert client.get("/staff/checkin/").status_code == 403


# -------------------------------------------------------------- referee role


@pytest.mark.parametrize(
    "url",
    [
        "/staff/invitations/invitation/",
        "/staff/registration/player/",
        "/staff/registration/registration/",
        "/staff/voting/ballot/",
        "/staff/core/siteconfig/",
        "/staff/core/auditlog/",
    ],
)
def test_referee_cannot_open_non_bracket_admin_pages(client, roles, url):
    login_as(client, "referee")
    assert client.get(url).status_code == 403


def test_referee_results_page_works(client, roles, game):
    fill_confirmed(game, 2)
    login_as(client, "referee")
    assert client.get("/staff/results/").status_code == 200


# ----------------------------------------------------- admin: audited changes only


@pytest.fixture
def admin_client(client, django_user_model):
    django_user_model.objects.create_superuser("boss", password="x")
    client.login(username="boss", password="x")
    return client


def test_status_is_not_editable_even_for_admins(admin_client, invitation):
    admin_client.post(
        f"/staff/invitations/invitation/{invitation.pk}/change/",
        {
            "guest_name": "د. سارة",
            "organization": "الاتحاد",
            "contact_email": EMAIL,
            "contact_phone": PHONE,
            "status": "sent",
        },
    )
    invitation.refresh_from_db()
    assert invitation.status == Invitation.Status.CHECKED_IN


def test_admin_contact_edit_is_audited_without_the_contact_values(admin_client, invitation):
    admin_client.post(
        f"/staff/invitations/invitation/{invitation.pk}/change/",
        {
            "guest_name": "د. سارة",
            "organization": "الاتحاد",
            "contact_email": "new.private@example.com",
            "contact_phone": PHONE,
        },
    )
    log = AuditLog.objects.get(action="invitation.change")
    assert log.after == {"fields": ["contact_email"]}
    assert "new.private" not in str(log.after)


def test_state_changes_go_through_audited_services(django_user_model):
    boss = django_user_model.objects.create_superuser("boss2", password="x")
    inv = Invitation.objects.create(guest_name="g", contact_email=EMAIL)
    assert services.mark_sent(inv, boss).status == Invitation.Status.SENT
    assert services.check_in(inv.token, boss)[0] == services.CheckInResult.OK
    assert services.revoke(inv, boss) is None  # a used invitation cannot be revoked
    undone = services.undo_checkin(inv, boss)
    assert undone.status == Invitation.Status.SENT and undone.checked_in_by is None
    assert services.revoke(inv, boss).status == Invitation.Status.REVOKED
    assert services.undo_checkin(inv, boss) is None  # nothing to undo
    actions = list(
        AuditLog.objects.filter(model="invitations.Invitation")
        .order_by("created_at", "pk")
        .values_list("action", "before", "after")
    )
    assert actions == [
        ("invitation.sent", {"status": "created"}, {"status": "sent"}),
        ("invitation.checkin", None, None),
        ("invitation.checkin_reversed", {"status": "checked_in"}, {"status": "sent"}),
        ("invitation.revoke", {"status": "sent"}, {"status": "revoked"}),
    ]


@override_settings(REQUIRE_2FA=True)
@pytest.mark.parametrize("role,url", [("door", "/staff/checkin/"), ("referee", "/staff/results/")])
def test_staff_pages_require_a_verified_second_factor(client, roles, role, url):
    """Audit 2026-11-13: the pages must not rely on the admin login being the only way in."""
    from django_otp.plugins.otp_totp.models import TOTPDevice

    user = login_as(client, role)
    assert client.get(url).status_code == 403  # password-only session

    device = TOTPDevice.objects.create(user=user, name="default", confirmed=True)
    session = client.session
    session["otp_device_id"] = device.persistent_id  # what django_otp.login() stores
    session.save()
    assert client.get(url).status_code == 200
