import pytest

from board import Board


def test_board_init_rejects_out_of_range_sizes():
    """Board.__init__ enforces MIN_SIDE (3) and MAX_SIDE (8)."""
    for size in range(1, 3):
        with pytest.raises(ValueError):
            Board(size, 5)
            Board(5, size)
    for size in range(9, 12):
        with pytest.raises(ValueError):
            Board(size, 5)
            Board(5, size)
    # Valid boundaries should not raise
    Board(3, 3)
    Board(8, 8)


def test_board_place_rejects_invalid_goods_and_indices():
    """Board.place raises on bad goods and returns None for out-of-bounds or occupied cells."""
    board = Board()
    with pytest.raises(ValueError):
        board.place("not a good")
    with pytest.raises(ValueError):
        board.place((None, 1))
    with pytest.raises(ValueError):
        board.place(("produce", 0))

    # Out of bounds returns None
    assert board.place(("produce", 1), at=-1) is None
    assert board.place(("produce", 1), at=100) is None

    # Occupied cell returns None
    board.place(("produce", 1))
    assert board.place(("textiles", 1), at=0) is None


def test_board_drop_handles_edge_cases():
    """Board.drop refuses same-cell drops, out-of-bounds indices, and non-mergeable pairs."""
    board = Board()
    board.place(("produce", 1), at=0)

    # Same cell drop
    assert board.drop(0, 0).ok is False

    # Out of bounds
    assert board.drop(-1, 0).ok is False
    assert board.drop(0, 100).ok is False

    # Empty cell drop (move) works fine
    result = board.drop(0, 1)
    assert result.ok and result.swapped is False

    # Non-mergeable drop swaps them
    board.place(("textiles", 1), at=2)
    result = board.drop(1, 2)
    assert result.ok and result.swapped is True


def test_board_sell_and_broom_on_invalid_or_empty_cells():
    """Board.sell returns None and Board.broom returns False when given invalid or empty indices."""
    board = Board()
    # Invalid index
    assert board.sell(-1) is None
    assert board.sell(999) is None
    assert board.broom(-1) is False
    assert board.broom(999) is False

    # Empty cell
    assert board.sell(0) is None
    assert board.broom(0) is False

    # Valid good works
    board.place(("produce", 1))
    assert board.sell(0) == 1
    board.place(("textiles", 1), at=1)
    assert board.broom(1) is True


def test_board_from_text_handles_empty_and_malformed_input():
    """Board.from_text defaults to standard size on empty input and parses short/malformed rows gracefully."""
    # Empty string defaults to DEFAULT_WIDTH x DEFAULT_HEIGHT (5x6)
    b = Board.from_text("")
    assert b.width == 5 and b.height == 6

    # Short row expands width to default
    b = Board.from_text("P1")
    assert b.width == 5 and b.height == 6

    # Missing rows are handled without crashing
    b = Board.from_text("P1\n\nT1")
    assert b.width == 5 and b.height == 6
