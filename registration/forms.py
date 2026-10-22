"""Registration form. Labels come from core/content.py (CLAUDE.md rule 1)."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.html import format_html

from core.content import CONTENT

from .models import normalize_phone


def _consent_label():
    """REG-CONSENT exactly as written, with «سياسة الخصوصية» linked to /privacy/
    (new tab, so a half-filled form is not lost)."""
    text, link = CONTENT["REG_CONSENT"], CONTENT["PRIVACY_TITLE"]
    if link not in text:
        return text
    before, after = text.split(link, 1)
    return format_html(
        '{}<a href="/privacy/" target="_blank" rel="noopener">{}</a>{}', before, link, after
    )


class RegistrationForm(forms.Form):
    full_name = forms.CharField(max_length=120, label=CONTENT["REG_FIELD_NAME"])
    phone = forms.CharField(max_length=20, label=CONTENT["REG_FIELD_PHONE"])
    email = forms.EmailField(required=False, label=CONTENT["REG_FIELD_EMAIL"])
    game_player_id = forms.CharField(max_length=80)  # label set per game in the view
    consent = forms.BooleanField(label=CONTENT["REG_CONSENT"])

    def __init__(self, *args, game=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["consent"].label = _consent_label()
        if game and game.player_id_label_ar:
            self.fields["game_player_id"].label = game.player_id_label_ar
        else:
            self.fields["game_player_id"].label = "Gamer Tag"

    def clean_phone(self):
        try:
            return normalize_phone(self.cleaned_data["phone"])
        except ValidationError:
            raise ValidationError(CONTENT["ERR_RETRY"]) from None
