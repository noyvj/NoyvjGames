"""G9: the optional long-game mode stretches the whole trajectory."""


def _click(env, id_):
    env.elements[id_].dispatch("click", None)


def test_off_by_default_and_standard_speed(game_env):
    m = game_env.module
    assert m.long_game is False
    assert m.warming_scale() == 1.0
    assert game_env.region.current_rise_rate() == m.BASE_TEMP_RISE_PER_ROUND
    assert "off" in game_env.elements["long-game-toggle-button"].innerText


def test_toggle_button_turns_it_on_and_off_before_round_one(game_env):
    m = game_env.module
    _click(game_env, "long-game-toggle-button")
    assert m.long_game is True
    assert game_env.elements["long-game-toggle-button"].innerText == "Long game: on"
    assert "Long game is on" in game_env.elements["long-game-display"].innerText
    _click(game_env, "long-game-toggle-button")
    assert m.long_game is False


def test_locked_once_any_round_has_been_played(game_env):
    m = game_env.module
    game_env.advance_round()
    assert m.can_toggle_long_game() is False
    assert m.set_long_game(True) is False
    assert m.long_game is False
    assert game_env.elements["long-game-toggle-button"].disabled is True


def test_warming_runs_slower_and_takes_more_rounds_to_reach_a_milestone(game_env):
    m = game_env.module
    assert m.set_long_game(True)
    r = game_env.region
    assert r.current_rise_rate() == m.BASE_TEMP_RISE_PER_ROUND * m.LONG_GAME_WARMING_SCALE

    def rounds_to_melt():
        n = 0
        while not r.is_melting() and n < 500:
            r.advance_round()
            n += 1
        return n

    long_rounds = rounds_to_melt()
    assert long_rounds >= (m.MELT_THRESHOLD / m.BASE_TEMP_RISE_PER_ROUND) * 2


def test_feedback_and_counterfactual_scale_together(game_env):
    m = game_env.module
    m.set_long_game(True)
    r = game_env.region
    r.temperature = m.MELT_THRESHOLD + 5
    expected_bonus = 5 * m.FEEDBACK_RATE_PER_DEGREE_OVER * m.LONG_GAME_WARMING_SCALE
    assert abs(r.feedback_bonus() - expected_bonus) < 1e-9
    assert abs(r.acceleration_factor() - (1 + 5 * m.FEEDBACK_RATE_PER_DEGREE_OVER)) < 1e-9
    r.counterfactual_temperature = m.MELT_THRESHOLD + 5
    before = r.counterfactual_temperature
    r.advance_round()
    assert abs((r.counterfactual_temperature - before) - (m.BASE_TEMP_RISE_PER_ROUND * m.LONG_GAME_WARMING_SCALE + expected_bonus)) < 1e-9


def test_income_is_reduced_but_by_less_than_warming(game_env):
    m = game_env.module
    m.set_long_game(True)
    r = game_env.region
    r.capacity["output"] = 10
    r.funds = 0.0
    r.advance_round()
    assert abs(r.funds - 10 * m.OUTPUT_INCOME_PER_UNIT * m.LONG_GAME_INCOME_SCALE) < 1e-9
    assert m.LONG_GAME_INCOME_SCALE > m.LONG_GAME_WARMING_SCALE
    m.render()
    assert f"{m.output_income_per_unit():g}" in game_env.elements["output-forecast"].innerText


def test_applies_to_every_region_including_the_unmanaged_one(game_env):
    m = game_env.module
    m.set_long_game(True)
    game_env.advance_round()
    for r in (m.region, m.region_b, m.region_c, m.region_d):
        assert r.temperature <= m.BASE_TEMP_RISE_PER_ROUND * m.LONG_GAME_WARMING_SCALE + 1e-9


def test_saved_only_when_on_and_restored(game_env):
    m = game_env.module
    assert "long_game" not in m.get_state()
    m.set_long_game(True)
    state = m.get_state()
    assert state["long_game"] is True
    m.set_long_game(False)
    m.load_state(state)
    assert m.long_game is True
    m.load_state({k: v for k, v in state.items() if k != "long_game"})
    assert m.long_game is False
    m.load_state({**state, "long_game": "yes"})
    assert m.long_game is False
