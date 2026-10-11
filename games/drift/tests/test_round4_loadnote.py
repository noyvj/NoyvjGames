"""I-30: a friendly 'restored X, started fresh Y' note when a loaded save is old or damaged, plus the
hardening that makes a damaged core field fall back instead of breaking the next render."""

import copy
import json


def _fresh_state(game_env, rounds=4):
    for _ in range(rounds):
        game_env.invest("housing")
        game_env.advance_round()
    return json.loads(json.dumps(game_env.module.get_state()))


def test_a_clean_save_loads_with_no_note(game_env):
    state = _fresh_state(game_env)
    assert game_env.module.load_state(state)
    assert game_env.module.load_note_text == ""
    assert game_env.elements["load-note-box"].hidden is True


def test_an_old_save_missing_newer_sections_says_so(game_env):
    state = _fresh_state(game_env)
    for key in ("subscore_log", "strain_sum", "strain_count", "ledger", "roi_log"):
        state.pop(key, None)
    game_env.module.load_state(state)
    note = game_env.elements["load-note"].innerText
    assert game_env.elements["load-note-box"].hidden is False
    assert "sub-score history" in note.split("Started fresh:")[1]
    assert "the round and funds" in note.split("Started fresh:")[0] and "capacity" in note.split("Started fresh:")[0]
    assert "round ledger" not in note.split("Started fresh:")[1]  # an optional section that was never written is not an error


def test_a_damaged_section_is_named_as_started_fresh(game_env):
    state = _fresh_state(game_env)
    state["ledger"] = "garbage"
    state["strain_log"] = [0.1, "x", 0.2]
    game_env.module.load_state(state)
    fresh = game_env.module.load_note_text.split("Started fresh:")[1]
    assert "the round ledger" in fresh and "strain history" in fresh
    assert game_env.region.ledger == [] and game_env.region.strain_log != [0.1, "x", 0.2]


def test_a_partly_unreadable_save_still_plays_on(game_env):
    state = _fresh_state(game_env)
    state["funds"] = "a lot"
    state["capacity"] = {"housing": "x", "services": None}
    state["round_number"] = -4
    state["total_arrivals"] = float("nan")
    assert game_env.module.load_state(state)
    game_env.module.render()
    game_env.advance_round()
    assert game_env.region.round_number >= 1
    assert isinstance(game_env.region.funds, float)
    for kind in game_env.module.CAPACITY_TYPES:
        assert isinstance(game_env.region.capacity[kind], float)


def test_readable_sections_are_not_reset_by_a_damaged_neighbour(game_env):
    state = _fresh_state(game_env, rounds=5)
    funds = state["funds"]
    state["wellbeing_log"] = {"not": "a list"}
    game_env.module.load_state(state)
    assert game_env.region.funds == funds and game_env.region.round_number == 6
    restored = game_env.module.load_note_text.split("Started fresh:")[0]
    assert "the round and funds" in restored and "wellbeing history" not in restored


def test_dismiss_hides_the_note(game_env):
    state = _fresh_state(game_env)
    del state["subscore_log"]
    game_env.module.load_state(state)
    assert game_env.elements["load-note-box"].hidden is False
    game_env.elements["load-note-dismiss"].dispatch("click", None)
    assert game_env.elements["load-note-box"].hidden is True and game_env.module.load_note_text == ""


def test_the_note_is_announced_once_on_load(game_env):
    spoken = []
    game_env.module._shared_announce = lambda text: spoken.append(text) or True
    state = _fresh_state(game_env)
    del state["subscore_log"]
    spoken.clear()
    game_env.module.load_state(state)
    assert sum("Loaded your save, but part of it" in s for s in spoken) == 1


def test_a_later_clean_load_clears_an_earlier_note(game_env):
    state = _fresh_state(game_env)
    bad = copy.deepcopy(state)
    del bad["subscore_log"]
    game_env.module.load_state(bad)
    assert game_env.module.load_note_text
    game_env.module.load_state(state)
    assert game_env.module.load_note_text == ""


def test_load_report_labels(game_env):
    m = game_env.module
    restored, reset = m.load_report({"round_number": 3, "funds": 10})
    assert restored == ["the round and funds"]
    assert "capacity" in reset and "strain history" in reset and "the round ledger" not in reset
    assert m.load_report({"ledger": []})[0] == ["the round ledger"]


def test_a_fresh_regions_own_save_reports_clean(game_env):
    restored, reset = game_env.module.load_report(game_env.module.get_state())
    assert reset == []
