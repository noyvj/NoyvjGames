"""Tests for the candidates() function in hints.py."""

import nonogram
import hints

UNKNOWN, FILLED, EMPTY = nonogram.UNKNOWN, nonogram.FILLED, nonogram.EMPTY


class MockPicture:
    """Minimal mock matching the Picture interface needed by hints.knowledge and hints.candidates."""

    def __init__(self, rows):
        self.rows = rows
        self.height = len(rows)
        self.width = len(rows[0])
        self.row_clues = [nonogram.line_clue(r) for r in rows]
        self.col_clues = nonogram.clues_of(rows)[1]

    def solution_grid(self):
        return [[FILLED if cell == 1 else EMPTY for cell in row] for row in self.rows]


def test_candidates_finds_row_deduction():
    """candidates() should return a candidate when a row has certain cells to fill."""
    pic = MockPicture([
        [1, 1, 0],
        [1, 0, 1],
        [0, 0, 0]
    ])
    grid = [[UNKNOWN] * 3 for _ in range(3)]

    cands = hints.candidates(pic, grid)

    assert len(cands) > 0
    row_cand = next((c for c in cands if c["kind"] == "row" and c["index"] == 0), None)
    assert row_cand is not None
    moves = row_cand["moves"]
    # For clue [2] on a 3-cell line, only the middle cell is certain.
    assert (1, FILLED) in moves


def test_candidates_finds_column_deduction():
    """candidates() should return a candidate when a column has certain cells to fill."""
    pic = MockPicture([
        [1, 0, 0],
        [1, 0, 0],
        [1, 0, 0]
    ])
    grid = [[UNKNOWN] * 3 for _ in range(3)]

    cands = hints.candidates(pic, grid)

    col_cand = next((c for c in cands if c["kind"] == "col" and c["index"] == 0), None)
    assert col_cand is not None
    moves = col_cand["moves"]
    assert (0, FILLED) in moves
    assert (1, FILLED) in moves
    assert (2, FILLED) in moves


def test_candidates_returns_empty_when_nothing_certain():
    """candidates() should return an empty list when no line has a certain move."""
    pic = MockPicture([
        [1, 0],
        [0, 1]
    ])
    grid = [[UNKNOWN] * 2 for _ in range(2)]

    cands = hints.candidates(pic, grid)

    assert cands == []
