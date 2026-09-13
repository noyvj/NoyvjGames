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

Tribal (Phase 1), Agrarian (Milestone 8), Classical (Milestone 9) and
Medieval (Milestone 10) are modelled so far. Era-specific constants live in
per-era tables keyed by era id (see ERA_ROLES/ERA_BUILDINGS) so each
remaining era adds a table entry rather than a second copy of this file —
Agrarian's own Farmers role and Farmland building were the first proof that
pattern actually extends cleanly rather than requiring a rewrite;
Classical's Administrators/Canals extend it a second time, this time with
a building whose bonus depends on the role rather than merely being
multiplied by it (see CANAL_YIELD_BONUS); Medieval's Guildmasters/Public
Works extend it a third time, this time with a building that isn't staffed
at all — Public Works is read only by sustainability.py, not by the
production math below (see PUBLIC_WORKS_COVERAGE_PER_BUILDING).
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
IMPLEMENTED_ERAS = ["tribal", "agrarian", "classical", "medieval"]

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
}

ERA_BUILDINGS = {
    "tribal": ["shelter", "granary", "hearth", "toolworks"],
    "agrarian": ["farmland"],
    "classical": ["canals"],
    "medieval": ["public_works"],
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
}

ROLE_EMOJI = {
    "foragers": "🌾",
    "gatherers": "🪵",
    "crafters": "🪓",
    "keepers": "🔥",
    "farmers": "🌱",
    "administrators": "📜",
    "guildmasters": "⚒️",
}

BUILDING_LABEL = {
    "shelter": "Shelter",
    "granary": "Storage Pit",
    "hearth": "Fire Circle",
    "toolworks": "Knapping Site",
    "farmland": "Farmland",
    "canals": "Canals",
    "public_works": "Public Works",
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
}

BUILDING_EMOJI = {
    "shelter": "⛺",
    "granary": "🫙",
    "hearth": "🔥",
    "toolworks": "🪨",
    "farmland": "🌿",
    "canals": "🏛️",
    "public_works": "🚰",
}

BUILDING_COST = {  # in materials
    "shelter": 12.0,
    "granary": 18.0,
    "hearth": 15.0,
    "toolworks": 25.0,
    "farmland": 20.0,
    "canals": 35.0,
    "public_works": 40.0,
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
}
START_ALLOCATION = {
    "foragers": 3,
    "gatherers": 2,
    "crafters": 0,
    "keepers": 0,
    "farmers": 0,
    "administrators": 0,
    "guildmasters": 0,
}

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
}


def effects_or_neutral(effects):
    """Fills in any missing keys, so a partial effects dict is always safe."""
    if not effects:
        return dict(NEUTRAL_EFFECTS)
    merged = dict(NEUTRAL_EFFECTS)
    merged.update(effects)
    return merged


class CityState:
    """One settlement, at one point in time, in one era."""

    def __init__(self, era=FIRST_ERA):
        self.era = era
        self.season = 1
        self.population = START_POPULATION
        self.growth_progress = 0.0
        self.resources = {
            "food": START_FOOD,
            "materials": START_MATERIALS,
            "tools": START_TOOLS,
            "knowledge": START_KNOWLEDGE,
            "surplus": START_SURPLUS,
        }
        self.allocation = dict(START_ALLOCATION)
        self.buildings = dict(START_BUILDINGS)
        self.land_health = 1.0
        # Last-season signals the sustainability score reads. Seeded so the
        # score is meaningful on season 1, before any season has run.
        self.fed_fraction = 1.0
        self.last_extraction = 0.0
        self.last_sustainable_yield = LAND_SUSTAINABLE_YIELD
        self.last_report = None
        # The sustainability score is computed by sustainability.py as a
        # pure function of this state, but its history is state — it gets
        # saved, snapshotted, and eventually graphed — so it lives here.
        # game.py appends one entry per completed season.
        self.score_history = []

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

    # --- building -------------------------------------------------------
    def can_build(self, building):
        return self.resources["materials"] >= BUILDING_COST[building]

    def build(self, building):
        if not self.can_build(building):
            return False
        self.resources["materials"] -= BUILDING_COST[building]
        self.buildings[building] += 1
        return True

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
        materials_gathered = (
            self.allocation["gatherers"]
            * MATERIALS_PER_GATHERER
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
                self.growth_progress += GROWTH_RATE * min(1.0, surplus_ratio)
                while self.growth_progress >= 1.0 and self.population < housing:
                    self.population += 1
                    self.growth_progress -= 1.0
                    births += 1
        self.clamp_allocation()

        # 8. What the land gave up, and whether it can take it.
        extraction = (food_gathered + materials_gathered) * effects["extraction_efficiency"]
        sustainable = self.sustainable_yield(effects)
        if extraction > sustainable:
            self.land_health -= (extraction - sustainable) * LAND_DEGRADE_PER_UNIT
        else:
            self.land_health += LAND_REGEN * effects["regen_mult"]
        self.land_health = max(MIN_LAND_HEALTH, min(1.0, self.land_health))
        self.last_extraction = extraction
        self.last_sustainable_yield = sustainable

        self.season += 1

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
        }
        self.last_report = report
        return report
