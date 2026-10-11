"""GG-18 map skins unlocked by achievements; GG-14 the secret Snow Leopard achievement."""

import json
import sys

from .fakes import FakeStorage


def _storage(initial=None):
    storage = FakeStorage(initial)
    sys.modules["js"].localStorage = storage
    return storage


def _earn(game, achievement_id, monkeypatch):
    monkeypatch.setitem(game.ACHIEVEMENT_CHECKS, achievement_id, lambda: True)


def test_default_skin_only_at_the_start(game_env):
    m = game_env.module
    assert m.current_skin == "default"
    assert m.skin_available("default")
    for skin_id in ("aurora", "dusk", "pixel", "leopard"):
        assert not m.skin_available(skin_id)
    assert game_env.elements["game"].attributes["data-skin"] == "default"
    assert "1 of 5 map skins unlocked" in game_env.elements["skin-note"].innerText


def test_locked_skin_cannot_be_chosen_and_options_say_what_unlocks_it(game_env):
    m = game_env.module
    assert m.set_skin("aurora") is False
    assert m.set_skin("nonsense") is False
    html = game_env.elements["skin-select"].innerHTML
    assert 'value="aurora" disabled' in html
    assert "locked: Half Shield" in html
    assert "locked: The Long Haul" in html
    assert "locked: Deep Reserves" in html
    assert "locked: Snow Leopard" in html


def test_each_skin_follows_its_named_achievement(game_env, monkeypatch):
    m = game_env.module
    storage = _storage()
    pairs = {"aurora": "half_dampening", "dusk": "long_haul", "pixel": "well_funded", "leopard": "snow_leopard"}
    assert {sid: ach for sid, _n, ach in m.SKINS if ach} == pairs
    for skin_id, achievement in pairs.items():
        _earn(m, achievement, monkeypatch)
        m.render()
        assert m.skin_available(skin_id)
    assert set(json.loads(storage.data[m.SKIN_UNLOCKS_KEY])) == set(pairs)
    assert "Every skin is yours" in game_env.elements["skin-note"].innerText


def test_choice_applies_persists_and_survives_a_fresh_load(game_env, monkeypatch):
    m = game_env.module
    storage = _storage()
    _earn(m, "half_dampening", monkeypatch)
    m.render()
    game_env.elements["skin-select"].value = "aurora"
    game_env.elements["skin-select"].dispatch("change", None)
    assert m.current_skin == "aurora"
    assert game_env.elements["game"].attributes["data-skin"] == "aurora"
    assert storage.data[m.SKIN_KEY] == "aurora"
    m.load_skins()
    assert m.current_skin == "aurora"


def test_unlocks_are_kept_for_good_on_this_device(game_env, monkeypatch):
    m = game_env.module
    _storage()
    _earn(m, "well_funded", monkeypatch)
    m.render()
    monkeypatch.setitem(m.ACHIEVEMENT_CHECKS, "well_funded", lambda: False)  # funds fell again
    m.render()
    assert m.skin_available("pixel")


def test_stored_values_are_cleaned(game_env):
    m = game_env.module
    _storage({m.SKIN_KEY: "aurora", m.SKIN_UNLOCKS_KEY: json.dumps(["aurora", "default", 7, "bogus"])})
    m.load_skins()
    assert m.skins_unlocked == {"aurora"}
    assert m.current_skin == "aurora"
    _storage({m.SKIN_KEY: "pixel", m.SKIN_UNLOCKS_KEY: "{broken"})
    m.load_skins()
    assert m.skins_unlocked == set() and m.current_skin == "default"
    _storage({m.SKIN_KEY: "leopard"})
    m.load_skins()
    assert m.current_skin == "default"  # a skin that is not unlocked is never worn


def test_toast_names_the_skin_an_achievement_opened(game_env, monkeypatch):
    m = game_env.module
    _storage()
    m._seed_achievement_toast_baseline()
    _earn(m, "half_dampening", monkeypatch)
    m.render()
    m._check_new_achievements_for_toast()
    text = game_env.elements["achievement-toast-text"].innerText
    assert "Half Shield" in text and "Aurora borealis map skin" in text


def test_loading_a_save_does_not_announce_skins(game_env, monkeypatch):
    m = game_env.module
    _storage()
    _earn(m, "long_haul", monkeypatch)
    m.render()
    m._seed_achievement_toast_baseline()
    game_env.elements["achievement-toast-text"].innerText = ""
    m._check_new_achievements_for_toast()
    assert game_env.elements["achievement-toast-text"].innerText == ""
    assert m._skin_announcements == []


def test_snow_leopard_needs_round_20_and_an_eight_degree_lead(game_env):
    m = game_env.module
    assert any(a["id"] == "snow_leopard" for a in m.ACHIEVEMENTS)
    assert "snow_leopard" not in m.achievement_ids_earned()
    for _ in range(m.SNOW_LEOPARD_MIN_ROUND + 2):
        for _ in range(8):
            game_env.invest("preserve")
        game_env.advance_round()
        if m.region.round_number < m.SNOW_LEOPARD_MIN_ROUND:
            assert "snow_leopard" not in m.achievement_ids_earned()
    assert m.region_d.temperature - m.region.temperature >= m.SNOW_LEOPARD_GAP
    assert "snow_leopard" in m.achievement_ids_earned()
    assert m.skin_available("leopard")


def test_no_lead_no_snow_leopard(game_env):
    m = game_env.module
    for _ in range(m.SNOW_LEOPARD_MIN_ROUND + 2):
        game_env.advance_round()
    assert m.region.round_number >= m.SNOW_LEOPARD_MIN_ROUND
    assert "snow_leopard" not in m.achievement_ids_earned()


def test_every_catalog_entry_has_a_check_and_a_glyph(game_env):
    m = game_env.module
    for entry in m.ACHIEVEMENTS:
        assert entry["id"] in m.ACHIEVEMENT_CHECKS
        assert entry["id"] in m.ACHIEVEMENT_GLYPHS
