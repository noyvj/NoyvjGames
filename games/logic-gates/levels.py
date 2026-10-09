"""Logic Gates -- the 40 levels, the chip registry built from them, and the rules for what is open.

A level is {"id", "name", "chapter", "index", "ins", "outs", "goal", "kind" ("comb" | "seq"), "fn" | "steps", "ref" (the reference
circuit), "par" (its chip count), "cap" (chips the board holds), "unlock" (chip id or None), "needs" (chip types the reference
uses), "loops", "nudge", "hint", "log"}. A level's chip, when it has one, is its own reference circuit, so what you earn is
exactly what you built."""

from chips import BASE
from levels_a import CH1, CH2
from levels_b import CH3
from levels_c import CH4, CH5
from net import parse_circuit, parse_steps

CHAPTERS = [
    {"id": 1, "name": "Switches and Lamps",
     "intro": "Meridian Relay went quiet eleven years ago. You have the contract to wake its logic core, one board at a time. The first boards are only switches, lamps and the smallest chips."},
    {"id": 2, "name": "Combining Gates",
     "intro": "The next boards route decisions: who wins a vote, which feed is shown, which door opens. Vale's margin notes are in pencil. You trust the circuit more than the notes."},
    {"id": 3, "name": "Memory",
     "intro": "A circuit remembers when its output feeds back into itself. Loops are allowed from here on. Vale's notes call this the Memory board and underline the word 'forget' twice."},
    {"id": 4, "name": "Adders",
     "intro": "Counting is remembering in a loop, and adding is counting in columns. Vale's last entry before the shutdown reads: carry the one, then blame the cooling line."},
    {"id": 5, "name": "A Tiny Computer",
     "intro": "Everything so far was parts. Now they become a machine small enough to read in one glance and big enough to be called a computer."},
]
CHAPTER_OF = {}

_RAW = [(1, CH1), (2, CH2), (3, CH3), (4, CH4), (5, CH5)]


def _build():
    registry = {k: dict(v, level=None) for k, v in BASE.items()}
    levels, unlock_by = [], {}
    for chapter, group in _RAW:
        for raw in group:
            ins, outs = raw["ins"], raw["outs"]
            lv = dict(raw)
            lv["chapter"] = chapter
            lv["index"] = len(levels) + 1
            lv["ref"] = parse_circuit(raw["ref"], ins, outs, registry)
            lv["ref_text"] = raw["ref"]
            lv["kind"] = "seq" if "seq" in raw else "comb"
            lv["steps"] = parse_steps(raw["seq"], ins, outs) if lv["kind"] == "seq" else None
            lv["loops"] = bool(raw.get("loops"))
            lv["par"] = len(lv["ref"]["chips"])
            lv["cap"] = max(8, 2 * lv["par"] + 4)
            lv["needs"] = sorted({c["type"] for c in lv["ref"]["chips"]})
            chip = raw.get("unlock")
            lv["unlock"] = chip
            if chip:
                unlock_by[chip] = raw["id"]
                if chip not in registry:
                    pins = raw.get("chip_pins") or (ins, outs)
                    text = raw.get("chip_net") or raw["ref"]
                    registry[chip] = {"label": raw.get("label", chip.upper()), "ins": list(pins[0]), "outs": list(pins[1]), "kind": "net",
                                      "net": parse_circuit(text, list(pins[0]), list(pins[1]), registry), "blurb": raw["goal"], "level": raw["id"]}
                else:
                    registry[chip]["level"] = raw["id"]
            levels.append(lv)
            CHAPTER_OF[raw["id"]] = chapter
    return registry, levels, unlock_by


REGISTRY, LEVELS, UNLOCK_BY = _build()
BY_ID = {lv["id"]: lv for lv in LEVELS}
CHIP_ORDER = [lv["unlock"] for lv in LEVELS if lv["unlock"]]


def get_level(level_id):
    return BY_ID.get(level_id)


def unlocked(solved_ids):
    """Chip ids unlocked by the solved levels, in unlock order."""
    solved = set(solved_ids)
    return [lv["unlock"] for lv in LEVELS if lv["unlock"] and lv["id"] in solved]


def allowed_chips(level, solved_ids):
    """What a level lets you place: every unlocked chip except the one this level hands out."""
    return [c for c in unlocked(solved_ids) if c != level["unlock"]]


def is_open(level, solved_ids):
    have = set(unlocked(solved_ids))
    return all(c in have for c in level["needs"])


def missing_chips(level, solved_ids):
    have = set(unlocked(solved_ids))
    return [c for c in level["needs"] if c not in have]
