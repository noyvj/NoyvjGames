import rules


def mk(rows, mixers=None):
    spec = {"id": "t", "rows": rows}
    if mixers:
        spec["mixers"] = mixers
    return rules.Board(spec)


def test_covered_returns_cells_from_a_single_line():
    """A single line covers exactly its cells."""
    b = mk(["A.a.", "....", "....", "...."])
    paths = {"A": [(0, 0), (1, 0)]}
    assert rules.covered(b, paths) == {(0, 0), (1, 0)}


def test_covered_with_empty_paths_returns_empty_set():
    """No lines means no covered cells."""
    b = mk(["A.a.", "....", "....", "...."])
    assert rules.covered(b, {}) == set()
