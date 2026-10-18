"""Tests for the effective_map() function in progress.py."""

import progress


def test_effective_map_normal_returns_best():
    """Test that effective_map returns grades from best on normal difficulty."""
    best = {sid: 3 for sid in progress.ORDER[:3]}
    tiers = {"easy": {}, "hard": {}}
    result = progress.effective_map(best, tiers, "normal")
    assert result == best


def test_effective_map_easy_uses_max():
    """Test that effective_map takes the max of best and easy tiers on easy difficulty."""
    best = {progress.ORDER[0]: 2, progress.ORDER[1]: 3}
    tiers = {"easy": {progress.ORDER[0]: 3, progress.ORDER[1]: 1}, "hard": {}}
    result = progress.effective_map(best, tiers, "easy")
    assert result == {progress.ORDER[0]: 3, progress.ORDER[1]: 3}


def test_effective_map_hard_uses_tiers():
    """Test that effective_map returns grades from hard tiers on hard difficulty."""
    best = {progress.ORDER[0]: 3, progress.ORDER[1]: 0}
    tiers = {"easy": {}, "hard": {progress.ORDER[0]: 2, progress.ORDER[1]: 1}}
    result = progress.effective_map(best, tiers, "hard")
    assert result == {progress.ORDER[0]: 2, progress.ORDER[1]: 1}


def test_effective_map_excludes_undone_shifts():
    """Test that effective_map filters out shifts with grade 0."""
    best = {progress.ORDER[0]: 3, progress.ORDER[1]: 0}
    tiers = {"easy": {}, "hard": {}}
    result = progress.effective_map(best, tiers, "normal")
    assert progress.ORDER[0] in result
    assert progress.ORDER[1] not in result
