"""Tests for the drawer_open() function in progress.py."""

import cases
import progress
import unittest.mock


def test_drawer_open_returns_true_for_valid_index_with_cases():
    """drawer_open() returns True when index is within bounds and has cases."""
    assert progress.drawer_open(0) is True
    assert progress.drawer_open(len(cases.DRAWER_LIST) - 1) is True


def test_drawer_open_returns_false_for_out_of_bounds_index():
    """drawer_open() returns False when index is outside the valid range."""
    assert progress.drawer_open(-1) is False
    assert progress.drawer_open(len(cases.DRAWER_LIST)) is False


def test_drawer_open_handles_empty_cases_list():
    """drawer_open() returns False if a drawer's cases list is empty, even at a valid index."""
    # All real drawers have cases, so we use a minimal mock to test the empty-cases branch.
    mock_drawers = [{"cases": [1]}, {"cases": []}]
    with unittest.mock.patch.object(cases, "DRAWER_LIST", mock_drawers):
        assert progress.drawer_open(0) is True
        assert progress.drawer_open(1) is False
