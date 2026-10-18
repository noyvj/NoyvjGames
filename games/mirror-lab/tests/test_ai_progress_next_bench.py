"""Tests for progress.next_bench()."""

import benches
import progress


def test_next_bench_returns_the_immediate_next_uncleared_bench():
    cleared = {}
    next_id = progress.next_bench(cleared, "c1-1")
    assert next_id == "c1-2"


def test_next_bench_skips_cleared_benches_and_wraps_to_chapter_2():
    # Clear c1-2 so it is skipped; c1-3 is still open in chapter 1
    cleared = {"c1-2": benches.BY_ID["c1-2"].solution_layout()}
    next_id = progress.next_bench(cleared, "c1-1")
    assert next_id == "c1-3"


def test_next_bench_returns_none_when_all_open_benches_are_cleared():
    # Clear every bench so no open benches remain
    cleared = {b.id: b.solution_layout() for b in benches.ALL_BENCHES}
    assert progress.next_bench(cleared, "c1-1") is None


def test_next_bench_returns_none_for_unknown_bench_id():
    assert progress.next_bench({}, "nonexistent-bench") is None
