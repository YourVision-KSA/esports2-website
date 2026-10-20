"""Draw the bracket for a game: python manage.py draw_bracket <slug> [--seed N]"""

from django.core.management.base import BaseCommand, CommandError

from core.models import Game

from ...draw import draw


class Command(BaseCommand):
    help = "Random draw: seed the single-elimination bracket for a confirmed game."

    def add_arguments(self, parser):
        parser.add_argument("slug")
        parser.add_argument(
            "--seed", type=int, default=None, help="RNG seed (recorded in the audit log)"
        )

    def handle(self, *args, **options):
        try:
            game = Game.objects.get(slug=options["slug"], status=Game.Status.CONFIRMED)
        except Game.DoesNotExist as exc:
            raise CommandError("no confirmed game with that slug") from exc
        try:
            matches = draw(game, seed=options["seed"])
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"{game.slug}: {len(matches)} matches created (seed={options['seed']})"
            )
        )
