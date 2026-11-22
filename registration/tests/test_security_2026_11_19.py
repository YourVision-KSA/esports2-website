"""Regression tests for the security assessment of 2026-11-19 (registration):
YV-06 unsolved attempts must not lock out a shared network, YV-07 limits group IPv6 by
/64, YV-33 strict phone normalisation. Several started as the reviewers' PoC tests."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.utils import timezone

from core.models import Game
from registration import services
from registration.forms import RegistrationForm
from registration.models import Player, Registration, normalize_phone

pytestmark = pytest.mark.django_db

NAT = "198.51.100.7"


def _post(client, game, ip=NAT, ua="UA", **data):
    body = {
        "full_name": "student",
        "phone": "0551112222",
        "email": "",
        "game_player_id": "me",
        "consent": "on",
        **data,
    }
    return client.post(f"/register/{game.slug}/", body, REMOTE_ADDR=ip, HTTP_USER_AGENT=ua)


# --------------------------------------------------------------------------- YV-06


@override_settings(TURNSTILE_ENABLED=True)
def test_unsolved_and_invalid_posts_do_not_lock_out_a_shared_network(
    client, phase_registration, game, monkeypatch, settings
):
    """Reviewer PoC test_unsolved_turnstile_posts_lock_out_shared_network: 60 POSTs with
    no Turnstile solution from the campus NAT used to 429 every real student there."""
    game.seats = 40
    game.save()
    monkeypatch.setattr("core.turnstile.verify", lambda token, ip="": token == "solved")
    for _ in range(settings.REG_IP_ATTEMPTS_PER_10MIN):
        assert _post(client, game, phone="0500000000").status_code == 400  # unsolved
        assert _post(client, game, phone="garbage").status_code == 200  # invalid form

    real = _post(client, game, ua="other phone", **{"cf-turnstile-response": "solved"})
    assert real.status_code == 302
    assert Player.objects.count() == 1


# --------------------------------------------------------------------------- YV-07


@override_settings(REG_IP_REGISTRATIONS_PER_DAY=2, REG_DEVICE_REGISTRATIONS_PER_DAY=10)
def test_ipv6_rotation_inside_one_64_hits_the_network_cap(client, phase_registration, game):
    assert _post(client, game, ip="2001:db8:1:2::1", phone="0550000001").status_code == 302
    assert _post(client, game, ip="2001:db8:1:2::2", phone="0550000002").status_code == 302
    rotated = _post(client, game, ip="2001:db8:1:2:abcd::3", phone="0550000003")
    assert rotated.status_code == 429
    # a different /64 is a different network
    assert _post(client, game, ip="2001:db8:1:3::1", phone="0550000004").status_code == 302


@override_settings(REG_IP_REGISTRATIONS_PER_DAY=1, REG_DEVICE_REGISTRATIONS_PER_DAY=10)
def test_ipv4_mapped_address_is_the_same_network_as_ipv4(client, phase_registration, game):
    assert _post(client, game, ip="203.0.113.9", phone="0550000001").status_code == 302
    assert _post(client, game, ip="::ffff:203.0.113.9", phone="0550000002").status_code == 429


# --------------------------------------------------------------------------- YV-33


@pytest.mark.parametrize(
    "raw",
    [
        "0512345678",
        "05١٢٣٤٥٦٧٨",  # Arabic-Indic digits
        "٠٥١٢٣٤٥٦٧٨",
        "05۱۲۳۴۵۶۷۸",  # Persian digits
        "+966 51 234 5678",
        "00966512345678",
        "966-51-234-5678",
        "(05) 1234 5678",
        "‏0512345678‎",  # direction marks from an RTL field
        " 05 12345678",  # no-break spaces
        "０５１２３４５６７８",  # full-width digits
    ],
)
def test_same_number_in_any_digits_or_format_normalizes_to_one_form(raw):
    assert normalize_phone(raw) == "+966512345678"


@pytest.mark.parametrize(
    "raw",
    [
        "05abcdefgh",  # reviewer PoC
        "05=1+2+3+4",  # reviewer PoC
        "051234567",  # too short
        "05123456789",  # too long
        "0412345678",  # not a mobile number
        "+9665١٢٣٤٥٦٧x",
        "",
    ],
)
def test_anything_else_is_rejected(raw):
    with pytest.raises(ValidationError):
        normalize_phone(raw)


def test_form_rejects_letters(game):
    form = RegistrationForm(
        {
            "full_name": "x",
            "phone": "05abcdefgh",
            "email": "",
            "game_player_id": "t",
            "consent": "on",
        },
        game=game,
    )
    assert not form.is_valid() and "phone" in form.errors


def test_same_number_in_arabic_digits_cannot_enter_a_second_tournament(game):
    """Reviewer PoC test_same_number_two_tournaments: one number, two players."""
    other = Game.objects.create(slug="other", name_ar="أخرى", status=Game.Status.CONFIRMED)
    services.register(full_name="A", phone="0551234567", email="", game=game, game_player_id="a")
    with pytest.raises(services.DuplicateRegistration):
        services.register(
            full_name="A", phone="05٥١٢٣٤٥٦٧", email="", game=other, game_player_id="a"
        )
    assert Player.objects.count() == 1
    assert Registration.objects.count() == 1


def test_database_refuses_an_unnormalized_phone():
    with pytest.raises(IntegrityError), transaction.atomic():
        Player.objects.create(
            full_name="x",
            phone="+9665abcdefgh",
            manage_token_hash="h1",
            consent_at=timezone.now(),
        )
