"""Tests for the trace() function in levels_c.py."""

import levels_c


def test_trace_program_a_default_ticks():
    """trace(PROGRAM_A) should return the accumulator values after each of 8 clock edges."""
    result = levels_c.trace(levels_c.PROGRAM_A)
    assert result == [3, 5, 6, 9, 11, 13, 14, 1]


def test_trace_program_b_default_ticks():
    """trace(PROGRAM_B) should return the accumulator values after each of 8 clock edges."""
    result = levels_c.trace(levels_c.PROGRAM_B)
    assert result == [1, 4, 7, 5, 5, 8, 11, 9]


def test_trace_with_custom_ticks():
    """trace() should stop after the specified number of ticks and return that many values."""
    result = levels_c.trace(levels_c.PROGRAM_A, ticks=3)
    assert result == [3, 5, 6]
