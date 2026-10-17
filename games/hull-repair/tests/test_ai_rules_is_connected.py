import rules


def mk(rows, mixers=None):
    spec = {"id": "t", "rows": rows}
    if mixers:
        spec["mixers"] = mixers
    return rules.Board(spec)


def test_a_line_that_reaches_its_sink_is_connected():
    """Normal case: a complete path from source to sink."""
    b = mk(["A...a", ".....", ".....", ".....", "....."])
    path = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)]
    assert rules.is_connected(b, "A", path)


def test_a_line_that_stops_short_is_not_connected():
    """Normal case: a partial path that does not reach the sink."""
    b = mk(["A...a", ".....", ".....", ".....", "....."])
    path = [(0, 0), (1, 0), (2, 0)]
    assert not rules.is_connected(b, "A", path)


def test_a_path_too_short_is_never_connected():
    """Edge case: a path with fewer than two cells cannot be connected."""
    b = mk(["A...a", ".....", ".....", ".....", "....."])
    path = [(0, 0)]
    assert not rules.is_connected(b, "A", path)
