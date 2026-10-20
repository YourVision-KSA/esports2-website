"""Voting models (docs/data-model.md, docs/voting.md).

One ballot per voter token, enforced by the unique token_hash. Tallies are
computed queries over status=counted — never stored counters.
"""

from django.conf import settings
from django.db import models


class Ballot(models.Model):
    class Status(models.TextChoices):
        COUNTED = "counted", "Counted"
        HELD = "held", "Held for review"
        INVALIDATED = "invalidated", "Invalidated"

    # HMAC of the voter token — the one-ballot rule (unique).
    token_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.COUNTED)
    turnstile_passed = models.BooleanField(default=False)
    # HMAC hashes only; raw IP/UA are never stored (CLAUDE.md hard rule 7).
    ip_hash = models.CharField(max_length=64, db_index=True)
    ua_hash = models.CharField(max_length=64)
    asn = models.PositiveIntegerField(null=True, blank=True)
    # Coarse heuristics for review; stripped 14 days after close (docs/voting.md).
    signals = models.JSONField(null=True, blank=True)
    held_reason = models.CharField(max_length=40, blank=True)
    invalidated_reason = models.CharField(max_length=40, blank=True)
    invalidated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"ballot {self.pk} [{self.status}]"


class BallotChoice(models.Model):
    ballot = models.ForeignKey(Ballot, on_delete=models.CASCADE, related_name="choices")
    game = models.ForeignKey("core.Game", on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["ballot", "game"], name="uniq_ballot_game"),
        ]

    def __str__(self):
        return f"ballot {self.ballot_id} -> game {self.game_id}"
