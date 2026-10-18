import rules


def mk(rows, mixers=None):
    spec = {"id": "t", "rows": rows}
    if mixers:
        spec["mixers"] = mixers
    return rules.Board(spec)


def test_one_line_connected_returns_its_letter():
    """A single line that reaches its sink is reported as connected."""
    b = mk(["Aa..", "....", "....", "...."])
    paths = {"A": [(0, 0), (1, 0)]}
    assert rules.connected_lines(b, paths) == ["A"]


def test_multiple_lines_connected_returns_all_in_order():
    """Several lines that each reach their respective sinks are all reported."""
    b = mk(["AB..", "ab..", "....", "...."])
    paths = {
        "A": [(0, 0), (0, 1)],
        "B": [(1, 0), (1, 1)]
    }
    assert rules.connected_lines(b, paths) == ["A", "B"]


def test_short_paths_are_not_connected():
    """A path with fewer than two cells cannot be connected."""
    b = mk(["A...", "...a", "....", "...."])
    paths = {"A": [(0, 0)]}
    assert rules.connected_lines(b, paths) == []
