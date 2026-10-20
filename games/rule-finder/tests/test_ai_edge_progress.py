"""Edge-case tests for progress.py."""

import cases
import progress


def test_drawer_named_empty_named():
    """drawer_named returns 0 when no cases are named."""
    drawer = cases.DRAWER_LIST[0]
    assert progress.drawer_named({}, drawer) == 0


def test_drawer_named_with_real_cases():
    """drawer_named counts correctly when some cases are named."""
    drawer = cases.DRAWER_LIST[0]
    first_case_id = list(cases.BY_ID.keys())[0]
    named = {first_case_id: {"t": 1, "r": "even"}}
    assert progress.drawer_named(named, drawer) == 1


def test_drawer_clean_empty_named():
    """drawer_clean returns 0 when no cases are named."""
    drawer = cases.DRAWER_LIST[0]
    assert progress.drawer_clean({}, drawer) == 0


def test_drawer_open_limits():
    """drawer_open handles out-of-bounds and zero indices correctly."""
    assert progress.drawer_open(-1) is False
    assert progress.drawer_open(0) is True
    assert progress.drawer_open(len(cases.DRAWER_LIST)) is False


def test_case_open_limits():
    """case_open returns True for known cases and False for unknown."""
    first_id = list(cases.BY_ID.keys())[0]
    assert progress.case_open(first_id) is True
    assert progress.case_open("nonexistent-case") is False


def test_totals_empty_named():
    """totals returns correct counts when no cases are named."""
    result = progress.totals({})
    assert result["cases"] == len(cases.ALL_CASES)
    assert result["named"] == 0
    assert result["clean"] == 0
    assert result["drawers"] == len(cases.DRAWER_LIST)
    assert result["drawers_closed"] == 0


def test_next_case_empty_named():
    """next_case returns the first case when nothing is named."""
    first_id = list(cases.BY_ID.keys())[0]
    next_cid = progress.next_case({}, first_id)
    assert next_cid is not None
    assert next_cid in cases.ORDER


def test_next_case_all_named():
    """next_case returns None when every case is named."""
    named = {c.id: {"t": 1, "r": "even"} for c in cases.ALL_CASES}
    first_id = list(cases.BY_ID.keys())[0]
    assert progress.next_case(named, first_id) is None
