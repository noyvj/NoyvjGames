"""Tests for sandbox.relief()."""

import sandbox


def _make_state(resources=None, land_health=0.5, pollution=0.5, sprawl=0.5, fed_fraction=0.8, population=10, shelter=5):
    """Minimal mock state matching what relief() expects."""
    res = resources or {"materials": 0.0, "tools": 0.0, "knowledge": 0.0, "food": 0.0}

    class State:
        def __init__(self):
            self.resources = res
            self.land_health = land_health
            self.pollution = pollution
            self.sprawl = sprawl
            self.fed_fraction = fed_fraction
            self.population = population
            self.buildings = {"shelter": shelter}

        def food_storage_capacity(self, effects=None):
            return 50.0

        def housing_capacity(self, effects=None):
            return self.buildings["shelter"] * 4

    return State()


def test_relief_clamps_resources_and_environment_to_floors_ceilings():
    """Normal case: values below/above bounds are pushed to the defined limits."""
    state = _make_state(
        resources={"materials": 10.0, "tools": 5.0, "knowledge": 100.0, "food": 10.0},
        land_health=0.1, pollution=0.8, sprawl=0.8, fed_fraction=0.5, population=10
    )
    sandbox.relief(state)

    assert state.resources["materials"] == sandbox.MATERIALS_FLOOR
    assert state.resources["tools"] == sandbox.TOOLS_FLOOR
    assert state.resources["knowledge"] == sandbox.KNOWLEDGE_FLOOR
    assert state.resources["food"] == 50.0
    assert state.land_health == sandbox.LAND_FLOOR
    assert state.pollution == sandbox.POLLUTION_CEILING
    assert state.sprawl == sandbox.SPRAWL_CEILING
    assert state.fed_fraction == 1.0
    assert state.population == sandbox.MIN_PEOPLE


def test_relief_leaves_high_values_unchanged():
    """Normal case: values already above floors/ceilings are not lowered (except fed_fraction)."""
    state = _make_state(
        resources={"materials": 1000.0, "tools": 100.0, "knowledge": 1000.0, "food": 200.0},
        land_health=1.0, pollution=0.0, sprawl=0.0, fed_fraction=0.9, population=100
    )
    sandbox.relief(state)

    assert state.resources["materials"] == 1000.0
    assert state.resources["tools"] == 100.0
    assert state.resources["knowledge"] == 1000.0
    assert state.resources["food"] == 200.0
    assert state.land_health == 1.0
    assert state.pollution == 0.0
    assert state.sprawl == 0.0
    assert state.fed_fraction == 1.0
    assert state.population == 100


def test_relief_adds_shelter_until_capacity_meets_population():
    """Edge case: shelter is incrementally added until housing capacity >= population or hits 10_000."""
    state = _make_state(
        resources={"materials": 500.0, "tools": 30.0, "knowledge": 500.0, "food": 60.0},
        land_health=1.0, pollution=0.0, sprawl=0.0, fed_fraction=1.0, population=50, shelter=2
    )
    sandbox.relief(state)

    # housing_capacity returns shelter * 4. We need capacity >= 50 => shelter >= 13 (since 12*4=48 < 50).
    assert state.buildings["shelter"] == 13
