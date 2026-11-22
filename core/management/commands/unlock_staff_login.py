"""Clear the staff-login throttle at once (docs/operations.md → Staff login throttle).

Event-day unlock: when someone hammers a staff username, the per-account throttle keeps
that account locked as long as the failures keep coming. After verifying the real staff
member, run this instead of an ad-hoc shell one-liner; the throttle also clears by
itself STAFF_LOGIN_WINDOW_MINUTES after the failures stop.
"""

from django.core.management.base import BaseCommand

from core.models import StaffLoginFailure


class Command(BaseCommand):
    help = "Delete all stored staff-login failures, clearing the login throttle at once."

    def handle(self, **options):
        deleted, _ = StaffLoginFailure.objects.all().delete()
        self.stdout.write(
            f"Deleted {deleted} failure record(s); the staff login throttle is clear."
        )
