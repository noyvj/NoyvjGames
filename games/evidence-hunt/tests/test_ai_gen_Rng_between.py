"""Tests for Rng.between() in gen.py."""

import gen


def test_between_returns_value_in_range():
    rng = gen.Rng(42)
    result = rng.between(1, 5)
    assert 1 <= result <= 5


def test_between_with_larger_range():
    rng = gen.Rng(99)
    result = rng.between(10, 20)
    assert 10 <= result <= 20


def test_between_edge_case_lo_equals_hi():
    rng = gen.Rng(7)
    result = rng.between(5, 5)
    assert result == 5
