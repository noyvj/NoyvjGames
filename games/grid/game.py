"""Grid — Energy Transition Game.

Runs in-browser via Pyodide. Milestone 1: the core turn-based loop —
demand growth, funds, six plant types to build/retire, and capacity-based
revenue on round advance. Emissions, cost curves, and disruption events
land in later milestones.
"""

from js import document
from pyodide.ffi import create_proxy

STARTING_FUNDS = 500
STARTING_DEMAND = 100
DEMAND_GROWTH_PER_ROUND = 10
REVENUE_PER_UNIT_MET = 2
REFUND_FRACTION = 0.5

# Order matters for rendering — cheapest/dirtiest first, mirroring the
# real-world build order the game wants players to eventually move away
# from.
PLANT_TYPES = ["coal", "gas", "nuclear", "solar", "wind", "hydro"]

PLANT_LABEL = {
    "coal": "Coal",
    "gas": "Gas",
    "nuclear": "Nuclear",
    "solar": "Solar",
    "wind": "Wind",
    "hydro": "Hydro",
}

# Flat, un-degraded costs and generation capacity per unit. Renewable
# cost decay is Milestone 2's job.
PLANT_BASE_COST = {
    "coal": 50,
    "gas": 40,
    "nuclear": 200,
    "solar": 80,
    "wind": 70,
    "hydro": 150,
}

PLANT_CAPACITY = {
    "coal": 20,
    "gas": 15,
    "nuclear": 100,
    "solar": 10,
    "wind": 12,
    "hydro": 40,
}

# Emissions produced per unit of capacity, per round, while that capacity
# is part of the fleet. Nuclear counts as zero-emission but — realistically,
# and per the plan's framing — isn't part of the renewable cost-curve
# below; its cost stays flat.
EMISSIONS_FACTOR = {
    "coal": 3.0,
    "gas": 1.5,
    "nuclear": 0.0,
    "solar": 0.0,
    "wind": 0.0,
    "hydro": 0.0,
}

RENEWABLE_TYPES = {"solar", "wind", "hydro"}

# Wright's-law-style learning curve: each renewable unit ever built (not
# just currently standing — retiring one doesn't erase the learning)
# permanently makes the next one of that type a little cheaper, floored so
# it never becomes free.
RENEWABLE_COST_DECAY = 0.95
MIN_COST_MULTIPLIER = 0.4


class GridState:
    def __init__(self):
        self.round_number = 1
        self.demand = STARTING_DEMAND
        self.funds = STARTING_FUNDS
        self.plant_counts = {t: 0 for t in PLANT_TYPES}
        self.cumulative_built = {t: 0 for t in PLANT_TYPES}
        self.emissions = 0.0

    def plant_cost(self, plant_type):
        base = PLANT_BASE_COST[plant_type]
        if plant_type not in RENEWABLE_TYPES:
            return base
        multiplier = max(
            MIN_COST_MULTIPLIER,
            RENEWABLE_COST_DECAY ** self.cumulative_built[plant_type],
        )
        return base * multiplier

    def total_capacity(self):
        return sum(self.plant_counts[t] * PLANT_CAPACITY[t] for t in PLANT_TYPES)

    def fossil_capacity(self):
        return sum(self.plant_counts[t] * PLANT_CAPACITY[t] for t in ("coal", "gas"))

    def fossil_share(self):
        total = self.total_capacity()
        if total == 0:
            return 0.0
        return self.fossil_capacity() / total

    def emissions_this_round(self):
        return sum(
            self.plant_counts[t] * PLANT_CAPACITY[t] * EMISSIONS_FACTOR[t]
            for t in PLANT_TYPES
        )

    def build_plant(self, plant_type):
        cost = self.plant_cost(plant_type)
        if self.funds < cost:
            return False
        self.funds -= cost
        self.plant_counts[plant_type] += 1
        self.cumulative_built[plant_type] += 1
        return True

    def retire_plant(self, plant_type):
        if self.plant_counts[plant_type] <= 0:
            return False
        self.plant_counts[plant_type] -= 1
        self.funds += PLANT_BASE_COST[plant_type] * REFUND_FRACTION
        return True

    def advance_round(self):
        met_demand = min(self.total_capacity(), self.demand)
        self.funds += met_demand * REVENUE_PER_UNIT_MET
        self.emissions += self.emissions_this_round()
        self.round_number += 1
        self.demand += DEMAND_GROWTH_PER_ROUND


state = GridState()


def render():
    document.getElementById("round-display").innerText = f"Round {state.round_number}"
    document.getElementById("demand-display").innerText = f"Demand: {state.demand}"
    document.getElementById("funds-display").innerText = f"Funds: {state.funds:.0f}"
    document.getElementById("capacity-display").innerText = f"Capacity: {state.total_capacity()}"
    document.getElementById("emissions-display").innerText = f"Emissions: {state.emissions:.0f}"
    document.getElementById("fossil-share-display").innerText = (
        f"Fossil share of grid: {state.fossil_share() * 100:.0f}%"
    )

    for plant_type in PLANT_TYPES:
        count = state.plant_counts[plant_type]
        cost = state.plant_cost(plant_type)
        document.getElementById(f"{plant_type}-count").innerText = str(count)

        build_button = document.getElementById(f"{plant_type}-build-button")
        build_button.innerText = f"Build ({cost:.0f})"
        build_button.disabled = state.funds < cost

        retire_button = document.getElementById(f"{plant_type}-retire-button")
        retire_button.disabled = count <= 0


def _make_build_handler(plant_type):
    def handler(event=None):
        state.build_plant(plant_type)
        render()
    return handler


def _make_retire_handler(plant_type):
    def handler(event=None):
        state.retire_plant(plant_type)
        render()
    return handler


def on_advance_round(event=None):
    state.advance_round()
    render()


def setup():
    for plant_type in PLANT_TYPES:
        document.getElementById(f"{plant_type}-build-button").addEventListener(
            "click", create_proxy(_make_build_handler(plant_type))
        )
        document.getElementById(f"{plant_type}-retire-button").addEventListener(
            "click", create_proxy(_make_retire_handler(plant_type))
        )
    document.getElementById("advance-round-button").addEventListener(
        "click", create_proxy(on_advance_round)
    )
    render()


setup()
