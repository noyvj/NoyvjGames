"""Milestone 3: intervention measures — preserve/monitor investment
dampens the feedback loop's acceleration, but never touches the
background temperature rise itself (that stays outside player control).
"""

import pytest


def test_no_dampening_with_no_investment(game_env):
    assert game_env.region.feedback_dampening_fraction() == 0.0


def test_preserve_investment_dampens_feedback(game_env):
    game_env.invest("preserve")
    assert game_env.region.feedback_dampening_fraction() == pytest.approx(0.08)


def test_monitor_investment_dampens_feedback_by_its_own_amount(game_env):
    game_env.invest("monitor")
    assert game_env.region.feedback_dampening_fraction() == pytest.approx(0.04)


def test_preserve_and_monitor_stack(game_env):
    game_env.invest("preserve")
    game_env.invest("monitor")
    assert game_env.region.feedback_dampening_fraction() == pytest.approx(0.12)


def test_dampening_caps_at_maximum(game_env):
    for _ in range(20):
        game_env.region.funds = 1000
        game_env.invest("preserve")
    assert game_env.region.feedback_dampening_fraction() == 0.85


def test_dampening_reduces_feedback_bonus_past_threshold(game_env):
    game_env.region.temperature = 12.0  # 2 degrees over threshold
    undampened_bonus = 2.0 * 0.15  # FEEDBACK_RATE_PER_DEGREE_OVER

    game_env.invest("preserve")  # 8% dampening
    dampened_bonus = game_env.region.feedback_bonus()

    assert dampened_bonus < undampened_bonus
    assert dampened_bonus == pytest.approx(undampened_bonus * 0.92)


def test_background_rise_is_never_dampened(game_env):
    # The base rate is fixed background trajectory — no amount of
    # investment should touch it, only the feedback contribution.
    for _ in range(10):
        game_env.region.funds = 1000
        game_env.invest("preserve")
    game_env.region.temperature = 5.0  # below threshold, no feedback active
    assert game_env.region.current_rise_rate() == 1.0  # exactly BASE_TEMP_RISE_PER_ROUND


def test_heavy_investment_slows_but_does_not_stop_acceleration(game_env):
    # Even maxed-out dampening still lets some feedback through — the
    # hope angle is "slows the loop," not "stops the background trajectory."
    for _ in range(20):
        game_env.region.funds = 1000
        game_env.invest("preserve")
    game_env.region.temperature = 20.0
    assert game_env.region.current_rise_rate() > 1.0  # still above baseline
    assert game_env.region.feedback_bonus() > 0.0  # feedback isn't fully eliminated


def test_intervention_produces_a_measurably_flatter_trajectory(game_env):
    # End-to-end sanity check: heavy early preserve investment should
    # leave temperature measurably lower after the same number of rounds.
    intervened = game_env.module.RegionState()
    for _ in range(10):
        intervened.invest("preserve")
    for _ in range(20):
        intervened.advance_round()

    unintervened = game_env.module.RegionState()
    for _ in range(20):
        unintervened.advance_round()

    assert intervened.temperature < unintervened.temperature


def test_render_shows_dampening_percentage(game_env):
    game_env.invest("preserve")
    assert "8%" in game_env.elements["dampening-display"].innerText
