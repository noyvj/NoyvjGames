"""Iteration Pass 2: global comparison (a hardcoded real-world-fossil-mix
benchmark plotted alongside the player's own emissions) and infrastructure
age/vulnerability (plants age each round; past a grace period, older
fleets risk a costly breakdown unless maintained)."""

import pytest

ALWAYS_TRIGGER = lambda: 0.0
NEVER_TRIGGER = lambda: 0.999999


def test_plant_age_starts_at_zero(game_env):
    for plant_type in game_env.module.PLANT_TYPES:
        assert game_env.state.plant_age[plant_type] == 0.0


def test_plant_ages_each_round_it_stands(game_env):
    game_env.build("coal")
    game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    assert game_env.state.plant_age["coal"] == 1.0


def test_plant_type_with_no_units_does_not_age(game_env):
    game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    assert game_env.state.plant_age["coal"] == 0.0


def test_building_a_second_unit_dilutes_average_age(game_env):
    game_env.build("coal")
    for _ in range(4):
        game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    assert game_env.state.plant_age["coal"] == 4.0
    game_env.build("coal")  # second unit, age 0, dilutes the average
    assert game_env.state.plant_age["coal"] == 2.0


def test_aging_breakdown_probability_zero_within_grace_period(game_env):
    game_env.build("coal")
    for _ in range(game_env.module.AGE_GRACE_PERIOD):
        game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    assert game_env.state.aging_breakdown_probability() == 0.0


def test_aging_breakdown_probability_rises_past_grace_period(game_env):
    game_env.build("coal")
    for _ in range(game_env.module.AGE_GRACE_PERIOD + 5):
        game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    assert game_env.state.aging_breakdown_probability() > 0.0


def test_aging_breakdown_removes_a_unit_and_charges_repair_cost(game_env):
    game_env.build("coal")
    for _ in range(game_env.module.AGE_GRACE_PERIOD + 10):
        game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=ALWAYS_TRIGGER)
    assert game_env.state.plant_counts["coal"] == 0
    assert game_env.state.last_aging_event["plant"] == "coal"
    assert game_env.state.last_aging_event["repair_cost"] == pytest.approx(
        game_env.module.PLANT_BASE_COST["coal"] * game_env.module.AGING_BREAKDOWN_COST_FRACTION
    )


def test_oldest_vulnerable_plant_picks_highest_age(game_env):
    game_env.build("coal")
    for _ in range(5):
        game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    game_env.build("gas")  # younger
    assert game_env.state.oldest_vulnerable_plant() == "coal"


def test_maintain_plant_reduces_age_and_costs_funds(game_env):
    game_env.build("coal")
    for _ in range(10):
        game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    age_before = game_env.state.plant_age["coal"]
    funds_before = game_env.state.funds
    result = game_env.state.maintain_plant("coal")
    assert result is True
    assert game_env.state.plant_age["coal"] == max(0.0, age_before - game_env.module.MAINTENANCE_AGE_REDUCTION)
    assert game_env.state.funds < funds_before


def test_maintain_plant_fails_with_no_units(game_env):
    assert game_env.state.maintain_plant("coal") is False


def test_maintain_plant_fails_without_funds(game_env):
    game_env.build("coal")
    game_env.state.funds = 0
    assert game_env.state.maintain_plant("coal") is False


def test_maintain_button_click_dispatches_to_state(game_env):
    game_env.build("coal")
    game_env.module.render()
    game_env.maintain("coal")
    assert game_env.state.plant_age["coal"] == 0.0  # nothing to reduce yet, but no crash


def test_wear_class_escalates_with_age(game_env):
    game_env.build("coal")
    assert game_env.state.wear_class("coal") == ""
    for _ in range(8):
        game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    assert game_env.state.wear_class("coal") == "wear-1"
    for _ in range(8):
        game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    assert game_env.state.wear_class("coal") == "wear-2"


def test_render_applies_wear_css_class(game_env):
    game_env.build("coal")
    for _ in range(8):
        game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    game_env.module.render()
    assert "wear-1" in game_env.elements["coal-name"].classList


def test_global_reference_emissions_accumulates(game_env):
    game_env.build("coal")
    game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    assert game_env.state.global_reference_emissions > 0.0


def test_trend_graph_includes_global_reference_line(game_env):
    game_env.build("coal")
    game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    game_env.module.render()
    svg = game_env.elements["trend-graph"].innerHTML
    assert "trend-line--global" in svg


def test_global_comparison_message_reflects_ahead_of_curve(game_env):
    msg = game_env.module.global_comparison_message(10, 100)
    assert "ahead" in msg


def test_global_comparison_message_reflects_behind_curve(game_env):
    msg = game_env.module.global_comparison_message(100, 10)
    assert "behind" in msg
