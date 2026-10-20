import progress
import rooms


def test_cleared_in_empty_and_full():
    """cleared_in returns 0 for empty best, and the chapter length for full best."""
    empty_best = {}
    full_best = {rid: {"n": 999} for rid in rooms.CHAPTER_LIST[0]["rooms"]}
    assert progress.cleared_in(empty_best, rooms.CHAPTER_LIST[0]) == 0
    assert progress.cleared_in(full_best, rooms.CHAPTER_LIST[0]) == len(rooms.CHAPTER_LIST[0]["rooms"])


def test_chapter_open_bounds():
    """chapter_open returns True for valid indices and False for out-of-bounds."""
    best = {}
    num_chapters = len(rooms.CHAPTER_LIST)
    assert progress.chapter_open(best, 0) is True
    assert progress.chapter_open(best, num_chapters - 1) is True
    assert progress.chapter_open(best, -1) is False
    assert progress.chapter_open(best, num_chapters) is False


def test_medal_of_missing_and_cleared():
    """medal_of returns 0 for a missing room, and a positive medal tier when present."""
    best = {}
    rid = "wake-up"
    assert progress.medal_of(best, rid) == 0

    par = rooms.BY_ID[rid].par
    best_with_clear = {rid: {"n": par}}
    assert progress.medal_of(best_with_clear, rid) >= 1


def test_tier_size_hard_vs_normal():
    """tier_size returns hbest for hard, best for normal, None if missing."""
    best = {"wake-up": {"n": 5}}
    hbest = {"wake-up": {"n": 4}}
    rid = "wake-up"

    assert progress.tier_size(best, hbest, rid, "normal") == 5
    assert progress.tier_size(best, hbest, rid, "hard") == {"n": 4}
    assert progress.tier_size({}, {}, rid, "normal") is None
    assert progress.tier_size({}, {}, rid, "hard") is None


def test_next_room_all_cleared():
    """next_room returns the next open room even when all are cleared (per docstring 'else the next open one')."""
    best = {rid: {"n": 999} for rid in rooms.ORDER}
    # wake-up is first in ORDER, so it returns the second room
    assert progress.next_room(best, "wake-up") == rooms.ORDER[1]


def test_totals_empty_and_full():
    """totals returns correct counts for empty and full best dicts."""
    empty_best = {}
    full_best = {rid: {"n": 1} for rid in rooms.ORDER}

    t_empty = progress.totals(empty_best)
    assert t_empty["cleared"] == 0
    assert t_empty["gold"] == 0
    assert t_empty["silver"] == 0
    assert t_empty["bronze"] == 0
    assert t_empty["rooms"] == len(rooms.ORDER)
    assert t_empty["chapters_done"] == 0
    assert t_empty["chapters"] == len(rooms.CHAPTER_LIST)

    t_full = progress.totals(full_best)
    assert t_full["cleared"] == len(rooms.ORDER)
    assert t_full["chapters_done"] == len(rooms.CHAPTER_LIST)
