"""Saving: get_state(), the field-by-field loaders, the save checker and the recovery panel, steward_summary().
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

import copy
import html
import json

from js import document

import herd_runstate as runstate
from herd_rules import (
    DECOUPLING_MEASURES, HALL_OF_FAME_SIZE, LEVER_LABELS, LEVER_LOG_MAX, POLICY_HEDGE_ROUNDS,
    POLICY_HISTORY_MAX, POLICY_LABEL_ROUNDS, POLICY_OPTIONS, RULE_SPECS, STARTING_FUNDS,
)
from herd_util import _is_finite_number, _safe_int
from herd_model import rules_are_custom
from herd_achievements import _display_milestone_toast, achievement_ids_earned
from herd_barns import DEFAULT_BARN, _load_barns
from herd_loadouts import _load_audits, _load_loadouts
from herd_collection import BREEDS, COMBOS, _valid_ids
from herd_family import FAMILY_BRANCHES


# SAVE-BUTTON-INTEGRATION.md contract for the shared shared/save-widget.js:
# get_state() returns every module-level mutable game-state field as one
# plain, JSON-safe dict, and load_state() is its exact inverse. SOL is the
# reference integration for this contract. decoupling_investment is copied
# (not handed back by reference) so continued play after taking a
# "snapshot" can't silently mutate it, same reasoning as SOL's
# serialize_state() docstring. info_page_open is deliberately excluded —
# it's a cosmetic panel toggle, not tracked game progress.
def get_state():
    if runstate.sandbox_active:  # GF-24: a save, an autosave or a leaderboard read while the sandbox is on is the REAL game
        return copy.deepcopy(runstate._sandbox_real["snapshot"])
    state = {
        "round_number": runstate.farm.round_number,
        "funds": runstate.farm.funds,
        "herd_size": runstate.farm.herd_size,
        "methane": runstate.farm.methane,
        "decoupling_investment": dict(runstate.farm.decoupling_investment),
        "plant_pivot_investment": runstate.farm.plant_pivot_investment,
        "counterfactual_funds": runstate.farm.counterfactual_funds,
        "counterfactual_methane": runstate.farm.counterfactual_methane,
        "methane_history": list(runstate.farm.methane_history),
        "max_pressure_fraction_seen": runstate.farm.max_pressure_fraction_seen,
        "seen_half_decoupled_callout": runstate.farm.seen_half_decoupled_callout,
        "seen_pressure_callout": runstate.farm.seen_pressure_callout,
        "seen_methane_penalty_nudge": runstate.farm.seen_methane_penalty_nudge,
        "certification_streak": runstate.farm.certification_streak,
        "certified": runstate.farm.certified,
        "poultry_size": runstate.farm.poultry_size,
        "poultry_investment": dict(runstate.farm.poultry_investment),
        "genetics_active": runstate.farm.genetics_active,
        "genetics_pending": list(runstate.farm.genetics_pending),
        "supply_chain_investment": runstate.farm.supply_chain_investment,
        "variation_enabled": runstate.farm.variation_enabled,
        "regional_cap_enabled": runstate.farm.regional_cap_enabled,
        "policy_offer_pending": runstate.farm.policy_offer_pending,
        "subsidy_rounds_left": runstate.farm.subsidy_rounds_left,
        "summary": steward_summary(),  # B-23: write-only, never read back
        "achievements_earned": achievement_ids_earned(),
    }
    # F1: satellite state only once the satellite has been opened.
    if runstate.farm.satellite_open:
        state["satellite_open"] = True
        state["satellite_size"] = runstate.farm.satellite_size
        state["satellite_retrofits"] = runstate.farm.satellite_retrofits
    # GF-29/F-17/GF-15/GF-16/GF-5: written only once there is something to keep.
    if len(runstate.farm.funds_history) > 1:
        state["funds_history"] = list(runstate.farm.funds_history)
    if runstate.farm.lever_log:
        state["lever_log"] = [list(entry) for entry in runstate.farm.lever_log]
    if runstate.farm.perfect_streak > 0:
        state["perfect_streak"] = runstate.farm.perfect_streak
    if runstate.farm.best_perfect_streak > 0:
        state["best_perfect_streak"] = runstate.farm.best_perfect_streak
    if runstate.breeds_collected:
        state["breeds_collected"] = list(runstate.breeds_collected)
    if runstate.combos_found:
        state["combos_found"] = list(runstate.combos_found)
    if runstate.hall_of_fame:
        state["hall_of_fame"] = [list(entry) for entry in runstate.hall_of_fame]
    if runstate.farm.undo_used:
        state["undo_used"] = True
    # GF-3: audit record, only once an audit has happened or something is pending.
    if runstate.farm.audits_done > 0:
        state["audits_done"] = runstate.farm.audits_done
        state["audit_log"] = [list(entry) for entry in runstate.farm.audit_log]
    if runstate.farm.audit_perks:
        state["audit_perks"] = list(runstate.farm.audit_perks)
    if runstate.farm.trust_rounds_left > 0:
        state["trust_rounds_left"] = runstate.farm.trust_rounds_left
    # GF-23: starting loadouts, only when there is something to keep.
    if runstate.farm.loadout != "standard":
        state["loadout"] = runstate.farm.loadout
    if runstate.loadouts_unlocked:
        state["loadouts_unlocked"] = list(runstate.loadouts_unlocked)
    if runstate.loadout_choice != "standard":
        state["loadout_choice"] = runstate.loadout_choice
    # GF-28: blind-run flags, only when set.
    if runstate.farm.blind_run:
        state["blind_run"] = True
        if runstate.farm.blind_revealed:
            state["blind_revealed"] = True
    # GF-21: the golden-cow tally, only once a cow has been welcomed.
    if runstate.farm.golden_claimed > 0:
        state["golden_claimed"] = runstate.farm.golden_claimed
        state["golden_funds"] = round(runstate.farm.golden_funds, 2)
    # GF-17: barn skins unlocked and the one in use, written only when there is something to keep.
    if runstate.barns_unlocked:
        state["barns_unlocked"] = list(runstate.barns_unlocked)
    if runstate.barn_skin != DEFAULT_BARN:
        state["barn_skin"] = runstate.barn_skin
    # F-9: advisor pool state, written only once there is something to keep.
    if runstate.farm.policy_offer_pending and len(runstate.farm.policy_offer) == 2:
        state["policy_offer"] = list(runstate.farm.policy_offer)
    if runstate.farm.policy_seen:
        state["policy_seen"] = list(runstate.farm.policy_seen)
    if runstate.farm.policy_history:
        state["policy_history"] = [list(entry) for entry in runstate.farm.policy_history]
    if runstate.farm.story_choices:
        state["family_choices"] = list(runstate.farm.story_choices)
    if runstate.family_endings:
        state["family_endings"] = list(runstate.family_endings)
    if runstate.farm.mixer_blends > 0:
        state["mixer_stats"] = [runstate.farm.mixer_blends, runstate.farm.mixer_perfects, round(runstate.farm.mixer_bonus_total, 1), runstate.farm.mixer_round]
    if runstate.farm.hedge_rounds_left > 0:
        state["hedge_rounds_left"] = runstate.farm.hedge_rounds_left
    if runstate.farm.label_rounds_left > 0:
        state["label_rounds_left"] = runstate.farm.label_rounds_left
    # F-1: ranch rules and the unranked flag, only when something is non-standard.
    custom = {n: v for n, v in runstate.ranch_rules.items() if abs(v - RULE_SPECS[n]["default"]) > 1e-9}
    if custom:
        state["ranch_rules"] = custom
    if runstate.farm.custom_rules_used:
        state["custom_rules_used"] = True
    # F25: succession state is written only once a handover has happened or
    # points/perks exist, so an ordinary save is unchanged.
    if runstate.generation > 1:
        state["generation"] = runstate.generation
    if runstate.legacy_points > 0:
        state["legacy_points"] = runstate.legacy_points
    if runstate.legacy_perks:
        state["legacy_perks"] = dict(runstate.legacy_perks)
    return state


def _policy_ids(raw):
    """Option ids from untrusted save data, kept only when they are real options."""
    if not isinstance(raw, list):
        return []
    return [o for o in raw if isinstance(o, str) and o in POLICY_OPTIONS]


def _load_family_story(data):
    """Story choices must be a valid path through the story (first a branch, then one of its options);
    endings found must be real branch ids. Anything else is dropped."""
    choices = []
    saved = data.get("family_choices")
    if isinstance(saved, list) and saved and isinstance(saved[0], str) and saved[0] in FAMILY_BRANCHES:
        choices.append(saved[0])
        if len(saved) > 1 and isinstance(saved[1], str) and saved[1] in FAMILY_BRANCHES[saved[0]]["options"]:
            choices.append(saved[1])
    runstate.farm.story_choices = choices
    found = data.get("family_endings")
    runstate.family_endings = []
    if isinstance(found, list):
        for branch in found:
            if isinstance(branch, str) and branch in FAMILY_BRANCHES and branch not in runstate.family_endings:
                runstate.family_endings.append(branch)


def _load_policy_fields(data):
    offer = _policy_ids(data.get("policy_offer"))
    runstate.farm.policy_offer = offer if len(offer) == 2 and offer[0] != offer[1] else []
    seen = _policy_ids(data.get("policy_seen"))
    runstate.farm.policy_seen = [o for i, o in enumerate(seen) if o not in seen[:i]]
    runstate.farm.policy_history = []
    history = data.get("policy_history")
    if isinstance(history, list):
        for entry in history[-POLICY_HISTORY_MAX:]:
            if (
                isinstance(entry, (list, tuple)) and len(entry) == 3 and _is_finite_number(entry[0])
                and entry[1] in POLICY_OPTIONS and entry[2] in POLICY_OPTIONS and entry[1] != entry[2]
            ):
                runstate.farm.policy_history.append([max(1, int(entry[0])), entry[1], entry[2]])
    _load_family_story(data)
    stats = data.get("mixer_stats")
    runstate.farm.mixer_blends = runstate.farm.mixer_perfects = runstate.farm.mixer_round = 0
    runstate.farm.mixer_bonus_total = 0.0
    if isinstance(stats, (list, tuple)) and len(stats) == 4 and all(_is_finite_number(v) for v in stats):
        runstate.farm.mixer_blends = _safe_int(stats[0], 0)
        runstate.farm.mixer_perfects = min(runstate.farm.mixer_blends, _safe_int(stats[1], 0))
        runstate.farm.mixer_bonus_total = max(0.0, float(stats[2]))
        runstate.farm.mixer_round = _safe_int(stats[3], 0)
    runstate.farm.hedge_rounds_left = min(POLICY_HEDGE_ROUNDS, _safe_int(data.get("hedge_rounds_left"), 0))
    runstate.farm.label_rounds_left = min(POLICY_LABEL_ROUNDS, _safe_int(data.get("label_rounds_left"), 0))


def _load_progress_fields(data):
    """Validated load of the highlights/log/streak/collection fields; every one
    defaults safely so older saves and hand-edited payloads cannot crash."""
    history = data.get("funds_history")
    cleaned = None
    if isinstance(history, list):
        cleaned = []
        for value in history:
            if (
                isinstance(value, (int, float)) and not isinstance(value, bool)
                and value == value and abs(value) != float("inf")
            ):
                cleaned.append(float(value))
            else:
                cleaned.append(None)
    # Aligned with methane_history: a missing or mismatched record becomes "unknown
    # until now" padding so rounds already played never invent numbers.
    if cleaned is None or len(cleaned) != len(runstate.farm.methane_history):
        cleaned = [None] * (len(runstate.farm.methane_history) - 1) + [runstate.farm.funds]
    runstate.farm.funds_history = cleaned
    log = data.get("lever_log")
    runstate.farm.lever_log = []
    if isinstance(log, list):
        for entry in log[-LEVER_LOG_MAX:]:
            if (
                isinstance(entry, (list, tuple)) and len(entry) == 3 and entry[1] in LEVER_LABELS
                and isinstance(entry[0], (int, float)) and not isinstance(entry[0], bool)
                and isinstance(entry[2], (int, float)) and not isinstance(entry[2], bool)
                and entry[0] == entry[0] and entry[2] == entry[2]
                and abs(entry[0]) != float("inf") and abs(entry[2]) != float("inf")
            ):
                runstate.farm.lever_log.append([max(1, int(entry[0])), entry[1], float(entry[2])])
    runstate.farm.perfect_streak = _safe_int(data.get("perfect_streak"), 0)
    runstate.farm.best_perfect_streak = max(runstate.farm.perfect_streak, _safe_int(data.get("best_perfect_streak"), 0))
    runstate.breeds_collected = _valid_ids(data.get("breeds_collected"), BREEDS)
    runstate.combos_found = _valid_ids(data.get("combos_found"), COMBOS)
    runstate.farm.undo_used = data.get("undo_used") is True
    runstate.farm.undo_snapshot = None
    _load_barns(data)
    _load_loadouts(data)
    _load_audits(data)
    runstate.farm.blind_run = data.get("blind_run") is True
    runstate.farm.blind_revealed = runstate.farm.blind_run and data.get("blind_revealed") is True
    runstate.farm.golden_claimed = _safe_int(data.get("golden_claimed"), 0)
    golden_funds = data.get("golden_funds")
    runstate.farm.golden_funds = float(golden_funds) if runstate.farm.golden_claimed > 0 and _is_finite_number(golden_funds) and golden_funds >= 0 else 0.0
    runstate.farm.custom_rules_used = data.get("custom_rules_used") is True or rules_are_custom()
    runstate.hall_of_fame = []
    saved_hall = data.get("hall_of_fame")
    if isinstance(saved_hall, list):
        for entry in saved_hall[:HALL_OF_FAME_SIZE]:
            if (
                isinstance(entry, (list, tuple)) and len(entry) == 3 and isinstance(entry[0], str)
                and all(isinstance(v, (int, float)) and not isinstance(v, bool) and v == v for v in entry[1:])
                and abs(entry[1]) != float("inf") and abs(entry[2]) != float("inf")
            ):
                runstate.hall_of_fame.append([entry[0][:40], max(0, int(entry[1])), max(1, int(entry[2]))])
        runstate.hall_of_fame.sort(key=lambda e: (-e[1], e[2]))


# ===========================================================================
# F-30: friendly save recovery. A save that fails validation never touches the farm: the player
# sees a plain reason for each problem and can keep the current farm or load the save with
# defaults in place of just the bad fields. The widget around load_state() reports "Load failed"
# because load_state() raises ValueError for such a save; the panel explains why.
# ===========================================================================
# key: (plain label, minimum, whole number only, default for a fresh farm)
SAVE_NUMBER_FIELDS = {
    "round_number": ("Round number", 1, True, 1),
    "funds": ("Funds", None, False, STARTING_FUNDS),
    "herd_size": ("Herd size", 0, True, 0),
    "methane": ("Methane", 0, False, 0.0),
    "plant_pivot_investment": ("Plant-based pivot units", 0, True, 0),
    "counterfactual_funds": ("Baseline funds", None, False, STARTING_FUNDS),
    "counterfactual_methane": ("Baseline methane", 0, False, 0.0),
    "max_pressure_fraction_seen": ("Worst pressure seen", 0, False, 0.0),
}
RECOVERY_MAX_REASONS = 6


def _shown(value):
    text = json.dumps(value, default=str) if not isinstance(value, str) else f'"{value}"'
    return text if len(text) <= 24 else text[:21] + "..."


def _number_problem(label, value, minimum, whole):
    """A plain-language reason this value cannot be used, or None when it is fine."""
    if not _is_finite_number(value):
        return f"{label} should be a number, but the save has {_shown(value)}."
    if whole and value != int(value):
        return f"{label} should be a whole number, but the save has {_shown(value)}."
    if minimum is not None and value < minimum:
        return f"{label} should be {minimum} or more, but the save has {_shown(value)}."
    return None


def check_save(data):
    """List of (key, reason) for every field that is present but unusable. A field that is simply
    missing is not a problem (older saves lack newer fields and load with defaults, as always)."""
    if not isinstance(data, dict):
        return [("", "This is not a Herd save (it is not a set of named values).")]
    problems = []
    for key, (label, minimum, whole, _default) in SAVE_NUMBER_FIELDS.items():
        if key in data:
            reason = _number_problem(label, data[key], minimum, whole)
            if reason:
                problems.append((key, reason))
    investment = data.get("decoupling_investment")
    if "decoupling_investment" in data and not isinstance(investment, dict):
        problems.append(("decoupling_investment", "The decoupling investments should be a list of counts, but the save has something else."))
    elif isinstance(investment, dict):
        for measure in DECOUPLING_MEASURES:
            if measure in investment:
                reason = _number_problem(f"{DECOUPLING_MEASURES[measure]['label']} units", investment[measure], 0, True)
                if reason:
                    problems.append((f"decoupling_investment.{measure}", reason))
    history = data.get("methane_history")
    if "methane_history" in data and (
        not isinstance(history, list) or not history or not all(_is_finite_number(v) for v in history)
    ):
        problems.append(("methane_history", "The methane history should be a list of numbers, but the save has something else."))
    return problems


def sanitize_save(data, problems):
    """A copy of the save with a fresh-farm default in place of just the bad fields."""
    clean = copy.deepcopy(data)
    for key, _reason in problems:
        if key in SAVE_NUMBER_FIELDS:
            clean[key] = SAVE_NUMBER_FIELDS[key][3]
        elif key == "decoupling_investment":
            clean[key] = {m: 0 for m in DECOUPLING_MEASURES}
        elif key.startswith("decoupling_investment."):
            clean["decoupling_investment"][key.split(".", 1)[1]] = 0
        elif key == "methane_history":
            clean[key] = [0.0]
    return clean


def render_save_recovery():
    panel = document.getElementById("save-recovery-panel")
    panel.hidden = runstate.pending_recovery is None
    if runstate.pending_recovery is None:
        return
    reasons = [reason for _key, reason in runstate.pending_recovery["problems"][:RECOVERY_MAX_REASONS]]
    extra = len(runstate.pending_recovery["problems"]) - len(reasons)
    if extra > 0:
        reasons.append(f"...and {extra} more.")
    document.getElementById("save-recovery-reasons").innerHTML = "".join(
        f"<li>{html.escape(r)}</li>" for r in reasons
    )
    can_default = runstate.pending_recovery["data"] is not None
    document.getElementById("save-recovery-defaults-button").hidden = not can_default
    document.getElementById("save-recovery-note").innerText = (
        "Your current farm has not been changed. You can keep it, or load this save with a fresh-farm "
        "value in place of only the fields listed above."
        if can_default else "Your current farm has not been changed."
    )


def _offer_recovery(data, problems):
    runstate.pending_recovery = {"data": data if isinstance(data, dict) else None, "problems": problems}
    render_save_recovery()
    _display_milestone_toast("That save could not be loaded as it is. See the notice at the top for why.")


def on_recovery_dismiss(event=None):
    runstate.pending_recovery = None
    render_save_recovery()


# B-23: a few honest, already-computed numbers for the hub's Climate Steward page. Written into the save as a
# read-only `summary` list ({label, value, unit, note?}); never read back by load_state().
def steward_summary():
    return [
        {"label": "Methane decoupled from output", "value": round(max(0.0, runstate.farm.decoupled_fraction()) * 100), "unit": "%"},
        {"label": "Breeds collected", "value": len(runstate.breeds_collected), "unit": f"of {len(BREEDS)}"},
        {"label": "Rounds farmed", "value": max(0, int(runstate.farm.round_number) - 1), "unit": ""},
    ]
