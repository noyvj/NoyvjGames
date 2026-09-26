"""Batch A #1: the "This week" pins."""

from .helpers import all_text, click, find_all, known_state


def test_toggle_pin_adds_removes_and_caps_at_three(game_env):
    m = game_env.module
    known_state(m)
    assert m.toggle_pin("raplak prism")[0] is True  # case-insensitive
    assert m.state["pins"] == ["Raplak Prism"]
    assert m.toggle_pin("Raplak Prism") == (True, "Unpinned Raplak Prism.")
    for name in ("Raplak Prism", "Shwaak Prism", "Granmu Prism"):
        assert m.toggle_pin(name)[0] is True
    ok, message = m.toggle_pin("Rahn Prism")
    assert ok is False and "up to 3" in message
    assert m.state["pins"] == ["Raplak Prism", "Shwaak Prism", "Granmu Prism"]


def test_unknown_names_are_rejected(game_env):
    m = game_env.module
    assert m.toggle_pin("Not A Part")[0] is False
    assert m.toggle_pin("")[0] is False
    assert m.state["pins"] == []


def test_combos_can_be_pinned_and_removal_prunes_the_pin(game_env):
    m = game_env.module
    known_state(m)
    m.add_combo("Mine", ["Raplak Prism", "Shwaak Prism"])
    assert m.toggle_pin("mine")[0] is True
    assert m.state["pins"] == ["Mine"]
    m.remove_combo("Mine")
    assert m.state["pins"] == []


def test_pin_status_for_a_part_and_a_combo(game_env):
    m = game_env.module
    known_state(m, parts={"Rahn Prism": {"owned": 0, "target": 1}})
    m.toggle_pin("Rahn Prism")
    m.toggle_pin("177")
    components, _ = m.calculate()
    status = {s["name"]: s for s in m.pin_status(components)}
    assert status["Rahn Prism"]["status"].startswith("0/1 built, short")
    assert status["177"]["status"] == "done (all parts built)"


def test_render_lists_pins_and_the_row_star_toggles(game_env):
    m = game_env.module
    known_state(m)
    body = game_env.elements["components-body"]
    row = next(r for r in body.children if r.attributes.get("data-part") == "Raplak Prism")
    star = find_all(row, tag="button", class_name="pin-btn")[0]
    assert star.textContent == "☆ pin"
    click(star)
    assert m.state["pins"] == ["Raplak Prism"]
    assert "Raplak Prism" in all_text(game_env.elements["week-pins"])
    row = next(r for r in game_env.elements["components-body"].children if r.attributes.get("data-part") == "Raplak Prism")
    assert find_all(row, tag="button", class_name="pin-btn")[0].textContent == "★ pinned"


def test_pin_input_button(game_env):
    m = game_env.module
    known_state(m)
    game_env.elements["week-pin-input"].value = "Shwaak Prism"
    click(game_env.elements["week-pin-button"])
    assert m.state["pins"] == ["Shwaak Prism"]
    assert game_env.elements["week-pin-input"].value == ""
    assert "Pinned" in game_env.elements["week-message"].textContent


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    known_state(m)
    assert "pins" not in m.get_state()
    m.state["pins"] = ["Raplak Prism", "177"]
    saved = m.get_state()
    m.state["pins"] = []
    m.load_state(saved)
    assert m.state["pins"] == ["Raplak Prism", "177"]
    m.load_state({"pins": ["Raplak Prism", "Raplak Prism", "Nope", 5, None, ["x"], "Shwaak Prism", "Granmu Prism", "Rahn Prism"]})
    assert m.state["pins"] == ["Raplak Prism", "Shwaak Prism", "Granmu Prism"]
    m.load_state({"pins": "Raplak Prism"})
    assert m.state["pins"] == []
    m.load_state({})
    assert m.state["pins"] == []
