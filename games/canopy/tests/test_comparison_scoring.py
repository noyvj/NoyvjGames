"""Milestone 5: comparison scoring — the live "harvested income vs standing
forest value" hope-angle payoff.
"""

BARE = "bare"


def test_standing_forest_value_starts_at_zero(game_env):
    assert game_env.module.standing_forest_value() == 0.0


def test_standing_forest_value_sums_across_plots(game_env):
    game_env.timers.tick_intervals(times=2)
    expected = sum(p.value for p in game_env.module.plots)
    assert game_env.module.standing_forest_value() == expected
    assert expected > 0.0


def test_standing_forest_value_excludes_bare_plots(game_env):
    plot = game_env.plot(0)
    game_env.timers.tick_intervals(times=2)
    game_env.select(0)
    game_env.clear()  # plot 0 is now bare, value reset to 0
    total = game_env.module.standing_forest_value()
    other_plots_total = sum(p.value for p in game_env.module.plots if p.index != 0)
    assert total == other_plots_total
    assert plot.value == 0.0


def test_comparison_message_when_nothing_has_happened(game_env):
    message = game_env.module.comparison_message(0, 0)
    assert "Nothing harvested" in message


def test_comparison_message_when_standing_value_wins(game_env):
    message = game_env.module.comparison_message(5.0, 20.0)
    assert "standing forest" in message.lower()
    assert "20.0" in message
    assert "5.0" in message


def test_comparison_message_when_income_wins(game_env):
    message = game_env.module.comparison_message(20.0, 5.0)
    assert "harvested more" in message.lower()
    assert "20.0" in message
    assert "5.0" in message


def test_comparison_message_when_tied(game_env):
    message = game_env.module.comparison_message(10.0, 10.0)
    assert "evenly matched" in message.lower()


def test_render_shows_standing_value(game_env):
    game_env.timers.tick_intervals(times=2)
    text = game_env.elements["standing-value-display"].innerText
    assert "Standing forest value" in text
    assert text != "Standing forest value: 0.0"


def test_render_shows_income_after_clearing(game_env):
    game_env.timers.tick_intervals(times=2)
    game_env.select(0)
    game_env.clear()
    text = game_env.elements["income-display"].innerText
    assert text != "Harvested income: 0.0"


def test_render_shows_comparison_message(game_env):
    game_env.timers.tick_intervals(times=2)
    text = game_env.elements["comparison-message"].innerText
    assert "standing forest" in text.lower()
