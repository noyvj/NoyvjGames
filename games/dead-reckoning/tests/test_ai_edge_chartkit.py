"""Edge-case tests for chartkit.py constructors."""


from chartkit import chart, depth_area, land, second_ship, stream, wind


def test_chart_preserves_defaults_when_overridden_with_zero_values():
    """Test that chart() keeps default keys intact when overridden with zero or empty values."""
    c = chart("c1", "Zero Chart", 1, start=[0.0, 0.0], dest=[0.0, 0.0])
    assert c["id"] == "c1"
    assert c["size"] == 20
    assert c["arrival_radius"] == 1.5
    assert c["speeds"] == [3.0, 7.0]
    assert c["modes"] == ["plan"]
    assert c["default_mode"] == "plan"
    assert c["par_wait"] == 0.0
    assert c["fair_ok"] is True


def test_stream_handles_zero_drift_and_empty_tide():
    """Test that stream() correctly omits tide when None, and handles zero drift range."""
    s_no_tide = stream("s1", "No Tide Stream", [0, 0, 10, 10], 90.0, [0.0, 0.0], 90.0, 0.0)
    assert "tide" not in s_no_tide
    assert s_no_tide["drift_range"] == [0.0, 0.0]

    s_with_tide = stream("s2", "Tidal Stream", [0, 0, 10, 10], 90.0, [1.0, 2.0], 90.0, 1.5, tide={"period": 12.0, "phase": 0.0})
    assert s_with_tide["tide"] == {"period": 12.0, "phase": 0.0}


def test_land_accepts_empty_poly_list():
    """Test that land() handles an empty polygon list without crashing."""
    land_obj = land("l1", "Empty Land", [])
    assert land_obj["id"] == "l1"
    assert land_obj["poly"] == []


def test_second_ship_inherits_defaults_when_waypoints_omitted():
    """Test that second_ship() uses start and dest as waypoints when none are provided."""
    s = second_ship([0.0, 0.0], [10.0, 10.0], 24.0)
    assert s["waypoints"] == [[0.0, 0.0], [10.0, 10.0]]
    assert s["name"] == "Ship B"


def test_wind_handles_zero_width_range():
    """Test that wind() correctly stores a zero-width range without error."""
    w = wind(0, [0.0, 0.0], True)
    assert w["from"] == 0
    assert w["range"] == [0.0, 0.0]
    assert w["true"] is True


def test_depth_area_handles_zero_fathoms_and_negative_coordinates():
    """Test that depth_area() accepts zero fathoms and negative coordinates without error."""
    d = depth_area("d1", "Zero Depth", -5.0, -5.0, 0.0, 0)
    assert d["id"] == "d1"
    assert d["x"] == -5.0
    assert d["y"] == -5.0
    assert d["r"] == 0.0
    assert d["fathoms"] == 0
