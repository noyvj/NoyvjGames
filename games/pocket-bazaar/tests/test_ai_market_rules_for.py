"""Tests for market.rules_for() (M-4b-9)."""

import pytest

import market


def test_rules_for_returns_a_dict_with_the_correct_festival():
    """rules_for reconstructs the day rules from a date and includes the festival name."""
    date = "2026-10-05"
    expected_fest = market.spec(date)["festival"]
    rules = market.rules_for(date)
    assert isinstance(rules, dict)
    assert rules["festival"] == expected_fest


def test_rules_for_matches_different_dates():
    """Different dates produce rules with their respective festivals."""
    for date in ("2026-10-01", "2026-10-15", "2027-01-01"):
        expected_fest = market.spec(date)["festival"]
        rules = market.rules_for(date)
        assert rules["festival"] == expected_fest


def test_rules_for_raises_on_invalid_date():
    """rules_for delegates to spec, so invalid dates should raise ValueError."""
    with pytest.raises(ValueError):
        market.rules_for("not-a-date")
