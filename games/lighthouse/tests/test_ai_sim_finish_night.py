"""Tests for sim.finish_night(). Verifies report generation, counter updates, delivery logic, and edge cases."""

import sim
import clock
from state import Keep


def test_finish_night_normal_case_updates_report_and_counters():
    """A standard night completes: report is built, nights_kept increments, oil_used accumulates."""
    k = Keep(123)
    sim.to_evening(k)
    sim.begin_night(k)

    length = clock.night_len(k.night)
    for _ in range(length):
        sim.advance(k)

    report = k.report
    assert report is not None
    assert report["night"] == k.night
    assert "summary" in report
    assert "ships" in report
    assert "lamp_hours" in report
    assert "oil_used" in report
    assert "damage" in report
    assert k.meta["nights_kept"] > 0
    assert k.meta["year_lamp_ticks"] > 0


def test_finish_night_accumulates_oil_correctly():
    """Oil used during the night is added to the meta total, preserving precision."""
    k = Keep(456)
    sim.to_evening(k)
    sim.begin_night(k)

    initial_oil_used = k.meta["oil_used"]

    length = clock.night_len(k.night)
    for _ in range(length):
        sim.advance(k)

    report = k.report
    assert report is not None
    # The meta total should be the initial amount plus what was used this night
    assert k.meta["oil_used"] == initial_oil_used + report["oil_used"]


def test_finish_night_edge_case_no_food_sets_hungry():
    """When food supplies are empty at dawn, keep.hungry becomes True and food stays zero."""
    k = Keep(789)
    sim.to_evening(k)
    sim.begin_night(k)
    k.supplies["food"] = 0

    length = clock.night_len(k.night)
    for _ in range(length):
        sim.advance(k)

    assert k.hungry is True
    assert k.supplies["food"] == 0
