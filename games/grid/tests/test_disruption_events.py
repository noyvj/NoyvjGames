"""Milestone 3: disruption events — probability and severity both scale
with emissions, but there's no hard fail-state; a bad round only shrinks
this round's revenue gain; it never bankrupts existing funds.
"""

import pytest

ALWAYS_TRIGGER = lambda: 0.0
NEVER_TRIGGER = lambda: 0.999999


def test_disruption_probability_is_zero_with_no_emissions(game_env):
    assert game_env.state.disruption_probability() == 0.0


def test_disruption_probability_increases_with_emissions(game_env):
    game_env.state.emissions = 1000.0
    assert game_env.state.disruption_probability() == pytest.approx(0.5)


def test_disruption_probability_caps_at_maximum(game_env):
    game_env.state.emissions = 999999.0
    assert game_env.state.disruption_probability() == 0.9


def test_no_event_when_rng_roll_is_too_high(game_env):
    game_env.state.emissions = 1000.0
    game_env.state.advance_round(rng=NEVER_TRIGGER)
    assert game_env.state.last_event is None


def test_no_event_possible_with_zero_probability(game_env):
    # Even a "very likely to trigger" rng can't beat a true zero probability.
    game_env.state.advance_round(rng=ALWAYS_TRIGGER)
    assert game_env.state.last_event is None


def test_event_triggers_when_rng_roll_beats_probability(game_env):
    game_env.state.emissions = 1000.0  # 50% probability
    game_env.state.advance_round(rng=ALWAYS_TRIGGER)
    assert game_env.state.last_event is not None


def test_disruption_severity_scales_with_emissions(game_env):
    game_env.state.emissions = 1500.0
    assert game_env.state.disruption_severity() == 0.5


def test_disruption_severity_caps_at_one(game_env):
    game_env.state.emissions = 999999.0
    assert game_env.state.disruption_severity() == 1.0


def test_low_severity_event_is_a_brownout_not_damage(game_env):
    game_env.build("coal")
    game_env.state.emissions = 300.0  # severity 0.1 — below damage threshold (0.5)
    game_env.state.advance_round(rng=ALWAYS_TRIGGER)
    assert game_env.state.last_event["type"] == "brownout"
    assert game_env.state.plant_counts["coal"] == 1  # untouched


def test_high_severity_event_damages_a_fossil_plant(game_env):
    game_env.build("coal")
    game_env.state.emissions = 2000.0  # severity 0.67 — above damage threshold
    game_env.state.advance_round(rng=ALWAYS_TRIGGER)
    assert game_env.state.last_event["type"] == "damage"
    assert game_env.state.plant_counts["coal"] == 0


def test_damage_never_targets_renewables_or_nuclear(game_env):
    game_env.build("solar")
    game_env.build("nuclear")
    game_env.state.emissions = 2000.0
    game_env.state.advance_round(rng=ALWAYS_TRIGGER)
    assert game_env.state.last_event["type"] == "brownout"  # no fossil plant to damage
    assert game_env.state.plant_counts["solar"] == 1
    assert game_env.state.plant_counts["nuclear"] == 1


def test_high_severity_with_no_fossil_plants_falls_back_to_brownout(game_env):
    game_env.build("wind")
    game_env.state.emissions = 2000.0
    game_env.state.advance_round(rng=ALWAYS_TRIGGER)
    assert game_env.state.last_event["type"] == "brownout"


def test_brownout_reduces_this_rounds_revenue(game_env):
    game_env.build("coal")  # 20 capacity, well under demand of 100
    game_env.state.emissions = 300.0  # severity 0.1
    funds_before = game_env.state.funds
    game_env.state.advance_round(rng=ALWAYS_TRIGGER)
    full_revenue = 20 * 2  # met_demand(20) * REVENUE_PER_UNIT_MET(2)
    expected_loss = full_revenue * 0.1 * 0.8  # severity * MAX_REVENUE_LOSS_FRACTION
    assert game_env.state.funds == pytest.approx(funds_before + full_revenue - expected_loss)


def test_event_never_reduces_funds_below_their_pre_round_value(game_env):
    # Worst case: severity 1.0 wipes out this round's entire revenue gain,
    # but existing funds are never touched — no hard fail-state.
    game_env.build("coal")
    game_env.state.emissions = 999999.0
    funds_before = game_env.state.funds
    game_env.state.advance_round(rng=ALWAYS_TRIGGER)
    assert game_env.state.funds >= funds_before


def test_event_log_accumulates_across_rounds(game_env):
    game_env.build("coal")
    game_env.state.emissions = 300.0
    game_env.state.advance_round(rng=ALWAYS_TRIGGER)
    game_env.state.advance_round(rng=ALWAYS_TRIGGER)
    assert len(game_env.state.event_log) == 2


def test_no_event_does_not_get_logged(game_env):
    game_env.state.advance_round(rng=ALWAYS_TRIGGER)  # zero emissions, zero probability
    assert game_env.state.event_log == []


def test_render_shows_no_disruption_message_initially(game_env):
    assert "No disruptions" in game_env.elements["event-display"].innerText


def test_render_shows_damage_event_message(game_env):
    game_env.build("coal")
    game_env.state.emissions = 2000.0
    game_env.state.advance_round(rng=ALWAYS_TRIGGER)
    game_env.module.render()
    text = game_env.elements["event-display"].innerText
    assert "Damage" in text
    assert "Coal" in text
