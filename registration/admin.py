"""Registration admin: waitlist overview, audited bulk removal with correct waitlist
promotion, phone-number release, audited CSV export, manage-link regeneration.

Registrations are never edited field by field here — every state change goes through
registration/services.py (seat lock + audit log). Audit 2026-11-13, findings 1 and 2.

Operator runbook (docs/operations.md → "Registration abuse"):
  * a scripted wave: filter/search by the "network" column (hash prefix of the client IP
    that registered), select, action "Remove selected registrations", give a reason;
  * someone registered another person's phone number: Players → select → action
    "Release phone number" — the real owner can then register and gets their own link.
"""

from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.template.response import TemplateResponse

from core.admin import export_csv_action
from core.audit import record as audit_record

from . import services
from .models import Player, Registration


def _confirm_with_reason(modeladmin, request, queryset, *, action, title, explanation, apply):
    """Two-step admin action: the first POST shows a confirmation page that asks for a
    reason; the second (confirm=yes) calls apply(reason). Superuser-only."""
    if not request.user.is_superuser:
        modeladmin.message_user(request, "This action is admin-only.", level=messages.ERROR)
        return None
    if request.POST.get("confirm") == "yes":
        reason = request.POST.get("reason", "").strip()[:200]
        if reason:
            apply(reason)
            return None
        modeladmin.message_user(request, "A reason is required.", level=messages.ERROR)
    context = {
        **modeladmin.admin_site.each_context(request),
        "title": title,
        "explanation": explanation,
        "objects": list(queryset),
        "action": action,
        "action_checkbox_name": helpers.ACTION_CHECKBOX_NAME,
        "opts": modeladmin.model._meta,
    }
    return TemplateResponse(request, "admin/confirm_with_reason.html", context)


class RegistrationInline(admin.TabularInline):
    model = Registration
    extra = 0
    fields = readonly_fields = (
        "game",
        "status",
        "waitlist_position",
        "game_player_id",
        "created_at",
    )
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "phone", "email", "created_at")
    search_fields = ("full_name", "phone", "email")
    readonly_fields = ("manage_token_hash", "consent_at")
    inlines = [RegistrationInline]
    actions = [
        export_csv_action(["id", "full_name", "phone", "email"]),
        "regenerate_manage_link",
        "release_phone",
    ]

    def has_add_permission(self, request):
        return False  # players are created only by the registration form

    def has_delete_permission(self, request, obj=None):
        return False  # removal goes through the audited actions; deletion is purge_pii

    def save_model(self, request, obj, form, change):
        """Corrections (a PDPL right) are allowed for admins and audit-logged. The log
        records WHICH fields changed, not their values (the log outlives the PII purge)."""
        super().save_model(request, obj, form, change)
        audit_record(request.user, "player.change", obj, after={"fields": form.changed_data})

    @admin.action(description="Regenerate manage link (emails it if possible)")
    def regenerate_manage_link(self, request, queryset):
        """For players who lost their link. The new link invalidates the old one."""
        if not request.user.is_superuser:
            self.message_user(request, "This action is admin-only.", level=messages.ERROR)
            return
        for player in queryset:
            url = services.regenerate_manage_link(player, request.user)
            if player.email:
                self.message_user(request, f"player {player.pk}: new link queued to email.")
            else:
                self.message_user(request, f"player {player.pk}: {url}")

    @admin.action(description="Release phone number (someone else registered it; audited)")
    def release_phone(self, request, queryset):
        def apply(reason):
            for player in queryset:
                services.release_phone(player, request.user, reason)
            self.message_user(
                request,
                f"Released {queryset.count()} phone number(s); their registrations were "
                "removed and the waitlist promoted. The real owners can register now.",
            )

        return _confirm_with_reason(
            self,
            request,
            queryset,
            action="release_phone",
            title="Release phone numbers",
            explanation=(
                "Each selected player's active registration is removed (the waitlist "
                "promotes), the phone number is detached so its real owner can register, "
                "and the old manage link stops working."
            ),
            apply=apply,
        )


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "game_player_id",
        "game",
        "status",
        "waitlist_position",
        "player",
        "network",
        "created_at",
    )
    list_filter = ("game", "status")
    search_fields = ("game_player_id", "player__full_name", "player__phone", "attempts__ip_hash")
    date_hierarchy = "created_at"
    # Read-only: status / waitlist changes only through the audited services (seat lock).
    readonly_fields = (
        "player",
        "game",
        "status",
        "waitlist_position",
        "game_player_id",
        "promoted_at",
        "withdrawn_at",
        "created_at",
        "updated_at",
    )
    actions = [
        export_csv_action(["id", "game_player_id", "status", "waitlist_position"]),
        "remove_registration",
    ]

    def has_add_permission(self, request):
        return False  # an admin-added row would bypass the seat cap and the waitlist

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="network")
    def network(self, obj):
        """First characters of the HMAC of the client IP that registered — the same value
        for every registration from one network. Search for it to select a cluster."""
        attempt = obj.attempts.first()
        return attempt.ip_hash[:10] if attempt else "-"

    @admin.action(description="Remove selected registrations (waitlist promotes; audited)")
    def remove_registration(self, request, queryset):
        active = queryset.filter(status__in=Registration.ACTIVE)

        def apply(reason):
            removed, promoted = services.remove_registrations(
                active.values_list("pk", flat=True), request.user, reason
            )
            self.message_user(
                request,
                f"Removed {removed} registration(s); promoted {promoted} from the waitlist.",
            )

        return _confirm_with_reason(
            self,
            request,
            active,
            action="remove_registration",
            title="Remove registrations",
            explanation=(
                "The selected active registrations are marked REMOVED, then free seats are "
                "filled from the waitlist in order. Every change is audit-logged."
            ),
            apply=apply,
        )
