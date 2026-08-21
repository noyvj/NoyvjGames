"""Iteration Pass 3 (fun/teaching balance), from
`climate-games-fun-teaching-balance.md`. Risk: the tiered plant system
could drift toward a pure optimization spreadsheet where the emissions
meter reads as a side-score rather than the actual mechanism gating
disruption risk.

Milestone 3 already ties disruption probability/severity directly to the
emissions meter (see test_disruption_events.py) with a soft linear ramp
rather than a hard cliff — no separate difficulty setting exists. The gap
this pass closes is legibility: nothing previously stated in words that
rising emissions ARE what's driving disruption risk. These tests cover the
new disruption_risk_message() and its render wiring.
"""

import pytest


def test_disruption_risk_message_zero_at_zero_emissions(game_env):
    msg = game_env.module.disruption_risk_message(0.0, 0.0)
    assert "no disruption risk" in msg.lower()


def test_disruption_risk_message_states_percentage(game_env):
    msg = game_env.module.disruption_risk_message(0.3, 0.1)
    assert "30%" in msg


def test_disruption_risk_message_mentions_emissions(game_env):
    msg = game_env.module.disruption_risk_message(0.3, 0.1)
    assert "emissions" in msg.lower()


def test_disruption_risk_message_flags_damage_risk_above_threshold(game_env):
    threshold = game_env.module.DAMAGE_SEVERITY_THRESHOLD
    below = game_env.module.disruption_risk_message(0.5, threshold - 0.01)
    at_or_above = game_env.module.disruption_risk_message(0.5, threshold)
    assert "damage" not in below.lower()
    assert "damage" in at_or_above.lower()


def test_render_shows_no_risk_message_initially(game_env):
    game_env.module.render()
    text = game_env.elements["disruption-risk-display"].innerText
    assert "no disruption risk" in text.lower()


def test_render_shows_live_risk_percentage_as_emissions_rise(game_env):
    game_env.state.emissions = 1000.0  # 50% probability, per test_disruption_events.py
    game_env.module.render()
    text = game_env.elements["disruption-risk-display"].innerText
    assert "50%" in text


def test_render_risk_message_tracks_disruption_probability_method(game_env):
    game_env.state.emissions = 1500.0
    game_env.module.render()
    expected = game_env.module.disruption_risk_message(
        game_env.state.disruption_probability(), game_env.state.disruption_severity()
    )
    assert game_env.elements["disruption-risk-display"].innerText == expected
