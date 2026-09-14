"""C13: a lifetime funds breakdown (revenue vs. build/maintenance/
disruption spend), for transparency. Pure additive bookkeeping alongside
the existing cost/refund math -- these tests exist partly to guard
against reintroducing anything like the flat-refund exploit this game's
own CLAUDE.md documents having found and fixed once: retiring must never
show up as a "build spend" or otherwise inflate any bucket."""

import pytest

ALWAYS_TRIGGER = lambda: 0.0
NEVER_TRIGGER = lambda: 0.999999


def test_all_lifetime_totals_start_at_zero(game_env):
    state = game_env.state
    assert state.lifetime_revenue == 0.0
    assert state.lifetime_build_spend == 0.0
    assert state.lifetime_maintenance_spend == 0.0
    assert state.lifetime_disruption_spend == 0.0


def test_build_spend_tracks_actual_plant_cost(game_env):
    game_env.build("coal")  # 50
    game_env.build("coal")  # still 50 -- coal has no learning-curve decay
    assert game_env.state.lifetime_build_spend == 100.0


def test_a_failed_build_does_not_add_to_build_spend(game_env):
    game_env.state.funds = 0.0
    game_env.build("coal")
    assert game_env.state.lifetime_build_spend == 0.0


def test_retiring_does_not_add_to_build_spend(game_env):
    """Guards against reintroducing anything like the flat-refund exploit
    -- a refund is income, never a build-spend entry."""
    game_env.build("coal")
    game_env.retire("coal")
    assert game_env.state.lifetime_build_spend == 50.0  # only the original build


def test_maintenance_spend_tracks_actual_maintenance_cost(game_env):
    game_env.build("coal")  # maintenance cost = 50 * 0.25 = 12.5
    game_env.maintain("coal")
    assert game_env.state.lifetime_maintenance_spend == 12.5


def test_a_failed_maintain_does_not_add_to_maintenance_spend(game_env):
    # No coal built -- maintain_plant() returns False.
    game_env.maintain("coal")
    assert game_env.state.lifetime_maintenance_spend == 0.0


def test_revenue_accumulates_across_rounds(game_env):
    game_env.build("coal")  # 20 capacity
    game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    expected = 20 * game_env.module.REVENUE_PER_UNIT_MET
    assert game_env.state.lifetime_revenue == expected


def test_disruption_spend_tracks_revenue_lost_to_a_brownout(game_env):
    game_env.build("coal")
    game_env.state.emissions = 300.0  # severity 0.1
    game_env.state.advance_round(rng=ALWAYS_TRIGGER, age_rng=NEVER_TRIGGER)
    assert game_env.state.lifetime_disruption_spend == pytest.approx(
        game_env.state.last_event["revenue_loss"]
    )


def test_disruption_spend_also_tracks_aging_breakdown_repair_cost(game_env):
    module = game_env.module
    game_env.build("coal")
    for _ in range(module.AGE_GRACE_PERIOD + 20):
        game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=ALWAYS_TRIGGER)
        if game_env.state.last_aging_event is not None:
            break
    assert game_env.state.last_aging_event is not None
    assert game_env.state.lifetime_disruption_spend == game_env.state.last_aging_event["repair_cost"]


def test_render_updates_the_breakdown_display(game_env):
    game_env.build("coal")
    game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    game_env.module.render()
    assert game_env.elements["funds-breakdown-build"].innerText == "50"
    assert float(game_env.elements["funds-breakdown-revenue"].innerText) > 0


def test_lifetime_totals_round_trip_through_save_load(game_env):
    module = game_env.module
    game_env.build("coal")
    game_env.maintain("coal")
    game_env.state.advance_round(rng=NEVER_TRIGGER, age_rng=NEVER_TRIGGER)
    snapshot = module.get_state()

    game_env.build("gas")  # diverge
    module.load_state(snapshot)

    assert module.state.lifetime_build_spend == snapshot["lifetime_build_spend"]
    assert module.state.lifetime_maintenance_spend == snapshot["lifetime_maintenance_spend"]
    assert module.state.lifetime_revenue == snapshot["lifetime_revenue"]
