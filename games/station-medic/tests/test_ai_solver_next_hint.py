"""Tests for next_hint() in solver.py."""

import cases
from shift import Case
from solver import solve_truth, next_hint


def test_next_hint_returns_action_on_initial_state():
    """A fresh shift should always have a first hint."""
    d = cases.ALL[0]
    c = Case(d)
    st = c.new_state()
    hint = next_hint(c, st)
    assert hint is not None
    assert isinstance(hint, tuple)


def test_next_hint_returns_action_mid_shift():
    """After one valid move, the solver should still provide a hint if the shift isn't done."""
    d = cases.ALL[1]
    c = Case(d)
    st = c.new_state()
    first_hint = next_hint(c, st)
    assert first_hint is not None
    st2, _ = c.apply(st, first_hint)
    hint2 = next_hint(c, st2)
    if not c.done(st2):
        assert hint2 is not None
        assert isinstance(hint2, tuple)


def test_next_hint_returns_none_when_shift_is_finished():
    """Edge case: a completed shift should yield no hint."""
    d = cases.ALL[0]
    c = Case(d)
    plan, finished_st, cost = solve_truth(c)
    assert cost == 0 and c.done(finished_st), "Test setup failed"
    assert next_hint(c, finished_st) is None
