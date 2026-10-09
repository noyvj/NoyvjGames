"""Every authored board: legal, solvable, exactly one restored layout, the stored one."""

import pytest

import boards
import play
import rules
import solver

ALL = boards.ALL_BOARDS


def test_the_decks_and_ids_are_consistent():
    assert [c["id"] for c in boards.CHAPTER_LIST] == ["dock", "crew", "engineering", "life", "core"]
    assert len(boards.ORDER) == len(set(boards.ORDER)) == sum(len(c["rooms"]) for c in boards.CHAPTER_LIST)
    for c in boards.CHAPTER_LIST:
        assert len(c["rooms"]) in (0, 8)
    assert boards.OPEN_AT == 5


@pytest.mark.parametrize("b", ALL, ids=lambda b: b.id)
def test_the_stored_layout_restores_the_board(b):
    assert b.solution is not None and rules.check_layout(b, b.solution) == []
    assert rules.status(b, b.solution) == rules.RESTORED
    assert set(b.solution) == set(b.lines)
    assert rules.oriented(b, "A", b.solution["A"]) == b.solution["A"]            # stored source-first


@pytest.mark.parametrize("b", ALL, ids=lambda b: b.id)
def test_the_solver_finds_exactly_one_restored_layout_and_it_is_the_stored_one(b):
    found = solver.solve(b, 2)
    assert len(found) == 1
    assert found[0] == b.solution
    assert solver.solve(b, 1, fill=False)                                          # and the lines can be joined


@pytest.mark.parametrize("b", ALL, ids=lambda b: b.id)
def test_the_drawing_can_lay_the_stored_layout_by_dragging(b):
    d = play.Drawing(b)
    for c in b.lines:
        path = b.solution[c]
        ok, msg = d.begin(path[0])
        assert ok, msg
        for cell in path[1:]:
            ok, msg = d.move(cell)
            assert ok, (b.id, c, cell, msg)
        d.end()
    assert d.status() == rules.RESTORED and d.paths == b.solution


def test_decks_grow_from_five_by_five_and_keep_their_sizes():
    sizes = [(b.w, b.h) for b in ALL]
    assert all(5 <= w <= 9 and 5 <= h <= 9 for w, h in sizes)
    first = boards.CHAPTER_LIST[0]["rooms"]
    assert max(boards.BY_ID[i].w for i in first) <= 6


def test_the_solver_counts_more_than_one_when_a_board_is_loose():
    loose = rules.Board({"id": "l", "rows": ["A...a", ".....", ".....", ".....", "....."]})
    assert len(solver.solve(loose, 2)) == 2
    impossible = rules.Board({"id": "i", "rows": ["A.#.a", "..#..", "..#..", "..#..", "..#.."]})
    assert solver.solve(impossible, 2) == []


def test_the_solver_agrees_with_the_rules_on_every_twist():
    cases = [
        (["A...a", "B...b", ".....", ".....", "....."], None),
        (["..B..", "A.=.a", "..b..", ".....", "....."], None),
        (["A>..a", ".....", ".....", ".....", "....."], None),
        (["A.1.B", ".....", ".....", ".....", "....."], {"1": "AB"}),
        (["A.#.a", ".....", ".....", ".....", "....."], None),
    ]
    for rows, mixers in cases:
        spec = {"id": "t", "rows": rows}
        if mixers:
            spec["mixers"] = mixers
        b = rules.Board(spec)
        for fill in (True, False):
            for layout in solver.solve(b, 5, fill=fill, node_limit=2000000):
                assert rules.check_layout(b, layout) == []
                assert rules.status(b, layout) >= (rules.RESTORED if fill else rules.PATCHED)
