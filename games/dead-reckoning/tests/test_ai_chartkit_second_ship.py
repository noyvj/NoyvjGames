from chartkit import second_ship


def test_second_ship_creates_ship_b_with_required_fields():
    """Test that second_ship creates a ship B with required fields."""
    ship = second_ship((0, 0), (10, 10), 12.0)
    assert ship["name"] == "Ship B"
    assert ship["start"] == [0, 0]
    assert ship["dest"] == [10, 10]
    assert ship["deadline"] == 12.0
    assert ship["waypoints"] == [[0, 0], [10, 10]]


def test_second_ship_with_custom_waypoints():
    """Test that second_ship uses custom waypoints when provided."""
    waypoints = [(0, 0), (5, 5), (10, 10)]
    ship = second_ship((0, 0), (10, 10), 12.0, waypoints=waypoints)
    assert ship["waypoints"] == [[0, 0], [5, 5], [10, 10]]


def test_second_ship_with_override_fields():
    """Test that second_ship allows overriding default values."""
    ship = second_ship((0, 0), (10, 10), 12.0, naive_fails=True, fair_ok=False)
    assert ship["naive_fails"] is True
    assert ship["fair_ok"] is False
