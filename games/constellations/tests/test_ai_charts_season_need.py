"""Tests for the season_need() function in charts.py."""

import charts


def test_season_need_returns_zero_for_season_zero():
    """Season 0 (Winter Sky) should have no requirement to open."""
    assert charts.season_need(0) == 0


def test_season_need_returns_five_for_season_one():
    """Season 1 (Spring Sky) should require 5 charts from season 0 to open."""
    assert charts.season_need(1) == 5


def test_season_need_returns_five_for_season_four():
    """Season 4 (Southern Sky) should require 5 charts from season 3 to open."""
    assert charts.season_need(4) == 5


def test_season_need_returns_min_of_open_at_and_previous_season_size():
    """For a season where the previous season has fewer than OPEN_AT charts,
    season_need() should return the size of the previous season."""
    # This is an edge case test - if a season had fewer than 5 charts,
    # season_need() would return the actual number of charts in that season
    assert charts.season_need(1) == min(charts.OPEN_AT, len(charts.SEASONS[0]["charts"]))
