"""Tests for Prog.run_pass() in sim.py."""

from chips import BASE
from net import parse_circuit
from sim import Prog, flatten


def _make_prog(net_text, in_names, out_names):
    reg = dict(BASE)
    circ = parse_circuit(net_text, in_names, out_names, reg)
    flat = flatten(circ, reg, in_names, out_names)
    return Prog(flat, in_names)


def test_and_gate_across_rows():
    """run_pass correctly computes AND across multiple truth-table rows using bitsets."""
    prog = _make_prog("y = and(A, B)", ["A", "B"], ["y"])
    mask = 0b11  # 2 rows: 00, 01
    vals = [0] * prog.size
    vals[1] = mask
    vals[prog.idx["in:A"]] = 0b01  # A is 1 at row 0, 0 at row 1
    vals[prog.idx["in:B"]] = 0b10  # B is 0 at row 0, 1 at row 1
    prog.run_pass(vals, mask)
    assert vals[prog.outs["y"]] == 0b00  # AND(1,0)=0, AND(0,1)=0


def test_single_row_edge_case():
    """run_pass works correctly with a single truth-table row (count=1)."""
    prog = _make_prog("y = and(A, B)", ["A", "B"], ["y"])
    mask = 0b1  # 1 row: 0
    vals = [0] * prog.size
    vals[1] = mask
    vals[prog.idx["in:A"]] = 0  # A is 0
    vals[prog.idx["in:B"]] = 0  # B is 0
    prog.run_pass(vals, mask)
    assert vals[prog.outs["y"]] == 0  # AND(0,0) = 0
