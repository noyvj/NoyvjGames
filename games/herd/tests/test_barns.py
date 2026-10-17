"""GF-17: cosmetic barn styles unlocked by achievements. Pure looks: no number may change."""
import json
from pathlib import Path
from .pagefiles import page_text

PAGES = ("index.html", "pc.html")
ROOT = Path(__file__).resolve().parent.parent


def earn(g, achievement_id, monkeypatch):
    monkeypatch.setitem(g.ACHIEVEMENT_CHECKS, achievement_id, lambda: True)


def test_default_barn_is_the_only_one_at_first(game_env):
    g = game_env.module
    assert g.barn_skin == "red" and g.barns_unlocked == []
    assert g.barn_is_unlocked("red") and not g.barn_is_unlocked("gold")
    assert game_env.elements["pasture-visual"].getAttribute("data-barn") == "red"
    assert game_env.elements["barn-use-red"].innerText == "In use"
    assert game_env.elements["barn-use-gold"].disabled is True
    assert "Decoupling Dividend" in game_env.elements["barn-note-gold"].innerText or "Earn the achievement" in game_env.elements["barn-note-gold"].innerText


def test_every_barn_names_a_real_achievement(game_env):
    g = game_env.module
    known = {entry["id"] for entry in g.ACHIEVEMENTS}
    for skin in g.BARN_SKINS:
        assert skin["unlock"] is None or skin["unlock"] in known
    assert sum(1 for skin in g.BARN_SKINS if skin["unlock"] is None) == 1


def test_earning_the_achievement_unlocks_and_toasts(game_env, monkeypatch):
    g = game_env.module
    earn(g, "growing_operation", monkeypatch)
    g.render()  # an ordinary render records the unlock
    assert "stone" in g.barns_unlocked
    assert game_env.elements["barn-use-stone"].disabled is False
    assert game_env.elements["barn-use-stone"].innerText == "Use this barn"
    assert g.barn_skin == "red", "unlocking never switches the barn by itself"


def test_choosing_a_barn_changes_only_the_look(game_env, monkeypatch):
    g = game_env.module
    earn(g, "plant_pioneer", monkeypatch)
    g.render()
    before_state = {k: v for k, v in g.get_state().items() if k not in ("barns_unlocked", "barn_skin", "achievements_earned", "summary")}
    game_env.elements["barn-use-sunflower"].dispatch("click")
    assert g.barn_skin == "sunflower"
    assert game_env.elements["pasture-visual"].getAttribute("data-barn") == "sunflower"
    assert game_env.elements["barn-use-sunflower"].innerText == "In use"
    assert "chosen" in game_env.elements["barn-status"].innerText
    after_state = {k: v for k, v in g.get_state().items() if k not in ("barns_unlocked", "barn_skin", "achievements_earned", "summary")}
    assert before_state == after_state


def test_a_locked_barn_cannot_be_chosen(game_env):
    g = game_env.module
    assert g.choose_barn("gold") is False
    game_env.elements["barn-use-gold"].dispatch("click")
    assert g.barn_skin == "red"
    assert g.choose_barn("nonsense") is False


def test_saved_only_when_not_default_and_round_trips(game_env, monkeypatch):
    g = game_env.module
    state = g.get_state()
    assert "barns_unlocked" not in state and "barn_skin" not in state
    earn(g, "long_haul", monkeypatch)
    g.render()
    assert "barn_skin" not in g.get_state()
    assert g.get_state()["barns_unlocked"] == ["moonlit"]
    g.choose_barn("moonlit")
    saved = json.loads(json.dumps(g.get_state()))
    assert saved["barn_skin"] == "moonlit"
    monkeypatch.undo()
    g.barns_unlocked.clear()
    g.barn_skin = "red"
    assert g.load_state(saved) is True
    assert g.barn_skin == "moonlit" and g.barns_unlocked == ["moonlit"]


def test_hostile_save_values_are_dropped(game_env):
    g = game_env.module
    base = g.get_state()
    for bad in ({"barns_unlocked": "gold", "barn_skin": "gold"}, {"barns_unlocked": [1, None, "x"], "barn_skin": 7},
                {"barns_unlocked": ["gold", "gold", "red"], "barn_skin": "stone"}, {"barn_skin": ["gold"]}):
        data = dict(base)
        data.update(bad)
        assert g.load_state(data) is True
        assert g.barn_skin == "red"
        assert "red" not in g.barns_unlocked and len(set(g.barns_unlocked)) == len(g.barns_unlocked)


def test_an_old_save_without_the_keys_loads_unchanged(game_env):
    g = game_env.module
    g.farm.funds += 50
    data = g.get_state()
    assert "barn_skin" not in data
    assert g.load_state(data) is True
    assert g.barn_skin == "red"


def test_unlocks_survive_a_handover_and_an_undo(game_env, monkeypatch):
    g = game_env.module
    earn(g, "sustainably_certified", monkeypatch)
    g.render()
    g.choose_barn("green")
    g.farm.certified = True
    g.hand_over_farm()
    assert g.barns_unlocked == ["green"] and g.barn_skin == "green"
    game_env.advance_round()
    g.barns_unlocked.append("gold")
    game_env.elements["undo-round-button"].disabled = False
    assert g.undo_last_round()
    assert "gold" in g.barns_unlocked and g.barn_skin == "green"


def test_both_pages_have_the_barn_ids():
    for page in PAGES:
        text = page_text(page)
        for ident in ("pasture-visual", "pasture-barn", "barn-panel", "barn-summary", "barn-status"):
            assert f'id="{ident}"' in text, (page, ident)
        for skin in ("red", "stone", "green", "sunflower", "moonlit", "gold"):
            assert f'id="barn-use-{skin}"' in text and f'id="barn-note-{skin}"' in text, (page, skin)
