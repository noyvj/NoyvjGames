"""Tests for the is_two_input() function in achievements.py."""

import achievements


def test_is_two_input_returns_true_for_constant_zero():
    """is_two_input() should return True when all output bits are 0 (constant function)."""
    code = 0b00000000
    assert achievements.is_two_input(code) is True


def test_is_two_input_returns_false_when_third_input_matters():
    """is_two_input() should return False if any pair of rows differs, meaning the output depends on C."""
    # Bits 4 and 5 differ (row 100 vs 101), so it depends on the third input
    code = 0b00010000
    assert achievements.is_two_input(code) is False


def test_is_two_input_edge_case_all_ones():
    """is_two_input() should return True for the constant-one function (all pairs match)."""
    code = 0b11111111
    assert achievements.is_two_input(code) is True
