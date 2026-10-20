import progress
import rooms


def test_cleared_in_counts_all_rooms_when_everyone_is_cleared():
    """Normal case: every room in a chapter is present in best."""
    chapter = rooms.CHAPTER_LIST[0]
    best = {rid: {"n": 1, "t": ""} for rid in chapter["rooms"]}
    assert progress.cleared_in(best, chapter) == len(chapter["rooms"])


def test_cleared_in_counts_only_matched_rooms():
    """Normal case: only some rooms from a chapter are present in best."""
    chapter = rooms.CHAPTER_LIST[1]
    best = {chapter["rooms"][0]: {"n": 1, "t": ""}, chapter["rooms"][-1]: {"n": 1, "t": ""}}
    assert progress.cleared_in(best, chapter) == 2


def test_cleared_in_returns_zero_for_empty_best():
    """Edge case: best is empty, so no rooms are cleared."""
    assert progress.cleared_in({}, rooms.CHAPTER_LIST[0]) == 0
