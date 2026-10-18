"""Tests for progress.effective()."""


import cases
import progress


def test_effective_normal_returns_best_seal():
    """Normal difficulty reads directly from best."""
    cid = cases.ALL[0]["id"]
    best = {cid: 3}
    tiers = {"easy": {}, "hard": {}}
    assert progress.effective(best, tiers, cid, "normal") == 3


def test_effective_easy_returns_max_of_best_and_easy_tier():
    """Easy difficulty returns the better of the Normal seal and the Easy record."""
    cid = cases.ALL[1]["id"]
    best = {cid: 2}
    tiers = {"easy": {cid: 3}, "hard": {}}
    assert progress.effective(best, tiers, cid, "easy") == 3


def test_effective_hard_ignores_best():
    """Hard difficulty reads only from the Hard tier; Normal seals are ignored."""
    cid = cases.ALL[2]["id"]
    best = {cid: 3}
    tiers = {"easy": {}, "hard": {cid: 1}}
    assert progress.effective(best, tiers, cid, "hard") == 1


def test_effective_missing_case_id_returns_zero():
    """Edge case: if the case id is missing from best or tiers, effective returns 0."""
    cid = cases.ALL[0]["id"]
    best = {}
    tiers = {"easy": {}, "hard": {}}
    assert progress.effective(best, tiers, cid, "normal") == 0
    assert progress.effective(best, tiers, cid, "easy") == 0
    assert progress.effective(best, tiers, cid, "hard") == 0
