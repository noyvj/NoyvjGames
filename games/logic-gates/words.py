"""Logic Gates -- the circuit in words: one line per chip and per lamp. It is the text twin of the drawing, the body of the
hint ladder's answer, and what a screen reader reads."""

from levels import REGISTRY

# GN-6: what the two tie parts on every board are, in plain words (the drawing's tooltip, the board key and the tutorial use these).
TIE_TIPS = {
    "1": "Tie 1: a fixed input. A wire tied to 1 for good, so a circuit can be given a constant 1, for example to keep a part switched on or to turn a NAND chip into an inverter.",
    "0": "Tie 0: a fixed input. A wire tied to 0 for good, so a circuit can be given a constant 0, for example to leave an input of a chip switched off.",
}
TIE_KEY = ("Tie 1 and tie 0 are fixed inputs: a wire tied to 1 or to 0 for good, so a circuit can be given a constant "
           "(for example, tie one input of a NAND chip to 1 and it becomes an inverter).")


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
