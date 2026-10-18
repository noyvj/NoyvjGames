"""Tests for nonogram.grid_matches()."""


import nonogram as n
import pictures

ALL = pictures.ALL


def test_solved_grid_matches_its_clues():
    """A fully solved grid derived from a real picture should return True."""
    p = pictures.GALLERIES[0]["pictures"][0]
    grid = n.grid_of(p.rows)
    assert n.grid_matches(p.row_clues, p.col_clues, grid) is True


def test_modified_grid_fails_to_match():
    """Flipping one filled cell to empty in a solved grid should return False."""
    p = pictures.GALLERIES[0]["pictures"][0]
    grid = n.grid_of(p.rows)
    # Flip the first FILLED cell we find
    for r, row in enumerate(grid):
        for c, cell in enumerate(row):
            if cell == n.FILLED:
                grid[r][c] = n.EMPTY
                break
        else:
            continue
        break
    assert n.grid_matches(p.row_clues, p.col_clues, grid) is False


def test_all_empty_grid_does_not_match_nonzero_clues():
    """An all-EMPTY grid should return False when the clues require filled cells."""
    p = pictures.GALLERIES[0]["pictures"][0]
    height, width = len(p.rows), len(p.rows[0])
    empty_grid = [[n.EMPTY] * width for _ in range(height)]
    assert n.grid_matches(p.row_clues, p.col_clues, empty_grid) is False
