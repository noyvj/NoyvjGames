"""Logic Gates -- the simulator. Deterministic, no randomness, no clock.

A circuit is flattened (every built chip replaced by the circuit inside it) into primitive nodes: seven gates and three
memory cells. Then one of two engines runs it:

  * acyclic (no loop of plain gates): one pass in dependency order. Memory cells with a remembered value (SR latch,
    flip-flop) are cut points, so a loop through one is fine. A pass is repeated after the memory cells update, until
    nothing changes, which is how a ripple counter's later stages see the earlier stage change.
  * cyclic (the player closed a loop of plain gates, e.g. two NORs): every node is recomputed from the previous values
    together, round after round, until nothing changes. If a state repeats without settling the circuit oscillates and
    the result says so instead of guessing.

Stateless acyclic circuits are evaluated for every truth-table row at once: each signal is one Python integer whose bit r
is that signal's value in row r."""

from chips import CUT_KINDS, STATE_KINDS

MAX_PASSES = 48
MAX_ROUNDS = 400


def flatten(circuit, registry, in_names, out_names):
    """-> {"nodes": [{"key", "kind", "ins", "outs"}], "outs": {name: src}, "top": {"id.PIN": src}}.
    Sources are strings: "in:A", "const:0", "const:1" or "<node key>.<pin>". An unwired pin reads const:0."""
    nodes, alias = [], {}

    def expand(circ, prefix, input_srcs, out_pins):
        local = {}
        chips = [c for c in circ["chips"] if c["type"] in registry]
        for chip in chips:
            d = registry[chip["type"]]
            key = f"{prefix}{chip['id']}"
            if d["kind"] == "net":
                local[chip["id"]] = {pin: f"{key}|o.{pin}" for pin in d["outs"]}
            else:
                local[chip["id"]] = {pin: f"{key}.{pin}" for pin in d["outs"]}

        def src(s):
            if not s:
                return "const:0"
            if s.startswith("in:"):
                return input_srcs.get(s[3:], "const:0")
            if s.startswith("const:"):
                return s
            cid, _, pin = s.partition(".")
            try:
                return local[int(cid)][pin]
            except (KeyError, ValueError):
                return "const:0"

        wires = circ["wires"]
        for chip in chips:
            d = registry[chip["type"]]
            key = f"{prefix}{chip['id']}"
            ins = [src(wires.get(f"{chip['id']}.{pin}")) for pin in d["ins"]]
            if d["kind"] == "net":
                inner, _unused = expand(d["net"], key + "/", dict(zip(d["ins"], ins)), d["outs"])
                for pin in d["outs"]:
                    alias[f"{key}|o.{pin}"] = inner[pin]
            else:
                nodes.append({"key": key, "kind": d["kind"], "ins": ins, "outs": list(d["outs"])})
        return {name: src(wires.get("out:" + name)) for name in out_pins}, local

    outs, local = expand(circuit, "", {n: "in:" + n for n in in_names}, out_names)

    def resolve(s):
        seen = 0
        while s in alias:
            s = alias[s]
            seen += 1
            if seen > 200:
                return "const:0"
        return s

    for node in nodes:
        node["ins"] = [resolve(s) for s in node["ins"]]
    top = {f"{cid}.{pin}": resolve(s) for cid, pins in local.items() for pin, s in pins.items()}
    return {"nodes": nodes, "outs": {n: resolve(s) for n, s in outs.items()}, "top": top}


class Prog:
    """A flattened circuit compiled to integer slots. Slot 0 is the constant 0, slot 1 the constant 1, then the inputs, then
    every node output."""

    def __init__(self, flat, in_names):
        self.in_names = list(in_names)
        self.idx = {"const:0": 0, "const:1": 1}
        for n in self.in_names:
            self.idx["in:" + n] = len(self.idx)
        self.nodes = []          # (kind, out slots, in slots)
        for node in flat["nodes"]:
            for pin in node["outs"]:
                self.idx[f"{node['key']}.{pin}"] = len(self.idx)
        for node in flat["nodes"]:
            outs = tuple(self.idx[f"{node['key']}.{p}"] for p in node["outs"])
            ins = tuple(self.idx.get(s, 0) for s in node["ins"])
            self.nodes.append((node["kind"], outs, ins))
        self.size = len(self.idx)
        self.outs = {n: self.idx.get(s, 0) for n, s in flat["outs"].items()}
        self.top = {k: self.idx.get(s, 0) for k, s in flat["top"].items()}
        self.stateful = [i for i, n in enumerate(self.nodes) if n[0] in STATE_KINDS]
        self.cuts = [i for i, n in enumerate(self.nodes) if n[0] in CUT_KINDS]
        self.order = self._order()
        self.slot_names = {v: k for k, v in self.idx.items()}

    def _order(self):
        """Node positions in dependency order, or None when plain gates form a loop."""
        producer = {}
        for pos, (kind, outs, _ins) in enumerate(self.nodes):
            for o in outs:
                producer[o] = pos
        deps = []
        for pos, (kind, _outs, ins) in enumerate(self.nodes):
            deps.append([] if kind in CUT_KINDS else sorted({producer[s] for s in ins if s in producer}))
        order, state = [], [0] * len(self.nodes)
        for start in range(len(self.nodes)):
            if state[start]:
                continue
            stack = [(start, iter(deps[start]))]
            state[start] = 1
            while stack:
                pos, it = stack[-1]
                for d in it:
                    if state[d] == 1:
                        return None
                    if not state[d]:
                        state[d] = 1
                        stack.append((d, iter(deps[d])))
                        break
                else:
                    state[pos] = 2
                    order.append(pos)
                    stack.pop()
        return order

    # ---- one pass over the nodes, all rows at once when mask has many bits ----------------------------
    def run_pass(self, vals, mask, state=None):
        nodes = self.nodes
        for pos in self.order:
            kind, o, i = nodes[pos]
            if kind == "not":
                vals[o[0]] = vals[i[0]] ^ mask
            elif kind == "and":
                vals[o[0]] = vals[i[0]] & vals[i[1]]
            elif kind == "or":
                vals[o[0]] = vals[i[0]] | vals[i[1]]
            elif kind == "xor":
                vals[o[0]] = vals[i[0]] ^ vals[i[1]]
            elif kind == "nand":
                vals[o[0]] = (vals[i[0]] & vals[i[1]]) ^ mask
            elif kind == "nor":
                vals[o[0]] = (vals[i[0]] | vals[i[1]]) ^ mask
            elif kind == "xnor":
                vals[o[0]] = (vals[i[0]] ^ vals[i[1]]) ^ mask
            elif kind == "dlatch":
                e = vals[i[1]]
                vals[o[0]] = (vals[i[0]] & e) | (state[pos] & (e ^ mask))

    def truth_rows(self, in_bits, count):
        """All rows at once for a stateless acyclic circuit. in_bits: {name: int bitset}. -> {out name: int bitset}"""
        mask = (1 << count) - 1
        vals = [0] * self.size
        vals[1] = mask
        for n in self.in_names:
            vals[self.idx["in:" + n]] = in_bits.get(n, 0)
        self.run_pass(vals, mask)
        return {n: vals[s] for n, s in self.outs.items()}

    @property
    def is_simple(self):
        return self.order is not None and not self.stateful


def _gate(kind, a, b):
    if kind == "not":
        return a ^ 1
    if kind == "and":
        return a & b
    if kind == "or":
        return a | b
    if kind == "xor":
        return a ^ b
    if kind == "nand":
        return (a & b) ^ 1
    if kind == "nor":
        return (a | b) ^ 1
    return (a ^ b) ^ 1          # xnor


class Sim:
    """Runs a Prog one input vector at a time, keeping what the memory cells remember between steps (power-on: all 0)."""

    def __init__(self, prog):
        self.prog = prog
        self.state = {p: 0 for p in prog.stateful}
        self.prev = {p: 0 for p in prog.stateful}
        self.vals = [0] * prog.size
        self.vals[1] = 1
        self.settled = True
        self.warm = False        # power-on: a flip-flop never fires on the very first look at its clock

    def _set_inputs(self, vals, inputs):
        for n in self.prog.in_names:
            vals[self.prog.idx["in:" + n]] = 1 if inputs.get(n) else 0

    def _update_state(self, vals):
        changed = False
        nodes = self.prog.nodes
        for pos in self.prog.stateful:
            kind, o, i = nodes[pos]
            st = self.state[pos]
            if kind == "sr":
                new = 0 if vals[i[1]] else (1 if vals[i[0]] else st)
            elif kind == "dlatch":
                new = vals[o[0]]
            else:
                clk = vals[i[1]]
                new = vals[i[0]] if clk and not self.prev[pos] and self.warm else st
                self.prev[pos] = clk
            if new != st:
                self.state[pos] = new
                changed = True
        return changed

    def _load_cuts(self, vals):
        nodes = self.prog.nodes
        for pos in self.prog.cuts:
            kind, o, _i = nodes[pos]
            st = self.state[pos]
            vals[o[0]] = st
            if kind == "sr":
                vals[o[1]] = st ^ 1

    def step(self, inputs):
        """Apply one input vector, settle, and return True if the circuit settled. self.vals holds every signal."""
        prog = self.prog
        if prog.order is not None:
            vals = [0] * prog.size
            vals[1] = 1
            self._set_inputs(vals, inputs)
            for _ in range(MAX_PASSES):
                self._load_cuts(vals)
                prog.run_pass(vals, 1, self.state)
                again = self._update_state(vals)
                self.warm = True
                if not again:
                    self.vals = vals
                    self.settled = True
                    return True
            self.vals = vals
            self.settled = False
            return False
        return self._step_cyclic(inputs)

    def _step_cyclic(self, inputs):
        prog = self.prog
        nodes = prog.nodes
        vals = self.vals[:]
        self._set_inputs(vals, inputs)
        seen = set()
        for _ in range(MAX_ROUNDS):
            new = vals[:]
            for pos, (kind, o, i) in enumerate(nodes):
                if kind in ("not", "and", "or", "xor", "nand", "nor", "xnor"):
                    new[o[0]] = _gate(kind, vals[i[0]], vals[i[1]] if len(i) > 1 else 0)
                elif kind == "dlatch":
                    e = vals[i[1]]
                    new[o[0]] = 1 if (vals[i[0]] and e) or (self.state[pos] and not e) else 0
                else:                                   # sr, dff: the output is what is remembered
                    st = self.state[pos]
                    new[o[0]] = st
                    if kind == "sr":
                        new[o[1]] = st ^ 1
            changed = self._update_state(vals)
            self.warm = True
            if new == vals and not changed:
                self.vals = new
                self.settled = True
                return True
            sig = (tuple(new), tuple(self.state[p] for p in prog.stateful))
            if sig in seen:
                self.vals = new
                self.settled = False
                return False
            seen.add(sig)
            vals = new
        self.vals = vals
        self.settled = False
        return False

    def out(self, name):
        return self.vals[self.prog.outs[name]]

    def top_value(self, key):
        slot = self.prog.top.get(key)
        return self.vals[slot] if slot is not None else 0
