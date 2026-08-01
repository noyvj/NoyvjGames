"""Milestone 4: replanted plots recover automatically after a fixed number
of ticks, on a slower timeline than a never-cleared plot, reaching
near-parity productivity (not full parity) once recovered.
"""

BARE = "bare"
REPLANTING = "replanting"
RECOVERED = "recovered"
RECOVERY_TICKS_FOR_TEST = 10


def test_replant_starts_the_recovery_countdown(game_env):
    plot = game_env.plot(0)
    plot.state = BARE
    plot.replant()
    assert plot.replant_ticks_remaining == 10


def test_replanting_plot_stays_replanting_before_timer_elapses(game_env):
    plot = game_env.plot(0)
    plot.state = BARE
    plot.replant()
    game_env.timers.tick_intervals(times=9)
    assert plot.state == REPLANTING


def test_replanting_plot_auto_recovers_when_timer_elapses(game_env):
    plot = game_env.plot(0)
    plot.state = BARE
    plot.replant()
    game_env.timers.tick_intervals(times=10)
    assert plot.state == RECOVERED


def test_recovery_timer_does_not_advance_outside_replanting(game_env):
    plot = game_env.plot(0)
    game_env.timers.tick_intervals(times=5)
    assert plot.replant_ticks_remaining == 0


def test_recovered_plot_resumes_accruing_value(game_env):
    plot = game_env.plot(0)
    plot.state = BARE
    plot.replant()
    game_env.timers.tick_intervals(times=10)
    assert plot.state == RECOVERED
    value_at_recovery = plot.value
    game_env.timers.tick_intervals(times=1)
    assert plot.value > value_at_recovery


def test_recovered_plot_is_near_parity_not_full_parity(game_env):
    fresh_plot = game_env.plot(0)
    recovered_plot = game_env.plot(1)
    recovered_plot.state = BARE
    recovered_plot.clear_count = 1  # one clear→replant cycle already happened
    recovered_plot.replant()

    game_env.timers.tick_intervals(times=RECOVERY_TICKS_FOR_TEST)

    assert recovered_plot.state == RECOVERED
    assert recovered_plot.productivity_multiplier() == 0.9
    assert fresh_plot.productivity_multiplier() == 1.0
    # Near-parity: close to, but not equal to, a never-cleared plot.
    assert 0 < (fresh_plot.productivity_multiplier() - recovered_plot.productivity_multiplier()) < 0.15


def test_panel_shows_countdown_while_replanting(game_env):
    plot = game_env.plot(0)
    plot.state = BARE
    game_env.select(0)
    game_env.replant()
    assert "recovering in" in game_env.elements["selected-plot-state"].innerText


def test_replant_button_disabled_after_replanting_starts(game_env):
    plot = game_env.plot(0)
    plot.state = BARE
    game_env.select(0)
    game_env.replant()
    assert game_env.elements["replant-button"].disabled is True
    assert game_env.elements["clear-button"].disabled is True
