"""Milestone 5: composite wellbeing scoring — three separately tracked
sub-scores (service quality, economic health, social cohesion) rather
than one blended number, averaged into a single wellbeing score.

test_prepared_region_beats_unprepared is the key hope-angle proof at
the scoring level: a region that invests ahead of pressure should score
meaningfully better than one that doesn't, across all three dimensions.
"""

import pytest


def test_service_quality_starts_at_100(game_env):
    assert game_env.region.service_quality() == pytest.approx(100.0)


def test_economic_health_reflects_starting_funds(game_env):
    # 300 / 1000 * 100 = 30
    assert game_env.region.economic_health() == pytest.approx(30.0)


def test_economic_health_caps_at_100(game_env):
    game_env.region.funds = 5000.0
    assert game_env.region.economic_health() == pytest.approx(100.0)


def test_social_cohesion_zero_before_any_arrivals(game_env):
    assert game_env.region.social_cohesion() == 0.0


def test_social_cohesion_reflects_integration_fraction(game_env):
    game_env.region.total_arrivals = 20.0
    game_env.region.integrated_population = 5.0
    assert game_env.region.social_cohesion() == pytest.approx(25.0)


def test_wellbeing_score_is_average_of_three_subscores(game_env):
    game_env.region.total_arrivals = 20.0
    game_env.region.integrated_population = 10.0  # social cohesion 50
    game_env.region.funds = 500.0  # economic health 50
    # service quality still 100 (no strain logged yet)
    expected = (100.0 + 50.0 + 50.0) / 3
    assert game_env.region.wellbeing_score() == pytest.approx(expected)


def test_average_strain_reflects_sustained_history(game_env):
    game_env.region.strain_log = [0.0, 1.0]
    assert game_env.region.average_strain() == pytest.approx(0.5)


def test_prepared_region_beats_unprepared(game_env):
    """The hope-angle proof: heavy upfront investment across all three
    capacity types should produce a visibly higher wellbeing score than
    doing nothing, across a normal session length."""
    unprepared = game_env.region
    for _ in range(15):
        unprepared.advance_round()
    unprepared_score = unprepared.wellbeing_score()

    game_env.module.region.__init__()
    prepared = game_env.region
    prepared.funds = 1000.0
    for _ in range(3):
        prepared.invest("housing")
        prepared.invest("services")
        prepared.invest("infrastructure")
    for _ in range(15):
        prepared.advance_round()
    prepared_score = prepared.wellbeing_score()

    assert prepared_score > unprepared_score


def test_render_shows_subscore_displays(game_env):
    game_env.module.render()
    assert "Service quality" in game_env.elements["service-quality-display"].innerText
    assert "Economic health" in game_env.elements["economic-health-display"].innerText
    assert "Social cohesion" in game_env.elements["social-cohesion-display"].innerText


def test_render_shows_wellbeing_message(game_env):
    game_env.module.render()
    assert len(game_env.elements["wellbeing-message-display"].innerText) > 0
