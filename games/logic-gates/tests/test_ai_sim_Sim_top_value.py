"""Tests for Sim.top_value()."""

from chips import BASE
from net import parse_circuit
from sim import Prog, Sim, flatten


def test_top_value_returns_chip_output():
    reg = dict(BASE)
    circ = parse_circuit("x = and(a, b); out := x.Y", ["a", "b"], ["out"], reg)
    prog = Prog(flatten(circ, reg, ["a", "b"], ["out"]), ["a", "b"])
    sim = Sim(prog)
    sim.step({"a": True, "b": False})
    assert sim.top_value("1.Y") == 0


def test_top_value_returns_chip_output_true():
    reg = dict(BASE)
    circ = parse_circuit("x = and(a, b); out := x.Y", ["a", "b"], ["out"], reg)
    prog = Prog(flatten(circ, reg, ["a", "b"], ["out"]), ["a", "b"])
    sim = Sim(prog)
    sim.step({"a": True, "b": True})
    assert sim.top_value("1.Y") == 1


def test_top_value_returns_zero_for_unknown_key():
    reg = dict(BASE)
    circ = parse_circuit("x = and(a, b); out := x.Y", ["a", "b"], ["out"], reg)
    prog = Prog(flatten(circ, reg, ["a", "b"], ["out"]), ["a", "b"])
    sim = Sim(prog)
    assert sim.top_value("nonexistent.pin") == 0
