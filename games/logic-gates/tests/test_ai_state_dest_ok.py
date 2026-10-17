"""Tests for state.dest_ok: validates destination strings against level outputs and circuit chips."""

import state


def test_dest_ok_accepts_valid_output_destination():
    """A destination starting with 'out:' is valid if its suffix matches a level output."""
    level = {"outs": ["X", "Y"]}
    assert state.dest_ok("out:X", {"chips": []}, level) is True
    assert state.dest_ok("out:Z", {"chips": []}, level) is False


def test_dest_ok_accepts_valid_chip_input_destination():
    """A destination '<id>.<pin>' is valid if the chip exists in the circuit and the pin is an input."""
    circuit = {"chips": [{"id": 1, "type": "and"}]}
    level = {"outs": ["X"]}
    assert state.dest_ok("1.A", circuit, level) is True


def test_dest_ok_rejects_non_string_destination():
    """dest_ok returns False immediately if the destination is not a string."""
    level = {"outs": ["X"]}
    assert state.dest_ok(123, {"chips": []}, level) is False
    assert state.dest_ok(None, {"chips": []}, level) is False
