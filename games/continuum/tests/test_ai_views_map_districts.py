"""Tests for views.map_districts()."""

import save
import sim
import views


def test_map_districts_returns_all_era_buildings_with_zero_counts():
    """Tribal era starts with no buildings; map_districts lists them all as 0."""
    c = save.Campaign()
    c.state.buildings = {}  # Clear any default starting buildings
    districts = views.map_districts(c.state)
    expected_buildings = sim.buildings_for_era("tribal")
    assert len(districts) == len(expected_buildings)
    for b, count in districts:
        assert b in expected_buildings
        assert count == 0


def test_map_districts_reflects_built_counts_and_era():
    """Building a shelter and advancing to Classical era updates the list."""
    c = save.Campaign()
    c.state.buildings["shelter"] = 3
    c.state.era = "classical"
    districts = views.map_districts(c.state)
    district_map = dict(districts)
    assert district_map["shelter"] == 3
    # Classical era adds canals, which should be present with count 0
    assert "canals" in district_map
    assert district_map["canals"] == 0


def test_map_districts_clamps_negative_and_non_numeric_counts_to_zero():
    """Malformed building counts in state degrade gracefully to 0."""
    c = save.Campaign()
    c.state.buildings["shelter"] = -5
    c.state.buildings["granary"] = "many"
    districts = views.map_districts(c.state)
    district_map = dict(districts)
    assert district_map["shelter"] == 0
    assert district_map["granary"] == 0
