"""Batch A #12: own-edits changelog and the typed-vs-imported marker."""

import json

from .helpers import all_text, click, find_all, known_state


def _row(game_env, name):
    return next(r for r in game_env.elements["resources-body"].children if r.attributes.get("data-resource") == name)


def _setup(m):
    known_state(m, parts={"Rahn Prism": {"owned": 0, "target": 3}})
    m._now_stamp = lambda: "2026-09-27 10:00"


def test_counts_merge_within_a_minute_and_read_naturally(game_env):
    m = game_env.module
    _setup(m)
    m.note_edit("build", 3)
    m.note_edit("build")
    m.note_edit("resource", 12)
    assert m.state["edit_log"] == [{"t": "2026-09-27 10:00", "k": "build", "d": 4}, {"t": "2026-09-27 10:00", "k": "resource", "d": 12}]
    assert m.edit_log_text() == "Today: added 4 builds, edited 12 resource counts. In the whole log: added 4 builds, edited 12 resource counts."
    assert m.edit_phrase("build", 1) == "added 1 build"
    assert m.note_edit("nonsense") is False and m.note_edit("build", 0) is False


def test_today_is_separated_from_earlier_days(game_env):
    m = game_env.module
    _setup(m)
    m.state["edit_log"] = [{"t": "2026-09-20 09:00", "k": "goal", "d": 2}]
    m.note_edit("timer")
    text = m.edit_log_text()
    assert text.startswith("Today: added 1 timer.") and "added 2 goals" in text


def test_log_is_capped(game_env):
    m = game_env.module
    for i in range(m.EDIT_LOG_MAX + 30):
        m._now_stamp = lambda i=i: f"2026-09-27 {i // 60 % 24:02d}:{i % 60:02d}"
        m.note_edit("goal")
    assert len(m.state["edit_log"]) == m.EDIT_LOG_MAX


def test_owned_edit_and_build_button_are_logged(game_env):
    m = game_env.module
    _setup(m)
    row = next(r for r in game_env.elements["components-body"].children if r.attributes.get("data-part") == "Rahn Prism")
    owned = find_all(row, tag="input", class_name="owned-input")[0]
    owned.value = "2"
    owned.dispatch("change", None)
    assert m.state["edit_log"][-1] == {"t": "2026-09-27 10:00", "k": "build", "d": 2}
    owned.value = "1"  # lowering it is not "adding builds"
    owned.dispatch("change", None)
    assert m.state["edit_log"][-1]["d"] == 2


def test_typing_a_count_marks_it_typed_and_import_marks_it_import(game_env):
    m = game_env.module
    _setup(m)
    row = _row(game_env, "Iradite")
    assert not find_all(row, class_name="src-marker")
    built = find_all(row, tag="input", class_name="built-input")[0]
    built.value = "30"
    built.dispatch("change", None)
    assert m.state["inv_source"]["Iradite"] == "hand"
    assert find_all(_row(game_env, "Iradite"), class_name="src-marker")[0].textContent == "typed"
    assert m.state["edit_log"][-1]["k"] == "resource"
    m.import_last_data(json.dumps({"MiscItems": [{"ItemType": "/Lotus/Types/Items/MiscItems/Iradite", "ItemCount": 44}]}))
    assert m.state["inv_source"]["Iradite"] == "import"
    assert find_all(_row(game_env, "Iradite"), class_name="src-marker")[0].textContent == "import"
    assert m.state["edit_log"][-1]["k"] == "import"
    assert "ran 1 import" in game_env.elements["edit-log-text"].textContent or "import" in all_text(game_env.elements["edit-log-text"])


def test_unchanged_value_is_not_an_edit(game_env):
    m = game_env.module
    _setup(m)
    built = find_all(_row(game_env, "Iradite"), tag="input", class_name="built-input")[0]
    built.value = "0"
    built.dispatch("change", None)
    assert m.state["edit_log"] == [] and m.state["inv_source"] == {}


def test_reset_clears_markers_and_clear_button_clears_the_log(game_env):
    m = game_env.module
    _setup(m)
    m.set_source("Iradite", "hand")
    m.note_edit("goal")
    click(game_env.elements["reset-button"])
    game_env.confirm.next_result = True
    assert m.state["inv_source"] == {}
    click(game_env.elements["clear-edit-log-button"])
    assert m.state["edit_log"] == []
    assert m.set_source("Nope", "hand") is None and m.state["inv_source"] == {}


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    st = m.get_state()
    assert "edit_log" not in st and "inv_source" not in st
    m.state["edit_log"] = [{"t": "2026-09-27 10:00", "k": "build", "d": 2}]
    m.state["inv_source"] = {"Iradite": "import"}
    saved = m.get_state()
    m.state["edit_log"], m.state["inv_source"] = [], {}
    m.load_state(saved)
    assert m.state["edit_log"] == [{"t": "2026-09-27 10:00", "k": "build", "d": 2}]
    assert m.state["inv_source"] == {"Iradite": "import"}
    m.load_state({
        "edit_log": [{"t": "bad", "k": "build", "d": 1}, {"t": "2026-09-27 10:00", "k": "nope", "d": 1},
                     {"t": "2026-09-27 10:00", "k": ["x"], "d": 1}, {"t": "2026-09-27 10:00", "k": "goal", "d": 0},
                     {"t": "2026-09-27 10:00", "k": "goal", "d": True}, {"t": "2026-09-27 10:00", "k": "goal", "d": 2}],
        "inv_source": {"Iradite": "hand", "Ferrite": "cloud", "Nope": "hand", "Rubedo": ["x"]},
    })
    assert m.state["edit_log"] == [{"t": "2026-09-27 10:00", "k": "goal", "d": 2}]
    assert m.state["inv_source"] == {"Iradite": "hand"}
    m.load_state({"edit_log": "x", "inv_source": [1]})
    assert m.state["edit_log"] == [] and m.state["inv_source"] == {}
