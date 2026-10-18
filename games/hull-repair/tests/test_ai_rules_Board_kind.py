import rules


def mk(rows, mixers=None):
    spec = {"id": "t", "rows": rows}
    if mixers:
        spec["mixers"] = mixers
    return rules.Board(spec)


def test_port_cell_returns_port():
    """A source or sink port cell should report 'port'."""
    b = mk(["A.....", ".....a", "......", "......"])
    assert b.kind(b.src["A"]) == "port"


def test_bridge_cell_returns_bridge():
    """A bridge cell should report 'bridge'."""
    b = mk(["A.....", "....=.", ".....a", "......"])
    bridge_cell = list(b.bridges)[0]
    assert b.kind(bridge_cell) == "bridge"


def test_open_cell_returns_open():
    """An empty floor cell should report 'open'."""
    b = mk(["A.....", ".....a", "......", "......"])
    open_cell = (2, 2)
    assert b.kind(open_cell) == "open"


def test_hole_cell_returns_hole():
    """A missing hull cell outside the playable area should report 'hole'."""
    b = mk(["A..#..", ".....a", "......", "......"])
    hole_cell = (3, 0)
    assert b.kind(hole_cell) == "hole"
