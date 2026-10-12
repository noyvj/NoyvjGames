"""Tests for the line_of() function in hints.py."""

import hints

UNKNOWN, FILLED, EMPTY = hints.UNKNOWN, hints.FILLED, hints.EMPTY


def test_line_of_extracts_a_row():
    """line_of() should return the specified row as a list."""
    grid = [
        [UNKNOWN, FILLED, EMPTY],
        [FILLED, EMPTY, UNKNOWN],
        [EMPTY, UNKNOWN, FILLED]
    ]
    assert hints.line_of(grid, "row", 1) == [FILLED, EMPTY, UNKNOWN]


def test_line_of_extracts_a_column():
    """line_of() should return the specified column as a list."""
    grid = [
        [UNKNOWN, FILLED, EMPTY],
        [FILLED, EMPTY, UNKNOWN],
        [EMPTY, UNKNOWN, FILLED]
    ]
    assert hints.line_of(grid, "col", 2) == [EMPTY, UNKNOWN, FILLED]
