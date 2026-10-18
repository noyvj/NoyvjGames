"""Tests for the effective() function in progress.py."""

import progress


def test_effective_normal_returns_best_grade():
    """Test that effective returns the grade from best when difficulty is normal."""
    sid = progress.ORDER[0]
    best = {sid: 3}
    tiers = {"easy": {}, "hard": {}}
    assert progress.effective(best, tiers, sid, "normal") == 3


def test_effective_easy_returns_max_of_best_and_easy_tier():
    """Test that effective returns the better of the Normal seal and the Easy record."""
    sid = progress.ORDER[0]
    best = {sid: 1}
    tiers = {"easy": {sid: 3}, "hard": {}}
    assert progress.effective(best, tiers, sid, "easy") == 3


def test_effective_hard_ignores_best_and_returns_tier_grade():
    """Test that effective returns only the Hard record, ignoring the Normal seal."""
    sid = progress.ORDER[0]
    best = {sid: 3}
    tiers = {"easy": {}, "hard": {sid: 2}}
    assert progress.effective(best, tiers, sid, "hard") == 2


def test_effective_missing_shift_returns_zero():
    """Test that effective returns 0 when the shift is not in best or tiers."""
    sid = "nonexistent-shift"
    best = {}
    tiers = {"easy": {}, "hard": {}}
    assert progress.effective(best, tiers, sid, "normal") == 0
    assert progress.effective(best, tiers, sid, "easy") == 0
    assert progress.effective(best, tiers, sid, "hard") == 0
