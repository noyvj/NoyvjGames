"""Logic Gates -- does a circuit meet a level? A pure function of (level, circuit): same wiring, same answer, always.

Combinational levels are checked on every row of the truth table at once. Sequential levels run their scripted steps from
power-on (every memory cell 0) and compare the lamps after each step that has an expectation."""

import json
from functools import lru_cache

from levels import REGISTRY
from sim import Prog, Sim, flatten

MAX_WRONG_SHOWN = 8


_PROGS = {}


def build_prog(level, circuit):
    """The compiled circuit; the same wiring on the same level is compiled once (a Prog is never changed by running it)."""
    key = (tuple(level["ins"]), tuple(level["outs"]), json.dumps(circuit, sort_keys=True))
    prog = _PROGS.get(key)
    if prog is None:
        if len(_PROGS) > 64:
            _PROGS.clear()
        prog = _PROGS[key] = Prog(flatten(circuit, REGISTRY, level["ins"], level["outs"]), level["ins"])
    return prog


def row_values(ins, r):
    n = len(ins)
    return {name: (r >> (n - 1 - k)) & 1 for k, name in enumerate(ins)}


@lru_cache(maxsize=None)
def _input_bits(n):
    count = 1 << n
    return tuple(sum(1 << r for r in range(count) if (r >> (n - 1 - k)) & 1) for k in range(n))


@lru_cache(maxsize=None)
def _want_bits(level_id, ins, outs):
    from levels import BY_ID
    fn = BY_ID[level_id]["fn"]
    n = len(ins)
    want = {o: 0 for o in outs}
    for r in range(1 << n):
        got = fn(row_values(ins, r))
        for o in outs:
            if got[o]:
                want[o] |= 1 << r
    return want


def want_table(level):
    """Expected outputs of a combinational level: [(inputs dict, outputs dict)] for every row."""
    fn = level["fn"]
    return [(row_values(level["ins"], r), fn(row_values(level["ins"], r))) for r in range(1 << len(level["ins"]))]


def _popcount(x):
    return bin(x).count("1")


def check_comb(level, prog):
    ins, outs = level["ins"], level["outs"]
    n = len(ins)
    count = 1 << n
    want = _want_bits(level["id"], tuple(ins), tuple(outs))
    settled = True
    if prog.is_simple:
        bits = _input_bits(n)
        got = prog.truth_rows({name: bits[k] for k, name in enumerate(ins)}, count)
    else:
        got = {o: 0 for o in outs}
        for r in range(count):
            sim = Sim(prog)
            if not sim.step(row_values(ins, r)):
                settled = False
            for o in outs:
                if sim.out(o):
                    got[o] |= 1 << r
    bad = 0
    for o in outs:
        bad |= got[o] ^ want[o]
    wrong_rows = [r for r in range(count) if (bad >> r) & 1]
    rows = []
    shown = range(count) if count <= 32 else wrong_rows[:MAX_WRONG_SHOWN]
    for r in shown:
        rows.append({"row": r, "inputs": [(i >> 0) for i in [row_values(ins, r)[x] for x in ins]],
                     "want": [(want[o] >> r) & 1 for o in outs], "got": [(got[o] >> r) & 1 for o in outs], "ok": not (bad >> r) & 1})
    ok = not wrong_rows and settled
    message = ""
    if not settled:
        message = "A loop in the wiring never settles on some switch settings. Loops are not allowed in this board's logic."
    elif wrong_rows:
        r = wrong_rows[0]
        vals = row_values(ins, r)
        setting = ", ".join(f"{k}={v}" for k, v in vals.items())
        diffs = [o for o in outs if ((got[o] ^ want[o]) >> r) & 1]
        o = diffs[0]
        message = f"With {setting}, lamp {o} shows {(got[o] >> r) & 1} but should show {(want[o] >> r) & 1}."
    return {"kind": "comb", "ok": ok, "total": count, "right": count - len(wrong_rows), "settled": settled, "rows": rows, "message": message}


def check_seq(level, prog):
    outs = level["outs"]
    sim = Sim(prog)
    inputs = {n: 0 for n in level["ins"]}
    rows, checked, right, settled_all, first_bad = [], 0, 0, True, None
    for i, step in enumerate(level["steps"]):
        inputs.update(step["set"])
        settled = sim.step(inputs)
        got = {o: sim.out(o) for o in outs}
        want = step["want"]
        ok = None
        if want is not None:
            checked += 1
            ok = settled and all(got[o] == v for o, v in want.items())
            right += 1 if ok else 0
        if not settled:
            settled_all = False
        row = {"step": i + 1, "inputs": [inputs[n] for n in level["ins"]], "got": [got[o] for o in outs],
               "want": [want.get(o) for o in outs] if want is not None else None, "ok": ok, "settled": settled}
        rows.append(row)
        if ok is False and first_bad is None:
            first_bad = (i, row, step)
    message = ""
    if first_bad is not None:
        i, row, step = first_bad
        if not row["settled"]:
            message = f"Step {i + 1}: the circuit never settles (it flickers round a loop)."
        else:
            o = next(o for o in outs if step["want"].get(o) is not None and step["want"][o] != row["got"][outs.index(o)])
            setting = ", ".join(f"{n}={v}" for n, v in zip(level["ins"], row["inputs"]))
            message = f"Step {i + 1} ({setting}): lamp {o} shows {row['got'][outs.index(o)]} but should show {step['want'][o]}."
    elif not settled_all:
        message = "The circuit never settles on one of the steps."
    return {"kind": "seq", "ok": checked > 0 and right == checked and settled_all, "total": checked, "right": right,
            "settled": settled_all, "rows": rows, "message": message}


def check_level(level, circuit):
    prog = build_prog(level, circuit)
    return check_comb(level, prog) if level["kind"] == "comb" else check_seq(level, prog)
