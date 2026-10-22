"""Hero 3D outcome report: python manage.py tier_report [--days 7]

Prints, per day and device class, how visitors ended up: 3D (high/mid) vs poster
(low = slow device, fallback = WebGL/bundle failure, reduced = reduced-motion setting).
Watch the mobile FALLBACK share — a rise means a 3D regression (docs/operations.md)."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import TierStat

COLUMNS = ["high", "mid", "low", "fallback", "reduced"]


class Command(BaseCommand):
    help = "Daily hero-3D tier/fallback counts per device class (count-only beacon)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=7)

    def handle(self, *args, **options):
        since = timezone.localdate() - timedelta(days=options["days"] - 1)
        rows = TierStat.objects.filter(day__gte=since)
        table: dict[tuple, dict[str, int]] = {}
        for r in rows:
            table.setdefault((r.day, r.device), dict.fromkeys(COLUMNS, 0))[r.outcome] = r.count
        header = f"{'day':<11}{'device':<9}" + "".join(f"{c:>9}" for c in COLUMNS)
        self.stdout.write(header + f"{'total':>8}{'fallback%':>11}")
        for (day, device), counts in sorted(table.items()):
            total = sum(counts.values())
            share = 100 * counts["fallback"] / total if total else 0
            line = f"{day!s:<11}{device:<9}" + "".join(f"{counts[c]:>9}" for c in COLUMNS)
            self.stdout.write(line + f"{total:>8}{share:>10.1f}%")
        if not table:
            self.stdout.write("(no beacons in this period)")
