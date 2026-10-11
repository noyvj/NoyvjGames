"""GI-25: cosmetic region skins, unlocked by achievements, chosen in Settings."""

import json
import sys
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


def _fake_storage(initial=None):
    store = dict(initial or {})

    class Storage:
        def getItem(self, key):
            return store.get(key)

        def setItem(self, key, value):
            store[key] = value

    sys.modules["js"].localStorage = Storage()
    return store


def _earn(game_env, achievement_id):
    """Earn an achievement the cheap honest way where one exists, else by setting what it checks."""
    region = game_env.region
    if achievement_id == "full_capacity_portfolio":
        for kind in ("housing", "services", "infrastructure"):
            game_env.invest(kind)
    elif achievement_id == "turning_point_reached":
        region.net_positive_round = 5
    elif achievement_id == "crisis_averted":
        region.round_number = 22
    elif achievement_id == "thriving_region":
        region.funds = 5000.0
        region.total_arrivals = 10.0
        region.integrated_population = 10.0
    game_env.module._check_new_achievements_for_toast()


def test_dusk_is_open_and_the_other_four_start_locked(game_env):
    m = game_env.module
    assert [s["id"] for s in m.SKINS] == ["dusk", "seaside", "alpine", "desert", "neon"]
    assert m.skin_unlocked("dusk")
    assert not any(m.skin_unlocked(s["id"]) for s in m.SKINS[1:])
    assert not m.skin_unlocked("nonsense")


def test_every_skin_unlocks_with_a_real_achievement(game_env):
    ids = {entry["id"] for entry in game_env.module.ACHIEVEMENTS}
    for skin in game_env.module.SKINS[1:]:
        assert skin["unlock"] in ids


def test_locked_buttons_say_how_to_open_them(game_env):
    game_env.module.render()
    button = game_env.elements["skin-seaside-button"]
    assert button.disabled and button.innerText.startswith("🔒")
    assert "Full Portfolio" in button.title
    assert not game_env.elements["skin-dusk-button"].disabled


def test_earning_the_achievement_unlocks_the_skin_and_says_so(game_env):
    _fake_storage()
    _earn(game_env, "full_capacity_portfolio")
    m = game_env.module
    assert m.skin_unlocked("seaside")
    assert "Seaside" in game_env.elements["skin-note"].innerText
    button = game_env.elements["skin-seaside-button"]
    assert not button.disabled and not button.innerText.startswith("🔒")


def test_each_skin_unlocks_from_its_own_achievement_only(game_env):
    _fake_storage()
    _earn(game_env, "turning_point_reached")
    m = game_env.module
    assert m.skin_unlocked("alpine") and not m.skin_unlocked("neon") and not m.skin_unlocked("desert")


def test_choosing_a_skin_sets_the_skyline_and_the_pressed_button(game_env):
    store = _fake_storage()
    _earn(game_env, "full_capacity_portfolio")
    game_env.elements["skin-seaside-button"].dispatch("click", None)
    assert game_env.elements["region-visual"].dataset.skin == "seaside"
    assert game_env.elements["skin-seaside-button"].getAttribute("aria-pressed") == "true"
    assert game_env.elements["skin-dusk-button"].getAttribute("aria-pressed") == "false"
    assert store["drift-skin"] == "seaside"


def test_a_locked_skin_cannot_be_chosen(game_env):
    _fake_storage()
    assert game_env.module.choose_skin("neon") is False
    game_env.elements["skin-neon-button"].dispatch("click", None)
    assert game_env.elements["region-visual"].dataset.skin == "dusk"


def test_the_dusk_button_goes_back(game_env):
    _fake_storage()
    _earn(game_env, "full_capacity_portfolio")
    game_env.module.choose_skin("seaside")
    game_env.elements["skin-dusk-button"].dispatch("click", None)
    assert game_env.elements["region-visual"].dataset.skin == "dusk"


def test_unlocks_persist_in_the_browser_and_are_validated(game_env):
    store = _fake_storage()
    _earn(game_env, "full_capacity_portfolio")
    assert json.loads(store["drift_skins_v1"]) == ["seaside"]
    m = game_env.module
    assert m._clean_skin_unlocks(["neon", "dusk", "bogus", 7, "alpine"]) == ["alpine", "neon"]
    assert m._clean_skin_unlocks("junk") == [] and m._clean_skin_unlocks(None) == []


def test_a_loaded_save_with_the_achievement_unlocks_quietly(game_env):
    _fake_storage()
    _earn(game_env, "full_capacity_portfolio")
    state = json.loads(json.dumps(game_env.module.get_state()))
    game_env.module.skins_unlocked.clear()
    game_env.module.skin_note = ""
    game_env.module.load_state(state)
    assert game_env.module.skin_unlocked("seaside")
    assert game_env.elements["skin-note"].innerText == ""  # no announcement for a loaded save


def test_the_choice_never_rides_the_save(game_env):
    _fake_storage()
    _earn(game_env, "full_capacity_portfolio")
    game_env.module.choose_skin("seaside")
    assert "skin" not in json.dumps(game_env.module.get_state())


def test_css_has_a_palette_for_every_skin_and_reset_returns_to_dusk():
    css = (GAME_DIR / "style.css").read_text(encoding="utf-8")
    for skin in ("seaside", "alpine", "desert", "neon"):
        assert f'.region-visual[data-skin="{skin}"]' in css
    js = (GAME_DIR / "settings.js").read_text(encoding="utf-8")
    assert 'getElementById("skin-dusk-button")' in js
