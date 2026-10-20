"""Tests for sim.burn_rate."""

import sim


class _MockKeep:
    """Minimal mock providing only what burn_rate needs."""

    def __init__(self):
        self.upgrades = set()

    def has(self, name):
        return name in self.upgrades


def test_burn_rate_returns_base_rate_for_dim_lamp():
    k = _MockKeep()
    assert sim.burn_rate(k, 0) == sim.LEVEL_BURN[0]


def test_burn_rate_applies_wick_discount():
    k = _MockKeep()
    k.upgrades.add("wick")
    expected = sim.LEVEL_BURN[1] * 0.8
    assert sim.burn_rate(k, 1) == expected


def test_burn_rate_with_high_level_and_wick():
    k = _MockKeep()
    k.upgrades.add("wick")
    expected = sim.LEVEL_BURN[3] * 0.8
    assert sim.burn_rate(k, 3) == expected
