"""Template context: Arabic content + current phase, available on every page."""

from .content import CONTENT
from .phases import current_phase


def site_context(request):
    return {
        "content": CONTENT,
        "phase": current_phase().value,
    }
