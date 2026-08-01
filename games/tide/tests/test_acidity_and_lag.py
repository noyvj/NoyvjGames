"""Milestone 2: acidity meter and the delayed fish-stock consequence — the
core "delayed consequence" lesson. This season's fishing yield depends on
acidity from several seasons ago, not today's number.
"""

import pytest


def test_acidity_starts_at_zero(game_env):
    assert game_env.state.acidity == 0.0


def test_acidity_rises_with_output_investment(game_env):
    game_env.invest("output")
    game_env.advance_season()
    assert game_env.state.acidity == 2.0  # 1 unit * ACIDITY_RISE_PER_OUTPUT


def test_acidity_falls_with_reduction_investment(game_env):
    game_env.invest("output")
    game_env.invest("output")
    game_env.invest("reduction")
    game_env.advance_season()
    # 2*2.0 rise - 1*1.5 fall = 2.5
    assert game_env.state.acidity == pytest.approx(2.5)


def test_acidity_never_goes_negative(game_env):
    game_env.invest("reduction")
    game_env.advance_season()  # no output, only reduction -> would be negative
    assert game_env.state.acidity == 0.0


def test_acidity_accumulates_across_seasons(game_env):
    game_env.invest("output")
    game_env.advance_season()
    game_env.advance_season()
    assert game_env.state.acidity == pytest.approx(4.0)


def test_fish_yield_is_full_before_any_seasons_played(game_env):
    assert game_env.state.fish_yield_multiplier() == 1.0


def test_fish_yield_stays_full_during_lag_window_despite_high_acidity(game_env):
    # Crank acidity way up immediately, but the consequence shouldn't show
    # up until FISH_LAG_SEASONS have actually elapsed.
    for _ in range(10):
        game_env.invest("output")
    game_env.advance_season()
    game_env.advance_season()
    assert game_env.state.acidity > 0
    assert game_env.state.fish_yield_multiplier() == 1.0  # only 2 of 3 lag seasons elapsed


def test_fish_yield_degrades_once_lag_window_elapses(game_env):
    for _ in range(10):
        game_env.invest("output")
    game_env.advance_season()
    game_env.advance_season()
    game_env.advance_season()  # 3rd season — lag window has now elapsed
    assert game_env.state.fish_yield_multiplier() < 1.0


def test_income_reflects_lagged_not_current_acidity(game_env):
    # Build a lot of output, run one season (acidity spikes), then remove
    # nothing — the NEXT couple of seasons' income should still be at full
    # multiplier because the spike hasn't "arrived" as a consequence yet.
    for _ in range(10):
        game_env.invest("output")
    funds_before = game_env.state.funds
    game_env.advance_season()
    full_income = game_env.state.capacity["output"] * 6  # OUTPUT_INCOME_PER_UNIT
    assert game_env.state.funds == pytest.approx(funds_before + full_income)


def test_fish_yield_floors_at_minimum(game_env):
    game_env.state.acidity_history = [999999.0, 999999.0, 999999.0]
    assert game_env.state.fish_yield_multiplier() == 0.2


def test_render_shows_acidity_and_fish_yield(game_env):
    game_env.invest("output")
    game_env.advance_season()
    assert "2.0" in game_env.elements["acidity-display"].innerText
    assert "100%" in game_env.elements["fish-yield-display"].innerText
