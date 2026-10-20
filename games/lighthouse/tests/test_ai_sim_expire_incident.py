"""Tests for expire_incident() in sim.py."""

import sim
from state import Keep


def make_keep():
    k = Keep(1)
    k.phase = "night"
    k.tick = 5
    k.oil = 10.0
    k.structure = {"tower": 80, "lantern": 80, "rail": 80, "dock": 80, "cistern": 80}
    k.night_stats = {"unhandled": 0, "oil_used": 0.0, "damage": 0}
    k.log = []
    k.add_log = lambda kind, msg: k.log.append(msg)
    return k


def test_smoke_incident_clears_and_deducts_oil():
    """Smoke incident expires: clears incident, deducts 2 oil, updates stats and log."""
    k = make_keep()
    k.incident = {"kind": "smoke", "tick": 0, "expires": 5}
    sim.expire_incident(k)
    assert k.incident is None
    assert k.night_stats["unhandled"] == 1
    assert k.oil == 8.0
    assert k.night_stats["oil_used"] == 2.0
    assert any("The smoke clears by itself" in msg for msg in k.log)


def test_shutter_incident_clears_and_damages_structure():
    """Shutter incident expires: clears incident, damages rail and lantern, updates stats and log."""
    k = make_keep()
    k.incident = {"kind": "shutter", "tick": 0, "expires": 5}
    sim.expire_incident(k)
    assert k.incident is None
    assert k.night_stats["unhandled"] == 1
    assert k.structure["rail"] == 77
    assert k.structure["lantern"] == 78
    assert k.night_stats["damage"] == 5
    assert any("The loose shutter banged" in msg for msg in k.log)


def test_smoke_incident_with_low_oil_uses_available_oil():
    """Edge case: smoke incident with less than 2 oil deducts all available oil."""
    k = make_keep()
    k.oil = 1.0
    k.incident = {"kind": "smoke", "tick": 0, "expires": 5}
    sim.expire_incident(k)
    assert k.incident is None
    assert k.night_stats["unhandled"] == 1
    assert k.oil == 0.0
    assert k.night_stats["oil_used"] == 1.0
