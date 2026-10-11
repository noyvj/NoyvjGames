"""The slide rules, one rule at a time, on tiny hand-built bays."""

import pytest

import rules


def bay(rows, door=None):
    spec = {"id": "t", "rows": rows}
    if door:
        spec["door"] = door
    return rules.Bay(spec)


def state_of(b, you, crate_list):
    """A state by hand: you at (x, y); crate_list = [(kind, (x, y)), ...]."""
    return (you[1] * b.w + you[0], tuple(sorted(k << rules.SHIFT | (y * b.w + x) for k, (x, y) in crate_list)))


def xy(b, cell):
    return b.xy(cell)


def crates(b, state):
    return sorted((xy(b, c & rules.MASK), c >> rules.SHIFT) for c in state[1])


def play(b, line):
    got = rules.replay(b, line)
    assert got is not None, "a move in %r did nothing" % line
    return got[0][-1]


def test_you_slide_until_a_wall_and_a_move_against_it_does_nothing():
    b = bay(["@....", ".....", ".....", ".....", "..1.A"])
    s = play(b, "R")
    assert xy(b, s[0]) == (4, 0)
    assert rules.step(b, s, "R") is None and rules.step(b, s, "U") is None


def test_you_slide_over_pads_and_stop_at_the_wall_beyond():
    b = bay(["@....", ".....", ".....", ".....", "..1.A"])
    assert xy(b, play(b, "RD")[0]) == (4, 4)


def test_sliding_into_a_loose_crate_pushes_it_and_you_stay_where_you_were():
    b = bay([".....", ".....", "@.1..", ".....", "....A"])
    s, info = rules.step(b, b.start, "R")
    assert xy(b, s[0]) == (1, 2)                          # you stopped next to where the crate was
    assert crates(b, s) == [((4, 2), 0)]                  # it slid to the wall
    assert info["push"]["cells"] == 2 and info["cells"] == 1 and info["longest"] == 2


def test_a_crate_that_cannot_move_still_lets_you_arrive_beside_it():
    b = bay(["@.1#.", ".....", ".....", ".....", "A...."])
    s, info = rules.step(b, b.start, "R")
    assert xy(b, s[0]) == (1, 0) and info["push"] is None and info["cells"] == 1
    assert rules.step(b, s, "R") is None                  # now it really is stuck against the crate


def test_a_crate_never_pushes_another_crate():
    b = bay(["@.12.", ".....", ".....", ".....", "A...B"])
    s, info = rules.step(b, b.start, "R")
    assert info["push"] is None and xy(b, s[0]) == (1, 0)


def test_a_pushed_crate_stops_against_another_crate():
    b = bay(["@.1.2", ".....", ".....", ".....", "A...B"])
    s, info = rules.step(b, b.start, "R")
    assert info["push"]["cells"] == 1
    assert crates(b, s) == [((3, 0), 0), ((4, 0), 1)]


def test_a_pad_catches_its_own_kind_on_contact_and_the_crate_stays_there():
    b = bay(["@.1.A", ".....", ".....", ".....", "....."])
    s, info = rules.step(b, b.start, "R")
    assert crates(b, s) == [((4, 0), 0)] and info["push"]["docked"] and b.cleared(s)
    mid = bay(["@.1A.", ".....", ".....", ".....", "....."])
    s2, info2 = rules.step(mid, mid.start, "R")
    assert crates(mid, s2) == [((3, 0), 0)] and info2["push"]["cells"] == 1       # it stops ON the pad, not past it


def test_a_pad_of_another_kind_lets_a_crate_slide_over_it():
    b = bay(["@.1B.", ".....", ".....", "A....", "...2."])
    # crate 1 (kind A) at (2, 0); pad B at (3, 0) is not its kind; crate 2 (kind B) is the one that belongs on it
    s, info = rules.step(b, b.start, "R")
    assert info["push"]["docked"] is False and ((4, 0), 0) in crates(b, s)


def test_a_docked_crate_is_solid_to_you_and_to_other_crates():
    b = bay(["@..1A", ".....", ".....", ".....", "....."])
    s = state_of(b, (0, 0), [(0, (4, 0))])             # the only crate sits docked on its pad
    assert b.cleared(s)
    out = rules.step(b, s, "R")                          # you slide right and stop against it
    assert xy(b, out[0][0]) == (3, 0) and out[1]["push"] is None


def test_a_hatch_lets_a_crate_through_and_stops_you():
    b = bay(["@.1h.", ".....", ".....", ".....", "A...."])
    s, info = rules.step(b, b.start, "R")
    assert info["push"]["hatch"] and crates(b, s) == [((4, 0), 0)] and info["hatch"]
    assert xy(b, s[0]) == (1, 0)
    b2 = bay(["@.h..", ".....", ".....", ".....", "1...A"])
    s2, info2 = rules.step(b2, b2.start, "R")
    assert xy(b2, s2[0]) == (1, 0) and info2["cells"] == 1       # you stop before the hatch


def test_a_bumper_stops_you_on_it_and_crates_roll_over_it():
    b = bay(["@.b..", ".....", ".....", ".....", "1...A"])
    s, info = rules.step(b, b.start, "R")
    assert xy(b, s[0]) == (2, 0) and info["cells"] == 2
    s2, _ = rules.step(b, s, "R")                                # you can leave it
    assert xy(b, s2[0]) == (4, 0)
    b2 = bay(["@.1b.", ".....", ".....", ".....", "A...."])
    s3, _ = rules.step(b2, b2.start, "R")
    assert crates(b2, s3) == [((4, 0), 0)]


def test_a_shut_door_stops_you_and_a_crate():
    b = bay(["@.=..", ".....", ".....", "1....", "A...."], door="A")
    assert not b.door_open(b.start[1])
    s, _ = rules.step(b, b.start, "R")
    assert xy(b, s[0]) == (1, 0)
    c = bay(["@1=..", ".....", ".....", ".....", "A..2B"], door="A")
    assert rules.step(c, c.start, "R") is None                   # the crate is against the shut door: nothing moves


def test_the_door_opens_when_its_pads_are_full_and_you_and_crates_pass():
    b = bay(["@.=..", ".....", ".....", "1....", "A...."], door="A")
    s, info = rules.step(b, b.start, "D")
    assert info["opened"] and b.door_open(s[1]) and b.cleared(s)
    assert xy(b, play(b, "DUR")[0]) == (4, 0)                      # up, then right straight through the open door
    c = bay(["@.1=A", ".....", ".....", ".....", "B...2"], door="B")
    docked_b = state_of(c, (0, 0), [(0, (2, 0)), (1, (0, 4))])      # crate B docked on its pad: the door is open
    assert c.door_open(docked_b[1])
    out = rules.step(c, docked_b, "R")
    assert out[1]["push"]["to"] == 4 and out[1]["push"]["docked"]    # the crate slid through the open door onto pad A
    loose_b = state_of(c, (0, 0), [(0, (2, 0)), (1, (4, 4))])
    assert not c.door_open(loose_b[1])
    shut_s, shut_info = rules.step(c, loose_b, "R")
    assert shut_info["push"] is None and xy(c, shut_s[0]) == (1, 0)        # the crate waits at the shut door


def test_a_door_needs_every_pad_of_its_kind_full():
    b = bay(["@..=.", ".....", ".....", "1.1..", "A.A.."], door="A")
    one = state_of(b, (0, 0), [(0, (0, 4)), (0, (2, 3))])
    assert not b.door_open(one[1])
    two = state_of(b, (0, 0), [(0, (0, 4)), (0, (2, 4))])
    assert b.door_open(two[1]) and b.cleared(two)


def test_the_bay_is_clear_when_every_crate_is_docked():
    b = bay(["@.1.A", ".....", ".....", ".....", "....."])
    assert not b.cleared(b.start)
    assert b.cleared(play(b, "R")) and b.docked_count(play(b, "R")) == 1


@pytest.mark.parametrize("rows", [["@...", "...."], ["@....", ".....", ".....", ".....", "....."], ["@..1.", ".....", ".....", ".....", "....."],
                                  ["@.1.A", ".....", ".....", ".....", "...@."], ["@.1.A", "....", ".....", ".....", "....."]])
def test_a_bay_must_be_valid(rows):
    with pytest.raises(rules.BayError):
        bay(rows)


def test_crates_and_pads_must_match_in_number_and_kind():
    with pytest.raises(rules.BayError):
        bay(["@.1..", ".....", ".....", ".....", "....B"])
    with pytest.raises(rules.BayError):
        bay(["@.1=.", ".....", ".....", ".....", "....A"])           # a door without a door pad kind
    with pytest.raises(rules.BayError):
        bay(["@.1..", ".....", ".....", ".....", "....A"], door="A")  # a door pad kind without a door
    with pytest.raises(rules.BayError):
        bay(["@.1.?", ".....", ".....", ".....", "....A"])


def test_replay_refuses_a_line_with_a_move_that_does_nothing_or_is_not_a_move():
    b = bay(["@.1.A", ".....", ".....", ".....", "....."])
    assert rules.replay(b, "RRR") is None and rules.replay(b, "X") is None and rules.replay(b, 5) is None
    assert rules.replay(b, "R")[0][-1] == rules.replay(b, "R")[0][-1]
    assert rules.valid_line("UDLR") and not rules.valid_line("UX") and not rules.valid_line(None) and not rules.valid_line("U" * 501)


def test_words_describe_the_bay_and_the_move():
    b = bay(["@.1h.", ".....", "..o..", "b....", "A...."])
    text = " ".join(rules.describe(b, b.start))
    for needle in ("You are at column 1, row 1", "Circle crate A", "loose", "Dock pad A", "Hatch", "Bumper", "Post"):
        assert needle in text
    _s, info = rules.step(b, b.start, "R")
    assert "pushed the circle crate A right" in rules.move_words(info, b)
    assert rules.line_words("UDLR") == "up, down, left, right"


def test_a_state_is_canonical_so_matching_crates_are_interchangeable():
    b = bay(["@1.1.", ".....", ".....", ".....", "A...A"])
    assert b.start[1] == tuple(sorted(b.start[1]))
    assert len(b.pad_kind) == 2 and b.kinds_in_play == (0,)
