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


class Plot:
    def __init__(self, index):
        self.index = index
        self.state = PRESERVED
        self.value = 0.0
        self.ticks_intact = 0
        self.clear_count = 0
        self.replant_ticks_remaining = 0
        self.just_recovered = False
        self.biodiversity = 0.0

    def productivity_multiplier(self):
        """Soil quality factor from past clearing — 1.0 for a never-cleared
        plot, stepping down permanently with each clear, floored so a plot
        never stops producing entirely."""
        return max(
            MIN_PRODUCTIVITY_MULTIPLIER,
            1 - DEGRADE_PER_CLEAR * self.clear_count,
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
        self.value += delta
        self.biodiversity += BIODIVERSITY_ACCRUAL_PER_TICK
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
        return payout

    def replant(self):
        if "replant" not in VALID_ACTIONS[self.state]:
            return False
        self.state = REPLANTING
        self.replant_ticks_remaining = RECOVERY_TICKS
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


# B2 (planning/TODO.md "Per-game: Canopy"): a "reset session" option, folded
# together with B13's grid-size variant since both mean "rebuild the whole
# session from scratch" -- offering them as two separate controls would just
# mean two code paths doing almost the same thing. Deliberately a hard reset
# with no confirmation dialog: matches the site's "no dead-end states"
# philosophy (nothing here is a save file being destroyed -- that's what the
# separate save-code widget is for) and the shared confirm-dialog pattern
# the TODO's own site-wide goal describes is still just a design, not a
# built component, elsewhere in this file.
def reset_session(grid_size=None, _render_after=True):
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
    if _render_after:
        render()
    return True


def on_reset_session(event=None):
    reset_session()


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
    return plot.state in ACCRUING_STATES


def _note_community_relations_change():
    """Tracks the running minimum community_relations has ever reached —
    achievements' `rebuilt_trust` needs to know relations genuinely dropped
    low at some point, not just where they sit right now."""
    global community_relations_min_ever
    community_relations_min_ever = min(community_relations_min_ever, community_relations)


def grant_stakeholder_request(event=None):
    global pending_stakeholder_request, community_relations, total_income
    global stakeholder_grants_count
    if pending_stakeholder_request is None:
        return False
    if not _stakeholder_target_is_still_standing():
        pending_stakeholder_request = None
        render()
        return False
    kind = pending_stakeholder_request.get("kind", STAKEHOLDER_KIND_CLEAR)
    if kind == STAKEHOLDER_KIND_INCENTIVE:
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
        community_relations = min(100, community_relations + STAKEHOLDER_GRANT_RELATIONS_DELTA)
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
    if kind != STAKEHOLDER_KIND_INCENTIVE:
        community_relations = max(0, community_relations + STAKEHOLDER_DECLINE_RELATIONS_DELTA)
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
    return label


def render_grid():
    grid_el = document.getElementById("plot-grid")
    grid_el.innerHTML = ""
    # B16: lets the plain-JS arrow-key handler in index.html know the grid
    # width without hardcoding it a second time in JS.
    grid_el.setAttribute("data-cols", str(GRID_COLS))
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
        tile.style.backgroundColor = plot_display_color(plot)
        tile.setAttribute("data-tooltip", _plot_tooltip_text(plot))
        tile.setAttribute("aria-label", _plot_tooltip_text(plot))
        # B17: a brief floating "+X" pop the tick this plot's standing
        # value actually rose, computed by tick() and consumed here once.
        pop_delta = _pending_value_pops.pop(plot.index, None)
        if pop_delta is not None:
            pop = document.createElement("span")
            pop.className = "value-pop"
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

    if selected_index is None:
        panel_state_el.innerText = "No plot selected"
        clear_button.disabled = True
        replant_button.disabled = True
        return

    plot = plots[selected_index]
    detail = f"value {plot.value:.1f}"
    if plot.state == REPLANTING:
        detail = f"recovering in {plot.replant_ticks_remaining} ticks"
    panel_state_el.innerText = (
        f"Plot {plot_coordinate_label(selected_index)}: {STATE_LABEL[plot.state]} ({detail})"
    )
    clear_button.disabled = "clear" not in VALID_ACTIONS[plot.state]
    replant_button.disabled = "replant" not in VALID_ACTIONS[plot.state]


# B14 (planning/TODO.md "Per-game: Canopy"): a per-browser "personal
# best" for both of the game's own two axes (standing value, harvested
# income), persisted via localStorage. Deliberately NOT part of
# get_state()/the save-code system -- this tracks the best this *browser*
# has ever seen across every session/save on this device, not one save's
# snapshot, the same distinction B14's other quartet-game equivalents
# (Tide's D13, Thaw's G19) draw.
PERSONAL_BEST_STORAGE_KEY = "canopy_personal_best_v1"


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


def _maybe_update_personal_best():
    """Called every render(); bumps + persists personal_best whenever the
    live session exceeds it on either axis. Two independent bests, not
    one combined score -- income vs. standing value is the game's own
    central two-axis comparison, and collapsing them into one number
    would lose exactly the distinction the rest of the game is built
    around."""
    global personal_best
    standing_value = standing_forest_value()
    changed = False
    if standing_value > personal_best["standing_value"]:
        personal_best["standing_value"] = standing_value
        changed = True
    if total_income > personal_best["income"]:
        personal_best["income"] = total_income
        changed = True
    if changed:
        _write_local_storage_item(PERSONAL_BEST_STORAGE_KEY, json.dumps(personal_best))


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
    clearing, so no soil degradation). Closed-form sum of an arithmetic
    sequence rather than a loop -- a long session can have thousands of
    ticks by the time a player opens this panel."""
    if n <= 0:
        return 0.0
    return BASE_ACCRUAL * (n + GROWTH_PER_TICK * n * (n + 1) / 2)


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
        f"about {ideal:.1f} by now — your actual standing value ({actual:.1f}) is {pct}% of that."
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
    document.getElementById("biodiversity-display").innerText = f"Biodiversity: {total_biodiversity():.1f}"
    document.getElementById("comparison-message").innerText = comparison_message(total_income, standing_value)
    document.getElementById("state-breakdown-display").innerText = state_breakdown_text()
    document.getElementById("community-relations-display").innerText = (
        f"Community relations: {community_relations}/100"
    )
    _maybe_update_personal_best()
    render_personal_best()


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
    grant_button.innerText = "Accept" if kind == STAKEHOLDER_KIND_INCENTIVE else "Grant"
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

ACHIEVEMENT_TOAST_DURATION_MS = 4000


def _earned_snapshot():
    return set(achievement_ids_earned())


def show_achievement_toast(message):
    global _toast_hide_proxy
    toast = document.getElementById("achievement-toast")
    if toast is None:
        return
    toast.innerText = message
    toast.hidden = False
    toast.classList.add("achievement-toast--visible")

    if _toast_hide_proxy is not None:
        _toast_hide_proxy.destroy()
        _toast_hide_proxy = None

    def _hide():
        global _toast_hide_proxy
        toast.classList.remove("achievement-toast--visible")
        toast.hidden = True
        if _toast_hide_proxy is not None:
            _toast_hide_proxy.destroy()
            _toast_hide_proxy = None

    _toast_hide_proxy = create_proxy(_hide)
    setTimeout(_toast_hide_proxy, ACHIEVEMENT_TOAST_DURATION_MS)


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
    hub_link.href = "../../index.html"
    hub_link.innerText = "View achievements across every game →"
    panel.appendChild(hub_link)


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


def render_grid_size_select():
    """Keeps the grid-size <select> showing whatever preset is actually
    live -- needed because reset_session() can change current_grid_size
    from code paths other than the dropdown itself (a loaded save, e.g.),
    which wouldn't otherwise be reflected back into the control."""
    select = document.getElementById("grid-size-select")
    if select is None:
        return
    select.value = current_grid_size


def render():
    render_info_page()
    render_grid()
    render_panel()
    render_stats()
    render_stakeholder_panel()
    render_grid_size_select()
    render_session_summary()
    update_achievements_display()
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
    render()


def on_replant(event=None):
    global total_replants
    if selected_index is None:
        return
    if plots[selected_index].replant():
        total_replants += 1
    render()


def tick(event=None):
    global pending_stakeholder_request, total_recoveries, _session_ticks
    _session_ticks += 1
    _pending_value_pops.clear()
    for plot in plots:
        delta = plot.accrue_tick()
        if delta >= VALUE_POP_MIN_DELTA:
            _pending_value_pops[plot.index] = delta
        if plot.advance_recovery():
            total_recoveries += 1
        if plot.has_wildlife():
            plots_with_wildlife_ever.add(plot.index)
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
    del _value_history[:-VALUE_HISTORY_MAX_POINTS]  # no-op once under the cap
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
def get_state():
    return {
        "plots": [
            {
                "index": plot.index,
                "state": plot.state,
                "value": plot.value,
                "ticks_intact": plot.ticks_intact,
                "clear_count": plot.clear_count,
                "replant_ticks_remaining": plot.replant_ticks_remaining,
                "just_recovered": plot.just_recovered,
                "biodiversity": plot.biodiversity,
            }
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
        # Write-only projection (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) — always
        # freshly recomputed here, never read back in load_state() below.
        "achievements_earned": achievement_ids_earned(),
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
    if saved_grid_size != current_grid_size or len(data.get("plots", [])) != len(plots):
        reset_session(grid_size=saved_grid_size, _render_after=False)

    for plot, plot_data in zip(plots, data.get("plots", [])):
        plot.index = plot_data.get("index", plot.index)
        plot.state = plot_data.get("state", plot.state)
        plot.value = plot_data.get("value", plot.value)
        plot.ticks_intact = plot_data.get("ticks_intact", plot.ticks_intact)
        plot.clear_count = plot_data.get("clear_count", plot.clear_count)
        plot.replant_ticks_remaining = plot_data.get(
            "replant_ticks_remaining", plot.replant_ticks_remaining
        )
        plot.just_recovered = plot_data.get("just_recovered", plot.just_recovered)
        plot.biodiversity = plot_data.get("biodiversity", plot.biodiversity)

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
    document.getElementById("reset-session-button").addEventListener(
        "click", create_proxy(on_reset_session)
    )
    document.getElementById("session-summary-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_session_summary)
    )
    document.getElementById("grid-size-select").addEventListener(
        "change", create_proxy(on_grid_size_change)
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
