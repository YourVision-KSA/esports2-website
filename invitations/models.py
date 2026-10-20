"""VIP invitations (docs/data-model.md). The QR encodes /invite/<token>; check-in
is a single atomic conditional UPDATE so exactly one concurrent scan wins."""

import secrets

from django.conf import settings
from django.db import models


def new_invite_token() -> str:
    return secrets.token_urlsafe(24)  # >=128-bit


class Invitation(models.Model):
    class Status(models.TextChoices):
        CREATED = "created", "Created"
        SENT = "sent", "Sent"
        CHECKED_IN = "checked_in", "Checked in"
        REVOKED = "revoked", "Revoked"

    guest_name = models.CharField(max_length=120)
    organization = models.CharField(max_length=120, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    token = models.CharField(max_length=48, unique=True, default=new_invite_token)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CREATED)
    sent_at = models.DateTimeField(null=True, blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.guest_name} [{self.status}]"

    def invite_url(self) -> str:
        return f"{settings.SITE_BASE_URL}/invite/{self.token}/"
