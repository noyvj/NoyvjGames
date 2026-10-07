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
        # GB-4: ticks of Tend growth boost left (0 = not tended). Only one
        # plot is tended at a time; saved as the top-level "tend" key, never
        # per plot, so the plot dict shape stays unchanged.
        self.tend_ticks_left = 0

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
        delta *= current_weather_multiplier()  # GB-23: rain / drought episodes
        delta *= current_perfect_streak_multiplier()  # GB-30: Perfect Season flame
        if self.tend_ticks_left > 0:  # GB-4: a Tended plot grows faster for a few ticks
            delta *= TEND_GROWTH_MULTIPLIER
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
        self.tend_ticks_left = 0  # GB-4: a cleared plot is no longer being tended
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


# ===========================================================================
# GB batch 1 (planning/IMPROVEMENT-IDEAS-ROUND-3.md section GB): golden
# seedling (GB-2), Tend (GB-4), Heart Tree (GB-8), names (GB-14), undo
# (GB-18), rare wildlife (GB-20), standing-value tiers (GB-22), weather
# (GB-23), chain bloom (GB-27), Forest Almanac (GB-28), Perfect Season
# (GB-30). Constants and state live here; the behaviour is in the "GB batch 1"
# section just above render().
#
# Rules kept from the rest of the game: no RNG (a small hash of forest_tick
# stands in wherever a "random" pick is wanted, so runs and tests stay
# deterministic); anything timed rides the 1-second tick (the golden seedling, Tend and the undo
# chip); the only setTimeouts are the brief pulse/flash clean-ups; new
# save keys are written only when non-default and validated on load.
# ===========================================================================
GOLDEN_SEEDLING_TICKS = 4  # GB-2: it stays for about 4 seconds (one tick = 1 s)
GOLDEN_SEEDLING_RECOVERY_TICKS = 4  # recovery progress banked on a click
GOLDEN_SEEDLING_MIN_GAP = 20  # ticks between one seedling and the next...
GOLDEN_SEEDLING_GAP_SPREAD = 25  # ...plus up to this many more (hash-picked)

TEND_DURATION_TICKS = 5  # GB-4
TEND_COOLDOWN_TICKS = 20
TEND_GROWTH_MULTIPLIER = 1.5  # economic accrual on the tended plot; replanting plots recover an extra tick per tick

HEART_TREE_MIN_MATURE_NEIGHBOURS = 7  # GB-8: of the 8 plots around a centre plot
HEART_TREE_AURA_BONUS = 0.10  # extra standing-value growth on the 8 plots around the Heart Tree

FOREST_NAME_MAX = 24  # GB-14
NICKNAME_MAX = 20

UNDO_WINDOW_TICKS = 3  # GB-18: the chip survives 3 full ticks (3 to 4 seconds at 1 tick/s)

BIODIVERSITY_FULL_SCORE = 2.0  # GB-20: "100% biodiversity" for one plot (100 ticks of base accrual)
RARE_STAG_MIN_FRACTION = 0.9
DUSK_TICKS_IN_AUTUMN = 10  # the last 10 ticks of autumn are the night-tinted ones
RARE_FOX_DECLINED_REQUESTS = 3
RARE_WILDLIFE = [
    ("ghost_stag", "\U0001F98C", "ghost stag", "Only at night-tinted late-autumn ticks, on a plot at 90%+ biodiversity."),
    ("wary_fox", "\U0001F98A", "wary fox", "Comes out once you have declined three requests to clear."),
]

STANDING_TIERS = [(1000.0, "Seedling"), (2500.0, "Grove"), (5000.0, "Woodland"), (10000.0, "Old-Growth")]  # GB-22
TIER_ACHIEVEMENT_THRESHOLDS = {"tier_grove": 2500.0, "tier_woodland": 5000.0, "tier_old_growth_steward": 10000.0}
FOREST_PULSE_MS = 1800

WEATHER_BLOCK_TICKS = 32  # GB-23: at most one episode starts per block
WEATHER_DURATION_TICKS = 8
WEATHER_FIRST_TICK = 24  # a fresh forest gets a calm opening
WEATHER_EPISODE_PERCENT = 55  # chance a given block has an episode
WEATHER_RAIN_MULTIPLIER = 1.15
WEATHER_DROUGHT_MULTIPLIER = 0.85
WEATHER_SEASON_KIND = {"spring": "rain", "summer": "drought", "autumn": "rain", "winter": None}
WEATHER_LABEL = {"rain": "Rain", "drought": "Drought"}
WEATHER_ICON = {"rain": "\u2614", "drought": "\U0001F3DC\ufe0f"}

CHAIN_BLOOM_WINDOW_TICKS = 3  # GB-27
CHAIN_BLOOM_MIN_PLOTS = 3
CHAIN_BLOOM_MAX_RANK = 7

PERFECT_SEASON_MIN_RELATIONS = 30  # GB-30
PERFECT_STREAK_BONUS_PER_SEASON = 0.02
PERFECT_STREAK_MAX_BONUS_SEASONS = 5

# ===========================================================================
# GB batch 2 (2026-10-07): challenge runs (GB-17), the Ranger contracts board
# (GB-9), the season forecast (B-12), the request-pace selector (B-6), the
# screen-reader announcer and C/R hotkeys (B-7), the plot tooltip card (B-16),
# and three display options read from localStorage: high-contrast plots
# (B-8), the soil overlay (B-10) and number formats (B-26). Same rules as
# batch 1: no RNG, everything timed rides the 1 s tick, new save keys written
# only when non-default and validated on load.
# ===========================================================================

# --- GB-17: challenge runs ---------------------------------------------------
CHALLENGE_NONE = "none"
CHALLENGE_PACIFIST = "pacifist"
CHALLENGE_SCORCHED = "scorched"
CHALLENGE_SPRINT = "sprint"
CHALLENGE_NO_HIGHLAND = "no_highland"
CHALLENGE_SPECS = {
    CHALLENGE_PACIFIST: {
        "label": "Pacifist",
        "icon": "\U0001F54A️",
        "achievement": "challenge_pacifist",
    },
    CHALLENGE_SCORCHED: {
        "label": "Scorched Start",
        "icon": "\U0001F525",
        "achievement": "challenge_scorched",
    },
    CHALLENGE_SPRINT: {
        "label": "Sprint",
        "icon": "⏱️",
        "achievement": "challenge_sprint",
    },
    CHALLENGE_NO_HIGHLAND: {
        "label": "No-Highland",
        "icon": "\U0001F3D4️",
        "achievement": "challenge_no_highland",
    },
}
CHALLENGE_PACIFIST_STANDING_PER_PLOT = 40  # goals scale with the grid so Small and Large stay fair
CHALLENGE_SCORCHED_STANDING_PER_PLOT = 50
CHALLENGE_NO_HIGHLAND_STANDING_PER_PLOT = 100
CHALLENGE_SPRINT_INCOME_PER_PLOT = 28
CHALLENGE_SPRINT_STANDING_PER_PLOT = 70
CHALLENGE_SPRINT_TICK_LIMIT = 60
CHALLENGE_SCORCHED_BARE_FRACTION = 2 / 3  # two thirds of the plots start bare (soil untouched, so nothing counts as a clear)
CHALLENGE_RECORDS_STORAGE_KEY = "canopy_challenge_records_v1"  # per browser: id -> fastest completion tick
CHALLENGE_ACTIVE = "active"
CHALLENGE_COMPLETE = "complete"
CHALLENGE_FAILED = "failed"

# --- GB-9: Ranger contracts board ---------------------------------------------
CONTRACT_SLOTS = 3
CONTRACT_REFILL_TICKS = 6  # a finished slot stays empty this long before the next contract appears
CONTRACT_REWARD_PER_PLOT = 5  # banked as income, so a 36-plot forest earns 180 a contract
CONTRACT_CALM_TICKS = 30
CONTRACT_TYPES = [
    # (id, icon, short stamp name)
    ("replant", "\U0001F331", "Replanter"),
    ("mature", "\U0001F333", "Elder grove"),
    ("wildlife", "\U0001F98B", "Wildlife warden"),
    ("decline", "✋", "Firm refusal"),
    ("accept", "\U0001F91D", "Good neighbour"),
    ("tend", "\U0001F33F", "Gardener"),
    ("seedling", "✨", "Seedling catcher"),
    ("standing", "\U0001F4C8", "Value grower"),
    ("calm", "\U0001F54A️", "Long peace"),
    ("trust", "\U0001F3D8️", "Village trust"),
]
CONTRACT_RANKS = [(0, "Trainee"), (3, "Ranger"), (8, "Senior ranger"), (15, "Warden"), (25, "Chief warden")]

# --- B-6: how often the village asks ---------------------------------------------
PACE_RELAXED = "relaxed"
PACE_NORMAL = "normal"
PACE_FREQUENT = "frequent"
REQUEST_PACE_FACTOR = {PACE_RELAXED: 1.5, PACE_NORMAL: 1.0, PACE_FREQUENT: 2 / 3}
REQUEST_PACE_LABEL = {PACE_RELAXED: "Relaxed requests", PACE_NORMAL: "Normal requests", PACE_FREQUENT: "Frequent requests"}

# --- B-8 / B-10 / B-26: display options stored per browser (settings.js writes them) ---
UI_PREF_PLOT_CONTRAST = "canopy-plot-contrast"
UI_PREF_SOIL_OVERLAY = "canopy-soil-overlay"
UI_PREF_NUMBER_FORMAT = "canopy-number-format"
NUMBER_FORMAT_STANDARD = "standard"  # one decimal, as the game always showed numbers
NUMBER_FORMAT_GROUPED = "grouped"  # 12,345.6
NUMBER_FORMAT_COMPACT = "compact"  # 12.3k
NUMBER_FORMAT_PRECISE = "precise"  # two decimals
NUMBER_FORMATS = (NUMBER_FORMAT_STANDARD, NUMBER_FORMAT_GROUPED, NUMBER_FORMAT_COMPACT, NUMBER_FORMAT_PRECISE)
STATE_LETTER = {BARE: "B", REPLANTING: "R", PRESERVED: "G", RECOVERED: "G"}  # G = growing; M = mature (below)
MATURE_LETTER = "M"
SOIL_BANDS = [(90, "good"), (70, "fair"), (50, "poor"), (0, "depleted")]

# Saved state (each written only when non-default).
forest_name = ""
adopted_plot_nickname = ""
heart_tree_index = None
rare_wildlife_found = []
peak_standing_value = 0.0
milestone_tier = 0
tend_cooldown_ticks = 0
perfect_streak = 0
season_cleared = False  # a main-forest Clear happened this season
season_min_relations = None  # lowest community relations seen this season
# GB batch 2 (session settings are chosen with the selects and reset the session, like difficulty):
current_challenge = CHALLENGE_NONE  # GB-17
challenge_complete_tick = None  # forest_tick the active challenge was finished on, or None
current_pace = PACE_NORMAL  # B-6
contract_board = []  # GB-9: [{"type", "target", "base"}] for the open contracts
contract_stamps = []  # contract type ids completed at least once this session
contracts_completed = 0
contract_refill_ticks = 0
contract_last_clear_tick = 0  # forest_tick of the last main-forest clear (for the "calm" contract)
contract_clear_count_seen = 0
tends_done = 0
seedlings_caught = 0

# Ephemeral state (never saved): timers and one-shot render hints.
golden_seedling = None  # {"plot": index, "ticks_left": n} or None
_golden_next_tick = GOLDEN_SEEDLING_MIN_GAP
_tend_message = ""
_undo_snapshot = None
_recent_matures = []  # (forest_tick, plot index) for chain bloom
_pending_bloom = {}  # plot index -> ripple rank, consumed by the next render_grid()
_pending_golden_bursts = set()  # plot indices, consumed by the next render_grid()
_forest_pulse_gen = 0
almanac_open = False
_gb_toast_queue = []  # GB toasts waiting for the next render
_announce_queue = []  # B-7: messages for the screen-reader live region, flushed once per render
contracts_open = False
_challenge_record_cache = None  # GB-17: per-browser fastest-completion record, read lazily


# B2 (planning/TODO.md "Per-game: Canopy"): a "reset session" option, folded
# together with B13's grid-size variant since both mean "rebuild the whole
# session from scratch" -- offering them as two separate controls would just
# mean two code paths doing almost the same thing. Deliberately a hard reset
# with no confirmation dialog: matches the site's "no dead-end states"
# philosophy (nothing here is a save file being destroyed -- that's what the
# separate save-code widget is for) and the shared confirm-dialog pattern
# the TODO's own site-wide goal describes is still just a design, not a
# built component, elsewhere in this file.
def reset_session(grid_size=None, _render_after=True, difficulty=None, challenge=None, pace=None):
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
    global _highland_plot_click_proxies
    global wetland_unlocked, wetland_plots, wetland_selected_index, wetland_income
    global wetland_flood_countdown, wetland_floods_survived, wetland_flood_value_lost
    global _wetland_plot_click_proxies
    global forest_log, forest_tick, adopted_plot_index, current_difficulty
    global legacy_multiplier, current_challenge, current_pace

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
    if difficulty is not None:
        if difficulty not in DEGRADE_PER_CLEAR_BY_DIFFICULTY:
            return False
        current_difficulty = difficulty
    if challenge is not None:  # GB-17
        if challenge != CHALLENGE_NONE and challenge not in CHALLENGE_SPECS:
            return False
        current_challenge = challenge
    if pace is not None:  # B-6
        if pace not in REQUEST_PACE_FACTOR:
            return False
        current_pace = pace
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
    _reset_gb_state()
    _apply_challenge_start()  # GB-17: Scorched Start burns the plots just built

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


# B24: Reset Session asks first, but only when there is something to lose, and
# names exactly what is being given up (the current standing value and income).
# A session with nothing standing worth keeping resets immediately.
#
# UX-4 (2026-10-07): the confirmation used to be a "press the button twice
# within 5 seconds" two-step that only relabelled the toolbar button. Players
# reported that Reset Session "does nothing": the first press changes nothing
# but a long label on a button that can be scrolled off-screen on a phone, and
# on the Desktop boot the button lives in the Menu, which closes after the
# first press, so the second press never happened. It now uses the shared
# ConfirmDialog (a modal with Cancel / Reset session buttons), which works the
# same on both boots and cannot be missed. Where ConfirmDialog is not available
# (the pytest fake-DOM harness, or a page without confirm-dialog.js) the reset
# happens at once, same fall-through every other game's helper has.
RESET_CONFIRM_ID = "canopy-reset-session"


def reset_confirm_message():
    return (
        f"Reset this session? You will give up {standing_forest_value():.1f} standing value"
        f" and {total_income:.1f} income. Saves you have already made are not touched."
    )


def _confirm_dialog_ask(action_id, message, confirm_label, on_confirm):
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
        allowSkip=False,
        onConfirm=create_proxy(lambda: on_confirm()),
    )


def render_reset_button():
    """Kept so render() keeps the toolbar label constant (older builds relabelled
    the button while a two-step confirm was armed)."""
    button = document.getElementById("reset-session-button")
    if button is None:
        return
    if button.innerText != "\U0001F504 Reset Session":
        button.innerText = "\U0001F504 Reset Session"


def on_reset_session(event=None):
    if standing_forest_value() <= 0 and total_income <= 0:
        reset_session()
        return
    _confirm_dialog_ask(
        RESET_CONFIRM_ID,
        reset_confirm_message(),
        "Reset session",
        reset_session,
    )


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
    candidates = [p for p in plots if p.state in ACCRUING_STATES and p.value > 0 and p.index != heart_tree_index]
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
    if _ticks_since_last_request < current_request_interval():  # B-6
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
    _note_season_relations()  # GB-30


def grant_stakeholder_request(event=None):
    global pending_stakeholder_request, community_relations, total_income
    global stakeholder_grants_count, total_replants, season_cleared
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
            season_cleared = True  # GB-30: a granted clear still cuts standing value
            _log_event(
                "clear",
                f"Granted the community's request: cleared {_plot_ref(plot.index)} for {payout:.1f} income",
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
        if idx == adopted_plot_index and adopted_plot_nickname:
            # GB-14: the adopted, nicknamed plot gets narrated ("Old Bramble survived a third clearing request").
            _log_event(
                "preserve",
                f"{adopted_plot_nickname} survived {_ordinal_word(plots[idx].requests_survived)} clearing request",
                idx,
            )
        else:
            _log_event("preserve", f"Declined a request to clear {plot_coordinate_label(idx)}: kept it standing", idx)
    # Declining a positive-trade-off incentive costs nothing -- turning down
    # a gift isn't the same as refusing the community's ask for the plot
    # itself, so there's no relations penalty for this kind.
    _note_community_relations_change()
    stakeholder_declines_count += 1
    pending_stakeholder_request = None
    _check_rare_wildlife()  # GB-20: the wary fox turns up after three refusals
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
        if adopted_plot_nickname:
            label += f" as {adopted_plot_nickname}"
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
    heart_aura = _heart_tree_aura()
    stag_plot = _ghost_stag_plot_index() if "ghost_stag" in rare_wildlife_found else None
    contrast_on = ui_pref(UI_PREF_PLOT_CONTRAST) == "true"  # B-8
    soil_on = ui_pref(UI_PREF_SOIL_OVERLAY) == "true"  # B-10
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
        mature_standing = plot.state in ACCRUING_STATES and plot.maturity_fraction() >= 1.0
        if mature_standing:
            tile.className += " plot-mature"
        if plot.is_veteran():
            tile.className += " plot-veteran"
            tile.appendChild(_make_tile_mark("veteran-mark", "\U0001F396\ufe0f"))
        if plot.index == adopted_plot_index:
            tile.className += " plot-adopted"
            tile.appendChild(_make_tile_mark("adopted-mark", "\u2B50"))
        bloom_rank = _pending_bloom.pop(plot.index, None)  # GB-27: one-shot, ripples in rank order
        golden_burst = plot.index in _pending_golden_bursts  # GB-2: reuses the B4 burst
        _pending_golden_bursts.discard(plot.index)
        if plot.index in _pending_mature_bursts or bloom_rank is not None or golden_burst:
            tile.className += " plot-mature-burst"
            if bloom_rank is not None:
                tile.className += f" plot-chain-bloom plot-chain-bloom-{bloom_rank}"
            for n in range(LEAF_BURST_COUNT):
                leaf = _make_tile_mark("leaf-burst", "\U0001F343")
                leaf.className = f"leaf-burst leaf-burst--{n}"
                tile.appendChild(leaf)
        if plot.tend_ticks_left > 0:  # GB-4
            tile.className += " plot-tended"
            tile.appendChild(_make_tile_mark("tend-mark", "\U0001F33F"))
        if plot.index == heart_tree_index:  # GB-8: no legend entry, no hint
            tile.className += " plot-heart-tree"
            tile.appendChild(_make_tile_mark("heart-tree-aura", ""))
            tile.appendChild(_make_tile_mark("heart-tree-mark", "\U0001F49A"))
        elif plot.index in heart_aura:
            tile.className += " plot-heart-aura"
        if golden_seedling is not None and golden_seedling["plot"] == plot.index:  # GB-2
            tile.className += " plot-golden-seedling"
            tile.appendChild(_make_tile_mark("golden-seedling-mark", "\u2728\U0001F331"))
        if plot.index == stag_plot:  # GB-20
            tile.className += " plot-ghost-stag"
            tile.appendChild(_make_tile_mark("ghost-stag-mark", "\U0001F98C"))
        tile.style.backgroundColor = plot_display_color(plot)
        if contrast_on:  # B-8: a letter on every tile so state reads without the green gradient
            tile.className += " plot-contrast"
            letter = MATURE_LETTER if mature_standing else STATE_LETTER[plot.state]
            letter_mark = _make_tile_mark("state-letter", letter)
            letter_mark.setAttribute("aria-hidden", "true")
            tile.appendChild(letter_mark)
        if soil_on:  # B-10: soil quality as a coloured border band and a number
            soil_pct, band = soil_band(plot)
            tile.className += f" plot-soil plot-soil--{band}"
            soil_mark = _make_tile_mark("soil-badge", str(soil_pct))
            soil_mark.setAttribute("aria-hidden", "true")
            tile.appendChild(soil_mark)
        tooltip = _plot_tooltip_text(plot)
        if golden_seedling is not None and golden_seedling["plot"] == plot.index:
            tooltip += " \u00b7 golden seedling: click it now for a burst of recovery"
        if plot.tend_ticks_left > 0:
            tooltip += f" \u00b7 tended ({plot.tend_ticks_left} ticks left)"
        detail = _plot_tooltip_detail(plot)  # B-16: second line of the plot card
        tile.setAttribute("data-tooltip", tooltip + "\n" + detail)
        tile.setAttribute("aria-label", tooltip + "\n" + detail)
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
    clear_button.disabled = "clear" not in VALID_ACTIONS[plot.state] or plot.index == heart_tree_index
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
    if current_challenge == CHALLENGE_NO_HIGHLAND:
        return  # GB-17: the regions stay sealed
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
    document.getElementById("highland-income-display").innerText = f"Harvested income: {fmt_num(highland_income)}"
    document.getElementById("highland-standing-value-display").innerText = (
        f"Standing grove value: {fmt_num(highland_standing_value())}"
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
    if not highland_unlocked and current_challenge == CHALLENGE_NO_HIGHLAND:
        section.hidden = True
        banner.hidden = False
        bar.hidden = True
        banner.innerText = "\u26F0\ufe0f Highland Grove and Wetland Forest are sealed during the No-Highland challenge."
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
    if current_challenge == CHALLENGE_NO_HIGHLAND:
        return  # GB-17: the regions stay sealed
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
    document.getElementById("wetland-income-display").innerText = f"Harvested income: {fmt_num(wetland_income)}"
    document.getElementById("wetland-standing-value-display").innerText = (
        f"Standing wetland value: {fmt_num(wetland_standing_value())}"
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
        f"Personal best: standing {fmt_num(personal_best['standing_value'])} "
        f"· income {fmt_num(personal_best['income'])}"
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
        total += (
            BASE_ACCRUAL * (1 + j * GROWTH_PER_TICK) * SEASON_GROWTH_MULTIPLIER[season]
            * weather_multiplier_at(start_tick + j)  # GB-23: the same rain/drought the real forest saw
        )
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
        f"\U0001F332 Canopy — {forest_name or 'my forest'} so far: {standing_value:.1f} standing value, "
        f"{total_income:.1f} harvested, {total_biodiversity():.1f} biodiversity. "
        f"{standing_plots}/{len(plots)} plots still standing."
        + (f" ({session_tag_text()})" if session_tag_text() else "")
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
    document.getElementById("income-display").innerText = f"Harvested income: {fmt_num(total_income)}"
    document.getElementById("standing-value-display").innerText = f"Standing forest value: {fmt_num(standing_value)}"
    document.getElementById("biodiversity-display").innerText = (
        f"Biodiversity: {fmt_num(total_biodiversity())} (+{biodiversity_rate_per_tick():.2f}/tick)"
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
    # GB-22: the standing-value tiers above 1,000 (which standing_fortune
    # already covers). Read off the best value reached, so a later clear
    # cannot un-earn a tier the forest already grew into.
    "tier_grove": lambda: _peak_now() >= TIER_ACHIEVEMENT_THRESHOLDS["tier_grove"],
    "tier_woodland": lambda: _peak_now() >= TIER_ACHIEVEMENT_THRESHOLDS["tier_woodland"],
    "tier_old_growth_steward": lambda: _peak_now() >= TIER_ACHIEVEMENT_THRESHOLDS["tier_old_growth_steward"],
    # GB-17: one badge per challenge, earned by finishing that challenge in this session.
    "challenge_pacifist": lambda: current_challenge == CHALLENGE_PACIFIST and challenge_complete_tick is not None,
    "challenge_scorched": lambda: current_challenge == CHALLENGE_SCORCHED and challenge_complete_tick is not None,
    "challenge_sprint": lambda: current_challenge == CHALLENGE_SPRINT and challenge_complete_tick is not None,
    "challenge_no_highland": lambda: current_challenge == CHALLENGE_NO_HIGHLAND and challenge_complete_tick is not None,
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
    "tier_grove": lambda: (int(min(_peak_now(), 2500.0)), 2500),
    "tier_woodland": lambda: (int(min(_peak_now(), 5000.0)), 5000),
    "tier_old_growth_steward": lambda: (int(min(_peak_now(), 10000.0)), 10000),
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


def _sync_earned_and_toast():
    """Diffs the live earned set against the last-seen snapshot; anything
    newly present gets a toast (batched into one message if several land
    in the same render pass, e.g. several achievements clearing at once on
    a big tick)."""
    global _previously_earned_ids
    current = _earned_snapshot()
    _story_reach_all(current)
    newly_earned_ids = current - _previously_earned_ids
    _previously_earned_ids = current
    newly_earned = [entry for entry in ACHIEVEMENTS if entry["id"] in newly_earned_ids]
    messages = []
    if len(newly_earned) == 1:
        messages.append(f"\U0001F3C6 Achievement unlocked: {newly_earned[0]['label']}")
    elif newly_earned:
        labels = ", ".join(entry["label"] for entry in newly_earned)
        messages.append(f"\U0001F3C6 {len(newly_earned)} achievements unlocked: {labels}")
    for message in messages:
        _announce(message)  # B-7: achievements are not in the forest log; GB toasts already are
    messages.extend(_gb_toast_queue)  # GB batch 1: discoveries, tiers, seasons
    del _gb_toast_queue[:]
    if messages:
        show_achievement_toast("  \u00b7  ".join(messages))


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
    if kind not in ("wildlife", "mature"):  # B-7: everything else is worth saying aloud
        _announce(text)


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
    global adopted_plot_index, adopted_plot_nickname
    if selected_index is None:
        return False
    if adopted_plot_index == selected_index:
        adopted_plot_index = None
    else:
        adopted_plot_index = selected_index
        _log_event("adopt", f"Adopted {plot_coordinate_label(selected_index)} as a long-term project", selected_index)
    adopted_plot_nickname = ""  # GB-14: a nickname belongs to one adoption
    _sync_name_inputs()
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
    nickname_part = f' "{adopted_plot_nickname}"' if adopted_plot_nickname else ""
    panel.innerText = (
        f"Adopted plot {plot_coordinate_label(adopted_plot_index)}{nickname_part}: {STATE_LABEL[plot.state]}, "
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
        rare_head = "\nRare sightings ({}/{}): ".format(len(rare_wildlife_found), len(RARE_WILDLIFE)) + (
            " ".join(f"{_rare_entry(r)[1]} {_rare_entry(r)[2]}" for r in rare_wildlife_found)
            if rare_wildlife_found else "none yet"
        )
        lines = forest_log_lines(kinds={"wildlife", "rare", "discovery"})  # GB-20/GB-8: rare finds live here too
        wildlife_el.innerText = head + rare_head + ("\n" + "\n".join(lines) if lines else "")
    history_el = document.getElementById("forest-history-list")
    if history_el is not None:
        lines = forest_log_lines()
        story_line = f"The story of {forest_name}\n" if forest_name else ""  # GB-14
        history_el.innerText = story_line + ("\n".join(lines) if lines else "No decisions yet: clear, replant, or decline a request to start the log.")


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
    for element_id, value in (("challenge-select", current_challenge), ("request-pace-select", current_pace)):
        extra_select = _el(element_id)
        if extra_select is not None:
            extra_select.value = value


# ===========================================================================
# W2-canopy -- "In the real world": a collapsible note that pairs what you
# just did (or what the community is asking) with one real, sourced example.
# Every figure below was read from the linked page on 2026-09-27 (nothing
# recalled from memory); where a page gave no number, none is quoted. The note
# is chosen deterministically (no RNG) and never changes any number in a run:
#   * a pending community request wins (a clear request -> community forestry,
#     an incentive / replant-fund offer -> funded restoration),
#   * else the newest mapped forest-log event (clear, replant, wildlife /
#     preserve / recovered, mature),
#   * else it rotates through the examples every REAL_WORLD_ROTATE_TICKS ticks.
# ===========================================================================
REAL_WORLD_READ_DATE = "2026-09-27"
REAL_WORLD_ROTATE_TICKS = 10
REAL_WORLD_ORDER = ["forest_loss", "restoration", "wildlife", "carbon", "community", "funded_restoration"]
REAL_WORLD_LOG_TOPICS = {
    "clear": "forest_loss",
    "replant": "restoration",
    "wildlife": "wildlife",
    "preserve": "wildlife",
    "recovered": "wildlife",
    "mature": "carbon",
    "rare": "wildlife",
    "discovery": "wildlife",
}
REAL_WORLD_EXAMPLES = {
    "forest_loss": {
        "title": "Global forest loss, and how it has slowed",
        "text": "Clearing forest is a real trade-off worldwide. The FAO's 2020 assessment put deforestation at 10 million hectares a year in 2015-2020, down from 17.6 million hectares a year in 1990-2000.",
        "source": "Wikipedia, Deforestation", "url": "https://en.wikipedia.org/wiki/Deforestation",
    },
    "restoration": {
        "title": "The Atlantic Forest Restoration Pact (Brazil)",
        "text": "Replanting can be organised at scale. The Pact for Atlantic Forest Restoration has brought together over 100 businesses, non-governmental and governmental organisations around a goal of restoring 15 million hectares of the original ecosystem by 2050.",
        "source": "Wikipedia, Atlantic Forest", "url": "https://en.wikipedia.org/wiki/Atlantic_Forest",
    },
    "wildlife": {
        "title": "How fast regrown forest recovers its wildlife",
        "text": "Studies of secondary forest find that species richness can quickly recover to pre-disturbance levels, but the relative abundances and identities of species can take much longer, and in the tropics biodiversity takes longer to recover than carbon stores.",
        "source": "Wikipedia, Secondary forest", "url": "https://en.wikipedia.org/wiki/Secondary_forest",
    },
    "carbon": {
        "title": "Forests as carbon sinks",
        "text": "Standing forest and the climate are linked. Forests are described as sequestering approximately 25% of human carbon emissions each year, though in 2019 they took up a third less carbon than in the 1990s, due to higher temperatures, droughts and deforestation.",
        "source": "Wikipedia, Carbon sink", "url": "https://en.wikipedia.org/wiki/Carbon_sink",
    },
    "community": {
        "title": "Community forestry in Nepal",
        "text": "Communities can manage forest themselves: over 19,000 community forest user groups exist in Nepal, covering one fourth of national forests and 1.6 million households. The same source notes that wealthier households can hold more decision-making power, which can reduce participation by poorer households.",
        "source": "Wikipedia, Community forestry in Nepal", "url": "https://en.wikipedia.org/wiki/Community_forestry_in_Nepal",
    },
    "funded_restoration": {
        "title": "Africa's Great Green Wall",
        "text": "Outside funding and partnership can back restoration, but progress can be hard to measure. The African Union adopted the Great Green Wall in 2007 with a goal of restoring 100 million hectares by 2030; the page cites about 30 million hectares restored as of 2024, and its progress figures differ between years and reports (for example 4% of the planned area in 2020).",
        "source": "Wikipedia, Great Green Wall (Africa)", "url": "https://en.wikipedia.org/wiki/Great_Green_Wall_(Africa)",
    },
}


def real_world_topic():
    """Which example the note shows right now (pure function of run state)."""
    request = pending_stakeholder_request
    if request is not None:
        if request.get("kind", STAKEHOLDER_KIND_CLEAR) == STAKEHOLDER_KIND_CLEAR:
            return "community"
        return "funded_restoration"
    for entry in reversed(forest_log):
        topic = REAL_WORLD_LOG_TOPICS.get(entry["kind"])
        if topic is not None:
            return topic
    return REAL_WORLD_ORDER[(forest_tick // REAL_WORLD_ROTATE_TICKS) % len(REAL_WORLD_ORDER)]


def render_real_world():
    box = document.getElementById("real-world-note")
    example = REAL_WORLD_EXAMPLES[real_world_topic()]
    box.hidden = False
    document.getElementById("real-world-text").innerText = f"{example['title']}. {example['text']}"
    link = document.getElementById("real-world-source")
    link.innerText = f"Source: {example['source']} (read {REAL_WORLD_READ_DATE})"
    link.href = example["url"]


# ===========================================================================
# GB batch 1 -- behaviour (constants/state are declared near the top of the
# file, above reset_session()). See planning/IMPROVEMENT-IDEAS-ROUND-3.md
# section GB for the wording of each idea.
# ===========================================================================


def _el(element_id):
    """getElementById that tolerates a page/test DOM without the element (a
    real browser returns None, the fake test DOM raises KeyError)."""
    try:
        return document.getElementById(element_id)
    except KeyError:
        return None


def _gb_hash(*parts):
    """A small deterministic integer hash, standing in for randomness (this
    game deliberately has no RNG, so runs and tests are repeatable)."""
    h = 2166136261
    for part in parts:
        h = ((h ^ (int(part) & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
    h ^= h >> 15
    h = (h * 2246822519) & 0xFFFFFFFF
    h ^= h >> 13
    return h


def _gb_toast(message):
    """Queues a GB toast; the next render shows it (joined with any achievement
    toast that lands in the same render, so neither hides the other)."""
    _gb_toast_queue.append(message)


def _timed_callback(callback, delay_ms):
    """setTimeout for a one-shot callback whose proxy destroys itself after
    firing (never destroy a still-pending proxy, see show_achievement_toast)."""
    holder = []

    def _run():
        try:
            callback()
        finally:
            holder[0].destroy()

    holder.append(create_proxy(_run))
    setTimeout(holder[0], delay_ms)


def _plot_ref(index):
    """How the log and readouts name a main-forest plot: its coordinate, or
    the adopted plot's nickname (GB-14) with the coordinate in brackets."""
    label = plot_coordinate_label(index)
    if index == adopted_plot_index and adopted_plot_nickname:
        return f"{adopted_plot_nickname} ({label})"
    return label


def _forest_display_name():
    return forest_name or "The forest"


def _ordinal_word(n):
    return {1: "a first", 2: "a second", 3: "a third"}.get(n, f"{n}th")


def _neighbour_indices(index):
    """The up-to-8 main-forest plots touching `index` (sides and corners)."""
    row, col = divmod(index, GRID_COLS)
    found = []
    for d_row in (-1, 0, 1):
        for d_col in (-1, 0, 1):
            if d_row == 0 and d_col == 0:
                continue
            r, c = row + d_row, col + d_col
            if 0 <= r < GRID_ROWS and 0 <= c < GRID_COLS:
                found.append(r * GRID_COLS + c)
    return found


# --- GB-23: weather ---------------------------------------------------------

def _season_at(tick):
    return SEASONS[(tick // SEASON_CYCLE_TICKS) % len(SEASONS)]


def _weather_episode(tick):
    """(kind, start_tick) of the rain/drought episode covering `tick`, or
    None. A pure function of the tick, so it needs no saved state and the
    counterfactual can price it in. Rain comes in spring and autumn, drought in
    summer, nothing in winter; at most one episode starts per block."""
    block = tick // WEATHER_BLOCK_TICKS
    for b in (block - 1, block):
        if b < 0 or _gb_hash(b, 23) % 100 >= WEATHER_EPISODE_PERCENT:
            continue
        start = b * WEATHER_BLOCK_TICKS + _gb_hash(b, 11) % (WEATHER_BLOCK_TICKS - 4)
        if start < WEATHER_FIRST_TICK or not (start <= tick < start + WEATHER_DURATION_TICKS):
            continue
        kind = WEATHER_SEASON_KIND[_season_at(start)]
        if kind:
            return kind, start
    return None


def weather_at(tick):
    episode = _weather_episode(tick)
    return episode[0] if episode else None


def weather_multiplier_at(tick):
    kind = weather_at(tick)
    if kind == "rain":
        return WEATHER_RAIN_MULTIPLIER
    if kind == "drought":
        return WEATHER_DROUGHT_MULTIPLIER
    return 1.0


def current_weather_multiplier():
    return weather_multiplier_at(forest_tick)


def weather_ticks_left():
    episode = _weather_episode(forest_tick)
    return episode[1] + WEATHER_DURATION_TICKS - forest_tick if episode else 0


# --- GB-30: Perfect Season streak ---------------------------------------------

def current_perfect_streak_multiplier():
    return 1.0 + PERFECT_STREAK_BONUS_PER_SEASON * min(perfect_streak, PERFECT_STREAK_MAX_BONUS_SEASONS)


def _note_season_relations():
    global season_min_relations
    if season_min_relations is None:
        season_min_relations = community_relations
    else:
        season_min_relations = min(season_min_relations, community_relations)


def perfect_season_status():
    """(on_track, reason): whether this season is still perfect so far. A
    season is perfect when no main-forest plot was cleared (nothing turned BARE
    and cut your standing value) and community trust never sank below
    PERFECT_SEASON_MIN_RELATIONS (a run of refusals you would come to regret)."""
    if season_cleared:
        return False, "a plot was cleared this season"
    low = season_min_relations if season_min_relations is not None else community_relations
    if low < PERFECT_SEASON_MIN_RELATIONS:
        return False, f"community trust dipped below {PERFECT_SEASON_MIN_RELATIONS}"
    return True, ""


def _end_season():
    """Called on the first tick of each new season: scores the season that just
    ended, then starts a fresh one."""
    global perfect_streak, season_cleared, season_min_relations
    _note_season_relations()
    on_track, reason = perfect_season_status()
    ended = SEASON_LABEL[_season_at(forest_tick - 1)]
    if on_track:
        perfect_streak += 1
        _log_event(
            "season",
            f"Perfect Season: {ended} ended with every plot standing and the village's trust intact "
            f"(streak {perfect_streak})",
        )
        if perfect_streak in (1, 3, 5):
            bonus = round(min(perfect_streak, PERFECT_STREAK_MAX_BONUS_SEASONS) * PERFECT_STREAK_BONUS_PER_SEASON * 100)
            _gb_toast(f"\U0001F525 Perfect Season x{perfect_streak}: +{bonus}% growth")
        _flash_element("perfect-streak-text")
    else:
        if perfect_streak > 0:
            _log_event("season", f"{ended} broke a {perfect_streak}-season Perfect Season streak: {reason}")
        perfect_streak = 0
    season_cleared = False
    season_min_relations = community_relations
    _announce(
        f"{SEASON_LABEL[current_season()]} begins, growth x{current_season_multiplier():.2f}"
    )  # B-7


def _flash_element(element_id):
    """Reuses the shared .just-improved pulse (personal-best flash pattern)."""
    element = _el(element_id)
    if element is None:
        return
    element.classList.add("just-improved")

    def _unflash():
        el = _el(element_id)
        if el is not None:
            el.classList.remove("just-improved")

    _timed_callback(_unflash, PERSONAL_BEST_BADGE_MS)


def render_season_indicator():
    season = current_season()
    next_season = SEASONS[(SEASONS.index(season) + 1) % len(SEASONS)]
    season_el = _el("season-text")
    if season_el is not None:
        season_el.innerText = (
            f"{SEASON_ICON[season]} {SEASON_LABEL[season]} "
            f"· {ticks_until_next_season()} ticks to {SEASON_LABEL[next_season]}"
        )
    weather = weather_at(forest_tick)
    weather_el = _el("weather-text")
    if weather_el is not None:
        if weather is None:
            weather_el.hidden = True
            weather_el.innerText = ""
        else:
            change = round((weather_multiplier_at(forest_tick) - 1) * 100)
            weather_el.hidden = False
            weather_el.innerText = (
                f"{WEATHER_ICON[weather]} {WEATHER_LABEL[weather]}: growth {change:+d}% "
                f"· {weather_ticks_left()} ticks left"
            )
    on_track, reason = perfect_season_status()
    streak_el = _el("perfect-streak-text")
    if streak_el is not None:
        bonus = round((current_perfect_streak_multiplier() - 1) * 100)
        streak_el.innerText = f"\U0001F525 Perfect Season streak: {perfect_streak}" + (f" (+{bonus}% growth)" if bonus else "")
        status = "on track this season" if on_track else f"broken this season ({reason})"
        streak_el.title = (
            "End a season without clearing any plot and without community trust sinking below "
            f"{PERFECT_SEASON_MIN_RELATIONS} to add a flame: +{round(PERFECT_STREAK_BONUS_PER_SEASON * 100)}% growth each, "
            f"up to +{round(PERFECT_STREAK_BONUS_PER_SEASON * PERFECT_STREAK_MAX_BONUS_SEASONS * 100)}%. "
            f"This season: {status}."
        )
        streak_el.setAttribute("aria-label", f"Perfect Season streak {perfect_streak}. {streak_el.title}")
    grid = _el("plot-grid")
    if grid is not None:
        for kind in ("rain", "drought"):
            if kind == weather:
                grid.classList.add(f"plot-grid--{kind}")
            else:
                grid.classList.remove(f"plot-grid--{kind}")
        if is_dusk_window():
            grid.classList.add("plot-grid--dusk")
        else:
            grid.classList.remove("plot-grid--dusk")


# --- GB-2: golden seedling ------------------------------------------------------

def _schedule_golden_seedling():
    global _golden_next_tick
    _golden_next_tick = forest_tick + GOLDEN_SEEDLING_MIN_GAP + _gb_hash(forest_tick, 3) % GOLDEN_SEEDLING_GAP_SPREAD


def _advance_golden_seedling():
    global golden_seedling
    if golden_seedling is not None:
        golden_seedling["ticks_left"] -= 1
        if golden_seedling["ticks_left"] <= 0 or plots[golden_seedling["plot"]].state not in (BARE, REPLANTING):
            golden_seedling = None
            _schedule_golden_seedling()
        return
    if forest_tick < _golden_next_tick:
        return
    candidates = [p.index for p in plots if p.state in (BARE, REPLANTING)]
    if not candidates:
        return  # nothing to grow on; try again next tick
    golden_seedling = {
        "plot": candidates[_gb_hash(forest_tick, 5) % len(candidates)],
        "ticks_left": GOLDEN_SEEDLING_TICKS,
    }


def collect_golden_seedling(index=None):
    """Banks a burst of recovery on the plot the golden seedling sits on (a
    bare plot is replanted first). `index` lets a tile click say which plot it
    was; the "G" key passes nothing. Returns True on a real collect."""
    global golden_seedling, total_replants, total_recoveries, seedlings_caught
    if golden_seedling is None or (index is not None and index != golden_seedling["plot"]):
        return False
    plot = plots[golden_seedling["plot"]]
    golden_seedling = None
    seedlings_caught += 1  # GB-9: counts toward a Ranger contract
    _schedule_golden_seedling()
    if plot.state == BARE and plot.replant():
        total_replants += 1
        _log_event("replant", f"A golden seedling sprouted on {_plot_ref(plot.index)}", plot.index)
    if plot.state == REPLANTING:
        for _ in range(GOLDEN_SEEDLING_RECOVERY_TICKS):
            if plot.advance_recovery():
                total_recoveries += 1
                _log_event("recovered", f"{_plot_ref(plot.index)} finished recovering", plot.index)
                break
    _pending_golden_bursts.add(plot.index)
    _log_event("golden", f"Caught a golden seedling on {_plot_ref(plot.index)}", plot.index)
    return True


# --- GB-4: Tend ---------------------------------------------------------------------

def _tended_plot():
    for plot in plots:
        if plot.tend_ticks_left > 0:
            return plot
    return None


def _tendable(plot):
    return plot.state in ACCRUING_STATES or plot.state == REPLANTING


def tend_status_text():
    tended = _tended_plot()
    if tended is not None:
        return f"Tending {_plot_ref(tended.index)}: {tended.tend_ticks_left} more ticks of faster growth."
    if tend_cooldown_ticks > 0:
        return f"Tend is recharging: {tend_cooldown_ticks} ticks."
    return _tend_message or "Tend is ready: hover a plot and press T, or select one and press Tend."


def tend_plot(index=None):
    """GB-4: a short growth boost (TEND_GROWTH_MULTIPLIER for
    TEND_DURATION_TICKS ticks; a replanting plot recovers an extra tick per
    tick) on one plot, then a TEND_COOLDOWN_TICKS cooldown. `index` is the
    hovered plot (the "T" key); without one it uses the selected plot."""
    global _tend_message, tends_done
    if index is None:
        index = selected_index
    if isinstance(index, bool) or not isinstance(index, (int, float)) or index != index:
        index = None
    else:
        index = int(index)
    if index is None or not (0 <= index < len(plots)):
        _tend_message = "Hover or select a plot first."
        render_tend_panel()
        return False
    plot = plots[index]
    if _tended_plot() is not None or tend_cooldown_ticks > 0:
        _tend_message = ""
        render_tend_panel()
        return False
    if not _tendable(plot):
        _tend_message = "A bare plot has nothing to tend yet: replant it first."
        render_tend_panel()
        return False
    plot.tend_ticks_left = TEND_DURATION_TICKS
    tends_done += 1  # GB-9: counts toward a Ranger contract
    _tend_message = ""
    _log_event("tend", f"Tended {_plot_ref(index)}", index)
    render()
    return True


def on_tend(event=None):
    tend_plot()


def _advance_tend():
    global tend_cooldown_ticks
    active = False
    for plot in plots:
        if plot.tend_ticks_left > 0:
            active = True
            plot.tend_ticks_left -= 1
            if plot.tend_ticks_left == 0:
                tend_cooldown_ticks = TEND_COOLDOWN_TICKS
    if not active and tend_cooldown_ticks > 0:
        tend_cooldown_ticks -= 1


def render_tend_panel():
    button = _el("tend-button")
    status = _el("tend-status")
    if status is not None:
        status.innerText = tend_status_text()
    if button is None:
        return
    plot = plots[selected_index] if selected_index is not None else None
    busy = _tended_plot() is not None or tend_cooldown_ticks > 0
    button.disabled = busy or plot is None or not _tendable(plot)
    if _tended_plot() is not None:
        button.innerText = "\U0001F33F Tending..."
    elif tend_cooldown_ticks > 0:
        button.innerText = f"\U0001F33F Tend ({tend_cooldown_ticks})"
    else:
        button.innerText = "\U0001F33F Tend (T)"


# --- GB-8: the Heart Tree ------------------------------------------------------------

def _mature_neighbour_count(index):
    return sum(
        1
        for n in _neighbour_indices(index)
        if plots[n].state in ACCRUING_STATES and plots[n].maturity_fraction() >= 1.0
    )


def _find_heart_tree_centre():
    for plot in plots:
        if plot.state in ACCRUING_STATES and len(_neighbour_indices(plot.index)) == 8:
            if _mature_neighbour_count(plot.index) >= HEART_TREE_MIN_MATURE_NEIGHBOURS:
                return plot.index
    return None


def _check_heart_tree():
    """A standing plot ringed by HEART_TREE_MIN_MATURE_NEIGHBOURS fully mature
    plots (of its 8 neighbours) grows the Heart Tree. There is no hint of this
    anywhere in the UI; finding it is the reward."""
    global heart_tree_index, pending_stakeholder_request
    if heart_tree_index is not None:
        return
    centre = _find_heart_tree_centre()
    if centre is None:
        return
    heart_tree_index = centre
    if (
        pending_stakeholder_request is not None
        and pending_stakeholder_request["plot_index"] == centre
        and pending_stakeholder_request.get("kind", STAKEHOLDER_KIND_CLEAR) == STAKEHOLDER_KIND_CLEAR
    ):
        pending_stakeholder_request = None  # nobody asks to fell the Heart Tree
    _log_event(
        "discovery",
        f"\U0001F333 The Heart Tree woke at {_plot_ref(centre)}: the ring of old trees around it gave it a "
        "place to grow. It will not be felled, and the plots around it thrive.",
        centre,
    )
    _gb_toast("\U0001F333 The forest has grown something ancient. The Heart Tree is awake.")


def _heart_tree_aura():
    if heart_tree_index is None:
        return frozenset()
    return frozenset(_neighbour_indices(heart_tree_index))


# --- GB-14: names ----------------------------------------------------------------------

def _clean_name(value, limit):
    if not isinstance(value, str):
        return ""
    printable = "".join(ch for ch in value if ch.isprintable())
    return " ".join(printable.split())[:limit]


def set_forest_name(value):
    global forest_name
    cleaned = _clean_name(value, FOREST_NAME_MAX)
    if cleaned == forest_name:
        return False
    forest_name = cleaned
    if cleaned:
        _log_event("name", f"The forest was named {cleaned}")
    render()
    return True


def set_plot_nickname(value):
    """Nicknames the adopted plot (B27); ignored when no plot is adopted."""
    global adopted_plot_nickname
    if adopted_plot_index is None:
        return False
    cleaned = _clean_name(value, NICKNAME_MAX)
    if cleaned == adopted_plot_nickname:
        return False
    adopted_plot_nickname = cleaned
    if cleaned:
        _log_event(
            "name",
            f"{plot_coordinate_label(adopted_plot_index)} is now known as {cleaned}",
            adopted_plot_index,
        )
    render()
    return True


def _event_value(event):
    return getattr(getattr(event, "target", None), "value", "")


def on_forest_name_change(event=None):
    set_forest_name(_event_value(event))


def on_plot_nickname_change(event=None):
    set_plot_nickname(_event_value(event))


def _sync_name_inputs():
    """Writes the saved names back into the two text fields (only on load,
    reset and adopt/release, never every render, so typing is never clobbered)."""
    forest_input = _el("forest-name-input")
    if forest_input is not None:
        forest_input.value = forest_name
    nickname_input = _el("plot-nickname-input")
    if nickname_input is not None:
        nickname_input.value = adopted_plot_nickname
        nickname_input.disabled = adopted_plot_index is None


# --- GB-18: undo a clear -------------------------------------------------------------------

def _arm_undo(plot_index, before_fields, payout, log_entry, season_cleared_before, best_income_before):
    global _undo_snapshot
    if current_difficulty == DIFFICULTY_RANGER:
        _undo_snapshot = None
        return
    _undo_snapshot = {
        "plot": plot_index,
        "fields": before_fields,
        "payout": payout,
        "clear_count_after": plots[plot_index].clear_count,
        "log_entry": log_entry,
        "season_cleared_before": season_cleared_before,
        "best_income_before": best_income_before,
        "ticks_left": UNDO_WINDOW_TICKS,
    }


def _advance_undo():
    """Counts the undo window down one tick; the chip is gone the tick after it hits 0."""
    global _undo_snapshot
    if _undo_snapshot is None:
        return
    if _undo_snapshot["ticks_left"] <= 0:
        _undo_snapshot = None
    else:
        _undo_snapshot["ticks_left"] -= 1


def undo_last_clear(event=None):
    """Restores the plot cleared in the last UNDO_WINDOW_MS (not in Ranger
    difficulty). Only valid while that plot is still bare from that clear."""
    global _undo_snapshot, total_income, season_cleared
    snapshot = _undo_snapshot
    if snapshot is None:
        return False
    _undo_snapshot = None
    plot = plots[snapshot["plot"]]
    if plot.state != BARE or plot.clear_count != snapshot["clear_count_after"]:
        render_undo_chip()
        return False
    plot.__dict__.update(snapshot["fields"])
    if personal_best["income"] <= total_income + 1e-9 and personal_best["income"] > snapshot["best_income_before"]:
        # The undone payout had just set the income record: take the record back too.
        personal_best["income"] = snapshot["best_income_before"]
        _write_local_storage_item(PERSONAL_BEST_STORAGE_KEY, json.dumps(personal_best))
    total_income = max(0.0, total_income - snapshot["payout"])
    season_cleared = snapshot["season_cleared_before"]
    if snapshot["log_entry"] in forest_log:
        forest_log.remove(snapshot["log_entry"])
    _log_event("preserve", f"Took back the clear: {_plot_ref(plot.index)} is standing again", plot.index)
    render()
    return True


def render_undo_chip():
    chip = _el("undo-clear-button")
    if chip is None:
        return
    if _undo_snapshot is None:
        chip.hidden = True
        return
    label = _plot_ref(_undo_snapshot["plot"])
    chip.hidden = False
    seconds = max(1, _undo_snapshot["ticks_left"])
    chip.innerText = f"\u21a9 Undo clear ({label}, {seconds}s)"
    chip.setAttribute("aria-label", f"Undo clearing {label}. About {seconds} seconds left.")


# --- GB-20: rare wildlife ------------------------------------------------------------------------

def is_dusk_window(tick=None):
    """The night-tinted late-autumn ticks: the last DUSK_TICKS_IN_AUTUMN of autumn."""
    tick = forest_tick if tick is None else tick
    return _season_at(tick) == "autumn" and tick % SEASON_CYCLE_TICKS >= SEASON_CYCLE_TICKS - DUSK_TICKS_IN_AUTUMN


def biodiversity_fraction(plot):
    return min(1.0, plot.biodiversity / BIODIVERSITY_FULL_SCORE)


def _ghost_stag_plot_index():
    """The plot the ghost stag would be standing on right now, or None."""
    if not is_dusk_window():
        return None
    for plot in plots:
        if plot.state in ACCRUING_STATES and biodiversity_fraction(plot) >= RARE_STAG_MIN_FRACTION:
            return plot.index
    return None


def declined_clear_requests_total():
    """Every declined clear request across the forest (each bumps its plot's
    requests_survived, which never resets)."""
    return sum(plot.requests_survived for plot in plots)


def _rare_entry(rare_id):
    for entry in RARE_WILDLIFE:
        if entry[0] == rare_id:
            return entry
    return None


def _found_rare(rare_id, plot_index=None):
    icon, name = _rare_entry(rare_id)[1:3]
    rare_wildlife_found.append(rare_id)
    if rare_id == "ghost_stag":
        text = f"{icon} A ghost stag stepped out of the dusk at {_plot_ref(plot_index)} and was gone by morning"
    else:
        text = f"{icon} A wary fox watched from the treeline, drawn by a forest that keeps its ground"
    _log_event("rare", text, plot_index)
    _gb_toast(f"{icon} Rare sighting: {name}. It has been added to your wildlife log.")


def _check_rare_wildlife():
    if "ghost_stag" not in rare_wildlife_found:
        stag_plot = _ghost_stag_plot_index()
        if stag_plot is not None:
            _found_rare("ghost_stag", stag_plot)
    if "wary_fox" not in rare_wildlife_found and declined_clear_requests_total() >= RARE_FOX_DECLINED_REQUESTS:
        _found_rare("wary_fox")


# --- GB-22: standing value tiers --------------------------------------------------------------------

def forest_title():
    return STANDING_TIERS[milestone_tier - 1][1] if milestone_tier > 0 else ""


def _peak_now():
    return max(peak_standing_value, standing_forest_value())


def _tiers_reached_for(peak):
    return sum(1 for threshold, _title in STANDING_TIERS if peak >= threshold)


def _check_milestones(celebrate=True):
    """Tracks the best standing value this session and celebrates each tier
    (1k Seedling, 2.5k Grove, 5k Woodland, 10k Old-Growth) once."""
    global peak_standing_value, milestone_tier
    peak_standing_value = _peak_now()
    reached = _tiers_reached_for(peak_standing_value)
    if reached <= milestone_tier:
        return
    old = milestone_tier
    milestone_tier = reached
    for i in range(old, reached):
        threshold, title = STANDING_TIERS[i]
        _log_event("milestone", f"{_forest_display_name()} grew into a {title} forest ({threshold:,.0f} standing value)")
    if celebrate:
        threshold, title = STANDING_TIERS[reached - 1]
        _gb_toast(f"\U0001F332 {_forest_display_name()} is now a {title} forest ({threshold:,.0f} standing value)")
        _flash_forest_pulse()


def _flash_forest_pulse():
    """The brief light pulse: the forest backdrop flushes and the title flashes
    (the shared personal-best .just-improved pattern)."""
    global _forest_pulse_gen
    visual = _el("forest-visual")
    if visual is not None:
        visual.classList.add("forest-pulse")
        _forest_pulse_gen += 1
        gen = _forest_pulse_gen

        def _unpulse():
            el = _el("forest-visual")
            if el is not None and gen == _forest_pulse_gen:
                el.classList.remove("forest-pulse")

        _timed_callback(_unpulse, FOREST_PULSE_MS)
    _flash_element("forest-title-display")


def render_forest_title():
    element = _el("forest-title-display")
    if element is None:
        return
    title = forest_title()
    element.hidden = not (title or forest_name)
    label = f"{forest_name}, " if forest_name else ""
    element.innerText = f"Forest: {label}{title} tier" if title else f"Forest: {forest_name}"


# --- GB-27: chain bloom -------------------------------------------------------------------------------------

def _register_chain_bloom(new_indices):
    """Plots reaching full maturity within CHAIN_BLOOM_WINDOW_TICKS of each
    other ripple their leaf bursts across the grid in order, each one bigger
    and later than the last (juice only: it changes no number)."""
    global _recent_matures
    _recent_matures = [(t, i) for t, i in _recent_matures if forest_tick - t < CHAIN_BLOOM_WINDOW_TICKS]
    _recent_matures.extend((forest_tick, i) for i in sorted(new_indices))
    if len(_recent_matures) < CHAIN_BLOOM_MIN_PLOTS:
        return
    for position, (_tick, index) in enumerate(_recent_matures):
        _pending_bloom[index] = min(position, CHAIN_BLOOM_MAX_RANK)


# --- GB-28: Forest Almanac ------------------------------------------------------------------------------------

ALMANAC_TREES = [
    ("evergreen", "\U0001F332", "Evergreen stand", lambda: True),
    ("seedling", "\U0001F331", "Replanted seedling", lambda: total_replants >= 1),
    ("deciduous", "\U0001F333", "Recovered woodland", lambda: total_recoveries >= 1),
    ("crown", "\U0001F451", "Old-growth crown", lambda: any(p.mature_celebrated for p in plots)),
]


def almanac_sections():
    """The Almanac as data: [(title, [(icon, name, found, hint), ...])]. Trees
    and wildlife show a silhouette until found; rare wildlife and hidden
    structures show '???' as their name."""
    seen_names = {name for _icon, name in species_seen()}
    trees = [(icon, name, bool(cond()), "") for _id, icon, name, cond in ALMANAC_TREES]
    wildlife = [(icon, name, name in seen_names, "") for icon, name in WILDLIFE_SPECIES]
    rare = [(icon, name, rid in rare_wildlife_found, hint) for rid, icon, name, hint in RARE_WILDLIFE]
    structures = [("\U0001F333", "Heart Tree", heart_tree_index is not None, "")]
    return [
        ("Trees planted", trees),
        ("Wildlife seen", wildlife),
        ("Rare wildlife", rare),
        ("Hidden structures", structures),
    ]


def seasons_survived():
    return forest_tick // SEASON_CYCLE_TICKS


def almanac_found_total():
    found = total = 0
    for _title, entries in almanac_sections():
        total += len(entries)
        found += sum(1 for entry in entries if entry[2])
    return found, total


def on_toggle_almanac(event=None):
    global almanac_open
    almanac_open = not almanac_open
    render_almanac()


def render_almanac():
    toggle = _el("almanac-toggle-button")
    panel = _el("almanac-panel")
    if toggle is None or panel is None:
        return
    found, total = almanac_found_total()
    toggle.innerText = f"Hide Almanac ({found}/{total})" if almanac_open else f"\U0001F4DA Almanac ({found}/{total})"
    panel.hidden = not almanac_open
    if not almanac_open:
        return
    panel.innerHTML = ""
    title = document.createElement("h2")
    title.className = "almanac-title"
    title.innerText = f"Forest Almanac: {forest_name}" if forest_name else "Forest Almanac"
    panel.appendChild(title)

    for section_title, entries in almanac_sections():
        heading = document.createElement("h3")
        heading.className = "almanac-heading"
        heading.innerText = f"{section_title} ({sum(1 for e in entries if e[2])}/{len(entries)})"
        panel.appendChild(heading)
        row = document.createElement("ul")
        row.className = "almanac-list"
        for icon, name, is_found, _hint in entries:
            item = document.createElement("li")
            item.className = "almanac-item almanac-item--found" if is_found else "almanac-item almanac-item--unfound"
            shown = name if is_found else "???"
            item.setAttribute("aria-label", f"{name}: found" if is_found else f"{section_title}: not yet found")
            glyph = document.createElement("span")
            glyph.className = "almanac-icon" if is_found else "almanac-icon almanac-silhouette"
            glyph.setAttribute("aria-hidden", "true")
            # Hidden structures give away nothing before they are found: no silhouette either.
            glyph.innerText = "" if (section_title == "Hidden structures" and not is_found) else icon
            item.appendChild(glyph)
            text = document.createElement("span")
            text.className = "almanac-name"
            text.innerText = shown
            item.appendChild(text)
            row.appendChild(item)
        panel.appendChild(row)

    seasons_heading = document.createElement("h3")
    seasons_heading.className = "almanac-heading"
    seasons_heading.innerText = f"Seasons survived: {seasons_survived()}"
    panel.appendChild(seasons_heading)
    seasons_row = document.createElement("ul")
    seasons_row.className = "almanac-list"
    for k, season in enumerate(SEASONS):
        done = seasons_survived() > k
        item = document.createElement("li")
        item.className = "almanac-item almanac-item--found" if done else "almanac-item almanac-item--unfound"
        item.setAttribute("aria-label", f"{SEASON_LABEL[season]}: {'lived through' if done else 'not yet lived through'}")
        glyph = document.createElement("span")
        glyph.className = "almanac-icon" if done else "almanac-icon almanac-silhouette"
        glyph.setAttribute("aria-hidden", "true")
        glyph.innerText = SEASON_ICON[season]
        item.appendChild(glyph)
        text = document.createElement("span")
        text.className = "almanac-name"
        text.innerText = SEASON_LABEL[season] if done else "???"
        item.appendChild(text)
        seasons_row.appendChild(item)
    panel.appendChild(seasons_row)
    streak_line = document.createElement("p")
    streak_line.className = "almanac-note"
    streak_line.innerText = f"Perfect Season streak: {perfect_streak}"
    panel.appendChild(streak_line)
    render_challenge_badges(panel)  # GB-17


# ===========================================================================
# GB batch 2 -- behaviour (constants and state are above reset_session()).
# ===========================================================================

# --- display options read from localStorage (B-8, B-10, B-26) ------------------------------------------------

def ui_pref(key, default=""):
    """A per-browser display option written by settings.js (never saved with a game)."""
    value = _read_local_storage_item(key)
    return default if value is None else str(value)


def number_format_mode():
    mode = ui_pref(UI_PREF_NUMBER_FORMAT, NUMBER_FORMAT_STANDARD)
    return mode if mode in NUMBER_FORMATS else NUMBER_FORMAT_STANDARD


def _compact_number(value):
    sign = "-" if value < 0 else ""
    magnitude = abs(value)
    suffixes = ((1e9, "B"), (1e6, "M"), (1e3, "k"))
    for position, (limit, suffix) in enumerate(suffixes):
        if magnitude >= limit:
            scaled = round(magnitude / limit, 1)
            if scaled >= 1000 and position > 0:  # 999.96k is "1M", not "1000k"
                limit, suffix = suffixes[position - 1]
                scaled = round(magnitude / limit, 1)
            text = f"{scaled:.1f}"
            if text.endswith(".0"):
                text = text[:-2]
            return f"{sign}{text}{suffix}"
    return f"{sign}{magnitude:.1f}"


def fmt_num(value, decimals=1):
    """B-26: a number for the HUD and mobile dock in the player's chosen format."""
    mode = number_format_mode()
    if mode == NUMBER_FORMAT_GROUPED:
        return f"{value:,.{decimals}f}"
    if mode == NUMBER_FORMAT_COMPACT:
        return _compact_number(value)
    if mode == NUMBER_FORMAT_PRECISE:
        return f"{value:.{max(decimals, 2)}f}"
    return f"{value:.{decimals}f}"


def soil_band(plot):
    """B-10: (percent, band name) for a plot's soil quality."""
    pct = round(plot.productivity_multiplier() * 100)
    for floor, name in SOIL_BANDS:
        if pct >= floor:
            return pct, name
    return pct, SOIL_BANDS[-1][1]


def _plot_tooltip_detail(plot):
    """B-16: the second line of the plot card: age, biodiversity rate, clear count."""
    if plot.state in ACCRUING_STATES:
        age = f"standing {plot.ticks_intact} ticks"
        rate = BIODIVERSITY_ACCRUAL_PER_TICK
        if plot.specialization == SPECIALIZATION_BIODIVERSITY:
            rate *= SPECIALIST_BIODIVERSITY_MULTIPLIER
    elif plot.state == REPLANTING:
        age = f"replanting, {plot.replant_ticks_remaining} ticks to go"
        rate = 0.0
    else:
        age = "bare"
        rate = 0.0
    if plot.clear_count == 0:
        cleared = "never cleared"
    else:
        cleared = f"cleared {plot.clear_count} time{'s' if plot.clear_count != 1 else ''}"
    return f"Age: {age} · biodiversity +{rate:.2f}/tick · {cleared}"


# --- B-7: screen-reader announcer, C / R hotkeys -------------------------------------------------------------

ANNOUNCE_MAX_QUEUED = 6


def _announce(message):
    """Queues a sentence for the polite live region; the next render speaks it."""
    if message:
        _announce_queue.append(str(message))
        del _announce_queue[:-ANNOUNCE_MAX_QUEUED]


def render_announcer():
    if not _announce_queue:
        return
    text = ". ".join(m.rstrip(". ") for m in _announce_queue)
    del _announce_queue[:]
    element = _el("sr-announcer")
    if element is not None:
        element.innerText = text


def hotkey_clear_selected(event=None):
    """C: clears the selected plot (select one first: a deliberate two-step so a stray key cannot fell a tree)."""
    if selected_index is None:
        _announce("No plot selected. Select a plot with Enter or a click, then press C to clear it")
        render_announcer()
        return False
    before = plots[selected_index].state
    on_clear()
    return plots[selected_index].state != before


def hotkey_replant_selected(event=None):
    """R: replants the selected bare plot."""
    if selected_index is None:
        _announce("No plot selected. Select a plot with Enter or a click, then press R to replant it")
        render_announcer()
        return False
    before = plots[selected_index].state
    on_replant()
    return plots[selected_index].state != before


# --- B-12: season forecast -----------------------------------------------------------------------------------

def _next_weather_episode():
    """(kind, ticks until it starts, start tick) of the next rain or drought episode that has not
    started yet, or None. weather_at() is a pure function of the tick, so this is exact."""
    for ahead in range(1, SEASON_CYCLE_TICKS * len(SEASONS) + 1):  # a full year: episodes can be 100+ ticks apart
        episode = _weather_episode(forest_tick + ahead)
        if episode is not None and episode[1] > forest_tick:
            return episode[0], episode[1] - forest_tick, episode[1]
    return None


def season_forecast_text():
    first = SEASONS[(SEASONS.index(current_season()) + 1) % len(SEASONS)]
    second = SEASONS[(SEASONS.index(first) + 1) % len(SEASONS)]
    ticks_first = ticks_until_next_season()
    ticks_second = ticks_first + SEASON_CYCLE_TICKS
    text = (
        f"Forecast: {SEASON_LABEL[first]} x{SEASON_GROWTH_MULTIPLIER[first]:.2f} in {ticks_first} ticks, "
        f"then {SEASON_LABEL[second]} x{SEASON_GROWTH_MULTIPLIER[second]:.2f} in {ticks_second} ticks"
    )
    upcoming = _next_weather_episode()
    if upcoming is not None:
        kind, begins_in, _start = upcoming
        change = round((weather_multiplier_at(forest_tick + begins_in) - 1) * 100)
        text += (
            f" · {WEATHER_ICON[kind]} {WEATHER_LABEL[kind]} (growth {change:+d}%) "
            f"in {begins_in} ticks, lasting {WEATHER_DURATION_TICKS}"
        )
    return text


def render_season_forecast():
    element = _el("season-forecast")
    if element is not None:
        element.innerText = season_forecast_text()


# --- B-6: request pace ---------------------------------------------------------------------------------------

def current_request_interval():
    """Ticks between community requests: the Pass 3 interval scaled by the chosen pace."""
    factor = REQUEST_PACE_FACTOR.get(current_pace, 1.0)
    return max(5, int(round(STAKEHOLDER_EVENT_INTERVAL_TICKS * factor)))


def session_tag_text():
    """Names every non-default setting that changes how a run plays, so shared results stay honest."""
    parts = []
    if current_difficulty == DIFFICULTY_RANGER:
        parts.append("Forest ranger")
    if current_pace != PACE_NORMAL:
        parts.append(REQUEST_PACE_LABEL[current_pace].lower())
    if current_challenge != CHALLENGE_NONE:
        parts.append(f"{CHALLENGE_SPECS[current_challenge]['label']} challenge")
    return ", ".join(parts)


def on_pace_change(event=None):
    if event is None:
        return
    reset_session(pace=event.target.value)


# --- GB-17: challenge runs -----------------------------------------------------------------------------------

def _apply_challenge_start():
    """Called by reset_session() once the plots exist. Scorched Start burns two thirds of the forest."""
    global contract_clear_count_seen, contract_last_clear_tick
    if current_challenge == CHALLENGE_SCORCHED:
        count = int(round(len(plots) * CHALLENGE_SCORCHED_BARE_FRACTION))
        for index in sorted(range(len(plots)), key=lambda i: (_gb_hash(i, 17), i))[:count]:
            plot = plots[index]
            plot.state = BARE
            plot.value = 0.0
            plot.ticks_intact = 0
            plot.biodiversity = 0.0
    contract_clear_count_seen = _total_clear_count()
    contract_last_clear_tick = 0


def _challenge_regions_cleared():
    return any(p.clear_count for p in highland_plots) or any(p.clear_count for p in wetland_plots)


def challenge_goal():
    """(standing goal, income goal) for the current challenge; income goal is 0 unless Sprint."""
    n = len(plots)
    if current_challenge == CHALLENGE_PACIFIST:
        return CHALLENGE_PACIFIST_STANDING_PER_PLOT * n, 0
    if current_challenge == CHALLENGE_SCORCHED:
        return CHALLENGE_SCORCHED_STANDING_PER_PLOT * n, 0
    if current_challenge == CHALLENGE_NO_HIGHLAND:
        return CHALLENGE_NO_HIGHLAND_STANDING_PER_PLOT * n, 0
    if current_challenge == CHALLENGE_SPRINT:
        return CHALLENGE_SPRINT_STANDING_PER_PLOT * n, CHALLENGE_SPRINT_INCOME_PER_PLOT * n
    return 0, 0


def challenge_rule_text():
    standing, income = challenge_goal()
    if current_challenge == CHALLENGE_PACIFIST:
        return f"reach {standing} standing value without clearing any plot (a granted request counts as a clear)"
    if current_challenge == CHALLENGE_SCORCHED:
        return f"start with two thirds of the plots bare, then reach {standing} standing value"
    if current_challenge == CHALLENGE_SPRINT:
        return (
            f"within {CHALLENGE_SPRINT_TICK_LIMIT} ticks, bank {income} income and hold "
            f"{standing} standing value at the same time"
        )
    if current_challenge == CHALLENGE_NO_HIGHLAND:
        return f"reach {standing} standing value with Highland Grove and Wetland Forest sealed"
    return ""


def challenge_state():
    """None (no challenge), or active / complete / failed. Failure is read off the live forest, so an
    undone clear does not fail a Pacifist run."""
    if current_challenge == CHALLENGE_NONE:
        return None
    if challenge_complete_tick is not None:
        return CHALLENGE_COMPLETE
    if current_challenge == CHALLENGE_PACIFIST and (_total_clear_count() > 0 or _challenge_regions_cleared()):
        return CHALLENGE_FAILED
    if current_challenge == CHALLENGE_SPRINT and forest_tick > CHALLENGE_SPRINT_TICK_LIMIT:
        return CHALLENGE_FAILED
    return CHALLENGE_ACTIVE


def _challenge_goal_met():
    standing, income = challenge_goal()
    if standing <= 0:
        return False
    return standing_forest_value() >= standing and total_income >= income


def load_challenge_records():
    global _challenge_record_cache
    if _challenge_record_cache is None:
        records = {}
        raw = _read_local_storage_item(CHALLENGE_RECORDS_STORAGE_KEY)
        if raw:
            try:
                parsed = json.loads(raw)
            except ValueError:
                parsed = None
            if isinstance(parsed, dict):
                for key, value in parsed.items():
                    if key in CHALLENGE_SPECS and isinstance(value, int) and not isinstance(value, bool) and value > 0:
                        records[key] = value
        _challenge_record_cache = records
    return _challenge_record_cache


def challenge_badge_earned(challenge_id):
    """A badge is permanent in this browser: finishing a challenge once keeps it, whatever the session does next."""
    if challenge_id in load_challenge_records():
        return True
    return current_challenge == challenge_id and challenge_complete_tick is not None


def _record_challenge_completion(tick):
    records = load_challenge_records()
    best = records.get(current_challenge)
    if best is None or tick < best:
        records[current_challenge] = max(1, int(tick))
        _write_local_storage_item(CHALLENGE_RECORDS_STORAGE_KEY, json.dumps(records))


def _check_challenge():
    global challenge_complete_tick
    if challenge_state() != CHALLENGE_ACTIVE or not _challenge_goal_met():
        return
    challenge_complete_tick = forest_tick
    label = CHALLENGE_SPECS[current_challenge]["label"]
    _record_challenge_completion(forest_tick)
    _log_event("challenge", f"{label} challenge complete in {forest_tick} ticks", None)
    _gb_toast(f"{CHALLENGE_SPECS[current_challenge]['icon']} {label} challenge complete: badge earned")
    _flash_forest_pulse()


def challenge_status_text():
    state = challenge_state()
    if state is None:
        return ""
    spec = CHALLENGE_SPECS[current_challenge]
    head = f"{spec['icon']} Challenge: {spec['label']} · {challenge_rule_text()}"
    standing, income = challenge_goal()
    best = load_challenge_records().get(current_challenge)
    best_text = f" Your fastest finish: {best} ticks." if best else ""
    if state == CHALLENGE_COMPLETE:
        return f"{head}. Complete in {challenge_complete_tick} ticks, badge earned.{best_text}"
    if state == CHALLENGE_FAILED:
        why = "a plot was cleared" if current_challenge == CHALLENGE_PACIFIST else "time ran out"
        return f"{head}. Failed ({why}). Reset Session to retry.{best_text}"
    if current_challenge == CHALLENGE_SPRINT:
        progress = (
            f"standing {int(standing_forest_value())}/{standing}, income {int(total_income)}/{income}, "
            f"{max(0, CHALLENGE_SPRINT_TICK_LIMIT - forest_tick)} ticks left"
        )
    else:
        progress = f"standing {int(standing_forest_value())}/{standing}"
    return f"{head}. In progress: {progress}.{best_text}"


def render_challenge_status():
    element = _el("challenge-status")
    if element is None:
        return
    text = challenge_status_text()
    element.hidden = not text
    element.innerText = text
    state = challenge_state()
    for name in (CHALLENGE_ACTIVE, CHALLENGE_COMPLETE, CHALLENGE_FAILED):
        if name == state:
            element.classList.add(f"challenge-status--{name}")
        else:
            element.classList.remove(f"challenge-status--{name}")


def on_challenge_change(event=None):
    if event is None:
        return
    reset_session(challenge=event.target.value)


def challenge_badge_entries():
    """[(icon, label, earned, best_ticks_or_None)] for the Almanac."""
    records = load_challenge_records()
    return [
        (spec["icon"], spec["label"], challenge_badge_earned(cid), records.get(cid))
        for cid, spec in CHALLENGE_SPECS.items()
    ]


def render_challenge_badges(panel):
    """Appends the Almanac's challenge-badge row."""
    entries = challenge_badge_entries()
    heading = document.createElement("h3")
    heading.className = "almanac-heading"
    heading.innerText = f"Challenge badges ({sum(1 for e in entries if e[2])}/{len(entries)})"
    panel.appendChild(heading)
    row = document.createElement("ul")
    row.className = "almanac-list"
    for icon, label, earned, best in entries:
        item = document.createElement("li")
        item.className = "almanac-item almanac-item--found" if earned else "almanac-item almanac-item--unfound"
        item.setAttribute("aria-label", f"{label} challenge: {'badge earned' if earned else 'not yet finished'}")
        glyph = document.createElement("span")
        glyph.className = "almanac-icon" if earned else "almanac-icon almanac-silhouette"
        glyph.setAttribute("aria-hidden", "true")
        glyph.innerText = icon
        item.appendChild(glyph)
        text = document.createElement("span")
        text.className = "almanac-name"
        text.innerText = (f"{label} ({best} ticks)" if best else label) if earned else "???"
        item.appendChild(text)
        row.appendChild(item)
    panel.appendChild(row)


# --- GB-9: Ranger contracts board ------------------------------------------------------------------------------

def _contract_target_and_base(type_id):
    n = len(plots)
    if type_id == "replant":
        return 3, total_replants
    if type_id == "mature":
        return max(2, n // 6, _mature_plot_count() + 2), 0
    if type_id == "wildlife":
        return max(3, n // 5, _wildlife_active_count() + 2), 0
    if type_id == "decline":
        return 2, stakeholder_declines_count
    if type_id == "accept":
        return 1, stakeholder_grants_count
    if type_id == "tend":
        return 2, tends_done
    if type_id == "seedling":
        return 1, seedlings_caught
    if type_id == "standing":
        return max(10, int(round((standing_forest_value() * 1.25 + 60 * n) / 10.0)) * 10), 0
    if type_id == "calm":
        return CONTRACT_CALM_TICKS, 0
    return min(100, max(60, community_relations + 15)), 0  # trust


def _contract_progress(contract):
    type_id = contract["type"]
    base = contract.get("base", 0)
    if type_id == "replant":
        return total_replants - base
    if type_id == "mature":
        return _mature_plot_count()
    if type_id == "wildlife":
        return _wildlife_active_count()
    if type_id == "decline":
        return stakeholder_declines_count - base
    if type_id == "accept":
        return stakeholder_grants_count - base
    if type_id == "tend":
        return tends_done - base
    if type_id == "seedling":
        return seedlings_caught - base
    if type_id == "standing":
        return int(standing_forest_value())
    if type_id == "calm":
        return max(0, forest_tick - contract_last_clear_tick)
    return community_relations


def contract_text(contract):
    target = contract["target"]
    return {
        "replant": f"Replant {target} plots",
        "mature": f"Have {target} fully mature plots at once",
        "wildlife": f"Have wildlife on {target} plots at once",
        "decline": f"Decline {target} community requests",
        "accept": f"Say yes to {target} community request or offer",
        "tend": f"Tend {target} plots (T)",
        "seedling": "Catch a golden seedling (G)",
        "standing": f"Grow your standing value to {target}",
        "calm": f"Go {target} ticks without clearing a plot",
        "trust": f"Raise community relations to {target}",
    }[contract["type"]]


def contract_reward():
    return CONTRACT_REWARD_PER_PLOT * len(plots)


def contract_rank():
    title = CONTRACT_RANKS[0][1]
    for needed, name in CONTRACT_RANKS:
        if contracts_completed >= needed:
            title = name
    return title


def _pick_contract_type():
    """Deterministic pick (hash of the tick and the count so far). Contracts whose stamp you have not
    collected come first, so a patient player sees all ten."""
    on_board = {c["type"] for c in contract_board}
    start = _gb_hash(forest_tick, contracts_completed, len(contract_board), 91) % len(CONTRACT_TYPES)
    ordered = [CONTRACT_TYPES[(start + k) % len(CONTRACT_TYPES)][0] for k in range(len(CONTRACT_TYPES))]
    candidates = [t for t in ordered if t not in on_board and not (t == "trust" and community_relations >= 90)]
    fresh = [t for t in candidates if t not in contract_stamps]
    pool = fresh or candidates
    return pool[0] if pool else None


def _add_contract():
    type_id = _pick_contract_type()
    if type_id is None:
        return False
    target, base = _contract_target_and_base(type_id)
    contract_board.append({"type": type_id, "target": target, "base": base})
    return True


def _fill_contract_board():
    del contract_board[:]
    if current_challenge != CHALLENGE_NONE:
        return
    while len(contract_board) < CONTRACT_SLOTS and _add_contract():
        pass


def _stamp_name(type_id):
    for tid, _icon, name in CONTRACT_TYPES:
        if tid == type_id:
            return name
    return type_id


def _complete_contract(contract):
    global total_income, contracts_completed, contract_refill_ticks
    contract_board.remove(contract)
    reward = contract_reward()
    total_income += reward
    contracts_completed += 1
    new_stamp = contract["type"] not in contract_stamps
    if new_stamp:
        contract_stamps.append(contract["type"])
    if len(contract_board) < CONTRACT_SLOTS and contract_refill_ticks <= 0:
        contract_refill_ticks = CONTRACT_REFILL_TICKS
    _log_event("contract", f"Contract done: {contract_text(contract)} (+{reward} income)", None)
    stamp_part = f", new stamp: {_stamp_name(contract['type'])}" if new_stamp else ""
    _gb_toast(f"\U0001F4DC Contract done: +{reward} income{stamp_part}")


def _advance_contracts():
    global contract_refill_ticks, contract_last_clear_tick, contract_clear_count_seen
    clears = _total_clear_count()
    if clears > contract_clear_count_seen:
        contract_last_clear_tick = forest_tick
    contract_clear_count_seen = clears
    if current_challenge != CHALLENGE_NONE:
        return
    for contract in list(contract_board):
        if _contract_progress(contract) >= contract["target"]:
            _complete_contract(contract)
    if len(contract_board) < CONTRACT_SLOTS:
        if contract_refill_ticks > 0:
            contract_refill_ticks -= 1
        elif _add_contract() and len(contract_board) < CONTRACT_SLOTS:
            contract_refill_ticks = CONTRACT_REFILL_TICKS


def on_toggle_contracts(event=None):
    global contracts_open
    contracts_open = not contracts_open
    render_contracts()


def render_contracts():
    toggle = _el("contracts-toggle-button")
    panel = _el("contracts-panel")
    if toggle is None or panel is None:
        return
    if current_challenge != CHALLENGE_NONE:
        label_count = "closed"
    else:
        label_count = f"{len(contract_board)} open"
    toggle.innerText = (
        f"Hide Contracts ({label_count})" if contracts_open else f"\U0001F4DC Contracts ({label_count})"
    )
    panel.hidden = not contracts_open
    if not contracts_open:
        return
    panel.innerHTML = ""
    title = document.createElement("h2")
    title.className = "contracts-title"
    title.innerText = "Ranger contracts"
    panel.appendChild(title)
    rank = document.createElement("p")
    rank.className = "contracts-rank"
    rank.innerText = (
        f"Rank: {contract_rank()} · {contracts_completed} contract{'s' if contracts_completed != 1 else ''} done "
        f"· each pays {contract_reward()} income"
    )
    panel.appendChild(rank)
    if current_challenge != CHALLENGE_NONE:
        closed = document.createElement("p")
        closed.className = "contracts-note"
        closed.innerText = "The ranger service is closed during a challenge run. Choose No challenge to reopen the board."
        panel.appendChild(closed)
    else:
        board = document.createElement("ul")
        board.className = "contracts-list"
        for contract in contract_board:
            progress = max(0, min(contract["target"], _contract_progress(contract)))
            item = document.createElement("li")
            item.className = "contract-card"
            label = document.createElement("p")
            label.className = "contract-card-label"
            icon = next((c[1] for c in CONTRACT_TYPES if c[0] == contract["type"]), "")
            label.innerText = f"{icon} {contract_text(contract)}"
            item.appendChild(label)
            count = document.createElement("p")
            count.className = "contract-card-progress"
            count.innerText = f"{progress} of {contract['target']}"
            item.appendChild(count)
            bar = document.createElement("progress")
            bar.className = "contract-card-bar"
            bar.max = contract["target"]
            bar.value = progress
            bar.setAttribute("aria-label", f"{contract_text(contract)}: {progress} of {contract['target']}")
            item.appendChild(bar)
            board.appendChild(item)
        if not contract_board:
            waiting = document.createElement("li")
            waiting.className = "contract-card contract-card--waiting"
            waiting.innerText = f"Next contract in {max(1, contract_refill_ticks)} ticks"
            board.appendChild(waiting)
        panel.appendChild(board)
    stamps_heading = document.createElement("h3")
    stamps_heading.className = "almanac-heading"
    stamps_heading.innerText = f"Stamps ({len(contract_stamps)}/{len(CONTRACT_TYPES)})"
    panel.appendChild(stamps_heading)
    stamp_row = document.createElement("ul")
    stamp_row.className = "almanac-list"
    for type_id, icon, name in CONTRACT_TYPES:
        got = type_id in contract_stamps
        item = document.createElement("li")
        item.className = "almanac-item almanac-item--found" if got else "almanac-item almanac-item--unfound"
        item.setAttribute("aria-label", f"{name}: {'stamped' if got else 'not yet stamped'}")
        glyph = document.createElement("span")
        glyph.className = "almanac-icon" if got else "almanac-icon almanac-silhouette"
        glyph.setAttribute("aria-hidden", "true")
        glyph.innerText = icon
        item.appendChild(glyph)
        text = document.createElement("span")
        text.className = "almanac-name"
        text.innerText = name if got else "???"
        item.appendChild(text)
        stamp_row.appendChild(item)
    panel.appendChild(stamp_row)


def _contracts_state_fields():
    """Written only once the board has moved on from a fresh session's (the opening board is a pure
    function of an empty forest, so a save without the key rebuilds exactly it)."""
    if current_challenge != CHALLENGE_NONE:
        return {}
    fresh = not (
        contracts_completed or contract_stamps or contract_refill_ticks or contract_last_clear_tick
        or tends_done or seedlings_caught
    )
    if fresh:
        return {}
    return {
        "ranger_contracts": {
            "board": [dict(c) for c in contract_board],
            "stamps": list(contract_stamps),
            "completed": contracts_completed,
            "refill": contract_refill_ticks,
            "last_clear_tick": contract_last_clear_tick,
            "tends": tends_done,
            "seedlings": seedlings_caught,
        }
    }


def _load_contracts(data):
    """Applies the validated ranger_contracts blob (a save without one keeps the fresh board)."""
    global contracts_completed, contract_refill_ticks, contract_last_clear_tick
    global contract_clear_count_seen, tends_done, seedlings_caught
    contract_clear_count_seen = _total_clear_count()
    raw = data.get("ranger_contracts")
    if not isinstance(raw, dict) or current_challenge != CHALLENGE_NONE:
        return
    valid = {t[0] for t in CONTRACT_TYPES}
    board = []
    seen = set()
    saved_board = raw.get("board")
    for entry in saved_board if isinstance(saved_board, list) else []:
        if not isinstance(entry, dict) or len(board) >= CONTRACT_SLOTS:
            continue
        type_id = entry.get("type")
        if not isinstance(type_id, str) or type_id not in valid or type_id in seen:
            continue
        target = _number_or(entry.get("target"), None, 1, 100000)
        if target is None:
            continue
        seen.add(type_id)
        board.append({"type": type_id, "target": int(target), "base": int(_number_or(entry.get("base"), 0, 0, 10 ** 9))})
    contract_board[:] = board
    del contract_stamps[:]
    saved_stamps = raw.get("stamps")
    for type_id in saved_stamps if isinstance(saved_stamps, list) else []:
        if isinstance(type_id, str) and type_id in valid and type_id not in contract_stamps:
            contract_stamps.append(type_id)
    contracts_completed = int(_number_or(raw.get("completed"), 0, 0, 10 ** 6))
    contract_refill_ticks = int(_number_or(raw.get("refill"), 0, 0, CONTRACT_REFILL_TICKS))
    contract_last_clear_tick = int(_number_or(raw.get("last_clear_tick"), 0, 0, 10 ** 9))
    tends_done = int(_number_or(raw.get("tends"), 0, 0, 10 ** 9))
    seedlings_caught = int(_number_or(raw.get("seedlings"), 0, 0, 10 ** 9))


def _reset_gb2_state():
    global challenge_complete_tick, contracts_completed, contract_refill_ticks
    global contract_last_clear_tick, contract_clear_count_seen, tends_done, seedlings_caught
    challenge_complete_tick = None
    contracts_completed = 0
    contract_refill_ticks = 0
    contract_last_clear_tick = 0
    contract_clear_count_seen = 0
    tends_done = 0
    seedlings_caught = 0
    del contract_stamps[:]
    del _announce_queue[:]
    _fill_contract_board()


def _gb2_state_fields():
    out = {}
    if current_challenge != CHALLENGE_NONE:
        out["challenge"] = {"id": current_challenge, "done_tick": challenge_complete_tick}
    if current_pace != PACE_NORMAL:
        out["request_pace"] = current_pace
    out.update(_contracts_state_fields())
    return out


def _load_gb2_state(data):
    global challenge_complete_tick
    if current_challenge != CHALLENGE_NONE:
        saved = data.get("challenge")
        done = saved.get("done_tick") if isinstance(saved, dict) else None
        if isinstance(done, int) and not isinstance(done, bool) and done >= 0:
            challenge_complete_tick = done
    _load_contracts(data)


def _saved_challenge_id(data):
    saved = data.get("challenge")
    cid = saved.get("id") if isinstance(saved, dict) else None
    return cid if isinstance(cid, str) and cid in CHALLENGE_SPECS else CHALLENGE_NONE


def _saved_pace(data):
    pace = data.get("request_pace")
    return pace if isinstance(pace, str) and pace in REQUEST_PACE_FACTOR else PACE_NORMAL


# --- per-tick hook and state -------------------------------------------------------------------------------------------

def _gb_after_tick():
    """Everything GB does at the end of a tick (after accrual and requests)."""
    _advance_tend()
    _advance_golden_seedling()
    _advance_undo()
    _note_season_relations()
    _check_rare_wildlife()
    _check_heart_tree()
    _check_milestones()
    _check_challenge()  # GB-17
    _advance_contracts()  # GB-9


def _reset_gb_state():
    global forest_name, adopted_plot_nickname, heart_tree_index, rare_wildlife_found
    global peak_standing_value, milestone_tier, tend_cooldown_ticks, perfect_streak
    global season_cleared, season_min_relations
    global golden_seedling, _tend_message, _undo_snapshot
    global _recent_matures, _golden_next_tick
    del _gb_toast_queue[:]
    forest_name = ""
    adopted_plot_nickname = ""
    heart_tree_index = None
    rare_wildlife_found = []
    peak_standing_value = 0.0
    milestone_tier = 0
    tend_cooldown_ticks = 0
    perfect_streak = 0
    season_cleared = False
    season_min_relations = None
    golden_seedling = None
    _golden_next_tick = GOLDEN_SEEDLING_MIN_GAP
    _tend_message = ""
    _undo_snapshot = None
    _recent_matures = []
    _pending_bloom.clear()
    _pending_golden_bursts.clear()
    _reset_gb2_state()  # GB batch 2: challenge result, contract board
    _sync_name_inputs()


def _gb_state_fields():
    """The GB save keys, each written only when it differs from a fresh game."""
    out = {}
    if forest_name:
        out["forest_name"] = forest_name
    if adopted_plot_nickname and adopted_plot_index is not None:
        out["adopted_plot_nickname"] = adopted_plot_nickname
    if heart_tree_index is not None:
        out["heart_tree_index"] = heart_tree_index
    if rare_wildlife_found:
        out["rare_wildlife_found"] = list(rare_wildlife_found)
    if peak_standing_value > 0:
        out["peak_standing_value"] = peak_standing_value
    if milestone_tier > 0:
        out["milestone_tier"] = milestone_tier
    tended = _tended_plot()
    if tended is not None:
        out["tend"] = {"plot": tended.index, "ticks_left": tended.tend_ticks_left}
    if tend_cooldown_ticks > 0:
        out["tend_cooldown_ticks"] = tend_cooldown_ticks
    low = season_min_relations
    if perfect_streak > 0 or season_cleared or (low is not None and low < PERFECT_SEASON_MIN_RELATIONS):
        out["perfect_season"] = {
            "streak": perfect_streak,
            "cleared": season_cleared,
            "min_relations": low if low is not None else community_relations,
        }
    out.update(_gb2_state_fields())
    return out


def _load_gb_state(data):
    """Validates and applies the GB save keys; anything missing or malformed
    falls back to the fresh-game value (a save is authoritative, so a live
    session's names/discoveries must not leak into a save that lacks them)."""
    global forest_name, adopted_plot_nickname, heart_tree_index
    global peak_standing_value, milestone_tier, tend_cooldown_ticks, perfect_streak
    global season_cleared, season_min_relations

    _reset_gb_state()
    for plot in plots:
        plot.tend_ticks_left = 0
    _schedule_golden_seedling()

    forest_name = _clean_name(data.get("forest_name"), FOREST_NAME_MAX)
    if adopted_plot_index is not None:
        adopted_plot_nickname = _clean_name(data.get("adopted_plot_nickname"), NICKNAME_MAX)

    saved_heart = data.get("heart_tree_index")
    if (
        isinstance(saved_heart, int) and not isinstance(saved_heart, bool)
        and 0 <= saved_heart < len(plots) and len(_neighbour_indices(saved_heart)) == 8
    ):
        heart_tree_index = saved_heart

    saved_rare = data.get("rare_wildlife_found")
    if isinstance(saved_rare, list):
        valid_ids = [entry[0] for entry in RARE_WILDLIFE]
        for rare_id in saved_rare:
            if isinstance(rare_id, str) and rare_id in valid_ids and rare_id not in rare_wildlife_found:
                rare_wildlife_found.append(rare_id)

    peak_standing_value = _number_or(data.get("peak_standing_value"), 0.0)
    peak_standing_value = max(peak_standing_value, standing_forest_value())
    tiers_now = _tiers_reached_for(peak_standing_value)
    if "milestone_tier" in data:
        milestone_tier = int(_number_or(data.get("milestone_tier"), 0, 0, len(STANDING_TIERS)))
        milestone_tier = min(milestone_tier, tiers_now)
    else:
        milestone_tier = tiers_now  # an older save: no celebration for what it already had

    saved_tend = data.get("tend")
    if isinstance(saved_tend, dict):
        tend_index = saved_tend.get("plot")
        if isinstance(tend_index, int) and not isinstance(tend_index, bool) and 0 <= tend_index < len(plots):
            left = int(_number_or(saved_tend.get("ticks_left"), 0, 0, TEND_DURATION_TICKS))
            if left > 0 and _tendable(plots[tend_index]):
                plots[tend_index].tend_ticks_left = left
    tend_cooldown_ticks = int(_number_or(data.get("tend_cooldown_ticks"), 0, 0, TEND_COOLDOWN_TICKS))

    saved_perfect = data.get("perfect_season")
    if isinstance(saved_perfect, dict):
        perfect_streak = int(_number_or(saved_perfect.get("streak"), 0, 0, 9999))
        season_cleared = saved_perfect.get("cleared") is True
        low = _number_or(saved_perfect.get("min_relations"), None, 0, 100)
        season_min_relations = int(low) if low is not None else None
    _load_gb2_state(data)
    _sync_name_inputs()


def render():
    render_info_page()
    render_grid()
    render_panel()
    render_stats()
    render_stakeholder_panel()
    render_real_world()
    render_grid_size_select()
    render_reset_button()
    render_adopt_panel()
    render_specialist_panel()
    render_season_indicator()
    render_season_forecast()
    render_challenge_status()
    render_forest_title()
    render_tend_panel()
    render_undo_chip()
    render_almanac()
    render_contracts()
    render_session_summary()
    render_highland_section()
    render_wetland_section()
    update_achievements_display()
    update_changelog_display()
    _sync_earned_and_toast()
    render_announcer()  # B-7: last, so everything this render queued is spoken once


def _make_select_handler(index):
    def handler(event):
        select_plot(index)
    return handler


def select_plot(index):
    global selected_index
    if golden_seedling is not None and golden_seedling["plot"] == index:
        collect_golden_seedling(index)  # GB-2: clicking the plot the seedling sits on catches it
    selected_index = index
    render()


def on_clear(event=None):
    global total_income, season_cleared
    if selected_index is None:
        return
    if selected_index == heart_tree_index:
        return  # GB-8: the Heart Tree is never felled
    plot = plots[selected_index]
    before_fields = dict(plot.__dict__)
    best_income_before = personal_best["income"]
    payout = plot.clear()
    if payout is not None:
        total_income += payout
        _log_event("clear", f"Cleared {_plot_ref(selected_index)} for {payout:.1f} income", selected_index)
        was_cleared = season_cleared
        season_cleared = True  # GB-30
        _arm_undo(selected_index, before_fields, payout, forest_log[-1], was_cleared, best_income_before)  # GB-18
    render()


def on_replant(event=None):
    global total_replants
    if selected_index is None:
        return
    if plots[selected_index].replant():
        total_replants += 1
        _log_event("replant", f"Replanted {_plot_ref(selected_index)}", selected_index)
    render()


def _note_recovery(plot):
    global total_recoveries
    total_recoveries += 1
    _log_event("recovered", f"{_plot_ref(plot.index)} finished recovering", plot.index)


def tick(event=None):
    global pending_stakeholder_request, _session_ticks, forest_tick
    _session_ticks += 1
    forest_tick += 1
    if forest_tick % SEASON_CYCLE_TICKS == 0:
        _end_season()  # GB-30: score the season that just ended
    _pending_value_pops.clear()
    _pending_mature_bursts.clear()
    aura = _heart_tree_aura()  # GB-8
    newly_mature = []
    for plot in plots:
        delta = plot.accrue_tick()
        if delta > 0 and plot.index in aura:
            bonus = delta * HEART_TREE_AURA_BONUS
            plot.value += bonus
            delta += bonus
        if delta >= VALUE_POP_MIN_DELTA:
            _pending_value_pops[plot.index] = delta
        if plot.advance_recovery():
            _note_recovery(plot)
        elif plot.tend_ticks_left > 0 and plot.state == REPLANTING and plot.advance_recovery():
            _note_recovery(plot)  # GB-4: a tended replanting plot recovers an extra tick per tick
        if plot.has_wildlife() and plot.index not in plots_with_wildlife_ever:
            icon, name = wildlife_species_for_plot(plot.index)
            _log_event("wildlife", f"{icon} A {name} appeared at {_plot_ref(plot.index)}", plot.index)
        if plot.has_wildlife():
            plots_with_wildlife_ever.add(plot.index)
        if (
            plot.state in ACCRUING_STATES
            and not plot.mature_celebrated
            and plot.maturity_fraction() >= 1.0
        ):
            plot.mature_celebrated = True
            _pending_mature_bursts.add(plot.index)
            newly_mature.append(plot.index)
            _log_event("mature", f"{_plot_ref(plot.index)} reached full maturity", plot.index)
    if newly_mature:
        _register_chain_bloom(newly_mature)  # GB-27
    if pending_stakeholder_request is not None and not _stakeholder_target_is_still_standing():
        # The requested plot was cleared/replanted directly (see the
        # grant/decline guard above) — drop the now-stale request so a new
        # one can still fire later, instead of maybe_trigger_stakeholder_
        # request() refusing to raise one forever because it sees a
        # (meaningless) request still pending.
        pending_stakeholder_request = None
    had_request = pending_stakeholder_request is not None
    maybe_trigger_stakeholder_request()
    if pending_stakeholder_request is not None and not had_request:
        _announce("New community request. " + stakeholder_request_message())  # B-7
    _gb_after_tick()  # GB-2/4/8/20/22/30: timers, discoveries and tiers
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
        **_gb_state_fields(),
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
    saved_challenge = _saved_challenge_id(data)
    saved_pace = _saved_pace(data)
    if (
        saved_grid_size != current_grid_size
        or saved_difficulty != current_difficulty
        or saved_challenge != current_challenge
        or saved_pace != current_pace
        or len(data.get("plots", [])) != len(plots)
    ):
        reset_session(
            grid_size=saved_grid_size, _render_after=False, difficulty=saved_difficulty,
            challenge=saved_challenge, pace=saved_pace,
        )

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
    _load_gb_state(data)  # GB batch 1: names, discoveries, tiers, tend, streak (validated)
    _previously_earned_ids = _earned_snapshot()
    _story_reach_all(_previously_earned_ids)  # W1: a loaded save's earned chapters come back too

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
    for element_id, handler in (("challenge-select", on_challenge_change), ("request-pace-select", on_pace_change)):
        element = _el(element_id)  # GB-17 / B-6
        if element is not None:
            element.addEventListener("change", create_proxy(handler))
    document.getElementById("highland-clear-button").addEventListener(
        "click", create_proxy(on_highland_clear)
    )
    document.getElementById("highland-replant-button").addEventListener(
        "click", create_proxy(on_highland_replant)
    )
    document.getElementById("wetland-clear-button").addEventListener(
        "click", create_proxy(on_wetland_clear)
    )
    # GB batch 1: optional elements (a page or test DOM without them just skips the wiring).
    for element_id, event_name, handler in (
        ("tend-button", "click", on_tend),
        ("undo-clear-button", "click", undo_last_clear),
        ("almanac-toggle-button", "click", on_toggle_almanac),
        ("contracts-toggle-button", "click", on_toggle_contracts),
        ("forest-name-input", "change", on_forest_name_change),
        ("plot-nickname-input", "change", on_plot_nickname_change),
    ):
        element = _el(element_id)
        if element is not None:
            element.addEventListener(event_name, create_proxy(handler))
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
    _fill_contract_board()  # GB-9: the module starts without a reset_session(), so seed the board here
    setInterval(create_proxy(tick), TICK_INTERVAL_MS)
    render()


setup()
