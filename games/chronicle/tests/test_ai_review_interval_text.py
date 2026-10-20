"""Tests for review.interval_text()."""


import review as rv


def test_interval_text_returns_tomorrow_for_one_day():
    assert rv.interval_text(1) == "tomorrow"


def test_interval_text_formats_multiple_days_correctly():
    assert rv.interval_text(3) == "in 3 days"
    assert rv.interval_text(7) == "in 7 days"


def test_interval_text_handles_zero_and_large_numbers():
    assert rv.interval_text(0) == "in 0 days"
    assert rv.interval_text(100) == "in 100 days"
