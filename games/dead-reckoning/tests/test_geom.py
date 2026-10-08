import math

from geom import (angle_diff, bearing, dist, norm_deg, point_in_polygon, rnd, seg_circle_hit,
                  seg_point_dist, seg_polygon_dist, seg_polygon_hit, seg_seg_hit, unit)


def test_headings_point_where_a_sailor_expects():
    for heading, vec in ((0, (0, 1)), (90, (1, 0)), (180, (0, -1)), (270, (-1, 0))):
        x, y = unit(heading)
        assert abs(x - vec[0]) < 1e-9 and abs(y - vec[1]) < 1e-9


def test_bearing_is_the_inverse_of_unit():
    for heading in (0, 17, 90, 133, 180, 271, 359):
        a = (3.0, 4.0)
        ux, uy = unit(heading)
        assert abs(bearing(a, (a[0] + 5 * ux, a[1] + 5 * uy)) - heading) < 1e-6


def test_bearing_of_a_point_to_itself_is_zero_not_an_error():
    assert bearing((1, 1), (1, 1)) == 0.0


def test_norm_and_angle_diff_wrap_the_right_way():
    assert norm_deg(-10) == 350 and norm_deg(370) == 10
    assert angle_diff(350, 10) == 20 and angle_diff(10, 350) == -20
    assert angle_diff(0, 180) == 180


def test_distance_is_euclidean():
    assert dist((0, 0), (3, 4)) == 5


def test_a_segment_through_a_circle_hits_at_the_near_edge():
    t = seg_circle_hit((0, 0), (10, 0), (5, 0), 1)
    assert abs(t - 0.4) < 1e-9


def test_a_segment_that_stops_short_or_misses_does_not_hit():
    assert seg_circle_hit((0, 0), (3, 0), (5, 0), 1) is None
    assert seg_circle_hit((0, 0), (10, 0), (5, 3), 1) is None


def test_a_segment_starting_inside_a_circle_hits_at_zero():
    assert seg_circle_hit((5, 0), (10, 0), (5, 0), 1) == 0.0


def test_a_long_step_cannot_skip_over_a_small_rock():
    # one step of 50 nm across a 0.1 nm rock still reports the hit
    assert seg_circle_hit((0, 0), (50, 0), (25, 0.05), 0.1) is not None


def test_segment_point_distance_clamps_to_the_ends():
    assert seg_point_dist((0, 0), (4, 0), (2, 3)) == 3
    assert seg_point_dist((0, 0), (4, 0), (7, 4)) == 5


def test_segments_cross_only_when_they_really_cross():
    assert abs(seg_seg_hit((0, 0), (10, 0), (5, -5), (5, 5)) - 0.5) < 1e-9
    assert seg_seg_hit((0, 0), (4, 0), (5, -5), (5, 5)) is None
    assert seg_seg_hit((0, 0), (4, 0), (0, 1), (4, 1)) is None


SQUARE = [(2, 2), (6, 2), (6, 6), (2, 6)]


def test_point_in_polygon():
    assert point_in_polygon((4, 4), SQUARE)
    assert not point_in_polygon((7, 4), SQUARE)


def test_segment_polygon_hit_and_distance():
    assert abs(seg_polygon_hit((0, 4), (10, 4), SQUARE) - 0.2) < 1e-9
    assert seg_polygon_hit((0, 0), (1, 0), SQUARE) is None
    assert seg_polygon_hit((3, 3), (9, 9), SQUARE) == 0.0
    assert seg_polygon_dist((0, 4), (1, 4), SQUARE) == 1
    assert seg_polygon_dist((0, 4), (4, 4), SQUARE) == 0


def test_rounding_never_returns_negative_zero():
    assert str(rnd(-0.0001)) == "0.0"
    assert math.isclose(rnd(1.2349), 1.23)
