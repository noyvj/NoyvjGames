"""Tests for chapter_loaded() in charts.py."""


import charts


def test_chapter_loaded_returns_true_for_open():
    """The 'open' chapter is always loaded at module init."""
    assert charts.chapter_loaded("open") is True


def test_chapter_loaded_returns_true_for_a_later_chapter():
    """Under CPython, all chapters are eagerly loaded."""
    assert charts.chapter_loaded("ships") is True


def test_chapter_loaded_returns_false_for_unknown_id():
    """An unknown chapter id should not be marked as loaded."""
    assert charts.chapter_loaded("nonexistent-chapter") is False
