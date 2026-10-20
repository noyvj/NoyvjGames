"""Tests for part_state() in view.py."""

from view import part_state


def test_part_state_returns_sound_for_high_values():
    assert part_state(80) == "sound"
    assert part_state(70) == "sound"


def test_part_state_returns_worn_and_poor_for_mid_range_values():
    assert part_state(50) == "worn"
    assert part_state(40) == "worn"
    assert part_state(30) == "poor"
    assert part_state(15) == "poor"


def test_part_state_returns_failing_below_threshold_edge_case():
    assert part_state(14) == "failing"
    assert part_state(0) == "failing"
