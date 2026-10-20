"""Edge-case tests for solver.py public functions."""

import pytest

import casework as cw
import progress
import solver


def test_validate_rejects_empty_data():
    """validate should return an error list when given an empty dictionary."""
    assert isinstance(solver.validate({}), list)
    assert len(solver.validate({})) > 0


def test_validate_rejects_truth_not_in_pool():
    """validate crashes when given a truth kind that is not a valid name, even if it's missing from the pool."""
    data = dict(progress.DATA["1-1"])
    data["truth"] = ["nonexistent_kind"]
    with pytest.raises(KeyError):
        solver.validate(data)


def test_analyse_returns_expected_structure():
    """analyse should return a dictionary with cands, kits, min_kit, and unique keys."""
    case = cw.Case(progress.DATA["1-1"])
    info = solver.analyse(case)
    assert set(info.keys()) == {"cands", "kits", "min_kit", "unique"}
    assert isinstance(info["cands"], list)
    assert isinstance(info["kits"], list)
    assert isinstance(info["min_kit"], int)
    assert isinstance(info["unique"], bool)


def test_separates_handles_empty_candidates():
    """separates should return True when there are fewer than two candidates to compare."""
    case = cw.Case(progress.DATA["1-1"])
    # Pass an empty list as cands to simulate zero remaining suspects
    assert solver.separates(case, set(), 0, cands=[]) is True


def test_all_kits_with_zero_limit():
    """all_kits with limit=0 should only check the empty bag and return a list of tuples."""
    case = cw.Case(progress.DATA["1-1"])
    kits = solver.all_kits(case, limit=0)
    assert isinstance(kits, list)
    for k in kits:
        assert len(k) == 0


def test_next_action_returns_none_when_solved():
    """next_action should return None immediately if the case is already solved."""
    case = cw.Case(progress.DATA["1-1"])
    st = case.new_state()
    st = st[:cw.SOLVED] + (1,) + st[cw.SOLVED + 1:]
    assert solver.next_action(case, st) is None
