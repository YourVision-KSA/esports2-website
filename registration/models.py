"""Registration models (docs/data-model.md).

The one-tournament-per-player rule is a PARTIAL UNIQUE INDEX, not application
logic: it holds even if two requests race past the service-layer check.
"""

import re
import secrets

from django.core.exceptions import ValidationError
from django.db import models

from core.security import token_hash


def normalize_phone(raw: str) -> str:
    """Normalize a Saudi mobile number to +9665XXXXXXXX. Raises ValidationError."""
    digits = re.sub(r"[\s\-()]", "", raw or "")
    if digits.startswith("+9665") and len(digits) == 13:
        return digits
    if digits.startswith("9665") and len(digits) == 12:
        return f"+{digits}"
    if digits.startswith("05") and len(digits) == 10:
        return f"+966{digits[1:]}"
    raise ValidationError("invalid phone")


def new_manage_token() -> str:
    """>=128-bit URL-safe secret for the player's manage link."""
    return secrets.token_urlsafe(24)


class Player(models.Model):
    """One player identity per phone number. No accounts — the manage link is
    the only credential (CLAUDE.md hard rule 4). Only its hash is stored."""

    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=16, unique=True)  # normalized +9665XXXXXXXX
    email = models.EmailField(blank=True)
    manage_token_hash = models.CharField(max_length=64, unique=True)
    consent_at = models.DateTimeField()  # privacy-notice consent (DEC-08)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"player {self.pk}"

    @classmethod
    def hash_token(cls, token: str) -> str:
        return token_hash(token)


class Registration(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        WAITLISTED = "waitlisted", "Waitlisted"
        WITHDRAWN = "withdrawn", "Withdrawn"
        REMOVED = "removed", "Removed"

    ACTIVE = (Status.CONFIRMED, Status.WAITLISTED)

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="registrations")
    game = models.ForeignKey("core.Game", on_delete=models.PROTECT, related_name="registrations")
    status = models.CharField(max_length=12, choices=Status.choices)
    # Dense FIFO order among waitlisted registrations of this game.
    waitlist_position = models.PositiveSmallIntegerField(null=True, blank=True)
    # The per-game ID (EA ID / Activision ID / Epic ID) — shown on public brackets.
    game_player_id = models.CharField(max_length=80)
    promoted_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # ONE TOURNAMENT PER PLAYER (docs/product.md §5): one active
            # registration across all games, enforced by the database.
            models.UniqueConstraint(
                fields=["player"],
                condition=models.Q(status__in=["confirmed", "waitlisted"]),
                name="uniq_active_registration_per_player",
            ),
            # No re-register for the same game (history stays clean).
            models.UniqueConstraint(fields=["player", "game"], name="uniq_player_game"),
        ]

    def __str__(self):
        return f"{self.game_player_id} @ {self.game.slug} [{self.status}]"
