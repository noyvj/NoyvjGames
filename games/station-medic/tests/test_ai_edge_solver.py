"""Edge-case tests for solver.py public API."""

import cases
from shift import Case
from solver import Solver, solve_truth, next_hint


def test_solver_limit_zero_exhausts_immediately():
    """A limit of 0 should cause exhaustion on the first recursive call to wins()."""
    d = cases.ALL[0]
    c = Case(d)
    s = Solver(c, limit=0)
    assert not s.wins(s.start())
    assert s.exhausted


def test_solver_moves_on_terminal_state_returns_empty():
    """When all patients are closed, moves() should yield no actions."""
    d = cases.ALL[0]
    c = Case(d)
    st = c.new_state()
    # The solver expects exactly 6-element patient tuples: (closed, iso, steady, read, cured, given)
    terminal_st = (st[0], tuple((1, 0, 0, 0, 0, 0) for _ in st[1]))
    solver = Solver(c)
    assert solver.moves(terminal_st) == []


def test_solve_truth_returns_valid_types():
    """solve_truth should return a tuple of (plan, state, cost)."""
    d = cases.ALL[0]
    c = Case(d)
    plan, st, cost = solve_truth(c)
    assert isinstance(plan, list)
    assert isinstance(st, tuple)
    assert cost is None or isinstance(cost, int)


def test_next_hint_returns_none_when_shift_is_complete():
    """next_hint should return None if the shift is already finished."""
    d = cases.ALL[0]
    c = Case(d)
    plan, st, _cost = solve_truth(c)
    assert c.done(st), "Test setup failed: shift not complete"
    assert next_hint(c, st) is None


def test_best_move_returns_none_on_terminal_state():
    """best_move should return None when the shift is already complete."""
    d = cases.ALL[0]
    c = Case(d)
    st = c.new_state()
    # Construct a valid solver state where all patients are closed
    terminal_solver_st = (st[0], tuple((1, 0, 0, 0, 0, 0) for _ in st[1]))
    solver = Solver(c)
    assert solver.best_move(terminal_solver_st) is None


def test_solver_limit_large_value_does_not_exhaust_on_easy_shift():
    """A very large limit should not trigger exhaustion on a simple shift."""
    d = cases.ALL[0]
    c = Case(d)
    s = Solver(c, limit=10**9)
    assert s.solvable()
    assert not s.exhausted
