"""Tests for gallery_hung() in pictures.py."""

import pictures


def test_gallery_hung_counts_subset():
    """When some pictures from gallery 0 are hung, it returns the correct count."""
    g0_pics = [p.id for p in pictures.GALLERIES[0]["pictures"]]
    solved = set(g0_pics[:3])
    assert pictures.gallery_hung(solved, 0) == 3


def test_gallery_hung_counts_all():
    """When all pictures from a gallery are hung, it returns the total number."""
    g1_pics = [p.id for p in pictures.GALLERIES[1]["pictures"]]
    solved = set(g1_pics)
    assert pictures.gallery_hung(solved, 1) == len(g1_pics)


def test_gallery_hung_ignores_other_galleries():
    """When the solved set contains IDs from other galleries, it only counts the target gallery."""
    g0_ids = {p.id for p in pictures.GALLERIES[0]["pictures"]}
    g1_ids = {p.id for p in pictures.GALLERIES[1]["pictures"]}
    solved = set(list(g0_ids)[:5]) | set(list(g1_ids)[:2])
    assert pictures.gallery_hung(solved, 0) == 5
    assert pictures.gallery_hung(solved, 1) == 2


def test_gallery_hung_empty_solved():
    """Edge case: when no pictures are hung, it returns zero."""
    assert pictures.gallery_hung(set(), 0) == 0
