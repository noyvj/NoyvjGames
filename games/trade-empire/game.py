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

import json
import math

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

GOOD_LABEL = {
    ORE: "Ore", GRAIN: "Grain", MACHINERY: "Machinery", WATER: "Water", ENERGY: "Energy",
    RARE_METALS: "Rare Metals", BIOMASS: "Biomass", ISOTOPES: "Isotopes",
    CRYSTAL: "Crystal", POLYMER: "Polymer", ANTIMATTER: "Antimatter",
}

# Flat per-unit base sell price, before Milestone 4's market multiplier.
SELL_PRICE = {
    ORE: 8, GRAIN: 6, MACHINERY: 10, WATER: 5, ENERGY: 9,
    RARE_METALS: 14, BIOMASS: 8, ISOTOPES: 18,
    CRYSTAL: 20, POLYMER: 12, ANTIMATTER: 26,
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

# All colony metadata, every system -- used for lookups that must stay
# correct regardless of what's unlocked (colony_needing(),
# colony_producing(), labels). Which of these are actually *reachable*
# right now is a separate question, answered by active_colony_ids().
ALL_COLONIES = {**COLONIES, **EXPANSION_COLONIES, **RIFT_COLONIES}

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
}


class ColonyState:
    def __init__(self, colony_id):
        self.id = colony_id
        self.need_satisfaction = STARTING_NEED_SATISFACTION
        self.development_level = 1
        self.cumulative_delivered = 0.0
        self.secondary_need_satisfaction = STARTING_NEED_SATISFACTION

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
        return base

    def cargo_capacity(self):
        return round(CARGO_CAPACITY * self.output_multiplier())

    def decay(self):
        decay_rate = NEED_DECAY_PER_TICK
        if self.is_developed():
            decay_rate *= SPECIALIZATION[self.id]["decay_multiplier"]
        self.need_satisfaction = max(0.0, self.need_satisfaction - decay_rate)
        if self.is_developed():
            self.secondary_need_satisfaction = max(0.0, self.secondary_need_satisfaction - decay_rate)

    def deliver(self, qty):
        gain = qty * NEED_SATISFACTION_PER_UNIT_DELIVERED
        self.need_satisfaction = min(1.0, self.need_satisfaction + gain)
        self.cumulative_delivered += qty
        if self.cumulative_delivered >= DEVELOPMENT_THRESHOLD and self.development_level < 2:
            self.development_level = 2

    def deliver_secondary(self, qty):
        gain = qty * NEED_SATISFACTION_PER_UNIT_DELIVERED
        self.secondary_need_satisfaction = min(1.0, self.secondary_need_satisfaction + gain)


# Milestone 7 — 2D map v1: colonies as nodes, routes as lines. Drawn
# directly from Python via Pyodide's `js` module (canvas 2D context
# methods are just JS method calls, so no separate JS glue file is
# needed here despite the canvas requirement). Static layout and static
# routes for now — no moving ships until Milestone 11.
CANVAS_WIDTH = 620
CANVAS_HEIGHT = 300
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


def render_map():
    canvas = document.getElementById("map-canvas")
    ctx = canvas.getContext("2d")
    ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)
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


def current_sell_price(good):
    return max(1, round(SELL_PRICE[good] * market_multiplier[good]))


def apply_market_sale(good, qty):
    market_multiplier[good] = max(
        MIN_PRICE_MULTIPLIER, market_multiplier[good] - qty * MARKET_PRICE_DECAY_PER_UNIT_SOLD
    )
    if market_multiplier[good] < MARKET_CRASH_THRESHOLD:
        market_crash_ever[good] = True


def recover_market():
    for good in market_multiplier:
        market_multiplier[good] = min(
            MAX_PRICE_MULTIPLIER, market_multiplier[good] + MARKET_PRICE_RECOVERY_PER_TICK
        )


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
}
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


def active_colony_ids():
    """Every colony ID the player can currently interact with — the home
    system always, the Kepler Cluster once Galaxy Expansion is unlocked,
    and the Rift Colonies once Outer Reaches is. Everything reachability-
    sensitive (route drawing, depart-button validity, a ship's list of
    possible destinations) is scoped to this rather than to ALL_COLONIES
    directly."""
    ids = list(COLONIES)
    if galaxy_expansion_unlocked():
        ids += list(EXPANSION_COLONIES)
    if outer_reaches_unlocked():
        ids += list(RIFT_COLONIES)
    return ids


def can_unlock_research(node_id):
    node = RESEARCH_NODES[node_id]
    requires = node.get("requires")
    if requires is not None and requires not in unlocked_research:
        return False
    return node_id not in unlocked_research and research_points >= node["cost"]


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
    return True


def max_automated_ships():
    bonus = AUTOMATION_SLOT_RESEARCH_BONUS if "automation_slot" in unlocked_research else 0
    bonus += AUTOMATION_SLOT_2_RESEARCH_BONUS if "automation_slot_2" in unlocked_research else 0
    return MAX_AUTOMATED_SHIPS + bonus


def travel_ticks():
    reduction = FAST_SHIPS_TICK_REDUCTION if "fast_ships" in unlocked_research else 0
    return max(1, TRAVEL_TICKS - reduction)


def fleet_cargo_multiplier():
    return HAULER_CARGO_MULTIPLIER if "hauler" in unlocked_research else 1.0


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
        self.cargo_qty = round(colony_states[self.location].cargo_capacity() * fleet_cargo_multiplier())
        return True

    def other_colonies(self):
        """Every colony this ship could plausibly be sent to right now —
        anywhere reachable except wherever it's currently docked."""
        if not self.docked:
            return []
        return [c for c in active_colony_ids() if c != self.location]

    def _begin_transit(self, destination):
        self.origin = self.location
        self.destination = destination
        self.location = None
        self.transit_total_ticks = travel_ticks()
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
            profit = qty * current_sell_price(good)
            dest_state = colony_states[destination]
            if ALL_COLONIES[destination]["needs"] == good:
                dest_state.deliver(qty)
            elif dest_state.is_developed() and dest_state.secondary_need() == good:
                dest_state.deliver_secondary(qty)
            result = (good, qty, profit)
            self.total_earned += profit
            key = frozenset((self.origin, destination))
            if key == self.route_key:
                self.route_legs += 1
            else:
                self.route_key = key
                self.route_legs = 1
        self.location = destination
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
    global total_profit, seen_first_automation_callout
    ship = ships[ship_id]
    if not ship.purchased or ship.automated or not automation_slots_available() or total_profit < AUTOMATION_COST:
        return False
    total_profit -= AUTOMATION_COST
    ship.automated = True
    if not seen_first_automation_callout:
        seen_first_automation_callout = True
        show_notice_toast(
            "🚀 First automated ship! It'll load and depart on its own from here — "
            "automate more ships to scale the whole fleet up."
        )
    return True


def can_purchase_ship(ship_id):
    ship = ships[ship_id]
    if ship.purchased:
        return False
    if ship_id == "6" and not ships["5"].purchased:
        return False
    return total_profit >= SHIP_PURCHASE_COST[ship_id]


def purchase_ship(ship_id):
    """J6 — a one-time credit spend that unlocks a 5th/6th ship, same
    shape as automate_ship()'s one-time AUTOMATION_COST spend."""
    global total_profit
    if not can_purchase_ship(ship_id):
        return False
    total_profit -= SHIP_PURCHASE_COST[ship_id]
    ships[ship_id].purchased = True
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

    purchase_button = document.getElementById(f"ship-{ship.id}-purchase-button")
    purchase_button.hidden = False
    purchase_button.innerText = f"Purchase Ship ({SHIP_PURCHASE_COST[ship.id]})"
    purchase_button.disabled = not can_purchase_ship(ship.id)


def render_ship(ship):
    label_text = ship.name
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
        f"Automating costs {AUTOMATION_COST} credits and is permanent: "
        "there is no way to de-automate a ship afterward."
    )
    if ship.automated:
        automate_button.innerText = "Automated"
        automate_button.disabled = True
    else:
        automate_button.innerText = f"Automate ({AUTOMATION_COST})"
        automate_button.disabled = not automation_slots_available() or total_profit < AUTOMATION_COST


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
    )
    # J24 — a plain "needs met" average alongside the graph.
    hist = need_history.get(colony_id, [])
    if hist:
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
            f"Development: Level 1 ({state.cumulative_delivered:.0f}/{DEVELOPMENT_THRESHOLD:.0f} "
            f"{GOOD_LABEL[colony['needs']]} delivered to develop further)"
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


def _trend_sparkline_svg(history, css_class, now_label=None):
    """J12/J14 — an unlabeled inline-SVG polyline over a short rolling
    history; the point is the shape of the trend, not any exact value.
    Values are expected roughly in 0..1 (market multiplier, need
    satisfaction) so a fixed height mapping is enough -- no separate
    axis scaling needed."""
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
    return (
        f'<svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}" class="{css_class}" '
        f'aria-hidden="{"false" if now_label else "true"}"><polyline points="{" ".join(points)}" />{marker}</svg>'
    )


def render_market():
    for good in market_multiplier:
        price = current_sell_price(good)
        pct = market_multiplier[good] * 100
        display = document.getElementById(f"market-{good}-display")
        display.innerText = f"{GOOD_LABEL[good]}: {price} credits/unit ({pct:.0f}% of baseline)"
        display.className = "market-price"
        display.title = ""
        if market_multiplier[good] < 0.7:
            display.className += " market-price--crashed"
            # J20 — recovery ETA back to baseline at the flat per-tick rate
            # (further sales of this good would push it back down).
            eta = math.ceil(round((MAX_PRICE_MULTIPLIER - market_multiplier[good])
                                  / MARKET_PRICE_RECOVERY_PER_TICK, 6))
            display.title = (
                f"Crashed: about {eta} tick(s) to recover to baseline if nothing "
                f"more of it is sold."
            )
        document.getElementById(f"market-{good}-bar").style.width = f"{pct:.0f}%"
        # J12 — a small price-history sparkline alongside the bar.
        document.getElementById(f"market-{good}-sparkline").innerHTML = _trend_sparkline_svg(
            price_history.get(good, []), "price-sparkline", f"Now: {price} credits"
        )


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
            status_el.innerText = f"{node['label']} — {node['description']}"
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
            if requires is not None and requires not in unlocked_research:
                status_el.innerText += f" (requires {RESEARCH_NODES[requires]['label']})"
            unlock_button.hidden = False
            unlock_button.innerText = f"Research ({node['cost']})"
            unlock_button.disabled = not can_unlock_research(node_id)
            # J26 — say exactly what a locked node still needs.
            needs = []
            if requires is not None and requires not in unlocked_research:
                needs.append(f"unlock {RESEARCH_NODES[requires]['label']} first")
            if research_points < node["cost"]:
                needs.append(f"{node['cost'] - research_points:.0f} more research points")
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
    return set(RESEARCH_NODES) <= unlocked_research


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
    "background_galaxy_maxed": lambda: background_world_count() >= ENDGAME_BACKGROUND_WORLD_CAP,
}

# Progress readouts, only for achievements with a natural numeric scale-up
# — a plain earned/not-yet is the honest shape for the rest.
ACHIEVEMENT_PROGRESS = {
    "profit_10k": lambda: (int(max_profit_ever), PROFIT_10K_THRESHOLD),
    "profit_100k": lambda: (int(max_profit_ever), PROFIT_100K_THRESHOLD),
    "diversified_trader": lambda: (len(HOME_SYSTEM_GOODS & goods_sold_ever), len(HOME_SYSTEM_GOODS)),
    "background_galaxy_maxed": lambda: (background_world_count(), ENDGAME_BACKGROUND_WORLD_CAP),
}


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field. Always recomputed, never itself a save
    input."""
    return [entry["id"] for entry in ACHIEVEMENTS if ACHIEVEMENT_CHECKS[entry["id"]]()]


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
    return set(achievement_ids_earned())


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
seen_first_automation_callout = False


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
        lines.append(f"{GOOD_LABEL[good]} ({producer_name} → {consumer_name}): {total:,} credits{per_trip}{suffix}")
    return lines


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
    ]

    panel.innerHTML = ""
    for line in overview_lines:
        p = document.createElement("p")
        p.className = "summary-line"
        p.innerText = line
        panel.appendChild(p)

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


def render():
    # J22 -- targets the inner #profit-display-text span, not #profit-display
    # itself: the sale-spark burst appends transient children to the sibling
    # #sale-spark-container inside #profit-display, and overwriting
    # #profit-display's own innerText every render would wipe those children
    # out before their one-shot animation ever gets a frame to paint.
    document.getElementById("profit-display-text").innerText = f"Total profit: {total_profit} credits"
    document.getElementById("sale-log").innerText = sale_log[-1] if sale_log else "No sales yet."
    document.getElementById("automation-slots-display").innerText = (
        f"Automation slots: {automated_ship_count()}/{max_automated_ships()} used"
    )
    render_fleet_priority()
    render_endgame()
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

    update_achievements_display()
    _sync_earned_and_toast()
    update_summary_display()


def _make_load_handler(ship_id):
    def handler(event=None):
        ships[ship_id].load()
        render()
    return handler


def _make_purchase_ship_handler(ship_id):
    def handler(event=None):
        purchase_ship(ship_id)
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


def _confirm_dialog_ask(action_id, message, confirm_label, on_confirm):
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
    confirm_dialog.ask(
        id=action_id,
        message=message,
        confirmLabel=confirm_label,
        onConfirm=create_proxy(on_confirm),
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
                f"Automate this ship for {AUTOMATION_COST} credits? "
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
    if container is None:
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
    global total_profit, research_points, total_sales_count, max_profit_ever
    research_points += RESEARCH_PER_TICK
    for ship in ships.values():
        result = ship.advance_transit()
        if result is not None:
            good, qty, profit = result
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
    run_automation()
    for colony_state in colony_states.values():
        colony_state.decay()
    recover_market()

    # J15 — idle-ticks bookkeeping: counts up only while a ship is
    # purchased, manual, docked, and empty; anything else (in transit,
    # loaded, automated, unpurchased) resets it to zero.
    for ship in ships.values():
        if ship.purchased and not ship.automated and ship.docked and not ship.loaded:
            ship.idle_ticks += 1
        else:
            ship.idle_ticks = 0

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
    if endgame_reached:
        ticks_since_endgame += 1
        total_profit += background_revenue_this_tick()

    max_profit_ever = max(max_profit_ever, total_profit)

    render()


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
                "name": ship.name,
                "idle_ticks": ship.idle_ticks,
                "route_key": sorted(ship.route_key) if ship.route_key else None,
                "route_legs": ship.route_legs,
                "total_earned": ship.total_earned,
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
        "seen_first_automation_callout": seen_first_automation_callout,
        # Write-only projection (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) — always
        # freshly recomputed here, never read back in load_state() below.
        "achievements_earned": achievement_ids_earned(),
    }


def load_state(data):
    """Exact inverse of get_state(). Colony state for the Kepler Cluster
    is (re)created here if the save has galaxy_expansion unlocked but the
    live module hasn't gotten there yet — mirroring what unlock_research()
    itself does — so a save loaded fresh into a brand-new session doesn't
    leave Fleet Priority's most_urgent_colony() unable to see colonies the
    save says should exist."""
    global total_profit, sale_log, research_points, unlocked_research
    global fleet_priority_enabled, endgame_reached, ticks_since_endgame
    global total_sales_count, max_profit_ever, goods_sold_ever, ever_repositioned
    global _previously_earned_ids, seen_first_automation_callout

    unlocked_research = set(data.get("unlocked_research", unlocked_research))

    if galaxy_expansion_unlocked():
        for colony_id in EXPANSION_COLONIES:
            if colony_id not in colony_states:
                colony_states[colony_id] = ColonyState(colony_id)
    if outer_reaches_unlocked():
        for colony_id in RIFT_COLONIES:
            if colony_id not in colony_states:
                colony_states[colony_id] = ColonyState(colony_id)

    saved_colony_states = data.get("colony_states", {})
    for colony_id, state in colony_states.items():
        saved = saved_colony_states.get(colony_id)
        if not saved:
            continue
        state.need_satisfaction = saved.get("need_satisfaction", state.need_satisfaction)
        state.development_level = saved.get("development_level", state.development_level)
        state.cumulative_delivered = saved.get("cumulative_delivered", state.cumulative_delivered)
        state.secondary_need_satisfaction = saved.get(
            "secondary_need_satisfaction", state.secondary_need_satisfaction
        )

    saved_ships = data.get("ships", {})
    for ship_id, ship in ships.items():
        saved = saved_ships.get(ship_id)
        if not saved:
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
        ship.name = saved.get("name", ship.name)
        ship.idle_ticks = saved.get("idle_ticks", ship.idle_ticks)
        saved_key = saved.get("route_key")
        ship.route_key = frozenset(saved_key) if saved_key else None
        ship.route_legs = saved.get("route_legs", 0)
        ship.total_earned = saved.get("total_earned", 0)

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
    seen_first_automation_callout = data.get(
        "seen_first_automation_callout", seen_first_automation_callout
    )
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


def setup():
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
    setInterval(create_proxy(tick), TICK_INTERVAL_MS)
    update_changelog_display()
    render()
    # A fresh session's already-earned achievements (there shouldn't be
    # any at this point, but a defensive baseline is cheap) shouldn't
    # toast on the very first render.
    global _previously_earned_ids
    _previously_earned_ids = _earned_snapshot()


setup()
