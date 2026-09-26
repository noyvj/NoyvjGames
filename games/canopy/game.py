"""Canopy — Deforestation & Carbon Sinks Game.

Runs in-browser via Pyodide. Milestone 1: grid of forest plots with a
state machine (PRESERVED/BARE/REPLANTING/RECOVERED) and click-driven
Clear/Replant actions. Milestone 2: passive standing value that compounds
the longer a plot stays PRESERVED/RECOVERED. Payout economics and soil
degradation land in later milestones.
"""

import copy
import json

import info_page
from js import document, setInterval, setTimeout
from pyodide.ffi import create_proxy

# B13 (planning/TODO.md "Per-game: Canopy"): a larger-grid option as a
# difficulty/length variant, selectable via reset_session() below. GRID_ROWS/
# GRID_COLS are deliberately mutable module globals rather than true
# constants -- a size change rebuilds `plots` at the new dimensions.
# "normal" (6x6 = 36) stays the default at import time so every existing
# test/tutorial reference to "36 plots" is unaffected unless a player (or a
# loaded save) explicitly picks "large" (9x8 = 72, double the plot count for
# a longer session). GRID_COLS stays under 26 for both presets so
# plot_coordinate_label()'s A..Z column-letter scheme never needs to wrap.
GRID_SIZE_PRESETS = {
    "small": (4, 4),
    "normal": (6, 6),
    "large": (9, 8),
}
current_grid_size = "normal"
GRID_ROWS, GRID_COLS = GRID_SIZE_PRESETS[current_grid_size]
TICK_INTERVAL_MS = 1000

# Standing value accrued per tick at ticks_intact == 0 is BASE_ACCRUAL *
# (1 + GROWTH_PER_TICK); the multiplier itself grows every subsequent tick,
# so patience is rewarded increasingly rather than at a flat rate.
BASE_ACCRUAL = 1.0
GROWTH_PER_TICK = 0.05

# Soil degradation: each clear on a given plot permanently lowers that
# plot's future productivity. Never fully to zero — a plot always keeps
# some minimum ability to regrow, matching the site's "no dead-end states"
# philosophy.
DEGRADE_PER_CLEAR = 0.1
MIN_PRODUCTIVITY_MULTIPLIER = 0.2

# B7: "forest ranger" harder difficulty -- each clear degrades soil twice as
# steeply. A session-wide setting (changing it resets the session, exactly
# like a grid-size change, since soil quality is derived from clear_count
# and would otherwise silently rewrite every plot's history).
DIFFICULTY_NORMAL = "normal"
DIFFICULTY_RANGER = "ranger"
DEGRADE_PER_CLEAR_BY_DIFFICULTY = {
    DIFFICULTY_NORMAL: DEGRADE_PER_CLEAR,
    DIFFICULTY_RANGER: DEGRADE_PER_CLEAR * 2,
}
current_difficulty = DIFFICULTY_NORMAL


def current_degrade_per_clear():
    return DEGRADE_PER_CLEAR_BY_DIFFICULTY.get(current_difficulty, DEGRADE_PER_CLEAR)


# How many ticks a replanted plot spends in REPLANTING before it
# automatically becomes RECOVERED. A never-cleared plot pays no such
# delay — this is the "slower timeline" the plan calls for.
RECOVERY_TICKS = 10

PRESERVED = "preserved"
BARE = "bare"
REPLANTING = "replanting"
RECOVERED = "recovered"

STATE_LABEL = {
    PRESERVED: "Preserved",
    BARE: "Bare",
    REPLANTING: "Replanting",
    RECOVERED: "Recovered",
}

# Icons ride alongside color so plot state doesn't rely on color alone —
# a small accessibility/legibility pass, not just decoration. B9
# (colorblind-safety, planning/ACHIEVEMENTS... no, planning/TODO.md's
# per-game Canopy section) closed the one gap here: BARE previously had no
# icon at all, meaning it depended on hue alone to read as distinct from a
# young REPLANTING/PRESERVED tile -- see style.css's `.plot-tile.plot-*`
# pattern overlays (also new this pass) for the second, independent
# redundant-coding channel per the Okabe-Ito-audit method (see
# games/continuum/CLAUDE.md's colorblind-safety-audit note for the
# worked example this follows).
STATE_ICON = {
    PRESERVED: "\U0001F332",  # evergreen tree
    BARE: "\U0001FAB5",  # wood log -- was previously blank (hue-only)
    REPLANTING: "\U0001F331",  # seedling
    RECOVERED: "\U0001F333",  # deciduous tree
}

# Which of the two actions are valid from each state. Preserve isn't a
# click action — a PRESERVED/RECOVERED plot accrues passive value simply
# by being left alone (see the plan's "preserve = do nothing" framing).
VALID_ACTIONS = {
    PRESERVED: {"clear"},
    RECOVERED: {"clear"},
    BARE: {"replant"},
    REPLANTING: set(),
}

# States in which a plot accrues standing value each tick.
ACCRUING_STATES = {PRESERVED, RECOVERED}


# B17 (planning/TODO.md "Per-game: Canopy"): a genuine in-game seasonal
# cycle -- distinct from B30's purely decorative real-calendar backdrop
# tint (settings.js's `data-season`, which never touches game math). This
# one is driven by `forest_tick`, a persisted counter (unlike the
# ephemeral `_session_ticks`), so a season boundary survives a save/load
# exactly like any other real game fact instead of resetting on reload.
# Each season applies a modest permanent multiplier to a plot's per-tick
# ECONOMIC growth only -- biodiversity accrual is deliberately untouched,
# so Pass 3's already-tuned wildlife-icon pacing doesn't shift underneath
# a season change.
SEASON_CYCLE_TICKS = 40
SEASONS = ["spring", "summer", "autumn", "winter"]
SEASON_GROWTH_MULTIPLIER = {"spring": 1.10, "summer": 1.00, "autumn": 0.95, "winter": 0.85}
SEASON_ICON = {"spring": "\U0001F331", "summer": "☀️", "autumn": "\U0001F342", "winter": "❄️"}
SEASON_LABEL = {"spring": "Spring", "summer": "Summer", "autumn": "Autumn", "winter": "Winter"}


def current_season():
    return SEASONS[(forest_tick // SEASON_CYCLE_TICKS) % len(SEASONS)]


def current_season_multiplier():
    return SEASON_GROWTH_MULTIPLIER[current_season()]


def ticks_until_next_season():
    return SEASON_CYCLE_TICKS - (forest_tick % SEASON_CYCLE_TICKS)


# Iteration-pass additions: a continuous color gradient per plot (not
# just one flat color per discrete state) so maturity/recovery progress
# is legible at a glance, plus a one-tick "just recovered" flash so the
# REPLANTING -> RECOVERED transition registers as a felt moment.
MATURITY_TICKS = 60

# Iteration Pass 2 — biodiversity sub-meter: a slower, flat (non-
# compounding) accrual separate from economic value, so a long-standing
# plot visibly "has life in it" beyond just being worth more. Represented
# via a wildlife icon once a plot crosses the threshold, not a number to
# read.
#
# Iteration Pass 3 (fun/teaching balance) — threshold lowered from the
# original 1.0 (a 50-tick wait for the first icon) to 0.2 (~10 ticks).
# The old pacing meant the first felt "something is alive here" payoff
# landed well after two stakeholder-tension cycles had already fired,
# leaving the early game's only real beat as a repeat of the same
# decision. Pulling this forward gives players a distinct payoff moment
# inside the first idle stretch instead of after it.
BIODIVERSITY_ACCRUAL_PER_TICK = 0.02
BIODIVERSITY_WILDLIFE_THRESHOLD = 0.2
# The wildlife icon itself is rendered purely via CSS (`.plot-has-wildlife
# ::after`'s content, style.css) once has_wildlife() adds that class — not
# read from a Python-side constant, so none is declared here.

# Iteration Pass 2 — stakeholder tension: periodically, the community
# asks to clear the single most-established standing plot for a stated
# real need. Deliberately not a trap: granting clears the plot (same
# payout as a normal Clear) and nudges community relations up; declining
# keeps the plot standing and nudges relations down a smaller amount —
# neither choice is free, neither is catastrophic, matching the site's
# no-dead-end-states philosophy. Reason cycles deterministically rather
# than by RNG, since nothing else in this game uses randomness.
#
# Iteration Pass 3 (fun/teaching balance) — interval tightened from 20
# ticks to 15. Grant/decline was already the game's clearest skill-bearing
# beat (it forces weighing relations against banking value before the
# community claims your best plot), so making it recur a bit sooner keeps
# the challenge curve paced against a session's growing plot count instead
# of leaving long unbroken waits between it.
STAKEHOLDER_EVENT_INTERVAL_TICKS = 15
STAKEHOLDER_REASONS = ["housing", "farming", "resources"]
STAKEHOLDER_REASON_TEXT = {
    "housing": "the community is asking to clear it for new housing — people need somewhere to live too",
    "farming": "a local family wants to farm it for food security this season",
    "resources": "the community needs timber from it for winter building repairs",
}
STAKEHOLDER_GRANT_RELATIONS_DELTA = 10
STAKEHOLDER_DECLINE_RELATIONS_DELTA = -5
STARTING_COMMUNITY_RELATIONS = 50

# B11 (planning/TODO.md "Per-game: Canopy"): diversify stakeholder requests
# to sometimes offer a positive trade-off instead of only "give up this
# plot or don't." An "incentive" request never asks the player to clear
# anything -- accepting keeps the named plot standing untouched and pays a
# funding bonus + relations boost; declining costs nothing (turning down a
# gift isn't the same as refusing the community's ask for the plot
# itself). Cycles in after every full pass through STAKEHOLDER_REASONS
# (see maybe_trigger_stakeholder_request()) so the original 3-reason
# "clear" cycle finishes before the first incentive ever appears --
# preserves test_stakeholder_reason_cycles_deterministically's exact
# first-3-requests expectation unchanged.
STAKEHOLDER_KIND_CLEAR = "clear"
STAKEHOLDER_KIND_INCENTIVE = "incentive"
STAKEHOLDER_REQUEST_CYCLE_LENGTH = len(STAKEHOLDER_REASONS) + 1  # 3 clear requests, then 1 incentive
STAKEHOLDER_INCENTIVE_REASONS = ["ecotourism", "conservation_grant", "carbon_credit"]
STAKEHOLDER_INCENTIVE_REASON_TEXT = {
    "ecotourism": "a nearby eco-tourism operator wants to feature it on their nature trail if it stays standing",
    "conservation_grant": "a conservation program is offering a small grant to keep it standing",
    "carbon_credit": "a carbon-credit buyer wants to certify it as protected forest",
}
STAKEHOLDER_INCENTIVE_ACCEPT_RELATIONS_DELTA = 10
STAKEHOLDER_INCENTIVE_INCOME_BONUS = 25.0
VETERAN_REQUESTS_SURVIVED = 3  # B22

# B25: an occasional "community grant" -- a fund offers money specifically
# for replanting a bare plot. Rides the incentive slot of the request cycle:
# every second incentive turn (the 8th, 16th, ... request), if any plot is
# bare, the incentive is a replant grant instead. Accepting replants the
# offered plot and pays the grant; declining costs nothing.
STAKEHOLDER_KIND_REPLANT_GRANT = "replant_grant"
REPLANT_GRANT_INCOME_BONUS = 15.0
REPLANT_GRANT_RELATIONS_DELTA = 5


# B21: a plot left standing SPECIALIST_MIN_TICKS_INTACT ticks can be given a
# one-time, permanent specialization. Economic: +25% standing-value accrual.
# Biodiversity: 2.5x biodiversity accrual. Not reversible, and lost with the
# plot if it is ever cleared (clear() resets it).
SPECIALIST_MIN_TICKS_INTACT = 90
SPECIALIZATION_ECONOMIC = "economic"
SPECIALIZATION_BIODIVERSITY = "biodiversity"
SPECIALIST_ECONOMIC_VALUE_MULTIPLIER = 1.25
SPECIALIST_BIODIVERSITY_MULTIPLIER = 2.5
SPECIALIZATION_LABEL = {SPECIALIZATION_ECONOMIC: "economic", SPECIALIZATION_BIODIVERSITY: "biodiversity"}


# B11 (planning/TODO.md "Per-game: Canopy"): a "reforestation partner" --
# an alternate way to replant a Bare plot. (Note: an EARLIER B11 --
# diversifying stakeholder requests with a positive "incentive" offer --
# is what the STAKEHOLDER_KIND_INCENTIVE comments above still reference;
# TODO.md was renumbered after that shipped, and this is the *current*
# B11.) Canopy has no separate resource currency for a partner to
# literally "co-fund", so the trade this offers is time for a permanent
# cut of value instead: the partner halves the recovery wait, in exchange
# for a fixed share of that one planting's future ECONOMIC value (never
# biodiversity). The deal is void the moment the plot is next cleared --
# a fresh partnership has to be struck on the next bare replant.
PARTNER_RECOVERY_TICKS = max(1, RECOVERY_TICKS // 2)
PARTNER_SHARE_RATIO = 0.35


class Plot:
    def __init__(self, index, region="main"):
        self.index = index
        # V-CD-5 (planning/TODO.md section N): which grid this plot belongs
        # to -- "main" (the default) or "highland". Structural, not saved
        # state: it's fixed for a plot's whole lifetime by which list it was
        # constructed into (see highland_plots' construction sites), so
        # _plot_to_dict()/_apply_plot_dict() never need to persist it --
        # reconstructing highland_plots always passes region="highland"
        # again. Drives productivity_multiplier()/accrue_tick()'s region-
        # specific rate multipliers below.
        self.region = region
        self.state = PRESERVED
        self.value = 0.0
        self.ticks_intact = 0
        self.clear_count = 0
        self.replant_ticks_remaining = 0
        self.just_recovered = False
        self.biodiversity = 0.0
        # B4: True once this plot has ever hit "fully mature" (so the leaf
        # burst celebrates that moment exactly once per plot, ever).
        self.mature_celebrated = False
        # B22: how many clear-requests aimed at this plot the player has
        # declined. A plot with 3+ of these and no clears is a "veteran".
        self.requests_survived = 0
        # B21: one-time permanent specialization (None until chosen).
        self.specialization = None
        # B11: 0.0 normally; PARTNER_SHARE_RATIO while this planting was
        # done with a reforestation partner (cleared back to 0.0 on the
        # next clear() -- see that method).
        self.partner_share = 0.0

    def can_specialize(self):
        return (
            self.state in ACCRUING_STATES
            and self.specialization is None
            and self.ticks_intact >= SPECIALIST_MIN_TICKS_INTACT
        )

    def is_veteran(self):
        return self.requests_survived >= VETERAN_REQUESTS_SURVIVED and self.clear_count == 0

    def productivity_multiplier(self):
        """Soil quality factor from past clearing — 1.0 for a never-cleared
        plot, stepping down permanently with each clear, floored so a plot
        never stops producing entirely.

        V-CD-5: a Highland Grove plot's soil degrades HIGHLAND_DEGRADE_
        MULTIPLIER times faster per clear than the main forest's (thin,
        fragile alpine soil erodes faster once disturbed) — main-forest
        plots (region == "main") are completely untouched by this, since
        the multiplier is exactly 1.0 for them."""
        region_degrade_multiplier = HIGHLAND_DEGRADE_MULTIPLIER if self.region == "highland" else 1.0
        # B1: Wetland Forest keeps the main forest's soil rate (its tension
        # is flooding, not erosion) -- so it multiplies by 1.0 here.
        return max(
            MIN_PRODUCTIVITY_MULTIPLIER,
            1 - current_degrade_per_clear() * region_degrade_multiplier * self.clear_count,
        )

    def accrue_tick(self):
        """Advances one tick of passive value growth. No-op outside
        PRESERVED/RECOVERED — bare and replanting plots hold no standing
        value to grow. Returns the value actually added this tick (0.0 on
        the no-op path) so callers (B17's floating "+X" pop) can react to
        a real increase without re-deriving it from before/after value."""
        if self.state not in ACCRUING_STATES:
            return 0.0
        self.ticks_intact += 1
        growth_multiplier = 1 + self.ticks_intact * GROWTH_PER_TICK
        delta = BASE_ACCRUAL * self.productivity_multiplier() * growth_multiplier
        # V-CD-5: Highland Grove compounds HIGHLAND_GROWTH_MULTIPLIER times
        # slower than the main forest (a harsher, shorter high-altitude
        # growing season) — 1.0 (a no-op) for main-forest plots.
        if self.region == "highland":
            delta *= HIGHLAND_GROWTH_MULTIPLIER
        elif self.region == "wetland":  # B1: lush, fast-growing, but floods
            delta *= WETLAND_GROWTH_MULTIPLIER
        delta *= current_season_multiplier()  # B17
        delta *= current_legacy_multiplier()  # B15
        if self.specialization == SPECIALIZATION_ECONOMIC:
            delta *= SPECIALIST_ECONOMIC_VALUE_MULTIPLIER
        if self.partner_share:  # B11: partner's cut comes off the top, permanently
            delta *= 1 - self.partner_share
        self.value += delta
        biodiversity_gain = BIODIVERSITY_ACCRUAL_PER_TICK
        if self.specialization == SPECIALIZATION_BIODIVERSITY:
            biodiversity_gain *= SPECIALIST_BIODIVERSITY_MULTIPLIER
        self.biodiversity += biodiversity_gain
        return delta

    def has_wildlife(self):
        return self.biodiversity >= BIODIVERSITY_WILDLIFE_THRESHOLD

    def clear(self):
        """Harvests this plot's standing value and returns it as a payout
        (None if clearing isn't valid from the current state). Clearing
        also permanently degrades the plot's future productivity."""
        if "clear" not in VALID_ACTIONS[self.state]:
            return None
        payout = self.value
        self.clear_count += 1
        self.state = BARE
        self.value = 0.0
        self.ticks_intact = 0
        self.biodiversity = 0.0
        self.specialization = None
        self.partner_share = 0.0  # B11: a partnership is only good for one planting
        return payout

    def replant(self, partner=False):
        """B11: `partner=True` uses a reforestation partner instead of a
        plain replant -- recovers in PARTNER_RECOVERY_TICKS (half the
        normal wait) but this planting's future economic value permanently
        shares PARTNER_SHARE_RATIO with the partner until the plot is next
        cleared."""
        if "replant" not in VALID_ACTIONS[self.state]:
            return False
        self.state = REPLANTING
        self.replant_ticks_remaining = PARTNER_RECOVERY_TICKS if partner else RECOVERY_TICKS
        self.partner_share = PARTNER_SHARE_RATIO if partner else 0.0
        return True

    def finish_recovery(self):
        """Transitions a REPLANTING plot to RECOVERED."""
        if self.state != REPLANTING:
            return False
        self.state = RECOVERED
        self.replant_ticks_remaining = 0
        self.just_recovered = True
        return True

    def maturity_fraction(self):
        """0..1 — how far this plot is toward "mature" for gradient
        purposes: ticks-intact progress for standing plots, recovery
        countdown progress for replanting ones, zero for bare."""
        if self.state in ACCRUING_STATES:
            return min(1.0, self.ticks_intact / MATURITY_TICKS)
        if self.state == REPLANTING:
            return 1 - (self.replant_ticks_remaining / RECOVERY_TICKS)
        return 0.0

    def advance_recovery(self):
        """Counts down one tick of the replanting timer, auto-completing
        recovery once it reaches zero. No-op outside REPLANTING. Returns
        True exactly when this call caused a REPLANTING -> RECOVERED
        transition, so callers (achievements' `total_recoveries` counter)
        can react to the real event without polling state every tick."""
        if self.state != REPLANTING:
            return False
        self.replant_ticks_remaining -= 1
        if self.replant_ticks_remaining <= 0:
            return self.finish_recovery()
        return False


# B17: plot index -> value gained this tick, for a floating "+X" pop on
# the next render_grid() call. Populated fresh in tick(), consumed (popped)
# by render_grid() so a pop only ever shows for the render right after the
# tick that earned it -- never persisted, never part of get_state().
_pending_value_pops = {}
VALUE_POP_MIN_DELTA = 0.05  # below this a pop would just be visual noise

# B1/B6 (planning/TODO.md "Per-game: Canopy"): session-summary support --
# a running tick count (for B20's counterfactual math) and a bounded
# history of (income, standing_value) samples (for B6's sparkline).
# Deliberately ephemeral: never part of get_state()/load_state(), same
# reasoning as `_pending_value_pops` above -- a loaded save's history
# would be a different, disjoint session's shape, not a continuation of
# this one, so starting fresh on load is more honest than splicing two
# unrelated histories together.
_session_ticks = 0
_value_history = []
VALUE_HISTORY_MAX_POINTS = 120  # ~2 minutes at one point/tick, TICK_INTERVAL_MS==1000

# B13: three parallel per-tick series (biodiversity, standing value, community
# relations) for the report card's small trend graphs. Ephemeral for the same
# reason as _value_history above.
_report_history = []
# B4: plot indices that first hit "fully mature" this tick, consumed by the
# next render_grid() (same one-shot pattern as _pending_value_pops).
_pending_mature_bursts = set()

plots = [Plot(i) for i in range(GRID_ROWS * GRID_COLS)]
selected_index = None
total_income = 0.0

community_relations = STARTING_COMMUNITY_RELATIONS
pending_stakeholder_request = None  # {"plot_index": int, "reason": str} or None
_ticks_since_last_request = 0
_stakeholder_request_count = 0

# New tracked state for achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md §4):
# most of Canopy's catalog is a pure function of state that already exists
# (plots, total_income, community_relations, ...), but a handful of
# achievements are genuinely about something *having happened*, which
# monotonic-but-resettable fields like `plot.clear_count` (never decreases,
# so it already covers "ever cleared") don't all cover on their own. Each
# of these follows the same five-step defensive pattern as SOL's
# `visited_bodies`: a safe default here, mutated only at the real event
# below, added to get_state(), and given a `.get(key, <current>)` fallback
# in load_state() so an older save missing the field just keeps its
# fresh-module default instead of crashing the next render.
total_replants = 0  # incremented in on_replant() on a real replant() call
total_recoveries = 0  # incremented in tick() when advance_recovery() finishes one
plots_with_wildlife_ever = set()  # plot indices that have ever crossed the wildlife threshold
stakeholder_grants_count = 0  # incremented in grant_stakeholder_request()'s real-grant path
stakeholder_declines_count = 0  # incremented in decline_stakeholder_request()'s real-decline path
community_relations_min_ever = STARTING_COMMUNITY_RELATIONS  # lowest community_relations has ever been

# B3/B23/B27: a bounded, persisted event log ("forest history"). Entries are
# {"tick", "kind", "plot", "text"} dicts; `plot` is the main-forest plot
# index the event concerns (or None), which is what B27's adopted-plot
# mini-history filters on. `forest_tick` is its own persisted counter
# rather than reusing `_session_ticks` (deliberately ephemeral, resets on
# load) so entry ticks stay monotonic across a save/load.
FOREST_LOG_MAX_ENTRIES = 200
forest_log = []
forest_tick = 0
adopted_plot_index = None  # B27

# B3 (planning/TODO.md "Per-game: Canopy"): a second, unlockable forest
# region. Deliberately a smaller, simpler, self-contained sibling grid --
# same Plot class and clear/replant/accrue mechanics as the main forest
# (no reason to invent a second economy), but no stakeholder tension and
# no biodiversity tracking of its own; it's a bonus area for a player
# who's already deep into a session, not a second full copy of every
# system. Fixed at HIGHLAND_ROWS x HIGHLAND_COLS regardless of the B13
# grid-size preset chosen for the main forest -- the two are independent
# axes (main-forest size vs. whether the bonus region exists at all).
HIGHLAND_ROWS = 3
HIGHLAND_COLS = 4
HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD = 2000.0

# V-CD-5 (planning/TODO.md section N, completion-audit fix): the original
# B3 idea specified Highland Grove should have genuinely different
# degradation/compounding rates than the main forest, not just a same-
# rules bonus copy. Highland Grove is framed (its lock banner/blurb, its
# mountain iconography, "a smaller, higher grove") as a high-altitude
# ecosystem, so the distinction is grounded in real alpine-ecology
# tradeoffs rather than an arbitrary number: thin alpine soil erodes
# faster once disturbed (soil degrades HIGHLAND_DEGRADE_MULTIPLIER times
# faster per clear than the main forest), while a harsher, shorter
# high-altitude growing season means standing value compounds
# HIGHLAND_GROWTH_MULTIPLIER times slower once a plot is intact. Both
# apply only inside Plot.productivity_multiplier()/accrue_tick() when
# self.region == "highland" -- main-forest plots (region == "main") are
# multiplied by an implicit 1.0 and are byte-for-byte unaffected.
HIGHLAND_DEGRADE_MULTIPLIER = 1.5
HIGHLAND_GROWTH_MULTIPLIER = 0.75

highland_unlocked = False
highland_plots = [Plot(i, region="highland") for i in range(HIGHLAND_ROWS * HIGHLAND_COLS)]
highland_selected_index = None
highland_income = 0.0
# Same leak-prevention pattern as the main grid's `_plot_click_proxies`
# (see render_grid()'s own comment) -- a second, independent dict since
# these track a disjoint set of DOM elements.
_highland_plot_click_proxies = {}

# B1 (planning/TODO.md "Per-game: Canopy"): a third biome, Wetland Forest.
# Same Plot class and clear/replant loop again, but its own tension: it
# grows faster than the main forest (WETLAND_GROWTH_MULTIPLIER) and a flood
# sweeps it on a fixed timer. A flood strips a fraction of every standing
# plot's value -- much less from a plot that has stood a full MATURITY_TICKS
# (deep roots hold the water back) than from a young one -- and silts up
# any plot still replanting, pushing its recovery back. There is a warning
# window before each flood, so the choice is real: harvest a young plot
# now and bank its value, or gamble that it holds. Unlocks (sticky, one-way)
# at a higher standing-value threshold than Highland Grove.
WETLAND_ROWS = 3
WETLAND_COLS = 4
WETLAND_UNLOCK_STANDING_VALUE_THRESHOLD = 5000.0
WETLAND_GROWTH_MULTIPLIER = 1.25
WETLAND_FLOOD_INTERVAL_TICKS = 50
WETLAND_FLOOD_WARNING_TICKS = 10
WETLAND_FLOOD_LOSS_YOUNG = 0.30
WETLAND_FLOOD_LOSS_MATURE = 0.10
WETLAND_FLOOD_SILT_TICKS = 8

wetland_unlocked = False
wetland_plots = [Plot(i, region="wetland") for i in range(WETLAND_ROWS * WETLAND_COLS)]
wetland_selected_index = None
wetland_income = 0.0
wetland_flood_countdown = WETLAND_FLOOD_INTERVAL_TICKS
wetland_floods_survived = 0
wetland_flood_value_lost = 0.0
_wetland_plot_click_proxies = {}


# B2 (planning/TODO.md "Per-game: Canopy"): a "reset session" option, folded
# together with B13's grid-size variant since both mean "rebuild the whole
# session from scratch" -- offering them as two separate controls would just
# mean two code paths doing almost the same thing. Deliberately a hard reset
# with no confirmation dialog: matches the site's "no dead-end states"
# philosophy (nothing here is a save file being destroyed -- that's what the
# separate save-code widget is for) and the shared confirm-dialog pattern
# the TODO's own site-wide goal describes is still just a design, not a
# built component, elsewhere in this file.
def reset_session(grid_size=None, _render_after=True, difficulty=None):
    """Rebuilds every module-level mutable global back to its fresh-start
    default, optionally at a different GRID_SIZE_PRESETS key. Always
    rebuilds `plots` from scratch (even on a same-size reset) rather than
    resetting each existing Plot in place -- simpler than maintaining two
    code paths, and correctness-equivalent since Plot.__init__ already is
    the fresh-plot state. `personal_best` (B14) is deliberately NOT reset
    here -- it's a per-browser best across every session on this device,
    not this session's own state."""
    global plots, GRID_ROWS, GRID_COLS, current_grid_size, _plot_click_proxies
    global selected_index, total_income, community_relations
    global pending_stakeholder_request, _ticks_since_last_request, _stakeholder_request_count
    global total_replants, total_recoveries, plots_with_wildlife_ever
    global stakeholder_grants_count, stakeholder_declines_count, community_relations_min_ever
    global _previously_earned_ids, _session_ticks
    global highland_unlocked, highland_plots, highland_selected_index, highland_income
    global _highland_plot_click_proxies, _reset_confirm_armed
    global wetland_unlocked, wetland_plots, wetland_selected_index, wetland_income
    global wetland_flood_countdown, wetland_floods_survived, wetland_flood_value_lost
    global _wetland_plot_click_proxies
    global forest_log, forest_tick, adopted_plot_index, current_difficulty
    global legacy_multiplier

    # B15: bank this (about-to-end) session's standing value for the next
    # session's legacy bonus, then reload the multiplier so the session
    # that's about to start immediately reflects it -- not just a future
    # page load. Skipped on the very first call (plots is still empty
    # before the module has ever had a session), so there's nothing to
    # bank yet.
    if plots:
        _bank_legacy_value()
        legacy_multiplier = load_legacy_bonus()

    _personal_best_flashed["standing_value"] = False
    _personal_best_flashed["income"] = False
    _reset_confirm_armed = False
    if difficulty is not None:
        if difficulty not in DEGRADE_PER_CLEAR_BY_DIFFICULTY:
            return False
        current_difficulty = difficulty
    if grid_size is not None:
        if grid_size not in GRID_SIZE_PRESETS:
            return False
        current_grid_size = grid_size
    GRID_ROWS, GRID_COLS = GRID_SIZE_PRESETS[current_grid_size]

    # Same leak-prevention discipline as render_grid()'s per-render proxy
    # cleanup -- these proxies' plots are about to be dropped entirely.
    for proxy in _plot_click_proxies.values():
        proxy.destroy()
    _plot_click_proxies = {}

    plots = [Plot(i) for i in range(GRID_ROWS * GRID_COLS)]
    selected_index = None
    total_income = 0.0
    community_relations = STARTING_COMMUNITY_RELATIONS
    pending_stakeholder_request = None
    _ticks_since_last_request = 0
    _stakeholder_request_count = 0
    total_replants = 0
    total_recoveries = 0
    plots_with_wildlife_ever = set()
    stakeholder_grants_count = 0
    stakeholder_declines_count = 0
    community_relations_min_ever = STARTING_COMMUNITY_RELATIONS
    _previously_earned_ids = set()
    _session_ticks = 0
    _value_history.clear()
    _report_history.clear()
    _pending_mature_bursts.clear()
    forest_log = []
    forest_tick = 0
    adopted_plot_index = None

    for proxy in _highland_plot_click_proxies.values():
        proxy.destroy()
    _highland_plot_click_proxies = {}
    highland_unlocked = False
    highland_plots = [Plot(i, region="highland") for i in range(HIGHLAND_ROWS * HIGHLAND_COLS)]
    highland_selected_index = None
    highland_income = 0.0

    for proxy in _wetland_plot_click_proxies.values():
        proxy.destroy()
    _wetland_plot_click_proxies = {}
    wetland_unlocked = False
    wetland_plots = [Plot(i, region="wetland") for i in range(WETLAND_ROWS * WETLAND_COLS)]
    wetland_selected_index = None
    wetland_income = 0.0
    wetland_flood_countdown = WETLAND_FLOOD_INTERVAL_TICKS
    wetland_floods_survived = 0
    wetland_flood_value_lost = 0.0

    if _render_after:
        render()
    return True


# B24: Reset Session now asks first, but only when there is something to
# lose. The first click arms the button and shows exactly what is being
# given up (the current standing value); a second click within
# RESET_CONFIRM_WINDOW_MS confirms. A session with nothing standing worth
# keeping (no standing value, no income) resets immediately, since there is
# nothing to confirm. Never persisted: a stale armed flag across a save/load
# would be a trap.
RESET_CONFIRM_WINDOW_MS = 5000
_reset_confirm_armed = False
_reset_confirm_token = 0


def reset_confirm_label():
    return (
        f"Confirm reset? Gives up {standing_forest_value():.1f} standing value"
        f" and {total_income:.1f} income"
    )


def render_reset_button():
    button = document.getElementById("reset-session-button")
    if button is None:
        return
    button.innerText = reset_confirm_label() if _reset_confirm_armed else "\U0001F504 Reset Session"


def _disarm_reset_confirm(token):
    global _reset_confirm_armed
    if token == _reset_confirm_token and _reset_confirm_armed:
        _reset_confirm_armed = False
        render_reset_button()


def on_reset_session(event=None):
    global _reset_confirm_armed, _reset_confirm_token
    if _reset_confirm_armed:
        _reset_confirm_armed = False
        reset_session()
        return
    if standing_forest_value() <= 0 and total_income <= 0:
        reset_session()
        return
    _reset_confirm_armed = True
    _reset_confirm_token += 1
    token = _reset_confirm_token
    setTimeout(create_proxy(lambda: _disarm_reset_confirm(token)), RESET_CONFIRM_WINDOW_MS)
    render_reset_button()


def on_difficulty_change(event=None):
    """B7: bound to the difficulty <select>; always a full reset, like
    on_grid_size_change()."""
    if event is None:
        return
    reset_session(difficulty=event.target.value)


def on_grid_size_change(event=None):
    """Bound to the grid-size <select>'s "change" event in index.html (see
    setup()) -- `event.target.value` is the chosen preset key ("normal"/
    "large"), same as any real DOM change handler. Changing it always
    triggers a full reset_session() at the new size; there's no meaningful
    way to resize a grid with an in-progress session's plots still on it."""
    if event is None:
        return
    reset_session(grid_size=event.target.value)


def _most_established_plot_index():
    """The standing plot with the highest accrued value — the one a
    stakeholder request targets, since it's the one with the most at
    stake for both sides of the decision."""
    candidates = [p for p in plots if p.state in ACCRUING_STATES and p.value > 0]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.value).index


def _replant_grant_target_index():
    """B25: the bare plot a replant grant would restore -- the one with the
    healthiest soil (most worth restoring), lowest index on ties."""
    bare = [p for p in plots if p.state == BARE]
    if not bare:
        return None
    return max(bare, key=lambda p: (p.productivity_multiplier(), -p.index)).index


def maybe_trigger_stakeholder_request():
    global pending_stakeholder_request, _ticks_since_last_request, _stakeholder_request_count
    if pending_stakeholder_request is not None:
        return
    _ticks_since_last_request += 1
    if _ticks_since_last_request < STAKEHOLDER_EVENT_INTERVAL_TICKS:
        return
    target = _most_established_plot_index()
    if target is None:
        return  # try again next tick once something's actually established
    grant_target = _replant_grant_target_index()
    incentive_slot = _stakeholder_request_count % STAKEHOLDER_REQUEST_CYCLE_LENGTH >= len(STAKEHOLDER_REASONS)
    if (
        incentive_slot
        and grant_target is not None
        and (_stakeholder_request_count // STAKEHOLDER_REQUEST_CYCLE_LENGTH) % 2 == 1
    ):
        pending_stakeholder_request = {
            "plot_index": grant_target,
            "reason": "replant_fund",
            "kind": STAKEHOLDER_KIND_REPLANT_GRANT,
        }
        _stakeholder_request_count += 1
        _ticks_since_last_request = 0
        return
    # B11: a full pass through STAKEHOLDER_REASONS (3 requests) plays out
    # exactly as before, then the 4th request in the cycle is a positive
    # incentive offer instead -- see the constants' own comment above.
    cycle_position = _stakeholder_request_count % STAKEHOLDER_REQUEST_CYCLE_LENGTH
    if cycle_position < len(STAKEHOLDER_REASONS):
        kind = STAKEHOLDER_KIND_CLEAR
        reason = STAKEHOLDER_REASONS[cycle_position]
    else:
        kind = STAKEHOLDER_KIND_INCENTIVE
        incentive_turn = _stakeholder_request_count // STAKEHOLDER_REQUEST_CYCLE_LENGTH
        reason = STAKEHOLDER_INCENTIVE_REASONS[incentive_turn % len(STAKEHOLDER_INCENTIVE_REASONS)]
    pending_stakeholder_request = {"plot_index": target, "reason": reason, "kind": kind}
    _stakeholder_request_count += 1
    _ticks_since_last_request = 0


def stakeholder_request_message():
    if pending_stakeholder_request is None:
        return ""
    idx = pending_stakeholder_request["plot_index"]
    reason = pending_stakeholder_request["reason"]
    label = plot_coordinate_label(idx)
    # .get(), not bare indexing: a request built before B11 (or a manually
    # constructed test fixture) simply lacks "kind" and means "clear", the
    # only kind that existed before.
    kind = pending_stakeholder_request.get("kind", STAKEHOLDER_KIND_CLEAR)
    if kind == STAKEHOLDER_KIND_REPLANT_GRANT:
        return (
            f"Plot {label} is bare, and a community restoration fund is offering a {REPLANT_GRANT_INCOME_BONUS:.0f} "
            "grant specifically to replant it. Accept to start replanting it now, or decline?"
        )
    if kind == STAKEHOLDER_KIND_INCENTIVE:
        return (
            f"Plot {label} is thriving, and {STAKEHOLDER_INCENTIVE_REASON_TEXT[reason]}. "
            "Accept for a relations boost and a funding bonus, or decline and keep your options open?"
        )
    return f"Plot {label} is thriving, but {STAKEHOLDER_REASON_TEXT[reason]}. Grant the request, or decline and keep it standing?"


def _stakeholder_target_is_still_standing():
    """A pending request names its target plot by index, but nothing stops
    the player from selecting that same plot and clicking Clear directly,
    bypassing Grant/Decline entirely. Guards both handlers below against a
    stale request: without this, Grant would hand out its relations bonus
    for free (clear() on an already-BARE plot is a no-op, no real payout),
    and Decline would penalize relations for a plot that isn't standing
    anymore."""
    plot = plots[pending_stakeholder_request["plot_index"]]
    if pending_stakeholder_request.get("kind") == STAKEHOLDER_KIND_REPLANT_GRANT:
        return plot.state == BARE  # B25: the offer is for a plot that must still be bare
    return plot.state in ACCRUING_STATES


def _note_community_relations_change():
    """Tracks the running minimum community_relations has ever reached —
    achievements' `rebuilt_trust` needs to know relations genuinely dropped
    low at some point, not just where they sit right now."""
    global community_relations_min_ever
    community_relations_min_ever = min(community_relations_min_ever, community_relations)


def grant_stakeholder_request(event=None):
    global pending_stakeholder_request, community_relations, total_income
    global stakeholder_grants_count, total_replants
    if pending_stakeholder_request is None:
        return False
    if not _stakeholder_target_is_still_standing():
        pending_stakeholder_request = None
        render()
        return False
    kind = pending_stakeholder_request.get("kind", STAKEHOLDER_KIND_CLEAR)
    if kind == STAKEHOLDER_KIND_REPLANT_GRANT:
        idx = pending_stakeholder_request["plot_index"]
        if plots[idx].replant():
            total_replants += 1
        total_income += REPLANT_GRANT_INCOME_BONUS
        community_relations = min(100, community_relations + REPLANT_GRANT_RELATIONS_DELTA)
        _log_event(
            "replant",
            f"Accepted a replanting grant: replanted {plot_coordinate_label(idx)} (+{REPLANT_GRANT_INCOME_BONUS:.0f})",
            idx,
        )
    elif kind == STAKEHOLDER_KIND_INCENTIVE:
        # B11: the whole point of a positive trade-off is that accepting it
        # does NOT clear the plot -- it stays standing untouched, and the
        # player is rewarded with a relations boost plus a funding bonus
        # that (deliberately unlike a normal Clear) doesn't come from the
        # plot's own standing value.
        community_relations = min(
            100, community_relations + STAKEHOLDER_INCENTIVE_ACCEPT_RELATIONS_DELTA
        )
        total_income += STAKEHOLDER_INCENTIVE_INCOME_BONUS
    else:
        plot = plots[pending_stakeholder_request["plot_index"]]
        payout = plot.clear()
        if payout is not None:
            total_income += payout
            _log_event(
                "clear",
                f"Granted the community's request: cleared {plot_coordinate_label(plot.index)} for {payout:.1f} income",
                plot.index,
            )
        community_relations = min(100, community_relations + STAKEHOLDER_GRANT_RELATIONS_DELTA)
    if kind == STAKEHOLDER_KIND_INCENTIVE:
        idx = pending_stakeholder_request["plot_index"]
        _log_event("preserve", f"Accepted an incentive to keep {plot_coordinate_label(idx)} standing", idx)
    _note_community_relations_change()
    stakeholder_grants_count += 1
    pending_stakeholder_request = None
    render()
    return True


def decline_stakeholder_request(event=None):
    global pending_stakeholder_request, community_relations
    global stakeholder_declines_count
    if pending_stakeholder_request is None:
        return False
    if not _stakeholder_target_is_still_standing():
        pending_stakeholder_request = None
        render()
        return False
    kind = pending_stakeholder_request.get("kind", STAKEHOLDER_KIND_CLEAR)
    if kind not in (STAKEHOLDER_KIND_INCENTIVE, STAKEHOLDER_KIND_REPLANT_GRANT):
        community_relations = max(0, community_relations + STAKEHOLDER_DECLINE_RELATIONS_DELTA)
        # B22/B3: declining a clear-request is a real preserve decision, and
        # the plot survived one more request without ever being cleared.
        idx = pending_stakeholder_request["plot_index"]
        plots[idx].requests_survived += 1
        _log_event("preserve", f"Declined a request to clear {plot_coordinate_label(idx)}: kept it standing", idx)
    # Declining a positive-trade-off incentive costs nothing -- turning down
    # a gift isn't the same as refusing the community's ask for the plot
    # itself, so there's no relations penalty for this kind.
    _note_community_relations_change()
    stakeholder_declines_count += 1
    pending_stakeholder_request = None
    render()
    return True


def _plot_tile_id(index):
    return f"plot-{index}"


# B4 (planning/TODO.md "Per-game: Canopy"): coordinate-style plot labels
# ("A1".."F6") so stakeholder-request messages and plot detail text read as
# a real place on the grid instead of an opaque array index. Columns are
# letters (A..F for GRID_COLS==6), rows are 1-based numbers — the same
# spreadsheet-style convention the TODO's own "C3" example uses. Pure
# presentation over the existing `index = row * GRID_COLS + col` layout;
# no stored state, so it's safe to compute anywhere without touching
# get_state()/load_state().
def plot_coordinate_label(index):
    row, col = divmod(index, GRID_COLS)
    return f"{chr(ord('A') + col)}{row + 1}"


# REVIEW(reuse): byte-identical implementation in games/herd/game.py.
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


# Gradient endpoints per state — bare stays flat (soil, not growth), the
# other two states gradient from a light/young color toward a deep,
# mature one as maturity_fraction() rises.
BARE_COLOR = "#6d4c31"
REPLANTING_START_COLOR = "#9c7a3c"
REPLANTING_END_COLOR = "#8bc34a"
GROWING_START_COLOR = "#8bc34a"
GROWING_END_COLOR = "#1b5e20"


def plot_display_color(plot):
    if plot.state == BARE:
        return BARE_COLOR
    if plot.state == REPLANTING:
        return _lerp_color(REPLANTING_START_COLOR, REPLANTING_END_COLOR, plot.maturity_fraction())
    return _lerp_color(GROWING_START_COLOR, GROWING_END_COLOR, plot.maturity_fraction())


# Per-plot click-handler proxies from the most recent render_grid() call.
# render_grid() rebuilds every tile element from scratch on every render
# (at minimum once per tick, i.e. once a second for the life of a
# session), and each create_proxy() call allocates a persistent
# Python<->JS bridge object that Pyodide never garbage-collects on its
# own. Without tracking and `.destroy()`ing the previous render's proxies,
# the old ones leak indefinitely even though the DOM nodes they were
# attached to are long gone — a slow memory leak over a long play
# session. Keyed by plot index so at most one live proxy per plot exists
# at any time.
_plot_click_proxies = {}


def soil_hint_text(plot):
    """B12: plain-language explanation behind the soil-quality percentage.
    Soil quality is the plot's productivity multiplier: each clear cuts it
    permanently, and standing value grows in proportion to it."""
    pct = round(plot.productivity_multiplier() * 100)
    floor_pct = round(MIN_PRODUCTIVITY_MULTIPLIER * 100)
    step_pct = round(current_degrade_per_clear() * 100)
    return (
        f"Soil quality: this plot's future value grows at {pct}% of the rate of a never-cleared plot. "
        f"Every clear permanently costs {step_pct} points (never below {floor_pct}%), and replanting "
        "does not restore it."
    )


def _plot_tooltip_text(plot):
    """B8: the exact numeric value + degradation level behind a plot tile,
    surfaced via a data attribute a small vanilla-JS listener in index.html
    reads on hover/tap (see that file -- positioning a tooltip near the
    cursor is plain DOM/event work with no game-state logic of its own, so
    it's a documented exception rather than round-tripping through
    Pyodide). Coordinate label first (B4) so the tooltip reads as "which
    plot, in what state, worth what" in one line."""
    soil_pct = round(plot.productivity_multiplier() * 100)
    label = f"{plot_coordinate_label(plot.index)} · {STATE_LABEL[plot.state]} · value {plot.value:.1f} · soil {soil_pct}%"
    if plot.state == REPLANTING:
        label += f" · recovering in {plot.replant_ticks_remaining} ticks"
    if plot.is_veteran():
        label += f" · veteran ({plot.requests_survived} requests survived)"
    if plot.specialization:
        label += f" · {SPECIALIZATION_LABEL[plot.specialization]} specialist"
    if plot.index == adopted_plot_index:
        label += " · adopted"
    return label


# B20: the floating "+X" pop varies by size only (font size + float
# distance in style.css), never by hue, so it adds no color-only meaning
# (consistent with the site's colorblind audit). Thresholds sit against a
# plot's real per-tick delta (~1.05 on a fresh plot, growing ~0.05/tick).
VALUE_POP_MEDIUM_DELTA = 2.0
VALUE_POP_LARGE_DELTA = 4.0


def _value_pop_size_class(delta):
    if delta >= VALUE_POP_LARGE_DELTA:
        return "value-pop--large"
    if delta >= VALUE_POP_MEDIUM_DELTA:
        return "value-pop--medium"
    return "value-pop--small"


LEAF_BURST_COUNT = 6


def _make_tile_mark(class_name, text):
    mark = document.createElement("span")
    mark.className = class_name
    mark.innerText = text
    return mark


def render_grid():
    grid_el = document.getElementById("plot-grid")
    grid_el.innerHTML = ""
    # B16: lets the plain-JS arrow-key handler in index.html know the grid
    # width without hardcoding it a second time in JS.
    grid_el.setAttribute("data-cols", str(GRID_COLS))
    # B13: style.css's `.plot-grid` rule hardcodes `repeat(6, 1fr)` for the
    # "normal" grid shape; an inline style here overrides it (inline style
    # always wins over any class rule, no cascade tricks needed) so the
    # "large" (9x8) preset actually lays out 8 columns instead of silently
    # wrapping at 6. Found live in a real browser -- the fake-DOM pytest
    # suite has no CSS engine to catch a purely visual layout bug like
    # this one.
    grid_el.style.gridTemplateColumns = f"repeat({GRID_COLS}, 1fr)"
    for plot in plots:
        tile = document.createElement("button")
        tile.id = _plot_tile_id(plot.index)
        tile.className = f"plot-tile plot-{plot.state}"
        if plot.index == selected_index:
            tile.className += " plot-selected"
        if plot.just_recovered:
            tile.className += " plot-just-recovered"
            plot.just_recovered = False
        # B19: a distinct "fully mature" cap-off visual once a Recovered
        # plot's maturity_fraction() caps out -- the hope-angle payoff that
        # recovery doesn't just reach parity, it visibly finishes.
        if plot.state == RECOVERED and plot.maturity_fraction() >= 1.0:
            tile.className += " plot-fully-mature"
        tile.title = STATE_LABEL[plot.state]
        tile.innerText = STATE_ICON[plot.state]
        if plot.has_wildlife():
            tile.className += " plot-has-wildlife"
        if plot.is_veteran():
            tile.className += " plot-veteran"
            tile.appendChild(_make_tile_mark("veteran-mark", "\U0001F396\ufe0f"))
        if plot.index == adopted_plot_index:
            tile.className += " plot-adopted"
            tile.appendChild(_make_tile_mark("adopted-mark", "\u2B50"))
        if plot.index in _pending_mature_bursts:
            tile.className += " plot-mature-burst"
            for n in range(LEAF_BURST_COUNT):
                leaf = _make_tile_mark("leaf-burst", "\U0001F343")
                leaf.className = f"leaf-burst leaf-burst--{n}"
                tile.appendChild(leaf)
        tile.style.backgroundColor = plot_display_color(plot)
        tile.setAttribute("data-tooltip", _plot_tooltip_text(plot))
        tile.setAttribute("aria-label", _plot_tooltip_text(plot))
        # B17: a brief floating "+X" pop the tick this plot's standing
        # value actually rose, computed by tick() and consumed here once.
        pop_delta = _pending_value_pops.pop(plot.index, None)
        if pop_delta is not None:
            pop = document.createElement("span")
            pop.className = f"value-pop {_value_pop_size_class(pop_delta)}"
            pop.innerText = f"+{pop_delta:.2f}"
            tile.appendChild(pop)
        old_proxy = _plot_click_proxies.pop(plot.index, None)
        if old_proxy is not None:
            old_proxy.destroy()
        proxy = create_proxy(_make_select_handler(plot.index))
        _plot_click_proxies[plot.index] = proxy
        tile.addEventListener("click", proxy)
        grid_el.appendChild(tile)


def render_panel():
    panel_state_el = document.getElementById("selected-plot-state")
    clear_button = document.getElementById("clear-button")
    replant_button = document.getElementById("replant-button")

    soil_el = document.getElementById("soil-hint")
    if selected_index is None:
        panel_state_el.innerText = "No plot selected"
        clear_button.disabled = True
        replant_button.disabled = True
        soil_el.hidden = True
        return

    plot = plots[selected_index]
    detail = f"value {plot.value:.1f}"
    if plot.state == REPLANTING:
        detail = f"recovering in {plot.replant_ticks_remaining} ticks"
    panel_state_el.innerText = (
        f"Plot {plot_coordinate_label(selected_index)}: {STATE_LABEL[plot.state]} ({detail})"
    )
    soil_el.hidden = False
    soil_el.innerText = f"Soil {round(plot.productivity_multiplier() * 100)}% ?"
    soil_el.title = soil_hint_text(plot)
    clear_button.disabled = "clear" not in VALID_ACTIONS[plot.state]
    replant_button.disabled = "replant" not in VALID_ACTIONS[plot.state]


# ===========================================================================
# Highland Grove -- B3's second, unlockable forest region (planning/
# TODO.md "Per-game: Canopy"). Reuses the Plot class and its clear/
# replant/accrue_tick() mechanics directly (same rules, same math); this
# section is the region-specific plumbing (its own grid, selection,
# income, and rendering) layered on top.
# ===========================================================================


def _maybe_unlock_highland():
    """Checked once per tick(). A sticky, one-way unlock -- once the main
    forest's standing value has ever crossed the threshold, Highland Grove
    stays unlocked even if that value later drops (e.g. the player clears
    plots afterward), matching this game's no-dead-end-states philosophy:
    unlocking a region is a permanent milestone, not a live gate that
    could lock back up mid-session."""
    global highland_unlocked
    if not highland_unlocked and standing_forest_value() >= HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD:
        highland_unlocked = True
        _log_event("unlock", "Highland Grove unlocked", None)


def highland_plot_coordinate_label(index):
    """B4's coordinate-label convention, applied to Highland Grove's own
    (smaller) grid -- uses HIGHLAND_COLS, not GRID_COLS, so a Highland
    tile's letter wraps at the right width for its own 4-wide grid rather
    than the main forest's."""
    row, col = divmod(index, HIGHLAND_COLS)
    return f"{chr(ord('A') + col)}{row + 1}"


def highland_standing_value():
    return sum(plot.value for plot in highland_plots)


def _highland_tooltip_text(plot):
    """Highland Grove's own version of _plot_tooltip_text() -- same shape,
    but using highland_plot_coordinate_label() so the label matches this
    grid's own width."""
    soil_pct = round(plot.productivity_multiplier() * 100)
    label = f"{highland_plot_coordinate_label(plot.index)} · {STATE_LABEL[plot.state]} · value {plot.value:.1f} · soil {soil_pct}%"
    if plot.state == REPLANTING:
        label += f" · recovering in {plot.replant_ticks_remaining} ticks"
    return label


def _make_highland_select_handler(index):
    def handler(event):
        highland_select_plot(index)
    return handler


def highland_select_plot(index):
    global highland_selected_index
    highland_selected_index = index
    render()


def on_highland_clear(event=None):
    global highland_income
    if highland_selected_index is None:
        return
    payout = highland_plots[highland_selected_index].clear()
    if payout is not None:
        highland_income += payout
    render()


def on_highland_replant(event=None):
    if highland_selected_index is None:
        return
    highland_plots[highland_selected_index].replant()
    render()


def render_highland_grid():
    grid_el = document.getElementById("highland-plot-grid")
    grid_el.innerHTML = ""
    grid_el.setAttribute("data-cols", str(HIGHLAND_COLS))
    # See render_grid()'s identical line for why this inline override is
    # needed on top of style.css's shared `.plot-grid` rule (B13's real-
    # browser-only bug, fixed for the main grid and applied here from the
    # start rather than repeating the same discovery).
    grid_el.style.gridTemplateColumns = f"repeat({HIGHLAND_COLS}, 1fr)"
    for plot in highland_plots:
        tile = document.createElement("button")
        tile.id = f"highland-plot-{plot.index}"
        tile.className = f"plot-tile plot-{plot.state}"
        if plot.index == highland_selected_index:
            tile.className += " plot-selected"
        if plot.just_recovered:
            tile.className += " plot-just-recovered"
            plot.just_recovered = False
        if plot.state == RECOVERED and plot.maturity_fraction() >= 1.0:
            tile.className += " plot-fully-mature"
        tile.title = STATE_LABEL[plot.state]
        tile.innerText = STATE_ICON[plot.state]
        tile.style.backgroundColor = plot_display_color(plot)
        tile.setAttribute("data-tooltip", _highland_tooltip_text(plot))
        tile.setAttribute("aria-label", _highland_tooltip_text(plot))
        old_proxy = _highland_plot_click_proxies.pop(plot.index, None)
        if old_proxy is not None:
            old_proxy.destroy()
        proxy = create_proxy(_make_highland_select_handler(plot.index))
        _highland_plot_click_proxies[plot.index] = proxy
        tile.addEventListener("click", proxy)
        grid_el.appendChild(tile)


def render_highland_panel():
    state_el = document.getElementById("highland-selected-plot-state")
    clear_button = document.getElementById("highland-clear-button")
    replant_button = document.getElementById("highland-replant-button")

    if highland_selected_index is None:
        state_el.innerText = "No plot selected"
        clear_button.disabled = True
        replant_button.disabled = True
        return

    plot = highland_plots[highland_selected_index]
    detail = f"value {plot.value:.1f}"
    if plot.state == REPLANTING:
        detail = f"recovering in {plot.replant_ticks_remaining} ticks"
    state_el.innerText = (
        f"Plot {highland_plot_coordinate_label(highland_selected_index)}: {STATE_LABEL[plot.state]} ({detail})"
    )
    clear_button.disabled = "clear" not in VALID_ACTIONS[plot.state]
    replant_button.disabled = "replant" not in VALID_ACTIONS[plot.state]


def render_highland_stats():
    document.getElementById("highland-income-display").innerText = f"Harvested income: {highland_income:.1f}"
    document.getElementById("highland-standing-value-display").innerText = (
        f"Standing grove value: {highland_standing_value():.1f}"
    )


def render_highland_section():
    """Shows a locked-progress banner until HIGHLAND_UNLOCK_STANDING_VALUE_
    THRESHOLD is crossed, then swaps to the actual playable section --
    same optional-reveal spirit as every other panel in this game, except
    this one *starts* inaccessible rather than merely collapsed."""
    banner = document.getElementById("highland-lock-banner")
    section = document.getElementById("highland-section")
    bar = document.getElementById("highland-unlock-progress")
    if banner is None or section is None:
        return
    if not highland_unlocked:
        section.hidden = True
        banner.hidden = False
        progress = min(standing_forest_value(), HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD)
        # B6: the unlock is a visible progress bar toward the threshold,
        # not just a fraction in text.
        bar.hidden = False
        bar.max = HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD
        bar.value = progress
        banner.innerText = (
            "⛰️ Highland Grove is locked — reach "
            f"{HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD:.0f} standing forest value in your "
            f"main forest to unlock a second region ({progress:.0f}/"
            f"{HIGHLAND_UNLOCK_STANDING_VALUE_THRESHOLD:.0f})."
        )
        return
    banner.hidden = True
    bar.hidden = True
    section.hidden = False
    render_highland_grid()
    render_highland_panel()
    render_highland_stats()


# ===========================================================================
# Wetland Forest -- B1's third region. Same shape as Highland Grove above
# (own grid, selection, income), plus the flood timer described at
# WETLAND_ROWS.
# ===========================================================================


def _maybe_unlock_wetland():
    global wetland_unlocked, wetland_flood_countdown
    if not wetland_unlocked and standing_forest_value() >= WETLAND_UNLOCK_STANDING_VALUE_THRESHOLD:
        wetland_unlocked = True
        wetland_flood_countdown = WETLAND_FLOOD_INTERVAL_TICKS
        _log_event("unlock", "Wetland Forest unlocked", None)


def wetland_plot_coordinate_label(index):
    row, col = divmod(index, WETLAND_COLS)
    return f"{chr(ord('A') + col)}{row + 1}"


def wetland_standing_value():
    return sum(plot.value for plot in wetland_plots)


def wetland_flood_loss_fraction(plot):
    """Share of a standing plot's value the next flood would strip: mature
    plots (a full MATURITY_TICKS intact) hold the water back far better
    than young ones. 0.0 for a plot holding no standing value."""
    if plot.state not in ACCRUING_STATES:
        return 0.0
    return WETLAND_FLOOD_LOSS_MATURE if plot.ticks_intact >= MATURITY_TICKS else WETLAND_FLOOD_LOSS_YOUNG


def wetland_flood_warning_active():
    return wetland_unlocked and wetland_flood_countdown <= WETLAND_FLOOD_WARNING_TICKS


def apply_wetland_flood():
    """Sweeps every wetland plot once. Returns the total value stripped."""
    global wetland_floods_survived, wetland_flood_value_lost
    lost = 0.0
    for plot in wetland_plots:
        if plot.state in ACCRUING_STATES:
            loss = plot.value * wetland_flood_loss_fraction(plot)
            plot.value -= loss
            lost += loss
        elif plot.state == REPLANTING:
            plot.replant_ticks_remaining = min(
                RECOVERY_TICKS, plot.replant_ticks_remaining + WETLAND_FLOOD_SILT_TICKS
            )
    wetland_floods_survived += 1
    wetland_flood_value_lost += lost
    _log_event("flood", f"Wetland flood: {lost:.1f} standing value swept away", None)
    return lost


def _advance_wetland_tick():
    """One tick of the wetland: grow/recover every plot, then run the flood
    timer. Only called once the region is unlocked."""
    global wetland_flood_countdown
    for plot in wetland_plots:
        plot.accrue_tick()
        plot.advance_recovery()
    wetland_flood_countdown -= 1
    if wetland_flood_countdown <= 0:
        apply_wetland_flood()
        wetland_flood_countdown = WETLAND_FLOOD_INTERVAL_TICKS


def _wetland_tooltip_text(plot):
    soil_pct = round(plot.productivity_multiplier() * 100)
    label = f"{wetland_plot_coordinate_label(plot.index)} · {STATE_LABEL[plot.state]} · value {plot.value:.1f} · soil {soil_pct}%"
    if plot.state == REPLANTING:
        label += f" · recovering in {plot.replant_ticks_remaining} ticks"
    loss = wetland_flood_loss_fraction(plot)
    if loss:
        label += f" · flood would cost {round(loss * 100)}%"
    return label


def _make_wetland_select_handler(index):
    def handler(event):
        wetland_select_plot(index)
    return handler


def wetland_select_plot(index):
    global wetland_selected_index
    wetland_selected_index = index
    render()


def on_wetland_clear(event=None):
    global wetland_income
    if wetland_selected_index is None:
        return
    payout = wetland_plots[wetland_selected_index].clear()
    if payout is not None:
        wetland_income += payout
    render()


def on_wetland_replant(event=None):
    if wetland_selected_index is None:
        return
    wetland_plots[wetland_selected_index].replant()
    render()


def render_wetland_grid():
    grid_el = document.getElementById("wetland-plot-grid")
    grid_el.innerHTML = ""
    grid_el.setAttribute("data-cols", str(WETLAND_COLS))
    grid_el.style.gridTemplateColumns = f"repeat({WETLAND_COLS}, 1fr)"
    warning = wetland_flood_warning_active()
    for plot in wetland_plots:
        tile = document.createElement("button")
        tile.id = f"wetland-plot-{plot.index}"
        tile.className = f"plot-tile plot-{plot.state}"
        if plot.index == wetland_selected_index:
            tile.className += " plot-selected"
        if plot.just_recovered:
            tile.className += " plot-just-recovered"
            plot.just_recovered = False
        if plot.state == RECOVERED and plot.maturity_fraction() >= 1.0:
            tile.className += " plot-fully-mature"
        if warning and wetland_flood_loss_fraction(plot) >= WETLAND_FLOOD_LOSS_YOUNG:
            tile.className += " plot-flood-risk"
        tile.title = STATE_LABEL[plot.state]
        tile.innerText = STATE_ICON[plot.state]
        tile.style.backgroundColor = plot_display_color(plot)
        tile.setAttribute("data-tooltip", _wetland_tooltip_text(plot))
        tile.setAttribute("aria-label", _wetland_tooltip_text(plot))
        old_proxy = _wetland_plot_click_proxies.pop(plot.index, None)
        if old_proxy is not None:
            old_proxy.destroy()
        proxy = create_proxy(_make_wetland_select_handler(plot.index))
        _wetland_plot_click_proxies[plot.index] = proxy
        tile.addEventListener("click", proxy)
        grid_el.appendChild(tile)


def render_wetland_panel():
    state_el = document.getElementById("wetland-selected-plot-state")
    clear_button = document.getElementById("wetland-clear-button")
    replant_button = document.getElementById("wetland-replant-button")

    if wetland_selected_index is None:
        state_el.innerText = "No plot selected"
        clear_button.disabled = True
        replant_button.disabled = True
        return

    plot = wetland_plots[wetland_selected_index]
    detail = f"value {plot.value:.1f}"
    if plot.state == REPLANTING:
        detail = f"recovering in {plot.replant_ticks_remaining} ticks"
    state_el.innerText = (
        f"Plot {wetland_plot_coordinate_label(wetland_selected_index)}: {STATE_LABEL[plot.state]} ({detail})"
    )
    clear_button.disabled = "clear" not in VALID_ACTIONS[plot.state]
    replant_button.disabled = "replant" not in VALID_ACTIONS[plot.state]


def wetland_flood_status_text():
    if wetland_flood_warning_active():
        return f"🌊 Flood warning — water arrives in {wetland_flood_countdown} ticks. Young plots (highlighted) would lose {round(WETLAND_FLOOD_LOSS_YOUNG * 100)}%."
    return f"Next flood in {wetland_flood_countdown} ticks · floods survived: {wetland_floods_survived}"


def render_wetland_stats():
    document.getElementById("wetland-income-display").innerText = f"Harvested income: {wetland_income:.1f}"
    document.getElementById("wetland-standing-value-display").innerText = (
        f"Standing wetland value: {wetland_standing_value():.1f}"
    )
    document.getElementById("wetland-flood-status").innerText = wetland_flood_status_text()


def render_wetland_section():
    banner = document.getElementById("wetland-lock-banner")
    section = document.getElementById("wetland-section")
    bar = document.getElementById("wetland-unlock-progress")
    if banner is None or section is None:
        return
    if not wetland_unlocked:
        section.hidden = True
        # Only tease this third region once the second one is open, so the
        # early game doesn't stack two locked banners.
        banner.hidden = not highland_unlocked
        bar.hidden = not highland_unlocked
        progress = min(standing_forest_value(), WETLAND_UNLOCK_STANDING_VALUE_THRESHOLD)
        bar.max = WETLAND_UNLOCK_STANDING_VALUE_THRESHOLD
        bar.value = progress
        banner.innerText = (
            "🌊 Wetland Forest is locked — reach "
            f"{WETLAND_UNLOCK_STANDING_VALUE_THRESHOLD:.0f} standing forest value in your "
            f"main forest to open a lush but flood-prone third region ({progress:.0f}/"
            f"{WETLAND_UNLOCK_STANDING_VALUE_THRESHOLD:.0f})."
        )
        return
    banner.hidden = True
    bar.hidden = True
    section.hidden = False
    render_wetland_grid()
    render_wetland_panel()
    render_wetland_stats()


# B14 (planning/TODO.md "Per-game: Canopy"): a per-browser "personal
# best" for both of the game's own two axes (standing value, harvested
# income), persisted via localStorage. Deliberately NOT part of
# get_state()/the save-code system -- this tracks the best this *browser*
# has ever seen across every session/save on this device, not one save's
# snapshot, the same distinction B14's other quartet-game equivalents
# (Tide's D13, Thaw's G19) draw.
PERSONAL_BEST_STORAGE_KEY = "canopy_personal_best_v1"

# Z6 (planning/TODO.md "Z. Games"): how long the shared
# .personal-best-display.just-improved pulse (shared/personal-best.css)
# stays on before self-removing -- matches the CSS animation's own
# duration so the class is gone right as the pulse finishes.
PERSONAL_BEST_BADGE_MS = 1800


def _read_local_storage_item(key):
    """Lazy `import js` (same convention as _read_achievements_json()) so
    this file stays importable outside a real browser. Broad except on
    the actual read/write below is deliberate: a real browser can refuse
    localStorage access entirely (private-browsing mode in some
    browsers), surfaced as a JS exception with no stable Python type to
    catch narrowly -- this feature is a nice-to-have, not core gameplay,
    so it degrades to "no personal best recorded" rather than crashing
    the module import the way _read_achievements_json()'s own docstring
    describes for that feature."""
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


def load_personal_best():
    """Reads the stored best (standing_value, income) pair, defaulting to
    zeros if nothing is stored yet, storage is unavailable, or the stored
    value is malformed (e.g. hand-edited or from a future incompatible
    format)."""
    raw = _read_local_storage_item(PERSONAL_BEST_STORAGE_KEY)
    if not raw:
        return {"standing_value": 0.0, "income": 0.0}
    try:
        data = json.loads(raw)
        return {
            "standing_value": float(data.get("standing_value", 0.0)),
            "income": float(data.get("income", 0.0)),
        }
    except (ValueError, TypeError, AttributeError):
        return {"standing_value": 0.0, "income": 0.0}


personal_best = load_personal_best()

# Z6: one-shot-per-session guard so _maybe_update_personal_best() flashes
# the badge exactly once per axis per session, not on every tick after the
# stored best is first beaten -- see that function's docstring.
_personal_best_flashed = {"standing_value": False, "income": False}

# B15 (planning/TODO.md "Per-game: Canopy"): "legacy forest" -- a fresh
# session starts with a small permanent economic-growth bonus based on
# the standing forest value the *previous* session ended with, banked to
# localStorage the moment reset_session() wipes state for a new one --
# same per-browser pattern as personal_best above. A first-ever session
# has nothing banked yet, so it starts at the neutral 1.0 multiplier
# (this is what makes it "opt-in" in practice: nothing changes until a
# real session has actually ended once). Built independently of any
# shared cross-game meta-progression module, per planning/TODO.md's Z3
# resolution ("better to let each game build its own").
LEGACY_STORAGE_KEY = "canopy_legacy_forest_v1"
LEGACY_BONUS_PER_BANKED_VALUE = 0.0002  # +0.02% growth per 1 banked value point
LEGACY_MAX_BONUS = 0.25  # capped so legacy can never dwarf the base game


def load_legacy_bonus():
    """Reads the banked standing value from the previous session and
    converts it into a growth multiplier, defaulting to 1.0 (no bonus) if
    nothing is banked yet, storage is unavailable, or the stored value is
    malformed."""
    raw = _read_local_storage_item(LEGACY_STORAGE_KEY)
    banked = 0.0
    if raw:
        try:
            banked = max(0.0, float(json.loads(raw).get("banked_value", 0.0)))
        except (ValueError, TypeError, AttributeError):
            banked = 0.0
    return 1.0 + min(LEGACY_MAX_BONUS, banked * LEGACY_BONUS_PER_BANKED_VALUE)


def _bank_legacy_value():
    """Called from reset_session() just before state is wiped -- banks
    this session's final standing value for the *next* session's legacy
    bonus. Replaces whatever was banked before (this session's own most
    recent result, not a lifetime max, matching B15's own "based on a
    previous session's final standing value" wording)."""
    _write_local_storage_item(
        LEGACY_STORAGE_KEY, json.dumps({"banked_value": standing_forest_value()})
    )


legacy_multiplier = load_legacy_bonus()


def current_legacy_multiplier():
    return legacy_multiplier


def render_legacy_bonus():
    element = document.getElementById("legacy-bonus-display")
    if element is None:
        return
    if legacy_multiplier <= 1.0:
        element.innerText = "Legacy bonus: none yet — it's set the first time a session ends."
    else:
        element.innerText = f"Legacy bonus: +{(legacy_multiplier - 1) * 100:.1f}% growth, from your last session's forest."


def _maybe_update_personal_best():
    """Called every render(); bumps + persists personal_best whenever the
    live session exceeds it on either axis. Two independent bests, not
    one combined score -- income vs. standing value is the game's own
    central two-axis comparison, and collapsing them into one number
    would lose exactly the distinction the rest of the game is built
    around.

    Both axes climb every tick during ordinary preserved-plot accrual, so
    once a session has beaten a stored best it would otherwise keep
    re-beating its own just-bumped record on every following tick --
    the flash would spam constantly instead of marking one felt moment.
    `_personal_best_flashed` makes each axis's flash fire at most once per
    session (still comparing against the true stored best, so a session
    that beats it on both axes in the same tick still only flashes once)."""
    standing_value = standing_forest_value()
    persist = False
    flash = False
    if standing_value > personal_best["standing_value"]:
        personal_best["standing_value"] = standing_value
        persist = True
        if not _personal_best_flashed["standing_value"]:
            _personal_best_flashed["standing_value"] = True
            flash = True
    if total_income > personal_best["income"]:
        personal_best["income"] = total_income
        persist = True
        if not _personal_best_flashed["income"]:
            _personal_best_flashed["income"] = True
            flash = True
    if persist:
        _write_local_storage_item(PERSONAL_BEST_STORAGE_KEY, json.dumps(personal_best))
    if flash:
        _flash_personal_best_badge()


def _flash_personal_best_badge():
    """Z6: briefly adds the shared .just-improved class (see
    shared/personal-best.css) right when a session beats its stored best,
    then removes it after PERSONAL_BEST_BADGE_MS -- the actual "badge"
    moment, distinct from render_personal_best()'s always-on label text.
    Same setTimeout+create_proxy shape as the achievement toast below."""
    element = document.getElementById("personal-best-display")
    if element is None:
        return
    element.classList.add("just-improved")

    def _unflash():
        el = document.getElementById("personal-best-display")
        if el is not None:
            el.classList.remove("just-improved")

    setTimeout(create_proxy(_unflash), PERSONAL_BEST_BADGE_MS)


def render_personal_best():
    element = document.getElementById("personal-best-display")
    if element is None:
        return
    element.innerText = (
        f"Personal best: standing {personal_best['standing_value']:.1f} "
        f"· income {personal_best['income']:.1f}"
    )


def standing_forest_value():
    """Live sum of standing value across every plot — only PRESERVED and
    RECOVERED plots hold nonzero value at any given moment."""
    return sum(plot.value for plot in plots)


# B10 (planning/TODO.md "Per-game: Canopy"): biodiversity was previously
# only legible indirectly (the wildlife icon threshold on individual
# tiles) — this surfaces it as one explicit number next to standing value,
# same "comparison, not just a meter" spirit as income vs. standing value.
def total_biodiversity():
    return sum(plot.biodiversity for plot in plots)


def biodiversity_rate_per_tick():
    """B10: how fast total biodiversity is rising right now -- every
    standing (PRESERVED/RECOVERED) plot adds the same flat
    BIODIVERSITY_ACCRUAL_PER_TICK, so the rate is just that times the
    standing-plot count. Zero when nothing is standing."""
    return sum(1 for plot in plots if plot.state in ACCRUING_STATES) * BIODIVERSITY_ACCRUAL_PER_TICK


def state_breakdown():
    """Count of plots in each state — the grid-level session summary."""
    counts = {PRESERVED: 0, BARE: 0, REPLANTING: 0, RECOVERED: 0}
    for plot in plots:
        counts[plot.state] += 1
    return counts


def state_breakdown_text():
    counts = state_breakdown()
    return (
        f"{counts[PRESERVED]} preserved · {counts[BARE]} bare · "
        f"{counts[REPLANTING]} replanting · {counts[RECOVERED]} recovered"
    )


# ===========================================================================
# Session Summary (B1/B6/B18/B20, planning/TODO.md "Per-game: Canopy") --
# a player-triggered panel recapping the session, same "optional, never
# forced" pattern as the info page. Reuses stats that already exist
# elsewhere in this module; the two pieces genuinely new here are B20's
# counterfactual (below) and B6's sparkline (render_session_summary()).
# ===========================================================================


def _ideal_accrual_for_ticks(n):
    """The standing value a single never-cleared, never-degraded plot
    would have accrued after `n` ticks of full PRESERVED accrual -- i.e.
    Plot.accrue_tick()'s own formula (BASE_ACCRUAL * productivity_
    multiplier() * (1 + ticks_intact * GROWTH_PER_TICK)) summed over
    ticks_intact = 1..n with productivity_multiplier() fixed at 1.0 (no
    clearing, so no soil degradation).

    B17/B15 made the per-tick multiplier season-dependent (and scaled by a
    session-constant legacy bonus), so the old closed-form arithmetic-sum
    no longer matches accrue_tick()'s real formula -- season changes every
    SEASON_CYCLE_TICKS, breaking the single-ratio assumption a closed form
    needs. Looping is the only way to stay exact; tick() runs at ~1/sec so
    even an hours-long session is a few thousand cheap iterations, run only
    on demand when the summary panel is opened (never per-tick).

    `start_tick` is forest_tick's value when *this session* began -- tick()
    increments forest_tick before calling accrue_tick(), so the season in
    effect during the plot's j-th accrual this session was whatever
    current_season() would have returned at absolute forest_tick
    (start_tick + j)."""
    if n <= 0:
        return 0.0
    start_tick = forest_tick - _session_ticks
    total = 0.0
    for j in range(1, n + 1):
        season = SEASONS[((start_tick + j) // SEASON_CYCLE_TICKS) % len(SEASONS)]
        total += BASE_ACCRUAL * (1 + j * GROWTH_PER_TICK) * SEASON_GROWTH_MULTIPLIER[season]
    return total * current_legacy_multiplier()


def counterfactual_standing_value():
    """B20's hope-angle counterfactual: what the *entire* grid would be
    worth right now if every plot had been left standing, untouched, since
    the session began -- the "if you'd done this from day one" comparison
    CLAUDE.md's hope-angle section calls for. Deliberately every plot at
    the *current* grid size, not a fixed 36 -- a "large" (B13) session
    compares against its own larger ideal."""
    return len(plots) * _ideal_accrual_for_ticks(_session_ticks)


def counterfactual_message():
    """The closing line itself. Framed as a comparison, not a scolding —
    matching this game's no-dead-end-states, no-wrong-answer philosophy;
    clearing plots for quick income is a legitimate playstyle, not a
    mistake to be corrected."""
    if _session_ticks == 0:
        return "Not enough time has passed yet to compare against a fully-preserved forest."
    ideal = counterfactual_standing_value()
    if ideal <= 0:
        return ""
    actual = standing_forest_value()
    if actual >= ideal - 0.5:
        return (
            f"Your standing forest ({actual:.1f}) is right around what every plot would be "
            f"worth if none had ever been cleared ({ideal:.1f}) — patience paid off in full."
        )
    pct = max(0, round((actual / ideal) * 100))
    return (
        f"If every plot had been left standing since the start, this forest would be worth "
        f"about {ideal:.1f} by now — your actual standing value ({actual:.1f}) is {pct}% of that, "
        f"a {100 - pct}% difference."
    )


# B6: a small inline SVG sparkline built directly as a markup string
# (assigned via innerHTML) rather than a chain of createElement calls --
# simplest way to draw two polylines from `_value_history`, and this
# element is replaced wholesale on every summary render anyway (same
# rebuild-from-scratch approach render_grid() already uses for its tiles).
SPARKLINE_WIDTH = 260
SPARKLINE_HEIGHT = 60
SPARKLINE_INCOME_COLOR = "#e8a33d"
SPARKLINE_STANDING_COLOR = "#4caf50"


def _sparkline_points(series, max_value):
    """Maps a list of values onto SVG viewport coordinates -- x spread
    evenly left-to-right, y scaled so 0 sits on the baseline and
    `max_value` sits at the top. A flat (all-zero, or single-point)
    series still renders as a flat line along the baseline rather than
    dividing by zero."""
    if not series:
        return ""
    denominator = max(max_value, 1e-9)
    step = SPARKLINE_WIDTH / max(1, len(series) - 1)
    points = []
    for i, value in enumerate(series):
        x = i * step
        y = SPARKLINE_HEIGHT - (value / denominator) * SPARKLINE_HEIGHT
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def session_history_svg():
    """Returns "" (rather than an empty/degenerate <svg>) once there's no
    history yet -- render_session_summary() shows a plain "not enough
    data yet" message instead in that case."""
    if not _value_history:
        return ""
    incomes = [point[0] for point in _value_history]
    standing_values = [point[1] for point in _value_history]
    max_value = max(max(incomes, default=0.0), max(standing_values, default=0.0))
    income_points = _sparkline_points(incomes, max_value)
    standing_points = _sparkline_points(standing_values, max_value)
    return (
        f'<svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}" '
        f'class="session-sparkline" role="img" '
        f'aria-label="Income and standing value over the session">'
        f'<polyline points="{standing_points}" fill="none" '
        f'stroke="{SPARKLINE_STANDING_COLOR}" stroke-width="2" />'
        f'<polyline points="{income_points}" fill="none" '
        f'stroke="{SPARKLINE_INCOME_COLOR}" stroke-width="2" />'
        f"</svg>"
    )


# B18: a short, plain-text shareable summary -- deliberately NOT a
# decodable save code (that's the separate shared/save-widget.js system);
# this is just bragging-rights text a player can paste somewhere, same
# spirit as SOL's A8 "shareable my solar system end-state summary card".
def share_snippet():
    standing_value = standing_forest_value()
    counts = state_breakdown()
    standing_plots = counts[PRESERVED] + counts[RECOVERED]
    return (
        f"\U0001F332 Canopy — my forest so far: {standing_value:.1f} standing value, "
        f"{total_income:.1f} harvested, {total_biodiversity():.1f} biodiversity. "
        f"{standing_plots}/{len(plots)} plots still standing."
    )


# B7 (planning/TODO.md "Per-game: Canopy"): save/compare two named
# playstyle runs. Per-browser via localStorage -- same mechanism and same
# "deliberately NOT part of get_state()" reasoning as B14's personal
# best, since these are standalone comparison snapshots a player takes on
# purpose, not live state to resume a session from. reset_session() does
# NOT clear these, matching personal_best's own cross-session lifetime.
PLAYSTYLE_RUNS_STORAGE_KEY = "canopy_playstyle_runs_v1"
PLAYSTYLE_RUN_SLOTS = ("a", "b")


def load_playstyle_runs():
    raw = _read_local_storage_item(PLAYSTYLE_RUNS_STORAGE_KEY)
    if not raw:
        return {"a": None, "b": None}
    try:
        data = json.loads(raw)
        return {slot: data.get(slot) for slot in PLAYSTYLE_RUN_SLOTS}
    except (ValueError, TypeError, AttributeError):
        return {"a": None, "b": None}


playstyle_runs = load_playstyle_runs()


def _playstyle_run_snapshot():
    """What gets frozen into a slot -- a plain, JSON-safe dict of the
    stats worth comparing across two different playstyles (one leaning
    quick-clear, one leaning preserve-everything, say)."""
    counts = state_breakdown()
    return {
        "income": total_income,
        "standing_value": standing_forest_value(),
        "biodiversity": total_biodiversity(),
        "plots_standing": counts[PRESERVED] + counts[RECOVERED],
        "plots_total": len(plots),
        "grid_size": current_grid_size,
    }


def save_playstyle_run(slot, event=None):
    global playstyle_runs
    if slot not in PLAYSTYLE_RUN_SLOTS:
        return False
    playstyle_runs = dict(playstyle_runs)
    playstyle_runs[slot] = _playstyle_run_snapshot()
    _write_local_storage_item(PLAYSTYLE_RUNS_STORAGE_KEY, json.dumps(playstyle_runs))
    render_session_summary()
    return True


def on_save_playstyle_run_a(event=None):
    save_playstyle_run("a")


def on_save_playstyle_run_b(event=None):
    save_playstyle_run("b")


def _playstyle_stat_row(label, key):
    def cell(run):
        if run is None:
            return "—"
        value = run[key]
        return f"{value:.1f}" if isinstance(value, float) else str(value)

    return (
        f"<tr><td>{label}</td>"
        f"<td>{cell(playstyle_runs.get('a'))}</td>"
        f"<td>{cell(playstyle_runs.get('b'))}</td></tr>"
    )


def playstyle_comparison_html():
    """"" (rather than an empty/degenerate <table>) once neither slot has
    ever been saved -- render_playstyle_comparison() shows a plain prompt
    instead in that case, same convention as session_history_svg()."""
    if playstyle_runs.get("a") is None and playstyle_runs.get("b") is None:
        return ""

    def plots_cell(run):
        return "—" if run is None else f"{run['plots_standing']}/{run['plots_total']}"

    rows = "".join(
        [
            _playstyle_stat_row("Income", "income"),
            _playstyle_stat_row("Standing value", "standing_value"),
            _playstyle_stat_row("Biodiversity", "biodiversity"),
            "<tr><td>Plots standing</td>"
            f"<td>{plots_cell(playstyle_runs.get('a'))}</td>"
            f"<td>{plots_cell(playstyle_runs.get('b'))}</td></tr>",
        ]
    )
    return (
        '<table class="playstyle-comparison-table">'
        "<thead><tr><th></th><th>Run A</th><th>Run B</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def render_playstyle_comparison():
    container = document.getElementById("session-summary-playstyle-comparison")
    if container is None:
        return
    html = playstyle_comparison_html()
    if html:
        container.innerHTML = html
    else:
        container.innerHTML = ""
        container.innerText = "Save a run below to start comparing playstyles."


session_summary_open = False


def on_toggle_session_summary(event=None):
    global session_summary_open
    session_summary_open = not session_summary_open
    render_session_summary()


def render_session_summary():
    toggle = document.getElementById("session-summary-toggle-button")
    panel = document.getElementById("session-summary-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide Session Summary" if session_summary_open else "\U0001F4CB Session Summary"
    panel.hidden = not session_summary_open
    if not session_summary_open:
        return

    document.getElementById("session-summary-counterfactual").innerText = counterfactual_message()

    sparkline_container = document.getElementById("session-summary-sparkline")
    svg = session_history_svg()
    if svg:
        sparkline_container.innerHTML = svg
    else:
        sparkline_container.innerHTML = ""
        sparkline_container.innerText = "Not enough time has passed yet to chart a trend."

    document.getElementById("session-summary-share-text").innerText = share_snippet()
    render_playstyle_comparison()
    render_report_card()
    render_forest_log_panels()


def comparison_message(income, standing_value):
    """The hope-angle payoff: a plain-language read on how short-term
    harvesting stacks up against the value of what's still standing."""
    if income == 0 and standing_value == 0:
        return "Nothing harvested or grown yet — clear a plot for quick income, or leave one standing to watch its value compound."
    if standing_value > income:
        return (
            f"Your standing forest ({standing_value:.1f}) is worth more than everything "
            f"you've harvested ({income:.1f}) — patience is compounding."
        )
    if income > standing_value:
        return (
            f"You've harvested more ({income:.1f}) than your forest currently holds "
            f"({standing_value:.1f}) — quick income, but nothing left compounding."
        )
    return f"Harvested income and standing forest value are evenly matched, at {income:.1f}."


def render_stats():
    standing_value = standing_forest_value()
    document.getElementById("income-display").innerText = f"Harvested income: {total_income:.1f}"
    document.getElementById("standing-value-display").innerText = f"Standing forest value: {standing_value:.1f}"
    document.getElementById("biodiversity-display").innerText = (
        f"Biodiversity: {total_biodiversity():.1f} (+{biodiversity_rate_per_tick():.2f}/tick)"
    )
    document.getElementById("comparison-message").innerText = comparison_message(total_income, standing_value)
    document.getElementById("state-breakdown-display").innerText = state_breakdown_text()
    document.getElementById("community-relations-display").innerText = (
        f"Community relations: {community_relations}/100"
    )
    _maybe_update_personal_best()
    render_personal_best()
    render_legacy_bonus()


INCENTIVE_MESSAGE_TOOLTIP = (
    "This is a genuinely positive offer: it never asks you to clear anything. "
    "Accepting keeps the plot standing and adds funding and community trust."
)
INCENTIVE_ACCEPT_TOOLTIP = (
    f"Accept: the plot stays standing, +{STAKEHOLDER_INCENTIVE_INCOME_BONUS:.0f} funding, "
    f"+{STAKEHOLDER_INCENTIVE_ACCEPT_RELATIONS_DELTA} community relations."
)
REPLANT_GRANT_ACCEPT_TOOLTIP = (
    f"Accept: replants the bare plot now, +{REPLANT_GRANT_INCOME_BONUS:.0f} funding, "
    f"+{REPLANT_GRANT_RELATIONS_DELTA} community relations."
)
INCENTIVE_DECLINE_TOOLTIP = "Decline: no cost and no relations penalty, the offer just passes."
CLEAR_GRANT_TOOLTIP = (
    f"Grant: clears the plot and banks its value, +{STAKEHOLDER_GRANT_RELATIONS_DELTA} community relations."
)
CLEAR_DECLINE_TOOLTIP = (
    f"Decline: the plot stays standing, {STAKEHOLDER_DECLINE_RELATIONS_DELTA} community relations."
)


def render_stakeholder_panel():
    panel_el = document.getElementById("stakeholder-panel")
    message_el = document.getElementById("stakeholder-message")
    grant_button = document.getElementById("stakeholder-grant-button")
    decline_button = document.getElementById("stakeholder-decline-button")

    if pending_stakeholder_request is None:
        panel_el.hidden = True
        return
    panel_el.hidden = False
    message_el.innerText = stakeholder_request_message()
    # B11: "Accept" reads more naturally than "Grant" for a positive-
    # trade-off offer, where the player isn't granting the community
    # anything -- the community is offering *them* something.
    kind = pending_stakeholder_request.get("kind", STAKEHOLDER_KIND_CLEAR)
    is_replant_grant = kind == STAKEHOLDER_KIND_REPLANT_GRANT
    grant_button.innerText = "Accept" if (kind == STAKEHOLDER_KIND_INCENTIVE or is_replant_grant) else "Grant"
    # B8: an incentive is a gift, not an ask -- say so on hover before the
    # player commits (and on the floating badge, before the panel is even
    # scrolled into view).
    is_incentive = kind == STAKEHOLDER_KIND_INCENTIVE or is_replant_grant
    grant_button.title = (
        REPLANT_GRANT_ACCEPT_TOOLTIP if is_replant_grant
        else INCENTIVE_ACCEPT_TOOLTIP if is_incentive else CLEAR_GRANT_TOOLTIP
    )
    decline_button.title = INCENTIVE_DECLINE_TOOLTIP if is_incentive else CLEAR_DECLINE_TOOLTIP
    message_el.title = INCENTIVE_MESSAGE_TOOLTIP if is_incentive else ""
    badge = document.getElementById("stakeholder-badge")
    if badge is not None:
        badge.innerText = "\U0001F381 Incentive offer" if is_incentive else "\U0001F3D8\ufe0f Pending request"
        badge.title = INCENTIVE_MESSAGE_TOOLTIP if is_incentive else "A community request is waiting for your decision."
    grant_button.disabled = False
    decline_button.disabled = False


# ===========================================================================
# Achievements (planning/ACHIEVEMENTS-SYSTEM-DESIGN.md) — SOL is the
# reference integration for the hub-wide achievements framework; this is
# Canopy's own catalog, grounded in its actual mechanics (plot management,
# soil degradation, biodiversity, stakeholder relations, income vs.
# standing-value playstyle) rather than generic filler.
# ===========================================================================
#
# Every achievement's earned status is a pure function of state that
# already exists elsewhere in this module, recomputed fresh on every call
# — never a separately hand-maintained "earned" flag ("derive, don't
# track", same discipline SOL's own achievements follow). Five checks
# genuinely needed new tracked state (see the module-level declarations
# above, `total_replants` through `community_relations_min_ever`) because
# the thing they measure ("this ever happened") isn't recoverable from
# state that only reflects the *current* moment — e.g. a plot's
# biodiversity resets to 0 the instant it's cleared, so "has any plot ever
# shown wildlife" has no live signal to read without `plots_with_wildlife_
# ever`. Every other check below reads plots/total_income/community_
# relations directly.
ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    """Same loading contract SOL's game.py established (itself following
    Le Champ de Mots' `_read_json_asset()`): the page's boot script
    fetches achievements.json and hands it to Python as a window global
    before this file runs; the pytest harness's fake `js` module simply
    has no such attribute, so this falls through to reading the file
    straight off disk, which keeps the module importable outside a real
    browser."""
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        js = None

    raw = getattr(js, "ACHIEVEMENTS_JSON", None) if js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 — only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, ACHIEVEMENTS_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Defensive per SOL's own note on this pattern: the real Pyodide runtime
# executes this file's fetched text via `pyodide.runPythonAsync(code)`,
# which never defines `__file__` the way a normal file-based import does —
# if `_read_achievements_json()`'s window-global read ever comes back
# empty, its filesystem fallback would crash with a bare NameError that
# takes down this entire module import, not just achievements. Achievements
# are additive, not core to Canopy's own gameplay, so this degrades to "no
# achievements catalog" instead.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []

THRIVING_FOREST_BIODIVERSITY_THRESHOLD = 25.0
STANDING_FORTUNE_THRESHOLD = 1000.0
QUICK_MONEY_THRESHOLD = 1000.0
BALANCED_LEDGER_THRESHOLD = 500.0
TRUE_CONSERVATIONIST_STANDING_THRESHOLD = 300.0
RESOURCEFUL_EXTRACTOR_CLEAR_COUNT = 15
SOIL_SCARRED_CLEAR_COUNT = 5
OLD_GROWTH_GROVE_MATURE_COUNT = 5
BIODIVERSITY_HAVEN_WILDLIFE_COUNT = 10
REBUILT_TRUST_LOW_WATERMARK = 10
REBUILT_TRUST_HIGH_WATERMARK = 50
GENEROUS_HOST_GRANT_COUNT = 10
PRINCIPLED_REFUSAL_DECLINE_COUNT = 10
FLOURISHING_CANOPY_STANDING_THRESHOLD = 500.0


def _total_clear_count():
    return sum(plot.clear_count for plot in plots)


def _max_clear_count():
    return max((plot.clear_count for plot in plots), default=0)


def _mature_plot_count():
    """How many standing (PRESERVED/RECOVERED) plots have reached full
    maturity_fraction() -- i.e. ticks_intact has caught up to
    MATURITY_TICKS, the same threshold the color-gradient rendering caps
    out at."""
    return sum(
        1
        for plot in plots
        if plot.state in ACCRUING_STATES and plot.maturity_fraction() >= 1.0
    )


def _wildlife_active_count():
    return sum(1 for plot in plots if plot.has_wildlife())


def _all_four_states_present():
    counts = state_breakdown()
    return all(counts[state] >= 1 for state in (PRESERVED, BARE, REPLANTING, RECOVERED))


# Each checker is a zero-argument predicate read fresh off live state —
# nothing here is ever cached or hand-flagged.
ACHIEVEMENT_CHECKS = {
    "first_clear": lambda: _total_clear_count() >= 1,
    "first_replant": lambda: total_replants >= 1,
    "first_recovery": lambda: total_recoveries >= 1,
    "standing_tall": lambda: _mature_plot_count() >= 1,
    "old_growth_grove": lambda: _mature_plot_count() >= OLD_GROWTH_GROVE_MATURE_COUNT,
    "wildlife_returns": lambda: len(plots_with_wildlife_ever) >= 1,
    "biodiversity_haven": lambda: _wildlife_active_count() >= BIODIVERSITY_HAVEN_WILDLIFE_COUNT,
    "thriving_forest": lambda: total_biodiversity() >= THRIVING_FOREST_BIODIVERSITY_THRESHOLD,
    "standing_fortune": lambda: standing_forest_value() >= STANDING_FORTUNE_THRESHOLD,
    "quick_money": lambda: total_income >= QUICK_MONEY_THRESHOLD,
    "balanced_ledger": lambda: (
        total_income >= BALANCED_LEDGER_THRESHOLD
        and standing_forest_value() >= BALANCED_LEDGER_THRESHOLD
    ),
    "true_conservationist": lambda: (
        _total_clear_count() == 0
        and standing_forest_value() >= TRUE_CONSERVATIONIST_STANDING_THRESHOLD
    ),
    "resourceful_extractor": lambda: _total_clear_count() >= RESOURCEFUL_EXTRACTOR_CLEAR_COUNT,
    "soil_scarred": lambda: _max_clear_count() >= SOIL_SCARRED_CLEAR_COUNT,
    "community_ally": lambda: community_relations >= 100,
    "rebuilt_trust": lambda: (
        community_relations_min_ever <= REBUILT_TRUST_LOW_WATERMARK
        and community_relations >= REBUILT_TRUST_HIGH_WATERMARK
    ),
    "generous_host": lambda: stakeholder_grants_count >= GENEROUS_HOST_GRANT_COUNT,
    "principled_refusal": lambda: stakeholder_declines_count >= PRINCIPLED_REFUSAL_DECLINE_COUNT,
    "flourishing_canopy": lambda: (
        state_breakdown()[BARE] == 0
        and state_breakdown()[REPLANTING] == 0
        and standing_forest_value() >= FLOURISHING_CANOPY_STANDING_THRESHOLD
    ),
    "every_stage_at_once": lambda: _all_four_states_present(),
    # B3: Highland Grove's own unlock IS the achievement condition -- no
    # extra threshold needed, `highland_unlocked` already is the pure,
    # already-derived boolean this pattern wants.
    "second_growth": lambda: highland_unlocked,
}

# Progress readouts, only for achievements with a natural numeric scale-up
# — a plain earned/not-yet is the honest shape for the rest (one-shot
# milestones like "clear your first plot" don't get a fake "0 of 1").
ACHIEVEMENT_PROGRESS = {
    "old_growth_grove": lambda: (_mature_plot_count(), OLD_GROWTH_GROVE_MATURE_COUNT),
    "biodiversity_haven": lambda: (_wildlife_active_count(), BIODIVERSITY_HAVEN_WILDLIFE_COUNT),
    "thriving_forest": lambda: (
        round(min(total_biodiversity(), THRIVING_FOREST_BIODIVERSITY_THRESHOLD), 1),
        THRIVING_FOREST_BIODIVERSITY_THRESHOLD,
    ),
    "standing_fortune": lambda: (int(standing_forest_value()), int(STANDING_FORTUNE_THRESHOLD)),
    "quick_money": lambda: (int(total_income), int(QUICK_MONEY_THRESHOLD)),
    "resourceful_extractor": lambda: (_total_clear_count(), RESOURCEFUL_EXTRACTOR_CLEAR_COUNT),
    "soil_scarred": lambda: (_max_clear_count(), SOIL_SCARRED_CLEAR_COUNT),
    "generous_host": lambda: (stakeholder_grants_count, GENEROUS_HOST_GRANT_COUNT),
    "principled_refusal": lambda: (stakeholder_declines_count, PRINCIPLED_REFUSAL_DECLINE_COUNT),
}


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field. Always recomputed, never itself a save
    input."""
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

# Tracks the earned-id set as of the last time it was checked, so a fresh
# unlock (one that wasn't in this set last time) can trigger a toast
# without re-toasting every already-earned achievement on every render.
# Reset (without toasting) right after setup()'s initial render and right
# after load_state() applies a save, so neither a fresh game nor a loaded
# one spams toasts for achievements that were already satisfied before
# this render cycle started.
_previously_earned_ids = set()
_toast_hide_proxy = None
_toast_hide_proxy_gen = 0

ACHIEVEMENT_TOAST_DURATION_MS = 4000


def _earned_snapshot():
    return set(achievement_ids_earned())


def show_achievement_toast(message):
    toast = document.getElementById("achievement-toast")
    if toast is None:
        return
    toast.innerText = message
    toast.hidden = False
    toast.classList.add("achievement-toast--visible")

    # Never destroy a still-pending timer's proxy: the browser would later
    # call it and Pyodide throws "Object has already been destroyed". Each
    # timer owns its own proxy and destroys it after firing; a newer toast
    # just bumps the generation so stale timers become no-ops.
    global _toast_hide_proxy_gen
    _toast_hide_proxy_gen += 1
    my_gen = _toast_hide_proxy_gen
    holder = []

    def _hide():
        if my_gen == _toast_hide_proxy_gen:
            toast.classList.remove("achievement-toast--visible")
            toast.hidden = True
        holder[0].destroy()

    holder.append(create_proxy(_hide))
    setTimeout(holder[0], ACHIEVEMENT_TOAST_DURATION_MS)


def _sync_earned_and_toast():
    """Diffs the live earned set against the last-seen snapshot; anything
    newly present gets a toast (batched into one message if several land
    in the same render pass, e.g. several achievements clearing at once on
    a big tick)."""
    global _previously_earned_ids
    current = _earned_snapshot()
    newly_earned_ids = current - _previously_earned_ids
    _previously_earned_ids = current
    if not newly_earned_ids:
        return
    newly_earned = [entry for entry in ACHIEVEMENTS if entry["id"] in newly_earned_ids]
    if not newly_earned:
        return
    if len(newly_earned) == 1:
        message = f"\U0001F3C6 Achievement unlocked: {newly_earned[0]['label']}"
    else:
        labels = ", ".join(entry["label"] for entry in newly_earned)
        message = f"\U0001F3C6 {len(newly_earned)} achievements unlocked: {labels}"
    show_achievement_toast(message)


def on_toggle_achievements(event=None):
    global achievements_open
    achievements_open = not achievements_open
    update_achievements_display()


def update_achievements_display():
    toggle = document.getElementById("achievements-toggle-button")
    panel = document.getElementById("achievements-panel")
    if toggle is None or panel is None:
        return
    earned_count = len(achievement_ids_earned())
    toggle.innerText = (
        f"Hide Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
        if achievements_open
        else f"\U0001F3C6 Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
    )
    panel.hidden = not achievements_open
    if not achievements_open:
        return

    panel.innerHTML = ""
    for entry in achievements_summary():
        card = document.createElement("div")
        card.className = (
            "achievement-card achievement-card--earned" if entry["earned"] else "achievement-card"
        )
        card.dataset.achievementId = entry["id"]

        label = document.createElement("p")
        label.className = "achievement-card-label"
        label.innerText = f"\U0001F3C6 {entry['label']}" if entry["earned"] else entry["label"]
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

    # A link out to the hub-wide achievements dashboard (planning/
    # ACHIEVEMENTS-SYSTEM-DESIGN.md §5, and the "roll achievements out
    # everywhere" TODO's toast+hub-link requirement). Canopy's own
    # achievements.json/panel/get_state() wiring is entirely self-contained
    # here, but registering this game in the *hub's* script.js
    # (GAMES_WITH_ACHIEVEMENTS) is a root-level file outside games/canopy/
    # -- deliberately left as a follow-up so this game's rollout doesn't
    # need to touch shared hub files while other games are being worked on
    # in parallel. The link still works today (it just takes a signed-in
    # visitor to the hub, where Canopy won't appear in the dashboard list
    # until that follow-up lands) and needs no change on this end once it
    # does.
    hub_link = document.createElement("a")
    hub_link.className = "achievements-hub-link"
    hub_link.href = "../../index.html#account-achievements-dashboard"
    hub_link.innerText = "View achievements across every game →"
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
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        js = None

    raw = getattr(js, "CHANGELOG_JSON", None) if js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 — only needed on this filesystem-fallback path

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
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide What's New" if changelog_open else "\U0001F4CB What's New"
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


# ===========================================================================
# B29: a guided, narrated example of a strong preserve/clear balance. Every
# number is computed from the game's own constants by `example_playthrough()`
# (never hand-typed), using the base rules only (no seasons, legacy, grants or
# specializations), so it stays correct if a constant is retuned. It compares
# three ways of running the same 10 plots over the same 120 ticks.
# ===========================================================================
EXAMPLE_PLOTS = 10
EXAMPLE_TICKS = 120
EXAMPLE_HARVESTED_PLOTS = 2


def _example_growth(ticks, clear_count=0):
    """Value a plot gains over `ticks` accruing ticks at a given soil quality."""
    productivity = max(MIN_PRODUCTIVITY_MULTIPLIER, 1 - DEGRADE_PER_CLEAR * clear_count)
    return sum(BASE_ACCRUAL * productivity * (1 + t * GROWTH_PER_TICK) for t in range(1, ticks + 1))


def _example_clearing_plot_total(period, horizon):
    """One plot cleared and replanted the moment it has accrued `period` ticks."""
    total, clock, clears = 0.0, 0, 0
    while clock + period <= horizon:
        total += _example_growth(period, clears)
        clock += period + RECOVERY_TICKS
        clears += 1
    accruing_left = max(0, horizon - clock)
    return total + _example_growth(accruing_left, clears), clears


def example_playthrough():
    """The narrated steps: a list of (title, text)."""
    patient_plot = _example_growth(EXAMPLE_TICKS)
    quick_plot, quick_clears = _example_clearing_plot_total(MATURITY_TICKS // 6, EXAMPLE_TICKS)
    kept = EXAMPLE_PLOTS - EXAMPLE_HARVESTED_PLOTS
    harvest_at = MATURITY_TICKS
    harvested_plot, _ = _example_clearing_plot_total(harvest_at, EXAMPLE_TICKS)
    balanced = kept * patient_plot + EXAMPLE_HARVESTED_PLOTS * harvested_plot
    quick_all = EXAMPLE_PLOTS * quick_plot
    never_clear = EXAMPLE_PLOTS * patient_plot
    return [
        (
            "1. Patience compounds",
            f"A plot left standing earns more each tick than the tick before: after 10 ticks it holds "
            f"{_example_growth(10):.0f}, after {MATURITY_TICKS} it holds {_example_growth(MATURITY_TICKS):.0f}, "
            f"after {EXAMPLE_TICKS} it holds {patient_plot:.0f}. Value grows faster than time, so the last "
            f"stretch of waiting is the best-paid.",
        ),
        (
            "2. Clearing is expensive",
            f"Clearing cashes a plot out, but it then sits bare and replanting for {RECOVERY_TICKS} ticks "
            f"earning nothing, and its soil permanently loses {DEGRADE_PER_CLEAR * 100:.0f}% productivity "
            f"per clear (never below {MIN_PRODUCTIVITY_MULTIPLIER * 100:.0f}%), and its wildlife is gone.",
        ),
        (
            "3. Clearing early backfires",
            f"Clearing every plot every {MATURITY_TICKS // 6} ticks makes {quick_clears} clears per plot and "
            f"totals about {quick_all:.0f} across {EXAMPLE_PLOTS} plots over {EXAMPLE_TICKS} ticks, "
            f"far less than not clearing at all ({never_clear:.0f}).",
        ),
        (
            "4. The balanced run",
            f"Keep {kept} plots standing the whole time and harvest just {EXAMPLE_HARVESTED_PLOTS} once each "
            f"they reach maturity (about tick {harvest_at}), then replant. That totals about {balanced:.0f}: "
            f"nearly all the value of never clearing, with cash in hand at the midpoint to spend on "
            f"community requests and specializations, and most of the forest still growing.",
        ),
        (
            "5. What to copy",
            "Preserve most plots, harvest a few at maturity rather than early, replant straight away, and "
            "spend the cash on the things that reward a standing forest. Clear the same plot repeatedly and "
            "its soil, not the market, becomes the limit.",
        ),
    ]


example_open = False


def on_toggle_example(event=None):
    global example_open
    example_open = not example_open
    update_example_display()


def update_example_display():
    toggle = document.getElementById("example-toggle-button")
    panel = document.getElementById("example-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide example playthrough" if example_open else "\U0001F4D6 Example playthrough"
    panel.hidden = not example_open
    if not example_open:
        return
    panel.innerHTML = ""
    intro = document.createElement("p")
    intro.className = "example-intro"
    intro.innerText = (
        f"A guided example of a strong preserve/clear balance: {EXAMPLE_PLOTS} plots over "
        f"{EXAMPLE_TICKS} ticks, base rules only (no seasons or bonuses). Numbers are worked out from "
        f"the game's own settings."
    )
    panel.appendChild(intro)
    for title, text in example_playthrough():
        row = document.createElement("div")
        row.className = "example-step"
        heading = document.createElement("p")
        heading.className = "example-step-title"
        heading.innerText = title
        row.appendChild(heading)
        body = document.createElement("p")
        body.className = "example-step-text"
        body.innerText = text
        row.appendChild(body)
        panel.appendChild(row)


# Info Page — optional, player-triggered supplement (never forced
# mid-session). Framing is written fresh, not copied from any source;
# sources are the curated real-world backing for the game's mechanics.
INFO_PAGE = {
    "framing": (
        "Standing forests are one of the world's largest active carbon "
        "sinks, and clearing them for quick income is one of the largest "
        "reversible sources of emissions — reversible because forests "
        "left alone, or given light assistance, can recover. Canopy's "
        "core tension, clear it now or let it compound, is a simplified "
        "stand-in for that real land-use tradeoff."
    ),
    "mechanic_tie_in": (
        "Canopy's replant-and-recover path loosely echoes real \"assisted "
        "natural regeneration\" — a genuinely cost-effective restoration "
        "approach, rather than costly full replanting from scratch."
    ),
    "sources": [
        {
            "label": "World Resources Institute — Forests in the IPCC Special Report on Land Use: 7 Things to Know",
            "url": "https://www.wri.org/insights/forests-ipcc-special-report-land-use-7-things-know",
            "note": "Explains why deforestation and forest carbon sinks are two sides of the same coin — maps directly to Canopy's clear/preserve tension.",
        },
        {
            "label": "World Resources Institute — How Effective Is Land At Removing Carbon Pollution? The IPCC Weighs In",
            "url": "https://www.wri.org/insights/how-effective-land-removing-carbon-pollution-ipcc-weighs",
            "note": "Real reforestation carbon-removal potential — grounds the \"replanting works, just slower\" hope angle in actual IPCC figures.",
        },
        {
            "label": "UNFCCC — Land Use, Land-Use Change and Forestry (LULUCF)",
            "url": "https://unfccc.int/topics/land-use/workstreams/land-use--land-use-change-and-forestry-lulucf",
            "note": "The formal policy framework for tracking forest carbon sinks internationally — why Canopy treats plots as carbon-relevant assets, not scenery.",
        },
        {
            "label": "Climate Change Resources — Deforestation & Reforestation",
            "url": "https://climatechangeresources.org/learn-more/science/reforestation-deforestation/",
            "note": "Accessible overview with links to real reforestation organizations, for players who want to go from facts to action.",
        },
    ],
}
info_page_open = False


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


# ===========================================================================
# Forest log (B3 history timeline, B23 wildlife log, B27 adopted plot),
# playstyle badge (B9/B18) and end-of-session report card (B13). All of it
# lives inside the already-opt-in Session Summary panel (collapsible
# <details> sections) so the main screen gains no new always-visible block.
# ===========================================================================

WILDLIFE_SPECIES = [
    ("\U0001F989", "owl"),
    ("\U0001F98A", "fox"),
    ("\U0001F98C", "deer"),
    ("\U0001F438", "frog"),
    ("\U0001F98B", "butterfly"),
    ("\U0001F426", "woodpecker"),
]
FOREST_LOG_DISPLAY_LIMIT = 60


def wildlife_species_for_plot(index):
    """B23: each plot's wildlife is a fixed species (deterministic by plot
    index, no RNG anywhere in this game) so the log can name what arrived."""
    return WILDLIFE_SPECIES[index % len(WILDLIFE_SPECIES)]


def species_seen():
    """B23: the distinct species whose icons have ever appeared, in catalog
    order. Derived from plots_with_wildlife_ever, so it needs no state of its
    own."""
    seen_names = {wildlife_species_for_plot(i)[1] for i in plots_with_wildlife_ever}
    return [sp for sp in WILDLIFE_SPECIES if sp[1] in seen_names]


def _log_event(kind, text, plot_index=None):
    forest_log.append({"tick": forest_tick, "kind": kind, "plot": plot_index, "text": text})
    del forest_log[:-FOREST_LOG_MAX_ENTRIES]


def forest_log_lines(limit=FOREST_LOG_DISPLAY_LIMIT, kinds=None, plot_index=None):
    """Newest-first display strings, optionally filtered by event kind(s) or
    plot."""
    entries = [
        e for e in forest_log
        if (kinds is None or e["kind"] in kinds) and (plot_index is None or e["plot"] == plot_index)
    ]
    return [f"t{e['tick']}: {e['text']}" for e in reversed(entries)][:limit]


# B27 ------------------------------------------------------------------------

def on_adopt_plot(event=None):
    """Toggles adoption of the selected main-forest plot as a personal
    long-term project. One adopted plot at a time."""
    global adopted_plot_index
    if selected_index is None:
        return False
    if adopted_plot_index == selected_index:
        adopted_plot_index = None
    else:
        adopted_plot_index = selected_index
        _log_event("adopt", f"Adopted {plot_coordinate_label(selected_index)} as a long-term project", selected_index)
    render()
    return True


def specialize_selected_plot(kind):
    """B21: applies a one-time permanent specialization to the selected
    main-forest plot. Returns True only on a real change."""
    if selected_index is None or kind not in SPECIALIZATION_LABEL:
        return False
    plot = plots[selected_index]
    if not plot.can_specialize():
        return False
    plot.specialization = kind
    _log_event(
        "specialize",
        f"{plot_coordinate_label(plot.index)} became a {SPECIALIZATION_LABEL[kind]} specialist",
        plot.index,
    )
    render()
    return True


def on_specialize_economic(event=None):
    specialize_selected_plot(SPECIALIZATION_ECONOMIC)


def on_specialize_biodiversity(event=None):
    specialize_selected_plot(SPECIALIZATION_BIODIVERSITY)


def render_specialist_panel():
    row = document.getElementById("specialist-row")
    if row is None:
        return
    plot = plots[selected_index] if selected_index is not None else None
    row.hidden = plot is None or not plot.can_specialize()


def render_adopt_panel():
    button = document.getElementById("adopt-plot-button")
    panel = document.getElementById("adopted-plot-panel")
    if button is None or panel is None:
        return
    button.disabled = selected_index is None
    button.innerText = (
        "\u2B50 Release adopted plot" if selected_index is not None and selected_index == adopted_plot_index
        else "\u2B50 Adopt plot"
    )
    if adopted_plot_index is None:
        panel.hidden = True
        return
    panel.hidden = False
    plot = plots[adopted_plot_index]
    history = forest_log_lines(limit=8, plot_index=adopted_plot_index)
    panel.innerText = (
        f"Adopted plot {plot_coordinate_label(adopted_plot_index)}: {STATE_LABEL[plot.state]}, "
        f"value {plot.value:.1f}, cleared {plot.clear_count}x, soil {round(plot.productivity_multiplier() * 100)}%."
        + (" History: " + " | ".join(history) if history else "")
    )


# B9 / B18 -------------------------------------------------------------------

BADGE_PRESERVATIONIST = "Preservationist"
BADGE_BALANCED = "Balanced"
BADGE_HARVESTER = "Harvester"
BADGE_UNDECIDED = "Undecided"
BADGE_PRESERVATIONIST_MAX_CLEAR_RATIO = 0.25  # clears per plot, below this
BADGE_BALANCED_MAX_CLEAR_RATIO = 0.6
BADGE_ICON = {
    BADGE_PRESERVATIONIST: "\U0001F332",
    BADGE_BALANCED: "\u2696\ufe0f",
    BADGE_HARVESTER: "\U0001FA93",
    BADGE_UNDECIDED: "\u2753",
}


def playstyle_badge():
    """B9: a named playstyle from the session's clear-vs-preserve balance --
    total clears so far as a fraction of the grid's plot count (a clear is
    a plot-clear event, so clearing the same plot twice counts twice, which
    is the honest reading of "how much harvesting"). Undecided until the
    session has any play at all."""
    clears = _total_clear_count()
    if clears == 0 and _session_ticks == 0 and forest_tick == 0:
        return BADGE_UNDECIDED
    ratio = clears / max(1, len(plots))
    if ratio < BADGE_PRESERVATIONIST_MAX_CLEAR_RATIO:
        return BADGE_PRESERVATIONIST
    if ratio < BADGE_BALANCED_MAX_CLEAR_RATIO:
        return BADGE_BALANCED
    return BADGE_HARVESTER


def badge_share_text():
    badge = playstyle_badge()
    return f"{BADGE_ICON[badge]} Canopy playstyle badge: {badge} ({_total_clear_count()} clears across {len(plots)} plots)"


# B13 ------------------------------------------------------------------------

REPORT_CARD_GRAPHS = [
    ("report-card-biodiversity", "Biodiversity", 0, "#4caf50"),
    ("report-card-standing", "Standing value", 1, "#66b2e8"),
    ("report-card-relations", "Community relations", 2, "#e8a33d"),
]


def _report_graph_svg(index, label, color):
    series = [point[index] for point in _report_history]
    if not series:
        return ""
    points = _sparkline_points(series, max(max(series), 1e-9))
    return (
        f'<svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}" class="session-sparkline" '
        f'role="img" aria-label="{label} over the session, now {series[-1]:.1f}">'
        f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2" /></svg>'
    )


def render_report_card():
    for element_id, label, index, color in REPORT_CARD_GRAPHS:
        container = document.getElementById(element_id)
        if container is None:
            continue
        svg = _report_graph_svg(index, label, color)
        if svg:
            container.innerHTML = svg
        else:
            container.innerHTML = ""
            container.innerText = "Not enough time has passed yet to chart a trend."


def render_forest_log_panels():
    badge_el = document.getElementById("session-summary-badge")
    if badge_el is not None:
        badge = playstyle_badge()
        badge_el.innerText = f"{BADGE_ICON[badge]} Playstyle badge: {badge}"
    seen = species_seen()
    wildlife_el = document.getElementById("wildlife-log-list")
    if wildlife_el is not None:
        head = (
            "Species seen ({}/{}): ".format(len(seen), len(WILDLIFE_SPECIES))
            + (" ".join(f"{icon} {name}" for icon, name in seen) if seen else "none yet")
        )
        lines = forest_log_lines(kinds={"wildlife"})
        wildlife_el.innerText = head + ("\n" + "\n".join(lines) if lines else "")
    history_el = document.getElementById("forest-history-list")
    if history_el is not None:
        lines = forest_log_lines()
        history_el.innerText = "\n".join(lines) if lines else "No decisions yet: clear, replant, or decline a request to start the log."


def on_copy_badge_source(event=None):
    """Nothing to do in Python: the copy itself is a plain-JS clipboard call
    (see index.html), which reads the badge text from the DOM."""


# B16 ------------------------------------------------------------------------

def select_stakeholder_plot(event=None):
    """B16: selects the plot named by the pending stakeholder request (bound
    to the "N" key in index.html). Returns the plot index, or None when no
    request is pending."""
    if pending_stakeholder_request is None:
        return None
    index = pending_stakeholder_request["plot_index"]
    select_plot(index)
    return index


def render_grid_size_select():
    """Keeps the grid-size <select> showing whatever preset is actually
    live -- needed because reset_session() can change current_grid_size
    from code paths other than the dropdown itself (a loaded save, e.g.),
    which wouldn't otherwise be reflected back into the control."""
    select = document.getElementById("grid-size-select")
    if select is None:
        return
    select.value = current_grid_size
    difficulty_select = document.getElementById("difficulty-select")
    if difficulty_select is not None:
        difficulty_select.value = current_difficulty


def render():
    render_info_page()
    render_grid()
    render_panel()
    render_stats()
    render_stakeholder_panel()
    render_grid_size_select()
    render_reset_button()
    render_adopt_panel()
    render_specialist_panel()
    render_session_summary()
    render_highland_section()
    render_wetland_section()
    update_achievements_display()
    update_changelog_display()
    _sync_earned_and_toast()


def _make_select_handler(index):
    def handler(event):
        select_plot(index)
    return handler


def select_plot(index):
    global selected_index
    selected_index = index
    render()


def on_clear(event=None):
    global total_income
    if selected_index is None:
        return
    payout = plots[selected_index].clear()
    if payout is not None:
        total_income += payout
        _log_event("clear", f"Cleared {plot_coordinate_label(selected_index)} for {payout:.1f} income", selected_index)
    render()


def on_replant(event=None):
    global total_replants
    if selected_index is None:
        return
    if plots[selected_index].replant():
        total_replants += 1
        _log_event("replant", f"Replanted {plot_coordinate_label(selected_index)}", selected_index)
    render()


def tick(event=None):
    global pending_stakeholder_request, total_recoveries, _session_ticks, forest_tick
    _session_ticks += 1
    forest_tick += 1
    _pending_value_pops.clear()
    _pending_mature_bursts.clear()
    for plot in plots:
        delta = plot.accrue_tick()
        if delta >= VALUE_POP_MIN_DELTA:
            _pending_value_pops[plot.index] = delta
        if plot.advance_recovery():
            total_recoveries += 1
            _log_event("recovered", f"{plot_coordinate_label(plot.index)} finished recovering", plot.index)
        if plot.has_wildlife() and plot.index not in plots_with_wildlife_ever:
            icon, name = wildlife_species_for_plot(plot.index)
            _log_event("wildlife", f"{icon} A {name} appeared at {plot_coordinate_label(plot.index)}", plot.index)
        if plot.has_wildlife():
            plots_with_wildlife_ever.add(plot.index)
        if (
            plot.state in ACCRUING_STATES
            and not plot.mature_celebrated
            and plot.maturity_fraction() >= 1.0
        ):
            plot.mature_celebrated = True
            _pending_mature_bursts.add(plot.index)
            _log_event("mature", f"{plot_coordinate_label(plot.index)} reached full maturity", plot.index)
    if pending_stakeholder_request is not None and not _stakeholder_target_is_still_standing():
        # The requested plot was cleared/replanted directly (see the
        # grant/decline guard above) — drop the now-stale request so a new
        # one can still fire later, instead of maybe_trigger_stakeholder_
        # request() refusing to raise one forever because it sees a
        # (meaningless) request still pending.
        pending_stakeholder_request = None
    maybe_trigger_stakeholder_request()
    # B6: sampled *after* this tick's accrual/payout effects above, so each
    # point reflects the state the player actually saw land this tick,
    # not the stale pre-tick value.
    _value_history.append((total_income, standing_forest_value()))
    _report_history.append((total_biodiversity(), standing_forest_value(), community_relations))
    del _report_history[:-VALUE_HISTORY_MAX_POINTS]
    del _value_history[:-VALUE_HISTORY_MAX_POINTS]  # no-op once under the cap
    # B3: checked every tick regardless of whether it's already unlocked
    # (a no-op once True) -- accrual only starts once unlocked, so a
    # freshly-revealed Highland Grove begins at zero rather than having
    # secretly been growing, invisible, the whole session.
    _maybe_unlock_highland()
    if highland_unlocked:
        for plot in highland_plots:
            plot.accrue_tick()
            plot.advance_recovery()
    _maybe_unlock_wetland()
    if wetland_unlocked:
        _advance_wetland_tick()
    render()


# SAVE-BUTTON-INTEGRATION.md contract for the shared shared/save-widget.js:
# get_state() returns every module-level mutable global as one plain,
# JSON-safe dict, and load_state() is its exact inverse. `plots` is a list
# of Plot objects (not JSON-native) — each is expanded into its own plain
# dict here and restored back onto the existing Plot instances in place
# (rather than rebuilding the list) so nothing else holding a reference
# into `plots` is left stale. `pending_stakeholder_request` is deep-copied
# on the way out so continued play after taking a snapshot can't mutate
# the dict already handed back to the caller. Canopy tracks no sets or
# other non-JSON-native scalar types, unlike SOL's `unlocked_bodies`.
def _plot_to_dict(plot):
    return {
        "index": plot.index,
        "state": plot.state,
        "value": plot.value,
        "ticks_intact": plot.ticks_intact,
        "clear_count": plot.clear_count,
        "replant_ticks_remaining": plot.replant_ticks_remaining,
        "just_recovered": plot.just_recovered,
        "biodiversity": plot.biodiversity,
        "mature_celebrated": plot.mature_celebrated,
        "requests_survived": plot.requests_survived,
        "specialization": plot.specialization,
    }


def _apply_plot_dict(plot, plot_data):
    """Safe-defaulting inverse of _plot_to_dict(): every key falls back to
    the plot's live value, so a save predating any field (mature_celebrated
    and requests_survived are newer than the rest) still loads."""
    plot.index = plot_data.get("index", plot.index)
    plot.state = plot_data.get("state", plot.state)
    plot.value = plot_data.get("value", plot.value)
    plot.ticks_intact = plot_data.get("ticks_intact", plot.ticks_intact)
    plot.clear_count = plot_data.get("clear_count", plot.clear_count)
    plot.replant_ticks_remaining = plot_data.get("replant_ticks_remaining", plot.replant_ticks_remaining)
    plot.just_recovered = plot_data.get("just_recovered", plot.just_recovered)
    plot.biodiversity = plot_data.get("biodiversity", plot.biodiversity)
    plot.mature_celebrated = plot_data.get("mature_celebrated", plot.mature_celebrated)
    plot.requests_survived = plot_data.get("requests_survived", plot.requests_survived)
    saved_spec = plot_data.get("specialization", plot.specialization)
    plot.specialization = saved_spec if saved_spec in SPECIALIZATION_LABEL else None


def _wetland_state_fields():
    """B1: Wetland Forest's own state, written only once the region is open
    (a save that never reached it stays exactly as it was before B1)."""
    if not wetland_unlocked:
        return {}
    return {
        "wetland_unlocked": True,
        "wetland_selected_index": wetland_selected_index,
        "wetland_income": wetland_income,
        "wetland_plots": [_plot_to_dict(plot) for plot in wetland_plots],
        "wetland_flood_countdown": wetland_flood_countdown,
        "wetland_floods_survived": wetland_floods_survived,
        "wetland_flood_value_lost": wetland_flood_value_lost,
    }


def _number_or(value, default, low=0.0, high=None):
    """A finite non-bool number clamped into [low, high], else `default`."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return default
    if value in (float("inf"), float("-inf")):
        return default
    value = max(low, value)
    return value if high is None else min(high, value)


def get_state():
    return {
        "plots": [
            _plot_to_dict(plot)
            for plot in plots
        ],
        "selected_index": selected_index,
        "total_income": total_income,
        "community_relations": community_relations,
        "pending_stakeholder_request": copy.deepcopy(pending_stakeholder_request),
        "_ticks_since_last_request": _ticks_since_last_request,
        "_stakeholder_request_count": _stakeholder_request_count,
        "info_page_open": info_page_open,
        "total_replants": total_replants,
        "total_recoveries": total_recoveries,
        "plots_with_wildlife_ever": sorted(plots_with_wildlife_ever),
        "stakeholder_grants_count": stakeholder_grants_count,
        "stakeholder_declines_count": stakeholder_declines_count,
        "community_relations_min_ever": community_relations_min_ever,
        # B13: which GRID_SIZE_PRESETS key produced the `plots` list above —
        # load_state() needs this *before* it can zip a saved `plots` list
        # onto the live one, since a "large" save loaded into a fresh
        # "normal"-sized module would otherwise silently truncate to 36.
        "current_grid_size": current_grid_size,
        "current_difficulty": current_difficulty,
        "forest_log": copy.deepcopy(forest_log),
        "forest_tick": forest_tick,
        "adopted_plot_index": adopted_plot_index,
        # B3: Highland Grove's own state -- a save predating this feature
        # simply lacks these keys and load_state() treats that as "not
        # unlocked yet, empty grove", the correct pre-B3 truth.
        "highland_unlocked": highland_unlocked,
        "highland_selected_index": highland_selected_index,
        "highland_income": highland_income,
        "highland_plots": [
            _plot_to_dict(plot)
            for plot in highland_plots
        ],
        # Write-only projection (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) — always
        # freshly recomputed here, never read back in load_state() below.
        "achievements_earned": achievement_ids_earned(),
        **_wetland_state_fields(),
    }


# Merges a loaded save onto the live state key-by-key, falling back to the
# current live value for any key the save doesn't carry, rather than bare
# `data["key"]` indexing or a wholesale replace. A save missing a field is
# not necessarily corrupt -- every field here (`biodiversity`,
# `pending_stakeholder_request`, `info_page_open`, ...) was added in a later
# milestone/pass than the one before it, so a save written before that pass
# legitimately lacks the key. Bare indexing would crash the next render/tick
# with a KeyError on exactly that (very real) forward-compatibility case --
# the same bug class found and fixed across nearly every other game in this
# hub (see BCM114-DEV-LOG.md's 2026-09-02 entries).
def load_state(data):
    global selected_index, total_income, community_relations
    global pending_stakeholder_request, _ticks_since_last_request
    global _stakeholder_request_count, info_page_open
    global total_replants, total_recoveries, plots_with_wildlife_ever
    global stakeholder_grants_count, stakeholder_declines_count
    global community_relations_min_ever, _previously_earned_ids
    global highland_unlocked, highland_selected_index, highland_income
    global forest_log, forest_tick, adopted_plot_index
    global wetland_unlocked, wetland_selected_index, wetland_income
    global wetland_flood_countdown, wetland_floods_survived, wetland_flood_value_lost

    # B13: a save written at a different grid size (or a save predating
    # B13 entirely, which simply lacks the key and so implies "normal", the
    # only size that existed before) needs `plots` rebuilt at the matching
    # size *before* the per-plot zip below, or a "large" (72-plot) save
    # loaded into a fresh "normal" (36-plot) module would silently drop the
    # other 36 plots' data instead of restoring them. reset_session()
    # already does exactly that rebuild; skip its own render() since the
    # real one happens at the end of this function once every field below
    # is actually restored.
    saved_grid_size = data.get("current_grid_size", "normal")
    saved_difficulty = data.get("current_difficulty", DIFFICULTY_NORMAL)
    if saved_difficulty not in DEGRADE_PER_CLEAR_BY_DIFFICULTY:
        saved_difficulty = DIFFICULTY_NORMAL
    if (
        saved_grid_size != current_grid_size
        or saved_difficulty != current_difficulty
        or len(data.get("plots", [])) != len(plots)
    ):
        reset_session(grid_size=saved_grid_size, _render_after=False, difficulty=saved_difficulty)

    for plot, plot_data in zip(plots, data.get("plots", [])):
        _apply_plot_dict(plot, plot_data)

    # Forest log / adoption (B3/B23/B27): an older save lacks all three, so
    # the (fresh or reset) live values stand.
    raw_log = data.get("forest_log", forest_log)
    forest_log = [
        {"tick": int(e.get("tick", 0)), "kind": str(e.get("kind", "")), "plot": e.get("plot"), "text": str(e.get("text", ""))}
        for e in raw_log
        if isinstance(e, dict)
    ][-FOREST_LOG_MAX_ENTRIES:]
    forest_tick = data.get("forest_tick", forest_tick)
    adopted_plot_index = data.get("adopted_plot_index", adopted_plot_index)
    if adopted_plot_index is not None and not (0 <= adopted_plot_index < len(plots)):
        adopted_plot_index = None

    selected_index = data.get("selected_index", selected_index)
    total_income = data.get("total_income", total_income)
    community_relations = data.get("community_relations", community_relations)
    pending_stakeholder_request = copy.deepcopy(
        data.get("pending_stakeholder_request", pending_stakeholder_request)
    )
    _ticks_since_last_request = data.get("_ticks_since_last_request", _ticks_since_last_request)
    _stakeholder_request_count = data.get("_stakeholder_request_count", _stakeholder_request_count)
    info_page_open = data.get("info_page_open", info_page_open)

    # Achievements' new tracked state (see the module-level declarations
    # above) — a save predating this feature simply lacks these keys, so
    # each falls back to whatever's already live (the fresh-module
    # default) rather than crashing on a missing key.
    total_replants = data.get("total_replants", total_replants)
    total_recoveries = data.get("total_recoveries", total_recoveries)
    plots_with_wildlife_ever = set(
        data.get("plots_with_wildlife_ever", plots_with_wildlife_ever)
    )
    stakeholder_grants_count = data.get("stakeholder_grants_count", stakeholder_grants_count)
    stakeholder_declines_count = data.get(
        "stakeholder_declines_count", stakeholder_declines_count
    )
    community_relations_min_ever = data.get(
        "community_relations_min_ever", community_relations_min_ever
    )
    # Belt-and-suspenders backfill (same idea as SOL's visited_bodies): an
    # old save predating this field can't have recorded a low watermark,
    # but its restored community_relations value is itself a valid lower
    # bound on what the min-ever must have been.
    community_relations_min_ever = min(community_relations_min_ever, community_relations)

    # B3: Highland Grove's own fields. A save predating this feature
    # simply lacks all four keys -- reset_session() (called above if the
    # grid size differed) already left highland_plots at a fresh 12-plot
    # grid and highland_unlocked False, exactly the correct pre-B3 state,
    # so the .get() fallbacks below are true no-ops for such a save
    # rather than needing special-casing.
    highland_unlocked = data.get("highland_unlocked", highland_unlocked)
    highland_selected_index = data.get("highland_selected_index", highland_selected_index)
    highland_income = data.get("highland_income", highland_income)
    for plot, plot_data in zip(highland_plots, data.get("highland_plots", [])):
        _apply_plot_dict(plot, plot_data)

    # B1: Wetland Forest. Absent keys mean "never reached it" (reset_session
    # above already left a fresh locked region); everything present is
    # validated because a hand-edited or corrupt save must not break ticks.
    wetland_unlocked = data.get("wetland_unlocked") is True
    if not wetland_unlocked:
        # A save that never reached the wetland must not inherit the live
        # session's wetland: put it back to a fresh, locked region.
        wetland_plots[:] = [Plot(i, region="wetland") for i in range(WETLAND_ROWS * WETLAND_COLS)]
        wetland_selected_index = None
        wetland_income = 0.0
        wetland_flood_countdown = WETLAND_FLOOD_INTERVAL_TICKS
        wetland_floods_survived = 0
        wetland_flood_value_lost = 0.0
    else:
        saved_selected = data.get("wetland_selected_index")
        wetland_selected_index = (
            saved_selected
            if isinstance(saved_selected, int) and not isinstance(saved_selected, bool)
            and 0 <= saved_selected < len(wetland_plots)
            else None
        )
        wetland_income = _number_or(data.get("wetland_income"), 0.0)
        wetland_flood_countdown = int(_number_or(
            data.get("wetland_flood_countdown"), WETLAND_FLOOD_INTERVAL_TICKS, 1, WETLAND_FLOOD_INTERVAL_TICKS
        ))
        wetland_floods_survived = int(_number_or(data.get("wetland_floods_survived"), 0))
        wetland_flood_value_lost = _number_or(data.get("wetland_flood_value_lost"), 0.0)
        saved_plots = data.get("wetland_plots")
        for plot, plot_data in zip(wetland_plots, saved_plots if isinstance(saved_plots, list) else []):
            if isinstance(plot_data, dict):
                _apply_plot_dict(plot, plot_data)

    # achievements_earned itself is never read back (write-only, §1) — but
    # the toast-diffing baseline must be reset here, before render() below
    # calls _sync_earned_and_toast(), so a loaded save's already-earned
    # achievements don't all fire toasts on load.
    _previously_earned_ids = _earned_snapshot()

    render()
    return True


def setup():
    clear_button = document.getElementById("clear-button")
    replant_button = document.getElementById("replant-button")
    clear_button.innerText = "Clear"
    replant_button.innerText = "Replant"
    clear_button.addEventListener("click", create_proxy(on_clear))
    replant_button.addEventListener("click", create_proxy(on_replant))
    document.getElementById("stakeholder-grant-button").addEventListener(
        "click", create_proxy(grant_stakeholder_request)
    )
    document.getElementById("stakeholder-decline-button").addEventListener(
        "click", create_proxy(decline_stakeholder_request)
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
    document.getElementById("example-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_example)
    )
    document.getElementById("reset-session-button").addEventListener(
        "click", create_proxy(on_reset_session)
    )
    document.getElementById("session-summary-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_session_summary)
    )
    document.getElementById("specialize-economic-button").addEventListener(
        "click", create_proxy(on_specialize_economic)
    )
    document.getElementById("specialize-biodiversity-button").addEventListener(
        "click", create_proxy(on_specialize_biodiversity)
    )
    document.getElementById("adopt-plot-button").addEventListener(
        "click", create_proxy(on_adopt_plot)
    )
    document.getElementById("save-playstyle-run-a-button").addEventListener(
        "click", create_proxy(on_save_playstyle_run_a)
    )
    document.getElementById("save-playstyle-run-b-button").addEventListener(
        "click", create_proxy(on_save_playstyle_run_b)
    )
    document.getElementById("grid-size-select").addEventListener(
        "change", create_proxy(on_grid_size_change)
    )
    document.getElementById("difficulty-select").addEventListener(
        "change", create_proxy(on_difficulty_change)
    )
    document.getElementById("highland-clear-button").addEventListener(
        "click", create_proxy(on_highland_clear)
    )
    document.getElementById("highland-replant-button").addEventListener(
        "click", create_proxy(on_highland_replant)
    )
    document.getElementById("wetland-clear-button").addEventListener(
        "click", create_proxy(on_wetland_clear)
    )
    document.getElementById("wetland-replant-button").addEventListener(
        "click", create_proxy(on_wetland_replant)
    )
    # Explicit, not just relying on index.html's `hidden` attribute -- the
    # toast element is only otherwise touched by show_achievement_toast()/
    # its own hide callback (unlike every *panel*, which gets its `hidden`
    # state re-set on every render()), so it needs its own starting state
    # set here rather than trusting markup alone.
    toast = document.getElementById("achievement-toast")
    if toast is not None:
        toast.hidden = True
    setInterval(create_proxy(tick), TICK_INTERVAL_MS)
    render()


setup()
