"""Slingshot -- the missions in order, the chapters, the gates and the stored reference plans.

Chapter n+1 opens when OPEN_AT (5) missions of chapter n are done (any five); inside a chapter every mission is open in any order. The
reference plans, their fuel costs and the budgets are written by tools/solve.py into refplans.py.
"""

import missions_c1
import missions_c2
import missions_c3

try:
    import refplans
    PLANS = refplans.PLANS
except ImportError:                                  # before the solver has run
    PLANS = {}

OPEN_AT = 5
CHAPTERS = []
ALL = []
for _mod in (missions_c1, missions_c2, missions_c3):
    ch = dict(_mod.CHAPTER)
    ch["missions"] = _mod.MISSIONS
    CHAPTERS.append(ch)
    for _m in _mod.MISSIONS:
        _m["steps"] = _m["scene"]["steps"]
        ref = PLANS.get(_m["id"])
        if ref:
            _m["ref"] = ref["ref"]
            _m["alt"] = ref.get("alt")
            _m["cost"] = ref["cost"]
            _m["budget"] = ref["budget"]
        else:
            _m.update({"ref": None, "alt": None, "cost": 0.0, "budget": 0.0})          # before the solver has run for this mission
        ALL.append(_m)

BY_ID = {m["id"]: m for m in ALL}
ORDER = [m["id"] for m in ALL]


def chapter_need(index):
    """Missions of the chapter before that must be done to open chapter `index` (0-based); 0 for the first."""
    return 0 if index == 0 else min(OPEN_AT, len(CHAPTERS[index - 1]["missions"]))


def chapter_done(reached, index):
    return sum(1 for m in CHAPTERS[index]["missions"] if m["id"] in reached)


def chapter_open(reached, index):
    return index == 0 or chapter_done(reached, index - 1) >= chapter_need(index)


def mission_open(reached, mid):
    return chapter_open(reached, BY_ID[mid]["chapter"] - 1)
