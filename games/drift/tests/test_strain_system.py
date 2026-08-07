"""Milestone 3: strain vs. capacity system — visible, soft consequences
when investment lags behind arrival pressure. No hard fail-state: strain
eats into regional income, capped at 1.0, never blocking play outright.
"""

import pytest


def test_strain_zero_before_any_arrivals(game_env):
    assert game_env.region.strain_fraction() == 0.0
    assert game_env.region.strain_level() == "stable"


def test_strain_maxes_out_with_zero_capacity(game_env):
    game_env.advance_round()  # 5 people arrive, no capacity built
    assert game_env.region.strain_fraction() == pytest.approx(1.0)
    assert game_env.region.strain_level() == "critical"


def test_strain_zero_when_capacity_covers_arrivals(game_env):
    game_env.region.invest("housing")  # +10 capacity
    game_env.advance_round()  # 5 people arrive, covered by 10 capacity
    assert game_env.region.strain_fraction() == 0.0


def test_strain_partial_when_capacity_falls_short(game_env):
    game_env.region.invest("housing")  # +10 capacity
    game_env.advance_round()  # total_arrivals=5, covered
    game_env.advance_round()  # total_arrivals=11.5, capacity=10
    # shortfall = 1.5, strain = 1.5 / 11.5
    assert game_env.region.strain_fraction() == pytest.approx(1.5 / 11.5)


def test_strain_level_thresholds(game_env):
    game_env.region.invest("housing")
    game_env.region.invest("housing")  # +20 capacity, comfortably covers early arrivals
    game_env.advance_round()
    assert game_env.region.strain_level() == "stable"


def test_strain_reduces_income(game_env):
    game_env.advance_round()  # strain 0 this round -> full income
    funds_after_round_1 = game_env.region.funds
    assert funds_after_round_1 == pytest.approx(300.0 + 50.0)

    funds_before_round_2 = game_env.region.funds
    game_env.advance_round()  # strain now 1.0 (zero capacity) -> zero income
    assert game_env.region.funds == pytest.approx(funds_before_round_2)


def test_strain_log_records_each_round(game_env):
    game_env.advance_round()
    game_env.advance_round()
    assert game_env.region.strain_log == pytest.approx([0.0, 1.0])


def test_strain_never_reduces_income_below_zero_contribution(game_env):
    for _ in range(5):
        game_env.advance_round()
    # income contribution each round is >= 0 even at full strain
    assert game_env.region.funds >= 300.0


def test_render_shows_strain_display(game_env):
    game_env.module.render()
    assert "stable" in game_env.elements["strain-display"].innerText


def test_render_updates_strain_bar_width(game_env):
    game_env.advance_round()
    game_env.module.render()
    assert game_env.elements["strain-bar"].style.width == "100%"
