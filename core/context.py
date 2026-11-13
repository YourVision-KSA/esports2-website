"""Template context: Arabic content + current phase + config, on every page."""

from . import privacy
from .content import CONTENT
from .models import SiteConfig
from .phases import Phase, current_phase


def site_context(request):
    config = SiteConfig.get_solo()
    phase = current_phase(config=config)
    return {
        "content": CONTENT,
        "phase": phase.value,
        # Same gate as the registration views (registration/views._registration_open):
        # REGISTRATION phase AND a complete privacy notice. Templates use this — not
        # `phase` — to decide whether to show links into /register/.
        "registration_open": phase == Phase.REGISTRATION and privacy.notice_complete(),
        "site_config": config,
    }
