"""Trade Empire — Interstellar Trade Empire (working title).

Runs in-browser via Pyodide. Milestone 1: a founding-contract intro, one
ship, one manual route between two colonies. Milestone 2: a third colony
and a second ship — routes are no longer a fixed pair, each ship can be
manually sent to whichever colony the player chooses, so the player is
now actively deciding "which route" as well as "when to depart."
"""

from js import document, setInterval
from pyodide.ffi import create_proxy

TICK_INTERVAL_MS = 1000
TRAVEL_TICKS = 5
CARGO_CAPACITY = 10

ORE = "ore"
GRAIN = "grain"
MACHINERY = "machinery"

GOOD_LABEL = {ORE: "Ore", GRAIN: "Grain", MACHINERY: "Machinery"}

# Flat per-unit sell price, paid by whichever colony a ship arrives at.
# No market saturation yet (Milestone 4) and "needs" isn't mechanically
# enforced yet either (Milestone 3) — a flat price keeps this
# milestone's scope to route/ship assignment, not economics.
SELL_PRICE = {ORE: 8, GRAIN: 6, MACHINERY: 10}

# Milestone 2: a third colony turns the fixed A<->B pair into a real
# triangle. Each colony's "needs" field is flavor for now (Milestone 3
# makes it matter mechanically) but already forms a genuine cycle:
# Aurum's ore feeds Ferrum, Ferrum's machinery feeds Verdant, Verdant's
# grain feeds Aurum.
COLONIES = {
    "aurum": {"name": "Aurum Station", "produces": ORE, "needs": GRAIN},
    "verdant": {"name": "Verdant Reach", "produces": GRAIN, "needs": MACHINERY},
    "ferrum": {"name": "Ferrum Forge", "produces": MACHINERY, "needs": ORE},
}

# Milestone 3 — minor flavor text per colony, shown in the colony panel.
COLONY_FLAVOR = {
    "aurum": "A wind-scoured mining outpost — good ore, poor soil. Every grain shipment matters.",
    "verdant": "Lush terraces feed the sector, but its factories run on imported machinery.",
    "ferrum": "The forges never stop, but they run on ore that has to come from somewhere else.",
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


class ColonyState:
    def __init__(self, colony_id):
        self.id = colony_id
        self.need_satisfaction = STARTING_NEED_SATISFACTION

    def output_multiplier(self):
        return MIN_OUTPUT_MULTIPLIER + self.need_satisfaction * (
            MAX_OUTPUT_MULTIPLIER - MIN_OUTPUT_MULTIPLIER
        )

    def cargo_capacity(self):
        return round(CARGO_CAPACITY * self.output_multiplier())

    def decay(self):
        self.need_satisfaction = max(0.0, self.need_satisfaction - NEED_DECAY_PER_TICK)

    def deliver(self, qty):
        gain = qty * NEED_SATISFACTION_PER_UNIT_DELIVERED
        self.need_satisfaction = min(1.0, self.need_satisfaction + gain)


colony_states = {colony_id: ColonyState(colony_id) for colony_id in COLONIES}


class Ship:
    def __init__(self, ship_id, start_colony):
        self.id = ship_id
        self.location = start_colony  # colony id, or None while in transit
        self.destination = None  # colony id being traveled to, while in transit
        self.cargo_good = None
        self.cargo_qty = 0
        self.transit_ticks_remaining = 0

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
        self.cargo_qty = colony_states[self.location].cargo_capacity()
        return True

    def other_colonies(self):
        """Every colony this ship could plausibly be sent to right now —
        anywhere except wherever it's currently docked."""
        if not self.docked:
            return []
        return [c for c in COLONIES if c != self.location]

    def depart(self, destination):
        if not self.docked or not self.loaded:
            return False
        if destination == self.location or destination not in COLONIES:
            return False
        self.destination = destination
        self.location = None
        self.transit_ticks_remaining = TRAVEL_TICKS
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
        profit = qty * SELL_PRICE[good]
        destination = self.destination
        if COLONIES[destination]["needs"] == good:
            colony_states[destination].deliver(qty)
        self.location = destination
        self.destination = None
        self.cargo_good = None
        self.cargo_qty = 0
        return (good, qty, profit)


ships = {
    "1": Ship("1", "aurum"),
    "2": Ship("2", "verdant"),
}
total_profit = 0
sale_log = []  # most recent sale message, for the status line


def sell_summary(good, qty, profit, colony_id):
    colony_name = COLONIES[colony_id]["name"]
    return f"Sold {qty} {GOOD_LABEL[good]} at {colony_name} for {profit} credits."


def ship_status_text(ship):
    if ship.in_transit:
        dest_name = COLONIES[ship.destination]["name"]
        return f"In transit to {dest_name} — {ship.transit_ticks_remaining} tick(s) remaining."
    colony = COLONIES[ship.location]
    if ship.loaded:
        return f"Docked at {colony['name']}, loaded with {ship.cargo_qty} {GOOD_LABEL[ship.cargo_good]}. Choose a destination."
    return f"Docked at {colony['name']}. Load {GOOD_LABEL[colony['produces']]} to prepare a run."


def render_ship(ship):
    document.getElementById(f"ship-{ship.id}-status").innerText = ship_status_text(ship)

    load_button = document.getElementById(f"ship-{ship.id}-load-button")
    load_button.disabled = not (ship.docked and not ship.loaded)

    for colony_id in COLONIES:
        depart_button = document.getElementById(f"ship-{ship.id}-depart-{colony_id}-button")
        depart_button.hidden = not (ship.docked and ship.loaded and colony_id != ship.location)
        depart_button.disabled = not (ship.docked and ship.loaded and colony_id != ship.location)


def render_colony(colony_id):
    colony = COLONIES[colony_id]
    state = colony_states[colony_id]
    document.getElementById(f"colony-{colony_id}-need-display").innerText = (
        f"{colony['name']}: needs {GOOD_LABEL[colony['needs']]} — "
        f"{state.need_satisfaction * 100:.0f}% satisfied "
        f"(output x{state.output_multiplier():.2f})"
    )
    document.getElementById(f"colony-{colony_id}-need-bar").style.width = (
        f"{state.need_satisfaction * 100:.0f}%"
    )


def render():
    document.getElementById("profit-display").innerText = f"Total profit: {total_profit} credits"
    document.getElementById("sale-log").innerText = sale_log[-1] if sale_log else "No sales yet."
    for ship in ships.values():
        render_ship(ship)
    for colony_id in COLONIES:
        render_colony(colony_id)


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


def tick(event=None):
    global total_profit
    for ship in ships.values():
        result = ship.advance_transit()
        if result is not None:
            good, qty, profit = result
            total_profit += profit
            sale_log.append(sell_summary(good, qty, profit, ship.location))
    for colony_state in colony_states.values():
        colony_state.decay()
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
    setInterval(create_proxy(tick), TICK_INTERVAL_MS)
    render()


setup()
