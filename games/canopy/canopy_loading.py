"""load_state(): restores a save into the live game, then redraws."""

import canopy_runstate as runstate
from canopy_achievements import ACHIEVEMENTS, _earned_snapshot, _story_reach_all, achievement_ledger
from canopy_carbon import CARBON_CREDIT_CAP, CARBON_SLUMP_MAX_TICKS
from canopy_challenge import SCENARIO_SPECS
from canopy_contracts import _saved_challenge_id, _saved_pace
from canopy_gbstate import _load_gb_state
from canopy_ghost import _reset_ghost_session
from canopy_hazards import _reset_fire, _reset_rival, blight_pressure, fire_damp, fires
from canopy_helpers import _index_or_none, _number_or
from canopy_labui import set_lab_values
from canopy_layout import clean_layout_cells
from canopy_plot import Plot
from canopy_plotsheet import set_plot_note
from canopy_regions import wetland_wildlife_found
from canopy_renderer import render, reset_session
from canopy_rules import (
    DEGRADE_PER_CLEAR_BY_DIFFICULTY, DIFFICULTY_NORMAL, DIFFICULTY_RIVAL, GRID_SIZE_PRESETS, SCENARIO_NONE,
    SPECIES, SPECIES_STANDARD, carbon, species_planted,
)
from canopy_savestate import _apply_plot_dict, _clean_stakeholder_request
from canopy_stakeholders import FACES, FACE_TRUST_GAIN, FACE_TRUST_MAX, REQUEST_KIND_LABELS, stakeholder_faces
from canopy_worldvars import (
    FOREST_LOG_MAX_ENTRIES, REQUEST_HISTORY_MAX, RIVAL_CLAIM_TICKS, RIVAL_FIRST_BID_TICKS,
    RIVAL_NOTICE_TICKS, WETLAND_COLS, WETLAND_FLOOD_INTERVAL_TICKS, WETLAND_ROWS, plot_notes,
    request_history, rival_claims, rival_locked, rival_state,
)


def load_state(data):
    _reset_ghost_session()  # Z-3e: a loaded save starts a fresh session for the ghost, like the other histories

    # B13: a save written at a different grid size (or a save predating
    # B13 entirely, which simply lacks the key and so implies "normal", the
    # only size that existed before) needs `plots` rebuilt at the matching
    # size *before* the per-plot zip below, or a "large" (72-plot) save
    # loaded into a fresh "normal" (36-plot) module would silently drop the
    # other 36 plots' data instead of restoring them. reset_session()
    # already does exactly that rebuild; skip its own render() since the
    # real one happens at the end of this function once every field below
    # is actually restored.
    if not isinstance(data, dict):
        return False
    saved_grid_size = data.get("current_grid_size", "normal")
    if not isinstance(saved_grid_size, str) or saved_grid_size not in GRID_SIZE_PRESETS:
        saved_grid_size = "normal"
    saved_difficulty = data.get("current_difficulty", DIFFICULTY_NORMAL)
    if not isinstance(saved_difficulty, str) or saved_difficulty not in DEGRADE_PER_CLEAR_BY_DIFFICULTY:
        saved_difficulty = DIFFICULTY_NORMAL
    saved_plots = data.get("plots")
    saved_plots = saved_plots if isinstance(saved_plots, list) else []
    saved_challenge = _saved_challenge_id(data)
    saved_pace = _saved_pace(data)
    if (
        saved_grid_size != runstate.current_grid_size
        or saved_difficulty != runstate.current_difficulty
        or saved_challenge != runstate.current_challenge
        or saved_pace != runstate.current_pace
        or len(saved_plots) != len(runstate.plots)
    ):
        reset_session(
            grid_size=saved_grid_size, _render_after=False, difficulty=saved_difficulty,
            challenge=saved_challenge, pace=saved_pace,
        )

    for plot, plot_data in zip(runstate.plots, saved_plots):
        _apply_plot_dict(plot, plot_data)

    # Forest log / adoption (B3/B23/B27): an older save lacks all three, so
    # the (fresh or reset) live values stand.
    raw_log = data.get("forest_log", runstate.forest_log)
    raw_log = raw_log if isinstance(raw_log, list) else []
    runstate.forest_log = [
        {"tick": int(_number_or(e.get("tick"), 0, 0, 10 ** 9)), "kind": str(e.get("kind", "")),
         "plot": _index_or_none(e.get("plot"), len(runstate.plots)), "text": str(e.get("text", ""))}
        for e in raw_log
        if isinstance(e, dict)
    ][-FOREST_LOG_MAX_ENTRIES:]
    saved_layout = data.get("layout")
    runstate.current_layout = None
    for plot in runstate.plots:
        plot.blocked = False
    if isinstance(saved_layout, dict):
        cells = clean_layout_cells(saved_layout.get("cells"))
        if cells is not None:
            runstate.current_layout = {"name": str(saved_layout.get("name", ""))[:20], "cells": cells}
            for plot, ch in zip(runstate.plots, cells):
                plot.blocked = ch == "0"
    _reset_rival()
    saved_rival = data.get("rival")
    if isinstance(saved_rival, dict) and runstate.current_difficulty == DIFFICULTY_RIVAL:
        size = len(runstate.plots)
        for key, ticks in (saved_rival.get("claims") or {}).items() if isinstance(saved_rival.get("claims"), dict) else []:
            try:
                index = int(key)
            except (TypeError, ValueError):
                continue
            if 0 <= index < size and isinstance(ticks, int) and not isinstance(ticks, bool) and 0 < ticks <= RIVAL_CLAIM_TICKS:
                rival_claims[index] = ticks
        for index in saved_rival.get("locked") or [] if isinstance(saved_rival.get("locked"), list) else []:
            if isinstance(index, int) and not isinstance(index, bool) and 0 <= index < size:
                rival_locked.add(index)
        notice = saved_rival.get("notice")
        if isinstance(notice, dict) and isinstance(notice.get("plot"), int) and not isinstance(notice.get("plot"), bool) \
                and 0 <= notice["plot"] < size and isinstance(notice.get("ticks_left"), int) and 0 < notice["ticks_left"] <= RIVAL_NOTICE_TICKS:
            runstate.rival_notice = {"plot": notice["plot"], "ticks_left": notice["ticks_left"]}
        rival_state["next_bid"] = int(_number_or(saved_rival.get("next_bid"), RIVAL_FIRST_BID_TICKS, 0, 10**9))
        rival_state["bids"] = int(_number_or(saved_rival.get("bids"), 0, 0, 10**6))
    saved_carbon = data.get("carbon")  # GB-29
    carbon.update({"credits": 0.0, "slump": 0, "sold": 0.0, "earned_from_sales": 0.0})
    if isinstance(saved_carbon, dict):
        carbon["credits"] = float(_number_or(saved_carbon.get("credits"), 0.0, 0.0, CARBON_CREDIT_CAP))
        carbon["slump"] = int(_number_or(saved_carbon.get("slump"), 0, 0, CARBON_SLUMP_MAX_TICKS))
        carbon["sold"] = float(_number_or(saved_carbon.get("sold"), 0.0, 0.0, 1e9))
        carbon["earned_from_sales"] = float(_number_or(saved_carbon.get("earned_from_sales"), 0.0, 0.0, 1e12))
    stakeholder_faces.clear()  # GB-25
    saved_faces = data.get("stakeholder_faces")
    if isinstance(saved_faces, dict):
        for face_id, raw in saved_faces.items():
            if face_id in FACES and isinstance(raw, dict):
                stakeholder_faces[face_id] = {
                    "trust": int(_number_or(raw.get("trust"), 0, 0, FACE_TRUST_MAX)),
                    "last": raw.get("last") if raw.get("last") in FACE_TRUST_GAIN else "",
                    "met": int(_number_or(raw.get("met"), 0, 0, 100000)),
                }
    species_planted.clear()  # GB-6
    blight_pressure.clear()  # GB-7
    _reset_fire()  # GB-1
    fires.clear()  # GB-1
    fire_damp.clear()
    saved_planted = data.get("species_planted")
    if isinstance(saved_planted, list):
        species_planted.update(x for x in saved_planted if x in SPECIES and x != SPECIES_STANDARD)
    set_lab_values(data.get("lab"))  # B-5: an older save has none, which means the normal game
    saved_scenario = data.get("scenario")
    runstate.current_scenario = saved_scenario if saved_scenario in SCENARIO_SPECS else SCENARIO_NONE
    plot_notes.clear()
    saved_notes = data.get("plot_notes")
    if isinstance(saved_notes, dict):
        for key, text in saved_notes.items():
            try:
                index = int(key)
            except (TypeError, ValueError):
                continue
            if 0 <= index < len(runstate.plots) and isinstance(text, str):
                set_plot_note(index, text)
    request_history.clear()
    for entry in data.get("request_history") or []:
        try:
            if entry["kind"] in REQUEST_KIND_LABELS and entry["choice"] in ("granted", "declined", "countered"):
                request_history.append({
                    "tick": max(0, int(entry["tick"])), "plot": int(entry["plot"]), "kind": entry["kind"],
                    "choice": entry["choice"], "value_then": round(float(entry["value_then"]), 2),
                })
        except (KeyError, TypeError, ValueError):
            continue
    del request_history[:-REQUEST_HISTORY_MAX]
    # QA-1: the scalars below are checked one by one (a bad value keeps the live one), so a damaged save can no
    # longer put a string, None or an out-of-range index where the next tick does arithmetic or indexing.
    runstate.forest_tick = int(_number_or(data.get("forest_tick"), runstate.forest_tick, 0, 10 ** 9))
    runstate.adopted_plot_index = _index_or_none(data.get("adopted_plot_index", runstate.adopted_plot_index), len(runstate.plots))

    runstate.selected_index = _index_or_none(data.get("selected_index", runstate.selected_index), len(runstate.plots))
    runstate.total_income = _number_or(data.get("total_income"), runstate.total_income, 0.0, 1e15)
    runstate.community_relations = int(_number_or(data.get("community_relations"), runstate.community_relations, 0, 100))
    if "pending_stakeholder_request" in data:
        runstate.pending_stakeholder_request = _clean_stakeholder_request(data["pending_stakeholder_request"], len(runstate.plots))
    runstate._ticks_since_last_request = int(_number_or(data.get("_ticks_since_last_request"), runstate._ticks_since_last_request, 0, 10 ** 9))
    runstate._stakeholder_request_count = int(_number_or(data.get("_stakeholder_request_count"), runstate._stakeholder_request_count, 0, 10 ** 9))
    saved_open = data.get("info_page_open")
    runstate.info_page_open = saved_open if isinstance(saved_open, bool) else runstate.info_page_open

    # Achievements' new tracked state (see the module-level declarations
    # above) — a save predating this feature simply lacks these keys, so
    # each falls back to whatever's already live (the fresh-module
    # default) rather than crashing on a missing key.
    runstate.total_replants = int(_number_or(data.get("total_replants"), runstate.total_replants, 0, 10 ** 9))
    runstate.total_recoveries = int(_number_or(data.get("total_recoveries"), runstate.total_recoveries, 0, 10 ** 9))
    saved_wildlife = data.get("plots_with_wildlife_ever")
    if isinstance(saved_wildlife, list):
        runstate.plots_with_wildlife_ever = {i for i in saved_wildlife if _index_or_none(i, len(runstate.plots)) is not None}
    runstate.stakeholder_grants_count = int(_number_or(data.get("stakeholder_grants_count"), runstate.stakeholder_grants_count, 0, 10 ** 9))
    runstate.stakeholder_declines_count = int(_number_or(
        data.get("stakeholder_declines_count"), runstate.stakeholder_declines_count, 0, 10 ** 9))
    runstate.community_relations_min_ever = int(_number_or(
        data.get("community_relations_min_ever"), runstate.community_relations_min_ever, 0, 100))
    # Belt-and-suspenders backfill (same idea as SOL's visited_bodies): an
    # old save predating this field can't have recorded a low watermark,
    # but its restored community_relations value is itself a valid lower
    # bound on what the min-ever must have been.
    runstate.community_relations_min_ever = min(runstate.community_relations_min_ever, runstate.community_relations)

    # B3: Highland Grove's own fields. A save predating this feature
    # simply lacks all four keys -- reset_session() (called above if the
    # grid size differed) already left highland_plots at a fresh 12-plot
    # grid and highland_unlocked False, exactly the correct pre-B3 state,
    # so the .get() fallbacks below are true no-ops for such a save
    # rather than needing special-casing.
    saved_unlocked = data.get("highland_unlocked")
    runstate.highland_unlocked = saved_unlocked if isinstance(saved_unlocked, bool) else runstate.highland_unlocked
    runstate.highland_selected_index = _index_or_none(data.get("highland_selected_index", runstate.highland_selected_index), len(runstate.highland_plots))
    runstate.highland_income = _number_or(data.get("highland_income"), runstate.highland_income, 0.0, 1e15)
    saved_highland = data.get("highland_plots")
    for plot, plot_data in zip(runstate.highland_plots, saved_highland if isinstance(saved_highland, list) else []):
        _apply_plot_dict(plot, plot_data)

    # B1: Wetland Forest. Absent keys mean "never reached it" (reset_session
    # above already left a fresh locked region); everything present is
    # validated because a hand-edited or corrupt save must not break ticks.
    runstate.wetland_unlocked = data.get("wetland_unlocked") is True
    if not runstate.wetland_unlocked:
        # A save that never reached the wetland must not inherit the live
        # session's wetland: put it back to a fresh, locked region.
        runstate.wetland_plots[:] = [Plot(i, region="wetland") for i in range(WETLAND_ROWS * WETLAND_COLS)]
        runstate.wetland_selected_index = None
        runstate.wetland_income = 0.0
        runstate.wetland_flood_countdown = WETLAND_FLOOD_INTERVAL_TICKS
        runstate.wetland_floods_survived = 0
        runstate.wetland_flood_value_lost = 0.0
        wetland_wildlife_found.clear()  # GB-24
    else:
        wetland_wildlife_found.clear()
        wetland_wildlife_found.update(x for x in (data.get("wetland_wildlife") or []) if x in ("heron", "crab")) if isinstance(data.get("wetland_wildlife"), list) else None
        saved_selected = data.get("wetland_selected_index")
        runstate.wetland_selected_index = (
            saved_selected
            if isinstance(saved_selected, int) and not isinstance(saved_selected, bool)
            and 0 <= saved_selected < len(runstate.wetland_plots)
            else None
        )
        runstate.wetland_income = _number_or(data.get("wetland_income"), 0.0)
        runstate.wetland_flood_countdown = int(_number_or(
            data.get("wetland_flood_countdown"), WETLAND_FLOOD_INTERVAL_TICKS, 1, WETLAND_FLOOD_INTERVAL_TICKS
        ))
        runstate.wetland_floods_survived = int(_number_or(data.get("wetland_floods_survived"), 0))
        runstate.wetland_flood_value_lost = _number_or(data.get("wetland_flood_value_lost"), 0.0)
        saved_plots = data.get("wetland_plots")
        for plot, plot_data in zip(runstate.wetland_plots, saved_plots if isinstance(saved_plots, list) else []):
            if isinstance(plot_data, dict):
                _apply_plot_dict(plot, plot_data)

    # achievements_earned itself is never read back (write-only, §1) — but
    # the toast-diffing baseline must be reset here, before render() below
    # calls _sync_earned_and_toast(), so a loaded save's already-earned
    # achievements don't all fire toasts on load.
    _load_gb_state(data)  # GB batch 1: names, discoveries, tiers, tend, streak (validated)
    # GN-1: the saved list of earned ids seeds the ledger (known ids only), so earlier levels' achievements come back.
    saved_earned = data.get("achievements_earned")
    known_ids = {entry["id"] for entry in ACHIEVEMENTS}
    # QA-1: union, not replace. Achievements belong to the browser (the B-15 forest menu says so), so opening another
    # forest's save or a save from another device must not take back ones this browser already earned.
    if isinstance(saved_earned, list):
        achievement_ledger.update(item for item in saved_earned if isinstance(item, str) and item in known_ids)
    runstate._previously_earned_ids = _earned_snapshot()
    _story_reach_all(runstate._previously_earned_ids)  # W1: a loaded save's earned chapters come back too

    render()
    return True
