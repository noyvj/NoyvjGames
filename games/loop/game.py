"""Loop — Circular Economy & Overconsumption Game.

Runs in-browser via Pyodide. Milestone 1: the core linear chain —
extraction -> manufacturing -> use -> disposal, a straight line by
default. Unlike the other games in the hub, there's no player investment
yet at this milestone: this is the passive baseline every future
circularity investment (Milestone 2 onward) gets measured against.
"""

from js import document
from pyodide.ffi import create_proxy

STARTING_FUNDS = 300.0

# Every cycle, the chain must supply this many units of manufactured
# goods — a fixed target, not something that grows, so "close the loop"
# stays a meaningful, reachable state rather than a moving target.
PRODUCTION_TARGET = 50.0

EXTRACTION_COST_PER_UNIT = 2.0
SALE_PRICE_PER_UNIT = 5.0


class ChainState:
    def __init__(self):
        self.cycle_number = 1
        self.funds = STARTING_FUNDS
        self.total_extracted = 0.0
        self.total_produced = 0.0

    def circular_supply(self):
        """Units of this cycle's production target met by repair/reuse/
        recycling instead of new extraction. Zero until Milestone 2 wires
        up circularity investments."""
        return 0.0

    def new_extraction_needed(self):
        """The straight-line default: whatever circular supply doesn't
        cover has to come from newly extracted raw material."""
        return max(0.0, PRODUCTION_TARGET - self.circular_supply())

    def advance_cycle(self):
        extraction = self.new_extraction_needed()
        cost = extraction * EXTRACTION_COST_PER_UNIT
        revenue = PRODUCTION_TARGET * SALE_PRICE_PER_UNIT
        self.funds += revenue - cost
        self.total_extracted += extraction
        self.total_produced += PRODUCTION_TARGET
        self.cycle_number += 1


chain = ChainState()


def render():
    document.getElementById("cycle-display").innerText = f"Cycle {chain.cycle_number}"
    document.getElementById("funds-display").innerText = f"Funds: {chain.funds:.0f}"
    document.getElementById("extraction-display").innerText = (
        f"New extraction this cycle: {chain.new_extraction_needed():.0f} units"
    )
    document.getElementById("production-display").innerText = (
        f"Production target: {PRODUCTION_TARGET:.0f} units/cycle"
    )
    document.getElementById("total-extracted-display").innerText = (
        f"Total extracted (lifetime): {chain.total_extracted:.0f} units"
    )


def on_advance_cycle(event=None):
    chain.advance_cycle()
    render()


def setup():
    document.getElementById("advance-cycle-button").addEventListener(
        "click", create_proxy(on_advance_cycle)
    )
    render()


setup()
