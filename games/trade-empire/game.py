"""Trade Empire — Interstellar Trade Empire (working title).

Runs in-browser via Pyodide. Milestone 1: a founding-contract intro, one
ship, one manual route between two colonies. Milestone 2: a third colony
and a second ship — routes are no longer a fixed pair, each ship can be
manually sent to whichever colony the player chooses. Milestone 3: colony
need satisfaction scales output. Milestone 4: market prices fluctuate
with supply. Milestone 5: two more colonies and two more ships — no new
mechanic, just enough scale that manually running every ship/route by
hand gets genuinely busy, which is exactly the case Milestone 6's
automation exists to answer. Milestone 6: ships can be automated.
Milestone 7: a 2D map — colonies as nodes, routes as lines, drawn on a
canvas directly from Python via Pyodide's `js` module. Still no moving
ships on it (Milestone 11). Milestone 8: a small, flat research tree
(no prerequisites yet) spent from a separate, passively-accruing
research-points currency, gating an automation-slot expansion, a
fleet-wide speed boost, and a fleet-wide cargo boost. Milestone 9:
evolving needs v2 — sustained delivery develops a colony further, and
development expands what it needs (a second, cross-cycle need) rather
than ever "solving" it. Milestone 10: colony specialization — an
environmental, non-player-chosen strength/weakness pair per colony
(reflecting each one's flavor text) that activates automatically once
it develops. Milestone 11: ships render as moving dots on the map,
interpolated between origin and destination using each trip's own
fixed tick count so Fast Ships research can't retroactively distort a
ship already mid-flight. Milestone 12: fleet-level automation — with
every good needed by exactly one colony, a single automated ship's
route is already fixed, so "prioritization across routes" means
letting an idle automated ship abandon its home shuttle and reposition
empty to whichever producer feeds the fleet's most under-served
colony, when Fleet Priority mode is switched on. Milestone 13: galaxy
scaling — a research-gated second system, the Kepler Cluster, with its
own self-contained three-good need-triangle (so colony_needing() and
colony_producing() stay single-valued fleetwide) that links back to
the home system through each Kepler colony's secondary need, once
developed. Colony state for the cluster isn't created until the
research unlocks it, so it never contends with the home system's
colonies for Fleet Priority's attention beforehand. Milestone 14:
endgame — reaching a fully automated fleet, Fleet Priority, and the
Kepler Cluster all at once is treated as a soft win-state: the pattern
the player built is narrated as spreading to a growing, abstracted
background galaxy (hundreds of worlds by design, not hundreds of
individually simulated colonies -- a deliberate scope cut) that
trickles in passive revenue. The sandbox itself never ends or locks.
"""

import copy
import json
import math
import random

from js import document, setInterval, setTimeout
from pyodide.ffi import create_proxy

TICK_INTERVAL_MS = 1000
TRAVEL_TICKS = 5
CARGO_CAPACITY = 10

ORE = "ore"
GRAIN = "grain"
MACHINERY = "machinery"
WATER = "water"
ENERGY = "energy"

# Milestone 13 — the Kepler Cluster's own goods, distinct from the home
# system's five so colony_needing()/colony_producing() stay single-
# valued across the whole galaxy without any good ever being wanted or
# made by two colonies at once.
RARE_METALS = "rare_metals"
BIOMASS = "biomass"
ISOTOPES = "isotopes"

# J13 — the Rift Colonies, a third self-contained triangle gated behind
# "Outer Reaches" (itself gated behind Galaxy Expansion). Same reasoning
# as Kepler's own goods: a third, non-overlapping namespace keeps
# colony_needing()/colony_producing() single-valued fleet-wide with zero
# special-casing.
CRYSTAL = "crystal"
POLYMER = "polymer"
ANTIMATTER = "antimatter"

# J1 — the Umbral Deep, a fourth self-contained triangle gated behind a
# two-step research chain (Deep Survey, then Umbral Reach) that costs more
# than anything before it. Its goods are again a brand-new, non-overlapping
# namespace, and priced above every earlier tier.
NEUTRONIUM = "neutronium"
SUPERFLUID = "superfluid"
AEROGEL = "aerogel"

GOOD_LABEL = {
    ORE: "Ore", GRAIN: "Grain", MACHINERY: "Machinery", WATER: "Water", ENERGY: "Energy",
    RARE_METALS: "Rare Metals", BIOMASS: "Biomass", ISOTOPES: "Isotopes",
    CRYSTAL: "Crystal", POLYMER: "Polymer", ANTIMATTER: "Antimatter",
    NEUTRONIUM: "Neutronium", SUPERFLUID: "Superfluid", AEROGEL: "Aerogel",
}

# Flat per-unit base sell price, before Milestone 4's market multiplier.
SELL_PRICE = {
    ORE: 8, GRAIN: 6, MACHINERY: 10, WATER: 5, ENERGY: 9,
    RARE_METALS: 14, BIOMASS: 8, ISOTOPES: 18,
    CRYSTAL: 20, POLYMER: 12, ANTIMATTER: 26,
    NEUTRONIUM: 34, SUPERFLUID: 24, AEROGEL: 16,
}

# Milestone 2: a third colony turned the fixed A<->B pair into a real
# triangle (Aurum's ore feeds Ferrum, Ferrum's machinery feeds Verdant,
# Verdant's grain feeds Aurum). Milestone 5 adds a second pair (Cryo and
# Helion each need exactly what the other produces) purely to add scale
# — more colonies and routes for the existing ships to manage, not a
# new mechanic. Every ship can already reach every colony, so this
# alone measurably increases how busy manual play gets.
COLONIES = {
    "aurum": {"name": "Aurum Station", "produces": ORE, "needs": GRAIN},
    "verdant": {"name": "Verdant Reach", "produces": GRAIN, "needs": MACHINERY},
    "ferrum": {"name": "Ferrum Forge", "produces": MACHINERY, "needs": ORE},
    "cryo": {"name": "Cryo Vault", "produces": WATER, "needs": ENERGY},
    "helion": {"name": "Helion Array", "produces": ENERGY, "needs": WATER},
}

# Milestone 13 — the Kepler Cluster: a second system, reachable only
# once "galaxy_expansion" is researched. Its own closed three-good
# triangle, exactly like the home system's original one, so it's fully
# self-sufficient in isolation -- the cross-system link only appears
# once a Kepler colony develops (see SECONDARY_NEED below).
EXPANSION_COLONIES = {
    "kepler_a": {"name": "Kepler Alpha", "produces": RARE_METALS, "needs": BIOMASS},
    "kepler_b": {"name": "Kepler Beta", "produces": BIOMASS, "needs": ISOTOPES},
    "kepler_c": {"name": "Kepler Gamma", "produces": ISOTOPES, "needs": RARE_METALS},
}

# J13 — a third system, the Rift Colonies, gated behind "Outer Reaches"
# (which itself requires Galaxy Expansion first) -- same self-contained
# triangle shape as Kepler, just one tier further out. No new mechanic,
# same deliberate "more of what already exists" scope call Milestone 5
# made for the home system's own second pair.
RIFT_COLONIES = {
    "rift_a": {"name": "Rift Colony Alpha", "produces": CRYSTAL, "needs": ANTIMATTER},
    "rift_b": {"name": "Rift Colony Beta", "produces": ANTIMATTER, "needs": POLYMER},
    "rift_c": {"name": "Rift Colony Gamma", "produces": POLYMER, "needs": CRYSTAL},
}

# J1 — a fourth system, the Umbral Deep, gated behind "Umbral Reach"
# (which requires "Deep Survey", which requires Outer Reaches). Same
# self-contained triangle shape as the two clusters before it -- no new
# mechanic, just one more tier further out. Deliberately not sharing a
# name prefix (unlike "Kepler ..."/"Rift Colony ..."), so the map's default
# first-word label is already unique without an override.
DEEP_COLONIES = {
    "deep_a": {"name": "Nadir Foundry", "produces": NEUTRONIUM, "needs": SUPERFLUID},
    "deep_b": {"name": "Hush Cryostat", "produces": SUPERFLUID, "needs": AEROGEL},
    "deep_c": {"name": "Tenebra Loom", "produces": AEROGEL, "needs": NEUTRONIUM},
}

# All colony metadata, every system -- used for lookups that must stay
# correct regardless of what's unlocked (colony_needing(),
# colony_producing(), labels). Which of these are actually *reachable*
# right now is a separate question, answered by active_colony_ids().
ALL_COLONIES = {**COLONIES, **EXPANSION_COLONIES, **RIFT_COLONIES, **DEEP_COLONIES}

# Milestone 3 — minor flavor text per colony, shown in the colony panel.
COLONY_FLAVOR = {
    "aurum": "A wind-scoured mining outpost — good ore, poor soil. Every grain shipment matters.",
    "verdant": "Lush terraces feed the sector, but its factories run on imported machinery.",
    "ferrum": "The forges never stop, but they run on ore that has to come from somewhere else.",
    "cryo": "A frozen moon's ice reserves, tapped for water — but the pumps need power to run at all.",
    "helion": "A solar array with power to spare, and nothing to cool it but water shipped in from Cryo.",
    "kepler_a": "A newly-charted asteroid belt rich in rare metals — reaching it took the galaxy expansion, and running it still does.",
    "kepler_b": "Vast hydroponic vaults growing biomass for the whole cluster — an engineered ecology this far out, not a natural one.",
    "kepler_c": "Fusion research yards refining isotopes — infrastructure that only exists this far from the core because the expansion made it worth building.",
    "rift_a": "A crystal-lattice quarry at the edge of charted space — Outer Reaches is the only reason a ship can reach it at all.",
    "rift_b": "A containment yard breeding antimatter in vanishingly small, carefully metered batches.",
    "rift_c": "A polymer refinery running on feedstock that has to be shipped in from somewhere else in the Rift.",
    "deep_a": "A foundry working scraps of collapsed star into neutronium, under a sky with nothing in it. Every hour of supply it gets is an hour of light it doesn't have.",
    "deep_b": "A cryostat holding helium at temperatures where it stops behaving like a liquid at all. Aerogel lining is the difference between working and not.",
    "deep_c": "Looms spinning aerogel inside neutronium-lined pressure vessels. The output is almost weightless; getting the vessels here was not.",
}

# Milestone 3 — colony need system v1: each colony's need_satisfaction
# (0..1) decays steadily and is topped up when a ship delivers the
# colony's needed good. Output scales with it — a well-supplied colony
# produces meaningfully more per load than a neglected one, so "keep
# the loop fed" becomes a real incentive, not just flavor text.
STARTING_NEED_SATISFACTION = 0.5
NEED_DECAY_PER_TICK = 0.01
NEED_SATISFACTION_PER_UNIT_DELIVERED = 0.05
# At satisfaction 0.0 a colony produces at half capacity; at 1.0, one
# and a half times — the starting 0.5 satisfaction matches today's flat
# CARGO_CAPACITY exactly, so Milestone 1/2 balance is the neutral point.
MIN_OUTPUT_MULTIPLIER = 0.5
MAX_OUTPUT_MULTIPLIER = 1.5

# Milestone 9 — evolving needs v2: sustained delivery of a colony's
# primary need develops it further, and development expands what it
# needs rather than ever "finishing" it — a second, cross-cycle need on
# top of the first, per the plan's "no final solved state per colony"
# framing. A colony's own secondary need deliberately reaches into the
# *other* need-cycle (the original triangle vs. the Cryo/Helion pair),
# so growth creates new dependencies linking the two clusters together
# rather than just deepening the one a colony already belongs to.
DEVELOPMENT_THRESHOLD = 100.0
SECONDARY_NEED = {
    "aurum": ENERGY,
    "verdant": WATER,
    "ferrum": ENERGY,
    "cryo": ORE,
    "helion": GRAIN,
    # Milestone 13 — a developed Kepler colony's secondary need reaches
    # all the way back into the home system, the same "links what was
    # previously separate" move Milestone 9 made within one system,
    # applied across the newly-opened distance between two.
    "kepler_a": ENERGY,
    "kepler_b": ORE,
    "kepler_c": WATER,
    # J13 — the Rift Colonies' own secondary need reaches back one tier,
    # into the Kepler Cluster, the same "links what was previously
    # separate" move applied one system further out.
    "rift_a": RARE_METALS,
    "rift_b": BIOMASS,
    "rift_c": ISOTOPES,
    # J1 — the Umbral Deep's secondary need reaches back one tier again,
    # into the Rift Colonies' goods.
    "deep_a": ANTIMATTER,
    "deep_b": CRYSTAL,
    "deep_c": POLYMER,
}

# Milestone 10 — colony specialization: distinct strengths/weaknesses
# per colony, reflecting the environment/history each one's flavor text
# already establishes (Aurum's harsh mining outpost earns the strongest
# output bonus and pays for it with the steepest decay; Verdant's easy,
# fertile terraces earn the mildest of each). Environmental, not a
# player choice — it activates automatically once a colony develops
# (Milestone 9's development_level >= 2), rather than being a separate
# unlock system of its own.
SPECIALIZATION = {
    "aurum": {
        "name": "Mining Powerhouse", "output_bonus": 0.25, "decay_multiplier": 1.6,
        "description": "+25% ore output; needs decay 60% faster (harsh, remote environment)",
    },
    "verdant": {
        "name": "Fertile Terraces", "output_bonus": 0.15, "decay_multiplier": 1.2,
        "description": "+15% grain output; needs decay 20% faster (easy growing conditions)",
    },
    "ferrum": {
        "name": "Forge World", "output_bonus": 0.20, "decay_multiplier": 1.4,
        "description": "+20% machinery output; needs decay 40% faster (single-purpose economy)",
    },
    "cryo": {
        "name": "Ice Miner", "output_bonus": 0.20, "decay_multiplier": 1.5,
        "description": "+20% water output; needs decay 50% faster (isolated, power-starved)",
    },
    "helion": {
        "name": "Solar Titan", "output_bonus": 0.15, "decay_multiplier": 1.3,
        "description": "+15% energy output; needs decay 30% faster (nothing grows there)",
    },
    "kepler_a": {
        "name": "Deep-Core Extractor", "output_bonus": 0.20, "decay_multiplier": 1.5,
        "description": "+20% rare metals output; needs decay 50% faster (unforgiving frontier belt)",
    },
    "kepler_b": {
        "name": "Hydroponic Vaults", "output_bonus": 0.15, "decay_multiplier": 1.2,
        "description": "+15% biomass output; needs decay 20% faster (engineered, well-tended ecology)",
    },
    "kepler_c": {
        "name": "Fusion Yards", "output_bonus": 0.20, "decay_multiplier": 1.4,
        "description": "+20% isotopes output; needs decay 40% faster (high-maintenance research infrastructure)",
    },
    "rift_a": {
        "name": "Lattice Quarry", "output_bonus": 0.25, "decay_multiplier": 1.6,
        "description": "+25% crystal output; needs decay 60% faster (edge-of-map, barely supplied)",
    },
    "rift_b": {
        "name": "Containment Yard", "output_bonus": 0.20, "decay_multiplier": 1.5,
        "description": "+20% antimatter output; needs decay 50% faster (a small batch is already a lot to keep stable)",
    },
    "rift_c": {
        "name": "Feedstock Refinery", "output_bonus": 0.20, "decay_multiplier": 1.4,
        "description": "+20% polymer output; needs decay 40% faster (every input is imported)",
    },
    # J1 — the highest-reward, highest-maintenance profiles in the game:
    # the furthest colonies pay the most and are the hardest to keep fed.
    "deep_a": {
        "name": "Collapsed-Star Smelter", "output_bonus": 0.30, "decay_multiplier": 1.7,
        "description": "+30% neutronium output; needs decay 70% faster (no sunlight, no margin for error)",
    },
    "deep_b": {
        "name": "Absolute-Zero Works", "output_bonus": 0.25, "decay_multiplier": 1.6,
        "description": "+25% superfluid output; needs decay 60% faster (the cold only holds while it is being tended)",
    },
    "deep_c": {
        "name": "Weightless Looms", "output_bonus": 0.25, "decay_multiplier": 1.5,
        "description": "+25% aerogel output; needs decay 50% faster (delicate output, heavy-duty inputs)",
    },
}


# J19 -- colony loyalty. A colony left chronically under-served (need
# satisfaction below NEGLECT_THRESHOLD for NEGLECT_DEMAND_TICKS in a row)
# makes a one-time concession demand. Granting it costs CONCESSION_COST
# credits and restores CONCESSION_SATISFACTION_BOOST of need satisfaction;
# ignoring it costs nothing, the demand simply lapses after
# DEMAND_WINDOW_TICKS and can only come back after DEMAND_COOLDOWN_TICKS.
# It's an offer that rewards attention, never a punishment.
NEGLECT_THRESHOLD = 0.25
NEGLECT_DEMAND_TICKS = 40
DEMAND_WINDOW_TICKS = 30
DEMAND_COOLDOWN_TICKS = 60
CONCESSION_COST = 80
CONCESSION_SATISFACTION_BOOST = 0.3


# J-25 -- colony temperaments. Each colony's mood follows its trade history
# (see ColonyState.temperament()) and changes how it treats the player:
# Grateful colonies pay a small premium on sales delivered there, Demanding
# ones answer a granted concession more strongly, and Opportunistic ones (the
# starting mood) take an Invest at a discount while their need is low. Nothing
# is ever marked down, so the base economy only moves up.
TEMPERAMENT_COUNT_MAX = 1_000_000
TEMPERAMENT_MARK = {"circle": "\u25cf", "triangle": "\u25b2", "square": "\u25a0"}
GRATEFUL_DELIVERED = 50.0
DEMANDING_LAPSED_DEMANDS = 2
DEFAULT_TEMPERAMENT = "opportunistic"
OPPORTUNIST_INVEST_DISCOUNT = 0.75
OPPORTUNIST_NEED_BELOW = 0.5
TEMPERAMENTS = {
    "grateful": {
        "label": "Grateful", "glyph": "circle", "premium": 0.04, "concession_boost": CONCESSION_SATISFACTION_BOOST,
        "why": "well supplied, so it pays +4% on every sale delivered there",
    },
    "demanding": {
        "label": "Demanding", "glyph": "triangle", "premium": 0.0, "concession_boost": 0.45,
        "why": "two demands went unanswered, but a granted concession now restores 45% satisfaction",
    },
    "opportunistic": {
        "label": "Opportunistic", "glyph": "square", "premium": 0.0, "concession_boost": CONCESSION_SATISFACTION_BOOST,
        "why": "new or undecided, and it takes an Invest at a 25% discount whenever its need is under 50%",
    },
}


class ColonyState:
    def __init__(self, colony_id):
        self.id = colony_id
        self.neglect_ticks = 0
        self.demand_ticks_left = 0
        self.demand_cooldown = 0
        self.need_satisfaction = STARTING_NEED_SATISFACTION
        self.development_level = 1
        self.cumulative_delivered = 0.0
        self.secondary_need_satisfaction = STARTING_NEED_SATISFACTION
        # J-25 -- trade history that decides the colony's temperament.
        self.demands_made = 0
        self.concessions_granted = 0

    def secondary_need(self):
        return SECONDARY_NEED[self.id]

    def is_developed(self):
        return self.development_level >= 2

    def output_multiplier(self):
        if not self.is_developed():
            satisfaction = self.need_satisfaction
        else:
            satisfaction = (self.need_satisfaction + self.secondary_need_satisfaction) / 2
        base = MIN_OUTPUT_MULTIPLIER + satisfaction * (MAX_OUTPUT_MULTIPLIER - MIN_OUTPUT_MULTIPLIER)
        if self.is_developed():
            base *= 1 + SPECIALIZATION[self.id]["output_bonus"]
        return base * founding_output_multiplier(self.id)

    def cargo_capacity(self):
        return round(CARGO_CAPACITY * self.output_multiplier())

    def decay(self):
        decay_rate = NEED_DECAY_PER_TICK * charter_decay_multiplier(self.id)
        if self.is_developed():
            decay_rate *= SPECIALIZATION[self.id]["decay_multiplier"]
        self.need_satisfaction = max(0.0, self.need_satisfaction - decay_rate)
        if self.is_developed():
            self.secondary_need_satisfaction = max(0.0, self.secondary_need_satisfaction - decay_rate)

    def has_demand(self):
        return self.demand_ticks_left > 0

    def update_loyalty(self):
        """One tick of loyalty bookkeeping (called from tick())."""
        if self.demand_cooldown > 0:
            self.demand_cooldown -= 1
        if self.has_demand():
            self.demand_ticks_left -= 1
            if self.demand_ticks_left == 0:
                self.demand_cooldown = DEMAND_COOLDOWN_TICKS
                self.neglect_ticks = 0
            return
        if self.need_satisfaction < NEGLECT_THRESHOLD:
            self.neglect_ticks += 1
        else:
            self.neglect_ticks = 0
        if self.neglect_ticks >= NEGLECT_DEMAND_TICKS and self.demand_cooldown == 0:
            self.demand_ticks_left = DEMAND_WINDOW_TICKS
            self.demands_made = min(TEMPERAMENT_COUNT_MAX, self.demands_made + 1)

    def lapsed_demands(self):
        """J-25 -- demands this colony made that were never granted (an open
        demand is not lapsed yet)."""
        return max(0, self.demands_made - self.concessions_granted - (1 if self.has_demand() else 0))

    def temperament(self):
        """J-25 -- derived purely from this colony's history, so it can never
        be tampered into a state the history does not support. Demanding:
        two or more demands went unanswered. Grateful: well supplied (50+
        units delivered or invested) or helped by a concession. Anything
        else, including every new colony, is Opportunistic."""
        if self.lapsed_demands() >= DEMANDING_LAPSED_DEMANDS:
            return "demanding"
        if self.cumulative_delivered >= GRATEFUL_DELIVERED or self.concessions_granted >= 1:
            return "grateful"
        return DEFAULT_TEMPERAMENT

    def concession_boost(self):
        return TEMPERAMENTS[self.temperament()]["concession_boost"]

    def grant_concession(self):
        boost = self.concession_boost()  # judged before this concession changes the history
        self.concessions_granted = min(TEMPERAMENT_COUNT_MAX, self.concessions_granted + 1)
        self.need_satisfaction = min(1.0, self.need_satisfaction + boost)
        self.demand_ticks_left = 0
        self.demand_cooldown = DEMAND_COOLDOWN_TICKS
        self.neglect_ticks = 0

    def add_development(self, units):
        self.cumulative_delivered += units
        if self.cumulative_delivered >= development_threshold() and self.development_level < 2:
            self.development_level = 2

    def deliver(self, qty):
        gain = qty * NEED_SATISFACTION_PER_UNIT_DELIVERED
        self.need_satisfaction = min(1.0, self.need_satisfaction + gain)
        self.add_development(qty)

    def deliver_secondary(self, qty):
        gain = qty * NEED_SATISFACTION_PER_UNIT_DELIVERED
        self.secondary_need_satisfaction = min(1.0, self.secondary_need_satisfaction + gain)


# Milestone 7 — 2D map v1: colonies as nodes, routes as lines. Drawn
# directly from Python via Pyodide's `js` module (canvas 2D context
# methods are just JS method calls, so no separate JS glue file is
# needed here despite the canvas requirement). Static layout and static
# routes for now — no moving ships until Milestone 11.
CANVAS_WIDTH = 620
# J1 — the Umbral Deep gets its own band along the bottom, so the canvas
# grew taller rather than wider (it is displayed at a fixed max width, so
# widening it again would have shrunk every existing node further).
CANVAS_HEIGHT = 450
NODE_RADIUS = 22
NODE_POSITIONS = {
    "aurum": (150, 36),
    "verdant": (262, 118),
    "ferrum": (218, 252),
    "cryo": (82, 252),
    "helion": (38, 118),
    # Milestone 13 — the Kepler Cluster sits in its own space on the
    # right half of the (now wider) canvas, visually distinct from the
    # home system's pentagon rather than crowded into it. Positions kept
    # exactly as Milestone 13 placed them (not re-centered for J13's
    # further widening below) so an in-flight ship's saved interpolation
    # coordinates stay valid.
    "kepler_a": (390, 50),
    "kepler_b": (430, 190),
    "kepler_c": (350, 230),
    # J13 — the Rift Colonies get their own space again, further right
    # still, on the canvas' newly-widened third of the width.
    "rift_a": (560, 50),
    "rift_b": (595, 190),
    "rift_c": (520, 250),
    # J1 — the Umbral Deep: its own band below every other system.
    "deep_a": (250, 350),
    "deep_b": (370, 415),
    "deep_c": (490, 350),
}
NODE_COLOR = "#3a5a9c"
EDGE_COLOR = "#3a3f5c"
LABEL_COLOR = "#e8e9f0"

# Bug fix, found during the code-quality audit: render_map() used to
# label every node with name.split()[0]. That's unique for the home
# system (Aurum/Verdant/Ferrum/Cryo/Helion all have distinct first
# words), but all three Kepler Cluster colonies share the literal
# prefix "Kepler" -- naively reusing the same rule rendered all three
# map nodes with the identical "Kepler" label, making them visually
# indistinguishable despite sitting at three different positions.
# Kepler colonies get an explicit short label instead; everything else
# keeps the original first-word behavior unchanged.
MAP_LABEL_OVERRIDE = {
    "kepler_a": "Kep. Alpha",
    "kepler_b": "Kep. Beta",
    "kepler_c": "Kep. Gamma",
    # J13 — same collision as Kepler's: all three Rift colonies share the
    # literal first word "Rift".
    "rift_a": "Rift Alpha",
    "rift_b": "Rift Beta",
    "rift_c": "Rift Gamma",
}


def colony_map_label(colony_id):
    return MAP_LABEL_OVERRIDE.get(colony_id, ALL_COLONIES[colony_id]["name"].split()[0])


def route_edges():
    """One directed edge per *reachable* colony, to whichever colony
    needs its produced good -- the same relationship colony_needing()
    already encodes, just read as a full list for drawing. Scoped to
    active_colony_ids() so a locked Kepler Cluster never contributes
    edges pointing at nodes the map isn't drawing yet."""
    edges = []
    for colony_id in active_colony_ids():
        destination = colony_needing(ALL_COLONIES[colony_id]["produces"])
        if destination:
            edges.append((colony_id, destination))
    return edges


# Milestone 11 — ships on the map: automated routes (and manual ones,
# so the map stays useful during manual play too) render as moving
# dots along the map's lines, interpolated between origin and
# destination using the trip's own fixed tick count at departure time
# (transit_total_ticks) rather than the current travel_ticks(), so a
# mid-flight ship's position stays consistent even if Fast Ships
# research changes the travel time for future departures.
SHIP_DOT_RADIUS = 5
AUTOMATED_SHIP_COLOR = "#e0c34c"
MANUAL_SHIP_COLOR = "#e8e9f0"
# J16 — a color distinct from every node/edge/ship hue already in use.
FLEET_PRIORITY_TARGET_COLOR = "#ff6ad0"


def ship_map_position(ship):
    if ship.docked:
        return NODE_POSITIONS[ship.location]
    origin_x, origin_y = NODE_POSITIONS[ship.origin]
    dest_x, dest_y = NODE_POSITIONS[ship.destination]
    if ship.transit_total_ticks <= 0:
        progress = 1.0
    else:
        elapsed = ship.transit_total_ticks - ship.transit_ticks_remaining
        progress = max(0.0, min(1.0, elapsed / ship.transit_total_ticks))
    return (
        origin_x + (dest_x - origin_x) * progress,
        origin_y + (dest_y - origin_y) * progress,
    )


# J10 -- a brief docking/undocking pulse on the map. Undocking is a ring
# that grows outward from the colony a ship just left; docking is a ring
# that closes in on the colony a ship just reached. Direction and line
# weight carry the meaning (not colour), each pulse lasts DOCK_PULSE_TICKS
# ticks, and none are drawn while the player has reduced motion on. Purely
# a view effect: nothing is saved.
DOCK_PULSE_TICKS = 3
dock_pulses = []  # [colony_id, "dock" | "undock", age_in_ticks]


def add_dock_pulse(colony_id, kind):
    if colony_id in NODE_POSITIONS:
        dock_pulses.append([colony_id, kind, 0])


def age_dock_pulses():
    for pulse in dock_pulses:
        pulse[2] += 1
    dock_pulses[:] = [p for p in dock_pulses if p[2] < DOCK_PULSE_TICKS]


def _reduced_motion_on():
    try:
        return bool(document.documentElement.classList.contains("reduce-motion"))
    except Exception:
        return False


def _effects_on():
    """J-31 -- the Settings "Effects" toggle (settings.js adds `.effects-off`
    to <html>). Effects are the optional flourishes: sale sparks, dock pulses
    and the ribbon unlock flourish. Reduced motion also turns them off."""
    try:
        classes = document.documentElement.classList
        return not (classes.contains("effects-off") or classes.contains("reduce-motion"))
    except Exception:
        return True


def dock_pulse_radius(kind, age):
    step = age / DOCK_PULSE_TICKS
    if kind == "undock":
        return NODE_RADIUS + 4 + step * 18
    return NODE_RADIUS + 4 + (1 - step) * 18


def draw_dock_pulses(ctx):
    if _reduced_motion_on() or not _effects_on():
        return
    for colony_id, kind, age in dock_pulses:
        if colony_id not in active_colony_ids():
            continue
        x, y = NODE_POSITIONS[colony_id]
        ctx.strokeStyle = LABEL_COLOR
        ctx.lineWidth = 3 if kind == "dock" else 1.5
        ctx.beginPath()
        ctx.arc(x, y, dock_pulse_radius(kind, age), 0, 2 * math.pi)
        ctx.stroke()


TEMPERAMENT_GLYPH_COLOR = "#f4e9b8"
TEMPERAMENT_GLYPH_RADIUS = 6


def temperament_glyph_points(glyph, cx, cy, r=TEMPERAMENT_GLYPH_RADIUS):
    """J-26 -- polygon points for a colony mood glyph: a circle (drawn as a
    12-sided shape, so the map's own arcs stay one per node), a triangle or a
    square. The shape, not its colour, carries the meaning."""
    if glyph == "triangle":
        return [(cx, cy - r), (cx + r, cy + r), (cx - r, cy + r)]
    if glyph == "square":
        return [(cx - r, cy - r), (cx + r, cy - r), (cx + r, cy + r), (cx - r, cy + r)]
    return [(cx + r * math.cos(i * math.pi / 6), cy + r * math.sin(i * math.pi / 6)) for i in range(12)]


def draw_temperament_glyph(ctx, colony_id, cx, cy):
    glyph = TEMPERAMENTS[colony_states[colony_id].temperament()]["glyph"]
    points = temperament_glyph_points(glyph, cx, cy)
    ctx.fillStyle = TEMPERAMENT_GLYPH_COLOR
    ctx.beginPath()
    ctx.moveTo(*points[0])
    for px, py in points[1:]:
        ctx.lineTo(px, py)
    ctx.closePath()
    ctx.fill()


def render_map():
    canvas = document.getElementById("map-canvas")
    ctx = canvas.getContext("2d")
    ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)
    if not blackout_has("chart"):  # J-29: Blackout, the star chart is dark
        canvas.title = "Blackout: the map is dark. Buy the star chart or research Galaxy Expansion to light it."
        ctx.fillStyle = LABEL_COLOR
        ctx.font = "14px sans-serif"
        ctx.textAlign = "center"
        ctx.textBaseline = "middle"
        ctx.fillText("Blackout: the star chart is dark", CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2 - 10)
        ctx.fillText("(colonies and needs are still listed below)", CANVAS_WIDTH / 2, CANVAS_HEIGHT / 2 + 12)
        return
    # J6 — hover text explaining what the pink target ring points at.
    if fleet_priority_enabled and colony_states:
        canvas.title = (
            f"Pink ring: Fleet Priority's current target, {ALL_COLONIES[most_urgent_colony()]['name']} "
            "(the colony with the lowest need satisfaction). Idle automated ships reposition "
            "toward whichever producer feeds it."
        )
    else:
        canvas.title = "Trade routes map. Turn on Fleet Priority to see its target ring."

    ctx.strokeStyle = EDGE_COLOR
    ctx.lineWidth = 2
    for from_id, to_id in route_edges():
        x1, y1 = NODE_POSITIONS[from_id]
        x2, y2 = NODE_POSITIONS[to_id]
        ctx.beginPath()
        ctx.moveTo(x1, y1)
        ctx.lineTo(x2, y2)
        ctx.stroke()

    # Milestone 13: only draw nodes the player can actually reach right
    # now -- a locked Kepler Cluster stays entirely off the map.
    for colony_id in active_colony_ids():
        x, y = NODE_POSITIONS[colony_id]
        ctx.fillStyle = NODE_COLOR
        ctx.beginPath()
        ctx.arc(x, y, NODE_RADIUS, 0, 2 * math.pi)
        ctx.fill()

        ctx.fillStyle = LABEL_COLOR
        ctx.font = "11px sans-serif"
        ctx.textAlign = "center"
        ctx.textBaseline = "middle"
        ctx.fillText(colony_map_label(colony_id), x, y)
        if colony_id in colony_states:
            draw_temperament_glyph(ctx, colony_id, x + NODE_RADIUS * 0.8, y - NODE_RADIUS * 0.8)

    # J16 — Fleet Priority's current target, made visible rather than
    # left implicit: a ring around whichever colony most_urgent_colony()
    # would currently send an idle automated ship toward.
    if fleet_priority_enabled and colony_states:
        target = most_urgent_colony()
        if target in NODE_POSITIONS:
            tx, ty = NODE_POSITIONS[target]
            ctx.strokeStyle = FLEET_PRIORITY_TARGET_COLOR
            ctx.lineWidth = 3
            ctx.beginPath()
            ctx.arc(tx, ty, NODE_RADIUS + 6, 0, 2 * math.pi)
            ctx.stroke()

    draw_dock_pulses(ctx)

    for ship in ships.values():
        if not ship.purchased:
            continue
        x, y = ship_map_position(ship)
        ctx.fillStyle = AUTOMATED_SHIP_COLOR if ship.automated else MANUAL_SHIP_COLOR
        if ship.automated:
            # J18 — colorblind-safe differentiation: a diamond, not just
            # a different hue, so automated-vs-manual doesn't rely on
            # color perception at all.
            ctx.beginPath()
            ctx.moveTo(x, y - SHIP_DOT_RADIUS)
            ctx.lineTo(x + SHIP_DOT_RADIUS, y)
            ctx.lineTo(x, y + SHIP_DOT_RADIUS)
            ctx.lineTo(x - SHIP_DOT_RADIUS, y)
            ctx.closePath()
            ctx.fill()
        else:
            ctx.beginPath()
            ctx.arc(x, y, SHIP_DOT_RADIUS, 0, 2 * math.pi)
            ctx.fill()


colony_states = {colony_id: ColonyState(colony_id) for colony_id in COLONIES}

# Milestone 4 — market economics: each good has a price multiplier that
# drops when it's sold and recovers gradually over time. Overproducing
# a single good (running the same route on repeat) craters its price;
# diversifying across the triangle keeps prices near baseline. Floored
# so a good never becomes worthless, and capped at baseline — no
# scarcity premium in v1.
MARKET_PRICE_DECAY_PER_UNIT_SOLD = 0.01
MARKET_PRICE_RECOVERY_PER_TICK = 0.01
MIN_PRICE_MULTIPLIER = 0.3
MAX_PRICE_MULTIPLIER = 1.0

market_multiplier = {
    ORE: 1.0, GRAIN: 1.0, MACHINERY: 1.0, WATER: 1.0, ENERGY: 1.0,
    RARE_METALS: 1.0, BIOMASS: 1.0, ISOTOPES: 1.0,
    CRYSTAL: 1.0, POLYMER: 1.0, ANTIMATTER: 1.0,
    NEUTRONIUM: 1.0, SUPERFLUID: 1.0, AEROGEL: 1.0,
}

# J11 — per-route profitability. Every good in the galaxy is produced by
# exactly one colony and needed by exactly one other (colony_producing()/
# colony_needing() are both single-valued), so a good's cumulative sale
# profit *is* that route's cumulative profit -- no separate route-keyed
# structure needed on top of the good-keyed one.
good_profit_recent = {}  # J2 — good -> last few sale profits, for the trend arrow
good_profit_total = {good: 0 for good in market_multiplier}
# V-E-8 (J11): completed sales per good, so each route line can show average profit per trip
good_trip_count = {good: 0 for good in market_multiplier}

# J12/J14 — a short rolling trend history (market price per good, need
# satisfaction per colony), just long enough for a small inline
# sparkline to read as a real shape. Same "unlabeled inline-SVG
# polyline" technique Herd's own trend graph uses.
TREND_HISTORY_MAX_POINTS = 30
price_history = {good: [] for good in market_multiplier}
need_history = {}


# J29 -- opt-in seasonal demand. Every SEASON_LENGTH_TICKS the "in demand"
# pair of goods rotates through the goods the player can reach; a good in
# demand sells for SEASONAL_DEMAND_BONUS more. Purely a bonus (nothing is
# ever marked down), fully predictable (the status line always names the
# current and next pair), and off by default so the base economy is
# unchanged. season_ticks only advances while the mode is on.
SEASON_LENGTH_TICKS = 30
SEASONAL_DEMAND_BONUS = 0.25
SEASONAL_HOT_GOOD_COUNT = 2
seasonal_demand_enabled = False
season_ticks = 0


# J23 -- diplomatic relations between star systems. Every unit delivered on
# a trip that crosses systems (home / Kepler / Rift / Umbral Deep) counts toward a
# relations level; each level is a small permanent bonus on the proceeds of
# every sale. Purely a bonus, and it can only matter once the player has
# reached a second system, so the base game is untouched.
DIPLOMACY_THRESHOLDS = (25, 75, 150)
DIPLOMACY_BONUS_PER_LEVEL = 0.05
cross_system_units = 0


def diplomacy_level():
    return sum(1 for threshold in DIPLOMACY_THRESHOLDS if cross_system_units >= threshold)


def diplomacy_multiplier():
    return 1.0 + diplomacy_level() * DIPLOMACY_BONUS_PER_LEVEL


def diplomacy_units_to_next_level():
    for threshold in DIPLOMACY_THRESHOLDS:
        if cross_system_units < threshold:
            return threshold - cross_system_units
    return 0


# J11 -- opt-in route hazards and insurance. With hazards on, each loaded
# arrival has a ROUTE_HAZARD_CHANCE of being disrupted (cargo lost, nothing
# sold or delivered). Insurance costs INSURANCE_PREMIUM_PER_TICK for every
# ship in transit and refunds INSURANCE_COVERAGE of the lost trip's
# proceeds, so it is a variance-versus-cost decision, roughly break-even.
# Both are off by default: the base economy carries no hazard.
ROUTE_HAZARD_CHANCE = 0.08
INSURANCE_COVERAGE = 0.75
INSURANCE_PREMIUM_PER_TICK = 1
route_hazards_enabled = False
route_insurance_enabled = False
disruptions_suffered = 0
insurance_payouts = 0
premiums_paid = 0
hazard_rng = random.Random()


def seasonal_reachable_goods():
    reachable = set(active_colony_ids())
    return [g for g in SELL_PRICE if colony_producing(g) in reachable]


def seasonal_hot_goods(season_index):
    goods = seasonal_reachable_goods()
    if not goods:
        return []
    count = min(SEASONAL_HOT_GOOD_COUNT, len(goods))
    start = (season_index * SEASONAL_HOT_GOOD_COUNT) % len(goods)
    return [goods[(start + offset) % len(goods)] for offset in range(count)]


def seasonal_status():
    """(season number, ticks left, hot goods now, hot goods next season)."""
    index = season_ticks // SEASON_LENGTH_TICKS
    left = SEASON_LENGTH_TICKS - (season_ticks % SEASON_LENGTH_TICKS)
    return index + 1, left, seasonal_hot_goods(index), seasonal_hot_goods(index + 1)


def seasonal_multiplier(good):
    if not seasonal_demand_enabled:
        return 1.0
    hot = seasonal_hot_goods(season_ticks // SEASON_LENGTH_TICKS)
    return 1.0 + SEASONAL_DEMAND_BONUS if good in hot else 1.0


def current_sell_price(good):
    return max(1, round(SELL_PRICE[good] * market_multiplier[good] * seasonal_multiplier(good)))


def apply_market_sale(good, qty):
    decay = MARKET_PRICE_DECAY_PER_UNIT_SOLD * (
        MARKET_INSIGHT_2_DECAY_MULTIPLIER if "market_insight_2" in unlocked_research else 1.0
    ) * (HARD_CHARTER_SATURATION_MULTIPLIER if hard_charter_active else 1.0)
    market_multiplier[good] = max(MIN_PRICE_MULTIPLIER, market_multiplier[good] - qty * decay)
    if market_multiplier[good] < MARKET_CRASH_THRESHOLD:
        market_crash_ever[good] = True


# J9 -- market speculation: a small warehouse per good. Buy a lot while a
# price is crashed, hold it, and sell once the price has recovered. Buying
# pushes the price up and selling pushes it down (the same per-unit impact
# a ship's sale has), capacity is small, and selling pays a fee, so it is a
# timing decision with real risk, not a money loop. Stockpile sales are not
# counted as trade sales (no achievements or route stats).
STOCKPILE_CAPACITY = 15
STOCKPILE_LOT = 5
STOCKPILE_SELL_FEE = 0.10
stockpile = {good: 0 for good in SELL_PRICE}
# J-4 -- the "price memory" ghost line: where each good's price multiplier was
# just before the player's last stockpile buy or sell, drawn dashed (and named
# in text) on its sparkline. Only the player's own market moves set it.
price_memory = {}


def can_stockpile_buy(good):
    if good not in stockpile or colony_producing(good) not in active_colony_ids():
        return False
    if stockpile[good] >= STOCKPILE_CAPACITY:
        return False
    qty = min(STOCKPILE_LOT, STOCKPILE_CAPACITY - stockpile[good])
    return total_profit >= qty * current_sell_price(good)


def buy_stockpile(good):
    global total_profit
    if not can_stockpile_buy(good):
        return False
    qty = min(STOCKPILE_LOT, STOCKPILE_CAPACITY - stockpile[good])
    price_memory[good] = market_multiplier[good]
    total_profit -= qty * current_sell_price(good)
    stockpile[good] += qty
    market_multiplier[good] = min(
        MAX_PRICE_MULTIPLIER, market_multiplier[good] + qty * MARKET_PRICE_DECAY_PER_UNIT_SOLD
    )
    return True


def stockpile_sale_value(good):
    return int(round(stockpile.get(good, 0) * current_sell_price(good) * (1 - STOCKPILE_SELL_FEE)))


def sell_stockpile(good):
    global total_profit
    if stockpile.get(good, 0) <= 0 or colony_producing(good) not in active_colony_ids():
        return False
    qty = stockpile[good]
    price_memory[good] = market_multiplier[good]
    total_profit += stockpile_sale_value(good)
    stockpile[good] = 0
    apply_market_sale(good, qty)
    return True


def recover_market():
    for good in market_multiplier:
        recovery = MARKET_PRICE_RECOVERY_PER_TICK * (
            MARKET_INSIGHT_RECOVERY_MULTIPLIER if "market_insight" in unlocked_research else 1.0
        ) * (AUTO_BALANCERS_RECOVERY_MULTIPLIER if charter_perk("auto_balancers") else 1.0)
        market_multiplier[good] = min(MAX_PRICE_MULTIPLIER, market_multiplier[good] + recovery)


def colony_needing(good):
    """The one colony whose need this good satisfies — every good in the
    galaxy (both systems combined) is needed by exactly one colony, so
    there's always a single unambiguous "correct" destination for a
    load of it. Milestone 6's autopilot uses this to decide where to
    send itself. Searches ALL_COLONIES rather than just the reachable
    ones -- a ship can only ever be carrying a Kepler good if it's
    already reached the Kepler Cluster, which itself requires the
    system to be unlocked, so this never resolves to an unreachable
    destination in practice."""
    for colony_id, colony in ALL_COLONIES.items():
        if colony["needs"] == good:
            return colony_id
    return None


def colony_producing(good):
    """Reverse of colony_needing() — the one colony that makes this good.
    Milestone 12 uses this to find where an idle automated ship should
    reposition to when repointing itself at the fleet's most urgent
    need."""
    for colony_id, colony in ALL_COLONIES.items():
        if colony["produces"] == good:
            return colony_id
    return None


# Milestone 6 — automation v1: a limited number of ships can be bought
# into fully autonomous operation. An automated ship loads whatever its
# current colony produces and departs for whichever colony needs it,
# every tick, with no further input — "a route can run itself." Slots
# are capped and each one costs real profit, so automating the whole
# fleet at once isn't free or immediate.
AUTOMATION_COST = 150
MAX_AUTOMATED_SHIPS = 2

# J15 — how many consecutive ticks a manual ship can sit docked and
# empty before its status line flags it as idle. ~20 real seconds at
# TICK_INTERVAL_MS, long enough that briefly deciding where to send a
# ship never trips it.
IDLE_WARNING_TICKS = 20

# J10 — player-chosen ship names, capped to keep the panel header tidy.
MAX_SHIP_NAME_LENGTH = 24

# Milestone 12 — fleet-level automation: off by default, so Milestone 6's
# per-route autopilot behavior (and every test written against it) is
# preserved exactly when the mode isn't switched on. When it is, an idle
# automated ship stops blindly reloading its local produce and instead
# checks whether the fleet's most under-served colony is fed by a
# *different* producer — if so, it repositions there empty to help,
# rather than staying tethered to its original A<->B shuttle forever.
fleet_priority_enabled = False


def most_urgent_colony():
    return min(colony_states, key=lambda cid: colony_states[cid].need_satisfaction)


def set_fleet_priority(enabled):
    global fleet_priority_enabled
    fleet_priority_enabled = enabled


# Milestone 8 — research tree v1: a small, flat framework (no
# prerequisites yet) gating an automation-slot expansion, a fleet-wide
# speed boost, and a new ship class — spent from a separate currency
# (research points) that accrues passively, independent of trade
# profit, so research and trade are two distinct things to manage
# rather than one pool spent two ways.
RESEARCH_PER_TICK = 0.5
RESEARCH_NODES = {
    "automation_slot": {
        "cost": 20, "label": "Automation Expansion", "description": "+1 automation slot",
    },
    "fast_ships": {
        "cost": 15, "label": "Fast Ships I", "description": "-1 tick travel time, fleet-wide",
    },
    "hauler": {
        "cost": 30, "label": "Hauler-Class Refit", "description": "+50% cargo capacity, fleet-wide",
    },
    # Milestone 13 — galaxy scaling: the priciest node yet, gating an
    # entire second system rather than a fleet-wide modifier.
    "galaxy_expansion": {
        "cost": 80, "label": "Galaxy Expansion",
        "description": "Unlocks the Kepler Cluster — 3 new colonies, a new need-triangle",
    },
    # J7 — a second automation-slot tier. Gated behind the first tier via
    # "requires" (a node id that must already be unlocked) rather than
    # just a steeper cost, so the tree gets its first real prerequisite
    # edge instead of staying flat forever.
    "automation_slot_2": {
        "cost": 150, "label": "Automation Expansion II", "description": "+1 more automation slot",
        "requires": "automation_slot",
    },
    # J13 — gates the Rift Colonies, priced above Galaxy Expansion (a
    # third system, one tier further out) and requiring it first.
    "outer_reaches": {
        "cost": 200, "label": "Outer Reaches",
        "description": "Unlocks the Rift Colonies — 3 new colonies, a new need-triangle",
        "requires": "galaxy_expansion",
    },
    # J1 — the deepest research investment yet: a two-step chain past
    # Outer Reaches. Deep Survey has no effect of its own beyond being the
    # required first step (honestly labelled as such); Umbral Reach is the
    # priciest node in the tree and is what actually opens the fourth
    # system.
    "deep_survey": {
        "cost": 240, "label": "Deep Survey",
        "description": "Long-baseline survey arrays — no direct bonus, but the required first step toward the Umbral Deep",
        "requires": "outer_reaches",
    },
    "umbral_reach": {
        "cost": 360, "label": "Umbral Reach",
        "description": "Unlocks the Umbral Deep — 3 new colonies, a new need-triangle",
        "requires": "deep_survey",
    },
    # J15 -- a specialization fork, unlocked once the tree has grown to
    # Automation Expansion II. Committing to either branch's first tier
    # permanently closes the other branch ("excludes"), so this is a real
    # choice about how the empire is run rather than a to-do list.
    "auto_efficiency": {
        "cost": 120, "label": "Autopilot Optimisation (Automation path)",
        "description": "Automated ships earn +10% on every sale",
        "requires": "automation_slot_2", "excludes": ("market_insight", "market_insight_2"),
    },
    "auto_efficiency_2": {
        "cost": 260, "label": "Autopilot Optimisation II (Automation path)",
        "description": "+1 more automation slot",
        "requires": "auto_efficiency", "excludes": ("market_insight", "market_insight_2"),
    },
    "market_insight": {
        "cost": 120, "label": "Market Insight (Market path)",
        "description": "Sold-down prices recover 50% faster",
        "requires": "automation_slot_2", "excludes": ("auto_efficiency", "auto_efficiency_2"),
    },
    "market_insight_2": {
        "cost": 260, "label": "Market Insight II (Market path)",
        "description": "Each unit sold pushes its price down 30% less",
        "requires": "market_insight", "excludes": ("auto_efficiency", "auto_efficiency_2"),
    },
}
AUTO_EFFICIENCY_BONUS = 0.10
AUTO_EFFICIENCY_2_SLOT_BONUS = 1
MARKET_INSIGHT_RECOVERY_MULTIPLIER = 1.5
MARKET_INSIGHT_2_DECAY_MULTIPLIER = 0.7
AUTOMATION_SLOT_RESEARCH_BONUS = 1
AUTOMATION_SLOT_2_RESEARCH_BONUS = 1
FAST_SHIPS_TICK_REDUCTION = 1
HAULER_CARGO_MULTIPLIER = 1.5

research_points = 0.0
unlocked_research = set()


def galaxy_expansion_unlocked():
    return "galaxy_expansion" in unlocked_research


def outer_reaches_unlocked():
    return "outer_reaches" in unlocked_research


def umbral_reach_unlocked():
    return "umbral_reach" in unlocked_research


def active_colony_ids():
    """Every colony ID the player can currently interact with — the home
    system always, the Kepler Cluster once Galaxy Expansion is unlocked,
    the Rift Colonies once Outer Reaches is, and the Umbral Deep once
    Umbral Reach is. Everything reachability-
    sensitive (route drawing, depart-button validity, a ship's list of
    possible destinations) is scoped to this rather than to ALL_COLONIES
    directly."""
    ids = list(COLONIES)
    if galaxy_expansion_unlocked():
        ids += list(EXPANSION_COLONIES)
    if outer_reaches_unlocked():
        ids += list(RIFT_COLONIES)
    if umbral_reach_unlocked():
        ids += list(DEEP_COLONIES)
    return ids


def can_unlock_research(node_id):
    node = RESEARCH_NODES[node_id]
    requires = node.get("requires")
    if requires is not None and requires not in unlocked_research:
        return False
    if research_node_blocked_by(node_id) is not None:
        return False
    return node_id not in unlocked_research and research_points >= node["cost"]


def research_node_blocked_by(node_id):
    """J15 -- the already-unlocked node (if any) that permanently closes
    this one, because the two are opposite sides of a specialization fork."""
    for other in RESEARCH_NODES[node_id].get("excludes", ()):
        if other in unlocked_research:
            return other
    return None


def unlock_research(node_id):
    global research_points
    if not can_unlock_research(node_id):
        return False
    research_points -= RESEARCH_NODES[node_id]["cost"]
    unlocked_research.add(node_id)
    if node_id == "galaxy_expansion":
        # Colony state for the cluster is created only now, on unlock —
        # not eagerly at module load like the home system's. Otherwise
        # it would sit there decaying, unreachable, from tick one, and
        # Milestone 12's most_urgent_colony() (which reads colony_states
        # directly) would fixate on it forever since nothing could ever
        # actually reach it to help.
        for colony_id in EXPANSION_COLONIES:
            colony_states[colony_id] = ColonyState(colony_id)
    elif node_id == "outer_reaches":
        # Same deferred-creation reasoning, one tier further out.
        for colony_id in RIFT_COLONIES:
            colony_states[colony_id] = ColonyState(colony_id)
    elif node_id == "umbral_reach":
        # Same deferred-creation reasoning, one tier further out again.
        for colony_id in DEEP_COLONIES:
            colony_states[colony_id] = ColonyState(colony_id)
    return True


def max_automated_ships():
    bonus = AUTOMATION_SLOT_RESEARCH_BONUS if "automation_slot" in unlocked_research else 0
    bonus += AUTOMATION_SLOT_2_RESEARCH_BONUS if "automation_slot_2" in unlocked_research else 0
    bonus += AUTO_EFFICIENCY_2_SLOT_BONUS if "auto_efficiency_2" in unlocked_research else 0
    return MAX_AUTOMATED_SHIPS + bonus


def travel_ticks():
    reduction = FAST_SHIPS_TICK_REDUCTION if "fast_ships" in unlocked_research else 0
    return max(1, TRAVEL_TICKS - reduction)


def fleet_cargo_multiplier():
    return HAULER_CARGO_MULTIPLIER if "hauler" in unlocked_research else 1.0


# J5 -- ship archetypes, chosen when buying ship 5 or 6 (the original four
# ships are always balanced). "cargo" carries more but is slower, "fast"
# arrives sooner but carries less; both trade off, so no archetype is
# strictly better. Saved per ship and validated on load.
SHIP_ARCHETYPES = {
    "balanced": {"label": "Balanced", "cargo": 1.0, "ticks": 0},
    "cargo": {"label": "Cargo-heavy", "cargo": 1.5, "ticks": 1},
    "fast": {"label": "Fast", "cargo": 0.75, "ticks": -1},
}
DEFAULT_ARCHETYPE = "balanced"


def archetype_for(ship):
    return SHIP_ARCHETYPES.get(getattr(ship, "archetype", DEFAULT_ARCHETYPE), SHIP_ARCHETYPES[DEFAULT_ARCHETYPE])


VETERAN_ROUND_TRIPS = 5  # J14 — round trips on one route for the badge
UNDERPERFORM_FRACTION = 0.5  # J25 — below this share of fleet-average earnings
ROUTE_TREND_WINDOW = 4  # J2 — sales per half-window compared for the arrow
DEFAULT_TREND_EPSILON = 0.05


class Ship:
    def __init__(self, ship_id, start_colony):
        self.id = ship_id
        self.location = start_colony  # colony id, or None while in transit
        self.origin = None  # colony id departed from, while in transit
        self.destination = None  # colony id being traveled to, while in transit
        self.cargo_good = None
        self.cargo_qty = 0
        self.transit_ticks_remaining = 0
        self.transit_total_ticks = 0  # ticks this specific trip started with, for map interpolation
        self.automated = False
        # J6 — ships 5/6 start unpurchased; the original 4-ship roster is
        # purchased from the moment the game starts, same as it always
        # was before this feature existed.
        self.purchased = True
        self.archetype = DEFAULT_ARCHETYPE  # J5
        # J10 — player-chosen display name, defaults to "Ship N".
        self.name = f"Ship {ship_id}"
        # J15 — consecutive ticks this ship has spent docked, empty, and
        # not automated. Reset the instant any of those stop being true
        # (tick() does the resetting; see IDLE_WARNING_TICKS below).
        self.idle_ticks = 0
        # J14 — veteran-hauler bookkeeping: the (unordered) colony pair of
        # the last completed cargo leg, and how many consecutive legs
        # have been on that same pair. Two legs = one round trip.
        self.route_key = None
        self.route_legs = 0
        # J25 — lifetime credits this ship's own deliveries have earned.
        self.total_earned = 0
        # J-6 -- throughput bookkeeping: units this ship has delivered, the
        # ticks it has been part of the fleet, and units per good.
        self.units_moved = 0
        self.ticks_owned = 0
        self.units_by_good = {}
        # J-7 -- the captain's perk id (or None) and the deliveries made since
        # the captain was assigned (the Lucky Trader's every-fourth-trip count).
        self.captain = None
        self.captain_deliveries = 0

    @property
    def round_trips(self):
        return self.route_legs // 2

    @property
    def is_veteran(self):
        return self.round_trips >= VETERAN_ROUND_TRIPS

    @property
    def in_transit(self):
        return self.location is None

    @property
    def docked(self):
        return self.location is not None

    @property
    def loaded(self):
        return self.cargo_qty > 0

    def load(self):
        if not self.purchased or not self.docked or self.loaded:
            return False
        self.cargo_good = ALL_COLONIES[self.location]["produces"]
        self.cargo_qty = max(
            1,
            round(
                colony_states[self.location].cargo_capacity() * fleet_cargo_multiplier() * archetype_for(self)["cargo"]
                * captain_cargo_multiplier(self)
            )
            + (CHARTER_CARGO_BONUS if charter_perk("surveyed_lanes") else 0),
        )
        return True

    def other_colonies(self):
        """Every colony this ship could plausibly be sent to right now —
        anywhere reachable except wherever it's currently docked."""
        if not self.docked:
            return []
        return [c for c in active_colony_ids() if c != self.location]

    def _begin_transit(self, destination):
        add_dock_pulse(self.location, "undock")
        self.origin = self.location
        self.destination = destination
        self.location = None
        self.transit_total_ticks = max(1, captain_adjusted_ticks(self, travel_ticks() + archetype_for(self)["ticks"]))
        self.transit_ticks_remaining = self.transit_total_ticks

    def depart(self, destination):
        if not self.purchased or not self.docked or not self.loaded:
            return False
        if destination == self.location or destination not in active_colony_ids():
            return False
        self._begin_transit(destination)
        return True

    def reposition(self, destination):
        """Milestone 12: fleet-priority repositioning — an automated ship
        travels empty to a different producer colony, abandoning its
        current home shuttle. Unlike depart(), this doesn't require
        cargo, but it's only ever called by run_automation() under
        fleet-priority mode; manual play has no button that reaches it,
        so the "must be loaded to leave" rule still holds for the
        player."""
        if not self.docked or self.loaded:
            return False
        if destination == self.location or destination not in active_colony_ids():
            return False
        self._begin_transit(destination)
        return True

    def advance_transit(self):
        """Ticks the transit countdown by one. Returns the sale proceeds
        (good, qty, profit) if this tick completed the transit, else None."""
        if not self.in_transit:
            return None
        self.transit_ticks_remaining -= 1
        if self.transit_ticks_remaining > 0:
            return None
        good, qty = self.cargo_good, self.cargo_qty
        destination = self.destination
        result = None
        if good is not None:
            # Milestone 12's empty reposition() trips have no cargo, so
            # there's nothing to sell or deliver on arrival -- just dock.
            global cross_system_units, disruptions_suffered, insurance_payouts
            efficiency = 1.0 + (AUTO_EFFICIENCY_BONUS if self.automated and "auto_efficiency" in unlocked_research else 0.0)
            profit = int(round(
                qty * current_sell_price(good) * diplomacy_multiplier() * legacy_sale_multiplier() * efficiency
                * captain_proceeds_multiplier(self, destination, good) * colony_premium_multiplier(destination)
            ))
            if route_hazards_enabled and hazard_rng.random() < ROUTE_HAZARD_CHANCE:
                # J11 -- a route disruption: the cargo is lost, nothing is
                # delivered or sold. Insurance pays a share of what the
                # trip would have earned. qty == 0 marks the disruption
                # for tick(), which logs it instead of a sale.
                payout = int(round(profit * INSURANCE_COVERAGE)) if route_insurance_enabled else 0
                disruptions_suffered += 1
                insurance_payouts += payout
                result = (good, 0, payout)
                self.total_earned += payout
            else:
                if self.origin is not None and _system_label_for_colony(self.origin) != _system_label_for_colony(destination):
                    cross_system_units = min(cross_system_units + qty, 10_000_000)
                dest_state = colony_states[destination]
                if ALL_COLONIES[destination]["needs"] == good:
                    dest_state.deliver(qty)
                elif dest_state.is_developed() and dest_state.secondary_need() == good:
                    dest_state.deliver_secondary(qty)
                result = (good, qty, profit)
                self.total_earned += profit
                self.units_moved = min(LEDGER_MAX, self.units_moved + qty)
                self.units_by_good[good] = min(LEDGER_MAX, self.units_by_good.get(good, 0) + qty)
                if self.captain is not None:
                    self.captain_deliveries += 1
            key = frozenset((self.origin, destination))
            if key == self.route_key:
                self.route_legs += 1
            else:
                self.route_key = key
                self.route_legs = 1
        self.location = destination
        add_dock_pulse(destination, "dock")
        self.origin = None
        self.destination = None
        self.cargo_good = None
        self.cargo_qty = 0
        return result


# J6 — a 5th/6th purchasable ship. Both exist from module load (so
# get_state()/load_state()'s existing generic per-ship loops need no
# special-casing) but start unpurchased/hidden behind a one-time credit
# cost -- SHIP_PURCHASE_COST below, enforced by can_purchase_ship()/
# purchase_ship() and Ship.load()/depart()'s own "purchased" guard.
# Sequential: the 6th requires the 5th already bought, same "one tier at
# a time" shape as the research tree's own prerequisite edges.
PURCHASABLE_SHIP_IDS = ("5", "6")
SHIP_PURCHASE_COST = {"5": 400, "6": 1000}

ships = {
    "1": Ship("1", "aurum"),
    "2": Ship("2", "verdant"),
    "3": Ship("3", "ferrum"),
    "4": Ship("4", "cryo"),
    "5": Ship("5", "aurum"),
    "6": Ship("6", "aurum"),
}
for _purchasable_id in PURCHASABLE_SHIP_IDS:
    ships[_purchasable_id].purchased = False

total_profit = 0
sale_log = []  # most recent sale message, for the status line
# Z25 save-portability audit: only sale_log[-1] is ever read (the status
# line and its own regression test both index just the last entry), but
# tick() appended to this list every sale with no truncation at all --
# unlike every sibling rolling-history field in this file
# (good_profit_recent/price_history/need_history), which are all capped.
# Left unbounded, a long automated session (this game ticks once a second
# via setInterval regardless of whether the player is present, see
# TICK_INTERVAL_MS) grows this without limit: measured ~100KB of a
# ~110KB save payload after 5000 ticks (~83 simulated minutes) in a
# fully-automated session. Capped generously above the "just the last
# one" need in case a future feature wants a short recent-sales view.
SALE_LOG_MAX_ENTRIES = 20

# New tracked state for achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md §4):
# each of these tracks something that genuinely *happened*, which isn't
# recoverable from state that only reflects the current moment (e.g.
# total_profit can go back down after an automation purchase, so it can't
# tell you the highest it's ever been).
total_sales_count = 0
max_profit_ever = 0
goods_sold_ever = set()
ever_repositioned = False
# Per-good watermark: True once that good's price has crashed below
# MARKET_CRASH_THRESHOLD at least once this session -- market_recovery
# checks for a good that's both crashed at some point and currently back
# above MARKET_RECOVERY_THRESHOLD.
market_crash_ever = {good: False for good in market_multiplier}
MARKET_CRASH_THRESHOLD = 0.4
MARKET_RECOVERY_THRESHOLD = 0.9


def automated_ship_count():
    return sum(1 for s in ships.values() if s.automated)


def automation_slots_available():
    return automated_ship_count() < max_automated_ships()


def automate_ship(ship_id):
    global total_profit
    ship = ships[ship_id]
    if not ship.purchased or ship.automated or not automation_slots_available() or total_profit < automation_cost():
        return False
    total_profit -= automation_cost()
    ship.automated = True
    return True


# J17 -- player-run trade posts. Once every automation slot is filled
# (automation is "maxed"), the player can establish a trade post in a
# reachable star system: a passive income source that needs no ship. One
# post per system, so it scales with how far the empire has expanded, and
# it pays a small flat amount each tick (not counted as a sale).
TRADE_POST_SYSTEMS = ("Home system", "Kepler Cluster", "Rift Colonies", "Umbral Deep")
TRADE_POST_COST = 400
TRADE_POST_INCOME_PER_TICK = 2
trade_posts = []


def automation_is_maxed():
    return not automation_slots_available()


def _system_is_reachable(system_label):
    if system_label == "Home system":
        return True
    if system_label == "Kepler Cluster":
        return galaxy_expansion_unlocked()
    if system_label == "Rift Colonies":
        return outer_reaches_unlocked()
    return umbral_reach_unlocked()


def next_trade_post_system():
    for system_label in TRADE_POST_SYSTEMS:
        if system_label not in trade_posts and _system_is_reachable(system_label):
            return system_label
    return None


def can_build_trade_post():
    return (
        automation_is_maxed()
        and next_trade_post_system() is not None
        and total_profit >= trade_post_cost()
    )


def build_trade_post():
    global total_profit
    if not can_build_trade_post():
        return False
    total_profit -= trade_post_cost()
    trade_posts.append(next_trade_post_system())
    return True


def trade_post_income_per_tick():
    return len(trade_posts) * trade_post_income_each()


# J7 -- colony investment: spend credits to push an undeveloped colony
# toward its Level 2 development (the same progress deliveries build),
# so surplus credits can accelerate growth and specialization. It costs
# more per unit than the credits a delivery earns, so it speeds a colony up
# without replacing supplying it. Repeatable until the colony is developed.
COLONY_INVEST_COST = 60
COLONY_INVEST_UNITS = 10


def can_grant_concession(colony_id):
    state = colony_states.get(colony_id)
    return state is not None and state.has_demand() and total_profit >= CONCESSION_COST


def grant_concession(colony_id):
    global total_profit
    if not can_grant_concession(colony_id):
        return False
    total_profit -= CONCESSION_COST
    colony_states[colony_id].grant_concession()
    return True


def colony_invest_cost_for(colony_id):
    """What an Invest costs at this colony right now (J-25: an Opportunistic
    colony with a low need takes it at a discount)."""
    base = colony_invest_cost()
    state = colony_states.get(colony_id)
    if (
        state is not None
        and state.temperament() == "opportunistic"
        and state.need_satisfaction < OPPORTUNIST_NEED_BELOW
    ):
        return max(1, int(round(base * OPPORTUNIST_INVEST_DISCOUNT)))
    return base


def can_invest_in_colony(colony_id):
    if colony_id not in active_colony_ids() or colony_id not in colony_states:
        return False
    return not colony_states[colony_id].is_developed() and total_profit >= colony_invest_cost_for(colony_id)


def invest_in_colony(colony_id):
    global total_profit
    if not can_invest_in_colony(colony_id):
        return False
    total_profit -= colony_invest_cost_for(colony_id)
    colony_states[colony_id].add_development(COLONY_INVEST_UNITS)
    return True


def colony_premium_multiplier(colony_id):
    """J-25 -- the temperament premium on proceeds delivered to this colony."""
    state = colony_states.get(colony_id)
    if state is None:
        return 1.0
    return 1.0 + TEMPERAMENTS[state.temperament()]["premium"]


def can_purchase_ship(ship_id):
    ship = ships[ship_id]
    if ship.purchased:
        return False
    if ship_id == "6" and not ships["5"].purchased:
        return False
    return total_profit >= SHIP_PURCHASE_COST[ship_id]


def purchase_ship(ship_id, archetype=DEFAULT_ARCHETYPE):
    """J6 — a one-time credit spend that unlocks a 5th/6th ship, same
    shape as automate_ship()'s one-time AUTOMATION_COST spend. J5 -- the
    buyer also picks an archetype (an unknown value falls back to balanced)."""
    global total_profit
    if not can_purchase_ship(ship_id):
        return False
    total_profit -= SHIP_PURCHASE_COST[ship_id]
    ships[ship_id].purchased = True
    ships[ship_id].archetype = archetype if archetype in SHIP_ARCHETYPES else DEFAULT_ARCHETYPE
    return True


def rename_ship(ship_id, new_name):
    """J10 — a blank/whitespace-only name is rejected rather than
    silently accepted, so a ship can never end up with an empty label."""
    name = (new_name or "").strip()
    if not name:
        return False
    ships[ship_id].name = name[:MAX_SHIP_NAME_LENGTH]
    return True


def reset_ship_name(ship_id):
    """J12 — restore the default "Ship N" name."""
    ships[ship_id].name = f"Ship {ship_id}"
    return True


# ---------------------------------------------------------------------------
# J-7/J-8 -- Fleet Captains. A ship that has become a veteran hauler (five
# round trips on one route) earns a captain: the player CHOOSES which of four
# named captains to put in the seat from a visible roster, so nothing is a
# random draw. Each captain's perk has a built-in trade-off, a captain serves
# on one ship at a time, and a captain may be moved to a different ship once
# per charter. Captains are met once and remembered across charters (a small
# collection); their postings reset with every renewal, like the fleet.
# Without a captain every helper below returns the plain value.
# ---------------------------------------------------------------------------
CAPTAIN_SWAPS_PER_CHARTER = 1  # moves of one captain after the first posting
LUCKY_EVERY = 4  # every Nth delivery by a Lucky Trader pays extra
LUCKY_BONUS = 0.40
LUCKY_OFF_BEAT = -0.03
FRUGAL_PROCEEDS = 0.08
FRUGAL_CARGO = 0.90
NIGHT_OWL_MIN_TICKS = 3  # a trip must be at least this long to save a tick
NIGHT_OWL_PROCEEDS = -0.05
PERFECTIONIST_BONUS = 0.12
PERFECTIONIST_BELOW = 0.6
PERFECTIONIST_PENALTY = -0.05
PERFECTIONIST_ABOVE = 0.9
CAPTAINS = {
    "frugal": {
        "label": "Frugal", "name": "Captain Ilsa Brandt",
        "perk": f"+{int(FRUGAL_PROCEEDS * 100)}% on this ship's sales.",
        "tradeoff": f"Holds {int(round((1 - FRUGAL_CARGO) * 100))}% less cargo (hurts a Fast hull most; a Cargo-heavy hull hides it).",
        "quote": "Every crate counted twice.",
    },
    "lucky": {
        "label": "Lucky Trader", "name": "Captain Joss Marrow",
        "perk": f"Every {LUCKY_EVERY}th delivery pays +{int(LUCKY_BONUS * 100)}%.",
        "tradeoff": f"The other deliveries pay {int(LUCKY_OFF_BEAT * 100)}%, so it is a small average gain, not a jackpot.",
        "quote": "I never gamble. The odds are simply fond of me.",
    },
    "night_owl": {
        "label": "Night Owl", "name": "Captain Sef Okonkwo",
        "perk": f"Trips of {NIGHT_OWL_MIN_TICKS}+ ticks arrive one tick sooner.",
        "tradeoff": f"{int(NIGHT_OWL_PROCEEDS * 100)}% on sales, and no gain on a Fast hull already near the one-tick floor.",
        "quote": "Dock lights are for people who sleep.",
    },
    "perfectionist": {
        "label": "Perfectionist", "name": "Captain Rhea Vance",
        "perk": f"+{int(PERFECTIONIST_BONUS * 100)}% when delivering to a colony under {int(PERFECTIONIST_BELOW * 100)}% satisfied.",
        "tradeoff": f"{int(PERFECTIONIST_PENALTY * 100)}% when the colony is already over {int(PERFECTIONIST_ABOVE * 100)}% satisfied.",
        "quote": "If it is not needed, it is not on my manifest.",
    },
}
CAPTAIN_IDS = tuple(CAPTAINS)
captain_earned = set()  # ship ids that reached veteran status this charter
captain_assignments = {perk_id: 0 for perk_id in CAPTAINS}  # postings this charter (the 2nd is the swap)
captains_met = set()  # captains ever posted, across every charter


def captain_of(ship):
    perk_id = getattr(ship, "captain", None)
    return perk_id if perk_id in CAPTAINS else None


def captain_ship_for(perk_id):
    """The ship currently serving under this captain, or None."""
    for ship in ships.values():
        if ship.captain == perk_id:
            return ship
    return None


def captain_cargo_multiplier(ship):
    return FRUGAL_CARGO if captain_of(ship) == "frugal" else 1.0


def captain_adjusted_ticks(ship, ticks):
    if captain_of(ship) == "night_owl" and ticks >= NIGHT_OWL_MIN_TICKS:
        return ticks - 1
    return ticks


def captain_proceeds_multiplier(ship, destination, good):
    perk_id = captain_of(ship)
    if perk_id is None:
        return 1.0
    if perk_id == "frugal":
        return 1.0 + FRUGAL_PROCEEDS
    if perk_id == "night_owl":
        return 1.0 + NIGHT_OWL_PROCEEDS
    if perk_id == "lucky":
        lucky_trip = (ship.captain_deliveries + 1) % LUCKY_EVERY == 0
        return 1.0 + (LUCKY_BONUS if lucky_trip else LUCKY_OFF_BEAT)
    state = colony_states.get(destination)
    if state is None:
        return 1.0
    satisfaction = state.need_satisfaction if ALL_COLONIES[destination]["needs"] == good else state.secondary_need_satisfaction
    if satisfaction < PERFECTIONIST_BELOW:
        return 1.0 + PERFECTIONIST_BONUS
    if satisfaction > PERFECTIONIST_ABOVE:
        return 1.0 + PERFECTIONIST_PENALTY
    return 1.0


def captain_note_veterans():
    """A ship that is a veteran hauler right now has earned a captain's seat
    for the rest of the charter (called every tick)."""
    for ship in ships.values():
        if ship.purchased and ship.is_veteran:
            captain_earned.add(ship.id)


def captain_is_earned(ship_id):
    return ship_id in captain_earned and ships[ship_id].purchased


def can_assign_captain(perk_id, ship_id):
    if not isinstance(perk_id, str) or not isinstance(ship_id, str):
        return False
    if perk_id not in CAPTAINS or ship_id not in ships or not captain_is_earned(ship_id):
        return False
    if ships[ship_id].captain is not None:
        return False
    if captain_assignments[perk_id] >= 1 + CAPTAIN_SWAPS_PER_CHARTER:
        return False
    return True


def is_captain_swap(perk_id):
    """True when posting this captain again would use up its once-per-charter move."""
    return captain_assignments[perk_id] >= 1


def assign_captain(perk_id, ship_id):
    if not can_assign_captain(perk_id, ship_id):
        return False
    current = captain_ship_for(perk_id)
    if current is not None:
        current.captain = None
        current.captain_deliveries = 0
    ship = ships[ship_id]
    ship.captain = perk_id
    ship.captain_deliveries = 0
    captain_assignments[perk_id] += 1
    captains_met.add(perk_id)
    return True


def can_release_captain(perk_id):
    return isinstance(perk_id, str) and perk_id in CAPTAINS and captain_ship_for(perk_id) is not None


def release_captain(perk_id):
    ship = captain_ship_for(perk_id)
    if ship is None:
        return False
    ship.captain = None
    ship.captain_deliveries = 0
    return True


def captain_status_text(perk_id):
    captain = CAPTAINS[perk_id]
    ship = captain_ship_for(perk_id)
    where = f"serving on {ship.name}" if ship is not None else "waiting in the roster"
    moves = max(0, 1 + CAPTAIN_SWAPS_PER_CHARTER - captain_assignments[perk_id])
    return (
        f"{captain['name']}, {captain['label']} ({where}). {captain['perk']} Trade-off: {captain['tradeoff']} "
        f"{moves} posting(s) left this charter."
    )


def captains_summary_text():
    earned = sorted(ship_id for ship_id in captain_earned if ships[ship_id].purchased)
    employed = sum(1 for ship in ships.values() if ship.captain)
    seats = ", ".join(ships[ship_id].name for ship_id in earned) if earned else "none yet"
    return (
        f"Seats earned (veteran haulers): {seats}. {employed} of {len(CAPTAINS)} captains posted. "
        f"{len(captains_met)} of {len(CAPTAINS)} captains met across every charter."
    )


def run_automation():
    """Gives every automated, docked ship one autopilot action this
    tick: load if empty, depart for whichever colony needs its cargo if
    loaded. Runs after transit resolution, so a ship that just arrived
    this tick doesn't sit idle for a full extra tick before restarting."""
    global ever_repositioned
    for ship in ships.values():
        if not ship.automated or not ship.docked:
            continue
        if not ship.loaded:
            if fleet_priority_enabled:
                urgent_good = ALL_COLONIES[most_urgent_colony()]["needs"]
                producer = colony_producing(urgent_good)
                if producer and producer != ship.location and ship.reposition(producer):
                    ever_repositioned = True
                    continue
            ship.load()
        else:
            destination = colony_needing(ship.cargo_good)
            if destination and destination != ship.location:
                ship.depart(destination)


# Milestone 14 — endgame: a soft win-state, not a stopping point. Once
# the fleet is fully automated, Fleet Priority is switched on, and the
# Kepler Cluster is unlocked, the player has built exactly what the
# game's whole arc was pointing at -- a self-running, multi-system
# economy. Rather than literally simulating "hundreds of worlds" as
# real per-colony DOM/state (impractical, and not actually more
# meaningful to look at than a handful of well-simulated ones), that
# scale is narrated as an abstracted, ever-growing background galaxy
# that the player's own pattern has visibly spread to -- a deliberate,
# documented scope cut in favor of a satisfying number over a hollow
# multiplication of unreachable colonies.
ENDGAME_BACKGROUND_WORLD_CAP = 500
ENDGAME_BACKGROUND_WORLDS_PER_TICK = 2
ENDGAME_BACKGROUND_REVENUE_PER_WORLD = 0.4

endgame_reached = False
ticks_since_endgame = 0

# J3 -- the Trade Guild: an NPC faction that occasionally offers a bulk
# contract (deliver N units of a good to a colony that needs it, before a
# deadline) for a bonus on top of the ordinary sale. Deliveries still sell
# normally, so a contract is purely an extra reward. Accepting is optional;
# failing or ignoring one costs nothing.
GUILD_MIN_SALES = 3  # nothing is offered until the player has made a few sales
GUILD_FIRST_OFFER_TICKS = 40
GUILD_COOLDOWN_TICKS = 60  # quiet time after a contract resolves or lapses
GUILD_OFFER_LAPSE_TICKS = 90  # how long an unanswered offer stays on the table
GUILD_DEADLINE_TICKS = 150
GUILD_UNITS_MIN, GUILD_UNITS_MAX = 10, 30
GUILD_REWARD_MULTIPLIER = 1.6  # bonus credits = units x current price x this
GUILD_STATES = ("none", "offered", "active")
guild_rng = random.Random()
guild_state = "none"
guild_contract = {"good": None, "destination": None, "units": 0, "delivered": 0, "ticks_left": 0, "reward": 0}
guild_cooldown = GUILD_FIRST_OFFER_TICKS
guild_completed = 0
guild_failed = 0


def _guild_clear(cooldown=None):
    global guild_state, guild_cooldown
    if cooldown is None:
        cooldown = guild_cooldown_ticks()
    guild_state = "none"
    guild_cooldown = cooldown
    guild_contract.update({"good": None, "destination": None, "units": 0, "delivered": 0, "ticks_left": 0, "reward": 0})


def guild_candidates():
    """(destination, good) pairs the guild could ask for: a reachable colony
    and the good it naturally needs."""
    return [(cid, ALL_COLONIES[cid]["needs"]) for cid in active_colony_ids()]


def guild_make_offer():
    global guild_state
    options = guild_candidates()
    if not options or guild_state != "none":
        return False
    destination, good = guild_rng.choice(options)
    units = guild_rng.randint(GUILD_UNITS_MIN, GUILD_UNITS_MAX)
    guild_contract.update({
        "good": good,
        "destination": destination,
        "units": units,
        "delivered": 0,
        "ticks_left": GUILD_OFFER_LAPSE_TICKS,
        "reward": int(round(units * current_sell_price(good) * guild_reward_multiplier())),
    })
    guild_state = "offered"
    return True


def guild_accept():
    global guild_state
    if guild_state != "offered":
        return False
    guild_state = "active"
    guild_contract["ticks_left"] = GUILD_DEADLINE_TICKS
    return True


def guild_decline():
    if guild_state != "offered":
        return False
    _guild_clear()
    return True


def guild_record_delivery(good, destination, qty):
    """Called for every completed, undisrupted sale."""
    global total_profit, max_profit_ever, guild_completed
    if guild_state != "active" or good != guild_contract["good"] or destination != guild_contract["destination"]:
        return
    guild_contract["delivered"] = min(guild_contract["units"], guild_contract["delivered"] + max(0, int(qty)))
    if guild_contract["delivered"] >= guild_contract["units"]:
        reward = guild_contract["reward"]
        total_profit += reward
        max_profit_ever = max(max_profit_ever, total_profit)
        guild_completed += 1
        _guild_clear()
        show_notice_toast(f"\U0001F91D Trade Guild contract complete: +{reward:,} credits.")


def guild_tick():
    global guild_cooldown, guild_failed
    if guild_state == "none":
        guild_cooldown -= 1
        if guild_cooldown <= 0 and total_sales_count >= GUILD_MIN_SALES:
            guild_make_offer()
    elif guild_state == "offered":
        guild_contract["ticks_left"] -= 1
        if guild_contract["ticks_left"] <= 0:
            _guild_clear()  # lapsed unanswered: no penalty
    elif guild_state == "active":
        guild_contract["ticks_left"] -= 1
        if guild_contract["ticks_left"] <= 0:
            guild_failed += 1
            _guild_clear()  # missed the deadline: no penalty, just no bonus


def guild_status_text():
    c = guild_contract
    if guild_state == "offered":
        return (
            f"The Trade Guild offers a contract: deliver {c['units']} {c['good'].replace('_', ' ')} to "
            f"{ALL_COLONIES[c['destination']]['name']} within {GUILD_DEADLINE_TICKS} ticks of accepting "
            f"for a {c['reward']:,}-credit bonus on top of the normal sale."
        )
    if guild_state == "active":
        return (
            f"Contract accepted: {c['delivered']}/{c['units']} {c['good'].replace('_', ' ')} delivered to "
            f"{ALL_COLONIES[c['destination']]['name']}, {c['ticks_left']} ticks left "
            f"for a {c['reward']:,}-credit bonus."
        )
    record = f" Contracts completed: {guild_completed}." if guild_completed else ""
    return "The Trade Guild is watching your fleet. A contract will be offered when it has one for you." + record


def render_guild():
    document.getElementById("guild-status-display").innerText = guild_status_text()
    document.getElementById("guild-accept-button").hidden = guild_state != "offered"
    document.getElementById("guild-decline-button").hidden = guild_state != "offered"


def on_guild_accept(event=None):
    if guild_accept():
        render()


def on_guild_decline(event=None):
    if guild_decline():
        render()


# J21 -- "trade empire legacy": once the endgame is reached, the player may
# found a NEW corporation. The world resets to a fresh start, but each
# founding permanently raises a small legacy bonus (built independently of
# any shared meta-progression module, per Z3's resolution). It rides the
# save file (so it travels with the account's save), never localStorage.
LEGACY_MAX_LEVEL = 5
LEGACY_STARTING_CREDITS = 150  # extra starting credits per legacy level
LEGACY_SALE_BONUS = 0.02  # +2% on every sale per legacy level (max +10%)
legacy_level = 0
legacy_achievements = []  # ids earned by earlier corporations, carried over
_fresh_state = None  # get_state() of a brand-new game, captured before setup()


def legacy_sale_multiplier():
    return 1.0 + LEGACY_SALE_BONUS * legacy_level


def legacy_starting_credits(level=None):
    return LEGACY_STARTING_CREDITS * (legacy_level if level is None else level)


def can_found_new_corporation():
    # O-1: renewal is no longer capped (the legacy BONUS still is, at
    # LEGACY_MAX_LEVEL); the charter tree and ledger keep growing.
    return endgame_reached and _fresh_state is not None and not sandbox_active  # Z-18: no renewal from the sandbox


def legacy_summary_text():
    if legacy_level <= 0:
        return "Legacy: none yet — reach the endgame to renew the charter with a permanent bonus."
    maxed = " (maxed)" if legacy_level >= LEGACY_MAX_LEVEL else ""
    return (
        f"Legacy level {legacy_level}/{LEGACY_MAX_LEVEL}{maxed}: +{legacy_starting_credits():,} starting credits "
        f"and +{round((legacy_sale_multiplier() - 1.0) * 100)}% on every sale."
    )


def found_new_corporation():
    """Renew the charter: reset to a fresh corporation, raise the legacy (to
    its cap), earn charter points, keep the perk tree, the ledger and the
    achievements, and roll new founding conditions. Returns False when the
    endgame hasn't been reached."""
    global legacy_level, legacy_achievements, total_profit, max_profit_ever, _previously_earned_ids
    global charters_completed, charter_points_earned, charter_perks, hard_charter_active, hard_charter_next
    global ledger_units_moved, ledger_routes_established, ledger_hard_completed, ledger_routes_seen
    global ledger_charter_units, charter_career, captains_met
    if not can_found_new_corporation():
        return False
    order = {entry["id"]: i for i, entry in enumerate(ACHIEVEMENTS)}
    carried = sorted(set(legacy_achievements) | set(achievement_ids_earned()), key=lambda a: order.get(a, 10**6))
    new_level = min(LEGACY_MAX_LEVEL, legacy_level + 1)
    keep = {
        "completed": charters_completed,
        "points": charter_points_earned + charter_points_for_next_renewal(),
        "perks": set(charter_perks),
        "hard_done": ledger_hard_completed,
        "units": ledger_units_moved,
        "routes": ledger_routes_established,
        "career": list(charter_career) + [{
            "n": min(CHARTER_COUNT_MAX, charters_completed + 1),
            "hard": bool(hard_charter_active),
            "units": ledger_charter_units,
            "routes": len(ledger_routes_seen),
            "peak": int(max_profit_ever),
            "perks": len(charter_perks),
            **({"dark": True} if blackout_done else {}),  # J-30
        }],
        "met": set(captains_met),
        "records": dict(records),
    }
    finishing_hard = hard_charter_active
    begin_hard = hard_charter_next and hard_charter_unlocked()
    load_state(json.loads(json.dumps(_fresh_state)))
    legacy_achievements = carried
    charter_perks = keep["perks"]
    charter_points_earned = keep["points"]
    charters_completed = keep["completed"]
    ledger_hard_completed = keep["hard_done"]
    ledger_units_moved, ledger_routes_established = keep["units"], keep["routes"]
    ledger_routes_seen = set()
    ledger_charter_units = 0
    charter_career = keep["career"][-CAREER_MAX_ENTRIES:]
    captains_met = keep["met"]
    records.clear()
    records.update(keep["records"])
    _guild_clear(guild_first_offer_ticks())  # Guild Standing shortens the first wait
    # Baseline BEFORE the renewal is counted: the carried achievements must
    # not all toast again, but the ones this renewal earns should.
    _previously_earned_ids = _earned_snapshot()
    legacy_level = new_level
    charters_completed = min(CHARTER_COUNT_MAX, keep["completed"] + 1)
    if finishing_hard:
        ledger_hard_completed = min(CHARTER_COUNT_MAX, keep["hard_done"] + 1)
    hard_charter_active = begin_hard
    hard_charter_next = False
    total_profit += legacy_starting_credits()
    max_profit_ever = max(max_profit_ever, total_profit)
    apply_founding_conditions()
    render()
    return True


# ---------------------------------------------------------------------------
# O-1..O-4 -- "Renew the Charter". J21's legacy (above) stays exactly as it
# was shipped: it is the flat, capped baseline (starting credits + a small
# sale bonus, five levels). What O-1 adds on top is a small permanent
# skill tree of "charter perks" bought with CHARTER POINTS, which a
# renewal earns. The legacy level counts renewals up to its cap of 5; the
# renewal count itself (charters_completed) keeps going, so the tree and
# the ledger stay meaningful long after the flat legacy is maxed. A save
# from before this feature that already has legacy level N is migrated on
# load as N completed charters with N x CHARTER_POINTS_PER_RENEWAL points
# (see load_state()), so nobody who already renewed loses progress.
#
# Everything here is opt-in: a player who never renews has no charter
# state at all, no founding conditions, and unchanged balance.
# ---------------------------------------------------------------------------
CHARTER_POINTS_PER_RENEWAL = 2
HARD_CHARTER_BONUS_POINTS = 1  # extra point for finishing a harder charter
CHARTER_BRANCHES = {
    "routes": "Routes",
    "automation": "Automation",
    "colonies": "Colonies",
    "reputation": "Reputation",
}
# Each perk is small, bought once, and is either a flat convenience or a
# modest multiplier on something that already exists; nothing here is a
# raw sale-price bonus (that is what the legacy level is for), and costs
# scale by tier (1 / 2 / 3 points). "founding" perks also take effect the
# moment a renewal begins a new charter (and immediately when bought).
CHARTER_PERKS = {
    # Routes
    "surveyed_lanes": {
        "branch": "routes", "cost": 1, "label": "Surveyed Lanes", "requires": (),
        "description": "+1 unit of cargo on every load.",
    },
    "waystation_network": {
        "branch": "routes", "cost": 2, "label": "Waystation Network", "requires": ("surveyed_lanes",),
        "description": "Trade posts cost 25% less and pay +1 credit per tick.",
    },
    "standing_convoy": {
        "branch": "routes", "cost": 3, "label": "Standing Convoy", "founding": True,
        "requires": ("waystation_network", "standing_orders"),
        "description": "Ship 1 begins every charter already automated, free of charge.",
    },
    # Automation
    "standing_orders": {
        "branch": "automation", "cost": 1, "label": "Standing Orders", "requires": (),
        "description": "Automating a ship costs 20% less.",
    },
    "lab_automation": {
        "branch": "automation", "cost": 2, "label": "Lab Automation", "requires": ("standing_orders",),
        "description": "Research points accrue 20% faster.",
    },
    "auto_balancers": {
        "branch": "automation", "cost": 3, "label": "Auto-balancers", "requires": ("lab_automation",),
        "description": "Sold-down prices recover 20% faster.",
    },
    # Colonies
    "frontier_grants": {
        "branch": "colonies", "cost": 1, "label": "Frontier Grants", "requires": (),
        "description": "Investing in a colony costs 45 credits instead of 60.",
    },
    "settler_guilds": {
        "branch": "colonies", "cost": 2, "label": "Settler Guilds", "requires": ("frontier_grants",),
        "description": "Colony needs decay 10% slower.",
    },
    "charter_colonies": {
        "branch": "colonies", "cost": 3, "label": "Charter Colonies", "requires": ("settler_guilds",),
        "description": "Colonies reach Level 2 after 85 units delivered instead of 100.",
    },
    # Reputation
    "guild_standing": {
        "branch": "reputation", "cost": 1, "label": "Guild Standing", "requires": (),
        "description": "The Trade Guild's first offer comes after 15 ticks instead of 40, and it pauses 45 instead of 60 between contracts.",
    },
    "colonial_goodwill": {
        "branch": "reputation", "cost": 2, "label": "Colonial Goodwill", "founding": True,
        "requires": ("guild_standing",),
        "description": "Home colonies begin each charter with +10% need satisfaction.",
    },
    "trusted_name": {
        "branch": "reputation", "cost": 3, "label": "Trusted Name", "requires": ("colonial_goodwill",),
        "description": "Trade Guild contracts pay a 15% larger bonus.",
    },
}
CHARTER_CARGO_BONUS = 1
WAYSTATION_COST_MULTIPLIER = 0.75
WAYSTATION_INCOME_BONUS = 1
STANDING_ORDERS_COST_MULTIPLIER = 0.8
LAB_AUTOMATION_RESEARCH_MULTIPLIER = 1.2
AUTO_BALANCERS_RECOVERY_MULTIPLIER = 1.2
FRONTIER_GRANTS_INVEST_COST = 45
SETTLER_GUILDS_DECAY_MULTIPLIER = 0.9
CHARTER_COLONIES_DEVELOPMENT_THRESHOLD = 85.0
GUILD_STANDING_FIRST_OFFER_TICKS = 15
GUILD_STANDING_COOLDOWN_TICKS = 45
COLONIAL_GOODWILL_START_BONUS = 0.1
TRUSTED_NAME_REWARD_MULTIPLIER = 1.15

# O-4 -- the opt-in harder charter (SOL's New Game+ Challenge shape: a
# tougher run, not a bonus-boosted easier one). Faster market saturation
# and quicker-fading colony needs; the reward is one extra charter point.
HARD_CHARTER_SATURATION_MULTIPLIER = 1.5
HARD_CHARTER_DECAY_MULTIPLIER = 1.35

# O-2 -- founding conditions: from the second charter on, a saved seed picks
# which two home colonies start thriving and connected (ships 1 and 2 begin
# docked at them) and what each specialises in; every other home colony
# begins stretched, so the first logistics bottleneck moves around.
FOUNDING_THRIVING_NEED = 0.8
FOUNDING_STRETCHED_NEED = 0.35
FOUNDING_FOCI = {
    "bulk": {"label": "Bulk exporter", "output": 1.15, "decay": 1.0},
    "steady": {"label": "Steady settlement", "output": 1.0, "decay": 0.7},
}
FOUNDING_SEED_MAX = 2**31 - 1
founding_seed = 0  # 0 = the standard first charter
charter_rng = random.Random()  # tests replace it with a seeded one

LEDGER_MAX = 10_000_000_000
CHARTER_COUNT_MAX = 100_000
CHARTER_VETERAN_COUNT = 3  # renewals for the Charter Veteran achievement

charters_completed = 0
charter_points_earned = 0
charter_perks = set()
hard_charter_active = False  # this charter was begun as a harder charter
hard_charter_next = False  # the player's pending choice for the next renewal
# O-3 -- lifetime ledger. Totals persist across renewals (found_new_corporation
# carries them over the reset); ledger_routes_seen is the current charter's
# set of distinct routes, so a route counts once per charter.
ledger_units_moved = 0
ledger_routes_established = 0
ledger_hard_completed = 0
ledger_routes_seen = set()
# J-14 -- units delivered in the CURRENT charter (the ledger above is
# lifetime), and the career log: one entry per completed charter, newest last.
ledger_charter_units = 0
charter_career = []
CAREER_MAX_ENTRIES = 40
# J-14 -- the crest shown beside the title: a shape plus a text label (never
# colour only), chosen by how many charters have been completed.
CREST_TIERS = (
    (10, "Sovereign", "\u2605"),
    (5, "Master", "\u25c6"),
    (3, "Veteran", "\u25a0"),
    (1, "Renewed", "\u25b2"),
    (0, "Founder", "\u25cf"),
)


def crest_for(completed):
    """(label, glyph) of the crest earned by `completed` finished charters."""
    for minimum, label, glyph in CREST_TIERS:
        if completed >= minimum:
            return label, glyph
    return CREST_TIERS[-1][1], CREST_TIERS[-1][2]


def charter_crest():
    """(label, glyph) of the active charter's crest."""
    return crest_for(charters_completed)


def charter_crest_text():
    label, glyph = charter_crest()
    return (
        f"{glyph} {label}" + (" (harder)" if hard_charter_active else "")
        + (" \u25d0 Dark run" if records["dark_runs"] else "")  # J-30: the badge by the title
    )


def charter_perk(perk_id):
    return perk_id in charter_perks


def charter_points_spent():
    return sum(CHARTER_PERKS[perk_id]["cost"] for perk_id in charter_perks)


def charter_points_available():
    return charter_points_earned - charter_points_spent()


def charter_perk_missing_requirements(perk_id):
    return [r for r in CHARTER_PERKS[perk_id]["requires"] if r not in charter_perks]


def can_buy_charter_perk(perk_id):
    if not isinstance(perk_id, str) or perk_id not in CHARTER_PERKS or perk_id in charter_perks:
        return False
    if charter_perk_missing_requirements(perk_id):
        return False
    return charter_points_available() >= CHARTER_PERKS[perk_id]["cost"]


def buy_charter_perk(perk_id):
    if not can_buy_charter_perk(perk_id):
        return False
    charter_perks.add(perk_id)
    _apply_founding_perk(perk_id)
    return True


def _apply_founding_perk(perk_id):
    """Founding perks act on the world once (at a renewal, or the moment they
    are bought). Everything else is a live modifier read where it applies."""
    if perk_id == "standing_convoy":
        ship = ships["1"]
        if ship.purchased and not ship.automated and automation_slots_available():
            ship.automated = True
    elif perk_id == "colonial_goodwill":
        for colony_id in COLONIES:
            state = colony_states.get(colony_id)
            if state is not None:
                state.need_satisfaction = min(1.0, state.need_satisfaction + COLONIAL_GOODWILL_START_BONUS)


# --- perk-aware values (each equals its plain constant when no perk applies) ---
def automation_cost():
    if charter_perk("standing_orders"):
        return int(round(AUTOMATION_COST * STANDING_ORDERS_COST_MULTIPLIER))
    return AUTOMATION_COST


def colony_invest_cost():
    return FRONTIER_GRANTS_INVEST_COST if charter_perk("frontier_grants") else COLONY_INVEST_COST


def trade_post_cost():
    if charter_perk("waystation_network"):
        return int(round(TRADE_POST_COST * WAYSTATION_COST_MULTIPLIER))
    return TRADE_POST_COST


def trade_post_income_each():
    return TRADE_POST_INCOME_PER_TICK + (WAYSTATION_INCOME_BONUS if charter_perk("waystation_network") else 0)


def development_threshold():
    return CHARTER_COLONIES_DEVELOPMENT_THRESHOLD if charter_perk("charter_colonies") else DEVELOPMENT_THRESHOLD


def guild_first_offer_ticks():
    return GUILD_STANDING_FIRST_OFFER_TICKS if charter_perk("guild_standing") else GUILD_FIRST_OFFER_TICKS


def guild_cooldown_ticks():
    return GUILD_STANDING_COOLDOWN_TICKS if charter_perk("guild_standing") else GUILD_COOLDOWN_TICKS


def guild_reward_multiplier():
    return GUILD_REWARD_MULTIPLIER * (TRUSTED_NAME_REWARD_MULTIPLIER if charter_perk("trusted_name") else 1.0)


def founding_from_seed(seed):
    """Deterministic founding conditions for a saved seed: the two home
    colonies that start thriving and connected, and each one's focus."""
    rng = random.Random(seed)
    order = list(COLONIES)
    pair = sorted(rng.sample(order, 2), key=order.index)
    foci = {colony_id: rng.choice(list(FOUNDING_FOCI)) for colony_id in pair}
    return {"pair": pair, "foci": foci}


def founding_focus(colony_id):
    """The founding focus key for a colony in the current charter, or None."""
    if not founding_seed:
        return None
    return founding_from_seed(founding_seed)["foci"].get(colony_id)


def founding_output_multiplier(colony_id):
    focus = founding_focus(colony_id)
    return FOUNDING_FOCI[focus]["output"] if focus else 1.0


def charter_decay_multiplier(colony_id):
    """Everything that scales how fast a colony's need fades, in one place."""
    multiplier = 1.0
    if hard_charter_active:
        multiplier *= HARD_CHARTER_DECAY_MULTIPLIER
    if charter_perk("settler_guilds"):
        multiplier *= SETTLER_GUILDS_DECAY_MULTIPLIER
    focus = founding_focus(colony_id)
    if focus:
        multiplier *= FOUNDING_FOCI[focus]["decay"]
    return multiplier


def apply_founding_conditions():
    """Called once, right after a renewal reset: rolls a fresh seed, sets the
    thriving pair against the stretched rest, docks ships 1 and 2 at the pair
    and applies any founding perks."""
    global founding_seed
    founding_seed = charter_rng.randrange(1, FOUNDING_SEED_MAX + 1)
    info = founding_from_seed(founding_seed)
    for colony_id in COLONIES:
        state = colony_states.get(colony_id)
        if state is not None:
            state.need_satisfaction = FOUNDING_THRIVING_NEED if colony_id in info["pair"] else FOUNDING_STRETCHED_NEED
    ships["1"].location = info["pair"][0]
    ships["2"].location = info["pair"][1]
    for perk_id in sorted(charter_perks):
        if CHARTER_PERKS[perk_id].get("founding"):
            _apply_founding_perk(perk_id)


def founding_summary_text():
    if not founding_seed:
        return "Founding conditions: the standard opening. From your second charter on, each one starts differently."
    info = founding_from_seed(founding_seed)
    a, b = info["pair"]
    parts = ", ".join(
        f"{ALL_COLONIES[cid]['name']} is a {FOUNDING_FOCI[info['foci'][cid]]['label'].lower()}" for cid in info["pair"]
    )
    return (
        f"Founding conditions: {ALL_COLONIES[a]['name']} and {ALL_COLONIES[b]['name']} start thriving and connected "
        f"(Ships 1 and 2 begin docked there); {parts}. The other home colonies start stretched."
    )


def hard_charter_unlocked():
    """Available from the first endgame onward, never before it."""
    return endgame_reached or charters_completed > 0


def set_hard_charter_next(enabled):
    global hard_charter_next
    if not hard_charter_unlocked():
        return False
    hard_charter_next = bool(enabled)
    return True


def charter_points_for_next_renewal():
    return CHARTER_POINTS_PER_RENEWAL + (HARD_CHARTER_BONUS_POINTS if hard_charter_active else 0)


def ledger_record_sale(qty, route_key):
    """O-3: called for every completed, undisrupted delivery."""
    global ledger_units_moved, ledger_routes_established, ledger_charter_units
    ledger_units_moved = min(LEDGER_MAX, ledger_units_moved + max(0, int(qty)))
    ledger_charter_units = min(LEDGER_MAX, ledger_charter_units + max(0, int(qty)))
    if route_key and route_key not in ledger_routes_seen:
        ledger_routes_seen.add(route_key)
        ledger_routes_established = min(LEDGER_MAX, ledger_routes_established + 1)


def charter_summary_text():
    if not charters_completed and not charter_perks:
        return "Charter: not yet renewed."
    hard = " (harder charter)" if hard_charter_active else ""
    return (
        f"Charter: {charters_completed} renewed, {charter_points_available()} charter points to spend, "
        f"{len(charter_perks)}/{len(CHARTER_PERKS)} perks{hard}."
    )


def endgame_criteria_met():
    """"Fully automated fleet" means every automation slot the player
    has unlocked is filled, not literally every ship -- the automation
    slot cap (currently 2, or 3 with its own research node) is well
    below the 4-ship roster, so requiring all 4 would make this
    unreachable."""
    return (
        automated_ship_count() >= max_automated_ships()
        and fleet_priority_enabled
        and galaxy_expansion_unlocked()
    )


def background_world_count():
    return min(ENDGAME_BACKGROUND_WORLD_CAP, ENDGAME_BACKGROUND_WORLDS_PER_TICK * ticks_since_endgame)


def background_revenue_this_tick():
    return round(background_world_count() * ENDGAME_BACKGROUND_REVENUE_PER_WORLD)


def sell_summary(good, qty, profit, colony_id):
    colony_name = ALL_COLONIES[colony_id]["name"]
    return f"Sold {qty} {GOOD_LABEL[good]} at {colony_name} for {profit} credits."


def ship_status_text(ship):
    if ship.in_transit:
        dest_name = ALL_COLONIES[ship.destination]["name"]
        prefix = "Automated — in transit" if ship.automated else "In transit"
        return f"{prefix} to {dest_name} — {ship.transit_ticks_remaining} tick(s) remaining."
    colony = ALL_COLONIES[ship.location]
    if ship.automated:
        return f"Automated — docked at {colony['name']}, running its route on its own."
    if ship.loaded:
        return f"Docked at {colony['name']}, loaded with {ship.cargo_qty} {GOOD_LABEL[ship.cargo_good]}. Choose a destination."
    base = f"Docked at {colony['name']}. Load {GOOD_LABEL[colony['produces']]} to prepare a run."
    if ship.idle_ticks >= IDLE_WARNING_TICKS:
        base += f" ⚠️ Idle for {ship.idle_ticks} ticks — consider loading it or automating this route."
    return base


def _render_unpurchased_ship(ship):
    """J6 — ship 5/6 before their one-time purchase: every normal control
    stays hidden, replaced by a single purchase button + status line."""
    document.getElementById(f"ship-{ship.id}-status").innerText = (
        f"Not yet purchased — {SHIP_PURCHASE_COST[ship.id]} credits to add it to the fleet."
    )
    document.getElementById(f"ship-{ship.id}-load-button").hidden = True
    document.getElementById(f"ship-{ship.id}-automate-button").hidden = True
    for colony_id in ALL_COLONIES:
        document.getElementById(f"ship-{ship.id}-depart-{colony_id}-button").hidden = True

    archetype_select = document.getElementById(f"ship-{ship.id}-archetype-select")
    if archetype_select is not None:
        archetype_select.hidden = False
    purchase_button = document.getElementById(f"ship-{ship.id}-purchase-button")
    purchase_button.hidden = False
    purchase_button.innerText = f"Purchase Ship ({SHIP_PURCHASE_COST[ship.id]})"
    purchase_button.disabled = not can_purchase_ship(ship.id)


def render_ship(ship):
    label_text = ship.name
    if ship.archetype != DEFAULT_ARCHETYPE:
        label_text += f" ({archetype_for(ship)['label']})"
    if ship.purchased and ship.is_veteran:
        label_text += " ★ Veteran hauler"  # J14
    label_el = document.getElementById(f"ship-{ship.id}-label")
    label_el.innerText = label_text
    label_el.title = (
        f"{ship.round_trips} round trips on the same route (veteran at {VETERAN_ROUND_TRIPS})."
        if ship.purchased else ""
    )

    if ship.id in PURCHASABLE_SHIP_IDS:
        purchase_button = document.getElementById(f"ship-{ship.id}-purchase-button")
        if not ship.purchased:
            _render_unpurchased_ship(ship)
            return
        purchase_button.hidden = True
        archetype_select = document.getElementById(f"ship-{ship.id}-archetype-select")
        if archetype_select is not None:
            archetype_select.hidden = True

    status_el = document.getElementById(f"ship-{ship.id}-status")
    status_el.innerText = ship_status_text(ship)
    # J15 — a manual ship left idle and empty for a long stretch gets a
    # distinct status style, a nudge that's easy to miss in a wall of
    # otherwise-identical "docked, nothing loaded" panels.
    idle_warning = not ship.automated and ship.idle_ticks >= IDLE_WARNING_TICKS
    status_el.className = "ship-status ship-status--idle-warning" if idle_warning else "ship-status"

    load_button = document.getElementById(f"ship-{ship.id}-load-button")
    load_button.hidden = ship.automated
    load_button.disabled = ship.automated or not (ship.docked and not ship.loaded)

    reachable = active_colony_ids()
    for colony_id in ALL_COLONIES:
        depart_button = document.getElementById(f"ship-{ship.id}-depart-{colony_id}-button")
        applicable = (
            ship.docked and ship.loaded and colony_id != ship.location and colony_id in reachable
        )
        depart_button.hidden = ship.automated or not applicable
        depart_button.disabled = ship.automated or not applicable

    automate_button = document.getElementById(f"ship-{ship.id}-automate-button")
    automate_button.hidden = False
    # J18 — automation is a one-time, permanent choice per ship.
    automate_button.title = (
        f"Automating costs {automation_cost()} credits and is permanent: "
        "there is no way to de-automate a ship afterward."
    )
    if ship.automated:
        automate_button.innerText = "Automated"
        automate_button.disabled = True
    else:
        automate_button.innerText = f"Automate ({automation_cost()})"
        automate_button.disabled = not automation_slots_available() or total_profit < automation_cost()


def render_colony(colony_id):
    colony = ALL_COLONIES[colony_id]
    state = colony_states[colony_id]
    need_text = (
        f"{colony['name']}: needs {GOOD_LABEL[colony['needs']]} — "
        f"{state.need_satisfaction * 100:.0f}% satisfied"
    )
    if state.is_developed():
        need_text += (
            f"; also needs {GOOD_LABEL[state.secondary_need()]} — "
            f"{state.secondary_need_satisfaction * 100:.0f}% satisfied"
        )
    need_text += f" (output x{state.output_multiplier():.2f})"
    document.getElementById(f"colony-{colony_id}-need-display").innerText = need_text
    document.getElementById(f"colony-{colony_id}-need-bar").style.width = (
        f"{state.need_satisfaction * 100:.0f}%"
    )
    # J14 — a need-satisfaction-over-time sparkline alongside the meter.
    document.getElementById(f"colony-{colony_id}-need-sparkline").innerHTML = _trend_sparkline_svg(
        need_history.get(colony_id, []), "need-sparkline"
    ) if blackout_has("feed") else ""
    # J24 — a plain "needs met" average alongside the graph.
    hist = need_history.get(colony_id, [])
    if hist and blackout_has("feed"):
        avg_pct = sum(hist) / len(hist) * 100
        document.getElementById(f"colony-{colony_id}-need-sparkline").innerHTML += (
            f'<span class="sparkline-pct" title="Average need satisfaction over the last '
            f'{len(hist)} ticks">avg {avg_pct:.0f}%</span>'
        )

    dev_el = document.getElementById(f"colony-{colony_id}-development-display")
    if state.is_developed():
        spec = SPECIALIZATION[colony_id]
        dev_el.innerText = f"Development: Level 2 — {spec['name']} ({spec['description']})"
    else:
        dev_el.innerText = (
            f"Development: Level 1 ({state.cumulative_delivered:.0f}/{development_threshold():.0f} "
            f"{GOOD_LABEL[colony['needs']]} delivered to develop further)"
        )
    demand_el = document.getElementById(f"colony-{colony_id}-demand-display")
    concede_button = document.getElementById(f"colony-{colony_id}-concede-button")
    if demand_el is not None and concede_button is not None:
        demanding = state.has_demand()
        demand_el.hidden = not demanding
        concede_button.hidden = not demanding
        if demanding:
            demand_el.innerText = (
                f"{colony['name']} feels neglected and asks for a concession: {CONCESSION_COST} credits "
                f"to restore {int(state.concession_boost() * 100)}% satisfaction "
                f"({state.demand_ticks_left} tick(s) left; ignoring it costs nothing)."
            )
            concede_button.innerText = f"Grant concession ({CONCESSION_COST})"
            concede_button.disabled = not can_grant_concession(colony_id)
    invest_button = document.getElementById(f"colony-{colony_id}-invest-button")
    if invest_button is not None:
        invest_button.hidden = state.is_developed()
        invest_button.innerText = f"Invest ({colony_invest_cost_for(colony_id)})"
        invest_button.disabled = not can_invest_in_colony(colony_id)
        invest_button.title = (
            f"Spend {colony_invest_cost_for(colony_id)} credits to add {COLONY_INVEST_UNITS} units of development progress "
            f"({COLONY_INVEST_UNITS / development_threshold() * 100:.0f}% of Level 2)."
        )
    mood_el = document.getElementById(f"colony-{colony_id}-temperament")
    if mood_el is not None:
        mood_el.innerText = temperament_text(colony_id)


def temperament_text(colony_id):
    """J-25/J-26 -- the colony panel's one-line explanation of its mood."""
    state = colony_states[colony_id]
    mood = TEMPERAMENTS[state.temperament()]
    return (
        f"Mood: {TEMPERAMENT_MARK[mood['glyph']]} {mood['label']} ({mood['glyph']} on the map): {mood['why']}. "
        f"History: {state.cumulative_delivered:.0f} delivered, {state.concessions_granted} concession(s) granted, "
        f"{state.lapsed_demands()} demand(s) unanswered."
    )


def render_needs_strip():
    """Mobile-dock companion to #colonies-panel (see style.css) -- one
    compact chip per colony with just enough to pick a depart
    destination without scrolling back up to the full colonies panel:
    which good it needs and how satisfied that need currently is. A
    colony's chip stays hidden until its ColonyState exists, the same
    gate render()'s main loop already uses for colony_states."""
    for colony_id in ALL_COLONIES:
        chip = document.getElementById(f"mobile-needs-strip-{colony_id}")
        state = colony_states.get(colony_id)
        chip.hidden = state is None
        if state is None:
            continue
        colony = ALL_COLONIES[colony_id]
        chip.innerText = (
            f"{colony_map_label(colony_id)}: needs {GOOD_LABEL[colony['needs']]} "
            f"{state.need_satisfaction * 100:.0f}%"
        )


SPARKLINE_WIDTH = 60
SPARKLINE_HEIGHT = 18


def _trend_sparkline_svg(history, css_class, now_label=None, ghost=None, ghost_label=None):
    """J12/J14 — an unlabeled inline-SVG polyline over a short rolling
    history; the point is the shape of the trend, not any exact value.
    Values are expected roughly in 0..1 (market multiplier, need
    satisfaction) so a fixed height mapping is enough -- no separate
    axis scaling needed. J-4: `ghost` (a 0..1 value) adds a dashed
    horizontal "price memory" line at that level."""
    if len(history) < 2:
        return ""
    n = len(history)
    points = []
    for i, value in enumerate(history):
        x = (i / (n - 1)) * SPARKLINE_WIDTH
        y = SPARKLINE_HEIGHT - max(0.0, min(1.0, value)) * SPARKLINE_HEIGHT
        points.append(f"{x:.1f},{y:.1f}")
    # J4 — an explicit, labeled marker on the most recent point.
    marker = ""
    if now_label:
        last_x, last_y = points[-1].split(",")
        marker = (
            f'<circle cx="{last_x}" cy="{last_y}" r="2" class="sparkline-now">'
            f"<title>{now_label}</title></circle>"
        )
    ghost_line = ""
    if ghost is not None:
        gy = SPARKLINE_HEIGHT - max(0.0, min(1.0, ghost)) * SPARKLINE_HEIGHT
        ghost_line = (
            f'<line x1="0" y1="{gy:.1f}" x2="{SPARKLINE_WIDTH}" y2="{gy:.1f}" class="sparkline-ghost" '
            f'stroke-dasharray="3 2"><title>{ghost_label or "Price before your last stockpile trade"}</title></line>'
        )
    return (
        f'<svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}" class="{css_class}" '
        f'aria-hidden="{"false" if now_label else "true"}">{ghost_line}<polyline points="{" ".join(points)}" />{marker}</svg>'
    )


def price_memory_text(good):
    """J-4 -- the text twin of the ghost line (the line is dashed, never colour only)."""
    if good not in price_memory:
        return ""
    return (
        f"dashed line: {price_memory[good] * 100:.0f}% of baseline before your last stockpile trade "
        f"(now {market_multiplier[good] * 100:.0f}%)"
    )


# J27 — a trade almanac: a static-ish reference of each good's baseline
# price, the range the market can push it through, and which colony makes
# it and which needs it. Only goods from systems the player can reach are
# listed, so it never spoils the systems that are still locked.
def _system_label_for_colony(colony_id):
    if colony_id in COLONIES:
        return "Home system"
    if colony_id in EXPANSION_COLONIES:
        return "Kepler Cluster"
    if colony_id in RIFT_COLONIES:
        return "Rift Colonies"
    return "Umbral Deep"


def almanac_rows():
    rows = []
    reachable = set(active_colony_ids())
    for good, base in SELL_PRICE.items():
        producer = colony_producing(good)
        consumer = colony_needing(good)
        if producer not in reachable:
            continue
        rows.append({
            "good": GOOD_LABEL[good],
            "base": base,
            "low": round(base * MIN_PRICE_MULTIPLIER, 1),
            "high": round(base * MAX_PRICE_MULTIPLIER, 1),
            "made_by": ALL_COLONIES[producer]["name"],
            "needed_by": ALL_COLONIES[consumer]["name"] if consumer else "nobody",
            "system": _system_label_for_colony(producer),
        })
    return rows


def render_almanac():
    body = document.getElementById("almanac-body")
    if body is None:
        return
    lines = [
        "<table class=\"almanac-table\"><thead><tr><th>Good</th><th>Base</th>"
        "<th>Typical range</th><th>Made by</th><th>Needed by</th></tr></thead><tbody>"
    ]
    for row in almanac_rows():
        lines.append(
            f"<tr><td>{row['good']}</td><td>{row['base']}</td>"
            f"<td>{row['low']:g}\u2013{row['high']:g}</td>"
            f"<td>{row['made_by']} <span class=\"almanac-system\">({row['system']})</span></td>"
            f"<td>{row['needed_by']}</td></tr>"
        )
    lines.append("</tbody></table>")
    body.innerHTML = "".join(lines)


def on_toggle_seasonal_demand(event=None):
    global seasonal_demand_enabled
    seasonal_demand_enabled = not seasonal_demand_enabled
    render_market()


def on_toggle_route_hazards(event=None):
    global route_hazards_enabled
    if sandbox_active:  # Z-18: no lost cargo in the sandbox
        route_hazards_enabled = False
        render_market()
        return
    route_hazards_enabled = not route_hazards_enabled
    render_market()


def on_toggle_route_insurance(event=None):
    global route_insurance_enabled
    route_insurance_enabled = not route_insurance_enabled
    render_market()


def on_build_trade_post(event=None):
    build_trade_post()
    render_market()


def render_trade_post():
    button = document.getElementById("trade-post-button")
    status = document.getElementById("trade-post-status")
    if button is None or status is None:
        return
    show = automation_is_maxed() or bool(trade_posts)
    button.hidden = not show
    status.hidden = not show
    if not show:
        return
    target = next_trade_post_system()
    button.innerText = f"Establish trade post ({trade_post_cost()})" if target else "All trade posts established"
    button.disabled = not can_build_trade_post()
    button.title = (
        f"Build a post in the {target}: +{trade_post_income_each()} credits per tick, no ship needed."
        if target else "Every reachable system already has a trade post."
    )
    posts = ", ".join(trade_posts) if trade_posts else "none yet"
    status.innerText = (
        f"Trade posts: {posts} (+{trade_post_income_per_tick()} credits per tick). "
        f"Available once every automation slot is in use; one per system."
    )


def render_route_hazards():
    hazards_button = document.getElementById("route-hazards-toggle-button")
    insurance_button = document.getElementById("route-insurance-toggle-button")
    status = document.getElementById("route-hazards-status")
    if hazards_button is None or insurance_button is None or status is None:
        return
    hazards_button.innerText = f"Route hazards: {'on' if route_hazards_enabled else 'off'}"
    insurance_button.innerText = f"Route insurance: {'on' if route_insurance_enabled else 'off'}"
    insurance_button.disabled = not route_hazards_enabled
    if not route_hazards_enabled:
        status.innerText = (
            f"Optional: with hazards on, {int(ROUTE_HAZARD_CHANCE * 100)}% of loaded arrivals are disrupted "
            "and the cargo is lost. Insurance is then available."
        )
        return
    line = (
        f"Hazards on: {int(ROUTE_HAZARD_CHANCE * 100)}% of loaded arrivals are disrupted. "
        f"Insurance costs {INSURANCE_PREMIUM_PER_TICK} credit per ship in transit per tick and refunds "
        f"{int(INSURANCE_COVERAGE * 100)}% of a lost trip. "
    )
    line += f"So far: {disruptions_suffered} disrupted, {insurance_payouts} paid out, {premiums_paid} in premiums."
    status.innerText = line


def render_diplomacy():
    status = document.getElementById("diplomacy-status")
    if status is None:
        return
    if not galaxy_expansion_unlocked():
        status.hidden = True
        return
    status.hidden = False
    level = diplomacy_level()
    to_next = diplomacy_units_to_next_level()
    bonus = int(round((diplomacy_multiplier() - 1.0) * 100))
    line = f"Diplomatic relations: level {level} of {len(DIPLOMACY_THRESHOLDS)} (+{bonus}% on every sale)."
    line += f" Deliver {to_next} more unit(s) between systems for the next level." if to_next else " Fully established."
    status.innerText = line


def render_seasonal_demand():
    button = document.getElementById("seasonal-demand-toggle-button")
    status = document.getElementById("seasonal-demand-status")
    if button is None or status is None:
        return
    button.innerText = f"Seasonal demand: {'on' if seasonal_demand_enabled else 'off'}"
    if not seasonal_demand_enabled:
        status.innerText = (
            f"Optional: every {SEASON_LENGTH_TICKS} ticks two goods are in demand and sell for "
            f"{int(SEASONAL_DEMAND_BONUS * 100)}% more. Nothing is ever marked down."
        )
        return
    number, left, hot, upcoming = seasonal_status()
    names = lambda goods: " and ".join(GOOD_LABEL[g] for g in goods)  # noqa: E731
    status.innerText = (
        f"Season {number}: {names(hot)} in demand (+{int(SEASONAL_DEMAND_BONUS * 100)}%) for "
        f"{left} more tick(s). Next: {names(upcoming)}."
    )


def render_market():
    render_trade_post()
    render_route_hazards()
    render_diplomacy()
    render_seasonal_demand()
    render_almanac()
    for good in market_multiplier:
        price = current_sell_price(good)
        pct = market_multiplier[good] * 100
        display = document.getElementById(f"market-{good}-display")
        if blackout_has("feed"):
            line = f"{GOOD_LABEL[good]}: {price} credits/unit ({pct:.0f}% of baseline)"
        else:  # J-29: Blackout, the price feed is dark -- a range and a coarse bar, no exact number
            low, high = blackout_price_range(price)
            line = f"{GOOD_LABEL[good]}: about {low}-{high} credits/unit (price feed dark)"
        if seasonal_multiplier(good) > 1.0:
            line += f" · in demand (+{int(SEASONAL_DEMAND_BONUS * 100)}%)"
        display.innerText = line
        display.className = "market-price"
        display.title = ""
        if market_multiplier[good] < 0.7 and blackout_has("feed"):
            display.className += " market-price--crashed"
            # J20 — recovery ETA back to baseline at the flat per-tick rate
            # (further sales of this good would push it back down).
            eta = math.ceil(round((MAX_PRICE_MULTIPLIER - market_multiplier[good])
                                  / MARKET_PRICE_RECOVERY_PER_TICK, 6))
            display.title = (
                f"Crashed: about {eta} tick(s) to recover to baseline if nothing "
                f"more of it is sold."
            )
        buy_button = document.getElementById(f"stockpile-{good}-buy-button")
        if buy_button is not None:
            sell_button = document.getElementById(f"stockpile-{good}-sell-button")
            status = document.getElementById(f"stockpile-{good}-status")
            buy_button.disabled = not can_stockpile_buy(good)
            buy_button.innerText = f"Buy {STOCKPILE_LOT}"
            sell_button.disabled = stockpile[good] <= 0
            status.innerText = (
                f"Stockpile {stockpile[good]}/{STOCKPILE_CAPACITY}"
                + (f" (sells for {stockpile_sale_value(good)} after the {int(STOCKPILE_SELL_FEE * 100)}% fee)" if stockpile[good] else "")
            )
        document.getElementById(f"market-{good}-bar").style.width = (
            f"{pct:.0f}%" if blackout_has("feed") else f"{blackout_bar_percent(pct)}%"
        )
        # J12 — a small price-history sparkline alongside the bar.
        memory_note = price_memory_text(good)
        sparkline_html = _trend_sparkline_svg(
            price_history.get(good, []), "price-sparkline", f"Now: {price} credits",
            ghost=price_memory.get(good), ghost_label=memory_note or None,
        ) if blackout_has("feed") else ""
        if memory_note and sparkline_html:
            sparkline_html += f'<span class="sparkline-pct price-memory-note">{memory_note}</span>'
        document.getElementById(f"market-{good}-sparkline").innerHTML = sparkline_html


def render_research():
    document.getElementById("research-points-display").innerText = (
        f"Research points: {research_points:.0f}"
    )
    for node_id, node in RESEARCH_NODES.items():
        status_el = document.getElementById(f"research-{node_id}-status")
        unlock_button = document.getElementById(f"research-{node_id}-unlock-button")
        if node_id in unlocked_research:
            status_el.innerText = f"{node['label']} — unlocked ({node['description']})"
            unlock_button.hidden = True
        else:
            status_text = f"{node['label']} — {node['description']}"
            requires = node.get("requires")
            # Onboarding-tooltip audit (planning/TODO.md, origin A14): the
            # static index.html placeholder text used to state a node's
            # prerequisite ("requires Automation Expansion"/"requires Galaxy
            # Expansion") before Pyodide finished loading, but render()
            # replaced it with RESEARCH_NODES["description"], which never
            # mentioned the prereq at all -- so a returning player with
            # plenty of research points but a missing prerequisite saw the
            # unlock button disabled with no stated reason anywhere
            # permanent. Restate it here, matching Aftermath's own
            # missing-prereq status-text pattern, so it survives every
            # render rather than only the pre-Python placeholder.
            # Build the text in a local and assign once: reading innerText
            # back from an element inside a collapsed <details> returns ""
            # in a real browser, so `innerText += ...` would wipe the label.
            if requires is not None and requires not in unlocked_research:
                status_text += f" (requires {RESEARCH_NODES[requires]['label']})"
            closed_by = research_node_blocked_by(node_id)
            if closed_by is not None:
                status_text += f" (closed: you chose {RESEARCH_NODES[closed_by]['label']})"
            status_el.innerText = status_text
            unlock_button.hidden = False
            unlock_button.innerText = f"Research ({node['cost']})"
            unlock_button.disabled = not can_unlock_research(node_id)
            # J26 — say exactly what a locked node still needs.
            needs = []
            if requires is not None and requires not in unlocked_research:
                needs.append(f"unlock {RESEARCH_NODES[requires]['label']} first")
            if research_points < node["cost"]:
                needs.append(f"{node['cost'] - research_points:.0f} more research points")
            if closed_by is not None:
                unlock_button.title = f"Closed by your choice of {RESEARCH_NODES[closed_by]['label']}."
            else:
                unlock_button.title = ("Still needed: " + " and ".join(needs)) if needs else "Ready to unlock."


def render_fleet_priority():
    button = document.getElementById("fleet-priority-button")
    button.innerText = f"Fleet Priority: {'ON' if fleet_priority_enabled else 'OFF'}"
    button.disabled = False
    status = document.getElementById("fleet-priority-status")
    if fleet_priority_enabled:
        status.innerText = (
            "Idle automated ships abandon their home shuttle and reposition empty "
            "toward whichever producer feeds the fleet's most under-served colony."
        )
    else:
        status.innerText = "Automated ships stick to their fixed shuttle route."


def render_endgame():
    panel = document.getElementById("endgame-panel")
    panel.hidden = not endgame_reached
    if not endgame_reached:
        document.getElementById("found-new-corporation-button").hidden = True
        document.getElementById("hard-charter-toggle-button").hidden = True
        return
    worlds = background_world_count()
    document.getElementById("endgame-message-display").innerText = (
        "A fully automated fleet, running on Fleet Priority, spanning two systems — "
        "the pattern you built is spreading. This is a soft finish line, not a stop: "
        "the sandbox keeps running for as long as you want to keep watching it."
    )
    document.getElementById("endgame-worlds-display").innerText = (
        f"{worlds:,} worlds beyond your own fleet have adopted the pattern, trading "
        f"quietly among themselves — {background_revenue_this_tick()} credits/tick "
        f"in background revenue."
    )
    document.getElementById("legacy-display").innerText = legacy_summary_text()
    document.getElementById("found-new-corporation-button").hidden = not can_found_new_corporation()
    _render_renewal_options()
    render_endgame_galaxy(worlds)


# J20 — a visual flourish on the background galaxy: a small canvas that
# actually grows a scattering of dots as background_world_count() climbs,
# rather than the number alone standing in for "a growing galaxy." A
# fixed golden-angle spiral keeps the scatter stable frame to frame
# (no jitter) without needing to store per-dot state anywhere.
ENDGAME_GALAXY_CANVAS_SIZE = 140
ENDGAME_GALAXY_DOT_CAP = 200
GOLDEN_ANGLE_RADIANS = 2.399963


def endgame_galaxy_dot_position(i):
    """Canvas position of dot `i`, or None when the spiral has drifted
    off the canvas (those dots are simply not drawn)."""
    center = ENDGAME_GALAXY_CANVAS_SIZE / 2
    angle = i * GOLDEN_ANGLE_RADIANS
    radius = 3 + 4.6 * math.sqrt(i)
    cx = center + radius * math.cos(angle)
    cy = center + radius * math.sin(angle)
    if 0 <= cx <= ENDGAME_GALAXY_CANVAS_SIZE and 0 <= cy <= ENDGAME_GALAXY_CANVAS_SIZE:
        return cx, cy
    return None


# J16 — hovering the galaxy canvas names the nearest drawn dot. The dots
# are decoration standing in for the abstracted background worlds, so the
# tooltip says so honestly rather than inventing per-world data.
ENDGAME_GALAXY_HOVER_RADIUS = 5
ENDGAME_GALAXY_DEFAULT_TITLE = "The background galaxy: each dot is one of the worlds that trickle in passive revenue."


def endgame_galaxy_hover_text(x, y, worlds):
    best_index = None
    best_distance = ENDGAME_GALAXY_HOVER_RADIUS
    for i in range(min(ENDGAME_GALAXY_DOT_CAP, worlds)):
        position = endgame_galaxy_dot_position(i)
        if position is None:
            continue
        distance = math.hypot(position[0] - x, position[1] - y)
        if distance <= best_distance:
            best_index, best_distance = i, distance
    if best_index is None:
        return ENDGAME_GALAXY_DEFAULT_TITLE
    return (
        f"Background world #{best_index + 1} of {worlds:,}: part of the growing galaxy "
        "that trickles in passive revenue (decorative dot; the galaxy is abstracted)."
    )


_galaxy_hover_wired = False


def _wire_endgame_galaxy_hover(canvas):
    global _galaxy_hover_wired
    if _galaxy_hover_wired:
        return
    _galaxy_hover_wired = True

    def on_move(event):
        scale = ENDGAME_GALAXY_CANVAS_SIZE / (getattr(canvas, "clientWidth", 0) or ENDGAME_GALAXY_CANVAS_SIZE)
        x = float(getattr(event, "offsetX", -100)) * scale
        y = float(getattr(event, "offsetY", -100)) * scale
        canvas.title = endgame_galaxy_hover_text(x, y, background_world_count())

    canvas.addEventListener("mousemove", create_proxy(on_move))


def render_endgame_galaxy(worlds):
    canvas = document.getElementById("endgame-galaxy-canvas")
    if canvas is None:
        return
    _wire_endgame_galaxy_hover(canvas)
    canvas.title = ENDGAME_GALAXY_DEFAULT_TITLE
    ctx = canvas.getContext("2d")
    ctx.clearRect(0, 0, ENDGAME_GALAXY_CANVAS_SIZE, ENDGAME_GALAXY_CANVAS_SIZE)
    ctx.fillStyle = FLEET_PRIORITY_TARGET_COLOR
    dot_count = min(ENDGAME_GALAXY_DOT_CAP, worlds)
    for i in range(dot_count):
        position = endgame_galaxy_dot_position(i)
        if position is not None:
            ctx.beginPath()
            ctx.arc(position[0], position[1], 1.6, 0, 2 * math.pi)
            ctx.fill()


# ===========================================================================
# Achievements (planning/ACHIEVEMENTS-SYSTEM-DESIGN.md) — SOL is the
# reference integration for the hub-wide achievements framework; this is
# Trade Empire's own catalog, grounded in its actual mechanics (sales,
# automation, fleet priority, research, colony development, market crashes,
# the multi-system endgame) rather than generic filler.
# ===========================================================================
#
# Every achievement's earned status is a pure function of state that
# already exists elsewhere in this module, recomputed fresh on every call
# — never a separately hand-maintained "earned" flag. A handful of checks
# genuinely needed new tracked state (see the module-level declarations
# above `total_sales_count` through `market_crash_ever`) because the thing
# they measure ("this ever happened") isn't recoverable from state that
# only reflects the *current* moment — e.g. total_profit can go back down
# after an automation purchase, so it alone can't answer "has this session
# ever reached 100,000 profit."
ACHIEVEMENTS_FILENAME = "achievements.json"

HOME_SYSTEM_GOODS = frozenset({ORE, GRAIN, MACHINERY, WATER, ENERGY})


def _read_achievements_json():
    """Same loading contract SOL's game.py established: the page's boot
    script fetches achievements.json and hands it to Python as a window
    global before this file runs; the pytest harness's fake `js` module
    simply has no such attribute, so this falls through to reading the
    file straight off disk, which keeps the module importable outside a
    real browser."""
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        js = None

    raw = getattr(js, "ACHIEVEMENTS_JSON", None) if js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 — only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, ACHIEVEMENTS_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Defensive per SOL's own note on this pattern: the real Pyodide runtime
# executes this file's fetched text via `pyodide.runPythonAsync(code)`,
# which never defines `__file__` the way a normal file-based import does —
# if `_read_achievements_json()`'s window-global read ever comes back
# empty, its filesystem fallback would crash with a bare NameError that
# takes down this entire module import, not just achievements. Achievements
# are additive, not core to Trade Empire's own gameplay, so this degrades
# to "no achievements catalog" instead.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []


# ===========================================================================
# Changelog panel (site-wide goal, planning/TODO.md, origin K16: "Per-game
# in-game changelog panel, for every game"). A quick highlights view, not a
# full duplicate of CLAUDE.md/BCM114-DEV-LOG.md -- same loading contract as
# ACHIEVEMENTS above, except CHANGELOG is a flat list (no wrapping key) --
# see changelog.json itself.
# ===========================================================================
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    """Same loading contract as `_read_achievements_json()` above."""
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        js = None

    raw = getattr(js, "CHANGELOG_JSON", None) if js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 — only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, CHANGELOG_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Degrades to an empty list rather than crashing this module's whole
# import -- the changelog panel is purely informational, not core to
# Trade Empire's own gameplay.
try:
    CHANGELOG = json.loads(_read_changelog_json())
except (ValueError, OSError, NameError):
    CHANGELOG = []

changelog_open = False


def on_toggle_changelog(event=None):
    global changelog_open
    changelog_open = not changelog_open
    update_changelog_display()


def update_changelog_display():
    toggle = document.getElementById("changelog-toggle-button")
    panel = document.getElementById("changelog-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide What's New" if changelog_open else "\U0001F4CB What's New"
    panel.hidden = not changelog_open
    if not changelog_open:
        return

    panel.innerHTML = ""
    for entry in sorted(CHANGELOG, key=lambda e: e["date"], reverse=True):
        card = document.createElement("div")
        card.className = "changelog-entry"

        date = document.createElement("p")
        date.className = "changelog-date"
        date.innerText = entry["date"]
        card.appendChild(date)

        text = document.createElement("p")
        text.className = "changelog-text"
        text.innerText = entry["entry"]
        card.appendChild(text)

        panel.appendChild(card)


PROFIT_10K_THRESHOLD = 10000
PROFIT_100K_THRESHOLD = 100000


def _all_research_unlocked():
    # J15: the two specialization branches exclude each other, so "all
    # research" means every shared node plus a completed branch (either).
    shared = {node_id for node_id, node in RESEARCH_NODES.items() if not node.get("excludes")}
    completed_branch = "auto_efficiency_2" in unlocked_research or "market_insight_2" in unlocked_research
    return shared <= unlocked_research and completed_branch


def _any_colony_developed():
    return any(state.is_developed() for state in colony_states.values())


def _home_system_fully_developed():
    return all(colony_states[cid].is_developed() for cid in COLONIES)


def _any_kepler_colony_developed():
    return any(
        colony_states[cid].is_developed() for cid in EXPANSION_COLONIES if cid in colony_states
    )


def _market_recovered_from_a_crash():
    return any(
        crashed and market_multiplier[good] >= MARKET_RECOVERY_THRESHOLD
        for good, crashed in market_crash_ever.items()
    )


# Each checker is a zero-argument predicate read fresh off live state —
# nothing here is ever cached or hand-flagged.
ACHIEVEMENT_CHECKS = {
    "first_sale": lambda: total_sales_count >= 1,
    "first_automation": lambda: automated_ship_count() >= 1,
    "automation_slots_maxed": lambda: automated_ship_count() >= max_automated_ships(),
    "fleet_priority_enabled": lambda: fleet_priority_enabled,
    "fleet_priority_reposition": lambda: ever_repositioned,
    "fast_ships_researched": lambda: "fast_ships" in unlocked_research,
    "hauler_researched": lambda: "hauler" in unlocked_research,
    "automation_slot_researched": lambda: "automation_slot" in unlocked_research,
    "all_research_unlocked": _all_research_unlocked,
    "galaxy_expansion_unlocked": galaxy_expansion_unlocked,
    "colony_developed": _any_colony_developed,
    "home_system_fully_developed": _home_system_fully_developed,
    "kepler_colony_developed": _any_kepler_colony_developed,
    "profit_10k": lambda: max_profit_ever >= PROFIT_10K_THRESHOLD,
    "profit_100k": lambda: max_profit_ever >= PROFIT_100K_THRESHOLD,
    "diversified_trader": lambda: HOME_SYSTEM_GOODS <= goods_sold_ever,
    "market_recovery": _market_recovered_from_a_crash,
    "endgame_reached": lambda: endgame_reached,
    "new_corporation": lambda: legacy_level >= 1,
    # O-1/O-4: derived from state that survives a renewal, so nothing needs carrying.
    "charter_perk": lambda: len(charter_perks) >= 1,
    "charter_veteran": lambda: charters_completed >= CHARTER_VETERAN_COUNT,
    "hard_charter_done": lambda: ledger_hard_completed >= 1,
    # J-7: derived from captains_met, which survives a renewal.
    "captains_table": lambda: len(captains_met) >= 1,
    "full_roster": lambda: len(captains_met) >= len(CAPTAINS),
    "guild_partner": lambda: guild_completed >= 1,
    "guild_favorite": lambda: guild_completed >= 5,
    "background_galaxy_maxed": lambda: background_world_count() >= ENDGAME_BACKGROUND_WORLD_CAP,
    "dark_run": lambda: records["dark_runs"] >= 1,  # J-30
}

# Progress readouts, only for achievements with a natural numeric scale-up
# — a plain earned/not-yet is the honest shape for the rest.
ACHIEVEMENT_PROGRESS = {
    "profit_10k": lambda: (int(max_profit_ever), PROFIT_10K_THRESHOLD),
    "profit_100k": lambda: (int(max_profit_ever), PROFIT_100K_THRESHOLD),
    "diversified_trader": lambda: (len(HOME_SYSTEM_GOODS & goods_sold_ever), len(HOME_SYSTEM_GOODS)),
    "background_galaxy_maxed": lambda: (background_world_count(), ENDGAME_BACKGROUND_WORLD_CAP),
    "charter_veteran": lambda: (min(charters_completed, CHARTER_VETERAN_COUNT), CHARTER_VETERAN_COUNT),
    "full_roster": lambda: (len(captains_met), len(CAPTAINS)),
}


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field. Always recomputed, never itself a save
    input."""
    if sandbox_active:  # Z-18: nothing in the sandbox earns anything; the real list is shown as it was
        return list(_sandbox_real["earned"])
    return [
        entry["id"]
        for entry in ACHIEVEMENTS
        if entry["id"] in legacy_achievements or ACHIEVEMENT_CHECKS[entry["id"]]()
    ]


def achievements_summary():
    """The full catalog, in order, each entry annotated with whether it's
    currently earned and (where one exists) a live progress readout."""
    earned_ids = set(achievement_ids_earned())
    summary = []
    for entry in ACHIEVEMENTS:
        progress_fn = ACHIEVEMENT_PROGRESS.get(entry["id"])
        summary.append(
            {
                "id": entry["id"],
                "label": entry["label"],
                "description": entry["description"],
                "earned": entry["id"] in earned_ids,
                "progress": progress_fn() if progress_fn else None,
            }
        )
    return summary


achievements_open = False

# Tracks the earned-id set as of the last time it was checked, so a fresh
# unlock (one that wasn't in this set last time) can trigger a toast
# without re-toasting every already-earned achievement on every render.
# Reset (without toasting) right after setup()'s initial render and right
# after load_state() applies a save, so neither a fresh game nor a loaded
# one spams toasts for achievements that were already satisfied before
# this render cycle started.
_previously_earned_ids = set()
_toast_hide_proxy = None
_toast_hide_proxy_gen = 0

ACHIEVEMENT_TOAST_DURATION_MS = 4000


def _earned_snapshot():
    earned = set(achievement_ids_earned())
    _story_reach_all(earned)  # W1: every toast check / load baseline also unlocks story chapters
    return earned


def _story_reach_all(earned_ids):
    """W1: unlocks the story chapter for every earned achievement, the
    opening one, and the two cluster beats that have no achievement of
    their own (the Rift Colonies and the Umbral Deep), via the shared
    story-chapters.js. Idempotent and silent: no story script, or a chapter
    id it does not know, simply does nothing. Never touches the save."""
    if sandbox_active:  # Z-18: chapters belong to the real game
        return
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    story = getattr(window, "NoyvjStory", None)
    if story is None:
        return
    story.reach("begin")
    for achievement_id in sorted(earned_ids):
        story.reach(achievement_id)
    if outer_reaches_unlocked():
        story.reach("rift_colonies")
    if umbral_reach_unlocked():
        story.reach("umbral_deep")


def show_achievement_toast(message):
    toast = document.getElementById("achievement-toast")
    if toast is None:
        return
    toast.innerText = message
    toast.hidden = False
    toast.classList.add("achievement-toast--visible")

    # Never destroy a still-pending timer's proxy: the browser would later
    # call it and Pyodide throws "Object has already been destroyed". Each
    # timer owns its own proxy and destroys it after firing; a newer toast
    # just bumps the generation so stale timers become no-ops.
    global _toast_hide_proxy_gen
    _toast_hide_proxy_gen += 1
    my_gen = _toast_hide_proxy_gen
    holder = []

    def _hide():
        if my_gen == _toast_hide_proxy_gen:
            toast.classList.remove("achievement-toast--visible")
            toast.hidden = True
        holder[0].destroy()

    holder.append(create_proxy(_hide))
    setTimeout(holder[0], ACHIEVEMENT_TOAST_DURATION_MS)


# J8/J17 — a second, independent toast for lightweight gameplay nudges
# (a manual ship's arrival, a one-time first-automation callout) that
# are deliberately *not* achievements, kept as its own element/class/
# proxy so it can never collide with an achievement unlocking at the
# same moment (both can be on screen together, in different spots).
_notice_hide_proxy = None
_notice_hide_proxy_gen = 0
NOTICE_TOAST_DURATION_MS = 3000


def show_notice_toast(message):
    toast = document.getElementById("notice-toast")
    if toast is None:
        return
    toast.innerText = message
    toast.hidden = False
    toast.classList.add("notice-toast--visible")

    # Never destroy a still-pending timer's proxy: the browser would later
    # call it and Pyodide throws "Object has already been destroyed". Each
    # timer owns its own proxy and destroys it after firing; a newer toast
    # just bumps the generation so stale timers become no-ops.
    global _notice_hide_proxy_gen
    _notice_hide_proxy_gen += 1
    my_gen = _notice_hide_proxy_gen
    holder = []

    def _hide():
        if my_gen == _notice_hide_proxy_gen:
            toast.classList.remove("notice-toast--visible")
            toast.hidden = True
        holder[0].destroy()

    holder.append(create_proxy(_hide))
    setTimeout(holder[0], NOTICE_TOAST_DURATION_MS)


# J17 — a one-time callout the first time any ship is automated,
# persisted so it never re-fires after being loaded from a save that
# already has an automated ship on it.


def _sync_earned_and_toast():
    """Diffs the live earned set against the last-seen snapshot; anything
    newly present gets a toast (batched into one message if several land
    in the same render pass)."""
    global _previously_earned_ids
    current = _earned_snapshot()
    newly_earned_ids = current - _previously_earned_ids
    _previously_earned_ids = current
    if not newly_earned_ids:
        return
    newly_earned = [entry for entry in ACHIEVEMENTS if entry["id"] in newly_earned_ids]
    if not newly_earned:
        return
    _ribbon_flourish()
    if len(newly_earned) == 1:
        message = f"\U0001F3C6 Achievement unlocked: {newly_earned[0]['label']}"
    else:
        labels = ", ".join(entry["label"] for entry in newly_earned)
        message = f"\U0001F3C6 {len(newly_earned)} achievements unlocked: {labels}"
    show_achievement_toast(message)


def on_toggle_achievements(event=None):
    global achievements_open
    achievements_open = not achievements_open
    update_achievements_display()


def update_achievements_display():
    toggle = document.getElementById("achievements-toggle-button")
    panel = document.getElementById("achievements-panel")
    if toggle is None or panel is None:
        return
    earned_count = len(achievement_ids_earned())
    toggle.innerText = (
        f"Hide Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
        if achievements_open
        else f"\U0001F3C6 Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
    )
    panel.hidden = not achievements_open
    if not achievements_open:
        return

    panel.innerHTML = ""
    for entry in achievements_summary():
        card = document.createElement("div")
        card.className = (
            "achievement-card achievement-card--earned" if entry["earned"] else "achievement-card"
        )
        card.dataset.achievementId = entry["id"]

        label = document.createElement("p")
        label.className = "achievement-card-label"
        label.innerText = f"\U0001F3C6 {entry['label']}" if entry["earned"] else entry["label"]
        card.appendChild(label)

        description = document.createElement("p")
        description.className = "achievement-card-description"
        description.innerText = entry["description"]
        card.appendChild(description)

        if not entry["earned"] and entry["progress"] is not None:
            current, target = entry["progress"]
            progress = document.createElement("p")
            progress.className = "achievement-card-progress"
            progress.innerText = f"{current} of {target}"
            card.appendChild(progress)

        panel.appendChild(card)

    hub_link = document.createElement("a")
    hub_link.className = "achievements-hub-link"
    hub_link.href = "../../index.html#account-achievements-dashboard"
    hub_link.innerText = "View achievements across every game →"
    panel.appendChild(hub_link)

    _request_achievement_stats()


def _request_achievement_stats():
    """Z27b: asks the page's optional JS hook (window.applyAchievementStats,
    shared/achievement-stats.js) to fill in each achievement card's own
    "Earned by N% of players" line from the cross-player stats endpoint
    (planning/TODO.md Z1). Absent hook (pytest, or a page without the
    shared script) leaves the cards exactly as rendered above -- same
    fails-soft shape as Grid's C15 window.gridCompare."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "applyAchievementStats", None)
    if hook is not None:
        hook()


# ===========================================================================
# J9/J11 — an on-demand session summary, following the same toggle+panel
# idiom as the achievements panel (built, not open, by default; only
# populated when open; kept live across render() while open). J11's per-
# route profitability rides along here as the summary's second half,
# rather than a separate panel of its own -- colony_producing()/
# colony_needing() already make "route" and "good" the same concept in
# this game, so listing every good's cumulative sale profit *is* the
# per-route readout.
# ===========================================================================
summary_open = False


def on_toggle_summary(event=None):
    global summary_open
    summary_open = not summary_open
    update_summary_display()


def route_trend_arrow(good):
    """J2 — ▲ improving / ▼ declining / ▶ steady, comparing the newer half
    of the last few sales on this good against the older half. Needs at
    least 4 sales to say anything."""
    recent = good_profit_recent.get(good, [])
    if len(recent) < 4:
        return ""
    half = len(recent) // 2
    older = sum(recent[:half]) / half
    newer = sum(recent[half:]) / (len(recent) - half)
    if older <= 0:
        return ""
    change = (newer - older) / older
    if change > DEFAULT_TREND_EPSILON:
        return "▲"
    if change < -DEFAULT_TREND_EPSILON:
        return "▼"
    return "▶"


def fleet_efficiency_lines():
    """J25 — which purchased ships are earning well below the fleet
    average. Empty until at least two ships have earned something."""
    earners = [sh for sh in ships.values() if sh.purchased]
    total = sum(sh.total_earned for sh in earners)
    if len(earners) < 2 or total <= 0:
        return []
    avg = total / len(earners)
    lines = []
    for sh in earners:
        if sh.total_earned < avg * UNDERPERFORM_FRACTION:
            hint = "idle" if sh.idle_ticks >= IDLE_WARNING_TICKS else "consider automating or rerouting"
            lines.append(f"{sh.name}: {sh.total_earned:,} credits earned (fleet average {avg:,.0f}) — {hint}")
    return lines


THROUGHPUT_WINDOW = 100  # J-6 -- throughput is quoted per this many ticks


def ship_throughput(ship):
    """J-6 -- units this ship has delivered per THROUGHPUT_WINDOW ticks in the
    fleet (None until it has been in the fleet for a tick)."""
    if not ship.purchased or ship.ticks_owned <= 0:
        return None
    return ship.units_moved / ship.ticks_owned * THROUGHPUT_WINDOW


def route_throughput(good):
    """J-6 -- units of `good` moved per ship per THROUGHPUT_WINDOW ticks,
    measured over the ships that have hauled it (None if none has)."""
    haulers = [sh for sh in ships.values() if sh.units_by_good.get(good, 0) > 0 and sh.ticks_owned > 0]
    if not haulers:
        return None
    units = sum(sh.units_by_good[good] for sh in haulers)
    return units / sum(sh.ticks_owned for sh in haulers) * THROUGHPUT_WINDOW


def fleet_throughput():
    """Average per-ship throughput across the purchased ships that have run."""
    rates = [ship_throughput(sh) for sh in ships.values()]
    rates = [r for r in rates if r is not None]
    return sum(rates) / len(rates) if rates else None


def throughput_lines():
    lines = []
    for ship in ships.values():
        rate = ship_throughput(ship)
        if rate is not None and ship.units_moved > 0:
            lines.append(
                f"{ship.name}: {rate:.1f} units per {THROUGHPUT_WINDOW} ticks "
                f"({ship.units_moved:,} units over {ship.ticks_owned:,} ticks)"
            )
    return lines


def throughput_text():
    avg = fleet_throughput()
    if avg is None or not any(sh.units_moved for sh in ships.values()):
        return f"Throughput: no deliveries yet (units moved per ship per {THROUGHPUT_WINDOW} ticks)."
    return f"Throughput: {avg:.1f} units per ship per {THROUGHPUT_WINDOW} ticks across the fleet."


def colony_overview_lines():
    """J13 — every active colony's need/supply state on one screen."""
    lines = []
    for colony_id, state in colony_states.items():
        colony = ALL_COLONIES[colony_id]
        lines.append(
            f"{colony['name']}: {GOOD_LABEL[colony['needs']]} {state.need_satisfaction * 100:.0f}% "
            f"met, {GOOD_LABEL[colony['produces']]} x{state.output_multiplier():.2f} output"
            f"{' (developed)' if state.is_developed() else ''}"
        )
    return lines


def _route_profitability_lines():
    lines = []
    for good, total in good_profit_total.items():
        if total <= 0:
            continue
        producer = colony_producing(good)
        consumer = colony_needing(good)
        producer_name = ALL_COLONIES[producer]["name"] if producer else "?"
        consumer_name = ALL_COLONIES[consumer]["name"] if consumer else "?"
        arrow = route_trend_arrow(good)
        suffix = f" {arrow}" if arrow else ""
        trips = good_trip_count.get(good, 0)
        per_trip = f", avg {total // trips:,}/trip over {trips} trips" if trips > 0 else ""
        rate = route_throughput(good)
        per_ship = f", {rate:.1f} units/ship/{THROUGHPUT_WINDOW} ticks" if rate is not None else ""
        lines.append(f"{GOOD_LABEL[good]} ({producer_name} → {consumer_name}): {total:,} credits{per_trip}{per_ship}{suffix}")
    return lines


def _detach_copy_result_holder(panel):
    """Z-20: empties the summary panel but keeps the shared "Copy result" button's container (and so
    its listener and its "Copied" message) alive, returning it with whether it held keyboard focus."""
    holder = document.getElementById("summary-copy-result")
    focused = False
    try:
        focused = holder is not None and bool(holder.contains(document.activeElement))
    except Exception:  # noqa: BLE001 -- no focus API (tests)
        pass
    panel.innerHTML = ""
    return holder, focused


def _reattach_copy_result_holder(panel, held):
    holder, focused = held
    if holder is None:
        return
    panel.appendChild(holder)
    if focused:
        try:
            holder.querySelector("button").focus()
        except Exception:  # noqa: BLE001
            pass


def share_result():
    """Z-20: the headline numbers for the shared "Copy result" button, as a JSON string the page
    reads (it calls this by name through window.pyodide): total profit, how far the empire got
    (colonies developed, ships) and whether the full-scale endgame was reached."""
    developed = sum(1 for state in colony_states.values() if state.is_developed())
    ships_owned = sum(1 for ship in ships.values() if ship.purchased)
    stats = [
        {"n": developed, "one": "colony developed", "many": "colonies developed"},
        {"n": ships_owned, "one": "ship", "many": "ships"},
    ]
    if endgame_reached:
        stats.append("endgame reached")
    return json.dumps({"game": "Trade Empire", "score": total_profit, "unit": "credits profit", "stats": stats})


def update_summary_display():
    toggle = document.getElementById("summary-toggle-button")
    panel = document.getElementById("summary-panel")
    toggle.innerText = "Hide Summary" if summary_open else "📊 Summary"
    panel.hidden = not summary_open
    if not summary_open:
        return

    developed = sum(1 for state in colony_states.values() if state.is_developed())
    ships_owned = sum(1 for ship in ships.values() if ship.purchased)
    overview_lines = [
        f"Total profit: {total_profit:,} credits (peak {max_profit_ever:,})",
        f"Sales completed: {total_sales_count}",
        f"Ships owned: {ships_owned}/{len(ships)}",
        f"Ships automated: {automated_ship_count()}/{max_automated_ships()}",
        f"Research unlocked: {len(unlocked_research)}/{len(RESEARCH_NODES)}",
        f"Colonies developed: {developed}/{len(colony_states)}",
        f"Achievements: {len(achievement_ids_earned())}/{len(ACHIEVEMENTS)}",
        "Status: full-scale endgame reached" if endgame_reached else "Status: still building",
        legacy_summary_text(),
        charter_summary_text(),
    ]

    holder = _detach_copy_result_holder(panel)
    for line in overview_lines:
        p = document.createElement("p")
        p.className = "summary-line"
        p.innerText = line
        panel.appendChild(p)
    _reattach_copy_result_holder(panel, holder)

    route_heading = document.createElement("p")
    route_heading.className = "panel-label summary-route-heading"
    route_heading.innerText = "Route profitability"
    panel.appendChild(route_heading)

    route_lines = _route_profitability_lines()
    if not route_lines:
        empty = document.createElement("p")
        empty.className = "summary-line"
        empty.innerText = "No completed sales yet."
        panel.appendChild(empty)
    for line in route_lines:
        p = document.createElement("p")
        p.className = "summary-line"
        p.innerText = line
        panel.appendChild(p)

    for heading, lines, empty_text in (
        (f"Throughput per ship (units per {THROUGHPUT_WINDOW} ticks)", throughput_lines(), "No deliveries yet."),
        ("Fleet efficiency", fleet_efficiency_lines(), "No underperforming ships."),
        ("Galaxy overview", colony_overview_lines(), "No colonies yet."),
    ):
        h = document.createElement("p")
        h.className = "panel-label summary-route-heading"
        h.innerText = heading
        panel.appendChild(h)
        for line in lines or [empty_text]:
            p = document.createElement("p")
            p.className = "summary-line"
            p.innerText = line
            panel.appendChild(p)


# ===========================================================================
# O-1/O-3/O-4 -- the Charter panel: the perk tree, the lifetime ledger and the
# renewal options. Static markup in index.html (the buy buttons keep keyboard
# focus across the once-a-second render); filled in here.
# ===========================================================================
charter_open = False


def _render_renewal_options():
    """The renewal preview and the harder-charter toggle, in the endgame panel."""
    gain = charter_points_for_next_renewal()
    preview = document.getElementById("charter-renew-preview-display")
    toggle = document.getElementById("hard-charter-toggle-button")
    if preview is not None:
        text = f"Renewing earns {gain} charter points."
        if hard_charter_next:
            text += " The next charter will be a harder one."
        preview.innerText = text
    if toggle is not None:
        toggle.hidden = not (hard_charter_unlocked() and can_found_new_corporation())
        toggle.innerText = f"Harder charter: {'on' if hard_charter_next else 'off'}"
        toggle.setAttribute("aria-pressed", "true" if hard_charter_next else "false")


def on_toggle_hard_charter(event=None):
    if set_hard_charter_next(not hard_charter_next):
        render()


def on_toggle_charter(event=None):
    global charter_open
    charter_open = not charter_open
    update_charter_display()


def charter_perk_status_text(perk_id):
    perk = CHARTER_PERKS[perk_id]
    text = f"{perk['label']} ({perk['cost']} pt) — {perk['description']}"
    if perk_id in charter_perks:
        return text + " Owned."
    missing = charter_perk_missing_requirements(perk_id)
    if missing:
        return text + " (requires " + " and ".join(CHARTER_PERKS[m]["label"] for m in missing) + ")"
    return text


def career_entry_text(entry):
    """J-14 -- one line of the career log."""
    kind = "Harder charter" if entry["hard"] else "Charter"
    label, glyph = crest_for(entry["n"])
    return (
        f"{glyph} {kind} {entry['n']} ({label} crest): {entry['units']:,} units moved, {entry['routes']} route(s), "
        f"peak profit {entry['peak']:,}, {entry['perks']} perk(s) owned."
        + (" \u25d0 Dark run." if entry.get("dark") else "")
    )


def update_charter_display():
    toggle = document.getElementById("charter-toggle-button")
    panel = document.getElementById("charter-panel")
    if toggle is None or panel is None:
        return
    suffix = " (harder)" if hard_charter_active else ""
    toggle.innerText = ("Hide Charter" if charter_open else "\U0001F4DC Charter") + suffix
    toggle.setAttribute("aria-expanded", "true" if charter_open else "false")
    panel.hidden = not charter_open
    if not charter_open:
        return

    def put(element_id, text):
        element = document.getElementById(element_id)
        if element is not None:
            element.innerText = text

    hard_note = " This is a harder charter: markets saturate faster and colony needs fade sooner." if hard_charter_active else ""
    put(
        "charter-points-display",
        f"Charter points: {charter_points_available()} to spend ({charter_points_earned} earned). "
        f"Renewing the charter earns {charter_points_for_next_renewal()} more." + hard_note,
    )
    put("charter-founding-display", founding_summary_text())
    for perk_id, perk in CHARTER_PERKS.items():
        put(f"charter-perk-{perk_id}-status", charter_perk_status_text(perk_id))
        button = document.getElementById(f"charter-perk-{perk_id}-buy-button")
        if button is None:
            continue
        owned = perk_id in charter_perks
        button.innerText = "Owned" if owned else f"Buy ({perk['cost']})"
        button.disabled = owned or not can_buy_charter_perk(perk_id)
        button.setAttribute("aria-label", f"Buy charter perk {perk['label']} for {perk['cost']} charter points")
        if owned:
            button.title = "Already owned."
        else:
            missing = charter_perk_missing_requirements(perk_id)
            if missing:
                button.title = "Still needed: " + " and ".join(CHARTER_PERKS[m]["label"] for m in missing)
            elif charter_points_available() < perk["cost"]:
                button.title = f"Needs {perk['cost'] - charter_points_available()} more charter point(s)."
            else:
                button.title = "Ready to buy."
    put("ledger-units-display", f"Goods moved: {ledger_units_moved:,} units delivered across every charter.")
    put(
        "ledger-routes-display",
        f"Routes established: {ledger_routes_established:,} in total ({len(ledger_routes_seen)} in this charter).",
    )
    put("ledger-charters-display", f"Charters completed: {charters_completed:,}.")
    put("ledger-hard-display", f"Harder charters completed: {ledger_hard_completed:,}.")
    put(
        "charter-crest-display",
        f"Active crest: {charter_crest_text()}. Crests change at 1, 3, 5 and 10 completed charters "
        "(Founder, Renewed, Veteran, Master, Sovereign), each with its own shape and word.",
    )
    career_list = document.getElementById("charter-career-list")
    if career_list is not None:
        career_list.innerHTML = ""
        if not charter_career:
            item = document.createElement("li")
            item.className = "charter-career-empty"
            item.innerText = (
                "No completed charters logged yet. Each renewal adds a line here: goods moved, routes, "
                "peak profit and perks owned."
            )
            career_list.appendChild(item)
        for entry in reversed(charter_career):
            item = document.createElement("li")
            item.className = "charter-career-entry"
            item.innerText = career_entry_text(entry)
            career_list.appendChild(item)


def _make_charter_perk_handler(perk_id):
    def do_buy():
        buy_charter_perk(perk_id)
        render()

    def handler(event=None):
        if not can_buy_charter_perk(perk_id):
            return
        perk = CHARTER_PERKS[perk_id]
        _confirm_dialog_ask(
            f"trade-empire-charter-perk-{perk_id}",
            f"Buy the {perk['label']} perk for {perk['cost']} charter points? {perk['description']} "
            "It is permanent and carries into every later charter.",
            "Buy perk",
            do_buy,
        )
    return handler


# ===========================================================================
# J-14 (crest) / J-31 (ledger ribbon) / J-7, J-8 (captains panel)
# ===========================================================================
RIBBON_SHAPES = ("\u25cf", "\u25b2", "\u25a0", "\u25c6")  # circle, triangle, square, diamond
RIBBON_MAX_BADGES = 8
RIBBON_FLOURISH_MS = 1200
captains_open = False


def _html_escape(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_crest():
    crest = document.getElementById("charter-crest")
    if crest is None:
        return
    label, glyph = charter_crest()
    crest.innerText = charter_crest_text()
    crest.title = (
        f"Charter crest: {glyph} {label}. Charters completed: {charters_completed}. "
        "The shape and the word both change as you renew the charter."
    )


def ribbon_badges():
    """Up to RIBBON_MAX_BADGES of the earned achievements, latest in the
    catalog first, each with a shape (cycling through four) and its label."""
    earned = achievement_ids_earned()
    labels = {entry["id"]: entry["label"] for entry in ACHIEVEMENTS}
    badges = []
    for index, achievement_id in enumerate(earned):
        badges.append((RIBBON_SHAPES[index % len(RIBBON_SHAPES)], labels.get(achievement_id, achievement_id)))
    return list(reversed(badges[-RIBBON_MAX_BADGES:])), len(earned)


def render_ribbon():
    ribbon = document.getElementById("ledger-ribbon")
    if ribbon is None:
        return
    badges, earned_count = ribbon_badges()
    parts = [
        f'<span class="ribbon-count">Ledger ribbon: {earned_count} of {len(ACHIEVEMENTS)} badges</span>'
    ]
    for shape, label in badges:
        parts.append(
            f'<span class="ribbon-badge"><span class="ribbon-shape" aria-hidden="true">{shape}</span> {_html_escape(label)}</span>'
        )
    hidden = earned_count - len(badges)
    if hidden > 0:
        parts.append(f'<span class="ribbon-more">+{hidden} more in Achievements</span>')
    if not badges:
        parts.append('<span class="ribbon-more">Earn an achievement to pin its badge here.</span>')
    ribbon.innerHTML = "".join(parts)


def _ribbon_flourish():
    """A brief glow on the ribbon when something unlocks. Skipped under
    reduced motion or with the Effects toggle off."""
    ribbon = document.getElementById("ledger-ribbon")
    if ribbon is None or not _effects_on():
        return

    def _clear():
        ribbon.classList.remove("ledger-ribbon--flourish")

    ribbon.classList.add("ledger-ribbon--flourish")
    setTimeout(create_proxy(_clear), RIBBON_FLOURISH_MS)


def on_toggle_captains(event=None):
    global captains_open
    captains_open = not captains_open
    render_captains()


def render_captains():
    toggle = document.getElementById("captains-toggle-button")
    panel = document.getElementById("captains-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide Captains" if captains_open else "\U0001F396\ufe0f Captains"
    toggle.setAttribute("aria-expanded", "true" if captains_open else "false")
    panel.hidden = not captains_open
    # The per-ship captain line is always kept current, panel open or not.
    for ship in ships.values():
        line = document.getElementById(f"ship-{ship.id}-captain")
        if line is None:
            continue
        perk_id = captain_of(ship)
        line.hidden = not ship.purchased or (perk_id is None and not captain_is_earned(ship.id))
        text_el = document.getElementById(f"ship-{ship.id}-captain-text")
        quote_el = document.getElementById(f"ship-{ship.id}-captain-quote")
        if perk_id is not None:
            captain = CAPTAINS[perk_id]
            if text_el is not None:
                text_el.innerText = f"Captain: {captain['name']}, {captain['label']}."
            if quote_el is not None:
                quote_el.innerText = f"\u201c{captain['quote']}\u201d"
        else:
            if text_el is not None:
                text_el.innerText = "Captain's seat earned: pick a captain in the Captains panel."
            if quote_el is not None:
                quote_el.innerText = ""
    if not captains_open:
        return
    summary = document.getElementById("captains-summary-display")
    if summary is not None:
        summary.innerText = captains_summary_text()
    for perk_id in CAPTAINS:
        status = document.getElementById(f"captain-{perk_id}-status")
        if status is not None:
            status.innerText = captain_status_text(perk_id)
        quote = document.getElementById(f"captain-{perk_id}-quote")
        if quote is not None:
            quote.innerText = f"\u201c{CAPTAINS[perk_id]['quote']}\u201d"
        release = document.getElementById(f"captain-{perk_id}-release-button")
        if release is not None:
            release.hidden = not can_release_captain(perk_id)
        for ship_id in ships:
            button = document.getElementById(f"captain-{perk_id}-ship-{ship_id}-button")
            if button is None:
                continue
            applicable = can_assign_captain(perk_id, ship_id)
            button.hidden = not applicable
            button.disabled = not applicable
            ship = ships[ship_id]
            verb = "Move to" if is_captain_swap(perk_id) else "Post to"
            button.innerText = f"{verb} {ship.name}"
            button.setAttribute(
                "aria-label", f"{verb} {ship.name}: {CAPTAINS[perk_id]['name']}, {CAPTAINS[perk_id]['label']}"
            )


def _make_captain_assign_handler(perk_id, ship_id):
    def do_assign():
        assign_captain(perk_id, ship_id)
        render()

    def handler(event=None):
        if not can_assign_captain(perk_id, ship_id):
            return
        if is_captain_swap(perk_id):
            captain = CAPTAINS[perk_id]
            _confirm_dialog_ask(
                f"trade-empire-captain-swap-{perk_id}",
                f"Move {captain['name']} to {ships[ship_id].name}? Each captain can be moved once per charter, "
                "so this is their last posting until you renew.",
                "Move captain",
                do_assign,
            )
        else:
            do_assign()
    return handler


def _make_captain_release_handler(perk_id):
    def handler(event=None):
        release_captain(perk_id)
        render()
    return handler


def render():
    # J22 -- targets the inner #profit-display-text span, not #profit-display
    # itself: the sale-spark burst appends transient children to the sibling
    # #sale-spark-container inside #profit-display, and overwriting
    # #profit-display's own innerText every render would wipe those children
    # out before their one-shot animation ever gets a frame to paint.
    _sandbox_top_up()
    document.getElementById("profit-display-text").innerText = (
        "Credits: unlimited (sandbox)" if sandbox_active else f"Total profit: {total_profit} credits"
    )
    document.getElementById("sale-log").innerText = sale_log[-1] if sale_log else "No sales yet."
    document.getElementById("automation-slots-display").innerText = (
        f"Automation slots: {automated_ship_count()}/{max_automated_ships()} used"
    )
    render_fleet_priority()
    render_endgame()
    render_guild()
    render_research()
    render_map()
    for ship in ships.values():
        render_ship(ship)
    for colony_id in colony_states:
        render_colony(colony_id)
    render_market()
    render_needs_strip()

    # Milestone 13: the Kepler Cluster's colony rows and its goods'
    # market rows stay hidden entirely until the expansion is unlocked
    # -- colony_states not having an entry for them yet is what keeps
    # render_colony() from ever being asked to render one prematurely.
    expansion_unlocked = galaxy_expansion_unlocked()
    document.getElementById("expansion-colonies-panel").hidden = not expansion_unlocked
    document.getElementById("expansion-market-panel").hidden = not expansion_unlocked

    # J13 — same hidden-until-relevant idiom, one tier further out.
    expansion2_unlocked = outer_reaches_unlocked()
    document.getElementById("expansion2-colonies-panel").hidden = not expansion2_unlocked
    document.getElementById("expansion2-market-panel").hidden = not expansion2_unlocked

    # J1 — and once more for the Umbral Deep.
    expansion3_unlocked = umbral_reach_unlocked()
    document.getElementById("expansion3-colonies-panel").hidden = not expansion3_unlocked
    document.getElementById("expansion3-market-panel").hidden = not expansion3_unlocked

    update_achievements_display()
    _sync_earned_and_toast()
    update_summary_display()
    update_charter_display()
    render_crest()
    render_ribbon()
    render_captains()
    render_blackout()
    throughput_el = document.getElementById("throughput-display")
    if throughput_el is not None:
        throughput_el.innerText = throughput_text()


def _make_load_handler(ship_id):
    def handler(event=None):
        ships[ship_id].load()
        render()
    return handler


def _make_stockpile_buy_handler(good):
    def handler(event=None):
        buy_stockpile(good)
        render()
    return handler


def _make_stockpile_sell_handler(good):
    def handler(event=None):
        sell_stockpile(good)
        render()
    return handler


def _make_concession_handler(colony_id):
    def handler(event=None):
        grant_concession(colony_id)
        render()
    return handler


def _make_invest_handler(colony_id):
    def handler(event=None):
        invest_in_colony(colony_id)
        render()
    return handler


def _make_purchase_ship_handler(ship_id):
    def handler(event=None):
        select = document.getElementById(f"ship-{ship_id}-archetype-select")
        purchase_ship(ship_id, str(select.value) if select is not None else DEFAULT_ARCHETYPE)
        render()
    return handler


def _make_rename_handler(ship_id):
    def handler(event=None):
        input_el = document.getElementById(f"ship-{ship_id}-name-input")
        rename_ship(ship_id, input_el.value)
        render()
    return handler


def _make_reset_name_handler(ship_id):
    def handler(event=None):
        reset_ship_name(ship_id)
        input_el = document.getElementById(f"ship-{ship_id}-name-input")
        if input_el is not None:
            input_el.value = ""
        render()
    return handler


def _make_depart_handler(ship_id, destination):
    def handler(event=None):
        ships[ship_id].depart(destination)
        render()
    return handler


def _confirm_dialog_ask(action_id, message, confirm_label, on_confirm, allow_skip=True):
    """Routes a guarded action through the shared shared/confirm-dialog.js
    widget when it's available, or runs the action immediately when it
    isn't -- same lazy `from js import window`/getattr-default shape as
    every other optional-JS-hook call in this hub (Grid's C14, Herd's
    F16). The pytest fake-DOM harness's `js` module only ever fakes
    `document`/`setTimeout`/`setInterval` (see conftest.py's
    `_install_pyodide_fakes`), never `window`, so `from js import window`
    raises ImportError there and this falls straight through to calling
    on_confirm() synchronously -- which is exactly what every existing
    automate/research test in this suite already expects."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        on_confirm()
        return
    confirm_dialog = getattr(window, "ConfirmDialog", None)
    if confirm_dialog is None:
        on_confirm()
        return
    options = {
        "id": action_id,
        "message": message,
        "confirmLabel": confirm_label,
        "onConfirm": create_proxy(on_confirm),
    }
    if not allow_skip:
        options["allowSkip"] = False  # only sent when needed (see shared/confirm-dialog.js)
    confirm_dialog.ask(**options)


def on_found_new_corporation(event=None):
    if not can_found_new_corporation():
        return
    next_level = min(LEGACY_MAX_LEVEL, legacy_level + 1)
    legacy_line = (
        f"You gain permanent Legacy level {next_level}: "
        f"+{legacy_starting_credits(next_level):,} starting credits and "
        f"+{round(LEGACY_SALE_BONUS * next_level * 100)}% on every sale. "
        if legacy_level < LEGACY_MAX_LEVEL
        else "Your Legacy bonus is already at its maximum. "
    )
    hard_line = " The next charter will be a harder one." if hard_charter_next else ""
    _confirm_dialog_ask(
        "found-new-corporation",
        "Renew the Charter? Your fleet, colonies, research and credits reset to a fresh start with new founding "
        f"conditions. You keep your achievements, charter perks and lifetime ledger, and earn "
        f"{charter_points_for_next_renewal()} charter points. " + legacy_line.rstrip() + hard_line,
        "Renew the Charter",
        found_new_corporation,
        allow_skip=False,
    )


def _make_automate_handler(ship_id):
    # J19 (planning/TODO.md's shared confirmation-dialog goal) -- checked
    # frequency before wiring this in: automating a ship is capped at
    # max_automated_ships() (2, +1 per automation-slot research node, up
    # to the 4-ship roster) and is a one-time, irreversible purchase per
    # ship (no de-automate toggle exists), so across an entire
    # playthrough this button is clicked at most 4 times, ever -- a rare,
    # deliberate milestone action, not part of the repeated Load/Depart
    # core loop. Worth the confirm; see CLAUDE.md for the full reasoning.
    def do_automate():
        automate_ship(ship_id)
        render()

    def handler(event=None):
        _confirm_dialog_ask(
            action_id=f"trade-empire-automate-ship-{ship_id}",
            message=(
                f"Automate this ship for {automation_cost()} credits? "
                "This is permanent -- there's no way to de-automate it "
                "afterward."
            ),
            confirm_label="Automate it",
            on_confirm=do_automate,
        )
    return handler


def _make_research_handler(node_id):
    # J19 -- same frequency reasoning as automation above: RESEARCH_NODES
    # has exactly 6 entries total, each unlockable exactly once ever (the
    # button hides on unlock, no re-lock/refund path), so this button is
    # clicked at most 6 times across an entire playthrough. Also
    # genuinely irreversible spend of a slowly-accrued currency -- the
    # priciest nodes (Galaxy Expansion 80, Outer Reaches 200) represent a
    # long stretch of passive accrual, not pocket change.
    def do_unlock():
        unlock_research(node_id)
        render()

    def handler(event=None):
        node = RESEARCH_NODES[node_id]
        _confirm_dialog_ask(
            action_id=f"trade-empire-research-{node_id}",
            message=(
                f"Unlock {node['label']} for {node['cost']} research "
                f"points? {node['description']}."
            ),
            confirm_label="Unlock it",
            on_confirm=do_unlock,
        )
    return handler


def _fleet_priority_toggle_handler(event=None):
    set_fleet_priority(not fleet_priority_enabled)
    render()


# J22 — a small decorative particle/spark burst on a "high-value" sale.
# Purely cosmetic: tick() below only calls this *after* total_profit has
# already been updated and the sale logged, so it can never change or
# delay the actual sale numbers.
#
# Threshold reasoning: a home-system sale (Ore/Grain/Machinery/Water/
# Energy, base prices 5-10) tops out around 180 credits even at full
# specialization + full development, *without* the Hauler Refit research
# (Milestone 10's Forge World bonus, the biggest home-system output
# bonus: 18 units x 10 credits/unit for Machinery). Reaching 200+ takes
# genuine progress -- either that Hauler Refit unlock, a well-developed
# colony, or selling one of the pricier Kepler/Rift-tier goods (Isotopes,
# Crystal, Antimatter) -- so it reliably skips the very first, ordinary
# sales a new player makes, without being so high it's a once-a-
# playthrough rarity either.
SALE_SPARK_THRESHOLD = 200
SALE_SPARK_COUNT = 6
SALE_SPARK_DURATION_MS = 700


def _spark_burst_high_value_sale():
    """J22: bursts a handful of small spark elements out of the profit
    display, then removes them once their one-shot CSS animation
    (te-sale-spark in style.css) finishes. Same create/setTimeout+
    create_proxy/remove-after-timeout shape as
    _flash_personal_best_badge()-style one-shot effects elsewhere on the
    hub -- this one creates transient elements instead of toggling a
    class on a persistent one, since a burst needs several independently
    positioned dots rather than one badge.

    Appends into #sale-spark-container, a dedicated sibling of
    #profit-display-text inside #profit-display -- NOT into
    #profit-display-text itself, since render() overwrites that span's
    innerText every tick and would wipe the sparks out before they ever
    got a frame to paint."""
    container = document.getElementById("sale-spark-container")
    if container is None or not _effects_on():
        return
    sparks = []
    for i in range(SALE_SPARK_COUNT):
        spark = document.createElement("span")
        spark.className = f"sale-spark sale-spark-{i}"
        container.appendChild(spark)
        sparks.append(spark)

    def _cleanup():
        for spark in sparks:
            spark.remove()

    setTimeout(create_proxy(_cleanup), SALE_SPARK_DURATION_MS)


def tick(event=None):
    global total_profit, research_points, total_sales_count, max_profit_ever, season_ticks, premiums_paid
    research_points += RESEARCH_PER_TICK * (LAB_AUTOMATION_RESEARCH_MULTIPLIER if charter_perk("lab_automation") else 1.0)
    if seasonal_demand_enabled:
        season_ticks += 1
    for ship in ships.values():
        result = ship.advance_transit()
        if result is not None:
            good, qty, profit = result
            if qty == 0:
                # J11 -- a disrupted trip: only an insurance payout (if any)
                # counts; no sale, no market impact, no delivery.
                total_profit += profit
                note = f" Insurance paid {profit} credits." if profit else ""
                show_notice_toast(f"\u26a0\ufe0f {ship.name}'s cargo was lost on the route.{note}")
                continue
            total_profit += profit
            total_sales_count += 1
            goods_sold_ever.add(good)
            good_profit_total[good] = good_profit_total.get(good, 0) + profit
            good_trip_count[good] = good_trip_count.get(good, 0) + 1
            recent = good_profit_recent.setdefault(good, [])
            recent.append(profit)
            del recent[:-2 * ROUTE_TREND_WINDOW]
            sale_log.append(sell_summary(good, qty, profit, ship.location))
            del sale_log[:-SALE_LOG_MAX_ENTRIES]
            guild_record_delivery(good, ship.location, qty)
            ledger_record_sale(qty, ship.route_key)
            apply_market_sale(good, qty)
            if profit >= SALE_SPARK_THRESHOLD:
                _spark_burst_high_value_sale()
            # J8 — a lightweight arrival toast, manual ships only: once a
            # ship is automated the player isn't meant to be watching
            # every individual cycle any more, so toasting every one of
            # an automated ship's (much more frequent) arrivals would be
            # the opposite of "lightweight."
            if not ship.automated:
                show_notice_toast(
                    f"🚚 {ship.name} arrived at {ALL_COLONIES[ship.location]['name']}."
                )
    age_dock_pulses()
    guild_tick()
    if route_hazards_enabled and route_insurance_enabled:
        for ship in ships.values():
            if ship.in_transit and total_profit >= INSURANCE_PREMIUM_PER_TICK:
                total_profit -= INSURANCE_PREMIUM_PER_TICK
                premiums_paid += INSURANCE_PREMIUM_PER_TICK
    run_automation()
    for colony_state in colony_states.values():
        colony_state.decay()
        colony_state.update_loyalty()
    recover_market()
    total_profit += trade_post_income_per_tick()

    # J15 — idle-ticks bookkeeping: counts up only while a ship is
    # purchased, manual, docked, and empty; anything else (in transit,
    # loaded, automated, unpurchased) resets it to zero.
    for ship in ships.values():
        if ship.purchased and not ship.automated and ship.docked and not ship.loaded:
            ship.idle_ticks += 1
        else:
            ship.idle_ticks = 0
        if ship.purchased:
            ship.ticks_owned = min(LEDGER_MAX, ship.ticks_owned + 1)  # J-6
    captain_note_veterans()  # J-7

    # J12/J14 — a short rolling history per good/colony, just long enough
    # for a small trend sparkline to read as a shape rather than noise.
    for good in market_multiplier:
        history = price_history.setdefault(good, [])
        history.append(market_multiplier[good])
        del history[:-TREND_HISTORY_MAX_POINTS]
    for colony_id, colony_state in colony_states.items():
        history = need_history.setdefault(colony_id, [])
        history.append(colony_state.need_satisfaction)
        del history[:-TREND_HISTORY_MAX_POINTS]

    global endgame_reached, ticks_since_endgame
    if not endgame_reached and endgame_criteria_met():
        endgame_reached = True
        blackout_note_endgame()  # J-30
    if endgame_reached:
        ticks_since_endgame += 1
        total_profit += background_revenue_this_tick()

    max_profit_ever = max(max_profit_ever, total_profit)

    render()


# ---------------------------------------------------------------------------
# Lifetime records (survive a charter renewal, like captains_met and the ledger).
# One small validated dict instead of a handful of loose globals; saved under
# "records" only once something in it is non-default.
# ---------------------------------------------------------------------------
RECORDS_COUNT_MAX = 1_000_000


def _fresh_records():
    return {"dark_runs": 0}


records = _fresh_records()


def _load_records(raw):
    """Restore the lifetime records from an untrusted save value (defaults for anything malformed)."""
    loaded = _fresh_records()
    if isinstance(raw, dict):
        loaded["dark_runs"] = _saved_int(raw.get("dark_runs"), 0, RECORDS_COUNT_MAX)
    records.clear()
    records.update(loaded)


def _records_for_save():
    """The records worth saving, or an empty dict when nothing was ever recorded."""
    return {key: value for key, value in records.items() if value != _fresh_records()[key]}


# ---------------------------------------------------------------------------
# J-29 / J-30 -- Blackout: an opt-in hard mode. The map is dark, sparklines are
# hidden and prices show as ranges, until the player buys the information back:
# the "price feed" (exact prices and the sparklines) comes with Market Insight
# research or a one-time purchase, the "star chart" (the map and the ships on
# it) comes with Galaxy Expansion research or a one-time purchase. Nothing about
# the economy changes -- only what the player is told. Switching it on before the
# first sale of a charter and never switching it off makes a "dark run"; reaching
# the endgame on one earns the Dark Run achievement, a ledger stamp and a mark
# beside the title. Plain-language warning, always optional, refused in the sandbox.
# ---------------------------------------------------------------------------
BLACKOUT_FEED_COST = 250
BLACKOUT_CHART_COST = 200
BLACKOUT_PRICE_BAND = 0.15
BLACKOUT_INTEL = {
    "feed": {
        "label": "Price feed", "cost": BLACKOUT_FEED_COST, "research": "market_insight",
        "gives": "exact prices and the price and need sparklines",
    },
    "chart": {
        "label": "Star chart", "cost": BLACKOUT_CHART_COST, "research": "galaxy_expansion",
        "gives": "the trade-routes map and the ships on it",
    },
}
BLACKOUT_WARNING = (
    "Blackout is a harder way to play and entirely optional. The map goes dark, the sparklines are hidden and "
    "prices show only as ranges until you buy the information back (a price feed and a star chart, or the research "
    "that gives them). The economy itself does not change. Turn it on before your first sale and keep it on to the "
    "endgame for a Dark Run."
)
blackout_enabled = False
blackout_clean = False  # on since before the first sale of this charter and never switched off
blackout_done = False  # this charter reached the endgame on an unbroken Blackout
blackout_bought = set()


def blackout_has(kind):
    """True when the player can see what `kind` ('feed' or 'chart') shows -- always, outside Blackout."""
    if not blackout_enabled:
        return True
    return kind in blackout_bought or BLACKOUT_INTEL[kind]["research"] in unlocked_research


def blackout_price_range(price):
    """(low, high) credits shown instead of an exact price while the price feed is dark."""
    low = max(1, int(price * (1 - BLACKOUT_PRICE_BAND)))
    high = max(low + 1, int(math.ceil(price * (1 + BLACKOUT_PRICE_BAND))))
    return low, high


def blackout_bar_percent(pct):
    """A coarse (25% steps) bar width, so a dark price feed still hints at a crash without giving the number."""
    return min(100, int(round(pct / 25.0)) * 25)


def set_blackout(enabled):
    """Switch Blackout on or off. Returns True when it is now as asked."""
    global blackout_enabled, blackout_clean
    if sandbox_active:
        return False
    enabled = bool(enabled)
    if enabled == blackout_enabled:
        return True
    blackout_enabled = enabled
    blackout_clean = enabled and total_sales_count == 0
    return True


def can_buy_blackout_intel(kind):
    if kind not in BLACKOUT_INTEL or not blackout_enabled or sandbox_active:
        return False
    return not blackout_has(kind) and total_profit >= BLACKOUT_INTEL[kind]["cost"]


def buy_blackout_intel(kind):
    global total_profit
    if not can_buy_blackout_intel(kind):
        return False
    total_profit -= BLACKOUT_INTEL[kind]["cost"]
    blackout_bought.add(kind)
    return True


def blackout_note_endgame():
    """Called the tick the endgame is first reached: an unbroken Blackout makes it a dark run."""
    global blackout_done
    if blackout_enabled and blackout_clean and not sandbox_active and not blackout_done:
        blackout_done = True
        records["dark_runs"] = min(RECORDS_COUNT_MAX, records["dark_runs"] + 1)


def blackout_status_text():
    if not blackout_enabled:
        extra = f" You have finished {records['dark_runs']} dark run(s)." if records["dark_runs"] else ""
        return "Optional hard mode, off." + extra
    parts = []
    for kind, info in BLACKOUT_INTEL.items():
        if blackout_has(kind):
            parts.append(f"{info['label']}: bought" if kind in blackout_bought else f"{info['label']}: open (research)")
        else:
            parts.append(f"{info['label']}: dark ({info['cost']} credits, or research {RESEARCH_NODES[info['research']]['label']})")
    run = "Dark run in progress." if blackout_clean else "This is not a dark run (it was not on from the first sale)."
    if blackout_done:
        run = "Dark run done: stamped in the ledger."
    return run + " " + "; ".join(parts) + "."


def blackout_stamp_text():
    """The ledger stamp: a shape plus words (never colour only)."""
    return f"◐ Dark run stamp x{records['dark_runs']}" if records["dark_runs"] else ""


def on_toggle_blackout(event=None):
    if blackout_enabled:
        ends = blackout_clean and total_sales_count > 0
        text = "Switch Blackout off? " + (
            "This ends your dark run for this charter." if ends else "Nothing else changes."
        )
        _confirm_dialog_ask("trade-empire-blackout-off", text, "Switch off", lambda: (set_blackout(False), render()))
    else:
        _confirm_dialog_ask(
            "trade-empire-blackout-on", BLACKOUT_WARNING, "Start Blackout", lambda: (set_blackout(True), render()),
            allow_skip=False,
        )


def _make_blackout_buy_handler(kind):
    def handler(event=None):
        if buy_blackout_intel(kind):
            render()
    return handler


def render_blackout():
    button = document.getElementById("blackout-toggle-button")
    status = document.getElementById("blackout-status")
    if button is None or status is None:
        return
    button.innerText = f"Blackout: {'on' if blackout_enabled else 'off'}"
    button.setAttribute("aria-pressed", "true" if blackout_enabled else "false")
    button.disabled = sandbox_active
    status.innerText = blackout_status_text()
    for kind, info in BLACKOUT_INTEL.items():
        buy = document.getElementById(f"blackout-buy-{kind}-button")
        if buy is None:
            continue
        buy.hidden = not blackout_enabled or blackout_has(kind)
        buy.disabled = not can_buy_blackout_intel(kind)
        buy.innerText = f"Buy the {info['label'].lower()} ({info['cost']})"
        buy.title = f"One-time purchase for this charter: {info['gives']}."
    stamp = document.getElementById("ledger-dark-display")
    if stamp is not None:
        stamp.innerText = blackout_stamp_text() or "Dark runs: none yet (Blackout is optional)."


# @@NEW-FEATURES-END@@ (new feature blocks are inserted above this line)


# ===========================================================================
# Save widget contract (planning/SAVE-BUTTON-INTEGRATION.md) — the shared
# shared/save-widget.js drop-in calls these two functions directly via
# Pyodide globals; nothing here needs to be wired to a button. get_state()
# returns a plain, JSON-serialisable dict of everything that makes a
# session distinct (ships, colonies, market, research, fleet priority,
# endgame progress); load_state() is its exact inverse, restoring onto the
# live module state field-by-field with a fallback to whatever's already
# live for any key an older/newer save doesn't carry — the same
# forward/backward-compatibility discipline every other game on the hub
# uses (see BCM114-DEV-LOG.md's 2026-09-02 entries for why bare `data[key]`
# indexing is the wrong default here).
# ===========================================================================


def get_state():
    if sandbox_active:  # Z-18: a save, an autosave or a board read while the sandbox is on is the REAL game
        return copy.deepcopy(_sandbox_real["snapshot"])
    return {
        "ships": {
            ship_id: {
                "location": ship.location,
                "origin": ship.origin,
                "destination": ship.destination,
                "cargo_good": ship.cargo_good,
                "cargo_qty": ship.cargo_qty,
                "transit_ticks_remaining": ship.transit_ticks_remaining,
                "transit_total_ticks": ship.transit_total_ticks,
                "automated": ship.automated,
                "purchased": ship.purchased,
                "archetype": ship.archetype,
                "name": ship.name,
                "idle_ticks": ship.idle_ticks,
                "route_key": sorted(ship.route_key) if ship.route_key else None,
                "route_legs": ship.route_legs,
                "total_earned": ship.total_earned,
                "units_moved": ship.units_moved,
                "ticks_owned": ship.ticks_owned,
                "units_by_good": dict(ship.units_by_good),
                "captain": ship.captain,
                "captain_deliveries": ship.captain_deliveries,
            }
            for ship_id, ship in ships.items()
        },
        "total_profit": total_profit,
        "sale_log": list(sale_log),
        "market_multiplier": dict(market_multiplier),
        "colony_states": {
            colony_id: {
                "need_satisfaction": state.need_satisfaction,
                "development_level": state.development_level,
                "cumulative_delivered": state.cumulative_delivered,
                "secondary_need_satisfaction": state.secondary_need_satisfaction,
                "neglect_ticks": state.neglect_ticks,
                "demand_ticks_left": state.demand_ticks_left,
                "demand_cooldown": state.demand_cooldown,
                "demands_made": state.demands_made,
                "concessions_granted": state.concessions_granted,
            }
            for colony_id, state in colony_states.items()
        },
        "research_points": research_points,
        "unlocked_research": sorted(unlocked_research),
        "fleet_priority_enabled": fleet_priority_enabled,
        "endgame_reached": endgame_reached,
        "ticks_since_endgame": ticks_since_endgame,
        "total_sales_count": total_sales_count,
        "max_profit_ever": max_profit_ever,
        "goods_sold_ever": sorted(goods_sold_ever),
        "ever_repositioned": ever_repositioned,
        "market_crash_ever": dict(market_crash_ever),
        "good_profit_total": dict(good_profit_total),
        "good_trip_count": dict(good_trip_count),
        "good_profit_recent": {g: list(v) for g, v in good_profit_recent.items()},
        "price_history": {good: list(values) for good, values in price_history.items()},
        "need_history": {colony_id: list(values) for colony_id, values in need_history.items()},
        "seasonal_demand": {"enabled": seasonal_demand_enabled, "ticks": season_ticks},
        "cross_system_units": cross_system_units,
        "trade_posts": list(trade_posts),
        "stockpile": {good: units for good, units in stockpile.items() if units},
        # J-4 -- only written once the player has made a stockpile trade.
        **({"price_memory": dict(price_memory)} if price_memory else {}),
        # J-7 -- fleet captains; only written once a seat is earned or a captain met.
        **(
            {
                "captains": {
                    "earned": sorted(captain_earned),
                    "assignments": {k: v for k, v in captain_assignments.items() if v},
                    "met": sorted(captains_met),
                }
            }
            if captain_earned or captains_met or any(captain_assignments.values())
            else {}
        ),
        # J21 -- only written once a new corporation has been founded, so a
        # first-run save is unchanged.
        **({"legacy": {"level": legacy_level, "achievements": list(legacy_achievements)}} if legacy_level else {}),
        # O-3 -- the lifetime ledger, only written once anything has been moved.
        **(
            {
                "ledger": {
                    "units": ledger_units_moved,
                    "routes": ledger_routes_established,
                    "hard_completed": ledger_hard_completed,
                    "routes_seen": sorted(sorted(key) for key in ledger_routes_seen),
                    "charter_units": ledger_charter_units,
                }
            }
            if ledger_units_moved or ledger_routes_established or ledger_hard_completed or ledger_routes_seen
            or ledger_charter_units
            else {}
        ),
        # O-1/O-2/O-4 -- charter tree, points and founding seed; only written
        # once a charter has been renewed (or a harder charter is queued).
        **(
            {
                "charter": {
                    "completed": charters_completed,
                    "points": charter_points_earned,
                    "perks": sorted(charter_perks),
                    "seed": founding_seed,
                    "hard": hard_charter_active,
                    "hard_next": hard_charter_next,
                    "career": [dict(entry) for entry in charter_career],
                }
            }
            if charters_completed or charter_points_earned or charter_perks or founding_seed
            or hard_charter_active or hard_charter_next
            else {}
        ),
        # J3 -- only written once the guild has done anything at all.
        **(
            {"guild": {"state": guild_state, **guild_contract, "completed": guild_completed, "failed": guild_failed}}
            if guild_state != "none" or guild_completed or guild_failed
            else {}
        ),
        # J-29/J-30 -- Blackout and the lifetime records; only written once used.
        **(
            {"blackout": {"enabled": blackout_enabled, "clean": blackout_clean, "done": blackout_done,
                          "bought": sorted(blackout_bought)}}
            if blackout_enabled or blackout_done or blackout_bought
            else {}
        ),
        **({"records": _records_for_save()} if _records_for_save() else {}),
        "route_hazards": {
            "hazards": route_hazards_enabled,
            "insurance": route_insurance_enabled,
            "disruptions": disruptions_suffered,
            "payouts": insurance_payouts,
            "premiums": premiums_paid,
        },
        # Write-only projection (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) — always
        # freshly recomputed here, never read back in load_state() below.
        "achievements_earned": achievement_ids_earned(),
    }


def _load_guild(raw):
    """Restore the guild from an untrusted save value; anything malformed or
    referring to a colony that isn't reachable falls back to 'none'."""
    global guild_completed, guild_failed
    _guild_clear(guild_first_offer_ticks())
    guild_completed = guild_failed = 0
    if not isinstance(raw, dict):
        return

    def as_int(value, low, high):
        return value if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high else None

    guild_completed = as_int(raw.get("completed"), 0, 10_000_000) or 0
    guild_failed = as_int(raw.get("failed"), 0, 10_000_000) or 0
    state_name = raw.get("state")
    if state_name not in ("offered", "active"):
        return
    good, destination = raw.get("good"), raw.get("destination")
    units = as_int(raw.get("units"), GUILD_UNITS_MIN, GUILD_UNITS_MAX)
    delivered = as_int(raw.get("delivered"), 0, GUILD_UNITS_MAX)
    ticks_left = as_int(raw.get("ticks_left"), 1, GUILD_DEADLINE_TICKS)
    reward = as_int(raw.get("reward"), 0, 10_000_000)
    valid = (
        destination in ALL_COLONIES
        and destination in active_colony_ids()
        and good == ALL_COLONIES[destination]["needs"]
        and None not in (units, delivered, ticks_left, reward)
        and delivered <= units
    )
    if not valid:
        return
    global guild_state
    guild_state = state_name
    guild_contract.update({
        "good": good, "destination": destination, "units": units,
        "delivered": delivered, "ticks_left": ticks_left, "reward": reward,
    })


def _saved_int(value, low, high, default=0):
    """A save's whole number, or `default` if it isn't a real int (never bool) in range."""
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        return default
    return value


def _load_career(raw, charters_done):
    """J-14 -- the career log from an untrusted save: only whole entries with
    sane numbers survive, never more than the charters actually completed."""
    if not isinstance(raw, list) or charters_done <= 0:
        return []
    entries = []
    for item in raw[:CAREER_MAX_ENTRIES * 2]:
        if not isinstance(item, dict):
            continue
        n = _saved_int(item.get("n"), 1, CHARTER_COUNT_MAX, 0)
        units = _saved_int(item.get("units"), 0, LEDGER_MAX, -1)
        routes = _saved_int(item.get("routes"), 0, 10_000, -1)
        peak = _saved_int(item.get("peak"), 0, LEDGER_MAX, -1)
        perks = _saved_int(item.get("perks"), 0, len(CHARTER_PERKS), -1)
        if n == 0 or -1 in (units, routes, peak, perks) or not isinstance(item.get("hard"), bool):
            continue
        entry = {"n": n, "hard": item["hard"], "units": units, "routes": routes, "peak": peak, "perks": perks}
        if item.get("dark") is True:
            entry["dark"] = True
        entries.append(entry)
    return entries[-min(CAREER_MAX_ENTRIES, charters_done):]


def _load_charter(charter_raw, ledger_raw):
    """Restore the charter tree, founding seed, hard-charter flags and the
    lifetime ledger from untrusted save values. Anything missing or malformed
    falls back to its default; a save from before O-1 that carries a J21
    legacy level is migrated as that many completed charters."""
    global charters_completed, charter_points_earned, charter_perks, founding_seed
    global hard_charter_active, hard_charter_next
    global ledger_units_moved, ledger_routes_established, ledger_hard_completed, ledger_routes_seen
    global ledger_charter_units, charter_career
    charters_completed = charter_points_earned = founding_seed = 0
    charter_perks = set()
    hard_charter_active = hard_charter_next = False
    ledger_units_moved = ledger_routes_established = ledger_hard_completed = 0
    ledger_routes_seen = set()
    ledger_charter_units = 0
    charter_career = []

    if isinstance(charter_raw, dict):
        charters_completed = _saved_int(charter_raw.get("completed"), 0, CHARTER_COUNT_MAX)
        charter_points_earned = _saved_int(charter_raw.get("points"), 0, CHARTER_COUNT_MAX * 10)
        founding_seed = _saved_int(charter_raw.get("seed"), 0, FOUNDING_SEED_MAX)
        raw_perks = charter_raw.get("perks")
        if isinstance(raw_perks, list):
            # Known string ids only (type-checked before the membership test so
            # an unhashable or non-string entry can't crash it), then drop any
            # perk whose prerequisites aren't also present.
            wanted = {p for p in raw_perks if isinstance(p, str) and p in CHARTER_PERKS}
            changed = True
            while changed:
                changed = False
                for perk_id in sorted(wanted):
                    if any(r not in wanted for r in CHARTER_PERKS[perk_id]["requires"]):
                        wanted.discard(perk_id)
                        changed = True
            charter_perks = wanted
            if charter_points_spent() > charter_points_earned:
                charter_perks = set()  # a save can't own more than it earned
        hard_charter_active = charter_raw.get("hard") is True and charters_completed >= 1
        hard_charter_next = charter_raw.get("hard_next") is True
        charter_career = _load_career(charter_raw.get("career"), charters_completed)
    elif legacy_level > 0:
        charters_completed = legacy_level
        charter_points_earned = CHARTER_POINTS_PER_RENEWAL * legacy_level
    if charters_completed == 0:
        founding_seed = 0

    if isinstance(ledger_raw, dict):
        ledger_units_moved = _saved_int(ledger_raw.get("units"), 0, LEDGER_MAX)
        ledger_routes_established = _saved_int(ledger_raw.get("routes"), 0, LEDGER_MAX)
        ledger_hard_completed = _saved_int(ledger_raw.get("hard_completed"), 0, CHARTER_COUNT_MAX)
        ledger_charter_units = min(ledger_units_moved, _saved_int(ledger_raw.get("charter_units"), 0, LEDGER_MAX))
        seen_raw = ledger_raw.get("routes_seen")
        if isinstance(seen_raw, list):
            for pair in seen_raw[:100]:
                if (
                    isinstance(pair, list) and len(pair) == 2
                    and all(isinstance(c, str) and c in ALL_COLONIES for c in pair)
                    and pair[0] != pair[1]
                ):
                    ledger_routes_seen.add(frozenset(pair))


def _load_blackout(raw):
    """J-29 -- restore Blackout from an untrusted save value (off unless it says a real True)."""
    global blackout_enabled, blackout_clean, blackout_done
    blackout_enabled = blackout_clean = blackout_done = False
    blackout_bought.clear()
    if not isinstance(raw, dict):
        return
    blackout_enabled = raw.get("enabled") is True
    blackout_clean = blackout_enabled and raw.get("clean") is True
    blackout_done = raw.get("done") is True
    bought = raw.get("bought")
    if isinstance(bought, list):
        blackout_bought.update(kind for kind in bought if isinstance(kind, str) and kind in BLACKOUT_INTEL)


def _load_captains(raw):
    """J-7 -- restore fleet captains from an untrusted save. Runs after the
    ships are loaded: a captain only stays on a purchased ship that has earned
    a seat, one captain per ship and one ship per captain."""
    global captain_earned, captain_assignments, captains_met
    captain_earned = set()
    captain_assignments = {perk_id: 0 for perk_id in CAPTAINS}
    captains_met = set()
    if isinstance(raw, dict):
        earned_raw = raw.get("earned")
        if isinstance(earned_raw, list):
            captain_earned = {s_id for s_id in earned_raw if isinstance(s_id, str) and s_id in ships}
        assign_raw = raw.get("assignments")
        if isinstance(assign_raw, dict):
            for perk_id in CAPTAINS:
                captain_assignments[perk_id] = _saved_int(assign_raw.get(perk_id), 0, 1 + CAPTAIN_SWAPS_PER_CHARTER)
        met_raw = raw.get("met")
        if isinstance(met_raw, list):
            captains_met = {p for p in met_raw if isinstance(p, str) and p in CAPTAINS}
    seen = set()
    for ship in ships.values():
        valid = (
            ship.captain in CAPTAINS and ship.captain not in seen
            and ship.purchased and ship.id in captain_earned
        )
        if valid:
            seen.add(ship.captain)
            captain_assignments[ship.captain] = max(captain_assignments[ship.captain], 1)
            captains_met.add(ship.captain)
        else:
            ship.captain = None
            ship.captain_deliveries = 0


def _saved_float(value, low, high, default):
    """A save's number, or `default` if it isn't a real, finite, in-range one."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    if not math.isfinite(value) or not low <= value <= high:
        return default
    return float(value)


def load_state(data):
    """The public entry the save widget calls: leaves the practice sandbox first (Z-18), then loads."""
    if sandbox_active:
        _sandbox_restore_real(apply_snapshot=False)
    result = _apply_state(data)
    _sandbox_notify_page()
    return result


def _apply_state(data):
    """Exact inverse of get_state(). Colony state for the Kepler Cluster
    is (re)created here if the save has galaxy_expansion unlocked but the
    live module hasn't gotten there yet — mirroring what unlock_research()
    itself does — so a save loaded fresh into a brand-new session doesn't
    leave Fleet Priority's most_urgent_colony() unable to see colonies the
    save says should exist."""
    global total_profit, sale_log, research_points, unlocked_research
    global fleet_priority_enabled, endgame_reached, ticks_since_endgame
    global total_sales_count, max_profit_ever, goods_sold_ever, ever_repositioned
    global _previously_earned_ids
    global seasonal_demand_enabled, season_ticks, cross_system_units
    global route_hazards_enabled, route_insurance_enabled, disruptions_suffered, insurance_payouts, premiums_paid
    global legacy_level, legacy_achievements

    stockpile_raw = data.get("stockpile")
    for good in stockpile:
        units = stockpile_raw.get(good) if isinstance(stockpile_raw, dict) else None
        valid = isinstance(units, int) and not isinstance(units, bool) and 0 <= units <= STOCKPILE_CAPACITY
        stockpile[good] = units if valid else 0

    posts_raw = data.get("trade_posts")
    trade_posts[:] = []
    if isinstance(posts_raw, list):
        for label in posts_raw:
            if isinstance(label, str) and label in TRADE_POST_SYSTEMS and label not in trade_posts:
                trade_posts.append(label)

    hazards_raw = data.get("route_hazards")
    if not isinstance(hazards_raw, dict):
        hazards_raw = {}

    def _count(key):
        value = hazards_raw.get(key)
        return value if isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 10_000_000 else 0

    route_hazards_enabled = hazards_raw.get("hazards") is True
    route_insurance_enabled = hazards_raw.get("insurance") is True
    disruptions_suffered, insurance_payouts, premiums_paid = _count("disruptions"), _count("payouts"), _count("premiums")

    units_raw = data.get("cross_system_units")
    cross_system_units = units_raw if isinstance(units_raw, int) and not isinstance(units_raw, bool) and 0 <= units_raw <= 10_000_000 else 0

    seasonal_raw = data.get("seasonal_demand")
    if isinstance(seasonal_raw, dict):
        seasonal_demand_enabled = seasonal_raw.get("enabled") is True
        ticks_raw = seasonal_raw.get("ticks")
        season_ticks = ticks_raw if isinstance(ticks_raw, int) and not isinstance(ticks_raw, bool) and 0 <= ticks_raw <= 10_000_000 else 0
    else:
        seasonal_demand_enabled, season_ticks = False, 0

    # Untrusted save value: only known node ids survive (a non-list, or a
    # list holding unhashable/non-string/unknown entries, must not crash the
    # set() build or invent research).
    research_raw = data.get("unlocked_research", sorted(unlocked_research))
    unlocked_research = {
        node for node in (research_raw if isinstance(research_raw, list) else [])
        if isinstance(node, str) and node in RESEARCH_NODES
    }

    # A save that hasn't unlocked an expansion must not keep that expansion's
    # colonies from whatever was running before (loading an earlier save, or
    # J21's fresh start after a late-game corporation).
    if not galaxy_expansion_unlocked():
        for colony_id in EXPANSION_COLONIES:
            colony_states.pop(colony_id, None)
    if not outer_reaches_unlocked():
        for colony_id in RIFT_COLONIES:
            colony_states.pop(colony_id, None)
    if not umbral_reach_unlocked():
        for colony_id in DEEP_COLONIES:
            colony_states.pop(colony_id, None)

    legacy_raw = data.get("legacy")
    legacy_level = 0
    legacy_achievements = []
    if isinstance(legacy_raw, dict):
        level = legacy_raw.get("level")
        if isinstance(level, int) and not isinstance(level, bool):
            legacy_level = max(0, min(LEGACY_MAX_LEVEL, level))
        known = {entry["id"] for entry in ACHIEVEMENTS}
        raw_ids = legacy_raw.get("achievements")
        if legacy_level and isinstance(raw_ids, list):
            legacy_achievements = [a for a in dict.fromkeys(raw_ids) if isinstance(a, str) and a in known]
    _load_charter(data.get("charter"), data.get("ledger"))
    _load_guild(data.get("guild"))  # after the charter: Guild Standing shortens the first wait

    if galaxy_expansion_unlocked():
        for colony_id in EXPANSION_COLONIES:
            if colony_id not in colony_states:
                colony_states[colony_id] = ColonyState(colony_id)
    if outer_reaches_unlocked():
        for colony_id in RIFT_COLONIES:
            if colony_id not in colony_states:
                colony_states[colony_id] = ColonyState(colony_id)
    if umbral_reach_unlocked():
        for colony_id in DEEP_COLONIES:
            if colony_id not in colony_states:
                colony_states[colony_id] = ColonyState(colony_id)

    saved_colony_states = data.get("colony_states", {})
    for colony_id, state in colony_states.items():
        saved = saved_colony_states.get(colony_id)
        if not saved:
            continue
        if not isinstance(saved, dict):
            continue
        # Untrusted save values: numbers only (never bool), finite, and inside
        # each field's real range; anything else keeps the colony's default.
        state.need_satisfaction = _saved_float(saved.get("need_satisfaction"), 0.0, 1.0, state.need_satisfaction)
        level = saved.get("development_level")
        if isinstance(level, int) and not isinstance(level, bool) and 1 <= level <= 2:
            state.development_level = level
        state.cumulative_delivered = _saved_float(
            saved.get("cumulative_delivered"), 0.0, 10_000_000.0, state.cumulative_delivered
        )
        state.secondary_need_satisfaction = _saved_float(
            saved.get("secondary_need_satisfaction"), 0.0, 1.0, state.secondary_need_satisfaction
        )
        for loyalty_key, limit in (
            ("neglect_ticks", TEMPERAMENT_COUNT_MAX),  # keeps counting through a cooldown, so it can pass NEGLECT_DEMAND_TICKS
            ("demand_ticks_left", DEMAND_WINDOW_TICKS),
            ("demand_cooldown", DEMAND_COOLDOWN_TICKS),
        ):
            raw = saved.get(loyalty_key)
            valid = isinstance(raw, int) and not isinstance(raw, bool) and 0 <= raw <= limit
            setattr(state, loyalty_key, raw if valid else 0)
        state.demands_made = _saved_int(saved.get("demands_made"), 0, TEMPERAMENT_COUNT_MAX)
        state.concessions_granted = _saved_int(saved.get("concessions_granted"), 0, TEMPERAMENT_COUNT_MAX)

    saved_ships = data.get("ships", {})
    if not isinstance(saved_ships, dict):
        saved_ships = {}
    for ship_id, ship in ships.items():
        saved = saved_ships.get(ship_id)
        if not saved or not isinstance(saved, dict):
            continue
        ship.location = saved.get("location", ship.location)
        ship.origin = saved.get("origin", ship.origin)
        ship.destination = saved.get("destination", ship.destination)
        ship.cargo_good = saved.get("cargo_good", ship.cargo_good)
        ship.cargo_qty = saved.get("cargo_qty", ship.cargo_qty)
        ship.transit_ticks_remaining = saved.get(
            "transit_ticks_remaining", ship.transit_ticks_remaining
        )
        ship.transit_total_ticks = saved.get("transit_total_ticks", ship.transit_total_ticks)
        ship.automated = saved.get("automated", ship.automated)
        ship.purchased = saved.get("purchased", ship.purchased)
        saved_archetype = saved.get("archetype")
        ship.archetype = saved_archetype if isinstance(saved_archetype, str) and saved_archetype in SHIP_ARCHETYPES else DEFAULT_ARCHETYPE
        ship.name = saved.get("name", ship.name)
        ship.idle_ticks = saved.get("idle_ticks", ship.idle_ticks)
        saved_key = saved.get("route_key")
        ship.route_key = frozenset(saved_key) if saved_key else None
        ship.route_legs = saved.get("route_legs", 0)
        ship.total_earned = saved.get("total_earned", 0)
        ship.units_moved = _saved_int(saved.get("units_moved"), 0, LEDGER_MAX)
        ship.ticks_owned = _saved_int(saved.get("ticks_owned"), 0, LEDGER_MAX)
        by_good = saved.get("units_by_good")
        ship.units_by_good = {}
        if isinstance(by_good, dict):
            for good_id, units in by_good.items():
                if isinstance(good_id, str) and good_id in SELL_PRICE and _saved_int(units, 1, LEDGER_MAX, 0):
                    ship.units_by_good[good_id] = units
        captain_raw = saved.get("captain")
        ship.captain = captain_raw if isinstance(captain_raw, str) and captain_raw in CAPTAINS else None
        ship.captain_deliveries = _saved_int(saved.get("captain_deliveries"), 0, LEDGER_MAX)

    # A ship can't be docked at, or flying to/from, a colony this save hasn't
    # unlocked (its colony state was just pruned above, and a docked ship
    # would crash load()): send it home, empty, rather than trusting the save.
    reachable_now = active_colony_ids()
    for ship in ships.values():
        docked_ok = ship.location in reachable_now if isinstance(ship.location, str) else False
        transit_ok = (
            ship.location is None
            and isinstance(ship.origin, str) and ship.origin in reachable_now
            and isinstance(ship.destination, str) and ship.destination in reachable_now
        )
        if not (docked_ok or transit_ok):
            ship.location = "aurum"
            ship.origin = ship.destination = None
            ship.cargo_good, ship.cargo_qty = None, 0
            ship.transit_ticks_remaining = ship.transit_total_ticks = 0

    _load_captains(data.get("captains"))
    _load_records(data.get("records"))
    _load_blackout(data.get("blackout"))
    price_memory.clear()
    memory_raw = data.get("price_memory")
    if isinstance(memory_raw, dict):
        for good_id, value in memory_raw.items():
            if isinstance(good_id, str) and good_id in SELL_PRICE:
                remembered = _saved_float(value, 0.0, 1.0, -1.0)
                if remembered >= 0.0:
                    price_memory[good_id] = remembered

    market_multiplier.update(data.get("market_multiplier", {}))
    total_profit = data.get("total_profit", total_profit)
    sale_log = list(data.get("sale_log", sale_log))
    research_points = data.get("research_points", research_points)
    fleet_priority_enabled = data.get("fleet_priority_enabled", fleet_priority_enabled)
    endgame_reached = data.get("endgame_reached", endgame_reached)
    ticks_since_endgame = data.get("ticks_since_endgame", ticks_since_endgame)

    total_sales_count = data.get("total_sales_count", total_sales_count)
    max_profit_ever = data.get("max_profit_ever", max_profit_ever)
    goods_sold_ever = set(data.get("goods_sold_ever", goods_sold_ever))
    ever_repositioned = data.get("ever_repositioned", ever_repositioned)
    market_crash_ever.update(data.get("market_crash_ever", {}))
    good_profit_total.update(data.get("good_profit_total", {}))
    good_trip_count.update(data.get("good_trip_count", {}))
    for good, values in data.get("good_profit_recent", {}).items():
        good_profit_recent[good] = list(values)
    for good, values in data.get("price_history", {}).items():
        price_history[good] = list(values)
    for colony_id, values in data.get("need_history", {}).items():
        need_history[colony_id] = list(values)
    # Belt-and-suspenders backfill, same idea as Canopy's community_
    # relations_min_ever: an old save predating this field can't have
    # recorded it, but the restored total_profit is itself a valid lower
    # bound on the highest profit this session must have reached.
    max_profit_ever = max(max_profit_ever, total_profit)

    # achievements_earned itself is never read back (write-only) -- but
    # the toast-diffing baseline must be reset here, before render() below
    # calls _sync_earned_and_toast(), so a loaded save's already-earned
    # achievements don't all fire toasts on load.
    _previously_earned_ids = _earned_snapshot()

    render()
    return True


# --- Z-18: entering and leaving the practice sandbox ---------------------------------------------
# shared/sandbox-mode.js calls sandbox_enter() / sandbox_leave() / sandbox_is_active() through Pyodide and
# draws the "Sandbox: nothing here is saved" banner. The rules: a large credit balance that never runs out
# (no bankruptcy), every research node known (so every system and route is open), every ship bought, no
# route hazards, no corporation renewal, nothing earned. The real game is set aside as a get_state()
# snapshot and loaded back through the same load_state() a save uses; the sandbox is a fresh corporation
# loaded the same way, so it can never write into the real one.
SANDBOX_CREDITS = 1_000_000
sandbox_active = False
_sandbox_real = None


def _sandbox_notify_page():
    """Tells shared/sandbox-mode.js to re-read sandbox_is_active() (the banner and button follow it)."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    shared = getattr(window, "NoyvjSandbox", None)
    if shared is not None:
        shared.sync()


def sandbox_is_active():
    return sandbox_active


def _sandbox_top_up():
    """The balance never drops below SANDBOX_CREDITS (called from every render, so also after each purchase)."""
    global total_profit, max_profit_ever
    if sandbox_active and total_profit < SANDBOX_CREDITS:
        total_profit = SANDBOX_CREDITS
        max_profit_ever = max(max_profit_ever, total_profit)


def _reset_running_tables():
    """load_state() only updates these tables key by key, so a load would keep whatever the game running before
    it had put there; put them back to a brand-new game's values first."""
    fresh = _fresh_state
    good_profit_recent.clear()
    need_history.clear()
    price_history.clear()
    price_history.update({good: list(values) for good, values in fresh["price_history"].items()})
    market_multiplier.update(fresh["market_multiplier"])
    good_profit_total.update(fresh["good_profit_total"])
    good_trip_count.update(fresh["good_trip_count"])
    market_crash_ever.update(fresh["market_crash_ever"])


def _sandbox_state():
    """The brand-new corporation the sandbox starts from, as a save dict."""
    data = copy.deepcopy(_fresh_state)
    data["unlocked_research"] = sorted(RESEARCH_NODES)
    data["research_points"] = _fresh_state["research_points"]
    data["total_profit"] = SANDBOX_CREDITS
    data["max_profit_ever"] = SANDBOX_CREDITS
    for ship in data["ships"].values():
        ship["purchased"] = True
    data["route_hazards"] = {"hazards": False, "insurance": False, "disruptions": 0, "payouts": 0, "premiums": 0}
    return data


def sandbox_enter():
    """Sets the real corporation aside and starts a practice one. True when the sandbox is on."""
    global sandbox_active, _sandbox_real
    if sandbox_active:
        return True
    snapshot = get_state()
    _sandbox_real = {
        "snapshot": snapshot,
        "earned": list(snapshot["achievements_earned"]),
        "guild_cooldown": guild_cooldown,
    }
    sandbox_active = True
    _reset_running_tables()
    _apply_state(_sandbox_state())
    _sandbox_top_up()
    render()
    return True


def _sandbox_restore_real(apply_snapshot=True):
    """Puts the real corporation back exactly as it was. With apply_snapshot False the caller loads a save instead."""
    global sandbox_active, _sandbox_real, guild_cooldown
    real = _sandbox_real
    sandbox_active = False
    _sandbox_real = None
    if real is None:
        return
    if apply_snapshot:
        _reset_running_tables()
        _apply_state(copy.deepcopy(real["snapshot"]))
        guild_cooldown = real["guild_cooldown"]
    else:
        _reset_running_tables()


def sandbox_leave():
    """Leaves the sandbox; the real corporation is back and untouched. True when it is."""
    if not sandbox_active:
        return True
    _sandbox_restore_real()
    return True


def _start_tick_loop():
    """W-2: hands `tick` to shared/time-controls.js (pause and 1x/2x/4x) when the
    page has it, otherwise falls back to the plain setInterval this game always
    used (fake-js test environments and any page without the shared script).
    Either way the tick itself is untouched: the controller only changes how
    often it is called, and not at all while paused or while the tab is hidden
    (shared/pause-hidden.js). Returns "shared" or "interval"."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        controls = getattr(window, "NoyvjTime", None)
    except ImportError:
        controls = None
    if controls is not None and getattr(controls, "start", None) is not None:
        controls.start("trade-empire", create_proxy(tick), TICK_INTERVAL_MS)
        return "shared"
    setInterval(create_proxy(tick), TICK_INTERVAL_MS)
    return "interval"


def setup():
    document.getElementById("seasonal-demand-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_seasonal_demand)
    )
    document.getElementById("trade-post-button").addEventListener("click", create_proxy(on_build_trade_post))
    for good in SELL_PRICE:
        buy_button = document.getElementById(f"stockpile-{good}-buy-button")
        if buy_button is not None:
            buy_button.addEventListener("click", create_proxy(_make_stockpile_buy_handler(good)))
            document.getElementById(f"stockpile-{good}-sell-button").addEventListener(
                "click", create_proxy(_make_stockpile_sell_handler(good))
            )
    for colony_id in ALL_COLONIES:
        concede_button = document.getElementById(f"colony-{colony_id}-concede-button")
        if concede_button is not None:
            concede_button.addEventListener("click", create_proxy(_make_concession_handler(colony_id)))
    for colony_id in ALL_COLONIES:
        invest_button = document.getElementById(f"colony-{colony_id}-invest-button")
        if invest_button is not None:
            invest_button.addEventListener("click", create_proxy(_make_invest_handler(colony_id)))
    document.getElementById("route-hazards-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_route_hazards)
    )
    document.getElementById("route-insurance-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_route_insurance)
    )
    for colony_id, colony in ALL_COLONIES.items():
        document.getElementById(f"colony-{colony_id}-name").innerText = colony["name"]
        document.getElementById(f"colony-{colony_id}-flavor").innerText = COLONY_FLAVOR[colony_id]
    for ship in ships.values():
        document.getElementById(f"ship-{ship.id}-load-button").innerText = "Load Cargo"
        document.getElementById(f"ship-{ship.id}-load-button").addEventListener(
            "click", create_proxy(_make_load_handler(ship.id))
        )
        for colony_id, colony in ALL_COLONIES.items():
            button = document.getElementById(f"ship-{ship.id}-depart-{colony_id}-button")
            button.innerText = f"Depart to {colony['name']}"
            button.addEventListener("click", create_proxy(_make_depart_handler(ship.id, colony_id)))
        document.getElementById(f"ship-{ship.id}-automate-button").addEventListener(
            "click", create_proxy(_make_automate_handler(ship.id))
        )
        # J10 — every ship can be renamed, not just the purchasable ones.
        document.getElementById(f"ship-{ship.id}-rename-button").addEventListener(
            "click", create_proxy(_make_rename_handler(ship.id))
        )
        reset_button = document.getElementById(f"ship-{ship.id}-reset-name-button")
        if reset_button is not None:
            reset_button.addEventListener("click", create_proxy(_make_reset_name_handler(ship.id)))
        if ship.id in PURCHASABLE_SHIP_IDS:
            document.getElementById(f"ship-{ship.id}-purchase-button").addEventListener(
                "click", create_proxy(_make_purchase_ship_handler(ship.id))
            )
    for node_id in RESEARCH_NODES:
        document.getElementById(f"research-{node_id}-unlock-button").addEventListener(
            "click", create_proxy(_make_research_handler(node_id))
        )
    document.getElementById("fleet-priority-button").addEventListener(
        "click", create_proxy(_fleet_priority_toggle_handler)
    )
    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    document.getElementById("summary-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_summary)
    )
    document.getElementById("guild-accept-button").addEventListener("click", create_proxy(on_guild_accept))
    document.getElementById("guild-decline-button").addEventListener("click", create_proxy(on_guild_decline))
    document.getElementById("found-new-corporation-button").addEventListener(
        "click", create_proxy(on_found_new_corporation)
    )
    document.getElementById("hard-charter-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_hard_charter)
    )
    document.getElementById("charter-toggle-button").addEventListener("click", create_proxy(on_toggle_charter))
    document.getElementById("captains-toggle-button").addEventListener("click", create_proxy(on_toggle_captains))
    document.getElementById("blackout-toggle-button").addEventListener("click", create_proxy(on_toggle_blackout))
    for kind in BLACKOUT_INTEL:
        document.getElementById(f"blackout-buy-{kind}-button").addEventListener(
            "click", create_proxy(_make_blackout_buy_handler(kind))
        )
    for perk_id in CAPTAINS:
        document.getElementById(f"captain-{perk_id}-release-button").addEventListener(
            "click", create_proxy(_make_captain_release_handler(perk_id))
        )
        for ship_id in ships:
            document.getElementById(f"captain-{perk_id}-ship-{ship_id}-button").addEventListener(
                "click", create_proxy(_make_captain_assign_handler(perk_id, ship_id))
            )
    for perk_id in CHARTER_PERKS:
        document.getElementById(f"charter-perk-{perk_id}-buy-button").addEventListener(
            "click", create_proxy(_make_charter_perk_handler(perk_id))
        )
    # Explicit, not just relying on index.html's `hidden` attribute -- the
    # toast element is only otherwise touched by show_achievement_toast()/
    # its own hide callback (unlike every *panel*, which gets its `hidden`
    # state re-set on every render()), so it needs its own starting state
    # set here rather than trusting markup alone.
    toast = document.getElementById("achievement-toast")
    if toast is not None:
        toast.hidden = True
    notice_toast = document.getElementById("notice-toast")
    if notice_toast is not None:
        notice_toast.hidden = True
    _start_tick_loop()
    update_changelog_display()
    render()
    # A fresh session's already-earned achievements (there shouldn't be
    # any at this point, but a defensive baseline is cheap) shouldn't
    # toast on the very first render.
    global _previously_earned_ids
    _previously_earned_ids = _earned_snapshot()


_fresh_state = json.loads(json.dumps(get_state()))
setup()
