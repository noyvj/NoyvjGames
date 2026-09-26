"""G27: the optional thaw-forecast mini-game."""


def _lock(env, value):
    env.elements["forecast-input"].value = value
    env.elements["forecast-lock-button"].dispatch("click", None)


def _exact_next(env):
    """Region A's temperature after the coming round, computed the way a
    careful player would from the displayed warming rate."""
    r = env.region
    return r.temperature + r.current_rise_rate()


def test_starts_with_invitation_and_no_record(game_env):
    game_env.module.render()
    assert "Optional" in game_env.elements["forecast-status"].innerText
    assert game_env.elements["forecast-record"].hidden is True
    assert game_env.module.forecast_title() is None


def test_locking_a_guess_shows_it(game_env):
    _lock(game_env, "1.0")
    assert game_env.module.forecast_guess == 1.0
    assert "locked in: +1.0" in game_env.elements["forecast-status"].innerText
    assert game_env.elements["forecast-lock-button"].innerText == "Change forecast"


def test_changing_a_locked_guess(game_env):
    _lock(game_env, "1.0")
    _lock(game_env, "2.5")
    assert game_env.module.forecast_guess == 2.5


def test_bad_input_is_ignored(game_env):
    m = game_env.module
    for bad in ("", "abc", "nan", "inf", "-inf", "99999", "-500", None):
        _lock(game_env, bad)
        assert m.forecast_guess is None


def test_hit_scores_and_clears_the_guess(game_env):
    m = game_env.module
    _lock(game_env, str(round(_exact_next(game_env), 2)))
    game_env.advance_round()
    assert m.forecast_total == 1 and m.forecast_hits == 1
    assert m.forecast_guess is None
    assert "Nailed it" in game_env.elements["forecast-status"].innerText
    assert game_env.elements["forecast-record"].hidden is False


def test_miss_scores_a_miss(game_env):
    m = game_env.module
    _lock(game_env, "50")
    game_env.advance_round()
    assert m.forecast_total == 1 and m.forecast_hits == 0
    assert "Not quite" in game_env.elements["forecast-status"].innerText


def test_tolerance_boundary(game_env):
    m = game_env.module
    _lock(game_env, str(_exact_next(game_env) + m.FORECAST_TOLERANCE - 0.01))
    game_env.advance_round()
    assert m.forecast_hits == 1
    _lock(game_env, str(_exact_next(game_env) + m.FORECAST_TOLERANCE + 0.05))
    game_env.advance_round()
    assert m.forecast_hits == 1 and m.forecast_total == 2


def test_no_guess_means_no_scoring(game_env):
    game_env.advance_round()
    assert game_env.module.forecast_total == 0


def test_forecast_never_touches_game_mechanics(game_env):
    a = game_env.module.region_b
    b = game_env.module.region_c
    game_env.advance_round()
    ref = (a.temperature, b.temperature, game_env.region.funds)
    _lock(game_env, "999")
    game_env.advance_round()
    control_env_temp = game_env.region.temperature
    assert control_env_temp > 0
    # the forecast is scored but region B/C advance exactly as they would have
    assert a.temperature > ref[0] and b.temperature > ref[1]


def test_titles_by_attempts_and_hit_rate(game_env):
    m = game_env.module
    m.forecast_total, m.forecast_hits = 1, 0
    assert m.forecast_title() == "Apprentice Forecaster"
    m.forecast_total, m.forecast_hits = 5, 3
    assert m.forecast_title() == "Seasoned Forecaster"
    m.forecast_total, m.forecast_hits = 10, 8
    assert m.forecast_title() == "Master Forecaster"
    m.forecast_total, m.forecast_hits = 10, 4
    assert m.forecast_title() == "Apprentice Forecaster"
    m.forecast_total, m.forecast_hits = 4, 4
    assert m.forecast_title() == "Apprentice Forecaster"


def test_save_round_trip(game_env):
    m = game_env.module
    m.forecast_total, m.forecast_hits = 6, 4
    data = m.get_state()
    assert data["forecast"] == {"total": 6, "hits": 4}
    m.forecast_total, m.forecast_hits = 0, 0
    m.forecast_guess = 3.0
    m.load_state(data)
    assert (m.forecast_total, m.forecast_hits) == (6, 4)
    assert m.forecast_guess is None  # a locked guess is per-session


def test_fresh_save_omits_forecast(game_env):
    assert "forecast" not in game_env.module.get_state()


def test_load_rejects_bad_forecast_values(game_env):
    m = game_env.module
    for bad in ("x", [1], {"total": "3", "hits": 1}, {"total": 3, "hits": 9},
                {"total": -1, "hits": -1}, {"total": True, "hits": True},
                {"total": 2.5, "hits": 1}, {"total": 10**9, "hits": 1}, {}):
        data = m.get_state()
        data["forecast"] = bad
        m.load_state(data)
        assert (m.forecast_total, m.forecast_hits) == (0, 0)


def test_loading_without_forecast_key_resets_record(game_env):
    m = game_env.module
    m.forecast_total, m.forecast_hits = 5, 5
    data = m.get_state()
    del data["forecast"]
    m.load_state(data)
    assert (m.forecast_total, m.forecast_hits) == (0, 0)
