"""Milestone 2: permafrost melt + methane feedback — the core lesson of
the game. Once temperature crosses the melt threshold, each round's rise
gets bigger than the last, a genuine accelerating feedback loop.
"""

import pytest


def test_not_melting_below_threshold(game_env):
    assert game_env.region.is_melting() is False


def test_melting_at_or_above_threshold(game_env):
    game_env.region.temperature = 10.0
    assert game_env.region.is_melting() is True


def test_feedback_bonus_is_zero_below_threshold(game_env):
    game_env.region.temperature = 5.0
    assert game_env.region.feedback_bonus() == 0.0


def test_feedback_bonus_grows_past_threshold(game_env):
    game_env.region.temperature = 12.0  # 2 degrees over
    assert game_env.region.feedback_bonus() == pytest.approx(0.3)  # 2 * 0.15


def test_rise_rate_equals_base_below_threshold(game_env):
    game_env.region.temperature = 5.0
    assert game_env.region.current_rise_rate() == 1.0


def test_rise_rate_exceeds_base_past_threshold(game_env):
    game_env.region.temperature = 12.0
    assert game_env.region.current_rise_rate() == pytest.approx(1.3)


def test_each_round_rises_faster_once_melting_starts(game_env):
    game_env.region.temperature = 9.5  # one round from crossing threshold
    game_env.advance_round()
    first_rise = game_env.region.temperature - 9.5
    temp_before_second = game_env.region.temperature
    game_env.advance_round()
    second_rise = game_env.region.temperature - temp_before_second
    assert second_rise > first_rise  # visibly accelerating, not linear


def test_rise_stays_linear_while_below_threshold(game_env):
    game_env.advance_round()
    first_rise = game_env.region.temperature
    temp_before = game_env.region.temperature
    game_env.advance_round()
    second_rise = game_env.region.temperature - temp_before
    assert second_rise == pytest.approx(first_rise)  # both exactly 1.0, no acceleration yet


def test_render_shows_rise_rate_and_melt_status(game_env):
    game_env.region.temperature = 12.0
    game_env.module.render()
    assert "1.30" in game_env.elements["rise-rate-display"].innerText
    assert "actively melting" in game_env.elements["melt-status-display"].innerText


def test_render_shows_stable_status_before_threshold(game_env):
    assert "stable" in game_env.elements["melt-status-display"].innerText
