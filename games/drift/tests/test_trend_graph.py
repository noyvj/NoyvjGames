"""Addendum I1: a mini strain/wellbeing trend graph, same rendering
approach as Grid's own trend_graph_svg -- an SVG built as a Python
string and assigned via .innerHTML rather than DOM-built.

wellbeing_log is logged once per completed round (see RegionState.__init__
and advance_round()'s comment), the same way arrivals_log/strain_log
already were, since wellbeing_score() depends on cumulative state that
can't be recomputed for a past round after the fact.
"""

import pytest


def test_wellbeing_log_starts_empty(game_env):
    assert game_env.region.wellbeing_log == []


def test_wellbeing_log_gains_one_entry_per_round(game_env):
    game_env.advance_round()
    assert len(game_env.region.wellbeing_log) == 1
    game_env.advance_round()
    assert len(game_env.region.wellbeing_log) == 2


def test_wellbeing_log_matches_wellbeing_score_at_time_logged(game_env):
    game_env.advance_round()
    assert game_env.region.wellbeing_log[-1] == pytest.approx(
        game_env.region.wellbeing_score()
    )


def test_trend_graph_svg_empty_with_fewer_than_two_points(game_env):
    module = game_env.module
    assert module.trend_graph_svg([], []) == ""
    assert module.trend_graph_svg([0.2], [40.0]) == ""


def test_trend_graph_svg_contains_two_polylines(game_env):
    module = game_env.module
    svg = module.trend_graph_svg([0.1, 0.3, 0.6], [60.0, 50.0, 35.0])
    assert svg.count("<polyline") == 2
    assert "trend-line--strain" in svg
    assert "trend-line--wellbeing" in svg


def test_trend_graph_svg_marker_count_matches_history_length(game_env):
    module = game_env.module
    svg = module.trend_graph_svg([0.1, 0.2, 0.3, 0.4], [70.0, 65.0, 60.0, 55.0])
    # Two markers (strain + wellbeing) per round.
    assert svg.count("<circle") == 8


def test_trend_graph_svg_marker_title_carries_exact_value(game_env):
    module = game_env.module
    svg = module.trend_graph_svg([0.5, 0.5], [42.0, 42.0])
    assert "Wellbeing: 42" in svg
    assert "Strain: 50" in svg


def test_render_shows_trend_graph_message_before_enough_rounds(game_env):
    game_env.module.render()
    assert (
        game_env.elements["trend-graph-message"].innerText
        == "Not enough rounds yet to show a trend."
    )
    assert game_env.elements["trend-graph"].innerHTML == ""


def test_render_shows_trend_graph_after_two_rounds(game_env):
    game_env.advance_round()
    game_env.advance_round()
    game_env.module.render()
    assert game_env.elements["trend-graph-message"].innerText == ""
    assert "<svg" in game_env.elements["trend-graph"].innerHTML
