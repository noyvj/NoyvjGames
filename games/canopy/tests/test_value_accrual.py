"""Milestone 2: passive standing value accrual for preserved/recovered plots."""

BARE = "bare"
REPLANTING = "replanting"
RECOVERED = "recovered"


def test_preserved_plot_accrues_value_over_ticks(game_env):
    plot = game_env.plot(0)
    assert plot.value == 0.0
    game_env.timers.tick_intervals(times=1)
    assert plot.value > 0.0


def test_bare_plot_does_not_accrue_value(game_env):
    plot = game_env.plot(0)
    plot.state = BARE
    game_env.timers.tick_intervals(times=3)
    assert plot.value == 0.0


def test_replanting_plot_does_not_accrue_value(game_env):
    plot = game_env.plot(0)
    plot.state = REPLANTING
    game_env.timers.tick_intervals(times=3)
    assert plot.value == 0.0


def test_recovered_plot_accrues_value(game_env):
    plot = game_env.plot(0)
    plot.state = RECOVERED
    game_env.timers.tick_intervals(times=1)
    assert plot.value > 0.0


def test_value_growth_rate_increases_over_time(game_env):
    plot = game_env.plot(0)
    game_env.timers.tick_intervals(times=1)
    first_tick_value = plot.value
    game_env.timers.tick_intervals(times=1)
    second_tick_delta = plot.value - first_tick_value
    # The per-tick increment itself grows — patience compounds, it isn't a
    # flat accrual rate.
    assert second_tick_delta > first_tick_value


def test_ticks_intact_advances_only_while_accruing(game_env):
    plot = game_env.plot(0)
    plot.state = BARE
    game_env.timers.tick_intervals(times=5)
    assert plot.ticks_intact == 0


def test_clearing_resets_value_and_ticks_intact(game_env):
    plot = game_env.plot(0)
    game_env.timers.tick_intervals(times=3)
    assert plot.value > 0.0
    game_env.select(0)
    game_env.clear()
    assert plot.value == 0.0
    assert plot.ticks_intact == 0


def test_panel_displays_current_value(game_env):
    game_env.timers.tick_intervals(times=2)
    game_env.select(0)
    assert "value" in game_env.elements["selected-plot-state"].innerText.lower()
