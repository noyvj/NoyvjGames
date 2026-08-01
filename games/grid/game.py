"""Grid — Energy Transition Game.

Runs in-browser via Pyodide. Milestone 1: the core turn-based loop —
demand growth, funds, six plant types to build/retire, and capacity-based
revenue on round advance. Emissions, cost curves, and disruption events
land in later milestones.
"""

import random

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

FOSSIL_TYPES = ("coal", "gas")

# Disruption events: probability AND severity both scale with emissions,
# so a dirty grid gets progressively harder to manage rather than
# suddenly "losing" — there's no funds floor here, only a shrinking gain,
# so this can never bankrupt the player outright (no hard fail-state).
DISRUPTION_PROBABILITY_SCALE = 2000.0
MAX_DISRUPTION_PROBABILITY = 0.9
DISRUPTION_SEVERITY_SCALE = 3000.0
MAX_REVENUE_LOSS_FRACTION = 0.8
DAMAGE_SEVERITY_THRESHOLD = 0.5


class GridState:
    def __init__(self):
        self.round_number = 1
        self.demand = STARTING_DEMAND
        self.funds = STARTING_FUNDS
        self.plant_counts = {t: 0 for t in PLANT_TYPES}
        self.cumulative_built = {t: 0 for t in PLANT_TYPES}
        self.emissions = 0.0
        self.event_log = []
        self.last_event = None
        self.clean_fraction_log = []

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

    def disruption_probability(self):
        return min(MAX_DISRUPTION_PROBABILITY, self.emissions / DISRUPTION_PROBABILITY_SCALE)

    def disruption_severity(self):
        """0..1 — how bad a disruption event is, if one occurs this round."""
        return min(1.0, self.emissions / DISRUPTION_SEVERITY_SCALE)

    def _fossil_plant_to_damage(self):
        """Picks a standing fossil plant type to damage, biased toward
        whichever fossil type has the most units standing. None if the
        grid has no fossil plants left to damage."""
        candidates = [t for t in FOSSIL_TYPES if self.plant_counts[t] > 0]
        if not candidates:
            return None
        return max(candidates, key=lambda t: self.plant_counts[t])

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

    def advance_round(self, rng=random.random):
        met_demand = min(self.total_capacity(), self.demand)
        revenue = met_demand * REVENUE_PER_UNIT_MET

        event = None
        if rng() < self.disruption_probability():
            severity = self.disruption_severity()
            revenue_loss = revenue * severity * MAX_REVENUE_LOSS_FRACTION
            revenue -= revenue_loss
            event = {"type": "brownout", "severity": severity, "revenue_loss": revenue_loss}

            if severity >= DAMAGE_SEVERITY_THRESHOLD:
                damaged_type = self._fossil_plant_to_damage()
                if damaged_type:
                    self.plant_counts[damaged_type] -= 1
                    event["type"] = "damage"
                    event["damaged_plant"] = damaged_type

        self.funds += revenue
        self.emissions += self.emissions_this_round()
        self.round_number += 1
        self.demand += DEMAND_GROWTH_PER_ROUND

        self.last_event = event
        if event:
            self.event_log.append(event)

        self.clean_fraction_log.append(1 - self.fossil_share())

    def average_clean_fraction(self):
        """Sustained cleanliness across the whole run so far — every round
        played counts equally, so a late clean sprint can't fully erase a
        dirty start. This is the "not just final snapshot" scoring rule."""
        if not self.clean_fraction_log:
            return 0.0
        return sum(self.clean_fraction_log) / len(self.clean_fraction_log)

    def score(self):
        return self.average_clean_fraction() * 100

    def clean_trend(self):
        """Compares the first half of rounds played to the second half —
        the hope-angle payoff: a visibly improving trend is the direct
        reward for early renewable investment, not just a good final number."""
        n = len(self.clean_fraction_log)
        if n < 4:
            return None
        half = n // 2
        first_half_avg = sum(self.clean_fraction_log[:half]) / half
        second_half_avg = sum(self.clean_fraction_log[half:]) / (n - half)
        return first_half_avg, second_half_avg


state = GridState()


def event_message(event):
    if event is None:
        return "No disruptions last round."
    if event["type"] == "damage":
        plant_name = PLANT_LABEL[event["damaged_plant"]]
        return (
            f"Damage! A {plant_name} plant went offline "
            f"(lost {event['revenue_loss']:.0f} funds in the disruption)."
        )
    return f"Brownout! Lost {event['revenue_loss']:.0f} funds to grid instability."


def clean_trend_message(trend):
    if trend is None:
        return "Not enough rounds yet to show a trend."
    first_half_avg, second_half_avg = trend
    first_pct, second_pct = first_half_avg * 100, second_half_avg * 100
    if second_half_avg > first_half_avg:
        return f"Your grid is getting cleaner over time ({first_pct:.0f}% → {second_pct:.0f}%) — the transition is paying off."
    if second_half_avg < first_half_avg:
        return f"Your grid has gotten dirtier over time ({first_pct:.0f}% → {second_pct:.0f}%)."
    return f"Your grid's cleanliness has held steady at {second_pct:.0f}%."


def render():
    document.getElementById("round-display").innerText = f"Round {state.round_number}"
    document.getElementById("demand-display").innerText = f"Demand: {state.demand}"
    document.getElementById("funds-display").innerText = f"Funds: {state.funds:.0f}"
    document.getElementById("capacity-display").innerText = f"Capacity: {state.total_capacity()}"
    document.getElementById("emissions-display").innerText = f"Emissions: {state.emissions:.0f}"
    document.getElementById("fossil-share-display").innerText = (
        f"Fossil share of grid: {state.fossil_share() * 100:.0f}%"
    )
    document.getElementById("event-display").innerText = event_message(state.last_event)
    document.getElementById("score-display").innerText = f"Sustained clean-grid score: {state.score():.0f}"
    document.getElementById("trend-display").innerText = clean_trend_message(state.clean_trend())

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
