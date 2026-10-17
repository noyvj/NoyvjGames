"""get_state(): everything that goes into a save, and the plot and region dictionaries."""

import copy

import canopy_runstate as runstate
from canopy_achievements import achievement_ids_earned
from canopy_effects import vault_owned
from canopy_helpers import _index_or_none, _number_or
from canopy_levels import crew_stats, poacher_run, spirit_run, storm_run, vault_meta
from canopy_regions import wetland_wildlife_found
from canopy_rules import (
    BARE, CLEAR_CUT_HEAL_TICKS, PRESERVED, RECOVERED, RECOVERY_TICKS, REPLANTING, SCENARIO_NONE,
    SPECIALIZATION_LABEL, SPECIES, SPECIES_STANDARD, STAKEHOLDER_INCENTIVE_REASON_TEXT,
    STAKEHOLDER_KIND_CLEAR, STAKEHOLDER_KIND_INCENTIVE, STAKEHOLDER_KIND_REPLANT_GRANT,
    STAKEHOLDER_REASON_TEXT, carbon, lab, lab_active, species_planted,
)
from canopy_stakeholders import stakeholder_faces
from canopy_tend import _tended_plot
from canopy_valuation import standing_forest_value
from canopy_worldvars import (
    CHALLENGE_NONE, PACE_NORMAL, PERFECT_SEASON_MIN_RELATIONS, contract_board, contract_stamps, plot_notes,
    request_history, rival_claims, rival_enabled, rival_locked, rival_state,
)


def _contracts_state_fields():
    """Written only once the board has moved on from a fresh session's (the opening board is a pure
    function of an empty forest, so a save without the key rebuilds exactly it)."""
    if runstate.current_challenge != CHALLENGE_NONE:
        return {}
    fresh = not (
        runstate.contracts_completed or contract_stamps or runstate.contract_refill_ticks or runstate.contract_last_clear_tick
        or runstate.tends_done or runstate.seedlings_caught
    )
    if fresh:
        return {}
    return {
        "ranger_contracts": {
            "board": [dict(c) for c in contract_board],
            "stamps": list(contract_stamps),
            "completed": runstate.contracts_completed,
            "refill": runstate.contract_refill_ticks,
            "last_clear_tick": runstate.contract_last_clear_tick,
            "tends": runstate.tends_done,
            "seedlings": runstate.seedlings_caught,
        }
    }


def _gb2_state_fields():
    out = {}
    if runstate.current_challenge != CHALLENGE_NONE:
        out["challenge"] = {"id": runstate.current_challenge, "done_tick": runstate.challenge_complete_tick}
    if runstate.current_pace != PACE_NORMAL:
        out["request_pace"] = runstate.current_pace
    out.update(_contracts_state_fields())
    return out


def _levels_state_fields():
    out = {}
    if runstate.current_layout is not None:  # B-29
        out["layout"] = {"name": runstate.current_layout["name"], "cells": runstate.current_layout["cells"]}
    if carbon["credits"] > 0 or carbon["sold"] > 0:  # GB-29
        out["carbon"] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in carbon.items()}
    if stakeholder_faces:  # GB-25
        out["stakeholder_faces"] = copy.deepcopy(stakeholder_faces)
    if species_planted:  # GB-6
        out["species_planted"] = sorted(species_planted)
    if lab_active():  # B-5
        out["lab"] = dict(lab)
    if rival_enabled() and (rival_claims or rival_locked or runstate.rival_notice or rival_state["bids"]):  # GB-12
        out["rival"] = {"claims": {str(i): n for i, n in rival_claims.items()}, "locked": sorted(rival_locked),
                        "notice": dict(runstate.rival_notice) if runstate.rival_notice else None, "next_bid": rival_state["next_bid"], "bids": rival_state["bids"]}
    if runstate.current_scenario != SCENARIO_NONE:  # B-11
        out["scenario"] = runstate.current_scenario
    if plot_notes:  # B-24
        out["plot_notes"] = {str(i): n for i, n in plot_notes.items()}
    if request_history:  # B-14: only once a request has been answered
        out["request_history"] = copy.deepcopy(request_history)
    if runstate.levels_state["done"] or runstate.levels_state["best"]:
        out["levels"] = copy.deepcopy(runstate.levels_state)
    if vault_owned or vault_meta["best_tier"] or vault_meta["best_ach"] or any(crew_stats.values()):
        out["seed_vault"] = {
            "owned": list(vault_owned),
            "best_tier": vault_meta["best_tier"],
            "best_ach": vault_meta["best_ach"],
            "crews": dict(crew_stats),
        }
    out.update(_expedition_state_fields())  # GB-3
    if runstate.current_level is not None:
        run = {"id": runstate.current_level, "ticks": runstate.level_ticks, "done_tick": runstate.level_done_tick}
        if poacher_run:
            run["poacher"] = dict(poacher_run)
        if storm_run:
            run["storm"] = dict(storm_run)
        if spirit_run:
            run["spirit"] = dict(spirit_run)
        out["level_run"] = run
    return out


def _expedition_state_fields():
    if runstate.current_expedition is None:
        return {}
    return {"expedition": {
        "seed": runstate.current_expedition["seed"], "owned": list(runstate.current_expedition["owned"]),
        "done_tick": runstate.current_expedition["done_tick"], "score": runstate.current_expedition["score"],
    }}


def _gb_state_fields():
    """The GB save keys, each written only when it differs from a fresh game."""
    out = {}
    if runstate.forest_name:
        out["forest_name"] = runstate.forest_name
    if runstate.adopted_plot_nickname and runstate.adopted_plot_index is not None:
        out["adopted_plot_nickname"] = runstate.adopted_plot_nickname
    if runstate.heart_tree_index is not None:
        out["heart_tree_index"] = runstate.heart_tree_index
    if runstate.clear_cuts_total > 0:  # GB-21
        out["clear_cuts_total"] = runstate.clear_cuts_total
    if runstate.rare_wildlife_found:
        out["rare_wildlife_found"] = list(runstate.rare_wildlife_found)
    if runstate.peak_standing_value > 0:
        out["peak_standing_value"] = runstate.peak_standing_value
    if runstate.milestone_tier > 0:
        out["milestone_tier"] = runstate.milestone_tier
    tended = _tended_plot()
    if tended is not None:
        out["tend"] = {"plot": tended.index, "ticks_left": tended.tend_ticks_left}
    if runstate.tend_cooldown_ticks > 0:
        out["tend_cooldown_ticks"] = runstate.tend_cooldown_ticks
    low = runstate.season_min_relations
    if runstate.perfect_streak > 0 or runstate.season_cleared or (low is not None and low < PERFECT_SEASON_MIN_RELATIONS):
        out["perfect_season"] = {
            "streak": runstate.perfect_streak,
            "cleared": runstate.season_cleared,
            "min_relations": low if low is not None else runstate.community_relations,
        }
    out.update(_gb2_state_fields())
    out.update(_levels_state_fields())  # GB batch 3: levels, Seed Vault, running level
    return out


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
        **({"species": plot.species} if plot.species else {}),  # GB-6: only when a species was chosen
        **({"soil_dip_ticks": plot.soil_dip_ticks} if plot.soil_dip_ticks > 0 else {}),  # GB-21: only while healing
        **({"partner_share": plot.partner_share} if plot.partner_share else {}),  # B11: the partner's cut is permanent, so it must survive a save
    }


def _apply_plot_dict(plot, plot_data):
    """Safe-defaulting inverse of _plot_to_dict(): every key falls back to
    the plot's live value, so a save predating any field (mature_celebrated
    and requests_survived are newer than the rest) still loads."""
    # QA-1: every field is checked, so a hand-edited or damaged save keeps the plot's live value for a bad
    # field instead of storing a string or NaN that breaks the next tick.
    if not isinstance(plot_data, dict):
        return
    plot.index = int(_number_or(plot_data.get("index"), plot.index, 0, 10 ** 6))
    saved_state = plot_data.get("state")
    plot.state = saved_state if isinstance(saved_state, str) and saved_state in (PRESERVED, BARE, REPLANTING, RECOVERED) else plot.state
    plot.value = _number_or(plot_data.get("value"), plot.value, 0.0, 1e12)
    plot.ticks_intact = int(_number_or(plot_data.get("ticks_intact"), plot.ticks_intact, 0, 10 ** 9))
    plot.clear_count = int(_number_or(plot_data.get("clear_count"), plot.clear_count, 0, 10 ** 6))
    plot.replant_ticks_remaining = int(_number_or(
        plot_data.get("replant_ticks_remaining"), plot.replant_ticks_remaining, 0, 10 ** 6))
    saved_flag = plot_data.get("just_recovered")
    plot.just_recovered = saved_flag if isinstance(saved_flag, bool) else plot.just_recovered
    plot.biodiversity = _number_or(plot_data.get("biodiversity"), plot.biodiversity, 0.0, 1e9)
    saved_flag = plot_data.get("mature_celebrated")
    plot.mature_celebrated = saved_flag if isinstance(saved_flag, bool) else plot.mature_celebrated
    plot.requests_survived = int(_number_or(plot_data.get("requests_survived"), plot.requests_survived, 0, 10 ** 6))
    saved_spec = plot_data.get("specialization", plot.specialization)
    plot.specialization = saved_spec if isinstance(saved_spec, str) and saved_spec in SPECIALIZATION_LABEL else None
    saved_species = plot_data.get("species")  # GB-6
    plot.species = saved_species if isinstance(saved_species, str) and saved_species in SPECIES and saved_species != SPECIES_STANDARD else None
    plot.replant_ticks_total = max(RECOVERY_TICKS, plot.replant_ticks_remaining)
    # GB-21: a save is authoritative, so a missing or malformed key means no dip (a bool or NaN never counts).
    plot.soil_dip_ticks = int(_number_or(plot_data.get("soil_dip_ticks"), 0, 0, CLEAR_CUT_HEAL_TICKS))
    # QA-1: partner_share used to be missing from the save, so saving and loading quietly ended a reforestation
    # partnership (the plot kept the faster recovery and lost the permanent revenue share). Authoritative like
    # soil_dip_ticks: a save without it means no partner.
    plot.partner_share = float(_number_or(plot_data.get("partner_share"), 0.0, 0.0, 1.0))


def _wetland_state_fields():
    """B1: Wetland Forest's own state, written only once the region is open
    (a save that never reached it stays exactly as it was before B1)."""
    if not runstate.wetland_unlocked:
        return {}
    return {
        **({"wetland_wildlife": sorted(wetland_wildlife_found)} if wetland_wildlife_found else {}),  # GB-24
        "wetland_unlocked": True,
        "wetland_selected_index": runstate.wetland_selected_index,
        "wetland_income": runstate.wetland_income,
        "wetland_plots": [_plot_to_dict(plot) for plot in runstate.wetland_plots],
        "wetland_flood_countdown": runstate.wetland_flood_countdown,
        "wetland_floods_survived": runstate.wetland_floods_survived,
        "wetland_flood_value_lost": runstate.wetland_flood_value_lost,
    }


def _clean_stakeholder_request(raw, size):
    """A saved pending request, or None when it is not one the game could have made (it would otherwise be
    indexed as plots[raw["plot_index"]] when the player answers it)."""
    if not isinstance(raw, dict):
        return None
    index = _index_or_none(raw.get("plot_index"), size)
    reason, kind = raw.get("reason"), raw.get("kind", STAKEHOLDER_KIND_CLEAR)
    if index is None or not isinstance(reason, str) or not isinstance(kind, str):
        return None
    # The message and the answer handlers look the reason up by kind, so an unknown pair would raise later.
    if kind == STAKEHOLDER_KIND_CLEAR:
        known = reason in STAKEHOLDER_REASON_TEXT
    elif kind == STAKEHOLDER_KIND_INCENTIVE:
        known = reason in STAKEHOLDER_INCENTIVE_REASON_TEXT
    else:
        known = kind == STAKEHOLDER_KIND_REPLANT_GRANT
    if not known:
        return None
    clean = copy.deepcopy(raw)
    clean["plot_index"] = index
    return clean


def resume_note():
    """QI-58: one plain line for the hub's "Pick up where you stopped" strip (read by shared/last-played.js)."""
    return f"{len(runstate.plots)} plots, forest worth {round(standing_forest_value())}"


def get_state():
    return {
        "plots": [
            _plot_to_dict(plot)
            for plot in runstate.plots
        ],
        "selected_index": runstate.selected_index,
        "total_income": runstate.total_income,
        "standing_value": round(standing_forest_value(), 1),  # R-27: read-only summary for the community comparison; ignored on load
        "community_relations": runstate.community_relations,
        "pending_stakeholder_request": copy.deepcopy(runstate.pending_stakeholder_request),
        "_ticks_since_last_request": runstate._ticks_since_last_request,
        "_stakeholder_request_count": runstate._stakeholder_request_count,
        "info_page_open": runstate.info_page_open,
        "total_replants": runstate.total_replants,
        "total_recoveries": runstate.total_recoveries,
        "plots_with_wildlife_ever": sorted(runstate.plots_with_wildlife_ever),
        "stakeholder_grants_count": runstate.stakeholder_grants_count,
        "stakeholder_declines_count": runstate.stakeholder_declines_count,
        "community_relations_min_ever": runstate.community_relations_min_ever,
        # B13: which GRID_SIZE_PRESETS key produced the `plots` list above —
        # load_state() needs this *before* it can zip a saved `plots` list
        # onto the live one, since a "large" save loaded into a fresh
        # "normal"-sized module would otherwise silently truncate to 36.
        "current_grid_size": runstate.current_grid_size,
        "current_difficulty": runstate.current_difficulty,
        "forest_log": copy.deepcopy(runstate.forest_log),
        "forest_tick": runstate.forest_tick,
        "adopted_plot_index": runstate.adopted_plot_index,
        # B3: Highland Grove's own state -- a save predating this feature
        # simply lacks these keys and load_state() treats that as "not
        # unlocked yet, empty grove", the correct pre-B3 truth.
        "highland_unlocked": runstate.highland_unlocked,
        "highland_selected_index": runstate.highland_selected_index,
        "highland_income": runstate.highland_income,
        "highland_plots": [
            _plot_to_dict(plot)
            for plot in runstate.highland_plots
        ],
        # Write-only projection (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) — always
        # freshly recomputed here, never read back in load_state() below.
        "achievements_earned": achievement_ids_earned(),
        **_wetland_state_fields(),
        **_gb_state_fields(),
    }
