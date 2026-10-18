"""Tests for src_label() in words.py."""

import levels
from words import src_label


def test_src_label_formats_switch_source():
    circuit = levels.LEVELS[0]["ref"]
    assert src_label("in:A", circuit) == "switch A"


def test_src_label_formats_tie_source():
    circuit = levels.LEVELS[0]["ref"]
    assert src_label("const:1", circuit) == "a wire tied to 1"


def test_src_label_formats_chip_reference():
    # Use a minimal circuit matching the game's data format.
    circuit = {"chips": [{"id": 1, "type": "and"}], "wires": {}}
    result = src_label("1.A", circuit)
    assert result.startswith("chip 1 (")


def test_src_label_returns_nothing_for_edge_cases():
    circuit = levels.LEVELS[0]["ref"]
    assert src_label("", circuit) == "nothing"
    assert src_label(None, circuit) == "nothing"
    assert src_label("99.A", circuit) == "nothing"
