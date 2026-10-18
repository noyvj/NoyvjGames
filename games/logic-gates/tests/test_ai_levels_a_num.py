"""Tests for the num() function in levels_a.py."""

import levels_a


def test_num_two_bits():
    """num() should combine two bits into a number with prefix0 as LSB and prefix1 as MSB."""
    v = {"A0": 1, "A1": 0}
    assert levels_a.num(v, "A", 2) == 1

    v = {"A0": 0, "A1": 1}
    assert levels_a.num(v, "A", 2) == 2

    v = {"A0": 1, "A1": 1}
    assert levels_a.num(v, "A", 2) == 3


def test_num_three_bits():
    """num() should combine three bits correctly."""
    v = {"S0": 1, "S1": 0, "S2": 1}
    assert levels_a.num(v, "S", 3) == 5


def test_num_edge_case_all_zeros():
    """num() should return 0 when all input bits are zero."""
    v = {"X0": 0, "X1": 0}
    assert levels_a.num(v, "X", 2) == 0
