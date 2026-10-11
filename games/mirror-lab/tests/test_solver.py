"""The placement solver: what a solution is, that it finds all of them, and that it ignores pieces no light reaches."""

import optics
import solve


def test_a_single_mirror_bench_has_one_solution():
    b = optics.Board(["....A", ".....", ".....", ">oooo", "....."])
    assert solve.solve(b, {"mirror": 1}) == [((3, 4, "mirror", 0),)]


def test_unreached_slots_are_never_decided_so_unused_pieces_are_not_counted_twice():
    # the second slot is far from the beam; a spare mirror there would change nothing and must not make a "different" solution
    b = optics.Board(["....A", ".....", "o....", ">oooo", "....."])
    sols = solve.solve(b, {"mirror": 2})
    assert sols == [((3, 4, "mirror", 0),)]


def test_every_solution_really_solves_and_nothing_is_missed_by_brute_force():
    import itertools
    b = optics.Board([">oo.", "....", "ooA."])
    tray = {"mirror": 2}
    found = {s for s in solve.solve(b, tray)}
    slots = sorted(b.slots)
    brute = set()
    options = [None] + [("mirror", 0), ("mirror", 1)]
    for combo in itertools.product(options, repeat=len(slots)):
        if sum(1 for x in combo if x) > 2:
            continue
        placed = {cell: x for cell, x in zip(slots, combo) if x}
        tr = optics.trace(b, placed)
        if tr.ok:
            # canonical: only pieces a beam reaches
            reached = {(r, c) for r, c, *_rest in tr.segments}
            if all(cell in reached for cell in placed):
                brute.add(tuple(sorted((r, c, p, s) for (r, c), (p, s) in placed.items())))
    assert found == brute and found


def test_the_solver_respects_the_tray():
    b = optics.Board([">o.", ".A.", "..."])
    assert solve.solve(b, {"mirror": 0}) == []
    assert solve.solve(b, {"mirror": 1}) == [((0, 1, "mirror", 1),)]


def test_solutions_are_sorted_fewest_first_and_the_search_is_deterministic():
    b = optics.Board([">ooA", "...."])
    a = solve.solve(b, {"mirror": 2, "splitter": 1})
    c = solve.solve(b, {"mirror": 2, "splitter": 1})
    assert a == c and [len(s) for s in a] == sorted(len(s) for s in a)


def test_the_limit_stops_early():
    b = optics.Board([">ooooA", "oooooo"])
    assert len(solve.solve(b, {"mirror": 2, "splitter": 2}, limit=1)) == 1
