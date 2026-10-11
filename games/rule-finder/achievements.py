"""Rule Finder -- achievements (the hub-wide framework: a static manifest `achievements.json` plus `achievements_earned` in the save).
Everything is computed from facts about the player's progress, never stored separately, so a loaded save and a played one can never
disagree. All are reachable without luck, none is hidden, and none rewards time or how often you come back. Every one has a number so
the player can see how close they are."""

import cases

TOTAL = len(cases.ORDER)

# (id, label, description, fact, need). Every case is open from the start, so any of them can be a goal at any time.
ACHIEVEMENTS = (
    ("first_gate", "First Gate", "Name your first case.", "named", 1),
    ("eight_named", "Eight Named", "Name 8 cases.", "named", 8),
    ("twenty_four", "Twenty-Four Named", "Name 24 cases.", "named", 24),
    ("all_forty_eight", "All Forty-Eight", "Name every case.", "named", TOTAL),
    ("drawer_closed", "Drawer Closed", "Name every case in one drawer.", "drawers_closed", 1),
    ("four_drawers", "Four Drawers", "Name every case in 4 drawers.", "drawers_closed", 4),
    ("quick_eye", "Quick Eye", "Name a case with 3 or fewer tests.", "quick", 1),
    ("at_par", "At Par", "Name 10 cases within par.", "clean", 10),
    ("counter_example", "Counter-Example", "Name a case after a near miss showed you a counter-example.", "counter", 1),
    ("both_ways", "Both Ways", "Name 5 cases with a rule that uses Not.", "both", 5),
    ("patient_hands", "Patient Hands", "Send 200 tests.", "tests", 200),
    ("shape_reader", "Shape Reader", "Name every case in Shape Strings.", "shapes_drawer", 8),
    ("odd_gate_open", "Odd Gate Open", "Name every case in The Odd Gate.", "odd_drawer", 8),
    ("full_codex", "Full Codex", "Read every page of the Codex.", "read", TOTAL),
)

IDS = tuple(a[0] for a in ACHIEVEMENTS)


def earned(facts):
    """The ids earned right now, in manifest order."""
    return [i for i, _l, _d, fact, need in ACHIEVEMENTS if facts.get(fact, 0) >= need]


def view(facts):
    out = []
    for i, label, description, fact, need in ACHIEVEMENTS:
        have = min(facts.get(fact, 0), need)
        out.append({"id": i, "label": label, "description": description, "earned": have >= need, "have": have, "need": need})
    return out


def goals(facts, count=3):
    """The next few achievements still to earn, in manifest order: the always-visible 'what to do next' list. Every case is open from the
    start, so all of them can be worked on now, in any order."""
    return [a for a in view(facts) if not a["earned"]][:count]
