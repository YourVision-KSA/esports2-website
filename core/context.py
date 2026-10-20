"""Template context: Arabic content + current phase + config, on every page."""

from .content import CONTENT
from .models import SiteConfig
from .phases import current_phase


def site_context(request):
    config = SiteConfig.get_solo()
    return {
        "content": CONTENT,
        "phase": current_phase(config=config).value,
        "site_config": config,
    }
