"""Tests for the tier_totals() function in progress.py."""


import progress


def test_tier_totals_normal_returns_exact_totals():
    """Test that tier_totals with difficulty='normal' returns exactly totals(best)."""
    best = {sid: 3 for sid in list(progress.ORDER)[:5]}
    tiers = {"easy": {}, "hard": {}}
    result = progress.tier_totals(best, tiers, "normal")
    expected = progress.totals(best)
    assert result == expected


def test_tier_totals_easy_uses_better_seal():
    """Test that tier_totals with difficulty='easy' uses the better of best and tiers['easy'] for each shift."""
    sids = list(progress.ORDER)[:3]
    best = {sids[0]: 2, sids[1]: 1}
    easy_tiers = {sids[0]: 3, sids[2]: 2}
    tiers = {"easy": easy_tiers, "hard": {}}

    result = progress.tier_totals(best, tiers, "easy")

    merged = {}
    for sid in progress.ORDER:
        b = best.get(sid, 0)
        e = easy_tiers.get(sid, 0)
        if b or e:
            merged[sid] = max(b, e)

    expected = progress.totals(merged)
    assert result == expected


def test_tier_totals_hard_ignores_best():
    """Test that tier_totals with difficulty='hard' reads only tiers['hard'], ignoring best."""
    sids = list(progress.ORDER)[:3]
    best = {sids[0]: 3, sids[1]: 3}
    hard_tiers = {sids[0]: 2, sids[1]: 1, sids[2]: 3}
    tiers = {"easy": {}, "hard": hard_tiers}

    result = progress.tier_totals(best, tiers, "hard")

    expected = progress.totals(hard_tiers)
    assert result == expected
