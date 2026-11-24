"""Player door check-in fields (entry badges, 2026-11-24).

Three steps on purpose: a unique column with a callable default would give every
EXISTING row the same value (Django evaluates the default once for the ALTER), so the
column arrives nullable, each existing player gets their own token, then the unique
constraint + default land.
"""

from django.conf import settings
from django.db import migrations, models

import registration.models


def fill_tokens(apps, schema_editor):
    Player = apps.get_model("registration", "Player")
    for player in Player.objects.filter(checkin_token__isnull=True).iterator():
        player.checkin_token = registration.models.new_checkin_token()
        player.save(update_fields=["checkin_token"])


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("registration", "0003_player_phone_normalized"),
    ]

    operations = [
        migrations.AddField(
            model_name="player",
            name="checkin_token",
            field=models.CharField(max_length=48, null=True),
        ),
        migrations.RunPython(fill_tokens, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="player",
            name="checkin_token",
            field=models.CharField(
                max_length=48, unique=True, default=registration.models.new_checkin_token
            ),
        ),
        migrations.AddField(
            model_name="player",
            name="checked_in_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="player",
            name="checked_in_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
