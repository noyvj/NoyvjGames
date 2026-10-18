"""Tests for benches.chapter_of()."""

import pytest

import benches


def test_chapter_of_returns_correct_info_for_first_bench():
    """Normal case: first bench belongs to chapter 1."""
    bench = benches.ALL_BENCHES[0]
    result = benches.chapter_of(bench)
    assert result is benches.CHAPTERS[bench.chapter - 1]


def test_chapter_of_returns_correct_info_for_last_bench():
    """Normal case: last bench belongs to chapter 5."""
    bench = benches.ALL_BENCHES[-1]
    result = benches.chapter_of(bench)
    assert result is benches.CHAPTERS[bench.chapter - 1]


def test_chapter_of_raises_index_error_for_invalid_chapter():
    """Edge case: an out-of-bounds chapter index raises IndexError."""
    class FakeBench:
        chapter = 6

    with pytest.raises(IndexError):
        benches.chapter_of(FakeBench())
