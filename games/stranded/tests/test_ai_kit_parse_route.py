"""Tests for kit.parse_route()."""

import pytest

import kit


def test_single_string_returns_one_tuple():
    result = kit.parse_route("d2d")
    assert result == ((None, "d2d"),)


def test_list_with_conditions_and_default():
    routes = ("bit>d2d", "!bit>d3a", "d4b")
    result = kit.parse_route(routes)
    assert len(result) == 3
    assert result[0] == (kit.parse_cond("bit"), "d2d")
    assert result[1] == (kit.parse_cond("!bit"), "d3a")
    assert result[2] == (None, "d4b")


def test_last_item_with_condition_raises_value_error():
    with pytest.raises(ValueError):
        kit.parse_route(("bit>d2d", "!bit>d3a", "cond>d4b"))
