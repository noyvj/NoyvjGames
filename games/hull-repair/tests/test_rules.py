import pytest

import rules

PLAIN = ["A...a", ".....", ".....", ".....", "....."]


def board(rows, mixers=None, bid="t"):
    spec = {"id": bid, "rows": rows}
    if mixers:
        spec["mixers"] = mixers
    return rules.Board(spec)


BRIDGE = ["..B..", "A.=.a", "..b..", ".....", "....."]
VALVE_R = ["A>..a", ".....", ".....", ".....", "....."]
MIXER = ["A.1.B", ".....", ".....", ".....", "....."]
ROW = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)]


def test_a_board_is_parsed_into_its_parts():
    b = board(["C.#=c", "A.1.B", ".....", ".....", "....."], {"1": "AB"})
    assert b.holes == {(2, 0)} and b.bridges == {(3, 0)} and b.lines == ("A", "B", "C")
    assert b.src["C"] == (0, 0) and b.dst["C"] == (4, 0) and b.dst["B"] == (2, 1) and b.mixers == {(2, 1): ("A", "B")}
    assert b.twists == ("holes", "bridges", "mixers") and (2, 0) not in b.playable and (2, 1) not in b.need


@pytest.mark.parametrize("rows,mixers", [
    (["A...a"] * 3, None),                                   # too small
    (["A...a", "....", ".....", ".....", "....."], None),    # ragged
    (["A....", ".....", ".....", ".....", "....."], None),   # a source with no sink
    (["A...a", ".....", ".....", ".....", "....a"], None),   # two sinks
    (["A...a", "....?", ".....", ".....", "....."], None),   # unknown cell
    (["A.1.a", ".....", ".....", ".....", "....."], {"1": "AB"}),   # mixer names a missing line
    (["A.1.B", ".....", ".....", ".....", "....."], None),   # a mixer with no lines
])
def test_bad_boards_are_refused(rows, mixers):
    with pytest.raises(ValueError):
        board(rows, mixers)


def test_a_straight_line_patches_and_does_not_restore():
    b = board(PLAIN)
    paths = {"A": ROW}
    assert rules.check_layout(b, paths) == [] and rules.status(b, paths) == rules.PATCHED
    assert len(rules.uncovered(b, paths)) == 20


def test_a_line_may_start_on_its_sink_and_still_count():
    b = board(PLAIN)
    assert rules.status(b, {"A": list(reversed(ROW))}) == rules.PATCHED
    assert rules.oriented(b, "A", list(reversed(ROW))) == ROW


def test_a_partial_line_is_legal_but_not_a_patch():
    b = board(PLAIN)
    assert rules.check_layout(b, {"A": ROW[:3]}) == [] and rules.status(b, {"A": ROW[:3]}) == rules.UNPATCHED


def test_restored_needs_every_open_cell():
    b = board(["A..a", "....", "....", "...."], bid="s")
    snake = [(0, 0), (0, 1), (0, 2), (0, 3), (1, 3), (1, 2), (1, 1), (1, 0), (2, 0), (2, 1), (2, 2), (2, 3), (3, 3), (3, 2), (3, 1), (3, 0)]
    assert rules.status(b, {"A": snake}) == rules.RESTORED


@pytest.mark.parametrize("paths", [
    {"A": [(1, 0), (2, 0)]},                                   # starts off a port
    {"A": [(0, 0), (2, 0)]},                                   # jumps
    {"A": [(0, 0), (1, 0), (0, 0)]},                           # repeats a cell
    {"A": [(0, 0), (1, 0), (1, 0)]},
    {"A": [(0, 0), (1, 0), (5, 0)]},                           # off the board
    {"Z": [(0, 0), (1, 0)]},                                   # no such line
])
def test_illegal_layouts_are_listed(paths):
    assert rules.check_layout(board(PLAIN), paths)


def test_lines_may_not_share_a_cell_or_enter_each_others_ports():
    b = board(["A...a", "B...b", ".....", ".....", "....."])
    assert rules.check_layout(b, {"A": [(0, 0), (1, 0), (1, 1)], "B": [(0, 1), (1, 1)]})
    assert rules.check_layout(b, {"A": [(0, 0), (0, 1)]})
    assert rules.check_layout(b, {"A": [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (4, 1)]})


def test_holes_block_a_line():
    b = board(["A.#.a", ".....", ".....", ".....", "....."])
    assert rules.check_layout(b, {"A": [(0, 0), (1, 0), (2, 0)]})


def test_a_bridge_carries_two_lines_but_only_straight():
    b = board(BRIDGE)
    cross = {"A": [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1)], "B": [(2, 0), (2, 1), (2, 2)]}
    assert rules.check_layout(b, cross) == [] and rules.status(b, cross) == rules.PATCHED
    assert rules.flags_of(b, cross) == ["bridge"]
    assert rules.check_layout(b, {"A": [(0, 1), (1, 1), (2, 1), (2, 0)]})                  # turned on the bridge
    other = board(["A...a", "..=..", ".....", "..B..", "..b.."], bid="o")
    two_flat = {"A": [(0, 0), (1, 0), (1, 1), (2, 1), (3, 1), (4, 1), (4, 0)]}
    assert rules.check_layout(other, two_flat) == []
    same_lane = {"A": [(0, 0), (1, 0), (1, 1), (2, 1), (3, 1), (4, 1), (4, 0)], "B": [(2, 3), (1, 3), (1, 2), (1, 1)]}
    assert rules.check_layout(other, same_lane)


def test_two_lines_in_one_bridge_lane_collide():
    b = board(["A..a.", "B.=.b", ".....", ".....", "....."], bid="l")
    both = {"A": [(0, 0), (0, 1)]}
    assert rules.check_layout(b, both)         # a port is not a cell to run through
    one = {"A": [(0, 0), (1, 0), (1, 1), (2, 1), (3, 1), (3, 0)]}
    assert rules.check_layout(b, one) == []
    two = dict(one, B=[(0, 1), (1, 1)])
    assert rules.check_layout(b, two)


def test_a_valve_only_lets_a_line_through_the_way_it_points():
    b = board(VALVE_R)
    assert rules.check_layout(b, {"A": ROW}) == []
    assert rules.check_layout(b, {"A": list(reversed(ROW))}) == []              # started on the sink: reversed reading is the same flow
    wrong = board(["A<..a", ".....", ".....", ".....", "....."], bid="w")
    assert rules.check_layout(wrong, {"A": ROW})
    assert rules.flags_of(b, {"A": ROW}) == ["valve"]
    bent = {"A": [(0, 0), (1, 0), (1, 1)]}
    assert rules.check_layout(b, bent)


def test_a_valve_is_a_cell_a_restored_board_must_cover():
    b = board(VALVE_R)
    assert (1, 0) in b.need


def test_a_mixer_takes_two_named_lines_from_different_sides():
    b = board(MIXER, {"1": "AB"})
    both = {"A": [(0, 0), (1, 0), (2, 0)], "B": [(4, 0), (3, 0), (2, 0)]}
    assert rules.check_layout(b, both) == [] and rules.status(b, both) == rules.PATCHED
    assert rules.flags_of(b, both) == ["mix"]
    assert rules.check_layout(b, {"A": [(0, 0), (1, 0), (2, 0), (3, 0)]})       # through the mixer
    assert rules.check_layout(b, {"A": [(0, 0), (1, 0), (2, 0)], "B": [(4, 0), (4, 1), (3, 1), (2, 1), (2, 0)]}) == []
    other = board(["A.1.B", ".....", "..C.c", ".....", "....."], {"1": "AB"}, "m")
    assert rules.check_layout(other, {"C": [(2, 2), (2, 1), (2, 0)]})            # a line that is not in the mixer


def test_encode_and_decode_round_trip_and_refuse_junk():
    b = board(BRIDGE)
    cross = {"A": [(0, 1), (1, 1), (2, 1), (3, 1), (4, 1)], "B": [(2, 0), (2, 1), (2, 2)]}
    text = rules.encode(cross)
    assert text == "A0111213141;B202122"
    assert rules.decode(b, text) == cross
    for junk in ("A0x1", "Z0102", "A0111;A0111", None, 5, "A" + "01" * 1500, "A0105", "A0111213141;B202122;", "A011"):
        assert rules.decode(b, junk) is None, junk
    assert rules.decode(b, "") == {}
