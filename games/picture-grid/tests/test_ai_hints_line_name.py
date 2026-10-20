"""Tests for the line_name() function in hints.py."""

import hints


def test_line_name_returns_row_with_1_based_index():
    """Test that line_name returns 'Row X' for row kind with 1-based indexing."""
    assert hints.line_name("row", 0) == "Row 1"
    assert hints.line_name("row", 1) == "Row 2"
    assert hints.line_name("row", 4) == "Row 5"


def test_line_name_returns_column_with_1_based_index():
    """Test that line_name returns 'Column X' for column kind with 1-based indexing."""
    assert hints.line_name("col", 0) == "Column 1"
    assert hints.line_name("col", 2) == "Column 3"
    assert hints.line_name("col", 9) == "Column 10"


def test_line_name_edge_case_with_large_index():
    """Test line_name with a large index value."""
    assert hints.line_name("row", 99) == "Row 100"
    assert hints.line_name("col", 100) == "Column 101"
