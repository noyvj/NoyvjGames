"""Tests for available_actions() in orders.py."""

import orders


def test_tribal_no_research_returns_basic_actions():
    """In Tribal era with no research, only shift and notice are available."""
    result = orders.available_actions([], "tribal")
    assert set(result) == {"shift", "notice"}


def test_digital_with_smart_utilities_returns_all_actions():
    """In Digital era with smart_utilities, all four actions become available."""
    result = orders.available_actions(["smart_utilities"], "digital")
    assert set(result) == {"shift", "notice", "refactor", "quick_off"}


def test_edge_case_action_requires_later_era_is_excluded():
    """Actions locked to later eras are excluded even if researched."""
    result = orders.available_actions(["smart_utilities"], "tribal")
    assert set(result) == {"shift", "notice"}
