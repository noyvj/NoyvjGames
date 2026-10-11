"""The nonogram maths: clues, one line, the line-logic solver and the two exhaustive counters."""

import itertools
import random

import nonogram as n

U, F, E = n.UNKNOWN, n.FILLED, n.EMPTY


def test_a_line_clue_lists_the_runs_left_to_right():
    assert n.line_clue("##.#.") == [2, 1]
    assert n.line_clue("#####") == [5]
    assert n.line_clue(".....") == []
    assert n.line_clue([1, 0, 1, 1]) == [1, 2]
    assert n.line_clue([True, True, False, True]) == [2, 1]


def test_clues_are_a_pure_function_of_the_picture():
    pic = ["##..", ".#..", "..##"]
    rows, cols = n.clues_of(pic)
    assert rows == [[2], [1], [2]] and cols == [[1], [2], [1], [1]]
    assert n.clues_of(pic) == (rows, cols)
    assert n.clues_of(tuple(pic)) == (rows, cols)


def test_bitmap_validation():
    assert n.bitmap_ok(["#.", ".#"]) and n.bitmap_ok(("#",))
    for bad in ([], ["#.", "#"], ["#x"], [".#", 5], "##", None, [""]):
        assert not n.bitmap_ok(bad), bad


def test_row_arrangements_are_every_way_to_lay_the_blocks():
    assert sorted(n.row_arrangements([1, 1], 4)) == [(0, 1, 0, 1), (1, 0, 0, 1), (1, 0, 1, 0)]
    assert n.row_arrangements([], 3) == [(0, 0, 0)]
    assert n.row_arrangements([3], 3) == [(1, 1, 1)]
    assert n.row_arrangements([2, 2], 4) == []
    assert len(n.row_arrangements([2, 1], 6)) == 6          # the blocks and their gap take 4 cells, 2 are spare: C(4, 2) = 6


def test_line_options_find_the_forced_cells():
    # a block of 4 in a line of 5 forces the middle three; the ends are open
    found = n.line_deductions([4], [U] * 5)
    assert found == [(1, F), (2, F), (3, F)]
    # a full line is forced completely
    assert n.line_deductions([2, 1, 1], [U] * 6) == [(0, F), (1, F), (2, E), (3, F), (4, E), (5, F)]
    # an empty clue forces everything empty
    assert n.line_deductions([], [U] * 3) == [(0, E), (1, E), (2, E)]
    # known cells are used: a filled end pins the block against it
    assert n.line_deductions([2], [F, U, U, U]) == [(1, F), (2, E), (3, E)]


def test_a_contradiction_is_reported_not_guessed_over():
    assert n.line_options([3], [F, E, F, U]) is None
    assert n.line_deductions([2, 2], [U, U, U, U]) is None
    assert n.line_options([1], [F, U, F]) is None
    assert n.line_options([], [U, F]) is None


def test_line_options_agree_with_plain_enumeration_on_every_short_line():
    """For every clue and every pattern of known cells in a line of 6, the forced cells match brute force."""
    width = 6
    clues = [[], [1], [2], [1, 1], [3], [2, 1], [1, 2], [1, 1, 1], [4], [2, 2]]
    for clue in clues:
        arrangements = n.row_arrangements(clue, width)
        for cells in itertools.product((U, F, E), repeat=width):
            fits = [a for a in arrangements if all(c == U or (c == F) == bool(v) for c, v in zip(cells, a))]
            options = n.line_options(clue, list(cells))
            if not fits:
                assert options is None, (clue, cells)
                continue
            can_fill, can_empty = options
            for i in range(width):
                assert bool(can_fill >> i & 1) == any(a[i] for a in fits), (clue, cells, i)
                assert bool(can_empty >> i & 1) == any(not a[i] for a in fits), (clue, cells, i)


def test_the_line_solver_finishes_an_easy_picture_and_never_guesses():
    pic = [".###.", ".###.", "..#..", "..#..", "..#.."]
    rows, cols = n.clues_of(pic)
    grid, solved = n.solve_lines(rows, cols)
    assert solved and n.bitmap_of(grid) == pic
    # every cell of the finished grid is decided
    assert n.count_of_unknown(grid) == 0


def test_a_picture_with_two_solutions_stops_the_line_solver_short():
    # a 2 by 2 ring of switches: the diagonal can go either way
    rows, cols = [[1], [1]], [[1], [1]]
    grid, solved = n.solve_lines(rows, cols)
    assert not solved and n.count_of_unknown(grid) == 4
    assert n.count_solutions(rows, cols, 5) == 2 and n.count_by_rows(rows, cols, 5) == 2


def test_inconsistent_clues_are_rejected_not_solved():
    rows, cols = [[3]], [[1], [1]]
    grid, solved = n.solve_lines(rows, cols)
    assert not solved
    assert n.count_solutions(rows, cols, 3) == 0 and n.count_by_rows(rows, cols, 3) == 0
    # row clues that disagree with column clues
    assert n.count_solutions([[2], [2]], [[1], [1], [1]], 3) == 0
    assert n.count_by_rows([[2], [2]], [[1], [1], [1]], 3) == 0


def test_the_counter_stops_at_its_limit():
    rows, cols = [[1]] * 4, [[1]] * 4                    # all 24 permutation matrices fit
    assert n.count_solutions(rows, cols, 24) == 24
    assert n.count_by_rows(rows, cols, 24) == 24
    assert n.count_solutions(rows, cols, 2) == 2
    assert n.count_by_rows(rows, cols, 2) == 2


def test_both_counters_agree_on_random_pictures():
    rnd = random.Random(20261012)
    for _ in range(120):
        h, w = rnd.randint(2, 6), rnd.randint(2, 6)
        pic = ["".join("#" if rnd.random() < 0.5 else "." for _ in range(w)) for _ in range(h)]
        rows, cols = n.clues_of(pic)
        a = n.count_solutions(rows, cols, 10 ** 6)
        b = n.count_by_rows(rows, cols, 10 ** 6)
        assert a == b and a >= 1, (pic, a, b)


def test_both_counters_agree_with_full_enumeration_on_every_3_by_3():
    """All 512 pictures of 3 by 3: the number of pictures sharing a clue set is what both counters report."""
    by_clue = {}
    pics = []
    for bits in range(512):
        pic = ["".join("#" if bits >> (r * 3 + c) & 1 else "." for c in range(3)) for r in range(3)]
        rows, cols = n.clues_of(pic)
        by_clue.setdefault((tuple(map(tuple, rows)), tuple(map(tuple, cols))), 0)
        by_clue[(tuple(map(tuple, rows)), tuple(map(tuple, cols)))] += 1
        pics.append((pic, rows, cols))
    for pic, rows, cols in pics:
        expect = by_clue[(tuple(map(tuple, rows)), tuple(map(tuple, cols)))]
        assert n.count_solutions(rows, cols, 10 ** 6) == expect
        assert n.count_by_rows(rows, cols, 10 ** 6) == expect
        # the line solver finishes exactly the pictures whose clues have one solution... or fewer-than-all: never more
        grid, solved = n.solve_lines(rows, cols)
        if solved:
            assert expect == 1
    # and a unique picture is not always line-solvable only if it needs guessing: record that the solver can say "stuck"
    assert any(count > 1 for count in by_clue.values())


def test_a_line_solved_picture_is_always_unique_but_not_the_other_way_round():
    """Line logic is sound: when it finishes, there is exactly one solution (checked on random pictures)."""
    rnd = random.Random(7)
    finished = 0
    for _ in range(200):
        h, w = rnd.randint(3, 7), rnd.randint(3, 7)
        pic = ["".join("#" if rnd.random() < 0.55 else "." for _ in range(w)) for _ in range(h)]
        rows, cols = n.clues_of(pic)
        grid, solved = n.solve_lines(rows, cols)
        if solved:
            finished += 1
            assert n.bitmap_of(grid) == pic and n.count_solutions(rows, cols, 2) == 1
    assert finished > 20


def test_solving_is_deterministic():
    pic = ["#.#.#", ".###.", "..#..", "..#..", ".###."]
    rows, cols = n.clues_of(pic)
    a = n.solve_lines(rows, cols)
    b = n.solve_lines(rows, cols)
    assert a == b and n.line_steps(rows, cols) == n.line_steps(rows, cols)


def test_solving_from_a_partial_grid_keeps_the_marks_and_adds_forced_cells():
    rows, cols = n.clues_of(["###..", "...#.", "...#.", ".....", "....."])
    start = n.blank_grid(5, 5)
    start[3][0] = E
    grid, _ = n.solve_lines(rows, cols, start)
    assert grid[3][0] == E
    assert n.count_of_unknown(start) == 24 and start[3][0] == E          # the input grid was copied, not changed in place
    assert n.count_of_unknown(grid) < 24


def test_prove_reports_the_whole_proof():
    out = n.prove([".###.", ".###.", "..#..", "..#..", "..#.."], cross_check=True)
    assert out["line_solved"] and out["count"] == 1 and out["count_by_rows"] == 1 and out["sweeps"] >= 1
    assert out["rows"] == [[3], [3], [1], [1], [1]]
