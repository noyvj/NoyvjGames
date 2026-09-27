"""Per-resource farming tips (batch B #7), read from the Warframe Wiki, not written by hand.

For each tracked resource listed below, the resource's own Wiki page
(https://wiki.warframe.com/w/<Resource_Name>) was fetched on 2026-09-27 and asked for the
sentence(s) that state a drop chance, a quantity obtained, or a best/recommended place.
Each stored "text" is that page sentence, so nothing is a hand-written tip and no number
was recalled from memory. The riskier figures (the Gyromag Systems, Breath Of The
Eidolon, Condroc Wing and Seram Beetle Shell entries) were re-read with a second,
differently worded fetch and agreed. Where a page states no drop rate or best place,
the entry says so instead of guessing.

SCOPE: the tracker follows 65 resources; this covers the 25 MOST NEEDED first, ranked by
how many of the 33 tracked parts' recipes use the resource (ties: total units needed at
the default targets). The other 40 have no stored tip yet.

KNOWN GAP: Coprite Alloy's page shows an "Enemy Drop Tables" section, but two separate
reads of it disagreed on the chances, so no figure is stored for it (unverifiable).
"""

WIKI = "https://wiki.warframe.com/w/"
READ_DATE = "2026-09-27"
TRACKED = 65

_REFINED_NOTE = ("The Wiki page names no drop rate or best node for this refined resource: it is made in the "
                 "Foundry (see its refine line and the raw material's own page).")

# The 25 most-needed resources in ranking order -> (section, the page's own sentence(s)) or (None, note).
_TIPS = {
    "Fish Scales": ("Acquisition", "Fish Scales can be acquired by taking fish to Fisher Hai-Luk to have them filleted. "
                    "The number of scales increases with the size of the fish captured, independently of weight."),
    "Pyrotic Alloy": (None, _REFINED_NOTE),
    "Esher Devar": (None, _REFINED_NOTE),
    "Tear Azurite": (None, _REFINED_NOTE),
    "Marquise Veridos": (None, _REFINED_NOTE),
    "Grokdrul": ("Drop Locations", "Grokdrul is a resource that can be found in Grineer camps on Plains of Eidolon, stored in drums."),
    "Coprite Alloy": (None, "Not stored: two reads of this page's drop table disagreed on the chances, so no figure is shown."),
    "Iradite": ("Gathering Tips", "Beginning a level 40-60 bounty will cause deposits to yield 3-5 Iradite."),
    "Fersteel Alloy": (None, _REFINED_NOTE),
    "Nistlepod": ("Drop Locations", "Nistlepod is resource that can be found in high-elevated areas of the Plains of Eidolon, "
                  "located on the mountainous regions of Mount Nang and Ostwan Range."),
    "Tromyzon Entroplasma": ("Acquisition", "Catch Tromyzon in Orb Vallis Pond Hotspots during Cold weather and dismantle them "
                             "via The Business in Fortuna: each Tromyzon yields one Entroplasma."),
    "Cetus Wisp": ("Tips", "During the day, 3-4 Wisps will spawn across the entirety of the Plains. At night, the number of "
                   "Wisps spawned will increase to 6-8."),
    "Gyromag Systems": ("Mission Drop Tables", "Profit-Taker Orb Bounty Phase 4 drops Gyromag Systems: 28.57% chance, quantity 5 "
                        "(Phases 1 to 3 list 25%)."),
    "Radiant Zodian": (None, _REFINED_NOTE),
    "Vega Toroid": ("Gathering Tips", "Spaceport, Orb Vallis: try to get one of the enemies to put down a Reinforcement Beacon "
                    "and wait until the beacon hits Alert Level 4."),
    "Breath Of The Eidolon": ("Mission Drop Tables", "Cetus Bounty Lvl 40-60 Stage 1 has a 50% chance to drop 5 of this resource "
                              "(the later stages list 16.89% to 21.74%)."),
    "Nano Spores": ("Gathering Tips", "Deimos, Saturn, Neptune, and Eris Survivals and Defense missions may be the best way to "
                    "get Nano Spores quickly."),
    "Plastids": ("Farming Locations", "They are usually found in quantities of 15 to 25. They drop from enemies, Storage "
                 "Containers and Lockers."),
    "Scrap": ("Acquisition", "Scrap can be acquired by dismantling Servofish at The Business in Fortuna. The yield is increased "
              "by how intricate the caught fish is."),
    "Travocyte Alloy": (None, _REFINED_NOTE),
    "Venerdo Alloy": (None, _REFINED_NOTE),
    "Benign Infested Tumor": ("Acquisition", "Benign Infested Tumors can be acquired by taking Deimos fish to Daughter to have "
                              "them filleted. The number of tumors increases with the size of the fish captured."),
    "Condroc Wing": ("Enemy Drop Tables", "Common Condroc, Emperor Condroc and Rogue Condroc each drop Condroc Wing: 100% chance, "
                     "quantity 1 per kill."),
    "Seram Beetle Shell": ("Acquisition", "Each Glappid cut yields one Seram Beetle Shell. Tusk Thumper Domas also have a "
                           "chance to drop Seram Beetle Shells upon defeat."),
    "Cuthol Tendrils": ("Acquisition", "Cuthol Tendrils are acquired by cutting up Cuthol caught through Fishing. "
                        "Each Cuthol cut yields one Cuthol Tendril."),
}

ORDER = tuple(_TIPS)
COVERED = len(ORDER)


def wiki_page(resource):
    return WIKI + resource.replace(" ", "_")


def tip(resource):
    """The stored tip for a resource, or None when it is outside the 25 read."""
    entry = _TIPS.get(resource)
    if entry is None:
        return None
    section, text = entry
    return {"resource": resource, "section": section, "text": text if section else None,
            "note": None if section else text, "url": wiki_page(resource), "date": READ_DATE}


def tip_line(resource):
    """A one-line rendering for a resource row, or "" when nothing is stored."""
    found = tip(resource)
    if found is None:
        return ""
    if found["text"]:
        return f"Wiki tip ({found['section']}, read {READ_DATE}): {found['text']}"
    return found["note"]


def all_tips():
    return [tip(name) for name in ORDER]


def summary_text():
    with_text = sum(1 for t in all_tips() if t["text"])
    return (f"{COVERED} of the {TRACKED} tracked resources are covered, the most-needed first (ranked by how many tracked parts use "
            f"them); {with_text} carry a sentence from the Wiki, the rest say what the page does not state. "
            f"Each was read from its own Wiki page on {READ_DATE}.")
