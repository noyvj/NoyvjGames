"""Hull Repair -- achievements (the hub-wide framework: a static manifest `achievements.json` plus `achievements_earned`
in the save). Everything is computed from facts about the player's progress, never stored separately, so a loaded save and
a played one can never disagree. All are reachable without luck, none is hidden, and none rewards time or how often you
come back. Every one has a number so the player can see how close they are.
"""

import boards

TOTAL_ROOMS = len(boards.ORDER)

# (id, label, description, fact, need). Every deck is open from the start, so any achievement can be a goal at any time.
ACHIEVEMENTS = (
    ("first_spark", "First Spark", "Patch your first room.", "patched", 1),
    ("ten_lit", "Ten Lit", "Patch 10 rooms.", "patched", 10),
    ("deck_patched", "Deck Patched", "Patch every room of one deck.", "decks_patched", 1),
    ("three_decks", "Three Decks", "Patch every room of 3 decks.", "decks_patched", 3),
    ("station_lit", "Station Lit", "Patch every room on the station.", "patched", TOTAL_ROOMS),
    ("tidy_work", "Tidy Work", "Restore 5 rooms: every line joined and every cell covered.", "restored", 5),
    ("careful_hands", "Careful Hands", "Restore 20 rooms.", "restored", 20),
    ("hull_whole", "Hull Whole", "Restore every room on the station.", "restored", TOTAL_ROOMS),
    ("over_and_under", "Over and Under", "Join a board with two lines crossing on a bridge.", "flag_bridge", 1),
    ("mind_the_valve", "Mind the Valve", "Join a board with a line through a valve.", "flag_valve", 1),
    ("colour_theory", "Colour Theory", "Join a board with a mixer.", "flag_mix", 1),
    ("second_thoughts", "Second Thoughts", "Join a board after taking a line back on it.", "flag_retry", 1),
    ("second_opinion", "Second Opinion", "Climb the whole hint ladder on one board: nudge, hint, answer.", "rung3", 1),
    ("pipe_layer", "Pipe Layer", "Lay 500 cells of pipe.", "laid", 500),
)

IDS = tuple(a[0] for a in ACHIEVEMENTS)


def earned(facts):
    """The ids earned right now, in manifest order."""
    return [i for i, _l, _d, fact, need in ACHIEVEMENTS if facts.get(fact, 0) >= need]


def view(facts):
    out = []
    for i, label, description, fact, need in ACHIEVEMENTS:
        have = min(facts.get(fact, 0), need)
        out.append({"id": i, "label": label, "description": description, "earned": have >= need,
                    "have": have, "need": need})
    return out


def goals(facts, count=3):
    """The next few achievements still to earn, in manifest order: the always-visible 'what to do next' list. Every deck is
    open from the start, so all of them can be worked on now. They can be done in any order."""
    return [a for a in view(facts) if not a["earned"]][:count]
