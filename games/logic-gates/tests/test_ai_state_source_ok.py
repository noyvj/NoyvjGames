"""Tests for state.source_ok(): validates wire sources against level inputs/constants and circuit chips."""

import levels
import state


def test_input_source_matches_level_inputs():
    """Normal case: valid input names from the level are accepted."""
    level = levels.LEVELS[0]
    circuit = {"chips": [], "wires": {}}
    assert state.source_ok(f"in:{level['ins'][0]}", circuit, level) is True


def test_constant_source_accepts_zero_and_one():
    """Normal case: tied wires to 0 or 1 are accepted."""
    level = levels.LEVELS[0]
    circuit = {"chips": [], "wires": {}}
    assert state.source_ok("const:0", circuit, level) is True
    assert state.source_ok("const:1", circuit, level) is True


def test_non_string_source_returns_false():
    """Edge case: sources that are not strings are rejected immediately."""
    level = levels.LEVELS[0]
    circuit = {"chips": [], "wires": {}}
    assert state.source_ok(42, circuit, level) is False
    assert state.source_ok(None, circuit, level) is False
