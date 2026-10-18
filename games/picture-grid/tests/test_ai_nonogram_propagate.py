"""Tests for nonogram.propagate().

propagate() repeats line logic on a grid until nothing changes, returning True if consistent and False on contradiction.
It modifies the grid in place."""


import nonogram as n
import pictures

# Use a real picture from the game data to build inputs
PICTURE = pictures.GALLERIES[0]["pictures"][0]
ROWS = PICTURE.row_clues
COLS = PICTURE.col_clues
SIZE = PICTURE.height


def test_propagate_on_blank_grid_returns_true_and_deduces_cells():
    """propagate() on a blank grid for a real picture should return True and fill in some cells."""
    grid = [[n.UNKNOWN] * SIZE for _ in range(SIZE)]
    original_unknowns = sum(1 for row in grid for cell in row if cell == n.UNKNOWN)
    result = n.propagate(ROWS, COLS, grid)
    assert result is True
    remaining_unknowns = sum(1 for row in grid for cell in row if cell == n.UNKNOWN)
    # It should have deduced at least one cell (or all if it's trivial)
    assert remaining_unknowns < original_unknowns or remaining_unknowns == 0


def test_propagate_on_partial_grid_returns_true():
    """propagate() on a partially filled grid that matches the picture should return True."""
    grid = [[n.UNKNOWN] * SIZE for _ in range(SIZE)]
    # Fill one cell known to be FILLED in the solution
    sol_grid, _ = n.solve_lines(ROWS, COLS)
    target = None
    for r in range(SIZE):
        for c in range(SIZE):
            if sol_grid[r][c] == n.FILLED:
                target = (r, c)
                break
        if target:
            break
    assert target is not None
    grid[target[0]][target[1]] = n.FILLED

    result = n.propagate(ROWS, COLS, grid)
    assert result is True


def test_propagate_on_contradictory_grid_returns_false():
    """propagate() on a grid with a contradiction should return False."""
    grid = [[n.UNKNOWN] * SIZE for _ in range(SIZE)]
    # Force a cell that must be EMPTY to FILLED
    sol_grid, _ = n.solve_lines(ROWS, COLS)
    target = None
    for r in range(SIZE):
        for c in range(SIZE):
            if sol_grid[r][c] == n.EMPTY:
                target = (r, c)
                break
        if target:
            break
    assert target is not None
    grid[target[0]][target[1]] = n.FILLED

    result = n.propagate(ROWS, COLS, grid)
    assert result is False
