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

GOOD_LABEL = {
    ORE: "Ore", GRAIN: "Grain", MACHINERY: "Machinery", WATER: "Water", ENERGY: "Energy",
    RARE_METALS: "Rare Metals", BIOMASS: "Biomass", ISOTOPES: "Isotopes",
}

# Flat per-unit base sell price, before Milestone 4's market multiplier.
SELL_PRICE = {
    ORE: 8, GRAIN: 6, MACHINERY: 10, WATER: 5, ENERGY: 9,
    RARE_METALS: 14, BIOMASS: 8, ISOTOPES: 18,
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

# All colony metadata, both systems -- used for lookups that must stay
# correct regardless of what's unlocked (colony_needing(),
# colony_producing(), labels). Which of these are actually *reachable*
# right now is a separate question, answered by active_colony_ids().
ALL_COLONIES = {**COLONIES, **EXPANSION_COLONIES}

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
CANVAS_WIDTH = 460
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
    # home system's pentagon rather than crowded into it.
    "kepler_a": (390, 50),
    "kepler_b": (430, 190),
    "kepler_c": (350, 230),
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

    for ship in ships.values():
        x, y = ship_map_position(ship)
        ctx.fillStyle = AUTOMATED_SHIP_COLOR if ship.automated else MANUAL_SHIP_COLOR
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
}


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
}
AUTOMATION_SLOT_RESEARCH_BONUS = 1
FAST_SHIPS_TICK_REDUCTION = 1
HAULER_CARGO_MULTIPLIER = 1.5

research_points = 0.0
unlocked_research = set()


def galaxy_expansion_unlocked():
    return "galaxy_expansion" in unlocked_research


def active_colony_ids():
    """Every colony ID the player can currently interact with — the
    home system always, plus the Kepler Cluster once its research node
    is unlocked. Everything reachability-sensitive (route drawing,
    depart-button validity, a ship's list of possible destinations)
    is scoped to this rather than to ALL_COLONIES directly."""
    ids = list(COLONIES)
    if galaxy_expansion_unlocked():
        ids += list(EXPANSION_COLONIES)
    return ids


def can_unlock_research(node_id):
    return node_id not in unlocked_research and research_points >= RESEARCH_NODES[node_id]["cost"]


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
    return True


def max_automated_ships():
    bonus = AUTOMATION_SLOT_RESEARCH_BONUS if "automation_slot" in unlocked_research else 0
    return MAX_AUTOMATED_SHIPS + bonus


def travel_ticks():
    reduction = FAST_SHIPS_TICK_REDUCTION if "fast_ships" in unlocked_research else 0
    return max(1, TRAVEL_TICKS - reduction)


def fleet_cargo_multiplier():
    return HAULER_CARGO_MULTIPLIER if "hauler" in unlocked_research else 1.0


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
        if not self.docked or self.loaded:
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
        if not self.docked or not self.loaded:
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
        self.location = destination
        self.origin = None
        self.destination = None
        self.cargo_good = None
        self.cargo_qty = 0
        return result


ships = {
    "1": Ship("1", "aurum"),
    "2": Ship("2", "verdant"),
    "3": Ship("3", "ferrum"),
    "4": Ship("4", "cryo"),
}
total_profit = 0
sale_log = []  # most recent sale message, for the status line

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
    if ship.automated or not automation_slots_available() or total_profit < AUTOMATION_COST:
        return False
    total_profit -= AUTOMATION_COST
    ship.automated = True
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
    return f"Docked at {colony['name']}. Load {GOOD_LABEL[colony['produces']]} to prepare a run."


def render_ship(ship):
    document.getElementById(f"ship-{ship.id}-status").innerText = ship_status_text(ship)

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


def render_market():
    for good in market_multiplier:
        price = current_sell_price(good)
        pct = market_multiplier[good] * 100
        display = document.getElementById(f"market-{good}-display")
        display.innerText = f"{GOOD_LABEL[good]}: {price} credits/unit ({pct:.0f}% of baseline)"
        display.className = "market-price"
        if market_multiplier[good] < 0.7:
            display.className += " market-price--crashed"
        document.getElementById(f"market-{good}-bar").style.width = f"{pct:.0f}%"


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
            unlock_button.hidden = False
            unlock_button.innerText = f"Research ({node['cost']})"
            unlock_button.disabled = not can_unlock_research(node_id)


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

ACHIEVEMENT_TOAST_DURATION_MS = 4000


def _earned_snapshot():
    return set(achievement_ids_earned())


def show_achievement_toast(message):
    global _toast_hide_proxy
    toast = document.getElementById("achievement-toast")
    if toast is None:
        return
    toast.innerText = message
    toast.hidden = False
    toast.classList.add("achievement-toast--visible")

    if _toast_hide_proxy is not None:
        _toast_hide_proxy.destroy()
        _toast_hide_proxy = None

    def _hide():
        global _toast_hide_proxy
        toast.classList.remove("achievement-toast--visible")
        toast.hidden = True
        if _toast_hide_proxy is not None:
            _toast_hide_proxy.destroy()
            _toast_hide_proxy = None

    _toast_hide_proxy = create_proxy(_hide)
    setTimeout(_toast_hide_proxy, ACHIEVEMENT_TOAST_DURATION_MS)


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
    hub_link.href = "../../index.html"
    hub_link.innerText = "View achievements across every game →"
    panel.appendChild(hub_link)


def render():
    document.getElementById("profit-display").innerText = f"Total profit: {total_profit} credits"
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

    update_achievements_display()
    _sync_earned_and_toast()


def _make_load_handler(ship_id):
    def handler(event=None):
        ships[ship_id].load()
        render()
    return handler


def _make_depart_handler(ship_id, destination):
    def handler(event=None):
        ships[ship_id].depart(destination)
        render()
    return handler


def _make_automate_handler(ship_id):
    def handler(event=None):
        automate_ship(ship_id)
        render()
    return handler


def _make_research_handler(node_id):
    def handler(event=None):
        unlock_research(node_id)
        render()
    return handler


def _fleet_priority_toggle_handler(event=None):
    set_fleet_priority(not fleet_priority_enabled)
    render()


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
            sale_log.append(sell_summary(good, qty, profit, ship.location))
            apply_market_sale(good, qty)
    run_automation()
    for colony_state in colony_states.values():
        colony_state.decay()
    recover_market()

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
    global _previously_earned_ids

    unlocked_research = set(data.get("unlocked_research", unlocked_research))

    if galaxy_expansion_unlocked():
        for colony_id in EXPANSION_COLONIES:
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
    # Explicit, not just relying on index.html's `hidden` attribute -- the
    # toast element is only otherwise touched by show_achievement_toast()/
    # its own hide callback (unlike every *panel*, which gets its `hidden`
    # state re-set on every render()), so it needs its own starting state
    # set here rather than trusting markup alone.
    toast = document.getElementById("achievement-toast")
    if toast is not None:
        toast.hidden = True
    setInterval(create_proxy(tick), TICK_INTERVAL_MS)
    render()
    # A fresh session's already-earned achievements (there shouldn't be
    # any at this point, but a defensive baseline is cheap) shouldn't
    # toast on the very first render.
    global _previously_earned_ids
    _previously_earned_ids = _earned_snapshot()


setup()
