"""Tests for unease.trifle_tonight().

Checks that the function correctly filters out invalid nights, respects the random chance threshold, and returns a valid
trifle id when all conditions are met."""

import unittest.mock

import mysteries
import unease


def test_trifle_tonight_returns_a_trifle_when_conditions_met():
    """When the night is allowed, chance passes, and no run-length limit is hit, it picks a trifle."""
    with unittest.mock.patch.object(unease, "unit", return_value=0.0):
        result = unease.trifle_tonight(
            seed=1, night=5, unease=50, fired=set(), odd_set=set(), kind_set=set()
        )
        assert result is not None
        assert result in mysteries.TRIFLE_ORDER


def test_trifle_tonight_returns_none_when_chance_fails():
    """If the random draw exceeds the chance threshold, no trifle falls regardless of other conditions."""
    with unittest.mock.patch.object(unease, "unit", return_value=1.0):
        result = unease.trifle_tonight(
            seed=1, night=5, unease=50, fired=set(), odd_set=set(), kind_set=set()
        )
        assert result is None


def test_trifle_tonight_returns_none_when_all_trifles_fired():
    """Once every trifle has been explained, the function stops returning new ones."""
    result = unease.trifle_tonight(
        seed=1, night=5, unease=0, fired=set(mysteries.TRIFLE_ORDER), odd_set=set(), kind_set=set()
    )
    assert result is None
