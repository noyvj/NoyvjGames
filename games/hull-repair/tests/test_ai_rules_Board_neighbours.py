import rules


def mk(rows, mixers=None):
    spec = {"id": "t", "rows": rows}
    if mixers:
        spec["mixers"] = mixers
    return rules.Board(spec)


def test_neighbours_in_open_board():
    """A cell in the middle of an empty board has four neighbours."""
    b = mk(["A....", ".....", ".....", ".....", "....a"])
    assert len(b.neighbours((2, 2))) == 4


def test_neighbours_avoid_holes():
    """A cell adjacent to a hole has fewer than four neighbours."""
    b = mk(["A.#..", ".....", ".....", ".....", "....a"])
    # (2, 1) is adjacent to the hole at (2, 0), so it loses one neighbour
    assert len(b.neighbours((2, 1))) == 3


def test_neighbours_at_board_edge():
    """A cell on the corner of the board has two neighbours."""
    b = mk(["A....", ".....", ".....", ".....", "....a"])
    assert len(b.neighbours((0, 0))) == 2
