"""Registration admin: waitlist overview, removals with promotion, audited
CSV export, manage-link regeneration."""

from django.contrib import admin

from core import audit, outbox
from core.admin import export_csv_action
from core.content import CONTENT

from . import services
from .models import Player, Registration, new_manage_token


class RegistrationInline(admin.TabularInline):
    model = Registration
    extra = 0
    readonly_fields = ("game", "status", "waitlist_position", "game_player_id", "created_at")
    can_delete = False


@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ("id", "full_name", "phone", "email", "created_at")
    search_fields = ("full_name", "phone", "email")
    readonly_fields = ("manage_token_hash", "consent_at")
    inlines = [RegistrationInline]
    actions = [
        export_csv_action(["id", "full_name", "phone", "email"]),
        "regenerate_manage_link",
    ]

    @admin.action(description="Regenerate manage link (emails it if possible)")
    def regenerate_manage_link(self, request, queryset):
        """For players who lost their link. New token invalidates the old one."""
        for player in queryset:
            raw = new_manage_token()
            player.manage_token_hash = Player.hash_token(raw)
            player.save(update_fields=["manage_token_hash"])
            audit.record(request.user, "player.regenerate_link", player)
            url = f"/r/{raw}/"
            if player.email:
                outbox.queue(
                    player.email,
                    CONTENT["EMAIL_MANAGE_SUBJECT"].format(site_name=CONTENT["SITE_NAME"]),
                    f"{url}",
                )
                self.message_user(request, f"{player.full_name}: link queued to email.")
            else:
                self.message_user(request, f"{player.full_name}: {url}")


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "game_player_id",
        "game",
        "status",
        "waitlist_position",
        "player",
        "created_at",
    )
    list_filter = ("game", "status")
    search_fields = ("game_player_id", "player__full_name", "player__phone")
    actions = [
        export_csv_action(["id", "game_player_id", "status", "waitlist_position"]),
        "remove_registration",
    ]

    @admin.action(description="Remove registration (promotes the waitlist, audited)")
    def remove_registration(self, request, queryset):
        for registration in queryset.filter(status__in=Registration.ACTIVE):
            services.withdraw(registration, actor=request.user)
            registration.refresh_from_db()
            registration.status = Registration.Status.REMOVED
            registration.save(update_fields=["status"])
            audit.record(request.user, "registration.remove", registration)
