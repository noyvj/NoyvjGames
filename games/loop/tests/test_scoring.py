"""Milestone 5: scoring + hope-angle payoff — funds plus a direct
lifetime-circular-share bonus, and a trend comparison showing the
chain closing (or reopening) over the course of a session.

test_circularity_beats_pure_extraction is the key hope-angle proof:
investing in circularity early should outperform pure extraction on
raw funds alone within a normal session length, not just on score.
"""

import pytest


def _play_pure_extraction(game_env, cycles):
    for _ in range(cycles):
        game_env.chain.advance_cycle()


def _play_circularity_first(game_env, cycles, recycle_units=10):
    game_env.chain.funds = 1000.0
    for _ in range(recycle_units):
        game_env.chain.invest_circularity("recycle")
    for _ in range(cycles):
        game_env.chain.advance_cycle()


def test_score_starts_at_starting_funds(game_env):
    assert game_env.chain.score() == pytest.approx(300.0)


def test_score_includes_circularity_bonus(game_env):
    game_env.chain.funds = 1000.0
    for _ in range(10):
        game_env.chain.invest_circularity("recycle")
    game_env.chain.advance_cycle()
    # fully closed this cycle -> lifetime circular fraction == 1.0
    assert game_env.chain.lifetime_circular_fraction() == 1.0
    expected_funds = game_env.chain.funds
    assert game_env.chain.score() == pytest.approx(expected_funds + 300.0)


def test_score_with_zero_circularity_equals_funds(game_env):
    game_env.chain.advance_cycle()
    assert game_env.chain.score() == pytest.approx(game_env.chain.funds)


def test_circular_trend_none_before_enough_cycles(game_env):
    game_env.chain.advance_cycle()
    assert game_env.chain.circular_trend() is None


def test_circular_trend_shows_improvement(game_env):
    game_env.chain.advance_cycle()
    game_env.chain.advance_cycle()  # first half: 0% circular
    game_env.chain.funds = 1000.0
    for _ in range(10):
        game_env.chain.invest_circularity("recycle")
    game_env.chain.advance_cycle()
    game_env.chain.advance_cycle()  # second half: 100% circular
    trend = game_env.chain.circular_trend()
    assert trend is not None
    first_half, second_half = trend
    assert second_half > first_half


def test_circularity_beats_pure_extraction(game_env):
    """The core hope-angle claim: closing the loop early isn't just
    cleaner, it's more profitable, because it dodges the compounding
    environmental-damage cost entirely."""
    _play_pure_extraction(game_env, cycles=15)
    pure_extraction_funds = game_env.chain.funds

    # fresh state for the comparison run
    game_env.module.chain.__init__()
    _play_circularity_first(game_env, cycles=15)
    circularity_first_funds = game_env.chain.funds

    assert circularity_first_funds > pure_extraction_funds


def test_render_shows_score_display(game_env):
    game_env.module.render()
    assert "Score" in game_env.elements["score-display"].innerText


def test_render_shows_trend_message(game_env):
    game_env.module.render()
    assert game_env.elements["trend-display"].innerText == "Not enough cycles yet to show a trend."
