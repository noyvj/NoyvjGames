"""Tests for the seasons_finished() function in charts.py."""

import charts

SEASON_0_CHARTS = [c["id"] for c in charts.SEASONS[0]["charts"]]
SEASON_1_CHARTS = [c["id"] for c in charts.SEASONS[1]["charts"]]
SEASON_2_CHARTS = [c["id"] for c in charts.SEASONS[2]["charts"]]
SEASON_3_CHARTS = [c["id"] for c in charts.SEASONS[3]["charts"]]
SEASON_4_CHARTS = [c["id"] for c in charts.SEASONS[4]["charts"]]


def test_seasons_finished_with_no_charts_solved():
    """When no charts are solved, seasons_finished returns 0."""
    assert charts.seasons_finished(set()) == 0


def test_seasons_finished_with_one_full_season():
    """When exactly one season is completely solved, seasons_finished returns 1."""
    solved = set(SEASON_0_CHARTS)
    assert charts.seasons_finished(solved) == 1


def test_seasons_finished_with_all_charts_solved():
    """When all charts across all seasons are solved, seasons_finished returns the total number of seasons."""
    all_charts = set(SEASON_0_CHARTS + SEASON_1_CHARTS + SEASON_2_CHARTS + SEASON_3_CHARTS + SEASON_4_CHARTS)
    assert charts.seasons_finished(all_charts) == len(charts.SEASONS)
