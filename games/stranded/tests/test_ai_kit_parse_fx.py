"""Tests for kit.parse_fx() - parsing stat deltas from text strings."""

import kit


def test_parse_fx_normal_cases():
    """Test normal parsing of stat deltas."""
    assert kit.parse_fx("t1 h-2 s1") == (1, 1, -2)
    assert kit.parse_fx("t+1 s+2 h+3") == (1, 2, 3)
    assert kit.parse_fx("t-1 s-2 h-3") == (-1, -2, -3)


def test_parse_fx_edge_case_empty_string():
    """Test edge case: empty string should return zeros."""
    assert kit.parse_fx("") == (0, 0, 0)


def test_parse_fx_invalid_token_raises():
    """Test that invalid tokens raise ValueError."""
    try:
        kit.parse_fx("t1 invalid")
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "bad fx" in str(e)
