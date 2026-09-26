"""C3: the optional regional grid -- a lighter multi-grid mode than a
fully independent second grid, sharing this grid's own spare capacity
instead of managing a second set of plants (same "shares a resource, has
its own separate exposure" shape as Tide's D3 sister settlement)."""

import pytest


def _connect(game_env):
    game_env.elements["regional-grid-connect-button"].dispatch("click", None)


def test_off_by_default_and_button_visible(game_env):
    m = game_env.module
    m.render()
    assert m.state.regional_grid_connected is False
    assert game_env.elements["regional-grid-connect-button"].hidden is False
    assert game_env.elements["regional-grid-connect-button"].disabled is False
    assert game_env.elements["regional-grid-display"].hidden is True
    assert m.state.regional_grid_readout_text() == ""


def test_connecting_swaps_button_for_the_readout_and_is_permanent(game_env):
    m = game_env.module
    _connect(game_env)
    assert m.state.regional_grid_connected is True
    button = game_env.elements["regional-grid-connect-button"]
    assert button.disabled is True
    assert "connected" in button.innerText.lower()
    assert game_env.elements["regional-grid-display"].hidden is False
    assert "Regional grid" in game_env.elements["regional-grid-display"].innerText
    # A second click (or a direct second call) is a harmless no-op.
    _connect(game_env)
    assert m.state.regional_grid_connected is True


def test_no_effect_on_funds_while_off(game_env):
    m = game_env.module
    plain = m.GridState()
    twin = m.GridState()
    plain.plant_counts["nuclear"] = 2
    twin.plant_counts["nuclear"] = 2
    plain.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    twin.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    assert twin.funds == pytest.approx(plain.funds)
    assert twin.regional_grid_total_shared == 0.0
    assert twin.regional_grid_total_shortfall_cost == 0.0
    assert twin.regional_grid_total_revenue == 0.0


def test_ample_surplus_fully_covers_regional_demand(game_env):
    m = game_env.module
    state = m.GridState()
    state.plant_counts["nuclear"] = 3  # 300 capacity vs. 100 starting demand
    state.connect_regional_grid()
    demand_before = state.demand
    funds_before = state.funds
    state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)

    expected_regional_demand = demand_before * m.REGIONAL_DEMAND_FRACTION
    expected_revenue = expected_regional_demand * m.REGIONAL_REVENUE_PER_UNIT_SHARED
    assert state.regional_grid_total_shared == pytest.approx(expected_regional_demand)
    assert state.regional_grid_total_shortfall_cost == 0.0
    assert state.regional_grid_total_revenue == pytest.approx(expected_revenue)
    # Funds went up by at least the regional revenue (plus ordinary sales revenue).
    assert state.funds > funds_before


def test_no_surplus_means_a_pure_shortfall_cost(game_env):
    m = game_env.module
    state = m.GridState()  # zero plants -- zero capacity, all shortfall
    state.connect_regional_grid()
    demand_before = state.demand
    state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)

    expected_regional_demand = demand_before * m.REGIONAL_DEMAND_FRACTION
    expected_cost = expected_regional_demand * m.REGIONAL_SHORTFALL_COST_PER_UNIT
    assert state.regional_grid_total_shared == 0.0
    assert state.regional_grid_total_revenue == 0.0
    assert state.regional_grid_total_shortfall_cost == pytest.approx(expected_cost)


def test_never_double_counts_surplus_already_claimed_by_arbitrage(game_env):
    m = game_env.module
    state = m.GridState()
    state.plant_counts["solar"] = 5  # 50 capacity
    state.plant_counts["battery"] = 2  # storage/charge rate
    state.demand = 20  # well below capacity -- real surplus to fight over
    state.set_arbitrage_mode("charge")
    state.connect_regional_grid()

    raw_surplus = max(0.0, state.effective_capacity_for_revenue() - state.demand)
    state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)

    claimed_by_arbitrage = state.last_arbitrage["units"] if state.last_arbitrage else 0.0
    assert claimed_by_arbitrage > 0  # the scenario actually exercises the overlap
    available_for_regional = max(0.0, raw_surplus - claimed_by_arbitrage)
    expected_shared = min(available_for_regional, 20 * m.REGIONAL_DEMAND_FRACTION)
    assert state.regional_grid_total_shared == pytest.approx(expected_shared)
    # The two systems' combined claim never exceeds the real surplus that existed.
    assert claimed_by_arbitrage + state.regional_grid_total_shared <= raw_surplus + 1e-9


def test_save_load_round_trip(game_env):
    m = game_env.module
    state = m.GridState()
    state.plant_counts["nuclear"] = 3
    state.connect_regional_grid()
    state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    shared_before = state.regional_grid_total_shared
    revenue_before = state.regional_grid_total_revenue

    m.state = state
    data = m.get_state()
    assert data["regional_grid"]["total_shared"] == pytest.approx(shared_before)

    fresh = m.GridState()
    m.state = fresh
    m.load_state(data)
    assert fresh.regional_grid_connected is True
    assert fresh.regional_grid_total_shared == pytest.approx(shared_before)
    assert fresh.regional_grid_total_revenue == pytest.approx(revenue_before)


def test_get_state_omits_the_key_when_never_connected(game_env):
    m = game_env.module
    state = m.GridState()
    state.advance_round(rng=lambda: 1.0, age_rng=lambda: 1.0)
    m.state = state
    data = m.get_state()
    assert "regional_grid" not in data


def test_a_save_missing_the_key_leaves_it_unconnected(game_env):
    m = game_env.module
    state = m.GridState()
    m.state = state
    m.load_state(m.get_state())
    assert state.regional_grid_connected is False


def test_malformed_payload_falls_back_to_safe_defaults(game_env):
    m = game_env.module
    state = m.GridState()
    m.state = state
    m.load_state({"regional_grid": {
        "total_shared": "not a number",
        "total_shortfall_cost": float("nan"),
        "total_revenue": float("-inf"),
    }})
    # Presence of the dict at all still means "was connected".
    assert state.regional_grid_connected is True
    assert state.regional_grid_total_shared == 0.0
    assert state.regional_grid_total_shortfall_cost == 0.0
    assert state.regional_grid_total_revenue == 0.0
