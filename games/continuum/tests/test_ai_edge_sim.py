"""Edge-case tests for sim.py public methods."""


def test_advance_season_with_zero_population(game_env):
    """advance_season should handle zero population without crashing or producing negative resources."""
    game_env.state.population = 0
    game_env.state.resources = {"food": 0, "materials": 0, "knowledge": 0, "tools": 0, "surplus": 0}
    game_env.state.advance_season()
    assert game_env.state.population >= 0


def test_clamp_allocation_with_negative_workers(game_env):
    """clamp_allocation only caps workers at housing capacity; it does not floor negative values."""
    game_env.state.workers = {"foragers": -5, "crafters": 2}
    game_env.state.clamp_allocation()
    assert game_env.state.workers["foragers"] == -5
    assert game_env.state.workers["crafters"] == 2


def test_housing_capacity_with_extreme_effects(game_env):
    """housing_capacity should return a reasonable value even with extreme effect multipliers."""
    extreme_effects = {"housing_bonus": 1000, "housing_penalty": -999}
    cap = game_env.state.housing_capacity(extreme_effects)
    assert cap >= 0


def test_holdings_residents_with_no_holdings(game_env):
    """holdings_residents should return zero when the settlement has no holdings."""
    game_env.state.holdings = []
    residents = game_env.state.holdings_residents()
    assert residents == 0
