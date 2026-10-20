import math

from geom import seg_seg_dist


def test_parallel_segments_measure_vertical_gap():
    """Normal case: two parallel horizontal segments separated by a gap."""
    assert abs(seg_seg_dist((0, 0), (4, 0), (1, 3), (5, 3)) - 3.0) < 1e-9


def test_perpendicular_offset_segments_closest_at_endpoint():
    """Normal case: a horizontal and a vertical segment that do not cross."""
    assert abs(seg_seg_dist((0, 0), (4, 0), (5, 1), (5, 5)) - math.sqrt(2)) < 1e-9


def test_collinear_disjoint_segments_measure_gap():
    """Edge case: two segments on the same line with a gap between them."""
    assert abs(seg_seg_dist((0, 0), (2, 0), (3, 0), (5, 0)) - 1.0) < 1e-9
