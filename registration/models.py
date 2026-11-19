"""Registration models (docs/data-model.md).

The one-tournament-per-player rule is a PARTIAL UNIQUE INDEX, not application
logic: it holds even if two requests race past the service-layer check.
"""

import re
import secrets
import unicodedata

from django.core.exceptions import ValidationError
from django.db import models

from core.security import token_hash

# Arabic-Indic (U+0660–0669) and Extended Arabic-Indic / Persian (U+06F0–06F9) digits →
# ASCII. An Arabic phone keyboard types these, and they are the same number.
_TO_ASCII_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "0123456789" * 2)
# Formatting a person or a phone may put in a number: whitespace (any, incl. no-break
# space), hyphens/dashes, brackets, dots, and the invisible direction marks that RTL
# text fields insert (LRM, RLM, ALM, LRE…PDF, LRI…PDI).
_FORMATTING = re.compile(r"[\s\-\u2010-\u2015().\u200e\u200f\u061c\u202a-\u202e\u2066-\u2069]")
# The ONLY stored form: +9665 followed by exactly 8 ASCII digits.
PHONE_RE = re.compile(r"\+9665[0-9]{8}", re.ASCII)


def normalize_phone(raw: str) -> str:
    """Normalize a Saudi mobile number to +9665XXXXXXXX. Raises ValidationError.

    Security assessment 2026-11-19 (YV-33): this used to strip a few characters and
    check only the prefix and length, so letters ("05abcdefgh") were accepted and the
    same number typed with Arabic-Indic digits became a second, different player.
    Now: Unicode-normalise (NFKC: full-width digits → ASCII), map Arabic-Indic and
    Persian digits to ASCII, strip formatting, accept the usual prefixes
    (05…, 9665…, +9665…, 009665…), then validate the result strictly against PHONE_RE.
    Anything else is rejected."""
    text = unicodedata.normalize("NFKC", raw or "").translate(_TO_ASCII_DIGITS)
    text = _FORMATTING.sub("", text)
    if text.startswith("00966"):
        text = "+" + text[2:]
    elif text.startswith("966"):
        text = "+" + text
    elif text.startswith("05"):
        text = "+966" + text[1:]
    if PHONE_RE.fullmatch(text):
        return text
    raise ValidationError("invalid phone")


def new_manage_token() -> str:
    """>=128-bit URL-safe secret for the player's manage link."""
    return secrets.token_urlsafe(24)


class Player(models.Model):
    """One player identity per phone number. No accounts — the manage link is
    the only credential (CLAUDE.md hard rule 4). Only its hash is stored."""

    full_name = models.CharField(max_length=120)
    # normalized +9665XXXXXXXX (normalize_phone); "purged-<pk>" / "released-<pk>" after
    # the end-of-life purge or a staff phone release. Enforced by the check constraint.
    phone = models.CharField(max_length=16, unique=True)
    email = models.EmailField(blank=True)
    manage_token_hash = models.CharField(max_length=64, unique=True)
    consent_at = models.DateTimeField()  # privacy-notice consent (DEC-08)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # Defence in depth for normalize_phone (YV-33): nothing but the normalized
            # form — or the purge/release placeholders — can reach the unique column.
            models.CheckConstraint(
                condition=models.Q(phone__regex=r"^\+9665[0-9]{8}$")
                | models.Q(phone__regex=r"^(purged|released)-[0-9]+$"),
                name="player_phone_normalized",
            ),
        ]

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


class RegistrationAttempt(models.Model):
    """One row per POST to the registration form — the application-side rate limit
    and the evidence staff use to find a scripted wave (audit 2026-11-13, finding 1).

    Like the vote (docs/voting.md → Privacy) only HMAC hashes are stored, never the raw
    IP, user agent or phone (CLAUDE.md hard rule 7). The rows are deleted by purge_pii.
    "Device" here means the (ip_hash, ua_hash) pair: weak on its own, but it costs a
    script something and needs no new cookie.
    """

    class Outcome(models.TextChoices):
        REGISTERED = "registered", "Registered"
        INVALID = "invalid", "Form invalid"
        LIMITED = "limited", "Rate-limited"
        TURNSTILE = "turnstile", "Bot check failed"
        DUPLICATE = "duplicate", "Already registered"
        FULL = "full", "Game full"

    ip_hash = models.CharField(max_length=64)
    ua_hash = models.CharField(max_length=64)
    phone_hash = models.CharField(max_length=64, blank=True)  # set once the form is valid
    game = models.ForeignKey("core.Game", on_delete=models.CASCADE, related_name="+")
    outcome = models.CharField(max_length=10, choices=Outcome.choices)
    registration = models.ForeignKey(
        Registration, null=True, blank=True, on_delete=models.SET_NULL, related_name="attempts"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["ip_hash", "created_at"], name="regattempt_ip_idx"),
            models.Index(fields=["phone_hash", "created_at"], name="regattempt_phone_idx"),
        ]

    def __str__(self):
        return f"attempt {self.pk} [{self.outcome}]"
