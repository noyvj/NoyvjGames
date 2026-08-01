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


class GridState:
    def __init__(self):
        self.round_number = 1
        self.demand = STARTING_DEMAND
        self.funds = STARTING_FUNDS
        self.plant_counts = {t: 0 for t in PLANT_TYPES}

    def plant_cost(self, plant_type):
        """Flat cost for Milestone 1 — Milestone 2 adds the renewable
        learning-curve decay on top of this base cost."""
        return PLANT_BASE_COST[plant_type]

    def total_capacity(self):
        return sum(self.plant_counts[t] * PLANT_CAPACITY[t] for t in PLANT_TYPES)

    def build_plant(self, plant_type):
        cost = self.plant_cost(plant_type)
        if self.funds < cost:
            return False
        self.funds -= cost
        self.plant_counts[plant_type] += 1
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
        self.round_number += 1
        self.demand += DEMAND_GROWTH_PER_ROUND


state = GridState()


def render():
    document.getElementById("round-display").innerText = f"Round {state.round_number}"
    document.getElementById("demand-display").innerText = f"Demand: {state.demand}"
    document.getElementById("funds-display").innerText = f"Funds: {state.funds:.0f}"
    document.getElementById("capacity-display").innerText = f"Capacity: {state.total_capacity()}"

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
