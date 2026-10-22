"""Core admin. SiteConfig changes and every PII export are audit-logged."""

import csv

from django.contrib import admin
from django.forms.models import model_to_dict
from django.http import HttpResponse

from . import audit
from .models import AuditLog, Game, OutboxEmail, SiteConfig, TierStat


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
            writer.writerow([getattr(obj, f, "") for f in fields])
        return response

    export.short_description = description
    export.__name__ = "export_csv"
    return export


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("slug", "name_ar", "status", "seats", "waitlist_cap", "display_order")
    list_editable = ("status", "display_order")
    prepopulated_fields = {"slug": ("name_en",)}


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    """The phase switch. Every change is audit-logged; only one row ever exists."""

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
    list_display = ("to_email", "subject", "status", "attempts", "next_attempt_at", "created_at")
    list_filter = ("status",)
    readonly_fields = ("attempts", "last_error", "created_at", "updated_at")


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
