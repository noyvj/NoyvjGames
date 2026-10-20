"""Tests for advisors.metric_value()."""

import advisors


def test_metric_value_returns_food_as_float(game_env):
    state = game_env.module.state
    result = advisors.metric_value(state, "food", None)
    assert isinstance(result, float)
    assert result == float(state.resources["food"])


def test_metric_value_returns_headroom_correctly(game_env):
    state = game_env.module.state
    effects = {}
    expected = float(state.housing_capacity(effects) - state.population)
    result = advisors.metric_value(state, "headroom", effects)
    assert result == expected


def test_metric_value_returns_zero_for_unknown_key(game_env):
    state = game_env.module.state
    result = advisors.metric_value(state, "unknown_key", None)
    assert result == 0.0
