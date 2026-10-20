"""Tests for sim.handle_incident."""

import sim
from state import Keep


def make_keep():
    k = Keep(42)
    sim.to_evening(k)
    k.log = []
    return k


def test_watch_task_clears_active_incident_and_costs_energy():
    """When the keeper is watching and time has passed since the incident started, handle_incident clears it and drains energy."""
    k = make_keep()
    k.tasks["watch"] = True
    k.energy = 5.0
    k.incident = {"kind": "smoke", "tick": 10, "expires": 20}

    sim.handle_incident(k, 11, 2, False)

    assert k.incident is None
    assert k.energy == 4.0
    assert len(k.log) > 0


def test_expired_smoke_incident_costs_oil():
    """When an incident expires and the keeper isn't watching (or time hasn't passed), it expires and smoke costs oil."""
    k = make_keep()
    k.tasks["watch"] = False
    k.energy = 5.0
    k.oil = 10.0
    k.incident = {"kind": "smoke", "tick": 5, "expires": 10}

    sim.handle_incident(k, 10, 2, False)

    assert k.incident is None
    assert k.oil == 8.0
    assert k.night_stats["unhandled"] == 1


def test_festival_night_prevents_new_incidents():
    """On a festival night, handle_incident returns early and never creates or processes incidents."""
    k = make_keep()
    k.tasks["watch"] = False
    k.incident = None

    sim.handle_incident(k, 10, 4, True)

    assert k.incident is None
    assert k.night_stats["incidents"] == 0
