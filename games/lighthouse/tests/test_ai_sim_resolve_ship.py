"""Tests for sim.resolve_ship()."""

import sim
from state import Keep
from data import SHIP_KINDS, DOCK_MIN, MAIL_WIND_MAX


def _make_keep():
    k = Keep(123)
    k.reputation = 0
    k.night_stats = {
        "passed": 0, "damaged": 0, "delayed": 0, "mail_landed": False,
        "events": 0, "rep": 0, "salvage": 0
    }
    k.meta = {"ships_passed": 0, "ships_damaged": 0, "ships_delayed": 0, "letters_read": {}}
    k.structure = {"dock": DOCK_MIN + 10}
    k.salvage = 0
    k.waiting = []
    k.boat_due = False
    k.log = []
    return k


def _make_ship(kind="ferry", name="TestShip"):
    base = SHIP_KINDS[kind]
    return {
        "id": f"{kind}-{name}",
        "kind": kind,
        "name": name,
        "window": 4,
        "need": 3,
        "rep": base["rep"],
        "salvage": base["salvage"],
    }


def test_passed_ship_increments_stats_and_salvage():
    keep = _make_keep()
    ship = _make_ship()
    rec = {"seen": 3, "danger": 0}
    sim.resolve_ship(keep, ship, rec, wind=1)

    assert rec["state"] == "passed"
    assert keep.night_stats["passed"] == 1
    assert keep.meta["ships_passed"] == 1
    assert keep.salvage == ship["salvage"]
    assert keep.reputation == ship["rep"]
    assert any("saw the light and went safely by" in str(entry) for entry in keep.log)


def test_mail_boat_lands_when_dock_and_wind_allow():
    keep = _make_keep()
    keep.structure["dock"] = DOCK_MIN + 5
    ship = _make_ship(kind="mail", name="MailBoat")
    rec = {"seen": 3, "danger": 0}
    sim.resolve_ship(keep, ship, rec, wind=MAIL_WIND_MAX)

    assert rec["state"] == "passed"
    assert keep.night_stats["mail_landed"] is True
    assert keep.boat_due is False
    assert any("ties up at the dock" in str(entry) for entry in keep.log)


def test_damaged_ship_is_added_to_waiting_list():
    keep = _make_keep()
    ship = _make_ship()
    rec = {"seen": 0, "danger": 2}
    sim.resolve_ship(keep, ship, rec, wind=1)

    assert rec["state"] == "damaged"
    assert keep.night_stats["damaged"] == 1
    assert keep.meta["ships_damaged"] == 1
    assert len(keep.waiting) == 1
    assert keep.waiting[0]["id"] == ship["id"]
    assert keep.reputation == 0
    assert any("lost the light in the murk" in str(entry) for entry in keep.log)
