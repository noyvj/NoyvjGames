import rules


def mk(rows, mixers=None):
    spec = {"id": "t", "rows": rows}
    if mixers:
        spec["mixers"] = mixers
    return rules.Board(spec)


def test_path_starting_on_source_port_returns_src():
    """A path starting on the source port reports 'src'."""
    b = mk(["A...", "...a", "....", "...."])
    assert rules.anchored_at(b, "A", [(0, 0), (1, 0)]) == "src"


def test_path_starting_on_sink_port_returns_dst():
    """A path starting on the sink port reports 'dst'."""
    b = mk(["..a.", "A...", "....", "...."])
    assert rules.anchored_at(b, "A", [(2, 0), (1, 0)]) == "dst"


def test_empty_path_returns_none():
    """An empty path never starts on a port and returns None."""
    b = mk(["A...", "...a", "....", "...."])
    assert rules.anchored_at(b, "A", []) is None
