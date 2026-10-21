"""Per-tick hooks for the GB features, the reset of their state and the loader for it."""

import canopy_runstate as runstate
from canopy_almanac import _check_milestones, _check_rare_wildlife, _tiers_reached_for
from canopy_challenge import _check_challenge
from canopy_clearcut import _advance_soil_dips
from canopy_contracts import _advance_contracts, _load_gb2_state, _reset_gb2_state
from canopy_expedition import _advance_expedition, _load_expedition
from canopy_helpers import _neighbour_indices, _number_or
from canopy_levels import _advance_level, _note_vault_progress, _reset_level_run
from canopy_tend import (
    _advance_golden_seedling, _advance_tend, _advance_undo, _check_heart_tree, _clean_name,
    _schedule_golden_seedling, _sync_name_inputs, _tendable,
)
from canopy_valuation import standing_forest_value
from canopy_vault import _advance_crews, _load_levels
from canopy_weather import _note_season_relations
from canopy_worldvars import (
    FOREST_NAME_MAX, GOLDEN_SEEDLING_MIN_GAP, NICKNAME_MAX, RARE_WILDLIFE, SEASON_FRAMES_MAX, STANDING_TIERS,
    TEND_COOLDOWN_TICKS, TEND_DURATION_TICKS, _gb_toast_queue, _pending_bloom, _pending_golden_bursts,
    season_frames,
)


# --- per-tick hook and state -------------------------------------------------------------------------------------------

def _gb_after_tick():
    """Everything GB does at the end of a tick (after accrual and requests)."""
    _advance_tend()
    _advance_golden_seedling()
    _advance_crews()  # GB-26: idle ranger crews (Seed Vault perks)
    _advance_undo()
    _advance_soil_dips()  # GB-21
    _advance_expedition()  # GB-3
    _note_season_relations()
    _check_rare_wildlife()
    _check_heart_tree()
    _check_milestones()
    _check_challenge()  # GB-17
    _advance_contracts()  # GB-9
    _advance_level()  # W-1: the running level's clock, mode and goal
    _note_vault_progress()  # GB-10: best tier and achievement counts feed the Seed Vault


def _reset_gb_state():
    del _gb_toast_queue[:]
    del season_frames[:]
    runstate.forest_name = ""
    runstate.adopted_plot_nickname = ""
    runstate.heart_tree_index = None
    runstate.rare_wildlife_found = []
    runstate.peak_standing_value = 0.0
    runstate.milestone_tier = 0
    runstate.tend_cooldown_ticks = 0
    runstate.perfect_streak = 0
    runstate.season_cleared = False
    runstate.season_min_relations = None
    runstate.golden_seedling = None
    runstate._golden_next_tick = GOLDEN_SEEDLING_MIN_GAP
    runstate._tend_message = ""
    runstate._undo_snapshot = None
    runstate.clear_cuts_total = 0
    runstate._harvester_badge_announced = False
    runstate._recent_matures = []
    _pending_bloom.clear()
    _pending_golden_bursts.clear()
    _reset_gb2_state()  # GB batch 2: challenge result, contract board
    _reset_level_run()  # GB batch 3: the running level's own state and the crew counters
    _sync_name_inputs()


def _load_season_frames(data):
    del season_frames[:]
    saved = data.get("season_frames")
    if not isinstance(saved, list):
        return
    for item in saved:
        if not isinstance(item, dict):
            continue
        n = int(_number_or(item.get("n"), 0, 0, 10 ** 6))
        cells = item.get("cells")
        cols = item.get("cols")
        label = item.get("label", "")
        if n < 1:
            continue
        if not isinstance(cols, int) or isinstance(cols, bool) or cols < 1 or cols > 40:
            continue
        if not isinstance(cells, str) or len(cells) == 0 or len(cells) > 1600:
            continue
        if not all(c in "PBR CX" for c in cells):
            continue
        if len(cells) % cols != 0:
            continue
        season_frames.append({
            "n": n,
            "label": str(label)[:20] if isinstance(label, str) else "",
            "cols": cols,
            "cells": cells,
        })
    del season_frames[:-SEASON_FRAMES_MAX]


def _load_gb_state(data):
    """Validates and applies the GB save keys; anything missing or malformed
    falls back to the fresh-game value (a save is authoritative, so a live
    session's names/discoveries must not leak into a save that lacks them)."""

    _reset_gb_state()
    for plot in runstate.plots:
        plot.tend_ticks_left = 0
    runstate.clear_cuts_total = int(_number_or(data.get("clear_cuts_total"), 0, 0, 10 ** 6))  # GB-21
    _schedule_golden_seedling()

    runstate.forest_name = _clean_name(data.get("forest_name"), FOREST_NAME_MAX)
    if runstate.adopted_plot_index is not None:
        runstate.adopted_plot_nickname = _clean_name(data.get("adopted_plot_nickname"), NICKNAME_MAX)

    saved_heart = data.get("heart_tree_index")
    if (
        isinstance(saved_heart, int) and not isinstance(saved_heart, bool)
        and 0 <= saved_heart < len(runstate.plots) and len(_neighbour_indices(saved_heart)) == 8
    ):
        runstate.heart_tree_index = saved_heart

    saved_rare = data.get("rare_wildlife_found")
    if isinstance(saved_rare, list):
        valid_ids = [entry[0] for entry in RARE_WILDLIFE]
        for rare_id in saved_rare:
            if isinstance(rare_id, str) and rare_id in valid_ids and rare_id not in runstate.rare_wildlife_found:
                runstate.rare_wildlife_found.append(rare_id)

    runstate.peak_standing_value = _number_or(data.get("peak_standing_value"), 0.0)
    runstate.peak_standing_value = max(runstate.peak_standing_value, standing_forest_value())
    tiers_now = _tiers_reached_for(runstate.peak_standing_value)
    if "milestone_tier" in data:
        runstate.milestone_tier = int(_number_or(data.get("milestone_tier"), 0, 0, len(STANDING_TIERS)))
        runstate.milestone_tier = min(runstate.milestone_tier, tiers_now)
    else:
        runstate.milestone_tier = tiers_now  # an older save: no celebration for what it already had

    saved_tend = data.get("tend")
    if isinstance(saved_tend, dict):
        tend_index = saved_tend.get("plot")
        if isinstance(tend_index, int) and not isinstance(tend_index, bool) and 0 <= tend_index < len(runstate.plots):
            left = int(_number_or(saved_tend.get("ticks_left"), 0, 0, TEND_DURATION_TICKS))
            if left > 0 and _tendable(runstate.plots[tend_index]):
                runstate.plots[tend_index].tend_ticks_left = left
    runstate.tend_cooldown_ticks = int(_number_or(data.get("tend_cooldown_ticks"), 0, 0, TEND_COOLDOWN_TICKS))

    saved_perfect = data.get("perfect_season")
    if isinstance(saved_perfect, dict):
        runstate.perfect_streak = int(_number_or(saved_perfect.get("streak"), 0, 0, 9999))
        runstate.season_cleared = saved_perfect.get("cleared") is True
        low = _number_or(saved_perfect.get("min_relations"), None, 0, 100)
        runstate.season_min_relations = int(low) if low is not None else None
    _load_season_frames(data)
    _load_gb2_state(data)
    _load_levels(data)  # GB batch 3
    _load_expedition(data)  # GB-3: after the grid, difficulty, pace, scenario, layout and level it depends on
    _sync_name_inputs()
