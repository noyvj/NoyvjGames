"""Tests for progress.drawer_named()."""

import cases
import progress


def test_drawer_named_counts_partial_progress():
    """drawer_named() returns the number of cases in the drawer that are in named."""
    first_case_id = cases.DRAWER_LIST[0]["cases"][0].id
    named = {first_case_id: {"t": 0, "r": "even"}}
    drawer = cases.DRAWER_LIST[0]
    count = progress.drawer_named(named, drawer)
    assert count == 1


def test_drawer_named_counts_all_progress():
    """drawer_named() returns the total number of cases when all are named."""
    drawer = cases.DRAWER_LIST[0]
    named = {c.id: {"t": 0, "r": "even"} for c in drawer["cases"]}
    count = progress.drawer_named(named, drawer)
    assert count == len(drawer["cases"])


def test_drawer_named_handles_empty_named():
    """drawer_named() returns 0 when no cases are named."""
    named = {}
    drawer = cases.DRAWER_LIST[0]
    count = progress.drawer_named(named, drawer)
    assert count == 0
