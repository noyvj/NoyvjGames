"""Edge-case tests for charts.py."""

import charts

SEASON_0_CHARTS = [c["id"] for c in charts.SEASONS[0]["charts"]]


def test_season_done_with_empty_solved():
    """When solved is empty, season_done returns 0 for any valid season index."""
    assert charts.season_done(set(), 0) == 0
    assert charts.season_done(set(), len(charts.SEASONS) - 1) == 0


def test_season_need_with_zero_and_largest_index():
    """season_need(0) is always 0; largest valid index uses the first season's length."""
    assert charts.season_need(0) == 0
    largest = len(charts.SEASONS) - 1
    expected = min(charts.OPEN_AT, len(charts.SEASONS[largest - 1]["charts"]))
    assert charts.season_need(largest) == expected


def test_season_open_with_zero_and_exact_threshold():
    """Season 0 is always open. Season n opens exactly when OPEN_AT charts of season n-1 are done."""
    assert charts.season_open(set(), 0) is True

    # Just below threshold
    solved_below = set(SEASON_0_CHARTS[:charts.OPEN_AT - 1])
    assert charts.season_open(solved_below, 1) is False

    # Exactly at threshold
    solved_at = set(SEASON_0_CHARTS[:charts.OPEN_AT])
    assert charts.season_open(solved_at, 1) is True


def test_chart_open_with_invalid_id():
    """chart_open returns False for unknown chart IDs instead of raising."""
    assert charts.chart_open(set(), "does_not_exist") is False


def test_seasons_finished_with_empty_solved():
    """When no charts are solved, seasons_finished returns 0."""
    assert charts.seasons_finished(set()) == 0


def test_star_total_with_empty_and_single_chart():
    """star_total sums stars correctly for empty and single-chart inputs."""
    assert charts.star_total(set()) == 0

    chart_id = SEASON_0_CHARTS[0]
    expected = len(charts.BY_ID[chart_id]["stars"])
    assert charts.star_total({chart_id}) == expected
