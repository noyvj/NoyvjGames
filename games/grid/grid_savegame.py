"""Saving: get_state(), the field-by-field loaders, the load report and steward_summary().
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

import copy

import seed as seed_lib

import grid_runstate as runstate
from grid_rules import (
    ARBITRAGE_MODES, EMERGENCY_HOLD_ROUNDS, EMERGENCY_ROUNDS, GRANTS, GRANT_CLEAN_ROUNDS,
    GRANT_CONTEST_ROUNDS, LOADOUT_NODES, MAINTENANCE_SCHEDULE_OPTIONS, NAME_MAX_LEN, PLANT_LABEL, PLANT_TYPES,
    POLICY_LEVER_DURATION, SCENARIOS, SEED_GAME, WEATHER_LOG_MAX_ENTRIES,
)
from grid_career_data import _sync_perks, save_career_to_storage, validate_career
from grid_achievements import ACHIEVEMENTS, achievement_ids_earned, renewable_capacity_share
from grid_shadow import SHADOW_MAX_ACTIONS


def _load_arbitrage_and_emergency(data):
    """Validated restore of C9/C27 fields (defaults if malformed)."""
    stored = data.get("stored_energy", runstate.state.stored_energy)
    ok = isinstance(stored, (int, float)) and not isinstance(stored, bool) and stored == stored
    runstate.state.stored_energy = max(0.0, min(float(stored), runstate.state.storage_cap())) if ok else 0.0
    mode = data.get("arbitrage_mode", runstate.state.arbitrage_mode)
    runstate.state.arbitrage_mode = mode if mode in ARBITRAGE_MODES else "idle"
    total = data.get("arbitrage_revenue_total", runstate.state.arbitrage_revenue_total)
    ok = isinstance(total, (int, float)) and not isinstance(total, bool) and total == total
    runstate.state.arbitrage_revenue_total = max(0.0, float(total)) if ok else 0.0
    runstate.state.last_arbitrage = None
    em = data.get("emergency", runstate.state.emergency)
    if (
        runstate.state.scenario == "emergency"
        and isinstance(em, dict)
        and em.get("status") in ("active", "stabilized", "missed")
    ):
        runstate.state.emergency = {
            "status": em["status"],
            "rounds_left": _as_int(em.get("rounds_left"), 0, 0, EMERGENCY_ROUNDS),
            "hold": _as_int(em.get("hold"), 0, 0, EMERGENCY_HOLD_ROUNDS),
        }
    else:
        runstate.state.emergency = None


# SAVE-BUTTON-INTEGRATION.md contract for the shared shared/save-widget.js:
# get_state() returns every module-level mutable global (the GridState
# instance's attributes, plus the info-page toggle) as one plain,
# JSON-safe dict. get_state() deep-copies every nested mutable container
# (plant_counts, cumulative_built, plant_age, event_log, last_event, the
# history lists, last_aging_event) on the way out, so a live reference is
# never shared between the saved snapshot and continued play — same
# reasoning as SOL's serialize_state() docstring. Grid has no non-JSON-
# native types (no sets) in its state, unlike SOL's unlocked_bodies.
# load_state() is its inverse, but not a blind mirror: plant_counts,
# cumulative_built and plant_age are merged into the live dicts key-by-key
# (_merge_plant_dict) rather than replacing them wholesale, so a save
# missing a plant-type key can't drop that key from live state entirely.
def get_state():
    if runstate.sandbox_active:  # Z-18: a save, an autosave or a leaderboard read while the sandbox is on is the REAL game
        return copy.deepcopy(runstate._sandbox_real["snapshot"])
    return {
        "round_number": runstate.state.round_number,
        "demand": runstate.state.demand,
        "funds": runstate.state.funds,
        "plant_counts": copy.deepcopy(runstate.state.plant_counts),
        "cumulative_built": copy.deepcopy(runstate.state.cumulative_built),
        "emissions": runstate.state.emissions,
        "event_log": copy.deepcopy(runstate.state.event_log),
        "last_event": copy.deepcopy(runstate.state.last_event),
        "clean_fraction_log": list(runstate.state.clean_fraction_log),
        "emissions_history": list(runstate.state.emissions_history),
        "avg_renewable_cost_history": list(runstate.state.avg_renewable_cost_history),
        "renewable_unlocked": runstate.state.renewable_unlocked,
        "plant_age": copy.deepcopy(runstate.state.plant_age),
        "global_reference_emissions": runstate.state.global_reference_emissions,
        "global_reference_emissions_history": list(runstate.state.global_reference_emissions_history),
        "bau_emissions": runstate.state.bau_emissions,
        "last_aging_event": copy.deepcopy(runstate.state.last_aging_event),
        "info_page_open": runstate.info_page_open,
        "maintenance_actions_count": runstate.state.maintenance_actions_count,
        "current_clean_streak": runstate.state.current_clean_streak,
        "best_clean_streak": runstate.state.best_clean_streak,
        "seen_retire_callout": runstate.state.seen_retire_callout,
        "seen_maintain_callout": runstate.state.seen_maintain_callout,
        "renewable_50_reached": runstate.state.renewable_50_reached,
        "lifetime_revenue": runstate.state.lifetime_revenue,
        "lifetime_build_spend": runstate.state.lifetime_build_spend,
        "lifetime_maintenance_spend": runstate.state.lifetime_maintenance_spend,
        "lifetime_disruption_spend": runstate.state.lifetime_disruption_spend,
        "steeper_demand_growth_enabled": runstate.state.steeper_demand_growth_enabled,
        "weather_variability_enabled": runstate.state.weather_variability_enabled,
        **(
            {
                "regional_grid": {
                    "total_shared": runstate.state.regional_grid_total_shared,
                    "total_shortfall_cost": runstate.state.regional_grid_total_shortfall_cost,
                    "total_revenue": runstate.state.regional_grid_total_revenue,
                }
            }
            if runstate.state.regional_grid_connected else {}
        ),
        "scenario": runstate.state.scenario,
        **(
            {"shadow": {"scenario": runstate.shadow_scenario, "actions": [dict(a) for a in runstate.shadow_actions]}}
            if runstate.shadow_scenario is not None else {}
        ),
        **({"real_grid": runstate.real_grid_choice} if runstate.real_grid_choice is not None else {}),
        "demand_response_level": runstate.state.demand_response_level,
        "weather_log": list(runstate.state.weather_log),
        "policy_lever_available": runstate.state.policy_lever_available,
        "active_policy": copy.deepcopy(runstate.state.active_policy),
        "last_policy_lever_round_offered": runstate.state.last_policy_lever_round_offered,
        "maintenance_schedule": dict(runstate.state.maintenance_schedule),
        "stored_energy": runstate.state.stored_energy,
        "arbitrage_mode": runstate.state.arbitrage_mode,
        "arbitrage_revenue_total": runstate.state.arbitrage_revenue_total,
        "emergency": copy.deepcopy(runstate.state.emergency),
        "career": copy.deepcopy(runstate.career),
        "funds_history": list(runstate.state.funds_history),
        "demand_history": list(runstate.state.demand_history),
        "aging_breakdown_count": runstate.state.aging_breakdown_count,
        "first_90_clean_round": runstate.state.first_90_clean_round,
        "last_round_recap": copy.deepcopy(runstate.state.last_round_recap),
        # 2026-10-08 batch: the seeded run, loadout, peek, Perfect Round streak, Ironman, nicknames, grants.
        "seed": runstate.state.seed,
        "start_option": runstate.state.start_option,
        "immunity_available": runstate.state.immunity_available,
        "immunity_used": runstate.state.immunity_used,
        "peeked_round": runstate.state.peeked_round,
        "perfect_streak": runstate.state.perfect_streak,
        "best_perfect_streak": runstate.state.best_perfect_streak,
        "ironman": runstate.state.ironman,
        "plant_names": {t: list(runstate.state.plant_name_list(t)) for t in PLANT_TYPES},
        "name_serial": dict(runstate.state.name_serial),
        "last_eulogy": copy.deepcopy(runstate.state.last_eulogy),
        "grant_offer": copy.deepcopy(runstate.state.grant_offer),
        "grant_effects": dict(runstate.state.grant_effects),
        "last_grant_message": runstate.state.last_grant_message,
        # Write-only projection (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) — always
        # freshly recomputed, never read back in load_state() below.
        "summary": steward_summary(),  # B-23: write-only, never read back
        "achievements_earned": achievement_ids_earned(),
    }


def _merge_plant_dict(live, saved):
    """Writes a saved per-plant-type dict into the live one key-by-key,
    rather than replacing it wholesale. The key set (PLANT_TYPES) belongs
    to game.py, not to the save: a save written before a plant type
    existed (or a hand-edited/truncated payload) can be missing one of
    those keys, and every consumer (render(), total_capacity(),
    plant_cost(), ...) does live[plant_type] unconditionally for every
    type in PLANT_TYPES — a wholesale replace would drop the missing key
    from the dict entirely and crash on the very next access, after the
    save widget already reported a successful load. Keys the save doesn't
    know about simply keep their current live value."""
    for plant_type in live:
        if plant_type in saved:
            live[plant_type] = saved[plant_type]


def _as_int(value, default, minimum=0, maximum=None):
    """Validation helper for hand-edited/corrupt saves: bool and non-numeric
    values fall back to the default, numbers are clamped into range."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return default
    value = int(value)
    if value < minimum:
        return minimum
    if maximum is not None and value > maximum:
        return maximum
    return value


def _as_finite_nonneg_float(value, default):
    """Same spirit as _as_int, for a plain non-negative float total (C3's
    regional-grid running totals): bool/non-numeric/NaN/inf all fall back
    to the default, and a negative value is floored at 0."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        return default
    return max(0.0, value)


def _load_shadow(data):
    """C21: the shadow grid's saved config; anything malformed loads as off."""
    runstate.shadow_actions.clear()
    runstate.shadow_scenario = None
    saved = data.get("shadow")
    if not isinstance(saved, dict):
        return
    scenario = saved.get("scenario")
    if not isinstance(scenario, str) or scenario not in SCENARIOS:
        return
    runstate.shadow_scenario = scenario
    actions = saved.get("actions")
    if isinstance(actions, list):
        for action in actions:
            if not isinstance(action, dict):
                continue
            rnd, kind, plant = action.get("round"), action.get("kind"), action.get("type")
            if (
                isinstance(rnd, int) and not isinstance(rnd, bool) and rnd >= 1
                and kind in ("build", "retire") and isinstance(plant, str) and plant in PLANT_TYPES
            ):
                runstate.shadow_actions.append({"round": rnd, "kind": kind, "type": plant})
        del runstate.shadow_actions[:-SHADOW_MAX_ACTIONS]


def _load_round3_fields(data):
    """Validated restore of the round-3 fields (C7/C17/C19/C23) that
    get_state() previously never saved, so they silently reset on every
    load. Anything malformed falls back to that field's default."""
    runstate.state.demand_response_level = _as_int(data.get("demand_response_level"), runstate.state.demand_response_level, 0, 200)
    log = data.get("weather_log", runstate.state.weather_log)
    if isinstance(log, list):
        runstate.state.weather_log = [str(x) for x in log if isinstance(x, str)][-WEATHER_LOG_MAX_ENTRIES:]
    available = data.get("policy_lever_available", runstate.state.policy_lever_available)
    runstate.state.policy_lever_available = available if isinstance(available, bool) else False
    policy = data.get("active_policy", runstate.state.active_policy)
    if (
        isinstance(policy, dict)
        and policy.get("type") in ("carbon_pricing", "renewable_subsidy")
        and _as_int(policy.get("rounds_remaining"), 0, 0, POLICY_LEVER_DURATION) > 0
    ):
        runstate.state.active_policy = {
            "type": policy["type"],
            "rounds_remaining": _as_int(policy["rounds_remaining"], 1, 1, POLICY_LEVER_DURATION),
        }
    else:
        runstate.state.active_policy = None
    runstate.state.last_policy_lever_round_offered = _as_int(
        data.get("last_policy_lever_round_offered"), runstate.state.last_policy_lever_round_offered, 0
    )
    schedule = data.get("maintenance_schedule")
    if isinstance(schedule, dict):
        for plant_type in PLANT_TYPES:
            interval = schedule.get(plant_type)
            if isinstance(interval, int) and not isinstance(interval, bool) and interval in MAINTENANCE_SCHEDULE_OPTIONS:
                runstate.state.maintenance_schedule[plant_type] = interval
    _load_arbitrage_and_emergency(data)


def _load_regional_grid(data):
    """C3: `regional_grid` is only ever present in a save when the switch
    was on (get_state()'s own convention, matching the C21 `shadow` field
    right above it) -- its absence means "never connected", not "reset to
    off", so a save from before this connected the grid stays connected."""
    payload = data.get("regional_grid")
    if not isinstance(payload, dict):
        return
    runstate.state.regional_grid_connected = True
    runstate.state.regional_grid_total_shared = _as_finite_nonneg_float(
        payload.get("total_shared"), runstate.state.regional_grid_total_shared
    )
    runstate.state.regional_grid_total_shortfall_cost = _as_finite_nonneg_float(
        payload.get("total_shortfall_cost"), runstate.state.regional_grid_total_shortfall_cost
    )
    runstate.state.regional_grid_total_revenue = _as_finite_nonneg_float(
        payload.get("total_revenue"), runstate.state.regional_grid_total_revenue
    )


def _finite_number(value, default=0.0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return default
    if value in (float("inf"), float("-inf")):
        return default
    return value


def _number_list(raw, fallback):
    if not isinstance(raw, list) or not all(
        not isinstance(v, bool) and isinstance(v, (int, float)) and v == v for v in raw
    ):
        return list(fallback)
    return list(raw)


def _load_round_recap(raw):
    """C-8: adopt a saved recap only as a fully validated dict; anything
    else (missing, wrong shape) leaves no recap rather than crashing render()."""
    if not isinstance(raw, dict):
        return None
    scheduled = []
    for entry in raw.get("scheduled") if isinstance(raw.get("scheduled"), list) else []:
        if isinstance(entry, dict) and entry.get("plant") in PLANT_LABEL:
            scheduled.append({"plant": entry["plant"], "cost": max(0.0, _finite_number(entry.get("cost")))})
    weather = raw.get("weather_pct")
    plant = raw.get("aging_plant")
    kind = raw.get("disruption_type")
    return {
        "round": _as_int(raw.get("round"), 1, 1),
        "net": _finite_number(raw.get("net")),
        "base_revenue": max(0.0, _finite_number(raw.get("base_revenue"))),
        "arbitrage": max(0.0, _finite_number(raw.get("arbitrage"))),
        "regional": max(0.0, _finite_number(raw.get("regional"))),
        "regional_shortfall": max(0.0, _finite_number(raw.get("regional_shortfall"))),
        "scheduled": scheduled,
        "weather_pct": None if weather is None else _finite_number(weather),
        "disruption_loss": max(0.0, _finite_number(raw.get("disruption_loss"))),
        "repair_cost": max(0.0, _finite_number(raw.get("repair_cost"))),
        "aging_plant": plant if plant in PLANT_LABEL else None,
        "disruption_type": kind if kind in ("brownout", "damage") else None,
        "demand_growth": max(0.0, _finite_number(raw.get("demand_growth"))),
        "perfect_bonus": max(0.0, _finite_number(raw.get("perfect_bonus"))),
        "perfect": bool(raw.get("perfect")),
        "immunity": bool(raw.get("immunity")),
    }


def _load_round_history_fields(data):
    """C-1/GC-26/C-8: the funds and demand series, aging count, first 90%-clean
    round and last-round recap -- each defaults safely for an older save."""
    runstate.state.funds_history = _number_list(data.get("funds_history"), [])
    runstate.state.demand_history = _number_list(data.get("demand_history"), [])
    runstate.state.aging_breakdown_count = _as_int(data.get("aging_breakdown_count"), 0, 0)
    first = data.get("first_90_clean_round")
    runstate.state.first_90_clean_round = _as_int(first, 1, 1) if first is not None and not isinstance(first, bool) else None
    runstate.state.last_round_recap = _load_round_recap(data.get("last_round_recap"))


def _load_round6_fields(data):
    """2026-10-08 batch: every field validated, each defaulting safely for an older save."""
    saved_seed = seed_lib.normalize(data.get("seed", "") if isinstance(data.get("seed"), str) else "", SEED_GAME)
    if saved_seed and saved_seed.split("-")[0] == seed_lib.prefix_for(SEED_GAME):
        runstate.state.seed = saved_seed
    option = data.get("start_option")
    runstate.state.start_option = option if option in LOADOUT_NODES else None
    runstate.state.immunity_available = bool(data.get("immunity_available", False)) and runstate.state.start_option == "diplomatic_immunity"
    runstate.state.immunity_used = bool(data.get("immunity_used", False))
    runstate.state.peeked_round = _as_int(data.get("peeked_round"), 0, 0)
    runstate.state.perfect_streak = _as_int(data.get("perfect_streak"), 0, 0)
    runstate.state.best_perfect_streak = max(runstate.state.perfect_streak, _as_int(data.get("best_perfect_streak"), 0, 0))
    runstate.state.ironman = bool(data.get("ironman", False))
    runstate.state.undo_record = None
    names = data.get("plant_names") if isinstance(data.get("plant_names"), dict) else {}
    serial = data.get("name_serial") if isinstance(data.get("name_serial"), dict) else {}
    for plant_type in PLANT_TYPES:
        raw_names = names.get(plant_type) if isinstance(names.get(plant_type), list) else []
        runstate.state.plant_names[plant_type] = [n[:NAME_MAX_LEN] for n in raw_names if isinstance(n, str) and n][:300]
        runstate.state.name_serial[plant_type] = _as_int(serial.get(plant_type), len(runstate.state.plant_names[plant_type]), 0, 10 ** 6)
    eulogy = data.get("last_eulogy")
    runstate.state.last_eulogy = (
        {"round": _as_int(eulogy.get("round"), 1, 1), "text": str(eulogy.get("text", ""))[:200]}
        if isinstance(eulogy, dict) and isinstance(eulogy.get("text"), str) and eulogy.get("text")
        else None
    )
    offer = data.get("grant_offer")
    runstate.state.grant_offer = (
        {"id": offer["id"], "round": _as_int(offer.get("round"), 1, 1)}
        if isinstance(offer, dict) and offer.get("id") in GRANTS
        else None
    )
    effects = data.get("grant_effects") if isinstance(data.get("grant_effects"), dict) else {}
    runstate.state.grant_effects = {
        "fossil_surcharge": _as_int(effects.get("fossil_surcharge"), 0, 0, GRANT_CLEAN_ROUNDS),
        "breakdown_risk": _as_int(effects.get("breakdown_risk"), 0, 0, GRANT_CONTEST_ROUNDS),
    }
    message = data.get("last_grant_message")
    runstate.state.last_grant_message = message[:200] if isinstance(message, str) else ""


def _load_career(data):
    """C1: adopt a saved career only if it has finished at least as many
    runs as the live one (a stale save never rolls progress back), after
    full validation; then refresh perks."""
    saved = validate_career(data.get("career"))
    if "career" in data and saved["runs"] >= runstate.career["runs"]:
        # Keep any achievements/unlocks the live career already has.
        saved["achievements"] = sorted(set(saved["achievements"]) | set(runstate.career["achievements"]))
        saved["achievements"] = [e["id"] for e in ACHIEVEMENTS if e["id"] in saved["achievements"]]
        runstate.career = validate_career(saved)
        save_career_to_storage()
    _sync_perks()


# C-26 -- what the last load had to repair. A save missing fields (an older format, or a hand-edited or
# truncated one) used to fall back to defaults silently; now the "What's New" panel says how many and which.
LOAD_REPORT_IGNORED_KEYS = {"achievements_earned"}  # write-only: never read back
load_report = {"loaded": False, "fields": []}


def compute_load_report(data):
    """The saved fields a load had to fill in with defaults: whole keys the save lacks, and plant types
    missing inside the three per-plant dicts."""
    expected = set(get_state().keys()) - LOAD_REPORT_IGNORED_KEYS
    fields = sorted(key for key in expected if key not in data)
    for key in ("plant_counts", "cumulative_built", "plant_age"):
        saved = data.get(key)
        if isinstance(saved, dict):
            fields.extend(f"{key}.{plant_type}" for plant_type in PLANT_TYPES if plant_type not in saved)
    return fields


def load_report_text():
    if not load_report["loaded"]:
        return ""
    fields = load_report["fields"]
    if not fields:
        return "Last save loaded: complete, nothing had to be repaired."
    shown = ", ".join(fields[:8]) + (f" and {len(fields) - 8} more" if len(fields) > 8 else "")
    return (
        f"Last save loaded: repaired {len(fields)} missing field{'s' if len(fields) != 1 else ''} "
        f"with safe defaults ({shown})."
    )


# B-23: a few honest, already-computed numbers for the hub's Climate Steward page. Written into the save as a
# read-only `summary` list ({label, value, unit, note?}); never read back by load_state().
def steward_summary():
    played = len(runstate.state.clean_fraction_log)
    return [
        {"label": "Renewable share of capacity", "value": round(renewable_capacity_share() * 100), "unit": "%"},
        {"label": "Rounds played", "value": played, "unit": ""},
        {"label": "Plants built", "value": int(sum(runstate.state.cumulative_built.values())), "unit": ""},
    ]
