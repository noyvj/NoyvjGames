from board import Board


def test_in_grid_returns_false_for_shelf_index():
    """Test that in_grid returns False for the shelf index when shelf is enabled."""
    board = Board(5, 6, shelf=True)
    shelf_index = board.size  # shelf is at the end
    assert board.in_grid(shelf_index) is False


def test_in_grid_returns_false_for_invalid_indices():
    """Test that in_grid returns False for invalid indices (negative, out of bounds)."""
    board = Board(5, 6)
    assert board.in_grid(-1) is False     # negative index
    assert board.in_grid(34) is False     # beyond grid (34 is beyond 5x6=30 cells)
    assert board.in_grid(100) is False    # way out of bounds


def test_in_grid_returns_false_for_non_integer_inputs():
    """Test that in_grid returns False for non-integer inputs."""
    board = Board(5, 6)
    assert board.in_grid(3.14) is False   # float
    assert board.in_grid(True) is False   # boolean (treated as 1)
    assert board.in_grid(False) is False  # boolean (treated as 0)
