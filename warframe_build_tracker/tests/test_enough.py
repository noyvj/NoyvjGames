"""Batch A #8: per-resource "I have enough"."""

from .helpers import all_text, find_all, known_state


def _row(game_env, name):
    return next(r for r in game_env.elements["resources-body"].children if r.attributes.get("data-resource") == name)


def _setup(m):
    known_state(m, parts={"Rahn Prism": {"owned": 0, "target": 1}}, inventory={"Iradite": {"built": 1}})


def test_calculations_are_unchanged_but_the_row_is_flagged(game_env):
    m = game_env.module
    _setup(m)
    _, before = m.calculate()
    m.set_enough("Iradite", True)
    _, after = m.calculate()
    strip = lambda rows: [{k: v for k, v in r.items() if k != "enough"} for r in rows]  # noqa: E731
    assert strip(before) == strip(after)
    assert {r["name"]: r["enough"] for r in after}["Iradite"] is True


def test_enough_resources_leave_the_shopping_list_and_summaries(game_env):
    m = game_env.module
    _setup(m)
    assert "Iradite" in game_env.elements["shopping-text"].value
    m.set_enough("Iradite", True)
    m.render()
    assert "Iradite" not in game_env.elements["shopping-text"].value
    assert "Esher Devar" in game_env.elements["shopping-text"].value  # others still listed
    part = next(r for r in game_env.elements["components-body"].children if r.attributes.get("data-part") == "Rahn Prism")
    assert "Iradite" not in all_text(part)  # no longer named as a missing resource


def test_checkbox_toggles_and_dims_the_row(game_env):
    m = game_env.module
    _setup(m)
    box = find_all(_row(game_env, "Iradite"), tag="input", class_name="enough-input")[0]
    box.checked = True
    box.dispatch("change", None)
    assert m.state["enough"] == ["Iradite"]
    row = _row(game_env, "Iradite")
    assert "enough" in row.className.split()
    box = find_all(row, tag="input", class_name="enough-input")[0]
    assert box.checked is True
    box.checked = False
    box.dispatch("change", None)
    assert m.state["enough"] == []


def test_set_enough_rejects_unknown_names(game_env):
    m = game_env.module
    assert m.set_enough("Unobtainium", True) is False
    assert m.state["enough"] == []


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    assert "enough" not in m.get_state()
    m.set_enough("Iradite", True)
    saved = m.get_state()
    m.state["enough"] = []
    m.load_state(saved)
    assert m.state["enough"] == ["Iradite"]
    m.load_state({"enough": ["Ferrite", "Ferrite", "Nope", 3, ["x"]]})
    assert m.state["enough"] == ["Ferrite"]
    m.load_state({"enough": "Ferrite"})
    assert m.state["enough"] == []
