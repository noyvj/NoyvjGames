"""Tests for plan.is_empty()."""

import plan as planlib


def test_the_empty_plan_returns_true():
    """planlib.empty() should be considered empty."""
    assert planlib.is_empty(planlib.empty()) is True


def test_a_plan_with_burns_returns_false():
    """A plan containing at least one burn is not empty."""
    p = {"burns": [{"t": 0, "at": "time", "head": 0.0, "dv": 1.0}], "pass": {}}
    assert planlib.is_empty(p) is False


def test_a_plan_with_pass_returns_false():
    """A plan containing a closest-approach burn is not empty."""
    p = {"burns": [], "pass": {"earth": 0.5}}
    assert planlib.is_empty(p) is False


def test_extra_keys_do_not_affect_emptiness():
    """An edge case: extra keys in the plan dict do not affect emptiness; only burns and pass matter."""
    p = {"burns": [], "pass": {}, "metadata": "ignored"}
    assert planlib.is_empty(p) is True
