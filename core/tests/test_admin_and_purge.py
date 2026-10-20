"""Audited exports and the end-of-life PII purge (docs/testing.md → Phases & misc)."""

import pytest
from django.core.management import call_command

from conftest import fill_confirmed
from core.models import AuditLog, OutboxEmail
from invitations.models import Invitation
from registration.models import Player

pytestmark = pytest.mark.django_db


def test_export_audit_logged(admin_user, game, rf):
    from django.contrib.admin.sites import site

    from registration.admin import PlayerAdmin

    fill_confirmed(game, 3)
    model_admin = PlayerAdmin(Player, site)
    request = rf.get("/")
    request.user = admin_user

    response = model_admin.get_actions(request)["export_csv"][0](
        model_admin, request, Player.objects.all()
    )
    assert response["Content-Type"].startswith("text/csv")
    log = AuditLog.objects.get(action="export.csv")
    assert log.actor == admin_user
    assert "count=3" in log.object_id


def test_export_refused_for_non_superuser(game, django_user_model, rf):
    from core.admin import export_csv_action

    fill_confirmed(game, 1)
    staff = django_user_model.objects.create_user("staff1", password="x", is_staff=True)
    request = rf.get("/")
    request.user = staff

    from django.contrib.admin.sites import site

    from registration.admin import PlayerAdmin

    model_admin = PlayerAdmin(Player, site)
    model_admin.message_user = lambda *a, **k: None
    action = export_csv_action(["id", "full_name"])
    assert action(model_admin, request, Player.objects.all()) is None  # refused
    assert not AuditLog.objects.filter(action="export.csv").exists()


def test_pii_purge_command(game):
    from bracket.draw import draw

    fill_confirmed(game, 16)
    draw(game, seed=1)
    Invitation.objects.create(guest_name="ضيف مهم", contact_email="vip@example.com")
    OutboxEmail.objects.create(to_email="x@example.com", subject="s", body_text="b")
    phones_before = set(Player.objects.values_list("phone", flat=True))

    call_command("purge_pii", "--yes")

    assert game.matches.count() == 15  # results structure kept
    assert not set(Player.objects.values_list("phone", flat=True)) & phones_before
    assert not Player.objects.exclude(email="").exists()
    invitation = Invitation.objects.get()
    assert invitation.guest_name == "purged"
    assert invitation.contact_email == ""
    assert OutboxEmail.objects.count() == 0


def test_purge_refuses_without_confirmation(game, capsys):
    fill_confirmed(game, 1)
    phone = Player.objects.get().phone
    call_command("purge_pii")
    assert Player.objects.get().phone == phone  # nothing changed
