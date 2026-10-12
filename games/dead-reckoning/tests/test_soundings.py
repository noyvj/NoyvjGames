from chartkit import depth_area


def test_depth_area_returns_expected_dict():
    """Test that depth_area returns the expected dictionary structure."""
    result = depth_area("bank", "The Bank", 5.0, 6.0, 2.0, 7)
    expected = {"id": "bank", "kind": "depth", "name": "The Bank", "x": 5.0, "y": 6.0, "r": 2.0, "fathoms": 7}
    assert result == expected
