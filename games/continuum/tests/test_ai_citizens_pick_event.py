"""Tests for pick_event() in citizens.py."""

import citizens


def test_pick_event_returns_highest_priority_when_present():
    kinds = {"hunger", "calm"}
    assert citizens.pick_event(kinds) == "hunger"


def test_pick_event_returns_lower_priority_when_only_that_is_present():
    kinds = {"spoil"}
    assert citizens.pick_event(kinds) == "spoil"


def test_pick_event_returns_calm_for_empty_set():
    kinds = set()
    assert citizens.pick_event(kinds) == "calm"
