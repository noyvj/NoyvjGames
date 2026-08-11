"""Iteration pass: continuous color gradient per plot state (not just
one flat color per discrete state) and a one-tick "just recovered"
flash when a replanting plot finishes recovery.
"""

import pytest


def test_maturity_fraction_zero_for_fresh_preserved_plot(game_env):
    assert game_env.plot(0).maturity_fraction() == 0.0


def test_maturity_fraction_rises_with_ticks_intact(game_env):
    game_env.timers.tick_intervals(10)
    assert game_env.plot(0).maturity_fraction() == pytest.approx(10 / 60)


def test_maturity_fraction_caps_at_one(game_env):
    game_env.timers.tick_intervals(200)
    assert game_env.plot(0).maturity_fraction() == 1.0


def test_maturity_fraction_zero_for_bare_plot(game_env):
    game_env.select(0)
    game_env.clear()
    assert game_env.plot(0).maturity_fraction() == 0.0


def test_maturity_fraction_reflects_replant_progress(game_env):
    game_env.select(0)
    game_env.clear()
    game_env.select(0)
    game_env.replant()
    game_env.timers.tick_intervals(5)  # halfway through a 10-tick recovery
    assert game_env.plot(0).maturity_fraction() == pytest.approx(0.5)


def test_display_color_bare_is_flat(game_env):
    game_env.select(0)
    game_env.clear()
    assert game_env.module.plot_display_color(game_env.plot(0)) == game_env.module.BARE_COLOR


def test_display_color_shifts_toward_mature_green_over_time(game_env):
    early_color = game_env.module.plot_display_color(game_env.plot(0))
    game_env.timers.tick_intervals(60)
    late_color = game_env.module.plot_display_color(game_env.plot(0))
    assert early_color != late_color
    assert late_color == game_env.module.GROWING_END_COLOR


def test_lerp_color_at_endpoints(game_env):
    lerp = game_env.module._lerp_color
    assert lerp("#000000", "#ffffff", 0.0) == "#000000"
    assert lerp("#000000", "#ffffff", 1.0) == "#ffffff"


def test_just_recovered_flag_set_on_recovery_completion(game_env):
    game_env.select(0)
    game_env.clear()
    game_env.select(0)
    game_env.replant()
    game_env.timers.tick_intervals(10)  # exactly RECOVERY_TICKS
    assert game_env.plot(0).state == game_env.module.RECOVERED


def test_render_grid_applies_flash_class_once(game_env):
    game_env.select(0)
    game_env.clear()
    game_env.select(0)
    game_env.replant()
    game_env.timers.tick_intervals(10)  # completes recovery + renders
    assert "plot-just-recovered" in game_env.elements["plot-0"].className

    game_env.module.render_grid()  # a second render shouldn't re-flash
    assert "plot-just-recovered" not in game_env.elements["plot-0"].className


def test_render_grid_sets_background_color_style(game_env):
    game_env.module.render_grid()
    assert game_env.elements["plot-0"].style.backgroundColor
