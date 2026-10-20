"""Tests for unease.beats_on()."""

import unease
from data import NIGHTS_PER_YEAR


def test_beats_on_returns_empty_for_night_one():
    """Night 1 has no beats scheduled."""
    assert unease.beats_on(2, 1) == []


def test_beats_on_returns_correct_beats_for_a_scheduled_night():
    """A night that has a beat scheduled returns it correctly."""
    seed = 2
    plan = unease.schedule(seed)
    # Find a night that actually has beats
    nights_with_beats = set(plan.values())
    assert len(nights_with_beats) > 0
    target_night = min(nights_with_beats)
    result = unease.beats_on(seed, target_night)
    assert isinstance(result, list)
    # Verify each returned beat belongs to the target night
    for mid, beat in result:
        assert plan[beat["id"]] == target_night


def test_beats_on_returns_empty_for_night_beyond_year():
    """Nights beyond the year return an empty list."""
    assert unease.beats_on(2, NIGHTS_PER_YEAR + 1) == []
