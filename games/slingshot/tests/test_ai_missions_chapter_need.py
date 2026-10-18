"""Tests for chapter_need() in missions.py."""

import missions


def test_chapter_need_for_first_chapter_returns_zero():
    assert missions.chapter_need(0) == 0


def test_chapter_need_for_second_chapter_respects_open_at():
    # Chapter 1 has 7 missions, OPEN_AT is 5, so min(5, 7) == 5
    assert missions.chapter_need(1) == 5


def test_chapter_need_for_third_chapter_respects_open_at():
    # Chapter 2 has 8 missions, OPEN_AT is 5, so min(5, 8) == 5
    assert missions.chapter_need(2) == 5


def test_chapter_need_uses_actual_chapter_lengths():
    # Ensures the function correctly applies min(OPEN_AT, len(...)) for all chapters
    for i in range(1, len(missions.CHAPTERS)):
        expected = min(missions.OPEN_AT, len(missions.CHAPTERS[i - 1]["missions"]))
        assert missions.chapter_need(i) == expected
