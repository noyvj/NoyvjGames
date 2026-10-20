"""Edge-case tests for progress.py."""

import progress


def test_done_in_with_empty_best():
    """Test done_in returns 0 when best is empty."""
    assert progress.done_in({}, progress.CHAPTERS[0]) == 0


def test_done_in_with_full_chapter():
    """Test done_in counts all shifts as done when grades are positive."""
    best = {sid: 3 for sid in progress.CHAPTERS[0]["shifts"]}
    assert progress.done_in(best, progress.CHAPTERS[0]) == len(progress.CHAPTERS[0]["shifts"])


def test_chapter_open_with_out_of_bounds_index():
    """Test chapter_open returns False for negative or out-of-range index."""
    best = {}
    assert progress.chapter_open(best, -1) is False
    assert progress.chapter_open(best, len(progress.CHAPTERS)) is False


def test_grade_of_with_missing_sid():
    """Test grade_of returns 0 when sid is not in best."""
    assert progress.grade_of({}, "99-9") == 0


def test_effective_normal_difficulty():
    """Test effective returns the Normal seal from best."""
    best = {"1-1": 3}
    tiers = {}
    assert progress.effective(best, tiers, "1-1", "normal") == 3


def test_effective_hard_difficulty_missing_shift():
    """Test effective returns 0 for Hard when the shift is not in the tier."""
    best = {"1-1": 3}
    tiers = {"hard": {}}
    assert progress.effective(best, tiers, "1-1", "hard") == 0


def test_next_shift_wraps_around_when_all_done():
    """Test next_shift wraps to the first shift when all are done."""
    best = {sid: 3 for sid in progress.ORDER}
    cur = progress.ORDER[-1]
    assert progress.next_shift(best, cur) == progress.ORDER[0]


def test_next_shift_with_invalid_cur():
    """Test next_shift finds the first open shift when cur is not in ORDER."""
    best = {}
    nxt = progress.next_shift(best, "invalid-shift")
    assert nxt is not None
    assert nxt in progress.ORDER
