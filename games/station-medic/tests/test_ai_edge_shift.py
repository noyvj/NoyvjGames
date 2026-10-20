"""Edge-case tests for shift.py public functions."""

import cases
import shift
from shift import Case


def test_grade_of_boundaries():
    """grade_of returns 3 for cost <= 0, 2 for cost <= 2, 1 otherwise."""
    assert shift.grade_of(0) == 3
    assert shift.grade_of(-5) == 3
    assert shift.grade_of(1) == 2
    assert shift.grade_of(2) == 2
    assert shift.grade_of(3) == 1
    assert shift.grade_of(100) == 1


def test_grade_for_difficulties():
    """grade_for adjusts seals per difficulty: easy (+1), normal (unchanged), hard (-1)."""
    for cost in range(-1, 5):
        assert shift.grade_for(cost, "easy") == 3 if cost <= 1 else 2 if cost <= 3 else 1
        assert shift.grade_for(cost, "normal") == shift.grade_of(cost)
        assert shift.grade_for(cost, "hard") == 3 if cost <= 0 else 2 if cost <= 1 else 1


def test_to_from_token_boundaries():
    """to_token and from_token handle valid actions, boundary indices (99), and reject >99."""
    # Valid action
    tok = shift.to_token(("scan", 0, 0))
    assert shift.from_token(tok) == ("scan", 0, 0)

    # Boundary indices (99 is allowed)
    tok_max = shift.to_token(("treat", 99, 99))
    assert shift.from_token(tok_max) == ("treat", 99, 99)

    # Out of bounds (>99 should be rejected by from_token)
    tok_over = shift.to_token(("scan", 100, 0))
    assert shift.from_token(tok_over) is None


def test_case_apply_out_of_bounds():
    """Case.apply refuses actions with out-of-bounds patient or treatment indices."""
    d = cases.ALL[0]
    c = Case(d)
    st = c.new_state()

    # Out of bounds patient index
    _, info = c.apply(st, ("scan", len(c.patients), 0))
    assert not info["ok"]

    # Out of bounds treatment index
    _, info = c.apply(st, ("treat", 0, len(c.tx)))
    assert not info["ok"]


def test_replay_invalid_tokens():
    """replay returns (None, None) when given an invalid token string."""
    d = cases.ALL[0]
    c = Case(d)
    st, infos = shift.replay(c, ["invalid:token"])
    assert st is None and infos is None

    # Also test with a valid action followed by an invalid one
    st2, infos2 = shift.replay(c, [shift.to_token(("scan", 0, 0)), "bad"])
    assert st2 is None and infos2 is None
