"""Z17 (site-wide goal, planning/TODO.md): F15's real-world comparison
gains an actual chart -- previously this comparison was a text sentence
only (`real_world_comparison_message()`), with no chart at all. Built on
the shared `shared/comparison_chart.py` component's `bar_comparison_svg()`
-- the same module Grid's own C15/global-comparison line and Continuum's
K13 "vs. history" chart also now share.
"""


def test_fresh_farm_renders_a_bar_chart_with_both_values(game_env):
    svg = game_env.module.real_world_comparison_chart_svg()
    assert "<svg" in svg
    assert "comparison-bar--you" in svg
    assert "comparison-bar--reference" in svg
    assert "42.0%" in svg  # REAL_WORLD_REDUCTION_FRACTION as a percentage
    assert "0.0%" in svg  # a fresh farm hasn't decoupled anything yet


def test_chart_reflects_decoupling_progress(game_env):
    game_env.grow_herd()
    game_env.module.farm.decoupling_investment["capture"] = 5
    svg = game_env.module.real_world_comparison_chart_svg()
    pct = game_env.module.farm.decoupled_fraction() * 100
    assert f"{pct:.1f}%" in svg


def test_chart_is_wired_into_render(game_env):
    game_env.grow_herd()
    html = game_env.elements["real-world-comparison-chart"].innerHTML
    assert "<svg" in html
    assert "comparison-bar-svg" in html
