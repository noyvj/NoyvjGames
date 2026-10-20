"""Tests for daily.parse_date() function."""

from datetime import date

import daily


def test_parse_date_valid_formats():
    """Test that parse_date returns correct date objects for valid YYYY-MM-DD strings."""
    assert daily.parse_date("2026-10-11") == date(2026, 10, 11)
    assert daily.parse_date("2026-01-01") == date(2026, 1, 1)
    assert daily.parse_date("2026-12-31") == date(2026, 12, 31)


def test_parse_date_invalid_formats():
    """Test that parse_date returns None for invalid date formats."""
    assert daily.parse_date("2026-13-01") is None  # Invalid month
    assert daily.parse_date("2026-02-30") is None  # Invalid day
    assert daily.parse_date("2026-1-1") is None    # Missing leading zeros
    assert daily.parse_date("2026/10/11") is None  # Wrong separator
    assert daily.parse_date("10-11-2026") is None  # Wrong order
    assert daily.parse_date("2026-10") is None     # Incomplete date
    assert daily.parse_date("2026-10-11T00:00") is None  # Includes time


def test_parse_date_edge_cases():
    """Test edge cases and non-string inputs."""
    assert daily.parse_date(None) is None
    assert daily.parse_date(20261011) is None  # Integer, not string
    assert daily.parse_date("") is None        # Empty string
    assert daily.parse_date("not-a-date") is None  # Random text
    assert daily.parse_date("2026-10-11 ") is None  # Trailing space
    assert daily.parse_date(" 2026-10-11") is None  # Leading space
