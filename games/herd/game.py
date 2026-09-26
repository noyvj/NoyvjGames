"""Herd — Industrial Agriculture & Methane Game.

Runs in-browser via Pyodide. The core farm loop (herd growth, income,
and round progression), the methane meter (coupled to herd size by
default), the decoupling investments that reduce that coupling, and the
soft market/regulatory consequence system are all implemented below --
all 7 milestones are complete (see CLAUDE.md's milestone table).
"""

import json
import math
import os

import comparison_chart
import info_page
from js import document, setTimeout
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
    "feed": {"cost": 15, "ratio_reduction": 0.04, "label": "Feed Additives", "icon": "\U0001F33E"},
    "caps": {"cost": 20, "ratio_reduction": 0.06, "label": "Herd Caps", "icon": "\U0001F404"},
    "capture": {"cost": 20, "ratio_reduction": 0.10, "label": "Capture Systems", "icon": "♻️"},
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

# Iteration-pass additions: a prominent dial gauge for coupling ratio
# (the mechanic the whole lesson depends on) and an ambient haze overlay
# tracking methane pressure, so the tension is felt, not just read as
# numbers.
GAUGE_LOW_COLOR = "#4c9c6e"  # fully decoupled
GAUGE_HIGH_COLOR = "#e0674c"  # fully coupled (baseline)
MAX_HAZE_OPACITY = 0.4

# Iteration Pass 2 — alternative protein pivot (the fallback path,
# chosen over market dynamics per CLAUDE.md's own conditional: market
# dynamics is an income-side mechanic that can't naturally feed into the
# coupling-ratio gauge, which the design notes require stay the
# centerpiece; the pivot is structurally another decoupling lever, so
# it blends directly into the same gauge feed/caps/capture already use).
# Unlike those three, this changes *what* is produced, not how
# efficiently the same thing is produced.
PLANT_PIVOT_COST = 25
PLANT_PIVOT_FRACTION_PER_UNIT = 0.05
MAX_PLANT_BASED_FRACTION = 0.6
# Plant-based output still carries a small footprint (land use etc.) —
# not literally zero, just far below animal output.
PLANT_BASED_EMISSIONS_MULTIPLIER = 0.05
# Real-world margin difference — a genuine cost, not a strict downgrade,
# since the methane cut this buys also reduces pressure-driven income
# loss elsewhere.
PLANT_BASED_INCOME_MULTIPLIER = 0.85

# F6 (planning/TODO.md) — a rising growth-cost curve instead of a flat
# one. Cost still starts at exactly HERD_GROWTH_COST for the very first
# unit (herd_size == 0), so nothing about the existing flat-cost tests
# for a fresh farm changes; every unit after that gets marginally more
# expensive, reflecting real land/logistics constraints on scaling a herd.
HERD_GROWTH_COST_SLOPE = 2.0

# F15 — the real documented methane-intensity reduction figure cited in
# this game's own Info Page (see INFO_PAGE below and CLAUDE.md), surfaced
# as a live in-game comparison rather than only inside the optional panel.
REAL_WORLD_REDUCTION_FRACTION = 0.42

# F5/F11/F17 — one-time nudge thresholds for the shared milestone-toast
# (distinct from the achievement-unlock toast). Each fires once per
# session the first time its condition is met, mirroring Thaw's
# tipping-flash pattern (a one-tick flag consumed by the next render).
HALF_DECOUPLED_CALLOUT_THRESHOLD = 0.5
PRESSURE_CALLOUT_THRESHOLD = 0.25
METHANE_PENALTY_NUDGE_THRESHOLD = 30.0

# F11 — sustainable certification: holding the coupling ratio at or
# below this level for this many consecutive rounds earns a permanent
# income price premium (the counterfactual baseline never gets it).
CERTIFICATION_RATIO_THRESHOLD = 0.5
CERTIFICATION_ROUNDS_REQUIRED = 5
CERTIFICATION_PRICE_PREMIUM = 0.10

# Achievements — clean_operator's round/pressure bar.
CLEAN_OPERATOR_MIN_ROUND = 15
CLEAN_OPERATOR_MAX_PRESSURE = 0.1

# F29 -- real-world grounding (see planning/FOR-YOU.md): farms do sell captured
# biogas/RNG (and its RIN/LCFS credits). The first CAPTURE_SELF_USE_UNITS of
# capture cover on-farm use; each capture unit beyond that yields saleable gas.
CAPTURE_SELF_USE_UNITS = 2
BIOGAS_SALE_PER_UNIT = 0.05  # funds per herd unit per surplus capture unit

# F23 -- second herd type, unlocked by sustainable certification (this
# game's prestige). Poultry: cheap, low-emission per unit, own levers, own
# housing upkeep. Its emissions are shown as "methane-equivalent" (real
# poultry emissions are mostly manure N2O/ammonia, not enteric methane).
POULTRY_GROW_COST = 12
POULTRY_GROW_SLOPE = 1.0
POULTRY_INCOME_PER_UNIT = 2.5
POULTRY_UPKEEP_PER_UNIT = 0.4
POULTRY_BASE_RATIO = 0.3
MIN_POULTRY_RATIO = 0.05
POULTRY_MEASURES = {
    "litter": {"cost": 12, "ratio_reduction": 0.04, "label": "Litter Management", "icon": "\U0001F33E"},
    "biofilter": {"cost": 15, "ratio_reduction": 0.05, "label": "Ventilation Biofilters", "icon": "\U0001F4A8"},
}

# F1 -- satellite farm ("regional herd network"): a second, smaller, older
# farm the player can open once the main farm is established. It has its own
# coupling ratio (older barns, so it starts dirtier than the main farm), its
# own retrofit lever and a hard size limit. The network effect: the main
# farm's decoupling beyond SATELLITE_OFFSET_FLOOR spills over as shared
# know-how and equipment, cutting the satellite's emissions by
# SATELLITE_OFFSET_RATE per point of that surplus (capped at
# SATELLITE_MAX_OFFSET) -- so investing at home also cleans up the network.
SATELLITE_MIN_MAIN_HERD = 6
SATELLITE_OPEN_COST = 40
SATELLITE_MAX_SIZE = 10
SATELLITE_GROW_COST = 15
SATELLITE_GROW_SLOPE = 1.5
SATELLITE_INCOME_PER_UNIT = 4.0
SATELLITE_BASE_RATIO = 1.2
MIN_SATELLITE_RATIO = 0.15
SATELLITE_RETROFIT_COST = 14
SATELLITE_RETROFIT_REDUCTION = 0.08
SATELLITE_MAX_RETROFITS = 8
SATELLITE_OFFSET_FLOOR = 0.4
SATELLITE_OFFSET_RATE = 1.0
SATELLITE_MAX_OFFSET = 0.5

# F5 -- generational genetics: a slow-burn fourth lever. Each investment
# takes GENETICS_MATURE_ROUNDS rounds to breed through, then permanently
# lowers the ratio.
GENETICS_COST = 30
GENETICS_RATIO_REDUCTION = 0.05
GENETICS_MATURE_ROUNDS = 3

# F13 -- supply chain: downstream processing/distribution, an income lever
# independent of herd growth.
SUPPLY_CHAIN_COST = 30
SUPPLY_CHAIN_BONUS_PER_UNIT = 0.06
SUPPLY_CHAIN_MAX_UNITS = 5

# F15 -- herd welfare: a light second axis. Better feed, caps (less
# crowding) and breeding raise it; above the neutral point it lifts income.
WELFARE_START = 50.0
WELFARE_FEED = 5.0
WELFARE_CAPS = 3.0
WELFARE_GENETICS = 4.0
WELFARE_MAX = 100.0
WELFARE_INCOME_BONUS_MAX = 0.10

# F9/F3 -- opt-in "market & weather variation": deterministic per-round
# income swings (season) plus periodic plant-based demand surges.
SEASONS = [
    ("Drought", -0.10),
    ("Dry spell", -0.05),
    ("Normal season", 0.0),
    ("Good pasture", 0.05),
    ("Bumper season", 0.10),
]
DEMAND_SURGE_PLANT_INCOME_MULTIPLIER = 1.05

# F19 -- opt-in regional methane cap: growth that would push per-round
# methane past the cap is blocked, forcing decoupling.
REGIONAL_CAP = 20.0

# F27 -- policy advisor: every POLICY_EVENT_INTERVAL rounds, choose between
# a decoupling subsidy and a flat cash bonus.
POLICY_EVENT_INTERVAL = 8
POLICY_SUBSIDY_DISCOUNT = 0.30
POLICY_SUBSIDY_ROUNDS = 5
POLICY_CASH_BONUS = 40


def season_for_round(round_number):
    """Deterministic pseudo-random season (same on every load/replay)."""
    return SEASONS[(round_number * 7 + 3) % len(SEASONS)]


def demand_surge_active(round_number):
    return round_number % 6 in (4, 5)


class FarmState:
    def __init__(self):
        self.round_number = 1
        self.funds = STARTING_FUNDS
        self.herd_size = 0
        self.methane = 0.0
        self.decoupling_investment = {m: 0 for m in DECOUPLING_MEASURES}
        self.plant_pivot_investment = 0

        # F1/F3/F13 — a parallel "pure-growth" counterfactual: the exact
        # same herd-growth path (same herd_size every round), but zero
        # decoupling/plant-pivot investment ever applied. Same technique
        # as Grid's bau_emissions / Thaw's counterfactual_temperature —
        # accumulated round-by-round in advance_round(), never
        # recalculated from scratch, so it survives save/load like any
        # other cumulative field. It does NOT mirror decoupling spend, so
        # it isolates whether decoupling investment paid for itself net
        # of its own cost, not just "what if you'd grown the same herd."
        self.counterfactual_funds = STARTING_FUNDS
        self.counterfactual_methane = 0.0

        # F5/F11/F17 — one-time nudge callouts. seen_* flags persist (so a
        # reload doesn't replay a nudge already shown); just_* flags are
        # one-tick, consumed by the very next render(), same shape as
        # Thaw's just_started_melting / Grid's seen_retire_callout pair.
        self.seen_half_decoupled_callout = False
        self.seen_pressure_callout = False
        self.seen_methane_penalty_nudge = False
        self.just_hit_callout = None  # None, or one of "half_decoupled"/"pressure"/"methane_penalty"

        # Achievements — clean_operator needs the worst pressure fraction
        # seen so far, since pressure_fraction() alone only reads the
        # *current* value and a player could spike pressure then invest
        # their way back down before checking achievements.
        self.max_pressure_fraction_seen = 0.0

        # F7 — methane-over-rounds trend history, same shape as Thaw's
        # per-region temperature_history / Grid's emissions_history.
        self.methane_history = [0.0]

        # F11 — sustainable certification progress. Both persist.
        self.certification_streak = 0
        self.certified = False

        # F16 — one-tick flag (not saved): the round's added methane just
        # dropped below the previous round's, i.e. the curve flattened.
        self.just_flattened = False

        # F23 poultry (unlocked by certification), F5 genetics, F13 supply
        # chain, F9/F3 variation toggle, F19 cap toggle, F27 policy event.
        self.poultry_size = 0
        self.poultry_investment = {m: 0 for m in POULTRY_MEASURES}
        self.genetics_active = 0
        self.genetics_pending = []  # rounds-remaining for each in-progress unit
        self.supply_chain_investment = 0
        self.variation_enabled = False
        self.regional_cap_enabled = False
        self.policy_offer_pending = False
        self.subsidy_rounds_left = 0

        # F1 satellite farm.
        self.satellite_open = False
        self.satellite_size = 0
        self.satellite_retrofits = 0

    # ---- F1 satellite farm ----
    def satellite_available(self):
        return self.satellite_open or self.herd_size >= SATELLITE_MIN_MAIN_HERD

    def satellite_own_ratio(self):
        """The satellite's ratio from its own retrofits alone."""
        reduction = self.satellite_retrofits * SATELLITE_RETROFIT_REDUCTION
        return max(MIN_SATELLITE_RATIO, SATELLITE_BASE_RATIO - reduction)

    def satellite_offset_fraction(self):
        """Share of the satellite's emissions the main farm's surplus
        decoupling cancels out: zero until the main farm is decoupled past
        SATELLITE_OFFSET_FLOOR, then growing with the surplus up to
        SATELLITE_MAX_OFFSET."""
        surplus = max(0.0, self.decoupled_fraction() - SATELLITE_OFFSET_FLOOR)
        return min(SATELLITE_MAX_OFFSET, surplus * SATELLITE_OFFSET_RATE)

    def satellite_coupling_ratio(self):
        return max(MIN_SATELLITE_RATIO, self.satellite_own_ratio() * (1 - self.satellite_offset_fraction()))

    def satellite_grow_cost(self):
        return SATELLITE_GROW_COST + self.satellite_size * SATELLITE_GROW_SLOPE

    def open_satellite(self):
        if self.satellite_open or self.herd_size < SATELLITE_MIN_MAIN_HERD or self.funds < SATELLITE_OPEN_COST:
            return False
        self.funds -= SATELLITE_OPEN_COST
        self.satellite_open = True
        return True

    def grow_satellite(self):
        cost = self.satellite_grow_cost()
        if (
            not self.satellite_open or self.satellite_size >= SATELLITE_MAX_SIZE
            or self.funds < cost or self.cap_blocks_growth(satellite=1)
        ):
            return False
        self.funds -= cost
        self.satellite_size += 1
        return True

    def retrofit_satellite(self):
        if (
            not self.satellite_open or self.satellite_retrofits >= SATELLITE_MAX_RETROFITS
            or self.funds < SATELLITE_RETROFIT_COST
        ):
            return False
        self.funds -= SATELLITE_RETROFIT_COST
        self.satellite_retrofits += 1
        return True

    def satellite_net_income(self):
        return self.satellite_size * SATELLITE_INCOME_PER_UNIT

    # ---- F27 policy advisor ----
    def decoupling_cost(self, measure):
        cost = DECOUPLING_MEASURES[measure]["cost"]
        if self.subsidy_rounds_left > 0:
            return cost * (1 - POLICY_SUBSIDY_DISCOUNT)
        return cost

    def choose_policy(self, choice):
        if not self.policy_offer_pending:
            return False
        if choice == "subsidy":
            self.subsidy_rounds_left = POLICY_SUBSIDY_ROUNDS
        elif choice == "cash":
            self.funds += POLICY_CASH_BONUS
        else:
            return False
        self.policy_offer_pending = False
        return True

    # ---- F23 poultry ----
    def poultry_unlocked(self):
        # F25: a heritage flock (legacy perk) carries the unlock to every
        # later generation without needing to re-earn certification.
        return self.certified or legacy_perks.get("heritage_flock", 0) > 0

    def poultry_coupling_ratio(self):
        reduction = sum(
            self.poultry_investment[m] * POULTRY_MEASURES[m]["ratio_reduction"] for m in POULTRY_MEASURES
        )
        return max(MIN_POULTRY_RATIO, POULTRY_BASE_RATIO - reduction)

    def poultry_grow_cost(self):
        return POULTRY_GROW_COST + self.poultry_size * POULTRY_GROW_SLOPE

    def grow_poultry(self):
        cost = self.poultry_grow_cost()
        if not self.poultry_unlocked() or self.funds < cost or self.cap_blocks_growth(poultry=1):
            return False
        self.funds -= cost
        self.poultry_size += 1
        return True

    def invest_poultry(self, measure):
        if not self.poultry_unlocked():
            return False
        cost = POULTRY_MEASURES[measure]["cost"]
        if self.funds < cost:
            return False
        self.funds -= cost
        self.poultry_investment[measure] += 1
        return True

    def poultry_net_income(self):
        return self.poultry_size * (POULTRY_INCOME_PER_UNIT - POULTRY_UPKEEP_PER_UNIT)

    # ---- F5 genetics ----
    def invest_genetics(self):
        if self.funds < GENETICS_COST:
            return False
        self.funds -= GENETICS_COST
        self.genetics_pending.append(GENETICS_MATURE_ROUNDS)
        return True

    # ---- F13 supply chain ----
    def invest_supply_chain(self):
        if self.funds < SUPPLY_CHAIN_COST or self.supply_chain_investment >= SUPPLY_CHAIN_MAX_UNITS:
            return False
        self.funds -= SUPPLY_CHAIN_COST
        self.supply_chain_investment += 1
        return True

    def supply_chain_multiplier(self):
        return 1 + self.supply_chain_investment * SUPPLY_CHAIN_BONUS_PER_UNIT

    # ---- F15 welfare ----
    def welfare(self):
        score = (
            WELFARE_START
            + self.decoupling_investment["feed"] * WELFARE_FEED
            + self.decoupling_investment["caps"] * WELFARE_CAPS
            + self.genetics_active * WELFARE_GENETICS
        )
        return min(WELFARE_MAX, score)

    def welfare_multiplier(self):
        return 1 + WELFARE_INCOME_BONUS_MAX * (self.welfare() - WELFARE_START) / (WELFARE_MAX - WELFARE_START)

    # ---- F9/F3 variation ----
    def season_modifier(self, round_number=None):
        if not self.variation_enabled:
            return 0.0
        return season_for_round(self.round_number if round_number is None else round_number)[1]

    def plant_income_multiplier(self, round_number=None):
        r = self.round_number if round_number is None else round_number
        if self.variation_enabled and demand_surge_active(r):
            return DEMAND_SURGE_PLANT_INCOME_MULTIPLIER
        return PLANT_BASED_INCOME_MULTIPLIER

    # ---- F29 biogas ----
    def biogas_sales(self):
        surplus = max(0, self.decoupling_investment["capture"] - CAPTURE_SELF_USE_UNITS)
        return self.herd_size * surplus * BIOGAS_SALE_PER_UNIT

    # ---- F19 regional cap ----
    def cap_blocks_growth(self, herd=0, poultry=0, satellite=0):
        if not self.regional_cap_enabled:
            return False
        projected = (
            (self.herd_size + herd) * self.coupling_ratio()
            + (self.poultry_size + poultry) * self.poultry_coupling_ratio()
            + (self.satellite_size + satellite) * self.satellite_coupling_ratio()
        )
        return projected > REGIONAL_CAP + 1e-9

    def certification_multiplier(self):
        return 1 + CERTIFICATION_PRICE_PREMIUM if self.certified else 1.0

    def _efficiency_coupling_ratio(self):
        """Methane produced per herd unit, per round, from the feed/caps/
        capture efficiency measures alone — floored so it never hits zero."""
        reduction = sum(
            self.decoupling_investment[m] * DECOUPLING_MEASURES[m]["ratio_reduction"]
            for m in DECOUPLING_MEASURES
        ) + self.genetics_active * GENETICS_RATIO_REDUCTION
        return max(MIN_COUPLING_RATIO, BASE_COUPLING_RATIO - reduction)

    def plant_based_fraction(self):
        return min(MAX_PLANT_BASED_FRACTION, self.plant_pivot_investment * PLANT_PIVOT_FRACTION_PER_UNIT)

    def coupling_ratio(self):
        """The efficiency-measure ratio, further blended down by however
        much of the herd's output has pivoted to (near-zero-methane)
        plant-based production. Same public method every other Pass 1
        mechanic already reads from, so the gauge shows one unified
        number regardless of which lever moved it."""
        base = self._efficiency_coupling_ratio()
        fraction = self.plant_based_fraction()
        blended_multiplier = (1 - fraction) + fraction * PLANT_BASED_EMISSIONS_MULTIPLIER
        return max(MIN_COUPLING_RATIO, base * blended_multiplier)

    def invest_plant_pivot(self):
        if self.funds < PLANT_PIVOT_COST:
            return False
        self.funds -= PLANT_PIVOT_COST
        self.plant_pivot_investment += 1
        return True

    def decoupled_fraction(self):
        """How far below baseline the current coupling ratio sits, 0..1.
        Shared by the decoupling-summary display, the real-world-42%
        comparison (F15), and the decoupling-threshold achievements/
        callout — one function, not four copies of the same subtraction."""
        return 1 - (self.coupling_ratio() / BASE_COUPLING_RATIO)

    def methane_this_round(self):
        return (
            self.herd_size * self.coupling_ratio()
            + self.poultry_size * self.poultry_coupling_ratio()
            + self.satellite_size * self.satellite_coupling_ratio()
        )

    def grow_herd_cost(self):
        """F6 — a rising growth-cost curve: the very first unit still
        costs exactly HERD_GROWTH_COST (herd_size == 0), and each unit
        after that costs marginally more, reflecting real land/logistics
        constraints on scaling a herd rather than a flat per-unit price
        forever."""
        return HERD_GROWTH_COST + self.herd_size * HERD_GROWTH_COST_SLOPE

    def grow_herd(self):
        cost = self.grow_herd_cost()
        if self.funds < cost or self.cap_blocks_growth(herd=1):
            return False
        self.funds -= cost
        self.herd_size += 1
        return True

    def invest_decoupling(self, measure):
        cost = self.decoupling_cost(measure)
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

    def counterfactual_pressure_fraction(self):
        return min(MAX_PRESSURE, self.counterfactual_methane / PRESSURE_SCALE)

    def counterfactual_score(self):
        """F1/F3/F13 — the pure-growth counterfactual's own score, using
        the exact same formula as score() so the two numbers are directly
        comparable."""
        return self.counterfactual_funds - self.counterfactual_methane * METHANE_PENALTY_WEIGHT

    def advance_round(self):
        fraction = self.plant_based_fraction()
        income_multiplier = (1 - fraction) + fraction * self.plant_income_multiplier()
        season = 1 + self.season_modifier()
        raw_income = (
            self.herd_size * HERD_INCOME_PER_UNIT * income_multiplier
            * self.certification_multiplier() * self.welfare_multiplier()
            + self.poultry_net_income() + self.satellite_net_income()
        ) * self.supply_chain_multiplier() * season
        pressure = self.pressure_fraction()
        self.funds += raw_income * (1 - pressure) + self.biogas_sales()
        self.methane += self.methane_this_round()
        self.max_pressure_fraction_seen = max(self.max_pressure_fraction_seen, pressure)

        # Counterfactual: same herd_size, but baseline (fully-coupled)
        # emissions and no plant-pivot income multiplier — never mirrors
        # decoupling/pivot spend, so the comparison isolates whether that
        # spend paid for itself.
        counterfactual_pressure = self.counterfactual_pressure_fraction()
        counterfactual_raw_income = (
            self.herd_size * HERD_INCOME_PER_UNIT + self.poultry_net_income() + self.satellite_net_income()
        ) * season
        self.counterfactual_funds += counterfactual_raw_income * (1 - counterfactual_pressure)
        self.counterfactual_methane += (
            self.herd_size * BASE_COUPLING_RATIO + self.poultry_size * POULTRY_BASE_RATIO
            + self.satellite_size * SATELLITE_BASE_RATIO
        )

        # F5 -- breeding matures; F27 -- subsidy runs down and a new offer
        # arrives every POLICY_EVENT_INTERVAL rounds.
        self.genetics_pending = [r - 1 for r in self.genetics_pending]
        matured = sum(1 for r in self.genetics_pending if r <= 0)
        self.genetics_active += matured
        self.genetics_pending = [r for r in self.genetics_pending if r > 0]
        if self.subsidy_rounds_left > 0:
            self.subsidy_rounds_left -= 1
        if (self.round_number + 1) % POLICY_EVENT_INTERVAL == 0:
            self.policy_offer_pending = True

        self.round_number += 1
        prev_increment = (
            self.methane_history[-1] - self.methane_history[-2] if len(self.methane_history) >= 2 else 0.0
        )
        self.methane_history.append(self.methane)
        # F16 — curve flattening: this round added less than the last.
        self.just_flattened = (
            prev_increment > 0 and (self.methane_history[-1] - self.methane_history[-2]) < prev_increment - 1e-9
        )

        # F11 — certification streak, counted on the ratio held this round.
        if self.coupling_ratio() <= CERTIFICATION_RATIO_THRESHOLD:
            self.certification_streak += 1
        else:
            self.certification_streak = 0
        if not self.certified and self.certification_streak >= CERTIFICATION_ROUNDS_REQUIRED:
            self.certified = True

        # F5/F11/F17 — one-time nudge callouts, checked in a fixed
        # priority order so at most one fires per round (the shared
        # milestone-toast can only show one message at a time anyway).
        if not self.seen_half_decoupled_callout and self.decoupled_fraction() >= HALF_DECOUPLED_CALLOUT_THRESHOLD:
            self.seen_half_decoupled_callout = True
            self.just_hit_callout = "half_decoupled"
        elif not self.seen_pressure_callout and pressure >= PRESSURE_CALLOUT_THRESHOLD:
            self.seen_pressure_callout = True
            self.just_hit_callout = "pressure"
        elif (
            not self.seen_methane_penalty_nudge
            and self.methane * METHANE_PENALTY_WEIGHT >= METHANE_PENALTY_NUDGE_THRESHOLD
        ):
            self.seen_methane_penalty_nudge = True
            self.just_hit_callout = "methane_penalty"

    def score(self):
        """Profitability weighted against sustained emissions — rewards
        decoupling specifically, not just growth or just restraint."""
        return self.funds - self.methane * METHANE_PENALTY_WEIGHT


farm = FarmState()


# REVIEW(reuse): byte-identical implementation in games/canopy/game.py.
# Low urgency at only 2 occurrences, but worth a shared color-utility module
# if a third game ever needs a hex-color lerp.
def _lerp_color(start_hex, end_hex, t):
    """Linear-interpolates between two #rrggbb colors at t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(start_hex[1:3], 16), int(start_hex[3:5], 16), int(start_hex[5:7], 16)
    r2, g2, b2 = int(end_hex[1:3], 16), int(end_hex[3:5], 16), int(end_hex[5:7], 16)
    r = round(r1 + (r2 - r1) * t)
    g = round(g1 + (g2 - g1) * t)
    b = round(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _gauge_point(fraction):
    """The (x, y) point on the coupling gauge's semicircle arc (same path
    coupling_gauge_svg() draws below) at the given 0..1 fraction along it
    -- shared by the live fill and the F8 record marker so both agree on
    the exact same geometry. Arc: center (60, 60), radius 50, running
    from 180 degrees (fraction 0, the CLEAN end) down to 0 degrees
    (fraction 1, the HIGH end), matching the path's own
    "M 10 60 A 50 50 0 0 1 110 60" sweep."""
    fraction = max(0.0, min(1.0, fraction))
    angle = math.radians(180 - fraction * 180)
    return 60 + 50 * math.cos(angle), 60 - 50 * math.sin(angle)


def coupling_gauge_svg(fraction, record_ratio=None):
    """Semi-circle dial gauge: 0 = fully decoupled (green), 1 = fully
    coupled at baseline (red). Iteration-pass addition — the single
    most prominent UI element, replacing a plain ratio number with an
    at-a-glance dial for the mechanic the whole lesson depends on.

    F8 (planning/TODO.md) — record_ratio, when given, draws a small
    diamond marker on the arc at the best (lowest) coupling ratio this
    browser has ever reached across every session/save on this device.
    Distinct from the live .gauge-fill arc, which only ever reflects the
    current farm's state -- a fresh session starts back at
    BASE_COUPLING_RATIO, so the two genuinely diverge once a player has
    played before. Same "shape, not just color" marker technique as
    Grid's own best-round diamond on its trend graph (see
    trend_graph_svg() there)."""
    fraction = max(0.0, min(1.0, fraction))
    color = _lerp_color(GAUGE_LOW_COLOR, GAUGE_HIGH_COLOR, fraction)
    dash = fraction * 100
    record_marker = ""
    if record_ratio is not None:
        record_fraction = max(0.0, min(1.0, record_ratio / BASE_COUPLING_RATIO))
        rx, ry = _gauge_point(record_fraction)
        record_marker = (
            f'<polygon points="{rx:.1f},{ry - 4:.1f} {rx + 4:.1f},{ry:.1f} '
            f'{rx:.1f},{ry + 4:.1f} {rx - 4:.1f},{ry:.1f}" class="gauge-record-marker">'
            f"<title>Best ever (this browser): {record_ratio:.2f} methane/herd/round</title>"
            "</polygon>"
        )
    return (
        '<svg viewBox="0 0 120 66" class="coupling-gauge-svg">'
        '<path d="M 10 60 A 50 50 0 0 1 110 60" class="gauge-track" pathLength="100" />'
        f'<path d="M 10 60 A 50 50 0 0 1 110 60" class="gauge-fill" pathLength="100" '
        f'stroke="{color}" stroke-dasharray="{dash:.1f} 100" />'
        f"{record_marker}"
        "</svg>"
    )


# F8 (planning/TODO.md) — a small per-browser "record decoupling ratio"
# marker on the coupling gauge, like Grid's best-round marker. F14's own
# comment above (in render()) already explains why a *session* best would
# be redundant: coupling_ratio() only ever falls within a single session
# (investment counts never go down), so it always equals the session's
# current value -- a fact the Round-2 pass explicitly used to skip this
# exact idea at the time. This is a different axis: the best ratio this
# browser has EVER reached, across every session/save on this device, via
# localStorage. A fresh session starts back at BASE_COUPLING_RATIO, so
# once a player has played before, "best ever" and "current" genuinely
# diverge -- that's what makes a persistent marker meaningful here. Same
# _read/_write_local_storage_item lazy-import pattern as Canopy's
# personal_best / Tide's best_coastline_saved / Thaw's G19.
RECORD_COUPLING_RATIO_STORAGE_KEY = "herd_record_coupling_ratio_v1"

# Z6 (planning/TODO.md "Z. Games"): duration of the shared
# .personal-best-display.just-improved pulse (shared/personal-best.css) --
# same value every other game using that shared badge uses.
RECORD_COUPLING_RATIO_BADGE_MS = 1800


def _read_local_storage_item(key):
    """Lazy `import js` so this module stays importable outside a real
    browser (the pytest fake `js` module has no localStorage at all,
    which this degrades to gracefully). Broad except on the actual read
    is deliberate: a real browser can refuse localStorage access entirely
    (private-browsing mode in some browsers), surfaced as a JS exception
    with no stable Python type to catch narrowly -- this feature is a
    nice-to-have, so it degrades to "no record yet" rather than crashing
    the module import."""
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        return None
    storage = getattr(js, "localStorage", None)
    if storage is None:
        return None
    try:
        return storage.getItem(key)
    except Exception:  # noqa: BLE001 — see docstring above
        return None


def _write_local_storage_item(key, value):
    try:
        import js  # noqa: PLC0415
    except ImportError:
        return
    storage = getattr(js, "localStorage", None)
    if storage is None:
        return
    try:
        storage.setItem(key, value)
    except Exception:  # noqa: BLE001 — see _read_local_storage_item's docstring
        pass


def load_record_coupling_ratio():
    """None means "no record yet" -- deliberately distinct from any real
    ratio value, since both BASE_COUPLING_RATIO (1.0) and
    MIN_COUPLING_RATIO (0.1) are real, reachable numbers and neither
    would be a safe "nothing recorded" sentinel the way 0.0 is for a
    "higher is better" stat like Tide's best_coastline_saved."""
    raw = _read_local_storage_item(RECORD_COUPLING_RATIO_STORAGE_KEY)
    if not raw:
        return None
    try:
        return float(json.loads(raw))
    except (ValueError, TypeError):
        return None


record_coupling_ratio = load_record_coupling_ratio()


def _maybe_update_record_coupling_ratio():
    """Called every render(); bumps + persists the record whenever the
    live farm's coupling_ratio() drops below it. Lower is better here --
    coupling_ratio() is methane per herd unit, and the gauge's own
    CLEAN/HIGH labels run green-at-0/red-at-baseline -- so a new record is
    a *drop* below whatever's stored, the opposite direction from every
    other game's "higher is better" personal-best stat.

    A fresh, never-decoupled farm sits exactly at BASE_COUPLING_RATIO --
    that's the starting point, not an achievement, so it must never get
    written as a "record" on its own. Only an actual improvement over
    baseline counts, which is also what keeps a brand-new browser (no
    localStorage entry, no decoupling investment yet) showing no marker
    at all, per this feature's own "record only appears once a record
    exists" requirement."""
    global record_coupling_ratio
    current = farm.coupling_ratio()
    if current >= BASE_COUPLING_RATIO - 1e-9:
        return
    if record_coupling_ratio is None or current < record_coupling_ratio - 1e-9:
        record_coupling_ratio = current
        _write_local_storage_item(RECORD_COUPLING_RATIO_STORAGE_KEY, json.dumps(record_coupling_ratio))
        _flash_record_coupling_ratio_badge()


def _flash_record_coupling_ratio_badge():
    """Z6: briefly adds the shared .just-improved class (see
    shared/personal-best.css) right when a new record is set. Same
    setTimeout+create_proxy shape as Canopy/Tide/Thaw's equivalent."""
    element = document.getElementById("coupling-gauge-record-display")
    if element is None:
        return
    element.classList.add("just-improved")

    def _unflash():
        el = document.getElementById("coupling-gauge-record-display")
        if el is not None:
            el.classList.remove("just-improved")

    setTimeout(create_proxy(_unflash), RECORD_COUPLING_RATIO_BADGE_MS)


def render_record_coupling_ratio():
    """The record only ever appears once one actually exists -- a brand
    new browser with no play history shows nothing here, matching the
    marker's own behavior on the gauge SVG (coupling_gauge_svg() draws no
    diamond at all when record_ratio is None)."""
    element = document.getElementById("coupling-gauge-record-display")
    if element is None:
        return
    if record_coupling_ratio is None:
        element.hidden = True
        return
    element.hidden = False
    element.innerText = f"Best ever (this browser): {record_coupling_ratio:.2f} methane/herd/round"


# Info Page — optional, player-triggered supplement (never forced
# mid-session). Framing is written fresh, not copied from any source;
# sources are the curated real-world backing for the game's mechanics.
INFO_PAGE = {
    "framing": (
        "Livestock digestion is a major, distinct source of methane — a "
        "gas that traps far more heat than CO2 in the short term, but "
        "also breaks down faster, which makes reducing it one of the "
        "fastest-acting climate levers available. Herd's coupling gauge "
        "and its plant-based pivot are built around that real reduction "
        "pathway."
    ),
    "mechanic_tie_in": (
        "Herd's plant-based pivot mechanic is grounded in a real "
        "documented case — a roughly 42% methane-intensity reduction "
        "achieved through better farm practices — showing decoupling "
        "herd size from methane is achievable, not hypothetical."
    ),
    "sources": [
        {
            "label": "FAO — Livestock and enteric methane",
            "url": "https://www.fao.org/in-action/enteric-methane/en",
            "note": "The definitive real-world figures behind Herd's core mechanic — agriculture's share of methane emissions and where it comes from.",
        },
        {
            "label": "Clean Air Task Force — Accelerating climate solutions in agriculture",
            "url": "https://www.catf.us/2024/10/accelerating-climate-solutions-agriculture-why-reducing-methane-livestock-urgent-opportunity/",
            "note": "Documents a real ~42% methane-intensity reduction from better farm practices — directly supports Herd's decoupling hope angle.",
        },
        {
            "label": "US EPA — Agriculture and Aquaculture: Food for Thought",
            "url": "https://www.epa.gov/snep/agriculture-and-aquaculture-food-thought",
            "note": "Explains why methane's short-lived-but-potent warming profile makes it a distinct lever from CO2.",
        },
    ],
}
info_page_open = False


# Rendering logic lives in shared/info_page.py now (see that module's
# docstring) -- this used to be a ~25-line implementation byte-identical
# across all 8 climate games. info_page_open stays local here since it's
# part of this game's save contract.
def render_info_page():
    info_page.render(INFO_PAGE, info_page_open)


def on_toggle_info_page(event=None):
    global info_page_open
    info_page_open = info_page.toggle(info_page_open)
    render_info_page()


# F7 — a compact methane-over-rounds trend line, same technique as
# Thaw's mini_temp_graph_svg: unlabeled beyond its axis-free shape, since
# the point is the shape of the curve (accelerating vs. flattening),
# not reading any one round's value precisely.
TREND_GRAPH_WIDTH = 240
TREND_GRAPH_HEIGHT = 48


def methane_trend_graph_svg(history):
    if len(history) < 2:
        return ""
    n = len(history)
    lo, hi = min(history), max(history)
    if hi - lo < 1e-9:
        ys = [TREND_GRAPH_HEIGHT / 2 for _ in history]
    else:
        ys = [TREND_GRAPH_HEIGHT - ((v - lo) / (hi - lo)) * TREND_GRAPH_HEIGHT for v in history]
    xs = [i * (TREND_GRAPH_WIDTH / (n - 1)) for i in range(n)]
    points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    return (
        f'<svg viewBox="0 0 {TREND_GRAPH_WIDTH} {TREND_GRAPH_HEIGHT}" class="methane-trend-graph-svg">'
        f'<polyline points="{points}" class="methane-trend-line" />'
        f"</svg>"
    )


# ===========================================================================
# F1/F3/F13 — pure-growth counterfactual comparison. FarmState.
# counterfactual_funds/counterfactual_methane/counterfactual_score() carry
# the actual math (see advance_round()); everything below is presentation.
# ===========================================================================
def counterfactual_comparison_message():
    """F1 — a live, one-line comparison versus a pure-growth farm with
    the exact same herd size and no decoupling investment ever made."""
    if farm.round_number <= 1:
        return "Advance a round to see how your farm compares to a pure-growth baseline."
    gap = farm.score() - farm.counterfactual_score()
    if gap >= 0:
        return f"Your farm is {gap:.0f} points ahead of a pure-growth farm with the same herd size."
    return f"Your farm is {abs(gap):.0f} points behind a pure-growth farm with the same herd size."


COMPARE_FALLBACK = "Comparison with other farms isn't available yet."


def _request_comparison():
    """F7 — asks the page's optional JS hook (window.herdCompare, see
    index.html) to fill #report-card-compare with a cross-player
    percentile, against the shared aggregate-stats endpoint (Z1,
    planning/TODO.md). Byte-for-byte the same optional-hook shape as
    Grid's own C15 (`_request_comparison()`/`window.gridCompare`) --
    the reference integration for this exact feature -- right down to
    the lazy `from js import window` import and the `getattr` default,
    so an absent hook (pytest, or a page that never defines it) is a
    silent no-op and the fallback text above simply stays put.

    `methane` (this farm's lifetime accumulated methane) is the field
    used, not a raw coupling ratio -- `coupling_ratio()` is a live
    per-round rate with no save-state field of its own, so it isn't
    one of the numeric paths `app/stats.py`'s STATS_FIELDS whitelists
    for this game, and the single-field `/percentile` endpoint can only
    rank a whitelisted field. `methane` is the closest real stand-in:
    it's the direct cumulative output of coupling_ratio() x herd_size
    every round (see `methane_this_round()`), so two farms at a similar
    round/herd_size mostly diverge on methane by how well they've
    decoupled -- same relationship Grid's own `emissions` field has to
    its cost-curve mechanic."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "herdCompare", None)
    if hook is not None:
        hook(float(farm.methane), farm.round_number)


def report_card_html():
    """F3 — an on-demand end-of-session report card. Reuses the exact
    same counterfactual numbers as the live comparison (F1) and the
    baseline-farm card (F13); this just restates them with more
    breakdown, the same relationship Grid's Run Summary panel has to its
    own always-visible readouts."""
    gap = farm.score() - farm.counterfactual_score()
    methane_avoided = max(0.0, farm.counterfactual_methane - farm.methane)
    lines = [
        f"Round {farm.round_number} — your score: {farm.score():.0f} vs. pure-growth baseline: {farm.counterfactual_score():.0f}",
        f"Same herd size ({farm.herd_size}), but your methane is {farm.methane:.0f} vs. the baseline's {farm.counterfactual_methane:.0f} — {methane_avoided:.0f} avoided.",
        f"Your funds: {farm.funds:.0f} vs. baseline funds: {farm.counterfactual_funds:.0f} (baseline never spent on decoupling, but also never avoided any pressure).",
        (
            f"Net: decoupling investment is worth {gap:.0f} points to your score right now."
            if gap >= 0
            else f"Net: your score is currently {abs(gap):.0f} points behind the baseline — invest more in decoupling to close the gap."
        ),
        beat_percentage_message(),
        investment_summary_message(),
        real_world_comparison_message(),
    ]
    body = "".join(f'<p class="status-line summary-line">{line}</p>' for line in lines)
    # F7: filled in by index.html's window.herdCompare() when the shared
    # stats endpoint (planning/TODO.md Z1) is reachable; otherwise this
    # fallback text simply stays.
    return body + f'<p id="report-card-compare" class="status-line summary-line">{COMPARE_FALLBACK}</p>'


def beat_percentage_message():
    """F6 — the exact percentage the score beats (or trails) the
    pure-growth baseline by."""
    baseline = farm.counterfactual_score()
    if abs(baseline) < 1e-9:
        return "Baseline score is zero, so a percentage comparison isn't meaningful yet."
    pct = (farm.score() - baseline) / abs(baseline) * 100
    if pct >= 0:
        return f"Your score beats the pure-growth baseline by {pct:.1f}%."
    return f"Your score trails the pure-growth baseline by {abs(pct):.1f}%."


def investment_summary_message():
    """F26 — a summary list where the three efficiency measures carry
    their own icons and the plant-based pivot is visibly a separate
    lever (a distinct marker plus the word 'separate')."""
    parts = [
        f"{spec['icon']} {spec['label']} x{farm.decoupling_investment[m]}"
        for m, spec in DECOUPLING_MEASURES.items()
    ]
    return (
        "Efficiency measures: " + ", ".join(parts)
        + f"  |  \U0001F331 Separate lever \u2014 Plant-Based Pivot x{farm.plant_pivot_investment}"
    )


def certification_message():
    if farm.certified:
        return (
            f"Certified sustainable: permanent +{CERTIFICATION_PRICE_PREMIUM * 100:.0f}% price premium "
            "on your output."
        )
    return (
        f"Sustainable certification: {farm.certification_streak}/{CERTIFICATION_ROUNDS_REQUIRED} "
        f"rounds at a coupling ratio of {CERTIFICATION_RATIO_THRESHOLD:.2f} or lower "
        f"(earns a permanent +{CERTIFICATION_PRICE_PREMIUM * 100:.0f}% price premium)."
    )


def plant_pivot_confirm_message():
    """F12 — the confirm dialog's exact income tradeoff, computed from
    the live constants."""
    discount = (1 - PLANT_BASED_INCOME_MULTIPLIER) * 100
    total = PLANT_PIVOT_FRACTION_PER_UNIT * (1 - PLANT_BASED_INCOME_MULTIPLIER) * 100
    return (
        f"Invest {PLANT_PIVOT_COST} funds in the Plant-Based Pivot? It shifts "
        f"{PLANT_PIVOT_FRACTION_PER_UNIT * 100:.0f}% of your output to near-zero-methane plant-based "
        f"production. Tradeoff: shifted output earns {discount:.0f}% less income per unit, so this step "
        f"lowers your total income by about {total:.2f}%."
    )


report_card_open = False


def on_toggle_report_card(event=None):
    global report_card_open
    report_card_open = not report_card_open
    update_report_card()


def update_report_card():
    toggle = document.getElementById("report-card-toggle-button")
    panel = document.getElementById("report-card-panel")
    toggle.innerText = "Hide Report Card" if report_card_open else "📊 Report Card"
    panel.hidden = not report_card_open
    if not report_card_open:
        return
    panel.innerHTML = report_card_html()
    _request_comparison()


# F15 — surfacing the real documented ~42% methane-intensity-reduction
# figure (also cited in INFO_PAGE) as a live in-game comparison.
def real_world_comparison_message():
    pct = farm.decoupled_fraction() * 100
    real_pct = REAL_WORLD_REDUCTION_FRACTION * 100
    if farm.decoupled_fraction() > REAL_WORLD_REDUCTION_FRACTION:
        return (
            f"Congratulations: you've cut emissions intensity by {pct:.0f}%, beating the real "
            f"~{real_pct:.0f}% benchmark documented on real farms."
        )
    if farm.decoupled_fraction() >= REAL_WORLD_REDUCTION_FRACTION:
        return (
            f"You've cut emissions intensity by {pct:.0f}% — matching the real "
            f"~{real_pct:.0f}% reduction documented on real farms."
        )
    return (
        f"You've cut emissions intensity by {pct:.0f}% so far — real farms have documented "
        f"a ~{real_pct:.0f}% reduction through better practices."
    )


def real_world_comparison_chart_svg():
    """Z17 (site-wide goal): a small bar chart alongside the F15 text
    sentence above -- this comparison previously had no chart at all,
    only prose. Built on the shared shared/comparison_chart.py component
    (the same module Grid's own C15/global-comparison line and
    Continuum's K13 "vs. history" chart now share), via its
    bar_comparison_svg() -- the simplest chart shape in that module, for
    a single current value against a single hardcoded real-world
    reference rather than a round-by-round history."""
    return comparison_chart.bar_comparison_svg(
        farm.decoupled_fraction() * 100,
        REAL_WORLD_REDUCTION_FRACTION * 100,
        unit="%",
        your_label="You",
        reference_label="Real farms (documented)",
        aria_label="Your emissions-intensity reduction against the documented real-world benchmark",
    )


# F8 — a combined readout for how the efficiency measures (feed/caps/
# capture) and the plant-based pivot interact, since coupling_ratio()
# blends both but the UI otherwise only ever shows them separately.
def combined_decoupling_message():
    efficiency_ratio = farm._efficiency_coupling_ratio()
    final_ratio = farm.coupling_ratio()
    plant_fraction = farm.plant_based_fraction()
    if plant_fraction <= 0:
        return (
            f"Efficiency measures alone bring you to {efficiency_ratio:.2f} methane/herd/round "
            "— the plant-based pivot isn't active yet."
        )
    return (
        f"Efficiency measures bring you to {efficiency_ratio:.2f}, and the {plant_fraction * 100:.0f}% "
        f"plant-based pivot blends that down further to {final_ratio:.2f} methane/herd/round."
    )


# F9 — a consequence preview next to the Grow Herd button: what the very
# next unit would cost and add, computed without mutating state.
def grow_consequence_message():
    cost = farm.grow_herd_cost()
    methane_delta = farm.coupling_ratio()
    fraction = farm.plant_based_fraction()
    income_multiplier = (1 - fraction) + fraction * PLANT_BASED_INCOME_MULTIPLIER
    income_per_unit = (
        HERD_INCOME_PER_UNIT * income_multiplier * farm.certification_multiplier()
        * (1 - farm.pressure_fraction())
    )
    # F18 — before -> after totals with a direction arrow.
    income_before = farm.herd_size * income_per_unit
    income_after = (farm.herd_size + 1) * income_per_unit
    methane_before = farm.methane_this_round()
    methane_after = methane_before + methane_delta
    return (
        f"Next unit: costs {cost:.0f}. Income/round {income_before:.1f} \u2192 {income_after:.1f} \u2191, "
        f"methane/round {methane_before:.2f} \u2192 {methane_after:.2f} \u2191."
    )


# ===========================================================================
# Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md) — following SOL's reference
# integration. Every achievement's earned status is a pure function of
# state that already exists elsewhere in this module, recomputed fresh
# every call — never a separately hand-maintained "earned" flag. Two
# checks needed genuinely new tracked state (max_pressure_fraction_seen
# on FarmState, mutated only in advance_round() where pressure is
# actually computed) — nothing else in this module records the worst
# pressure a session has seen.
# ===========================================================================
ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    """Same loading contract as SOL's `_read_achievements_json()` / Le
    Champ de Mots' `_read_json_asset()`: the boot script fetches
    achievements.json and hands it to Python as a window global before
    this file runs; the pytest harness's fake `js` module has no such
    attribute, so this falls through to reading the file straight off
    disk, keeping the module importable outside a real browser."""
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        _js = None

    raw = getattr(_js, "ACHIEVEMENTS_JSON", None) if _js is not None else None
    if raw is not None:
        return str(raw)

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, ACHIEVEMENTS_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Degrades to "no achievements catalog" rather than crashing this module's
# whole import — achievements are additive, not core to Herd's gameplay.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []

GROWING_OPERATION_TARGET = 10
MAJOR_OPERATION_TARGET = 25
LONG_HAUL_TARGET = 25
CENTURY_FARM_TARGET = 50
# Starting funds is exactly 300 (STARTING_FUNDS), so a target of 300
# would be trivially "earned" on a brand-new, untouched farm -- picked
# 400 specifically so it requires genuine progress.
SCORE_400_TARGET = 400
DECOUPLING_DIVIDEND_TARGET = 50.0
OUTPERFORMING_BASELINE_MIN_ROUND = 5


def _all_three_measures_invested():
    return all(farm.decoupling_investment[m] >= 1 for m in DECOUPLING_MEASURES)


# Each checker is a zero-argument predicate read fresh off live state —
# nothing here is ever cached or hand-flagged.
ACHIEVEMENT_CHECKS = {
    "first_herd": lambda: farm.herd_size >= 1,
    "growing_operation": lambda: farm.herd_size >= GROWING_OPERATION_TARGET,
    "major_operation": lambda: farm.herd_size >= MAJOR_OPERATION_TARGET,
    "first_decoupling": lambda: any(farm.decoupling_investment[m] >= 1 for m in DECOUPLING_MEASURES),
    "all_three_measures": _all_three_measures_invested,
    "quarter_decoupled": lambda: farm.decoupled_fraction() >= 0.25,
    "half_decoupled": lambda: farm.decoupled_fraction() >= 0.5,
    "fully_decoupled": lambda: farm.decoupled_fraction() >= 0.9,
    "sustainably_certified": lambda: farm.certified,
    "plant_pioneer": lambda: farm.plant_pivot_investment >= 1,
    "half_plant_based": lambda: farm.plant_based_fraction() >= 0.3,
    "max_plant_pivot": lambda: farm.plant_based_fraction() >= MAX_PLANT_BASED_FRACTION,
    "real_world_match": lambda: farm.decoupled_fraction() >= REAL_WORLD_REDUCTION_FRACTION,
    "outperforming_baseline": lambda: (
        farm.round_number > OUTPERFORMING_BASELINE_MIN_ROUND and farm.score() > farm.counterfactual_score()
    ),
    "decoupling_dividend": lambda: (
        farm.score() - farm.counterfactual_score() >= DECOUPLING_DIVIDEND_TARGET
    ),
    "clean_operator": lambda: (
        farm.round_number >= CLEAN_OPERATOR_MIN_ROUND
        and farm.max_pressure_fraction_seen < CLEAN_OPERATOR_MAX_PRESSURE
    ),
    "long_haul": lambda: farm.round_number >= LONG_HAUL_TARGET,
    "century_farm": lambda: farm.round_number >= CENTURY_FARM_TARGET,
    "score_400": lambda: farm.score() >= SCORE_400_TARGET,
}

# Progress readouts, only for achievements with a natural numeric scale-up
# — a plain earned/not-yet is the honest shape for a one-shot milestone
# like "invest in all three measures at least once."
ACHIEVEMENT_PROGRESS = {
    "growing_operation": lambda: (min(farm.herd_size, GROWING_OPERATION_TARGET), GROWING_OPERATION_TARGET),
    "major_operation": lambda: (min(farm.herd_size, MAJOR_OPERATION_TARGET), MAJOR_OPERATION_TARGET),
    "quarter_decoupled": lambda: (min(100, round(farm.decoupled_fraction() * 100)), 25),
    "half_decoupled": lambda: (min(100, round(farm.decoupled_fraction() * 100)), 50),
    "fully_decoupled": lambda: (min(100, round(farm.decoupled_fraction() * 100)), 90),
    "half_plant_based": lambda: (min(100, round(farm.plant_based_fraction() * 100)), 30),
    "max_plant_pivot": lambda: (
        min(100, round(farm.plant_based_fraction() * 100)),
        round(MAX_PLANT_BASED_FRACTION * 100),
    ),
    "real_world_match": lambda: (
        min(100, round(farm.decoupled_fraction() * 100)),
        round(REAL_WORLD_REDUCTION_FRACTION * 100),
    ),
    "decoupling_dividend": lambda: (
        max(0, min(round(DECOUPLING_DIVIDEND_TARGET), round(farm.score() - farm.counterfactual_score()))),
        round(DECOUPLING_DIVIDEND_TARGET),
    ),
    "long_haul": lambda: (min(farm.round_number, LONG_HAUL_TARGET), LONG_HAUL_TARGET),
    "century_farm": lambda: (min(farm.round_number, CENTURY_FARM_TARGET), CENTURY_FARM_TARGET),
    "score_400": lambda: (max(0, min(round(farm.score()), SCORE_400_TARGET)), SCORE_400_TARGET),
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
        card.dataset.achievementId = entry["id"]

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
    # #account-achievements-dashboard, ACHIEVEMENTS-SYSTEM-DESIGN.md §5).
    # Relative path, no leading "/" (site-level milestone 7's GitHub
    # Pages subpath fix). Rebuilt each open alongside the cards since the
    # panel is cleared first. The hub-side script.js registration that
    # makes Herd's save data actually show up on that dashboard is a
    # root-file change, out of scope for this games/herd/-only dispatch.
    hub_link = document.createElement("a")
    hub_link.innerText = "View the hub-wide achievements dashboard →"
    hub_link.href = "../../index.html#account-achievements-dashboard"
    hub_link.className = "achievements-hub-link"
    panel.appendChild(hub_link)

    _request_achievement_stats()


def _request_achievement_stats():
    """Z27b: asks the page's optional JS hook (window.applyAchievementStats,
    shared/achievement-stats.js) to fill in each achievement card's own
    "Earned by N% of players" line from the cross-player stats endpoint
    (planning/TODO.md Z1). Absent hook (pytest, or a page without the
    shared script) leaves the cards exactly as rendered above -- same
    fails-soft shape as Grid's C15 window.gridCompare."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "applyAchievementStats", None)
    if hook is not None:
        hook()


# Unlock toast (TODO.md "roll achievements out everywhere" — required on
# top of the base per-game rollout). Same pattern as Grid/Canopy's
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
    (grow/invest/advance round) — never from render() itself, since
    load_state() also calls render() and a loaded save with several
    achievements already earned must not flood the player with toasts
    for all of them at once (see _seed_achievement_toast_baseline)."""
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


# F5/F11/F17 — a second, distinct toast for one-time gameplay nudges
# (not achievements): the half-decoupled callout, the pressure-spike
# callout, and the methane-penalty nudge. Kept separate from the
# achievement toast (same shape Grid keeps its achievement-toast and
# disruption-toast separate) so a nudge is never visually confused with
# an unlock.
_MILESTONE_CALLOUT_MESSAGES = {
    "half_decoupled": (
        "You've cut your emissions-per-herd-unit ratio 50% below baseline. That's what "
        '"decoupled" means: the same herd now emits half as much methane, so growth and '
        "emissions are no longer locked together."
    ),
    "pressure": (
        "Market/regulatory pressure just crossed 25% income loss — sustained methane is now "
        "visibly eating into your income."
    ),
    "methane_penalty": (
        "Your accumulated methane is now cutting a real chunk out of your score — decoupling "
        "measures reduce this without requiring you to shrink your herd."
    ),
}


def _display_milestone_toast(message):
    toast = document.getElementById("milestone-toast")
    text = document.getElementById("milestone-toast-text")
    text.innerText = message
    toast.hidden = False
    toast.classList.add("visible")

    def _hide(*args):
        toast.hidden = True
        toast.classList.remove("visible")
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, 5000)


def _check_milestone_callout():
    """Consumes FarmState.just_hit_callout (set at most once per
    advance_round() call) and shows its toast. Called from
    on_advance_round(), not render(), so a save/load round-trip (which
    also calls render()) never replays an old callout."""
    if farm.just_hit_callout is not None:
        message = _MILESTONE_CALLOUT_MESSAGES.get(farm.just_hit_callout)
        farm.just_hit_callout = None
        if message:
            _display_milestone_toast(message)


# F19 — lightweight pulse feedback on a successful investment click.
# Adds a CSS animation class to the element for a fixed short duration,
# then removes it, same setTimeout+create_proxy technique as the toasts
# above.
def _pulse(element_id):
    element = document.getElementById(element_id)
    element.classList.add("invest-pulse")

    def _unpulse(*args):
        element.classList.remove("invest-pulse")
        proxy.destroy()

    proxy = create_proxy(_unpulse)
    setTimeout(proxy, 350)


# F2 — scale the pasture visual's cow count with real herd size. The
# hero illustration has 5 fixed cow elements; rather than dynamically
# generating DOM nodes for an unbounded herd size, cows are progressively
# revealed at these herd-size thresholds and the rest stay hidden, so an
# empty pasture (herd_size == 0) reads as genuinely empty.
PASTURE_COW_THRESHOLDS = [
    ("pasture-cow-a", 1),
    ("pasture-cow-b", 3),
    ("pasture-cow-c", 6),
    ("pasture-cow-d", 10),
    ("pasture-cow-e", 15),
]


def update_pasture_visual():
    for element_id, threshold in PASTURE_COW_THRESHOLDS:
        document.getElementById(element_id).hidden = farm.herd_size < threshold
    # F2 — a small herd-size number overlay alongside the cow visual.
    count = document.getElementById("pasture-herd-count")
    count.innerText = f"Herd: {farm.herd_size}"
    count.hidden = farm.herd_size < 1
    # F30 — methane wisps thin out as the coupling ratio improves,
    # reinforcing the haze cue with motion: fainter with a lower ratio,
    # gone once the farm is ~90% decoupled.
    wisp_opacity = max(0.0, min(1.0, farm.coupling_ratio() / BASE_COUPLING_RATIO))
    for element_id in ("pasture-wisp-a", "pasture-wisp-c"):
        wisp = document.getElementById(element_id)
        wisp.style.opacity = f"{wisp_opacity:.2f}"
        wisp.hidden = farm.decoupled_fraction() >= 0.9


# ===========================================================================
# K16 (planning/TODO.md "What's New" changelog, site-wide goal): a small
# in-game "what's new" panel, same shape as the achievements catalog above
# -- a flat JSON list fetched into the Pyodide boot sequence and handed to
# Python as a window global (see index.html), rendered into a
# hidden-until-opened panel. Unlike achievements.json this catalog isn't a
# set of checkable conditions -- it's just curated highlight text -- so
# there's no earned/unearned state, only a newest-first list.
# ===========================================================================
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    """Same loading contract as _read_achievements_json(): the boot script
    fetches changelog.json and hands it to Python as a window global before
    this file runs; the pytest harness's fake `js` module has no such
    attribute, so this falls through to reading the file straight off disk,
    keeping the module importable outside a real browser."""
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        _js = None

    raw = getattr(_js, "CHANGELOG_JSON", None) if _js is not None else None
    if raw is not None:
        return str(raw)

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, CHANGELOG_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Degrades to "no changelog" rather than crashing this module's whole
# import -- same defensive shape as ACHIEVEMENTS above, since a "what's
# new" panel is additive, not core to Herd's gameplay.
try:
    CHANGELOG = sorted(json.loads(_read_changelog_json()), key=lambda entry: entry["date"], reverse=True)
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
    toggle.innerText = "Hide What's New" if changelog_open else f"\U0001f4cb What's New ({len(CHANGELOG)})"
    panel.hidden = not changelog_open
    if not changelog_open:
        return

    panel.innerHTML = ""
    if not CHANGELOG:
        empty = document.createElement("p")
        empty.innerText = "Nothing logged yet."
        panel.appendChild(empty)
        return

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


# F17 -- farm tour: short flavor vignettes reacting to the coupling ratio.
VIGNETTES = {
    "coupled": [
        "A neighbour's kid asks why the sky over the ridge looks hazy this morning.",
        "The co-op newsletter mentions methane again. You fold it into the pile of letters.",
        "Every feed truck that pulls in seems to leave a little more haze behind.",
    ],
    "improving": [
        "The vet notes the herd's digestion is calmer since the feed change.",
        "A sensor on the barn roof reads lower than last month. You tap it twice to be sure.",
        "At the market stall someone asks how you cut the smell. You show them the numbers.",
    ],
    "clean": [
        "Evening light, quiet pasture: the wisps over the cows have almost gone.",
        "A regional inspector visits, nods, and asks if she can bring a school group next spring.",
        "You catch yourself explaining decoupling to a stranger at the gate, and enjoying it.",
    ],
}


def farm_vignette():
    """Pure function of ratio + round: same farm, same story."""
    ratio = farm.coupling_ratio()
    band = "coupled" if ratio > 0.8 else ("improving" if ratio > 0.4 else "clean")
    options = VIGNETTES[band]
    return "\U0001F69C " + options[farm.round_number % len(options)]


def season_message():
    if not farm.variation_enabled:
        return "Market & weather variation is off (turn it on under Scenario options)."
    name, mod = season_for_round(farm.round_number)
    text = f"This round: {name}, income {mod * 100:+.0f}%."
    if demand_surge_active(farm.round_number):
        text += " Plant-based demand surge: plant-based output earns more this round."
    return text


def welfare_message():
    bonus = (farm.welfare_multiplier() - 1) * 100
    return f"Herd welfare: {farm.welfare():.0f}/100 (income {bonus:+.1f}% from welfare)"


def genetics_message():
    return (
        f"Breeding: {farm.genetics_active} lines active, {len(farm.genetics_pending)} maturing "
        f"({GENETICS_MATURE_ROUNDS} rounds each)"
    )


def biogas_message():
    surplus = max(0, farm.decoupling_investment["capture"] - CAPTURE_SELF_USE_UNITS)
    if surplus == 0:
        return (
            f"Biogas sales: the first {CAPTURE_SELF_USE_UNITS} Capture Systems cover on-farm energy; "
            "extra capacity is sold as biogas."
        )
    return f"Biogas sales: {surplus} surplus capture unit(s) earn {farm.biogas_sales():.1f} funds per round."


def policy_message():
    if farm.policy_offer_pending:
        return (
            f"Policy advisor: choose a {POLICY_SUBSIDY_DISCOUNT * 100:.0f}% decoupling subsidy for "
            f"{POLICY_SUBSIDY_ROUNDS} rounds, or a flat {POLICY_CASH_BONUS} cash bonus."
        )
    if farm.subsidy_rounds_left > 0:
        return f"Decoupling subsidy active: {farm.subsidy_rounds_left} rounds left."
    return ""


def render_extras():
    document.getElementById("vignette-display").innerText = farm_vignette()
    document.getElementById("season-display").innerText = season_message()
    document.getElementById("welfare-display").innerText = welfare_message()
    document.getElementById("genetics-display").innerText = genetics_message()
    genetics_button = document.getElementById("genetics-invest-button")
    genetics_button.innerText = f"Breeding Program ({GENETICS_COST})"
    genetics_button.disabled = farm.funds < GENETICS_COST
    document.getElementById("supply-chain-display").innerText = (
        f"Supply chain: {farm.supply_chain_investment}/{SUPPLY_CHAIN_MAX_UNITS} "
        f"(+{(farm.supply_chain_multiplier() - 1) * 100:.0f}% income)"
    )
    supply_button = document.getElementById("supply-chain-invest-button")
    supply_button.innerText = f"Processing & Distribution ({SUPPLY_CHAIN_COST})"
    supply_button.disabled = farm.funds < SUPPLY_CHAIN_COST or farm.supply_chain_investment >= SUPPLY_CHAIN_MAX_UNITS
    document.getElementById("biogas-display").innerText = biogas_message()
    document.getElementById("variation-checkbox").checked = farm.variation_enabled
    document.getElementById("cap-checkbox").checked = farm.regional_cap_enabled
    document.getElementById("cap-display").innerText = (
        f"Regional cap: {farm.methane_this_round():.1f} of {REGIONAL_CAP:.0f} methane/round. Growth is blocked past the cap."
        if farm.regional_cap_enabled else "Regional methane cap is off."
    )
    # F27 policy advisor
    document.getElementById("policy-panel").hidden = not farm.policy_offer_pending
    document.getElementById("policy-display").innerText = policy_message()
    render_succession()
    render_satellite()

    # F23 poultry
    unlocked = farm.poultry_unlocked()
    document.getElementById("poultry-panel").hidden = not unlocked
    if unlocked:
        document.getElementById("poultry-display").innerText = (
            f"Flock: {farm.poultry_size} bird(s). Emissions {farm.poultry_coupling_ratio():.2f} methane-equivalent "
            f"per bird per round (cattle start at {BASE_COUPLING_RATIO:.2f}). Upkeep {POULTRY_UPKEEP_PER_UNIT} per bird."
        )
        grow_cost = farm.poultry_grow_cost()
        button = document.getElementById("poultry-grow-button")
        button.innerText = f"Grow Flock ({grow_cost:.0f})"
        button.disabled = farm.funds < grow_cost or farm.cap_blocks_growth(poultry=1)
        for measure, spec in POULTRY_MEASURES.items():
            document.getElementById(f"{measure}-count").innerText = str(farm.poultry_investment[measure])
            b = document.getElementById(f"{measure}-invest-button")
            b.innerText = f"{spec['label']} ({spec['cost']})"
            b.disabled = farm.funds < spec["cost"]


def satellite_message():
    if not farm.satellite_open:
        return (
            f"Open a smaller satellite farm for {SATELLITE_OPEN_COST} funds. It starts dirtier than your main farm "
            f"({SATELLITE_BASE_RATIO:.2f} methane per animal), but decoupling your main farm past "
            f"{round(SATELLITE_OFFSET_FLOOR * 100)}% starts cutting its emissions too."
        )
    offset = round(farm.satellite_offset_fraction() * 100)
    return (
        f"Satellite herd: {farm.satellite_size} of {SATELLITE_MAX_SIZE} animals. Emissions "
        f"{farm.satellite_coupling_ratio():.2f} methane per animal per round "
        f"(its own retrofits give {farm.satellite_own_ratio():.2f}; main-farm surplus offsets {offset}%). "
        f"Retrofits {farm.satellite_retrofits}/{SATELLITE_MAX_RETROFITS}."
    )


def render_satellite():
    panel = document.getElementById("satellite-panel")
    available = farm.satellite_available()
    panel.hidden = not available
    if not available:
        return
    document.getElementById("satellite-display").innerText = satellite_message()
    open_button = document.getElementById("satellite-open-button")
    grow_button = document.getElementById("satellite-grow-button")
    retrofit_button = document.getElementById("satellite-retrofit-button")
    open_button.hidden = farm.satellite_open
    grow_button.hidden = not farm.satellite_open
    retrofit_button.hidden = not farm.satellite_open
    open_button.innerText = f"Open Satellite Farm ({SATELLITE_OPEN_COST})"
    open_button.disabled = farm.funds < SATELLITE_OPEN_COST
    grow_cost = farm.satellite_grow_cost()
    grow_button.innerText = f"Grow Satellite Herd ({grow_cost:.1f})"
    grow_button.disabled = (
        farm.funds < grow_cost or farm.satellite_size >= SATELLITE_MAX_SIZE or farm.cap_blocks_growth(satellite=1)
    )
    retrofit_button.innerText = f"Retrofit Barns ({SATELLITE_RETROFIT_COST})"
    retrofit_button.disabled = (
        farm.funds < SATELLITE_RETROFIT_COST or farm.satellite_retrofits >= SATELLITE_MAX_RETROFITS
    )


def _make_satellite_handler(action, button_id):
    def handler(event=None):
        if getattr(farm, action)():
            _pulse(button_id)
        render()
    return handler


def on_grow_poultry(event=None):
    if farm.grow_poultry():
        _pulse("poultry-grow-button")
    render()


def _make_poultry_handler(measure):
    def handler(event=None):
        if farm.invest_poultry(measure):
            _pulse(f"{measure}-count")
        render()
    return handler


def on_invest_genetics(event=None):
    if farm.invest_genetics():
        _pulse("genetics-invest-button")
    render()


def on_invest_supply_chain(event=None):
    if farm.invest_supply_chain():
        _pulse("supply-chain-invest-button")
    render()


def on_toggle_variation(event=None):
    farm.variation_enabled = bool(document.getElementById("variation-checkbox").checked)
    render()


def on_toggle_cap(event=None):
    farm.regional_cap_enabled = bool(document.getElementById("cap-checkbox").checked)
    render()


def on_policy_subsidy(event=None):
    farm.choose_policy("subsidy")
    render()


def on_policy_cash(event=None):
    farm.choose_policy("cash")
    render()


def render():
    render_info_page()
    _maybe_update_record_coupling_ratio()
    coupling_fraction = farm.coupling_ratio() / BASE_COUPLING_RATIO
    document.getElementById("coupling-gauge").innerHTML = coupling_gauge_svg(
        coupling_fraction, record_coupling_ratio
    )
    document.getElementById("coupling-gauge-label").innerText = (
        f"Emissions per herd unit: {farm.coupling_ratio():.2f} methane/round"
    )
    render_record_coupling_ratio()

    document.getElementById("haze-overlay").style.opacity = (
        f"{(farm.pressure_fraction() / MAX_PRESSURE) * MAX_HAZE_OPACITY:.3f}"
    )

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

    grow_cost = farm.grow_herd_cost()
    grow_button = document.getElementById("grow-herd-button")
    grow_button.innerText = f"Grow Herd ({grow_cost:.0f})"
    grow_button.disabled = farm.funds < grow_cost or farm.cap_blocks_growth(herd=1)
    # F9 — consequence preview next to the Grow Herd button.
    document.getElementById("grow-consequence-preview").innerText = grow_consequence_message()

    for measure, spec in DECOUPLING_MEASURES.items():
        document.getElementById(f"{measure}-name").innerText = f"{spec['icon']} {spec['label']}"
        document.getElementById(f"{measure}-count").innerText = str(
            farm.decoupling_investment[measure]
        )
        button = document.getElementById(f"{measure}-invest-button")
        cost = farm.decoupling_cost(measure)
        button.innerText = f"{spec['label']} ({cost:g})"
        button.disabled = farm.funds < cost

    document.getElementById("decoupling-summary-display").innerText = (
        f"Decoupled: {farm.decoupled_fraction() * 100:.0f}% below baseline emissions per herd unit"
    )

    plant_fraction = farm.plant_based_fraction()
    document.getElementById("plant-pivot-count").innerText = str(farm.plant_pivot_investment)
    document.getElementById("plant-pivot-display").innerText = (
        f"{plant_fraction * 100:.0f}% of output shifted to plant-based production"
    )
    plant_pivot_button = document.getElementById("plant-pivot-invest-button")
    plant_pivot_button.innerText = f"Plant-Based Pivot ({PLANT_PIVOT_COST})"
    plant_pivot_button.disabled = farm.funds < PLANT_PIVOT_COST or plant_fraction >= MAX_PLANT_BASED_FRACTION

    # F8 — combined efficiency + plant-pivot readout.
    document.getElementById("combined-decoupling-display").innerText = combined_decoupling_message()

    # F14 — min/max labels behind the coupling gauge. coupling_ratio()
    # only ever decreases as investment counts rise (they never go down),
    # so the session's best-ever value is simply the current one, and the
    # worst-ever is always the fixed baseline.
    document.getElementById("gauge-range-display").innerText = (
        f"Session best: {farm.coupling_ratio():.2f}  |  Baseline: {BASE_COUPLING_RATIO:.2f}"
    )

    # F15 — the real-world 42% comparison.
    document.getElementById("real-world-comparison-display").innerText = real_world_comparison_message()
    document.getElementById("real-world-comparison-chart").innerHTML = real_world_comparison_chart_svg()

    document.getElementById("certification-display").innerText = certification_message()

    # F7 — methane-over-rounds trend graph.
    document.getElementById("methane-trend-graph").innerHTML = methane_trend_graph_svg(farm.methane_history)

    # F1/F13 — live pure-growth counterfactual + persistent baseline-farm card.
    document.getElementById("counterfactual-comparison-display").innerText = counterfactual_comparison_message()
    document.getElementById("baseline-herd-display").innerText = f"Herd size: {farm.herd_size}"
    document.getElementById("baseline-funds-display").innerText = f"Funds: {farm.counterfactual_funds:.0f}"
    document.getElementById("baseline-methane-display").innerText = f"Methane: {farm.counterfactual_methane:.0f}"
    document.getElementById("baseline-score-display").innerText = f"Score: {farm.counterfactual_score():.0f}"

    # F3 — report card panel, kept in sync if left open across a render.
    if report_card_open:
        document.getElementById("report-card-panel").innerHTML = report_card_html()
        _request_comparison()  # F7 -- re-asks the hook; JS side caches/dedupes

    # Achievements panel, kept in sync if left open across a render.
    update_achievements_display()

    # "What's New" changelog panel, kept in sync if left open across a render.
    update_changelog_display()

    # F2 — pasture visual cow count scales with real herd size.
    update_pasture_visual()

    render_extras()


def on_grow_herd(event=None):
    if farm.grow_herd():
        _pulse("grow-herd-button")
    render()
    _check_new_achievements_for_toast()


def _make_decoupling_handler(measure):
    def handler(event=None):
        ratio_before = farm.coupling_ratio()
        if farm.invest_decoupling(measure):
            _pulse(f"{measure}-count")
            if farm.coupling_ratio() < ratio_before - 1e-9:
                _pulse("gauge-range-display")  # F22 — new session-best
        render()
        _check_new_achievements_for_toast()
    return handler


def _confirm_dialog_ask(action_id, message, confirm_label, on_confirm, allow_skip=True):
    """Routes a guarded action through the shared shared/confirm-dialog.js
    widget when it's available, or runs the action immediately when it
    isn't -- same lazy `from js import window`/getattr-default shape as
    every other optional-JS-hook call in this hub (Grid's own copy of
    this helper, continuum's `_notify_visual_layer()`, champ-de-mots'
    `_dispatch_report()`). The pytest fake-DOM harness's `js` module only
    ever fakes `document`/`setTimeout` (see conftest.py's
    `_install_pyodide_fakes`), never `window`, so `from js import window`
    raises ImportError there and this falls straight through to calling
    on_confirm() synchronously -- which is exactly what every existing
    plant-pivot-invest test in this suite already expects."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        on_confirm()
        return
    confirm_dialog = getattr(window, "ConfirmDialog", None)
    if confirm_dialog is None:
        on_confirm()
        return
    kwargs = {}
    if not allow_skip:
        kwargs["allowSkip"] = False
    confirm_dialog.ask(
        id=action_id,
        message=message,
        confirmLabel=confirm_label,
        onConfirm=create_proxy(on_confirm),
        **kwargs,
    )


# ===========================================================================
# F25: farm succession -- an Aftermath-style meta-progression, built
# independently. A certified farm can be handed to the next generation: the
# farm restarts from scratch, the generation counter rises and the outgoing
# farm earns legacy points, which buy permanent perks. Tied to F23: raising a
# poultry flock feeds the handover, and the Heritage Flock perk carries the
# poultry unlock into every later generation. Deliberately module-level (like
# `chains_completed_count` in Loop): a reset of `farm` must never touch it.
# ===========================================================================
SUCCESSION_BASE_POINTS = 1
SUCCESSION_FLOCK_BONUS_POINTS = 1
SUCCESSION_FLOCK_MIN_SIZE = 3
LEGACY_PERKS = {
    "family_savings": {"label": "Family Savings", "cost": 1, "max": 3,
                       "blurb": "+75 starting funds per level, every generation."},
    "heritage_flock": {"label": "Heritage Flock", "cost": 2, "max": 1,
                       "blurb": "The poultry flock is available from round 1, no certification needed."},
    "mentor_methods": {"label": "Mentor's Methods", "cost": 2, "max": 1,
                       "blurb": "Every generation starts with one Feed Additives unit already in place."},
}
FAMILY_SAVINGS_FUNDS = 75

generation = 1
legacy_points = 0
legacy_perks = {}


def can_hand_over():
    return farm.certified


def handover_points():
    """Points the current farm would earn on handover."""
    points = SUCCESSION_BASE_POINTS
    if farm.poultry_size >= SUCCESSION_FLOCK_MIN_SIZE:
        points += SUCCESSION_FLOCK_BONUS_POINTS
    return points


def _apply_perk_to_farm(name):
    """One level of a perk's effect on the CURRENT farm (used both when a perk
    is bought and when a new generation starts)."""
    if name == "family_savings":
        farm.funds += FAMILY_SAVINGS_FUNDS
        farm.counterfactual_funds += FAMILY_SAVINGS_FUNDS
    elif name == "mentor_methods":
        farm.decoupling_investment["feed"] += 1


def buy_legacy_perk(name):
    spec = LEGACY_PERKS.get(name)
    if spec is None:
        return False
    level = legacy_perks.get(name, 0)
    global legacy_points
    if level >= spec["max"] or legacy_points < spec["cost"]:
        return False
    legacy_points -= spec["cost"]
    legacy_perks[name] = level + 1
    _apply_perk_to_farm(name)
    return True


def hand_over_farm():
    """Awards points, starts the next generation on a fresh farm and applies
    every perk owned so far. Returns the points earned, or None if the farm
    can't be handed over yet."""
    global farm, generation, legacy_points
    if not can_hand_over():
        return None
    earned = handover_points()
    legacy_points += earned
    generation += 1
    farm = FarmState()
    for name, level in legacy_perks.items():
        for _ in range(level):
            _apply_perk_to_farm(name)
    return earned


def render_succession():
    panel = document.getElementById("succession-panel")
    visible = farm.certified or generation > 1 or legacy_points > 0 or bool(legacy_perks)
    panel.hidden = not visible
    if not visible:
        return
    status = f"Generation {generation}. Legacy points: {legacy_points}."
    if can_hand_over():
        status += f" Handing over now would earn {handover_points()} point(s)."
    else:
        status += " Earn sustainable certification to be able to hand the farm down."
    document.getElementById("succession-display").innerText = status
    hand_button = document.getElementById("succession-button")
    hand_button.disabled = not can_hand_over()
    for name, spec in LEGACY_PERKS.items():
        level = legacy_perks.get(name, 0)
        button = document.getElementById(f"perk-{name.replace('_', '-')}-button")
        button.innerText = f"{spec['label']} ({level}/{spec['max']}) \u2014 {spec['cost']} pt"
        button.title = spec["blurb"]
        button.disabled = level >= spec["max"] or legacy_points < spec["cost"]


def on_hand_over_farm(event=None):
    def do_handover():
        if hand_over_farm() is not None:
            render()
            _check_new_achievements_for_toast()

    _confirm_dialog_ask(
        action_id="herd-succession",
        message=(
            f"Hand the farm to the next generation? The farm restarts from scratch and you earn "
            f"{handover_points()} legacy point(s) to spend on permanent perks."
        ),
        confirm_label="Hand over",
        on_confirm=do_handover,
        allow_skip=False,
    )


def _make_perk_handler(name):
    def handler(event=None):
        if buy_legacy_perk(name):
            render()
    return handler


def on_invest_plant_pivot(event=None):
    # F16 (planning/TODO.md's shared confirmation-dialog goal) -- this is
    # the pricier of the two decoupling investments (25, vs. 15/20/20 for
    # feed/caps/capture) and, unlike those three, it changes *what* the
    # herd produces rather than just how efficiently -- worth a beat of
    # confirmation before committing funds to it. Pre-action confirm
    # only, per the shared pattern's own shape (no undo window); a player
    # who invests repeatedly can check "don't ask again" once.
    def do_invest():
        ratio_before = farm.coupling_ratio()
        if farm.invest_plant_pivot():
            _pulse("plant-pivot-count")
            if farm.coupling_ratio() < ratio_before - 1e-9:
                _pulse("gauge-range-display")  # F22 — new session-best
        render()
        _check_new_achievements_for_toast()

    _confirm_dialog_ask(
        action_id="herd-plant-pivot-invest",
        message=plant_pivot_confirm_message(),
        confirm_label="Invest",
        on_confirm=do_invest,
    )


def on_advance_round(event=None):
    farm.advance_round()
    render()
    _check_milestone_callout()
    _check_new_achievements_for_toast()
    if farm.just_flattened:
        farm.just_flattened = False
        _pulse("methane-trend-graph")  # F16


# SAVE-BUTTON-INTEGRATION.md contract for the shared shared/save-widget.js:
# get_state() returns every module-level mutable game-state field as one
# plain, JSON-safe dict, and load_state() is its exact inverse. SOL is the
# reference integration for this contract. decoupling_investment is copied
# (not handed back by reference) so continued play after taking a
# "snapshot" can't silently mutate it, same reasoning as SOL's
# serialize_state() docstring. info_page_open is deliberately excluded —
# it's a cosmetic panel toggle, not tracked game progress.
def get_state():
    state = {
        "round_number": farm.round_number,
        "funds": farm.funds,
        "herd_size": farm.herd_size,
        "methane": farm.methane,
        "decoupling_investment": dict(farm.decoupling_investment),
        "plant_pivot_investment": farm.plant_pivot_investment,
        "counterfactual_funds": farm.counterfactual_funds,
        "counterfactual_methane": farm.counterfactual_methane,
        "methane_history": list(farm.methane_history),
        "max_pressure_fraction_seen": farm.max_pressure_fraction_seen,
        "seen_half_decoupled_callout": farm.seen_half_decoupled_callout,
        "seen_pressure_callout": farm.seen_pressure_callout,
        "seen_methane_penalty_nudge": farm.seen_methane_penalty_nudge,
        "certification_streak": farm.certification_streak,
        "certified": farm.certified,
        "poultry_size": farm.poultry_size,
        "poultry_investment": dict(farm.poultry_investment),
        "genetics_active": farm.genetics_active,
        "genetics_pending": list(farm.genetics_pending),
        "supply_chain_investment": farm.supply_chain_investment,
        "variation_enabled": farm.variation_enabled,
        "regional_cap_enabled": farm.regional_cap_enabled,
        "policy_offer_pending": farm.policy_offer_pending,
        "subsidy_rounds_left": farm.subsidy_rounds_left,
        "achievements_earned": achievement_ids_earned(),
    }
    # F1: satellite state only once the satellite has been opened.
    if farm.satellite_open:
        state["satellite_open"] = True
        state["satellite_size"] = farm.satellite_size
        state["satellite_retrofits"] = farm.satellite_retrofits
    # F25: succession state is written only once a handover has happened or
    # points/perks exist, so an ordinary save is unchanged.
    if generation > 1:
        state["generation"] = generation
    if legacy_points > 0:
        state["legacy_points"] = legacy_points
    if legacy_perks:
        state["legacy_perks"] = dict(legacy_perks)
    return state


def _safe_int(value, default):
    """Non-negative int from untrusted save data, else default."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    if value != value or value in (float("inf"), float("-inf")):
        return default
    return max(0, int(value))


def load_state(data):
    if not isinstance(data, dict):
        return False
    # Every top-level field uses a .get() fallback (to the farm's current
    # live value) rather than bare data["key"] indexing -- a save missing
    # any single field (an older save predating that field, e.g. one from
    # before the Pass 2 plant-based pivot added plant_pivot_investment to
    # the state dict, or a hand-edited/corrupted payload) must not crash
    # load_state() outright and abort every field after the missing one,
    # the same bare-indexing bug already fixed in Tide's load_state() --
    # see BCM114-DEV-LOG.md 2026-09-02.
    farm.round_number = data.get("round_number", farm.round_number)
    farm.funds = data.get("funds", farm.funds)
    farm.herd_size = data.get("herd_size", farm.herd_size)
    farm.methane = data.get("methane", farm.methane)
    # Merge key-by-key rather than replacing the dict outright: a save
    # missing a measure (an older save format from before that measure
    # existed, or a hand-edited/corrupted payload) must not wipe that
    # measure's key out of the live dict entirely -- render() and
    # _efficiency_coupling_ratio() both do decoupling_investment[measure]
    # for every measure in DECOUPLING_MEASURES unconditionally, so a
    # missing key would crash the game on the very next render/round.
    farm.decoupling_investment = {m: 0 for m in DECOUPLING_MEASURES}
    saved_decoupling_investment = data.get("decoupling_investment")
    if isinstance(saved_decoupling_investment, dict):
        farm.decoupling_investment.update(saved_decoupling_investment)
    farm.plant_pivot_investment = data.get("plant_pivot_investment", farm.plant_pivot_investment)
    farm.counterfactual_funds = data.get("counterfactual_funds", farm.counterfactual_funds)
    farm.counterfactual_methane = data.get("counterfactual_methane", farm.counterfactual_methane)
    saved_methane_history = data.get("methane_history")
    if isinstance(saved_methane_history, list) and saved_methane_history:
        farm.methane_history = list(saved_methane_history)
    farm.max_pressure_fraction_seen = data.get(
        "max_pressure_fraction_seen", farm.max_pressure_fraction_seen
    )
    farm.seen_half_decoupled_callout = data.get(
        "seen_half_decoupled_callout", farm.seen_half_decoupled_callout
    )
    farm.seen_pressure_callout = data.get("seen_pressure_callout", farm.seen_pressure_callout)
    farm.seen_methane_penalty_nudge = data.get(
        "seen_methane_penalty_nudge", farm.seen_methane_penalty_nudge
    )
    farm.certification_streak = data.get("certification_streak", 0)
    farm.certified = bool(data.get("certified", False))
    # F25: succession state, validated (ints only; perk names must exist and
    # levels are clamped to each perk's own maximum).
    global generation, legacy_points, legacy_perks
    generation = max(1, _safe_int(data.get("generation"), 1))
    legacy_points = _safe_int(data.get("legacy_points"), 0)
    legacy_perks = {}
    saved_perks = data.get("legacy_perks")
    if isinstance(saved_perks, dict):
        for name, spec in LEGACY_PERKS.items():
            level = min(spec["max"], _safe_int(saved_perks.get(name), 0))
            if level > 0:
                legacy_perks[name] = level
    # Round-3 fields: every one validated and defaulted (older saves lack them).
    farm.poultry_size = _safe_int(data.get("poultry_size"), 0)
    farm.poultry_investment = {m: 0 for m in POULTRY_MEASURES}
    saved_poultry = data.get("poultry_investment")
    if isinstance(saved_poultry, dict):
        for m in POULTRY_MEASURES:
            farm.poultry_investment[m] = _safe_int(saved_poultry.get(m), 0)
    farm.satellite_open = data.get("satellite_open") is True
    farm.satellite_size = min(SATELLITE_MAX_SIZE, _safe_int(data.get("satellite_size"), 0)) if farm.satellite_open else 0
    farm.satellite_retrofits = (
        min(SATELLITE_MAX_RETROFITS, _safe_int(data.get("satellite_retrofits"), 0)) if farm.satellite_open else 0
    )
    farm.genetics_active = _safe_int(data.get("genetics_active"), 0)
    pending = data.get("genetics_pending")
    farm.genetics_pending = (
        [_safe_int(r, 1) for r in pending if isinstance(r, (int, float)) and not isinstance(r, bool)]
        if isinstance(pending, list) else []
    )
    farm.supply_chain_investment = min(SUPPLY_CHAIN_MAX_UNITS, _safe_int(data.get("supply_chain_investment"), 0))
    farm.variation_enabled = data.get("variation_enabled") is True
    farm.regional_cap_enabled = data.get("regional_cap_enabled") is True
    farm.policy_offer_pending = data.get("policy_offer_pending") is True
    farm.subsidy_rounds_left = _safe_int(data.get("subsidy_rounds_left"), 0)
    # achievements_earned is deliberately never read back here -- it's a
    # write-only projection recomputed fresh by get_state() every save,
    # per ACHIEVEMENTS-SYSTEM-DESIGN.md.
    render()
    _seed_achievement_toast_baseline()
    return True


def setup():
    # index.html already marks these hidden via the `hidden` attribute,
    # but that markup default doesn't exist for the pytest fake-DOM
    # harness (a FakeElement starts with hidden=False) -- setting it
    # explicitly here keeps both environments consistent and costs
    # nothing in a real browser, where it's already true.
    document.getElementById("achievement-toast").hidden = True
    document.getElementById("milestone-toast").hidden = True
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
    document.getElementById("plant-pivot-invest-button").addEventListener(
        "click", create_proxy(on_invest_plant_pivot)
    )
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("report-card-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_report_card)
    )
    document.getElementById("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    for element_id, handler in (
        ("poultry-grow-button", on_grow_poultry),
        ("succession-button", on_hand_over_farm),
        ("perk-family-savings-button", _make_perk_handler("family_savings")),
        ("perk-heritage-flock-button", _make_perk_handler("heritage_flock")),
        ("perk-mentor-methods-button", _make_perk_handler("mentor_methods")),
        ("genetics-invest-button", on_invest_genetics),
        ("supply-chain-invest-button", on_invest_supply_chain),
        ("variation-checkbox", on_toggle_variation),
        ("cap-checkbox", on_toggle_cap),
        ("policy-subsidy-button", on_policy_subsidy),
        ("policy-cash-button", on_policy_cash),
    ):
        document.getElementById(element_id).addEventListener("click", create_proxy(handler))
    for element_id, action in (
        ("satellite-open-button", "open_satellite"),
        ("satellite-grow-button", "grow_satellite"),
        ("satellite-retrofit-button", "retrofit_satellite"),
    ):
        document.getElementById(element_id).addEventListener(
            "click", create_proxy(_make_satellite_handler(action, element_id))
        )
    for measure in POULTRY_MEASURES:
        document.getElementById(f"{measure}-invest-button").addEventListener(
            "click", create_proxy(_make_poultry_handler(measure))
        )
    render()
    _seed_achievement_toast_baseline()


setup()
