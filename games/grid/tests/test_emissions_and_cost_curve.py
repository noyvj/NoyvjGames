"""Milestone 2: emissions meter (tied to fossil-heavy grid composition)
and the renewable learning-curve cost decay.
"""

import pytest


def test_emissions_start_at_zero(game_env):
    assert game_env.state.emissions == 0.0


def test_renewables_only_produce_no_emissions(game_env):
    game_env.build("solar")
    game_env.build("wind")
    game_env.build("hydro")
    game_env.advance_round()
    assert game_env.state.emissions == 0.0


def test_building_coal_and_advancing_increases_emissions(game_env):
    game_env.build("coal")  # 20 capacity * 3.0 factor = 60
    game_env.advance_round()
    assert game_env.state.emissions == 60.0


def test_gas_emissions_factor_is_lower_than_coal(game_env):
    game_env.build("gas")  # 15 capacity * 1.5 = 22.5
    game_env.advance_round()
    assert game_env.state.emissions == 22.5


def test_nuclear_produces_no_emissions(game_env):
    game_env.build("nuclear")
    game_env.advance_round()
    assert game_env.state.emissions == 0.0


def test_emissions_accumulate_every_round_the_plant_stands(game_env):
    game_env.build("coal")
    game_env.advance_round()
    game_env.advance_round()
    assert game_env.state.emissions == 60.0 * 2


def test_retiring_a_fossil_plant_stops_further_emissions(game_env):
    game_env.build("coal")
    game_env.advance_round()
    game_env.retire("coal")
    game_env.advance_round()
    assert game_env.state.emissions == 60.0  # only the first round counted


def test_fossil_share_is_zero_with_no_plants(game_env):
    assert game_env.state.fossil_share() == 0.0


def test_fossil_share_is_one_with_only_fossil_plants(game_env):
    game_env.build("coal")
    assert game_env.state.fossil_share() == 1.0


def test_fossil_share_reflects_mixed_grid(game_env):
    game_env.build("coal")  # 20 capacity, fossil
    game_env.build("solar")  # 10 capacity, clean
    assert game_env.state.fossil_share() == pytest.approx(20 / 30)


def test_renewable_cost_starts_at_base_cost(game_env):
    assert game_env.state.plant_cost("solar") == 80


def test_renewable_cost_decreases_after_building(game_env):
    game_env.build("solar")
    assert game_env.state.plant_cost("solar") == pytest.approx(80 * 0.95)


def test_renewable_cost_decay_compounds_with_more_builds(game_env):
    for _ in range(3):
        game_env.build("solar")
    assert game_env.state.plant_cost("solar") == pytest.approx(80 * 0.95**3)


def test_renewable_cost_floors_at_minimum_multiplier(game_env):
    game_env.state.cumulative_built["solar"] = 1000
    assert game_env.state.plant_cost("solar") == pytest.approx(80 * 0.4)


def test_fossil_cost_never_decays(game_env):
    for _ in range(5):
        game_env.build("coal")
    assert game_env.state.plant_cost("coal") == 50


def test_nuclear_cost_never_decays(game_env):
    game_env.build("nuclear")
    assert game_env.state.plant_cost("nuclear") == 200


def test_cumulative_built_survives_retiring(game_env):
    game_env.build("wind")
    game_env.retire("wind")
    cost_after_retire = game_env.state.plant_cost("wind")
    assert cost_after_retire == pytest.approx(70 * 0.95)  # discount persists
    assert game_env.state.plant_counts["wind"] == 0  # but the fleet is smaller


def test_retiring_a_deeply_discounted_renewable_never_profits(game_env):
    # Once the learning-curve discount passes 50% off base cost, a flat
    # "50% of base cost" refund would pay out more than the plant just
    # cost to build -- a risk-free build+retire money exploit. The refund
    # must track the plant's current (discounted) cost instead, so
    # retiring never earns more than it just cost to build.
    game_env.state.cumulative_built["solar"] = 20  # deep into the discount
    funds_before = game_env.state.funds
    game_env.build("solar")
    game_env.retire("solar")
    assert game_env.state.funds <= funds_before


def test_render_shows_discounted_build_cost(game_env):
    game_env.build("solar")
    expected_cost = 80 * 0.95
    assert f"Build ({expected_cost:.0f})" == game_env.elements["solar-build-button"].innerText


def test_render_shows_emissions_and_fossil_share(game_env):
    game_env.build("coal")
    game_env.advance_round()
    assert "60" in game_env.elements["emissions-display"].innerText
    assert "100%" in game_env.elements["fossil-share-display"].innerText
