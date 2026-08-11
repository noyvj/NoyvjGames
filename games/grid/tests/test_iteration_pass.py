"""Iteration pass: emissions-vs-renewable-cost trend graph, and a
context blurb shown the first time a renewable plant is built.
"""

import pytest


def test_average_renewable_cost_starts_at_base(game_env):
    # base costs 80/70/150, no cost-curve decay applied yet
    assert game_env.state.average_renewable_cost() == pytest.approx((80 + 70 + 150) / 3)


def test_average_renewable_cost_falls_after_investment(game_env):
    before = game_env.state.average_renewable_cost()
    game_env.build("solar")
    after = game_env.state.average_renewable_cost()
    assert after < before


def test_renewable_unlocked_false_initially(game_env):
    assert game_env.state.renewable_unlocked is False


def test_renewable_unlocked_true_after_first_renewable_build(game_env):
    game_env.build("wind")
    assert game_env.state.renewable_unlocked is True


def test_renewable_unlocked_stays_false_for_fossil_builds(game_env):
    game_env.build("coal")
    game_env.build("gas")
    assert game_env.state.renewable_unlocked is False


def test_emissions_and_cost_history_grow_each_round(game_env):
    game_env.advance_round()
    game_env.advance_round()
    assert len(game_env.state.emissions_history) == 2
    assert len(game_env.state.avg_renewable_cost_history) == 2


def test_trend_graph_svg_empty_with_fewer_than_two_points(game_env):
    assert game_env.module.trend_graph_svg([], []) == ""
    assert game_env.module.trend_graph_svg([5.0], [10.0]) == ""


def test_trend_graph_svg_contains_two_polylines(game_env):
    svg = game_env.module.trend_graph_svg([0.0, 10.0, 20.0], [150.0, 100.0, 60.0])
    assert svg.count("<polyline") == 2
    assert "trend-line--emissions" in svg
    assert "trend-line--cost" in svg


def test_trend_graph_svg_point_count_matches_history_length(game_env):
    svg = game_env.module.trend_graph_svg([0.0, 5.0, 10.0, 15.0], [150.0, 140.0, 130.0, 120.0])
    # 4 points per polyline -> 4 comma-separated coordinate pairs each
    emissions_line = svg.split('class="trend-line trend-line--emissions"')[0]
    points_attr = emissions_line.split('points="')[1].split('"')[0]
    assert len(points_attr.split(" ")) == 4


def test_render_hides_blurb_by_default(game_env):
    game_env.module.render()
    assert game_env.elements["renewable-blurb"].hidden is True


def test_render_shows_blurb_after_renewable_build(game_env):
    game_env.build("hydro")
    game_env.module.render()
    assert game_env.elements["renewable-blurb"].hidden is False
    assert len(game_env.elements["renewable-blurb"].innerText) > 0


def test_render_shows_trend_graph_message_before_enough_rounds(game_env):
    game_env.module.render()
    assert "Not enough rounds" in game_env.elements["trend-graph-message"].innerText
    assert game_env.elements["trend-graph"].innerHTML == ""


def test_render_shows_trend_graph_after_two_rounds(game_env):
    game_env.advance_round()
    game_env.advance_round()
    game_env.module.render()
    assert "<svg" in game_env.elements["trend-graph"].innerHTML
    assert "Emissions" in game_env.elements["trend-graph-message"].innerText
