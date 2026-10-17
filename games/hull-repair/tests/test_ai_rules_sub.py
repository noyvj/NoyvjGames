import boards
import rules


def test_subtracts_two_board_coordinates():
    b = boards.ALL_BOARDS[0]
    line = b.lines[0]
    c1 = b.src[line]
    c2 = b.dst[line]
    result = rules.sub(c1, c2)
    assert result == (c1[0] - c2[0], c1[1] - c2[1])


def test_subtracts_horizontal_delta():
    # Coordinates are (x, y) tuples. Subtracting two cells in the same row yields a negative x delta.
    c1 = (0, 0)
    c2 = (3, 0)
    assert rules.sub(c1, c2) == (-3, 0)


def test_subtracts_identical_coordinates():
    # Edge case: subtracting a coordinate from itself should yield zero.
    c = (5, 5)
    assert rules.sub(c, c) == (0, 0)
