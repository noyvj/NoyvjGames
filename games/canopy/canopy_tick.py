"""tick(): one second of game time, and the tick loop starter."""

from js import setInterval
from pyodide.ffi import create_proxy

import canopy_runstate as runstate
from canopy_almanac import _register_chain_bloom
from canopy_carbon import _carbon_tick
from canopy_comfort import _note_tick_clock
from canopy_community import _community_tick
from canopy_forestlog import wildlife_species_for_plot
from canopy_gbstate import _gb_after_tick
from canopy_ghost import _record_ghost_tick
from canopy_hazards import _blight_tick, _fire_tick, _note_recovery, _rival_tick
from canopy_helpers import _announce, _log_event, _plot_ref
from canopy_regions import (
    _advance_wetland_tick, _maybe_unlock_highland, _maybe_unlock_wetland, note_wetland_wildlife,
)
from canopy_renderer import render
from canopy_rules import (
    ACCRUING_STATES, REPLANTING, SEASON_CYCLE_TICKS, TICK_INTERVAL_MS, mixed_forest_multiplier,
)
from canopy_stakeholders import (
    _stakeholder_target_is_still_standing, maybe_trigger_stakeholder_request, stakeholder_request_message,
)
from canopy_summary import _record_replay_frame
from canopy_tend import _heart_tree_aura
from canopy_valuation import standing_forest_value, total_biodiversity
from canopy_weather import _end_season
from canopy_worldvars import (
    HEART_TREE_AURA_BONUS, VALUE_HISTORY_MAX_POINTS, VALUE_POP_MIN_DELTA, _pending_mature_bursts,
    _pending_value_pops, _report_history, _value_history,
)


def tick(event=None):
    if runstate.survey_mode:  # B-13: time is frozen while the player plans
        return
    runstate._session_ticks += 1
    runstate.forest_tick += 1
    _note_tick_clock()  # B-30
    if runstate.forest_tick % SEASON_CYCLE_TICKS == 0:
        _end_season()  # GB-30: score the season that just ended
    _pending_value_pops.clear()
    _pending_mature_bursts.clear()
    runstate._mixed_bonus = mixed_forest_multiplier()  # GB-6
    _blight_tick()  # GB-7
    _fire_tick()  # GB-1
    _rival_tick()  # GB-12
    _carbon_tick()  # GB-29
    _community_tick()  # GB-19
    aura = _heart_tree_aura()  # GB-8
    newly_mature = []
    for plot in runstate.plots:
        delta = plot.accrue_tick()
        if delta > 0 and plot.index in aura:
            bonus = delta * HEART_TREE_AURA_BONUS
            plot.value += bonus
            delta += bonus
        if delta >= VALUE_POP_MIN_DELTA and not runstate.perf_mode:  # B-30: no pops while throttled
            _pending_value_pops[plot.index] = delta
        if plot.advance_recovery():
            _note_recovery(plot)
        elif plot.tend_ticks_left > 0 and plot.state == REPLANTING and plot.advance_recovery():
            _note_recovery(plot)  # GB-4: a tended replanting plot recovers an extra tick per tick
        if plot.has_wildlife() and plot.index not in runstate.plots_with_wildlife_ever:
            icon, name = wildlife_species_for_plot(plot.index)
            _log_event("wildlife", f"{icon} A {name} appeared at {_plot_ref(plot.index)}", plot.index)
        if plot.has_wildlife():
            runstate.plots_with_wildlife_ever.add(plot.index)
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
    if runstate.pending_stakeholder_request is not None and not _stakeholder_target_is_still_standing():
        # The requested plot was cleared/replanted directly (see the
        # grant/decline guard above) — drop the now-stale request so a new
        # one can still fire later, instead of maybe_trigger_stakeholder_
        # request() refusing to raise one forever because it sees a
        # (meaningless) request still pending.
        runstate.pending_stakeholder_request = None
    had_request = runstate.pending_stakeholder_request is not None
    maybe_trigger_stakeholder_request()
    if runstate.pending_stakeholder_request is not None and not had_request:
        _announce("New community request. " + stakeholder_request_message())  # B-7
    _gb_after_tick()  # GB-2/4/8/20/22/30: timers, discoveries and tiers
    # B6: sampled *after* this tick's accrual/payout effects above, so each
    # point reflects the state the player actually saw land this tick,
    # not the stale pre-tick value.
    _value_history.append((runstate.total_income, standing_forest_value()))
    _report_history.append((total_biodiversity(), standing_forest_value(), runstate.community_relations))
    del _report_history[:-VALUE_HISTORY_MAX_POINTS]
    _record_ghost_tick(standing_forest_value())  # Z-3e
    _record_replay_frame()  # B-3
    del _value_history[:-VALUE_HISTORY_MAX_POINTS]  # no-op once under the cap
    # B3: checked every tick regardless of whether it's already unlocked
    # (a no-op once True) -- accrual only starts once unlocked, so a
    # freshly-revealed Highland Grove begins at zero rather than having
    # secretly been growing, invisible, the whole session.
    _maybe_unlock_highland()
    if runstate.highland_unlocked:
        for plot in runstate.highland_plots:
            plot.accrue_tick()
            plot.advance_recovery()
    _maybe_unlock_wetland()
    if runstate.wetland_unlocked:
        _advance_wetland_tick()
    note_wetland_wildlife()  # GB-24
    render()


def _start_tick_loop():
    """W-2: hands `tick` to shared/time-controls.js (pause and 1x/2x/4x) when the
    page has it, otherwise falls back to the plain setInterval this game always
    used (fake-js test environments and any page without the shared script).
    Either way the tick itself is untouched: the controller only changes how
    often it is called, and not at all while paused or while the tab is hidden
    (shared/pause-hidden.js). Returns "shared" or "interval"."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        controls = getattr(window, "NoyvjTime", None)
    except ImportError:
        controls = None
    if controls is not None and getattr(controls, "start", None) is not None:
        controls.start("canopy", create_proxy(tick), TICK_INTERVAL_MS)
        return "shared"
    setInterval(create_proxy(tick), TICK_INTERVAL_MS)
    return "interval"
