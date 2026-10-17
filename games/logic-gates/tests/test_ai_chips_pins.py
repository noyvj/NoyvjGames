"""Tests for pins() in chips.py."""

from chips import BASE, pins


def test_pins_standard_gate_order():
    """A standard gate should list inputs first, then outputs."""
    assert pins(BASE["and"]) == ["A", "B", "Y"]


def test_pins_memory_cell_order():
    """A memory cell with multiple inputs and outputs should preserve order."""
    assert pins(BASE["sr"]) == ["S", "R", "Q", "QN"]


def test_pins_single_input_output():
    """An edge case: a chip with exactly one input and one output."""
    assert pins(BASE["not"]) == ["A", "Y"]
