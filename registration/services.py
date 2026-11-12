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
    outbox.queue(
        to_email=player.email,
        subject=CONTENT["EMAIL_MANAGE_SUBJECT"].format(site_name=CONTENT["SITE_NAME"]),
        body_text=CONTENT["EMAIL_MANAGE_BODY"].format(
            name=player.full_name,
            game=registration.game.name_ar,
            status=registration.get_status_display(),
            manage_url=manage_url(raw_token),
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
        promoted = _fill_seats_and_renumber(game, actor)
        return promoted[0] if promoted else None


def _fill_seats_and_renumber(game: Game, actor) -> list[Registration]:
    """Promote waitlisted registrations (FIFO) into free confirmed seats, then renumber
    the remaining waitlist densely 1..n. The caller must hold the game row lock
    (select_for_update) inside its transaction. Each promotion is audit-logged."""
    confirmed = game.registrations.filter(status=Registration.Status.CONFIRMED).count()
    waitlist = list(
        game.registrations.select_for_update()
        .filter(status=Registration.Status.WAITLISTED)
        .order_by("waitlist_position", "created_at")
    )
    promoted = []
    while confirmed < game.seats and waitlist:
        reg = waitlist.pop(0)
        reg.status = Registration.Status.CONFIRMED
        reg.waitlist_position = None
        reg.promoted_at = timezone.now()
        reg.save()
        audit.record(
            actor,
            "registration.promote",
            reg,
            before={"status": "waitlisted"},
            after={"status": "confirmed"},
        )
        confirmed += 1
        promoted.append(reg)
    for i, reg in enumerate(waitlist, start=1):
        if reg.waitlist_position != i:
            reg.waitlist_position = i
            reg.save(update_fields=["waitlist_position"])
    return promoted


def remove_registrations(registration_ids, actor, reason: str) -> tuple[int, int]:
    """Staff removal of registrations — one or many, e.g. a scripted wave of fake sign-ups
    (audit 2026-11-13, finding 1). Returns (removed, promoted).

    Per game, in ONE transaction under the game row lock: every selected active
    registration is marked REMOVED first, and only then are freed seats filled from the
    waitlist. So removing fakes that sit on both the seats and the waitlist never promotes
    a fake that is about to be removed, and real players move up in FIFO order. Every
    removal and promotion is audit-logged with the actor and the reason."""
    removed = promoted = 0
    ids = list(registration_ids)
    game_ids = sorted(
        set(Registration.objects.filter(pk__in=ids).values_list("game_id", flat=True))
    )
    with transaction.atomic():
        for game_id in game_ids:  # fixed lock order: no deadlock between two staff
            game = Game.objects.select_for_update().get(pk=game_id)
            selected = Registration.objects.select_for_update().filter(
                pk__in=ids, game=game, status__in=Registration.ACTIVE
            )
            for reg in selected:
                before = reg.status
                reg.status = Registration.Status.REMOVED
                reg.waitlist_position = None
                reg.save(update_fields=["status", "waitlist_position", "updated_at"])
                audit.record(
                    actor,
                    "registration.remove",
                    reg,
                    before={"status": before},
                    after={"status": "removed", "reason": reason},
                )
                removed += 1
            promoted += len(_fill_seats_and_renumber(game, actor))
    return removed, promoted


def release_phone(player: Player, actor, reason: str) -> None:
    """Free a phone number that someone else registered (squatting — audit 2026-11-13,
    finding 1). Removes the player's active registrations (waitlist promotes), detaches
    the number so its real owner can register fresh and get their own manage link, and
    invalidates the old manage link. The phone itself is NOT written to the audit log
    (the log is kept after the PII purge)."""
    with transaction.atomic():
        player = Player.objects.select_for_update().get(pk=player.pk)
        active = player.registrations.filter(status__in=Registration.ACTIVE)
        remove_registrations(active.values_list("pk", flat=True), actor, reason)
        player.phone = f"released-{player.pk}"
        player.manage_token_hash = Player.hash_token(new_manage_token())
        player.save(update_fields=["phone", "manage_token_hash", "updated_at"])
        audit.record(actor, "player.release_phone", player, after={"reason": reason})


def regenerate_manage_link(player: Player, actor) -> str:
    """New manage link for a player who lost theirs; the old link stops working.
    Emails it (same template as at registration) when the player gave an email.
    Returns the absolute URL so staff can share it another way."""
    raw = new_manage_token()
    with transaction.atomic():
        player.manage_token_hash = Player.hash_token(raw)
        player.save(update_fields=["manage_token_hash", "updated_at"])
        audit.record(actor, "player.regenerate_link", player)
        registration = (
            player.registrations.filter(status__in=Registration.ACTIVE).first()
            or player.registrations.order_by("-created_at").first()
        )
        if player.email and registration:
            _queue_manage_link_email(player, registration, raw)
    return manage_url(raw)


def manage_url(raw_token: str) -> str:
    return settings.SITE_BASE_URL + reverse("manage", args=[raw_token])


def seats_left(game: Game) -> int:
    n = game.registrations.filter(status=Registration.Status.CONFIRMED).count()
    return max(game.seats - n, 0)
