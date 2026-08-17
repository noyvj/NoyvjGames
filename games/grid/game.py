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

PLANT_ICON = {
    "coal": "⚫",  # black circle
    "gas": "\U0001F525",  # fire
    "nuclear": "☢️",  # radioactive
    "solar": "☀️",  # sun
    "wind": "\U0001F4A8",  # dash/wind
    "hydro": "\U0001F4A7",  # droplet
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

# Reference point for the emissions meter bar — matches the severity
# scale, so a full bar means disruption severity has hit its own cap.
EMISSIONS_METER_MAX = DISRUPTION_SEVERITY_SCALE

# Iteration Pass 2 — global comparison: a hardcoded real-world-ish
# benchmark (roughly matching global electricity generation's fossil
# share and an average coal/gas emissions factor) so the player's actual
# emissions trajectory has something concrete to be measured against,
# not just "went up" or "went down" in isolation.
GLOBAL_AVG_FOSSIL_SHARE = 0.61
GLOBAL_AVG_FOSSIL_EMISSIONS_FACTOR = (EMISSIONS_FACTOR["coal"] + EMISSIONS_FACTOR["gas"]) / 2

# Iteration Pass 2 — infrastructure age/vulnerability: plants accumulate
# age each round; past a grace period, older fleets become progressively
# more failure-prone unless maintained. A separate lever from build/retire,
# and separate from the emissions-driven disruption system above.
AGE_GRACE_PERIOD = 8
AGE_BREAKDOWN_RATE = 0.03
MAX_AGE_BREAKDOWN_PROBABILITY = 0.6
AGING_BREAKDOWN_COST_FRACTION = 0.6
MAINTENANCE_COST_FRACTION = 0.25
MAINTENANCE_AGE_REDUCTION = 6

# (age threshold, CSS class) pairs, ascending — render() applies the
# highest threshold a plant type's age has crossed, so its icon visibly
# degrades before a breakdown actually happens.
AGE_WEAR_THRESHOLDS = [
    (24, "wear-3"),
    (16, "wear-2"),
    (8, "wear-1"),
]


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
        self.emissions_history = []
        self.avg_renewable_cost_history = []
        self.renewable_unlocked = False
        self.plant_age = {t: 0.0 for t in PLANT_TYPES}
        self.global_reference_emissions = 0.0
        self.global_reference_emissions_history = []
        self.last_aging_event = None

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

    def average_renewable_cost(self):
        """Average current cost across the three renewable types — falls
        as cumulative renewable investment grows, thanks to the cost
        curve. Tracked over time as one half of the iteration-pass trend
        graph, so the "investing early makes things cheaper" lesson is
        visible as a line, not just felt in individual build costs."""
        return sum(self.plant_cost(t) for t in RENEWABLE_TYPES) / len(RENEWABLE_TYPES)

    def build_plant(self, plant_type):
        cost = self.plant_cost(plant_type)
        if self.funds < cost:
            return False
        self.funds -= cost
        old_count = self.plant_counts[plant_type]
        # A freshly built unit has age 0, so it dilutes the type's average
        # fleet age proportionally rather than the average staying put.
        self.plant_age[plant_type] = self.plant_age[plant_type] * old_count / (old_count + 1)
        self.plant_counts[plant_type] += 1
        self.cumulative_built[plant_type] += 1
        if plant_type in RENEWABLE_TYPES:
            self.renewable_unlocked = True
        return True

    def retire_plant(self, plant_type):
        if self.plant_counts[plant_type] <= 0:
            return False
        self.plant_counts[plant_type] -= 1
        self.funds += PLANT_BASE_COST[plant_type] * REFUND_FRACTION
        return True

    def maintenance_cost(self, plant_type):
        return PLANT_BASE_COST[plant_type] * MAINTENANCE_COST_FRACTION

    def maintain_plant(self, plant_type):
        """Spends funds to refurbish a plant type's fleet, knocking its
        average age down rather than resetting it to zero — maintenance
        extends a fleet's life, it doesn't make it new again."""
        if self.plant_counts[plant_type] <= 0:
            return False
        cost = self.maintenance_cost(plant_type)
        if self.funds < cost:
            return False
        self.funds -= cost
        self.plant_age[plant_type] = max(0.0, self.plant_age[plant_type] - MAINTENANCE_AGE_REDUCTION)
        return True

    def oldest_vulnerable_plant(self):
        """The standing plant type with the highest average age — the one
        at risk of an aging breakdown this round, if any exist at all."""
        candidates = [t for t in PLANT_TYPES if self.plant_counts[t] > 0]
        if not candidates:
            return None
        return max(candidates, key=lambda t: self.plant_age[t])

    def aging_breakdown_probability(self):
        oldest = self.oldest_vulnerable_plant()
        if oldest is None:
            return 0.0
        age = self.plant_age[oldest]
        if age <= AGE_GRACE_PERIOD:
            return 0.0
        return min(MAX_AGE_BREAKDOWN_PROBABILITY, (age - AGE_GRACE_PERIOD) * AGE_BREAKDOWN_RATE)

    def wear_class(self, plant_type):
        age = self.plant_age[plant_type]
        for threshold, css_class in AGE_WEAR_THRESHOLDS:
            if age >= threshold:
                return css_class
        return ""

    def advance_round(self, rng=random.random, age_rng=random.random):
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
        self.global_reference_emissions += (
            self.total_capacity() * GLOBAL_AVG_FOSSIL_SHARE * GLOBAL_AVG_FOSSIL_EMISSIONS_FACTOR
        )

        aging_event = None
        oldest = self.oldest_vulnerable_plant()
        for plant_type in PLANT_TYPES:
            if self.plant_counts[plant_type] > 0:
                self.plant_age[plant_type] += 1
        if oldest is not None and age_rng() < self.aging_breakdown_probability():
            self.plant_counts[oldest] -= 1
            repair_cost = PLANT_BASE_COST[oldest] * AGING_BREAKDOWN_COST_FRACTION
            self.funds = max(0.0, self.funds - repair_cost)
            aging_event = {"type": "aging_breakdown", "plant": oldest, "repair_cost": repair_cost}

        self.round_number += 1
        self.demand += DEMAND_GROWTH_PER_ROUND

        self.last_event = event
        if event:
            self.event_log.append(event)
        self.last_aging_event = aging_event

        self.clean_fraction_log.append(1 - self.fossil_share())
        self.emissions_history.append(self.emissions)
        self.avg_renewable_cost_history.append(self.average_renewable_cost())
        self.global_reference_emissions_history.append(self.global_reference_emissions)

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


def event_severity_class(event):
    """CSS class for the event notification — visually distinct so a real
    disruption doesn't read the same as "nothing happened"."""
    if event is None:
        return "event-display"
    if event["type"] == "damage":
        return "event-display event-display--danger"
    return "event-display event-display--warning"


TREND_GRAPH_WIDTH = 280
TREND_GRAPH_HEIGHT = 80

# Shown once, the first time a player builds any renewable plant —
# grounds the cost-curve mechanic (Milestone 2) in the real trend it's
# modeling. Iteration-pass addition: a light factual anchor, not a
# lecture, per the cross-cutting note in CLAUDE.md.
RENEWABLE_UNLOCK_BLURB = (
    "In the real world, each doubling of solar deployment has "
    "historically cut its cost by roughly 20% — economists call this a "
    "learning curve, and it's exactly what's driving your renewable "
    "prices down here."
)


def _normalize_series(series, height, lo=None, hi=None):
    """Maps a series to SVG y-coordinates within [0, height]. Defaults to
    scaling against its own min/max so differently-scaled series
    (emissions counts, renewable costs) can share one chart; an explicit
    lo/hi lets two series (a player's emissions vs. the global-reference
    benchmark) share one scale instead, so they stay directly comparable."""
    if lo is None:
        lo = min(series)
    if hi is None:
        hi = max(series)
    if hi - lo < 1e-9:
        return [height / 2 for _ in series]
    return [height - ((v - lo) / (hi - lo)) * height for v in series]


def trend_graph_svg(emissions_history, cost_history, global_reference_history):
    """Three-line trend graph: emissions (rising, red) vs. average
    renewable cost (falling as investment compounds, green) vs. a
    hardcoded global-average emissions benchmark (dashed grey) — the
    Pass 2 addition that gives the player's own emissions line something
    concrete to be measured against, not just a shape in isolation.
    Capped at three lines so it stays legible."""
    if len(emissions_history) < 2:
        return ""

    n = len(emissions_history)
    xs = [i * (TREND_GRAPH_WIDTH / (n - 1)) for i in range(n)]
    # Normalized together (not each series against its own min/max) so
    # the player's emissions line and the global-reference line stay
    # comparable to each other on the same scale.
    combined_min = min(min(emissions_history), min(global_reference_history))
    combined_max = max(max(emissions_history), max(global_reference_history))
    emissions_ys = _normalize_series(emissions_history, TREND_GRAPH_HEIGHT, combined_min, combined_max)
    global_ys = _normalize_series(global_reference_history, TREND_GRAPH_HEIGHT, combined_min, combined_max)
    cost_ys = _normalize_series(cost_history, TREND_GRAPH_HEIGHT)

    emissions_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, emissions_ys))
    cost_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, cost_ys))
    global_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, global_ys))

    return (
        f'<svg viewBox="0 0 {TREND_GRAPH_WIDTH} {TREND_GRAPH_HEIGHT}" class="trend-graph-svg">'
        f'<polyline points="{global_points}" class="trend-line trend-line--global" />'
        f'<polyline points="{emissions_points}" class="trend-line trend-line--emissions" />'
        f'<polyline points="{cost_points}" class="trend-line trend-line--cost" />'
        f"</svg>"
    )


def global_comparison_message(emissions, global_reference_emissions):
    if emissions < global_reference_emissions:
        return (
            f"Your grid has emitted {emissions:.0f} vs. an estimated {global_reference_emissions:.0f} "
            "for a grid built to the global-average fossil mix — you're ahead of the curve."
        )
    if emissions > global_reference_emissions:
        return (
            f"Your grid has emitted {emissions:.0f} vs. an estimated {global_reference_emissions:.0f} "
            "for a grid built to the global-average fossil mix — you're behind the curve."
        )
    return "Your grid is tracking almost exactly the global-average fossil mix so far."


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
    event_el = document.getElementById("event-display")
    event_el.innerText = event_message(state.last_event)
    event_el.className = event_severity_class(state.last_event)

    document.getElementById("score-display").innerText = f"Sustained clean-grid score: {state.score():.0f}"
    document.getElementById("trend-display").innerText = clean_trend_message(state.clean_trend())

    emissions_fraction = min(1.0, state.emissions / EMISSIONS_METER_MAX)
    document.getElementById("emissions-bar").style.width = f"{emissions_fraction * 100:.0f}%"
    document.getElementById("score-bar").style.width = f"{state.score():.0f}%"

    svg = trend_graph_svg(
        state.emissions_history, state.avg_renewable_cost_history, state.global_reference_emissions_history
    )
    document.getElementById("trend-graph").innerHTML = svg
    document.getElementById("trend-graph-message").innerText = (
        "Your emissions (red) vs. a global-average-fossil-mix benchmark (dashed grey) vs. average renewable cost (green) over time."
        if svg else "Not enough rounds yet to show an emissions/cost trend."
    )
    document.getElementById("global-comparison-message").innerText = global_comparison_message(
        state.emissions, state.global_reference_emissions
    )

    blurb_el = document.getElementById("renewable-blurb")
    blurb_el.innerText = RENEWABLE_UNLOCK_BLURB
    blurb_el.hidden = not state.renewable_unlocked

    aging_el = document.getElementById("aging-event-display")
    if state.last_aging_event is None:
        aging_el.innerText = "No aging breakdowns last round."
        aging_el.className = "event-display"
    else:
        plant_name = PLANT_LABEL[state.last_aging_event["plant"]]
        cost = state.last_aging_event["repair_cost"]
        aging_el.innerText = f"Aging breakdown! A {plant_name} plant failed from wear (repair cost {cost:.0f})."
        aging_el.className = "event-display event-display--danger"

    for plant_type in PLANT_TYPES:
        count = state.plant_counts[plant_type]
        cost = state.plant_cost(plant_type)
        document.getElementById(f"{plant_type}-count").innerText = str(count)
        name_el = document.getElementById(f"{plant_type}-name")
        name_el.innerText = f"{PLANT_ICON[plant_type]} {PLANT_LABEL[plant_type]}"
        for _, wear_css_class in AGE_WEAR_THRESHOLDS:
            name_el.classList.remove(wear_css_class)
        wear_css_class = state.wear_class(plant_type)
        if wear_css_class:
            name_el.classList.add(wear_css_class)

        build_button = document.getElementById(f"{plant_type}-build-button")
        build_button.innerText = f"Build ({cost:.0f})"
        build_button.disabled = state.funds < cost

        retire_button = document.getElementById(f"{plant_type}-retire-button")
        retire_button.disabled = count <= 0

        maintenance_cost = state.maintenance_cost(plant_type)
        maintain_button = document.getElementById(f"{plant_type}-maintain-button")
        maintain_button.innerText = f"Maintain ({maintenance_cost:.0f})"
        maintain_button.disabled = count <= 0 or state.funds < maintenance_cost


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


def _make_maintain_handler(plant_type):
    def handler(event=None):
        state.maintain_plant(plant_type)
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
        document.getElementById(f"{plant_type}-maintain-button").addEventListener(
            "click", create_proxy(_make_maintain_handler(plant_type))
        )
    document.getElementById("advance-round-button").addEventListener(
        "click", create_proxy(on_advance_round)
    )
    render()


setup()
