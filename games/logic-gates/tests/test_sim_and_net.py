"""The simulator and the circuit text form."""

import pytest

from chips import BASE
from net import parse_circuit, parse_steps
from sim import Prog, Sim, flatten

REG = dict(BASE)


def prog_of(text, ins, outs):
    circuit = parse_circuit(text, ins, outs, REG)
    return Prog(flatten(circuit, REG, ins, outs), ins)


@pytest.mark.parametrize("gate,table", [
    ("not", {(0,): 1, (1,): 0}),
    ("and", {(0, 0): 0, (0, 1): 0, (1, 0): 0, (1, 1): 1}),
    ("or", {(0, 0): 0, (0, 1): 1, (1, 0): 1, (1, 1): 1}),
    ("xor", {(0, 0): 0, (0, 1): 1, (1, 0): 1, (1, 1): 0}),
    ("nand", {(0, 0): 1, (0, 1): 1, (1, 0): 1, (1, 1): 0}),
    ("nor", {(0, 0): 1, (0, 1): 0, (1, 0): 0, (1, 1): 0}),
    ("xnor", {(0, 0): 1, (0, 1): 0, (1, 0): 0, (1, 1): 1}),
])
def test_every_gate_matches_its_truth_table(gate, table):
    ins = ["A"] if gate == "not" else ["A", "B"]
    prog = prog_of(f"Y := {gate}({', '.join(ins)})", ins, ["Y"])
    for row, want in table.items():
        sim = Sim(prog)
        assert sim.step(dict(zip(ins, row)))
        assert sim.out("Y") == want


def test_all_rows_at_once_agree_with_one_row_at_a_time():
    prog = prog_of("x = xor(A, B); a = and(x, C); n = nor(A, C); Y := or(a, n)", ["A", "B", "C"], ["Y"])
    bits = []
    for k in range(3):
        bits.append(sum(1 << r for r in range(8) if (r >> (2 - k)) & 1))
    packed = prog.truth_rows(dict(zip(["A", "B", "C"], bits)), 8)["Y"]
    for r in range(8):
        sim = Sim(prog)
        sim.step({"A": (r >> 2) & 1, "B": (r >> 1) & 1, "C": r & 1})
        assert sim.out("Y") == (packed >> r) & 1


def test_unwired_pins_read_zero():
    prog = prog_of("Y := or(A, B)", ["A", "B"], ["Y"])
    circuit = parse_circuit("Y := or(A)", ["A", "B"], ["Y"], REG)
    sim = Sim(Prog(flatten(circuit, REG, ["A", "B"], ["Y"]), ["A", "B"]))
    sim.step({"A": 0, "B": 1})
    assert sim.out("Y") == 0
    assert prog.is_simple


def test_a_nor_loop_remembers_and_a_bare_inverter_loop_is_reported_unsettled():
    latch = prog_of("q = nor(R, qn); qn = nor(S, q); Q := q", ["S", "R"], ["Q"])
    assert latch.order is None
    sim = Sim(latch)
    seen = []
    for s, r in [(0, 1), (1, 0), (0, 0), (0, 1), (0, 0)]:
        assert sim.step({"S": s, "R": r})
        seen.append(sim.out("Q"))
    assert seen == [0, 1, 1, 0, 0]
    ring = prog_of("n = not(n); Y := n", ["A"], ["Y"])
    assert Sim(ring).step({"A": 0}) is False


def test_memory_cells_hold_state_between_steps():
    ff = prog_of("Q := dff(D, CLK)", ["D", "CLK"], ["Q"])
    sim = Sim(ff)
    out = []
    for d, clk in [(1, 0), (1, 1), (0, 1), (0, 0), (0, 1)]:
        sim.step({"D": d, "CLK": clk})
        out.append(sim.out("Q"))
    assert out == [0, 1, 1, 1, 0]


def test_a_flip_flop_does_not_fire_at_power_on_even_if_its_clock_starts_high():
    sim = Sim(prog_of("n = not(CLK); Q := dff(1, n)", ["CLK"], ["Q"]))
    sim.step({"CLK": 0})
    assert sim.out("Q") == 0


def test_parse_errors_are_value_errors():
    for bad in ("Y := and(A, nope)", "Z := A", "x = zap(A)", "x = and(A, B, A)"):
        with pytest.raises(ValueError):
            parse_circuit(bad, ["A", "B"], ["Y"], REG)
    with pytest.raises(ValueError):
        parse_steps("Q=2", ["Q"], ["Q"])


def test_step_text_keeps_inputs_between_steps_and_expectations_are_optional():
    steps = parse_steps("S=1 R=0 -> Q=1; S=0; R=1 -> Q=0", ["S", "R"], ["Q"])
    assert [s["want"] for s in steps] == [{"Q": 1}, None, {"Q": 0}]
    assert steps[1]["set"] == {"S": 0}
