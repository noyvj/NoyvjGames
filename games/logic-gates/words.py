"""Logic Gates -- the circuit in words: one line per chip and per lamp. It is the text twin of the drawing, the body of the
hint ladder's answer, and what a screen reader reads."""

from levels import REGISTRY


def chip_name(chip):
    return REGISTRY[chip["type"]]["label"] if chip["type"] in REGISTRY else chip["type"]


def src_label(src, circuit):
    """A source string in plain words."""
    if not src:
        return "nothing"
    if src.startswith("in:"):
        return f"switch {src[3:]}"
    if src.startswith("const:"):
        return f"a wire tied to {src[6:]}"
    cid, _, pin = src.partition(".")
    for chip in circuit["chips"]:
        if str(chip["id"]) == cid:
            d = REGISTRY.get(chip["type"])
            many = d is not None and len(d["outs"]) > 1
            return f"chip {cid} ({chip_name(chip)}){' output ' + pin if many else ''}"
    return "nothing"


def describe(circuit, outs):
    lines = []
    for chip in circuit["chips"]:
        d = REGISTRY.get(chip["type"])
        if d is None:
            continue
        cid = chip["id"]
        parts = [pin + " from " + src_label(circuit["wires"].get(str(cid) + "." + pin), circuit) for pin in d["ins"]]
        lines.append(f"Chip {chip['id']}, {chip_name(chip)}: " + "; ".join(parts) + ".")
    for name in outs:
        lines.append(f"Lamp {name} from {src_label(circuit['wires'].get('out:' + name), circuit)}.")
    return lines
