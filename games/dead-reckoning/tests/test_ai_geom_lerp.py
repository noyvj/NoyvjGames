from geom import lerp


def test_lerp_at_t_is_0_returns_start_point():
    assert lerp((1, 2), (5, 6), 0) == (1, 2)


def test_lerp_at_t_is_half_gives_midpoint():
    assert lerp((0, 0), (10, 10), 0.5) == (5.0, 5.0)


def test_lerp_at_t_is_1_returns_end_point():
    assert lerp((-2, -3), (4, 7), 1) == (4, 7)


def test_lerp_extrapolates_when_t_is_greater_than_one():
    # Edge case: t=2 should double the vector from a to b
    assert lerp((0, 0), (3, 4), 2) == (6.0, 8.0)
