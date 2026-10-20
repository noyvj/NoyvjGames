"""Edge-case tests for sky.py public functions."""

import charts
import pytest
import sky


def test_segments_touch_at_endpoint():
    """Touching exactly at one endpoint should return True."""
    assert sky.segments_touch((0, 0), (2, 2), (2, 2), (4, 0)) is True


def test_segments_touch_strictly_crossing():
    """Strictly crossing segments should return True."""
    assert sky.segments_touch((0, 0), (4, 4), (0, 4), (4, 0)) is True


def test_segments_touch_disjoint():
    """Disjoint collinear segments should return False."""
    assert sky.segments_touch((0, 0), (1, 1), (3, 3), (4, 4)) is False


def test_edges_conflict_same_edge():
    """Identical edges must not conflict."""
    c = charts.BY_ID["columba"]
    pts = [(s["x"], s["y"]) for s in c["stars"]]
    assert sky.edges_conflict(pts, (0, 1), (0, 1)) is False


def test_edges_conflict_collinear_same_direction():
    """Collinear edges leaving a star in the same direction conflict."""
    pts = [(2, 0), (1, 0), (3, 0)]
    assert sky.edges_conflict(pts, (0, 1), (1, 2)) is True


def test_edges_conflict_crossing():
    """Crossing edges must conflict."""
    pts = [(0, 0), (2, 2), (0, 2), (2, 0)]
    assert sky.edges_conflict(pts, (0, 1), (2, 3)) is True


def test_point_segment_distance2_on_segment():
    """Distance should be zero when the point lies on the segment."""
    assert sky.point_segment_distance2((1, 0), (0, 0), (2, 0)) == 0.0


def test_point_segment_distance2_far_away():
    """Distance squared for a point far from the segment."""
    assert sky.point_segment_distance2((1, 5), (0, 0), (2, 0)) == 25.0


def test_point_segment_distance2_zero_length_segment():
    """Distance to a zero-length segment is just the point distance squared."""
    assert sky.point_segment_distance2((3, 4), (0, 0), (0, 0)) == 25.0


def test_analyse_empty_chosen():
    """Analyse with no chosen lines should return valid=False."""
    c = charts.BY_ID["columba"]
    chart = sky.Chart(c)
    result = sky.analyse(chart, [])
    assert result["valid"] is False


def test_analyse_valid_figure():
    """A known valid figure from the chart data should pass analyse."""
    c = charts.BY_ID["columba"]
    chart = sky.Chart(c)
    chosen = [chart.index[tuple(e)] for e in c["figure"]]
    result = sky.analyse(chart, chosen)
    assert result["valid"] is True


def test_analyse_disconnected_pieces():
    """Two disjoint edges should yield more than one piece."""
    c = charts.BY_ID["columba"]
    chart = sky.Chart(c)
    e1 = c["edges"][0]
    e2 = next(e for e in c["edges"] if set(e) != set(e1) and not (set(e) & set(e1)))
    chosen = [chart.index[tuple(e1)], chart.index[tuple(e2)]]
    result = sky.analyse(chart, chosen)
    assert result["parts"] > 1


def test_propagate_contradiction():
    """Propagating a contradiction should return (None, trail)."""
    c = charts.BY_ID["columba"]
    chart = sky.Chart(c)
    conflict_idx = next((k for k in range(len(chart.edges)) if chart.conflict[k] != 0), None)
    if conflict_idx is None:
        pytest.skip("No conflicting edges in this chart")
    other_k = None
    for m in range(len(chart.edges)):
        if chart.conflict[conflict_idx] >> m & 1:
            other_k = m
            break
    known = {conflict_idx: sky.IN, other_k: sky.IN}
    result, trail = sky.propagate(chart, known)
    assert result is None


def test_propagate_with_must_lines():
    """Propagating with only must lines should return a valid partial state."""
    c = charts.BY_ID["columba"]
    chart = sky.Chart(c)
    known = {k: sky.IN for k in chart.must}
    result, trail = sky.propagate(chart, known)
    assert isinstance(result, dict)


def test_propagate_lookahead_false():
    """Without lookahead, propagate should not deduce beyond basic rules."""
    c = charts.BY_ID["columba"]
    chart = sky.Chart(c)
    result, trail = sky.propagate(chart, {}, lookahead=False)
    assert isinstance(result, dict)
