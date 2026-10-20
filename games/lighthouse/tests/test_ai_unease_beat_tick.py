"""Tests for unease.beat_tick()."""

import clock
import unittest.mock as mock
import unease


def test_beat_tick_morning_returns_minus_one():
    """A morning beat always returns -1 regardless of the night."""
    assert unease.beat_tick(10, "morning") == -1


def test_beat_tick_dusk_and_deep():
    """Dusk and deep night ticks follow their fractions of night length."""
    for phase, frac in unease.AT_FRACTION.items():
        if phase == "dawn":
            continue
        n = 20
        nl = clock.night_len(n)
        expected = min(nl - 2, int(nl * frac))
        assert unease.beat_tick(n, phase) == expected


def test_beat_tick_dawn():
    """Dawn tick is 86% of night length."""
    n = 30
    nl = clock.night_len(n)
    expected = min(nl - 2, int(nl * unease.AT_FRACTION["dawn"]))
    assert unease.beat_tick(n, "dawn") == expected


def test_beat_tick_caps_at_night_length_minus_two():
    """When the fraction times night length exceeds night_len - 2, it should cap."""
    with mock.patch("unease.night_len", return_value=5):
        assert unease.beat_tick(1, "dawn") == 3
