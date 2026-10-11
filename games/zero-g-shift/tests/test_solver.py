"""The solver: par, shortest lines, dead ends, and the move that broke a position."""

import pytest

import bays
import rules
import solver


def bay(rows, door=None):
    spec = {"id": "t", "rows": rows}
    if door:
        spec["door"] = door
    return rules.Bay(spec)


def test_par_line_and_count_on_a_one_move_bay():
    b = bay(["@.1.A", ".....", ".....", ".....", "....."])
    a = solver.Analysis(b)
    assert a.par == 1 and a.line_from(b.start) == "R" and a.optimal_count() == 1 and a.complete
    assert a.best_move(b.start) == "R" and a.all_optimal_lines() == ["R"]


def test_a_bay_that_cannot_be_cleared_has_no_par():
    b = bay(["@.1..", ".....", ".....", ".....", "A...."])
    a = solver.Analysis(b)
    assert a.par is None and a.line_from(b.start) is None and a.optimal_count() == 0 and a.distance(b.start) is None
    assert not a.can_win_all_ways() and a.dead_count() == a.size


def test_the_search_is_exhaustive_and_deterministic():
    b = bays.ALL_BAYS[0]
    a1, a2 = solver.Analysis(b), solver.Analysis(b)
    assert a1.states == a2.states and a1.edges == a2.edges and a1.dist == a2.dist
    assert a1.size == len(a1.index) == len(a1.edges)


def test_a_cap_is_reported_not_hidden():
    a = solver.Analysis(bays.ALL_BAYS[0], cap=5)
    assert a.size == 5 and a.complete is False


def test_the_stored_line_is_what_the_solver_finds_and_it_replays_to_a_clear():
    for b in bays.ALL_BAYS:
        a = solver.analysis(b)
        assert a.line_from(b.start) == b.line
        states, _infos = rules.replay(b, b.line)
        assert b.cleared(states[-1]) and not any(b.cleared(s) for s in states[:-1])


def _path_to(a, target):
    """The moves from the start to state number `target` (breadth-first, fixed order)."""
    parent = {0: None}
    queue = [0]
    for i in queue:
        for d, j in zip(solver.ORDER, a.edges[i]):
            if j >= 0 and j not in parent:
                parent[j] = (i, d)
                queue.append(j)
    line = []
    while parent[target] is not None:
        target, d = parent[target][0], parent[target][1]
        line.append(d)
    return "".join(reversed(line))


@pytest.mark.parametrize("b", bays.ALL_BAYS[:4], ids=lambda b: b.id)
def test_the_move_that_broke_a_position_is_the_first_one_that_cannot_be_undone(b):
    a = solver.analysis(b)
    dead = [i for i, d in enumerate(a.dist) if d < 0]
    assert dead, "every deck-one bay has at least one way to get stuck, or the warning means nothing"
    checked = 0
    for target in dead[:25]:
        line = _path_to(a, target)
        states = rules.replay(b, line)[0]
        first = next(k for k, s in enumerate(states) if a.distance(s) is None)
        assert solver.first_broken_move(b, line) == first
        checked += 1
    assert checked
    assert solver.first_broken_move(b, b.line) is None


def test_distance_counts_down_along_the_stored_line():
    b = bays.ALL_BAYS[3]
    a = solver.analysis(b)
    states, _ = rules.replay(b, b.line)
    assert [a.distance(s) for s in states] == list(range(len(b.line), -1, -1))


def test_optimal_count_matches_the_lines_it_lists():
    for b in bays.ALL_BAYS:
        a = solver.analysis(b)
        lines = a.all_optimal_lines(limit=50)
        assert len(lines) == a.optimal_count() and b.line in lines
        for line in lines:
            assert rules.replay(b, line) is not None and b.cleared(rules.replay(b, line)[0][-1])


def test_the_longest_slide_is_measured_over_every_reachable_move():
    b = bay(["@.1.A", ".....", ".....", ".....", "....."])
    a = solver.Analysis(b)
    assert a.longest_slide_available() >= 4
