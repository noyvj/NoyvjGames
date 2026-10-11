"""The benches are PROVED: every one has a solution, the stored solution is valid and as small as any, the tray is not padded, the empty
bench is not already solved, and the benches the data calls single-answer really have exactly one solution. The solver is re-run here,
so the frozen data cannot drift from the rules."""

import benches
import optics
import progress
import solve
import specs
import build_benches

SOLVED = {b.id: solve.solve(b.board, b.tray) for b in benches.ALL_BENCHES}


def test_there_are_three_chapters_of_eight_benches_with_unique_ids_and_names():
    assert [len(ch["benches"]) for ch in benches.CHAPTERS] == [8, 8, 8]
    assert len(benches.ALL_BENCHES) == 24
    ids = [b.id for b in benches.ALL_BENCHES]
    assert len(set(ids)) == 24 and ids == benches.ORDER
    assert len({b.name for b in benches.ALL_BENCHES}) == 24
    assert [b.number for b in benches.CHAPTERS[1]["benches"]] == list(range(1, 9))


def test_every_bench_board_is_a_small_rectangle_with_one_emitter_and_a_sensor():
    for b in benches.ALL_BENCHES:
        assert 5 <= b.board.w <= 7 and 4 <= b.board.h <= 7, b.id                     # at most 7 columns so cells stay 44 px wide on a phone
        assert len(b.board.emitters) == 1 and b.board.required, b.id
        assert len(b.board.slots) > b.tray_size, b.id                                # more slots than pieces: a choice to make


def test_the_frozen_data_matches_the_pictures_in_the_specs():
    for chapter, items in specs.CHAPTERS.items():
        for spec in items:
            rows, tray, solution = build_benches.parse_picture(spec["pic"])
            b = benches.BY_ID[spec["id"]]
            assert list(b.rows) == rows and b.tray == tray and b.solution == solution, spec["id"]
            assert b.name == spec["name"] and b.line == spec["line"]


def test_every_bench_has_at_least_one_solution_and_the_stored_one_is_valid():
    for b in benches.ALL_BENCHES:
        assert SOLVED[b.id], b.id
        layout = b.solution_layout()
        assert optics.layout_problem(b.board, b.tray, layout) is None, b.id
        assert optics.trace(b.board, layout).ok, b.id
        assert tuple(sorted(b.solution)) in SOLVED[b.id], b.id


def test_the_stored_counts_match_the_solver():
    for b in benches.ALL_BENCHES:
        assert b.count == len(SOLVED[b.id]), b.id
        assert b.par == min(len(s) for s in SOLVED[b.id]), b.id


def test_the_tray_is_not_padded_and_no_stored_piece_can_be_removed():
    for b in benches.ALL_BENCHES:
        layout = b.solution_layout()
        assert len(layout) == b.par == b.tray_size, b.id                             # the stored solution uses the whole tray, and it is the fewest
        for cell in layout:
            smaller = {k: v for k, v in layout.items() if k != cell}
            assert not optics.trace(b.board, smaller).ok, (b.id, cell)
        for piece, n in b.tray.items():
            fewer = dict(b.tray)
            fewer[piece] -= 1
            assert not solve.solve(b.board, {k: v for k, v in fewer.items() if v}), (b.id, piece)


def test_the_empty_bench_is_never_already_solved():
    for b in benches.ALL_BENCHES:
        assert not optics.trace(b.board, {}).ok, b.id


def test_single_answer_benches_have_exactly_one_solution_and_the_others_have_a_few():
    unique = [b for b in benches.ALL_BENCHES if b.unique]
    several = [b for b in benches.ALL_BENCHES if not b.unique]
    assert len(unique) >= 12 and len(several) >= 5
    for b in unique:
        assert len(SOLVED[b.id]) == 1, b.id
    for b in several:
        assert 2 <= len(SOLVED[b.id]) <= 4, b.id


def test_a_bench_is_not_cleared_by_a_wrong_orientation_of_the_stored_pieces():
    """Flipping any flippable piece of a single-answer bench breaks it (the answer really depends on the flip)."""
    flippable = 0
    for b in benches.ALL_BENCHES:
        if not b.unique:
            continue
        for cell, (piece, state) in b.solution_layout().items():
            if optics.PIECE_STATES[piece] < 2:
                continue
            flippable += 1
            layout = b.solution_layout()
            layout[cell] = (piece, 1 - state)
            assert not optics.trace(b.board, layout).ok, (b.id, cell)
    assert flippable >= 20


def test_chapter_content_matches_its_theme():
    for b in benches.CHAPTERS[0]["benches"]:
        assert set(b.tray) == {"mirror"} and not b.board.decoys and not any(k in "SL" for k in b.board.sensors.values())
    for b in benches.CHAPTERS[1]["benches"]:
        assert "splitter" in b.tray and "prism" not in b.tray
    for b in benches.CHAPTERS[2]["benches"]:
        assert "prism" in b.tray
        assert any(k in "SL" for k in b.board.sensors.values())
    chapter3_sensor_kinds = {k for b in benches.CHAPTERS[2]["benches"] for k in b.board.sensors.values()}
    assert {"S", "L"} <= chapter3_sensor_kinds
    assert {k for b in benches.ALL_BENCHES for k in b.tray} == {"mirror", "splitter", "prism"}


def test_the_chapter_gate_opens_at_five_of_eight():
    ids = [b.id for b in benches.CHAPTERS[0]["benches"]]
    cleared = {}
    assert progress.chapter_open(cleared, 1) and not progress.chapter_open(cleared, 2) and not progress.chapter_open(cleared, 3)
    for i, bid in enumerate(ids[:4]):
        cleared[bid] = benches.BY_ID[bid].solution_layout()
    assert not progress.chapter_open(cleared, 2)
    cleared[ids[4]] = benches.BY_ID[ids[4]].solution_layout()
    assert progress.chapter_open(cleared, 2) and not progress.chapter_open(cleared, 3)
    assert not progress.bench_open(cleared, "c3-1") and progress.bench_open(cleared, "c2-8")


def test_the_operator_lines_are_present_and_dry_and_short():
    for b in benches.ALL_BENCHES:
        assert 20 < len(b.line) < 140, b.id
