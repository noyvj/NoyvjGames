"""Continuum -- K22: consulting mode, an optional harder scenario.

Instead of growing a settlement from nothing, the player is called in to a
pre-built city that is already in trouble and has a fixed number of seasons
to turn it around. It is opt-in and only offered before any season has been
played on a fresh Tribal start (it replaces the settlement wholesale), and
it can be abandoned back to a fresh start at any time.

The goal: bring the sustainability score up to "Steady" or better (using the
same hard-mode-aware bands as the rest of the game) and hold it for
`HOLD_SEASONS` seasons in a row, within `SEASON_LIMIT` seasons of arriving.
Winning or missing the deadline only records a result; play carries on
either way (Continuum has no forced end state).

Progress rides in `campaign.ui["consulting"]` and is validated on every read
(`clean()`), so a hand-edited or old save can never break the panel: any
malformed value reads as "no consulting case".

The inherited city is described as data (`CASES`). Its research is derived,
not listed: a couple of nodes per tier below the case's own era, chosen so
every tier up to the case's era is unlocked and the player can still research
in their own era. The same function is used to exclude those inherited nodes
from the branch-depth achievements (`inherited_nodes` is a pure function of
the tree and the case's era, so nothing extra needs saving).
"""

import math

import sim
import sustainability

HOLD_SEASONS = 3
SEASON_LIMIT = 30
INHERITED_KNOWLEDGE = 25.0
GOOD_LABELS = ("Steady", "Thriving")

CASES = {
    "smokestack": {
        "label": "The Smokestack City",
        "blurb": (
            "An industrial city that chased output: most workers are in the factories, the air is thick, "
            "the land is worn thin and people are packed into too little shelter. Clear the smoke and house them."
        ),
        "era": "industrial",
        "population": 48,
        "resources": {"food": 18.0, "materials": 55.0, "tools": 4.0, "surplus": 6.0},
        "land_health": 0.5,
        "pollution": 0.75,
        "sprawl": 0.0,
        "buildings": {
            "shelter": 6, "granary": 1, "hearth": 2, "toolworks": 1, "farmland": 3,
            "canals": 1, "public_works": 1, "sanitation_works": 0,
        },
        "allocation": {
            "foragers": 4, "gatherers": 3, "crafters": 2, "keepers": 1, "farmers": 6,
            "administrators": 3, "guildmasters": 3, "factory_workers": 26,
        },
    },
    "sprawl": {
        "label": "The Sprawling Suburbs",
        "blurb": (
            "A digital-age city that spread out faster than it filled in: nobody plans it, transit is missing "
            "and every new resident leans harder on the land. Bring it back into shape."
        ),
        "era": "digital",
        "population": 70,
        "resources": {"food": 25.0, "materials": 80.0, "tools": 6.0, "surplus": 10.0},
        "land_health": 0.55,
        "pollution": 0.3,
        "sprawl": 0.7,
        "buildings": {
            "shelter": 12, "granary": 2, "hearth": 3, "toolworks": 2, "farmland": 4,
            "canals": 2, "public_works": 3, "sanitation_works": 1, "transit_hubs": 0,
        },
        "allocation": {
            "foragers": 4, "gatherers": 5, "crafters": 3, "keepers": 3, "farmers": 12,
            "administrators": 4, "guildmasters": 4, "factory_workers": 20, "planners": 0,
        },
    },
}


def inherited_nodes(tree, era):
    """A modest, valid set of nodes from tiers below `era`'s first tier.

    Up to `TIER_UNLOCK_REQUIREMENT` nodes per tier, each with all its
    prerequisites already chosen, so every tier up to `era` is unlocked.
    """
    import research

    first_tier = research.era_tiers(era)[0]
    chosen = []
    for tier in range(1, first_tier):
        picked = 0
        for node_id in sorted(n for n, node in tree.nodes.items() if node.tier == tier):
            node = tree.nodes[node_id]
            if picked >= research.TIER_UNLOCK_REQUIREMENT:
                break
            if all(p in chosen for p in node.prerequisites) and not node.min_affinity:
                chosen.append(node_id)
                picked += 1
    return chosen


def inherited_for(campaign):
    """Node ids the current consulting case handed over, or an empty list."""
    entry = get(campaign.ui)
    if entry is None:
        return []
    return inherited_nodes(campaign.tree, CASES[entry["case"]]["era"])


def is_pristine(campaign):
    """True while a case can still be taken: a fresh, untouched Tribal start."""
    state = campaign.state
    return (
        campaign.revisiting is None
        and not campaign.era_snapshots
        and state.era == sim.FIRST_ERA
        and campaign.furthest_era == sim.FIRST_ERA
        and state.season <= 1
        and not campaign.tree.researched
        and get(campaign.ui) is None
    )


def apply(campaign, case_id, chronicle=None):
    """Replaces the (pristine) settlement with a consulting case, in place."""
    case = CASES.get(case_id)
    if case is None or not is_pristine(campaign):
        return False
    state = campaign.state
    tree = campaign.tree
    state.era = case["era"]
    state.season = 1
    state.population = case["population"]
    state.growth_progress = 0.0
    for key in state.resources:
        state.resources[key] = 0.0
    state.resources.update(case["resources"])
    for key in state.allocation:
        state.allocation[key] = 0
    state.allocation.update(case["allocation"])
    for key in state.buildings:
        state.buildings[key] = 0
    state.buildings.update(case["buildings"])
    state.land_health = case["land_health"]
    state.pollution = case["pollution"]
    state.sprawl = case["sprawl"]
    state.fed_fraction = 1.0
    state.last_report = None
    state.score_history = []
    state.trajectory = []
    state.calm_streak = 0
    state.clamp_allocation()
    campaign.furthest_era = case["era"]
    tree.current_era = case["era"]
    tree.restore(inherited_nodes(tree, case["era"]))
    state.resources["knowledge"] = INHERITED_KNOWLEDGE
    campaign.ui["consulting"] = {"case": case_id, "start_season": state.season, "streak": 0, "result": None}
    if chronicle is not None:
        chronicle.bootstrap(state, tree, tree.effects())
    return True


def abandon(campaign, chronicle=None):
    """Drops the case and returns the campaign to a fresh Tribal start."""
    import save

    if get(campaign.ui) is None:
        return False
    fresh = save.Campaign()
    campaign.load_dict(fresh.to_dict())
    campaign.ui.pop("consulting", None)
    if chronicle is not None:
        chronicle.bootstrap(campaign.state, campaign.tree, campaign.tree.effects())
    return True


def clean(raw):
    """Validates the saved entry; None when absent or malformed."""
    if not isinstance(raw, dict) or not isinstance(raw.get("case"), str) or raw["case"] not in CASES:
        return None
    start = raw.get("start_season")
    streak = raw.get("streak")
    result = raw.get("result")
    if isinstance(start, bool) or not isinstance(start, int) or start < 1:
        return None
    if isinstance(streak, bool) or not isinstance(streak, int):
        streak = 0
    if result not in (None, "turned_around", "missed"):
        result = None
    return {
        "case": raw["case"],
        "start_season": min(start, 10**7),
        "streak": min(max(streak, 0), HOLD_SEASONS),
        "result": result,
    }


def get(ui):
    """The validated consulting entry from `campaign.ui`, or None."""
    return clean(ui.get("consulting")) if isinstance(ui, dict) else None


def seasons_used(entry, state):
    return max(0, int(state.season) - entry["start_season"])


def step(campaign, effects):
    """Call once after each completed season; returns the entry (or None)."""
    entry = get(campaign.ui)
    if entry is None:
        return None
    if entry["result"] is None:
        state = campaign.state
        score = sustainability.score(state, effects)
        label = sustainability.score_label(score, bool(state.hard_mode))
        entry["streak"] = entry["streak"] + 1 if label in GOOD_LABELS else 0
        if entry["streak"] >= HOLD_SEASONS:
            entry["result"] = "turned_around"
        elif seasons_used(entry, state) >= SEASON_LIMIT:
            entry["result"] = "missed"
    campaign.ui["consulting"] = entry
    return entry


def status_text(entry, state):
    """One line for the panel, or '' with no case."""
    if entry is None:
        return ""
    case = CASES[entry["case"]]["label"]
    used = seasons_used(entry, state)
    if entry["result"] == "turned_around":
        return f"{case}: turned around in {used} seasons. The council thanks you."
    if entry["result"] == "missed":
        return f"{case}: the {SEASON_LIMIT}-season window has closed without a lasting turnaround. You can keep playing."
    left = max(0, SEASON_LIMIT - used)
    return (
        f"{case}: hold a Steady or better score for {HOLD_SEASONS} seasons in a row "
        f"({entry['streak']} of {HOLD_SEASONS} so far, {left} seasons left)."
    )


def is_finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)
