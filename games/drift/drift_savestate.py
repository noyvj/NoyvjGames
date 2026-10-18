"""get_state(), steward_summary() and load_state(): the save format."""

import copy

from js import document

import drift_runstate as runstate
from drift_achievements import achievement_ids_earned, announce
from drift_assist import _assist_state_fields, _load_assist_state
from drift_calendar import _reset_civic_notes
from drift_collection import _seed_achievement_toast_baseline, merge_collection
from drift_loading import (
    _ledger_state_fields, _load_civic_state, _load_ledger, _load_neighbor, _load_roi_log, _load_spend_dict,
    _neighbor_state_fields, _set_load_note, load_report,
)
from drift_messages import CODA_LEGACY_CHOICES
from drift_model_region import region
from drift_plans import autopilot_log
from drift_renderer import render
from drift_report import _after_load_batch3
from drift_rules import (
    CAPACITY_TYPES, POLICIES, POLICY_MAX_LEVEL, REGION_NAME_MAX_LENGTH, SECOND_WAVE_ROUNDS,
    STRAIN_LEVEL_THRESHOLDS, _finite_number, _number_list, _small_int,
)
from drift_undo import _reset_undo_state


def get_state():
    return {
        "round_number": region.round_number,
        "funds": region.funds,
        "capacity": copy.deepcopy(region.capacity),
        "background_severity": region.background_severity,
        "total_arrivals": region.total_arrivals,
        "arrivals_log": copy.deepcopy(region.arrivals_log),
        "strain_log": copy.deepcopy(region.strain_log),
        # Z25: strain_log's decoupled running consumers -- see
        # RegionState.__init__'s comment and load_state()'s recompute
        # fallback for an old save that predates these three fields.
        "strain_sum": region._strain_sum,
        "strain_count": region._strain_count,
        "ever_critical_strain": region._ever_critical_strain,
        "wellbeing_log": copy.deepcopy(region.wellbeing_log),
        "integrated_population": region.integrated_population,
        "cumulative_services_investment": region.cumulative_services_investment,
        "cumulative_integration_contribution": region.cumulative_integration_contribution,
        "net_positive_round": region.net_positive_round,
        "current_stable_streak": region.current_stable_streak,
        "best_stable_streak": region.best_stable_streak,
        "thriving_round": region.thriving_round,
        "coda_ever_viewed": region.coda_ever_viewed,
        "last_milestone_round": region.last_milestone_round,
        "last_milestone_snapshot": copy.deepcopy(region.last_milestone_snapshot),
        "accelerated_severity_enabled": region.accelerated_severity_enabled,
        "severity_toggle_dot_baseline": region.severity_toggle_dot_baseline,
        "severity_density_callout_shown": region.severity_density_callout_shown,
        "subscore_log": copy.deepcopy(region.subscore_log),
        "region_name": region.region_name,
        "coda_legacy_choice": region.coda_legacy_choice,
        "crisis_start_enabled": region.crisis_start_enabled,
        **({"policy_level": dict(region.policy_level)} if any(region.policy_level.values()) else {}),
        **({"learning_active": True} if region.learning_active else {}),
        **(
            {"second_wave": {
                "status": region.second_wave_status, "rounds_left": region.second_wave_rounds_left,
                "peak_strain": region.second_wave_peak_strain, "result": region.second_wave_result,
                **({"start_round": region.second_wave_start_round} if region.second_wave_start_round is not None else {}),
            }}
            if region.second_wave_status is not None else {}
        ),
        **({"roi_log": list(region.roi_log)} if region.roi_log else {}),
        **_neighbor_state_fields(),
        **_ledger_state_fields(),
        **_assist_state_fields(),
        "coda_visible": runstate.coda_visible,
        "info_page_open": runstate.info_page_open,
        # I17: a write-only number for the community capacity index; never read back.
        "wellbeing_score": region.wellbeing_score(),
        # Write-only projection (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) — always
        # freshly recomputed, never read back in load_state() below.
        "summary": steward_summary(),  # B-23: write-only, never read back
        "achievements_earned": achievement_ids_earned(),
    }


# B-23: a few honest, already-computed numbers for the hub's Climate Steward page. Written into the save as a
# read-only `summary` list ({label, value, unit, note?}); never read back by load_state().
def steward_summary():
    return [
        {"label": "Newcomers integrated", "value": round(region.integration_fraction() * 100), "unit": "%"},
        {"label": "Wellbeing score", "value": round(region.wellbeing_score()), "unit": "of 100"},
        {"label": "Rounds played", "value": max(0, int(region.round_number) - 1), "unit": ""},
    ]


def load_state(data):

    if not isinstance(data, dict):
        return False

    report = load_report(data)
    region.round_number = int(_finite_number(data.get("round_number"), region.round_number, 1))
    region.funds = _finite_number(data.get("funds"), region.funds)
    saved_capacity = data.get("capacity")
    if isinstance(saved_capacity, dict):
        for capacity_type in CAPACITY_TYPES:
            if capacity_type in saved_capacity:
                region.capacity[capacity_type] = _finite_number(saved_capacity[capacity_type], region.capacity[capacity_type])
    region.background_severity = _finite_number(data.get("background_severity"), region.background_severity)
    region.total_arrivals = _finite_number(data.get("total_arrivals"), region.total_arrivals)
    saved_arrivals_log = data.get("arrivals_log")
    if _number_list(saved_arrivals_log):
        region.arrivals_log = copy.deepcopy(saved_arrivals_log)
    saved_strain_log = data.get("strain_log")
    if _number_list(saved_strain_log):
        region.strain_log = copy.deepcopy(saved_strain_log)
    # Z25: _strain_sum/_strain_count/_ever_critical_strain ride the save
    # from here on; an old save from before this refactor won't have
    # them, so recompute all three from whatever strain_log that old
    # save still has (its full, not-yet-capped history) rather than
    # defaulting to 0/False and silently losing the correct lifetime
    # average / achievement-earned state.
    if "strain_sum" in data and "strain_count" in data:
        region._strain_sum = _finite_number(data.get("strain_sum"), region._strain_sum)
        region._strain_count = int(_finite_number(data.get("strain_count"), region._strain_count))
    else:
        region._strain_sum = sum(region.strain_log)
        region._strain_count = len(region.strain_log)
    if "ever_critical_strain" in data:
        region._ever_critical_strain = bool(
            data.get("ever_critical_strain", region._ever_critical_strain)
        )
    else:
        region._ever_critical_strain = any(
            s >= STRAIN_LEVEL_THRESHOLDS[2][0] for s in region.strain_log
        )
    saved_wellbeing_log = data.get("wellbeing_log")
    if _number_list(saved_wellbeing_log):
        region.wellbeing_log = copy.deepcopy(saved_wellbeing_log)
    region.integrated_population = _finite_number(data.get("integrated_population"), region.integrated_population)
    region.cumulative_services_investment = _finite_number(
        data.get("cumulative_services_investment"), region.cumulative_services_investment
    )
    region.cumulative_integration_contribution = _finite_number(
        data.get("cumulative_integration_contribution"), region.cumulative_integration_contribution
    )
    region.net_positive_round = data.get("net_positive_round", region.net_positive_round)
    region.current_stable_streak = data.get("current_stable_streak", region.current_stable_streak)
    region.best_stable_streak = data.get("best_stable_streak", region.best_stable_streak)
    region.thriving_round = data.get("thriving_round", region.thriving_round)
    region.coda_ever_viewed = data.get("coda_ever_viewed", region.coda_ever_viewed)
    region.last_milestone_round = data.get("last_milestone_round", region.last_milestone_round)
    saved_milestone_snapshot = data.get("last_milestone_snapshot")
    if isinstance(saved_milestone_snapshot, dict):
        region.last_milestone_snapshot = copy.deepcopy(saved_milestone_snapshot)
    region.accelerated_severity_enabled = data.get(
        "accelerated_severity_enabled", region.accelerated_severity_enabled
    )
    saved_dot_baseline = data.get("severity_toggle_dot_baseline")
    if isinstance(saved_dot_baseline, int) and not isinstance(saved_dot_baseline, bool):
        region.severity_toggle_dot_baseline = saved_dot_baseline
    region.severity_density_callout_shown = bool(
        data.get("severity_density_callout_shown", region.severity_density_callout_shown)
    )
    saved_subscores = data.get("subscore_log")
    if isinstance(saved_subscores, list):
        region.subscore_log = [e for e in copy.deepcopy(saved_subscores) if isinstance(e, dict)]
    saved_name = data.get("region_name")
    if isinstance(saved_name, str):
        region.region_name = saved_name.strip()[:REGION_NAME_MAX_LENGTH]
    saved_choice = data.get("coda_legacy_choice")
    if saved_choice in CODA_LEGACY_CHOICES or saved_choice is None:
        region.coda_legacy_choice = saved_choice
    region.crisis_start_enabled = bool(data.get("crisis_start_enabled", region.crisis_start_enabled))
    # I29: a loaded region keeps whatever it began with; a save without the key began without it.
    region.learning_active = data.get("learning_active") is True
    region.second_wave_status = None
    region.second_wave_rounds_left = 0
    region.second_wave_peak_strain = 0.0
    region.second_wave_result = None
    region.second_wave_start_round = None
    saved_wave = data.get("second_wave")
    if isinstance(saved_wave, dict):
        status = saved_wave.get("status")
        left = saved_wave.get("rounds_left")
        peak = saved_wave.get("peak_strain")
        result = saved_wave.get("result")
        if status in ("warned", "active", "done"):
            region.second_wave_status = status
            if isinstance(left, int) and not isinstance(left, bool) and 0 <= left <= SECOND_WAVE_ROUNDS:
                region.second_wave_rounds_left = left
            elif status == "active":
                region.second_wave_rounds_left = SECOND_WAVE_ROUNDS
            if isinstance(peak, (int, float)) and not isinstance(peak, bool) and peak == peak and 0.0 <= peak <= 1.0:
                region.second_wave_peak_strain = float(peak)
            if status == "done":
                region.second_wave_result = result if result in ("held", "strained") else "strained"
            start_round = saved_wave.get("start_round")
            if _small_int(start_round, 1):
                region.second_wave_start_round = start_round
    region.roi_log = _load_roi_log(data.get("roi_log"))
    region.policy_level = {p: 0 for p in POLICIES}
    saved_policies = data.get("policy_level")
    if isinstance(saved_policies, dict):
        for p in POLICIES:
            level = saved_policies.get(p)
            if isinstance(level, int) and not isinstance(level, bool) and 0 <= level <= POLICY_MAX_LEVEL:
                region.policy_level[p] = level
    _load_neighbor(data.get("neighbor"))
    region.spend_by_type = _load_spend_dict(data.get("spend_by_type"))
    region.round_spend = _load_spend_dict(data.get("round_spend"))
    region.ledger = _load_ledger(data.get("ledger"))
    used_round = data.get("rewind_used_round")
    region.rewind_used_round = (
        used_round if isinstance(used_round, int) and not isinstance(used_round, bool) and used_round >= 1 else None
    )
    merge_collection(data.get("collection"))
    _load_civic_state(data)
    _load_assist_state(data)
    _after_load_batch3()
    autopilot_log.clear()
    _reset_civic_notes()
    _reset_undo_state()
    name_input = document.getElementById("region-name-input")
    name_input.value = region.region_name
    runstate.coda_visible = data.get("coda_visible", runstate.coda_visible)
    runstate.info_page_open = data.get("info_page_open", runstate.info_page_open)
    # "achievements_earned" is intentionally never read back here — see
    # get_state()'s comment and ACHIEVEMENTS-SYSTEM-DESIGN.md §1.

    _set_load_note(report)
    render()
    _seed_achievement_toast_baseline()
    if runstate.load_note_text:
        announce(runstate.load_note_text)
    return True
