"""Tests for sim.tired()."""

import sim
from state import Keep


def test_tired_returns_false_when_energy_is_sufficient():
    k = Keep(1)
    sim.to_evening(k)
    k.energy = sim.TIRED
    assert not sim.tired(k)


def test_tired_returns_true_when_energy_is_below_threshold():
    k = Keep(1)
    sim.to_evening(k)
    k.energy = sim.TIRED - 0.5
    assert sim.tired(k)


def test_tired_edge_case_at_exact_threshold_plus_epsilon():
    k = Keep(1)
    sim.to_evening(k)
    k.energy = sim.TIRED + 0.1
    assert not sim.tired(k)
