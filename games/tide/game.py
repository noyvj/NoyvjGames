"""Tide — Ocean Acidification & Sea-Level Rise Game.

Runs in-browser via Pyodide. Milestone 1: the core settlement loop —
seasonal rounds, funds, and three investment categories (output/
reduction/adaptation), mirroring Grid's build-capacity pattern. Acidity,
sea-level rise, and the tile-grid coastline land in later milestones.
"""

from js import document
from pyodide.ffi import create_proxy

STARTING_FUNDS = 300

CATEGORIES = ["output", "reduction", "adaptation"]

CATEGORY_LABEL = {
    "output": "Output",
    "reduction": "Acidity Reduction",
    "adaptation": "Adaptation",
}

INVEST_COST = {
    "output": 20,
    "reduction": 25,
    "adaptation": 30,
}

OUTPUT_INCOME_PER_UNIT = 6


class SettlementState:
    def __init__(self):
        self.season = 1
        self.funds = STARTING_FUNDS
        self.capacity = {c: 0 for c in CATEGORIES}

    def invest(self, category):
        cost = INVEST_COST[category]
        if self.funds < cost:
            return False
        self.funds -= cost
        self.capacity[category] += 1
        return True

    def advance_season(self):
        self.funds += self.capacity["output"] * OUTPUT_INCOME_PER_UNIT
        self.season += 1


state = SettlementState()


def render():
    document.getElementById("season-display").innerText = f"Season {state.season}"
    document.getElementById("funds-display").innerText = f"Funds: {state.funds:.0f}"

    for category in CATEGORIES:
        document.getElementById(f"{category}-count").innerText = str(state.capacity[category])
        invest_button = document.getElementById(f"{category}-invest-button")
        invest_button.innerText = f"Invest ({INVEST_COST[category]})"
        invest_button.disabled = state.funds < INVEST_COST[category]


def _make_invest_handler(category):
    def handler(event=None):
        state.invest(category)
        render()
    return handler


def on_advance_season(event=None):
    state.advance_season()
    render()


def setup():
    for category in CATEGORIES:
        document.getElementById(f"{category}-invest-button").addEventListener(
            "click", create_proxy(_make_invest_handler(category))
        )
    document.getElementById("advance-season-button").addEventListener(
        "click", create_proxy(on_advance_season)
    )
    render()


setup()
