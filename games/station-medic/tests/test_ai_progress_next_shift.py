"""Tests for the next_shift() function in progress.py."""

import progress


def test_next_shift_returns_first_undone_after_cur():
    """Test that next_shift returns the first undone shift after cur when best is empty."""
    # Use real shift IDs from the game data
    cur = progress.ORDER[0]
    best = {}
    result = progress.next_shift(best, cur)
    assert result == progress.ORDER[1], f"Expected {progress.ORDER[1]}, got {result}"


def test_next_shift_skips_done_shifts():
    """Test that next_shift skips shifts marked as done in best and finds the next undone one."""
    # Pick a shift far enough ahead so we can mark some as done
    cur = progress.ORDER[5]
    best = {progress.ORDER[i]: 3 for i in range(6, 10)}  # shifts 6-9 are done
    result = progress.next_shift(best, cur)
    assert result == progress.ORDER[10], f"Expected {progress.ORDER[10]}, got {result}"


def test_next_shift_wraps_around_when_all_done():
    """Test that next_shift wraps around to the first shift when all shifts are done."""
    # Mark every shift as done
    best = {sid: 3 for sid in progress.ORDER}
    cur = progress.ORDER[-1]  # last shift
    result = progress.next_shift(best, cur)
    assert result == progress.ORDER[0], f"Expected {progress.ORDER[0]}, got {result}"
