"""F-11 Beginner / Standard / Expert profiles."""

from pathlib import Path
from .pagefiles import game_css, page_text

HERE = Path(__file__).resolve().parent.parent


def _set(env, profile):
    env.local_storage.setItem("herd-profile", profile)
    env.elements["profile-select"].value = profile
    env.elements["profile-select"].dispatch("change", None)


def test_standard_is_the_default_and_shows_no_hint(game_env):
    m = game_env.module
    m.render()
    assert m.current_profile() == "standard"
    assert game_env.elements["next-lever-hint"].hidden is True and game_env.elements["next-lever-hint"].innerText == ""


def test_beginner_gets_a_hint_and_it_names_the_best_value_lever(game_env):
    m = game_env.module
    game_env.farm.herd_size = 5
    game_env.farm.funds = 200.0
    _set(game_env, "beginner")
    hint = game_env.elements["next-lever-hint"]
    assert hint.hidden is False and hint.innerText.startswith("Suggestion:")
    best = max(m.HINT_LEVERS, key=lambda k: game_env.farm.methane_saved_by(k) / game_env.farm.decoupling_cost(k))
    assert m.DECOUPLING_MEASURES[best]["label"] in hint.innerText


def test_the_hint_has_a_sensible_answer_for_every_situation(game_env):
    m = game_env.module
    assert "Grow Herd" in m.next_lever_hint()
    game_env.farm.herd_size = 3
    game_env.farm.funds = 0.0
    assert "Advance Round" in m.next_lever_hint()
    game_env.farm.funds = 100.0
    assert "Feed Additives" in m.next_lever_hint() or "Herd Caps" in m.next_lever_hint() or "Capture" in m.next_lever_hint()
    game_env.farm.decoupling_investment.update({"feed": 20, "caps": 20, "capture": 20})
    assert m.next_lever_hint().startswith("Suggestion:")


def test_the_hint_never_changes_the_farm(game_env):
    game_env.farm.herd_size = 4
    game_env.farm.funds = 150.0
    before = (game_env.farm.funds, dict(game_env.farm.decoupling_investment), list(game_env.farm.lever_log))
    game_env.module.next_lever_hint()
    assert (game_env.farm.funds, dict(game_env.farm.decoupling_investment), list(game_env.farm.lever_log)) == before


def test_expert_and_standard_show_no_hint(game_env):
    _set(game_env, "beginner")
    _set(game_env, "expert")
    assert game_env.elements["next-lever-hint"].hidden is True
    _set(game_env, "standard")
    assert game_env.elements["next-lever-hint"].hidden is True


def test_junk_in_storage_means_standard(game_env):
    game_env.local_storage.setItem("herd-profile", "godmode")
    assert game_env.module.current_profile() == "standard"


def test_the_choice_is_never_in_a_save(game_env):
    _set(game_env, "beginner")
    assert "profile" not in str(game_env.module.get_state())


def test_expert_css_layer_and_js_and_pages():
    css = game_css()
    for selector in (".grow-consequence-preview", ".invest-efficiency", ".info-toggle"):
        assert f'html[data-profile="expert"] {selector}' in css
    js = (HERE / "settings.js").read_text(encoding="utf-8")
    assert 'data-profile' in js and 'applyProfile("standard")' in js
    for page in ("index.html", "pc.html"):
        html = page_text(page)
        assert 'id="profile-select"' in html and 'id="next-lever-hint"' in html
