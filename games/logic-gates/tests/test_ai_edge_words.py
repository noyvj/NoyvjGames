"""Edge-case tests for words.py."""

import words
from levels import REGISTRY


def test_chip_name_returns_label_for_known_type():
    chip = {"type": "and"}
    assert words.chip_name(chip) == REGISTRY["and"]["label"]


def test_chip_name_returns_type_for_unknown_type():
    chip = {"type": "nonexistent_gate"}
    assert words.chip_name(chip) == "nonexistent_gate"


def test_src_label_handles_empty_string():
    circuit = {"chips": [], "wires": {}}
    assert words.src_label("", circuit) == "nothing"


def test_src_label_handles_none():
    circuit = {"chips": [], "wires": {}}
    assert words.src_label(None, circuit) == "nothing"


def test_src_label_handles_in_switch():
    circuit = {"chips": [], "wires": {}}
    assert words.src_label("in:A", circuit) == "switch A"


def test_src_label_handles_const_tie():
    circuit = {"chips": [], "wires": {}}
    assert words.src_label("const:1", circuit) == "a wire tied to 1"


def test_src_label_handles_missing_chip_id():
    circuit = {"chips": [{"id": "u1", "type": "and"}], "wires": {}}
    assert words.src_label("u2.out", circuit) == "nothing"


def test_src_label_handles_known_chip_single_output():
    chip_type = "not"
    reg_entry = REGISTRY[chip_type]
    circuit = {"chips": [{"id": "u1", "type": chip_type}], "wires": {}}
    label = words.src_label("u1.out", circuit)
    expected_suffix = " output out" if len(reg_entry["outs"]) > 1 else ""
    assert label == f"chip u1 ({reg_entry['label']}){expected_suffix}"


def test_src_label_handles_known_chip_multi_output():
    chip_type = "sr"
    reg_entry = REGISTRY[chip_type]
    circuit = {"chips": [{"id": "u1", "type": chip_type}], "wires": {}}
    label = words.src_label("u1.Q", circuit)
    assert label == f"chip u1 ({reg_entry['label']}) output Q"


def test_describe_empty_inputs():
    circuit = {"chips": [], "wires": {}}
    outs = []
    assert words.describe(circuit, outs) == []


def test_describe_skips_unknown_chips():
    circuit = {"chips": [{"id": "u1", "type": "fake_chip"}], "wires": {}}
    outs = ["A"]
    result = words.describe(circuit, outs)
    assert len(result) == 1
    assert result[0].startswith("Lamp A from")


def test_describe_handles_missing_wire_for_lamp():
    circuit = {"chips": [], "wires": {}}
    outs = ["X"]
    result = words.describe(circuit, outs)
    assert "nothing" in result[0]
