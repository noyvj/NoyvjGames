"""Milestone 1: core state loop — demand growth, funds, plant build/retire,
round progression. No emissions or cost curve yet (Milestone 2)."""


def test_initial_state(game_env):
    assert game_env.state.round_number == 1
    assert game_env.state.demand == 100
    assert game_env.state.funds == 500
    assert all(count == 0 for count in game_env.state.plant_counts.values())


def test_build_plant_deducts_cost_and_increments_count(game_env):
    game_env.build("coal")
    assert game_env.state.plant_counts["coal"] == 1
    assert game_env.state.funds == 500 - 50


def test_build_plant_fails_when_insufficient_funds(game_env):
    game_env.state.funds = 10
    game_env.build("nuclear")  # costs 200
    assert game_env.state.plant_counts["nuclear"] == 0
    assert game_env.state.funds == 10


def test_build_button_disabled_when_cost_exceeds_funds(game_env):
    game_env.state.funds = 10
    game_env.module.render()
    assert game_env.elements["nuclear-build-button"].disabled is True
    assert game_env.elements["coal-build-button"].disabled is True  # costs 50 > 10


def test_build_button_enabled_when_affordable(game_env):
    assert game_env.elements["coal-build-button"].disabled is False


def test_retire_plant_decrements_count_and_refunds_half_cost(game_env):
    game_env.build("gas")  # cost 40, funds now 460
    game_env.retire("gas")
    assert game_env.state.plant_counts["gas"] == 0
    assert game_env.state.funds == 460 + 20  # 50% refund of base cost 40


def test_retire_plant_is_a_noop_when_count_is_zero(game_env):
    funds_before = game_env.state.funds
    game_env.retire("hydro")
    assert game_env.state.plant_counts["hydro"] == 0
    assert game_env.state.funds == funds_before


def test_retire_button_disabled_when_count_is_zero(game_env):
    assert game_env.elements["coal-retire-button"].disabled is True


def test_retire_button_enabled_after_building(game_env):
    game_env.build("wind")
    assert game_env.elements["wind-retire-button"].disabled is False


def test_total_capacity_sums_across_plant_types(game_env):
    game_env.build("coal")  # 20
    game_env.build("solar")  # 10
    assert game_env.state.total_capacity() == 30


def test_advance_round_increments_round_number(game_env):
    game_env.advance_round()
    assert game_env.state.round_number == 2


def test_advance_round_grows_demand_by_fixed_amount(game_env):
    game_env.advance_round()
    assert game_env.state.demand == 110


def test_advance_round_grants_revenue_capped_by_demand(game_env):
    # Two nuclear plants (200 capacity each) comfortably exceed the
    # starting demand of 100 — revenue should be capped at demand, not
    # scale with the surplus capacity.
    game_env.build("nuclear")
    game_env.build("nuclear")
    assert game_env.state.total_capacity() == 200
    funds_before = game_env.state.funds
    game_env.advance_round()
    assert game_env.state.funds == funds_before + 100 * 2  # capped at demand (100), not capacity (200)


def test_advance_round_revenue_reflects_unmet_demand(game_env):
    game_env.build("coal")  # 20 capacity, demand is 100
    funds_before = game_env.state.funds
    game_env.advance_round()
    assert game_env.state.funds == funds_before + 20 * 2  # only capacity counts, not full demand


def test_multiple_rounds_compound_demand_growth(game_env):
    game_env.advance_round()
    game_env.advance_round()
    game_env.advance_round()
    assert game_env.state.demand == 100 + 3 * 10
    assert game_env.state.round_number == 4


def test_render_updates_status_displays(game_env):
    game_env.build("coal")
    game_env.advance_round()
    assert game_env.elements["round-display"].innerText == "Round 2"
    assert "110" in game_env.elements["demand-display"].innerText
    assert "Capacity: 20" == game_env.elements["capacity-display"].innerText


def test_render_shows_plant_counts(game_env):
    game_env.build("hydro")
    game_env.build("hydro")
    assert game_env.elements["hydro-count"].innerText == "2"
