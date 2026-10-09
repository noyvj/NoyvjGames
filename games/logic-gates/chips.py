"""Logic Gates -- the chips that exist before any level is solved: the seven gates and the three memory cells.

Every other chip is built by the player: a level's reference solution becomes the chip it unlocks (see levels.py), so a
chip can never behave differently from the circuit the player wired to earn it. The memory cells (SR latch, D latch, D
flip-flop) are the exception: their behaviour is a small model here, so a whole computer built from them simulates in
a few milliseconds, and the levels that teach them still build them from gates or from the cell below.

A chip is {"label", "ins", "outs", "kind", "net", "blurb", "level"}. kind is a gate name, a memory cell name, or "net"
(a chip made of a circuit, in "net")."""

GATE_KINDS = ("not", "and", "or", "xor", "nand", "nor", "xnor")
STATE_KINDS = ("sr", "dlatch", "dff")
# Memory cells whose output comes only from what they remember, so a loop through one is not a loop in the logic.
CUT_KINDS = ("sr", "dff")

BASE = {
    "not": {"label": "NOT", "ins": ["A"], "outs": ["Y"], "kind": "not", "blurb": "Y is 1 when A is 0, and 0 when A is 1."},
    "and": {"label": "AND", "ins": ["A", "B"], "outs": ["Y"], "kind": "and", "blurb": "Y is 1 only when A and B are both 1."},
    "or": {"label": "OR", "ins": ["A", "B"], "outs": ["Y"], "kind": "or", "blurb": "Y is 1 when A or B or both are 1."},
    "xor": {"label": "XOR", "ins": ["A", "B"], "outs": ["Y"], "kind": "xor", "blurb": "Y is 1 when A and B differ."},
    "nand": {"label": "NAND", "ins": ["A", "B"], "outs": ["Y"], "kind": "nand", "blurb": "Y is 0 only when A and B are both 1."},
    "nor": {"label": "NOR", "ins": ["A", "B"], "outs": ["Y"], "kind": "nor", "blurb": "Y is 1 only when A and B are both 0."},
    "xnor": {"label": "XNOR", "ins": ["A", "B"], "outs": ["Y"], "kind": "xnor", "blurb": "Y is 1 when A and B match."},
    "sr": {"label": "SR LATCH", "ins": ["S", "R"], "outs": ["Q", "QN"], "kind": "sr",
           "blurb": "S sets Q to 1 and R resets it to 0. With both at 0 it remembers. R wins if both are 1."},
    "dlatch": {"label": "D LATCH", "ins": ["D", "E"], "outs": ["Q"], "kind": "dlatch",
               "blurb": "While E is 1, Q follows D. While E is 0, Q holds the last value."},
    "dff": {"label": "FLIP-FLOP", "ins": ["D", "CLK"], "outs": ["Q"], "kind": "dff",
            "blurb": "Q takes D at the instant CLK goes from 0 to 1, and holds it until the next rising edge."},
}

# The seven gates, in the order the levels hand them out.
GATE_ORDER = ("not", "and", "or", "xor", "nand", "nor", "xnor")


def pins(chip_def):
    """All pin names of a chip: inputs then outputs."""
    return list(chip_def["ins"]) + list(chip_def["outs"])
