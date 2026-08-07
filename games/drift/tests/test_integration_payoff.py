"""Milestone 4: integration payoff loop — services capacity moves
arrived people from "pending" to "integrated" over time (the lag), and
integrated people contribute back to the regional economy every round
after that. This is the mechanical core of the hope angle: integration
is modeled as eventually net-positive, not a permanent drain.
"""

import pytest


def test_integrated_population_starts_at_zero(game_env):
    assert game_env.region.integrated_population == 0.0


def test_pending_population_zero_by_default(game_env):
    assert game_env.region.pending_population() == 0.0


def test_pending_population_reflects_unintegrated_arrivals(game_env):
    game_env.region.total_arrivals = 20.0
    game_env.region.integrated_population = 5.0
    assert game_env.region.pending_population() == pytest.approx(15.0)


def test_integration_zero_without_services_capacity(game_env):
    game_env.region.total_arrivals = 20.0
    assert game_env.region.integration_this_round() == 0.0


def test_integration_capped_by_services_throughput(game_env):
    game_env.region.invest("services")  # +8 capacity -> throughput 2.4
    game_env.region.total_arrivals = 50.0  # far more pending than throughput
    assert game_env.region.integration_this_round() == pytest.approx(2.4)


def test_integration_capped_by_pending_population(game_env):
    game_env.region.invest("services")  # throughput 2.4
    game_env.region.total_arrivals = 1.0  # fewer pending than throughput
    assert game_env.region.integration_this_round() == pytest.approx(1.0)


def test_integration_contribution_zero_when_nobody_integrated(game_env):
    assert game_env.region.integration_contribution() == 0.0


def test_integration_contribution_scales_with_integrated_population(game_env):
    game_env.region.integrated_population = 10.0
    assert game_env.region.integration_contribution() == pytest.approx(15.0)


def test_advance_round_moves_pending_into_integrated(game_env):
    game_env.region.invest("services")
    game_env.region.total_arrivals = 50.0
    game_env.advance_round()
    # 2.4 integrated this round, from throughput, before this round's new arrivals
    assert game_env.region.integrated_population == pytest.approx(2.4)


def test_integration_lag_takes_multiple_rounds(game_env):
    """The core timing/lag proof: a large pending population with modest
    services capacity can't be integrated in a single round."""
    game_env.region.invest("services")  # throughput 2.4/round
    game_env.region.total_arrivals = 50.0
    for _ in range(5):
        game_env.advance_round()
    integrated_after_5_rounds = game_env.region.integrated_population
    assert integrated_after_5_rounds < 50.0
    assert integrated_after_5_rounds == pytest.approx(2.4 * 5)


def test_integration_contribution_adds_to_income(game_env):
    game_env.region.invest("services")
    game_env.region.total_arrivals = 50.0
    game_env.advance_round()  # integrates 2.4 people, contributes 0 this round (integrated after)
    funds_before = game_env.region.funds
    game_env.advance_round()  # now 2.4 integrated people contribute 3.6 this round
    # strain at this point covers most of the base income; contribution
    # is additive on top regardless of strain
    contribution = 2.4 * 1.5
    assert game_env.region.funds >= funds_before + contribution - 1.0


def test_render_shows_integrated_display(game_env):
    game_env.module.render()
    assert "0" in game_env.elements["integrated-display"].innerText


def test_render_shows_pending_display(game_env):
    game_env.region.total_arrivals = 10.0
    game_env.module.render()
    assert "10" in game_env.elements["pending-display"].innerText
