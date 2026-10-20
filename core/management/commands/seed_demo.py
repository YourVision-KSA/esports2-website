"""Seed local development data: the candidate games and a vote-phase SiteConfig.

Game display names are DRAFT strings from docs/content-ar.md (GAME-RL/FIFA/COD)
pending the owner's wording and the vote result. Never run in production.
"""

from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import Game, SiteConfig

GAMES = [
    # (slug, name_ar [DRAFT], name_en, platform, player-ID label [DRAFT])
    ("rocket-league", "روكيت ليج", "Rocket League", "PS5", "معرّف Epic"),
    ("fifa", "فيفا", "EA SPORTS FC", "PS5", "معرّف EA"),
    ("call-of-duty", "كول أوف ديوتي", "Call of Duty", "PC", "معرّف Activision"),
    ("tekken", "تيكن", "Tekken 8", "PS5", "معرّف اللاعب"),
    ("valorant", "فالورانت", "Valorant", "PC", "معرّف Riot"),
]


class Command(BaseCommand):
    help = "Create candidate games and open the vote window (local dev only)."

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demo is for local development only (DEBUG=True).")
        for slug, name_ar, name_en, platform, label in GAMES:
            game, created = Game.objects.get_or_create(
                slug=slug,
                defaults=dict(
                    name_ar=name_ar, name_en=name_en, platform=platform, player_id_label_ar=label
                ),
            )
            self.stdout.write(f"{'created' if created else 'exists '}: {slug}")
        cfg = SiteConfig.get_solo()
        now = timezone.now()
        cfg.vote_opens_at = now - timedelta(hours=1)
        cfg.vote_closes_at = now + timedelta(days=7)
        cfg.registration_opens_at = now + timedelta(days=14)
        cfg.registration_closes_at = now + timedelta(days=21)
        cfg.save()
        self.stdout.write(self.style.SUCCESS("Phase: VOTE (open for 7 days)."))
