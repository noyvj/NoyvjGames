"""Edge-case tests for progress.py."""

import progress


def test_done_in_empty_best():
    """done_in returns 0 when best is empty."""
    assert progress.done_in({}, progress.CHAPTERS[0]) == 0


def test_done_in_all_done():
    """done_in counts all cases when every case in the chapter has a seal > 0."""
    best = {cid: 3 for cid in progress.CHAPTERS[0]["cases"]}
    assert progress.done_in(best, progress.CHAPTERS[0]) == len(progress.CHAPTERS[0]["cases"])


def test_chapter_open_first_always_true():
    """Chapter 0 is always open regardless of best."""
    assert progress.chapter_open({}, 0) is True
    assert progress.chapter_open({"1-1": 3}, 0) is True


def test_chapter_open_requires_threshold():
    """Chapter N opens only when OPEN_AT cases in the previous chapter are done, or all are done."""
    prev_chapter = progress.CHAPTERS[0]
    threshold = min(progress.OPEN_AT, len(prev_chapter["cases"]))

    best_few = {cid: 3 for cid in prev_chapter["cases"][:max(1, threshold - 1)]}
    assert progress.chapter_open(best_few, 1) is False

    best_enough = {cid: 3 for cid in prev_chapter["cases"][:threshold]}
    assert progress.chapter_open(best_enough, 1) is True


def test_case_open_invalid_cid():
    """case_open returns False for a CID not in CHAPTER_OF."""
    assert progress.case_open({}, "nonexistent-case") is False


def test_effective_normal_returns_best():
    """Normal difficulty reads directly from best."""
    best = {"1-1": 2}
    tiers = {}
    assert progress.effective(best, tiers, "1-1", "normal") == 2
    assert progress.effective(best, tiers, "missing-case", "normal") == 0


def test_effective_easy_uses_max():
    """Easy difficulty returns the maximum of best and tiers['easy']."""
    best = {"1-1": 1}
    tiers = {"easy": {"1-1": 2}}
    assert progress.effective(best, tiers, "1-1", "easy") == 2


def test_effective_hard_ignores_best():
    """Hard difficulty reads only from tiers['hard']."""
    best = {"1-1": 3}
    tiers = {"hard": {"1-1": 1}}
    assert progress.effective(best, tiers, "1-1", "hard") == 1


def test_totals_empty_best():
    """totals returns zeroed counts when best is empty."""
    t = progress.totals({})
    assert t["done"] == 0
    assert t["clean"] == 0
    assert t["steady"] == 0
    assert t["rough"] == 0
    assert t["chapters_done"] == 0


def test_effective_map_filters_zeros():
    """effective_map only includes cases with a non-zero grade."""
    best = {"1-1": 3, "1-2": 0}
    tiers = {}
    mapped = progress.effective_map(best, tiers, "normal")
    assert "1-1" in mapped and mapped["1-1"] == 3
    assert "1-2" not in mapped


def test_tier_totals_normal_ignores_tiers():
    """tier_totals for normal difficulty returns exactly totals(best)."""
    best = {"1-1": 3}
    tiers = {"easy": {}, "hard": {}}
    t = progress.tier_totals(best, tiers, "normal")
    assert t["done"] == progress.totals(best)["done"]


def test_next_case_wraps_round():
    """next_case wraps around to the start when no undone cases remain after cur."""
    best = {cid: 3 for cid in progress.ORDER}
    nxt = progress.next_case(best, progress.ORDER[-1])
    assert nxt == progress.ORDER[0]


def test_next_case_unknown_cur_starts_from_beginning():
    """next_case treats an unknown cur as -1 and searches from the start."""
    best = {}
    nxt = progress.next_case(best, "unknown")
    assert nxt == progress.ORDER[0]
