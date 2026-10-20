"""Tests for trajectory.clean_points()."""

import trajectory


def test_valid_points_are_preserved_and_clamped():
    raw = [
        [-1.0, 0.0, -5.0, -10.0],
        [2.0, 1.0, 15.0, 150.0],
    ]
    result = trajectory.clean_points(raw)
    assert len(result) == 2
    # idx clamped to >= 0, pop clamped to >= 0, liv clamped to [0, 100]
    assert result[0][0] == 0.0
    assert result[0][2] == 0.0
    assert result[0][3] == 0.0
    assert result[1][3] == 100.0


def test_invalid_items_are_filtered_out():
    raw = [
        [1.0, 0.0, 10.0, 50.0],
        "bad",
        [1.0, 0.0],
        [True, 0.0, 10.0, 50.0],
        [float("inf"), 0.0, 10.0, 50.0],
    ]
    result = trajectory.clean_points(raw)
    assert len(result) == 1
    assert result[0] == [1.0, 0.0, 10.0, 50.0]


def test_non_list_input_returns_empty_list():
    for junk in (None, "string", 42, {"a": 1}):
        assert trajectory.clean_points(junk) == []
