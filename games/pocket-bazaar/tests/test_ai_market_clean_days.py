"""Tests for market.clean_days()."""

import market


def test_valid_dates_and_values_are_kept():
    raw = {
        "2026-10-01": {"stars": 3, "served": 5, "total": 8, "coins": 120},
        "2026-10-05": {"stars": 2, "served": 4, "total": 6, "coins": 90},
    }
    assert market.clean_days(raw) == raw


def test_junk_entries_are_dropped_entry_by_entry():
    raw = {
        "2026-10-01": {"stars": 3, "served": 5, "total": 8, "coins": 120},
        "not-a-date": {"stars": 1, "served": 1, "total": 1, "coins": 1},
        "2026-10-05": {"stars": True, "served": 4, "total": 6, "coins": 90},
        "2026-10-10": {"stars": 2, "served": 4, "total": 6, "coins": 90},
    }
    result = market.clean_days(raw)
    assert set(result.keys()) == {"2026-10-01", "2026-10-10"}
    assert result["2026-10-01"]["stars"] == 3


def test_non_dict_input_returns_empty_dict():
    for bad in (None, [], "x", 42):
        assert market.clean_days(bad) == {}
