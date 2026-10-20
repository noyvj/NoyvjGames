"""Tests for citizens.choose_resident()."""

import citizens


def test_choose_resident_returns_valid_tuple_when_roster_has_eligible_citizen():
    """Normal case: roster contains a citizen from an earlier era."""
    record = {"seed": 42, "roster": [{"born": "tribal"}]}
    name, trade, is_notable = citizens.choose_resident(record, "agrarian", 1)
    assert isinstance(name, str) and len(name) > 0
    assert isinstance(trade, str) and len(trade) > 0
    assert isinstance(is_notable, bool)


def test_choose_resident_returns_ordinary_when_roster_is_empty():
    """Normal case: no citizens available to choose from."""
    record = {"seed": 42, "roster": []}
    name, trade, is_notable = citizens.choose_resident(record, "tribal", 1)
    assert is_notable is False
    assert isinstance(name, str) and len(name) > 0
    assert isinstance(trade, str) and len(trade) > 0


def test_choose_resident_ignores_future_era_citizens():
    """Edge case: all citizens in roster are from future eras relative to the current era."""
    record = {"seed": 42, "roster": [{"born": "space"}, {"born": "relay"}]}
    name, trade, is_notable = citizens.choose_resident(record, "tribal", 1)
    assert is_notable is False
    assert isinstance(name, str) and len(name) > 0
    assert isinstance(trade, str) and len(trade) > 0
