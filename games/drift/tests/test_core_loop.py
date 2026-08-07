"""Milestone 1: core allocation loop — a receiving region invests its
budget across housing, integration services, and infrastructure
capacity, round by round. No displacement pressure yet: this is the
foundation those later milestones build on.
"""

import pytest


def test_initial_state(game_env):
    assert game_env.region.round_number == 1
    assert game_env.region.funds == 300.0
    for capacity_type in ("housing", "services", "infrastructure"):
        assert game_env.region.capacity[capacity_type] == 0.0


def test_total_capacity_zero_by_default(game_env):
    assert game_env.region.total_capacity() == 0.0


def test_invest_in_housing_adds_capacity(game_env):
    game_env.region.invest("housing")
    assert game_env.region.capacity["housing"] == 10.0


def test_invest_in_services_adds_capacity(game_env):
    game_env.region.invest("services")
    assert game_env.region.capacity["services"] == 8.0


def test_invest_in_infrastructure_adds_capacity(game_env):
    game_env.region.invest("infrastructure")
    assert game_env.region.capacity["infrastructure"] == 6.0


def test_invest_spends_funds(game_env):
    funds_before = game_env.region.funds
    game_env.region.invest("housing")
    assert game_env.region.funds == pytest.approx(funds_before - 20.0)


def test_invest_fails_when_insufficient_funds(game_env):
    game_env.region.funds = 5.0
    result = game_env.region.invest("infrastructure")
    assert result is False
    assert game_env.region.capacity["infrastructure"] == 0.0


def test_total_capacity_sums_all_types(game_env):
    game_env.region.invest("housing")
    game_env.region.invest("services")
    game_env.region.invest("infrastructure")
    assert game_env.region.total_capacity() == pytest.approx(10.0 + 8.0 + 6.0)


def test_advance_round_increments_round_number(game_env):
    game_env.advance_round()
    assert game_env.region.round_number == 2


def test_advance_round_adds_base_income(game_env):
    funds_before = game_env.region.funds
    game_env.advance_round()
    assert game_env.region.funds == pytest.approx(funds_before + 50.0)


def test_multiple_rounds_compound_income(game_env):
    game_env.advance_round()
    game_env.advance_round()
    game_env.advance_round()
    assert game_env.region.funds == pytest.approx(300.0 + 3 * 50.0)


def test_render_updates_status_displays(game_env):
    game_env.region.invest("housing")
    game_env.module.render()
    assert game_env.elements["round-display"].innerText == "Round 1"
    assert "280" in game_env.elements["funds-display"].innerText
    assert "10" in game_env.elements["total-capacity-display"].innerText


def test_render_updates_investment_counts(game_env):
    game_env.region.invest("services")
    game_env.region.invest("services")
    game_env.module.render()
    assert game_env.elements["services-count"].innerText == "16"


def test_invest_button_disabled_when_unaffordable(game_env):
    game_env.region.funds = 5.0
    game_env.module.render()
    assert game_env.elements["infrastructure-invest-button"].disabled is True
