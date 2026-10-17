import rules


def test_vertical_delta_returns_zero():
    """Vertical delta (x=0) should return lane 0."""
    assert rules.lane_of((0, 1)) == 0


def test_horizontal_delta_returns_one():
    """Horizontal delta (y=0) should return lane 1."""
    assert rules.lane_of((1, 0)) == 1


def test_zero_delta_treated_as_vertical():
    """Zero vector falls back to vertical lane 0."""
    assert rules.lane_of((0, 0)) == 0
