"""Tests for progress.done_in()."""

import progress


def test_done_in_all_cases_completed():
    """Normal case: when every case in a chapter has a seal > 0, done_in returns the number of cases."""
    best = {cid: 3 for cid in progress.CHAPTERS[0]["cases"]}
    assert progress.done_in(best, progress.CHAPTERS[0]) == len(progress.CHAPTERS[0]["cases"])


def test_done_in_some_cases_completed():
    """Normal case: when only some cases in a chapter are completed, done_in returns the count of completed ones."""
    chapter = progress.CHAPTERS[1]
    best = {chapter["cases"][0]: 2}
    assert progress.done_in(best, chapter) == 1


def test_done_in_no_cases_completed():
    """Boundary case: when no cases in a chapter are completed, done_in returns 0."""
    best = {}
    assert progress.done_in(best, progress.CHAPTERS[2]) == 0


def test_done_in_empty_best_dict():
    """Edge case: an empty best dict should return 0 for any chapter."""
    assert progress.done_in({}, progress.CHAPTERS[3]) == 0
