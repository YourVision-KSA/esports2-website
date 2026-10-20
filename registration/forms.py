"""Registration form. Labels come from core/content.py (CLAUDE.md rule 1)."""

from django import forms
from django.core.exceptions import ValidationError

from core.content import CONTENT

from .models import normalize_phone


class RegistrationForm(forms.Form):
    full_name = forms.CharField(max_length=120, label=CONTENT["REG_FIELD_NAME"])
    phone = forms.CharField(max_length=20, label=CONTENT["REG_FIELD_PHONE"])
    email = forms.EmailField(required=False, label=CONTENT["REG_FIELD_EMAIL"])
    game_player_id = forms.CharField(max_length=80)  # label set per game in the view
    consent = forms.BooleanField(label=CONTENT["REG_CONSENT"])

    def __init__(self, *args, game=None, **kwargs):
        super().__init__(*args, **kwargs)
        if game and game.player_id_label_ar:
            self.fields["game_player_id"].label = game.player_id_label_ar
        else:
            self.fields["game_player_id"].label = "Gamer Tag"

    def clean_phone(self):
        try:
            return normalize_phone(self.cleaned_data["phone"])
        except ValidationError:
            raise ValidationError(CONTENT["ERR_RETRY"]) from None
