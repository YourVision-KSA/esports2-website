"""Deliver due outbox emails. Local/manual equivalent of the scheduler tick."""

from django.core.management.base import BaseCommand

from core.outbox import send_due


class Command(BaseCommand):
    help = "Send due OutboxEmail rows (retries handled automatically)."

    def handle(self, *args, **options):
        sent = send_due()
        self.stdout.write(self.style.SUCCESS(f"sent {sent} email(s)"))
