"""Tests for progress.drawer_named_by_id()."""

import unittest.mock as mock

import progress


class _Case:
    """Minimal case mock matching the interface expected by progress.py."""

    def __init__(self, cid):
        self.id = cid


def test_returns_count_for_matching_drawer():
    """drawer_named_by_id() returns how many cases in the target drawer are named."""
    drawer_a = {"id": "drawer_a", "cases": [_Case("a1"), _Case("a2"), _Case("a3")]}
    drawer_b = {"id": "drawer_b", "cases": [_Case("b1")]}

    named = {"a1": {}, "a3": {}}

    with mock.patch.object(progress.cases, 'DRAWER_LIST', [drawer_a, drawer_b]):
        result = progress.drawer_named_by_id(named, "drawer_a")

    assert result == 2


def test_returns_zero_when_no_cases_named():
    """drawer_named_by_id() returns zero when no cases in the drawer are named."""
    drawer_x = {"id": "drawer_x", "cases": [_Case("x1"), _Case("x2")]}

    named = {}

    with mock.patch.object(progress.cases, 'DRAWER_LIST', [drawer_x]):
        result = progress.drawer_named_by_id(named, "drawer_x")

    assert result == 0


def test_returns_zero_for_nonexistent_drawer():
    """drawer_named_by_id() returns zero when the drawer id does not match any drawer."""
    drawer_y = {"id": "drawer_y", "cases": [_Case("y1")]}

    named = {"y1": {}}

    with mock.patch.object(progress.cases, 'DRAWER_LIST', [drawer_y]):
        result = progress.drawer_named_by_id(named, "nonexistent")

    assert result == 0
