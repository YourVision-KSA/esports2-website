"""Small presentation helpers for the Arena Night templates."""

from django import template
from django.contrib.staticfiles.finders import find

register = template.Library()

# Per-game accent for the card rule (docs/frontend.md rev 4: cyan / magenta / gold cycle).
_ACCENTS = ["var(--accent)", "var(--accent-2)", "var(--gold)"]


@register.filter
def game_image(game):
    """Static path of the game-evoking card image; falls back to the default.
    Images are placeholders the owner can swap (docs/frontend.md imagery rule)."""
    path = f"img/games/{game.slug}.jpg"
    return path if find(path) else "img/games/default.jpg"


@register.filter
def accent(counter0):
    return _ACCENTS[counter0 % len(_ACCENTS)]
