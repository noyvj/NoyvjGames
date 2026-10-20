"""Tests for view.rep_title() which maps reputation points to a title string."""

import data
import view


def test_rep_title_returns_default_for_points_below_lowest_threshold():
    """Edge case: points below the first threshold should return the first title."""
    lowest_threshold = data.REP_TITLES[0][0]
    title = view.rep_title(lowest_threshold - 1)
    assert title == data.REP_TITLES[0][1]


def test_rep_title_returns_correct_title_at_exact_threshold():
    """Normal case: points exactly at a threshold should return that threshold's title."""
    mid_idx = len(data.REP_TITLES) // 2
    threshold, expected_name = data.REP_TITLES[mid_idx]
    title = view.rep_title(threshold)
    assert title == expected_name


def test_rep_title_returns_highest_title_for_points_above_max_threshold():
    """Normal case: points above the highest threshold should return the final title."""
    max_threshold = data.REP_TITLES[-1][0]
    expected_name = data.REP_TITLES[-1][1]
    title = view.rep_title(max_threshold + 1)
    assert title == expected_name
