"""Tests for progress.tier_totals."""

import progress


def test_normal_returns_best_seals():
    """Normal difficulty should return totals based exactly on best."""
    best = {cid: 3 for cid in progress.ORDER}
    tiers = {"easy": {}, "hard": {}}
    result = progress.tier_totals(best, tiers, "normal")

    assert result["clean"] == len(progress.ORDER)
    assert result["done"] == len(progress.ORDER)
    assert result["steady"] == 0
    assert result["rough"] == 0


def test_easy_uses_max_of_best_and_easy_tiers():
    """Easy difficulty should use the better of the Normal seal and the Easy tier record."""
    cases = list(progress.ORDER)[:3]
    best = {cid: 2 for cid in cases}
    tiers = {"easy": {cases[0]: 3, cases[1]: 1, cases[2]: 0}, "hard": {}}

    result = progress.tier_totals(best, tiers, "easy")

    assert result["clean"] == 1
    assert result["steady"] == 2
    assert result["rough"] == 0


def test_hard_ignores_best_and_uses_only_hard_tiers():
    """Hard difficulty should ignore best and only use the Hard tier record."""
    cases = list(progress.ORDER)[:3]
    best = {cid: 3 for cid in cases}
    tiers = {"easy": {}, "hard": {cases[0]: 1, cases[1]: 2, cases[2]: 0}}

    result = progress.tier_totals(best, tiers, "hard")

    assert result["clean"] == 0
    assert result["steady"] == 1
    assert result["rough"] == 1


def test_edge_case_empty_inputs():
    """Edge case: empty inputs should return zeroed totals with correct structure."""
    best = {}
    tiers = {"easy": {}, "hard": {}}

    result = progress.tier_totals(best, tiers, "normal")

    assert result["done"] == 0
    assert result["chapters_done"] == 0
    assert result["cases"] == len(progress.ORDER)
