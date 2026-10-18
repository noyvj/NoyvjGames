"""Tests for Case.all_entered() in casework.py."""

import casework as cw
import progress


def test_all_entered_returns_false_when_one_room_is_not_entered():
    """Normal case: 3 rooms, only the first is entered."""
    case = cw.Case(progress.DATA["1-1"])
    st = case.new_state()
    partial_mask = 1 << 0
    st_with_partial = list(st)
    st_with_partial[cw.ENTERED] = partial_mask
    st_with_partial = tuple(st_with_partial)

    assert not case.all_entered(st_with_partial), "Should be False when not all rooms are entered"


def test_all_entered_returns_true_when_all_rooms_are_entered():
    """Normal case: 3 rooms, all entered."""
    case = cw.Case(progress.DATA["1-1"])
    st = case.new_state()
    n_rooms = len(case.rooms)
    full_mask = (1 << n_rooms) - 1
    st_with_full = list(st)
    st_with_full[cw.ENTERED] = full_mask
    st_with_full = tuple(st_with_full)

    assert case.all_entered(st_with_full), "Should be True when all rooms are entered"


def test_all_entered_handles_larger_case():
    """Normal case: a larger house (chapter 3, case 1) to ensure bitmask works beyond small sizes."""
    case = cw.Case(progress.DATA["3-1"])
    st = case.new_state()
    n_rooms = len(case.rooms)
    full_mask = (1 << n_rooms) - 1
    st_with_full = list(st)
    st_with_full[cw.ENTERED] = full_mask
    st_with_full = tuple(st_with_full)

    assert case.all_entered(st_with_full), "Should be True for a larger case when all rooms are entered"


def test_all_entered_edge_case_zero_rooms_entered():
    """Edge case: no rooms entered yet (entered mask is 0)."""
    case = cw.Case(progress.DATA["1-1"])
    st = case.new_state()
    # new_state initializes entered to 0
    assert not case.all_entered(st), "Should be False when zero rooms are entered"
