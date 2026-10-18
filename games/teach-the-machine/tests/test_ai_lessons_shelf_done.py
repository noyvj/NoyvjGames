"""Tests for shelf_done() in lessons.py."""

import lessons


def test_shelf_done_counts_cleared_lessons_on_a_specific_shelf():
    """shelf_done returns how many lessons from shelf s are in the cleared set."""
    shelf_0_lessons = [lesson["id"] for lesson in lessons.SHELVES[0]["lessons"]]
    lid1, lid2 = shelf_0_lessons[:2]
    cleared = {lid1}
    assert lessons.shelf_done(cleared, 0) == 1

    cleared = {lid1, lid2}
    assert lessons.shelf_done(cleared, 0) == 2


def test_shelf_done_returns_zero_when_no_lessons_are_cleared():
    """Edge case: an empty cleared set should return 0 for any shelf."""
    assert lessons.shelf_done(set(), 0) == 0
    assert lessons.shelf_done(set(), 1) == 0


def test_shelf_done_ignores_lessons_from_other_shelves():
    """Clearing a lesson from shelf 1 should not affect the count for shelf 0."""
    shelf_0_lessons = [lesson["id"] for lesson in lessons.SHELVES[0]["lessons"]]
    lid0 = shelf_0_lessons[0]
    shelf_1_lessons = [lesson["id"] for lesson in lessons.SHELVES[1]["lessons"]]
    lid1 = shelf_1_lessons[0]

    cleared = {lid1}
    assert lessons.shelf_done(cleared, 0) == 0

    cleared = {lid0, lid1}
    assert lessons.shelf_done(cleared, 0) == 1
