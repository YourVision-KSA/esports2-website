"""Vote-window ops report (docs/voting.md burst detection). Run twice daily
during the vote; the HELD SHARE is the headline metric (alert if > 20%)."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from voting.models import Ballot
from voting.services import tally


class Command(BaseCommand):
    help = "Print vote statistics: totals, held share, top IP hashes/ASNs, hourly rate."

    def handle(self, *args, **options):
        t = tally()
        total = t["counted"] + t["held"] + t["invalidated"]
        held_share = (t["held"] / total * 100) if total else 0.0
        self.stdout.write(
            f"total={total} counted={t['counted']} held={t['held']} invalidated={t['invalidated']}"
        )
        line = f"HELD SHARE: {held_share:.1f}%"
        self.stdout.write(self.style.ERROR(line) if held_share > 20 else line)

        self.stdout.write("\nCounted votes per game:")
        for row in t["choices"]:
            self.stdout.write(f"  {row['game__slug']}: {row['votes']}")

        self.stdout.write("\nTop 20 ip_hash by ballot count:")
        top_ips = Ballot.objects.values("ip_hash").annotate(n=Count("id")).order_by("-n")[:20]
        for row in top_ips:
            self.stdout.write(f"  {row['ip_hash'][:16]}…: {row['n']}")

        self.stdout.write("\nTop ASNs:")
        top_asn = (
            Ballot.objects.exclude(asn=None)
            .values("asn")
            .annotate(n=Count("id"))
            .order_by("-n")[:10]
        )
        for row in top_asn:
            self.stdout.write(f"  AS{row['asn']}: {row['n']}")

        self.stdout.write("\nBallots in the last 24h by hour:")
        day_ago = timezone.now() - timedelta(hours=24)
        recent = Ballot.objects.filter(created_at__gte=day_ago)
        by_hour: dict[str, int] = {}
        for b in recent.values_list("created_at", flat=True):
            key = b.astimezone().strftime("%H:00")
            by_hour[key] = by_hour.get(key, 0) + 1
        for hour in sorted(by_hour):
            self.stdout.write(f"  {hour}: {by_hour[hour]}")
