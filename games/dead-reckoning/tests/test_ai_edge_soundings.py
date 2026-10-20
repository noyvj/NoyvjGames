"""Edge-case tests for soundings.py."""


from soundings import OPEN_DEPTH, depth_at, matching_areas, sounding


def test_depth_at_with_empty_chart():
    """Test that depth_at returns OPEN_DEPTH when given an empty chart dictionary."""
    assert depth_at({}, (0.0, 0.0)) == OPEN_DEPTH


def test_depth_at_with_zero_radius_area():
    """Test that a depth area with zero radius only matches its exact center point."""
    zero_area = {"id": "z", "kind": "depth", "name": "Zero", "x": 5.0, "y": 5.0, "r": 0.0, "fathoms": 5}
    chart = {"depths": [zero_area], "open_depth": 40}
    assert depth_at(chart, (5.0, 5.0)) == 5
    assert depth_at(chart, (5.01, 5.0)) == 40


def test_sounding_clamps_to_minimum_fathom():
    """Test that sounding clamps the result to a minimum of 1 fathom."""
    shallow_area = {"id": "sh", "kind": "depth", "name": "Shallow", "x": 0.0, "y": 0.0, "r": 10.0, "fathoms": 1}
    chart = {"id": "test", "depths": [shallow_area], "open_depth": 40}
    for w in range(5):
        assert sounding(chart, (0.0, 0.0), w)["depth"] >= 1


def test_sounding_with_large_watch_value():
    """Test that sounding handles very large watch numbers without error."""
    chart = {"id": "big", "depths": [], "open_depth": 40}
    reading = sounding(chart, (0.0, 0.0), 99999)
    assert isinstance(reading["depth"], int) and reading["err_pct"] == 10


def test_matching_areas_with_no_open_depth_key():
    """Test that matching_areas falls back to OPEN_DEPTH when the chart lacks an open_depth key."""
    chart = {"id": "m", "depths": []}
    assert matching_areas(chart, OPEN_DEPTH) == ["open"]


def test_matching_areas_boundary_values_for_open_water():
    """Test that matching_areas correctly includes or excludes open water at the error boundary."""
    chart = {"id": "m", "depths": [], "open_depth": 40}
    # Bound is 40 * 0.1 + 1 = 5. So 35 and 45 should match, 34 and 46 should not.
    assert matching_areas(chart, 35) == ["open"]
    assert matching_areas(chart, 45) == ["open"]
    assert matching_areas(chart, 34) == []
    assert matching_areas(chart, 46) == []
