"""Tests for dynasty.scenario_unlock_label()."""

import dynasty


def test_hardy_scenario_returns_correct_label():
    """The 'hardy' scenario maps to its unlocking perk's label."""
    assert dynasty.scenario_unlock_label("hardy") == "Hardier Tribe"


def test_river_scenario_returns_correct_label():
    """The 'river' scenario maps to its unlocking perk's label."""
    assert dynasty.scenario_unlock_label("river") == "River-valley Charter"


def test_nonexistent_scenario_returns_empty_string():
    """A scenario ID not in SCENARIO_UNLOCKS returns an empty string."""
    assert dynasty.scenario_unlock_label("nonexistent") == ""
