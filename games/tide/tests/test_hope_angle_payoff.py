"""Milestone 5: hope-angle payoff — a direct before/after comparison
(actual damage vs. an undampened counterfactual) plus a flattening-curve
trend, both scaling with sustained adaptation investment.
"""

import pytest


def test_damage_saved_is_zero_with_no_adaptation(game_env):
    game_env.advance_season()
    assert game_env.state.damage_saved() == 0.0


def test_damage_saved_is_positive_with_adaptation(game_env):
    for _ in range(3):  # crosses the first tier threshold
        game_env.invest("adaptation")
    game_env.advance_season()
    assert game_env.state.damage_saved() > 0.0


def test_damage_saved_matches_the_dampened_amount(game_env):
    for _ in range(3):
        game_env.invest("adaptation")  # dampening = 0.3
    game_env.advance_season()
    assert game_env.state.damage_saved() == pytest.approx(5.0 * 0.3)


def test_damage_saved_accumulates_across_seasons(game_env):
    for _ in range(3):
        game_env.invest("adaptation")
    game_env.advance_season()
    game_env.advance_season()
    assert game_env.state.damage_saved() == pytest.approx(2 * 5.0 * 0.3)


def test_more_adaptation_saves_more_damage(game_env):
    game_env.invest("adaptation")
    game_env.advance_season()
    low_savings = game_env.state.damage_saved()

    for _ in range(4):
        game_env.invest("adaptation")
    game_env.advance_season()
    high_savings_delta = game_env.state.damage_saved() - low_savings
    assert high_savings_delta > 0


def test_damage_trend_is_none_with_too_few_seasons(game_env):
    game_env.advance_season()
    game_env.advance_season()
    assert game_env.state.damage_trend() is None


def test_damage_trend_shows_flattening_with_growing_adaptation(game_env):
    game_env.advance_season()  # no adaptation, full damage
    game_env.advance_season()  # no adaptation, full damage
    for _ in range(6):
        game_env.invest("adaptation")
    game_env.advance_season()  # heavily dampened
    game_env.advance_season()  # heavily dampened
    first_half, second_half = game_env.state.damage_trend()
    assert second_half < first_half


def test_damage_saved_message_when_none_saved(game_env):
    message = game_env.module.damage_saved_message(0.0)
    assert "No adaptation investment yet" in message


def test_damage_saved_message_when_positive(game_env):
    message = game_env.module.damage_saved_message(12.5)
    assert "13" in message or "12" in message
    assert "saved" in message.lower()


def test_damage_trend_message_insufficient_data(game_env):
    assert "Not enough seasons" in game_env.module.damage_trend_message(None)


def test_damage_trend_message_flattening_wording(game_env):
    message = game_env.module.damage_trend_message((5.0, 2.0))
    assert "flattening" in message.lower()


def test_damage_trend_message_steepening_wording(game_env):
    message = game_env.module.damage_trend_message((2.0, 5.0))
    assert "steepening" in message.lower()


def test_damage_trend_message_steady_wording(game_env):
    message = game_env.module.damage_trend_message((3.0, 3.0))
    assert "steady" in message.lower()


def test_render_shows_damage_saved_and_trend(game_env):
    game_env.invest("adaptation")
    game_env.advance_season()
    game_env.module.render()
    assert "saved" in game_env.elements["damage-saved-display"].innerText.lower() or \
        "No adaptation" in game_env.elements["damage-saved-display"].innerText
