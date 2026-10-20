"""Tests for flourish_label_of() in banners.py."""

import banners


def test_flourish_label_of_returns_correct_label_for_known_id():
    """A known flourish ID returns its catalog label."""
    assert banners.flourish_label_of("pennants") == "Pennants"


def test_flourish_label_of_returns_correct_label_for_another_known_id():
    """Another known flourish ID also returns its correct label."""
    assert banners.flourish_label_of("lanterns") == "Lanterns"


def test_flourish_label_of_falls_back_to_default_for_unknown_id():
    """An unknown or invalid ID falls back to the default 'No flourish' label."""
    assert banners.flourish_label_of("nonexistent") == "No flourish"
