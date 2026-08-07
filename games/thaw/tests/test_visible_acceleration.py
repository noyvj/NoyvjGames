"""Milestone 4: visible acceleration — surfacing the loop's steepening
slope clearly, with threshold-crossing detection, not just a bigger
raw number.
"""

import pytest


def test_melt_started_round_is_none_before_crossing(game_env):
    assert game_env.region.melt_started_round is None


def test_melt_started_round_recorded_on_crossing(game_env):
    for _ in range(10):
        game_env.advance_round()
    assert game_env.region.melt_started_round is not None


def test_melt_started_round_is_the_round_it_actually_crossed(game_env):
    game_env.region.temperature = 9.5
    game_env.region.round_number = 7
    game_env.advance_round()  # temperature becomes 10.5, crossing during round 7
    assert game_env.region.melt_started_round == 7


def test_melt_started_round_stays_fixed_after_first_crossing(game_env):
    for _ in range(10):
        game_env.advance_round()
    first_recorded = game_env.region.melt_started_round
    for _ in range(5):
        game_env.advance_round()
    assert game_env.region.melt_started_round == first_recorded


def test_acceleration_factor_is_one_below_threshold(game_env):
    assert game_env.region.acceleration_factor() == 1.0


def test_acceleration_factor_exceeds_one_past_threshold(game_env):
    game_env.region.temperature = 20.0
    assert game_env.region.acceleration_factor() > 1.0


def test_acceleration_message_steady_before_melting(game_env):
    assert "steady" in game_env.region.acceleration_message().lower()


def test_acceleration_message_shows_factor_and_round_after_melting(game_env):
    for _ in range(15):
        game_env.advance_round()
    message = game_env.region.acceleration_message()
    assert "accelerated" in message.lower()
    assert str(game_env.region.melt_started_round) in message


def test_render_shows_acceleration_message(game_env):
    for _ in range(15):
        game_env.advance_round()
    assert "accelerated" in game_env.elements["acceleration-display"].innerText.lower()


def test_render_shows_steady_message_before_melting(game_env):
    assert "steady" in game_env.elements["acceleration-display"].innerText.lower()


def test_acceleration_bar_grows_as_factor_increases(game_env):
    game_env.region.temperature = 5.0
    game_env.module.render()
    bar_before = game_env.elements["acceleration-bar"].style.width

    game_env.region.temperature = 30.0
    game_env.module.render()
    bar_after = game_env.elements["acceleration-bar"].style.width

    assert bar_before == "0%"
    assert bar_after != "0%"
