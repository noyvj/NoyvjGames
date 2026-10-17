"""load_state(): putting a saved game back, then redrawing.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

import copy

import grid_runstate as runstate
from grid_rules import SCENARIOS
from grid_savegame import (
    _load_career, _load_regional_grid, _load_round3_fields, _load_round6_fields, _load_round_history_fields,
    _load_shadow, _merge_plant_dict, compute_load_report, load_report,
)
from grid_announce import _seed_achievement_toast_baseline
from grid_sandbox import _sandbox_notify_page, _sandbox_restore_real
from grid_realgrid import REAL_GRIDS
from grid_renderer import render


def load_state(data):
    if runstate.sandbox_active:  # Z-18: loading a save always lands in the real game
        _sandbox_restore_real()
    load_report["fields"] = compute_load_report(data) if isinstance(data, dict) else []
    load_report["loaded"] = True

    # Every field is pulled with .get(..., <current live value>) rather
    # than bare data["key"] indexing, so a save written before a later
    # milestone/pass added a field (global_reference_emissions and
    # global_reference_emissions_history, last_aging_event and plant_age
    # all landed in Pass 2, after Milestone 1/2 saves already existed)
    # can't crash load_state() with a KeyError -- a missing key just
    # leaves that field at whatever the live state already had, the same
    # "don't drop what the save doesn't know about" philosophy
    # _merge_plant_dict already applies one level deeper.
    runstate.state.round_number = data.get("round_number", runstate.state.round_number)
    runstate.state.demand = data.get("demand", runstate.state.demand)
    runstate.state.funds = data.get("funds", runstate.state.funds)
    _merge_plant_dict(runstate.state.plant_counts, data.get("plant_counts", {}))
    _merge_plant_dict(runstate.state.cumulative_built, data.get("cumulative_built", {}))
    runstate.state.emissions = data.get("emissions", runstate.state.emissions)
    runstate.state.event_log = copy.deepcopy(data.get("event_log", runstate.state.event_log))
    runstate.state.last_event = copy.deepcopy(data.get("last_event", runstate.state.last_event))
    runstate.state.clean_fraction_log = list(data.get("clean_fraction_log", runstate.state.clean_fraction_log))
    runstate.state.emissions_history = list(data.get("emissions_history", runstate.state.emissions_history))
    runstate.state.avg_renewable_cost_history = list(
        data.get("avg_renewable_cost_history", runstate.state.avg_renewable_cost_history)
    )
    runstate.state.renewable_unlocked = data.get("renewable_unlocked", runstate.state.renewable_unlocked)
    _merge_plant_dict(runstate.state.plant_age, data.get("plant_age", {}))
    runstate.state.global_reference_emissions = data.get(
        "global_reference_emissions", runstate.state.global_reference_emissions
    )
    runstate.state.global_reference_emissions_history = list(
        data.get("global_reference_emissions_history", runstate.state.global_reference_emissions_history)
    )
    runstate.state.bau_emissions = data.get("bau_emissions", runstate.state.bau_emissions)
    runstate.state.last_aging_event = copy.deepcopy(data.get("last_aging_event", runstate.state.last_aging_event))
    runstate.info_page_open = data.get("info_page_open", runstate.info_page_open)
    runstate.state.maintenance_actions_count = data.get("maintenance_actions_count", runstate.state.maintenance_actions_count)
    runstate.state.current_clean_streak = data.get("current_clean_streak", runstate.state.current_clean_streak)
    runstate.state.best_clean_streak = data.get("best_clean_streak", runstate.state.best_clean_streak)
    runstate.state.seen_retire_callout = data.get("seen_retire_callout", runstate.state.seen_retire_callout)
    runstate.state.seen_maintain_callout = data.get("seen_maintain_callout", runstate.state.seen_maintain_callout)
    runstate.state.renewable_50_reached = data.get("renewable_50_reached", runstate.state.renewable_50_reached)
    runstate.state.lifetime_revenue = data.get("lifetime_revenue", runstate.state.lifetime_revenue)
    runstate.state.lifetime_build_spend = data.get("lifetime_build_spend", runstate.state.lifetime_build_spend)
    runstate.state.lifetime_maintenance_spend = data.get("lifetime_maintenance_spend", runstate.state.lifetime_maintenance_spend)
    runstate.state.lifetime_disruption_spend = data.get("lifetime_disruption_spend", runstate.state.lifetime_disruption_spend)
    runstate.state.steeper_demand_growth_enabled = data.get(
        "steeper_demand_growth_enabled", runstate.state.steeper_demand_growth_enabled
    )
    runstate.state.weather_variability_enabled = data.get(
        "weather_variability_enabled", runstate.state.weather_variability_enabled
    )
    _load_regional_grid(data)
    saved_scenario = data.get("scenario", runstate.state.scenario)
    runstate.state.scenario = saved_scenario if saved_scenario in SCENARIOS else "standard"
    _load_shadow(data)
    saved_real = data.get("real_grid")
    runstate.real_grid_choice = saved_real if isinstance(saved_real, str) and saved_real in REAL_GRIDS else None
    _load_round3_fields(data)
    _load_round_history_fields(data)
    _load_career(data)
    _load_round6_fields(data)
    # "achievements_earned" is intentionally never read back here — see
    # get_state()'s comment and ACHIEVEMENTS-SYSTEM-DESIGN.md §1.

    render()
    _seed_achievement_toast_baseline()
    _sandbox_notify_page()
    return True
