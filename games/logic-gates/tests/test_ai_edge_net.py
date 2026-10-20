"""Edge-case tests for net.py circuit and step parsers."""

import pytest

from levels import BY_ID, REGISTRY
from net import parse_circuit, parse_steps


def test_parse_circuit_empty_text_returns_empty_circuit():
    """Empty circuit text yields an empty board structure."""
    lv = BY_ID["both"]
    result = parse_circuit("", lv["ins"], lv["outs"], REGISTRY)
    assert result == {"chips": [], "wires": {}}


def test_parse_circuit_rejects_unknown_output_name():
    """Assigning to an output not in the level's list raises ValueError."""
    lv = BY_ID["both"]
    with pytest.raises(ValueError) as exc_info:
        parse_circuit("Z := A", lv["ins"], lv["outs"], REGISTRY)
    assert "Z is not an output" in str(exc_info.value)


def test_parse_circuit_rejects_unknown_input_name_in_chip_args():
    """Referencing an input not in the level's list raises ValueError."""
    lv = BY_ID["both"]
    with pytest.raises(ValueError) as exc_info:
        parse_circuit("n = not(Z)", lv["ins"], lv["outs"], REGISTRY)
    assert "unknown name Z" in str(exc_info.value)


def test_parse_circuit_rejects_wrong_argument_count():
    """Passing too many arguments to a chip raises ValueError."""
    lv = BY_ID["both"]
    with pytest.raises(ValueError) as exc_info:
        parse_circuit("n = not(A, B)", lv["ins"], lv["outs"], REGISTRY)
    assert "takes 1 inputs" in str(exc_info.value)


def test_parse_steps_empty_text_returns_empty_list():
    """Empty step text yields an empty list of steps."""
    result = parse_steps("", ["A", "B"], ["Y"])
    assert result == []


def test_parse_steps_rejects_invalid_value():
    """Step inputs must be 0 or 1; other values raise ValueError."""
    with pytest.raises(ValueError) as exc_info:
        parse_steps("A=2", ["A", "B"], ["Y"])
    assert "bad input assignment A=2" in str(exc_info.value)
