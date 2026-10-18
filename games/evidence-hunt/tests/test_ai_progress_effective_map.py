"""Tests for progress.effective_map."""

import progress


def test_normal_difficulty_filters_and_returns_best():
    """Normal difficulty uses only `best`; cases with grade 0 are omitted."""
    best = {progress.ORDER[0]: 3, progress.ORDER[1]: 2, progress.ORDER[2]: 0}
    tiers = {"easy": {}, "hard": {}}
    result = progress.effective_map(best, tiers, "normal")
    assert len(result) == 2
    assert result[progress.ORDER[0]] == 3
    assert result[progress.ORDER[1]] == 2
    assert progress.ORDER[2] not in result


def test_easy_difficulty_uses_max_of_best_and_tiers():
    """Easy difficulty takes the better seal between `best` and `tiers['easy']`."""
    best = {progress.ORDER[0]: 3, progress.ORDER[1]: 1}
    tiers = {"easy": {progress.ORDER[0]: 2, progress.ORDER[1]: 3}}
    result = progress.effective_map(best, tiers, "easy")
    assert len(result) == 2
    assert result[progress.ORDER[0]] == 3
    assert result[progress.ORDER[1]] == 3


def test_hard_difficulty_ignores_best():
    """Hard difficulty reads only `tiers['hard']`; `best` is ignored."""
    best = {progress.ORDER[0]: 3, progress.ORDER[1]: 2}
    tiers = {"easy": {}, "hard": {progress.ORDER[0]: 1}}
    result = progress.effective_map(best, tiers, "hard")
    assert len(result) == 1
    assert result[progress.ORDER[0]] == 1
    assert progress.ORDER[1] not in result


def test_empty_inputs_returns_empty_dict():
    """When both `best` and `tiers` are empty, the map is empty."""
    best = {}
    tiers = {"easy": {}, "hard": {}}
    result = progress.effective_map(best, tiers, "normal")
    assert result == {}
