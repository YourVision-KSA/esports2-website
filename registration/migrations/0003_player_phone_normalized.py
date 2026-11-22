# Security assessment 2026-11-19, YV-33: strict phone numbers.
#
# 1. Re-normalise any stored phone with the new normalize_phone (e.g. Arabic-Indic
#    digits → ASCII). A row that still cannot be normalised (or whose normalised form
#    collides with another player's) is SKIPPED with a printed "pk + reason" line and
#    makes the constraint below fail loudly — fix it by hand (staff "release phone");
#    nothing is guessed here.
# 2. Add the CHECK constraint so only the normalised form (or the purge/release
#    placeholders) can be stored from now on.

from django.core.exceptions import ValidationError
from django.db import migrations, models


def renormalize(apps, schema_editor):
    from registration.models import normalize_phone

    Player = apps.get_model("registration", "Player")
    for player in Player.objects.exclude(phone__regex=r"^\+9665[0-9]{8}$").exclude(
        phone__regex=r"^(purged|released)-[0-9]+$"
    ):
        try:
            phone = normalize_phone(player.phone)
        except ValidationError:
            # Only the pk — never the number itself — may appear in deploy logs (rule 7).
            print(f"phone-normalise SKIPPED player pk={player.pk}: not a valid Saudi mobile")
            continue
        if Player.objects.filter(phone=phone).exists():
            print(
                f"phone-normalise SKIPPED player pk={player.pk}: normalised form collides "
                "with another player's phone"
            )
            continue
        player.phone = phone
        player.save(update_fields=["phone"])


class Migration(migrations.Migration):
    dependencies = [
        ("registration", "0002_registrationattempt"),
    ]

    operations = [
        migrations.RunPython(renormalize, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="player",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    ("phone__regex", "^\\+9665[0-9]{8}$"),
                    ("phone__regex", "^(purged|released)-[0-9]+$"),
                    _connector="OR",
                ),
                name="player_phone_normalized",
            ),
        ),
    ]
