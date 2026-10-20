from board import Board


def test_merged_good_returns_none_for_invalid_indices():
    """Test that merged_good returns None for invalid indices."""
    board = Board()
    assert board.merged_good(-1, 0) is None
    assert board.merged_good(100, 0) is None
    assert board.merged_good(0, 100) is None


def test_merged_good_returns_none_for_same_cell():
    """Test that merged_good returns None when both indices are the same."""
    board = Board()
    assert board.merged_good(0, 0) is None


def test_merged_good_returns_none_for_empty_cells():
    """Test that merged_good returns None when either cell is empty."""
    board = Board()
    board.place(("produce", 1), at=0)
    assert board.merged_good(0, 1) is None
    assert board.merged_good(1, 0) is None


def test_merged_good_merges_identical_goods():
    """Test that merged_good returns the next tier for identical goods."""
    board = Board()
    board.place(("produce", 1), at=0)
    board.place(("produce", 1), at=1)
    assert board.merged_good(0, 1) == ("produce", 2)
    assert board.merged_good(1, 0) == ("produce", 2)


def test_merged_good_returns_none_for_different_goods():
    """Test that merged_good returns None for different goods."""
    board = Board()
    board.place(("produce", 1), at=0)
    board.place(("textiles", 1), at=1)
    assert board.merged_good(0, 1) is None


def test_merged_good_returns_none_for_showpieces():
    """Test that merged_good returns None for tier 5 (showpiece) goods."""
    board = Board()
    board.place(("produce", 5), at=0)
    board.place(("produce", 5), at=1)
    assert board.merged_good(0, 1) is None


def test_merged_good_handles_wildcards():
    """Test that merged_good handles wildcards correctly."""
    board = Board()
    board.place(("wild", 1), at=0)
    board.place(("produce", 1), at=1)
    assert board.merged_good(0, 1) == ("produce", 2)
    assert board.merged_good(1, 0) == ("produce", 2)


def test_merged_good_returns_none_for_two_wildcards():
    """Test that merged_good returns None for two wildcards."""
    board = Board()
    board.place(("wild", 1), at=0)
    board.place(("wild", 1), at=1)
    assert board.merged_good(0, 1) is None


def test_merged_good_with_wildcard_and_showpiece():
    """Test that merged_good returns None for wildcard with showpiece."""
    board = Board()
    board.place(("wild", 1), at=0)
    board.place(("produce", 5), at=1)
    assert board.merged_good(0, 1) is None
