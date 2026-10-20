"""End-of-life PII purge (docs/data-model.md → Retention, docs/operations.md).

Run at the published retention deadline. Keeps: Game, Match structure, AuditLog.
Removes: player PII, invitation contacts, outbox bodies, ballot signals.
Winner display keeps the gamer tag only (per the privacy notice — DEC-08).
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import OutboxEmail
from invitations.models import Invitation
from registration.models import Player
from voting.models import Ballot


class Command(BaseCommand):
    help = "Delete personal data at the retention deadline. IRREVERSIBLE."

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true", help="confirm the purge")

    @transaction.atomic
    def handle(self, *args, **options):
        if not options["yes"]:
            self.stderr.write("Refusing to run without --yes (this is irreversible).")
            return
        n_players = Player.objects.count()
        # Anonymize players: keep row + gamer-tag display on brackets, drop PII.
        for i, player in enumerate(Player.objects.all(), start=1):
            player.full_name = f"player-{i}"
            player.phone = f"purged-{i}"
            player.email = ""
            player.manage_token_hash = f"purged-{i}"
            player.save(update_fields=["full_name", "phone", "email", "manage_token_hash"])
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
