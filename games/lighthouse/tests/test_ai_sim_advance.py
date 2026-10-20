"""Tests for sim.advance(): one tick of the night."""

import sim
from state import Keep


def make_night_keep():
    """Create a Keep object ready for the night phase."""
    k = Keep(42)
    sim.to_evening(k)
    sim.begin_night(k)
    return k


def test_advance_advances_one_tick_and_burns_oil():
    """Normal case: advance runs one tick, advances the clock, and burns oil."""
    k = make_night_keep()
    initial_tick = k.tick
    initial_oil = k.oil
    result = sim.advance(k)
    assert result is True
    assert k.tick == initial_tick + 1
    assert k.oil < initial_oil


def test_advance_with_watch_task_drains_energy():
    """Normal case: when the keeper keeps watch, energy drains by WATCH_DRAIN."""
    k = make_night_keep()
    k.tasks["watch"] = True
    initial_energy = k.energy
    sim.advance(k)
    assert k.energy == max(0.0, initial_energy - sim.WATCH_DRAIN)


def test_advance_returns_false_outside_night():
    """Edge case: advance does nothing and returns False if the phase is not night."""
    k = Keep(42)
    sim.to_evening(k)
    assert sim.advance(k) is False
    assert k.tick == 0
