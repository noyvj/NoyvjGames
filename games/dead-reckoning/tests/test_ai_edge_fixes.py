"""Edge-case tests for fixes.py."""

import fixes


def test_in_sight_returns_empty_when_fog_is_enabled():
    chart = {"fog": True, "landmarks": [{"id": "l1", "x": 10.0, "y": 10.0, "visible": 5.0}]}
    assert fixes.in_sight(chart, (10.0, 10.0)) == []


def test_in_sight_returns_empty_when_no_landmarks_exist():
    chart = {"landmarks": []}
    assert fixes.in_sight(chart, (0.0, 0.0)) == []


def test_in_sight_includes_landmark_at_exact_visible_boundary():
    chart = {"landmarks": [{"id": "l1", "x": 10.0, "y": 10.0, "visible": 5.0}]}
    assert len(fixes.in_sight(chart, (10.0, 5.0))) == 1


def test_readings_returns_empty_list_when_no_landmarks_in_sight():
    chart = {"id": "test", "landmarks": [{"id": "l1", "x": 100.0, "y": 100.0, "visible": 1.0}]}
    assert fixes.readings(chart, (0.0, 0.0), 0) == []


def test_position_from_returns_none_for_unknown_landmark():
    chart = {"landmarks": [{"id": "l1", "x": 10.0, "y": 10.0}]}
    assert fixes.position_from(chart, "unknown", 0, 5) is None


def test_position_from_with_zero_range_returns_landmark_position():
    chart = {"landmarks": [{"id": "l1", "x": 12.5, "y": 8.3}]}
    assert fixes.position_from(chart, "l1", 45, 0) == (12.5, 8.3)


def test_readings_clamps_minimum_range_to_0_1():
    chart = {"id": "test", "landmarks": [{"id": "l1", "name": "l1", "kind": "rock", "x": 10.0, "y": 10.0, "visible": 5.0}]}
    readings = fixes.readings(chart, (9.999, 10.0), 0)
    assert len(readings) == 1
    assert readings[0]["range"] >= 0.1
