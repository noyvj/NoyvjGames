"""The helpers load_state() uses to read each saved part safely, and the load note."""

import copy

from js import document

import drift_runstate as runstate
from drift_collection import collection
from drift_model_region import region
from drift_plans import _clean_autopilot
from drift_regional import _new_neighbor_region
from drift_rules import (
    AUTOPILOT_DEFAULT_RULES, CALENDAR_KINDS, CALENDAR_LOG_MAX, CAPACITY_TYPES, COUNCIL_BY_ID,
    DRIFT_LOG_MAX_ENTRIES, LEDGER_FIELDS, LEDGER_MAX_ENTRIES, SPEND_KEYS, _finite_number, _is_number,
    _number_list, _small_int, calendar_event_for_round, council_next_program,
)


# --- Save system (SAVE-BUTTON-INTEGRATION.md contract for the shared
# shared/save-widget.js) ---
# get_state() packages every module-level mutable global into one plain,
# JSON-safe dict; load_state() is its exact inverse. `region` is a
# RegionState instance rather than a plain dict, so its attributes are
# unpacked/restored by hand. `capacity`, `arrivals_log`, and `strain_log`
# are deep-copied on the way out (and back in) so a live reference isn't
# leaked into the saved snapshot -- continued play after taking a
# "snapshot" would otherwise silently mutate it, same reasoning as SOL's
# serialize_state() docstring. `net_positive_round` (Iteration Pass 3's
# turning-point milestone) is either `None` or an int, already JSON-safe.
#
# `capacity`'s key set (housing/services/infrastructure) belongs to
# CAPACITY_TYPES in this file, not to the save -- it's restored key-by-key
# into the live dict rather than wholesale-replaced, so a save missing one
# of those keys (an older save format from before a capacity type existed,
# or a hand-edited/corrupted payload) can't wipe that type out of the live
# dict entirely. total_capacity() and render() both do
# `region.capacity[t]` for every `t in CAPACITY_TYPES` unconditionally, so
# a missing key there would crash the very next render -- same bug shape
# as SOL's planet_state and Continuum's resources/allocation/buildings.
#
# Every other field below is restored via `.get(key, <current live
# value>)` rather than bare `data[key]` indexing, for the same reason:
# a save written before a field existed (e.g. one from before Iteration
# Pass 3 added cumulative_services_investment/
# cumulative_integration_contribution/net_positive_round, or before the
# info-page feature added info_page_open) must not KeyError outright --
# it should fall back to whatever the live region already has, same
# graceful-degradation contract as capacity's per-key merge above. This
# mirrors the exact fix Tide's load_state() needed for the identical bug
# shape (see BCM114-DEV-LOG.md 2026-09-02).
def _neighbor_state_fields():
    """I1/I7: the neighbouring region, written only once it has been opened."""
    if runstate.neighbor is None:
        return {}
    return {"neighbor": {
        "round_number": runstate.neighbor.round_number,
        "funds": runstate.neighbor.funds,
        "capacity": dict(runstate.neighbor.capacity),
        "background_severity": runstate.neighbor.background_severity,
        "total_arrivals": runstate.neighbor.total_arrivals,
        "integrated_population": runstate.neighbor.integrated_population,
        "strain_sum": runstate.neighbor._strain_sum,
        "strain_count": runstate.neighbor._strain_count,
        "cumulative_services_investment": runstate.neighbor.cumulative_services_investment,
        "cumulative_integration_contribution": runstate.neighbor.cumulative_integration_contribution,
        "support_sent": runstate.neighbor_support_sent,
    }}


def _load_roi_log(saved):
    """I-12: a list of finite non-negative numbers (anything else is dropped), at most DRIFT_LOG_MAX_ENTRIES."""
    if not isinstance(saved, list):
        return []
    values = [_finite_number(v, None) for v in saved]
    return [round(v, 3) for v in values if v is not None and v <= 1e6][-DRIFT_LOG_MAX_ENTRIES:]


def _load_neighbor(saved):
    if not isinstance(saved, dict):
        runstate.neighbor = None
        runstate.neighbor_support_sent = 0.0
        return
    other = _new_neighbor_region()
    other.round_number = int(_finite_number(saved.get("round_number"), 1, 1))
    other.funds = _finite_number(saved.get("funds"), other.funds)
    saved_capacity = saved.get("capacity")
    if isinstance(saved_capacity, dict):
        for capacity_type in CAPACITY_TYPES:
            other.capacity[capacity_type] = _finite_number(saved_capacity.get(capacity_type), other.capacity[capacity_type])
    other.background_severity = _finite_number(saved.get("background_severity"), other.background_severity)
    other.total_arrivals = _finite_number(saved.get("total_arrivals"), other.total_arrivals)
    other.integrated_population = min(other.total_arrivals, _finite_number(saved.get("integrated_population"), 0.0))
    other._strain_count = int(_finite_number(saved.get("strain_count"), 0))
    other._strain_sum = min(float(other._strain_count), _finite_number(saved.get("strain_sum"), 0.0))
    other.cumulative_services_investment = _finite_number(saved.get("cumulative_services_investment"), 0.0)
    other.cumulative_integration_contribution = _finite_number(saved.get("cumulative_integration_contribution"), 0.0)
    runstate.neighbor = other
    runstate.neighbor_support_sent = _finite_number(saved.get("support_sent"), 0.0)


def _ledger_state_fields():
    """I-8, GI-18, GI-15/22: written only once there is something to write, so a
    fresh region's save is unchanged. Ledger rows ride as plain lists in
    LEDGER_FIELDS order to keep the payload small."""
    out = {}
    if any(region.spend_by_type.values()):
        out["spend_by_type"] = dict(region.spend_by_type)
    if any(region.round_spend.values()):
        out["round_spend"] = dict(region.round_spend)
    if region.ledger:
        out["ledger"] = [[row[name] for name in LEDGER_FIELDS] for row in region.ledger]
    if region.rewind_used_round is not None:
        out["rewind_used_round"] = region.rewind_used_round
    if collection["titles"] or collection["civic"]:
        out["collection"] = copy.deepcopy(collection)
    if region.best_perfect_fit_streak > 0:
        out["perfect_fit"] = {"streak": region.perfect_fit_streak, "best": region.best_perfect_fit_streak}
    if region.calendar_enabled or region.braced_rounds or region.calendar_log:
        out["calendar"] = {
            "enabled": region.calendar_enabled,
            "braced": list(region.braced_rounds),
            "log": [dict(entry) for entry in region.calendar_log],
        }
    if region.council_picks:
        out["council"] = list(region.council_picks)
    if region.autopilot != AUTOPILOT_DEFAULT_RULES:
        out["autopilot"] = dict(region.autopilot)
    if region.stars_banked is not None:
        out["stars_banked"] = region.stars_banked
    return out


def _load_spend_dict(saved):
    out = {key: 0.0 for key in SPEND_KEYS}
    if isinstance(saved, dict):
        for key in SPEND_KEYS:
            out[key] = _finite_number(saved.get(key), 0.0)
    return out


def _load_ledger(saved):
    rows = []
    if not isinstance(saved, list):
        return rows
    for entry in saved:
        if not isinstance(entry, list) or len(entry) != len(LEDGER_FIELDS):
            continue
        row = {}
        ok = True
        for name, value in zip(LEDGER_FIELDS, entry):
            if name == "auto":
                row[name] = bool(value) if isinstance(value, bool) else False
            elif name == "round":
                if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                    ok = False
                    break
                row[name] = value
            else:
                number = _finite_number(value, None)
                if number is None:
                    ok = False
                    break
                row[name] = number
        if ok:
            rows.append(row)
    return rows[-LEDGER_MAX_ENTRIES:]


def _load_civic_state(data):
    """GI-13 / GI-2 / GI-1 / GI-5 / GI-21: every field optional and validated; bad values reset to the default."""
    fit = data.get("perfect_fit")
    region.perfect_fit_streak = 0
    region.best_perfect_fit_streak = 0
    if isinstance(fit, dict) and _small_int(fit.get("best")) and _small_int(fit.get("streak")):
        region.best_perfect_fit_streak = fit["best"]
        region.perfect_fit_streak = min(fit["streak"], fit["best"])
    region.calendar_enabled = False
    region.braced_rounds = []
    region.calendar_log = []
    cal = data.get("calendar")
    if isinstance(cal, dict):
        region.calendar_enabled = cal.get("enabled") is True
        braced = cal.get("braced")
        if isinstance(braced, list):
            region.braced_rounds = sorted({r for r in braced if _small_int(r, 1) and calendar_event_for_round(r) is not None})
        log = cal.get("log")
        if isinstance(log, list):
            for entry in log:
                if (
                    isinstance(entry, dict) and _small_int(entry.get("round"), 1)
                    and entry.get("kind") in CALENDAR_KINDS and isinstance(entry.get("braced"), bool)
                    and (entry.get("held") is None or isinstance(entry.get("held"), bool))
                ):
                    region.calendar_log.append(
                        {"round": entry["round"], "kind": entry["kind"], "braced": entry["braced"], "held": entry["held"]}
                    )
            region.calendar_log = region.calendar_log[-CALENDAR_LOG_MAX:]
    region.council_picks = []
    picks = data.get("council")
    if isinstance(picks, list):
        for pid in picks:
            program = COUNCIL_BY_ID.get(pid) if isinstance(pid, str) else None
            # a pick is only valid if it is the next tier of its branch, so a hand-edited save cannot skip tiers
            if program is not None and council_next_program(program["branch"], region.council_picks) is program:
                region.council_picks.append(pid)
    region.autopilot = _clean_autopilot(data.get("autopilot"))
    banked = data.get("stars_banked")
    region.stars_banked = banked if _small_int(banked, 1) else None


# ---- I-30: tell the player when a loaded save was only partly readable --------------------------------


# (label, keys, required in every save this version writes, check). A required section that is absent means
# the save is from an older version; one that is present but fails its check was damaged or edited.
LOAD_SECTIONS = [
    ("the round and funds", ["round_number", "funds"], True,
     lambda d: _is_number(d.get("round_number"), 1) and _is_number(d.get("funds"))),
    ("capacity", ["capacity"], True,
     lambda d: isinstance(d.get("capacity"), dict) and all(_is_number(d["capacity"].get(t)) for t in CAPACITY_TYPES)),
    ("arrivals and pressure", ["background_severity", "total_arrivals", "arrivals_log"], True,
     lambda d: _is_number(d.get("background_severity")) and _is_number(d.get("total_arrivals")) and _number_list(d.get("arrivals_log"))),
    ("strain history", ["strain_log"], True, lambda d: _number_list(d.get("strain_log"))),
    ("wellbeing history", ["wellbeing_log"], True, lambda d: _number_list(d.get("wellbeing_log"))),
    ("integration progress", ["integrated_population", "cumulative_services_investment", "cumulative_integration_contribution"], True,
     lambda d: all(_is_number(d.get(k)) for k in ("integrated_population", "cumulative_services_investment", "cumulative_integration_contribution"))),
    ("sub-score history", ["subscore_log"], True,
     lambda d: isinstance(d.get("subscore_log"), list) and all(isinstance(e, dict) for e in d["subscore_log"])),
    ("the round ledger", ["ledger"], False, lambda d: isinstance(d.get("ledger"), list)),
    ("policies", ["policy_level"], False, lambda d: isinstance(d.get("policy_level"), dict)),
    ("the second wave", ["second_wave"], False, lambda d: isinstance(d.get("second_wave"), dict)),
    ("the neighbouring district", ["neighbor"], False, lambda d: isinstance(d.get("neighbor"), dict)),
    ("the Crisis Calendar", ["calendar"], False, lambda d: isinstance(d.get("calendar"), dict)),
    ("the Mayor's Council", ["council"], False, lambda d: isinstance(d.get("council"), list)),
    ("the Budget Autopilot", ["autopilot"], False, lambda d: isinstance(d.get("autopilot"), dict)),
    ("the ROI history", ["roi_log"], False, lambda d: isinstance(d.get("roi_log"), list)),
]


def load_report(data):
    """(restored, reset): labels of the sections of `data` that will load as saved, and of those that will fall
    back to a fresh start (missing from an older save, or present but unreadable)."""
    restored, reset = [], []
    for label, keys, required, check in LOAD_SECTIONS:
        present = any(key in data for key in keys)
        if not present:
            if required:
                reset.append(label)
            continue
        (restored if check(data) else reset).append(label)
    return restored, reset


def _set_load_note(report):
    restored, reset = report
    if not reset:
        runstate.load_note_text = ""
        return
    runstate.load_note_text = (
        "Loaded your save, but part of it was missing or could not be read (an older or damaged save). "
        f"Restored: {', '.join(restored) if restored else 'nothing from the main record'}. "
        f"Started fresh: {', '.join(reset)}."
    )


def render_load_note():
    document.getElementById("load-note-box").hidden = not runstate.load_note_text
    document.getElementById("load-note").innerText = runstate.load_note_text
