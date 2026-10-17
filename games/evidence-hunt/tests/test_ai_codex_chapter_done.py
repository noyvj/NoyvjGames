"""Tests for codex.chapter_done()."""

import codex
import progress


def test_chapter_done_returns_true_when_all_cases_are_completed():
    """A chapter is done when every case ID in it has an entry in best."""
    chapter_idx = 0
    cases = progress.CHAPTERS[chapter_idx]["cases"]
    best = {cid: 3 for cid in cases}
    assert codex.chapter_done(best, chapter_idx) is True


def test_chapter_done_returns_false_when_any_case_is_missing():
    """If even one case lacks a seal grade, the chapter is not done."""
    chapter_idx = 0
    cases = progress.CHAPTERS[chapter_idx]["cases"]
    best = {cid: 3 for cid in cases[:-1]}
    assert codex.chapter_done(best, chapter_idx) is False


def test_chapter_done_handles_empty_best_as_edge_case():
    """An empty best dict should correctly report no chapters as done."""
    best = {}
    for idx in range(len(progress.CHAPTERS)):
        assert codex.chapter_done(best, idx) is False
