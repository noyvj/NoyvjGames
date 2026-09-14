"""Grid — Energy Transition Game.

Runs in-browser via Pyodide. Turn-based loop across demand growth, funds,
six plant types to build/retire/maintain, capacity-based revenue on round
advance, an emissions meter and renewable cost curve, and emissions-driven
disruption events plus infrastructure aging — see CLAUDE.md's milestone
table for how each system landed.
"""

import copy
import json
import random

import info_page
from js import document, setTimeout
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
# cost decay off these base costs is applied by plant_cost() below.
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

# C10: the exact wear percentage shown next to the existing wear-icon
# states, on the same scale as the top wear tier -- 100% lines up with
# wear-3, not with MAX_AGE_BREAKDOWN_PROBABILITY's own cap (a different
# scale entirely; conflating the two would make the number lie about
# what "100%" means).
WEAR_PERCENT_REFERENCE_AGE = AGE_WEAR_THRESHOLDS[0][0]


def _breakdown_probability_for_age(age):
    """Shared by GridState.aging_breakdown_probability() (the single
    oldest standing plant type, which is the only one actually at risk of
    breaking down a given round) and breakdown_risk_probability() below
    (C19's per-type risk badge, informational for every standing type
    past the grace period, not just the current oldest)."""
    if age <= AGE_GRACE_PERIOD:
        return 0.0
    return min(MAX_AGE_BREAKDOWN_PROBABILITY, (age - AGE_GRACE_PERIOD) * AGE_BREAKDOWN_RATE)


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
        # New tracked state for the achievements framework (see the
        # "Achievements" section below) -- nothing else in this module
        # records how many times Maintain has actually been used, or how
        # long a streak of disruption-free rounds has run, so these three
        # need genuine new tracked fields rather than being derivable from
        # what's already here. Each is mutated only at the real event it
        # measures (a successful maintain_plant() call; a round advancing
        # with or without a disruption event), never hand-set elsewhere.
        self.maintenance_actions_count = 0
        self.current_clean_streak = 0
        self.best_clean_streak = 0
        # C20 -- one-time first-use callouts for Retire's refund math and
        # Maintain's cost math, so the explanation isn't left only inside
        # the small "i" tooltip. Persisted so a returning player who's
        # already seen it doesn't get it again after a save/load.
        self.seen_retire_callout = False
        self.seen_maintain_callout = False
        # C8 -- one-time callout the first time cumulative renewable
        # capacity crosses 50% of the grid's total. Persisted so it
        # doesn't re-trigger every session once already reached.
        self.renewable_50_reached = False

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
        # Refund off the plant's *current* (possibly learning-curve-discounted)
        # cost, not its flat base cost — once a renewable's discount passes
        # 50% off base, a flat base-cost refund would pay out more than the
        # plant just cost to build, turning build+retire into a risk-free
        # money exploit. plant_cost() already equals the base cost for
        # non-renewables, so this changes nothing for fossil/nuclear.
        self.funds += self.plant_cost(plant_type) * REFUND_FRACTION
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
        self.maintenance_actions_count += 1
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
        return _breakdown_probability_for_age(self.plant_age[oldest])

    def breakdown_risk_probability(self, plant_type):
        """C19: this specific type's own risk of an aging breakdown, past
        the grace period -- unlike aging_breakdown_probability() above,
        this isn't gated on being the single oldest standing type. Only
        the oldest ever actually breaks down in a given round (see
        advance_round()), but the badge this drives is informational: it
        flags every type that HAS crossed the risk threshold, so a player
        watching a second-oldest fleet age up sees the warning coming
        before it becomes "the" oldest and its risk becomes live."""
        return _breakdown_probability_for_age(self.plant_age[plant_type])

    def wear_class(self, plant_type):
        age = self.plant_age[plant_type]
        for threshold, css_class in AGE_WEAR_THRESHOLDS:
            if age >= threshold:
                return css_class
        return ""

    def wear_percent(self, plant_type):
        """C10: the exact aging/wear percentage, shown as a number next to
        the existing wear-icon states rather than leaving wear legible
        only as a coarse three-step visual. Capped at 100 -- past the
        top wear tier, "more than fully worn" isn't a meaningful distinct
        reading, it's still just wear-3."""
        return min(100, round(self.plant_age[plant_type] / WEAR_PERCENT_REFERENCE_AGE * 100))

    def primary_emissions_source(self):
        """C3: which standing fossil type is most responsible for this
        round's emissions -- the type a generic brownout message should
        actually name, rather than reading as an unattributed "the grid"
        event. None when there's no fossil plant standing at all (a
        brownout can still occur from *historical* accumulated emissions
        even after the player has fully retired fossil capacity -- see
        event_message()'s fallback for that case)."""
        candidates = [t for t in FOSSIL_TYPES if self.plant_counts[t] > 0]
        if not candidates:
            return None
        return max(candidates, key=lambda t: self.plant_counts[t] * PLANT_CAPACITY[t] * EMISSIONS_FACTOR[t])

    def advance_round(self, rng=random.random, age_rng=random.random):
        met_demand = min(self.total_capacity(), self.demand)
        revenue = met_demand * REVENUE_PER_UNIT_MET

        event = None
        if rng() < self.disruption_probability():
            severity = self.disruption_severity()
            revenue_loss = revenue * severity * MAX_REVENUE_LOSS_FRACTION
            revenue -= revenue_loss
            event = {
                "type": "brownout",
                "severity": severity,
                "revenue_loss": revenue_loss,
                # C3: attach a specific cause even for a generic brownout,
                # rather than leaving it as an unattributed message --
                # None only when no fossil plant is currently standing to
                # blame (see event_message()'s "lingering" fallback text).
                "cause_plant": self.primary_emissions_source(),
            }

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
            self.current_clean_streak = 0
        else:
            self.current_clean_streak += 1
            self.best_clean_streak = max(self.best_clean_streak, self.current_clean_streak)
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
    # C3: name the specific plant type most responsible, rather than a
    # generic "the grid" message -- falls back to a lingering-emissions
    # framing for the (rarer) case of a brownout with no fossil plant
    # currently standing to attribute it to (historical emissions from
    # fossil capacity retired earlier this run can still be driving risk).
    cause_plant = event.get("cause_plant")
    if cause_plant:
        plant_name = PLANT_LABEL[cause_plant]
        return (
            f"Brownout! {plant_name} generation strained the grid "
            f"(lost {event['revenue_loss']:.0f} funds to instability)."
        )
    return f"Brownout! Lost {event['revenue_loss']:.0f} funds to lingering historical emissions."


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

# Info Page — optional, player-triggered supplement (never forced
# mid-session). Framing is written fresh, not copied from any source;
# sources are the curated real-world backing for the game's mechanics.
INFO_PAGE = {
    "framing": (
        "Electricity generation is one of the largest single sources of "
        "global emissions, and the fastest way to cut it is building out "
        "cleaner capacity — not rationing power. Renewables have gotten "
        "dramatically cheaper the more of them get built, a real economic "
        "trend called a learning curve. That's the same tension Grid asks "
        "you to manage: lean into that cheaper long-run path, or lean on "
        "familiar fossil capacity."
    ),
    "mechanic_tie_in": (
        "Grid's cost curve and its global-comparison line are grounded in "
        "published wind/solar learning-rate data (roughly 15%/24% cost "
        "decline per capacity doubling), not an invented number."
    ),
    "sources": [
        {
            "label": "IEA — Rapid rollout of clean technologies makes energy cheaper, not more costly",
            "url": "https://www.iea.org/news/rapid-rollout-of-clean-technologies-makes-energy-cheaper-not-more-costly",
            "note": "Real-world backing for Grid's central claim: leaning renewable is the cheaper long-run path, not a sacrifice.",
        },
        {
            "label": "Oxford Institute for Energy Studies — A critical assessment of learning curves for solar and wind",
            "url": "https://www.oxfordenergy.org/publications/a-critical-assessment-of-learning-curves-for-solar-and-wind-power-technologies/",
            "note": "A balanced, critical look at the same cost-decline concept Grid's core mechanic is built on.",
        },
        {
            "label": "US DOE / Lawrence Berkeley National Lab — Learning a Better Way To Forecast Wind and Solar Energy Costs",
            "url": "https://www.energy.gov/cmei/solar/articles/learning-better-way-forecast-wind-and-solar-energy-costs",
            "note": "The actual learning-rate figures (wind ~15%, solar ~24% per capacity doubling) behind Grid's cost curve.",
        },
        {
            "label": "IEA — Breakthrough Agenda Report 2025: Power",
            "url": "https://www.iea.org/reports/breakthrough-agenda-report-2025/power",
            "note": "Current real-world electricity cost figures, grounding the global-comparison line.",
        },
    ],
}
info_page_open = False


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


def disruption_risk_message(probability, severity):
    """Iteration Pass 3: makes the emissions-meter -> disruption-risk
    coupling explicit in words. The probability/severity math already
    scales directly off the emissions meter (Milestone 3) — this just
    makes sure the player can *read* that connection instead of only
    inferring it after the fact from event timing, so the meter reads as
    the actual mechanism gating success, not a side-score next to it."""
    if probability <= 0.0:
        return "No disruption risk yet — emissions are still at zero."
    pct = probability * 100
    if severity >= DAMAGE_SEVERITY_THRESHOLD:
        return (
            f"Rising emissions mean a {pct:.0f}% chance of a disruption next round — "
            "severe enough to damage a fossil plant if it hits."
        )
    return f"Rising emissions mean a {pct:.0f}% chance of a disruption next round."


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


# ===========================================================================
# Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md) — following SOL's reference
# integration (games/sol/game.py). Every achievement's earned status is a
# pure function of state that already exists elsewhere in this module,
# recomputed fresh every call — never a separately hand-maintained "earned"
# flag. Three exceptions needed genuinely new tracked state (declared on
# GridState above, mutated only where the real event happens: a successful
# maintain_plant() call, or a round advancing with/without a disruption
# event) — nothing else in this module records how many times Maintain has
# been used, or how long a streak of disruption-free rounds has run.
# ===========================================================================
ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    """Same loading contract as SOL's `_read_achievements_json()` / Le
    Champ de Mots' `_read_json_asset()`: the boot script fetches
    achievements.json and hands it to Python as a window global before this
    file runs; the pytest harness's fake `js` module has no such attribute,
    so this falls through to reading the file straight off disk, keeping
    the module importable outside a real browser."""
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        _js = None

    raw = getattr(_js, "ACHIEVEMENTS_JSON", None) if _js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 -- only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, ACHIEVEMENTS_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Degrades to "no achievements catalog" rather than crashing this module's
# whole import — achievements are additive, not core to Grid's gameplay
# (same posture SOL/Le Champ de Mots take for their own optional assets).
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []

MAINTENANCE_ACHIEVEMENT_TARGET = 5
CLEAN_STREAK_TARGET = 15
NO_DAMAGE_ROUND_TARGET = 21
SCORE_50_MIN_ROUNDS = 10
SCORE_80_MIN_ROUNDS = 20
AHEAD_OF_CURVE_MIN_ROUND = 11
GRID_AT_SCALE_TARGET = 300


def renewable_capacity_share():
    """Renewables' share of total standing capacity, 0..1. Shared by the
    achievements below and (later) the one-time 50%-crossing callout."""
    total = state.total_capacity()
    if total == 0:
        return 0.0
    renewable_capacity = sum(state.plant_counts[t] * PLANT_CAPACITY[t] for t in RENEWABLE_TYPES)
    return renewable_capacity / total


def _standing_plant_type_count():
    return sum(1 for t in PLANT_TYPES if state.plant_counts[t] >= 1)


def _any_renewable_at_cost_floor():
    return any(
        state.plant_cost(t) <= PLANT_BASE_COST[t] * MIN_COST_MULTIPLIER * 1.0001
        for t in RENEWABLE_TYPES
    )


# Each checker is a zero-argument predicate read fresh off live state —
# nothing here is ever cached or hand-flagged.
ACHIEVEMENT_CHECKS = {
    "first_watt": lambda: sum(state.plant_counts.values()) >= 1,
    "renewable_pioneer": lambda: any(state.plant_counts[t] >= 1 for t in RENEWABLE_TYPES),
    "clean_quarter": lambda: renewable_capacity_share() >= 0.25,
    "clean_half": lambda: renewable_capacity_share() >= 0.5,
    "clean_three_quarters": lambda: renewable_capacity_share() >= 0.75,
    "fully_renewable": lambda: state.total_capacity() > 0 and state.fossil_share() == 0.0,
    "learning_curve_floored": _any_renewable_at_cost_floor,
    "diverse_grid": lambda: _standing_plant_type_count() >= len(PLANT_TYPES),
    "fossil_phase_out": lambda: (
        state.cumulative_built["coal"] + state.cumulative_built["gas"] >= 3
        and state.plant_counts["coal"] == 0
        and state.plant_counts["gas"] == 0
        and state.total_capacity() > 0
    ),
    "clean_streak_15": lambda: state.best_clean_streak >= CLEAN_STREAK_TARGET,
    "no_damage_20": lambda: (
        state.round_number >= NO_DAMAGE_ROUND_TARGET
        and not any(e.get("type") == "damage" for e in state.event_log)
    ),
    "score_50": lambda: state.score() >= 50 and len(state.clean_fraction_log) >= SCORE_50_MIN_ROUNDS,
    "score_80": lambda: state.score() >= 80 and len(state.clean_fraction_log) >= SCORE_80_MIN_ROUNDS,
    "well_maintained": lambda: state.maintenance_actions_count >= MAINTENANCE_ACHIEVEMENT_TARGET,
    "ahead_of_the_curve": lambda: (
        state.round_number >= AHEAD_OF_CURVE_MIN_ROUND
        and state.emissions < state.global_reference_emissions
    ),
    "grid_at_scale": lambda: state.total_capacity() >= GRID_AT_SCALE_TARGET,
}

# Progress readouts, only for achievements with a natural numeric scale-up
# — a plain earned/not-yet is the honest shape for a one-shot milestone
# like "retire every fossil plant you built".
ACHIEVEMENT_PROGRESS = {
    "clean_quarter": lambda: (min(100, round(renewable_capacity_share() * 100)), 25),
    "clean_half": lambda: (min(100, round(renewable_capacity_share() * 100)), 50),
    "clean_three_quarters": lambda: (min(100, round(renewable_capacity_share() * 100)), 75),
    "diverse_grid": lambda: (_standing_plant_type_count(), len(PLANT_TYPES)),
    "clean_streak_15": lambda: (min(state.best_clean_streak, CLEAN_STREAK_TARGET), CLEAN_STREAK_TARGET),
    "score_50": lambda: (min(100, round(state.score())), 50),
    "score_80": lambda: (min(100, round(state.score())), 80),
    "well_maintained": lambda: (
        min(state.maintenance_actions_count, MAINTENANCE_ACHIEVEMENT_TARGET),
        MAINTENANCE_ACHIEVEMENT_TARGET,
    ),
    "grid_at_scale": lambda: (min(state.total_capacity(), GRID_AT_SCALE_TARGET), GRID_AT_SCALE_TARGET),
}


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field (ACHIEVEMENTS-SYSTEM-DESIGN.md). Always
    recomputed, never itself a save input."""
    return [entry["id"] for entry in ACHIEVEMENTS if ACHIEVEMENT_CHECKS[entry["id"]]()]


def achievements_summary():
    """The full catalog, in order, each entry annotated with whether it's
    currently earned and (where one exists) a live progress readout."""
    earned_ids = set(achievement_ids_earned())
    summary = []
    for entry in ACHIEVEMENTS:
        progress_fn = ACHIEVEMENT_PROGRESS.get(entry["id"])
        summary.append(
            {
                "id": entry["id"],
                "label": entry["label"],
                "description": entry["description"],
                "earned": entry["id"] in earned_ids,
                "progress": progress_fn() if progress_fn else None,
            }
        )
    return summary


achievements_open = False

# Unlock toast + hub-dashboard link (TODO.md "roll achievements out
# everywhere" — required on top of the base per-game rollout, per
# ACHIEVEMENTS-SYSTEM-DESIGN.md's site-wide goal). Same pattern as SOL's
# reference retrofit: a snapshot of which ids were already earned as of
# the last seed point, so a fresh load or a loaded save doesn't flood the
# player with toasts for achievements it already satisfies.
_achievements_seen_ids = set()


def _seed_achievement_toast_baseline():
    global _achievements_seen_ids
    _achievements_seen_ids = set(achievement_ids_earned())


def _display_achievement_toast(message):
    toast = document.getElementById("achievement-toast")
    text = document.getElementById("achievement-toast-text")
    text.innerText = message
    toast.hidden = False
    toast.classList.add("visible")

    def _hide(*args):
        toast.hidden = True
        toast.classList.remove("visible")
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, 4000)


def _check_new_achievements_for_toast():
    """Called after every player action that could change earned status
    (build/retire/maintain/advance round) — never from render() itself,
    since load_state() also calls render() and a loaded save with several
    achievements already earned must not flood the player with toasts for
    all of them at once (see _seed_achievement_toast_baseline)."""
    global _achievements_seen_ids
    earned_now = set(achievement_ids_earned())
    newly = earned_now - _achievements_seen_ids
    if newly:
        by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
        labels = [by_id[aid]["label"] for aid in newly if aid in by_id]
        if labels:
            if len(labels) == 1:
                _display_achievement_toast(f"🏆 Achievement unlocked: {labels[0]}")
            else:
                _display_achievement_toast(f"🏆 {len(labels)} achievements unlocked: " + ", ".join(labels))
    _achievements_seen_ids = earned_now


def on_toggle_achievements(event=None):
    global achievements_open
    achievements_open = not achievements_open
    update_achievements_display()


def update_achievements_display():
    toggle = document.getElementById("achievements-toggle-button")
    panel = document.getElementById("achievements-panel")
    earned_count = len(achievement_ids_earned())
    toggle.innerText = (
        f"Hide Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
        if achievements_open
        else f"🏆 Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
    )
    panel.hidden = not achievements_open
    if not achievements_open:
        return

    panel.innerHTML = ""
    for entry in achievements_summary():
        card = document.createElement("div")
        card.className = "achievement-card achievement-card--earned" if entry["earned"] else "achievement-card"

        label = document.createElement("p")
        label.className = "achievement-card-label"
        label.innerText = f"🏆 {entry['label']}" if entry["earned"] else entry["label"]
        card.appendChild(label)

        description = document.createElement("p")
        description.className = "achievement-card-description"
        description.innerText = entry["description"]
        card.appendChild(description)

        if not entry["earned"] and entry["progress"] is not None:
            current, target = entry["progress"]
            progress = document.createElement("p")
            progress.className = "achievement-card-progress"
            progress.innerText = f"{current} of {target}"
            card.appendChild(progress)

        panel.appendChild(card)

    # A link out to the hub-wide achievements dashboard (root index.html's
    # #account-achievements-dashboard, ACHIEVEMENTS-SYSTEM-DESIGN.md §5),
    # same convention as SOL's reference retrofit. Relative path, no
    # leading "/" (site-level milestone 7's GitHub Pages subpath fix).
    # Rebuilt each open alongside the cards since the panel is cleared
    # first. Note: the hub-side script.js registration that makes Grid's
    # save data actually show up on that dashboard is a root-file change,
    # out of scope for this games/grid/-only dispatch — see CLAUDE.md.
    hub_link = document.createElement("a")
    hub_link.innerText = "View the hub-wide achievements dashboard →"
    hub_link.href = "../../index.html#account-achievements-dashboard"
    hub_link.className = "achievements-hub-link"
    panel.appendChild(hub_link)


# Rendering/toggle logic lives in shared/info_page.py now (see that
# module's docstring) -- this used to be a ~25+4 line implementation
# byte-identical across all 8 climate games. info_page_open stays local
# here since it's part of this game's save contract.
def render_info_page():
    info_page.render(INFO_PAGE, info_page_open)


def on_toggle_info_page(event=None):
    global info_page_open
    info_page_open = info_page.toggle(info_page_open)
    render_info_page()


def render():
    render_info_page()
    update_achievements_display()
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
    document.getElementById("disruption-risk-display").innerText = disruption_risk_message(
        state.disruption_probability(), state.disruption_severity()
    )

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

    document.getElementById("renewable-milestone-callout").hidden = not renewable_milestone_visible
    document.getElementById("retire-callout").hidden = not retire_callout_visible
    document.getElementById("maintain-callout").hidden = not maintain_callout_visible

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

        # C10: the exact wear percentage next to the coarse wear-icon
        # state -- only meaningful once a unit is actually standing.
        wear_pct_el = document.getElementById(f"{plant_type}-wear-pct")
        wear_pct_el.innerText = f"{state.wear_percent(plant_type)}% worn" if count > 0 else ""

        # C19: a breakdown-risk badge once this type's own average age
        # has crossed the risk threshold, independent of whether it's
        # currently *the* oldest type (the one actually at risk this
        # round -- see breakdown_risk_probability()'s docstring).
        risk_badge = document.getElementById(f"{plant_type}-risk-badge")
        risk_probability = state.breakdown_risk_probability(plant_type) if count > 0 else 0.0
        risk_badge.hidden = risk_probability <= 0.0
        if not risk_badge.hidden:
            risk_badge.innerText = f"⚠ Aging risk ({risk_probability * 100:.0f}%)"

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
        _check_renewable_milestone()
        render()
        _check_new_achievements_for_toast()
    return handler


# C8 -- transient (never saved) "currently showing" flag for the one-time
# 50%-renewable-capacity callout, same reasoning as C20's callouts below:
# state.renewable_50_reached is the persisted "has this ever happened"
# gate, this is just whether it's visible in this session right now.
renewable_milestone_visible = False


def _check_renewable_milestone():
    """Called after every action that could change capacity composition
    (build/retire/advance round) -- not from render() itself, so a loaded
    save doesn't flash the callout purely from being rendered once."""
    global renewable_milestone_visible
    if not state.renewable_50_reached and renewable_capacity_share() >= 0.5:
        state.renewable_50_reached = True
        renewable_milestone_visible = True


def on_dismiss_renewable_milestone(event=None):
    global renewable_milestone_visible
    renewable_milestone_visible = False
    render()


# C20 -- transient (never saved) "currently showing" flags for the
# first-use callouts below. state.seen_retire_callout/seen_maintain_callout
# are the persisted "have we ever shown this" gate; these two control
# whether it's visible *right now* in this session, so a loaded save that
# already has the persisted flag set doesn't re-flash the callout on load.
retire_callout_visible = False
maintain_callout_visible = False


def _make_retire_handler(plant_type):
    def handler(event=None):
        global retire_callout_visible
        succeeded = state.retire_plant(plant_type)
        if succeeded and not state.seen_retire_callout:
            state.seen_retire_callout = True
            retire_callout_visible = True
        _check_renewable_milestone()
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_maintain_handler(plant_type):
    def handler(event=None):
        global maintain_callout_visible
        succeeded = state.maintain_plant(plant_type)
        if succeeded and not state.seen_maintain_callout:
            state.seen_maintain_callout = True
            maintain_callout_visible = True
        render()
        _check_new_achievements_for_toast()
    return handler


def on_dismiss_retire_callout(event=None):
    global retire_callout_visible
    retire_callout_visible = False
    render()


def on_dismiss_maintain_callout(event=None):
    global maintain_callout_visible
    maintain_callout_visible = False
    render()


DISRUPTION_TOAST_SEVERITY_CLASSES = ("disruption-toast--warning", "disruption-toast--danger")


def _display_disruption_toast(message, severity_class):
    """C12: a visible toast/banner for a disruption or aging-breakdown
    event, on top of the persistent #event-display/#aging-event-display
    status lines -- those require scrolling to notice; this surfaces the
    same information immediately regardless of scroll position. Same
    show-then-auto-hide shape as the achievement-unlock toast, styled by
    severity rather than always the same color."""
    toast = document.getElementById("disruption-toast")
    text = document.getElementById("disruption-toast-text")
    text.innerText = message
    for cls in DISRUPTION_TOAST_SEVERITY_CLASSES:
        toast.classList.remove(cls)
    toast.classList.add(severity_class)
    toast.hidden = False
    toast.classList.add("visible")

    def _hide(*args):
        toast.hidden = True
        toast.classList.remove("visible")
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, 5000)


def _check_disruption_toast():
    """Called only from on_advance_round(), right after a round resolves:
    a disruption event takes priority over an aging breakdown when both
    land the same round, matching render()'s own priority (a "damage"
    disruption event already implies a plant went offline this round, the
    more urgent read)."""
    if state.last_event is not None:
        severity_class = (
            "disruption-toast--danger" if state.last_event["type"] == "damage" else "disruption-toast--warning"
        )
        _display_disruption_toast(event_message(state.last_event), severity_class)
    elif state.last_aging_event is not None:
        plant_name = PLANT_LABEL[state.last_aging_event["plant"]]
        cost = state.last_aging_event["repair_cost"]
        _display_disruption_toast(
            f"Aging breakdown! A {plant_name} plant failed from wear (repair cost {cost:.0f}).",
            "disruption-toast--danger",
        )


def on_advance_round(event=None):
    state.advance_round()
    _check_renewable_milestone()
    render()
    _check_disruption_toast()
    _check_new_achievements_for_toast()


# SAVE-BUTTON-INTEGRATION.md contract for the shared shared/save-widget.js:
# get_state() returns every module-level mutable global (the GridState
# instance's attributes, plus the info-page toggle) as one plain,
# JSON-safe dict. get_state() deep-copies every nested mutable container
# (plant_counts, cumulative_built, plant_age, event_log, last_event, the
# history lists, last_aging_event) on the way out, so a live reference is
# never shared between the saved snapshot and continued play — same
# reasoning as SOL's serialize_state() docstring. Grid has no non-JSON-
# native types (no sets) in its state, unlike SOL's unlocked_bodies.
# load_state() is its inverse, but not a blind mirror: plant_counts,
# cumulative_built and plant_age are merged into the live dicts key-by-key
# (_merge_plant_dict) rather than replacing them wholesale, so a save
# missing a plant-type key can't drop that key from live state entirely.
def get_state():
    return {
        "round_number": state.round_number,
        "demand": state.demand,
        "funds": state.funds,
        "plant_counts": copy.deepcopy(state.plant_counts),
        "cumulative_built": copy.deepcopy(state.cumulative_built),
        "emissions": state.emissions,
        "event_log": copy.deepcopy(state.event_log),
        "last_event": copy.deepcopy(state.last_event),
        "clean_fraction_log": list(state.clean_fraction_log),
        "emissions_history": list(state.emissions_history),
        "avg_renewable_cost_history": list(state.avg_renewable_cost_history),
        "renewable_unlocked": state.renewable_unlocked,
        "plant_age": copy.deepcopy(state.plant_age),
        "global_reference_emissions": state.global_reference_emissions,
        "global_reference_emissions_history": list(state.global_reference_emissions_history),
        "last_aging_event": copy.deepcopy(state.last_aging_event),
        "info_page_open": info_page_open,
        "maintenance_actions_count": state.maintenance_actions_count,
        "current_clean_streak": state.current_clean_streak,
        "best_clean_streak": state.best_clean_streak,
        "seen_retire_callout": state.seen_retire_callout,
        "seen_maintain_callout": state.seen_maintain_callout,
        "renewable_50_reached": state.renewable_50_reached,
        # Write-only projection (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) — always
        # freshly recomputed, never read back in load_state() below.
        "achievements_earned": achievement_ids_earned(),
    }


def _merge_plant_dict(live, saved):
    """Writes a saved per-plant-type dict into the live one key-by-key,
    rather than replacing it wholesale. The key set (PLANT_TYPES) belongs
    to game.py, not to the save: a save written before a plant type
    existed (or a hand-edited/truncated payload) can be missing one of
    those keys, and every consumer (render(), total_capacity(),
    plant_cost(), ...) does live[plant_type] unconditionally for every
    type in PLANT_TYPES — a wholesale replace would drop the missing key
    from the dict entirely and crash on the very next access, after the
    save widget already reported a successful load. Keys the save doesn't
    know about simply keep their current live value."""
    for plant_type in live:
        if plant_type in saved:
            live[plant_type] = saved[plant_type]


def load_state(data):
    global info_page_open

    # Every field is pulled with .get(..., <current live value>) rather
    # than bare data["key"] indexing, so a save written before a later
    # milestone/pass added a field (global_reference_emissions and
    # global_reference_emissions_history, last_aging_event and plant_age
    # all landed in Pass 2, after Milestone 1/2 saves already existed)
    # can't crash load_state() with a KeyError -- a missing key just
    # leaves that field at whatever the live state already had, the same
    # "don't drop what the save doesn't know about" philosophy
    # _merge_plant_dict already applies one level deeper.
    state.round_number = data.get("round_number", state.round_number)
    state.demand = data.get("demand", state.demand)
    state.funds = data.get("funds", state.funds)
    _merge_plant_dict(state.plant_counts, data.get("plant_counts", {}))
    _merge_plant_dict(state.cumulative_built, data.get("cumulative_built", {}))
    state.emissions = data.get("emissions", state.emissions)
    state.event_log = copy.deepcopy(data.get("event_log", state.event_log))
    state.last_event = copy.deepcopy(data.get("last_event", state.last_event))
    state.clean_fraction_log = list(data.get("clean_fraction_log", state.clean_fraction_log))
    state.emissions_history = list(data.get("emissions_history", state.emissions_history))
    state.avg_renewable_cost_history = list(
        data.get("avg_renewable_cost_history", state.avg_renewable_cost_history)
    )
    state.renewable_unlocked = data.get("renewable_unlocked", state.renewable_unlocked)
    _merge_plant_dict(state.plant_age, data.get("plant_age", {}))
    state.global_reference_emissions = data.get(
        "global_reference_emissions", state.global_reference_emissions
    )
    state.global_reference_emissions_history = list(
        data.get("global_reference_emissions_history", state.global_reference_emissions_history)
    )
    state.last_aging_event = copy.deepcopy(data.get("last_aging_event", state.last_aging_event))
    info_page_open = data.get("info_page_open", info_page_open)
    state.maintenance_actions_count = data.get("maintenance_actions_count", state.maintenance_actions_count)
    state.current_clean_streak = data.get("current_clean_streak", state.current_clean_streak)
    state.best_clean_streak = data.get("best_clean_streak", state.best_clean_streak)
    state.seen_retire_callout = data.get("seen_retire_callout", state.seen_retire_callout)
    state.seen_maintain_callout = data.get("seen_maintain_callout", state.seen_maintain_callout)
    state.renewable_50_reached = data.get("renewable_50_reached", state.renewable_50_reached)
    # "achievements_earned" is intentionally never read back here — see
    # get_state()'s comment and ACHIEVEMENTS-SYSTEM-DESIGN.md §1.

    render()
    _seed_achievement_toast_baseline()
    return True


def setup():
    # index.html already marks this hidden via the `hidden` attribute, but
    # that markup default doesn't exist for the pytest fake-DOM harness (a
    # FakeElement starts with hidden=False) -- setting it explicitly here
    # keeps both environments consistent and costs nothing in a real
    # browser, where it's already true.
    document.getElementById("achievement-toast").hidden = True
    document.getElementById("disruption-toast").hidden = True
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
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("renewable-milestone-dismiss-button").addEventListener(
        "click", create_proxy(on_dismiss_renewable_milestone)
    )
    document.getElementById("retire-callout-dismiss-button").addEventListener(
        "click", create_proxy(on_dismiss_retire_callout)
    )
    document.getElementById("maintain-callout-dismiss-button").addEventListener(
        "click", create_proxy(on_dismiss_maintain_callout)
    )
    render()
    _seed_achievement_toast_baseline()


setup()
