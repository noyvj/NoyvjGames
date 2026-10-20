"""Tests for daily.parse_date()."""


from datetime import date


import daily


def test_valid_iso_date_returns_correct_object():
    """Normal case: a standard YYYY-MM-DD string returns the expected date object."""
    assert daily.parse_date("2026-10-05") == date(2026, 10, 5)


def test_another_valid_iso_date_returns_correct_object():
    """Normal case: another valid YYYY-MM-DD string works correctly."""
    assert daily.parse_date("2026-01-01") == date(2026, 1, 1)


def test_invalid_format_returns_none():
    """Edge case: a string with wrong separators or length returns None."""
    assert daily.parse_date("2026/10/05") is None
