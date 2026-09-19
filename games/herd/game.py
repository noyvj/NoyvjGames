"""Herd — Industrial Agriculture & Methane Game.

Runs in-browser via Pyodide. The core farm loop (herd growth, income,
and round progression), the methane meter (coupled to herd size by
default), the decoupling investments that reduce that coupling, and the
soft market/regulatory consequence system are all implemented below --
all 7 milestones are complete (see CLAUDE.md's milestone table).
"""

import json
import os

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

# Achievements — clean_operator's round/pressure bar.
CLEAN_OPERATOR_MIN_ROUND = 15
CLEAN_OPERATOR_MAX_PRESSURE = 0.1


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

    def _efficiency_coupling_ratio(self):
        """Methane produced per herd unit, per round, from the feed/caps/
        capture efficiency measures alone — floored so it never hits zero."""
        reduction = sum(
            self.decoupling_investment[m] * DECOUPLING_MEASURES[m]["ratio_reduction"]
            for m in DECOUPLING_MEASURES
        )
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
        return self.herd_size * self.coupling_ratio()

    def grow_herd_cost(self):
        """F6 — a rising growth-cost curve: the very first unit still
        costs exactly HERD_GROWTH_COST (herd_size == 0), and each unit
        after that costs marginally more, reflecting real land/logistics
        constraints on scaling a herd rather than a flat per-unit price
        forever."""
        return HERD_GROWTH_COST + self.herd_size * HERD_GROWTH_COST_SLOPE

    def grow_herd(self):
        cost = self.grow_herd_cost()
        if self.funds < cost:
            return False
        self.funds -= cost
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

    def counterfactual_pressure_fraction(self):
        return min(MAX_PRESSURE, self.counterfactual_methane / PRESSURE_SCALE)

    def counterfactual_score(self):
        """F1/F3/F13 — the pure-growth counterfactual's own score, using
        the exact same formula as score() so the two numbers are directly
        comparable."""
        return self.counterfactual_funds - self.counterfactual_methane * METHANE_PENALTY_WEIGHT

    def advance_round(self):
        fraction = self.plant_based_fraction()
        income_multiplier = (1 - fraction) + fraction * PLANT_BASED_INCOME_MULTIPLIER
        raw_income = self.herd_size * HERD_INCOME_PER_UNIT * income_multiplier
        pressure = self.pressure_fraction()
        self.funds += raw_income * (1 - pressure)
        self.methane += self.methane_this_round()
        self.max_pressure_fraction_seen = max(self.max_pressure_fraction_seen, pressure)

        # Counterfactual: same herd_size, but baseline (fully-coupled)
        # emissions and no plant-pivot income multiplier — never mirrors
        # decoupling/pivot spend, so the comparison isolates whether that
        # spend paid for itself.
        counterfactual_pressure = self.counterfactual_pressure_fraction()
        counterfactual_raw_income = self.herd_size * HERD_INCOME_PER_UNIT
        self.counterfactual_funds += counterfactual_raw_income * (1 - counterfactual_pressure)
        self.counterfactual_methane += self.herd_size * BASE_COUPLING_RATIO

        self.round_number += 1
        self.methane_history.append(self.methane)

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


def coupling_gauge_svg(fraction):
    """Semi-circle dial gauge: 0 = fully decoupled (green), 1 = fully
    coupled at baseline (red). Iteration-pass addition — the single
    most prominent UI element, replacing a plain ratio number with an
    at-a-glance dial for the mechanic the whole lesson depends on."""
    fraction = max(0.0, min(1.0, fraction))
    color = _lerp_color(GAUGE_LOW_COLOR, GAUGE_HIGH_COLOR, fraction)
    dash = fraction * 100
    return (
        '<svg viewBox="0 0 120 66" class="coupling-gauge-svg">'
        '<path d="M 10 60 A 50 50 0 0 1 110 60" class="gauge-track" pathLength="100" />'
        f'<path d="M 10 60 A 50 50 0 0 1 110 60" class="gauge-fill" pathLength="100" '
        f'stroke="{color}" stroke-dasharray="{dash:.1f} 100" />'
        "</svg>"
    )


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
        real_world_comparison_message(),
    ]
    return "".join(f'<p class="status-line summary-line">{line}</p>' for line in lines)


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


# F15 — surfacing the real documented ~42% methane-intensity-reduction
# figure (also cited in INFO_PAGE) as a live in-game comparison.
def real_world_comparison_message():
    pct = farm.decoupled_fraction() * 100
    real_pct = REAL_WORLD_REDUCTION_FRACTION * 100
    if farm.decoupled_fraction() >= REAL_WORLD_REDUCTION_FRACTION:
        return (
            f"You've cut emissions intensity by {pct:.0f}% — matching or beating the real "
            f"~{real_pct:.0f}% reduction documented on real farms."
        )
    return (
        f"You've cut emissions intensity by {pct:.0f}% so far — real farms have documented "
        f"a ~{real_pct:.0f}% reduction through better practices."
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
    income_delta = HERD_INCOME_PER_UNIT * income_multiplier * (1 - farm.pressure_fraction())
    return (
        f"Next unit: costs {cost:.0f}, adds ~{income_delta:.1f} income/round and "
        f"+{methane_delta:.2f} methane/round."
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
        "You've cut your emissions-per-herd-unit ratio 50% below baseline — decoupling is "
        "working, without shrinking your herd."
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


def render():
    render_info_page()
    coupling_fraction = farm.coupling_ratio() / BASE_COUPLING_RATIO
    document.getElementById("coupling-gauge").innerHTML = coupling_gauge_svg(coupling_fraction)
    document.getElementById("coupling-gauge-label").innerText = (
        f"Emissions per herd unit: {farm.coupling_ratio():.2f} methane/round"
    )

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
    grow_button.disabled = farm.funds < grow_cost
    # F9 — consequence preview next to the Grow Herd button.
    document.getElementById("grow-consequence-preview").innerText = grow_consequence_message()

    for measure, spec in DECOUPLING_MEASURES.items():
        document.getElementById(f"{measure}-name").innerText = f"{spec['icon']} {spec['label']}"
        document.getElementById(f"{measure}-count").innerText = str(
            farm.decoupling_investment[measure]
        )
        button = document.getElementById(f"{measure}-invest-button")
        button.innerText = f"{spec['label']} ({spec['cost']})"
        button.disabled = farm.funds < spec["cost"]

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

    # Achievements panel, kept in sync if left open across a render.
    update_achievements_display()

    # F2 — pasture visual cow count scales with real herd size.
    update_pasture_visual()


def on_grow_herd(event=None):
    if farm.grow_herd():
        _pulse("grow-herd-button")
    render()
    _check_new_achievements_for_toast()


def _make_decoupling_handler(measure):
    def handler(event=None):
        if farm.invest_decoupling(measure):
            _pulse(f"{measure}-count")
        render()
        _check_new_achievements_for_toast()
    return handler


def _confirm_dialog_ask(action_id, message, confirm_label, on_confirm):
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
    confirm_dialog.ask(
        id=action_id,
        message=message,
        confirmLabel=confirm_label,
        onConfirm=create_proxy(on_confirm),
    )


def on_invest_plant_pivot(event=None):
    # F16 (planning/TODO.md's shared confirmation-dialog goal) -- this is
    # the pricier of the two decoupling investments (25, vs. 15/20/20 for
    # feed/caps/capture) and, unlike those three, it changes *what* the
    # herd produces rather than just how efficiently -- worth a beat of
    # confirmation before committing funds to it. Pre-action confirm
    # only, per the shared pattern's own shape (no undo window); a player
    # who invests repeatedly can check "don't ask again" once.
    def do_invest():
        if farm.invest_plant_pivot():
            _pulse("plant-pivot-count")
        render()
        _check_new_achievements_for_toast()

    _confirm_dialog_ask(
        action_id="herd-plant-pivot-invest",
        message=(
            f"Invest {PLANT_PIVOT_COST} funds in the Plant-Based Pivot? "
            "It shifts part of your herd's output to near-zero-methane "
            "plant-based production, at a small ongoing income cost."
        ),
        confirm_label="Invest",
        on_confirm=do_invest,
    )


def on_advance_round(event=None):
    farm.advance_round()
    render()
    _check_milestone_callout()
    _check_new_achievements_for_toast()


# SAVE-BUTTON-INTEGRATION.md contract for the shared shared/save-widget.js:
# get_state() returns every module-level mutable game-state field as one
# plain, JSON-safe dict, and load_state() is its exact inverse. SOL is the
# reference integration for this contract. decoupling_investment is copied
# (not handed back by reference) so continued play after taking a
# "snapshot" can't silently mutate it, same reasoning as SOL's
# serialize_state() docstring. info_page_open is deliberately excluded —
# it's a cosmetic panel toggle, not tracked game progress.
def get_state():
    return {
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
        "achievements_earned": achievement_ids_earned(),
    }


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
    render()
    _seed_achievement_toast_baseline()


setup()
