"""Invitation admin: create, mark sent (queues the email), revoke, undo a mistaken
check-in, audited export.

Audit 2026-11-13, finding 2: the door role used to hold view/change_invitation, so a door
volunteer could set a used QR code back to SENT, un-revoke, or fake a check-in on the
change form (with no AuditLog row), and could read every VIP's email and phone.
Now:
  * this admin is superuser-only, whatever permissions a group is given by mistake;
  * status and the check-in fields are read-only on the form — the status moves only
    through invitations/services.py (check_in, mark_sent, revoke, undo_checkin), each
    audited;
  * door staff use /staff/checkin/ with the single checkin_invitation permission; that
    page shows name + organisation only (what the ID check needs), never contact details.
"""

from django.contrib import admin

from core import audit
from core.admin import export_csv_action

from . import services
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
    fields = (
        "guest_name",
        "organization",
        "contact_email",
        "contact_phone",
        "status",
        "sent_at",
        "checked_in_at",
        "checked_in_by",
        "invite_url",
    )
    readonly_fields = ("status", "sent_at", "checked_in_at", "checked_in_by", "invite_url")
    actions = [
        export_csv_action(
            ["guest_name", "organization", "status", "contact_email", "contact_phone"]
        ),
        "mark_sent",
        "revoke",
        "undo_checkin",
    ]

    # ---- superuser-only, regardless of group permissions ----------------------------
    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False  # revoke instead; rows are scrubbed by purge_pii at end of life

    def save_model(self, request, obj, form, change):
        """Only the guest/contact fields are editable here. Logged by field NAME — the
        audit log is kept after the PII purge, so it must not hold contact details."""
        super().save_model(request, obj, form, change)
        audit.record(
            request.user,
            "invitation.change" if change else "invitation.create",
            obj,
            after={"fields": form.changed_data},
        )

    # ---- audited status changes ---------------------------------------------------
    @admin.action(description="Mark SENT and queue the invitation email")
    def mark_sent(self, request, queryset):
        n = sum(1 for inv in queryset if services.mark_sent(inv, request.user))
        self.message_user(
            request,
            f"Marked {n} sent; emails queued where an address exists. "
            "No email? Share the invite URL via WhatsApp.",
        )

    @admin.action(description="REVOKE selected invitations (audit-logged)")
    def revoke(self, request, queryset):
        n = sum(1 for inv in queryset if services.revoke(inv, request.user))
        self.message_user(request, f"Revoked {n} invitation(s). Checked-in ones are unchanged.")

    @admin.action(description="Undo a mistaken check-in (audit-logged)")
    def undo_checkin(self, request, queryset):
        n = sum(1 for inv in queryset if services.undo_checkin(inv, request.user))
        self.message_user(request, f"Reversed {n} check-in(s); those QR codes work again.")
