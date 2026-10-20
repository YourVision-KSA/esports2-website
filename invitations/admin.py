"""Invitation admin: create, mark sent (queues the email), revoke, audited export."""

from django.contrib import admin
from django.utils import timezone

from core import audit, outbox
from core.admin import export_csv_action
from core.content import CONTENT

from .models import Invitation


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = (
        "guest_name",
        "organization",
        "status",
        "sent_at",
        "checked_in_at",
        "checked_in_by",
    )
    list_filter = ("status", "organization")
    search_fields = ("guest_name", "organization", "contact_email")
    readonly_fields = ("token", "checked_in_at", "checked_in_by", "invite_url")
    actions = [
        export_csv_action(
            ["guest_name", "organization", "status", "contact_email", "contact_phone"]
        ),
        "mark_sent",
        "revoke",
    ]

    @admin.action(description="Mark SENT and queue the invitation email")
    def mark_sent(self, request, queryset):
        for invitation in queryset.filter(status=Invitation.Status.CREATED):
            if invitation.contact_email:
                outbox.queue(
                    invitation.contact_email,
                    CONTENT["INVITE_TITLE"],
                    f"{CONTENT['INVITE_BODY']}\n\n{invitation.invite_url()}",
                )
            invitation.status = Invitation.Status.SENT
            invitation.sent_at = timezone.now()
            invitation.save(update_fields=["status", "sent_at"])
            audit.record(request.user, "invitation.sent", invitation)
        self.message_user(
            request,
            "Marked sent; emails queued where an address exists. "
            "No email? Share the invite URL via WhatsApp.",
        )

    @admin.action(description="REVOKE selected invitations (audit-logged)")
    def revoke(self, request, queryset):
        for invitation in queryset.exclude(status=Invitation.Status.CHECKED_IN):
            before = invitation.status
            invitation.status = Invitation.Status.REVOKED
            invitation.save(update_fields=["status"])
            audit.record(
                request.user,
                "invitation.revoke",
                invitation,
                before={"status": before},
                after={"status": "revoked"},
            )
