"""Tests for day.rescue_cost()."""

import day
import sim
from state import Keep


def keep_at(night=1, seed=3):
    k = Keep(seed)
    k.night = night
    sim.to_evening(k)
    return k


def test_rescue_cost_without_boat_upgrade():
    """Without the boat upgrade, rescue costs timber and tar."""
    k = keep_at()
    assert day.rescue_cost(k) == {"timber": 1, "tar": 1}


def test_rescue_cost_with_boat_upgrade():
    """With the boat upgrade, rescue costs only timber."""
    k = keep_at()
    k.upgrades.append("boat")
    assert day.rescue_cost(k) == {"timber": 1}


def test_rescue_cost_edge_case_other_upgrades_present():
    """Having other upgrades does not affect the cost if boat is missing."""
    k = keep_at()
    k.upgrades.extend(["wick", "glass"])
    assert day.rescue_cost(k) == {"timber": 1, "tar": 1}
