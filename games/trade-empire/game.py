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
colony, when Fleet Priority mode is switched on.
"""

import math

from js import document, setInterval
from pyodide.ffi import create_proxy

TICK_INTERVAL_MS = 1000
TRAVEL_TICKS = 5
CARGO_CAPACITY = 10

ORE = "ore"
GRAIN = "grain"
MACHINERY = "machinery"
WATER = "water"
ENERGY = "energy"

GOOD_LABEL = {ORE: "Ore", GRAIN: "Grain", MACHINERY: "Machinery", WATER: "Water", ENERGY: "Energy"}

# Flat per-unit base sell price, before Milestone 4's market multiplier.
SELL_PRICE = {ORE: 8, GRAIN: 6, MACHINERY: 10, WATER: 5, ENERGY: 9}

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

# Milestone 3 — minor flavor text per colony, shown in the colony panel.
COLONY_FLAVOR = {
    "aurum": "A wind-scoured mining outpost — good ore, poor soil. Every grain shipment matters.",
    "verdant": "Lush terraces feed the sector, but its factories run on imported machinery.",
    "ferrum": "The forges never stop, but they run on ore that has to come from somewhere else.",
    "cryo": "A frozen moon's ice reserves, tapped for water — but the pumps need power to run at all.",
    "helion": "A solar array with power to spare, and nothing to cool it but water shipped in from Cryo.",
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
CANVAS_SIZE = 300
NODE_RADIUS = 22
NODE_POSITIONS = {
    "aurum": (150, 36),
    "verdant": (262, 118),
    "ferrum": (218, 252),
    "cryo": (82, 252),
    "helion": (38, 118),
}
NODE_COLOR = "#3a5a9c"
EDGE_COLOR = "#3a3f5c"
LABEL_COLOR = "#e8e9f0"


def route_edges():
    """One directed edge per colony, to whichever colony needs its
    produced good — the same relationship colony_needing() already
    encodes, just read as a full list for drawing."""
    edges = []
    for colony_id, colony in COLONIES.items():
        destination = colony_needing(colony["produces"])
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
    ctx.clearRect(0, 0, CANVAS_SIZE, CANVAS_SIZE)

    ctx.strokeStyle = EDGE_COLOR
    ctx.lineWidth = 2
    for from_id, to_id in route_edges():
        x1, y1 = NODE_POSITIONS[from_id]
        x2, y2 = NODE_POSITIONS[to_id]
        ctx.beginPath()
        ctx.moveTo(x1, y1)
        ctx.lineTo(x2, y2)
        ctx.stroke()

    for colony_id, (x, y) in NODE_POSITIONS.items():
        ctx.fillStyle = NODE_COLOR
        ctx.beginPath()
        ctx.arc(x, y, NODE_RADIUS, 0, 2 * math.pi)
        ctx.fill()

        ctx.fillStyle = LABEL_COLOR
        ctx.font = "11px sans-serif"
        ctx.textAlign = "center"
        ctx.textBaseline = "middle"
        ctx.fillText(COLONIES[colony_id]["name"].split()[0], x, y)

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

market_multiplier = {ORE: 1.0, GRAIN: 1.0, MACHINERY: 1.0, WATER: 1.0, ENERGY: 1.0}


def current_sell_price(good):
    return max(1, round(SELL_PRICE[good] * market_multiplier[good]))


def apply_market_sale(good, qty):
    market_multiplier[good] = max(
        MIN_PRICE_MULTIPLIER, market_multiplier[good] - qty * MARKET_PRICE_DECAY_PER_UNIT_SOLD
    )


def recover_market():
    for good in market_multiplier:
        market_multiplier[good] = min(
            MAX_PRICE_MULTIPLIER, market_multiplier[good] + MARKET_PRICE_RECOVERY_PER_TICK
        )


def colony_needing(good):
    """The one colony whose need this good satisfies — every good in this
    world is needed by exactly one colony, so there's always a single
    unambiguous "correct" destination for a load of it. Milestone 6's
    autopilot uses this to decide where to send itself."""
    for colony_id, colony in COLONIES.items():
        if colony["needs"] == good:
            return colony_id
    return None


def colony_producing(good):
    """Reverse of colony_needing() — the one colony that makes this good.
    Milestone 12 uses this to find where an idle automated ship should
    reposition to when repointing itself at the fleet's most urgent
    need."""
    for colony_id, colony in COLONIES.items():
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
}
AUTOMATION_SLOT_RESEARCH_BONUS = 1
FAST_SHIPS_TICK_REDUCTION = 1
HAULER_CARGO_MULTIPLIER = 1.5

research_points = 0.0
unlocked_research = set()


def can_unlock_research(node_id):
    return node_id not in unlocked_research and research_points >= RESEARCH_NODES[node_id]["cost"]


def unlock_research(node_id):
    global research_points
    if not can_unlock_research(node_id):
        return False
    research_points -= RESEARCH_NODES[node_id]["cost"]
    unlocked_research.add(node_id)
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
        self.cargo_good = COLONIES[self.location]["produces"]
        self.cargo_qty = round(colony_states[self.location].cargo_capacity() * fleet_cargo_multiplier())
        return True

    def other_colonies(self):
        """Every colony this ship could plausibly be sent to right now —
        anywhere except wherever it's currently docked."""
        if not self.docked:
            return []
        return [c for c in COLONIES if c != self.location]

    def _begin_transit(self, destination):
        self.origin = self.location
        self.destination = destination
        self.location = None
        self.transit_total_ticks = travel_ticks()
        self.transit_ticks_remaining = self.transit_total_ticks

    def depart(self, destination):
        if not self.docked or not self.loaded:
            return False
        if destination == self.location or destination not in COLONIES:
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
        if destination == self.location or destination not in COLONIES:
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
            if COLONIES[destination]["needs"] == good:
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
    for ship in ships.values():
        if not ship.automated or not ship.docked:
            continue
        if not ship.loaded:
            if fleet_priority_enabled:
                urgent_good = COLONIES[most_urgent_colony()]["needs"]
                producer = colony_producing(urgent_good)
                if producer and producer != ship.location and ship.reposition(producer):
                    continue
            ship.load()
        else:
            destination = colony_needing(ship.cargo_good)
            if destination and destination != ship.location:
                ship.depart(destination)


def sell_summary(good, qty, profit, colony_id):
    colony_name = COLONIES[colony_id]["name"]
    return f"Sold {qty} {GOOD_LABEL[good]} at {colony_name} for {profit} credits."


def ship_status_text(ship):
    if ship.in_transit:
        dest_name = COLONIES[ship.destination]["name"]
        prefix = "Automated — in transit" if ship.automated else "In transit"
        return f"{prefix} to {dest_name} — {ship.transit_ticks_remaining} tick(s) remaining."
    colony = COLONIES[ship.location]
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

    for colony_id in COLONIES:
        depart_button = document.getElementById(f"ship-{ship.id}-depart-{colony_id}-button")
        applicable = ship.docked and ship.loaded and colony_id != ship.location
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
    colony = COLONIES[colony_id]
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


def render():
    document.getElementById("profit-display").innerText = f"Total profit: {total_profit} credits"
    document.getElementById("sale-log").innerText = sale_log[-1] if sale_log else "No sales yet."
    document.getElementById("automation-slots-display").innerText = (
        f"Automation slots: {automated_ship_count()}/{max_automated_ships()} used"
    )
    render_fleet_priority()
    render_research()
    render_map()
    for ship in ships.values():
        render_ship(ship)
    for colony_id in COLONIES:
        render_colony(colony_id)
    render_market()


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
    global total_profit, research_points
    research_points += RESEARCH_PER_TICK
    for ship in ships.values():
        result = ship.advance_transit()
        if result is not None:
            good, qty, profit = result
            total_profit += profit
            sale_log.append(sell_summary(good, qty, profit, ship.location))
            apply_market_sale(good, qty)
    run_automation()
    for colony_state in colony_states.values():
        colony_state.decay()
    recover_market()
    render()


def setup():
    for colony_id, colony in COLONIES.items():
        document.getElementById(f"colony-{colony_id}-name").innerText = colony["name"]
        document.getElementById(f"colony-{colony_id}-flavor").innerText = COLONY_FLAVOR[colony_id]
    for ship in ships.values():
        document.getElementById(f"ship-{ship.id}-load-button").innerText = "Load Cargo"
        document.getElementById(f"ship-{ship.id}-load-button").addEventListener(
            "click", create_proxy(_make_load_handler(ship.id))
        )
        for colony_id, colony in COLONIES.items():
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
    setInterval(create_proxy(tick), TICK_INTERVAL_MS)
    render()


setup()
