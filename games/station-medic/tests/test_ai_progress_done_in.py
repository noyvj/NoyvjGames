"""Tests for the done_in() function in progress.py."""


import progress


def test_done_in_counts_done_shifts_in_chapter():
    """Test that done_in correctly counts shifts with a grade > 0 in a given chapter."""
    chapter = progress.CHAPTERS[0]
    best = {sid: 3 for sid in chapter["shifts"][:len(chapter["shifts"]) // 2]}
    result = progress.done_in(best, chapter)
    assert result == len(chapter["shifts"]) // 2


def test_done_in_counts_all_shifts_when_all_are_done():
    """Test that done_in returns the total number of shifts when every shift in the chapter is done."""
    chapter = progress.CHAPTERS[0]
    best = {sid: 2 for sid in chapter["shifts"]}
    result = progress.done_in(best, chapter)
    assert result == len(chapter["shifts"])


def test_done_in_returns_zero_when_no_shifts_are_done():
    """Test the edge case where no shifts in the chapter have been completed."""
    chapter = progress.CHAPTERS[0]
    best = {}
    result = progress.done_in(best, chapter)
    assert result == 0
