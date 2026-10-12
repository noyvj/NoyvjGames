"""Tests for the season_done() function in charts.py."""

import charts

# Sample data for testing
SEASON_0_CHARTS = [c["id"] for c in charts.SEASONS[0]["charts"]]
SEASON_1_CHARTS = [c["id"] for c in charts.SEASONS[1]["charts"]]
SEASON_2_CHARTS = [c["id"] for c in charts.SEASONS[2]["charts"]]


def test_season_done_with_no_charts_solved():
    """When no charts are solved, season_done returns 0 for any season."""
    solved = set()
    assert charts.season_done(solved, 0) == 0
    assert charts.season_done(solved, 1) == 0
    assert charts.season_done(solved, 2) == 0


def test_season_done_with_some_charts_solved_in_season():
    """When some charts in a season are solved, season_done returns the correct count."""
    solved = {SEASON_0_CHARTS[0], SEASON_0_CHARTS[2]}  # First and third charts in season 0
    assert charts.season_done(solved, 0) == 2
    assert charts.season_done(solved, 1) == 0  # No charts solved in season 1


def test_season_done_with_all_charts_solved_in_season():
    """When all charts in a season are solved, season_done returns the season's chart count."""
    solved = set(SEASON_1_CHARTS)  # All charts in season 1
    assert charts.season_done(solved, 1) == len(SEASON_1_CHARTS)
    assert charts.season_done(solved, 0) == 0  # No charts solved in season 0


def test_season_done_with_charts_from_multiple_seasons():
    """When charts from multiple seasons are solved, season_done counts correctly per season."""
    solved = {SEASON_0_CHARTS[0], SEASON_1_CHARTS[1], SEASON_2_CHARTS[0]}
    assert charts.season_done(solved, 0) == 1
    assert charts.season_done(solved, 1) == 1
    assert charts.season_done(solved, 2) == 1
