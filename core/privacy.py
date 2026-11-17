"""Privacy-notice completeness gate (audit 2026-11-13, finding 4; DEC-08/DEC-09).

The notice at /privacy/ is linked from the registration consent checkbox. While any of its
strings still contains a [bracketed placeholder] (data controller, contact email,
retention period, hosting confirmation, under-18 policy, publish date), consent given on
the form is not informed — so registration stays CLOSED, whatever SiteConfig says:

  * registration views treat the phase as closed (GET → closed page, POST → 403);
  * the SiteConfig admin refuses to save a registration opening date, with a message
    listing what is missing;
  * `python manage.py check_privacy` lists the placeholders (exit status 1 while any remain).

The strings themselves stay in core/content.py, copied from docs/content-ar.md (the
source of truth, CLAUDE.md hard rule 1) — fill them there, never here.
"""

import re

from .content import CONTENT

PLACEHOLDER = re.compile(r"\[[^\[\]]+\]")


def _privacy_strings():
    """(label, text) for every published privacy string, in page order."""
    for key, value in CONTENT.items():
        if not key.startswith("PRIVACY_"):
            continue
        if key == "PRIVACY_SECTIONS":
            for n, (title, paragraphs) in enumerate(value, start=1):
                yield f"PRIVACY-S{n}-TITLE", title
                for m, text in enumerate(paragraphs, start=1):
                    yield f"PRIVACY-S{n}-P{m}", text
        else:
            yield key.replace("_", "-"), value


def unfilled_placeholders() -> list[tuple[str, str]]:
    """[(content-ar.md key, placeholder text), ...] — empty when the notice is complete."""
    return [
        (label, match) for label, text in _privacy_strings() for match in PLACEHOLDER.findall(text)
    ]


def notice_complete() -> bool:
    # Looked up through the module so tests can switch the gate (conftest.py).
    import core.privacy

    return not core.privacy.unfilled_placeholders()


STAFF_MESSAGE = (
    "Registration cannot open: the privacy notice (/privacy/) still has unfilled "
    "placeholders. Fill them in docs/content-ar.md and core/content.py first "
    "(owner decisions DEC-08/DEC-09); `python manage.py check_privacy` lists them."
)
