"""Privacy notice (/privacy/, DEC-08): reachable from everywhere data is collected, cached
like other content pages, and the consent wording itself stays exactly as approved."""

import pytest

from conftest import set_phase
from core.content import CONTENT
from core.phases import Phase
from registration.forms import RegistrationForm

pytestmark = pytest.mark.django_db


def test_privacy_page_renders_all_sections_and_is_cacheable(client):
    response = client.get("/privacy/")
    assert response.status_code == 200
    body = response.content.decode()
    for title, paragraphs in CONTENT["PRIVACY_SECTIONS"]:
        assert title in body
        for p in paragraphs:
            assert p in body
    assert "Set-Cookie" not in response.headers  # edge-cached content page (rule 8)
    assert "max-age=60" in response["Cache-Control"]
    assert "csrfmiddlewaretoken" not in body


def test_consent_label_links_to_privacy_without_changing_the_text():
    label = str(RegistrationForm().fields["consent"].label)
    assert 'href="/privacy/"' in label and 'target="_blank"' in label
    plain = label.replace('<a href="/privacy/" target="_blank" rel="noopener">', "").replace(
        "</a>", ""
    )
    assert plain == CONTENT["REG_CONSENT"]


def test_consent_is_still_required():
    form = RegistrationForm(
        data={"full_name": "لاعب", "phone": "0550000001", "game_player_id": "tag"}
    )
    assert not form.is_valid() and "consent" in form.errors


def test_privacy_linked_from_footer_and_vote_page(client, phase_vote, candidate_games):
    set_phase(Phase.VOTE)
    assert 'href="/privacy/"' in client.get("/").content.decode()
    assert 'href="/privacy/"' in client.get("/vote/").content.decode()
