"""Tests for plan.clean_burn()."""


import plan as planlib


def test_valid_burn_returns_cleaned_dict():
    """A properly formed burn dict is returned with t cast to int and values clamped."""
    raw = {"t": 10, "at": "peri", "head": 45.0, "dv": 1.234}
    result = planlib.clean_burn(raw, 100)
    assert result == {"t": 10, "at": "peri", "head": 45.0, "dv": 1.234}


def test_missing_optional_fields_defaults_correctly():
    """When at, head, or dv are omitted, clean_burn falls back to 'time', 0.0, and 0.0."""
    raw = {"t": 5}
    result = planlib.clean_burn(raw, 100)
    assert result == {"t": 5, "at": "time", "head": 0.0, "dv": 0.0}


def test_boolean_t_returns_none():
    """Edge case: t is a boolean (True/False) should be rejected because bool is a subclass of int."""
    raw = {"t": True, "at": "time", "head": 0.0, "dv": 0.0}
    assert planlib.clean_burn(raw, 100) is None
