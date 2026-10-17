"""Tests for lesson_open() in lessons.py."""

import lessons


def test_shelf_0_lesson_is_always_open():
    """A lesson on the first shelf is open regardless of cleared count."""
    lid = lessons.ALL[0]["id"]
    assert lessons.lesson_open(set(), lid) is True


def test_shelf_1_lesson_opens_with_enough_cleared():
    """A lesson on shelf 2 opens once 5 lessons from shelf 1 are cleared."""
    # Pick a real lesson from shelf 1
    shelf1_lesson = lessons.SHELVES[1]["lessons"][0]
    lid = shelf1_lesson["id"]
    # Clear exactly OPEN_AT (5) lessons from shelf 0
    cleared = {item["id"] for item in list(lessons.SHELVES[0]["lessons"])[:5]}
    assert lessons.lesson_open(cleared, lid) is True


def test_invalid_lesson_id_returns_false():
    """Passing a non-existent lesson ID never raises and returns False."""
    assert lessons.lesson_open(set(), "does-not-exist") is False
