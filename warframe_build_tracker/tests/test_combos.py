"""Per-part notes and the build comparison (known and custom combos)."""

from .test_refinery import _all_text
from .test_tracker import _find_row, _reset_to_known_state


def _fresh(m, parts=None, inventory=None):
    _reset_to_known_state(m, parts=parts, inventory=inventory)
    m.state["combos"] = []


def test_every_requested_part_has_a_wiki_note(game_env):
    m = game_env.module
    assert set(m.PART_NOTES) == {name for name, _ in m.DEFAULT_PARTS}
    assert all(note.strip() for note in m.PART_NOTES.values())


def test_note_shows_in_the_table(game_env):
    m = game_env.module
    _fresh(m)
    m.render()
    row = _find_row(game_env.elements["components-body"], "data-part", "Certus Brace")
    assert "+20% Amp critical chance." in _all_text(row)


def test_known_combos_only_name_real_parts_and_carry_a_source(game_env):
    m = game_env.module
    for combo in m.KNOWN_COMBOS:
        assert combo["source"] and all(p in m.RECIPES for p in combo["parts"]), combo
    assert [c["name"] for c in m.KNOWN_COMBOS] == ["177"]


def test_progress_counts_built_parts_and_short_resources(game_env):
    m = game_env.module
    _fresh(m, parts={"Certus Brace": {"owned": 0, "target": 1}, "Propa Scaffold": {"owned": 0, "target": 1}})
    components, _ = m.calculate()
    row = m.combo_progress(m.KNOWN_COMBOS[0], components)
    assert row["built"] == ["Raplak Prism"]
    assert row["missing_parts"] == ["Propa Scaffold", "Certus Brace"]
    assert row["units_short"] > 0 and not row["complete"]


def test_a_finished_combo_is_complete_and_sorts_last(game_env):
    m = game_env.module
    _fresh(m, parts={"Klamora Prism": {"owned": 0, "target": 1}})
    ok, _ = m.add_combo("Done", ["Raplak Prism"])
    assert ok
    ok, _ = m.add_combo("Not yet", ["Klamora Prism"])
    assert ok
    components, _ = m.calculate()
    rows = m.compare_combos(components)
    assert rows[-1]["combo"]["name"] in ("177", "Done") and rows[-1]["complete"]
    assert rows[0]["combo"]["name"] == "Not yet"
    assert "Not yet (amp): 0/1 parts built; still to build Klamora Prism" in m.combos_text(components)


def test_add_combo_validation(game_env):
    m = game_env.module
    _fresh(m)
    assert m.add_combo("", ["Raplak Prism"])[0] is False
    assert m.add_combo("X", [])[0] is False
    assert m.add_combo("X", ["Raplak Prism"] * 2)[0] is False
    assert m.add_combo("X", ["Nope"])[0] is False
    assert m.add_combo("X", ["Raplak Prism", "Propa Scaffold", "Certus Brace", "Lohrin Brace", "Klamora Prism", "Lega Prism"])[0] is False
    assert m.add_combo("177", ["Raplak Prism"])[0] is False  # clashes with the built-in name
    assert m.add_combo("Mine", ["Raplak Prism"])[0] is True
    assert m.add_combo("mine", ["Lega Prism"])[0] is False  # case-insensitive clash
    assert m.state["combos"] == [{"name": "Mine", "parts": ["Raplak Prism"]}]
    assert m.remove_combo("Mine") is True and m.remove_combo("Mine") is False


def test_form_buttons_drive_it(game_env):
    m = game_env.module
    _fresh(m)
    game_env.elements["combo-name-input"].value = "Zaw pick"
    game_env.elements["combo-parts-input"].value = "Balla Strike, Shtung Grip , Vargeet Jai II Link"
    game_env.elements["combo-add-button"].dispatch("click", None)
    assert m.state["combos"][0]["parts"] == ["Balla Strike", "Shtung Grip", "Vargeet Jai II Link"]
    assert "Zaw pick (zaw)" in game_env.elements["combo-compare"].textContent
    game_env.elements["combo-remove-input"].value = "Zaw pick"
    game_env.elements["combo-remove-button"].dispatch("click", None)
    assert m.state["combos"] == []


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    _fresh(m)
    assert "combos" not in m.get_state()
    m.add_combo("Mine", ["Raplak Prism", "Certus Brace"])
    saved = m.get_state()
    m.state["combos"] = []
    m.load_state(saved)
    assert m.state["combos"] == [{"name": "Mine", "parts": ["Raplak Prism", "Certus Brace"]}]
    m.load_state({"combos": [
        {"name": "ok", "parts": ["Lega Prism"]},
        {"name": "", "parts": ["Lega Prism"]},
        {"name": "bad", "parts": ["Nope"]},
        {"name": "dup", "parts": ["Lega Prism", "Lega Prism"]},
        {"name": "177", "parts": ["Lega Prism"]},
        {"name": 5, "parts": []},
        "junk",
    ]})
    assert m.state["combos"] == [{"name": "ok", "parts": ["Lega Prism"]}]
    m.load_state({"combos": "nope"})
    assert m.state["combos"] == []
