"""Tests for Solver.best_move() in solver.py."""

import cases
from shift import Case
from solver import Solver, solve_truth


def test_best_move_returns_a_valid_action_tuple_on_start():
    """On a fresh shift, best_move returns a tuple action (e.g., ('treat', p, x)) rather than None or a scalar."""
    d = cases.ALL[0]
    c = Case(d)
    s = Solver(c)
    st = s.start()
    act = s.best_move(st)
    assert isinstance(act, tuple), "best_move must return a tuple action"
    assert len(act) >= 2, "action tuple must contain at least (type, index)"


def test_best_move_matches_solver_plan_first_step():
    """best_move should return the exact first action that solve_truth would take."""
    d = cases.ALL[1]
    c = Case(d)
    s = Solver(c)
    st = s.start()
    act = s.best_move(st)
    plan, _, _ = solve_truth(c)
    assert act == plan[0], f"best_move returned {act}, expected {plan[0]}"


def test_best_move_returns_none_when_shift_is_finished():
    """When all patients are closed, moves() yields no candidates and best_move returns None."""
    d = cases.ALL[0]
    c = Case(d)
    s = Solver(c)
    # Construct a finished state: all patients closed, no readings, no cures
    finished_pats = tuple((1, 0, 0, (-1,) * len(c.tests), 0, 0) for _ in c.patients)
    finished_st = (c.stock0, finished_pats)
    act = s.best_move(finished_st)
    assert act is None, "best_move should return None when all patients are closed"
