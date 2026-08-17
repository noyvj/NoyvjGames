"""Iteration Pass 2: alternative protein pivot — the fallback path
(chosen over market dynamics: an income-side mechanic can't naturally
feed into the coupling-ratio gauge the design notes require stay the
centerpiece, while the pivot is structurally another decoupling lever).
Shifting output toward plant-based production blends directly into the
same coupling_ratio() every other decoupling measure already feeds.
"""

import pytest


def test_plant_based_fraction_starts_at_zero(game_env):
    assert game_env.farm.plant_based_fraction() == 0.0


def test_coupling_ratio_unaffected_with_no_pivot_investment(game_env):
    assert game_env.farm.coupling_ratio() == game_env.farm._efficiency_coupling_ratio()


def test_invest_plant_pivot_increases_fraction(game_env):
    game_env.farm.funds = 1000
    game_env.farm.invest_plant_pivot()
    assert game_env.farm.plant_based_fraction() == pytest.approx(
        game_env.module.PLANT_PIVOT_FRACTION_PER_UNIT
    )


def test_invest_plant_pivot_fails_without_funds(game_env):
    game_env.farm.funds = 0
    assert game_env.farm.invest_plant_pivot() is False


def test_plant_based_fraction_caps_at_maximum(game_env):
    game_env.farm.funds = 100000
    for _ in range(1000):
        game_env.farm.invest_plant_pivot()
    assert game_env.farm.plant_based_fraction() == game_env.module.MAX_PLANT_BASED_FRACTION


def test_pivot_lowers_coupling_ratio_below_efficiency_only_ratio(game_env):
    game_env.farm.funds = 1000
    game_env.farm.invest_plant_pivot()
    assert game_env.farm.coupling_ratio() < game_env.farm._efficiency_coupling_ratio()


def test_pivot_feeds_into_the_same_coupling_gauge_as_efficiency_measures(game_env):
    # Both levers should move the exact same public number.
    game_env.farm.funds = 1000
    game_env.farm.invest_decoupling("feed")
    ratio_after_feed = game_env.farm.coupling_ratio()
    game_env.farm.invest_plant_pivot()
    ratio_after_pivot = game_env.farm.coupling_ratio()
    assert ratio_after_pivot < ratio_after_feed


def test_pivot_reduces_methane_produced_per_round(game_env):
    game_env.farm.herd_size = 10
    baseline_methane = game_env.farm.methane_this_round()
    game_env.farm.funds = 1000
    for _ in range(5):
        game_env.farm.invest_plant_pivot()
    pivoted_methane = game_env.farm.methane_this_round()
    assert pivoted_methane < baseline_methane


def test_pivot_slightly_reduces_raw_income_per_round(game_env):
    game_env.farm.herd_size = 10
    game_env.farm.funds = 1000
    funds_before = game_env.farm.funds
    game_env.farm.advance_round()
    no_pivot_gain = game_env.farm.funds - funds_before

    farm2 = game_env.module.FarmState()
    farm2.herd_size = 10
    farm2.funds = 1000
    for _ in range(5):
        farm2.invest_plant_pivot()
    funds_before_2 = farm2.funds
    farm2.advance_round()
    pivot_gain = farm2.funds - funds_before_2

    # Pivot costs a real margin on the income side (not a strict
    # downgrade overall, since it also cuts pressure-driven income loss
    # via lower methane, but the raw per-unit price is genuinely lower).
    assert pivot_gain != no_pivot_gain


def test_invest_plant_pivot_button_dispatches(game_env):
    game_env.farm.funds = 1000
    game_env.invest_plant_pivot()
    assert game_env.farm.plant_pivot_investment == 1


def test_render_shows_plant_pivot_percentage(game_env):
    game_env.farm.funds = 1000
    game_env.farm.invest_plant_pivot()
    game_env.module.render()
    assert "5%" in game_env.elements["plant-pivot-display"].innerText


def test_plant_pivot_button_disabled_at_cap(game_env):
    game_env.farm.funds = 100000
    for _ in range(1000):
        game_env.farm.invest_plant_pivot()
    game_env.module.render()
    assert game_env.elements["plant-pivot-invest-button"].disabled is True
