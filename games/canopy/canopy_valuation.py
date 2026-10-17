"""Standing forest value, biodiversity, active plot counts, clear counts and the playstyle badge: the numbers many panels read."""

import canopy_runstate as runstate
from canopy_rules import (
    ACCRUING_STATES, BARE, BIODIVERSITY_ACCRUAL_PER_TICK, PRESERVED, RECOVERED, REPLANTING,
    SEASON_CYCLE_TICKS,
)


def active_plot_count():
    return sum(1 for p in runstate.plots if not p.blocked)


def layout_active():
    return runstate.current_layout is not None


def standing_forest_value():
    """Live sum of standing value across every plot — only PRESERVED and
    RECOVERED plots hold nonzero value at any given moment."""
    return sum(plot.value for plot in runstate.plots)


# B10 (planning/TODO.md "Per-game: Canopy"): biodiversity was previously
# only legible indirectly (the wildlife icon threshold on individual
# tiles) — this surfaces it as one explicit number next to standing value,
# same "comparison, not just a meter" spirit as income vs. standing value.
def total_biodiversity():
    return sum(plot.biodiversity for plot in runstate.plots)


def biodiversity_rate_per_tick():
    """B10: how fast total biodiversity is rising right now -- every
    standing (PRESERVED/RECOVERED) plot adds the same flat
    BIODIVERSITY_ACCRUAL_PER_TICK, so the rate is just that times the
    standing-plot count. Zero when nothing is standing."""
    return sum(1 for plot in runstate.plots if plot.state in ACCRUING_STATES) * BIODIVERSITY_ACCRUAL_PER_TICK


def state_breakdown():
    """Count of plots in each state — the grid-level session summary."""
    counts = {PRESERVED: 0, BARE: 0, REPLANTING: 0, RECOVERED: 0}
    for plot in runstate.plots:
        if not plot.blocked:  # B-29: open ground in a custom layout is not a plot
            counts[plot.state] += 1
    return counts


def _total_clear_count():
    return sum(plot.clear_count for plot in runstate.plots)


def _max_clear_count():
    return max((plot.clear_count for plot in runstate.plots), default=0)


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
    if clears == 0 and runstate._session_ticks == 0 and runstate.forest_tick == 0:
        return BADGE_UNDECIDED
    ratio = clears / max(1, active_plot_count())
    if ratio < BADGE_PRESERVATIONIST_MAX_CLEAR_RATIO:
        return BADGE_PRESERVATIONIST
    if ratio < BADGE_BALANCED_MAX_CLEAR_RATIO:
        return BADGE_BALANCED
    return BADGE_HARVESTER


def badge_share_text():
    badge = playstyle_badge()
    cuts = f", {runstate.clear_cuts_total} of them clear-cuts" if runstate.clear_cuts_total else ""
    return f"{BADGE_ICON[badge]} Canopy playstyle badge: {badge} ({_total_clear_count()} clears{cuts} across {active_plot_count()} plots)"


def _peak_now():
    return max(runstate.peak_standing_value, standing_forest_value())


def seasons_survived():
    return runstate.forest_tick // SEASON_CYCLE_TICKS
