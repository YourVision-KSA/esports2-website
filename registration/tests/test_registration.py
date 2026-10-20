"""Registration critical tests (docs/testing.md → Registration): the seat race,
the one-tournament rule, waitlist FIFO, manage links, the email outbox."""

import pytest
from django.test import override_settings

from conftest import fill_confirmed, run_concurrently, set_phase
from core.models import Game, OutboxEmail
from core.phases import Phase
from registration import services
from registration.models import Player, Registration

pytestmark = pytest.mark.django_db


def reg(game, i, email=""):
    return services.register(
        full_name=f"P{i}",
        phone=f"+96655{i:07d}",
        email=email,
        game=game,
        game_player_id=f"tag-{i}",
    )


# ---------------------------------------------------------------- seat race


@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
def test_seat_race_last_seat(game):
    fill_confirmed(game, 15)
    results = run_concurrently(lambda: reg(game, 1), lambda: reg(game, 2))
    assert all(exc is None for _, exc in results)
    statuses = sorted(r.status for (r, _), _ in results)
    assert statuses == [Registration.Status.CONFIRMED, Registration.Status.WAITLISTED]
    assert game.registrations.filter(status=Registration.Status.CONFIRMED).count() == 16
    waitlisted = game.registrations.get(status=Registration.Status.WAITLISTED)
    assert waitlisted.waitlist_position == 1


@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
def test_seat_cap_never_exceeded(game):
    fill_confirmed(game, 13)  # 3 seats left
    results = run_concurrently(*[lambda i=i: reg(game, i) for i in range(10)])
    assert all(exc is None for _, exc in results)
    confirmed = game.registrations.filter(status=Registration.Status.CONFIRMED)
    waitlisted = game.registrations.filter(status=Registration.Status.WAITLISTED).order_by(
        "waitlist_position"
    )
    assert confirmed.count() == 16
    assert waitlisted.count() == 7
    assert list(waitlisted.values_list("waitlist_position", flat=True)) == list(range(1, 8))


# ------------------------------------------------- one tournament per player


def test_one_tournament_per_player(game):
    other = Game.objects.create(slug="fifa", name_ar="فيفا", status=Game.Status.CONFIRMED)
    reg(game, 1)
    with pytest.raises(services.DuplicateRegistration):
        reg(other, 1)  # same phone
    assert Registration.objects.filter(status__in=Registration.ACTIVE).count() == 1


@pytest.mark.concurrency
@pytest.mark.django_db(transaction=True)
def test_one_tournament_per_player_concurrent(game):
    """Two simultaneous registrations for DIFFERENT games, same phone: the
    partial unique index must leave exactly one active registration."""
    other = Game.objects.create(slug="cod", name_ar="كود", status=Game.Status.CONFIRMED)
    results = run_concurrently(lambda: reg(game, 1), lambda: reg(other, 1))
    errors = [exc for _, exc in results if exc is not None]
    assert len(errors) == 1
    assert isinstance(errors[0], services.DuplicateRegistration)
    assert Registration.objects.filter(status__in=Registration.ACTIVE).count() == 1
    assert Player.objects.count() == 1


def test_same_phone_is_same_player(game):
    other = Game.objects.create(slug="fifa", name_ar="فيفا", status=Game.Status.CONFIRMED)
    registration, token = reg(game, 1)
    services.withdraw(registration)
    registration2, token2 = reg(other, 1)  # re-register after withdrawing
    assert registration2.player_id == registration.player_id
    assert token2 is None  # original manage link stays valid, token never re-shown
    assert Player.objects.count() == 1


# ----------------------------------------------------------------- waitlist


def test_waitlist_fifo_promotion(game):
    confirmed = fill_confirmed(game, 16)
    w1, _ = reg(game, 1)
    w2, _ = reg(game, 2)
    w3, _ = reg(game, 3)
    assert [w1.waitlist_position, w2.waitlist_position, w3.waitlist_position] == [1, 2, 3]

    promoted = services.withdraw(confirmed[0])
    assert promoted.pk == w1.pk
    assert promoted.status == Registration.Status.CONFIRMED
    w2.refresh_from_db(), w3.refresh_from_db()
    assert (w2.waitlist_position, w3.waitlist_position) == (1, 2)
    from core.models import AuditLog

    assert AuditLog.objects.filter(action="registration.promote").count() == 1


def test_waitlisted_withdrawal_closes_the_gap(game):
    fill_confirmed(game, 16)
    w1, _ = reg(game, 1)
    w2, _ = reg(game, 2)
    w3, _ = reg(game, 3)
    assert services.withdraw(w2) is None  # no seat freed, nobody promoted
    w1.refresh_from_db(), w3.refresh_from_db()
    assert (w1.waitlist_position, w3.waitlist_position) == (1, 2)


def test_withdraw_idempotent(game):
    fill_confirmed(game, 16)
    w1, _ = reg(game, 1)
    confirmed = game.registrations.filter(status=Registration.Status.CONFIRMED).first()
    assert services.withdraw(confirmed) is not None
    assert services.withdraw(confirmed) is None  # second call: no-op
    assert game.registrations.filter(status=Registration.Status.CONFIRMED).count() == 16


def test_waitlist_cap(game):
    fill_confirmed(game, 16)
    for i in range(game.waitlist_cap):
        reg(game, i)
    with pytest.raises(services.GameFull):
        reg(game, 99)


# ---------------------------------------------------------- views and gates


def test_registration_phase_gate(client, game):
    set_phase(Phase.VOTE)
    response = client.post(
        f"/register/{game.slug}/",
        {"full_name": "x", "phone": "0550000001", "game_player_id": "t", "consent": "on"},
    )
    assert response.status_code == 403
    assert Registration.objects.count() == 0


def test_register_view_end_to_end(client, game, phase_registration):
    response = client.post(
        f"/register/{game.slug}/",
        {"full_name": "لاعب", "phone": "055 000 0001", "game_player_id": "tag1", "consent": "on"},
    )
    assert response.status_code == 302
    assert response.url.startswith("/r/")
    registration = Registration.objects.get()
    assert registration.status == Registration.Status.CONFIRMED
    assert registration.player.phone == "+966550000001"  # normalized
    # Follow the manage link; the token in the URL must resolve via its hash.
    manage = client.get(response.url)
    assert manage.status_code == 200


def test_manage_token_unguessable(client, game, phase_registration):
    _, token = reg(game, 1)
    assert len(token) >= 22  # token_urlsafe(24) -> 32 chars; >=128 bits either way
    player = Player.objects.get()
    assert token not in player.manage_token_hash  # only the hash is stored
    assert client.get("/r/wrong-token-000000000000/").status_code == 404


def test_registration_email_queues_manage_link(game):
    registration, token = reg(game, 1, email="p1@example.com")
    email = OutboxEmail.objects.get()
    assert f"/r/{token}/" in email.body_text
    assert email.to_email == "p1@example.com"
    # Without an email: no row.
    OutboxEmail.objects.all().delete()
    reg(game, 2)
    assert OutboxEmail.objects.count() == 0


@override_settings(EMAIL_BACKEND="core.tests.test_outbox.FailingBackend")
def test_smtp_failure_never_affects_registration(game):
    from core.outbox import send_due

    registration, _ = reg(game, 1, email="p1@example.com")
    send_due()  # SMTP fails; the registration must be untouched
    registration.refresh_from_db()
    assert registration.status == Registration.Status.CONFIRMED
    assert OutboxEmail.objects.get().status == OutboxEmail.Status.QUEUED
