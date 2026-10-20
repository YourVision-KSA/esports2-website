"""Registration services: the seat-claim transaction and waitlist promotion
(docs/data-model.md — the critical path). The Game row lock serializes all
registration writes for one game; the DB constraints backstop every rule.
"""

from django.conf import settings
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from core import audit, outbox
from core.content import CONTENT
from core.models import Game

from .models import Player, Registration, new_manage_token, normalize_phone


class DuplicateRegistration(Exception):
    """Player already has an active registration (one tournament per player)."""


class GameFull(Exception):
    """Seats and waitlist are both full."""


def register(
    *, full_name: str, phone: str, email: str, game: Game, game_player_id: str
) -> tuple[Registration, str | None]:
    """Claim a seat (or waitlist spot). Returns (registration, manage_token).

    manage_token is the RAW token — returned exactly once, at creation, for the
    player who just registered. Only its hash is stored. None when the player
    already existed (their original link stays valid).
    """
    phone = normalize_phone(phone)
    raw_token: str | None = None

    with transaction.atomic():
        # Serialize per game: the seat race is decided by this row lock.
        game = Game.objects.select_for_update().get(pk=game.pk, status=Game.Status.CONFIRMED)

        player = Player.objects.filter(phone=phone).first()
        if player is None:
            raw_token = new_manage_token()
            try:
                # Savepoint: a concurrent create with the same phone must not
                # poison the outer transaction (unique(phone) decides the race).
                with transaction.atomic():
                    player = Player.objects.create(
                        full_name=full_name,
                        phone=phone,
                        email=email,
                        manage_token_hash=Player.hash_token(raw_token),
                        consent_at=timezone.now(),
                    )
            except IntegrityError:
                player = Player.objects.get(phone=phone)
                raw_token = None  # their original manage link stays valid

        if player.registrations.filter(status__in=Registration.ACTIVE).exists():
            raise DuplicateRegistration

        n_confirmed = game.registrations.filter(status=Registration.Status.CONFIRMED).count()
        n_waitlisted = game.registrations.filter(status=Registration.Status.WAITLISTED).count()

        if n_confirmed < game.seats:
            status, position = Registration.Status.CONFIRMED, None
        elif n_waitlisted < game.waitlist_cap:
            status, position = Registration.Status.WAITLISTED, n_waitlisted + 1
        else:
            raise GameFull

        try:
            registration = Registration.objects.create(
                player=player,
                game=game,
                status=status,
                waitlist_position=position,
                game_player_id=game_player_id,
            )
        except IntegrityError as exc:
            # The partial unique index backstops a race on the one-tournament rule.
            raise DuplicateRegistration from exc

        # Manage link email — queued in the SAME transaction (docs/data-model.md).
        if player.email and raw_token:
            _queue_manage_link_email(player, registration, raw_token)

    return registration, raw_token


def _queue_manage_link_email(player: Player, registration: Registration, raw_token: str):
    manage_url = settings.SITE_BASE_URL + reverse("manage", args=[raw_token])
    outbox.queue(
        to_email=player.email,
        subject=CONTENT["EMAIL_MANAGE_SUBJECT"].format(site_name=CONTENT["SITE_NAME"]),
        body_text=CONTENT["EMAIL_MANAGE_BODY"].format(
            name=player.full_name,
            game=registration.game.name_ar,
            status=registration.get_status_display(),
            manage_url=manage_url,
        ),
    )


def withdraw(registration: Registration, actor=None) -> Registration | None:
    """Withdraw a registration; promote the first waitlisted player if a
    confirmed seat was freed. Idempotent. Returns the promoted registration."""
    with transaction.atomic():
        game = Game.objects.select_for_update().get(pk=registration.game_id)
        registration = Registration.objects.select_for_update().get(pk=registration.pk)

        if registration.status not in Registration.ACTIVE:
            return None  # already withdrawn/removed — no-op

        was_confirmed = registration.status == Registration.Status.CONFIRMED
        old_position = registration.waitlist_position
        registration.status = Registration.Status.WITHDRAWN
        registration.waitlist_position = None
        registration.withdrawn_at = timezone.now()
        registration.save()
        audit.record(
            actor,
            "registration.withdraw",
            registration,
            before={"status": "active"},
            after={"status": "withdrawn"},
        )

        waitlist = list(
            game.registrations.select_for_update()
            .filter(status=Registration.Status.WAITLISTED)
            .order_by("waitlist_position")
        )

        promoted = None
        if was_confirmed and waitlist:
            promoted = waitlist.pop(0)
            promoted.status = Registration.Status.CONFIRMED
            promoted.waitlist_position = None
            promoted.promoted_at = timezone.now()
            promoted.save()
            audit.record(
                actor,
                "registration.promote",
                promoted,
                before={"status": "waitlisted"},
                after={"status": "confirmed"},
            )
        elif old_position is not None:
            # A waitlisted player left: close the gap behind them.
            waitlist = [r for r in waitlist if r.waitlist_position > old_position]

        # Re-number remaining waitlist densely (FIFO preserved).
        remaining = (
            game.registrations.select_for_update()
            .filter(status=Registration.Status.WAITLISTED)
            .order_by("waitlist_position")
        )
        for i, reg in enumerate(remaining, start=1):
            if reg.waitlist_position != i:
                reg.waitlist_position = i
                reg.save(update_fields=["waitlist_position"])

        return promoted


def seats_left(game: Game) -> int:
    n = game.registrations.filter(status=Registration.Status.CONFIRMED).count()
    return max(game.seats - n, 0)
