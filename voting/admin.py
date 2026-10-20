"""Ballot review admin: bulk hold/count/invalidate, each action audit-logged
(docs/voting.md burst-detection workflow)."""

from django.contrib import admin

from core import audit

from .models import Ballot, BallotChoice


class ChoiceInline(admin.TabularInline):
    model = BallotChoice
    extra = 0
    can_delete = False
    readonly_fields = ("game",)


@admin.register(Ballot)
class BallotAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "held_reason", "turnstile_passed", "asn", "created_at")
    list_filter = ("status", "held_reason", "turnstile_passed")
    search_fields = ("ip_hash", "asn")
    readonly_fields = (
        "token_hash",
        "ip_hash",
        "ua_hash",
        "asn",
        "signals",
        "turnstile_passed",
        "created_at",
    )
    inlines = [ChoiceInline]
    actions = ["mark_counted", "mark_held", "mark_invalidated"]

    def has_add_permission(self, request):
        return False  # ballots are only created by voters

    def _bulk(self, request, queryset, status, action, reason=""):
        for ballot in queryset:
            audit.record(
                request.user,
                action,
                ballot,
                before={"status": ballot.status},
                after={"status": status, "reason": reason},
            )
        updates = {"status": status}
        if status == Ballot.Status.INVALIDATED:
            updates.update(invalidated_reason=reason or "staff_bulk", invalidated_by=request.user)
        queryset.update(**updates)

    @admin.action(description="Mark selected ballots COUNTED (audit-logged)")
    def mark_counted(self, request, queryset):
        self._bulk(request, queryset, Ballot.Status.COUNTED, "ballot.count")

    @admin.action(description="Mark selected ballots HELD (audit-logged)")
    def mark_held(self, request, queryset):
        self._bulk(request, queryset, Ballot.Status.HELD, "ballot.hold", "staff_review")

    @admin.action(description="INVALIDATE selected ballots (audit-logged)")
    def mark_invalidated(self, request, queryset):
        self._bulk(request, queryset, Ballot.Status.INVALIDATED, "ballot.invalidate", "staff_bulk")
