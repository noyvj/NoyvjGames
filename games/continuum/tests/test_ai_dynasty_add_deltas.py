"""Tests for dynasty.add_deltas()."""

import dynasty


def test_add_deltas_sum_matching_keys():
    """Normal case: matching keys are summed, original dict is untouched."""
    effects = {"food_yield_mult": 0.0, "knowledge_mult": 0.0}
    deltas = {"food_yield_mult": 0.02, "knowledge_mult": 0.03}
    result = dynasty.add_deltas(effects, deltas)
    assert result == {"food_yield_mult": 0.02, "knowledge_mult": 0.03}
    assert effects == {"food_yield_mult": 0.0, "knowledge_mult": 0.0}


def test_add_deltas_skips_unknown_keys():
    """Normal case: keys in `deltas` not present in `effects` are ignored."""
    effects = {"food_yield_mult": 0.0}
    deltas = {"food_yield_mult": 0.02, "phantom_key": 100}
    result = dynasty.add_deltas(effects, deltas)
    assert result == {"food_yield_mult": 0.02}
    assert "phantom_key" not in result


def test_add_deltas_with_empty_effects():
    """Edge case: `effects` is empty; returns an empty dict without adding unknown keys."""
    effects = {}
    deltas = {"food_storage_bonus": 6.0}
    result = dynasty.add_deltas(effects, deltas)
    assert result == {}
