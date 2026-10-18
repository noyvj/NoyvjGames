"""Tests for chapter_shelved() in reactions.py."""

import reactions


def test_counts_shelved_reactions_for_chapter_0():
    # Chapter 0 has 8 reactions. We pick two real IDs from it.
    c0_ids = [r.id for r in reactions.CHAPTERS[0]["reactions"]]
    shelf = {c0_ids[0]: 1, c0_ids[1]: 2}
    assert reactions.chapter_shelved(shelf, 0) == 2


def test_counts_shelved_reactions_for_chapter_1():
    # Chapter 1 has 8 reactions. Pick one real ID from it.
    c1_ids = [r.id for r in reactions.CHAPTERS[1]["reactions"]]
    shelf = {c1_ids[3]: 1}
    assert reactions.chapter_shelved(shelf, 1) == 1


def test_returns_zero_when_no_reactions_from_chapter_are_shelved():
    # Edge case: shelf contains IDs from other chapters or unrelated keys.
    shelf = {"carbon-dioxide": 1}  # carbon-dioxide is in chapter 0
    assert reactions.chapter_shelved(shelf, 1) == 0
