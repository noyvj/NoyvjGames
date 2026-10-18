"""Tests for chapter_open() in missions.py."""

import missions


def test_chapter_0_is_always_open_edge_case():
    """Chapter 0 (index 0) is always open regardless of reached missions."""
    assert missions.chapter_open({}, 0) is True
    assert missions.chapter_open({"c1m1": {"fuel": 1.0}}, 0) is True


def test_chapter_1_opens_after_five_missions_in_chapter_0():
    """Chapter 1 opens when exactly OPEN_AT (5) missions from chapter 0 are reached."""
    c0_ids = [m["id"] for m in missions.CHAPTERS[0]["missions"]]
    assert missions.chapter_open({c0_ids[i] for i in range(4)}, 1) is False
    assert missions.chapter_open({c0_ids[i] for i in range(5)}, 1) is True


def test_chapter_2_opens_after_five_missions_in_chapter_1():
    """Chapter 2 opens when exactly OPEN_AT (5) missions from chapter 1 are reached."""
    c1_ids = [m["id"] for m in missions.CHAPTERS[1]["missions"]]
    assert missions.chapter_open({c1_ids[i] for i in range(4)}, 2) is False
    assert missions.chapter_open({c1_ids[i] for i in range(5)}, 2) is True
