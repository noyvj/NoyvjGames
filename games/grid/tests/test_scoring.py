"""Milestone 4: scoring that rewards sustained clean transition over the
whole run, not just a final snapshot — the hope-angle payoff.
"""

import pytest

NEVER_TRIGGER = lambda: 0.999999


def test_score_is_zero_before_any_round_is_played(game_env):
    assert game_env.state.score() == 0.0
    assert game_env.state.average_clean_fraction() == 0.0


def test_score_is_full_marks_after_an_all_clean_round(game_env):
    game_env.build("solar")
    game_env.state.advance_round(rng=NEVER_TRIGGER)
    assert game_env.state.score() == 100.0


def test_score_is_zero_after_an_all_fossil_round(game_env):
    game_env.build("coal")
    game_env.state.advance_round(rng=NEVER_TRIGGER)
    assert game_env.state.score() == 0.0


def test_score_averages_across_mixed_rounds(game_env):
    game_env.build("coal")  # round 1: 100% fossil -> clean fraction 0.0
    game_env.state.advance_round(rng=NEVER_TRIGGER)
    game_env.build("solar")  # now mixed; round 2 composition determines clean fraction
    game_env.state.advance_round(rng=NEVER_TRIGGER)
    assert 0.0 < game_env.state.score() < 100.0


def test_score_rewards_sustained_cleanliness_not_just_the_final_round(game_env):
    # Two dirty rounds, then one clean round — a late clean sprint can't
    # erase the dirty average, unlike a final-snapshot-only score would.
    game_env.build("coal")
    game_env.state.advance_round(rng=NEVER_TRIGGER)
    game_env.state.advance_round(rng=NEVER_TRIGGER)
    game_env.retire("coal")
    game_env.build("solar")
    game_env.state.advance_round(rng=NEVER_TRIGGER)
    # Final round is 100% clean, but the running average is only 1/3 clean.
    assert game_env.state.score() == pytest.approx(100 / 3)


def test_clean_trend_is_none_with_too_few_rounds(game_env):
    game_env.state.advance_round(rng=NEVER_TRIGGER)
    game_env.state.advance_round(rng=NEVER_TRIGGER)
    assert game_env.state.clean_trend() is None


def test_clean_trend_shows_improvement(game_env):
    game_env.build("coal")
    game_env.state.advance_round(rng=NEVER_TRIGGER)  # dirty
    game_env.state.advance_round(rng=NEVER_TRIGGER)  # dirty
    game_env.retire("coal")
    game_env.build("solar")
    game_env.state.advance_round(rng=NEVER_TRIGGER)  # clean
    game_env.state.advance_round(rng=NEVER_TRIGGER)  # clean
    first_half, second_half = game_env.state.clean_trend()
    assert second_half > first_half


def test_clean_trend_shows_decline(game_env):
    game_env.build("solar")
    game_env.state.advance_round(rng=NEVER_TRIGGER)  # clean
    game_env.state.advance_round(rng=NEVER_TRIGGER)  # clean
    game_env.retire("solar")
    game_env.build("coal")
    game_env.state.advance_round(rng=NEVER_TRIGGER)  # dirty
    game_env.state.advance_round(rng=NEVER_TRIGGER)  # dirty
    first_half, second_half = game_env.state.clean_trend()
    assert second_half < first_half


def test_clean_trend_message_insufficient_data(game_env):
    assert "Not enough rounds" in game_env.module.clean_trend_message(None)


def test_clean_trend_message_improving_wording(game_env):
    message = game_env.module.clean_trend_message((0.2, 0.8))
    assert "cleaner" in message.lower()
    assert "20%" in message
    assert "80%" in message


def test_clean_trend_message_worsening_wording(game_env):
    message = game_env.module.clean_trend_message((0.8, 0.2))
    assert "dirtier" in message.lower()


def test_clean_trend_message_steady_wording(game_env):
    message = game_env.module.clean_trend_message((0.5, 0.5))
    assert "steady" in message.lower()


def test_render_shows_score(game_env):
    game_env.build("solar")
    game_env.state.advance_round(rng=NEVER_TRIGGER)
    game_env.module.render()
    assert "100" in game_env.elements["score-display"].innerText


def test_render_shows_trend_message(game_env):
    game_env.module.render()
    assert "Not enough rounds" in game_env.elements["trend-display"].innerText
