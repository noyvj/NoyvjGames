"""tick(), _full_render(), and the per-tick achievement/story hooks."""

from js import document

import sol_runstate as runstate
from sol_achievements import (
    TROPHY_HISTORY_MAX, achievement_ids_earned, recent_trophies, render_trophy_shelf,
    update_achievements_display,
)
from sol_capsules import update_capsules_display
from sol_charter import _check_missions, _refill_mission_slots
from sol_charter_panel import update_charter_display
from sol_codex import _check_codex, _refresh_goals_panel
from sol_econ import (
    _track_close_calls, update_ecology_display, update_generator_display, update_governor_display,
    update_research_display, update_research_node_flags, update_research_tree_display,
    update_resource_display, update_sky_city_display, update_terraform_display, update_trade_display,
    update_travel_display,
)
from sol_ghost import _ghost_run_finished, _ghost_tick, update_splits_display
from sol_headless import update_doctrine_display
from sol_observatory import _note_world_rumors, _update_comet, update_comet_strip, update_observatory_display
from sol_overview import update_overview_display
from sol_panels import update_changelog_display, update_governor_report_display
from sol_planner import (
    _refresh_all_cost_displays, update_build_plan_display, update_epilogue_display,
    update_prestige_tree_display, update_win_display,
)
from sol_rhythm import (
    _decay_click_streak, _note_split, pb_splits, render_click_streak, run_splits, update_chains_display,
)
from sol_rules import GAS_GIANT_BODIES, PLANETS, TERRAFORM_MAX, TICK_INTERVAL_MS, planet_state
from sol_runmods import _update_anomaly, update_anomaly_strip
from sol_scarcity_panel import _scarcity_tick, update_scarcity_display
from sol_sim import _incoming_trade_restore, _simulate_planet, governor_step
from sol_statsview import update_all_cross_summaries, update_away_summary, update_stats_panel_display
from sol_story import ACHIEVEMENTS, render_story_log, story_note
from sol_util import _display_toast, _hide_all_views, _terraformed_planet_count


def _seed_achievement_toast_baseline():
    runstate._achievements_seen_ids = set(achievement_ids_earned())


def _report_full_completion():
    """A29: hands the completion time to the shared leaderboard widget, which
    only submits when this player has opted in and is signed in. Reported once
    per page load; the server keeps just the best score anyway."""
    if runstate.full_system_completed_tick is None or runstate._leaderboard_reported or runstate._scarcity is not None:
        return
    runstate._leaderboard_reported = True
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    board = getattr(window, "NoyvjLeaderboard", None)
    if board is None:
        return
    seconds = runstate.full_system_completed_tick * (TICK_INTERVAL_MS / 1000)
    board.report("sol", "fastest_completion", seconds, f"prestige {runstate.prestige_level}")


def _note_full_completion():
    finished = _terraformed_planet_count() >= len(PLANETS)
    if runstate.full_system_completed_tick is None and finished:
        runstate.full_system_completed_tick = runstate.total_ticks
    if finished and not runstate.run_completed:
        runstate.run_completed = True
        duration = max(0, runstate.total_ticks - runstate.run_start_tick)
        _note_split("full")
        is_best = runstate.best_run_ticks is None or duration < runstate.best_run_ticks
        if is_best:
            pb_splits.clear()
            pb_splits.update(run_splits)  # A-30: the new personal-best run's splits
        runstate.best_run_ticks = duration if runstate.best_run_ticks is None else min(runstate.best_run_ticks, duration)
        _ghost_run_finished(duration, is_best)  # A-29: the recording is kept only for a new best
    _report_full_completion()


def _note_trophies(new_ids):
    order = {entry["id"]: i for i, entry in enumerate(ACHIEVEMENTS)}
    for aid in sorted(new_ids, key=lambda a: order.get(a, 0)):
        if aid in recent_trophies:
            recent_trophies.remove(aid)
        recent_trophies.append(aid)
        runstate._trophy_fresh_id = aid
    del recent_trophies[:-TROPHY_HISTORY_MAX]
    render_trophy_shelf()


def _check_new_achievements_for_toast():
    """Called every tick(): compares the live earned set against the last
    snapshot, and pops a toast for anything newly earned since then. Never
    called from _full_render() itself -- see _seed_achievement_toast_baseline
    above for why a load must never diff against a stale/empty baseline."""
    if runstate._scarcity is not None:
        return  # a Scarcity Run never counts for achievements, the story log or the board
    _note_full_completion()
    if _note_story_beats():
        render_story_log()
    earned_now = set(achievement_ids_earned())
    newly = earned_now - runstate._achievements_seen_ids
    if newly:
        for aid in sorted(newly):
            story_note(f"ach:{aid}")
        render_story_log()
        _note_trophies(newly)
        by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
        labels = [by_id[aid]["label"] for aid in newly if aid in by_id]
        if labels:
            if len(labels) == 1:
                _display_toast(f"🏆 Achievement unlocked: {labels[0]}")
            else:
                _display_toast(f"🏆 {len(labels)} achievements unlocked: " + ", ".join(labels))
    runstate._achievements_seen_ids = earned_now


def _note_story_beats():
    """Notes the longer beats (idempotent): a finished world, the first trade
    route, the first prestige."""
    changed = False
    for planet, planet_data in planet_state.items():
        if planet_data["terraform_progress"] >= TERRAFORM_MAX:
            changed = story_note(f"terraform:{planet}") or changed
    if _total_trade_routes_built_now():
        changed = story_note("route:first") or changed
    if runstate.prestige_level >= 1:
        changed = story_note("prestige:1") or changed
    return _note_world_rumors() or changed


def _total_trade_routes_built_now():
    return sum(sum(data["trade_routes"].values()) for data in planet_state.values()) > 0


def tick(*args):
    runstate.total_ticks += 1
    _update_anomaly()

    # Trade contributions are computed from pre-tick trade_routes before
    # anything mutates this tick, so every planet's routes are based on
    # pre-tick counts rather than an order-dependent mix.
    incoming_trade_restore = {planet: _incoming_trade_restore(planet) for planet in PLANETS}

    for planet in PLANETS:
        _simulate_planet(planet, incoming_trade_restore[planet])

    governor_step()
    _track_close_calls()
    _scarcity_tick()
    _ghost_tick()

    for planet in PLANETS:
        update_resource_display(planet)
        update_generator_display(planet)
        update_ecology_display(planet)
        update_trade_display(planet)
        if planet in GAS_GIANT_BODIES:
            update_sky_city_display(planet)
        update_terraform_display(planet)

    update_research_node_flags()
    _decay_click_streak()
    update_all_cross_summaries()
    update_away_summary()
    update_win_display()
    update_achievements_display()
    update_stats_panel_display()
    update_governor_report_display()
    update_changelog_display()
    update_overview_display()
    update_epilogue_display()
    update_splits_display()
    update_chains_display()
    update_anomaly_strip()
    _check_missions()
    _check_codex()
    _update_comet()
    update_comet_strip()
    update_charter_display()
    update_doctrine_display()
    update_observatory_display()
    update_capsules_display()
    update_scarcity_display()
    _check_new_achievements_for_toast()
    if runstate.total_ticks % 10 == 0:
        _refresh_goals_panel()  # FY-53: once a second is plenty for a progress bar


def _full_render():
    """Switches the visible view to match `current_planet` and refreshes
    every display once. Used both by setup() on first load and by
    load_save_state() after restoring a save — tick() (already running
    on its own interval by the time a save loads mid-session) handles
    ongoing per-planet numeric updates from here on, but the one-off
    view-switch and the displays tick() doesn't touch (research,
    governor, travel-button unlock gating) need an explicit pass."""
    _hide_all_views()
    view_id = "away-view" if runstate.current_planet not in PLANETS else f"{runstate.current_planet.lower()}-view"
    document.getElementById(view_id).hidden = False

    for planet in PLANETS:
        update_resource_display(planet)
        update_generator_display(planet)
        update_ecology_display(planet)
        update_trade_display(planet)
        if planet in GAS_GIANT_BODIES:
            update_sky_city_display(planet)
        update_terraform_display(planet)
    update_research_display()
    update_research_tree_display()
    update_governor_display()
    update_travel_display()
    update_all_cross_summaries()
    update_win_display()
    update_achievements_display()
    update_stats_panel_display()
    update_governor_report_display()
    update_changelog_display()
    update_overview_display()
    render_story_log()
    update_build_plan_display()
    update_prestige_tree_display()
    update_epilogue_display()
    update_splits_display()
    update_chains_display()
    _update_anomaly()
    update_anomaly_strip()
    runstate._terraform_done_seen.update(p for p in PLANETS if planet_state[p]["terraform_progress"] >= TERRAFORM_MAX)
    _refill_mission_slots()
    update_charter_display()
    update_doctrine_display()
    _update_comet()
    update_comet_strip()
    update_observatory_display()
    update_capsules_display()
    update_scarcity_display(force=True)
    render_trophy_shelf()
    render_click_streak()
    _refresh_all_cost_displays()
    _refresh_goals_panel()
    document.getElementById("away-report").hidden = True
    # A full render (fresh setup, or a save/load round-trip) always starts
    # with no toast showing and re-seeds the "already earned" baseline to
    # whatever's true right now -- see _seed_achievement_toast_baseline's
    # own docstring for why loading a save must never replay its whole
    # earned history as a burst of toasts.
    document.getElementById("achievement-toast").hidden = True
    _seed_achievement_toast_baseline()
