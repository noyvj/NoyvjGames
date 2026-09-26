"""Batch A #10: long-term goals, separate from the active builds."""

from .helpers import all_text, click, find_all, known_state


def test_add_validation(game_env):
    m = game_env.module
    assert m.add_goal("Own every Kuva weapon")[0] is True
    assert m.add_goal("own every kuva weapon")[0] is False
    assert m.add_goal("")[0] is False
    assert m.state["goals"][0]["text"] == "Own every Kuva weapon"
    assert m.add_goal("x" * 200)[0] is True and len(m.state["goals"][1]["text"]) == m.GOAL_TEXT_MAX
    for i in range(m.GOAL_MAX):
        m.state["goals"].append({"text": f"g{i}", "done": False})
    assert m.add_goal("more")[0] is False


def test_goals_do_not_touch_the_shopping_list_or_needs(game_env):
    m = game_env.module
    known_state(m, parts={"Rahn Prism": {"owned": 0, "target": 1}})
    before = (game_env.elements["shopping-text"].value, m.calculate())
    m.add_goal("Legendary rank")
    m.render()
    assert game_env.elements["shopping-text"].value == before[0]
    assert m.calculate() == before[1]
    assert "Legendary rank" not in game_env.elements["shopping-text"].value


def test_ui_add_tick_remove(game_env):
    m = game_env.module
    known_state(m)
    els = game_env.elements
    els["goal-input"].value = "Kuva Bramma"
    click(els["goal-add-button"])
    assert "Kuva Bramma" in all_text(els["goal-list"])
    assert els["goal-input"].value == ""
    box = find_all(els["goal-list"], tag="input")[0]
    box.checked = True
    box.dispatch("change", None)
    assert m.state["goals"][0]["done"] is True
    click(find_all(els["goal-list"], tag="button")[0])
    assert m.state["goals"] == []


def test_save_round_trip_and_validation(game_env):
    m = game_env.module
    assert "goals" not in m.get_state()
    m.add_goal("A")
    m.state["goals"][0]["done"] = True
    saved = m.get_state()
    m.state["goals"] = []
    m.load_state(saved)
    assert m.state["goals"] == [{"text": "A", "done": True}]
    m.load_state({"goals": [{"text": "ok", "done": False}, {"text": "", "done": False}, {"text": "x", "done": "no"},
                            {"text": 4, "done": False}, "junk", None]})
    assert m.state["goals"] == [{"text": "ok", "done": False}]
    m.load_state({"goals": {"a": 1}})
    assert m.state["goals"] == []
