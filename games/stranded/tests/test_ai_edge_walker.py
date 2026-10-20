"""Tests for edge cases in walker.py."""

import walker


def test_initial_returns_valid_structure():
    """initial returns a state tuple and a found list without crashing."""
    state, found = walker.initial()
    assert isinstance(state, tuple) and len(state) == 3
    assert isinstance(found, list)


def test_available_handles_boolean_out_of_range_and_non_int_inputs():
    """available correctly rejects booleans, out-of-range integers, and non-integers."""
    state, _ = walker.initial()

    # Boolean should be rejected because bool is a subclass of int
    ok_bool, why_bool = walker.available(state, True)
    assert ok_bool is False

    # Out of range (negative and too large)
    scene = walker.scene_of(state)
    ok_neg, _ = walker.available(state, -1)
    assert ok_neg is False
    ok_large, _ = walker.available(state, len(scene["choices"]) + 10)
    assert ok_large is False

    # Non-integer types should be rejected gracefully
    for bad_idx in ["0", None]:
        result = walker.available(state, bad_idx)
        assert isinstance(result, tuple) and len(result) == 2
        assert isinstance(result[0], bool) and isinstance(result[1], str)


def test_step_returns_none_on_invalid_index():
    """step returns (None, info) when the index is out of range or invalid."""
    state, _ = walker.initial()
    nxt, info = walker.step(state, 999)
    assert nxt is None
    assert isinstance(info, dict) and "why" in info


def test_replay_handles_empty_and_invalid_inputs():
    """replay returns a valid result for empty string and None for invalid paths."""
    # Empty path should succeed with zero steps
    result_empty = walker.replay("")
    assert result_empty is not None
    steps, _, _ = result_empty
    assert len(steps) == 0

    # Non-digit characters should be rejected
    assert walker.replay("1a2") is None

    # Path with index out of bounds should be rejected
    assert walker.replay("99") is None


def test_visible_handles_empty_lines():
    """visible returns an empty list when given no lines to filter."""
    state, _ = walker.initial()
    result = walker.visible([], state)
    assert result == []


def test_holds_with_none_condition():
    """holds returns True unconditionally when the condition is None."""
    state, _ = walker.initial()
    assert walker.holds(None, state) is True
