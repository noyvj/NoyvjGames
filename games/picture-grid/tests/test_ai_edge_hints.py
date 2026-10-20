"""Edge-case tests for hints.py public functions."""

import hints

UNKNOWN, FILLED, EMPTY = hints.UNKNOWN, hints.FILLED, hints.EMPTY


def test_clue_words_empty_and_boundary():
    """clue_words() should return '0' for empty input and format numbers correctly."""
    assert hints.clue_words([]) == "0"
    assert hints.clue_words([1]) == "1"
    assert hints.clue_words([1, 2, 3]) == "1 2 3"


def test_line_name_zero_and_large_index():
    """line_name() should format names correctly for boundary indices."""
    assert hints.line_name("row", 0) == "Row 1"
    assert hints.line_name("col", 99) == "Column 100"


def test_reasoning_empty_clue_and_all_filled():
    """reasoning() should return 'empty' for zero input and 'complete' when marks match clue."""
    cells = [UNKNOWN] * 5
    assert hints.reasoning([], cells) == "empty"

    clue = [2, 1]
    # A line of length 4: F F E F -> clue is 2, 1
    filled_cells = [FILLED, FILLED, EMPTY, FILLED]
    assert hints.reasoning(clue, filled_cells) == "complete"


def test_reasoning_all_unknown_exact_and_overlap():
    """reasoning() should distinguish 'exact' (no spare room) from 'overlap' (spare room exists)."""
    # Length 3 line, clue 3 -> exact
    assert hints.reasoning([3], [UNKNOWN, UNKNOWN, UNKNOWN]) == "exact"

    # Length 5 line, clue 1 -> overlap
    assert hints.reasoning([1], [UNKNOWN] * 5) == "overlap"


def test_cells_phrase_empty_single_and_consecutive():
    """cells_phrase() should handle empty input, single moves, and consecutive ranges."""
    assert hints.cells_phrase("row", []) == ""
    assert hints.cells_phrase("row", [(2, FILLED)]) == "filled column 3"
    assert hints.cells_phrase("row", [(0, FILLED), (1, FILLED), (2, FILLED), (5, EMPTY)]) == "filled columns 1 to 3, dotted column 6"


def test_fill_text_and_nudge_text_boundary_indices():
    """fill_text() and nudge_text() should format strings correctly for boundary indices."""
    moves = [(0, FILLED), (1, FILLED)]
    assert hints.fill_text("row", 0, moves) == "Row 1: filled columns 1 to 2."

    assert hints.nudge_text("col", 99) == "Column 100 has a move that is certain. No guessing is needed there."
