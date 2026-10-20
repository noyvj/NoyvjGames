"""Tests for charts.name_of()."""

import charts


def test_name_of_returns_correct_name_for_open_chapter():
    # Pick a real chart ID from the open chapter index
    open_charts = charts._INDEX["open"]
    cid, expected_name = open_charts[0]
    assert charts.name_of(cid) == expected_name


def test_name_of_returns_correct_name_for_wind_chapter():
    # Pick a real chart ID from the wind chapter index
    wind_charts = charts._INDEX["wind"]
    cid, expected_name = wind_charts[0]
    assert charts.name_of(cid) == expected_name


def test_name_of_returns_none_for_unknown_id():
    # Practice and daily IDs are not in the campaign index
    assert charts.name_of("practice-1-abc") is None
    assert charts.name_of("daily-2026-10-17") is None
    assert charts.name_of("nonexistent-chart") is None
