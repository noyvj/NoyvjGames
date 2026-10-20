"""Tests for edge cases of functions in levels_a.py."""


import levels_a


def test_num_with_zero_bits():
    """num should return 0 when bits is 0, regardless of input dict."""
    assert levels_a.num({"A0": 1}, "A", 0) == 0


def test_num_with_all_zeros():
    """num should return 0 when all input bits are zero."""
    assert levels_a.num({"A0": 0, "A1": 0, "A2": 0}, "A", 3) == 0


def test_num_with_single_bit_set():
    """num should correctly compute the value for a single bit set to 1."""
    assert levels_a.num({"A0": 1}, "A", 1) == 1
    assert levels_a.num({"A0": 0, "A1": 0, "A2": 1}, "A", 3) == 4


def test_num_with_all_bits_set():
    """num should return the maximum value for the given bit width."""
    v = {"D0": 1, "D1": 1, "D2": 1}
    assert levels_a.num(v, "D", 3) == 7


def test_num_with_negative_bits():
    """num handles negative bits by returning 0 (range is empty)."""
    assert levels_a.num({"A0": 1}, "A", -5) == 0
