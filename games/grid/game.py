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

# C2 -- "battery" is a grid-storage tier, not a generation tier: it never
# produces power of its own, so it's deliberately excluded from
# GENERATION_TYPES below (total_capacity()/fossil_share()/the plant-mix
# chart all stay generation-only) and from RENEWABLE_TYPES (it doesn't
# offset emissions directly, so it must never count toward the
# clean-capacity-share metric the achievements/callouts are built on --
# that would let a player "go clean" by buying storage instead of
# actually building clean generation, undermining the whole lesson).
# Its mechanical role is scoped narrowly and directly to what real grid
# storage actually does: buffer renewable intermittency -- see
# GridState.effective_capacity_for_revenue()'s weather-variability
# compensation. It deliberately does NOT dampen emissions-driven
# disruption/brownout losses -- that's a different mechanic (grid
# instability from a dirty fleet), and blunting it with a purchasable
# item would dilute the emissions-disruption link Pass 3 confirmed is
# this game's central lesson-carrying mechanism.
PLANT_TYPES = ["coal", "gas", "nuclear", "solar", "wind", "hydro", "battery"]

GENERATION_TYPES = tuple(t for t in PLANT_TYPES if t != "battery")

PLANT_LABEL = {
    "coal": "Coal",
    "gas": "Gas",
    "nuclear": "Nuclear",
    "solar": "Solar",
    "wind": "Wind",
    "hydro": "Hydro",
    "battery": "Battery Storage",
}

PLANT_ICON = {
    "coal": "⚫",  # black circle
    "gas": "\U0001F525",  # fire
    "nuclear": "☢️",  # radioactive
    "solar": "☀️",  # sun
    "wind": "\U0001F4A8",  # dash/wind
    "hydro": "\U0001F4A7",  # droplet
    "battery": "\U0001F50B",  # battery
}

# Flat, un-degraded costs and generation capacity per unit. Renewable
# cost decay off these base costs is applied by plant_cost() below.
# Battery's "capacity" is storage-buffer capacity, not generation --
# see effective_capacity_for_revenue().
PLANT_BASE_COST = {
    "coal": 50,
    "gas": 40,
    "nuclear": 200,
    "solar": 80,
    "wind": 70,
    "hydro": 150,
    "battery": 120,
}

PLANT_CAPACITY = {
    "coal": 20,
    "gas": 15,
    "nuclear": 100,
    "solar": 10,
    "wind": 12,
    "hydro": 40,
    "battery": 15,
}

# Emissions produced per unit of capacity, per round, while that capacity
# is part of the fleet. Nuclear counts as zero-emission but — realistically,
# and per the plan's framing — isn't part of the renewable cost-curve
# below; its cost stays flat. Battery is also zero-emission (it stores,
# doesn't generate).
EMISSIONS_FACTOR = {
    "coal": 3.0,
    "gas": 1.5,
    "nuclear": 0.0,
    "solar": 0.0,
    "wind": 0.0,
    "hydro": 0.0,
    "battery": 0.0,
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

# C16 -- opt-in "steeper demand growth" difficulty variant. A separate
# knob from the emissions-driven disruption curve above (see CLAUDE.md's
# Pass 3 note: that curve is the one that has to scale with the mechanic
# that teaches the lesson, emissions, not a bolted-on separate difficulty
# system) -- this only changes how fast demand rises, it never touches
# disruption_probability()/disruption_severity() or their inputs.
STEEP_DEMAND_GROWTH_MULTIPLIER = 2.0

# C4 -- opt-in "weather variability on renewable output" hard mode.
# Explicitly scoped out of Pass 1 as a deliberate deferral (see CLAUDE.md);
# picked back up here as an opt-in extra, never default-on, and -- same
# reasoning as C16 above -- a separate knob from the emissions-driven
# disruption curve. This only ever affects this round's *actual* output
# for revenue purposes; it never touches total_capacity() (the "installed"
# figure used for cost/display elsewhere), emissions, or disruption math.
WEATHER_VARIANCE_FRACTION = 0.2

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

# C17 -- the closing "grid vs. business-as-usual" counterfactual: a
# self-comparison against a hypothetical grid that built the exact same
# total capacity this playthrough did, but entirely as coal, tracked
# round by round in GridState.bau_emissions (see advance_round()).
# Deliberately isolates the fuel-mix decision by holding how much got
# built constant -- a demand-based version would instead reward
# under-building relative to rising demand as if it were "clean," which
# isn't the lesson this is meant to teach. Also distinct from the Pass 2
# global-average-fossil-mix benchmark above: that one answers "how do I
# compare to the real world," this one answers "how much did *my own*
# fuel-mix choices this run actually save."
BAU_EMISSIONS_FACTOR = EMISSIONS_FACTOR["coal"]

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

# C26 -- three distinct wear-tier glyphs (plus "fresh"), a shape cue that
# reads independently of the wear-1/2/3 CSS desaturation on the name.
WEAR_TIER_GLYPH = {"": "\u25CB", "wear-1": "\u25D4", "wear-2": "\u25D1", "wear-3": "\u25CF"}

# C13 -- starting scenarios, selectable only before anything has been built
# or any round played. Each is a fixed opening fleet + funds.
SCENARIOS = {
    "standard": {"label": "Standard start", "funds": STARTING_FUNDS, "plants": {}},
    "coal_legacy": {
        "label": "Coal-heavy legacy grid",
        "funds": 300,
        "plants": {"coal": 4, "gas": 1},
    },
    "greenfield": {
        "label": "Greenfield renewable-first",
        "funds": 700,
        "plants": {},
    },
    # C27 -- opt-in emergency-response scenario: the grid starts already
    # short of demand after a major disruption. See GridState.emergency.
    "emergency": {
        "label": "Emergency response",
        "funds": 300,
        "plants": {"coal": 3, "gas": 1},
        "demand": 180,
    },
}
SCENARIO_ORDER = ["standard", "coal_legacy", "greenfield", "emergency"]

# C27 -- the player has EMERGENCY_ROUNDS rounds to bring capacity up to
# demand and hold it there for EMERGENCY_HOLD_ROUNDS rounds in a row. There
# is no game over (root design rule): missing the window just closes the
# emergency as "not stabilized in time" and the run carries on.
EMERGENCY_ROUNDS = 6
EMERGENCY_HOLD_ROUNDS = 2

# C9 -- storage arbitrage. Batteries hold up to ARBITRAGE_STORAGE_MULTIPLE x
# their own capacity, charge/discharge at their own capacity per round, lose
# (1 - ARBITRAGE_EFFICIENCY) of what they charge, and sell discharged energy
# at a peak-price premium. Modes are chosen by the player each round.
ARBITRAGE_MODES = ("idle", "charge", "discharge")
ARBITRAGE_STORAGE_MULTIPLE = 2
ARBITRAGE_EFFICIENCY = 0.85
ARBITRAGE_PEAK_PRICE_MULTIPLIER = 1.5

# C25 -- how far the "grid of the future" projection looks ahead.
PROJECTION_ROUNDS = 20

# Round-3 pass (2026-09-20) additions below -- see CLAUDE.md's own build
# note for the full rationale on each.

# TODO-C7 -- demand response: a fourth lever alongside build/retire/
# maintain. Each purchase permanently trims this round's demand growth by
# a fixed amount, at an escalating cost (mirrors the renewable learning
# curve's shape but in reverse -- each purchase costs more than the last,
# since a grid gets harder to trim further the more efficient it already
# is). Floored so demand growth can never go negative or stall entirely.
DEMAND_RESPONSE_BASE_COST = 150
DEMAND_RESPONSE_COST_GROWTH = 1.35
DEMAND_RESPONSE_REDUCTION_PER_LEVEL = 1.5
DEMAND_RESPONSE_MIN_GROWTH = 3.0

# TODO-C17 -- weather-event log: a running narration of how Weather
# Variability actually affected renewable output round to round, separate
# from the emissions-driven disruption log. Capped the same way
# event_log/ticker-style logs are capped elsewhere in the quartet, so a
# very long run's save doesn't grow this list unboundedly.
WEATHER_LOG_MAX_ENTRIES = 30

# TODO-C19 -- policy lever: an occasional opt-in choice that temporarily
# shifts the cost curve, offered every POLICY_LEVER_INTERVAL rounds if no
# policy is currently active. Carbon pricing makes fossil more expensive
# to build; a renewable subsidy makes renewables cheaper to build. Both
# are build-time-only price signals -- see GridState.plant_cost()'s
# comment on why Retire deliberately never refunds off the policy price.
POLICY_LEVER_INTERVAL = 6
POLICY_LEVER_DURATION = 4
CARBON_PRICING_FOSSIL_COST_MULTIPLIER = 1.3
RENEWABLE_SUBSIDY_COST_MULTIPLIER = 0.75

# TODO-C23 -- maintenance scheduling: pre-commit a plant type to an
# auto-maintain cadence instead of manually clicking Maintain every time.
# 0 means "off" (manual only, the pre-existing behavior).
MAINTENANCE_SCHEDULE_OPTIONS = (0, 3, 5, 8)


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
        # C17 -- cumulative emissions for the business-as-usual
        # counterfactual: what this exact same installed capacity would
        # have emitted had it all been built as coal. Evolves
        # independently each round in advance_round(), the same "shadow
        # trajectory" pattern as global_reference_emissions above -- never
        # recomputed from history, so it survives save/load exactly like
        # every other running total.
        self.bau_emissions = 0.0
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
        # C13 -- lifetime running totals per spend/income category, for
        # the funds-breakdown display. Mutated only where funds already
        # change for that reason -- no new call sites invented, and
        # nothing here changes what any of those existing debits/credits
        # actually are (see build_plant()/retire_plant()'s own comments
        # on the flat-refund exploit this game already audited and fixed
        # once -- this is pure additive bookkeeping alongside that math,
        # not a second implementation of it).
        self.lifetime_revenue = 0.0
        self.lifetime_build_spend = 0.0
        self.lifetime_maintenance_spend = 0.0
        self.lifetime_disruption_spend = 0.0
        # C16 -- opt-in "steeper demand growth" difficulty variant, off by
        # default. Persisted so it stays set across a save/load.
        self.steeper_demand_growth_enabled = False
        # C4 -- opt-in weather-variability hard mode, off by default.
        self.weather_variability_enabled = False
        # C13 -- which starting scenario was applied (see SCENARIOS).
        self.scenario = "standard"
        # TODO-C7 -- demand-response investment level (see constants above).
        self.demand_response_level = 0
        # TODO-C17 -- weather-event log entries, newest last (rendered
        # newest-first). Also two scratch fields effective_capacity_for_
        # revenue() fills in each call so advance_round() can narrate what
        # actually happened without re-consuming weather_rng a second time.
        self.weather_log = []
        self.last_weather_renewable_nameplate = 0.0
        self.last_weather_renewable_actual = 0.0
        # TODO-C19 -- policy lever: offered periodically, opt-in, one at a
        # time (see constants above).
        self.policy_lever_available = False
        self.active_policy = None
        self.last_policy_lever_round_offered = 0
        # TODO-C23 -- per-plant-type auto-maintain cadence, 0 = manual only.
        self.maintenance_schedule = {t: 0 for t in PLANT_TYPES}
        # C9 -- storage arbitrage: stored energy units, the player's chosen
        # mode for the next round, and the last round's result for display.
        self.stored_energy = 0.0
        self.arbitrage_mode = "idle"
        self.last_arbitrage = None
        self.arbitrage_revenue_total = 0.0
        # C27 -- None outside the emergency scenario, else a dict
        # {"status": "active"|"stabilized"|"missed", "rounds_left", "hold"}.
        self.emergency = None

    def storage_cap(self):
        """C9: max stored energy the battery fleet can hold."""
        return self.battery_capacity() * ARBITRAGE_STORAGE_MULTIPLE

    def set_arbitrage_mode(self, mode):
        if mode not in ARBITRAGE_MODES:
            return False
        self.arbitrage_mode = mode
        return True

    def _run_arbitrage(self, effective_capacity):
        """C9: called from advance_round() with this round's effective
        generation. Charging banks surplus (generation above demand, which
        earns nothing otherwise) at ARBITRAGE_EFFICIENCY; discharging sells
        stored energy into a shortfall at a peak-price premium. Returns the
        extra revenue. Never touches emissions/disruption math."""
        # A retired battery shrinks the cap; anything above it is lost.
        self.stored_energy = min(self.stored_energy, self.storage_cap())
        rate = self.battery_capacity()
        self.last_arbitrage = None
        if rate <= 0 or self.arbitrage_mode == "idle":
            return 0.0
        if self.arbitrage_mode == "charge":
            surplus = max(0.0, effective_capacity - self.demand)
            taken = min(surplus, rate, (self.storage_cap() - self.stored_energy) / ARBITRAGE_EFFICIENCY)
            self.stored_energy += taken * ARBITRAGE_EFFICIENCY
            self.last_arbitrage = {"mode": "charge", "units": taken, "revenue": 0.0}
            return 0.0
        shortfall = max(0.0, self.demand - effective_capacity)
        sold = min(shortfall, rate, self.stored_energy)
        revenue = sold * REVENUE_PER_UNIT_MET * ARBITRAGE_PEAK_PRICE_MULTIPLIER
        self.stored_energy -= sold
        self.arbitrage_revenue_total += revenue
        self.last_arbitrage = {"mode": "discharge", "units": sold, "revenue": revenue}
        return revenue

    def _update_emergency(self):
        """C27: called at the end of advance_round() (demand already grown)."""
        em = self.emergency
        if em is None or em["status"] != "active":
            return
        em["rounds_left"] -= 1
        if self.total_capacity() >= self.demand:
            em["hold"] += 1
        else:
            em["hold"] = 0
        if em["hold"] >= EMERGENCY_HOLD_ROUNDS:
            em["status"] = "stabilized"
        elif em["rounds_left"] <= 0:
            em["status"] = "missed"

    def apply_scenario(self, scenario_id):
        """C13: only allowed before anything has been built/advanced, so a
        scenario can never be used to reset progress mid-run."""
        if scenario_id not in SCENARIOS:
            return False
        if self.round_number != 1 or any(self.cumulative_built.values()):
            return False
        scenario = SCENARIOS[scenario_id]
        self.plant_counts = {t: 0 for t in PLANT_TYPES}
        for plant_type, count in scenario["plants"].items():
            self.plant_counts[plant_type] = count
        self.funds = scenario["funds"]
        self.demand = scenario.get("demand", STARTING_DEMAND)
        self.emergency = (
            {"status": "active", "rounds_left": EMERGENCY_ROUNDS, "hold": 0}
            if scenario_id == "emergency"
            else None
        )
        self.scenario = scenario_id
        return True

    def _learning_curve_cost(self, plant_type):
        """The plant's cost before any temporary TODO-C19 policy-lever
        adjustment -- base cost adjusted only by the renewable learning
        curve. retire_plant() refunds off *this*, never off plant_cost()'s
        policy-adjusted price: a policy multiplier is a build-time-only
        price signal, not a permanent value change, and basing a refund on
        it would open an exploit in one direction (build cheap during a
        renewable subsidy, retire later for a refund based on the same
        discounted price is fine and symmetric -- but the concern is
        whether *any* combination nets a profit). It never can: the
        refund fraction is a flat 50%, and neither the subsidy (25% off)
        nor stacking it with the learning-curve floor discount pushes the
        price a player actually paid below double what a 50%-of-base-cost
        refund would return, so there's no direction where this pays out
        more than it cost -- same reasoning already documented on
        REFUND_FRACTION's fix elsewhere in this file, just re-verified
        against this new temporary-price case."""
        base = PLANT_BASE_COST[plant_type]
        if plant_type not in RENEWABLE_TYPES:
            return base
        multiplier = max(
            MIN_COST_MULTIPLIER,
            RENEWABLE_COST_DECAY ** self.cumulative_built[plant_type],
        )
        return base * multiplier

    def plant_cost(self, plant_type):
        """The actual price to build this plant type right now, including
        any active TODO-C19 policy-lever adjustment. Use
        _learning_curve_cost() instead when computing a Retire refund --
        see that method's docstring."""
        cost = self._learning_curve_cost(plant_type)
        if self.active_policy is not None:
            policy_type = self.active_policy["type"]
            if policy_type == "carbon_pricing" and plant_type in FOSSIL_TYPES:
                cost *= CARBON_PRICING_FOSSIL_COST_MULTIPLIER
            elif policy_type == "renewable_subsidy" and plant_type in RENEWABLE_TYPES:
                cost *= RENEWABLE_SUBSIDY_COST_MULTIPLIER
        return cost

    def total_capacity(self):
        # Generation only -- battery is storage, not generation (see
        # GENERATION_TYPES' comment above PLANT_TYPES).
        return sum(self.plant_counts[t] * PLANT_CAPACITY[t] for t in GENERATION_TYPES)

    def battery_capacity(self):
        """C2: total storage-buffer capacity, in the same units as
        PLANT_CAPACITY -- used only by effective_capacity_for_revenue()'s
        weather-variability compensation, never counted as generation."""
        return self.plant_counts["battery"] * PLANT_CAPACITY["battery"]

    def fossil_capacity(self):
        return sum(self.plant_counts[t] * PLANT_CAPACITY[t] for t in ("coal", "gas"))

    def fossil_share(self):
        total = self.total_capacity()
        if total == 0:
            return 0.0
        return self.fossil_capacity() / total

    def capacity_share(self, plant_type):
        """C7: this type's share of total standing capacity, 0..1 -- the
        per-type generalization of fossil_share()/renewable_capacity_share(),
        for the plant-mix bar chart."""
        total = self.total_capacity()
        if total == 0:
            return 0.0
        return (self.plant_counts[plant_type] * PLANT_CAPACITY[plant_type]) / total

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
        self.lifetime_build_spend += cost
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
        self.funds += self._learning_curve_cost(plant_type) * REFUND_FRACTION
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
        self.lifetime_maintenance_spend += cost
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

    def effective_capacity_for_revenue(self, weather_rng=random.random):
        """C4: this round's actual output for revenue purposes -- equal to
        total_capacity() unless weather_variability_enabled, in which case
        each renewable type's contribution is scaled by an independent
        random factor in [1 - WEATHER_VARIANCE_FRACTION, 1 +
        WEATHER_VARIANCE_FRACTION] (fossil/nuclear are dispatchable and
        unaffected). Never mutates total_capacity()'s own inputs -- this is
        purely how much of the installed fleet actually generated this
        round, not a change to what's installed.

        C2: battery buffer capacity compensates for a *shortfall* below
        renewables' combined nameplate (a bad-weather round), up to the
        battery fleet's own capacity -- this is the one place battery
        capacity ever contributes to revenue, and only when there's
        something to buffer against. It never adds capacity beyond
        covering that shortfall (no free generation), and never touches
        the emissions-driven disruption/brownout math at all (see
        PLANT_TYPES' comment on why that's a deliberately separate axis).
        """
        if not self.weather_variability_enabled:
            # TODO-C17: no weather effect this call -- reset the scratch
            # fields so advance_round() never narrates a stale reading
            # from a round where the toggle was on.
            self.last_weather_renewable_nameplate = 0.0
            self.last_weather_renewable_actual = 0.0
            return self.total_capacity()

        dispatchable_total = 0.0
        renewable_nameplate = 0.0
        renewable_actual = 0.0
        for plant_type in GENERATION_TYPES:
            capacity = self.plant_counts[plant_type] * PLANT_CAPACITY[plant_type]
            if plant_type in RENEWABLE_TYPES:
                renewable_nameplate += capacity
                factor = 1 + (weather_rng() * 2 - 1) * WEATHER_VARIANCE_FRACTION
                renewable_actual += capacity * max(0.0, factor)
            else:
                dispatchable_total += capacity

        # TODO-C17: stash this round's nameplate/actual renewable output so
        # advance_round() can narrate it into weather_log without spending
        # a second, non-deterministic call against weather_rng.
        self.last_weather_renewable_nameplate = renewable_nameplate
        self.last_weather_renewable_actual = renewable_actual

        shortfall = max(0.0, renewable_nameplate - renewable_actual)
        compensation = min(self.battery_capacity(), shortfall)
        return dispatchable_total + renewable_actual + compensation

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

    def advance_round(self, rng=random.random, age_rng=random.random, weather_rng=random.random):
        # TODO-C23: run any pre-committed auto-maintenance before this
        # round's own aging/breakdown roll, so a scheduled type actually
        # gets the benefit this round rather than one round late.
        self._run_scheduled_maintenance()

        effective_capacity = self.effective_capacity_for_revenue(weather_rng)
        met_demand = min(effective_capacity, self.demand)
        revenue = met_demand * REVENUE_PER_UNIT_MET
        # C9: optional storage arbitrage on top of ordinary revenue.
        revenue += self._run_arbitrage(effective_capacity)

        # TODO-C17: narrate this round's weather effect on renewable
        # output, using the nameplate/actual figures
        # effective_capacity_for_revenue() just stashed above -- no second
        # weather_rng call, so this never changes the round's own outcome,
        # only whether it gets written down. Skipped when there's no
        # renewable nameplate capacity to have varied in the first place.
        if self.weather_variability_enabled and self.last_weather_renewable_nameplate > 0:
            delta_pct = (
                (self.last_weather_renewable_actual - self.last_weather_renewable_nameplate)
                / self.last_weather_renewable_nameplate
                * 100
            )
            direction = "above" if delta_pct >= 0 else "below"
            self.weather_log.append(
                f"Round {self.round_number}: weather variability put renewable "
                f"output {abs(delta_pct):.0f}% {direction} nameplate capacity."
            )
            if len(self.weather_log) > WEATHER_LOG_MAX_ENTRIES:
                self.weather_log = self.weather_log[-WEATHER_LOG_MAX_ENTRIES:]

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
        self.lifetime_revenue += revenue
        if event is not None:
            self.lifetime_disruption_spend += event["revenue_loss"]
        self.emissions += self.emissions_this_round()
        self.global_reference_emissions += (
            self.total_capacity() * GLOBAL_AVG_FOSSIL_SHARE * GLOBAL_AVG_FOSSIL_EMISSIONS_FACTOR
        )
        # C17 -- same installed capacity this round, same basis
        # emissions_this_round() itself uses, priced against "what if
        # this had all just been coal" instead of whatever mix the player
        # actually built. Deliberately total_capacity()-based rather than
        # demand-based: the counterfactual isolates the *fuel-mix*
        # decision specifically, holding how much got built constant, so
        # a grid that's genuinely all-coal correctly nets to zero avoided
        # emissions instead of showing a misleading "savings" purely from
        # under-building relative to rising demand.
        self.bau_emissions += self.total_capacity() * BAU_EMISSIONS_FACTOR

        aging_event = None
        oldest = self.oldest_vulnerable_plant()
        for plant_type in PLANT_TYPES:
            if self.plant_counts[plant_type] > 0:
                self.plant_age[plant_type] += 1
        if oldest is not None and age_rng() < self.aging_breakdown_probability():
            self.plant_counts[oldest] -= 1
            repair_cost = PLANT_BASE_COST[oldest] * AGING_BREAKDOWN_COST_FRACTION
            self.funds = max(0.0, self.funds - repair_cost)
            self.lifetime_disruption_spend += repair_cost
            aging_event = {"type": "aging_breakdown", "plant": oldest, "repair_cost": repair_cost}

        # TODO-C19: advance the currently-active policy lever's clock, and
        # -- once no policy is active and the offer isn't already sitting
        # open -- check whether it's time to offer a fresh one. Checked
        # against the round that's *about to* start (round_number is still
        # pre-increment here), so "every POLICY_LEVER_INTERVAL rounds"
        # reads the same way a player experiences round numbers in the UI.
        if self.active_policy is not None:
            self.active_policy["rounds_remaining"] -= 1
            if self.active_policy["rounds_remaining"] <= 0:
                self.active_policy = None
        if (
            self.active_policy is None
            and not self.policy_lever_available
            and self.round_number > self.last_policy_lever_round_offered
            and self.round_number % POLICY_LEVER_INTERVAL == 0
        ):
            self.policy_lever_available = True

        self.round_number += 1
        # TODO-C7: demand_growth_this_round() is the single source of truth
        # for how much demand rises this round, including any demand-
        # response investment -- see that method's own docstring.
        self.demand += self.demand_growth_this_round()

        self.last_event = event
        if event:
            self.event_log.append(event)
            self.current_clean_streak = 0
        else:
            self.current_clean_streak += 1
            self.best_clean_streak = max(self.best_clean_streak, self.current_clean_streak)
        self.last_aging_event = aging_event
        self._update_emergency()

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

    def emissions_avoided(self):
        """C17: cumulative emissions saved vs. the business-as-usual
        coal-only counterfactual in bau_emissions -- the closing summary's
        headline "hope angle" number. Floored at zero so a player who did
        worse than the counterfactual (e.g. never invested at all, so the
        two trajectories are ~equal) never sees a misleading negative."""
        return max(0.0, self.bau_emissions - self.emissions)

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

    def resilience_score(self):
        """C11: diversification as its own axis, 0..100 -- normalized
        Shannon entropy of the generation-capacity shares across the six
        generation types. All-one-type (all-renewable OR all-fossil) scores
        0; an even spread across every type scores 100. Deliberately
        independent of clean share: it rewards not depending on a single
        source, not cleanliness."""
        import math  # noqa: PLC0415

        shares = [self.capacity_share(t) for t in GENERATION_TYPES]
        entropy = -sum(x * math.log(x) for x in shares if x > 0)
        return round(entropy / math.log(len(GENERATION_TYPES)) * 100)

    def projection(self, rounds=PROJECTION_ROUNDS):
        """C25: extrapolates the current fleet unchanged for `rounds` more
        rounds -- emissions if nothing changes, versus the all-coal
        business-as-usual line over the same window, plus where demand
        will be against today's capacity. A straight-line extrapolation,
        deliberately not a forecast of what the player would do. Uses
        demand_growth_this_round() (TODO-C7) so an active demand-response
        investment correctly flattens the projected demand line too."""
        base_growth = self.demand_growth_this_round()
        return {
            "rounds": rounds,
            "emissions": self.emissions + self.emissions_this_round() * rounds,
            "bau_emissions": self.emissions + self.total_capacity() * BAU_EMISSIONS_FACTOR * rounds,
            "demand": self.demand + base_growth * rounds,
            "capacity": self.total_capacity(),
        }

    def benchmark_grade(self):
        """C5: a letter grade of cumulative emissions against the
        real-world benchmark line (global_reference_emissions). None until
        a round has been played (no benchmark to compare against yet)."""
        if self.global_reference_emissions <= 0:
            return None
        ratio = self.emissions / self.global_reference_emissions
        for limit, letter in GRADE_THRESHOLDS:
            if ratio <= limit:
                return letter
        return "F"

    def demand_response_cost(self):
        """TODO-C7: escalating cost for the next demand-response purchase."""
        return DEMAND_RESPONSE_BASE_COST * (DEMAND_RESPONSE_COST_GROWTH ** self.demand_response_level)

    def invest_demand_response(self):
        """TODO-C7: the fourth lever -- spend funds to permanently trim
        this grid's demand growth, rather than build/retire/maintain
        capacity to meet whatever demand turns out to be."""
        cost = self.demand_response_cost()
        if self.funds < cost:
            return False
        self.funds -= cost
        # Counted alongside build spend in the funds breakdown -- it's the
        # same category of "spent on infrastructure," just demand-side
        # instead of supply-side.
        self.lifetime_build_spend += cost
        self.demand_response_level += 1
        return True

    def demand_growth_this_round(self):
        """TODO-C7: DEMAND_GROWTH_PER_ROUND (doubled if the steeper-demand
        difficulty toggle is on), trimmed by demand-response investment,
        floored so growth can never go negative or stall out entirely.
        Single source of truth for advance_round()/projection()/the
        demand-growth-arrow tooltip, so all three always agree."""
        growth = DEMAND_GROWTH_PER_ROUND
        if self.steeper_demand_growth_enabled:
            growth *= STEEP_DEMAND_GROWTH_MULTIPLIER
        growth -= self.demand_response_level * DEMAND_RESPONSE_REDUCTION_PER_LEVEL
        return max(DEMAND_RESPONSE_MIN_GROWTH, growth)

    def enact_policy(self, policy_type):
        """TODO-C19: opt into the currently-offered policy lever. Only one
        can be active at a time; enacting one clears the offer until the
        next POLICY_LEVER_INTERVAL passes."""
        if not self.policy_lever_available:
            return False
        if policy_type not in ("carbon_pricing", "renewable_subsidy"):
            return False
        self.policy_lever_available = False
        self.active_policy = {"type": policy_type, "rounds_remaining": POLICY_LEVER_DURATION}
        self.last_policy_lever_round_offered = self.round_number
        return True

    def decline_policy(self):
        """TODO-C19: opt out of the currently-offered lever without
        enacting either option -- it won't be offered again until the
        next interval."""
        if not self.policy_lever_available:
            return False
        self.policy_lever_available = False
        self.last_policy_lever_round_offered = self.round_number
        return True

    def set_maintenance_schedule(self, plant_type, interval):
        """TODO-C23: pre-commit plant_type to an auto-maintain cadence
        (every `interval` rounds), or pass 0 to go back to manual-only."""
        if plant_type not in self.maintenance_schedule:
            return False
        if interval not in MAINTENANCE_SCHEDULE_OPTIONS:
            return False
        self.maintenance_schedule[plant_type] = interval
        return True

    def _run_scheduled_maintenance(self):
        """TODO-C23: called once at the start of advance_round(), before
        this round's aging/breakdown roll -- so a scheduled maintenance
        pass actually pre-empts the risk it's meant to manage, the same
        round it fires, rather than lagging a round behind. Best-effort:
        a type whose schedule fires but can't afford maintenance this
        round is silently skipped (maintain_plant() already returns False
        for that, same as a manual click on an unaffordable Maintain
        button would)."""
        for plant_type in PLANT_TYPES:
            interval = self.maintenance_schedule[plant_type]
            if interval <= 0:
                continue
            if self.plant_counts[plant_type] <= 0:
                continue
            if self.round_number % interval != 0:
                continue
            self.maintain_plant(plant_type)


# C5 -- ascending (max emissions/benchmark ratio, letter). Above the last
# limit is an "F".
GRADE_THRESHOLDS = [(0.2, "A"), (0.5, "B"), (0.8, "C"), (1.0, "D")]

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


def disruption_reason(event):
    """C10: a 'why this happened' line tied to the specific plant behind the
    event, for the disruption toast."""
    severity_pct = event["severity"] * 100
    if event["type"] == "damage":
        plant = PLANT_LABEL[event["damaged_plant"]]
        return (
            f"Why: accumulated emissions put disruption severity at {severity_pct:.0f}%, past the "
            f"{DAMAGE_SEVERITY_THRESHOLD * 100:.0f}% damage line -- your largest fossil fleet ({plant}) took the hit."
        )
    cause = event.get("cause_plant")
    if cause:
        return (
            f"Why: emissions put disruption severity at {severity_pct:.0f}%, and {PLANT_LABEL[cause]} "
            "is your biggest emissions source."
        )
    return f"Why: historical emissions still put disruption severity at {severity_pct:.0f}%."


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


def trend_graph_svg(emissions_history, cost_history, global_reference_history, clean_fraction_history=None):
    """Three-line trend graph: emissions (rising, red) vs. average
    renewable cost (falling as investment compounds, green) vs. a
    hardcoded global-average emissions benchmark (dashed grey) — the
    Pass 2 addition that gives the player's own emissions line something
    concrete to be measured against, not just a shape in isolation.
    Capped at three lines so it stays legible.

    C15: every point on every line also gets a small hoverable marker
    carrying the exact round/value in a native <title> tooltip, so a
    player who wants a precise number isn't limited to reading it off
    the shape of the line."""
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

    # C15: a small hoverable marker at every data point, each carrying a
    # native SVG <title> tooltip with that round's exact value. No JS
    # event wiring needed -- the browser's own hover-title behavior does
    # the work, consistent with this module keeping real logic in Python
    # rather than adding a parallel JS layer for something this simple.
    def _markers(ys, values, css_class, label):
        return "".join(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" class="trend-point {css_class}">'
            f"<title>Round {i + 1} -- {label}: {v:.0f}</title>"
            f"</circle>"
            for i, (x, y, v) in enumerate(zip(xs, ys, values))
        )

    markers = (
        _markers(global_ys, global_reference_history, "trend-point--global", "Global-average benchmark")
        + _markers(emissions_ys, emissions_history, "trend-point--emissions", "Your emissions")
        + _markers(cost_ys, cost_history, "trend-point--cost", "Avg renewable cost")
    )

    # C12: a diamond marker (shape, not just color) on the emissions line at
    # the player's best round -- highest clean share, earliest on ties.
    best_marker = ""
    if clean_fraction_history and len(clean_fraction_history) == n and max(clean_fraction_history) > 0:
        best_i = clean_fraction_history.index(max(clean_fraction_history))
        bx, by = xs[best_i], emissions_ys[best_i]
        best_marker = (
            f'<polygon points="{bx:.1f},{by - 6:.1f} {bx + 5:.1f},{by:.1f} {bx:.1f},{by + 6:.1f} {bx - 5:.1f},{by:.1f}" '
            f'class="trend-best-marker"><title>Best round: Round {best_i + 1} '
            f"({clean_fraction_history[best_i] * 100:.0f}% clean)</title></polygon>"
        )

    return (
        f'<svg viewBox="0 0 {TREND_GRAPH_WIDTH} {TREND_GRAPH_HEIGHT}" class="trend-graph-svg">'
        f'<polyline points="{global_points}" class="trend-line trend-line--global" />'
        f'<polyline points="{emissions_points}" class="trend-line trend-line--emissions" />'
        f'<polyline points="{cost_points}" class="trend-line trend-line--cost" />'
        f"{markers}"
        f"{best_marker}"
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


def business_as_usual_message(emissions, bau_emissions):
    """C17: the closing counterfactual -- what this exact same installed
    capacity would have emitted had it all been built as coal, compared
    to what this grid actually emitted with its real fuel mix. Distinct
    from global_comparison_message() above: that one benchmarks against a
    real-world-ish average mix, this one isolates this player's own
    fuel-mix decisions specifically, holding how much got built constant."""
    if bau_emissions <= 0:
        return "Not enough rounds yet to compare against a business-as-usual grid."
    avoided = max(0.0, bau_emissions - emissions)
    if avoided <= 0:
        return (
            f"A business-as-usual grid built entirely from coal would have emitted "
            f"{bau_emissions:.0f} by now -- yours has emitted {emissions:.0f}, "
            "no better than staying all-coal so far."
        )
    pct_avoided = (avoided / bau_emissions) * 100
    return (
        f"A business-as-usual grid built entirely from coal would have emitted "
        f"{bau_emissions:.0f} by now. Yours has emitted {emissions:.0f} -- "
        f"{avoided:.0f} avoided ({pct_avoided:.0f}% less)."
    )


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

# C5 -- a dedicated, player-triggered "Run Summary" panel: a score
# breakdown (score, average clean share, the clean-trend comparison) plus
# the existing funds-breakdown numbers restated in one place, closing
# with the C17 business-as-usual counterfactual. Not tied to any hard
# "game over" state (Grid has none, by design -- see CLAUDE.md's "No hard
# fail-state" note) -- it's a summary of the run *so far*, available at
# any point, the same "on-demand panel" shape as the achievements panel
# above rather than a one-time end screen. Deliberately not persisted
# across save/load, same as achievements_open -- purely a this-session
# display preference, not game state.
summary_panel_open = False


def on_toggle_summary_panel(event=None):
    global summary_panel_open
    summary_panel_open = not summary_panel_open
    update_summary_panel()


COMPARE_FALLBACK = "Comparison with other players isn't available yet."


def _request_comparison():
    """C15: asks the page's optional JS hook (window.gridCompare, see
    index.html) to fill #summary-compare with a cross-player percentile.
    Absent hook (pytest, or a page without it) leaves the fallback text."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "gridCompare", None)
    if hook is not None:
        hook(float(state.emissions), state.round_number)


def grade_message():
    """C5: operator-report letter grade vs. the real-world benchmark line."""
    grade = state.benchmark_grade()
    if grade is None:
        return "Operator grade: not graded yet -- play a round to get a benchmark to compare against."
    pct = state.emissions / state.global_reference_emissions * 100
    return (
        f"Operator grade: {grade} -- cumulative emissions are {pct:.0f}% of a "
        "global-average-mix grid's (A: under 20%, B: under 50%, C: under 80%, D: under 100%)."
    )


def projection_message(projection):
    """C25: the 'grid of the future' line."""
    shortfall = projection["demand"] - projection["capacity"]
    demand_note = (
        f"demand would reach {projection['demand']:.0f} against {projection['capacity']} capacity "
        f"({shortfall:.0f} short)"
        if shortfall > 0
        else f"capacity {projection['capacity']} would still cover demand of {projection['demand']:.0f}"
    )
    return (
        f"If you changed nothing for {projection['rounds']} more rounds: emissions would reach "
        f"{projection['emissions']:.0f} (all-coal would be {projection['bau_emissions']:.0f}), and {demand_note}."
    )


def summary_panel_html():
    """C5: the Run Summary panel's content -- pure read of existing
    state/score/funds-breakdown/C17-counterfactual math, no new
    calculations invented here beyond formatting."""
    avg_clean_pct = state.average_clean_fraction() * 100
    lines = [
        f"Round {state.round_number} — sustained clean-grid score: {state.score():.0f}/100",
        f"Average clean share across every round played: {avg_clean_pct:.0f}%",
        clean_trend_message(state.clean_trend()),
        (
            f"Funds so far — revenue: {state.lifetime_revenue:.0f}, spent building: "
            f"{state.lifetime_build_spend:.0f}, spent maintaining: "
            f"{state.lifetime_maintenance_spend:.0f}, lost to disruptions: "
            f"{state.lifetime_disruption_spend:.0f}."
        ),
        f"Best disruption-free streak so far: {state.best_clean_streak} round(s).",
        business_as_usual_message(state.emissions, state.bau_emissions),
        grade_message(),
        f"Grid resilience (diversification, separate from clean share): {state.resilience_score()}/100.",
        projection_message(state.projection()),
    ]
    body = "".join(f'<p class="status-line summary-line">{line}</p>' for line in lines)
    # C15: filled in by index.html's window.gridCompare() when the shared
    # stats endpoint (planning/TODO.md Z1) is reachable; otherwise this
    # fallback text simply stays.
    return body + f'<p id="summary-compare" class="status-line summary-line">{COMPARE_FALLBACK}</p>'


def update_summary_panel():
    toggle = document.getElementById("summary-toggle-button")
    panel = document.getElementById("summary-panel")
    toggle.innerText = "Hide Run Summary" if summary_panel_open else "📊 Run Summary"
    panel.hidden = not summary_panel_open
    if not summary_panel_open:
        return
    panel.innerHTML = summary_panel_html()
    _request_comparison()


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


# ===========================================================================
# "What's New" changelog panel (site-wide goal, planning/TODO.md, origin K16)
# ===========================================================================
# Same static-JSON-asset loading contract as ACHIEVEMENTS above (and SOL's
# reference integration): the boot script fetches changelog.json and hands
# it to Python as a window global before this module runs; the pytest
# harness's fake `js` has no such attribute, so this falls through to
# reading the file straight off disk. A flat, hand-written list of
# highlights pulled from this game's own CLAUDE.md milestone table and
# build notes — not a full duplicate of the dev logs, just a quick
# "what's new" view.
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        _js = None

    raw = getattr(_js, "CHANGELOG_JSON", None) if _js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 -- only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, CHANGELOG_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Same defensive posture as ACHIEVEMENTS above: the changelog is additive,
# not core to gameplay, so any loading failure degrades to "no changelog"
# instead of crashing the whole module import.
try:
    CHANGELOG = json.loads(_read_changelog_json())["changelog"]
except (ValueError, OSError, NameError, KeyError):
    CHANGELOG = []

changelog_open = False


def on_toggle_changelog(event=None):
    global changelog_open
    changelog_open = not changelog_open
    update_changelog_display()


def update_changelog_display():
    toggle = document.getElementById("changelog-toggle-button")
    panel = document.getElementById("changelog-panel")
    toggle.innerText = "Hide What's New" if changelog_open else "📋 What's New"
    panel.hidden = not changelog_open
    if not changelog_open:
        return

    panel.innerHTML = ""
    # changelog.json is authored newest-first already, so no re-sort needed
    # here — same "trust the JSON's own order" posture ACHIEVEMENTS takes.
    for entry in CHANGELOG:
        row = document.createElement("div")
        row.className = "changelog-entry"

        date = document.createElement("p")
        date.className = "changelog-entry-date"
        date.innerText = entry["date"]
        row.appendChild(date)

        text = document.createElement("p")
        text.className = "changelog-entry-text"
        text.innerText = entry["entry"]
        row.appendChild(text)

        panel.appendChild(row)


# TODO-C17 -- weather-event log panel, same hidden-until-opened .section
# idiom as the changelog panel just above.
weather_log_open = False


def on_toggle_weather_log(event=None):
    global weather_log_open
    weather_log_open = not weather_log_open
    update_weather_log_display()


def update_weather_log_display():
    toggle = document.getElementById("weather-log-toggle-button")
    panel = document.getElementById("weather-log-panel")
    toggle.innerText = "Hide Weather Log" if weather_log_open else "🌦️ Weather Log"
    panel.hidden = not weather_log_open
    if not weather_log_open:
        return

    panel.innerHTML = ""
    if not state.weather_log:
        empty = document.createElement("p")
        empty.className = "weather-log-empty"
        empty.innerText = (
            "No weather-variability effects recorded yet -- turn on Weather Variability "
            "above and advance a round with renewables built to see entries here."
        )
        panel.appendChild(empty)
        return

    # Newest first, matching the achievements/changelog panels' convention.
    for message in reversed(state.weather_log):
        row = document.createElement("p")
        row.className = "weather-log-entry"
        row.innerText = message
        panel.appendChild(row)


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


def demand_growth_arrow():
    """C20 (extended by TODO-C7): demand's per-round growth against the
    standard pace -- up when net growth is faster than standard, flat
    when unchanged, and (new) down once demand-response investment has
    pulled net growth below standard, regardless of the Steeper Demand
    Growth toggle."""
    growth = state.demand_growth_this_round()
    if growth > DEMAND_GROWTH_PER_ROUND:
        return "\u25B2"
    if growth < DEMAND_GROWTH_PER_ROUND:
        return "\u25BC"
    return "\u25AC"


def demand_growth_title():
    growth = state.demand_growth_this_round()
    if state.demand_response_level > 0:
        baseline = DEMAND_GROWTH_PER_ROUND * (
            STEEP_DEMAND_GROWTH_MULTIPLIER if state.steeper_demand_growth_enabled else 1
        )
        return (
            f"Demand is rising +{growth:.1f} per round -- demand-response investment "
            f"(level {state.demand_response_level}) has trimmed it down from the "
            f"otherwise-{baseline:.0f}-per-round pace."
        )
    if state.steeper_demand_growth_enabled:
        return f"Demand is rising +{growth:.0f} per round -- faster than the standard +{DEMAND_GROWTH_PER_ROUND} (Steeper Demand Growth is on)."
    return f"Demand is rising at the standard +{DEMAND_GROWTH_PER_ROUND} per round."


def wear_tooltip(plant_type):
    """C4: what the wear percentage means numerically."""
    age = state.plant_age[plant_type]
    return (
        f"Average fleet age {age:.1f} rounds. Wear % = age / {WEAR_PERCENT_REFERENCE_AGE} rounds (100% is the "
        f"top wear tier). Breakdown risk starts past {AGE_GRACE_PERIOD} rounds: +{AGE_BREAKDOWN_RATE * 100:.0f}% "
        f"per extra round, capped at {MAX_AGE_BREAKDOWN_PROBABILITY * 100:.0f}%. Maintain takes "
        f"{MAINTENANCE_AGE_REDUCTION} rounds off the average age."
    )


def render():
    render_info_page()
    update_achievements_display()
    update_changelog_display()
    update_weather_log_display()
    update_summary_panel()
    document.getElementById("round-display").innerText = f"Round {state.round_number}"
    demand_el = document.getElementById("demand-display")
    demand_el.innerText = f"Demand: {state.demand} {demand_growth_arrow()}"
    demand_el.title = demand_growth_title()
    document.getElementById("streak-display").innerText = (
        f"Clean streak: {state.current_clean_streak} round(s) without a disruption "
        f"(best {state.best_clean_streak})"
    )
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

    # C16: opt-in difficulty toggle -- purely reflects the current setting,
    # never touches disruption math (see STEEP_DEMAND_GROWTH_MULTIPLIER's
    # comment above).
    steep_button = document.getElementById("steeper-demand-toggle-button")
    steep_button.innerText = (
        f"🔥 Steeper Demand Growth (x{STEEP_DEMAND_GROWTH_MULTIPLIER:g}): ON"
        if state.steeper_demand_growth_enabled
        else f"Steeper Demand Growth (x{STEEP_DEMAND_GROWTH_MULTIPLIER:g}): OFF"
    )
    if state.steeper_demand_growth_enabled:
        steep_button.classList.add("active")
    else:
        steep_button.classList.remove("active")

    weather_button = document.getElementById("weather-variability-toggle-button")
    weather_button.innerText = (
        "🌩️ Weather Variability: ON" if state.weather_variability_enabled else "Weather Variability: OFF"
    )
    if state.weather_variability_enabled:
        weather_button.classList.add("active")
    else:
        weather_button.classList.remove("active")

    svg = trend_graph_svg(
        state.emissions_history,
        state.avg_renewable_cost_history,
        state.global_reference_emissions_history,
        state.clean_fraction_log,
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

    # C13: a funds breakdown across the run so far, for transparency --
    # pure additive read of the lifetime_* totals above, no change to any
    # actual cost/refund math itself.
    document.getElementById("funds-breakdown-revenue").innerText = f"{state.lifetime_revenue:.0f}"
    document.getElementById("funds-breakdown-build").innerText = f"{state.lifetime_build_spend:.0f}"
    document.getElementById("funds-breakdown-maintenance").innerText = f"{state.lifetime_maintenance_spend:.0f}"
    document.getElementById("funds-breakdown-disruption").innerText = f"{state.lifetime_disruption_spend:.0f}"

    funds_values = {
        "revenue": state.lifetime_revenue,
        "build": state.lifetime_build_spend,
        "maintenance": state.lifetime_maintenance_spend,
        "disruption": state.lifetime_disruption_spend,
    }
    funds_max = max(funds_values.values()) or 1.0
    for key, value in funds_values.items():
        document.getElementById(f"funds-bar-{key}").style.width = f"{value / funds_max * 100:.0f}%"

    scenario_button = document.getElementById("scenario-toggle-button")
    scenario_button.innerText = f"Scenario: {SCENARIOS[state.scenario]['label']}"
    scenario_locked = state.round_number != 1 or any(state.cumulative_built.values())
    scenario_button.disabled = scenario_locked
    scenario_button.title = (
        "Starting scenario -- locked once you build anything or advance a round."
        if scenario_locked
        else "Click to cycle the starting scenario (only available before your first build or round)."
    )

    document.getElementById("renewable-milestone-callout").hidden = not renewable_milestone_visible
    document.getElementById("retire-callout").hidden = not retire_callout_visible
    document.getElementById("maintain-callout").hidden = not maintain_callout_visible

    # TODO-C7: demand-response lever -- a fourth build/retire/maintain-
    # style action, but acting on demand growth instead of the fleet.
    dr_cost = state.demand_response_cost()
    dr_button = document.getElementById("demand-response-button")
    dr_button.innerText = f"Invest in Demand Response ({dr_cost:.0f})"
    dr_button.disabled = state.funds < dr_cost
    dr_button.title = (
        f"Permanently trims demand growth by {DEMAND_RESPONSE_REDUCTION_PER_LEVEL:g}/round "
        f"(floor {DEMAND_RESPONSE_MIN_GROWTH:g}/round). Each purchase costs more than the last."
    )
    document.getElementById("demand-response-level-display").innerText = (
        f"Demand response level: {state.demand_response_level}"
        if state.demand_response_level > 0
        else "Demand response: not yet invested"
    )

    # TODO-C19: policy lever -- offered periodically, opt-in.
    policy_banner = document.getElementById("policy-lever-banner")
    policy_banner.hidden = not state.policy_lever_available
    active_policy_el = document.getElementById("active-policy-display")
    if state.active_policy is None:
        active_policy_el.innerText = ""
        active_policy_el.hidden = True
    else:
        active_policy_el.hidden = False
        label = (
            "Carbon Pricing" if state.active_policy["type"] == "carbon_pricing" else "Renewable Subsidy"
        )
        effect = (
            f"fossil build costs +{(CARBON_PRICING_FOSSIL_COST_MULTIPLIER - 1) * 100:.0f}%"
            if state.active_policy["type"] == "carbon_pricing"
            else f"renewable build costs -{(1 - RENEWABLE_SUBSIDY_COST_MULTIPLIER) * 100:.0f}%"
        )
        active_policy_el.innerText = (
            f"Active policy: {label} -- {effect} ({state.active_policy['rounds_remaining']} round(s) left)."
        )

    _render_arbitrage_and_emergency()

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
        wear_pct_el.innerText = (
            f"{WEAR_TIER_GLYPH[wear_css_class]} {state.wear_percent(plant_type)}% worn" if count > 0 else ""
        )
        wear_pct_el.title = wear_tooltip(plant_type) if count > 0 else ""

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

        # TODO-C23: keep the select's own displayed value in sync with
        # state (e.g. after a load_state() or a grid-size reset), same
        # reasoning as the difficulty/grid-size <select>s elsewhere in
        # this file -- disabled whenever there's no plant of this type to
        # schedule anything for, same gating as Maintain itself.
        schedule_select = document.getElementById(f"{plant_type}-maintenance-schedule-select")
        schedule_select.value = str(state.maintenance_schedule[plant_type])
        schedule_select.disabled = count <= 0

    # C7: plant-mix bar chart -- composition of *generation* capacity by
    # type. Battery has no row here (see GENERATION_TYPES' comment) --
    # it's storage, not part of "what's generating," so it has no
    # meaningful share of a generation-mix chart.
    for plant_type in GENERATION_TYPES:
        mix_pct = state.capacity_share(plant_type) * 100
        document.getElementById(f"{plant_type}-mix-bar").style.width = f"{mix_pct:.0f}%"
        document.getElementById(f"{plant_type}-mix-pct").innerText = f"{mix_pct:.0f}%"


ARBITRAGE_MODE_LABEL = {"idle": "Idle", "charge": "Charge", "discharge": "Discharge"}


def arbitrage_status_message():
    """C9: one plain-text line -- stored level plus what last round did."""
    cap = state.storage_cap()
    text = f"Stored {state.stored_energy:.0f}/{cap:.0f}."
    last = state.last_arbitrage
    if last is not None:
        if last["mode"] == "charge":
            text += f" Last round: banked {last['units']:.0f} surplus."
        else:
            text += f" Last round: sold {last['units']:.0f} for +{last['revenue']:.0f} funds."
    return text


def emergency_message():
    """C27: banner text for the emergency scenario, or '' outside it."""
    em = state.emergency
    if em is None:
        return ""
    if em["status"] == "stabilized":
        return "Emergency over: the grid is stabilized. The run carries on as normal."
    if em["status"] == "missed":
        return (
            "Emergency window closed without stabilizing. There is no game over -- "
            "keep building; demand still has to be met."
        )
    return (
        f"EMERGENCY: a major disruption left capacity {state.total_capacity()} against demand {state.demand}. "
        f"Get capacity to at least demand for {EMERGENCY_HOLD_ROUNDS} rounds in a row "
        f"(held {em['hold']}/{EMERGENCY_HOLD_ROUNDS}, {em['rounds_left']} round(s) left)."
    )


def _render_arbitrage_and_emergency():
    has_battery = state.plant_counts["battery"] > 0
    mode_button = document.getElementById("arbitrage-mode-button")
    mode_button.innerText = f"Storage: {ARBITRAGE_MODE_LABEL[state.arbitrage_mode]}"
    mode_button.disabled = not has_battery
    mode_button.title = (
        "Click to cycle Idle / Charge / Discharge for the next round."
        if has_battery
        else "Build a battery to use storage arbitrage."
    )
    status_el = document.getElementById("arbitrage-status-display")
    status_el.hidden = not has_battery
    status_el.innerText = arbitrage_status_message() if has_battery else ""
    emergency_el = document.getElementById("emergency-status-display")
    text = emergency_message()
    emergency_el.hidden = not text
    emergency_el.innerText = text


def on_cycle_arbitrage_mode(event=None):
    """C9: cycle Idle -> Charge -> Discharge for the next round."""
    modes = ARBITRAGE_MODES
    state.set_arbitrage_mode(modes[(modes.index(state.arbitrage_mode) + 1) % len(modes)])
    render()


def _load_arbitrage_and_emergency(data):
    """Validated restore of C9/C27 fields (defaults if malformed)."""
    stored = data.get("stored_energy", state.stored_energy)
    ok = isinstance(stored, (int, float)) and not isinstance(stored, bool) and stored == stored
    state.stored_energy = max(0.0, min(float(stored), state.storage_cap())) if ok else 0.0
    mode = data.get("arbitrage_mode", state.arbitrage_mode)
    state.arbitrage_mode = mode if mode in ARBITRAGE_MODES else "idle"
    total = data.get("arbitrage_revenue_total", state.arbitrage_revenue_total)
    ok = isinstance(total, (int, float)) and not isinstance(total, bool) and total == total
    state.arbitrage_revenue_total = max(0.0, float(total)) if ok else 0.0
    state.last_arbitrage = None
    em = data.get("emergency", state.emergency)
    if (
        state.scenario == "emergency"
        and isinstance(em, dict)
        and em.get("status") in ("active", "stabilized", "missed")
    ):
        state.emergency = {
            "status": em["status"],
            "rounds_left": _as_int(em.get("rounds_left"), 0, 0, EMERGENCY_ROUNDS),
            "hold": _as_int(em.get("hold"), 0, 0, EMERGENCY_HOLD_ROUNDS),
        }
    else:
        state.emergency = None


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


def _pulse_emissions_meter():
    """C24: a brief pulse on the emissions meter the instant renewables
    cross 50% of capacity. Pure CSS class, removed by timer."""
    meter = document.getElementById("emissions-bar")
    meter.classList.add("meter-pulse")

    def _clear(*args):
        meter.classList.remove("meter-pulse")
        proxy.destroy()

    proxy = create_proxy(_clear)
    setTimeout(proxy, 1600)


def on_cycle_scenario(event=None):
    """C13: cycle to the next starting scenario (only before any build)."""
    next_id = SCENARIO_ORDER[(SCENARIO_ORDER.index(state.scenario) + 1) % len(SCENARIO_ORDER)]
    state.apply_scenario(next_id)
    render()


def _check_renewable_milestone():
    """Called after every action that could change capacity composition
    (build/retire/advance round) -- not from render() itself, so a loaded
    save doesn't flash the callout purely from being rendered once."""
    global renewable_milestone_visible
    if not state.renewable_50_reached and renewable_capacity_share() >= 0.5:
        state.renewable_50_reached = True
        renewable_milestone_visible = True
        _pulse_emissions_meter()


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


def _confirm_dialog_ask(action_id, message, confirm_label, on_confirm):
    """Routes a guarded action through the shared shared/confirm-dialog.js
    widget when it's available, or runs the action immediately when it
    isn't -- same lazy `from js import window`/getattr-default shape as
    every other optional-JS-hook call in this hub (e.g. continuum's
    `_notify_visual_layer()`, champ-de-mots' `_dispatch_report()`). The
    pytest fake-DOM harness's `js` module only ever fakes `document`/
    `setTimeout` (see tests/conftest.py), never `window`, so `from js
    import window` raises ImportError there and this falls straight
    through to calling on_confirm() synchronously -- which is exactly
    what every existing test that drives a retire click already expects."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        on_confirm()
        return
    confirm_dialog = getattr(window, "ConfirmDialog", None)
    if confirm_dialog is None:
        on_confirm()
        return
    confirm_dialog.ask(
        id=action_id,
        message=message,
        confirmLabel=confirm_label,
        onConfirm=create_proxy(on_confirm),
    )


def _make_retire_handler(plant_type):
    def do_retire():
        global retire_callout_visible
        succeeded = state.retire_plant(plant_type)
        if succeeded and not state.seen_retire_callout:
            state.seen_retire_callout = True
            retire_callout_visible = True
        _check_renewable_milestone()
        render()
        _check_new_achievements_for_toast()

    def handler(event=None):
        # C14 (planning/TODO.md's shared confirmation-dialog goal) --
        # retiring a plant type's very last unit is a real, not-quite-free
        # decision (refund_plant() only rebates REFUND_FRACTION of the
        # current cost -- rebuilding costs full price again), so that one
        # case alone is gated behind the shared confirm dialog. Retiring
        # down from 2+ units stays exactly as instant as it always was.
        if state.plant_counts[plant_type] <= 0:
            do_retire()  # already 0 -- retire_plant() is a no-op; let it report False as usual
            return
        if state.plant_counts[plant_type] == 1:
            _confirm_dialog_ask(
                action_id=f"grid-retire-last-{plant_type}",
                message=(
                    f"Retire your last {PLANT_LABEL[plant_type]} plant "
                    f"(wear {state.wear_percent(plant_type)}%, average age {state.plant_age[plant_type]:.1f} rounds)? "
                    "You'll lose that capacity, and rebuilding later costs "
                    "full price again."
                ),
                confirm_label="Retire it",
                on_confirm=do_retire,
            )
        else:
            do_retire()
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


def _make_maintenance_schedule_handler(plant_type):
    """TODO-C23: the per-plant-type auto-maintain cadence <select>'s own
    change handler -- reads the just-changed value straight off the
    event's target, same convention as on_grid_size_change() elsewhere in
    this file."""
    def handler(event):
        state.set_maintenance_schedule(plant_type, int(event.target.value))
        render()
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
        _display_disruption_toast(
            f"{event_message(state.last_event)} {disruption_reason(state.last_event)}", severity_class
        )
    elif state.last_aging_event is not None:
        plant_name = PLANT_LABEL[state.last_aging_event["plant"]]
        cost = state.last_aging_event["repair_cost"]
        _display_disruption_toast(
            f"Aging breakdown! A {plant_name} plant failed from wear (repair cost {cost:.0f}).",
            "disruption-toast--danger",
        )


def on_toggle_steeper_demand(event=None):
    state.steeper_demand_growth_enabled = not state.steeper_demand_growth_enabled
    render()


def on_toggle_weather_variability(event=None):
    state.weather_variability_enabled = not state.weather_variability_enabled
    render()


def on_invest_demand_response(event=None):
    """TODO-C7: the demand-response lever's own button click."""
    state.invest_demand_response()
    render()


def on_enact_carbon_pricing(event=None):
    """TODO-C19: accept the currently-offered policy lever as carbon pricing."""
    state.enact_policy("carbon_pricing")
    render()


def on_enact_renewable_subsidy(event=None):
    """TODO-C19: accept the currently-offered policy lever as a renewable subsidy."""
    state.enact_policy("renewable_subsidy")
    render()


def on_decline_policy(event=None):
    """TODO-C19: turn down the currently-offered policy lever entirely."""
    state.decline_policy()
    render()


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
        "bau_emissions": state.bau_emissions,
        "last_aging_event": copy.deepcopy(state.last_aging_event),
        "info_page_open": info_page_open,
        "maintenance_actions_count": state.maintenance_actions_count,
        "current_clean_streak": state.current_clean_streak,
        "best_clean_streak": state.best_clean_streak,
        "seen_retire_callout": state.seen_retire_callout,
        "seen_maintain_callout": state.seen_maintain_callout,
        "renewable_50_reached": state.renewable_50_reached,
        "lifetime_revenue": state.lifetime_revenue,
        "lifetime_build_spend": state.lifetime_build_spend,
        "lifetime_maintenance_spend": state.lifetime_maintenance_spend,
        "lifetime_disruption_spend": state.lifetime_disruption_spend,
        "steeper_demand_growth_enabled": state.steeper_demand_growth_enabled,
        "weather_variability_enabled": state.weather_variability_enabled,
        "scenario": state.scenario,
        "demand_response_level": state.demand_response_level,
        "weather_log": list(state.weather_log),
        "policy_lever_available": state.policy_lever_available,
        "active_policy": copy.deepcopy(state.active_policy),
        "last_policy_lever_round_offered": state.last_policy_lever_round_offered,
        "maintenance_schedule": dict(state.maintenance_schedule),
        "stored_energy": state.stored_energy,
        "arbitrage_mode": state.arbitrage_mode,
        "arbitrage_revenue_total": state.arbitrage_revenue_total,
        "emergency": copy.deepcopy(state.emergency),
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


def _as_int(value, default, minimum=0, maximum=None):
    """Validation helper for hand-edited/corrupt saves: bool and non-numeric
    values fall back to the default, numbers are clamped into range."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return default
    value = int(value)
    if value < minimum:
        return minimum
    if maximum is not None and value > maximum:
        return maximum
    return value


def _load_round3_fields(data):
    """Validated restore of the round-3 fields (C7/C17/C19/C23) that
    get_state() previously never saved, so they silently reset on every
    load. Anything malformed falls back to that field's default."""
    state.demand_response_level = _as_int(data.get("demand_response_level"), state.demand_response_level, 0, 200)
    log = data.get("weather_log", state.weather_log)
    if isinstance(log, list):
        state.weather_log = [str(x) for x in log if isinstance(x, str)][-WEATHER_LOG_MAX_ENTRIES:]
    available = data.get("policy_lever_available", state.policy_lever_available)
    state.policy_lever_available = available if isinstance(available, bool) else False
    policy = data.get("active_policy", state.active_policy)
    if (
        isinstance(policy, dict)
        and policy.get("type") in ("carbon_pricing", "renewable_subsidy")
        and _as_int(policy.get("rounds_remaining"), 0, 0, POLICY_LEVER_DURATION) > 0
    ):
        state.active_policy = {
            "type": policy["type"],
            "rounds_remaining": _as_int(policy["rounds_remaining"], 1, 1, POLICY_LEVER_DURATION),
        }
    else:
        state.active_policy = None
    state.last_policy_lever_round_offered = _as_int(
        data.get("last_policy_lever_round_offered"), state.last_policy_lever_round_offered, 0
    )
    schedule = data.get("maintenance_schedule")
    if isinstance(schedule, dict):
        for plant_type in PLANT_TYPES:
            interval = schedule.get(plant_type)
            if isinstance(interval, int) and not isinstance(interval, bool) and interval in MAINTENANCE_SCHEDULE_OPTIONS:
                state.maintenance_schedule[plant_type] = interval
    _load_arbitrage_and_emergency(data)


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
    state.bau_emissions = data.get("bau_emissions", state.bau_emissions)
    state.last_aging_event = copy.deepcopy(data.get("last_aging_event", state.last_aging_event))
    info_page_open = data.get("info_page_open", info_page_open)
    state.maintenance_actions_count = data.get("maintenance_actions_count", state.maintenance_actions_count)
    state.current_clean_streak = data.get("current_clean_streak", state.current_clean_streak)
    state.best_clean_streak = data.get("best_clean_streak", state.best_clean_streak)
    state.seen_retire_callout = data.get("seen_retire_callout", state.seen_retire_callout)
    state.seen_maintain_callout = data.get("seen_maintain_callout", state.seen_maintain_callout)
    state.renewable_50_reached = data.get("renewable_50_reached", state.renewable_50_reached)
    state.lifetime_revenue = data.get("lifetime_revenue", state.lifetime_revenue)
    state.lifetime_build_spend = data.get("lifetime_build_spend", state.lifetime_build_spend)
    state.lifetime_maintenance_spend = data.get("lifetime_maintenance_spend", state.lifetime_maintenance_spend)
    state.lifetime_disruption_spend = data.get("lifetime_disruption_spend", state.lifetime_disruption_spend)
    state.steeper_demand_growth_enabled = data.get(
        "steeper_demand_growth_enabled", state.steeper_demand_growth_enabled
    )
    state.weather_variability_enabled = data.get(
        "weather_variability_enabled", state.weather_variability_enabled
    )
    saved_scenario = data.get("scenario", state.scenario)
    state.scenario = saved_scenario if saved_scenario in SCENARIOS else "standard"
    _load_round3_fields(data)
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
        document.getElementById(f"{plant_type}-maintenance-schedule-select").addEventListener(
            "change", create_proxy(_make_maintenance_schedule_handler(plant_type))
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
    document.getElementById("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    document.getElementById("summary-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_summary_panel)
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
    document.getElementById("steeper-demand-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_steeper_demand)
    )
    document.getElementById("weather-variability-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_weather_variability)
    )
    document.getElementById("scenario-toggle-button").addEventListener(
        "click", create_proxy(on_cycle_scenario)
    )
    document.getElementById("weather-log-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_weather_log)
    )
    document.getElementById("arbitrage-mode-button").addEventListener(
        "click", create_proxy(on_cycle_arbitrage_mode)
    )
    document.getElementById("demand-response-button").addEventListener(
        "click", create_proxy(on_invest_demand_response)
    )
    document.getElementById("policy-accept-carbon-pricing-button").addEventListener(
        "click", create_proxy(on_enact_carbon_pricing)
    )
    document.getElementById("policy-accept-renewable-subsidy-button").addEventListener(
        "click", create_proxy(on_enact_renewable_subsidy)
    )
    document.getElementById("policy-decline-button").addEventListener(
        "click", create_proxy(on_decline_policy)
    )
    render()
    _seed_achievement_toast_baseline()


setup()
