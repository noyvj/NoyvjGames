"""Save validation (sanitize_save and its rules) and the per-region save dict and its loader."""

import math

from js import document

from thaw_mechanics import CARBON_BANK_CAP, FRAMINGS
from thaw_rules import ACCEL_HISTORY_MAX, CATEGORIES, CATEGORY_LABEL, POLICY_STANCES, RESCUE_DURATION_ROUNDS


# ===========================================================================
# G-29: friendly corrupt-save recovery. Before a save is applied, every field is checked; a field
# that cannot be read (wrong type, out of range, not finite) is left out so the game keeps its own
# default for it, and a notice names each field that was replaced. The rest of the save loads
# normally, so one bad number never costs the whole save.
# ===========================================================================
FIELD_LABELS = {
    "round_number": "round number", "funds": "funds", "temperature": "temperature",
    "melt_started_round": "round melt started", "counterfactual_temperature": "no-action temperature",
    "temperature_history": "temperature history", "capacity": "units", "strategy_label": "strategy label",
    "dampening_at_melt_start": "dampening when melt began", "rounds_since_tipping_event": "rounds since tipping",
    "tipping_events": "tipping events", "average_acceleration_factor": "average acceleration",
    "acceleration_samples": "acceleration samples", "rescue_used": "rescue used",
    "rescue_rounds_left": "rescue rounds left", "policy_stance": "policy stance",
    "dampening_history": "dampening history", "stabilized_rounds": "steady rounds", "restored_total": "restored warming",
    "best_stable_streak": "best stable streak", "acceleration_history": "acceleration history",
    "just_started_melting": "melt flag", "just_invested_intervention": "investment flag",
    "just_delayed_milestone": "milestone flag", "milestone_delay_announced": "milestone note flag",
    "just_became_critical": "critical flag", "just_preempted_melt": "pre-emptive flag",
}
_REGION_RULES = {
    "round_number": ("int", 1, 1000000),
    "funds": ("num", 0, 1e15),
    "temperature": ("num", -1000, 1e12),
    "melt_started_round": ("intnull", 1, 1000000),
    "counterfactual_temperature": ("num", -1000, 1e15),
    "temperature_history": ("numlist", -1000, 1e15),
    "strategy_label": ("str", 0, 200),
    "dampening_at_melt_start": ("numnull", 0, 1),
    "rounds_since_tipping_event": ("int", 0, 1000000),
    "tipping_events": ("int", 0, 1000000),
    "average_acceleration_factor": ("num", 0, 1e9),
    "acceleration_samples": ("int", 0, 1000000000),
    "rescue_used": ("bool", 0, 0),
    "rescue_rounds_left": ("int", 0, RESCUE_DURATION_ROUNDS),
    "stabilized_rounds": ("int", 0, 100000),
    "restored_total": ("num", 0, 1000000),
    "best_stable_streak": ("int", 0, 100000),
    "acceleration_history": ("list", 0, 0),
    "dampening_history": ("list", 0, 0),
    "just_started_melting": ("bool", 0, 0),
    "just_invested_intervention": ("bool", 0, 0),
    "just_delayed_milestone": ("bool", 0, 0),
    "milestone_delay_announced": ("bool", 0, 0),
    "just_became_critical": ("bool", 0, 0),
    "just_preempted_melt": ("bool", 0, 0),
}
_TOP_RULES = {
    "info_page_open": ("bool", 0, 0, "info panel flag"),
    "worst_case_region_revealed": ("bool", 0, 0, "Region D reveal flag"),
    "preset_used_ever": ("bool", 0, 0, "preset flag"),
    "worst_case_intro_seen": ("bool", 0, 0, "Region D note flag"),
    "science_log": ("list", 0, 0, "scientist's log"),
    "carbon_bank": ("int", 0, CARBON_BANK_CAP, "carbon bank"),
    "balance_bonuses": ("int", 0, 1000000, "balance bonuses"),
    "framing": ("str", 0, 40, "framing"),
    "forecast": ("dict", 0, 0, "forecast record"),
    "routing": ("dict", 0, 0, "convoy record"),
    "long_game": ("bool", 0, 0, "long game flag"),
    "hold_the_line": ("bool", 0, 0, "Hold the Line flag"),
    "run": ("dict", 0, 0, "run result"),
    "undo_used": ("bool", 0, 0, "rewind flag"),
    "hard_mode": ("bool", 0, 0, "hard mode flag"),
    "custom_preset": ("dict", 0, 0, "custom preset"),
    "crates": ("dict", 0, 0, "supply crates"),
}
load_problems = []  # human-readable names of the fields the last load had to replace


def _is_num(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _field_ok(kind, value, lo, hi):
    if kind == "bool":
        return isinstance(value, bool)
    if kind == "int":
        return _is_num(value) and float(value).is_integer() and lo <= value <= hi
    if kind == "intnull":
        return value is None or _field_ok("int", value, lo, hi)
    if kind == "num":
        return _is_num(value) and lo <= value <= hi
    if kind == "numnull":
        return value is None or _field_ok("num", value, lo, hi)
    if kind == "numlist":
        return isinstance(value, list) and len(value) <= 200000 and all(_is_num(v) and lo <= v <= hi for v in value)
    if kind == "str":
        return isinstance(value, str) and lo <= len(value) <= hi
    if kind == "list":
        return isinstance(value, list)
    if kind == "dict":
        return isinstance(value, dict)
    return False


def _clean_region_block(label, block, problems):
    """A copy of one saved region block with unreadable fields removed (and named in `problems`)."""
    if not isinstance(block, dict):
        problems.append(f"Region {label} (the whole block)")
        return None
    clean = dict(block)
    for field, (kind, lo, hi) in _REGION_RULES.items():
        if field in clean and not _field_ok(kind, clean[field], lo, hi):
            problems.append(f"Region {label} {FIELD_LABELS[field]}")
            del clean[field]
    if "policy_stance" in clean and not (isinstance(clean["policy_stance"], str) and clean["policy_stance"] in POLICY_STANCES):
        problems.append(f"Region {label} {FIELD_LABELS['policy_stance']}")
        del clean["policy_stance"]
    if "capacity" in clean:
        capacity = clean["capacity"]
        if not isinstance(capacity, dict):
            problems.append(f"Region {label} {FIELD_LABELS['capacity']}")
            del clean["capacity"]
        else:
            capacity = dict(capacity)
            for category in CATEGORIES:
                if category in capacity and not _field_ok("int", capacity[category], 0, 1000000000):
                    problems.append(f"Region {label} {CATEGORY_LABEL[category]} units")
                    del capacity[category]
            clean["capacity"] = capacity
    return clean


def sanitize_save(data):
    """(clean copy of a save dict, [names of the fields that were replaced by defaults])."""
    problems = []
    clean = dict(data)
    for key, label in (("region", "A"), ("region_b", "B"), ("region_c", "C"), ("region_d", "D")):
        if key in clean:
            block = _clean_region_block(label, clean[key], problems)
            if block is None:
                del clean[key]
            else:
                clean[key] = block
    for key, (kind, lo, hi, label) in _TOP_RULES.items():
        if key in clean and not _field_ok(kind, clean[key], lo, hi):
            problems.append(label)
            del clean[key]
    if "framing" in clean and clean["framing"] not in FRAMINGS:
        problems.append("framing")
        del clean["framing"]
    return clean, problems


def load_notice_text():
    if not load_problems:
        return ""
    shown = load_problems[:8]
    more = f" and {len(load_problems) - 8} more" if len(load_problems) > 8 else ""
    return (
        f"Part of this save could not be read, so {len(load_problems)} "
        f"field{'s were' if len(load_problems) != 1 else ' was'} loaded with default values instead: "
        f"{', '.join(shown)}{more}. Everything else loaded normally, and nothing in the save itself was changed."
    )


def render_load_notice():
    notice = document.getElementById("load-notice")
    text = load_notice_text()
    notice.hidden = not text
    document.getElementById("load-notice-text").innerText = text


# --- Save system (SAVE-BUTTON-INTEGRATION.md contract) ---
# Bridges to the shared shared/save-widget.js: get_state() returns a
# plain JSON-safe dict (the widget does its own JS<->Pyodide dict
# conversion), and load_state() is its exact inverse. SOL is the
# reference integration for this contract. Thaw tracks THREE independent
# regions (the original primary region, plus Pass 2's Region B and
# Region C) — all three must round-trip, not just the primary one.


def _region_state_dict(r):
    """One RegionState's fields as a plain, JSON-safe dict. `capacity`
    and `temperature_history` are copied here (dict()/list()), not just
    referenced, so continued play after taking a snapshot can't silently
    mutate a saved copy — same reasoning as SOL's serialize_state()
    docstring."""
    data = {
        "round_number": r.round_number,
        "funds": r.funds,
        "capacity": dict(r.capacity),
        "temperature": r.temperature,
        "melt_started_round": r.melt_started_round,
        "just_started_melting": r.just_started_melting,
        "counterfactual_temperature": r.counterfactual_temperature,
        "temperature_history": list(r.temperature_history),
        "just_invested_intervention": r.just_invested_intervention,
        "strategy_label": r.strategy_label,
        "dampening_at_melt_start": r.dampening_at_melt_start,
        "just_delayed_milestone": r.just_delayed_milestone,
        "milestone_delay_announced": r.milestone_delay_announced,
        "just_became_critical": r.just_became_critical,
        "rounds_since_tipping_event": r.rounds_since_tipping_event,
        "tipping_events": r.tipping_events,
        "just_preempted_melt": r.just_preempted_melt,
        # G11: the community-comparison metric -- see RegionState.__init__'s
        # comment on why this rides get_state() as a plain running average
        # rather than being recomputed from temperature_history.
        "average_acceleration_factor": r.average_acceleration_factor,
        "acceleration_samples": r.acceleration_samples,
    }
    # G21: written only once a rescue has actually been used, so a save
    # from a region that never needed one is byte-identical to before.
    if r.rescue_used:
        data["rescue_used"] = True
        data["rescue_rounds_left"] = r.rescue_rounds_left
    # G13: only the key is saved; the dampening it grants is re-derived on
    # load, so retuning a stance can never leave a stale number in a save.
    if r.policy_stance is not None:
        data["policy_stance"] = r.policy_stance
    # G15: likewise written only once restoration has actually started.
    if r.stabilized_rounds or r.restored_total:
        data["stabilized_rounds"] = r.stabilized_rounds
        data["restored_total"] = r.restored_total
    # GG-13 / G-24: written only once there is something to write.
    if r.best_stable_streak:
        data["best_stable_streak"] = r.best_stable_streak
    if r.acceleration_history:
        data["acceleration_history"] = list(r.acceleration_history)
    # G-16: written only once a round has been played.
    if r.dampening_history:
        data["dampening_history"] = list(r.dampening_history)
    return data


def _apply_region_state(r, data):
    """The exact inverse of _region_state_dict() — restores one
    RegionState's fields in place from a previously-saved dict.

    Every field is read with `.get(key, <current live value>)` rather than
    a bare `data["key"]` — a save may be a hand-edited/truncated payload,
    or simply come from a different build of this game with a different
    field set (an older save from before some field existed, or a newer
    one this build doesn't know about yet). A bare index raised a
    KeyError partway through these assignments, leaving some fields
    already overwritten from the save and others still at their pre-load
    values — worse than either a clean load or leaving the field alone.
    Falling back to the field's current value keeps a partial/malformed
    save loading everything it safely can instead of crashing outright.

    `capacity` is merged into the live dict key-by-key rather than
    replaced wholesale, same reasoning as above but at the nested-dict
    level: a save whose capacity is missing a category (an older save
    format from before that category existed, or a hand-edited/corrupted
    payload) must not wipe that category's key out of the live dict
    entirely — invest(), feedback_dampening_fraction() and render() all do
    unconditional capacity["monitor"]-style key access, so a missing key
    would crash the game on the very next call, including the re-render
    load_state() itself triggers. Same fix shape as SOL's planet_state and
    Continuum's resources/allocation/buildings dicts. Also mirrors Tide's
    load_state(), which already used this exact `.get()` pattern
    throughout (see that file's REVIEW(patterns) comment flagging Thaw,
    among others, as still doing bare data["key"] indexing)."""
    r.round_number = data.get("round_number", r.round_number)
    r.funds = data.get("funds", r.funds)
    saved_capacity = data.get("capacity")
    if isinstance(saved_capacity, dict):
        for category in CATEGORIES:
            if category in saved_capacity:
                r.capacity[category] = saved_capacity[category]
    r.temperature = data.get("temperature", r.temperature)
    r.melt_started_round = data.get("melt_started_round", r.melt_started_round)
    r.just_started_melting = data.get("just_started_melting", r.just_started_melting)
    r.counterfactual_temperature = data.get(
        "counterfactual_temperature", r.counterfactual_temperature
    )
    saved_history = data.get("temperature_history")
    if isinstance(saved_history, list):
        r.temperature_history = list(saved_history)
    r.just_invested_intervention = data.get(
        "just_invested_intervention", r.just_invested_intervention
    )
    r.strategy_label = data.get("strategy_label", r.strategy_label)
    r.dampening_at_melt_start = data.get("dampening_at_melt_start", r.dampening_at_melt_start)
    r.just_delayed_milestone = data.get("just_delayed_milestone", r.just_delayed_milestone)
    r.milestone_delay_announced = data.get(
        "milestone_delay_announced", r.milestone_delay_announced
    )
    r.just_became_critical = data.get("just_became_critical", r.just_became_critical)
    r.rounds_since_tipping_event = data.get(
        "rounds_since_tipping_event", r.rounds_since_tipping_event
    )
    r.tipping_events = data.get("tipping_events", r.tipping_events)
    r.just_preempted_melt = data.get("just_preempted_melt", r.just_preempted_melt)
    r.average_acceleration_factor = data.get(
        "average_acceleration_factor", r.average_acceleration_factor
    )
    r.acceleration_samples = data.get("acceleration_samples", r.acceleration_samples)
    # G21: validated -- a bool and an int in range, else the safe default.
    saved_rescue_used = data.get("rescue_used")
    if isinstance(saved_rescue_used, bool):
        r.rescue_used = saved_rescue_used
    saved_rescue_rounds = data.get("rescue_rounds_left")
    if (
        isinstance(saved_rescue_rounds, int)
        and not isinstance(saved_rescue_rounds, bool)
        and 0 <= saved_rescue_rounds <= RESCUE_DURATION_ROUNDS
    ):
        r.rescue_rounds_left = saved_rescue_rounds
    if r.rescue_rounds_left > 0:
        r.rescue_used = True
    saved_streak = data.get("stabilized_rounds")
    if isinstance(saved_streak, int) and not isinstance(saved_streak, bool) and 0 <= saved_streak <= 100000:
        r.stabilized_rounds = saved_streak
    else:
        r.stabilized_rounds = 0
    saved_restored = data.get("restored_total")
    if (
        isinstance(saved_restored, (int, float))
        and not isinstance(saved_restored, bool)
        and math.isfinite(saved_restored)
        and 0 <= saved_restored <= 1000000
    ):
        r.restored_total = float(saved_restored)
    else:
        r.restored_total = 0.0
    saved_best = data.get("best_stable_streak")
    if isinstance(saved_best, int) and not isinstance(saved_best, bool) and 0 <= saved_best <= 100000:
        r.best_stable_streak = saved_best
    else:
        r.best_stable_streak = 0
    r.best_stable_streak = max(r.best_stable_streak, r.rounds_since_tipping_event)
    saved_accel = data.get("acceleration_history")
    if isinstance(saved_accel, list):
        r.acceleration_history = [
            float(v) for v in saved_accel
            if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and 0 <= v <= 1000000
        ][-ACCEL_HISTORY_MAX:]
    else:
        r.acceleration_history = []
    r.just_pulled_back = False
    saved_damp = data.get("dampening_history")
    if (
        isinstance(saved_damp, list)
        and len(saved_damp) <= len(r.temperature_history)
        and all(_is_num(v) and 0 <= v <= 1 for v in saved_damp)
    ):
        r.dampening_history = [float(v) for v in saved_damp]
    else:
        r.dampening_history = []
    saved_stance = data.get("policy_stance")
    if isinstance(saved_stance, str) and saved_stance in POLICY_STANCES:
        r.policy_stance = saved_stance
        r.policy_dampening = POLICY_STANCES[saved_stance]["dampening"]
    else:
        r.policy_stance = None
        r.policy_dampening = 0.0
