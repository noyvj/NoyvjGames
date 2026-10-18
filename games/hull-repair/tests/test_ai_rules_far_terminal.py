import rules


def mk(rows, mixers=None):
    spec = {"id": "t", "rows": rows}
    if mixers:
        spec["mixers"] = mixers
    return rules.Board(spec)


def test_far_terminal_returns_destination_when_path_starts_on_source():
    b = mk(["A.a.", "....", "....", "...."])
    path = [(0, 0), (1, 0)]
    assert rules.far_terminal(b, "A", path) == b.dst["A"]


def test_far_terminal_returns_source_when_path_starts_on_sink_port():
    # anchored_at matches the line letter regardless of case, so a path
    # starting on the sink port anchors to that line and returns the source.
    b = mk(["A.a.", "....", "....", "...."])
    path = [(2, 0), (1, 0)]
    assert rules.far_terminal(b, "A", path) == b.src["A"]


def test_far_terminal_returns_none_for_empty_path():
    b = mk(["A.a.", "....", "....", "...."])
    assert rules.far_terminal(b, "A", []) is None
