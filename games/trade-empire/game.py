"""Trade Empire — Interstellar Trade Empire (working title).

Runs in-browser via Pyodide. Milestone 1: a founding-contract intro, one
ship, one manual route between two colonies. The player loads cargo,
departs, waits out a short transit, and the ship auto-sells on arrival —
profit ticks in as a running total. Fully manual: nothing runs itself yet,
that's what later automation milestones are for.
"""

from js import document, setInterval
from pyodide.ffi import create_proxy

TICK_INTERVAL_MS = 1000
TRAVEL_TICKS = 5
CARGO_CAPACITY = 10

ORE = "ore"
GRAIN = "grain"

GOOD_LABEL = {ORE: "Ore", GRAIN: "Grain"}

# Flat per-unit sell price, paid by the colony that *needs* the good on
# arrival. No market saturation yet (that's Milestone 4) — a fixed price
# keeps this milestone's loop legible on its own.
SELL_PRICE = {ORE: 8, GRAIN: 6}

COLONIES = {
    "aurum": {"name": "Aurum Station", "produces": ORE, "needs": GRAIN},
    "verdant": {"name": "Verdant Reach", "produces": GRAIN, "needs": ORE},
}


def other_colony(colony_id):
    return "verdant" if colony_id == "aurum" else "aurum"


class Ship:
    def __init__(self):
        self.location = "aurum"  # colony id, or None while in transit
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
        self.cargo_qty = CARGO_CAPACITY
        return True

    def depart(self):
        if not self.docked or not self.loaded:
            return False
        self.destination = other_colony(self.location)
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
        self.location = self.destination
        self.destination = None
        self.cargo_good = None
        self.cargo_qty = 0
        return (good, qty, profit)


ship = Ship()
total_profit = 0
sale_log = []  # most recent sale message, for the status line


def sell_summary(good, qty, profit, colony_id):
    colony_name = COLONIES[colony_id]["name"]
    return f"Sold {qty} {GOOD_LABEL[good]} at {colony_name} for {profit} credits."


def status_text():
    if ship.in_transit:
        dest_name = COLONIES[ship.destination]["name"]
        return f"In transit to {dest_name} — {ship.transit_ticks_remaining} tick(s) remaining."
    colony = COLONIES[ship.location]
    if ship.loaded:
        return f"Docked at {colony['name']}, loaded with {ship.cargo_qty} {GOOD_LABEL[ship.cargo_good]}. Ready to depart."
    return f"Docked at {colony['name']}. Load {GOOD_LABEL[colony['produces']]} to prepare a run."


def render():
    document.getElementById("ship-status").innerText = status_text()
    document.getElementById("profit-display").innerText = f"Total profit: {total_profit} credits"
    document.getElementById("sale-log").innerText = sale_log[-1] if sale_log else "No sales yet."

    load_button = document.getElementById("load-button")
    depart_button = document.getElementById("depart-button")
    load_button.disabled = not (ship.docked and not ship.loaded)
    depart_button.disabled = not (ship.docked and ship.loaded)


def on_load(event=None):
    ship.load()
    render()


def on_depart(event=None):
    ship.depart()
    render()


def tick(event=None):
    global total_profit
    result = ship.advance_transit()
    if result is not None:
        good, qty, profit = result
        total_profit += profit
        sale_log.append(sell_summary(good, qty, profit, ship.location))
    render()


def setup():
    load_button = document.getElementById("load-button")
    depart_button = document.getElementById("depart-button")
    load_button.innerText = "Load Cargo"
    depart_button.innerText = "Depart"
    load_button.addEventListener("click", create_proxy(on_load))
    depart_button.addEventListener("click", create_proxy(on_depart))
    setInterval(create_proxy(tick), TICK_INTERVAL_MS)
    render()


setup()
