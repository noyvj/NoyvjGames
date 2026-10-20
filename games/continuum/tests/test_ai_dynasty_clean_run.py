"""Tests for dynasty.clean_run()."""

import dynasty


def test_clean_run_parses_valid_dict():
    """Normal case: a dict with all expected keys should be parsed correctly."""
    raw = {"banked": 5, "counted": True, "start": True, "failed": True}
    result = dynasty.clean_run(raw)
    assert result["banked"] == 5
    assert result["counted"] is True
    assert result["start"] is True
    assert result["failed"] is True


def test_clean_run_fills_missing_keys_with_defaults():
    """Normal case: a dict missing some keys should use defaults for those keys."""
    raw = {"banked": 10}
    result = dynasty.clean_run(raw)
    assert result["banked"] == 10
    assert result["counted"] is False
    assert result["start"] is False
    assert result["failed"] is False


def test_clean_run_returns_defaults_for_non_dict_input():
    """Edge case: non-dict input should fall back to the default record."""
    result = dynasty.clean_run(None)
    assert result == {"banked": 0, "counted": False, "start": False, "failed": False}
