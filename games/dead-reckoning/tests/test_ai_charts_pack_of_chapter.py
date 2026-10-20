"""Tests for pack_of_chapter() in charts.py."""

import charts


def test_pack_of_chapter_returns_the_correct_pack_for_wind():
    """Normal case: chapter 'wind' should return its lazy pack id."""
    assert charts.pack_of_chapter("wind") == "chapter-wind"


def test_pack_of_chapter_returns_the_correct_pack_for_fog():
    """Normal case: chapter 'fog' should return its lazy pack id."""
    assert charts.pack_of_chapter("fog") == "chapter-fog"


def test_pack_of_chapter_returns_none_for_open_and_unknown_ids():
    """Edge case: the first chapter has no pack, and unknown IDs also return None."""
    assert charts.pack_of_chapter("open") is None
    assert charts.pack_of_chapter("nonexistent") is None
