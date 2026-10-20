"""Tests for view.ship_view."""

import data
import sim
from state import Keep
from view import ship_view

# Valid ship kinds from the game's data
_VALID_KIND = list(data.SHIP_KINDS.keys())[0]


def keep_at(night=1, seed=3):
    k = Keep(seed)
    k.night = night
    sim.to_evening(k)
    return k


def test_pending_ship_before_arrival():
    """A ship that hasn't arrived yet shows pending state, not present, and not lit."""
    k = keep_at(1)
    sim.begin_night(k)
    ship = {"id": "s1", "kind": _VALID_KIND, "name": "Test Ship", "arrive": 50, "window": 20, "need": 7}
    v = ship_view(k, ship, k.tick, reach=9)
    assert v["state"] == "pending"
    assert v["present"] is False
    assert v["lit"] is False
    assert v["arrived"] is False


def test_ship_in_window_with_sufficient_reach():
    """A ship in its arrival window with pending state shows present and lit when reach >= need."""
    k = keep_at(1)
    sim.begin_night(k)
    ship = {"id": "s2", "kind": _VALID_KIND, "name": "Passing Ship", "arrive": 40, "window": 20, "need": 5}
    k.tick = ship["arrive"] + 5
    k.progress[ship["id"]] = {"state": "pending", "seen": 1}

    v = ship_view(k, ship, k.tick, reach=6)
    assert v["present"] is True
    assert v["lit"] is True
    assert v["pos"] == round((k.tick - ship["arrive"]) / float(ship["window"] - 1), 3)


def test_ship_in_window_with_insufficient_reach():
    """A ship in its arrival window shows present but not lit when reach < need."""
    k = keep_at(1)
    sim.begin_night(k)
    ship = {"id": "s3", "kind": _VALID_KIND, "name": "Dim Ship", "arrive": 40, "window": 20, "need": 7}
    k.tick = ship["arrive"] + 5
    k.progress[ship["id"]] = {"state": "pending", "seen": 1}

    v = ship_view(k, ship, k.tick, reach=5)
    assert v["present"] is True
    assert v["lit"] is False


def test_ship_not_present_outside_night_phase():
    """Even if a ship has pending state and is in its window, it should not be present outside night phase."""
    k = keep_at(1)
    sim.to_evening(k)  # Phase is evening
    ship = {"id": "s4", "kind": _VALID_KIND, "name": "Evening Ship", "arrive": 40, "window": 20, "need": 5}
    k.progress[ship["id"]] = {"state": "pending", "seen": 1}

    v = ship_view(k, ship, k.tick, reach=9)
    assert v["present"] is False
    assert v["lit"] is False
