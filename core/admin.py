"""Core admin. SiteConfig changes and every PII export are audit-logged."""

import csv

from django import forms
from django.contrib import admin
from django.forms.models import model_to_dict
from django.http import HttpResponse

from . import audit, privacy
from .models import AuditLog, Game, OutboxEmail, SiteConfig, TierStat

# Spreadsheet apps evaluate a cell that starts with one of these as a formula
# (CSV/formula injection — audit 2026-11-13). Registrants control names and gamer tags.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def csv_safe(value) -> str:
    """Neutralise a cell for Excel/Sheets: a leading quote makes it plain text."""
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(_FORMULA_PREFIXES) else text


def export_csv_action(fields, description="Export selected to CSV (audit-logged)"):
    """Factory for admin CSV export actions. Superuser-only; every export is
    audit-logged (docs/data-model.md). Use for anything containing PII."""

    def export(modeladmin, request, queryset):
        if not request.user.is_superuser:
            modeladmin.message_user(request, "Exports are admin-only.", level=30)
            return None
        audit.record(
            request.user,
            "export.csv",
            model=modeladmin.model._meta.label,
            object_id=f"count={queryset.count()}",
        )
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = "attachment; filename=export.csv"
        writer = csv.writer(response)
        writer.writerow(fields)
        for obj in queryset:
            writer.writerow([csv_safe(getattr(obj, f, "")) for f in fields])
        return response

    export.short_description = description
    export.__name__ = "export_csv"
    return export


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("slug", "name_ar", "status", "seats", "waitlist_cap", "display_order")
    list_editable = ("status", "display_order")
    prepopulated_fields = {"slug": ("name_en",)}


class SiteConfigForm(forms.ModelForm):
    class Meta:
        model = SiteConfig
        fields = [
            "vote_opens_at",
            "vote_closes_at",
            "registration_opens_at",
            "registration_closes_at",
            "event_start_date",
            "event_end_date",
            "archived",
            "stream_url_1",
            "stream_url_2",
            "stream_url_3",
        ]

    def clean_registration_opens_at(self):
        """Refuse to schedule registration while the privacy notice is unfinished
        (core/privacy.py — audit 2026-11-13). The registration views enforce the same
        rule at request time, so this is the early, visible warning for staff."""
        value = self.cleaned_data.get("registration_opens_at")
        if value and not privacy.notice_complete():
            missing = ", ".join(sorted({key for key, _ in privacy.unfilled_placeholders()}))
            raise forms.ValidationError(f"{privacy.STAFF_MESSAGE} Unfilled: {missing}.")
        return value


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    """The phase switch. Every change is audit-logged; only one row ever exists."""

    form = SiteConfigForm

    def has_add_permission(self, request):
        return not SiteConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        before = model_to_dict(SiteConfig.get_solo()) if change else None
        super().save_model(request, obj, form, change)
        audit.record(
            request.user,
            "siteconfig.change",
            obj,
            before={k: str(v) for k, v in (before or {}).items()},
            after={k: str(v) for k, v in model_to_dict(obj).items()},
        )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Read-only: the audit trail is append-only by design."""

    list_display = ("created_at", "actor", "action", "model", "object_id")
    list_filter = ("action", "model")
    search_fields = ("object_id",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OutboxEmail)
class OutboxEmailAdmin(admin.ModelAdmin):
    """Read-only. Bodies can hold a manage link (a credential) until sent; sent bodies
    are blanked by core/outbox.py (audit 2026-11-13). Retrying a failed email = set it
    back to queued with the action below."""

    list_display = ("to_email", "subject", "status", "attempts", "next_attempt_at", "created_at")
    list_filter = ("status",)
    readonly_fields = (
        "to_email",
        "subject",
        "body_text",
        "status",
        "attempts",
        "next_attempt_at",
        "last_error",
        "created_at",
        "updated_at",
    )
    actions = ["retry"]

    def has_add_permission(self, request):
        return False

    @admin.action(description="Retry selected failed emails")
    def retry(self, request, queryset):
        n = queryset.filter(status=OutboxEmail.Status.FAILED).update(
            status=OutboxEmail.Status.QUEUED, attempts=0, next_attempt_at=None
        )
        self.message_user(request, f"{n} email(s) queued again.")


@admin.register(TierStat)
class TierStatAdmin(admin.ModelAdmin):
    """Read-only view of the 3D tier counters (no PII). Trend: manage.py tier_report."""

    list_display = ("day", "device", "outcome", "count")
    list_filter = ("device", "outcome", "day")
    date_hierarchy = "day"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
