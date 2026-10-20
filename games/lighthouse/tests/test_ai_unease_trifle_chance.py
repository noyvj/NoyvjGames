"""Tests for unease.trifle_chance().

Verifies the linear scaling of the small oddity chance against the hidden unease meter,
including the base chance, the cap, and a negative edge case."""

import unease
import mysteries


def test_trifle_chance_at_zero_unease():
    """When unease is zero, the chance should be the base value of 0.05."""
    assert unease.trifle_chance(0) == 0.05


def test_trifle_chance_at_maximum_unease():
    """At the maximum unease cap, the chance should reach 0.45 (0.05 + 0.4)."""
    cap = mysteries.UNEASE_CAP
    assert unease.trifle_chance(cap) == 0.45


def test_trifle_chance_with_negative_unease_edge_case():
    """Negative unease falls below the base chance, showing no clamping inside this function."""
    assert unease.trifle_chance(-10) < 0.05
