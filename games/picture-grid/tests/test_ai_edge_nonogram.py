"""Edge-case tests for nonogram.py public functions."""


import nonogram as n
import pictures


def test_bitmap_ok_rejects_empty_and_invalid():
    """bitmap_ok should return False for empty lists, wrong widths, and invalid characters."""
    assert not n.bitmap_ok([])
    assert not n.bitmap_ok([[]])
    assert not n.bitmap_ok(["#", ".."])   # jagged rows
    assert not n.bitmap_ok(["#?", ".#"])  # invalid char
    assert not n.bitmap_ok(["##", "#"])   # different widths


def test_bitmap_ok_accepts_valid_rectangles():
    """bitmap_ok should return True for valid non-empty rectangles of '#' and '.'."""
    assert n.bitmap_ok(["#"])
    assert n.bitmap_ok([".", "."])
    assert n.bitmap_ok(["#.", ".#"])
    # Use a real picture from the game data
    p = pictures.BY_ID["hammer"]
    assert n.bitmap_ok(p.rows)


def test_line_clue_handles_edge_cases():
    """line_clue should return correct block lengths for empty, full, and mixed lines."""
    assert n.line_clue([]) == []
    assert n.line_clue([".", ".", "."]) == []
    assert n.line_clue(["#", "#", "#"]) == [3]
    assert n.line_clue(["#", ".", "#"]) == [1, 1]
    # Test with integers/booleans as the docstring mentions
    assert n.line_clue([True, False, True]) == [1, 1]
    assert n.line_clue([1, 0, 1]) == [1, 1]


def test_blank_grid_produces_correct_unknowns():
    """blank_grid should return a grid of UNKNOWN cells with the given dimensions."""
    grid = n.blank_grid(3, 4)
    assert len(grid) == 3
    for row in grid:
        assert len(row) == 4
        assert all(cell == n.UNKNOWN for cell in row)
    # Zero dimensions should still work without crashing
    empty = n.blank_grid(0, 0)
    assert empty == []


def test_solve_lines_handles_contradiction_and_complete():
    """solve_lines should return solved=False for contradictions and True for complete grids."""
    # Contradiction: rows want all filled, cols want only one filled per column
    _, solved = n.solve_lines([[2], [2]], [[1], [1]])
    assert not solved

    # Complete grid (all FILLED)
    complete = [[n.FILLED, n.FILLED], [n.FILLED, n.FILLED]]
    _, solved2 = n.solve_lines([[2], [2]], [[2], [2]], complete)
    assert solved2


def test_count_solutions_respects_limit():
    """count_solutions should stop counting once limit is reached and return at least limit."""
    # A 2x2 grid with clues [1] for all rows and cols has exactly 2 solutions.
    count = n.count_solutions([[1], [1]], [[1], [1]], limit=1)
    assert count == 1  # reached limit early

    # Use a real picture from the game data (exactly 1 solution)
    p = pictures.BY_ID["hammer"]
    assert n.count_solutions(p.row_clues, p.col_clues, limit=2) == 1


def test_line_deductions_handles_fully_known_lines():
    """line_deductions should return an empty list when all cells are already known."""
    clue = [2]
    cells = [n.FILLED, n.FILLED]
    assert n.line_deductions(clue, cells) == []

    # Contradiction in line
    contradiction_cells = [n.EMPTY, n.FILLED]
    assert n.line_deductions([2], contradiction_cells) is None
