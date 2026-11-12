"""Smaller fixes from the 2026-11-13 audit: manage-link regeneration email, sent outbox
bodies, CSV formula injection, PII purge safety, reproducible draw, repository hygiene."""

from pathlib import Path

import pytest
from django.core import mail
from django.core.management import CommandError, call_command
from django.test import override_settings

from conftest import fill_confirmed, make_player, set_phase
from core.admin import csv_safe, export_csv_action
from core.models import AuditLog, OutboxEmail
from core.outbox import send_due
from core.phases import Phase
from registration import services
from registration.models import Player, Registration, RegistrationAttempt

pytestmark = pytest.mark.django_db
ROOT = Path(__file__).resolve().parents[2]


# ------------------------------------------------------ manage link + outbox


@override_settings(SITE_BASE_URL="https://esports.example.sa")
def test_regenerated_link_email_is_absolute_and_uses_the_template(admin_client, game):
    from core.content import CONTENT

    reg = fill_confirmed(game, 1)[0]
    player = reg.player
    player.email = "p@example.com"
    player.save()
    admin_client.post(
        "/staff/registration/player/",
        {"action": "regenerate_manage_link", "_selected_action": [player.pk]},
    )
    body = OutboxEmail.objects.get().body_text
    assert "https://esports.example.sa/r/" in body
    assert CONTENT["EMAIL_MANAGE_BODY"].split("{")[0].strip() in body
    token = body.split("https://esports.example.sa/r/")[1].split("/")[0]
    assert Player.objects.get(manage_token_hash=Player.hash_token(token)) == player


def test_sent_outbox_bodies_are_blanked(game):
    OutboxEmail.objects.create(to_email="x@example.com", subject="s", body_text="/r/SECRET/")
    assert send_due() == 1
    assert mail.outbox[0].body == "/r/SECRET/"  # delivered intact
    assert OutboxEmail.objects.get().body_text == ""  # then not kept


def test_outbox_body_is_read_only_in_admin(admin_client):
    email = OutboxEmail.objects.create(to_email="x@example.com", subject="s", body_text="keep")
    admin_client.post(
        f"/staff/core/outboxemail/{email.pk}/change/",
        {"to_email": "evil@example.com", "subject": "s", "body_text": "changed"},
    )
    email.refresh_from_db()
    assert (email.to_email, email.body_text) == ("x@example.com", "keep")


# ---------------------------------------------------------------- CSV export


@pytest.mark.parametrize("value", ["=HYPERLINK(1)", "+1", "-1", "@SUM(1)", "\t=1", "\r=1"])
def test_csv_cells_cannot_start_a_formula(value):
    assert csv_safe(value) == "'" + value


def test_csv_export_neutralises_registrant_text(admin_user, game, rf):
    from django.contrib.admin.sites import site

    from registration.admin import PlayerAdmin

    make_player(1, full_name='=HYPERLINK("http://x","click")')
    request = rf.get("/")
    request.user = admin_user
    model_admin = PlayerAdmin(Player, site)
    response = export_csv_action(["full_name"])(model_admin, request, Player.objects.all())
    assert "'=HYPERLINK" in response.content.decode()


# ----------------------------------------------------------------- PII purge


def test_purge_refuses_before_archive(game):
    set_phase(Phase.EVENT)
    fill_confirmed(game, 1)
    phone = Player.objects.get().phone
    with pytest.raises(CommandError, match="not archived"):
        call_command("purge_pii", "--yes")
    assert Player.objects.get().phone == phone


def test_purge_is_safe_to_run_twice_and_removes_attempts(game):
    set_phase(Phase.ARCHIVE)
    regs = fill_confirmed(game, 3)
    services.withdraw(regs[0])
    RegistrationAttempt.objects.create(ip_hash="a", ua_hash="b", game=game, outcome="invalid")
    call_command("purge_pii", "--yes")
    # second run, rows returned in a different order — must not hit the unique columns
    Player.objects.filter(pk=regs[2].player_id).update(full_name="zzz")
    call_command("purge_pii", "--yes")
    assert set(Player.objects.values_list("phone", flat=True)) == {
        f"purged-{r.player_id}" for r in regs
    }
    assert not RegistrationAttempt.objects.exists()
    assert Registration.objects.get(pk=regs[0].pk).game_player_id == ""  # withdrawn: blanked
    assert Registration.objects.get(pk=regs[1].pk).game_player_id  # played: tag kept


# ------------------------------------------------------------------- draw seed


def test_draw_without_seed_records_a_reproducible_seed(game):
    from bracket.draw import draw

    fill_confirmed(game, 16)
    draw(game)
    seed = AuditLog.objects.get(action="bracket.draw").after["seed"]
    assert isinstance(seed, int)
    first_round = list(
        game.matches.filter(round=1).order_by("slot").values_list("player1_id", "player2_id")
    )
    game.matches.all().delete()
    draw(game, seed=seed)
    assert first_round == list(
        game.matches.filter(round=1).order_by("slot").values_list("player1_id", "player2_id")
    )


# ---------------------------------------------------------- repository hygiene


def test_deploy_only_trusts_pushes_to_this_repositorys_main():
    """Public repo: a fork PR from a branch named "main" must not trigger a deploy."""
    workflow = (ROOT / ".github/workflows/deploy.yml").read_text()
    condition = workflow.split("    if: >-", 1)[1].split("    runs-on:", 1)[0]
    for required in (
        "github.event.workflow_run.event == 'push'",
        "github.event.workflow_run.head_repository.full_name == github.repository",
        "github.event.workflow_run.head_branch == 'main'",
        "github.ref == 'refs/heads/main'",
    ):
        assert required in condition


def test_ci_token_is_read_only():
    assert "permissions:\n  contents: read" in (ROOT / ".github/workflows/ci.yml").read_text()


def test_container_runs_as_non_root_and_installs_the_hashed_lock():
    dockerfile = (ROOT / "Dockerfile").read_text()
    assert "\nUSER " in dockerfile
    assert "--require-hashes -r requirements.txt" in dockerfile
    lock = (ROOT / "requirements.txt").read_text()
    assert "django==" in lock and "--hash=sha256:" in lock
