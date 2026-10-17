"""Tests for progress.next_case()."""

import cases
import progress


def test_next_case_returns_first_unnamed():
    """When one case is named, next_case returns the following case in order."""
    first_id = cases.ALL_CASES[0].id
    second_id = cases.ALL_CASES[1].id
    named = {first_id: {"t": 0}}
    result = progress.next_case(named, first_id)
    assert result == second_id


def test_next_case_wraps_around_to_first():
    """When the current case is the last one and all others are named, next_case wraps to the first case."""
    order = cases.ORDER
    named = {cid: {"t": 0} for cid in order[1:]}
    result = progress.next_case(named, order[-1])
    assert result == order[0]


def test_next_case_returns_none_when_all_named():
    """When every case is named, next_case returns None."""
    all_ids = [c.id for c in cases.ALL_CASES]
    named = {cid: {"t": 0} for cid in all_ids}
    result = progress.next_case(named, all_ids[0])
    assert result is None
