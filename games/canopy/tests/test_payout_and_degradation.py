"""Milestone 3: clearing harvests standing value as income; repeated
clearing of the same plot permanently degrades its future productivity.
"""

import pytest


def test_clearing_pays_out_the_plots_accrued_value(game_env):
    plot = game_env.plot(0)
    game_env.timers.tick_intervals(times=3)
    accrued = plot.value
    game_env.select(0)
    game_env.clear()
    assert game_env.total_income == accrued


def test_clearing_with_zero_value_pays_out_zero(game_env):
    game_env.select(0)
    game_env.clear()
    assert game_env.total_income == 0.0


def test_income_accumulates_across_multiple_clears(game_env):
    game_env.timers.tick_intervals(times=2)
    first_value = game_env.plot(0).value
    game_env.select(0)
    game_env.clear()

    game_env.timers.tick_intervals(times=2)
    second_value = game_env.plot(1).value
    game_env.select(1)
    game_env.clear()

    assert game_env.total_income == first_value + second_value


def test_invalid_clear_does_not_change_income(game_env):
    plot = game_env.plot(0)
    plot.state = "bare"
    game_env.select(0)
    game_env.clear()
    assert game_env.total_income == 0.0


def test_first_clear_increments_clear_count(game_env):
    plot = game_env.plot(0)
    game_env.select(0)
    game_env.clear()
    assert plot.clear_count == 1


def test_never_cleared_plot_has_full_productivity(game_env):
    plot = game_env.plot(0)
    assert plot.productivity_multiplier() == 1.0


def test_productivity_degrades_after_a_clear(game_env):
    plot = game_env.plot(0)
    game_env.select(0)
    game_env.clear()
    assert plot.productivity_multiplier() == 0.9


def test_productivity_degradation_stacks_across_clear_replant_cycles(game_env):
    plot = game_env.plot(0)
    for _ in range(3):
        game_env.select(plot.index)
        game_env.clear()
        plot.replant()
        plot.finish_recovery()
    assert plot.clear_count == 3
    assert plot.productivity_multiplier() == round(1 - 0.1 * 3, 10)


def test_productivity_multiplier_never_drops_below_floor(game_env):
    plot = game_env.plot(0)
    plot.clear_count = 100
    assert plot.productivity_multiplier() == 0.2


def test_degraded_plot_accrues_value_more_slowly(game_env):
    fresh_plot = game_env.plot(0)
    degraded_plot = game_env.plot(1)
    degraded_plot.clear_count = 1

    game_env.timers.tick_intervals(times=1)

    assert degraded_plot.value < fresh_plot.value
    assert degraded_plot.value == pytest.approx(fresh_plot.value * 0.9)


def test_clearing_resets_value_but_keeps_clear_count(game_env):
    plot = game_env.plot(0)
    game_env.timers.tick_intervals(times=2)
    game_env.select(0)
    game_env.clear()
    assert plot.value == 0.0
    assert plot.clear_count == 1


def test_income_display_updates_on_clear(game_env):
    game_env.timers.tick_intervals(times=2)
    game_env.select(0)
    game_env.clear()
    assert "Harvested income" in game_env.elements["income-display"].innerText
    assert game_env.elements["income-display"].innerText != "Harvested income: 0.0"
