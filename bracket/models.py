"""Bracket models (docs/data-model.md). A fixed single-elimination tree of 15
matches per game, created at draw time."""

from django.db import models


class Match(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DONE = "done", "Done"
        FORFEIT = "forfeit", "Forfeit"

    game = models.ForeignKey("core.Game", on_delete=models.CASCADE, related_name="matches")
    round = models.PositiveSmallIntegerField()  # 1=R16 … 4=final
    slot = models.PositiveSmallIntegerField()  # position within the round
    player1 = models.ForeignKey(
        "registration.Registration",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    player2 = models.ForeignKey(
        "registration.Registration",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    winner = models.ForeignKey(
        "registration.Registration",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    score_text = models.CharField(max_length=40, blank=True)  # free text, e.g. "3–1"
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    next_match = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="feeders"
    )
    next_slot = models.PositiveSmallIntegerField(null=True, blank=True)  # 1 or 2
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "matches"
        ordering = ["game", "round", "slot"]
        constraints = [
            models.UniqueConstraint(fields=["game", "round", "slot"], name="uniq_game_round_slot"),
            # The winner must be one of the two participants (DB CHECK).
            models.CheckConstraint(
                condition=(
                    models.Q(winner__isnull=True)
                    | models.Q(winner=models.F("player1"))
                    | models.Q(winner=models.F("player2"))
                ),
                name="winner_is_participant",
            ),
        ]

    def __str__(self):
        return f"{self.game.slug} R{self.round} #{self.slot}"
