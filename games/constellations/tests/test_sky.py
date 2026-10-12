"""The rules and the solvers on small hand-made charts, checked against brute force."""

import itertools

import pytest

import sky


def chart(points, edges, degree=(), must=(), never=()):
    data = {"stars": [{"x": x, "y": y} for x, y in points], "edges": [list(e) for e in edges],
            "clues": {"degree": dict(degree), "must": [list(e) for e in must], "never": [list(e) for e in never]}}
    return sky.Chart(data)


def brute_force(ch):
    """Every subset of the candidate lines, judged by analyse(): the definition of 'a valid figure'."""
    out = []
    for size in range(1, len(ch.edges) + 1):
        for subset in itertools.combinations(range(len(ch.edges)), size):
            if sky.analyse(ch, subset)["valid"]:
                out.append(frozenset(subset) | ch.must)
    return list(set(out))


SQUARE = [(0, 0), (100, 0), (100, 100), (0, 100)]
ALL_PAIRS = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]


def test_orientation_and_proper_crossing():
    assert sky.segments_touch((0, 0), (10, 10), (0, 10), (10, 0))
    assert not sky.segments_touch((0, 0), (10, 0), (0, 1), (10, 1))


def test_touching_and_collinear_overlap_count_as_conflicts():
    assert sky.segments_touch((0, 0), (10, 0), (10, 0), (20, 5))              # end meets end
    assert sky.segments_touch((0, 0), (10, 0), (5, 0), (5, 9))                # an end on the other's middle
    assert sky.segments_touch((0, 0), (10, 0), (5, 0), (15, 0))               # overlapping on one line
    assert not sky.segments_touch((0, 0), (10, 0), (11, 0), (20, 0))          # collinear but apart


def test_lines_that_share_a_star_do_not_conflict_unless_one_runs_along_the_other():
    pts = [(0, 0), (10, 0), (20, 0), (10, 10)]
    assert not sky.edges_conflict(pts, (0, 1), (1, 3))
    assert sky.edges_conflict(pts, (0, 1), (0, 2))                            # 0-2 passes through 1 and runs along 0-1
    assert not sky.edges_conflict(pts, (0, 1), (1, 2))                        # end to end, leaving in opposite ways
    assert not sky.edges_conflict(pts, (0, 1), (0, 1))


def test_crossing_diagonals_conflict_and_sides_do_not():
    ch = chart(SQUARE, ALL_PAIRS)
    a, b = ch.index[(0, 2)], ch.index[(1, 3)]
    assert ch.conflict[a] >> b & 1
    assert not ch.conflict[ch.index[(0, 1)]] >> ch.index[(2, 3)] & 1


def test_analyse_reports_numbers_crossings_and_pieces():
    ch = chart(SQUARE, ALL_PAIRS, degree={0: 2, 1: 2, 2: 2, 3: 2})
    ring = [ch.index[e] for e in [(0, 1), (1, 2), (2, 3), (0, 3)]]
    report = sky.analyse(ch, ring)
    assert report["valid"] and report["connected"] and report["parts"] == 1
    cross = [ch.index[(0, 2)], ch.index[(1, 3)]]
    r2 = sky.analyse(ch, cross)
    assert r2["crossings"] and not r2["valid"]
    r3 = sky.analyse(ch, ring[:2])
    assert r3["under"] == [0, 2, 3] and not r3["valid"]
    r4 = sky.analyse(ch, ring + [ch.index[(0, 2)]])
    assert 0 in r4["over"] and 2 in r4["over"]


def test_two_separate_pieces_are_not_one_figure():
    pts = [(0, 0), (10, 0), (100, 0), (110, 0)]
    ch = chart(pts, [(0, 1), (2, 3), (1, 2)], degree={0: 1, 1: 1, 2: 1, 3: 1})
    both = [ch.index[(0, 1)], ch.index[(2, 3)]]
    report = sky.analyse(ch, both)
    assert report["parts"] == 2 and not report["valid"]
    assert sky.solutions(ch, 5) == []                                          # numbers force two pieces, which is never one figure


def test_nothing_drawn_is_never_valid():
    ch = chart(SQUARE, ALL_PAIRS)
    assert not sky.is_valid(ch, [])


def test_must_lines_are_always_there_and_never_lines_may_not_be_used():
    ch = chart(SQUARE, ALL_PAIRS, degree={0: 1, 1: 2, 2: 2, 3: 1}, must=[(0, 1)], never=[(0, 3)])
    path = [ch.index[(1, 2)], ch.index[(2, 3)]]
    assert sky.analyse(ch, path)["valid"]                                      # the given 0-1 line is added by analyse
    assert sky.analyse(ch, [])["degree"][0] == 1
    bad = sky.analyse(ch, path + [ch.index[(0, 3)]])
    assert bad["never_used"] == [ch.index[(0, 3)]] and not bad["valid"]


@pytest.mark.parametrize("degree,must,never", [
    ({}, [], []),
    ({0: 2, 1: 2, 2: 2, 3: 2}, [], []),
    ({0: 1, 1: 1}, [], []),
    ({0: 3}, [], []),
    ({2: 0}, [], []),
    ({1: 2}, [(0, 1)], [(1, 2)]),
    ({0: 2, 3: 1}, [], [(0, 3)]),
])
def test_both_counters_and_brute_force_agree_on_a_square(degree, must, never):
    ch = chart(SQUARE, ALL_PAIRS, degree=degree, must=must, never=never)
    expect = brute_force(ch)
    assert set(sky.solutions(ch, 10 ** 6)) == set(expect)
    assert sky.count_by_stars(ch, 10 ** 6) == len(expect)


def test_counters_agree_on_a_pentagon_with_a_centre():
    pts = [(50, 0), (100, 40), (80, 100), (20, 100), (0, 40), (50, 50)]
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (0, 2), (1, 3)]
    for degree in ({}, {5: 0}, {0: 2, 1: 2, 2: 2, 3: 2, 4: 2}, {5: 3}, {5: 2, 0: 2}):
        ch = chart(pts, edges, degree=degree)
        expect = brute_force(ch)
        assert set(sky.solutions(ch, 10 ** 6)) == set(expect), degree
        assert sky.count_by_stars(ch, 10 ** 6) == len(expect), degree


def test_the_limit_stops_the_count_early():
    ch = chart(SQUARE, ALL_PAIRS)
    assert len(sky.solutions(ch, 3)) == 3
    assert sky.count_solutions(ch, 2) == 2


# ---- line logic -------------------------------------------------------------------------------------------------------
def test_full_forced_and_cross_rules():
    pts = [(0, 0), (100, 0), (100, 100), (0, 100)]
    ch = chart(pts, ALL_PAIRS, degree={0: 1, 1: 3, 2: 1, 3: 1})
    known, trail = sky.propagate(ch)
    rules = {t[0] for t in trail}
    assert "forced" in rules                                                   # star 1 needs all three of its lines
    assert known[ch.index[(0, 1)]] == sky.IN and known[ch.index[(1, 2)]] == sky.IN and known[ch.index[(1, 3)]] == sky.IN
    assert known[ch.index[(0, 2)]] == sky.OUT                                  # 0 has its one line already
    assert sky.solved_by_logic(ch) is not None


def test_propagate_never_contradicts_a_real_solution():
    pts = [(50, 0), (100, 40), (80, 100), (20, 100), (0, 40), (50, 50)]
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4), (0, 5), (1, 5), (2, 5), (3, 5), (4, 5), (0, 2), (1, 3)]
    for degree in ({0: 2, 1: 2, 2: 2, 3: 2, 4: 2}, {5: 3}, {5: 2, 0: 2}, {0: 3, 5: 2}):
        ch = chart(pts, edges, degree=degree)
        truth = sky.solutions(ch, 10 ** 6)
        for lookahead in (False, True):
            known, _ = sky.propagate(ch, lookahead=lookahead)
            if not truth:
                continue
            assert known is not None
            for sol in truth:
                for k, val in known.items():
                    assert (k in sol) == (val == sky.IN), (degree, lookahead)


def test_propagate_reports_a_contradiction_as_none():
    ch = chart(SQUARE, ALL_PAIRS, degree={0: 3, 1: 0, 2: 0, 3: 0})
    known, _ = sky.propagate(ch)
    assert known is None


def test_a_what_if_step_is_only_used_when_asked():
    ch = chart(SQUARE, ALL_PAIRS, degree={0: 2, 1: 2, 2: 2, 3: 2})
    plain, trail = sky.propagate(ch)
    assert all(t[0] != "what-if" for t in trail)
    _, trail2 = sky.propagate(ch, lookahead=True)
    assert all(t[0] in {"full", "forced", "cross", "close", "bridge", "what-if"} for t in trail2)


def test_the_bridge_rule_joins_two_halves_through_their_only_link():
    pts = [(0, 0), (50, 0), (100, 0), (150, 0)]
    pts = [(0, 0), (100, 0), (200, 10), (300, 0)]
    ch = chart(pts, [(0, 1), (1, 2), (2, 3), (0, 2)], degree={0: 1, 3: 1})
    known, trail = sky.propagate(ch)
    assert known[ch.index[(2, 3)]] == sky.IN
    assert any(t[0] == "bridge" for t in trail) or any(t[0] == "forced" for t in trail)


# ---- a chart that allows two lines to cross (the Southern Cross) -------------------------------------------------------
KITE = [(100, 400), (500, 100), (500, 800), (900, 500)]       # stars 0..3: left, top, bottom, right; the diagonals 0-3 and 1-2 cross


def cross_chart(allow=True, degree=None):
    data = {"stars": [{"x": x, "y": y} for x, y in KITE], "edges": [list(e) for e in ALL_PAIRS],
            "clues": {"degree": dict(degree if degree is not None else {0: 1, 1: 1, 2: 1, 3: 1}), "must": [], "never": []}}
    if allow:
        data["cross_ok"] = [[[0, 3], [1, 2]]]
    return sky.Chart(data)


def test_the_diagonals_of_the_kite_cross_but_only_a_listed_pair_may():
    plain, allowed = cross_chart(False), cross_chart(True)
    d1, d2 = plain.edge(0, 3), plain.edge(1, 2)
    assert plain.conflict[d1] >> d2 & 1
    assert not allowed.conflict[allowed.edge(0, 3)] >> allowed.edge(1, 2) & 1
    assert allowed.cross_ok == ((min(d1, d2), max(d1, d2)),)
    assert sky.analyse(plain, {d1, d2})["valid"] is False and sky.analyse(plain, {d1, d2})["crossings"]
    report = sky.analyse(allowed, {d1, d2})
    assert report["valid"] and report["parts"] == 1 and not report["crossings"]


def test_two_lines_that_cross_where_allowed_count_as_one_piece_and_two_that_do_not_cross_do_not():
    ch = cross_chart(True)
    sides = {ch.edge(0, 1), ch.edge(2, 3)}
    report = sky.analyse(ch, sides)
    assert report["parts"] == 2 and not report["valid"]
    assert sky.analyse(ch, {ch.edge(0, 3), ch.edge(1, 2)})["parts"] == 1


def test_the_solvers_agree_that_the_crossing_pair_is_the_only_figure():
    ch = cross_chart(True)
    found = sky.solutions(ch, 3)
    assert found == [frozenset({ch.edge(0, 3), ch.edge(1, 2)})]
    assert sky.count_by_stars(ch, 3) == 1
    assert brute_force(ch) == found
    assert sky.solutions(cross_chart(False), 3) == [] and sky.count_by_stars(cross_chart(False), 3) == 0


def test_line_logic_finishes_the_crossing_chart():
    ch = cross_chart(True)
    known, trail = sky.propagate(ch)
    assert {k for k, v in known.items() if v == sky.IN} == {ch.edge(0, 3), ch.edge(1, 2)}
    assert {r for r, _k, _v, _s in trail} >= {"close", "bridge"}
    assert sky.solved_by_logic(ch) == frozenset({ch.edge(0, 3), ch.edge(1, 2)})


def test_a_crossing_allowance_never_changes_a_chart_that_has_none():
    import charts
    for c in charts.ALL:
        assert ("cross_ok" in c) == (c["id"] == "crux")
        assert charts.rules(c["id"]).cross_ok == (() if c["id"] != "crux" else charts.rules("crux").cross_ok)
