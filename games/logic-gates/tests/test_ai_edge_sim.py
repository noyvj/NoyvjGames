"""Edge-case tests for sim.py."""

from chips import BASE
from net import parse_circuit
from sim import Prog, Sim, flatten


def test_flatten_with_empty_io_names():
    """flatten should handle empty in_names and out_names without error."""
    circuit = {"chips": [], "wires": {}}
    flat = flatten(circuit, dict(BASE), [], [])
    assert flat["outs"] == {}
    assert flat["top"] == {}


def test_sim_step_with_empty_inputs():
    """Sim.step should handle an empty inputs dict gracefully."""
    circuit = parse_circuit("y = not(x)", ["x"], ["y"], dict(BASE))
    prog = Prog(flatten(circuit, dict(BASE), ["x"], ["y"]), ["x"])
    sim = Sim(prog)
    result = sim.step({})
    assert result is True
    assert sim.settled is True


def test_truth_rows_zero_count():
    """truth_rows with count=0 should return bitsets of value 0."""
    circuit = parse_circuit("y = not(x)", ["x"], ["y"], dict(BASE))
    prog = Prog(flatten(circuit, dict(BASE), ["x"], ["y"]), ["x"])
    rows = prog.truth_rows({"x": 0}, 0)
    assert rows["y"] == 0


def test_sim_top_value_missing_key():
    """top_value should return 0 for a key not present in the circuit."""
    circuit = parse_circuit("y = not(x)", ["x"], ["y"], dict(BASE))
    prog = Prog(flatten(circuit, dict(BASE), ["x"], ["y"]), ["x"])
    sim = Sim(prog)
    sim.step({"x": True})
    assert sim.top_value("nonexistent") == 0
