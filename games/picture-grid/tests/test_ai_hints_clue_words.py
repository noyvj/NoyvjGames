"""Tests for the clue_words() function in hints.py."""

import hints


def test_clue_words_with_normal_clue():
    """Test clue_words() with a typical nonogram clue."""
    assert hints.clue_words([3, 2]) == "3 2"


def test_clue_words_with_single_number_clue():
    """Test clue_words() with a single-number clue."""
    assert hints.clue_words([5]) == "5"


def test_clue_words_with_empty_clue():
    """Test clue_words() with an empty clue (should return '0')."""
    assert hints.clue_words([]) == "0"
