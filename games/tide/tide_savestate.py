"""get_state(), the steward summary, the resume note, the helper fields the save carries and the community coastline line (R-30)."""

import copy
import math

from js import document

import tide_runstate as runstate
from tide_achievements import achievement_ids_earned
from tide_rules import ADAPTATION_TIERS, COASTLINE_ROWS, DEFAULT_COASTLINE, DEFAULT_SEA_SCENARIO


# SAVE-BUTTON-INTEGRATION.md contract for the shared shared/save-widget.js:
# get_state() packages every module-level mutable global — here, all of
# it lives on the single `state` object — into a plain JSON-safe dict
# (numbers/strings/lists/dicts/bools only, no SettlementState instance
# itself crossing the boundary). The three log lists and the capacity
# dict are deep-copied so a live reference into `state` is never leaked
# into the saved snapshot; a shallow reference would let continued play
# after "saving" silently mutate what was supposed to be a frozen copy
# (same reasoning as SOL's serialize_state() docstring). Tide tracks no
# non-JSON-native types (no sets, unlike SOL's unlocked_bodies), so no
# extra conversion is needed. load_state() is the exact inverse, then
# calls render() (Tide's full-render function) so the UI reflects the
# loaded state immediately.
def _tier_first_season_field():
    """D9: the season each adaptation tier was first active, for the tiers this
    settlement has reached (t1 = sandbag berms, ...). A write-only number
    group for the community seawall comparison; never read back."""
    first = {}
    for tier_index in range(1, len(ADAPTATION_TIERS)):
        for i, tier in enumerate(runstate.state.tier_log):
            if tier >= tier_index:
                first[f"t{tier_index}"] = i + 1
                break
    return {"tier_first_season": first} if first else {}


def coastline_standard_terms():
    """R-30: True when this settlement is played on the standard terms, so its dry-row count can be
    compared with other players': the standard coastline, the moderate sea-level scenario, no
    Workshop dials or Tidal Chess, and not a Daily Tide run."""
    return (
        runstate.state.coastline == DEFAULT_COASTLINE
        and runstate.state.sea_scenario == DEFAULT_SEA_SCENARIO
        and not runstate.state.keeps_records_out()
    )


def coastline_kept_comparable():
    """R-30: standard terms and at least one season resolved (an untouched settlement keeps all six
    rows and would only pull the community average up)."""
    return runstate.state.season > 1 and coastline_standard_terms()


def _coastline_kept_field():
    """R-30: how many of the six coastline rows are still dry, for the community coastline line. A
    write-only number (the same count the Climate Steward summary calls rows still dry); only written
    for a comparable settlement, never read back. The backend lists it in app/stats.py STATS_FIELDS."""
    return {"coastline_kept": runstate.state.rows_dry_count()} if coastline_kept_comparable() else {}


def set_community_coastline(mean, count=None):
    """Called by the page with the field's mean (and how many saves it covers). Anything that is not a
    finite number from 0 to the number of rows clears the line. Returns True when a figure is kept."""
    ok = (
        isinstance(mean, (int, float)) and not isinstance(mean, bool)
        and math.isfinite(mean) and 0 <= mean <= COASTLINE_ROWS
    )
    if ok:
        saves = count if isinstance(count, int) and not isinstance(count, bool) and count > 0 else None
        runstate.community_coastline = {"mean": float(mean), "count": saves}
    else:
        runstate.community_coastline = None
    render_coastline_community()
    return ok


def coastline_community_text():
    """R-30: the community line, or "" while there is no figure to show."""
    if runstate.community_coastline is None:
        return ""
    mean = f"{runstate.community_coastline['mean']:.1f}"
    from_text = f" (from {runstate.community_coastline['count']} settlements)" if runstate.community_coastline["count"] else ""
    if coastline_standard_terms():
        you = runstate.state.rows_dry_count()
        return f"Players keep on average {mean} of {COASTLINE_ROWS} coastline rows dry; you keep {you}{from_text}."
    return (
        f"Players on the standard coastline with moderate sea-level rise keep on average {mean} of "
        f"{COASTLINE_ROWS} coastline rows dry{from_text}. This settlement plays on other terms, so there is "
        "nothing to compare."
    )


def render_coastline_community():
    el = document.getElementById("coastline-community")
    if el is None:
        return
    text = coastline_community_text()
    el.innerText = text
    el.hidden = not text


def resume_note():
    """QI-58: one plain line for the hub's "Pick up where you stopped" strip (read by shared/last-played.js)."""
    return f"Season {runstate.state.season}, funds {round(runstate.state.funds)}"


# B-23: a few honest, already-computed numbers for the hub's Climate Steward page. Written into the save as a
# read-only `summary` list ({label, value, unit, note?}); never read back by load_state().
def steward_summary():
    dry = sum(1 for row in range(COASTLINE_ROWS) if not runstate.state.row_lost(row))
    return [
        {"label": "Coastline rows still dry", "value": dry, "unit": f"of {COASTLINE_ROWS}"},
        {"label": "Settlers housed", "value": int(runstate.state.population), "unit": ""},
        {"label": "Seawall tier", "value": runstate.state.current_tier_index(), "unit": f"of {len(ADAPTATION_TIERS) - 1}",
         "note": runstate.state.current_tier()["name"]},
    ]


def get_state():
    return {
        "season": runstate.state.season,
        "funds": runstate.state.funds,
        "capacity": copy.deepcopy(runstate.state.capacity),
        "acidity": runstate.state.acidity,
        "acidity_history": copy.deepcopy(runstate.state.acidity_history),
        "sea_level": runstate.state.sea_level,
        "cumulative_damage": runstate.state.cumulative_damage,
        "undampened_damage_total": runstate.state.undampened_damage_total,
        "damage_log": copy.deepcopy(runstate.state.damage_log),
        "ticker_log": copy.deepcopy(runstate.state.ticker_log),
        "trend_flattening_announced": runstate.state.trend_flattening_announced,
        "ticker_full_history": copy.deepcopy(runstate.state.ticker_full_history),
        "hard_lag_mode": runstate.state.hard_lag_mode,
        **(
            {"sister": {
                "damage": runstate.state.sister_cumulative_damage, "net_funds": runstate.state.sister_net_funds,
            }}
            if runstate.state.sister_enabled else {}
        ),
        "output_mix": runstate.state.output_mix,
        "fish_yield_history": copy.deepcopy(runstate.state.fish_yield_history),
        "first_flood_announced": runstate.state.first_flood_announced,
        "baseline_season": runstate.state.baseline_season,
        "baseline_sea_level": runstate.state.baseline_sea_level,
        "baseline_damage": runstate.state.baseline_damage,
        "min_fish_yield_ever": runstate.state.min_fish_yield_ever,
        "max_acidity_ever": runstate.state.max_acidity_ever,
        "max_funds_ever": runstate.state.max_funds_ever,
        "fortified_in_time_earned": runstate.state.fortified_in_time_earned,
        **({"ranks": {"storms_weathered": runstate.state.storms_weathered, "storms_clean": runstate.state.storms_clean,
                      "early_retreats": runstate.state.early_retreats}}
           if (runstate.state.storms_weathered or runstate.state.storms_clean or runstate.state.early_retreats) else {}),  # D-10
        "tier_log": copy.deepcopy(runstate.state.tier_log),
        **_tier_first_season_field(),
        **_coastline_kept_field(),  # R-30: write-only, never read back
        "hard_lag_note_seen": runstate.state.hard_lag_note_seen,
        "fish_crash_open": runstate.state.fish_crash_open,
        "recovery_celebrated_season": runstate.state.recovery_celebrated_season,
        "sea_scenario": runstate.state.sea_scenario,
        **({"coastline": runstate.state.coastline} if runstate.state.coastline != DEFAULT_COASTLINE else {}),  # D-8
        **({"daily": copy.deepcopy(runstate.state.daily)} if runstate.state.daily else {}),  # GD-5
        **({"buys": {"log": [list(r) for r in runstate.state.season_buys], "now": list(runstate.state.buys_now)}}
           if (runstate.state.season_buys or any(runstate.state.buys_now)) else {}),  # D-3
        "settlement_name": runstate.state.settlement_name,
        "chronicle": copy.deepcopy(runstate.state.chronicle),
        "heritage": copy.deepcopy(runstate.state.heritage),
        "monitoring_reports": runstate.state.monitoring_reports,
        "monitoring_last_season": runstate.state.monitoring_last_season,
        "storm_mode": runstate.state.storm_mode,
        "storm_log": copy.deepcopy(runstate.state.storm_log),
        "retreat_rows": list(runstate.state.retreat_rows),
        "population": runstate.state.population,
        "peak_population": runstate.state.peak_population,
        "displaced_total": runstate.state.displaced_total,
        "relocated_total": runstate.state.relocated_total,
        "diversification": dict(runstate.state.diversification),
        "checkpoint": copy.deepcopy(runstate.state.checkpoint),
        "foresight": copy.deepcopy(runstate.state.foresight),
        "replay_count": runstate.state.replay_count,
        "season_ledger": copy.deepcopy(runstate.state.season_ledger),
        "season_snapshots": copy.deepcopy(runstate.state.season_snapshots),
        **({"pinned_goal": {"id": runstate.state.pinned_goal, "reached": runstate.state.pinned_goal_reached}} if runstate.state.pinned_goal else {}),  # GD-19
        **({"run_stats": {
            "rewind_used": runstate.state.rewind_used, "hard_lag_all_run": runstate.state.hard_lag_all_run, "ironman": runstate.state.ironman_earned,
            "actions": runstate.state.actions_count, "seconds": round(runstate.state.active_seconds, 1),
            "maxtier_actions": runstate.state.maxtier_actions, "maxtier_seconds": runstate.state.maxtier_seconds,
        }} if (runstate.state.rewind_used or runstate.state.ironman_earned or runstate.state.actions_count or not runstate.state.hard_lag_all_run) else {}),  # GD-20/23/24
        **({"sightings": list(runstate.state.sightings)} if runstate.state.sightings else {}),  # GD-18
        **({"crew": list(runstate.state.crew)} if runstate.state.crew else {}),  # GD-11
        **({"chess": {"on": runstate.state.chess_mode, "runoff": list(runstate.state.runoff_queue), "dips": runstate.state.chess_dips}} if runstate.state.chess_mode else {}),  # GD-4
        **({"brace": dict(runstate.state.brace), "storm_result": runstate.state.last_storm_result}
           if (runstate.state.brace["barriers"] or runstate.state.brace["stockpile"] or runstate.state.brace["evacuate"] or runstate.state.last_storm_result) else {}),  # GD-3
        **({"acid_boss": {"mode": runstate.state.acid_boss_mode, "braced": runstate.state.acid_braced, "result": runstate.state.acid_boss_result}}
           if (runstate.state.acid_boss_mode or runstate.state.acid_braced or runstate.state.acid_boss_result) else {}),  # GD-12
        **({"workshop": dict(runstate.state.workshop)} if runstate.state.workshop_active() else {}),  # D-5
        **({"market": {"event": copy.deepcopy(runstate.state.market_event), "accepted": runstate.state.market_accepted, "dip": runstate.state.income_dip_seasons}}
           if (runstate.state.market_event or runstate.state.market_accepted or runstate.state.income_dip_seasons) else {}),  # GD-8
        **({"balance": {"streak": runstate.state.balance_streak, "invested": sorted(runstate.state.season_invested)}} if (runstate.state.balance_streak or runstate.state.season_invested) else {}),  # GD-14
        **({"domino": {"left": runstate.state.domino_seasons_left, "count": runstate.state.domino_count}} if (runstate.state.domino_seasons_left or runstate.state.domino_count) else {}),  # GD-28
        "summary": steward_summary(),  # B-23: write-only, never read back
        # Write-only projection (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) —
        # always freshly recomputed, never read back in load_state().
        "achievements_earned": achievement_ids_earned(),
    }


# Late binding: tide_model_town calls get_state() but comes earlier in the module list, so it gets it from here.
import tide_model_town
tide_model_town.get_state = get_state
