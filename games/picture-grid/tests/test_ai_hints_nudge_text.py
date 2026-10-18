"""Tests for the nudge_text() function in hints.py."""

import hints


def test_nudge_text_row():
    """nudge_text() should format a row correctly."""
    assert hints.nudge_text("row", 0) == "Row 1 has a move that is certain. No guessing is needed there."


def test_nudge_text_column():
    """nudge_text() should format a column correctly."""
    assert hints.nudge_text("col", 4) == "Column 5 has a move that is certain. No guessing is needed there."


def test_nudge_text_edge_case_first_line():
    """nudge_text() handles index 0 correctly for both row and column."""
    assert hints.nudge_text("row", 0) == "Row 1 has a move that is certain. No guessing is needed there."
    assert hints.nudge_text("col", 0) == "Column 1 has a move that is certain. No guessing is needed there."
