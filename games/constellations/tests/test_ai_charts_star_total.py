"""Tests for the star_total() function in charts.py."""

import charts

# Sample data for testing
SEASON_0_CHARTS = [c["id"] for c in charts.SEASONS[0]["charts"]]
SEASON_1_CHARTS = [c["id"] for c in charts.SEASONS[1]["charts"]]
SEASON_2_CHARTS = [c["id"] for c in charts.SEASONS[2]["charts"]]


def test_star_total_with_no_charts_solved():
    """When no charts are solved, star_total returns 0."""
    assert charts.star_total(set()) == 0


def test_star_total_with_one_chart_solved():
    """When one chart is solved, star_total returns the number of stars in that chart."""
    cid = SEASON_0_CHARTS[0]
    expected = len(charts.BY_ID[cid]["stars"])
    assert charts.star_total({cid}) == expected


def test_star_total_with_multiple_charts_solved():
    """When multiple charts are solved, star_total returns the sum of their stars."""
    cid1 = SEASON_0_CHARTS[0]
    cid2 = SEASON_1_CHARTS[0]
    expected = len(charts.BY_ID[cid1]["stars"]) + len(charts.BY_ID[cid2]["stars"])
    assert charts.star_total({cid1, cid2}) == expected
