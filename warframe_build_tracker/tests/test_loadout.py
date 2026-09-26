"""Batch A #16: mod-list and playstyle notes on finished builds."""

from .helpers import all_text, click, find_all, known_state


def test_notes_attach_only_to_finished_builds(game_env):
    m = game_env.module
    known_state(m, parts={"Rahn Prism": {"owned": 0, "target": 1}})
    assert m.set_loadout("Raplak Prism", "Serration, Split Chamber", "Long range")[0] is True
    assert m.state["loadouts"]["Raplak Prism"] == {"mods": "Serration, Split Chamber", "play": "Long range"}
    ok, message = m.set_loadout("Rahn Prism", "mods", "")
    assert ok is False and "not finished" in message
    assert "Rahn Prism" not in m.state["loadouts"]
    assert m.set_loadout("Nope", "x", "y")[0] is False


def test_finished_combo_and_a_recently_completed_build(game_env):
    m = game_env.module
    known_state(m)
    assert m.set_loadout("177", "Arcane Energize", "Alt-fire")[0] is True
    m.state["parts"]["Rahn Prism"]["owned"] = 0  # no longer finished, but it is on the recent strip
    m.state["completed"] = [{"n": "Rahn Prism", "d": "2026-09-27"}]
    assert m.set_loadout("Rahn Prism", "mods", "")[0] is True


def test_length_is_capped_and_empty_notes_clear(game_env):
    m = game_env.module
    known_state(m)
    m.set_loadout("Raplak Prism", "m" * 5000, "p" * 5000)
    entry = m.state["loadouts"]["Raplak Prism"]
    assert len(entry["mods"]) == m.LOADOUT_MAX and len(entry["play"]) == m.LOADOUT_MAX
    assert m.set_loadout("raplak prism", " ", "") == (True, "Cleared the notes on Raplak Prism.")
    assert m.state["loadouts"] == {}


def test_notes_render_as_text_only(game_env):
    m = game_env.module
    known_state(m)
    m.set_loadout("Raplak Prism", "<b>bold</b>", "<script>x</script>")
    m.render()
    box = game_env.elements["loadout-list"]
    assert "<b>bold</b>" in all_text(box)
    assert all("<b>" not in (el.innerHTML or "") for el in find_all(box))  # set via textContent, never innerHTML


def test_ui_save_and_remove(game_env):
    m = game_env.module
    known_state(m)
    els = game_env.elements
    els["loadout-name-input"].value = "raplak prism"
    els["loadout-mods-input"].value = "Serration"
    els["loadout-play-input"].value = "Sniping"
    click(els["loadout-save-button"])
    assert m.state["loadouts"]["Raplak Prism"] == {"mods": "Serration", "play": "Sniping"}
    assert els["loadout-mods-input"].value == ""
    assert "Serration" in all_text(els["loadout-list"])
    click(find_all(els["loadout-list"], tag="button")[0])
    assert m.state["loadouts"] == {}


def test_removed_combo_prunes_its_notes(game_env):
    m = game_env.module
    known_state(m)
    m.add_combo("Duo", ["Raplak Prism", "Rahn Prism"])
    m.set_loadout("Duo", "a", "b")
    m.remove_combo("Duo")
    assert m.state["loadouts"] == {}


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    assert "loadouts" not in m.get_state()
    m.state["loadouts"] = {"Raplak Prism": {"mods": "a", "play": ""}}
    saved = m.get_state()
    m.state["loadouts"] = {}
    m.load_state(saved)
    assert m.state["loadouts"] == {"Raplak Prism": {"mods": "a", "play": ""}}
    m.load_state({"loadouts": {
        "Raplak Prism": {"mods": "x" * 900, "play": "ok"}, "Nope": {"mods": "a", "play": "b"},
        "Rahn Prism": {"mods": "", "play": "  "}, "Lega Prism": {"mods": 4, "play": "b"}, "Cantic Prism": "junk",
    }})
    assert list(m.state["loadouts"]) == ["Raplak Prism"]
    assert len(m.state["loadouts"]["Raplak Prism"]["mods"]) == m.LOADOUT_MAX
    m.load_state({"loadouts": [1]})
    assert m.state["loadouts"] == {}
