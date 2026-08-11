"""Iteration pass: a three-bar composite wellbeing dashboard and a
mid-run plain-language checkpoint identifying which dimension is
currently lagging most.
"""

import pytest


def test_checkpoint_identifies_cohesion_by_default(game_env):
    # fresh region: service quality 100, economic health 30, cohesion 0
    # -> cohesion is lowest
    msg = game_env.module.checkpoint_message(game_env.region)
    assert "cohesion" in msg.lower()


def test_checkpoint_identifies_services_when_strain_dominates(game_env):
    game_env.region.strain_log = [1.0, 1.0, 1.0]  # service_quality -> 0
    game_env.region.funds = 1000.0  # economic_health -> 100
    game_env.region.total_arrivals = 10.0
    game_env.region.integrated_population = 10.0  # cohesion -> 100
    msg = game_env.module.checkpoint_message(game_env.region)
    assert "services" in msg.lower() or "service" in msg.lower()


def test_checkpoint_identifies_economy_when_funds_are_lowest(game_env):
    game_env.region.strain_log = [0.0]  # service_quality -> 100
    game_env.region.funds = 0.0  # economic_health -> 0
    game_env.region.total_arrivals = 10.0
    game_env.region.integrated_population = 10.0  # cohesion -> 100
    msg = game_env.module.checkpoint_message(game_env.region)
    assert "economic" in msg.lower() or "economy" in msg.lower()


def test_render_shows_checkpoint_message(game_env):
    game_env.module.render()
    assert len(game_env.elements["checkpoint-display"].innerText) > 0


def test_render_service_quality_bar_starts_full(game_env):
    game_env.module.render()
    assert game_env.elements["service-quality-bar"].style.width == "100%"


def test_render_economic_health_bar_matches_starting_funds(game_env):
    game_env.module.render()
    # 300 / 1000 * 100 = 30
    assert game_env.elements["economic-health-bar"].style.width == "30%"


def test_render_social_cohesion_bar_starts_empty(game_env):
    game_env.module.render()
    assert game_env.elements["social-cohesion-bar"].style.width == "0%"


def test_render_bars_update_after_rounds(game_env):
    for _ in range(5):
        game_env.advance_round()
    assert game_env.elements["economic-health-bar"].style.width != "30%"
