import rules


def mk(rows, mixers=None):
    spec = {"id": "t", "rows": rows}
    if mixers:
        spec["mixers"] = mixers
    return rules.Board(spec)


def test_adjacent_orthogonal_horizontal():
    """Two cells side-by-side are adjacent."""
    b = mk(["A...a", ".....", ".....", "....."])
    assert rules.adjacent(b.src["A"], (b.src["A"][0] + 1, b.src["A"][1])) is True


def test_adjacent_orthogonal_vertical():
    """Two cells one above the other are adjacent."""
    b = mk(["A...a", ".....", ".....", "....."])
    assert rules.adjacent(b.src["A"], (b.src["A"][0], b.src["A"][1] + 1)) is True


def test_adjacent_diagonal_edge_case():
    """Diagonally touching cells are not adjacent."""
    b = mk(["A...a", ".....", ".....", "....."])
    assert rules.adjacent(b.src["A"], (b.src["A"][0] + 1, b.src["A"][1] + 1)) is False
