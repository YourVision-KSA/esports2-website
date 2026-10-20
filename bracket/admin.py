"""Match admin — the referee fallback (cut-list item 6) and the admin correction
path. Direct field edits are blocked; results go through the audited services."""

from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import Match
from .services import CorrectionBlocked, correct_result


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("game", "round", "slot", "player1", "player2", "winner", "score_text", "status")
    list_filter = ("game", "round", "status")
    readonly_fields = (
        "game",
        "round",
        "slot",
        "next_match",
        "next_slot",
        "player1",
        "player2",
        "status",
    )
    fields = readonly_fields + ("winner", "score_text")

    def has_add_permission(self, request):
        return False  # matches are created only by the draw command

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        """Route edits through the audited correction service (admin-only)."""
        if not request.user.is_superuser:
            self.message_user(request, "Result corrections are admin-only.", level=40)
            return
        if not obj.winner:
            return
        try:
            correct_result(obj, obj.winner, obj.score_text, actor=request.user)
        except CorrectionBlocked:
            self.message_user(
                request,
                "Blocked: the next match is already played. Fix downstream first.",
                level=40,
            )
        except ValidationError as exc:
            self.message_user(request, f"Refused: {exc}", level=40)
