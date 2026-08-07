"""Loop — Circular Economy & Overconsumption Game.

Runs in-browser via Pyodide. Milestone 2: circularity investments —
repair networks, reuse systems, and recycling loops that each supply
a chunk of the production target without new extraction. Investing
enough in any combination can push new extraction to zero: a fully
closed loop, the clearest win-state in the whole hub.
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

# Circularity investments each add fixed supply toward the production
# target, sourced from repaired/reused/recycled material instead of new
# extraction. Recycling loops are the most potent (closest to the
# disposal end of the chain, recovering material that would otherwise be
# pure waste); repair networks the least (they only extend use-phase,
# not recover material outright) — reuse sits in between.
CIRCULARITY_INVESTMENTS = {
    "repair": {"cost": 20, "supply_per_unit": 3.0, "label": "Repair Networks", "icon": "\U0001F527"},
    "reuse": {"cost": 25, "supply_per_unit": 4.0, "label": "Reuse Systems", "icon": "\U0001F504"},
    "recycle": {"cost": 30, "supply_per_unit": 5.0, "label": "Recycling Loops", "icon": "♻️"},
}

# Environmental cost meter: cumulative new extraction leaves behind
# lasting land/emissions damage, which in turn makes further extraction
# progressively more expensive (degraded sites cost more to work) — a
# soft, compounding consequence with no hard fail-state. Circularity
# investment is the only way to avoid feeding this meter at all, since
# it substitutes for new extraction rather than merely paying its cost.
ENVIRONMENTAL_DAMAGE_SCALE = 500.0
MAX_COST_MULTIPLIER = 2.5


class ChainState:
    def __init__(self):
        self.cycle_number = 1
        self.funds = STARTING_FUNDS
        self.total_extracted = 0.0
        self.total_produced = 0.0
        self.circularity_investment = {c: 0 for c in CIRCULARITY_INVESTMENTS}

    def circular_supply(self):
        """Units of this cycle's production target met by repair/reuse/
        recycling instead of new extraction."""
        return sum(
            self.circularity_investment[c] * CIRCULARITY_INVESTMENTS[c]["supply_per_unit"]
            for c in CIRCULARITY_INVESTMENTS
        )

    def new_extraction_needed(self):
        """The straight-line default: whatever circular supply doesn't
        cover has to come from newly extracted raw material. Floored at
        zero — enough circularity investment closes the loop entirely."""
        return max(0.0, PRODUCTION_TARGET - self.circular_supply())

    def is_loop_closed(self):
        return self.new_extraction_needed() <= 0.0

    def invest_circularity(self, measure):
        cost = CIRCULARITY_INVESTMENTS[measure]["cost"]
        if self.funds < cost:
            return False
        self.funds -= cost
        self.circularity_investment[measure] += 1
        return True

    def damage_fraction(self):
        """0..1 — cumulative land/emissions damage from lifetime new
        extraction, capped so extraction never becomes literally
        impossible, just steadily more expensive."""
        return min(1.0, self.total_extracted / ENVIRONMENTAL_DAMAGE_SCALE)

    def extraction_cost_multiplier(self):
        return 1.0 + self.damage_fraction() * (MAX_COST_MULTIPLIER - 1.0)

    def advance_cycle(self):
        extraction = self.new_extraction_needed()
        cost = extraction * EXTRACTION_COST_PER_UNIT * self.extraction_cost_multiplier()
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
        "Loop closed — no new extraction needed" if chain.is_loop_closed()
        else f"New extraction this cycle: {chain.new_extraction_needed():.0f} units"
    )
    document.getElementById("production-display").innerText = (
        f"Production target: {PRODUCTION_TARGET:.0f} units/cycle"
    )
    document.getElementById("total-extracted-display").innerText = (
        f"Total extracted (lifetime): {chain.total_extracted:.0f} units"
    )
    document.getElementById("damage-display").innerText = (
        f"Environmental damage: {chain.damage_fraction() * 100:.0f}% "
        f"(extraction cost x{chain.extraction_cost_multiplier():.2f})"
    )
    document.getElementById("damage-bar").style.width = f"{chain.damage_fraction() * 100:.0f}%"

    for measure, spec in CIRCULARITY_INVESTMENTS.items():
        document.getElementById(f"{measure}-name").innerText = f"{spec['icon']} {spec['label']}"
        document.getElementById(f"{measure}-count").innerText = str(
            chain.circularity_investment[measure]
        )
        button = document.getElementById(f"{measure}-invest-button")
        button.innerText = f"{spec['label']} ({spec['cost']})"
        button.disabled = chain.funds < spec["cost"]


def on_advance_cycle(event=None):
    chain.advance_cycle()
    render()


def _make_circularity_handler(measure):
    def handler(event=None):
        chain.invest_circularity(measure)
        render()
    return handler


def setup():
    document.getElementById("advance-cycle-button").addEventListener(
        "click", create_proxy(on_advance_cycle)
    )
    for measure in CIRCULARITY_INVESTMENTS:
        document.getElementById(f"{measure}-invest-button").addEventListener(
            "click", create_proxy(_make_circularity_handler(measure))
        )
    render()


setup()
