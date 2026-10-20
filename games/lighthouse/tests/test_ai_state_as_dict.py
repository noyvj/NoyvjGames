"""Tests for as_dict() in state.py."""

from state import as_dict


def test_as_dict_returns_the_same_dict_when_input_is_a_dict():
    """Passing a dict returns that exact dict object."""
    original = {"levels": [1, 1, 1], "tasks": {"wind": True}}
    assert as_dict(original) is original


def test_as_dict_returns_an_empty_dict_when_input_is_none():
    """Passing None (common when .get() misses a key) returns {}."""
    assert as_dict(None) == {}


def test_as_dict_returns_an_empty_dict_for_non_dict_types_edge_case():
    """Passing a non-dict type like a list or string safely falls back to {}."""
    assert as_dict([1, 2]) == {}
    assert as_dict("not a dict") == {}
