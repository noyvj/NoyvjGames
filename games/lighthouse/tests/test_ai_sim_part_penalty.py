"""Tests for sim.part_penalty()."""

import sim
from state import Keep


def test_penalty_is_two_when_lantern_structure_is_below_25():
    k = Keep(1)
    sim.to_evening(k)
    k.structure["lantern"] = 24
    assert sim.part_penalty(k) == 2


def test_penalty_is_one_when_lantern_structure_is_between_25_and_49():
    k = Keep(1)
    sim.to_evening(k)
    k.structure["lantern"] = 30
    assert sim.part_penalty(k) == 1


def test_penalty_is_zero_at_the_fifty_threshold():
    k = Keep(1)
    sim.to_evening(k)
    k.structure["lantern"] = 50
    assert sim.part_penalty(k) == 0
