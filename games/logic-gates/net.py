"""Logic Gates -- a tiny text form for circuits and scripted steps, used by the level data and the tests.

    circuit text:   "n = not(A); p = and(A, n); Y := or(p, B)"
    A name in lower case is a chip. Inputs and outputs are upper case. Arguments run in the chip's input-pin order and may be
    an input, a 0 or 1, a chip name (its only output) or chip.PIN. `OUT := ref` wires an output lamp; the right side may also
    be a call, which makes an unnamed chip. A chip may be used before it is written (a loop).

    step text:      "S=1 R=0 -> Q=1 QN=0; S=0 -> Q=1"
    Inputs not mentioned keep their last value (all start at 0). After `->` come the lamp values wanted after settling; a step
    without `->` only sets inputs."""

import re

_CALL = re.compile(r"^([a-z][a-z0-9_]*)\((.*)\)$")


def _split(text):
    return [s.strip() for s in re.split(r"[;\n]", text) if s.strip()]


def _args(text):
    return [a.strip() for a in text.split(",") if a.strip()]


def parse_circuit(text, inputs, outputs, registry):
    """Text to a circuit dict {"chips": [{"id", "type"}], "wires": {dest: source}}. Raises ValueError on a bad line."""
    chips, names, pending, outs = [], {}, [], []
    for line in _split(text):
        if ":=" in line:
            left, right = [p.strip() for p in line.split(":=", 1)]
            if left not in outputs:
                raise ValueError(f"{left} is not an output")
            m = _CALL.match(right)
            if m:
                cid = len(chips) + 1
                chips.append({"id": cid, "type": m.group(1)})
                pending.append((cid, m.group(1), _args(m.group(2))))
                right = f"#{cid}"
            outs.append((left, right))
        else:
            left, right = [p.strip() for p in line.split("=", 1)]
            m = _CALL.match(right)
            if not m or m.group(1) not in registry:
                raise ValueError(f"bad chip line: {line}")
            cid = len(chips) + 1
            chips.append({"id": cid, "type": m.group(1)})
            names[left] = cid
            pending.append((cid, m.group(1), _args(m.group(2))))

    def source(token):
        if token in ("0", "1"):
            return "const:" + token
        if token in inputs:
            return "in:" + token
        if token.startswith("#"):
            cid = int(token[1:])
            return f"{cid}.{registry[chips[cid - 1]['type']]['outs'][0]}"
        name, _, pin = token.partition(".")
        if name not in names:
            raise ValueError(f"unknown name {token}")
        cid = names[name]
        d = registry[chips[cid - 1]["type"]]
        if not pin:
            if len(d["outs"]) != 1:
                raise ValueError(f"{name} has several outputs; say which")
            pin = d["outs"][0]
        if pin not in d["outs"]:
            raise ValueError(f"{name} has no output {pin}")
        return f"{cid}.{pin}"

    wires = {}
    for cid, ctype, args in pending:
        d = registry[ctype]
        if len(args) > len(d["ins"]):
            raise ValueError(f"{ctype} takes {len(d['ins'])} inputs")
        for pin, arg in zip(d["ins"], args):
            wires[f"{cid}.{pin}"] = source(arg)
    for out, ref in outs:
        wires["out:" + out] = source(ref)
    return {"chips": chips, "wires": wires}


def parse_steps(text, inputs, outputs):
    """Step text to [{"set": {input: bit}, "want": {output: bit} | None}]."""
    steps = []
    for line in _split(text):
        left, _, right = line.partition("->")
        sets, want = {}, None
        for tok in left.split():
            name, _, val = tok.partition("=")
            if name not in inputs or val not in ("0", "1"):
                raise ValueError(f"bad input assignment {tok}")
            sets[name] = int(val)
        if right.strip():
            want = {}
            for tok in right.split():
                name, _, val = tok.partition("=")
                if name not in outputs or val not in ("0", "1"):
                    raise ValueError(f"bad expectation {tok}")
                want[name] = int(val)
        steps.append({"set": sets, "want": want})
    return steps
