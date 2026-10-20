"""Edge-case tests for kit.py builders and parsers."""

import pytest

import kit


def test_parse_fx_empty_string():
    """Empty string returns zero deltas."""
    assert kit.parse_fx("") == (0, 0, 0)


def test_parse_fx_large_deltas():
    """Large positive and negative deltas are summed correctly by parse_fx (clamping happens in the walker)."""
    assert kit.parse_fx("t+100 h-50") == (100, 0, -50)


def test_parse_cond_empty_and_none():
    """Empty or None input returns None."""
    assert kit.parse_cond("") is None
    assert kit.parse_cond(None) is None


def test_parse_cond_invalid_token_rejected():
    """Invalid condition token raises ValueError."""
    with pytest.raises(ValueError, match="bad condition"):
        kit.parse_cond("bit&123")


def test_parse_route_single_scene():
    """Single string route returns one tuple with no condition."""
    result = kit.parse_route("d3a")
    assert len(result) == 1
    assert result[0] == (None, "d3a")


def test_parse_route_invalid_last_condition_rejected():
    """Last route in a list must not have a condition; raises ValueError."""
    with pytest.raises(ValueError, match="the last route needs no condition"):
        kit.parse_route(["t4>d2a", "!bit>d3b"])


def test_C_builder_structure():
    """C() correctly parses reply, to, fx, need, set, get."""
    c = kit.C("Hello", "Reply!", "d2a", "t+1", "bit", "flag1 flag2", "item1")
    assert c["text"] == "Hello"
    assert c["reply"] == [(None, "Reply!")]
    assert c["to"] == ((None, "d2a"),)
    assert c["fx"] == (1, 0, 0)
    assert c["need"] == {"all": ["bit"], "none": [], "min": {}, "max": {}}
    assert c["set"] == ("flag1", "flag2")
    assert c["get"] == ("item1",)


def test_S_builder_structure():
    """S() correctly parses lines, fx, set, get and wraps choices."""
    s = kit.S("d1a", 1, "Start", ["?bit|Hidden", "Visible"], fx="h-2", set="s1", get="g1")
    assert s["id"] == "d1a"
    assert s["day"] == 1
    assert s["title"] == "Start"
    assert len(s["lines"]) == 2
    assert s["lines"][0] == ({"all": ["bit"], "none": [], "min": {}, "max": {}}, "Hidden")
    assert s["lines"][1] == (None, "Visible")
    assert s["fx"] == (0, 0, -2)
    assert s["set"] == ("s1",)
    assert s["get"] == ("g1",)
