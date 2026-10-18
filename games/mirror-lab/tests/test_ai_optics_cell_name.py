"""Tests for optics.cell_name()."""

import optics


def test_cell_name_zero_indexed():
    assert optics.cell_name(0, 0) == "row 1, column 1"


def test_cell_name_matches_solver_usage():
    # Matches the (3, 4) coordinate used in test_solver.py for a 5x5 board
    assert optics.cell_name(3, 4) == "row 4, column 5"


def test_cell_name_large_indices():
    # Edge case: large indices that can appear in out-of-bounds or debug messages
    assert optics.cell_name(99, 99) == "row 100, column 100"
