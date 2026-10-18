import rules


def mk(rows, mixers=None):
    spec = {"id": "t", "rows": rows}
    if mixers:
        spec["mixers"] = mixers
    return rules.Board(spec)


def test_valve_forward_delta_for_right_arrow():
    """Normal case: forward path on a right-pointing valve."""
    b = mk(["A..>a", ".....", ".....", "....."])
    assert b.valve_dir((3, 0), False) == (1, 0)


def test_valve_reversed_delta_for_down_arrow():
    """Normal case: reversed path on a down-pointing valve."""
    b = mk(["A..v.a", "......", "......", "......"])
    assert b.valve_dir((3, 0), True) == (0, -1)


def test_valve_index_wrap_around_on_left_arrow():
    """Edge case: '<' is index 3; reversed adds 2 -> 5 % 4 = 1."""
    b = mk(["A..<.a", "......", "......", "......"])
    assert b.valve_dir((3, 0), True) == (1, 0)
