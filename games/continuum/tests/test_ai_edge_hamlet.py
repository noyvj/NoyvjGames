"""Edge-case tests for hamlet.py public functions."""

import math

import hamlet
import sim


def _state():
    """Helper to create a fresh CityState, matching test_hamlet_view.py."""
    return sim.CityState()


def test_stations_for_era_at_first_and_last_era():
    """Test stations_for_era with the earliest and latest eras."""
    tribal = hamlet.stations_for_era("tribal")
    assert len(tribal) == 7
    assert tribal[0]["id"] == hamlet.TOWN_ID

    relay = hamlet.stations_for_era("relay")
    assert len(relay) == len(hamlet.STATIONS)


def test_position_with_zero_and_maximum_slots():
    """Test position() at slot 0 and the largest defined slot."""
    town = hamlet.STATIONS_BY_ID[hamlet.TOWN_ID]
    x0, z0 = hamlet.position(town)
    assert x0 == 0.0 and z0 == hamlet.RING_RADIUS

    relay_station = hamlet.STATIONS_BY_ID["relay"]
    xr, zr = hamlet.position(relay_station)
    expected_angle = 16 * (2.0 * math.pi / hamlet.SLOT_COUNT)
    assert math.isclose(xr, hamlet.RING_RADIUS * math.sin(expected_angle), abs_tol=0.01)


def test_flat_percent_with_zero_and_negative_coordinates():
    """Test flat_percent() with origin and negative coordinates."""
    left, top = hamlet.flat_percent(0.0, 0.0)
    assert left == 50.0 and top == 54.0

    neg_left, neg_top = hamlet.flat_percent(-hamlet.RING_RADIUS, -hamlet.RING_RADIUS)
    assert isinstance(neg_left, float) and isinstance(neg_top, float)


def test_station_view_with_zero_population_and_resources():
    """Test station_view when the settlement has no population or resources."""
    state = _state()
    state.population = 0
    state.resources["materials"] = 0.0
    state.resources["knowledge"] = 0.0
    state.allocation = {role: 0 for role in state.allocation}

    view = hamlet.station_view(hamlet.STATIONS_BY_ID["foragers"], state)
    assert view["primary_ok"] is False
    assert "idle" in view["aria_label"].lower()


def test_researchable_nodes_with_no_available_nodes():
    """Test researchable_nodes when the tree has no available nodes."""
    class MockNode:
        def __init__(self, nid):
            self.node_id = nid
            self.cost = 10

    class MockTree:
        def visible_nodes(self):
            return [MockNode("a"), MockNode("b")]

        def is_researched(self, nid):
            return True

        def is_available(self, nid):
            return False

        def cost_of(self, nid):
            return 10

    tree = MockTree()
    nodes = hamlet.researchable_nodes(tree)
    assert nodes == []


def test_locked_count_with_all_researched():
    """Test locked_count when all visible nodes are already researched."""
    class MockNode:
        def __init__(self, nid):
            self.node_id = nid

    class MockTree:
        def visible_nodes(self):
            return [MockNode("a"), MockNode("b")]

        def is_researched(self, nid):
            return True

        def is_available(self, nid):
            return False

    tree = MockTree()
    count = hamlet.locked_count(tree)
    assert count == 0
