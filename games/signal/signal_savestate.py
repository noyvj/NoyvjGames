"""get_state() and load_state(): the save contract with the shared save widget (cleaning and merging a saved dict)."""

import json

import signal_runstate as runstate
from signal_records import (
    _DEFAULT_SETTINGS, _clean_record, _finished, _parse_day_key, achievement_ids_earned, compute_stats,
    evaluate_achievements,
)
from signal_rules import ACHIEVEMENT_IDS, DAILY_MODES, PRESETS, PRESET_ORDER, SCHEMA, _is_int, parse_date
from signal_session import _prune_days, _today


# --------------------------------------------------------------------------
# Save / load (shared/save-widget.js contract)


def _json_copy(value):
    return json.loads(json.dumps(value))


def get_state():
    today = runstate._last_today or _today()
    derived = {}
    for m in DAILY_MODES:
        st = compute_stats(m, "daily", today)
        derived[m] = st
    return {
        "schema": SCHEMA,
        "stats": derived,
        "days": _json_copy(runstate.S["days"]),
        "practice": _json_copy(runstate.S["practice"]),
        "practice_stats": _json_copy(runstate.S["practice_stats"]),
        "settings": dict(runstate.S["settings"]),
        "earned": dict(runstate.S["earned"]),
        "flags": dict(runstate.S["flags"]),
        "onboarding_seen": runstate.S["onboarding_seen"],
        "session": _json_copy(runstate.S["session"]),
        "achievements_earned": achievement_ids_earned(),
    }


def _rank(rec):
    """Ordering key for merging two records of the same puzzle: a daily beats
    an archive replay (so local progress is never overwritten by a remote
    archive replay), finished beats in-progress, a win beats a loss, fewer
    pings beats more. Ties fall back to the canonical JSON so the merge is
    commutative."""
    kind_daily = 1 if rec["kind"] == "daily" else 0
    finished = _finished(rec)
    return (
        kind_daily,
        1 if finished else 0,
        1 if rec["result"] == "won" else 0,
        -rec["pings_used"] if finished else rec["pings_used"],
        json.dumps(rec, sort_keys=True),
    )


def _merge_days(local, incoming):
    merged = dict(local)
    for key, rec in incoming.items():
        if key not in merged or _rank(rec) > _rank(merged[key]):
            merged[key] = rec
    return merged


def _clean_settings(raw):
    out = dict(_DEFAULT_SETTINGS)
    if not isinstance(raw, dict):
        return out
    mode = raw.get("mode")
    if isinstance(mode, str) and mode in DAILY_MODES:
        out["mode"] = mode
    for key in ("assist_shading", "ascii_share", "show_streaks"):
        if isinstance(raw.get(key), bool):
            out[key] = raw[key]
    last = raw.get("last_preset")
    if isinstance(last, str) and last in PRESETS:
        out["last_preset"] = last
    return out


def _clean_practice_stats(raw):
    out = {}
    for key in PRESET_ORDER:
        budget = PRESETS[key]["budget"]
        entry = raw.get(key) if isinstance(raw, dict) else None
        played = won = 0
        hist = [0] * budget
        if isinstance(entry, dict):
            if _is_int(entry.get("played")) and entry["played"] >= 0:
                played = entry["played"]
            if _is_int(entry.get("won")) and 0 <= entry["won"] <= played:
                won = entry["won"]
            h = entry.get("pings_hist")
            if isinstance(h, list) and len(h) == budget and all(_is_int(x) and x >= 0 for x in h):
                hist = list(h)
        out[key] = {"played": played, "won": won, "pings_hist": hist}
    return out


def _clean_earned(raw):
    out = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            if isinstance(key, str) and key in ACHIEVEMENT_IDS and isinstance(value, str) and parse_date(value):
                out[key] = value
    return out


def _clean_days(raw):
    out = {}
    if not isinstance(raw, dict):
        return out
    for key, rec in raw.items():
        parsed = _parse_day_key(key)
        if parsed is None:
            continue
        clean = _clean_record(rec, ("daily", "archive"), expected_mode=parsed[1])
        if clean is not None:
            out[key] = clean
    return out


def _notify_ui():
    """Tell app.js the state changed under it (a save was just loaded)."""
    try:
        import js  # noqa: WPS433
        callback = getattr(js.window, "signalOnStateLoaded", None)
        if callback:
            callback()
    except Exception:  # noqa: BLE001 -- no browser, or the UI is not up yet
        pass


def load_state(data):
    """Merge a saved state in (inverse of get_state). Returns True if the
    data was usable. Junk never raises: bad fields are dropped one by one.
    Days are unioned (never lost), earned achievements are unioned, practice
    counters take the larger value, settings come from the save. Streaks and
    stats are recomputed from `days`, never trusted from the blob."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError:
            return False
    if not isinstance(data, dict):
        return False
    schema = data.get("schema", SCHEMA)
    if not _is_int(schema) or schema < 1 or schema > SCHEMA:
        return False
    runstate.S["days"] = _merge_days(runstate.S["days"], _clean_days(data.get("days")))
    incoming_stats = _clean_practice_stats(data.get("practice_stats"))
    for key in PRESET_ORDER:
        mine, theirs = runstate.S["practice_stats"][key], incoming_stats[key]
        mine["played"] = max(mine["played"], theirs["played"])
        mine["won"] = min(max(mine["won"], theirs["won"]), mine["played"])
        mine["pings_hist"] = [max(a, b) for a, b in zip(mine["pings_hist"], theirs["pings_hist"])]
    if runstate.S["practice"] is None:
        runstate.S["practice"] = _clean_record(data.get("practice"), ("practice",))
    for key, value in _clean_earned(data.get("earned")).items():
        if key not in runstate.S["earned"] or value < runstate.S["earned"][key]:
            runstate.S["earned"][key] = value
    if isinstance(data.get("settings"), dict):
        runstate.S["settings"] = _clean_settings(data["settings"])
    flags = data.get("flags")
    if isinstance(flags, dict) and flags.get("shared") is True:
        runstate.S["flags"]["shared"] = True
    if data.get("onboarding_seen") is True:
        runstate.S["onboarding_seen"] = True
    _prune_days()
    evaluate_achievements()
    _notify_ui()
    return True
