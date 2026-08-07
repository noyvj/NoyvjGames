"""Milestone 5: hope-angle payoff — a parallel undampened counterfactual
trajectory proves early intervention produced a meaningfully flatter
warming curve than inaction would have.
"""

import pytest


def test_temperature_saved_is_zero_with_no_investment(game_env):
    for _ in range(5):
        game_env.advance_round()
    assert game_env.region.temperature_saved() == pytest.approx(0.0)


def test_counterfactual_tracks_actual_below_threshold(game_env):
    game_env.advance_round()
    assert game_env.region.counterfactual_temperature == game_env.region.temperature


def test_temperature_saved_is_positive_with_intervention_past_threshold(game_env):
    for _ in range(6):
        game_env.invest("preserve")
    for _ in range(15):
        game_env.advance_round()
    assert game_env.region.temperature_saved() > 0.0


def test_more_intervention_saves_more_temperature(game_env):
    light = game_env.module.RegionState()
    light.invest("preserve")
    for _ in range(15):
        light.advance_round()

    heavy = game_env.module.RegionState()
    for _ in range(6):
        heavy.invest("preserve")
    for _ in range(15):
        heavy.advance_round()

    assert heavy.temperature_saved() > light.temperature_saved()


def test_counterfactual_is_never_lower_than_actual(game_env):
    # The undampened trajectory can only ever warm as fast or faster than
    # the (possibly dampened) actual one.
    for _ in range(6):
        game_env.invest("preserve")
    for _ in range(20):
        game_env.advance_round()
    assert game_env.region.counterfactual_temperature >= game_env.region.temperature


def test_trajectory_message_when_no_difference_yet(game_env):
    message = game_env.region.trajectory_message()
    assert "No meaningful difference" in message


def test_trajectory_message_when_intervention_pays_off(game_env):
    for _ in range(6):
        game_env.invest("preserve")
    for _ in range(15):
        game_env.advance_round()
    message = game_env.region.trajectory_message()
    assert "lower" in message.lower()


def test_render_shows_trajectory_message(game_env):
    for _ in range(6):
        game_env.invest("preserve")
    for _ in range(15):
        game_env.advance_round()
    text = game_env.elements["trajectory-display"].innerText
    assert "lower" in text.lower()
