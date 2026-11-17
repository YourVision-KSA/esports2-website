"""Strip the ballots' `signals` JSON 14 days after the vote closes (docs/voting.md →
Privacy; promised in the privacy notice, PRIVACY-S7-P2). Status, hashes and reasons stay
for the audit trail. Audit 2026-11-13: the notice promised this, but nothing did it.

Run once, any time from 14 days after vote_closes_at (a Cloud Run job, or by hand):
    python manage.py strip_vote_signals
Idempotent. Refuses earlier unless --force (staging only).
"""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core import audit
from core.models import SiteConfig
from voting.models import Ballot

RETENTION = timedelta(days=14)


class Command(BaseCommand):
    help = "Remove ballot signals 14 days after the vote closed (keeps status + hashes)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="ignore the 14-day rule")

    def handle(self, *args, **options):
        closes = SiteConfig.get_solo().vote_closes_at
        due = closes is not None and timezone.now() >= closes + RETENTION
        if not due and not options["force"]:
            raise CommandError(
                "Refusing: the vote closed less than 14 days ago (or has no close time). "
                "Ballot signals are still needed for review."
            )
        n = Ballot.objects.exclude(signals=None).update(signals=None)
        audit.record(None, "ballot.strip_signals", model="voting.Ballot", object_id=f"count={n}")
        self.stdout.write(self.style.SUCCESS(f"Stripped signals from {n} ballot(s)."))
