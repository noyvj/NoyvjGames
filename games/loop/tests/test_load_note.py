"""H-27: a friendly 'repaired X, reset Y' note after loading a damaged or odd save."""

import json

import pytest


def good_state(env):
    m = env.module
    env.chain.funds = 5000.0
    for _ in range(3):
        env.invest_circularity("recycle")
    env.elements["cycle-note-input"].value = "note"
    env.advance_cycle()
    env.advance_cycle()
    return json.loads(json.dumps(m.get_state()))


def load(env, state):
    env.module.load_state(state)
    return env.module.load_report


def test_a_clean_save_shows_no_note(game_env):
    state = good_state(game_env)
    assert load(game_env, state) == []
    assert game_env.elements["load-note"].hidden is True
    assert game_env.module.load_note_lines() == []


def test_a_fresh_game_save_shows_no_note(game_env):
    assert load(game_env, json.loads(json.dumps(game_env.module.get_state()))) == []


@pytest.mark.parametrize("key,bad,name", [
    ("market_shocks", "yes", "Market shocks switch"),
    ("rival_crossover_cycle", -5, "Rival Corporation crossover"),
    ("culture_level", 99, "Culture campaign level"),
    ("waste_focus", "magic", "Waste stream focus"),
    ("rewind_used", 1, "Rewind token"),
    ("past_chains", "junk", "Past chains"),
    ("ledger", [["junk"]], "Cycle ledger"),
])
def test_an_invalid_value_is_reported_as_reset(game_env, key, bad, name):
    state = good_state(game_env)
    state[key] = bad
    report = load(game_env, state)
    assert (name, "reset") in report or (name, "repaired") in report
    lines = game_env.module.load_note_lines()
    assert name in " ".join(lines)
    assert lines[-1] == "Everything else loaded as saved."
    assert game_env.elements["load-note"].hidden is False
    assert name in game_env.elements["load-note-list"].innerHTML


def test_dropping_one_bad_ledger_row_is_a_repair_not_a_reset(game_env):
    state = good_state(game_env)
    state["ledger"] = state["ledger"] + [["junk"]]
    report = load(game_env, state)
    assert report == [("Cycle ledger", "repaired")]
    assert game_env.module.load_note_lines()[0] == "Repaired: Cycle ledger."


def test_a_wholly_bad_ledger_is_a_reset(game_env):
    state = good_state(game_env)
    state["ledger"] = [["junk"], ["more"]]
    assert load(game_env, state) == [("Cycle ledger", "reset")]
    assert "Reset to the starting value: Cycle ledger." in game_env.module.load_note_lines()


def test_several_problems_are_listed_once_each(game_env):
    state = good_state(game_env)
    state["insurance_used"] = "x"
    state["insurance_armed"] = "x"  # same player-facing name twice
    state["rival_on"] = "x"
    report = load(game_env, state)
    assert report.count(("Streak insurance", "reset")) == 1
    assert ("Rival Corporation switch", "reset") in report


def test_a_value_that_is_just_the_default_is_not_a_problem(game_env):
    state = good_state(game_env)
    state["market_shocks"] = False
    state["culture_level"] = 0
    state["picked_category"] = state["goods_category"]
    assert load(game_env, state) == []


def test_the_dismiss_button_clears_the_note(game_env):
    state = good_state(game_env)
    state["market_shocks"] = "yes"
    load(game_env, state)
    assert game_env.elements["load-note"].hidden is False
    game_env.elements["load-note-dismiss"].dispatch("click", None)
    assert game_env.elements["load-note"].hidden is True
    assert game_env.module.load_report == []


def test_the_note_is_cleared_by_the_next_clean_load(game_env):
    state = good_state(game_env)
    bad = dict(state, market_shocks="yes")
    load(game_env, bad)
    assert game_env.module.load_report
    assert load(game_env, state) == []
    assert game_env.elements["load-note"].hidden is True


def test_the_note_text_is_escaped(game_env):
    m = game_env.module
    m.load_report[:] = [("<b>x</b>", "reset")]
    m.render()
    assert "<b>" not in game_env.elements["load-note-list"].innerHTML
    m.load_report.clear()


def test_the_note_is_never_saved(game_env):
    state = good_state(game_env)
    state["market_shocks"] = "yes"
    load(game_env, state)
    assert "load_report" not in game_env.module.get_state()
    assert "load-note" not in json.dumps(game_env.module.get_state())
