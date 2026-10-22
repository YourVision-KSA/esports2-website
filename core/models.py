"""Core models: Game, SiteConfig (phase switch), AuditLog, OutboxEmail.

Field definitions follow docs/data-model.md. Constraints are not negotiable.
"""

from django.conf import settings
from django.db import models


class Game(models.Model):
    """A tournament. Names are DATA — the public vote decides which are confirmed."""

    class Status(models.TextChoices):
        CANDIDATE = "candidate", "Candidate"
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"

    slug = models.SlugField(unique=True)
    name_ar = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100, blank=True)
    platform = models.CharField(max_length=40, blank=True)  # display only (PS5 / PC)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CANDIDATE)
    seats = models.PositiveSmallIntegerField(default=16)
    waitlist_cap = models.PositiveSmallIntegerField(default=8)  # DEC-07
    display_order = models.PositiveSmallIntegerField(default=0)
    # Label for the per-game player-ID field, e.g. "معرّف EA" (set by admin)
    player_id_label_ar = models.CharField(max_length=60, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "slug"]

    def __str__(self):
        return self.name_en or self.slug


class SiteConfig(models.Model):
    """Singleton: the phase switch. Phases are derived from these datetimes and
    enforced server-side on every request (CLAUDE.md hard rule 2)."""

    vote_opens_at = models.DateTimeField(null=True, blank=True)
    vote_closes_at = models.DateTimeField(null=True, blank=True)
    registration_opens_at = models.DateTimeField(null=True, blank=True)
    registration_closes_at = models.DateTimeField(null=True, blank=True)
    event_start_date = models.DateField(null=True, blank=True)
    event_end_date = models.DateField(null=True, blank=True)
    archived = models.BooleanField(default=False)
    stream_url_1 = models.URLField(blank=True)
    stream_url_2 = models.URLField(blank=True)
    stream_url_3 = models.URLField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "site configuration"

    def __str__(self):
        return "Site configuration"

    def save(self, *args, **kwargs):
        self.pk = 1  # enforce the singleton
        super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls) -> "SiteConfig":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class AuditLog(models.Model):
    """Append-only audit trail (docs/data-model.md). Written via core.audit.record();
    no update/delete paths exist in app code."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    action = models.CharField(max_length=60)  # slug, e.g. "result.enter"
    model = models.CharField(max_length=60)
    object_id = models.CharField(max_length=64)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} {self.model}#{self.object_id}"


class OutboxEmail(models.Model):
    """Queued outgoing email. Senders insert rows; a scheduler tick delivers them.
    A mail failure never fails the action that queued it (docs/architecture.md)."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    to_email = models.EmailField()
    subject = models.CharField(max_length=200)
    body_text = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.to_email}: {self.subject} [{self.status}]"


class TierStat(models.Model):
    """Daily COUNT of how the hero 3D scene ended up on visitors' devices — the "WebGL
    fallback rate" metric (docs/frontend.md → Quality tiers, docs/operations.md).

    Aggregated only: no IP, no user agent, no cookie, no visitor id — one row per
    (day, outcome, device class) with a counter. Written by core.beacon.record_tier()."""

    class Outcome(models.TextChoices):
        HIGH = "high", "3D high"
        MID = "mid", "3D mid"
        LOW = "low", "Poster (slow device)"
        FALLBACK = "fallback", "Poster (WebGL/bundle failed)"
        REDUCED = "reduced", "Poster (reduced motion)"

    class Device(models.TextChoices):
        MOBILE = "mobile", "Mobile"
        DESKTOP = "desktop", "Desktop"

    day = models.DateField()
    outcome = models.CharField(max_length=10, choices=Outcome.choices)
    device = models.CharField(max_length=8, choices=Device.choices)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-day", "device", "outcome"]
        constraints = [
            models.UniqueConstraint(fields=["day", "outcome", "device"], name="tierstat_unique_day")
        ]

    def __str__(self):
        return f"{self.day} {self.device} {self.outcome}: {self.count}"
