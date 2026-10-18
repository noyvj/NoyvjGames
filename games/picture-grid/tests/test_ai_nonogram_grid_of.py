"""Tests for nonogram.grid_of()."""

import nonogram as n
import pictures


def test_grid_of_converts_a_real_picture_to_working_cells():
    """A real picture's rows are converted to FILLED/EMPTY correctly."""
    p = pictures.ALL[0]
    grid = n.grid_of(p.rows)
    assert len(grid) == p.height
    assert all(len(row) == p.width for row in grid)
    for r, row in enumerate(p.rows):
        for c, ch in enumerate(row):
            expected = n.FILLED if ch == "#" else n.EMPTY
            assert grid[r][c] == expected


def test_grid_of_converts_a_sparse_picture_correctly():
    """A sparse picture (few filled cells) maps dots and hashes accurately."""
    p = pictures.GALLERIES[1]["pictures"][0]  # Small Machines, first picture
    grid = n.grid_of(p.rows)
    for r, row in enumerate(p.rows):
        for c, ch in enumerate(row):
            expected = n.FILLED if ch == "#" else n.EMPTY
            assert grid[r][c] == expected


def test_grid_of_handles_a_single_cell_bitmap():
    """A 1x1 bitmap is converted to a single-element list."""
    filled_1x1 = ["#"]
    empty_1x1 = ["."]
    assert n.grid_of(filled_1x1) == [[n.FILLED]]
    assert n.grid_of(empty_1x1) == [[n.EMPTY]]
