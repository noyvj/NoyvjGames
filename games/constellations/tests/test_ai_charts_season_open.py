"""Tests for charts.season_open() - the season gating function."""

import charts


def test_season_zero_is_always_open():
    """Season 0 (Winter Sky) should always be open, even with no charts solved."""
    assert charts.season_open({}, 0) is True


def test_season_one_opens_after_five_winter_charts():
    """Season 1 (Spring Sky) opens when 5 Winter charts are done."""
    # With 4 Winter charts done, Season 1 should still be closed
    winter_ids = [c["id"] for c in charts.SEASONS[0]["charts"]]
    assert charts.season_open({winter_ids[0]: 3}, 1) is False

    # With 5 Winter charts done, Season 1 should open
    assert charts.season_open({winter_ids[i]: 3 for i in range(5)}, 1) is True


def test_season_two_opens_after_five_spring_charts():
    """Season 2 (Summer Sky) opens when 5 Spring charts are done."""
    spring_ids = [c["id"] for c in charts.SEASONS[1]["charts"]]
    assert charts.season_open({spring_ids[i]: 3 for i in range(5)}, 2) is True


def test_season_three_opens_after_five_summer_charts():
    """Season 3 (Autumn Sky) opens when 5 Summer charts are done."""
    summer_ids = [c["id"] for c in charts.SEASONS[2]["charts"]]
    assert charts.season_open({summer_ids[i]: 3 for i in range(5)}, 3) is True


def test_season_four_opens_after_five_autumn_charts():
    """Season 4 (Southern Sky) opens when 5 Autumn charts are done."""
    autumn_ids = [c["id"] for c in charts.SEASONS[3]["charts"]]
    assert charts.season_open({autumn_ids[i]: 3 for i in range(5)}, 4) is True


def test_season_five_is_not_in_seasons_list():
    """Season 5 doesn't exist, so it should always return False."""
    assert charts.season_open({}, 5) is False
