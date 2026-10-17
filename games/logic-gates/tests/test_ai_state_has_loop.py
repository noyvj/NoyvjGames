"""Tests for state.has_loop()."""


import state


def test_no_loop_simple_chain():
    """A straight wire from one chip to another should not be detected as a loop."""
    level = state.level_view("straight-through")
    circuit = {"chips": [{"id": 1, "type": "and"}, {"id": 2, "type": "or"}], "wires": {}}
    circuit["wires"]["2.A"] = "1.Y"
    assert state.has_loop(circuit, level) is False


def test_has_loop_two_chips_cycle():
    """Two chips feeding each other's inputs should be detected as a loop."""
    level = state.level_view("straight-through")
    circuit = {"chips": [{"id": 1, "type": "and"}, {"id": 2, "type": "or"}], "wires": {}}
    circuit["wires"]["2.A"] = "1.Y"
    circuit["wires"]["1.A"] = "2.Y"
    assert state.has_loop(circuit, level) is True


def test_no_loop_single_chip():
    """Edge case: a single chip with no wires should not have a loop."""
    level = state.level_view("straight-through")
    circuit = {"chips": [{"id": 1, "type": "and"}], "wires": {}}
    assert state.has_loop(circuit, level) is False
