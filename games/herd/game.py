"""Herd — Industrial Agriculture & Methane Game.

Runs in-browser via Pyodide. Milestone 1: the core farm loop — herd
growth, income, and round progression. The methane meter (coupled to
herd size), decoupling investments, and soft consequences land in
later milestones.
"""

from js import document
from pyodide.ffi import create_proxy

STARTING_FUNDS = 300.0
HERD_GROWTH_COST = 20
HERD_INCOME_PER_UNIT = 5

# Coupling: methane emitted per herd unit per round, before any decoupling
# investment. This ratio is the entire lesson — it's what makes "grow the
# farm" and "keep emissions low" pull against each other by default.
BASE_COUPLING_RATIO = 1.0


class FarmState:
    def __init__(self):
        self.round_number = 1
        self.funds = STARTING_FUNDS
        self.herd_size = 0
        self.methane = 0.0

    def coupling_ratio(self):
        """Methane produced per herd unit, per round. Milestone 3 adds
        decoupling investments that reduce this below its base value."""
        return BASE_COUPLING_RATIO

    def methane_this_round(self):
        return self.herd_size * self.coupling_ratio()

    def grow_herd(self):
        if self.funds < HERD_GROWTH_COST:
            return False
        self.funds -= HERD_GROWTH_COST
        self.herd_size += 1
        return True

    def advance_round(self):
        self.funds += self.herd_size * HERD_INCOME_PER_UNIT
        self.methane += self.methane_this_round()
        self.round_number += 1


farm = FarmState()


def render():
    document.getElementById("round-display").innerText = f"Round {farm.round_number}"
    document.getElementById("funds-display").innerText = f"Funds: {farm.funds:.0f}"
    document.getElementById("herd-display").innerText = f"Herd size: {farm.herd_size}"
    document.getElementById("methane-display").innerText = f"Methane: {farm.methane:.0f}"
    document.getElementById("coupling-display").innerText = (
        f"Coupling ratio: {farm.coupling_ratio():.2f} methane/herd/round"
    )

    grow_button = document.getElementById("grow-herd-button")
    grow_button.innerText = f"Grow Herd ({HERD_GROWTH_COST})"
    grow_button.disabled = farm.funds < HERD_GROWTH_COST


def on_grow_herd(event=None):
    farm.grow_herd()
    render()


def on_advance_round(event=None):
    farm.advance_round()
    render()


def setup():
    document.getElementById("grow-herd-button").addEventListener(
        "click", create_proxy(on_grow_herd)
    )
    document.getElementById("advance-round-button").addEventListener(
        "click", create_proxy(on_advance_round)
    )
    render()


setup()
