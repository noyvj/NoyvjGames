"""Herd — Industrial Agriculture & Methane Game.

Runs in-browser via Pyodide. The core farm loop (herd growth, income,
and round progression), the methane meter (coupled to herd size by
default), the decoupling investments that reduce that coupling, and the
soft market/regulatory consequence system are all implemented below --
all 7 milestones are complete (see CLAUDE.md's milestone table).
"""

import copy
import html
import json
import math
import os
import time

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

# F-9 -- the policy advisor draws its two offers from a pool of six options, without repeats
# until the pool has been used, in a fixed order (no luck). Each option has a plain real-world tag
# (a kind of scheme that exists, with no figures) shown next to it and in the advisor history.
POLICY_ORDER = ["subsidy", "cash", "carbon_credit", "feed_hedge", "organic_trial", "welfare_grant"]
POLICY_OPTIONS = {
    "subsidy": {
        "label": "Decoupling subsidy", "tag": "Subsidy programme",
        "blurb": f"{POLICY_SUBSIDY_DISCOUNT * 100:.0f}% off every decoupling lever for {POLICY_SUBSIDY_ROUNDS} rounds",
        "real": "Real-world idea: public programmes that help pay for methane-reduction equipment on farms.",
    },
    "cash": {
        "label": "Cash bonus", "tag": "Direct payment", "blurb": f"{POLICY_CASH_BONUS} funds now",
        "real": "Real-world idea: direct payments to farmers.",
    },
    "carbon_credit": {
        "label": "Carbon-credit contract", "tag": "Carbon market",
        "blurb": "funds now, more the further you are below baseline emissions",
        "real": "Real-world idea: voluntary carbon-credit contracts that pay a farm for emission cuts that are checked.",
    },
    "feed_hedge": {
        "label": "Feed-price hedge", "tag": "Price hedge", "blurb": "Feed Additives half price for 6 rounds",
        "real": "Real-world idea: forward contracts that fix a feed price in advance.",
    },
    "organic_trial": {
        "label": "Organic label trial", "tag": "Eco-label", "blurb": "+8% herd income for 4 rounds",
        "real": "Real-world idea: eco-labels that let a farm sell at a small premium while it is certified.",
    },
    "welfare_grant": {
        "label": "Welfare grant", "tag": "Welfare payment",
        "blurb": "funds now, more the higher your herd welfare is above 50",
        "real": "Real-world idea: payments that reward higher animal-welfare standards.",
    },
}
POLICY_HEDGE_DISCOUNT = 0.5
POLICY_HEDGE_ROUNDS = 6
POLICY_LABEL_BONUS = 0.08
POLICY_LABEL_ROUNDS = 4
POLICY_CARBON_BASE = 20
POLICY_CARBON_PER_DECOUPLED = 80
POLICY_WELFARE_BASE = 10
POLICY_WELFARE_PER_POINT = 1.2
POLICY_HISTORY_MAX = 40


# GF-15 -- perfect-round streak: a round is "perfect" when the methane it added
# fell below the previous round's AND funds ended the round higher than they ended
# the round before (so spending on decoupling still paid for itself). Streaks pay a
# small one-off bonus to the real farm (never the baseline) at these lengths.
PERFECT_STREAK_BONUSES = {3: 10, 5: 20, 10: 40}

# F-17 -- lever history: every purchase is logged (round, lever key, cost paid) and
# the log is capped so a very long game cannot grow the save without bound.
LEVER_LOG_MAX = 300
LEVER_LABELS = {
    "herd": "Grow Herd",
    "feed": "Feed Additives",
    "caps": "Herd Caps",
    "capture": "Capture Systems",
    "pivot": "Plant-Based Pivot",
    "genetics": "Breeding Program",
    "supply": "Processing & Distribution",
    "poultry": "Grow Flock",
    "litter": "Litter Management",
    "biofilter": "Ventilation Biofilters",
    "satellite_open": "Open Satellite Farm",
    "satellite_grow": "Grow Satellite Herd",
    "satellite_retrofit": "Retrofit Barns",
}

# F-19 -- bulk buying: Grow Herd and the three decoupling levers can be bought in steps
# of 1, 5 or as many as the funds (and the regional cap) allow, capped at BULK_MAX_UNITS
# so one click can never loop for long.
BULK_MODES = (1, 5, "max")
BULK_MAX_UNITS = 50

# GF-18 -- undo the last round: once per game, and it costs funds.
UNDO_PENALTY_FUNDS = 25

# F-20 -- round-delta chips: shown after Advance Round, fade after a few seconds unless pinned.
DELTA_KEYS = ("funds", "methane", "welfare", "pressure")
DELTA_FADE_MS = 6000

# F-28 -- a discreet pace note, and a save-and-rest nudge every this many rounds in one sitting.
SAVE_NUDGE_EVERY = 10

# GF-13 -- every herd unit has a name (fixed by its position in the herd and the generation,
# never random, so the names are the same after a reload). Longest-serving units of a
# retired generation go to the hall of fame.
COW_NAMES = [
    "Beyonmoo", "Sir Grazealot", "Moolan Rouge", "Udder Chaos", "Cowlin Farrell", "Hay Z",
    "Clover Kent", "Bovine Jovi", "Lady Gagraze", "Moo Thurman", "Dolly Pasture", "Count Chewcula",
    "Mootilda", "Grassy Elliott", "Marie Cowrie", "Buttercup Cumberbatch", "Hoofy Mercury",
    "Curd Vader", "Ruminate Rosie", "Daisy Ridley", "Cud Norris", "Flossie Nightingale",
    "Moomin", "Bessie Smith",
]
HALL_OF_FAME_SIZE = 5
HALL_PER_HANDOVER = 3


# F-1 -- Ranch Rules: four balance sliders for a custom run. Standard values are the ones the rest of
# the file is written around, so a farm on standard rules behaves exactly as it always has. Any other
# value makes the run "unranked": it stays off the opt-in leaderboard and out of the other-farms
# comparison (FY-32). Rules live outside `farm` (like the succession perks) so a handover keeps them.
RULE_SPECS = {
    "starting_funds": {"label": "Starting funds", "min": 150, "max": 600, "step": 50, "default": 300, "unit": ""},
    "season_swing": {"label": "Season swing", "min": 0, "max": 200, "step": 50, "default": 100, "unit": "%"},
    "pressure_strength": {"label": "Pressure penalty", "min": 50, "max": 200, "step": 25, "default": 100, "unit": "%"},
    "growth_slope": {"label": "Growth-cost slope", "min": 0, "max": 4, "step": 0.5, "default": 2.0, "unit": ""},
}
RULES_STORAGE_KEY = "herd-ranch-rules"
ranch_rules = {name: spec["default"] for name, spec in RULE_SPECS.items()}


def rule(name):
    return ranch_rules[name]


def clean_rule_value(name, value):
    """A usable value for this rule (a number inside its range, on its step), or None."""
    spec = RULE_SPECS.get(name)
    if spec is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value != value or abs(value) == float("inf"):
        return None
    clamped = max(spec["min"], min(spec["max"], float(value)))
    snapped = spec["min"] + round((clamped - spec["min"]) / spec["step"]) * spec["step"]
    return max(spec["min"], min(spec["max"], snapped))


def rules_are_custom():
    return any(abs(ranch_rules[n] - spec["default"]) > 1e-9 for n, spec in RULE_SPECS.items())


def rules_unranked():
    """True for a run that started or ran under non-standard Ranch Rules (it stays unranked for good)."""
    return farm.custom_rules_used or rules_are_custom()


def pressure_scale():
    """Methane at which pressure would reach 100% income loss; the strength rule shrinks or stretches it."""
    return PRESSURE_SCALE * 100.0 / ranch_rules["pressure_strength"]


def season_for_round(round_number):
    """Deterministic pseudo-random season (same on every load/replay)."""
    return SEASONS[(round_number * 7 + 3) % len(SEASONS)]


def demand_surge_active(round_number):
    return round_number % 6 in (4, 5)


class FarmState:
    def __init__(self):
        self.round_number = 1
        self.funds = rule("starting_funds")
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
        self.counterfactual_funds = rule("starting_funds")
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
        # F-9: the two options on the table, those already offered this cycle, a short history
        # of what was taken, and the two new timed effects.
        self.policy_offer = []
        self.policy_seen = []
        self.policy_history = []  # [round, taken id, other id]
        self.hedge_rounds_left = 0
        self.label_rounds_left = 0

        # F1 satellite farm.
        self.satellite_open = False
        self.satellite_size = 0
        self.satellite_retrofits = 0

        # GF-29/F-17/GF-15: per-round funds record (aligned with methane_history,
        # None where an older save never recorded it), the purchase log and the
        # perfect-round streak.
        self.funds_history = [rule("starting_funds")]
        # F-1: true once any round (or the farm's start) happened under non-standard Ranch Rules.
        self.custom_rules_used = rules_are_custom()
        self.lever_log = []
        self.perfect_streak = 0
        self.best_perfect_streak = 0
        self.last_round_perfect = False  # one-tick, not saved
        self.just_streak_bonus = None  # one-tick (streak, bonus), not saved

        # GF-18: one rewind per game. undo_snapshot (the state just before the last
        # Advance Round) is never saved; undo_used is, once it is true.
        self.undo_used = False
        self.undo_snapshot = None

    # ---- F-19 bulk buying ----
    def bulk_plan(self, key, mode):
        """(units, total cost) for buying `mode` (1, 5 or "max") units of Grow Herd ("herd")
        or one decoupling lever, worked out on a scratch copy so nothing changes here.
        It stops at whatever the funds or the regional cap allow. For 5 and max it also
        stops once the lever's efficiency ratio is at its floor, so a bulk click never buys
        units that save nothing (a single unit is always allowed, as before)."""
        want = mode if mode in (1, 5) else BULK_MAX_UNITS
        scratch = copy.copy(self)
        scratch.decoupling_investment = dict(self.decoupling_investment)
        scratch.lever_log = []
        units = 0
        while units < want:
            if (
                want > 1 and key in DECOUPLING_MEASURES
                and scratch._efficiency_coupling_ratio() <= MIN_COUPLING_RATIO + 1e-9
            ):
                break
            bought = scratch.grow_herd() if key == "herd" else scratch.invest_decoupling(key)
            if not bought:
                break
            units += 1
        return units, self.funds - scratch.funds

    def buy_bulk(self, key, mode):
        """Buys what bulk_plan() promised, one real purchase at a time (so every unit is
        logged and priced exactly as a single click would be). Returns units bought."""
        units, _total = self.bulk_plan(key, mode)
        bought = 0
        for _ in range(units):
            ok = self.grow_herd() if key == "herd" else self.invest_decoupling(key)
            if not ok:
                break
            bought += 1
        return bought

    # ---- GF-13 named cows ----
    def herd_unit_rounds(self):
        """The round each herd unit was bought, oldest first. Units the purchase log no
        longer holds (an old save, or a log that hit its cap) are counted as bought in round 1."""
        rounds = [r for r, k, _c in self.lever_log if k == "herd"]
        rounds = rounds[-self.herd_size:] if self.herd_size > 0 else []
        return [1] * (self.herd_size - len(rounds)) + rounds

    # ---- F-17 lever history ----
    def log_purchase(self, key, cost):
        self.lever_log.append([self.round_number, key, round(float(cost), 2)])
        extra = len(self.lever_log) - LEVER_LOG_MAX
        if extra > 0:
            del self.lever_log[:extra]

    # ---- F-13 funds per methane saved ----
    def methane_saved_by(self, key):
        """Methane per round that ONE more unit of this lever would remove at the
        current herd, found by trying the unit and putting it back (no lasting
        change). Uses the same ratio formulas as the real purchase, so the
        satellite network offset and the plant-pivot cap are included."""
        before = self.methane_this_round()
        if key in DECOUPLING_MEASURES:
            self.decoupling_investment[key] += 1
            after = self.methane_this_round()
            self.decoupling_investment[key] -= 1
        elif key == "pivot":
            self.plant_pivot_investment += 1
            after = self.methane_this_round()
            self.plant_pivot_investment -= 1
        elif key in POULTRY_MEASURES:
            self.poultry_investment[key] += 1
            after = self.methane_this_round()
            self.poultry_investment[key] -= 1
        elif key == "genetics":
            self.genetics_active += 1
            after = self.methane_this_round()
            self.genetics_active -= 1
        elif key == "satellite_retrofit":
            self.satellite_retrofits += 1
            after = self.methane_this_round()
            self.satellite_retrofits -= 1
        else:
            return 0.0
        return max(0.0, before - after)

    # ---- F-24 cap headroom ----
    def cap_headroom(self):
        """Free methane per round under the regional cap, never below zero."""
        return max(0.0, REGIONAL_CAP - self.methane_this_round())

    def growth_pace(self):
        """Herd units added per round so far, averaged over the rounds played."""
        return self.herd_size / max(1, self.round_number - 1)

    def rounds_until_cap(self):
        """Rounds until the cap blocks growth if the herd keeps growing at its pace so
        far and nothing is decoupled. None when the herd is not growing; 0 when the
        next animal is already blocked."""
        pace = self.growth_pace()
        ratio = self.coupling_ratio()
        if self.cap_blocks_growth(herd=1):
            return 0
        if pace <= 0 or ratio <= 0:
            return None
        return int(self.cap_headroom() / (pace * ratio))

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
        self.log_purchase("satellite_open", SATELLITE_OPEN_COST)
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
        self.log_purchase("satellite_grow", cost)
        return True

    def retrofit_satellite(self):
        if (
            not self.satellite_open or self.satellite_retrofits >= SATELLITE_MAX_RETROFITS
            or self.funds < SATELLITE_RETROFIT_COST
        ):
            return False
        self.funds -= SATELLITE_RETROFIT_COST
        self.satellite_retrofits += 1
        self.log_purchase("satellite_retrofit", SATELLITE_RETROFIT_COST)
        return True

    def satellite_net_income(self):
        return self.satellite_size * SATELLITE_INCOME_PER_UNIT

    # ---- F27 policy advisor ----
    def decoupling_cost(self, measure):
        cost = DECOUPLING_MEASURES[measure]["cost"]
        if self.subsidy_rounds_left > 0:
            cost *= 1 - POLICY_SUBSIDY_DISCOUNT
        if measure == "feed" and self.hedge_rounds_left > 0:
            cost *= 1 - POLICY_HEDGE_DISCOUNT
        return cost

    def label_multiplier(self):
        return 1 + POLICY_LABEL_BONUS if self.label_rounds_left > 0 else 1.0

    def current_policy_offer(self):
        """The two option ids on the table (the original pair when an older save has none stored)."""
        if len(self.policy_offer) == 2:
            return list(self.policy_offer)
        return ["subsidy", "cash"]

    def draw_policy_offer(self):
        """Two options from the pool, in the fixed order, none repeated until the pool is used up."""
        unseen = [o for o in POLICY_ORDER if o not in self.policy_seen]
        if len(unseen) < 2:
            self.policy_seen = []
            unseen = list(POLICY_ORDER)
        first = unseen[0]
        second = unseen[1 + len(self.policy_history) % (len(unseen) - 1)]
        self.policy_seen += [first, second]
        return [first, second]

    def carbon_credit_value(self):
        return round(POLICY_CARBON_BASE + POLICY_CARBON_PER_DECOUPLED * max(0.0, self.decoupled_fraction()))

    def welfare_grant_value(self):
        return round(POLICY_WELFARE_BASE + POLICY_WELFARE_PER_POINT * max(0.0, self.welfare() - WELFARE_START))

    def choose_policy(self, choice):
        if not self.policy_offer_pending or choice not in self.current_policy_offer():
            return False
        if choice == "subsidy":
            self.subsidy_rounds_left = POLICY_SUBSIDY_ROUNDS
        elif choice == "cash":
            self.funds += POLICY_CASH_BONUS
        elif choice == "carbon_credit":
            self.funds += self.carbon_credit_value()
        elif choice == "feed_hedge":
            self.hedge_rounds_left = POLICY_HEDGE_ROUNDS
        elif choice == "organic_trial":
            self.label_rounds_left = POLICY_LABEL_ROUNDS
        elif choice == "welfare_grant":
            self.funds += self.welfare_grant_value()
        else:
            return False
        other = [o for o in self.current_policy_offer() if o != choice][0]
        self.policy_history.append([self.round_number, choice, other])
        del self.policy_history[:-POLICY_HISTORY_MAX]
        self.policy_offer_pending = False
        self.policy_offer = []
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
        self.log_purchase("poultry", cost)
        return True

    def invest_poultry(self, measure):
        if not self.poultry_unlocked():
            return False
        cost = POULTRY_MEASURES[measure]["cost"]
        if self.funds < cost:
            return False
        self.funds -= cost
        self.poultry_investment[measure] += 1
        self.log_purchase(measure, cost)
        return True

    def poultry_net_income(self):
        return self.poultry_size * (POULTRY_INCOME_PER_UNIT - POULTRY_UPKEEP_PER_UNIT)

    # ---- F5 genetics ----
    def invest_genetics(self):
        if self.funds < GENETICS_COST:
            return False
        self.funds -= GENETICS_COST
        self.genetics_pending.append(GENETICS_MATURE_ROUNDS)
        self.log_purchase("genetics", GENETICS_COST)
        return True

    # ---- F13 supply chain ----
    def invest_supply_chain(self):
        if self.funds < SUPPLY_CHAIN_COST or self.supply_chain_investment >= SUPPLY_CHAIN_MAX_UNITS:
            return False
        self.funds -= SUPPLY_CHAIN_COST
        self.supply_chain_investment += 1
        self.log_purchase("supply", SUPPLY_CHAIN_COST)
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
        raw = season_for_round(self.round_number if round_number is None else round_number)[1]
        return raw * ranch_rules["season_swing"] / 100.0

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
        self.log_purchase("pivot", PLANT_PIVOT_COST)
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
        return HERD_GROWTH_COST + self.herd_size * ranch_rules["growth_slope"]

    def grow_herd(self):
        cost = self.grow_herd_cost()
        if self.funds < cost or self.cap_blocks_growth(herd=1):
            return False
        self.funds -= cost
        self.herd_size += 1
        self.log_purchase("herd", cost)
        return True

    def invest_decoupling(self, measure):
        cost = self.decoupling_cost(measure)
        if self.funds < cost:
            return False
        self.funds -= cost
        self.decoupling_investment[measure] += 1
        self.log_purchase(measure, cost)
        return True

    def pressure_fraction(self):
        """Fraction of income lost to market/regulatory pressure and
        degraded yields, scaling with sustained methane. Capped so income
        never fully vanishes — a bad strategy gets worse, not impossible."""
        return min(MAX_PRESSURE, self.methane / pressure_scale())

    def counterfactual_pressure_fraction(self):
        return min(MAX_PRESSURE, self.counterfactual_methane / pressure_scale())

    def counterfactual_score(self):
        """F1/F3/F13 — the pure-growth counterfactual's own score, using
        the exact same formula as score() so the two numbers are directly
        comparable."""
        return self.counterfactual_funds - self.counterfactual_methane * METHANE_PENALTY_WEIGHT

    def income_breakdown(self):
        """Every piece of one round's income, in the order the game applies them. advance_round()
        banks exactly breakdown["total"], so the F-6 inspector can never disagree with the game."""
        fraction = self.plant_based_fraction()
        plant_blend = (1 - fraction) + fraction * self.plant_income_multiplier()
        certification = self.certification_multiplier()
        welfare = self.welfare_multiplier()
        supply = self.supply_chain_multiplier()
        season = 1 + self.season_modifier()
        herd_base = self.herd_size * HERD_INCOME_PER_UNIT
        herd_income = self.herd_size * HERD_INCOME_PER_UNIT * plant_blend * certification * welfare
        poultry = self.poultry_net_income()
        satellite = self.satellite_net_income()
        label = self.label_multiplier()
        raw_income = (herd_income + poultry + satellite) * supply * season * label
        pressure = self.pressure_fraction()
        biogas = self.biogas_sales()
        return {
            "herd_base": herd_base, "plant_fraction": fraction, "plant_blend": plant_blend,
            "certification": certification, "welfare": welfare, "herd_income": herd_income,
            "poultry": poultry, "satellite": satellite, "supply": supply, "season": season, "label": label,
            "raw": raw_income, "pressure": pressure, "after_pressure": raw_income * (1 - pressure),
            "biogas": biogas, "total": raw_income * (1 - pressure) + biogas,
        }

    def advance_round(self):
        pressure = self.pressure_fraction()
        season = 1 + self.season_modifier()
        self.funds += self.income_breakdown()["total"]
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
        if self.hedge_rounds_left > 0:
            self.hedge_rounds_left -= 1
        if self.label_rounds_left > 0:
            self.label_rounds_left -= 1
        if (self.round_number + 1) % POLICY_EVENT_INTERVAL == 0:
            self.policy_offer_pending = True
            self.policy_offer = self.draw_policy_offer()

        self.round_number += 1
        prev_increment = (
            self.methane_history[-1] - self.methane_history[-2] if len(self.methane_history) >= 2 else 0.0
        )
        self.methane_history.append(self.methane)
        # F16 — curve flattening: this round added less than the last.
        self.just_flattened = (
            prev_increment > 0 and (self.methane_history[-1] - self.methane_history[-2]) < prev_increment - 1e-9
        )

        # GF-15 -- perfect round: this round's methane fell below the last one's AND
        # funds ended higher than they ended the previous round. Funds history is
        # kept for the highlights reel too (GF-29).
        prev_funds = self.funds_history[-1] if self.funds_history else None
        self.funds_history.append(self.funds)
        self.last_round_perfect = bool(
            self.just_flattened and prev_funds is not None and self.funds > prev_funds
        )
        self.just_streak_bonus = None
        if self.last_round_perfect:
            self.perfect_streak += 1
            self.best_perfect_streak = max(self.best_perfect_streak, self.perfect_streak)
            bonus = PERFECT_STREAK_BONUSES.get(self.perfect_streak)
            if bonus:
                self.funds += bonus
                self.funds_history[-1] = self.funds
                self.just_streak_bonus = (self.perfect_streak, bonus)
        else:
            self.perfect_streak = 0

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


def _store_rules():
    """Remembers the rules in this browser so a new farm starts on the same ones (F-1)."""
    _write_local_storage_item(RULES_STORAGE_KEY, json.dumps({n: v for n, v in ranch_rules.items()}))


def _load_stored_rules():
    raw = _read_local_storage_item(RULES_STORAGE_KEY)
    if not raw:
        return
    try:
        saved = json.loads(raw)
    except (ValueError, TypeError):
        return
    if not isinstance(saved, dict):
        return
    for name in RULE_SPECS:
        cleaned = clean_rule_value(name, saved.get(name))
        if cleaned is not None:
            ranch_rules[name] = cleaned


_load_stored_rules()
if rules_are_custom():
    farm = FarmState()  # the farm built above predates the stored rules


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
        f"{trend_markers_svg(xs, ys, history)}"
        f"</svg>"
    )


def trend_markers_svg(xs, ys, history):
    """F-14: shape markers on the methane trend graph, drawn always but only visible when the
    pattern-fills setting is on (style.css). A square marks a round that added LESS methane than
    the round before (the curve flattening), a circle any other round, and the latest round is a
    larger diamond. Shape, never colour, carries the meaning. Rounds are capped to the last 40 so
    a long game does not draw hundreds of tiny shapes."""
    n = len(history)
    first = max(0, n - 40)
    marks = []
    for i in range(first, n):
        x, y = xs[i], ys[i]
        if i == n - 1:
            marks.append(
                f'<polygon class="trend-marker trend-marker--latest" '
                f'points="{x:.1f},{y - 4:.1f} {x + 4:.1f},{y:.1f} {x:.1f},{y + 4:.1f} {x - 4:.1f},{y:.1f}" />'
            )
            continue
        flattened = i >= 2 and (history[i] - history[i - 1]) < (history[i - 1] - history[i - 2]) - 1e-9
        if flattened:
            marks.append(f'<rect class="trend-marker trend-marker--flat" x="{x - 2.5:.1f}" y="{y - 2.5:.1f}" width="5" height="5" />')
        else:
            marks.append(f'<circle class="trend-marker trend-marker--rise" cx="{x:.1f}" cy="{y:.1f}" r="2.5" />')
    return "".join(marks)


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
UNRANKED_COMPARE_NOTE = "Custom ranch rules: this run is unranked, so it is not compared with other farms."


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
    if rules_unranked():
        return  # F-1: custom-rule runs are not compared with other farms
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "herdCompare", None)
    if hook is not None:
        hook(float(farm.methane), farm.round_number)


def copy_result_fields():
    """Z-20: the fields shared/copy-result.js turns into one pasteable line,
    e.g. "Herd, 412 score, Careful Rancher, round 9, ...". Read by the page's
    own inline script through pyodide.globals when the shared Copy result
    button is pressed, so it always matches the farm as it stands."""
    methane_avoided = max(0.0, farm.counterfactual_methane - farm.methane)
    stats = [
        RATING_TITLES[rating_index()][0],
        f"round {farm.round_number}",
        f"{farm.decoupled_fraction() * 100:.0f}% decoupled",
        f"{methane_avoided:.0f} methane avoided",
    ]
    if rules_unranked():
        stats.append("custom rules, unranked")
    return {"game": "Herd", "score": round(farm.score()), "unit": "score", "stats": stats}


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
        policy_report_line(),
        real_world_comparison_message(),
    ]
    lines.insert(1, rating_message())
    body = "".join(f'<p class="status-line summary-line">{line}</p>' for line in lines)
    # F7: filled in by index.html's window.herdCompare() when the shared
    # stats endpoint (planning/TODO.md Z1) is reachable; otherwise this
    # fallback text simply stays.
    compare_text = UNRANKED_COMPARE_NOTE if rules_unranked() else COMPARE_FALLBACK
    return body + f'<p id="report-card-compare" class="status-line summary-line">{compare_text}</p>' + highlights_html()


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
    # F-1: a bigger opening purse would make this one free, so a custom-rules run cannot earn it.
    "score_400": lambda: farm.score() >= SCORE_400_TARGET and not rules_unranked(),
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
    # F-27: the remaining numeric achievements, so every card that is not earned shows how far along it is.
    "first_herd": lambda: (min(farm.herd_size, 1), 1),
    "first_decoupling": lambda: (min(sum(farm.decoupling_investment.values()), 1), 1),
    "all_three_measures": lambda: (sum(1 for m in DECOUPLING_MEASURES if farm.decoupling_investment[m] >= 1), len(DECOUPLING_MEASURES)),
    "sustainably_certified": lambda: (
        min(farm.certification_streak, CERTIFICATION_ROUNDS_REQUIRED), CERTIFICATION_ROUNDS_REQUIRED
    ),
    "plant_pioneer": lambda: (min(farm.plant_pivot_investment, 1), 1),
    "outperforming_baseline": lambda: (
        max(0, min(farm.round_number - 1, OUTPERFORMING_BASELINE_MIN_ROUND)), OUTPERFORMING_BASELINE_MIN_ROUND
    ),
    # Clean Operator is lost for this farm once pressure has gone past the limit: no progress line then.
    "clean_operator": lambda: (
        (min(farm.round_number, CLEAN_OPERATOR_MIN_ROUND), CLEAN_OPERATOR_MIN_ROUND)
        if farm.max_pressure_fraction_seen < CLEAN_OPERATOR_MAX_PRESSURE else None
    ),
}

# What one step of each progress readout counts, for the "N to go" line on a card.
ACHIEVEMENT_PROGRESS_UNITS = {
    "growing_operation": " herd units", "major_operation": " herd units", "first_herd": " herd unit",
    "quarter_decoupled": "%", "half_decoupled": "%", "fully_decoupled": "%", "half_plant_based": "%",
    "max_plant_pivot": "%", "real_world_match": "%", "decoupling_dividend": " points", "score_400": " points",
    "long_haul": " rounds", "century_farm": " rounds", "clean_operator": " rounds", "outperforming_baseline": " rounds",
    "sustainably_certified": " rounds", "all_three_measures": " measures", "first_decoupling": " investment",
    "plant_pioneer": " investment",
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
                "unit": ACHIEVEMENT_PROGRESS_UNITS.get(entry["id"], ""),
            }
        )
    return summary


def progress_percent(current, target):
    return 0.0 if target <= 0 else max(0.0, min(100.0, current / target * 100.0))


def progress_left_text(current, target, unit=""):
    """"N to go" with the unit the achievement counts in (the exact amount left, never rounded up)."""
    left = max(0, target - current)
    return f"{left}{unit} to go ({current} of {target})"


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
            # F-27: a mini bar and the exact amount left, shown on hover or keyboard focus (the
            # card takes focus, so a tap on a phone works too). The text is always in the page.
            card.setAttribute("tabindex", "0")
            card.setAttribute("aria-label", f"{entry['label']}: {progress_left_text(current, target, entry['unit'])}")
            bar = document.createElement("div")
            bar.className = "achievement-card-bar"
            bar.setAttribute("role", "presentation")
            fill = document.createElement("div")
            fill.className = "achievement-card-bar-fill"
            fill.style.width = f"{progress_percent(current, target):.0f}%"
            bar.appendChild(fill)
            card.appendChild(bar)
            left = document.createElement("p")
            left.className = "achievement-card-left"
            left.innerText = progress_left_text(current, target, entry["unit"])
            card.appendChild(left)

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
    _story_reach_all(_achievements_seen_ids)  # W1: a loaded save's earned chapters come back too


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


def _story_reach_all(earned_ids):
    """W1: unlocks the story chapter for every earned achievement (and the
    opening one) via the shared story-chapters.js. Idempotent and silent: no
    story script, or a chapter id it does not know, simply does nothing."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    story = getattr(window, "NoyvjStory", None)
    if story is None:
        return
    story.reach("begin")
    for achievement_id in sorted(earned_ids):
        story.reach(achievement_id)


def _check_new_achievements_for_toast():
    """Called after every player action that could change earned status
    (grow/invest/advance round) — never from render() itself, since
    load_state() also calls render() and a loaded save with several
    achievements already earned must not flood the player with toasts
    for all of them at once (see _seed_achievement_toast_baseline)."""
    global _achievements_seen_ids
    earned_now = set(achievement_ids_earned())
    _story_reach_all(earned_now)
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
        cow = document.getElementById(element_id)
        cow.hidden = farm.herd_size < threshold
        cow.title = pasture_cow_title(threshold)  # GF-13: hover shows the animal's name
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
    name, _raw = season_for_round(farm.round_number)
    mod = farm.season_modifier()
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
        f"({GENETICS_MATURE_ROUNDS} rounds each; a ring below counts each one down)"
    )


def biogas_message():
    surplus = max(0, farm.decoupling_investment["capture"] - CAPTURE_SELF_USE_UNITS)
    if surplus == 0:
        return (
            f"Biogas sales: the first {CAPTURE_SELF_USE_UNITS} Capture Systems cover on-farm energy; "
            "extra capacity is sold as biogas."
        )
    return f"Biogas sales: {surplus} surplus capture unit(s) earn {farm.biogas_sales():.1f} funds per round."


def policy_option_blurb(option_id):
    """What the option would do right now, with today's numbers."""
    spec = POLICY_OPTIONS[option_id]
    if option_id == "carbon_credit":
        return f"{farm.carbon_credit_value()} funds now ({spec['blurb']})"
    if option_id == "welfare_grant":
        return f"{farm.welfare_grant_value()} funds now ({spec['blurb']})"
    return spec["blurb"]


def policy_active_message():
    parts = []
    if farm.subsidy_rounds_left > 0:
        parts.append(f"decoupling subsidy, {farm.subsidy_rounds_left} rounds left")
    if farm.hedge_rounds_left > 0:
        parts.append(f"feed-price hedge, {farm.hedge_rounds_left} rounds left")
    if farm.label_rounds_left > 0:
        parts.append(f"organic label trial, {farm.label_rounds_left} rounds left")
    return ("Active: " + "; ".join(parts) + ".") if parts else ""


def policy_message():
    if farm.policy_offer_pending:
        first, second = farm.current_policy_offer()
        return (
            f"Policy advisor: pick one. {POLICY_OPTIONS[first]['label']}: {policy_option_blurb(first)}. "
            f"Or {POLICY_OPTIONS[second]['label']}: {policy_option_blurb(second)}."
        )
    return policy_active_message()


def policy_real_message():
    if not farm.policy_offer_pending:
        return ""
    return " ".join(POLICY_OPTIONS[o]["real"] for o in farm.current_policy_offer())


def policy_history_html():
    if not farm.policy_history:
        return (
            f"<li>No advisor offers taken yet. An advisor visits every {POLICY_EVENT_INTERVAL} rounds "
            "with two options from a pool of six.</li>"
        )
    rows = []
    for rnd, taken, other in reversed(farm.policy_history):
        t, o = POLICY_OPTIONS[taken], POLICY_OPTIONS[other]
        rows.append(
            f"<li>Round {rnd}: took {t['label']} ({t['tag']}), passed on {o['label']} ({o['tag']}).</li>"
        )
    return "".join(rows)


def policy_report_line():
    if not farm.policy_history:
        return "Advisor choices: none yet."
    names = ", ".join(POLICY_OPTIONS[t]["label"] for _r, t, _o in farm.policy_history[-4:])
    return f"Advisor choices ({len(farm.policy_history)} so far, latest last): {names}."


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
    # F-14: the two small bars (welfare out of 100, supply chain out of its maximum).
    document.getElementById("welfare-bar").style.width = f"{farm.welfare() / WELFARE_MAX * 100:.0f}%"
    document.getElementById("supply-chain-bar").style.width = (
        f"{farm.supply_chain_investment / SUPPLY_CHAIN_MAX_UNITS * 100:.0f}%"
    )
    document.getElementById("variation-checkbox").checked = farm.variation_enabled
    document.getElementById("cap-checkbox").checked = farm.regional_cap_enabled
    document.getElementById("cap-display").innerText = (
        f"Regional cap: {farm.methane_this_round():.1f} of {REGIONAL_CAP:.0f} methane/round. Growth is blocked past the cap."
        if farm.regional_cap_enabled else "Regional methane cap is off."
    )
    # F27 policy advisor
    document.getElementById("policy-panel").hidden = not farm.policy_offer_pending
    document.getElementById("policy-display").innerText = policy_message()
    document.getElementById("policy-real-display").innerText = policy_real_message()
    for slot, button_id in enumerate(("policy-subsidy-button", "policy-cash-button")):
        option = POLICY_OPTIONS[farm.current_policy_offer()[slot]]
        button = document.getElementById(button_id)
        button.innerText = f"Take: {option['label']} ({option['tag']})"
        button.title = option["real"]
    document.getElementById("policy-history-list").innerHTML = policy_history_html()
    render_succession()
    render_satellite()
    document.getElementById("tagline-display").innerText = tagline_message()

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


SATELLITE_LEVER_KEYS = {
    "open_satellite": "satellite_open",
    "grow_satellite": "satellite_grow",
    "retrofit_satellite": "satellite_retrofit",
}


def _satellite_action_cost(action):
    return {
        "open_satellite": SATELLITE_OPEN_COST,
        "grow_satellite": farm.satellite_grow_cost(),
        "retrofit_satellite": SATELLITE_RETROFIT_COST,
    }[action]


def _make_satellite_handler(action, button_id):
    def handler(event=None):
        def do_buy():
            if getattr(farm, action)():
                _pulse(button_id)
            render()

        _guarded_purchase(LEVER_LABELS[SATELLITE_LEVER_KEYS[action]], _satellite_action_cost(action), do_buy)
    return handler


# R-23: the sentence under the title reacts to how the session is going.
TAGLINE_DEFAULT = "Grow a farm. Herd size and methane emissions are coupled by default — decoupling them takes deliberate investment."
TAGLINE_PRESSURE = "Methane is building, and the market is starting to push back. Growth is beginning to cost more than it earns."
TAGLINE_HALF = "Half the coupling is gone: the same herd now emits far less. Keep going, or start to diversify."
TAGLINE_CERTIFIED = "A certified farm. Growing the herd and cutting methane are no longer pulling against each other."


def tagline_message():
    """One sentence for the current state, in priority order: certified,
    then decoupled by half or more, then methane pressure past the callout
    level, else the opening line."""
    if farm.certified:
        return TAGLINE_CERTIFIED
    if farm.decoupled_fraction() >= HALF_DECOUPLED_CALLOUT_THRESHOLD:
        return TAGLINE_HALF
    if farm.pressure_fraction() >= PRESSURE_CALLOUT_THRESHOLD:
        return TAGLINE_PRESSURE
    return TAGLINE_DEFAULT


# ===========================================================================
# GF-16 breed collection, GF-5 decoupling combos, GF-22 rating titles,
# GF-29 highlights reel, F-13 lever efficiency, F-24 cap headroom and F-17
# lever history. All of it is derived from state that already exists (plus the
# funds history and purchase log on FarmState) except the two collections,
# which are module-level like the succession perks: a handover restarts the
# farm but never empties the shelf or the combo book.
# ===========================================================================
COMBO_REWARD_FUNDS = 20
RATING_FIRST_MESSAGE = "Advance a round to start your highlight reel."

# GF-16: breeds are a collector shelf. Each is earned once, for good, by reaching a
# state on any farm. The last one is hidden until earned (its silhouette shows a
# rumour, not the rule), but every breed can be earned in a normal game.
BREEDS = [
    {"id": "clover_calf", "label": "Clover Calf", "glyph": "\U0001F42E",
     "how": "Own your first animal.", "check": lambda f: f.herd_size >= 1},
    {"id": "brindle_belle", "label": "Brindle Belle", "glyph": "\U0001F404",
     "how": "Grow the herd to 10.", "check": lambda f: f.herd_size >= 10},
    {"id": "prairie_patriarch", "label": "Prairie Patriarch", "glyph": "\U0001F402",
     "how": "Grow the herd to 25.", "check": lambda f: f.herd_size >= 25},
    {"id": "sage_grazer", "label": "Sage Grazer", "glyph": "\U0001F33E",
     "how": "Buy 3 Feed Additives.", "check": lambda f: f.decoupling_investment["feed"] >= 3},
    {"id": "roomy_ruminant", "label": "Roomy Ruminant", "glyph": "\U0001F6A7",
     "how": "Buy 3 Herd Caps.", "check": lambda f: f.decoupling_investment["caps"] >= 3},
    {"id": "biogas_bessie", "label": "Biogas Bessie", "glyph": "♻️",
     "how": "Buy 3 Capture Systems.", "check": lambda f: f.decoupling_investment["capture"] >= 3},
    {"id": "meadow_mooncow", "label": "Meadow Mooncow", "glyph": "\U0001F33F",
     "how": "Shift 20% of output to plant-based (4 Pivots).", "check": lambda f: f.plant_pivot_investment >= 4},
    {"id": "coop_champion", "label": "Coop Champion", "glyph": "\U0001F414",
     "how": "Raise a flock of 5.", "check": lambda f: f.poultry_size >= 5},
    {"id": "hilltop_wanderer", "label": "Hilltop Wanderer", "glyph": "⛰️",
     "how": "Grow the satellite herd to 3.", "check": lambda f: f.satellite_open and f.satellite_size >= 3},
    {"id": "certified_jersey", "label": "Certified Jersey", "glyph": "\U0001F3C5",
     "how": "Earn sustainable certification.", "check": lambda f: f.certified},
    {"id": "methane_eater_cow", "label": "Methane-Eater Cow", "glyph": "✨", "hidden": True,
     "hint": "Rumoured: a herd that is both very clean and very well cared for.",
     "how": "Coupling ratio under 0.25 with herd welfare at 90 or more.",
     "check": lambda f: f.coupling_ratio() < 0.25 and f.welfare() >= 90},
]

# GF-5: named combos of levers held together, each paid once (to the real farm only,
# like the streak bonuses). The book shows the rule for every entry but hides the
# name until it is found.
COMBOS = [
    {"id": "circular_barn", "label": "Circular Barn", "how": "3 Capture Systems and 2 Feed Additives.",
     "check": lambda f: f.decoupling_investment["capture"] >= 3 and f.decoupling_investment["feed"] >= 2},
    {"id": "happy_herd", "label": "Happy Herd", "how": "Herd welfare 70 or more and 2 Herd Caps.",
     "check": lambda f: f.welfare() >= 70 and f.decoupling_investment["caps"] >= 2},
    {"id": "green_gourmet", "label": "Green Gourmet", "how": "3 Plant-Based Pivots and 2 Processing & Distribution.",
     "check": lambda f: f.plant_pivot_investment >= 3 and f.supply_chain_investment >= 2},
    {"id": "full_stack", "label": "Full Stack", "how": "At least one of every lever on the main farm: Feed, Caps, Capture, Pivot, Breeding (matured) and Processing.",
     "check": lambda f: (
         all(f.decoupling_investment[m] >= 1 for m in DECOUPLING_MEASURES)
         and f.plant_pivot_investment >= 1 and f.genetics_active >= 1 and f.supply_chain_investment >= 1)},
    {"id": "poultry_partners", "label": "Poultry Partners", "how": "A flock of 3 with Litter Management and a Biofilter.",
     "check": lambda f: f.poultry_size >= 3 and f.poultry_investment["litter"] >= 1 and f.poultry_investment["biofilter"] >= 1},
    {"id": "twin_barns", "label": "Twin Barns", "how": "Open the satellite farm and retrofit it 3 times.",
     "check": lambda f: f.satellite_open and f.satellite_retrofits >= 3},
    {"id": "slow_burn", "label": "Slow Burn", "how": "Two breeding lines matured.",
     "check": lambda f: f.genetics_active >= 2},
    {"id": "biogas_baron", "label": "Biogas Baron", "how": "5 Capture Systems, so surplus gas is sold.",
     "check": lambda f: f.decoupling_investment["capture"] >= 5},
]

breeds_collected = []
combos_found = []


def _sync_collection(award=True):
    """Marks every breed and combo the current farm qualifies for. With award=True
    (normal play) a new combo pays its reward and a toast names what was found;
    with award=False (loading a save) it only records, so a load never changes
    funds. Returns the list of newly found labels."""
    found = []
    for breed in BREEDS:
        if breed["id"] not in breeds_collected and breed["check"](farm):
            breeds_collected.append(breed["id"])
            found.append(f"new breed {breed['label']}")
    for combo in COMBOS:
        if combo["id"] not in combos_found and combo["check"](farm):
            combos_found.append(combo["id"])
            if award:
                farm.funds += COMBO_REWARD_FUNDS
            found.append(f"combo {combo['label']}" + (f" (+{COMBO_REWARD_FUNDS} funds)" if award else ""))
    if award and found:
        _display_milestone_toast("\U0001F4D6 Collection: " + ", ".join(found) + ".")
    return found


def _valid_ids(raw, catalog):
    if not isinstance(raw, list):
        return []
    known = {entry["id"] for entry in catalog}
    result = []
    for value in raw:
        if isinstance(value, str) and value in known and value not in result:
            result.append(value)
    return result


def breed_shelf_html():
    cards = []
    for breed in BREEDS:
        earned = breed["id"] in breeds_collected
        hidden = breed.get("hidden", False)
        classes = "breed-card"
        if earned:
            classes += " breed-card--earned" + (" breed-card--legend" if hidden else "")
            name, detail, glyph = breed["label"], breed["how"], breed["glyph"]
        else:
            classes += " breed-card--locked"
            name = "???" if hidden else breed["label"]
            detail = breed["hint"] if hidden else breed["how"]
            glyph = "❔" if hidden else breed["glyph"]
        status = "collected" if earned else "not collected yet"
        cards.append(
            f'<li class="{classes}"><span class="breed-glyph" aria-hidden="true">{glyph}</span>'
            f'<span class="breed-name">{name}</span>'
            f'<span class="breed-detail">{detail}</span>'
            f'<span class="sr-only">{status}</span></li>'
        )
    return "".join(cards)


def combo_book_html():
    rows = []
    for combo in COMBOS:
        found = combo["id"] in combos_found
        name = combo["label"] if found else "???"
        mark = f"found, paid {COMBO_REWARD_FUNDS} funds" if found else "not found yet"
        classes = "combo-card combo-card--found" if found else "combo-card combo-card--locked"
        rows.append(
            f'<li class="{classes}"><span class="combo-name">{name}</span>'
            f'<span class="combo-detail">{combo["how"]}</span>'
            f'<span class="sr-only">{mark}</span></li>'
        )
    return "".join(rows)


def collection_summary_message():
    return (
        f"Breeds {len(breeds_collected)}/{len(BREEDS)}  |  Combos {len(combos_found)}/{len(COMBOS)}  |  "
        f"Best perfect-round streak {farm.best_perfect_streak}"
    )


# GF-22: a rating ladder, highest rung currently satisfied wins. Pure functions of state.
def _decoupled_at_least(share):
    # Epsilon: ten 1% steps of float arithmetic must still count as exactly 10%.
    return farm.decoupled_fraction() >= share - 1e-9


def _score_beat_pct():
    baseline = farm.counterfactual_score()
    if abs(baseline) < 1e-9:
        return 0.0
    return (farm.score() - baseline) / abs(baseline) * 100


RATING_TITLES = [
    ("Hobby Farmer", "\U0001F9D1‍\U0001F33E", "Start a farm.", lambda: True),
    ("Feed Hand", "\U0001F33E", "Decouple 10% below baseline.", lambda: _decoupled_at_least(0.10)),
    ("Careful Rancher", "\U0001F920", "Decouple 25% below baseline.", lambda: _decoupled_at_least(0.25)),
    ("Ahead of the Curve", "\U0001F4C8", "Decouple 40% and score above the pure-growth baseline.",
     lambda: _decoupled_at_least(0.40) and farm.score() > farm.counterfactual_score()),
    ("Certified Steward", "\U0001F3C5", "Earn sustainable certification.", lambda: farm.certified),
    ("Methane Cutter", "✂️", "Decouple 70% and beat the baseline score by 25%.",
     lambda: _decoupled_at_least(0.70) and _score_beat_pct() >= 25),
    ("Decoupling Legend", "\U0001F451", "Decouple 80%, certified, and beat the baseline score by 50%.",
     lambda: farm.certified and _decoupled_at_least(0.80) and _score_beat_pct() >= 50),
]


def rating_index():
    current = 0
    for index, (_name, _glyph, _need, check) in enumerate(RATING_TITLES):
        if check():
            current = index
    return current


def rating_message():
    index = rating_index()
    name, glyph, _need, _check = RATING_TITLES[index]
    text = f"{glyph} Rating: {name}."
    if index + 1 < len(RATING_TITLES):
        next_name, _g, need, _c = RATING_TITLES[index + 1]
        text += f" Next, {next_name}: {need}"
    else:
        text += " The top of the ladder."
    return text


def streak_message():
    streak = farm.perfect_streak
    upcoming = [length for length in sorted(PERFECT_STREAK_BONUSES) if length > streak]
    text = f"\U0001F525 Perfect-round streak: {streak} (best {farm.best_perfect_streak})."
    if upcoming:
        text += f" Bonus at {upcoming[0]}: +{PERFECT_STREAK_BONUSES[upcoming[0]]} funds."
    return text + " A perfect round adds less methane than the last and still ends with more funds."


# GF-29: three screenshot-friendly lines from the per-round histories.
def highlights_lines():
    gains = [
        (index, farm.funds_history[index] - farm.funds_history[index - 1])
        for index in range(1, len(farm.funds_history))
        if farm.funds_history[index] is not None and farm.funds_history[index - 1] is not None
    ]
    increments = [
        farm.methane_history[index] - farm.methane_history[index - 1]
        for index in range(1, len(farm.methane_history))
    ]
    if not increments:
        return [RATING_FIRST_MESSAGE]
    lines = []
    if gains:
        index, gain = max(gains, key=lambda pair: pair[1])
        lines.append(f"Biggest single round: round {index}, {gain:+.0f} funds.")
    drops = [(i + 2, increments[i] - increments[i + 1]) for i in range(len(increments) - 1)]
    drops = [pair for pair in drops if pair[1] > 1e-9]
    if drops:
        round_number, drop = max(drops, key=lambda pair: pair[1])
        lines.append(f"Best methane cut in one round: round {round_number}, {drop:.1f} less than the round before.")
    else:
        lines.append("Best methane cut in one round: none yet. Invest in decoupling to bend the curve.")
    flock = f" plus a flock of {farm.poultry_size}" if farm.poultry_size else ""
    lines.append(
        f"Herd peaked at {farm.herd_size} animals{flock}; longest perfect-round streak {farm.best_perfect_streak}."
    )
    return lines


def highlights_html():
    items = "".join(f"<li>{line}</li>" for line in highlights_lines())
    return f'<div class="highlights-reel"><p class="meter-label">Highlights</p><ul>{items}</ul></div>'


# F-13: funds per methane saved, for the lever list.
EFFICIENCY_NONE = "No methane saved at your current herd."


def lever_efficiency_message(key, cost):
    saved = farm.methane_saved_by(key)
    if saved <= 1e-9:
        return EFFICIENCY_NONE
    return f"Saves {saved:.2f} methane/round: about {cost / saved:.1f} funds per methane saved."


def _lever_cost(key):
    if key in DECOUPLING_MEASURES:
        return farm.decoupling_cost(key)
    if key == "pivot":
        return PLANT_PIVOT_COST
    return POULTRY_MEASURES[key]["cost"]


# F-24: headroom under the regional cap.
def cap_headroom_message():
    if not farm.regional_cap_enabled:
        return ""
    headroom = farm.cap_headroom()
    rounds = farm.rounds_until_cap()
    if rounds == 0:
        tail = "The next animal is blocked. Decouple to make room."
    elif rounds is None:
        tail = "The herd is not growing, so the cap is not close."
    else:
        tail = (
            f"At your pace so far ({farm.growth_pace():.1f} animals a round) you must decouple within "
            f"{rounds} round{'s' if rounds != 1 else ''}."
        )
    return f"Headroom: {headroom:.1f} methane/round free under the cap. {tail}"


# F-17: lever history log with a filter.
lever_history_filter = "all"
LEVER_HISTORY_SHOWN = 40


def lever_history_html():
    entries = [e for e in farm.lever_log if lever_history_filter in ("all", e[1])]
    if not entries:
        return "<li>Nothing bought yet.</li>"
    shown = entries[::-1][:LEVER_HISTORY_SHOWN]
    rows = "".join(
        f"<li>Round {r}: bought {LEVER_LABELS.get(k, k)} (-{c:g})</li>" for r, k, c in shown
    )
    if len(entries) > len(shown):
        rows += f"<li>and {len(entries) - len(shown)} earlier</li>"
    return rows


def on_lever_history_filter(event=None):
    global lever_history_filter
    value = getattr(document.getElementById("lever-history-filter"), "value", "all")
    lever_history_filter = value if value == "all" or value in LEVER_LABELS else "all"
    render_progress_extras()


def render_progress_extras():
    """Everything the new collector and progress features draw. Runs from render()."""
    document.getElementById("rating-display").innerText = rating_message()
    streak = document.getElementById("streak-display")
    streak.innerText = streak_message()
    streak.hidden = farm.round_number <= 1
    document.getElementById("collection-summary").innerText = collection_summary_message()
    document.getElementById("breed-shelf-grid").innerHTML = breed_shelf_html()
    document.getElementById("combo-book-list").innerHTML = combo_book_html()
    document.getElementById("lever-history-list").innerHTML = lever_history_html()
    cap_text = cap_headroom_message()
    meter = document.getElementById("cap-headroom-meter")
    meter.hidden = not cap_text
    document.getElementById("cap-headroom-display").innerText = cap_text
    document.getElementById("cap-headroom-bar").style.width = (
        f"{min(1.0, farm.methane_this_round() / REGIONAL_CAP) * 100:.0f}%"
    )
    for key in ("feed", "caps", "capture", "pivot", "litter", "biofilter"):
        element = document.getElementById(f"{key}-efficiency")
        element.innerText = lever_efficiency_message(key, _lever_cost(key))


# ===========================================================================
# Round-4 batch (planning/TODO.md "GF + F. Herd"): F-19 bulk buying, F-20 round-delta
# chips, GF-18 undo last round, F-21 season calendar, F-22 poultry vs cattle card,
# F-23 breeding rings, GF-13 named cows and hall of fame, F-28 pace note.
# ===========================================================================

# ---- F-19 bulk-buy stepper -------------------------------------------------------------
bulk_mode = 1
BULK_BUTTON_IDS = {1: "bulk-1-button", 5: "bulk-5-button", "max": "bulk-max-button"}
BULK_HINT = "Tip: x5 and Max buy several units at once; the button shows the total cost first."


def bulk_button_label(key, name, single_cost, cost_format):
    """(label, disabled) for a Grow Herd or decoupling button under the current bulk mode.
    Mode 1 keeps the exact old label and rules."""
    units, total = farm.bulk_plan(key, bulk_mode)
    single = f"{name} ({format(single_cost, cost_format)})"
    if bulk_mode == 1:
        return single, units == 0
    if units == 0:
        if key in DECOUPLING_MEASURES and farm._efficiency_coupling_ratio() <= MIN_COUPLING_RATIO + 1e-9:
            return f"{name} (maxed out)", True
        return single, True
    return f"{name} x{units} ({total:g} total)", False


def bulk_note_message():
    if bulk_mode == 1:
        return BULK_HINT
    units, total = farm.bulk_plan("herd", bulk_mode)
    if units == 0:
        return "Grow Herd: nothing is affordable (or the cap blocks it) at this step size."
    before = farm.methane_this_round()
    after = before + units * farm.coupling_ratio()
    return (
        f"Grow Herd x{units} costs {total:g} in total; methane/round {before:.2f} → {after:.2f} ↑ "
        f"(herd {farm.herd_size} → {farm.herd_size + units})."
    )


def render_bulk_stepper():
    for mode, element_id in BULK_BUTTON_IDS.items():
        button = document.getElementById(element_id)
        selected = mode == bulk_mode
        button.setAttribute("aria-pressed", "true" if selected else "false")
        if selected:
            button.classList.add("selected")
        else:
            button.classList.remove("selected")
    document.getElementById("bulk-note").innerText = bulk_note_message()


def _make_bulk_handler(mode):
    def handler(event=None):
        global bulk_mode
        bulk_mode = mode
        render()
    return handler


# ---- F-20 round-delta chips ------------------------------------------------------------
last_deltas = {}
delta_pinned = set()
delta_faded = False
delta_token = 0


def round_deltas(funds_before, methane_before, welfare_before, pressure_before):
    """How the four headline numbers moved over the round that just finished."""
    return {
        "funds": farm.funds - funds_before,
        "methane": farm.methane - methane_before,
        "welfare": farm.welfare() - welfare_before,
        "pressure": (farm.pressure_fraction() - pressure_before) * 100,
    }


def delta_chip_text(key, delta):
    """Shape plus sign plus words, never colour alone: up triangle, down triangle or a square for no change."""
    arrow = "▲" if delta > 1e-9 else ("▼" if delta < -1e-9 else "■")
    if key == "funds":
        return f"{arrow} Funds {delta:+.0f}"
    if key == "methane":
        return f"{arrow} Methane {delta:+.1f}"
    if key == "welfare":
        return f"{arrow} Welfare {delta:+.0f}"
    return f"{arrow} Pressure {delta:+.1f} pts"


def _delta_is_good(key, delta):
    if abs(delta) <= 1e-9:
        return None
    return delta > 0 if key in ("funds", "welfare") else delta < 0


def render_delta_chips():
    strip = document.getElementById("round-delta-strip")
    strip.hidden = not last_deltas
    for key in DELTA_KEYS:
        chip = document.getElementById(f"delta-chip-{key}")
        if key not in last_deltas:
            chip.hidden = True
            continue
        delta = last_deltas[key]
        chip.hidden = False
        chip.innerText = delta_chip_text(key, delta)
        pinned = key in delta_pinned
        chip.setAttribute("aria-pressed", "true" if pinned else "false")
        chip.title = "Pinned: click to let it fade." if pinned else "Click to pin this change so it stays."
        good = _delta_is_good(key, delta)
        for name, on in (
            ("delta-chip--good", good is True), ("delta-chip--bad", good is False),
            ("delta-chip--pinned", pinned), ("delta-chip--faded", delta_faded and not pinned),
        ):
            if on:
                chip.classList.add(name)
            else:
                chip.classList.remove(name)


def _schedule_delta_fade():
    global delta_token, delta_faded
    delta_token += 1
    delta_faded = False
    token = delta_token

    def _fade(*args):
        global delta_faded
        if token == delta_token:
            delta_faded = True
            render_delta_chips()
        proxy.destroy()

    proxy = create_proxy(_fade)
    setTimeout(proxy, DELTA_FADE_MS)


def _make_delta_pin_handler(key):
    def handler(event=None):
        if key in delta_pinned:
            delta_pinned.discard(key)
        else:
            delta_pinned.add(key)
        render_delta_chips()
    return handler


# ---- GF-18 undo the last round ----------------------------------------------------------
UNDO_NOTE_READY = (
    f"Rewind to just before the last Advance Round. Once per game, costs {UNDO_PENALTY_FUNDS} funds; "
    "purchases made since are undone too."
)


def can_undo():
    snapshot = farm.undo_snapshot
    return (
        not farm.undo_used and isinstance(snapshot, dict)
        and snapshot.get("funds", 0) >= UNDO_PENALTY_FUNDS
    )


def undo_note_message():
    if farm.undo_used:
        return "You have used this game's undo."
    if farm.undo_snapshot is None:
        return f"Undo is ready after you advance a round (once per game, costs {UNDO_PENALTY_FUNDS} funds)."
    if not can_undo():
        return f"Not enough funds before that round to pay the {UNDO_PENALTY_FUNDS}-fund undo fee."
    return UNDO_NOTE_READY


def render_undo():
    document.getElementById("undo-round-button").disabled = not can_undo()
    document.getElementById("undo-note").innerText = undo_note_message()


def undo_last_round():
    """Puts the farm back to the moment before the last Advance Round and charges the fee.
    Succession (generation, legacy points and perks, hall of fame) and collected breeds are
    kept as they are now; everything on the farm itself comes from the snapshot."""
    global generation, legacy_points, legacy_perks, hall_of_fame, last_deltas, delta_faded
    if not can_undo():
        return False
    snapshot = farm.undo_snapshot
    kept = (generation, legacy_points, dict(legacy_perks), list(hall_of_fame), list(breeds_collected))
    load_state(snapshot)
    generation, legacy_points, legacy_perks, hall_of_fame = kept[0], kept[1], kept[2], kept[3]
    for breed_id in kept[4]:
        if breed_id not in breeds_collected:
            breeds_collected.append(breed_id)
    farm.funds -= UNDO_PENALTY_FUNDS
    if farm.funds_history:
        farm.funds_history[-1] = farm.funds
    farm.undo_used = True
    farm.undo_snapshot = None
    farm.just_hit_callout = None
    last_deltas = {}
    delta_faded = False
    render()
    return True


def on_undo_round(event=None):
    if not can_undo():
        return
    _confirm_dialog_ask(
        action_id="herd-undo-round",
        message=(
            f"Rewind the last round? The farm goes back to just before you pressed Advance Round, "
            f"anything bought since is undone, and it costs {UNDO_PENALTY_FUNDS} funds. "
            "You can do this once per game."
        ),
        confirm_label="Rewind",
        on_confirm=undo_last_round,
        allow_skip=False,
    )


# ---- F-21 season calendar --------------------------------------------------------------
CALENDAR_ROUNDS = 12
SEASON_MARKS = {-0.10: "▼▼", -0.05: "▼", 0.0: "■", 0.05: "▲", 0.10: "▲▲"}


def season_calendar_cells(count=CALENDAR_ROUNDS):
    """The next `count` rounds starting with the current one: each cell's season name,
    income swing and whether a plant-based demand surge is running."""
    cells = []
    for number in range(farm.round_number, farm.round_number + count):
        name, raw = season_for_round(number)
        cells.append({
            "round": number, "name": name, "mod": farm.season_modifier(number), "raw": raw,
            "surge": demand_surge_active(number),
        })
    return cells


def season_calendar_html():
    items = []
    for cell in season_calendar_cells():
        mark = SEASON_MARKS.get(cell["raw"], "■")
        tone = "up" if cell["mod"] > 0 else ("down" if cell["mod"] < 0 else "flat")
        surge = '<span class="season-surge" aria-hidden="true">\U0001F331</span>' if cell["surge"] else ""
        label = f"Round {cell['round']}: {cell['name']}, income {cell['mod'] * 100:+.0f}%"
        if cell["surge"]:
            label += ", plant-based demand surge"
        now = " season-cell--now" if cell["round"] == farm.round_number else ""
        items.append(
            f'<li class="season-cell season-cell--{tone}{now}" title="{label}" aria-label="{label}">'
            f'<span class="season-round">R{cell["round"]}</span>'
            f'<span class="season-mark" aria-hidden="true">{mark}</span>'
            f'<span class="season-pct">{cell["mod"] * 100:+.0f}%</span>{surge}</li>'
        )
    return "".join(items)


def render_season_calendar():
    calendar = document.getElementById("season-calendar")
    calendar.hidden = not farm.variation_enabled
    calendar.innerHTML = season_calendar_html() if farm.variation_enabled else ""


# ---- F-22 poultry vs cattle -------------------------------------------------------------
def poultry_compare_rows():
    """Per-unit, per-round figures side by side: (label, cattle text, poultry text)."""
    cattle_income = HERD_INCOME_PER_UNIT * farm.welfare_multiplier() * farm.certification_multiplier()
    poultry_income = POULTRY_INCOME_PER_UNIT - POULTRY_UPKEEP_PER_UNIT
    cattle_ratio = farm.coupling_ratio()
    poultry_ratio = farm.poultry_coupling_ratio()
    return [
        ("Income per unit (before pressure)", f"{cattle_income:.2f}", f"{poultry_income:.2f} after upkeep"),
        ("Methane-equivalent per unit", f"{cattle_ratio:.2f}", f"{poultry_ratio:.2f}"),
        ("Income per methane", f"{cattle_income / cattle_ratio:.1f}", f"{poultry_income / poultry_ratio:.1f}"),
        (
            "Welfare effect",
            f"Feed +{WELFARE_FEED:g}, Caps +{WELFARE_CAPS:g}, Breeding +{WELFARE_GENETICS:g} per lever",
            "None: flock levers do not move the welfare score",
        ),
    ]


def poultry_compare_html():
    rows = "".join(
        f"<tr><th scope=\"row\">{label}</th><td>{cattle}</td><td>{poultry}</td></tr>"
        for label, cattle, poultry in poultry_compare_rows()
    )
    return (
        '<table class="compare-table"><caption>Cattle against poultry, per unit per round</caption>'
        '<thead><tr><th scope="col"></th><th scope="col">\U0001F404 Cattle</th>'
        f'<th scope="col">\U0001F414 Poultry</th></tr></thead><tbody>{rows}</tbody></table>'
    )


# ---- F-23 breeding rings ----------------------------------------------------------------
def genetics_rings_html():
    """One small ring per breeding line still maturing: a quarter of the ring per round
    done, the rounds left written in the middle (so it is never a colour-only cue)."""
    if not farm.genetics_pending:
        return '<span class="ring-empty">No line maturing</span>'
    radius = 11
    circumference = 2 * math.pi * radius
    rings = []
    for left in sorted(farm.genetics_pending):
        left = max(0, min(GENETICS_MATURE_ROUNDS, left))
        done = (GENETICS_MATURE_ROUNDS - left) / GENETICS_MATURE_ROUNDS
        label = f"Breeding line: {left} round{'s' if left != 1 else ''} left of {GENETICS_MATURE_ROUNDS}"
        rings.append(
            f'<svg class="breed-ring" viewBox="0 0 30 30" width="30" height="30" role="img" aria-label="{label}">'
            f'<title>{label}</title>'
            f'<circle class="breed-ring-track" cx="15" cy="15" r="{radius}" fill="none" stroke-width="3"/>'
            f'<circle class="breed-ring-fill" cx="15" cy="15" r="{radius}" fill="none" stroke-width="3" '
            f'stroke-dasharray="{done * circumference:.2f} {circumference:.2f}" transform="rotate(-90 15 15)"/>'
            f'<text x="15" y="19" text-anchor="middle" class="breed-ring-text">{left}</text></svg>'
        )
    return "".join(rings)


# ---- GF-13 named cows and the hall of fame ----------------------------------------------
hall_of_fame = []  # [name, rounds served, generation], longest first


def cow_name(index, gen=None):
    """The name of herd unit `index` (0 = the first animal bought) in a generation. Fixed by
    position, so the same after any reload; a different generation starts further along the list."""
    gen = generation if gen is None else gen
    position = index + (gen - 1) * 7
    lap, slot = divmod(position, len(COW_NAMES))
    name = COW_NAMES[slot]
    if lap == 0:
        return name
    numerals = ["", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
    return f"{name} {numerals[lap] if lap < len(numerals) else lap + 1}"


def cow_roster():
    """(name, rounds served) for every herd unit, oldest first."""
    return [
        (cow_name(i), max(0, farm.round_number - bought))
        for i, bought in enumerate(farm.herd_unit_rounds())
    ]


def retire_herd_to_hall():
    """Called on handover: the longest-serving animals of the outgoing farm join the hall of fame."""
    roster = [(name, served) for name, served in cow_roster() if served > 0]
    roster.sort(key=lambda entry: -entry[1])
    for name, served in roster[:HALL_PER_HANDOVER]:
        hall_of_fame.append([name, served, generation])
    hall_of_fame.sort(key=lambda entry: (-entry[1], entry[2]))
    del hall_of_fame[HALL_OF_FAME_SIZE:]


def hall_of_fame_html():
    if not hall_of_fame:
        return (
            "<li>No animals retired yet. Hand a certified farm to the next generation and its "
            "longest-serving animals are honoured here.</li>"
        )
    return "".join(
        f"<li>{html.escape(str(name))}: {served} round{'s' if served != 1 else ''} "
        f"(generation {gen})</li>"
        for name, served, gen in hall_of_fame
    )


def pasture_cow_title(threshold):
    """Hover text for a pasture cow: the animal that revealed it (the threshold-th unit)."""
    roster = cow_roster()
    if len(roster) < threshold:
        return ""
    name, served = roster[threshold - 1]
    return f"{name}, animal #{threshold}, {served} round{'s' if served != 1 else ''} on the farm"


# ---- F-28 pace note and save nudge ------------------------------------------------------
session_started = time.time()
session_rounds = 0


def pace_note_message():
    if session_rounds <= 0:
        return ""
    minutes = max(0, int((time.time() - session_started) // 60))
    return (
        f"This sitting: {session_rounds} round{'s' if session_rounds != 1 else ''}, "
        f"about {minutes} min."
    )


def save_nudge_message():
    """A gentle prompt every SAVE_NUDGE_EVERY rounds played in one sitting, else empty."""
    if session_rounds > 0 and session_rounds % SAVE_NUDGE_EVERY == 0:
        return (
            f"{session_rounds} rounds this sitting. A good moment to save and take a break: "
            "the Save button keeps this farm safe."
        )
    return ""


def render_round_extras():
    """Everything the round-4 batch draws, run from render()."""
    render_bulk_stepper()
    render_delta_chips()
    render_undo()
    render_season_calendar()
    document.getElementById("genetics-rings").innerHTML = genetics_rings_html()
    document.getElementById("poultry-compare").innerHTML = poultry_compare_html()
    document.getElementById("hall-of-fame-list").innerHTML = hall_of_fame_html()
    note = pace_note_message()
    pace = document.getElementById("pace-note")
    pace.innerText = note
    pace.hidden = not note


def round_announcement(funds_before, methane_before):
    """Plain sentence for the aria-live region after Advance Round."""
    change = farm.funds - funds_before
    added = farm.methane - methane_before
    text = (
        f"Round {farm.round_number - 1} done. Funds {farm.funds:.0f}, {'up' if change >= 0 else 'down'} "
        f"{abs(change):.0f}. Methane added {added:.1f}, total {farm.methane:.0f}. Herd {farm.herd_size}."
    )
    if farm.last_round_perfect:
        text += f" Perfect round, streak {farm.perfect_streak}."
    return text


def on_grow_poultry(event=None):
    def do_buy():
        if farm.grow_poultry():
            _pulse("poultry-grow-button")
        render()

    _guarded_purchase("Grow Flock", farm.poultry_grow_cost(), do_buy)


def _make_poultry_handler(measure):
    def handler(event=None):
        def do_buy():
            if farm.invest_poultry(measure):
                _pulse(f"{measure}-count")
            render()

        _guarded_purchase(POULTRY_MEASURES[measure]["label"], POULTRY_MEASURES[measure]["cost"], do_buy)
    return handler


def on_invest_genetics(event=None):
    def do_buy():
        if farm.invest_genetics():
            _pulse("genetics-invest-button")
        render()

    _guarded_purchase("Breeding Program", GENETICS_COST, do_buy)


def on_invest_supply_chain(event=None):
    def do_buy():
        if farm.invest_supply_chain():
            _pulse("supply-chain-invest-button")
        render()

    _guarded_purchase("Processing & Distribution", SUPPLY_CHAIN_COST, do_buy)


def on_toggle_variation(event=None):
    farm.variation_enabled = bool(document.getElementById("variation-checkbox").checked)
    render()


def on_toggle_cap(event=None):
    farm.regional_cap_enabled = bool(document.getElementById("cap-checkbox").checked)
    render()


def _make_policy_handler(slot):
    def handler(event=None):
        farm.choose_policy(farm.current_policy_offer()[slot])
        render()
    return handler


# ===========================================================================
# Round-5 batch (planning/TODO.md "GF + F. Herd"). F-6: an "explain this number" inspector.
# ===========================================================================
EXPLAIN_KINDS = {
    "income": "Income per round",
    "methane": "Methane per round",
    "coupling": "Coupling ratio",
    "pressure": "Pressure",
}
explain_kind = None  # which breakdown is showing; session only, never saved


def _node(label, value, note="", children=None):
    return {"label": label, "value": value, "note": note, "children": children or []}


def _tree_html(nodes):
    if not nodes:
        return ""
    items = []
    for node in nodes:
        note = f' <span class="explain-note">{html.escape(node["note"])}</span>' if node["note"] else ""
        items.append(
            f'<li><span class="explain-label">{html.escape(node["label"])}</span> '
            f'<span class="explain-value">{html.escape(node["value"])}</span>{note}{_tree_html(node["children"])}</li>'
        )
    return f'<ul class="explain-tree">{"".join(items)}</ul>'


def _signed(value, digits=1):
    return f"{value:+.{digits}f}"


def explain_income_nodes():
    b = farm.income_breakdown()
    herd_children = []
    if farm.herd_size:
        herd_children.append(_node("Base income", f"{b['herd_base']:.1f}", f"{farm.herd_size} units x {HERD_INCOME_PER_UNIT} each"))
        if b["plant_fraction"] > 0:
            herd_children.append(_node(
                "Plant-based blend", f"x{b['plant_blend']:.3f}",
                f"{b['plant_fraction'] * 100:.0f}% of output is plant-based, which earns {farm.plant_income_multiplier():.2f} per unit",
            ))
        if farm.certified:
            herd_children.append(_node("Sustainable certification", f"x{b['certification']:.2f}", "permanent price premium"))
        if abs(b["welfare"] - 1) > 1e-9:
            herd_children.append(_node("Welfare", f"x{b['welfare']:.3f}", f"welfare score {farm.welfare():.0f} (neutral is {WELFARE_START:.0f})"))
    nodes = [_node("Herd income", f"{b['herd_income']:.1f}", "", herd_children)]
    if farm.poultry_size:
        nodes.append(_node("Poultry flock", _signed(b["poultry"]), f"{farm.poultry_size} birds, after housing upkeep"))
    if farm.satellite_size:
        nodes.append(_node("Satellite farm", _signed(b["satellite"]), f"{farm.satellite_size} units"))
    if farm.supply_chain_investment:
        nodes.append(_node("Supply chain", f"x{b['supply']:.2f}", f"{farm.supply_chain_investment} of {SUPPLY_CHAIN_MAX_UNITS} units"))
    if farm.variation_enabled:
        nodes.append(_node("Season", f"x{b['season']:.2f}", season_for_round(farm.round_number)[0]))
    if farm.label_rounds_left > 0:
        nodes.append(_node("Organic label trial", f"x{b['label']:.2f}", f"{farm.label_rounds_left} rounds left"))
    nodes.append(_node("Income before pressure", f"{b['raw']:.1f}"))
    nodes.append(_node("Market/regulatory pressure", f"-{b['pressure'] * 100:.0f}%", f"takes {b['raw'] * b['pressure']:.1f} of it; see the Pressure breakdown"))
    if b["biogas"]:
        nodes.append(_node("Biogas sales", _signed(b["biogas"]), "from capture systems beyond the first two"))
    return [_node("Funds earned when you advance this round", _signed(b["total"]), "", nodes)]


def explain_methane_nodes():
    herd = _node(
        "Herd", f"{farm.herd_size * farm.coupling_ratio():.2f}",
        f"{farm.herd_size} units x {farm.coupling_ratio():.2f} each (the coupling ratio)",
    )
    nodes = [herd]
    if farm.poultry_size:
        nodes.append(_node("Poultry flock", f"{farm.poultry_size * farm.poultry_coupling_ratio():.2f}", f"{farm.poultry_size} birds x {farm.poultry_coupling_ratio():.2f} each (methane-equivalent)"))
    if farm.satellite_size:
        offset = farm.satellite_offset_fraction()
        nodes.append(_node(
            "Satellite farm", f"{farm.satellite_size * farm.satellite_coupling_ratio():.2f}",
            f"{farm.satellite_size} units x {farm.satellite_coupling_ratio():.2f} each ({farm.satellite_own_ratio():.2f} after retrofits, {offset * 100:.0f}% cancelled by the main farm)",
        ))
    nodes.append(_node("Added to your total when you advance", f"{farm.methane_this_round():.2f}", f"total so far {farm.methane:.1f}"))
    return [_node("Methane this round", f"{farm.methane_this_round():.2f}", "", nodes)]


def explain_coupling_nodes():
    children = [_node("Starting level", f"{BASE_COUPLING_RATIO:.2f}", "every herd unit begins fully coupled")]
    for measure, spec in DECOUPLING_MEASURES.items():
        count = farm.decoupling_investment[measure]
        if count:
            children.append(_node(spec["label"], f"-{count * spec['ratio_reduction']:.2f}", f"{count} units x {spec['ratio_reduction']:.2f}"))
    if farm.genetics_active:
        children.append(_node("Breeding program", f"-{farm.genetics_active * GENETICS_RATIO_REDUCTION:.2f}", f"{farm.genetics_active} matured units x {GENETICS_RATIO_REDUCTION:.2f}"))
    efficiency = farm._efficiency_coupling_ratio()
    children.append(_node("After efficiency measures", f"{efficiency:.2f}", f"never below {MIN_COUPLING_RATIO:.2f}"))
    fraction = farm.plant_based_fraction()
    if fraction > 0:
        children.append(_node("Plant-based pivot", f"x{(1 - fraction) + fraction * PLANT_BASED_EMISSIONS_MULTIPLIER:.3f}", f"{fraction * 100:.0f}% of output is plant-based and gives off almost nothing"))
    return [_node("Coupling ratio", f"{farm.coupling_ratio():.2f}", "methane per herd unit per round", children)]


def explain_pressure_nodes():
    children = [
        _node("All methane so far", f"{farm.methane:.1f}", "never resets"),
        _node("Divided by", f"{pressure_scale():.0f}", "the scale of the pressure curve"),
        _node("Pressure", f"{farm.methane / pressure_scale() * 100:.0f}%", f"stops at {MAX_PRESSURE * 100:.0f}%"),
    ]
    lost = farm.income_breakdown()
    children.append(_node("Income lost this round", f"{lost['raw'] * lost['pressure']:.1f}", f"of {lost['raw']:.1f} before pressure"))
    return [_node("Market/regulatory pressure", f"{farm.pressure_fraction() * 100:.0f}% of income", "", children)]


EXPLAIN_BUILDERS = {
    "income": explain_income_nodes,
    "methane": explain_methane_nodes,
    "coupling": explain_coupling_nodes,
    "pressure": explain_pressure_nodes,
}


def explain_html(kind):
    builder = EXPLAIN_BUILDERS.get(kind)
    return _tree_html(builder()) if builder else ""


def render_explain():
    output = document.getElementById("explain-output")
    output.innerHTML = explain_html(explain_kind) if explain_kind else ""
    output.hidden = explain_kind is None
    for kind in EXPLAIN_KINDS:
        button = document.getElementById(f"explain-{kind}-button")
        button.setAttribute("aria-pressed", "true" if kind == explain_kind else "false")
        if kind == explain_kind:
            button.classList.add("selected")
        else:
            button.classList.remove("selected")


def _make_explain_handler(kind):
    def handler(event=None):
        global explain_kind
        explain_kind = None if explain_kind == kind else kind
        render_explain()
    return handler


# ===========================================================================
# Round-6 batch (planning/TODO.md "GF + F. Herd").
# ===========================================================================

# ---- F-1 Ranch Rules ----------------------------------------------------------------------
def rule_id(name):
    return "rule-" + name.replace("_", "-")


def format_rule(name, value):
    spec = RULE_SPECS[name]
    number = f"{value:g}" if abs(value - round(value)) > 1e-9 else f"{int(round(value))}"
    return f"{number}{spec['unit']}"


def farm_is_pristine():
    """No round played, nothing bought: the only moment a changed starting purse can still apply."""
    return (
        farm.round_number == 1 and farm.herd_size == 0 and not farm.lever_log
        and farm.poultry_size == 0 and farm.plant_pivot_investment == 0
    )


def set_rule(name, value):
    """Changes one rule. Returns True when the value really changed. Pace and penalty rules apply at
    once; a new starting purse applies right away only to a farm that has not started."""
    cleaned = clean_rule_value(name, value)
    if cleaned is None or abs(cleaned - ranch_rules[name]) < 1e-9:
        return False
    old = ranch_rules[name]
    ranch_rules[name] = cleaned
    if name == "starting_funds" and farm_is_pristine():
        delta = cleaned - old
        farm.funds += delta
        farm.counterfactual_funds += delta
        if farm.funds_history and farm.funds_history[0] is not None:
            farm.funds_history[0] += delta
    if rules_are_custom():
        farm.custom_rules_used = True
    elif farm_is_pristine():
        farm.custom_rules_used = False
    _store_rules()
    return True


def reset_rules():
    changed = False
    for name, spec in RULE_SPECS.items():
        changed = set_rule(name, spec["default"]) or changed
    return changed


def _load_rules_from_save(data):
    """A save brings its own rules (standard ones when it has none); values are clamped and snapped."""
    saved = data.get("ranch_rules")
    for name, spec in RULE_SPECS.items():
        ranch_rules[name] = spec["default"]
        if isinstance(saved, dict):
            cleaned = clean_rule_value(name, saved.get(name))
            if cleaned is not None:
                ranch_rules[name] = cleaned
    _store_rules()


def rules_summary_message():
    custom = [f"{RULE_SPECS[n]['label']} {format_rule(n, v)}" for n, v in ranch_rules.items()
              if abs(v - RULE_SPECS[n]["default"]) > 1e-9]
    if custom:
        return (
            "Custom rules: " + ", ".join(custom) + ". This run is unranked: it stays off the community "
            "leaderboard and out of the other-farms comparison."
        )
    if farm.custom_rules_used:
        return "The rules are standard again, but this run already used custom rules, so it stays unranked."
    return "Standard rules: this run can be ranked."


def rules_badge_message():
    return "Custom ranch rules: this run is unranked." if rules_unranked() else ""


def rules_start_note():
    if farm_is_pristine():
        return "A new starting purse applies right now, because the farm has not started."
    return "A new starting purse applies to the next new farm or handover; the other rules apply at once."


def render_rules():
    for name, value in ranch_rules.items():
        slider = document.getElementById(rule_id(name))
        slider.value = f"{value:g}"
        document.getElementById(rule_id(name) + "-value").innerText = format_rule(name, value)
    document.getElementById("rules-summary").innerText = rules_summary_message()
    document.getElementById("rules-start-note").innerText = rules_start_note()
    badge = document.getElementById("rules-badge")
    text = rules_badge_message()
    badge.innerText = text
    badge.hidden = not text


def _make_rule_handler(name):
    def handler(event=None):
        try:
            value = float(document.getElementById(rule_id(name)).value)
        except (TypeError, ValueError):
            return
        set_rule(name, value)
        render()
    return handler


def on_reset_rules(event=None):
    reset_rules()
    render()


# ---- F-7 dry-run planner ------------------------------------------------------------------
# Queue purchases for the next few rounds and see where a COPY of the farm would be. Nothing here
# touches the real farm, the save or any achievement; the plan itself is not saved.
PLAN_LEVERS = ["herd", "feed", "caps", "capture", "pivot", "genetics", "supply"]
PLAN_HORIZONS = (5, 10)
PLAN_COUNTS = (1, 2, 5)
PLAN_MAX_STEPS = 12
plan_steps = []  # [round offset (0 = now), lever key, count]
plan_horizon = 5


def clone_farm(source):
    """A scratch copy of a farm: every list and dict is copied, so playing the copy cannot change the original."""
    twin = copy.copy(source)
    twin.decoupling_investment = dict(source.decoupling_investment)
    twin.poultry_investment = dict(source.poultry_investment)
    for name in ("genetics_pending", "methane_history", "funds_history", "policy_offer", "policy_seen"):
        setattr(twin, name, list(getattr(source, name)))
    twin.lever_log = [list(entry) for entry in source.lever_log]
    twin.policy_history = [list(entry) for entry in source.policy_history]
    twin.undo_snapshot = None
    return twin


def _plan_buy(scratch, key):
    if key == "herd":
        return scratch.grow_herd()
    if key in DECOUPLING_MEASURES:
        return scratch.invest_decoupling(key)
    return {
        "pivot": scratch.invest_plant_pivot, "genetics": scratch.invest_genetics,
        "supply": scratch.invest_supply_chain,
    }[key]()


def project_plan(steps=None, horizon=None):
    """Plays the queued purchases on a scratch copy for `horizon` rounds. Returns {"rows", "idle", "skipped"}:
    rows are the plan's state after each round, idle the same rounds with no purchases at all."""
    steps = plan_steps if steps is None else steps
    horizon = plan_horizon if horizon is None else horizon
    scratch, idle = clone_farm(farm), clone_farm(farm)
    rows, idle_rows, skipped = [], [], []

    def snapshot(f, number):
        return {
            "round": number, "funds": f.funds, "per_round": f.methane_this_round(), "methane": f.methane,
            "coupling": f.coupling_ratio(), "score": f.score(), "baseline": f.counterfactual_score(),
        }

    for offset in range(horizon):
        for step_offset, key, count in steps:
            if step_offset != offset:
                continue
            bought = 0
            for _ in range(count):
                if not _plan_buy(scratch, key):
                    break
                bought += 1
            if bought < count:
                skipped.append(f"Round +{offset}: {LEVER_LABELS[key]} x{count - bought} not bought (funds or cap)")
        scratch.advance_round()
        idle.advance_round()
        rows.append(snapshot(scratch, farm.round_number + offset))
        idle_rows.append(snapshot(idle, farm.round_number + offset))
    return {"rows": rows, "idle": idle_rows, "skipped": skipped}


def add_plan_step(offset, key, count):
    if key not in PLAN_LEVERS or count not in PLAN_COUNTS or not 0 <= offset < max(PLAN_HORIZONS):
        return False
    if len(plan_steps) >= PLAN_MAX_STEPS:
        return False
    plan_steps.append([int(offset), key, int(count)])
    plan_steps.sort(key=lambda step: step[0])
    return True


def plan_step_text(step):
    offset, key, count = step
    when = "now, before this round ends" if offset == 0 else f"{offset} round{'s' if offset != 1 else ''} from now"
    return f"{LEVER_LABELS[key]} x{count}, {when}"


def plan_queue_html():
    visible = [s for s in plan_steps if s[0] < plan_horizon]
    if not plan_steps:
        return "<li>Nothing queued. Pick a lever and a round, then press Add to plan.</li>"
    items = "".join(f"<li>{html.escape(plan_step_text(step))}</li>" for step in plan_steps)
    hidden = len(plan_steps) - len(visible)
    if hidden:
        items += f"<li>{hidden} step(s) fall beyond the {plan_horizon}-round view and are left out of the projection.</li>"
    return items


def plan_table_html(result):
    head = (
        '<caption>Projected farm after each round</caption><thead><tr><th scope="col">Round</th>'
        '<th scope="col">Funds</th><th scope="col">Methane per round</th><th scope="col">Coupling</th>'
        '<th scope="col">Score</th><th scope="col">Score vs doing nothing</th>'
        '<th scope="col">Score vs pure-growth baseline</th></tr></thead>'
    )
    body = ""
    for row, idle in zip(result["rows"], result["idle"]):
        body += (
            f'<tr><th scope="row">{row["round"]}</th><td>{row["funds"]:.0f}</td><td>{row["per_round"]:.1f}</td>'
            f'<td>{row["coupling"]:.2f}</td><td>{row["score"]:.0f}</td><td>{row["score"] - idle["score"]:+.0f}</td>'
            f'<td>{row["score"] - row["baseline"]:+.0f}</td></tr>'
        )
    return f'<table class="compare-table plan-table">{head}<tbody>{body}</tbody></table>'


def plan_chart_svg(result):
    """Score over the projected rounds: solid = your plan, dashed = doing nothing, dotted = pure-growth baseline
    (line style as well as colour, with a letter at each line's end)."""
    width, height, pad = 260, 90, 8
    series = (
        ("plan", "P", [r["score"] for r in result["rows"]], "plan-line--plan"),
        ("doing nothing", "N", [r["score"] for r in result["idle"]], "plan-line--idle"),
        ("pure-growth baseline", "B", [r["baseline"] for r in result["rows"]], "plan-line--base"),
    )
    values = [v for _n, _l, vs, _c in series for v in vs]
    low, high = min(values), max(values)
    span = (high - low) or 1.0
    count = len(result["rows"])
    parts = []
    for name, letter, vs, css in series:
        points = []
        for i, v in enumerate(vs):
            x = pad + (width - 2 * pad - 12) * (i / max(1, count - 1))
            y = height - pad - (height - 2 * pad) * ((v - low) / span)
            points.append((x, y))
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        ex, ey = points[-1]
        parts.append(
            f'<polyline class="plan-line {css}" points="{path}"><title>{name}</title></polyline>'
            f'<text class="plan-line-letter" x="{ex + 3:.1f}" y="{ey + 3:.1f}">{letter}</text>'
        )
    label = "Projected score by round: plan (P, solid), doing nothing (N, dashed), pure-growth baseline (B, dotted)."
    return (
        f'<svg viewBox="0 0 {width} {height}" class="plan-chart-svg" role="img" aria-label="{label}">'
        f'<title>{label}</title>{"".join(parts)}</svg>'
    )


def plan_summary_message(result):
    last, idle = result["rows"][-1], result["idle"][-1]
    text = (
        f"After {plan_horizon} rounds the plan reaches a score of {last['score']:.0f} (doing nothing: "
        f"{idle['score']:.0f}, pure-growth baseline: {last['baseline']:.0f}), with {last['per_round']:.1f} methane "
        f"per round and {last['funds']:.0f} funds."
    )
    if result["skipped"]:
        text += " " + " ".join(result["skipped"]) + "."
    return text


def render_planner():
    document.getElementById("plan-queue-list").innerHTML = plan_queue_html()
    for horizon in PLAN_HORIZONS:
        button = document.getElementById(f"plan-horizon-{horizon}-button")
        button.setAttribute("aria-pressed", "true" if horizon == plan_horizon else "false")
        if horizon == plan_horizon:
            button.classList.add("selected")
        else:
            button.classList.remove("selected")
    document.getElementById("plan-undo-button").disabled = not plan_steps
    document.getElementById("plan-clear-button").disabled = not plan_steps
    result = project_plan()
    document.getElementById("plan-summary").innerText = plan_summary_message(result)
    document.getElementById("plan-chart").innerHTML = plan_chart_svg(result)
    document.getElementById("plan-table").innerHTML = plan_table_html(result)


def on_plan_add(event=None):
    lever = document.getElementById("plan-lever-select").value
    try:
        offset = int(document.getElementById("plan-round-select").value)
        count = int(document.getElementById("plan-count-select").value)
    except (TypeError, ValueError):
        return
    add_plan_step(offset, lever, count)
    render_planner()


def on_plan_remove_last(event=None):
    if plan_steps:
        plan_steps.pop()
    render_planner()


def on_plan_clear(event=None):
    del plan_steps[:]
    render_planner()


def _make_plan_horizon_handler(horizon):
    def handler(event=None):
        global plan_horizon
        plan_horizon = horizon
        render_planner()
    return handler


# ---- F-2 Ranch Ledger ---------------------------------------------------------------------
# One compact line per finished farm (a handover) or per farm the player files by hand, kept in this
# browser (localStorage), never in a save. A trend chart of score against the pure-growth baseline,
# filterable by mode.
LEDGER_STORAGE_KEY = "herd-ranch-ledger-v1"
LEDGER_MAX = 60
LEDGER_FILTERS = ("all", "plain", "seasons", "cap")
LEDGER_LEVERS = ("feed", "caps", "capture", "pivot", "genetics", "supply")
LEDGER_LEVER_SHORT = {"feed": "Feed", "caps": "Caps", "capture": "Capture", "pivot": "Pivot", "genetics": "Breeding", "supply": "Supply"}
ledger_filter = "all"


def farm_mode():
    if farm.variation_enabled and farm.regional_cap_enabled:
        return "seasons and cap"
    if farm.variation_enabled:
        return "seasons"
    if farm.regional_cap_enabled:
        return "cap"
    return "plain"


def ledger_entry(finished=False):
    levers = dict(farm.decoupling_investment)
    levers["pivot"] = farm.plant_pivot_investment
    levers["genetics"] = farm.genetics_active + len(farm.genetics_pending)
    levers["supply"] = farm.supply_chain_investment
    return {
        "gen": generation, "round": farm.round_number, "funds": round(farm.funds, 1), "methane": round(farm.methane, 1),
        "score": round(farm.score(), 1), "base": round(farm.counterfactual_score(), 1), "herd": farm.herd_size,
        "poultry": farm.poultry_size, "mode": farm_mode(), "custom": bool(rules_unranked()), "done": bool(finished),
        "levers": {k: int(levers.get(k, 0)) for k in LEDGER_LEVERS},
    }


def _clean_ledger_entry(raw):
    """A usable ledger line from stored JSON, or None."""
    if not isinstance(raw, dict):
        return None
    numbers = {}
    for key in ("gen", "round", "funds", "methane", "score", "base", "herd", "poultry"):
        if not _is_finite_number(raw.get(key)):
            return None
        numbers[key] = float(raw[key])
    mode = raw.get("mode")
    if mode not in ("plain", "seasons", "cap", "seasons and cap"):
        return None
    levers = raw.get("levers")
    if not isinstance(levers, dict):
        return None
    clean_levers = {k: _safe_int(levers.get(k), 0) for k in LEDGER_LEVERS}
    return {
        "gen": max(1, int(numbers["gen"])), "round": max(1, int(numbers["round"])), "funds": numbers["funds"],
        "methane": max(0.0, numbers["methane"]), "score": numbers["score"], "base": numbers["base"],
        "herd": max(0, int(numbers["herd"])), "poultry": max(0, int(numbers["poultry"])), "mode": mode,
        "custom": raw.get("custom") is True, "done": raw.get("done") is True, "levers": clean_levers,
    }


def read_ledger():
    raw = _read_local_storage_item(LEDGER_STORAGE_KEY)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    entries = [e for e in (_clean_ledger_entry(item) for item in data) if e is not None]
    return entries[-LEDGER_MAX:]


def ledger_record(entry):
    """Files a line. Filing the same generation at the same round again replaces that line instead of repeating it."""
    entries = [e for e in read_ledger() if not (e["gen"] == entry["gen"] and e["round"] == entry["round"])]
    entries.append(entry)
    del entries[:-LEDGER_MAX]
    _write_local_storage_item(LEDGER_STORAGE_KEY, json.dumps(entries))
    return entries


def ledger_matches(entry, which):
    if which == "all":
        return True
    if which == "plain":
        return entry["mode"] == "plain"
    return which in entry["mode"]


def ledger_rows(which=None):
    which = ledger_filter if which is None else which
    return [e for e in read_ledger() if ledger_matches(e, which)]


def ledger_levers_text(entry):
    parts = [f"{LEDGER_LEVER_SHORT[k]} {entry['levers'][k]}" for k in LEDGER_LEVERS if entry["levers"][k]]
    return ", ".join(parts) if parts else "none"


def ledger_table_html(rows):
    if not rows:
        return "<p class=\"comparison-message\">No farms filed here yet. A handover files the farm automatically; the button above files the one you are playing.</p>"
    head = (
        '<caption>Finished and filed farms, oldest first</caption><thead><tr><th scope="col">Gen</th>'
        '<th scope="col">Rounds</th><th scope="col">Funds</th><th scope="col">Methane</th><th scope="col">Score</th>'
        '<th scope="col">Vs baseline</th><th scope="col">Levers</th><th scope="col">Flock</th><th scope="col">Mode</th></tr></thead>'
    )
    body = ""
    for e in rows:
        note = " (custom rules, unranked)" if e["custom"] else ""
        body += (
            f'<tr><th scope="row">{e["gen"]}{"" if e["done"] else " (filed)"}</th><td>{e["round"] - 1}</td><td>{e["funds"]:.0f}</td>'
            f'<td>{e["methane"]:.0f}</td><td>{e["score"]:.0f}</td><td>{e["score"] - e["base"]:+.0f}</td>'
            f'<td>{html.escape(ledger_levers_text(e))}</td><td>{e["poultry"]}</td><td>{html.escape(e["mode"])}{note}</td></tr>'
        )
    return f'<table class="compare-table ledger-table">{head}<tbody>{body}</tbody></table>'


def ledger_chart_svg(rows):
    """Score minus the pure-growth baseline for each filed farm, in order: a line with a square at every
    point (the shape, not just the colour), a dashed zero line and the best point labelled."""
    if len(rows) < 2:
        return ""
    width, height, pad = 260, 80, 10
    values = [e["score"] - e["base"] for e in rows] + [0.0]
    low, high = min(values), max(values)
    span = (high - low) or 1.0

    def y_of(v):
        return height - pad - (height - 2 * pad) * ((v - low) / span)

    points = [(pad + (width - 2 * pad) * i / (len(rows) - 1), y_of(e["score"] - e["base"])) for i, e in enumerate(rows)]
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    marks = "".join(f'<rect class="ledger-mark" x="{x - 2.5:.1f}" y="{y - 2.5:.1f}" width="5" height="5"/>' for x, y in points)
    label = f"Score against the pure-growth baseline for {len(rows)} filed farms; best {max(values):+.0f}."
    return (
        f'<svg viewBox="0 0 {width} {height}" class="ledger-chart-svg" role="img" aria-label="{label}"><title>{label}</title>'
        f'<line class="ledger-zero" x1="{pad}" x2="{width - pad}" y1="{y_of(0):.1f}" y2="{y_of(0):.1f}"/>'
        f'<polyline class="ledger-line" points="{path}"/>{marks}</svg>'
    )


def render_ledger():
    rows = ledger_rows()
    document.getElementById("ledger-table").innerHTML = ledger_table_html(rows)
    document.getElementById("ledger-chart").innerHTML = ledger_chart_svg(rows)
    total = len(read_ledger())
    best = max((e["score"] - e["base"] for e in read_ledger()), default=None)
    document.getElementById("ledger-summary").innerText = (
        "Nothing filed yet." if total == 0 else
        f"{total} farm{'s' if total != 1 else ''} filed in this browser; best result against the baseline: {best:+.0f}."
    )
    document.getElementById("ledger-clear-button").disabled = total == 0


def on_ledger_filter(event=None):
    global ledger_filter
    value = document.getElementById("ledger-filter").value
    ledger_filter = value if value in LEDGER_FILTERS else "all"
    render_ledger()


def on_ledger_add(event=None):
    ledger_record(ledger_entry(finished=False))
    render_ledger()
    _display_milestone_toast("Filed this farm in the Ranch Ledger.")


def _clear_ledger():
    _write_local_storage_item(LEDGER_STORAGE_KEY, "[]")
    render_ledger()


def on_ledger_clear(event=None):
    _confirm_dialog_ask(
        action_id="herd-clear-ledger",
        message="Clear the Ranch Ledger? Every filed farm is removed from this browser. Your saves are not touched.",
        confirm_label="Clear ledger",
        on_confirm=_clear_ledger,
        allow_skip=False,
    )


# ---- F-16 pin-a-stat strip ---------------------------------------------------------------
# Up to three readouts pinned into a sticky strip, so they stay in view while the extras panels are
# open. The choice is a browser preference (localStorage), never part of a save.
PINS_STORAGE_KEY = "herd-pinned-stats"
PIN_MAX = 3
PIN_STATS = {
    "funds": ("Funds", lambda: f"{farm.funds:.0f}"),
    "income": ("Income per round", lambda: f"{farm.income_breakdown()['total']:.1f}"),
    "welfare": ("Welfare", lambda: f"{farm.welfare():.0f}/100"),
    "methane_round": ("Methane per round", lambda: f"{farm.methane_this_round():.1f}"),
    "methane": ("Total methane", lambda: f"{farm.methane:.0f}"),
    "score": ("Score", lambda: f"{farm.score():.0f}"),
    "herd": ("Herd", lambda: f"{farm.herd_size}"),
    "pressure": ("Pressure", lambda: f"{farm.pressure_fraction() * 100:.0f}% income loss"),
}


def clean_pins(raw):
    """Pin ids from stored or untrusted data: real stats only, no repeats, at most PIN_MAX."""
    if not isinstance(raw, list):
        return []
    pins = []
    for item in raw:
        if isinstance(item, str) and item in PIN_STATS and item not in pins:
            pins.append(item)
    return pins[:PIN_MAX]


def load_pins():
    raw = _read_local_storage_item(PINS_STORAGE_KEY)
    if not raw:
        return []
    try:
        return clean_pins(json.loads(raw))
    except (ValueError, TypeError):
        return []


pinned_stats = load_pins()


def set_pin(stat, on):
    """Pins or unpins one stat. Pinning a fourth is refused. Returns True when the pins changed."""
    global pinned_stats
    if stat not in PIN_STATS:
        return False
    if on and stat not in pinned_stats and len(pinned_stats) < PIN_MAX:
        pinned_stats = pinned_stats + [stat]
    elif not on and stat in pinned_stats:
        pinned_stats = [s for s in pinned_stats if s != stat]
    else:
        return False
    _write_local_storage_item(PINS_STORAGE_KEY, json.dumps(pinned_stats))
    return True


def pinned_strip_html():
    return "".join(
        f'<span class="pin-chip"><span class="pin-chip-label">{PIN_STATS[stat][0]}</span> '
        f'<span class="pin-chip-value">{PIN_STATS[stat][1]()}</span></span>'
        for stat in pinned_stats
    )


def render_pins():
    strip = document.getElementById("pinned-strip")
    strip.hidden = not pinned_stats
    strip.innerHTML = pinned_strip_html()
    full = len(pinned_stats) >= PIN_MAX
    for stat in PIN_STATS:
        box = document.getElementById(f"pin-{stat.replace('_', '-')}")
        box.checked = stat in pinned_stats
        box.disabled = full and stat not in pinned_stats
    document.getElementById("pin-note").innerText = (
        f"{len(pinned_stats)} of {PIN_MAX} pinned. Untick one to pin another." if full
        else f"{len(pinned_stats)} of {PIN_MAX} pinned. Pinned stats stay in a strip at the top of the page."
    )


def _make_pin_handler(stat):
    def handler(event=None):
        set_pin(stat, bool(document.getElementById(f"pin-{stat.replace('_', '-')}").checked))
        render_pins()
    return handler


def render():
    _sync_collection()
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
        f"{min(1.0, farm.methane / pressure_scale()) * 100:.0f}%"
    )
    document.getElementById("score-display").innerText = f"Score: {farm.score():.0f}"

    grow_cost = farm.grow_herd_cost()
    grow_button = document.getElementById("grow-herd-button")
    grow_button.innerText, grow_button.disabled = bulk_button_label("herd", "Grow Herd", grow_cost, ".0f")
    # F9 — consequence preview next to the Grow Herd button.
    document.getElementById("grow-consequence-preview").innerText = grow_consequence_message()

    for measure, spec in DECOUPLING_MEASURES.items():
        document.getElementById(f"{measure}-name").innerText = f"{spec['icon']} {spec['label']}"
        document.getElementById(f"{measure}-count").innerText = str(
            farm.decoupling_investment[measure]
        )
        button = document.getElementById(f"{measure}-invest-button")
        cost = farm.decoupling_cost(measure)
        button.innerText, button.disabled = bulk_button_label(measure, spec["label"], cost, "g")

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

    # F3 — report card panel, kept in sync if left open across a render. The toggle's label is
    # always set so a fresh page never shows the "Loading..." placeholder from index.html.
    document.getElementById("report-card-toggle-button").innerText = (
        "Hide Report Card" if report_card_open else "📊 Report Card"
    )
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
    render_progress_extras()
    render_round_extras()
    render_explain()
    render_rules()
    render_planner()
    render_ledger()
    render_pins()


# F-18: an optional "ask before a big purchase" setting. The Settings select (settings.js) keeps the
# threshold in localStorage as a percentage of current funds; 0 means off, which is the default.
CONFIRM_THRESHOLD_KEY = "herd-confirm-percent"
CONFIRM_THRESHOLD_CHOICES = (0, 25, 50, 75)


def confirm_threshold_percent():
    raw = _read_local_storage_item(CONFIRM_THRESHOLD_KEY)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 0
    return value if value in CONFIRM_THRESHOLD_CHOICES else 0


def purchase_needs_confirm(cost):
    """True when the setting is on and this purchase costs more than the chosen share of the
    funds the farm has right now."""
    percent = confirm_threshold_percent()
    return percent > 0 and cost > 0 and farm.funds > 0 and cost > farm.funds * percent / 100.0 + 1e-9


def big_purchase_message(label, cost):
    share = cost / farm.funds * 100 if farm.funds > 0 else 100
    return (
        f"{label} costs {cost:.0f} funds, {share:.0f}% of the {farm.funds:.0f} you have. "
        f"You asked to be checked before any purchase above {confirm_threshold_percent()}% of your funds."
    )


def _guarded_purchase(label, cost, action):
    """Runs `action` straight away, or after the shared confirm dialog when the F-18 setting says
    this purchase is big. The dialog has no "don't ask again" box (the setting itself is the way
    to turn it off)."""
    if purchase_needs_confirm(cost):
        _confirm_dialog_ask(
            action_id="herd-big-purchase",
            message=big_purchase_message(label, cost),
            confirm_label="Buy",
            on_confirm=action,
            allow_skip=False,
        )
    else:
        action()


def on_grow_herd(event=None):
    def do_buy():
        if farm.buy_bulk("herd", bulk_mode):
            _pulse("grow-herd-button")
        render()
        _check_new_achievements_for_toast()

    _guarded_purchase("Grow Herd", farm.bulk_plan("herd", bulk_mode)[1], do_buy)


def _make_decoupling_handler(measure):
    def handler(event=None):
        def do_buy():
            ratio_before = farm.coupling_ratio()
            if farm.buy_bulk(measure, bulk_mode):
                _pulse(f"{measure}-count")
                if farm.coupling_ratio() < ratio_before - 1e-9:
                    _pulse("gauge-range-display")  # F22 — new session-best
            render()
            _check_new_achievements_for_toast()

        _guarded_purchase(DECOUPLING_MEASURES[measure]["label"], farm.bulk_plan(measure, bulk_mode)[1], do_buy)
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
    global farm, generation, legacy_points, last_deltas
    if not can_hand_over():
        return None
    earned = handover_points()
    ledger_record(ledger_entry(finished=True))  # F-2: the finished farm is filed before it is retired
    retire_herd_to_hall()  # GF-13: the longest-serving animals are honoured before the herd is retired
    legacy_points += earned
    generation += 1
    farm = FarmState()
    last_deltas = {}  # the old farm's round-change chips do not belong to the new one
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

    if purchase_needs_confirm(PLANT_PIVOT_COST):
        # F-18: the setting says this is a big purchase, so ask every time (no "don't ask again").
        _confirm_dialog_ask(
            action_id="herd-big-purchase",
            message=f"{big_purchase_message('Plant-Based Pivot', PLANT_PIVOT_COST)} {plant_pivot_confirm_message()}",
            confirm_label="Invest",
            on_confirm=do_invest,
            allow_skip=False,
        )
        return
    _confirm_dialog_ask(
        action_id="herd-plant-pivot-invest",
        message=plant_pivot_confirm_message(),
        confirm_label="Invest",
        on_confirm=do_invest,
    )


def _report_decoupling_gap():
    """F21: the decoupling gap (score minus the pure-growth counterfactual's
    score) goes to the shared opt-in leaderboard widget, which only submits
    for an opted-in, signed-in player and remembers the personal best."""
    gap = farm.score() - farm.counterfactual_score()
    if gap <= 0 or rules_unranked():  # F-1: custom-rule runs stay off the leaderboard
        return
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    board = getattr(window, "NoyvjLeaderboard", None)
    if board is not None:
        board.report("herd", "decoupling_gap", round(gap, 1), f"round {farm.round_number}")


last_round_income = None  # GF-14: the income of the round before, for the "best round" burst


def celebrate_round(income, beat):
    """GF-14: hands the round's income to the page's optional HerdFx hook (settings.js), which counts it up
    under the Advance Round button and bursts confetti when `beat` is true. A page without the hook, or the
    pytest harness, is a silent no-op."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return False
    hook = getattr(window, "HerdFx", None)
    if hook is None:
        return False
    hook.roundGain(float(income), bool(beat))
    return True


def on_advance_round(event=None):
    global last_deltas, session_rounds, last_round_income
    income_this_round = farm.income_breakdown()["total"]
    funds_before, methane_before = farm.funds, farm.methane
    welfare_before, pressure_before = farm.welfare(), farm.pressure_fraction()
    farm.undo_snapshot = get_state()  # GF-18: the state to rewind to
    farm.advance_round()
    session_rounds += 1
    last_deltas = round_deltas(funds_before, methane_before, welfare_before, pressure_before)
    _schedule_delta_fade()
    _report_decoupling_gap()
    render()
    beat = last_round_income is not None and income_this_round > last_round_income + 1e-9
    last_round_income = income_this_round
    celebrate_round(income_this_round, beat)
    document.getElementById("round-announcer").innerText = round_announcement(funds_before, methane_before)
    nudge = save_nudge_message()
    if farm.just_streak_bonus is not None:
        streak, bonus = farm.just_streak_bonus
        farm.just_streak_bonus = None
        message = f"\U0001F525 Perfect-round streak of {streak}: +{bonus} funds."
        _display_milestone_toast(f"{message} {nudge}".strip())
    elif nudge:
        _display_milestone_toast(nudge)
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
        "summary": steward_summary(),  # B-23: write-only, never read back
        "achievements_earned": achievement_ids_earned(),
    }
    # F1: satellite state only once the satellite has been opened.
    if farm.satellite_open:
        state["satellite_open"] = True
        state["satellite_size"] = farm.satellite_size
        state["satellite_retrofits"] = farm.satellite_retrofits
    # GF-29/F-17/GF-15/GF-16/GF-5: written only once there is something to keep.
    if len(farm.funds_history) > 1:
        state["funds_history"] = list(farm.funds_history)
    if farm.lever_log:
        state["lever_log"] = [list(entry) for entry in farm.lever_log]
    if farm.perfect_streak > 0:
        state["perfect_streak"] = farm.perfect_streak
    if farm.best_perfect_streak > 0:
        state["best_perfect_streak"] = farm.best_perfect_streak
    if breeds_collected:
        state["breeds_collected"] = list(breeds_collected)
    if combos_found:
        state["combos_found"] = list(combos_found)
    if hall_of_fame:
        state["hall_of_fame"] = [list(entry) for entry in hall_of_fame]
    if farm.undo_used:
        state["undo_used"] = True
    # F-9: advisor pool state, written only once there is something to keep.
    if farm.policy_offer_pending and len(farm.policy_offer) == 2:
        state["policy_offer"] = list(farm.policy_offer)
    if farm.policy_seen:
        state["policy_seen"] = list(farm.policy_seen)
    if farm.policy_history:
        state["policy_history"] = [list(entry) for entry in farm.policy_history]
    if farm.hedge_rounds_left > 0:
        state["hedge_rounds_left"] = farm.hedge_rounds_left
    if farm.label_rounds_left > 0:
        state["label_rounds_left"] = farm.label_rounds_left
    # F-1: ranch rules and the unranked flag, only when something is non-standard.
    custom = {n: v for n, v in ranch_rules.items() if abs(v - RULE_SPECS[n]["default"]) > 1e-9}
    if custom:
        state["ranch_rules"] = custom
    if farm.custom_rules_used:
        state["custom_rules_used"] = True
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


def _policy_ids(raw):
    """Option ids from untrusted save data, kept only when they are real options."""
    if not isinstance(raw, list):
        return []
    return [o for o in raw if isinstance(o, str) and o in POLICY_OPTIONS]


def _load_policy_fields(data):
    offer = _policy_ids(data.get("policy_offer"))
    farm.policy_offer = offer if len(offer) == 2 and offer[0] != offer[1] else []
    seen = _policy_ids(data.get("policy_seen"))
    farm.policy_seen = [o for i, o in enumerate(seen) if o not in seen[:i]]
    farm.policy_history = []
    history = data.get("policy_history")
    if isinstance(history, list):
        for entry in history[-POLICY_HISTORY_MAX:]:
            if (
                isinstance(entry, (list, tuple)) and len(entry) == 3 and _is_finite_number(entry[0])
                and entry[1] in POLICY_OPTIONS and entry[2] in POLICY_OPTIONS and entry[1] != entry[2]
            ):
                farm.policy_history.append([max(1, int(entry[0])), entry[1], entry[2]])
    farm.hedge_rounds_left = min(POLICY_HEDGE_ROUNDS, _safe_int(data.get("hedge_rounds_left"), 0))
    farm.label_rounds_left = min(POLICY_LABEL_ROUNDS, _safe_int(data.get("label_rounds_left"), 0))


def _load_progress_fields(data):
    """Validated load of the highlights/log/streak/collection fields; every one
    defaults safely so older saves and hand-edited payloads cannot crash."""
    global breeds_collected, combos_found, hall_of_fame
    history = data.get("funds_history")
    cleaned = None
    if isinstance(history, list):
        cleaned = []
        for value in history:
            if (
                isinstance(value, (int, float)) and not isinstance(value, bool)
                and value == value and abs(value) != float("inf")
            ):
                cleaned.append(float(value))
            else:
                cleaned.append(None)
    # Aligned with methane_history: a missing or mismatched record becomes "unknown
    # until now" padding so rounds already played never invent numbers.
    if cleaned is None or len(cleaned) != len(farm.methane_history):
        cleaned = [None] * (len(farm.methane_history) - 1) + [farm.funds]
    farm.funds_history = cleaned
    log = data.get("lever_log")
    farm.lever_log = []
    if isinstance(log, list):
        for entry in log[-LEVER_LOG_MAX:]:
            if (
                isinstance(entry, (list, tuple)) and len(entry) == 3 and entry[1] in LEVER_LABELS
                and isinstance(entry[0], (int, float)) and not isinstance(entry[0], bool)
                and isinstance(entry[2], (int, float)) and not isinstance(entry[2], bool)
                and entry[0] == entry[0] and entry[2] == entry[2]
                and abs(entry[0]) != float("inf") and abs(entry[2]) != float("inf")
            ):
                farm.lever_log.append([max(1, int(entry[0])), entry[1], float(entry[2])])
    farm.perfect_streak = _safe_int(data.get("perfect_streak"), 0)
    farm.best_perfect_streak = max(farm.perfect_streak, _safe_int(data.get("best_perfect_streak"), 0))
    breeds_collected = _valid_ids(data.get("breeds_collected"), BREEDS)
    combos_found = _valid_ids(data.get("combos_found"), COMBOS)
    farm.undo_used = data.get("undo_used") is True
    farm.undo_snapshot = None
    farm.custom_rules_used = data.get("custom_rules_used") is True or rules_are_custom()
    hall_of_fame = []
    saved_hall = data.get("hall_of_fame")
    if isinstance(saved_hall, list):
        for entry in saved_hall[:HALL_OF_FAME_SIZE]:
            if (
                isinstance(entry, (list, tuple)) and len(entry) == 3 and isinstance(entry[0], str)
                and all(isinstance(v, (int, float)) and not isinstance(v, bool) and v == v for v in entry[1:])
                and abs(entry[1]) != float("inf") and abs(entry[2]) != float("inf")
            ):
                hall_of_fame.append([entry[0][:40], max(0, int(entry[1])), max(1, int(entry[2]))])
        hall_of_fame.sort(key=lambda e: (-e[1], e[2]))


# ===========================================================================
# F-30: friendly save recovery. A save that fails validation never touches the farm: the player
# sees a plain reason for each problem and can keep the current farm or load the save with
# defaults in place of just the bad fields. The widget around load_state() reports "Load failed"
# because load_state() raises ValueError for such a save; the panel explains why.
# ===========================================================================
# key: (plain label, minimum, whole number only, default for a fresh farm)
SAVE_NUMBER_FIELDS = {
    "round_number": ("Round number", 1, True, 1),
    "funds": ("Funds", None, False, STARTING_FUNDS),
    "herd_size": ("Herd size", 0, True, 0),
    "methane": ("Methane", 0, False, 0.0),
    "plant_pivot_investment": ("Plant-based pivot units", 0, True, 0),
    "counterfactual_funds": ("Baseline funds", None, False, STARTING_FUNDS),
    "counterfactual_methane": ("Baseline methane", 0, False, 0.0),
    "max_pressure_fraction_seen": ("Worst pressure seen", 0, False, 0.0),
}
RECOVERY_MAX_REASONS = 6
pending_recovery = None  # {"data": dict | None, "problems": [(key, reason)]}, never saved


def _is_finite_number(value):
    return (
        isinstance(value, (int, float)) and not isinstance(value, bool)
        and value == value and abs(value) != float("inf")
    )


def _shown(value):
    text = json.dumps(value, default=str) if not isinstance(value, str) else f'"{value}"'
    return text if len(text) <= 24 else text[:21] + "..."


def _number_problem(label, value, minimum, whole):
    """A plain-language reason this value cannot be used, or None when it is fine."""
    if not _is_finite_number(value):
        return f"{label} should be a number, but the save has {_shown(value)}."
    if whole and value != int(value):
        return f"{label} should be a whole number, but the save has {_shown(value)}."
    if minimum is not None and value < minimum:
        return f"{label} should be {minimum} or more, but the save has {_shown(value)}."
    return None


def check_save(data):
    """List of (key, reason) for every field that is present but unusable. A field that is simply
    missing is not a problem (older saves lack newer fields and load with defaults, as always)."""
    if not isinstance(data, dict):
        return [("", "This is not a Herd save (it is not a set of named values).")]
    problems = []
    for key, (label, minimum, whole, _default) in SAVE_NUMBER_FIELDS.items():
        if key in data:
            reason = _number_problem(label, data[key], minimum, whole)
            if reason:
                problems.append((key, reason))
    investment = data.get("decoupling_investment")
    if "decoupling_investment" in data and not isinstance(investment, dict):
        problems.append(("decoupling_investment", "The decoupling investments should be a list of counts, but the save has something else."))
    elif isinstance(investment, dict):
        for measure in DECOUPLING_MEASURES:
            if measure in investment:
                reason = _number_problem(f"{DECOUPLING_MEASURES[measure]['label']} units", investment[measure], 0, True)
                if reason:
                    problems.append((f"decoupling_investment.{measure}", reason))
    history = data.get("methane_history")
    if "methane_history" in data and (
        not isinstance(history, list) or not history or not all(_is_finite_number(v) for v in history)
    ):
        problems.append(("methane_history", "The methane history should be a list of numbers, but the save has something else."))
    return problems


def sanitize_save(data, problems):
    """A copy of the save with a fresh-farm default in place of just the bad fields."""
    clean = copy.deepcopy(data)
    for key, _reason in problems:
        if key in SAVE_NUMBER_FIELDS:
            clean[key] = SAVE_NUMBER_FIELDS[key][3]
        elif key == "decoupling_investment":
            clean[key] = {m: 0 for m in DECOUPLING_MEASURES}
        elif key.startswith("decoupling_investment."):
            clean["decoupling_investment"][key.split(".", 1)[1]] = 0
        elif key == "methane_history":
            clean[key] = [0.0]
    return clean


def render_save_recovery():
    panel = document.getElementById("save-recovery-panel")
    panel.hidden = pending_recovery is None
    if pending_recovery is None:
        return
    reasons = [reason for _key, reason in pending_recovery["problems"][:RECOVERY_MAX_REASONS]]
    extra = len(pending_recovery["problems"]) - len(reasons)
    if extra > 0:
        reasons.append(f"...and {extra} more.")
    document.getElementById("save-recovery-reasons").innerHTML = "".join(
        f"<li>{html.escape(r)}</li>" for r in reasons
    )
    can_default = pending_recovery["data"] is not None
    document.getElementById("save-recovery-defaults-button").hidden = not can_default
    document.getElementById("save-recovery-note").innerText = (
        "Your current farm has not been changed. You can keep it, or load this save with a fresh-farm "
        "value in place of only the fields listed above."
        if can_default else "Your current farm has not been changed."
    )


def _offer_recovery(data, problems):
    global pending_recovery
    pending_recovery = {"data": data if isinstance(data, dict) else None, "problems": problems}
    render_save_recovery()
    _display_milestone_toast("That save could not be loaded as it is. See the notice at the top for why.")


def on_recovery_defaults(event=None):
    global pending_recovery
    if pending_recovery is None or pending_recovery["data"] is None:
        return
    clean = sanitize_save(pending_recovery["data"], pending_recovery["problems"])
    pending_recovery = None
    render_save_recovery()
    _apply_state(clean)


def on_recovery_dismiss(event=None):
    global pending_recovery
    pending_recovery = None
    render_save_recovery()


# B-23: a few honest, already-computed numbers for the hub's Climate Steward page. Written into the save as a
# read-only `summary` list ({label, value, unit, note?}); never read back by load_state().
def steward_summary():
    return [
        {"label": "Methane decoupled from output", "value": round(max(0.0, farm.decoupled_fraction()) * 100), "unit": "%"},
        {"label": "Breeds collected", "value": len(breeds_collected), "unit": f"of {len(BREEDS)}"},
        {"label": "Rounds farmed", "value": max(0, int(farm.round_number) - 1), "unit": ""},
    ]


def load_state(data):
    """Validates first, so a broken save never leaves the farm half-loaded. A problem save raises
    ValueError (the save widget then says "Load failed") after the recovery panel explains why.
    If something unforeseen goes wrong while applying a save that passed the checks, the farm is put
    back exactly as it was and the same panel is shown."""
    global pending_recovery
    problems = check_save(data)
    if problems:
        _offer_recovery(data, problems)
        if not isinstance(data, dict):
            return False
        raise ValueError("Save not loaded: " + " ".join(reason for _key, reason in problems[:3]))
    backup = get_state()
    try:
        result = _apply_state(data)
    except Exception:
        _apply_state(backup)
        _offer_recovery(None, [("", "Something in this save could not be read, so it was not loaded.")])
        raise
    if pending_recovery is not None:
        pending_recovery = None
        render_save_recovery()
    return result


def _apply_state(data):
    # Every top-level field uses a .get() fallback (to the farm's current
    # live value) rather than bare data["key"] indexing -- a save missing
    # any single field (an older save predating that field, e.g. one from
    # before the Pass 2 plant-based pivot added plant_pivot_investment to
    # the state dict, or a hand-edited/corrupted payload) must not crash
    # load_state() outright and abort every field after the missing one,
    # the same bare-indexing bug already fixed in Tide's load_state() --
    # see BCM114-DEV-LOG.md 2026-09-02.
    _load_rules_from_save(data)
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
    _load_progress_fields(data)
    farm.variation_enabled = data.get("variation_enabled") is True
    farm.regional_cap_enabled = data.get("regional_cap_enabled") is True
    farm.policy_offer_pending = data.get("policy_offer_pending") is True
    farm.subsidy_rounds_left = _safe_int(data.get("subsidy_rounds_left"), 0)
    _load_policy_fields(data)
    # achievements_earned is deliberately never read back here -- it's a
    # write-only projection recomputed fresh by get_state() every save,
    # per ACHIEVEMENTS-SYSTEM-DESIGN.md.
    _sync_collection(award=False)  # a load records what the farm qualifies for but never pays
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
    document.getElementById("save-recovery-defaults-button").addEventListener("click", create_proxy(on_recovery_defaults))
    document.getElementById("save-recovery-dismiss-button").addEventListener("click", create_proxy(on_recovery_dismiss))
    document.getElementById("save-recovery-panel").hidden = True
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
        ("policy-subsidy-button", _make_policy_handler(0)),
        ("policy-cash-button", _make_policy_handler(1)),
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
    document.getElementById("lever-history-filter").addEventListener(
        "change", create_proxy(on_lever_history_filter)
    )
    for mode, element_id in BULK_BUTTON_IDS.items():
        document.getElementById(element_id).addEventListener("click", create_proxy(_make_bulk_handler(mode)))
    for key in DELTA_KEYS:
        document.getElementById(f"delta-chip-{key}").addEventListener(
            "click", create_proxy(_make_delta_pin_handler(key))
        )
    document.getElementById("undo-round-button").addEventListener("click", create_proxy(on_undo_round))
    for rule_name in RULE_SPECS:
        document.getElementById(rule_id(rule_name)).addEventListener("input", create_proxy(_make_rule_handler(rule_name)))
    document.getElementById("rules-reset-button").addEventListener("click", create_proxy(on_reset_rules))
    for element_id, handler in (
        ("plan-add-button", on_plan_add), ("plan-undo-button", on_plan_remove_last),
        ("plan-clear-button", on_plan_clear),
    ):
        document.getElementById(element_id).addEventListener("click", create_proxy(handler))
    for stat in PIN_STATS:
        document.getElementById(f"pin-{stat.replace('_', '-')}").addEventListener("click", create_proxy(_make_pin_handler(stat)))
    document.getElementById("ledger-filter").addEventListener("change", create_proxy(on_ledger_filter))
    document.getElementById("ledger-add-button").addEventListener("click", create_proxy(on_ledger_add))
    document.getElementById("ledger-clear-button").addEventListener("click", create_proxy(on_ledger_clear))
    for horizon in PLAN_HORIZONS:
        document.getElementById(f"plan-horizon-{horizon}-button").addEventListener(
            "click", create_proxy(_make_plan_horizon_handler(horizon))
        )
    for kind in EXPLAIN_KINDS:
        document.getElementById(f"explain-{kind}-button").addEventListener("click", create_proxy(_make_explain_handler(kind)))
    render()
    _seed_achievement_toast_baseline()


setup()
