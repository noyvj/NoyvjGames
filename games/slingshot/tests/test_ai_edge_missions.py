"""Edge-case tests for missions.py public functions."""

import missions


def test_chapter_need_for_first_chapter_returns_zero():
    assert missions.chapter_need(0) == 0


def test_chapter_need_for_subsequent_chapters_returns_open_at():
    # CHAPTERS has 3 chapters, each with more than OPEN_AT (5) missions.
    assert missions.chapter_need(1) == missions.OPEN_AT
    assert missions.chapter_need(2) == missions.OPEN_AT


def test_chapter_done_with_empty_reached_set_returns_zero():
    assert missions.chapter_done(set(), 0) == 0


def test_chapter_done_with_all_missions_of_chapter_one_reached():
    reached = {m["id"] for m in missions.CHAPTERS[0]["missions"]}
    assert missions.chapter_done(reached, 0) == len(missions.CHAPTERS[0]["missions"])


def test_chapter_open_for_first_chapter_is_always_true():
    assert missions.chapter_open(set(), 0) is True
    assert missions.chapter_open({"c1m1"}, 0) is True


def test_chapter_open_for_second_chapter_requires_five_missions():
    # Exactly OPEN_AT - 1 done should not open chapter 2
    reached = {m["id"] for m in missions.CHAPTERS[0]["missions"][:missions.OPEN_AT - 1]}
    assert missions.chapter_open(reached, 1) is False

    # Exactly OPEN_AT done should open chapter 2
    reached = {m["id"] for m in missions.CHAPTERS[0]["missions"][:missions.OPEN_AT]}
    assert missions.chapter_open(reached, 1) is True


def test_mission_open_returns_true_when_chapter_is_open():
    # Chapter 1 is always open, so any mission in it should be open.
    assert missions.mission_open(set(), "c1m1") is True

    # Chapter 2 opens when chapter 1 has OPEN_AT done.
    reached = {m["id"] for m in missions.CHAPTERS[0]["missions"][:missions.OPEN_AT]}
    assert missions.mission_open(reached, "c2m1") is True
