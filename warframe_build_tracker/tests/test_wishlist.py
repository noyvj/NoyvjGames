"""Batch A #7: the wishlist as clan-chat text."""

from .helpers import click, known_state


def test_lists_builds_and_needs_with_pins_first(game_env):
    m = game_env.module
    known_state(m, parts={"Rahn Prism": {"owned": 0, "target": 1}, "Shwaak Prism": {"owned": 1, "target": 3}},
                inventory={"Iradite": {"built": 10}})
    m.state["pins"] = ["Shwaak Prism"]
    components, resources = m.calculate()
    text = m.wishlist_text(components, resources)
    first, second = text.split("\n")
    assert first == "Building: Shwaak Prism x2, Rahn Prism x1"
    assert second.startswith("Need: ") and "Iradite x" in second


def test_nothing_needed(game_env):
    m = game_env.module
    known_state(m)
    components, resources = m.calculate()
    assert m.wishlist_text(components, resources).startswith("Nothing on my wishlist")


def test_have_enough_resources_drop_off_and_goals_stay_out(game_env):
    m = game_env.module
    known_state(m, parts={"Rahn Prism": {"owned": 0, "target": 1}})
    m.add_goal("Endgame weapon")
    components, resources = m.calculate()
    assert "Iradite" in m.wishlist_text(components, resources)
    m.set_enough("Iradite", True)
    components, resources = m.calculate()
    text = m.wishlist_text(components, resources)
    assert "Iradite" not in text and "Endgame" not in text


def test_textarea_and_copy_button(game_env):
    m = game_env.module
    known_state(m, parts={"Rahn Prism": {"owned": 0, "target": 1}})
    assert "Building: Rahn Prism x1" in game_env.elements["wishlist-text"].value
    click(game_env.elements["copy-wishlist-button"])
    assert game_env.js.navigator.clipboard.written[-1].startswith("Building: Rahn Prism x1")
