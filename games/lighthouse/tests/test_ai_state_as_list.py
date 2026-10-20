"""Tests for as_list() in state.py."""

from state import as_list


def test_as_list_returns_the_input_when_it_is_already_a_list():
    original = [1, 2, 3]
    assert as_list(original) is original


def test_as_list_returns_empty_list_for_non_list_inputs():
    assert as_list({}) == []
    assert as_list("hello") == []
    assert as_list(42) == []


def test_as_list_handles_none_gracefully():
    assert as_list(None) == []
