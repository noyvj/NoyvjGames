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

Only the Tribal era is modelled so far. Era-specific constants live in
per-era tables keyed by era id so the Agrarian era (Phase 2/3) adds a
table entry rather than a second copy of this file.
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
IMPLEMENTED_ERAS = ["tribal"]

FIRST_ERA = ERA_ORDER[0]


def era_index(era):
    return ERA_ORDER.index(era)


# --- roles and buildings (Tribal era) ---------------------------------
# Population is allocated across roles; unassigned people are idle. Roles
# are era-scoped conceptually but share one allocation dict, so later eras
# extend the list rather than replacing the mechanic.
ROLES = ["foragers", "gatherers", "crafters", "keepers"]

# The label/blurb tables below are currently mirrored as static markup in
# index.html, which is why nothing reads them yet: with one era there are
# eight strings and static rows are simpler. They are kept as the intended
# source of truth because roles and buildings change per era — the moment a
# second era ships, the Work and Build panels have to be rendered from these
# the way the research panel already is, and the copies in index.html go.
ROLE_LABEL = {
    "foragers": "Foragers",
    "gatherers": "Gatherers",
    "crafters": "Crafters",
    "keepers": "Keepers",
}

ROLE_BLURB = {
    "foragers": "Bring in food from the land.",
    "gatherers": "Bring in wood, fibre and stone.",
    "crafters": "Turn materials into tools.",
    "keepers": "Hold and pass on what the settlement knows.",
}

BUILDINGS = ["shelter", "granary", "hearth", "toolworks"]

BUILDING_LABEL = {
    "shelter": "Shelter",
    "granary": "Storage Pit",
    "hearth": "Fire Circle",
    "toolworks": "Knapping Site",
}

BUILDING_BLURB = {
    "shelter": "Houses people. Nobody grows a settlement they can't sleep in.",
    "granary": "Holds food that would otherwise spoil.",
    "hearth": "Where the settlement gathers. Warmth, cooking, and a shared story.",
    "toolworks": "A dedicated place to work stone — crafters produce more.",
}

BUILDING_COST = {  # in materials
    "shelter": 12.0,
    "granary": 18.0,
    "hearth": 15.0,
    "toolworks": 25.0,
}

SHELTER_CAPACITY = 4  # people housed per shelter
GRANARY_STORAGE = 25.0  # extra food storage per storage pit
HEARTH_SERVES = 8.0  # people whose social/cultural needs one fire circle meets
TOOLWORKS_CRAFT_BONUS = 0.3  # additive multiplier on tool output per knapping site

# --- starting conditions ----------------------------------------------
START_POPULATION = 6
MIN_POPULATION = 1
START_FOOD = 20.0
START_MATERIALS = 20.0
START_TOOLS = 2.0
START_KNOWLEDGE = 0.0
START_BUILDINGS = {"shelter": 2, "granary": 0, "hearth": 1, "toolworks": 0}
START_ALLOCATION = {"foragers": 3, "gatherers": 2, "crafters": 0, "keepers": 0}

# --- production and consumption ---------------------------------------
FOOD_PER_FORAGER = 3.0
MATERIALS_PER_GATHERER = 2.0
TOOLS_PER_CRAFTER = 0.8
MATERIALS_PER_TOOL = 1.0
KNOWLEDGE_PER_KEEPER = 0.6

FOOD_PER_PERSON = 2.0
BASE_FOOD_STORAGE = 30.0

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
        """
        assigned = self.assigned_workers()
        if assigned <= 0:
            return 0.0
        shares = [self.allocation[r] / assigned for r in ROLES]
        concentration = sum(s * s for s in shares)
        even = 1.0 / len(ROLES)
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
        food_gathered = (
            self.allocation["foragers"]
            * FOOD_PER_FORAGER
            * tool_factor
            * self.land_health
            * effects["food_yield_mult"]
        )
        materials_gathered = (
            self.allocation["gatherers"]
            * MATERIALS_PER_GATHERER
            * tool_factor
            * self.land_health
            * effects["materials_yield_mult"]
        )
        self.resources["materials"] += materials_gathered

        # 2. Craft. Tools cost materials, so crafting competes with building.
        craft_bonus = 1.0 + self.buildings["toolworks"] * TOOLWORKS_CRAFT_BONUS
        wanted_tools = (
            self.allocation["crafters"] * TOOLS_PER_CRAFTER * craft_bonus * effects["tool_yield_mult"]
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
        storage_capacity = self.food_storage_capacity(effects)
        spoiled = max(0.0, self.resources["food"] - storage_capacity)
        self.resources["food"] -= spoiled

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

        report = {
            "season": self.season - 1,
            "food_gathered": food_gathered,
            "materials_gathered": materials_gathered,
            "tools_made": tools_made,
            "knowledge_made": knowledge_made,
            "food_consumed": consumed,
            "fed_fraction": fed_fraction,
            "spoiled": spoiled,
            "births": births,
            "deaths": deaths,
            "extraction": extraction,
            "sustainable_yield": sustainable,
            "tool_factor": tool_factor,
        }
        self.last_report = report
        return report
