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

# Decoupling measures reduce the coupling ratio without requiring herd
# shrinkage — same herd size, lower emissions. Floored so it can never
# hit zero (decoupling is never "free," just much better).
MIN_COUPLING_RATIO = 0.1

DECOUPLING_MEASURES = {
    "feed": {"cost": 15, "ratio_reduction": 0.04, "label": "Feed Additives"},
    "caps": {"cost": 20, "ratio_reduction": 0.06, "label": "Herd Caps"},
    "capture": {"cost": 20, "ratio_reduction": 0.10, "label": "Capture Systems"},
}

# Soft consequences: sustained methane deterministically eats into income
# via market/regulatory pressure and degraded yields — no hard fail-state,
# no randomness, just an unchecked-growth strategy quietly undercutting
# its own revenue over time.
PRESSURE_SCALE = 100.0
MAX_PRESSURE = 0.8

# Scoring: profitability minus a methane penalty. Rewards decoupling
# specifically — pure growth racks up methane (and the pressure drag that
# comes with it), pure restraint never earns much profit either. Tuned
# (see tests/test_scoring.py) so decoupled growth overtakes pure growth
# within about 10 rounds — a real payoff within a normal play session,
# not a decades-long theoretical one.
METHANE_PENALTY_WEIGHT = 2.0


class FarmState:
    def __init__(self):
        self.round_number = 1
        self.funds = STARTING_FUNDS
        self.herd_size = 0
        self.methane = 0.0
        self.decoupling_investment = {m: 0 for m in DECOUPLING_MEASURES}

    def coupling_ratio(self):
        """Methane produced per herd unit, per round. Each decoupling
        measure permanently lowers this, floored so it never hits zero."""
        reduction = sum(
            self.decoupling_investment[m] * DECOUPLING_MEASURES[m]["ratio_reduction"]
            for m in DECOUPLING_MEASURES
        )
        return max(MIN_COUPLING_RATIO, BASE_COUPLING_RATIO - reduction)

    def methane_this_round(self):
        return self.herd_size * self.coupling_ratio()

    def grow_herd(self):
        if self.funds < HERD_GROWTH_COST:
            return False
        self.funds -= HERD_GROWTH_COST
        self.herd_size += 1
        return True

    def invest_decoupling(self, measure):
        cost = DECOUPLING_MEASURES[measure]["cost"]
        if self.funds < cost:
            return False
        self.funds -= cost
        self.decoupling_investment[measure] += 1
        return True

    def pressure_fraction(self):
        """Fraction of income lost to market/regulatory pressure and
        degraded yields, scaling with sustained methane. Capped so income
        never fully vanishes — a bad strategy gets worse, not impossible."""
        return min(MAX_PRESSURE, self.methane / PRESSURE_SCALE)

    def advance_round(self):
        raw_income = self.herd_size * HERD_INCOME_PER_UNIT
        self.funds += raw_income * (1 - self.pressure_fraction())
        self.methane += self.methane_this_round()
        self.round_number += 1

    def score(self):
        """Profitability weighted against sustained emissions — rewards
        decoupling specifically, not just growth or just restraint."""
        return self.funds - self.methane * METHANE_PENALTY_WEIGHT


farm = FarmState()


def render():
    document.getElementById("round-display").innerText = f"Round {farm.round_number}"
    document.getElementById("funds-display").innerText = f"Funds: {farm.funds:.0f}"
    document.getElementById("herd-display").innerText = f"Herd size: {farm.herd_size}"
    document.getElementById("methane-display").innerText = f"Methane: {farm.methane:.0f}"
    document.getElementById("coupling-display").innerText = (
        f"Coupling ratio: {farm.coupling_ratio():.2f} methane/herd/round"
    )
    document.getElementById("pressure-display").innerText = (
        f"Market/regulatory pressure: {farm.pressure_fraction() * 100:.0f}% income loss"
    )
    document.getElementById("methane-bar").style.width = (
        f"{min(1.0, farm.methane / PRESSURE_SCALE) * 100:.0f}%"
    )
    document.getElementById("score-display").innerText = f"Score: {farm.score():.0f}"

    grow_button = document.getElementById("grow-herd-button")
    grow_button.innerText = f"Grow Herd ({HERD_GROWTH_COST})"
    grow_button.disabled = farm.funds < HERD_GROWTH_COST

    for measure, spec in DECOUPLING_MEASURES.items():
        document.getElementById(f"{measure}-count").innerText = str(
            farm.decoupling_investment[measure]
        )
        button = document.getElementById(f"{measure}-invest-button")
        button.innerText = f"{spec['label']} ({spec['cost']})"
        button.disabled = farm.funds < spec["cost"]


def on_grow_herd(event=None):
    farm.grow_herd()
    render()


def _make_decoupling_handler(measure):
    def handler(event=None):
        farm.invest_decoupling(measure)
        render()
    return handler


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
    for measure in DECOUPLING_MEASURES:
        document.getElementById(f"{measure}-invest-button").addEventListener(
            "click", create_proxy(_make_decoupling_handler(measure))
        )
    render()


setup()
