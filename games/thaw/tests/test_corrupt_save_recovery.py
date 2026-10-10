"""G-29: a save with unreadable fields still loads, and a notice names what was replaced."""

import copy


def _good_state(game_env):
    for _ in range(4):
        game_env.advance_round()
    return game_env.module.get_state()


def _notice(game_env):
    return game_env.elements["load-notice-text"].innerText


def test_a_clean_save_shows_no_notice(game_env):
    m = game_env.module
    assert m.load_state(_good_state(game_env))
    assert m.load_problems == []
    assert game_env.elements["load-notice"].hidden is True


def test_sanitize_does_not_touch_the_original(game_env):
    m = game_env.module
    state = _good_state(game_env)
    state["region"]["funds"] = "lots"
    before = copy.deepcopy(state)
    clean, problems = m.sanitize_save(state)
    assert state == before
    assert "funds" not in clean["region"]
    assert problems == ["Region A funds"]


def test_bad_field_is_named_and_the_rest_loads(game_env):
    m = game_env.module
    state = _good_state(game_env)
    state["region"]["funds"] = "lots"
    state["region_b"]["temperature"] = float("nan")
    state["region_c"]["round_number"] = -3
    state["region"]["capacity"]["preserve"] = "x"
    m.region.funds = 123.0
    m.region_c.round_number = 2
    assert m.load_state(state)
    assert m.region.funds == 123.0  # this game's own value kept
    assert m.region.round_number == 5  # everything else loaded
    assert m.region_c.round_number == 2  # unreadable, so left as it was
    text = _notice(game_env)
    for name in ("Region A funds", "Region B temperature", "Region C round number", "Region A Permafrost Preservation units"):
        assert name in text
    assert game_env.elements["load-notice"].hidden is False
    assert "nothing in the save itself was changed" in text


def test_wrong_types_never_crash_a_load_or_render(game_env):
    m = game_env.module
    state = _good_state(game_env)
    for field in ("funds", "temperature", "counterfactual_temperature", "temperature_history", "capacity",
                  "round_number", "melt_started_round", "strategy_label", "tipping_events"):
        broken = copy.deepcopy(state)
        broken["region"][field] = [object()] if field != "capacity" else 5
        assert m.load_state(broken), field
        m.render()
        assert m.load_problems, field


def test_not_a_dict_block_is_reported(game_env):
    m = game_env.module
    state = _good_state(game_env)
    state["region_b"] = 7
    assert m.load_state(state)
    assert "Region B (the whole block)" in _notice(game_env)


def test_top_level_flags_are_checked(game_env):
    m = game_env.module
    state = _good_state(game_env)
    state["carbon_bank"] = 99999
    state["long_game"] = "yes"
    state["framing"] = "sideways"
    state["science_log"] = "nope"
    assert m.load_state(state)
    for name in ("carbon bank", "long game flag", "framing", "scientist's log"):
        assert name in _notice(game_env)
    assert m.long_game is False and m.carbon_bank == 0 and m.framing == "regional"


def test_not_a_save_at_all_says_so(game_env):
    m = game_env.module
    assert m.load_state([1, 2, 3]) is False
    assert "not a game save at all" in _notice(game_env)
    assert game_env.elements["load-notice"].hidden is False


def test_dismiss_clears_the_notice(game_env):
    m = game_env.module
    state = _good_state(game_env)
    state["region"]["funds"] = None
    m.load_state(state)
    assert game_env.elements["load-notice"].hidden is False
    game_env.elements["load-notice-dismiss"].dispatch("click")
    assert game_env.elements["load-notice"].hidden is True
    assert m.load_problems == []


def test_next_clean_load_clears_an_old_notice(game_env):
    m = game_env.module
    state = _good_state(game_env)
    bad = copy.deepcopy(state)
    bad["region"]["funds"] = None
    m.load_state(bad)
    m.load_state(state)
    assert game_env.elements["load-notice"].hidden is True


def test_many_problems_are_summarised(game_env):
    m = game_env.module
    state = _good_state(game_env)
    for label in ("region", "region_b", "region_c"):
        for field in ("funds", "temperature", "round_number"):
            state[label][field] = "bad"
    m.load_state(state)
    assert "9 fields were" in _notice(game_env)
    assert "and 1 more" in _notice(game_env)


def test_single_problem_uses_singular(game_env):
    m = game_env.module
    state = _good_state(game_env)
    state["region"]["funds"] = "bad"
    m.load_state(state)
    assert "1 field was loaded" in _notice(game_env)


def test_valid_float_integers_and_old_saves_are_accepted(game_env):
    m = game_env.module
    state = _good_state(game_env)
    state["region"]["round_number"] = 5.0
    state["region"]["tipping_events"] = 0.0
    clean, problems = m.sanitize_save(state)
    assert problems == []
    old = {"region": {"round_number": 3, "funds": 100, "temperature": 3.0}}
    assert m.sanitize_save(old)[1] == []


def test_unknown_keys_are_ignored_not_reported(game_env):
    m = game_env.module
    state = _good_state(game_env)
    state["from_the_future"] = {"x": 1}
    state["region"]["new_thing"] = 5
    assert m.sanitize_save(state)[1] == []
