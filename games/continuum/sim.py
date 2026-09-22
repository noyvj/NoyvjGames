"""Continuum — city simulation core.

Milestone 1 of Phase 1. This module is the settlement engine: population,
resources, worker allocation, buildings, production, consumption, and the
land-health feedback loop. It is deliberately free of DOM code, of scoring
code, and of research code — `game.py` owns the browser, `sustainability.py`
owns the score, `research.py` owns the tree. Keeping those apart is the
tech note the design doc is most insistent about, since seven eras' worth
of content lands on top of this file.

Two properties are load-bearing for everything that comes later:

1. **Deterministic.** No RNG anywhere in the season loop. Every number a
   season produces is a pure function of the state that went into it, which
   is what makes both testing and the save system's era-snapshot/revisit
   behaviour tractable.
2. **Effects-driven.** Every yield, capacity and rate is multiplied through
   an `effects` dict (see `NEUTRAL_EFFECTS`). Milestone 1 always passes the
   neutral one; Milestone 3's research tree passes an aggregate of the
   player's researched nodes. Building that seam in from the start is what
   stops the research tree from having to reach into the simulation later.

Tribal (Phase 1), Agrarian (Milestone 8), Classical (Milestone 9),
Medieval (Milestone 10), Industrial (Milestone 11) and Digital (Milestone
12) are modelled so far. Era-specific constants live in per-era tables
keyed by era id (see ERA_ROLES/ERA_BUILDINGS) so each remaining era adds a
table entry rather than a second copy of this file — Agrarian's own
Farmers role and Farmland building were the first proof that pattern
actually extends cleanly rather than requiring a rewrite; Classical's
Administrators/Canals extend it a second time, this time with a building
whose bonus depends on the role rather than merely being multiplied by it
(see CANAL_YIELD_BONUS); Medieval's Guildmasters/Public Works extend it a
third time, this time with a building that isn't staffed at all — Public
Works is read only by sustainability.py, not by the production math below
(see PUBLIC_WORKS_COVERAGE_PER_BUILDING). Industrial's Factory Workers/
Sanitation Works extend it a fourth time, and this is the first era where
the new content has a GROWTH-side mechanical consequence, not only a
sustainability-score one: Factory Workers produce `pollution`, a lagged
stock read directly by the population-growth step below (see the
"pollution and industrial growth cost" section), grounded in
continuum-real-world-sources.md's Economic Journal source showing
industrial pollution measurably reducing long-run city growth historically
— see CLAUDE.md's Milestone 11 build notes for the full reasoning.
Digital's Urban Planners/Transit Hubs extend it a fifth time, and this era's
own growth-side consequence deliberately takes a DIFFERENT shape from
Industrial's: instead of a second direct multiplier on GROWTH_RATE,
`state.sprawl` (also a lagged 0..1 stock, produced by unmanaged population
growth per the National Geographic source on urban areas outgrowing their
populations) amplifies how much land pressure the settlement's existing
extraction already creates — reusing the land_health/GROWTH_MIN_LAND_HEALTH
machinery Phase 1 already built rather than stacking a second bespoke
growth-rate lever alongside pollution's. See CLAUDE.md's Milestone 12 build
notes for the full reasoning.

Space Age (Milestone 13) extends it a sixth and FINAL time, and is
deliberately NOT a seventh copy of the growth-vs-extraction shape every
prior era used. Per CLAUDE.md's Milestone 13 build notes, "post-scarcity
off-world infrastructure" changes the KIND of question this era asks, not
just its numbers: Habitat Architects and Habitat Rings never touch
production, growth, or extraction at all. Instead they determine
`habitat_capacity()` — how much of the population is actually served WELL
by the settlement's off-world ring-habitat layout, per the Dagstuhl/
SpaceCHI source's "usability... at scale" framing — which sustainability.py
reads as a brand-new fourth PROVISION (alongside food/shelter/culture) from
Space Age on, not as a bolt-on penalty/bonus function the way every prior
era's adjustment was. This is the game's first era-specific mechanic to
live in `livability()`/`equity()`'s own shared plumbing rather than beside
it.
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
]

ERA_LABEL = {
    "tribal": "Tribal",
    "agrarian": "Agrarian",
    "classical": "Classical",
    "medieval": "Medieval",
    "industrial": "Industrial",
    "digital": "Digital",
    "space": "Space Age",
}

# Eras with real content behind them. Phase 2/3 append as each is built.
# Nothing reads this yet — it exists so that the moment a second era ships,
# "which eras are playable" has one answer rather than being inferred from
# whichever table happens to have an entry.
IMPLEMENTED_ERAS = ["tribal", "agrarian", "classical", "medieval", "industrial", "digital", "space"]

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
}

ERA_BUILDINGS = {
    "tribal": ["shelter", "granary", "hearth", "toolworks"],
    "agrarian": ["farmland"],
    "classical": ["canals"],
    "medieval": ["public_works"],
    "industrial": ["sanitation_works"],
    "digital": ["transit_hubs"],
    "space": ["habitat_rings"],
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
}
DEFAULT_SCENARIO = "standard"


def scenario_config(scenario_id):
    """The starting-condition dict for `scenario_id`, defaulting to
    DEFAULT_SCENARIO for anything unrecognised (an old save, a hand-edited
    one, or simply `None`) — the same "unknown input degrades to the safe
    default rather than raising" standard `save.restore_city()`'s own
    `era` handling already holds itself to."""
    return SCENARIOS.get(scenario_id, SCENARIOS[DEFAULT_SCENARIO])

# --- production and consumption ---------------------------------------
FOOD_PER_FORAGER = 3.0
# Notably higher than foraging -- the real productivity jump settled
# agriculture gave over foraging/gathering (see
# continuum-real-world-sources.md's Agrarian sources, e.g. the National
# Geographic and HISTORY pieces on the Neolithic Revolution's storable
# surplus). Farmers still scale with the same tool_factor/land_health/
# food_yield_mult as foragers -- agriculture is better, not exempt from
# the land's own limits.
FOOD_PER_FARMER = 5.0
MATERIALS_PER_GATHERER = 2.0
TOOLS_PER_CRAFTER = 0.8
# Guild specialisation (Medieval+, see continuum-real-world-sources.md's
# Fiveable source on guild specialisation): a Guildmaster produces tools
# faster than an ordinary Crafter, the same "same job, more productive
# specialist" bump FOOD_PER_FARMER already gave Farmers over Foragers
# (roughly the same ~1.6x ratio). Guildmasters still route through the
# same craft_bonus/tool_yield_mult chain Crafters do -- one tool economy,
# not two, the same discipline Farmers/Farmland were held to.
TOOLS_PER_GUILDMASTER = 1.3
# Mechanization (Industrial+, see continuum-real-world-sources.md's
# Britannica source on 19th-century industrial growth and the Sociology
# Institute source on urban population rising from 3% to ~50% of the
# world): a Factory Worker's output is a categorically bigger jump over a
# Gatherer's than any previous era's role addition was over its
# predecessor (Farmers/Guildmasters were both roughly a ~1.6x bump per the
# earlier build notes) -- mechanization was a genuinely bigger leap
# historically, not just another same-sized step, so the ratio here is
# deliberately larger. Factory Workers still route through the same
# tool_factor/land_health/materials_yield_mult chain Gatherers do, and
# feed the same shared extraction total -- one materials economy, not two,
# the same discipline every prior era's new role has been held to.
MATERIALS_PER_FACTORY_WORKER = 5.0
MATERIALS_PER_TOOL = 1.0
KNOWLEDGE_PER_KEEPER = 0.6

FOOD_PER_PERSON = 2.0
BASE_FOOD_STORAGE = 30.0

# --- surplus and trade (Agrarian+) --------------------------------------
# Per continuum-real-world-sources.md's Agrarian sources (National
# Geographic/HISTORY on storable surplus; EBSCO on surplus enabling
# specialization), once a settlement has reached the Agrarian era, food
# that would otherwise spoil past storage capacity is partly preserved as
# `surplus` instead of pure waste -- an abstraction of early trade/barter
# networks absorbing what a purely subsistence settlement would have lost.
# The rest still spoils; see CityState.advance_season()'s spoilage step.
SURPLUS_CONVERSION_RATE = 0.4

# --- canals and coordinated labor (Classical+) --------------------------
# Per continuum-real-world-sources.md's Classical sources (The Getty and
# TheCollector on Uruk/Sumer): canal-fed irrigation is what let a city scale
# past what unaided farmland could feed, but the same sources are explicit
# that canal management required *centralized planning and coordinated
# labor* -- it wasn't self-running infrastructure. That's modelled directly:
# a canal's yield bonus is scaled by how fully it is staffed by
# Administrators (capped at 1.0), so a canal built with nobody assigned to
# run it contributes nothing yet -- the building alone isn't the lesson,
# the coordinated labor is. See CityState.advance_season()'s harvest step.
CANAL_YIELD_BONUS = 0.5  # additive multiplier on farmer food output per fully-staffed canal
ADMINISTRATORS_PER_CANAL = 2  # administrators needed to fully staff one canal

# --- public works and shock resilience (Medieval+) ----------------------
# Per continuum-real-world-sources.md's Medieval sources (SAGE's Coomans &
# Hermenault on Ghent, and JHU Press's Magnusson on medieval England), the
# Medieval era's public-works spending is documented as being specifically
# about mitigating risk -- floods, disease, military vulnerability -- not
# about raising output the way Farmland/Canals do. That's why Public Works
# is modelled entirely differently from every other building so far: it
# has NO production formula in this file at all, and is read only by
# sustainability.py's resilience() (see CLAUDE.md's Milestone 10 build
# notes for why a labor-staffing dependency like Canals/Administrators
# would have forced the wrong lesson onto a different source). What this
# file provides is the one number sustainability.py and game.py both need:
# how many people one Public Works building can meaningfully protect.
PUBLIC_WORKS_COVERAGE_PER_BUILDING = 15.0

# --- pollution and the growth-side cost of industry (Industrial+) -------
# Per continuum-real-world-sources.md's Industrial sources -- Britannica on
# 19th-century industrial growth outpacing planning (slums and disease
# before sanitation reform caught up), and, more specifically, the Economic
# Journal (Oxford Academic) study showing industrial pollution measurably
# reduced long-run city growth -- Industrial is the first era where the
# game's central growth-vs-livability tension has to be a real MECHANICAL
# trade-off, not only a sustainability-score-side one the way Agrarian's
# hoarding penalty, Classical's overextension penalty and Medieval's
# public-works bonus all were. `CityState.pollution` is a lagged 0..1
# stock, modelled with the exact same shape `land_health` already uses
# (see the season loop's step 8 below): what happens this season updates
# the stock for the NEXT season's growth check, rather than this one's --
# so a settlement doesn't feel a pollution spike until the season after it
# happened, the same way over-harvesting the land doesn't tank growth the
# instant it happens either. Factory Workers are the only source of it;
# Sanitation Works (built, not staffed -- see the Public Works precedent
# and CLAUDE.md's Milestone 11 build notes for why staffing wasn't the
# right shape here either) is the only thing that absorbs it, and a small
# natural decay (weather, dilution, simply not being added to) always
# pulls it back down on its own even with no Sanitation Works built at
# all, so an idle-but-already-polluted settlement isn't stuck forever.
POLLUTION_PER_FACTORY_WORKER = 0.02  # pollution added per assigned factory worker per season
POLLUTION_NATURAL_DECAY = 0.015  # baseline pollution lost per season regardless of sanitation
SANITATION_ABSORPTION_PER_BUILDING = 0.05  # pollution absorbed per Sanitation Works per season
# How much of GROWTH_RATE is lost at full (1.0) pollution -- the direct
# mechanical read of the Economic Journal source's "measurably reduced
# long-run city growth" finding. Deliberately a SOFT, proportional cost
# (scales the growth rate down) rather than land_health's HARD gate
# (blocks growth outright below GROWTH_MIN_LAND_HEALTH) -- a different
# shape on purpose, since the source describes pollution slowing growth,
# not stopping it dead the way a truly exhausted plot of land would.
POLLUTION_GROWTH_PENALTY_WEIGHT = 0.6

# --- sprawl and the growth-side cost of unmanaged density (Digital+) ----
# Per continuum-real-world-sources.md's Current/Digital sources -- most
# directly National Geographic Education's finding that urban areas grew
# 1.28 times faster than their populations between 2000 and 2014, i.e.
# cities spreading outward faster than they're actually filling up -- this
# is Digital's own growth-vs-livability tension, and the task that spec'd
# this milestone was explicit it should have a real mechanical consequence,
# not just another additive score bonus/penalty the way Agrarian/Classical/
# Medieval's adjustments were. `CityState.sprawl` is a second lagged 0..1
# stock, the same shape POLLUTION_PER_FACTORY_WORKER's model already
# established, but DELIBERATELY WIRED INTO A DIFFERENT LEVER than
# pollution's direct GROWTH_RATE multiplier: sprawl amplifies how much land
# pressure the settlement's existing extraction creates (see the season
# loop's step 8 below), reusing Phase 1's own land_health/
# GROWTH_MIN_LAND_HEALTH machinery instead of stacking a second bespoke
# growth-rate penalty next to Industrial's. Population growth that outpaces
# density investment produces it (unmanaged growth spreads outward, per the
# source); Urban Planners (a role, working proactively every season) and
# Transit Hubs (a building, absorbing what has already accumulated -- the
# same "built, not staffed" shape Public Works/Sanitation Works already
# established) both bring it back down, and a small natural decay (infill,
# slow densification even with no dedicated investment) always pulls it
# down a little on its own, the same "nothing is stuck forever" discipline
# pollution's own decay already uses.
SPRAWL_PER_NEW_RESIDENT = 0.05  # sprawl added per person of season growth, left unmanaged
PLANNER_SPRAWL_MITIGATION = 0.03  # sprawl reduced per assigned planner per season
TRANSIT_HUB_ABSORPTION_PER_BUILDING = 0.05  # sprawl absorbed per Transit Hub per season
SPRAWL_NATURAL_DECAY = 0.01  # baseline sprawl lost per season regardless of investment
# How much extra land pressure the same extraction creates at full (1.0)
# sprawl -- a sprawled-out settlement needs more roads, pipes and cleared
# land to support the same production, so the SAME extraction total leaves
# a bigger real footprint. This is genuinely different in shape from
# POLLUTION_GROWTH_PENALTY_WEIGHT: pollution scales GROWTH_RATE directly
# (a new lever), sprawl instead scales `extraction` itself (an existing
# lever, present since Phase 1) before it's compared against the land's
# sustainable yield -- so a heavily-sprawled Digital settlement can trip
# land_health's existing hard GROWTH_MIN_LAND_HEALTH gate for the exact
# same reason an over-harvesting Tribal one always could, not through a
# second, parallel growth formula.
SPRAWL_EXTRACTION_PENALTY_WEIGHT = 0.5

# --- off-world habitat layout and usability (Space Age+) ----------------
# Per continuum-real-world-sources.md's Space Age sources -- most directly
# the Dagstuhl/SpaceCHI 2025 source on how modular space habitat layouts
# affect real usability "at scale," and Planetizen's framing of NASA's 1977
# "Space Settlements: A Design Study" as literally an urban-planning policy
# document (residential space, schools, transit) rather than something
# categorically different from ordinary city planning. This is deliberately
# NOT a seventh copy of Industrial/Digital's growth-side stock-and-penalty
# shape: "post-scarcity" genuinely changes what the settlement's central
# tension is about, and the task that spec'd this milestone was explicit
# that defaulting to another growth lever just because the last two eras
# used one would be the wrong call here. Habitat Architects and Habitat
# Rings never touch production, extraction, or growth anywhere in this
# file -- `habitat_capacity()` below is read only by sustainability.py's
# provisions(), as a brand-new fourth basic need alongside food/shelter/
# culture, from Space Age on. See CLAUDE.md's Milestone 13 build notes for
# the full reasoning, including why livability/equity (not a bolt-on
# penalty/bonus function) is genuinely the right home for this one.
#
# The shape reused here is deliberately Classical's canal/administrator
# pairing, not Medieval/Industrial/Digital's "unstaffed building" one: a
# Habitat Ring's usefulness is scaled by how many Architects actually
# designed its layout (capped at 1.0), because the Dagstuhl source's whole
# point is that a modular structure's raw capacity and its real usability
# are different things -- the same lesson Classical's canals taught about
# coordinated labor, now applied to coordinated design instead.
RING_CAPACITY_PER_BUILDING = 30.0  # people one FULLY-architected ring can serve well
ARCHITECTS_PER_RING = 3  # architects needed to fully realise one ring's layout

# Tools multiply every gathering yield, capped at one tool per person —
# a settlement can't get more out of the land by hoarding axes nobody holds.
TOOL_EFFECT = 0.5
TOOL_DECAY_RATE = 0.08

# --- land ---------------------------------------------------------------
# The heart of the sustainability model, and the reason a small settlement
# can out-score a large one: the land yields a finite amount per season, and
# taking more than that degrades it, which cuts every future yield. Staying
# under the line lets it recover.
LAND_SUSTAINABLE_YIELD = 26.0
LAND_DEGRADE_PER_UNIT = 0.006
LAND_REGEN = 0.03
MIN_LAND_HEALTH = 0.15

# --- population dynamics ------------------------------------------------
# Growth accrues as progress rather than firing on a dice roll, so growth is
# a readable consequence of surplus and housing rather than luck.
GROWTH_RATE = 0.35
STARVATION_SEVERITY = 0.5
GROWTH_MIN_LAND_HEALTH = 0.3

# Seasons of stored food that counts as a full buffer (used by the
# resilience half of the sustainability score, and as the growth threshold).
BUFFER_SEASONS = 3.0


# --- research effects seam ---------------------------------------------
# Milestone 3's research tree aggregates its researched nodes into a dict
# of exactly these keys. Milestone 1 runs on the neutral version, so the
# simulation never needs to know whether a tree exists.
NEUTRAL_EFFECTS = {
    "food_yield_mult": 1.0,
    "materials_yield_mult": 1.0,
    "tool_yield_mult": 1.0,
    "knowledge_mult": 1.0,
    "regen_mult": 1.0,  # raises the land's sustainable yield and recovery rate
    "extraction_efficiency": 1.0,  # <1 = less land pressure per unit harvested
    "food_storage_bonus": 0.0,
    "housing_bonus": 0.0,
    "culture_bonus": 0.0,
    "equity_bonus": 0.0,  # consumed by sustainability.py, not by the sim
    "resilience_bonus": 0.0,  # ditto
    # Additive on top of SURPLUS_CONVERSION_RATE (Milestone 8) -- still the
    # one research seam, just one more key in the same dict.
    "surplus_conversion_bonus": 0.0,
    # Additive on top of CANAL_YIELD_BONUS (Milestone 9) -- same seam again.
    "canal_yield_bonus": 0.0,
    # Additive multiplier on Public Works' per-building coverage (Milestone
    # 10) -- same shape as housing_bonus/culture_bonus above (a capacity
    # multiplier), not a yield key, since Public Works has no production
    # formula for a yield key to modify in the first place.
    "public_works_bonus": 0.0,
    # Industrial (Milestone 11) -- a multiplicative key at a 1.0 base, same
    # as food_yield_mult/materials_yield_mult above: reduces how much
    # pollution a Factory Worker generates per season (smoke-abatement
    # research, not sanitation infrastructure -- see sanitation_bonus below
    # for the building-side lever).
    "pollution_output_mult": 1.0,
    # Additive multiplier on Sanitation Works' per-building absorption --
    # same capacity-multiplier shape as public_works_bonus above.
    "sanitation_bonus": 0.0,
    # Digital (Milestone 12) -- a multiplicative key at a 1.0 base, same
    # shape as pollution_output_mult above: reduces how much sprawl a
    # season of unmanaged population growth produces (data-driven zoning
    # research, not Transit Hubs' own building-side lever -- see
    # transit_bonus below for that).
    "sprawl_output_mult": 1.0,
    # Additive multiplier on Transit Hubs' per-building absorption -- same
    # capacity-multiplier shape as public_works_bonus/sanitation_bonus.
    "transit_bonus": 0.0,
    # Space Age (Milestone 13) -- additive on top of how far Architects'
    # staffing already stretches a Habitat Ring's layout quality (see
    # habitat_capacity() below), the same capacity-multiplier shape as
    # public_works_bonus/sanitation_bonus/transit_bonus above.
    "habitat_layout_bonus": 0.0,
}


def effects_or_neutral(effects):
    """Fills in any missing keys, so a partial effects dict is always safe."""
    if not effects:
        return dict(NEUTRAL_EFFECTS)
    merged = dict(NEUTRAL_EFFECTS)
    merged.update(effects)
    return merged


# Z25 (planning/TODO.md): score_history was append-only and uncapped, and
# every one of the seven possible era_snapshots embeds a full copy of it at
# time-of-snapshot -- so the save grew faster than linearly as more eras
# completed, the same shape log.Chronicle's own MAX_ENTRIES cap already
# guards against elsewhere in this game. Capped here, the same 60-entry
# size as Chronicle, for consistency rather than a separately-tuned number.
SCORE_HISTORY_MAX_ENTRIES = 60
# The two thresholds `_ever_recovered_from_collapse`-shaped logic has always
# used (see game.py's achievement check) -- named here now that the
# "lowest ever seen, then later recovered" tracking moved onto CityState
# itself so the cap above can't quietly break that achievement.
SCORE_COLLAPSE_THRESHOLD = 30
SCORE_RECOVERY_THRESHOLD = 70


class CityState:
    """One settlement, at one point in time, in one era."""

    def __init__(self, era=FIRST_ERA, scenario=DEFAULT_SCENARIO):
        # K12 -- resolved once, at construction, against SCENARIOS' own
        # keys rather than trusted verbatim, so a bogus id (a stale
        # constant from a future build, a hand-edited save value) can
        # never linger as `self.scenario` -- same "validate against the
        # schema's own source of truth" standard save.restore_city() holds
        # `era` to. `scenario_config()` already degrades gracefully for
        # the *values* used below; this is what keeps the *label* honest
        # about which scenario's numbers were actually applied.
        self.scenario = scenario if scenario in SCENARIOS else DEFAULT_SCENARIO
        config = scenario_config(self.scenario)
        # K18 -- opt-in stricter sustainability variant, off by default.
        # Unlike `scenario` (a one-time starting condition), this can be
        # flipped at any time during play, the same "toggle anytime"
        # shape Grid's own steeper-demand-growth/weather-variability
        # toggles use -- see sustainability.py for what it actually
        # tightens.
        self.hard_mode = False
        self.era = era
        self.season = 1
        self.population = config["population"]
        self.growth_progress = 0.0
        self.resources = {
            "food": config["food"],
            "materials": config["materials"],
            "tools": config["tools"],
            "knowledge": START_KNOWLEDGE,
            "surplus": START_SURPLUS,
        }
        self.allocation = dict(START_ALLOCATION)
        self.buildings = dict(START_BUILDINGS)
        self.land_health = config["land_health"]
        # Industrial+ (Milestone 11): a lagged 0..1 stock, same shape as
        # land_health -- see the "pollution and the growth-side cost of
        # industry" constants above. Always 0.0 before Industrial, both
        # because nothing produces it yet and because the season loop's
        # own era guard forces it there defensively.
        self.pollution = 0.0
        # Digital+ (Milestone 12): a second lagged 0..1 stock, same shape as
        # pollution -- see the "sprawl and the growth-side cost of
        # unmanaged density" constants above. Always 0.0 before Digital,
        # both because nothing produces it yet and because the season
        # loop's own era guard forces it there defensively.
        self.sprawl = 0.0
        # Last-season signals the sustainability score reads. Seeded so the
        # score is meaningful on season 1, before any season has run.
        self.fed_fraction = 1.0
        self.last_extraction = 0.0
        self.last_sustainable_yield = LAND_SUSTAINABLE_YIELD
        self.last_report = None
        # The sustainability score is computed by sustainability.py as a
        # pure function of this state, but its history is state — it gets
        # saved, snapshotted, and eventually graphed — so it lives here.
        # game.py calls record_score() with one value per completed season.
        # Z25: capped at SCORE_HISTORY_MAX_ENTRIES (see record_score below)
        # to stop this list -- and every era_snapshot's own copy of it --
        # from growing unbounded over a very long session.
        self.score_history = []
        # Two facts derived from score_history that must survive the cap
        # above intact, since both are read by real features (the K17
        # peak-score/efficiency-rank readout, and the "ever recovered from
        # collapse" achievement) that need the TRUE lifetime history, not
        # just whatever's left in the capped tail. Updated incrementally by
        # record_score() the instant each score is recorded -- before any
        # later cap-driven truncation could discard the evidence.
        self.peak_score = None
        self.lowest_score_seen = None
        self.ever_recovered_from_collapse = False
        # K11 (challenges.py) -- the opt-in civic-challenge state. Kept as a
        # plain literal here (challenges.py imports sim, so sim can't import
        # it back); save.py validates it on load via challenges.clean().
        self.challenge = {"active": None, "completed": {}, "failed": 0}
        # K19/K13/K25/K8 (trajectory.py) -- one [output_index, era_index,
        # population, livability] point per completed season, capped.
        self.trajectory = []
        # K10 -- completed seasons in a row with everyone fed and nobody
        # dying. Reset by any hunger or death, the same "clean streak" idea
        # as Grid's own.
        self.calm_streak = 0

    # --- allocation -----------------------------------------------------
    def assigned_workers(self):
        return sum(self.allocation.values())

    def idle_workers(self):
        return max(0, self.population - self.assigned_workers())

    def assign_worker(self, role):
        if self.idle_workers() <= 0:
            return False
        self.allocation[role] += 1
        return True

    def unassign_worker(self, role):
        if self.allocation[role] <= 0:
            return False
        self.allocation[role] -= 1
        return True

    def clamp_allocation(self):
        """Trims assignments back into the population, worst-case first.

        Needed because population can fall (starvation) without the player
        touching the allocation, and later because loading a save or
        revisiting an era can drop a smaller population onto an allocation
        sized for a bigger one.
        """
        overflow = self.assigned_workers() - self.population
        if overflow <= 0:
            return
        for role in reversed(ROLES):
            if overflow <= 0:
                break
            take = min(overflow, self.allocation[role])
            self.allocation[role] -= take
            overflow -= take

    def role_diversity(self):
        """0..1 — how evenly the workforce is spread across roles.

        1.0 means every role is staffed equally; 0.0 means everyone does the
        same job. Read by the resilience half of the sustainability score:
        a settlement that does exactly one thing has nothing to fall back on.

        Measured against `roles_for_era(self.era)`, not the flat global
        `ROLES` list — a settlement still in the Tribal era shouldn't have
        its "how evenly spread" denominator diluted by a Farmers slot it
        can't even assign to yet. This is what keeps every Tribal-era
        sustainability number byte-identical to before Milestone 8 added a
        second era's roles onto the same allocation dict.
        """
        assigned = self.assigned_workers()
        if assigned <= 0:
            return 0.0
        unlocked = roles_for_era(self.era)
        shares = [self.allocation[r] / assigned for r in unlocked]
        concentration = sum(s * s for s in shares)
        even = 1.0 / len(unlocked)
        if concentration <= even:
            return 1.0
        return (1.0 - concentration) / (1.0 - even)

    # --- capacities -----------------------------------------------------
    def housing_capacity(self, effects=None):
        effects = effects_or_neutral(effects)
        return self.buildings["shelter"] * SHELTER_CAPACITY + effects["housing_bonus"]

    def food_storage_capacity(self, effects=None):
        effects = effects_or_neutral(effects)
        return (
            BASE_FOOD_STORAGE
            + self.buildings["granary"] * GRANARY_STORAGE
            + effects["food_storage_bonus"]
        )

    def culture_capacity(self, effects=None):
        """How many people the settlement's social infrastructure serves."""
        effects = effects_or_neutral(effects)
        return self.buildings["hearth"] * HEARTH_SERVES * (1.0 + effects["culture_bonus"])

    def tool_factor(self):
        if self.population <= 0:
            return 1.0
        per_person = min(1.0, self.resources["tools"] / self.population)
        return 1.0 + TOOL_EFFECT * per_person

    def sustainable_yield(self, effects=None):
        effects = effects_or_neutral(effects)
        return LAND_SUSTAINABLE_YIELD * effects["regen_mult"]

    def public_works_coverage(self, effects=None):
        """How many people Public Works can meaningfully protect against a
        bad season (flood, disease, fire) -- read by the resilience half of
        the sustainability score (Milestone 10), not by anything in the
        season loop below. Same shape as culture_capacity()'s
        `buildings * PER_BUILDING * (1 + bonus)` pattern."""
        effects = effects_or_neutral(effects)
        return (
            self.buildings["public_works"]
            * PUBLIC_WORKS_COVERAGE_PER_BUILDING
            * (1.0 + effects["public_works_bonus"])
        )

    def habitat_capacity(self, effects=None):
        """How many people the settlement's off-world Habitat Rings can
        actually serve WELL -- not merely hold, but serve at the layout
        quality Architects have actually designed into them (Space Age+,
        see the "off-world habitat layout" comment block above). Read only
        by sustainability.py's provisions() from Space Age on; never by
        anything in the season loop below, and deliberately not a growth
        lever the way pollution/sprawl were -- see CLAUDE.md's Milestone 13
        build notes. Forced to 0.0 before Space Age rather than merely
        trusting it stays there by construction -- the same defensive
        era-gate discipline every prior era-specific mechanic in this file
        has been held to."""
        if era_index(self.era) < era_index("space"):
            return 0.0
        effects = effects_or_neutral(effects)
        if self.buildings["habitat_rings"] <= 0:
            return 0.0
        layout_quality = min(
            1.0,
            self.allocation["architects"]
            / (self.buildings["habitat_rings"] * ARCHITECTS_PER_RING),
        )
        return (
            self.buildings["habitat_rings"]
            * RING_CAPACITY_PER_BUILDING
            * layout_quality
            * (1.0 + effects["habitat_layout_bonus"])
        )

    # --- building -------------------------------------------------------
    def can_build(self, building):
        return self.resources["materials"] >= BUILDING_COST[building]

    def build(self, building):
        if not self.can_build(building):
            return False
        self.resources["materials"] -= BUILDING_COST[building]
        self.buildings[building] += 1
        return True

    # --- sustainability score history ------------------------------------
    def _record_score_derivatives(self, score):
        """Updates peak_score/lowest_score_seen/ever_recovered_from_collapse
        for one more observed score. Factored out of record_score() so
        recompute_score_derivatives_from_history() can replay an existing
        list through the exact same logic (used when restoring a save from
        before these fields existed — see save.py's restore_city())."""
        if self.peak_score is None or score > self.peak_score:
            self.peak_score = score
        if not self.ever_recovered_from_collapse:
            if (
                self.lowest_score_seen is not None
                and self.lowest_score_seen < SCORE_COLLAPSE_THRESHOLD
                and score >= SCORE_RECOVERY_THRESHOLD
            ):
                self.ever_recovered_from_collapse = True
            if self.lowest_score_seen is None or score < self.lowest_score_seen:
                self.lowest_score_seen = score

    def record_score(self, score):
        """Appends one season's sustainability score, trimming the front of
        score_history down to SCORE_HISTORY_MAX_ENTRIES once it grows past
        that cap (Z25). Safe to cap because the two facts that actually
        need the full lifetime history (peak_score, ever_recovered_from_
        collapse) are updated here, before the trim, not derived from the
        list afterward."""
        self._record_score_derivatives(score)
        self.score_history.append(score)
        if len(self.score_history) > SCORE_HISTORY_MAX_ENTRIES:
            del self.score_history[: len(self.score_history) - SCORE_HISTORY_MAX_ENTRIES]

    def recompute_score_derivatives_from_history(self):
        """Rebuilds peak_score/lowest_score_seen/ever_recovered_from_collapse
        from whatever's currently in score_history. Only meaningful for a
        save written before these fields existed — see save.py's
        restore_city(), the only caller."""
        self.peak_score = None
        self.lowest_score_seen = None
        self.ever_recovered_from_collapse = False
        for value in self.score_history:
            self._record_score_derivatives(value)

    # --- the season loop ------------------------------------------------
    def advance_season(self, effects=None):
        """Runs one season and returns a report dict describing what happened.

        Order matters and is deliberate: produce, then craft, then eat, then
        spoil, then live or die, then account for what the land took. The
        report is what the UI narrates and what the tests assert against.
        """
        effects = effects_or_neutral(effects)
        self.clamp_allocation()

        tool_factor = self.tool_factor()

        # 1. Harvest. Both gathering yields scale with tools and with how
        #    healthy the land still is — the loop that punishes over-use.
        #    Farmers (Agrarian+) are a second way to get food, not a
        #    separate economy: farmland raises their base yield the same
        #    way a knapping site raises a crafter's, but they still scale
        #    with the same tool_factor/land_health/food_yield_mult as
        #    foraging, and both feed the same extraction total below —
        #    settled agriculture is more productive here, not exempt from
        #    what the land can sustain.
        farm_bonus = 1.0 + self.buildings["farmland"] * FARMLAND_YIELD_BONUS
        # Canals (Classical+): a per-canal bonus on top of farmland, but only
        # in proportion to how fully Administrators staff it (see the
        # CANAL_YIELD_BONUS note above) -- a built-but-unstaffed canal adds
        # nothing, which is the point, not an edge case to special-case away.
        if self.buildings["canals"] > 0:
            canal_staffing = min(
                1.0,
                self.allocation["administrators"]
                / (self.buildings["canals"] * ADMINISTRATORS_PER_CANAL),
            )
        else:
            canal_staffing = 0.0
        canal_bonus = (
            self.buildings["canals"]
            * (CANAL_YIELD_BONUS + effects["canal_yield_bonus"])
            * canal_staffing
        )
        farm_bonus += canal_bonus
        food_gathered = (
            self.allocation["foragers"] * FOOD_PER_FORAGER
            + self.allocation["farmers"] * FOOD_PER_FARMER * farm_bonus
        ) * tool_factor * self.land_health * effects["food_yield_mult"]
        #    Factory Workers (Industrial+) are a second way to get
        #    materials, not a separate economy -- same tool_factor/
        #    land_health/materials_yield_mult chain as Gatherers, and the
        #    same shared extraction total below, the same discipline every
        #    prior era's new production role has been held to.
        materials_gathered = (
            (
                self.allocation["gatherers"] * MATERIALS_PER_GATHERER
                + self.allocation["factory_workers"] * MATERIALS_PER_FACTORY_WORKER
            )
            * tool_factor
            * self.land_health
            * effects["materials_yield_mult"]
        )
        self.resources["materials"] += materials_gathered

        # 2. Craft. Tools cost materials, so crafting competes with building.
        #    Guildmasters (Medieval+) are a second way to make tools, not a
        #    separate economy: the same Knapping Site bonus and the same
        #    tool_yield_mult apply to them, and their output feeds the same
        #    shared tool stock -- specialised training is more productive
        #    here, not exempt from what materials/effects allow.
        craft_bonus = 1.0 + self.buildings["toolworks"] * TOOLWORKS_CRAFT_BONUS
        wanted_tools = (
            (
                self.allocation["crafters"] * TOOLS_PER_CRAFTER
                + self.allocation["guildmasters"] * TOOLS_PER_GUILDMASTER
            )
            * craft_bonus
            * effects["tool_yield_mult"]
        )
        affordable_tools = self.resources["materials"] / MATERIALS_PER_TOOL
        tools_made = max(0.0, min(wanted_tools, affordable_tools))
        self.resources["materials"] -= tools_made * MATERIALS_PER_TOOL
        self.resources["tools"] += tools_made

        # 3. Knowledge — the research tree's currency (spent from Milestone 3).
        knowledge_made = (
            self.allocation["keepers"] * KNOWLEDGE_PER_KEEPER * effects["knowledge_mult"]
        )
        self.resources["knowledge"] += knowledge_made

        # 4. Tools wear out. Neglecting crafting entirely is a slow decline,
        #    not a sudden one.
        self.resources["tools"] *= 1.0 - TOOL_DECAY_RATE

        # 5. Eat.
        self.resources["food"] += food_gathered
        needed = self.population * FOOD_PER_PERSON
        consumed = min(self.resources["food"], needed)
        self.resources["food"] -= consumed
        fed_fraction = 1.0 if needed <= 0 else consumed / needed
        self.fed_fraction = fed_fraction

        # 6. Spoilage — food beyond what the settlement can store is lost.
        #    Agrarian+ (Milestone 8): some of what would spoil is preserved
        #    as trade-ready `surplus` instead, rather than pure waste — see
        #    the SURPLUS_CONVERSION_RATE note above. Either way, everything
        #    beyond storage_capacity leaves `food`; only where it goes
        #    (lost vs. banked) differs by era.
        storage_capacity = self.food_storage_capacity(effects)
        would_spoil = max(0.0, self.resources["food"] - storage_capacity)
        if era_index(self.era) >= era_index("agrarian"):
            conversion_rate = min(1.0, SURPLUS_CONVERSION_RATE + effects["surplus_conversion_bonus"])
            surplus_banked = would_spoil * conversion_rate
        else:
            surplus_banked = 0.0
        spoiled = would_spoil - surplus_banked
        self.resources["food"] -= would_spoil
        self.resources["surplus"] += surplus_banked

        # 7. Population. Starvation kills; surplus plus housing headroom grows.
        births = 0
        deaths = 0
        if fed_fraction < 1.0:
            unfed = (1.0 - fed_fraction) * self.population
            toll = max(1, int(round(unfed * STARVATION_SEVERITY)))
            survivors = max(MIN_POPULATION, self.population - toll)
            deaths = self.population - survivors
            self.population = survivors
            self.growth_progress = 0.0
        else:
            housing = self.housing_capacity(effects)
            has_room = self.population < housing
            surplus_ratio = 0.0 if needed <= 0 else self.resources["food"] / needed
            if has_room and surplus_ratio >= 1.0 and self.land_health > GROWTH_MIN_LAND_HEALTH:
                # Industrial+ (Milestone 11): the growth-side half of the
                # pollution mechanic -- reads self.pollution as it stood at
                # the END of the previous season (this season's own
                # pollution output is computed in step 8b below, same
                # lagged-stock ordering land_health already uses relative
                # to this same growth check). A soft, proportional slow-
                # down, not a hard block -- see the POLLUTION_GROWTH_PENALTY_
                # WEIGHT constant's own comment for why that shape was
                # chosen over copying land_health's hard gate.
                if era_index(self.era) >= era_index("industrial"):
                    pollution_penalty = self.pollution * POLLUTION_GROWTH_PENALTY_WEIGHT
                else:
                    pollution_penalty = 0.0
                effective_growth_rate = GROWTH_RATE * (1.0 - pollution_penalty)
                self.growth_progress += effective_growth_rate * min(1.0, surplus_ratio)
                while self.growth_progress >= 1.0 and self.population < housing:
                    self.population += 1
                    self.growth_progress -= 1.0
                    births += 1
        self.clamp_allocation()

        # 8. What the land gave up, and whether it can take it.
        extraction = (food_gathered + materials_gathered) * effects["extraction_efficiency"]
        # Digital+ (Milestone 12): sprawl amplifies how much land pressure
        # this same extraction total creates -- reads self.sprawl as it
        # stood at the END of the previous season (this season's own sprawl
        # output is computed in step 8c below, the same lagged-stock
        # ordering pollution's own step 8b already uses relative to this
        # same land-pressure calculation). See SPRAWL_EXTRACTION_PENALTY_
        # WEIGHT's own comment for why this is a different lever from
        # pollution's direct GROWTH_RATE multiplier.
        if era_index(self.era) >= era_index("digital"):
            extraction *= 1.0 + self.sprawl * SPRAWL_EXTRACTION_PENALTY_WEIGHT
        sustainable = self.sustainable_yield(effects)
        if extraction > sustainable:
            self.land_health -= (extraction - sustainable) * LAND_DEGRADE_PER_UNIT
        else:
            self.land_health += LAND_REGEN * effects["regen_mult"]
        self.land_health = max(MIN_LAND_HEALTH, min(1.0, self.land_health))
        self.last_extraction = extraction
        self.last_sustainable_yield = sustainable

        # 8b. Industrial pollution (Industrial+) -- updated last, the same
        # lagged-stock position land_health's own update sits in relative
        # to this season's growth check above. Factory Workers are the only
        # source; Sanitation Works (built, never staffed) and a small
        # constant natural decay are the only things that bring it back
        # down. Forced to exactly 0.0 before Industrial rather than merely
        # trusting it stayed there by construction -- the same defensive
        # era-gate discipline surplus_banked/canal_bonus/public_works_
        # coverage were all held to.
        if era_index(self.era) >= era_index("industrial"):
            pollution_produced = (
                self.allocation["factory_workers"]
                * POLLUTION_PER_FACTORY_WORKER
                * effects["pollution_output_mult"]
            )
            pollution_absorbed = (
                self.buildings["sanitation_works"]
                * SANITATION_ABSORPTION_PER_BUILDING
                * (1.0 + effects["sanitation_bonus"])
            )
            self.pollution = max(
                0.0,
                min(
                    1.0,
                    self.pollution
                    + pollution_produced
                    - pollution_absorbed
                    - POLLUTION_NATURAL_DECAY,
                ),
            )
        else:
            self.pollution = 0.0

        # 8c. Digital sprawl (Digital+) -- updated last, same lagged-stock
        # position as pollution's step 8b above, and for the same reason:
        # this season's land-pressure calculation in step 8 already read
        # whatever `self.sprawl` was at the END of the PREVIOUS season, not
        # anything computed here. Produced by unmanaged population growth
        # (`births`, from step 7 above) per the National Geographic source's
        # "urban areas grew 1.28x faster than their populations" finding;
        # Urban Planners work every season regardless of growth (their whole
        # job is managing it before it happens), Transit Hubs (built, never
        # staffed) absorb what has already accumulated, and a small natural
        # decay always pulls it down a little on its own. Forced to exactly
        # 0.0 before Digital rather than merely trusting it stayed there by
        # construction -- the same defensive era-gate discipline pollution/
        # surplus_banked/canal_bonus/public_works_coverage were all held to.
        if era_index(self.era) >= era_index("digital"):
            sprawl_produced = births * SPRAWL_PER_NEW_RESIDENT * effects["sprawl_output_mult"]
            sprawl_mitigated = self.allocation["planners"] * PLANNER_SPRAWL_MITIGATION
            sprawl_absorbed = (
                self.buildings["transit_hubs"]
                * TRANSIT_HUB_ABSORPTION_PER_BUILDING
                * (1.0 + effects["transit_bonus"])
            )
            self.sprawl = max(
                0.0,
                min(
                    1.0,
                    self.sprawl
                    + sprawl_produced
                    - sprawl_mitigated
                    - sprawl_absorbed
                    - SPRAWL_NATURAL_DECAY,
                ),
            )
        else:
            self.sprawl = 0.0

        self.season += 1

        if deaths > 0 or fed_fraction < 1.0:
            self.calm_streak = 0
        else:
            self.calm_streak += 1

        # Public Works coverage (Medieval+) -- purely for narration, the
        # same "convenience fields on the report" precedent Milestone 9 set
        # for canals/canal_staffing_ratio. Not read by any production
        # formula above; sustainability.py computes the same ratio
        # independently via public_works_coverage() for the score itself.
        if self.population > 0:
            public_works_coverage_ratio = min(
                1.0, self.public_works_coverage(effects) / self.population
            )
        else:
            public_works_coverage_ratio = 0.0

        # Habitat layout coverage (Space Age+) -- purely for narration, the
        # same "convenience fields on the report" precedent Milestones 9-10
        # set for canals/public_works. Not read by any production formula
        # above; sustainability.py computes the same ratio independently
        # via habitat_capacity() for the score itself.
        if self.population > 0:
            habitat_layout_ratio = min(1.0, self.habitat_capacity(effects) / self.population)
        else:
            habitat_layout_ratio = 0.0

        report = {
            "season": self.season - 1,
            "food_gathered": food_gathered,
            "materials_gathered": materials_gathered,
            "tools_made": tools_made,
            "knowledge_made": knowledge_made,
            "food_consumed": consumed,
            "fed_fraction": fed_fraction,
            "spoiled": spoiled,
            "surplus_banked": surplus_banked,
            "births": births,
            "deaths": deaths,
            "extraction": extraction,
            "sustainable_yield": sustainable,
            "tool_factor": tool_factor,
            "canals": self.buildings["canals"],
            "canal_staffing_ratio": canal_staffing,
            "public_works": self.buildings["public_works"],
            "public_works_coverage_ratio": public_works_coverage_ratio,
            "pollution": self.pollution,
            "sprawl": self.sprawl,
            "habitat_rings": self.buildings["habitat_rings"],
            "habitat_layout_ratio": habitat_layout_ratio,
        }
        self.last_report = report
        return report
