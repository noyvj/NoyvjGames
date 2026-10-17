"""Tests for the shift_open() function in progress.py."""

import progress


def test_shift_open_returns_true_for_valid_shift():
    """Test that shift_open returns True for a valid shift ID."""
    sid = progress.ORDER[0]
    best = {}
    assert progress.shift_open(best, sid) is True


def test_shift_open_returns_true_for_another_valid_shift():
    """Test that shift_open returns True for another valid shift ID."""
    sid = progress.ORDER[-1] if len(progress.ORDER) > 1 else progress.ORDER[0]
    best = {}
    assert progress.shift_open(best, sid) is True


def test_shift_open_returns_false_for_invalid_shift():
    """Test that shift_open returns False for an unknown shift ID."""
    invalid_sid = "nonexistent_shift"
    best = {}
    assert progress.shift_open(best, invalid_sid) is False


def test_shift_open_with_partial_best_state():
    """Test that shift_open still returns True for valid shifts even when some are done."""
    sid = progress.ORDER[0]
    best = {progress.ORDER[1]: 3} if len(progress.ORDER) > 1 else {}
    assert progress.shift_open(best, sid) is True
