"""Tests for shelves_finished() in lessons.py."""

import lessons


def test_no_shelves_finished_with_empty_cleared_set():
    """Edge case: no lessons cleared means zero shelves are finished."""
    assert lessons.shelves_finished(set()) == 0


def test_all_shelves_finished_when_every_lesson_is_cleared():
    """Normal case: clearing every lesson across all shelves finishes all shelves."""
    all_ids = {le["id"] for le in lessons.ALL}
    assert lessons.shelves_finished(all_ids) == len(lessons.SHELVES)


def test_partial_shelf_completion_counts_correctly():
    """Normal case: only fully clearing one shelf counts as one finished shelf."""
    # Take all lesson IDs from the first shelf
    shelf_0_ids = {le["id"] for le in lessons.SHELVES[0]["lessons"]}
    assert lessons.shelves_finished(shelf_0_ids) == 1

    # Add just one lesson from the second shelf (not enough to finish it)
    shelf_1_first_id = lessons.SHELVES[1]["lessons"][0]["id"]
    assert lessons.shelves_finished(shelf_0_ids | {shelf_1_first_id}) == 1
