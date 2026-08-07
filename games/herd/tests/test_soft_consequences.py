"""Milestone 4: soft consequence system — sustained methane deterministically
cuts into income via market/regulatory pressure. No hard fail-state, no
randomness, no destroyed infrastructure — just a self-limiting revenue drag.
"""

import pytest


def test_pressure_is_zero_with_no_methane(game_env):
    assert game_env.farm.pressure_fraction() == 0.0


def test_pressure_scales_with_methane(game_env):
    game_env.farm.methane = 50.0
    assert game_env.farm.pressure_fraction() == pytest.approx(0.5)


def test_pressure_caps_at_maximum(game_env):
    game_env.farm.methane = 999999.0
    assert game_env.farm.pressure_fraction() == 0.8


def test_pressure_reduces_income_this_round(game_env):
    game_env.grow_herd()
    game_env.grow_herd()
    game_env.farm.methane = 50.0  # 50% pressure
    funds_before = game_env.farm.funds
    game_env.advance_round()
    full_income = 2 * 5  # herd_size * HERD_INCOME_PER_UNIT
    expected_income = full_income * 0.5
    assert game_env.farm.funds == pytest.approx(funds_before + expected_income)


def test_zero_methane_means_full_income(game_env):
    game_env.grow_herd()
    funds_before = game_env.farm.funds
    game_env.advance_round()
    assert game_env.farm.funds == funds_before + 5


def test_unchecked_growth_earns_less_than_full_income_over_time(game_env):
    # Grow aggressively with zero decoupling — income should visibly lag
    # behind the naive herd_size * HERD_INCOME_PER_UNIT as methane piles up.
    for _ in range(10):
        game_env.grow_herd()
    for _ in range(10):
        game_env.advance_round()
    naive_total_income = 10 * game_env.farm.round_number * 5  # wildly generous upper bound
    assert game_env.farm.funds < naive_total_income


def test_pressure_never_fully_eliminates_income(game_env):
    game_env.grow_herd()
    game_env.farm.methane = 999999.0
    funds_before = game_env.farm.funds
    game_env.advance_round()
    assert game_env.farm.funds > funds_before  # some income still gets through


def test_no_hard_fail_state_funds_never_forced_negative_by_pressure(game_env):
    game_env.farm.funds = 0.0
    game_env.farm.methane = 999999.0
    game_env.advance_round()
    assert game_env.farm.funds >= 0.0


def test_render_shows_pressure_and_methane_bar(game_env):
    game_env.farm.methane = 50.0
    game_env.module.render()
    assert "50%" in game_env.elements["pressure-display"].innerText
    assert game_env.elements["methane-bar"].style.width == "50%"
