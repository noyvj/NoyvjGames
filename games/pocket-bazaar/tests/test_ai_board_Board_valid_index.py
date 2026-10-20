from board import Board


def test_valid_index_accepts_normal_grid_indices():
    """Normal case: indices within the default 5x6 grid (0..29) are valid."""
    b = Board()
    for i in range(30):
        assert b.valid_index(i) is True


def test_valid_index_rejects_out_of_bounds_and_negative():
    """Edge case: indices outside the board or negative are invalid."""
    b = Board()
    assert b.valid_index(-1) is False
    assert b.valid_index(30) is False


def test_valid_index_rejects_booleans():
    """Edge case: booleans must not be treated as integers."""
    b = Board()
    assert b.valid_index(True) is False
    assert b.valid_index(False) is False
