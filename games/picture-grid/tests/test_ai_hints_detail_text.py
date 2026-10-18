"""Tests for the detail_text() function in hints.py."""

import hints

UNKNOWN, FILLED, EMPTY = hints.UNKNOWN, hints.FILLED, hints.EMPTY


def make_picture(rows_data):
    """Create a minimal picture object with computed clues."""
    pic = type('Picture', (), {})()
    pic.rows = rows_data
    pic.height = len(rows_data)
    pic.width = len(rows_data[0])
    r_clues, c_clues = hints.nonogram.clues_of(pic.rows)
    pic.row_clues = r_clues
    pic.col_clues = c_clues
    return pic


def test_detail_text_empty_clue():
    """Tests the 'empty' reasoning path when clue is 0."""
    pic = make_picture([[EMPTY] * 5])
    known = [UNKNOWN] * 5
    text = hints.detail_text(pic, "row", 0, known)
    assert "clue 0" in text
    assert "no filled cells" in text


def test_detail_text_complete_clue():
    """Tests the 'complete' reasoning path when all blocks are already placed."""
    rows = [[FILLED, FILLED, EMPTY, FILLED, EMPTY]]
    pic = make_picture(rows)
    known = [FILLED, FILLED, UNKNOWN, FILLED, UNKNOWN]
    text = hints.detail_text(pic, "row", 0, known)
    assert "clue 2 1" in text
    assert "every other cell" in text


def test_detail_text_overlap_clue():
    """Tests the 'overlap' reasoning path when there is spare room."""
    pic = type('Picture', (), {})()
    pic.rows = [[EMPTY] * 5]
    pic.height = 5
    pic.width = 5
    pic.row_clues = [[3]]
    pic.col_clues = [0] * 5
    known = [UNKNOWN] * 5
    text = hints.detail_text(pic, "row", 0, known)
    assert "clue 3" in text
    assert "spare cells" in text
