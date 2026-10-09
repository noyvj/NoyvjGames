import play
import rules

PLAIN = ["A...a", "B...b", ".....", ".....", "....."]
BR = ["..B..", "A.=.a", "..b..", ".....", "....."]
VA = ["A>..a", ".....", ".....", ".....", "....."]


def mk(rows, mixers=None):
    spec = {"id": "t", "rows": rows}
    if mixers:
        spec["mixers"] = mixers
    return rules.Board(spec)


def drag(d, cells):
    ok, msg = d.begin(cells[0])
    assert ok, msg
    results = [d.move(c) for c in cells[1:]]
    d.end()
    return results


def test_dragging_from_a_port_lays_a_line_and_counts_cells():
    d = play.Drawing(mk(PLAIN))
    drag(d, [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)])
    assert d.paths["A"] == [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)] and d.line_state("A") == "connected"
    assert d.take_counts() == (4, 0) and d.take_counts() == (0, 0)
    assert d.status() == rules.UNPATCHED


def test_you_can_start_from_the_sink_too():
    d = play.Drawing(mk(PLAIN))
    drag(d, [(4, 0), (3, 0), (2, 0), (1, 0), (0, 0)])
    assert d.line_state("A") == "connected" and d.paths["A"][0] == (4, 0)


def test_a_finished_line_refuses_to_grow_and_a_wrong_port_is_refused():
    d = play.Drawing(mk(PLAIN))
    r = drag(d, [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (4, 1)])
    assert r[-1][0] is False
    d2 = play.Drawing(mk(PLAIN))
    r = drag(d2, [(0, 0), (0, 1)])
    assert r[0][0] is False and "another line" in r[0][1]


def test_moves_must_be_to_a_neighbouring_playable_cell():
    d = play.Drawing(mk(["A.#.a", ".....", ".....", ".....", "....."]))
    r = drag(d, [(0, 0), (1, 0), (2, 0)])
    assert r[1] == (False, "That part of the hull is gone.")
    d.begin((0, 0))
    assert d.move((3, 3))[0] is False


def test_dragging_back_over_your_own_line_trims_it():
    d = play.Drawing(mk(PLAIN))
    drag(d, [(0, 0), (1, 0), (2, 0), (3, 0), (2, 0)])
    assert d.paths["A"] == [(0, 0), (1, 0), (2, 0)]
    assert d.take_counts() == (3, 1)


def test_dragging_into_another_line_cuts_it():
    d = play.Drawing(mk(PLAIN))
    drag(d, [(0, 1), (1, 1), (2, 1), (3, 1)])
    drag(d, [(0, 0), (1, 0), (1, 1)])
    assert "B" not in d.paths                           # cut back to its port: no line left
    assert (1, 1) in d.paths["A"] and (1, 1) not in d.paths.get("B", [])
    assert rules.check_layout(d.board, d.paths) == []


def test_tapping_the_end_of_a_line_takes_one_cell_back():
    d = play.Drawing(mk(PLAIN))
    drag(d, [(0, 0), (1, 0), (2, 0), (3, 0)])
    d.take_counts()
    d.begin((3, 0))
    d.end()
    assert d.paths["A"] == [(0, 0), (1, 0), (2, 0)] and d.take_counts() == (0, 1)


def test_tapping_the_far_port_of_a_joined_line_takes_one_cell_back():
    d = play.Drawing(mk(PLAIN))
    drag(d, [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)])
    d.begin((4, 0))
    d.end()
    assert d.paths["A"][-1] == (3, 0) and d.line_state("A") == "drawing"


def test_tapping_the_middle_of_a_line_cuts_it_back_to_there():
    d = play.Drawing(mk(PLAIN))
    drag(d, [(0, 0), (1, 0), (2, 0), (3, 0)])
    d.begin((1, 0))
    d.end()
    assert d.paths["A"] == [(0, 0), (1, 0)]


def test_a_fresh_drag_from_a_port_starts_that_line_over():
    d = play.Drawing(mk(PLAIN))
    drag(d, [(0, 0), (1, 0), (2, 0)])
    drag(d, [(0, 0), (0, 1)])         # (0,1) is B's port: refused, A restarted at its port only
    assert "A" not in d.paths
    drag(d, [(0, 0), (1, 0), (1, 1)])
    assert d.paths["A"] == [(0, 0), (1, 0), (1, 1)]


def test_a_touch_on_empty_floor_or_a_hole_picks_nothing_up():
    d = play.Drawing(mk(["A.#.a", "B...b", ".....", ".....", "....."]))
    assert d.begin((3, 3))[0] is False and d.begin((2, 0))[0] is False and d.drag is None


def test_undo_clear_and_clear_line():
    d = play.Drawing(mk(PLAIN))
    drag(d, [(0, 0), (1, 0), (2, 0)])
    drag(d, [(0, 1), (1, 1)])
    assert d.clear_line("A") and "A" not in d.paths and "B" in d.paths
    assert d.undo() and "A" in d.paths
    assert d.clear() and d.paths == {}
    assert d.undo() and set(d.paths) == {"A", "B"}
    assert d.undo() and set(d.paths) == {"A"} and d.undo() is True and d.undo() is False
    assert d.took_back


def test_a_bridge_only_goes_straight_and_two_lines_can_cross_it():
    d = play.Drawing(mk(BR))
    r = drag(d, [(0, 1), (1, 1), (2, 1), (2, 0)])
    assert r[-1][0] is False and "straight" in r[-1][1]
    d2 = play.Drawing(mk(BR))
    drag(d2, [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1)])
    drag(d2, [(2, 0), (2, 1), (2, 2)])
    assert d2.status() == rules.PATCHED and len(d2.paths["A"]) == 5
    assert rules.flags_of(d2.board, d2.paths) == ["bridge"]


def test_a_line_in_the_same_bridge_lane_cuts_the_other():
    b = mk(["A..a.", "B.=.b", ".....", ".....", "....."])
    d = play.Drawing(b)
    drag(d, [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1)])
    drag(d, [(0, 0), (1, 0), (1, 1), (2, 1), (3, 1), (3, 0)])
    assert d.paths["A"][-1] == (3, 0) and d.line_state("A") == "connected"
    assert d.line_state("B") == "empty" and "B" not in d.paths
    assert rules.check_layout(b, d.paths) == []


def test_a_valve_lets_the_line_through_only_its_way():
    d = play.Drawing(mk(VA))
    r = drag(d, [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)])
    assert all(x[0] for x in r) and d.status() == rules.PATCHED
    wrong = play.Drawing(mk(["A<..a", ".....", ".....", ".....", "....."]))
    r = drag(wrong, [(0, 0), (1, 0)])
    assert r[0][0] is False and "arrow" in r[0][1]
    from_sink = play.Drawing(mk(VA))
    r = drag(from_sink, [(4, 0), (3, 0), (2, 0), (1, 0), (0, 0)])
    assert all(x[0] for x in r) and from_sink.status() == rules.PATCHED
    sideways = play.Drawing(mk(["A..a.", ".v...", ".....", ".....", "....."]))
    r = drag(sideways, [(0, 0), (0, 1), (1, 1)])
    assert r[1][0] is False


def test_a_mixer_takes_both_named_lines_and_nothing_else():
    b = mk(["A.1.B", ".....", "..C.c", ".....", "....."], {"1": "AB"})
    d = play.Drawing(b)
    assert drag(d, [(0, 0), (1, 0), (2, 0)])[-1][0]
    assert drag(d, [(4, 0), (3, 0), (2, 0)])[-1][0]
    assert d.line_state("A") == "connected" and d.line_state("B") == "connected"
    d.begin((2, 0))
    assert d.drag is None
    other = play.Drawing(b)
    r = drag(other, [(2, 2), (2, 1), (2, 0)])
    assert r[-1][0] is False and "mixer" in r[-1][1]


def test_every_layout_the_drawing_makes_is_legal():
    d = play.Drawing(mk(PLAIN))
    for cells in ([(0, 0), (1, 0), (1, 1)], [(0, 1), (1, 1), (2, 1)], [(4, 1), (4, 2), (3, 2), (2, 2), (2, 1)], [(2, 1), (2, 0)]):
        d.begin(cells[0])
        for c in cells[1:]:
            d.move(c)
        d.end()
        assert rules.check_layout(d.board, d.paths) == []
