"""Reaction Bench -- achievements (the hub-wide framework: a static manifest `achievements.json` plus `achievements_earned` in the save).

Everything is computed from facts about the player's progress (the shelf, the elements found, the hint record, the product rounds
chosen right first time), never stored separately, so a loaded save and a played one can never disagree and the saved list is a
write-only projection that load never reads back. All fourteen are reachable by plain play on any difficulty (the level only changes
how the suggestion ladder opens and no achievement reads it), none is hidden, none is timed or luck-based, and every one shows a
number so the player can see how close they are. The one named "no suggestion" achievement is Straight Through: it counts only
orders shelved without pressing the ladder, and it is earnable on every level (the ladder is always optional). Nothing here reads a
clock or a random source.

The plan's table achievements were 9, 18 and 36 elements; the bench reaches 15 elements (see CLAUDE.md), so they scale to 4, 8 and
every element on the bench.
"""

import reactions

TOTAL = len(reactions.ALL)
BENCH = len(reactions.BENCH_ELEMENTS)
CHAPTER_SIZE = [len(c["reactions"]) for c in reactions.CHAPTERS]
CHAPTER_NAME = [c["name"] for c in reactions.CHAPTERS]
BURNING, ACIDS, WORKS = 1, 3, 4                         # the chapter indexes the three chapter achievements read

# The salts on the bench: every product that is an ionic compound of a metal (or ammonium) with chloride, sulfate, phosphate,
# carbonate or nitrate. An order "makes a salt" when one of its products is on this list.
SALT_FORMULAS = ("NaCl", "AlCl3", "MgCl2", "FeCl3", "K2SO4", "(NH4)2SO4", "Na2CO3", "CaCO3", "Cu(NO3)2", "Ca3(PO4)2", "(NH4)3PO4")
SALT_ORDERS = tuple(r.id for r in reactions.ALL if any(f in SALT_FORMULAS for f in r.products))
OXYGEN_ORDERS = tuple(r.id for r in reactions.ALL if "O" in r.elements)
OXYGEN_NEED = 15
CLEAN_NEED = 10
FIRST_NEED = 10
QUARTER, HALF = 4, 8

# (id, label, description, fact, need)
ACHIEVEMENTS = (
    ("first_balance", "First Balance", "Put your first compound on the shelf.", "shelved", 1),
    ("ten_on_the_shelf", "Ten on the Shelf", "Shelve 10 compounds.", "shelved", 10),
    ("twenty_shelved", "Twenty Shelved", "Shelve 20 compounds.", "shelved", 20),
    ("every_flask", "Every Flask", "Shelve all %d compounds." % TOTAL, "shelved", TOTAL),
    ("fire_starter", "Fire Starter", "Shelve every order in %s." % CHAPTER_NAME[BURNING], "ch%d" % BURNING, CHAPTER_SIZE[BURNING]),
    ("salt_of_the_earth", "Salt of the Earth", "Shelve every order that makes a salt.", "salts", len(SALT_ORDERS)),
    ("acid_test", "Acid Test", "Shelve every order in %s." % CHAPTER_NAME[ACIDS], "ch%d" % ACIDS, CHAPTER_SIZE[ACIDS]),
    ("the_works", "The Works", "Shelve every order in %s." % CHAPTER_NAME[WORKS], "ch%d" % WORKS, CHAPTER_SIZE[WORKS]),
    ("quarter_table", "Quarter Table", "Light %d tiles of the periodic table." % QUARTER, "found", QUARTER),
    ("half_table", "Half Table", "Light %d tiles of the periodic table." % HALF, "found", HALF),
    ("full_table", "Full Table", "Light every tile on the bench (%d)." % BENCH, "found", BENCH),
    ("oxygen_everywhere", "Oxygen Everywhere", "Shelve %d orders that use oxygen." % OXYGEN_NEED, "oxygen", OXYGEN_NEED),
    ("straight_through", "Straight Through", "Shelve %d orders without asking for a suggestion." % CLEAN_NEED, "clean", CLEAN_NEED),
    ("right_product", "Right Product", "Choose the right list first time in %d product rounds." % FIRST_NEED, "first", FIRST_NEED),
)

IDS = tuple(a[0] for a in ACHIEVEMENTS)
FACTS = ("shelved", "found", "salts", "oxygen", "clean", "first") + tuple("ch%d" % c for c in range(len(CHAPTER_SIZE)))


def facts_of(shelf, found, hinted, first):
    """The numbers the achievements read: `shelf` (order ids on the shelf), `found` (how many bench elements are lit), `hinted`
    (order id -> highest suggestion rung pressed while it was not yet shelved) and `first` (product rounds chosen right on the
    first try)."""
    out = {"shelved": len(shelf), "found": found, "first": len(first)}
    out["salts"] = sum(1 for rid in SALT_ORDERS if rid in shelf)
    out["oxygen"] = sum(1 for rid in OXYGEN_ORDERS if rid in shelf)
    out["clean"] = sum(1 for rid in shelf if not hinted.get(rid))
    for c, chapter in enumerate(reactions.CHAPTERS):
        out["ch%d" % c] = reactions.chapter_shelved(shelf, c)
    return out


def earned(facts):
    """The ids earned right now, in manifest order."""
    return [i for i, _l, _d, fact, need in ACHIEVEMENTS if facts.get(fact, 0) >= need]


def view(facts):
    out = []
    for i, label, description, fact, need in ACHIEVEMENTS:
        have = min(facts.get(fact, 0), need)
        out.append({"id": i, "label": label, "description": description, "earned": have >= need, "have": have, "need": need})
    return out
