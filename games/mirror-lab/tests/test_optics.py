"""The ray tracer: the law of reflection on a table of cases, splitter, prism and filter geometry, loop cutting, bounds, determinism."""

import itertools

import optics

N, E, S, W = 0, 1, 2, 3
DELTA = {N: (-1, 0), E: (0, 1), S: (1, 0), W: (0, -1)}
EMITTER_CHAR = {N: "^", E: ">", S: "v", W: "<"}
LEFT_OF = {E: N, N: W, W: S, S: E}
RIGHT_OF = {E: S, S: W, W: N, N: E}


def board(rows):
    return optics.Board(rows)


def around(travel, sensors, centre="o"):
    """A 5 x 5 bench with a slot in the middle, an emitter two cells before it facing it, and the given sensor letters on the
    neighbours of the middle: `sensors` maps a compass direction to a board character."""
    rows = [list(".....") for _ in range(5)]
    rows[2][2] = centre
    dr, dc = DELTA[travel]
    rows[2 - 2 * dr][2 - 2 * dc] = EMITTER_CHAR[travel]
    for d, ch in sensors.items():
        rows[2 + DELTA[d][0]][2 + DELTA[d][1]] = ch
    return board(["".join(r) for r in rows])


def cell_toward(d):
    return (2 + DELTA[d][0], 2 + DELTA[d][1])


# ---- the law of reflection ---------------------------------------------------------------------------------------------
# A "/" mirror: a beam travelling east leaves north, north leaves east, west leaves south, south leaves west.
# A "\" mirror: east leaves south, south leaves east, west leaves north, north leaves west.
REFLECT = {("/", E): N, ("/", N): E, ("/", W): S, ("/", S): W, ("\\", E): S, ("\\", S): E, ("\\", W): N, ("\\", N): W}
STATE = {"/": 0, "\\": 1}


def test_law_of_reflection_table():
    for (kind, travel), expected in REFLECT.items():
        ahead, left, right = travel, LEFT_OF[travel], RIGHT_OF[travel]
        b = around(travel, {ahead: "A", left: "A", right: "A"})
        tr = optics.trace(b, {(2, 2): ("mirror", STATE[kind])})
        assert tr.lit == {cell_toward(expected)}, (kind, travel, expected, tr.lit)


def test_a_mirror_is_its_own_inverse():
    """Sending a beam back along a mirror's output returns it along the input: reflect(reflect(d)) comes back reversed."""
    for state in (0, 1):
        for d in (N, E, S, W):
            out = optics.mirror_out(state, d)
            back = optics.mirror_out(state, (out + 2) % 4)
            assert back == (d + 2) % 4


def test_a_mirror_keeps_the_beam_kind_and_turns_once():
    b = board([">o.", ".A.", "..."])
    tr = optics.trace(b, {(0, 1): ("mirror", 1)})
    assert {seg[4] for seg in tr.segments} == {"W"}
    assert tr.max_turns == 1 and tr.lit == {(1, 1)}


def test_two_reflections_make_a_parallel_path():
    b = board([".o..A.", "......", ">o...."])
    tr = optics.trace(b, {(2, 1): ("mirror", 0), (0, 1): ("mirror", 0)})
    assert tr.lit == {(0, 4)} and tr.ok and tr.max_turns == 2


# ---- walls, emitters, edges and sensors ---------------------------------------------------------------------------------
def test_walls_emitters_and_the_edge_stop_a_beam():
    assert not optics.trace(board([">.#.A"]), {}).lit
    assert optics.trace(board([">..A."]), {}).lit == {(0, 3)}
    assert (0, 4) not in optics.trace(board([">.<.A"]), {}).lit          # the second emitter blocks the first beam
    assert not optics.trace(board(["A.>"]), {}).lit                      # the beam leaves the board


def test_a_sensor_does_not_stop_the_beam():
    tr = optics.trace(board([">AAA"]), {})
    assert tr.lit == {(0, 1), (0, 2), (0, 3)} and tr.ok


def test_a_fixed_mirror_turns_the_beam():
    tr = optics.trace(board([">.\\", "..A", "..A"]), {})
    assert tr.lit == {(1, 2), (2, 2)}
    tr = optics.trace(board([">./", "..A"]), {})
    assert tr.lit == set()                                                # "/" sends an east beam north, off the board


def test_decoys_make_a_bench_unsolved_when_lit():
    b = board([">AX"])
    tr = optics.trace(b, {})
    assert tr.lit == {(0, 1)} and tr.dark_hit == {(0, 2)} and not tr.ok
    b = board([">AoX"])
    tr = optics.trace(b, {(0, 2): ("absorber", 0)})
    assert tr.ok and not tr.dark_hit


def test_sensor_kinds_need_their_own_beam():
    b = board([">S", ">L"])
    assert not optics.trace(b, {}).lit                                    # a white beam lights neither an S nor an L sensor
    assert optics.trace(board([">A"]), {}).ok


# ---- the splitter ------------------------------------------------------------------------------------------------------
def test_splitter_goes_straight_and_turns_left_for_every_direction():
    for travel in (N, E, S, W):
        b = around(travel, {travel: "A", LEFT_OF[travel]: "A", RIGHT_OF[travel]: "A"})
        tr = optics.trace(b, {(2, 2): ("splitter", 0)})
        assert tr.lit == {cell_toward(travel), cell_toward(LEFT_OF[travel])}, (travel, tr.lit)


# ---- the prism ---------------------------------------------------------------------------------------------------------
def test_prism_sends_the_short_beam_left_and_the_long_beam_right_in_state_zero_and_swaps_in_state_one():
    for travel in (N, E, S, W):
        for state in (0, 1):
            s_dir = LEFT_OF[travel] if state == 0 else RIGHT_OF[travel]
            l_dir = RIGHT_OF[travel] if state == 0 else LEFT_OF[travel]
            b = around(travel, {s_dir: "S", l_dir: "L"})
            tr = optics.trace(b, {(2, 2): ("prism", state)})
            assert tr.lit == set(b.required) and tr.ok, (travel, state)
            wrong = around(travel, {s_dir: "L", l_dir: "S"})
            assert not optics.trace(wrong, {(2, 2): ("prism", state)}).lit
            assert not optics.trace(b, {(2, 2): ("prism", 1 - state)}).lit


def test_a_prism_sends_nothing_straight_on():
    b = around(E, {E: "A"})
    assert not optics.trace(b, {(2, 2): ("prism", 0)}).lit


def test_a_short_or_long_beam_only_bends_and_does_not_split_again():
    b = board(["..o..", ".....", ">oo..", ".....", "..L.."])
    tr = optics.trace(b, {(2, 2): ("prism", 0), (0, 2): ("prism", 1)})
    out = [(do, k) for r, c, di, do, k, born in tr.segments if (r, c) == (0, 2) and do is not None]
    assert out == [(E, "S")]                                              # the S beam bends to its own side (right of north is east), once


# ---- absorbers and filters ---------------------------------------------------------------------------------------------
def test_absorber_stops_every_beam():
    b = board([">oA"])
    assert optics.trace(b, {(0, 1): ("absorber", 0)}).lit == set()
    assert optics.trace(b, {}).lit == {(0, 2)}


def test_a_filter_turns_white_into_its_kind_and_stops_the_other():
    b = board([">oS"])
    assert optics.trace(b, {(0, 1): ("filter_s", 0)}).lit == {(0, 2)}
    assert not optics.trace(b, {(0, 1): ("filter_l", 0)}).lit
    b = board([">ooL"])
    assert not optics.trace(b, {(0, 1): ("filter_l", 0), (0, 2): ("filter_s", 0)}).lit          # an L beam cannot pass an S filter
    assert optics.trace(b, {(0, 1): ("filter_l", 0), (0, 2): ("filter_l", 0)}).lit == {(0, 3)}


# ---- loops and bounds --------------------------------------------------------------------------------------------------
def ring_board():
    """A clockwise ring of fixed mirrors with a splitter slot on its left side, where the emitter's beam crosses it."""
    return board([
        ".......",
        "..o.A\\.",
        ".....A.",
        ">oo..A.",
        "..\\A./.",
        ".......",
    ])


def test_a_loop_of_mirrors_is_cut_and_the_trace_ends():
    b = ring_board()
    tr = optics.trace(b, {(1, 2): ("mirror", 0), (3, 2): ("splitter", 0)})
    assert tr.loops >= 1 and tr.ok
    bound = b.w * b.h * 4 * len(optics.KINDS)
    assert tr.states <= bound and len(tr.segments) <= 2 * bound


def test_beam_count_never_exceeds_the_bound_even_on_a_busy_board():
    rows = ["o" * 6 for _ in range(6)]
    rows[0] = ">" + "o" * 5
    b = board(rows)
    slots = sorted(b.slots)
    bound = b.w * b.h * 4 * len(optics.KINDS)
    for piece in ("splitter", "mirror", "prism"):
        for combo in itertools.islice(itertools.product(range(2), repeat=len(slots)), 0, 300):
            placed = {}
            for cell, flag in zip(slots, combo):
                if flag:
                    placed[cell] = (piece, 0 if piece == "splitter" else (cell[0] + cell[1]) % 2)
            tr = optics.trace(b, placed)
            assert tr.states <= bound


def test_tracing_is_deterministic_and_leaves_the_layout_alone():
    b = ring_board()
    placed = {(1, 2): ("mirror", 0), (3, 2): ("splitter", 0)}
    a, c = optics.trace(b, placed), optics.trace(b, placed)
    assert a.segments == c.segments and a.lit == c.lit and a.loops == c.loops and a.max_turns == c.max_turns
    assert placed == {(1, 2): ("mirror", 0), (3, 2): ("splitter", 0)}


def test_max_turns_counts_the_most_turns_on_one_beam():
    tr = optics.trace(board([">.\\", "..."]), {})
    assert tr.max_turns == 1
    b = board([">o.", "...", "oo."])
    tr = optics.trace(b, {(0, 1): ("mirror", 1), (2, 1): ("mirror", 0), (2, 0): ("mirror", 1)})
    assert tr.max_turns == 3


# ---- board parsing and layout checks ---------------------------------------------------------------------------------------
def test_bad_boards_are_refused():
    for rows in ([], ["..", "."], [">.", ".Z"], ["...", "..."], [">..", 5], [""]):
        try:
            optics.Board(rows)
        except ValueError:
            continue
        raise AssertionError(rows)


def test_layout_problems_are_named():
    b = board([">oo", "..."])
    tray = {"mirror": 1}
    assert optics.layout_problem(b, tray, {(0, 1): ("mirror", 0)}) is None
    assert "not a slot" in optics.layout_problem(b, tray, {(1, 1): ("mirror", 0)})
    assert "more mirror" in optics.layout_problem(b, tray, {(0, 1): ("mirror", 0), (0, 2): ("mirror", 1)})
    assert "bad state" in optics.layout_problem(b, tray, {(0, 1): ("mirror", 2)})
    assert "unknown piece" in optics.layout_problem(b, tray, {(0, 1): ("lens", 0)})
