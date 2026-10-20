"""Edge-case tests for geom.py focusing on limits and boundary conditions."""


from geom import angle_diff, bearing, norm_deg, point_in_polygon, seg_circle_hit, unit


SQUARE = [(2, 2), (6, 2), (6, 6), (2, 6)]


def test_norm_deg_handles_zero_and_large_wraps():
    """norm_deg should fold negative and large positive values into [0, 360)."""
    assert norm_deg(0) == 0.0
    assert norm_deg(360) == 0.0
    assert norm_deg(-360) == 0.0
    assert norm_deg(720.5) == 0.5
    assert norm_deg(-90) == 270.0


def test_unit_handles_cardinal_directions_and_full_circle():
    """unit should return correct vectors for cardinals and wrap 360 to 0."""
    for h, expected in ((0, (0, 1)), (90, (1, 0)), (180, (0, -1)), (270, (-1, 0))):
        x, y = unit(h)
        assert abs(x - expected[0]) < 1e-9 and abs(y - expected[1]) < 1e-9
    x, y = unit(360)
    assert abs(x - 0.0) < 1e-9 and abs(y - 1.0) < 1e-9


def test_bearing_of_identical_points_returns_zero():
    """bearing should return 0.0 for zero-distance input without raising."""
    assert bearing((5.0, 5.0), (5.0, 5.0)) == 0.0


def test_angle_diff_handles_exact_opposites_and_wrapping():
    """angle_diff should correctly handle exact opposites and wrap-around cases."""
    assert angle_diff(0, 180) == 180
    assert angle_diff(180, 0) == 180
    assert angle_diff(350, 10) == 20
    assert angle_diff(10, 350) == -20
    assert angle_diff(45, 45) == 0


def test_seg_circle_hit_with_zero_length_segment():
    """seg_circle_hit should handle zero-length segments inside and outside circles."""
    assert seg_circle_hit((0.5, 0.5), (0.5, 0.5), (0, 0), 1) == 0.0
    assert seg_circle_hit((2, 2), (2, 2), (0, 0), 1) is None


def test_point_in_polygon_with_empty_and_boundary_inputs():
    """point_in_polygon should safely handle empty polygons and distinguish inside/outside."""
    assert not point_in_polygon((0, 0), [])
    assert point_in_polygon((4, 4), SQUARE)
    assert not point_in_polygon((7, 4), SQUARE)
