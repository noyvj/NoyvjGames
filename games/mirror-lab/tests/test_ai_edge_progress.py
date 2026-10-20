"""Edge-case tests for progress.py."""

import benches
import progress


def test_chapter_cleared_empty_and_full():
    assert progress.chapter_cleared({}, 1) == 0
    full = {b.id: b.solution_layout() for b in benches.CHAPTERS[0]["benches"]}
    assert progress.chapter_cleared(full, 1) == len(benches.CHAPTERS[0]["benches"])


def test_chapter_open_bounds_and_thresholds():
    assert progress.chapter_open({}, 1) is True
    assert progress.chapter_open({}, len(benches.CHAPTERS) + 1) is False
    four_cleared = {b.id: b.solution_layout() for b in benches.CHAPTERS[0]["benches"][:4]}
    assert progress.chapter_open(four_cleared, 2) is False
    five_cleared = {b.id: b.solution_layout() for b in benches.CHAPTERS[0]["benches"][:5]}
    assert progress.chapter_open(five_cleared, 2) is True


def test_bench_open_invalid_and_chapter_status():
    assert progress.bench_open({}, "nonexistent-bench") is False
    ch1_cleared = {b.id: b.solution_layout() for b in benches.CHAPTERS[0]["benches"][:5]}
    ch2_bench = benches.CHAPTERS[1]["benches"][0]
    assert progress.bench_open(ch1_cleared, ch2_bench.id) is True
    ch2_open = {b.id: b.solution_layout() for b in benches.CHAPTERS[0]["benches"]}
    assert progress.bench_open(ch2_open, ch2_bench.id) is True


def test_fewest_tags_empty_and_matching_par():
    assert progress.fewest_tags({}) == 0
    b = benches.ALL_BENCHES[0]
    layout_at_par = {b.id: b.solution_layout()}
    assert progress.fewest_tags(layout_at_par) == 1


def test_sensors_lit_empty_and_single_bench():
    assert progress.sensors_lit({}) == 0
    b = benches.ALL_BENCHES[0]
    cleared = {b.id: b.solution_layout()}
    assert progress.sensors_lit(cleared) == len(b.board.required)


def test_totals_empty_and_partial():
    t = progress.totals({})
    assert t["benches"] == len(benches.ALL_BENCHES)
    assert t["cleared"] == 0
    assert t["sensors"] == 0
    assert t["fewest"] == 0
    assert t["chapters"] == len(benches.CHAPTERS)
    assert t["chapters_cleared"] == 0

    b = benches.ALL_BENCHES[0]
    partial = {b.id: b.solution_layout()}
    t_partial = progress.totals(partial)
    assert t_partial["cleared"] == 1
    assert t_partial["sensors"] == len(b.board.required)
