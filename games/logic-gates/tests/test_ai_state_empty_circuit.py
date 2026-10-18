"""Tests for state.empty_circuit()."""

import state


def test_empty_circuit_has_chips_and_wires_keys():
    """Verify the returned dict contains the expected top-level keys."""
    circuit = state.empty_circuit()
    assert "chips" in circuit and "wires" in circuit


def test_empty_circuit_chips_is_an_empty_list():
    """Verify chips is a fresh empty list."""
    circuit = state.empty_circuit()
    assert isinstance(circuit["chips"], list) and len(circuit["chips"]) == 0


def test_empty_circuit_wires_is_an_empty_dict():
    """Verify wires is a fresh empty dict."""
    circuit = state.empty_circuit()
    assert isinstance(circuit["wires"], dict) and len(circuit["wires"]) == 0


def test_empty_circuit_returns_independent_instances():
    """Verify each call returns a new object, not shared state."""
    c1 = state.empty_circuit()
    c2 = state.empty_circuit()
    c1["chips"].append({"id": 1, "type": "and"})
    assert len(c2["chips"]) == 0
