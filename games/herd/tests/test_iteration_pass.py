"""Iteration pass: a prominent coupling-ratio dial gauge and an ambient
haze overlay tracking methane pressure.
"""

import pytest


def test_lerp_color_at_endpoints(game_env):
    lerp = game_env.module._lerp_color
    assert lerp("#000000", "#ffffff", 0.0) == "#000000"
    assert lerp("#000000", "#ffffff", 1.0) == "#ffffff"


def test_gauge_svg_empty_dash_at_zero_fraction(game_env):
    svg = game_env.module.coupling_gauge_svg(0.0)
    assert 'stroke-dasharray="0.0 100"' in svg


def test_gauge_svg_full_dash_at_one_fraction(game_env):
    svg = game_env.module.coupling_gauge_svg(1.0)
    assert 'stroke-dasharray="100.0 100"' in svg


def test_gauge_svg_uses_low_color_when_decoupled(game_env):
    svg = game_env.module.coupling_gauge_svg(0.0)
    assert game_env.module.GAUGE_LOW_COLOR in svg


def test_gauge_svg_uses_high_color_when_fully_coupled(game_env):
    svg = game_env.module.coupling_gauge_svg(1.0)
    assert game_env.module.GAUGE_HIGH_COLOR in svg


def test_gauge_svg_clamps_out_of_range_fractions(game_env):
    svg_low = game_env.module.coupling_gauge_svg(-5.0)
    svg_high = game_env.module.coupling_gauge_svg(5.0)
    assert 'stroke-dasharray="0.0 100"' in svg_low
    assert 'stroke-dasharray="100.0 100"' in svg_high


def test_render_shows_gauge_svg(game_env):
    game_env.module.render()
    assert "<svg" in game_env.elements["coupling-gauge"].innerHTML


def test_render_gauge_starts_at_full_coupling(game_env):
    # coupling_ratio() starts at BASE_COUPLING_RATIO (1.0) -> fraction 1.0
    game_env.module.render()
    assert 'stroke-dasharray="100.0 100"' in game_env.elements["coupling-gauge"].innerHTML


def test_render_gauge_shrinks_after_decoupling_investment(game_env):
    game_env.farm.funds = 1000.0
    game_env.invest_decoupling("capture")
    game_env.module.render()
    html = game_env.elements["coupling-gauge"].innerHTML
    assert 'stroke-dasharray="100.0 100"' not in html


def test_haze_overlay_zero_by_default(game_env):
    game_env.module.render()
    assert game_env.elements["haze-overlay"].style.opacity == "0.000"


def test_haze_overlay_rises_with_pressure(game_env):
    game_env.farm.methane = 50.0  # 50% of PRESSURE_SCALE
    game_env.module.render()
    expected = (game_env.farm.pressure_fraction() / game_env.module.MAX_PRESSURE) * game_env.module.MAX_HAZE_OPACITY
    assert game_env.elements["haze-overlay"].style.opacity == f"{expected:.3f}"


def test_haze_overlay_caps_at_max_opacity(game_env):
    game_env.farm.methane = 10_000.0
    game_env.module.render()
    assert game_env.elements["haze-overlay"].style.opacity == f"{game_env.module.MAX_HAZE_OPACITY:.3f}"
