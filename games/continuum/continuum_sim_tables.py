"""Continuum's simulation tables: the era order and labels, the roles and buildings of every era (labels, blurbs, emoji, costs),
the starting values and the starting scenarios. Data only. Ask for this file to add a role, a building or a scenario.
Part of the split of the old single-file sim.py: see "File map" in games/continuum/CLAUDE.md.
"""

# --- eras -------------------------------------------------------------
# The full arc, in play order and build order (the design doc's proposed
# list, confirmed at Phase 1). Only "tribal" is implemented; the rest are
# declared now because the research tree's tier map and the save file's
# era-snapshot dict both key off this order.
ERA_ORDER = [
    "tribal",
    "agrarian",
    "classical",
    "medieval",
    "industrial",
    "digital",
    "space",
    "relay",
]

ERA_LABEL = {
    "tribal": "Tribal",
    "agrarian": "Agrarian",
    "classical": "Classical",
    "medieval": "Medieval",
    "industrial": "Industrial",
    "digital": "Digital",
    "space": "Space Age",
    "relay": "Relay Age",
}

# Eras with real content behind them. Phase 2/3 append as each is built.
# Nothing reads this yet — it exists so that the moment a second era ships,
# "which eras are playable" has one answer rather than being inferred from
# whichever table happens to have an entry.
IMPLEMENTED_ERAS = [
    "tribal", "agrarian", "classical", "medieval", "industrial", "digital", "space", "relay",
]

FIRST_ERA = ERA_ORDER[0]


def era_index(era):
    return ERA_ORDER.index(era)


# --- roles and buildings ------------------------------------------------
# Population is allocated across roles; unassigned people are idle. Roles
# are era-scoped (see ERA_ROLES below) but share one allocation dict, so a
# later era's roster EXTENDS what's available rather than replacing it —
# a role or building unlocked in an earlier era never goes away just
# because the settlement has moved on. This is what Milestone 8's own
# CLAUDE.md build notes call "one continuous, growing city" rather than
# seven separate rosters swapped in and out.
#
# ERA_ROLES/ERA_BUILDINGS are the source of truth for WHICH roles/buildings
# a settlement that has reached a given era can use (see roles_for_era()/
# buildings_for_era() below); ROLES/BUILDINGS stay flat lists of every role
# and building this build knows about at all, since the allocation/
# buildings dicts, save.py's key-by-key restore, and clamp_allocation() all
# need to reason about every key that could exist, not just the ones the
# current era has unlocked.
ERA_ROLES = {
    "tribal": ["foragers", "gatherers", "crafters", "keepers"],
    "agrarian": ["farmers"],
    "classical": ["administrators"],
    "medieval": ["guildmasters"],
    "industrial": ["factory_workers"],
    "digital": ["planners"],
    "space": ["architects"],
    "relay": ["wayfinders"],
}

ERA_BUILDINGS = {
    "tribal": ["shelter", "granary", "hearth", "toolworks"],
    "agrarian": ["farmland"],
    "classical": ["canals"],
    "medieval": ["public_works"],
    "industrial": ["sanitation_works"],
    "digital": ["transit_hubs"],
    "space": ["habitat_rings"],
    "relay": ["relay_stations"],
}

ROLES = [role for era in ERA_ORDER for role in ERA_ROLES.get(era, [])]
BUILDINGS = [building for era in ERA_ORDER for building in ERA_BUILDINGS.get(era, [])]


def roles_for_era(era):
    """Every role unlocked by `era` or an earlier one, in stable order."""
    return [role for e in ERA_ORDER[: era_index(era) + 1] for role in ERA_ROLES.get(e, [])]


def buildings_for_era(era):
    """Every building unlocked by `era` or an earlier one, in stable order."""
    return [b for e in ERA_ORDER[: era_index(era) + 1] for b in ERA_BUILDINGS.get(e, [])]


# The label/blurb/emoji tables below are the source of truth for the Work
# and Build panels' text: game.py's render_work()/render_buildings() build
# each row from these every render (Milestone 8 made these panels dynamic,
# the same way the research panel already was, now that a second era's
# roster exists — see this file's own "only Tribal is modelled so far"
# note above, now out of date, and the Milestone 8 build notes for why the
# emoji moved here from static markup once rows stopped being static).
ROLE_LABEL = {
    "foragers": "Foragers",
    "gatherers": "Gatherers",
    "crafters": "Crafters",
    "keepers": "Keepers",
    "farmers": "Farmers",
    "administrators": "Administrators",
    "guildmasters": "Guildmasters",
    "factory_workers": "Factory Workers",
    "planners": "Urban Planners",
    "architects": "Habitat Architects",
    "wayfinders": "Wayfinders",
}

ROLE_BLURB = {
    "foragers": "Bring in food from the land.",
    "gatherers": "Bring in wood, fibre and stone.",
    "crafters": "Turn materials into tools.",
    "keepers": "Hold and pass on what the settlement knows.",
    "farmers": "Work cultivated fields — more food per person than foraging, especially with farmland built.",
    "administrators": (
        "Coordinate canal labor and civic record-keeping. Produce nothing "
        "themselves, but a canal without administrators to run it delivers "
        "little of what it was built for."
    ),
    "guildmasters": (
        "Trained through a guild rather than picking up the craft on the "
        "job — turn materials into tools faster than an ordinary crafter, "
        "especially with a Knapping Site to work from."
    ),
    "factory_workers": (
        "Mechanized extraction and production, far beyond what an ordinary "
        "gatherer manages by hand — but the smoke and waste it throws off "
        "doesn't go anywhere on its own. Sanitation Works is what actually "
        "deals with that."
    ),
    "planners": (
        "Produce nothing themselves — their whole job is deciding where the "
        "next resident actually goes. Left unmanaged, growth spreads "
        "outward faster than the settlement itself grows; planners are what "
        "keeps that from being the default."
    ),
    "architects": (
        "Produce nothing either — like Administrators once did for canals, "
        "their whole job is making a Habitat Ring actually work for the "
        "people living in it. A ring with nobody designing its layout still "
        "holds bodies; it just doesn't serve them well, and out here there "
        "is no unmanaged sprawl to fall back into instead — only however "
        "well or badly this ring was laid out."
    ),
    "wayfinders": (
        "Carry the settlement's banked surplus out along the relay links to "
        "the outlying holdings — routes, schedules, hauling, resupply. Like "
        "Habitat Architects they produce nothing at home, but here the "
        "worker and the building are two halves of one throughput: "
        "Wayfinders supply the hauling, Relay Stations set how much can "
        "move at all, and the holdings only get as much as the smaller of "
        "the two."
    ),
}

ROLE_EMOJI = {
    "foragers": "🌾",
    "gatherers": "🪵",
    "crafters": "🪓",
    "keepers": "🔥",
    "farmers": "🌱",
    "administrators": "📜",
    "guildmasters": "⚒️",
    "factory_workers": "🏭",
    "planners": "🗺️",
    "architects": "🛰️",
    "wayfinders": "🧭",
}

BUILDING_LABEL = {
    "shelter": "Shelter",
    "granary": "Storage Pit",
    "hearth": "Fire Circle",
    "toolworks": "Knapping Site",
    "farmland": "Farmland",
    "canals": "Canals",
    "public_works": "Public Works",
    "sanitation_works": "Sanitation Works",
    "transit_hubs": "Transit Hubs",
    "habitat_rings": "Habitat Rings",
    "relay_stations": "Relay Stations",
}

BUILDING_BLURB = {
    "shelter": "Houses people. Nobody grows a settlement they can't sleep in.",
    "granary": "Holds food that would otherwise spoil.",
    "hearth": "Where the settlement gathers. Warmth, cooking, and a shared story.",
    "toolworks": "A dedicated place to work stone — crafters produce more.",
    "farmland": "Cultivated fields — farmers produce more food per plot worked.",
    "canals": (
        "Directed irrigation, at city scale — but only as good as the "
        "administrators coordinating it. An unstaffed canal is just a ditch."
    ),
    "public_works": (
        "Drains, waste removal, flood and fire works — paid for before "
        "disaster forces the issue, not after. Nobody works here; it just "
        "covers more of the settlement against a bad season the more of "
        "it gets built."
    ),
    "sanitation_works": (
        "Drains, filtration and waste removal built to keep pace with a "
        "factory floor, not a farmhouse. Nobody works here either — it "
        "just absorbs more of the smoke and waste Factory Workers throw "
        "off the more of it gets built, before it can pile up and start "
        "dragging on the settlement's growth."
    ),
    "transit_hubs": (
        "Dense, mixed-use nodes built around transit rather than roads out "
        "— the same number of people housed in less land, not more of it. "
        "Nobody works here; it just absorbs sprawl that has already built "
        "up, the more of it gets built, the same way Sanitation Works "
        "absorbs pollution."
    ),
    "habitat_rings": (
        "A sealed, rotating ring of living space — no more land outside it "
        "to spread into, no weather to wait out, no elsewhere for a bad "
        "layout to matter less. Holds people the moment it's built; only "
        "Habitat Architects determine whether it actually serves them."
    ),
    "relay_stations": (
        "A link out to a holding beyond the settlement — surface outpost, "
        "orbital platform or first footing off-world — that houses a few "
        "more people and opens up land the core doesn't have. It is also a "
        "promise: those residents can only be kept supplied with surplus "
        "sent from home, and Wayfinders have to carry it. A relay whose "
        "holding goes unsupplied is worse than no relay at all."
    ),
}

BUILDING_EMOJI = {
    "shelter": "⛺",
    "granary": "🫙",
    "hearth": "🔥",
    "toolworks": "🪨",
    "farmland": "🌿",
    "canals": "🏛️",
    "public_works": "🚰",
    "sanitation_works": "🏗️",
    "transit_hubs": "🚉",
    "habitat_rings": "🛞",
    "relay_stations": "📡",
}

BUILDING_COST = {  # in materials
    "shelter": 12.0,
    "granary": 18.0,
    "hearth": 15.0,
    "toolworks": 25.0,
    "farmland": 20.0,
    "canals": 35.0,
    "public_works": 40.0,
    "sanitation_works": 45.0,
    "transit_hubs": 55.0,
    "habitat_rings": 70.0,
    "relay_stations": 85.0,
}

SHELTER_CAPACITY = 4  # people housed per shelter
GRANARY_STORAGE = 25.0  # extra food storage per storage pit
HEARTH_SERVES = 8.0  # people whose social/cultural needs one fire circle meets
TOOLWORKS_CRAFT_BONUS = 0.3  # additive multiplier on tool output per knapping site
FARMLAND_YIELD_BONUS = 0.4  # additive multiplier on farmer food output per field

# --- starting conditions ----------------------------------------------
START_POPULATION = 6
MIN_POPULATION = 1
START_FOOD = 20.0
START_MATERIALS = 20.0
START_TOOLS = 2.0
START_KNOWLEDGE = 0.0
START_SURPLUS = 0.0
START_BUILDINGS = {
    "shelter": 2,
    "granary": 0,
    "hearth": 1,
    "toolworks": 0,
    "farmland": 0,
    "canals": 0,
    "public_works": 0,
    "sanitation_works": 0,
    "transit_hubs": 0,
    "habitat_rings": 0,
    "relay_stations": 0,
}
START_ALLOCATION = {
    "foragers": 3,
    "gatherers": 2,
    "crafters": 0,
    "keepers": 0,
    "farmers": 0,
    "administrators": 0,
    "guildmasters": 0,
    "factory_workers": 0,
    "planners": 0,
    "architects": 0,
    "wayfinders": 0,
}
# START_ALLOCATION always assigns exactly 5 workers (3 foragers + 2
# gatherers) -- every SCENARIOS["population"] below is deliberately kept
# at 5 or above so a fresh CityState() never starts with more workers
# assigned than it has people (which CityState.__init__ doesn't itself
# defend against, unlike every later mutation path, since a fresh
# settlement's own starting numbers are asserted sane by
# tests/test_core_loop.py rather than clamped defensively at construction
# time).

# --- K12: starting scenarios (opt-in initial-condition variants) --------
# planning/TODO.md's K12: "let the player pick a starting scenario or
# difficulty variant that meaningfully changes initial conditions or
# challenge level" -- before/at game start, following the same "toggle
# set, not a full menu system" UI shape Grid's own difficulty toggles
# established (see games/grid/CLAUDE.md's settings-panel section).
#
# Deliberately NOT wired through NEUTRAL_EFFECTS: `effects` is the
# research tree's one seam into the season loop (see "Research reaches
# the simulation through exactly one seam" above) -- an ongoing modifier
# a node can grant. A scenario is the opposite shape: a one-time starting
# condition applied once, at CityState construction, never revisited by
# the season loop again. Every value below is a literal starting number,
# not a multiplier, so `CityState(scenario="frontier")` reads exactly like
# a harder opening hand, not a hidden ongoing penalty.
SCENARIOS = {
    "standard": {
        "label": "Standard Start",
        "blurb": "The settlement as designed — no thumb on the scale.",
        "population": START_POPULATION,
        "food": START_FOOD,
        "materials": START_MATERIALS,
        "tools": START_TOOLS,
        "land_health": 1.0,
    },
    "frontier": {
        "label": "Harsh Frontier",
        "blurb": "Fewer hands, thinner stores, and land that's already been worked hard. A tougher opening.",
        "population": 5,
        "food": 10.0,
        "materials": 10.0,
        "tools": 1.0,
        "land_health": 0.75,
    },
    "fertile": {
        "label": "Fertile Valley",
        "blurb": "A generous opening: more people, deeper stores, and land at full health.",
        "population": 7,
        "food": 30.0,
        "materials": 26.0,
        "tools": 3.0,
        "land_health": 1.0,
    },
    # O-8: a fourth opening, offered only to a player who has already
    # reached the Space Age (or later) once -- see REFUGE_UNLOCK_ERA and
    # game.py's `refuge_unlocked()`. Deliberately a different SHAPE from the
    # three above, not just a harder or easier dial: the other three vary
    # how much you start with, this one varies what you start with. A
    # crowd of people and the memory of how things are done (`knowledge`,
    # the elders), but worked-out land, thin stores and not enough roofs.
    # The pressure is inverted from Harsh Frontier (too few hands): here
    # there are too many mouths for the land, so the first job is to put
    # the crowd to work and let the ground recover before asking more of it.
    "refuge": {
        "label": "Refuge Start",
        "blurb": (
            "A larger, older group arrives with the elders' memory but on worn land: "
            "twice the mouths, thin stores and too few roofs. Recover the ground before you grow."
        ),
        "population": 12,
        "food": 26.0,
        "materials": 16.0,
        "tools": 1.0,
        "land_health": 0.6,
        "knowledge": 6.0,
    },
    # K-2: three more openings, each unlocked by a Dynasty perk (dynasty.py's
    # SCENARIO_UNLOCKS; gated in game.py's UI only, so a save carrying one
    # always loads). Like the Refuge they vary WHAT you start with rather than
    # how much, and none is strictly better than Standard: a bigger band on
    # thin stores, a food-rich valley short of timber, a small group that
    # carries the elders' books.
    "hardy": {
        "label": "Hardier Tribe",
        "blurb": (
            "A bigger, tougher band fills every roof from the first day, but it arrives with "
            "thin stores and a worked-over patch of ground. Feed them before you grow them."
        ),
        "population": 8,
        "food": 14.0,
        "materials": 12.0,
        "tools": 1.0,
        "land_health": 0.9,
    },
    "river": {
        "label": "River Valley",
        "blurb": (
            "Fish and silt: the larder starts full and the land is at full health, "
            "but there is little timber and almost no tools. Build before you coast."
        ),
        "population": 6,
        "food": 30.0,
        "materials": 12.0,
        "tools": 1.0,
        "land_health": 1.0,
    },
    "heirloom": {
        "label": "Library Heirloom",
        "blurb": (
            "A small group that carries the elders' books: ten knowledge to spend on the first "
            "discoveries, but fewer hands and lighter stores."
        ),
        "population": 5,
        "food": 18.0,
        "materials": 14.0,
        "tools": 1.0,
        "land_health": 1.0,
        "knowledge": 10.0,
    },
}
DEFAULT_SCENARIO = "standard"
# O-8: the era a player must have reached (in any settlement, ever) to be
# offered the Refuge Start. Gated in game.py's UI, not in the engine:
# `CityState(scenario="refuge")` always works, so a save carrying it loads.
REFUGE_UNLOCK_ERA = "space"


def scenario_config(scenario_id):
    """The starting-condition dict for `scenario_id`, defaulting to
    DEFAULT_SCENARIO for anything unrecognised (an old save, a hand-edited
    one, or simply `None`) — the same "unknown input degrades to the safe
    default rather than raising" standard `save.restore_city()`'s own
    `era` handling already holds itself to."""
    return SCENARIOS.get(scenario_id, SCENARIOS[DEFAULT_SCENARIO])
