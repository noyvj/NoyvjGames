"""Tests for state.clean_circuit(). Validates filtering of untrusted circuit data."""

import state


def test_valid_circuit_passes_through():
    """Normal case: valid chips and wires are kept exactly as provided."""
    level = {"id": "lvl", "ins": ["A"], "outs": ["X"], "cap": 10, "loops": False}
    allowed = ["and", "or"]
    data = {
        "chips": [{"id": 1, "type": "and"}],
        "wires": {"out:X": "in:A"}
    }
    result = state.clean_circuit(data, level, allowed)
    assert result["chips"] == [{"id": 1, "type": "and"}]
    assert result["wires"] == {"out:X": "in:A"}


def test_invalid_chips_and_wires_are_dropped():
    """Normal case: bad types, duplicate IDs, out-of-range IDs, and invalid wire endpoints are silently dropped."""
    level = {"id": "lvl", "ins": ["A", "B"], "outs": ["X"], "cap": 10, "loops": False}
    allowed = ["and", "or"]
    data = {
        "chips": [
            {"id": 1, "type": "and"},       # valid
            {"id": 2, "type": "xor"},       # invalid type
            {"id": 1, "type": "or"},        # duplicate id
            {"id": 0, "type": "and"},       # id out of range
            {"id": True, "type": "or"},     # bool id
            {"id": 3, "type": "and"}        # valid
        ],
        "wires": {
            "out:X": "in:A",                # valid
            "out:Y": "in:B",                # invalid dest (Y not in outs)
            "in:A": "const:1"               # invalid dest (in: not allowed)
        }
    }
    result = state.clean_circuit(data, level, allowed)
    assert len(result["chips"]) == 2
    assert result["chips"][0]["id"] == 1
    assert result["chips"][1]["id"] == 3
    assert result["wires"] == {"out:X": "in:A"}


def test_loop_detection_drops_creating_wire():
    """Edge case: when a level forbids loops, the wire that completes a cycle is removed."""
    level = {"id": "lvl", "ins": ["A"], "outs": ["X"], "cap": 10, "loops": False}
    allowed = ["and"]
    data = {
        "chips": [
            {"id": 1, "type": "and"},
            {"id": 2, "type": "and"}
        ],
        "wires": {
            "1.A": "in:A",                  # valid
            "2.A": "1.Y"                    # valid, no loop yet
        }
    }
    # Add a wire that would create a loop: 1.A <- 2.Y
    data["wires"]["1.A"] = "2.Y"
    result = state.clean_circuit(data, level, allowed)
    assert result["wires"].get("2.A") is None  # dropped due to loop (processed second)
    assert result["wires"].get("1.A") == "2.Y"  # kept
