"""Picture Grid -- achievements (the hub-wide framework: a static manifest `achievements.json` plus `achievements_earned` in the save).

Everything is computed from facts about the player's progress (the hung set, the tally, the hint record, the slideshow flag), never
stored separately, so a loaded save and a played one can never disagree and the saved list is a write-only projection that load
never reads back. All fourteen are reachable by plain play on any difficulty (the level only changes how the hint ladder opens and
no achievement reads it), none is hidden, none is timed or luck-based, and every one shows a number so the player can see how
close they are. Nothing here reads a clock or a random source.
"""

import pictures

TOTAL = len(pictures.ORDER)
GALLERY_SIZE = [len(g["pictures"]) for g in pictures.GALLERIES]
BIG_SIDE = max(p.width for p in pictures.ALL)          # the largest frame (15 by 15)
CLEAN_NEED = 10
CELLS_NEED = 10000

# (id, label, description, fact, need). A gallery fact is "gal<index>", counting the pictures hung in that gallery.
ACHIEVEMENTS = (
    ("first_frame", "First Frame", "Hang your first picture.", "hung", 1),
    ("ten_hung", "Ten Hung", "Hang 10 pictures.", "hung", 10),
    ("thirty_hung", "Thirty Hung", "Hang 30 pictures.", "hung", 30),
    ("sixty_hung", "Sixty Hung", "Hang every picture.", "hung", TOTAL),
    ("small_hands", "Small Hands", "Hang every picture in Instruments.", "gal0", GALLERY_SIZE[0]),
    ("machine_shop", "Machine Shop", "Hang every picture in Small Machines.", "gal1", GALLERY_SIZE[1]),
    ("robot_row", "Robot Row", "Hang every picture in Robots.", "gal2", GALLERY_SIZE[2]),
    ("station_rooms", "Station Rooms", "Hang every picture in Station Rooms.", "gal3", GALLERY_SIZE[3]),
    ("deep_sky_done", "Deep Sky Done", "Hang every picture in Deep Sky.", "gal4", GALLERY_SIZE[4]),
    ("the_long_wall", "The Long Wall", "Hang every picture in The Long Wall.", "gal5", GALLERY_SIZE[5]),
    ("big_one", "Big One", "Hang a %d by %d picture." % (BIG_SIDE, BIG_SIDE), "big", 1),
    ("clean_lines", "Clean Lines", "Hang %d pictures without asking for a suggestion." % CLEAN_NEED, "clean", CLEAN_NEED),
    ("slow_light", "Slow Light", "Open the Slideshow.", "slides", 1),
    ("ten_thousand", "Ten Thousand", "Fill %s cells." % format(CELLS_NEED, ","), "cells", CELLS_NEED),
)

IDS = tuple(a[0] for a in ACHIEVEMENTS)
FACTS = ("hung", "big", "clean", "slides", "cells") + tuple("gal%d" % g for g in range(len(GALLERY_SIZE)))


def facts_of(solved, hinted, fills, slides):
    """The numbers the achievements read: `solved` (hung picture ids), `hinted` (picture id -> highest rung asked while it was first
    being solved), the player's own fills, and whether the slideshow was ever opened."""
    out = {"hung": len(solved), "cells": fills, "slides": 1 if slides else 0}
    out["big"] = sum(1 for pid in solved if pictures.BY_ID[pid].width == BIG_SIDE and pictures.BY_ID[pid].height == BIG_SIDE)
    out["clean"] = sum(1 for pid in solved if not hinted.get(pid))
    for g in range(len(GALLERY_SIZE)):
        out["gal%d" % g] = pictures.gallery_hung(solved, g)
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
