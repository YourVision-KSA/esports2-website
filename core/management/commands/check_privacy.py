"""List the unfilled [placeholders] in the privacy notice (core/privacy.py).

    python manage.py check_privacy

Exit status 1 while any remain — registration cannot open until this prints "complete".
Fill them in docs/content-ar.md first (the source of truth), then core/content.py.
"""

from django.core.management.base import BaseCommand, CommandError

from core import privacy


class Command(BaseCommand):
    help = "List unfilled placeholders in the privacy notice (exit 1 if any)."

    def handle(self, *args, **options):
        missing = privacy.unfilled_placeholders()
        if not missing:
            self.stdout.write(self.style.SUCCESS("Privacy notice complete: no placeholders."))
            return
        for key, placeholder in missing:
            self.stdout.write(f"{key}: {placeholder}")
        raise CommandError(
            f"{len(missing)} placeholder(s) left — registration stays closed until they are "
            "filled (owner decisions DEC-08/DEC-09)."
        )
