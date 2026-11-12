"""Enroll a staff user in TOTP 2FA from the command line (docs/operations.md step 8).

In production the admin uses OTPAdminSite (esports/urls.py), which refuses login to any
user without a *confirmed* TOTP device — so the first device cannot be added through the
admin itself. This command breaks that chicken-and-egg: run it INTERACTIVELY (locally, against
the production database through the Cloud SQL Auth Proxy — docs/operations.md step 8), scan
or type the printed otpauth:// URL into an authenticator app, then log in normally.

The URL contains the permanent TOTP secret. Audit 2026-11-13: it must never reach a log
(a Cloud Run job's stdout goes to Cloud Logging and is kept there). So the URL is printed
only to an interactive terminal; anywhere else the command refuses unless --url-file is
given, which writes the URL to a new file readable only by its owner.

Usage: python manage.py enroll_totp <username> [--url-file PATH]
Re-running for a user who already has a confirmed device refuses, unless --replace is
given (rotating a device after suspected compromise — see docs/operations.md runbook).
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django_otp.plugins.otp_totp.models import TOTPDevice


class Command(BaseCommand):
    help = "Create a staff TOTP device; show its otpauth:// URL (terminal or --url-file)."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument(
            "--url-file",
            help="Write the otpauth:// URL to this NEW file (mode 0600) instead of the terminal.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete the user's existing TOTP devices first (device rotation).",
        )

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist:
            raise CommandError(f"No user named {options['username']!r}.") from None
        if not user.is_staff:
            raise CommandError(f"{user.username!r} is not staff; refusing to enroll.")

        url_file = options.get("url_file")
        if not url_file and not self.stdout.isatty():
            raise CommandError(
                "Refusing to print the TOTP secret to a non-interactive output (it would end "
                "up in logs). Run this in a terminal, or pass --url-file PATH."
            )
        if url_file and os.path.exists(url_file):
            raise CommandError(f"{url_file} already exists; choose a new path.")

        existing = TOTPDevice.objects.filter(user=user)
        if existing.exists():
            if not options["replace"]:
                raise CommandError(
                    f"{user.username!r} already has a TOTP device. Use --replace to rotate it."
                )
            existing.delete()
            self.stdout.write("Existing device(s) deleted.")

        # confirmed=True: the printed URL is handed to the user directly, there is no
        # separate confirmation step (the admin's own confirm flow is unreachable here).
        device = TOTPDevice.objects.create(user=user, name="default", confirmed=True)
        self.stdout.write(f"TOTP device created for {user.username!r}.")
        if url_file:
            # O_EXCL: never overwrite an existing file; 0600: owner-only.
            fd = os.open(url_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as fh:
                fh.write(device.config_url + "\n")
            self.stdout.write(f"Setup URL written to {url_file} — add it to an authenticator")
            self.stdout.write("app, then DELETE the file.")
        else:
            self.stdout.write("Add it to an authenticator app via this URL (or type the key):")
            self.stdout.write(device.config_url)
        self.stdout.write(self.style.SUCCESS("Done. The user can now log in at /staff/."))
