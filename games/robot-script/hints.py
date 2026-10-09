"""Robot Script -- the hint ladder: nudge, hint, answer. All three are free and none touches a medal.

Rung 1 is the room's own nudge (one plain sentence written for that room). Rung 2 is built from the reference list: how
long it is and what it is made of. Rung 3 is the reference list itself, written out, with a way to put it in the editor.
"""

import dsl

RUNGS = ("Nudge", "Hint", "Answer")

KIND_WORDS = {"rep": ("repeat block", "repeat blocks"), "until": ("until block", "until blocks"),
              "if": ("if block", "if blocks"), "call": ("routine call", "routine calls")}


def _first(prog):
    items = prog["main"]
    if not items:
        return "nothing"
    head = items[0]
    if isinstance(head, str):
        return dsl.ACTION_NAMES[head].lower()
    return {"rep": "a repeat block", "until": "an until block", "if": "an if block", "call": "a routine call"}[head[0]]


def hint_text(room):
    """Rung 2: what the reference list is made of."""
    ref = room.ref
    counts = dsl.counts(ref)
    parts = []
    for kind in dsl.CONSTRUCTS:
        n = counts[kind]
        if n:
            one, many = KIND_WORDS[kind]
            parts.append("%d %s" % (n, one if n == 1 else many))
    made = "It uses " + ", ".join(parts) + "." if parts else "It uses only plain moves, no blocks."
    return "The reference list is %d steps, which is gold. %s It starts with %s." % (dsl.size(ref), made, _first(ref))


def answer(room):
    return {"text": dsl.to_text(room.ref), "lines": dsl.to_lines(room.ref), "steps": dsl.size(room.ref)}


def view(room, rung):
    """What the ladder shows for a room whose player has climbed `rung` rungs (0 to 3)."""
    out = {"rung": rung, "next": RUNGS[rung] if rung < 3 else "", "nudge": room.nudge if rung >= 1 else "",
           "hint": hint_text(room) if rung >= 2 else "", "answer": answer(room) if rung >= 3 else None}
    return out
