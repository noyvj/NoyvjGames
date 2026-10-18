"""Tests for missions.chapter_done()."""

import missions


def test_chapter_done_counts_reached_missions_in_chapter_0():
    reached = {"c1m1": {"fuel": 1.0, "flights": 1}, "c1m2": {"fuel": 1.5, "flights": 0}}
    assert missions.chapter_done(reached, 0) == 2


def test_chapter_done_counts_reached_missions_in_chapter_1():
    reached = {"c2m1": {"fuel": 3.0, "flights": 1}, "c2m2": {"fuel": 2.0, "flights": 2}}
    assert missions.chapter_done(reached, 1) == 2


def test_chapter_done_returns_zero_for_empty_reached():
    assert missions.chapter_done({}, 0) == 0
