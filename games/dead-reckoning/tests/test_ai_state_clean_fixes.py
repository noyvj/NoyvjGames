"""Tests for state.clean_fixes()."""

from state import clean_fixes


def test_valid_fixes_are_returned_sorted():
    """Normal case: valid fixes are kept and sorted by after_leg."""
    data = [
        {"after_leg": 2, "x": 10.5, "y": 20.3, "landmark": "l1"},
        {"after_leg": 0, "x": 5.0, "y": 5.0, "landmark": "l2"},
        {"after_leg": 1, "x": 8.0, "y": 9.0, "landmark": "l3"},
    ]
    result = clean_fixes(data, sailed=3, landmark_ids={"l1", "l2", "l3"})
    assert len(result) == 3
    assert [f["after_leg"] for f in result] == [0, 1, 2]
    assert result[0]["x"] == 5.0 and result[0]["y"] == 5.0
    assert result[1]["x"] == 8.0 and result[1]["y"] == 9.0
    assert result[2]["x"] == 10.5 and result[2]["y"] == 20.3


def test_x_y_are_clamped_to_bounds():
    """Normal case: x and y values outside [-5.0, size + 5.0] are clamped."""
    data = [
        {"after_leg": 0, "x": -10.0, "y": 50.0, "landmark": "l1"},
    ]
    result = clean_fixes(data, sailed=2, landmark_ids={"l1"}, size=40)
    assert len(result) == 1
    assert result[0]["x"] == -5.0
    assert result[0]["y"] == 45.0


def test_invalid_entries_are_filtered():
    """Edge case: out-of-range after_leg, missing landmark id, and non-dict entries are skipped."""
    data = [
        {"after_leg": 3, "x": 10.0, "y": 10.0, "landmark": "l1"},
        {"after_leg": -1, "x": 10.0, "y": 10.0, "landmark": "l1"},
        {"after_leg": True, "x": 10.0, "y": 10.0, "landmark": "l1"},
        "not a dict",
        {"after_leg": 1, "x": 10.0, "y": 10.0, "landmark": "unknown_landmark"},
        {"after_leg": 1, "x": 10.0, "y": 10.0, "landmark": "l1"},
    ]
    result = clean_fixes(data, sailed=3, landmark_ids={"l1"})
    assert len(result) == 1
    assert result[0]["after_leg"] == 1
