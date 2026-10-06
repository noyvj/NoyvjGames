"""Lexis -- the Contact report shown after contact with planet 3.

The one place the game says, after the fact, what each sign really means and which notebook entries were
right. Everything is computed from the state and the true language data (never stored), so it cannot
disagree with the engine. During play the notebook is never marked; this is the closing account.
"""

from bridge import MARKERS
from compound import COMPONENTS
from pulse import PULSE

# What the report calls each planet, and the order it lists them in.
PLANETS = (("pulse", "Planet 1: the quiet beacon"), ("compound", "Planet 2: the market world"),
           ("bridge", "Planet 3: the counting station"))


def _pulse_lines():
    words = [w.meaning for w in PULSE.words if w.kind != "frame"]
    return [
        "Every sign is a group of four marks. A group that starts with a short mark spells a number in binary, "
        "biggest place first.",
        "A group that starts with a long mark is a word: " + ", ".join(words) + ". One more sign ends every message.",
    ]


def _compound_lines():
    roots = [f"{code} is {meaning}" for code, (meaning, slot) in COMPONENTS.items() if slot == "root"]
    sizes = [f"{code} is {meaning}" for code, (meaning, slot) in COMPONENTS.items() if slot == "size"]
    return [
        "A sign is two parts: first what the thing is, then its size.",
        "Things: " + ", ".join(roots) + ". Sizes: " + ", ".join(sizes) + ".",
        "You could read signs you were never shown, because each part keeps its meaning wherever it appears.",
    ]


def _bridge_lines():
    markers = ", ".join(f"{letter} is {role}" for letter, role in MARKERS.items())
    return [
        "A message is a thing, then perhaps a small sign, then perhaps a number. Things come from planet 2 and "
        "numbers from planet 1.",
        "The small signs: " + markers + ". Plural adds the number that follows it, negate takes all of that thing "
        "away, and ask makes the station tell you how many there are without changing anything.",
    ]


def _notebook_row(planet, notebook, truth, scenes_seen, scenes_total, spoken):
    written = len(notebook.entries)
    right = notebook.confirm(list(notebook.entries), truth=truth)
    return {"planet": planet, "transmissions": scenes_seen, "transmissions_total": scenes_total,
            "sent": len(spoken), "written": written, "right": right}


def build(state, achievements_view, scenes_total):
    """The report as plain data. `scenes_total` maps planet to its curriculum length; `achievements_view` is
    achievements.view(...). Returns None until contact with planet 3."""
    if not state.contact.get("bridge"):
        return None
    pulse_truth = state.notebook.truth
    compound_truth = lambda form: (COMPONENTS.get(form) or (None,))[0]
    bridge_truth = lambda form: MARKERS.get(form)
    rows = {
        "pulse": _notebook_row("pulse", state.notebook, pulse_truth, state.scenes_seen,
                               scenes_total["pulse"], state.spoken),
        "compound": _notebook_row("compound", state.compound_notebook, compound_truth, state.compound_scenes_seen,
                                  scenes_total["compound"], state.compound_spoken),
        "bridge": _notebook_row("bridge", state.bridge_notebook, bridge_truth, state.bridge_scenes_seen,
                                scenes_total["bridge"], state.bridge_spoken),
    }
    lines = {"pulse": _pulse_lines(), "compound": _compound_lines(), "bridge": _bridge_lines()}
    planets = [dict(rows[key], name=name, learned=lines[key]) for key, name in PLANETS]
    earned = [a for a in achievements_view if a["earned"]]
    return {
        "planets": planets,
        "totals": {key: sum(row[key] for row in rows.values()) for key in ("transmissions", "sent", "written", "right")},
        "achievements": [{"label": a["label"], "description": a["description"]} for a in earned],
        "achievements_total": len(achievements_view),
    }
