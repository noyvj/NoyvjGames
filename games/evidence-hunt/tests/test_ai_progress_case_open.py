"""Tests for progress.case_open."""

import progress


def test_case_in_chapter_0_is_always_open():
    """A case in the first chapter is open even with an empty best dict."""
    ch0_cid = next(cid for cid, idx in progress.CHAPTER_OF.items() if idx == 0)
    assert progress.case_open({}, ch0_cid) is True


def test_case_in_later_chapter_opens_when_previous_has_enough_done():
    """A case in a later chapter opens once the previous chapter has at least OPEN_AT cases done."""
    ch1_cid = next(cid for cid, idx in progress.CHAPTER_OF.items() if idx == 1)

    # Build best dict with exactly OPEN_AT cases done from chapter 0
    ch0_cases = [cid for cid, idx in progress.CHAPTER_OF.items() if idx == 0]
    best = {c: 3 for c in ch0_cases[:progress.OPEN_AT]}

    assert progress.case_open(best, ch1_cid) is True


def test_case_in_later_chapter_closed_when_previous_has_fewer_done():
    """A case in a later chapter stays closed if the previous chapter has fewer than OPEN_AT cases done."""
    ch1_cid = next(cid for cid, idx in progress.CHAPTER_OF.items() if idx == 1)

    # Build best dict with one less than OPEN_AT cases done
    ch0_cases = [cid for cid, idx in progress.CHAPTER_OF.items() if idx == 0]
    best = {c: 3 for c in ch0_cases[:progress.OPEN_AT - 1]}

    assert progress.case_open(best, ch1_cid) is False


def test_case_not_in_any_chapter_returns_false():
    """An unknown case ID should return False."""
    assert progress.case_open({}, "nonexistent-case") is False
