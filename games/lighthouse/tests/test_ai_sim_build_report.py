"""Tests for sim.build_report()."""

import sim


class MockKeep:
    """Minimal mock of Keep providing only what build_report needs."""

    def __init__(self, night=1):
        self.night = night
        self.night_stats = {
            "dark": False, "stopped": False, "damage": 0, "incidents": 0,
            "worst_cond": 0, "lamp_ticks": 0, "oil_used": 0.0, "rep": 0,
            "salvage": 0, "passed": 0, "delayed": 0, "damaged": 0,
        }


def test_build_report_mixed_outcomes():
    keep = MockKeep(night=5)
    keep.night_stats["lamp_ticks"] = 60
    keep.night_stats["oil_used"] = 2.5
    keep.night_stats["damage"] = 3
    keep.night_stats["incidents"] = 1
    keep.night_stats["worst_cond"] = 3
    keep.night_stats["passed"] = 1
    keep.night_stats["delayed"] = 1

    outcomes = [
        {"name": "Ship A", "kind": "ferry", "outcome": "passed"},
        {"name": "Ship B", "kind": "ferry", "outcome": "delayed"}
    ]

    report = sim.build_report(keep, outcomes, quiet=False)
    assert report["summary"] == "1 of 2 ships got safely by."
    assert report["lamp_hours"] == round(60 * sim.data.TICK_MINUTES / 60.0, 1)
    assert report["damage"] == 3
    assert report["incidents"] == 1
    assert report["worst"] == 3
    assert "The weather and the wind took 3 points off the station." in report["lines"]
    assert "1 small trouble in the night." in report["lines"]


def test_build_report_clean_night():
    keep = MockKeep(night=10)
    keep.night_stats["lamp_ticks"] = 30
    keep.night_stats["oil_used"] = 1.0
    keep.night_stats["damage"] = 0
    keep.night_stats["incidents"] = 0
    keep.night_stats["worst_cond"] = 1

    outcomes = [
        {"name": "Ship C", "kind": "ferry", "outcome": "passed"},
        {"name": "Ship D", "kind": "ferry", "outcome": "passed"}
    ]

    report = sim.build_report(keep, outcomes, quiet=True)
    assert report["summary"] == "Every ship that came by found the light."
    assert report["quiet"] is True
    assert report["lines"] == []


def test_build_report_no_outcomes():
    keep = MockKeep(night=1)

    report = sim.build_report(keep, [], quiet=False)
    assert report["summary"] == "No ships came by tonight. You kept the light anyway."
    assert report["ships"] == []
