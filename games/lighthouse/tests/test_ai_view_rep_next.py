"""Tests for view.rep_next()."""

import data
from view import rep_next


def test_rep_next_returns_first_title_when_points_are_zero():
    # rep_next returns the first threshold strictly greater than points.
    # Since REP_TITLES starts at 0, rep_next(0) skips it and returns the second threshold.
    assert len(data.REP_TITLES) >= 2
    result = rep_next(0)
    assert result is not None
    assert result["at"] == data.REP_TITLES[1][0]
    assert result["title"] == data.REP_TITLES[1][1]


def test_rep_next_returns_next_title_when_points_are_between_thresholds():
    # Points just below the second threshold should return the second title.
    assert len(data.REP_TITLES) >= 2
    next_threshold = data.REP_TITLES[1][0]
    result = rep_next(next_threshold - 1)
    assert result is not None
    assert result["at"] == next_threshold
    assert result["title"] == data.REP_TITLES[1][1]


def test_rep_next_returns_none_when_points_exceed_all_titles():
    # Edge case: points meet or exceed the highest threshold.
    max_threshold = data.REP_TITLES[-1][0]
    result = rep_next(max_threshold + 1)
    assert result is None
