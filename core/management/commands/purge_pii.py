"""End-of-life PII purge (docs/data-model.md → Retention, docs/operations.md).

Run at the published retention deadline. Keeps: Game, Match structure, AuditLog.
Removes: player PII, invitation contacts, outbox bodies, ballot signals, registration
attempt hashes. Winner display keeps the gamer tag only (per the privacy notice — DEC-08).

Safety (audit 2026-11-13): refuses unless the site is in the ARCHIVE phase (or --force),
so it cannot wipe names and phones mid-event; placeholders use the row's primary key, so
a second run cannot collide with the unique columns; gamer tags of registrations that are
no longer active (withdrawn/removed — never shown on a bracket) are blanked too.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from core.models import OutboxEmail
from core.phases import Phase, current_phase
from invitations.models import Invitation
from registration.models import Player, Registration, RegistrationAttempt
from voting.models import Ballot


class Command(BaseCommand):
    help = "Delete personal data at the retention deadline. IRREVERSIBLE."

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true", help="confirm the purge")
        parser.add_argument(
            "--force",
            action="store_true",
            help="run even though the site is not archived (staging/rehearsal only)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if not options["yes"]:
            self.stderr.write("Refusing to run without --yes (this is irreversible).")
            return
        if current_phase() != Phase.ARCHIVE and not options["force"]:
            raise CommandError(
                "Refusing: the site is not archived (SiteConfig.archived). Archive first, "
                "or pass --force on a staging copy."
            )
        n_players = Player.objects.count()
        # Anonymize players: keep row + gamer-tag display on brackets, drop PII.
        for player in Player.objects.all():
            player.full_name = f"player-{player.pk}"
            player.phone = f"purged-{player.pk}"
            player.email = ""
            player.manage_token_hash = f"purged-{player.pk}"
            player.save(update_fields=["full_name", "phone", "email", "manage_token_hash"])
        Registration.objects.exclude(status__in=Registration.ACTIVE).update(game_player_id="")
        RegistrationAttempt.objects.all().delete()
        n_inv = Invitation.objects.count()
        Invitation.objects.all().update(
            guest_name="purged", organization="", contact_email="", contact_phone=""
        )
        n_mail = OutboxEmail.objects.count()
        OutboxEmail.objects.all().delete()
        Ballot.objects.all().update(signals=None)
        self.stdout.write(
            self.style.SUCCESS(
                f"Purged PII: {n_players} players anonymized, "
                f"{n_inv} invitations scrubbed, {n_mail} outbox rows deleted."
            )
        )
        self.stdout.write("Remember: delete SIGNALS_SALT from the environment now.")
