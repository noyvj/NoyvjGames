"""The constraint solver, checked against an independent brute force."""

import itertools
import random

import pytest


def brute_force(game, board, pings):
    out = []
    for combo in itertools.combinations(board.cells, board.k):
        if any(board.dist[a][b] < board.spacing for a, b in itertools.combinations(combo, 2)):
            continue
        if all(sum(board.weight[t][cell] for t in combo) == v for cell, v in pings):
            out.append(tuple(sorted(combo)))
    return sorted(out)


@pytest.mark.parametrize("mode", ["easy", "hard"])
def test_solver_matches_brute_force_on_random_puzzles(game, mode):
    board = game.board_for(mode)
    rng = random.Random(7)
    wanted = 3 if mode == "hard" else 10
    done = 0
    while done < wanted:
        truth = tuple(sorted(rng.sample(board.cells, board.k)))
        if any(board.dist[a][b] < board.spacing for a, b in itertools.combinations(truth, 2)):
            continue
        done += 1
        cells = rng.sample(range(board.n * board.n), 4 if mode == "hard" else 3)
        pings = [(c, game.reading_at(board, truth, c)) for c in cells]
        solved, complete = game.solve(board, pings, limit=10 ** 6)
        assert complete
        assert sorted(solved) == brute_force(game, board, pings)
        assert truth in solved


def test_solver_partitions_solutions_exactly_once(game):
    board = game.board_for("easy")
    pings = [(40, 3)]
    solved, _ = game.solve(board, pings, limit=10 ** 6)
    assert len(solved) == len(set(solved))
    assert len(solved) == len(brute_force(game, board, pings))


def test_zero_reading_clears_the_whole_neighbourhood(game):
    board = game.board_for("easy")
    centre = 4 * 9 + 4
    solved, _ = game.solve(board, [(centre, 0)], limit=10 ** 6)
    for sol in solved:
        for t in sol:
            assert board.dist[centre][t] >= board.radius


def test_solver_limit_and_node_cap(game):
    board = game.board_for("hard")
    sols, complete = game.solve(board, [], limit=5)
    assert len(sols) == 5 and complete
    sols, complete = game.solve(board, [(40, 5)], limit=10 ** 9, node_cap=20)
    assert complete is False


def test_impossible_readings_have_no_solution(game):
    board = game.board_for("easy")
    sols, complete = game.solve(board, [(40, 99)], limit=2)
    assert sols == [] and complete


def test_forced_cell_must_appear(game):
    board = game.board_for("easy")
    truth = (30, 50)
    pings = [(c, game.reading_at(board, truth, c)) for c in (40, 31, 49)]
    sols, _ = game.solve(board, pings, limit=50, forced=30)
    assert truth in sols and all(30 in s for s in sols)
    assert game.solve(board, pings, limit=5, forced=0)[0] == []  # ring tile is never a candidate


def test_possible_cells_keeps_the_truth(game):
    board = game.board_for("easy")
    truth = (30, 50)
    pings = [(c, game.reading_at(board, truth, c)) for c in (40, 31, 49, 12)]
    cells = game.possible_cells(board, pings)
    assert set(truth) <= set(cells)
    assert len(cells) < len(board.cells)


def test_possible_cells_never_falsely_rules_out_when_search_is_capped(game):
    board = game.board_for("hard")
    truth = (20, 24, 56, 60)
    pings = [(40, game.reading_at(board, truth, 40))]
    capped = game.possible_cells(board, pings, node_cap=3)
    exact = game.possible_cells(board, pings, node_cap=10 ** 7)
    assert set(exact) <= set(capped)
    assert set(truth) <= set(exact)


def test_big_boards_solve_fast_enough_for_a_smoke_test(game):
    board = game.board_for("bigsky")
    truth = game._place(board, game.Rng(99))
    assert len(truth) == board.k
    pings = [(c, game.reading_at(board, truth, c)) for c in (112, 20, 200, 60, 150, 90)]
    sols, complete = game.solve(board, pings, limit=2)
    assert complete and len(sols) >= 1
    forced, _ = game.solve(board, pings, limit=1, forced=truth[0])
    assert forced  # the true set is consistent, so a set containing its first tile exists
