"""Edge-case tests for fleet.py (milestone 7). Tests limits, empty/zero inputs, and boundary conditions."""


import copy

import charts
import fleet


def test_is_two_accepts_valid_inputs_and_rejects_invalid():
    """is_two should only return True for dicts containing a 'ship2' dict."""
    assert not fleet.is_two(None)
    assert not fleet.is_two("chart")
    assert not fleet.is_two({"id": "x"})
    assert not fleet.is_two({"id": "x", "ship2": "not a dict"})
    c = charts.get_chart("two-01")
    assert fleet.is_two(c)


def test_ship_chart_returns_original_for_index_0_and_copies_keys_for_index_1():
    """ship_chart(0) returns the chart itself; ship_chart(1) extracts ship2 keys."""
    c = charts.get_chart("two-01")
    assert fleet.ship_chart(c, 0) is c
    b = fleet.ship_chart(c, 1)
    assert b["id"] == c["id"] + "~B"
    for key in ("start", "dest", "speeds", "deadline", "arrival_radius"):
        assert b[key] == c["ship2"][key], f"Missing or mismatched key: {key}"
    # Missing keys in ship2 are simply not overridden; base chart keys remain
    partial = copy.deepcopy(c)
    partial["ship2"] = {"start": [10.0, 10.0]}
    b_partial = fleet.ship_chart(partial, 1)
    assert b_partial["dest"] == c["dest"] and b_partial["start"] == [10.0, 10.0]


def test_closest_approach_handles_single_point_tracks():
    """Tracks with only the start point should compare at t=0."""
    a = [[0.0, 0.0, 0.0]]
    b = [[0.0, 3.0, 4.0]]
    ap = fleet.closest_approach(a, b)
    assert ap["dist"] == 5.0 and not ap["too_close"] and ap["t"] == 0.0


def test_closest_approach_exactly_at_separation_does_not_flag_too_close():
    """A gap of exactly SEPARATION (1.0 nm) is fine."""
    a = [[0.0, 0.0, 0.0], [1.0, 1.0, 0.0]]
    b = [[0.0, 0.0, 1.0], [1.0, 1.0, 1.0]]
    ap = fleet.closest_approach(a, b)
    assert ap["dist"] == 1.0 and not ap["too_close"] and ap["breach_t"] is None


def test_closest_approach_ignores_time_after_one_ship_ends():
    """Only the overlapping time window counts."""
    a = [[0.0, 0.0, 0.0], [1.0, 10.0, 0.0]]
    b = [[0.0, 5.0, 10.0], [2.0, -5.0, 10.0]]
    ap = fleet.closest_approach(a, b)
    assert ap["overlap"] == 1.0 and ap["dist"] >= 4.0


def test_sail_fleet_handles_minimal_legal_legs_without_crashing():
    """sail_fleet should return a valid structure even with the smallest allowed leg duration."""
    c = charts.get_chart("two-01")
    la = [{"heading": 90, "speed": 3.0, "hours": 0.5}]
    lb = [{"heading": 270, "speed": 3.0, "hours": 0.5}]
    res = fleet.sail_fleet(c, la, lb)
    assert "ships" in res and "approach" in res and "events" in res
    assert len(res["ships"]) == 2
