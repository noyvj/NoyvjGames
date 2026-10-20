"""Edge-case tests for pictures.py public functions."""

import pictures


def test_gallery_hung_empty_solved():
    """gallery_hung returns 0 when no pictures are hung."""
    assert pictures.gallery_hung(set(), 0) == 0


def test_gallery_hung_boundary_galleries():
    """gallery_hung works for the first and last gallery indices."""
    solved = {p.id for p in pictures.ALL}
    assert pictures.gallery_hung(solved, 0) == len(pictures.GALLERIES[0]["pictures"])
    assert pictures.gallery_hung(solved, len(pictures.GALLERIES) - 1) == len(pictures.GALLERIES[-1]["pictures"])


def test_gallery_open_zero_and_negative():
    """gallery_open returns True for g <= 0 regardless of solved state."""
    assert pictures.gallery_open(set(), 0) is True
    assert pictures.gallery_open(set(), -5) is True


def test_gallery_open_out_of_bounds():
    """gallery_open returns False when g is beyond the last gallery."""
    assert pictures.gallery_open(set(), len(pictures.GALLERIES)) is False
    assert pictures.gallery_open(set(), 100) is False


def test_picture_open_valid_and_invalid_ids():
    """picture_open correctly identifies open and closed pictures."""
    solved = set()
    first_id = pictures.ALL[0].id
    assert pictures.picture_open(solved, first_id) is True
    assert pictures.picture_open(solved, "nonexistent") is False


def test_galleries_done_empty_and_full():
    """galleries_done returns correct counts for empty and fully solved states."""
    assert pictures.galleries_done(set()) == 0
    full_solved = {p.id for p in pictures.ALL}
    assert pictures.galleries_done(full_solved) == len(pictures.GALLERIES)
