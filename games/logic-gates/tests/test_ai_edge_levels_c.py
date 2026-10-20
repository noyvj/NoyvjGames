"""Tests for edge cases in levels_c.py."""


import levels_c


def test_lamps_empty_kwargs():
    """lamps() should return an empty string when called with no arguments."""
    assert levels_c.lamps() == ""


def test_lamps_single_kwarg():
    """lamps() should format a single key-value pair correctly."""
    assert levels_c.lamps(A=1) == "A=1"


def test_word_min_values():
    """word() with op=0 and imm=0 should return 0."""
    assert levels_c.word(0, 0) == 0


def test_word_max_values():
    """word() with maximum allowed values (op=3, imm=3) should return 15."""
    assert levels_c.word(3, 3) == 15


def test_trace_zero_ticks():
    """trace() with ticks=0 should return an empty list regardless of program."""
    prog = [levels_c.word(0, 0), levels_c.word(0, 0), levels_c.word(0, 0), levels_c.word(0, 0)]
    assert levels_c.trace(prog, ticks=0) == []


def test_trace_full_cycle_with_word_builder():
    """trace() with ticks=4 and a constant program should cycle through indices 0-3."""
    # Build program words using the game's word() helper
    prog = [
        levels_c.word(0, 1),  # ADD 1
        levels_c.word(1, 2),  # AND 2
        levels_c.word(0, 3),  # ADD 3
        levels_c.word(0, 0),  # ADD 0
    ]
    out = levels_c.trace(prog, ticks=4)
    assert out == [1, 0, 3, 3]
