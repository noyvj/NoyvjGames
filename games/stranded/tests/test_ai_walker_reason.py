"""Tests for walker.reason() function."""

import walker


def test_reason_returns_empty_string_for_none_condition():
    """reason returns empty string when condition is None."""
    state, _ = walker.initial()
    assert walker.reason(None, state) == ""


def test_reason_returns_empty_string_when_condition_holds():
    """reason returns empty string when all requirements are met."""
    state, _ = walker.initial()
    # Provide all expected keys to avoid KeyError in holds(), with empty collections.
    cond = {"all": [], "none": [], "min": {}, "max": {}}
    assert walker.reason(cond, state) == ""


def test_reason_returns_message_for_missing_flag():
    """reason returns a 'Needs' message when a required flag is missing."""
    state, _ = walker.initial()
    cond = {"all": ["missing_flag"], "none": [], "min": {}, "max": {}}
    result = walker.reason(cond, state)
    assert result.startswith("Needs missing_flag")


def test_reason_joins_multiple_failures():
    """reason joins multiple failure reasons with semicolons when several requirements fail."""
    state, _ = walker.initial()
    cond = {"all": ["flag_a", "flag_b"], "none": [], "min": {}, "max": {}}
    result = walker.reason(cond, state)
    assert "Needs flag_a" in result
    assert "Needs flag_b" in result
    assert "; " in result
