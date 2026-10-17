"""The session library data: saved runs, validation, picks and the overlay record."""

import json

import tide_runstate as runstate
from tide_bridge import _finite_number, _read_local_storage_item, _write_local_storage_item
from tide_rules import (
    ADAPTATION_TIERS, COASTLINES, COASTLINE_ROWS, DEFAULT_COASTLINE, FISH_DAMAGE_SCALE, LEDGER_LIMIT,
    LIBRARY_CURRENT, LIBRARY_KEY, LIBRARY_LIMIT, LIBRARY_MIN_SEASONS, SEA_SCENARIOS, SETTLEMENT_NAME_MAX,
    TIER_BADGES,
)


# ---- D-2 session library -------------------------------------------------
_ghosts = {}  # D-3: friends' runs loaded from run codes ("g1", "g2", ...): memory only, never saved, never playable


def _clean_series(values):
    if not isinstance(values, list) or not values:
        return None
    out = []
    for v in values[-LEDGER_LIMIT:]:
        if not _finite_number(v, 0, 1):
            return None
        out.append(round(float(v), 3))
    return out


def _validate_session_record(item):
    if not isinstance(item, dict):
        return None
    rid, name = item.get("id"), item.get("name")
    seasons, rows_dry, tier = item.get("seasons"), item.get("rows_dry"), item.get("tier")
    acidity, fish = _clean_series(item.get("acidity")), _clean_series(item.get("fish"))
    if (
        not isinstance(rid, int) or isinstance(rid, bool) or rid < 1
        or not isinstance(name, str)
        or not isinstance(seasons, int) or isinstance(seasons, bool) or not 0 <= seasons <= 10**6
        or not isinstance(rows_dry, int) or isinstance(rows_dry, bool) or not 0 <= rows_dry <= COASTLINE_ROWS
        or not isinstance(tier, int) or isinstance(tier, bool) or not 0 <= tier < len(ADAPTATION_TIERS)
        or item.get("scenario") not in SEA_SCENARIOS
        or item.get("coast", DEFAULT_COASTLINE) not in COASTLINES
        or item.get("lag") not in ("standard", "hard")
        or not isinstance(item.get("storms"), bool)
        or not _finite_number(item.get("score"), -1e9, 1e9)
        or acidity is None or fish is None
    ):
        return None
    return {
        "id": rid, "name": " ".join(name.split())[:SETTLEMENT_NAME_MAX] or f"Session {rid}",
        "seasons": seasons, "scenario": item["scenario"], "lag": item["lag"], "coast": item.get("coast", DEFAULT_COASTLINE),
        "storms": item["storms"], "score": round(float(item["score"]), 1),
        "rows_dry": rows_dry, "tier": tier, "acidity": acidity, "fish": fish,
    }


def library_records():
    """Saved sessions of this browser, oldest first; damaged entries are skipped."""
    raw = _read_local_storage_item(LIBRARY_KEY)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    records = [r for r in (_validate_session_record(item) for item in data) if r is not None]
    return records[-LIBRARY_LIMIT:]


def _write_library(records):
    _write_local_storage_item(LIBRARY_KEY, json.dumps(records, separators=(",", ":")))


def live_session_record():
    """The running session in the same shape as a saved one."""
    return {
        "id": LIBRARY_CURRENT, "name": runstate.state.display_name(), "seasons": max(0, runstate.state.season - 1),
        "scenario": runstate.state.sea_scenario, "lag": "hard" if runstate.state.hard_lag_mode else "standard", "coast": runstate.state.coastline,
        "storms": bool(runstate.state.storm_mode), "score": round(runstate.state.damage_saved(), 1),
        "rows_dry": runstate.state.rows_dry_count(), "tier": runstate.state.current_tier_index(),
        "acidity": [round(min(1.0, a / FISH_DAMAGE_SCALE), 3) for a in runstate.state.acidity_history][-LEDGER_LIMIT:],
        "fish": [round(v, 3) for v in runstate.state.fish_yield_history][-LEDGER_LIMIT:],
    }


def library_get(session_id):
    if session_id == LIBRARY_CURRENT:
        return live_session_record()
    if str(session_id) in _ghosts:  # D-3: a friend's run loaded from a code (memory only)
        return _ghosts[str(session_id)]
    for record in library_records():
        if str(record["id"]) == str(session_id):
            return record
    return None


def library_overlay_record():
    if not runstate.library_overlay_id:
        return None
    record = library_get(runstate.library_overlay_id)
    if record is None or record["id"] == LIBRARY_CURRENT or not record["acidity"]:
        return None
    return record


def library_summary_text(record):
    lag = "harder lag" if record["lag"] == "hard" else "standard lag"
    storms = ", storm seasons on" if record["storms"] else ""
    coast = record.get("coast", DEFAULT_COASTLINE)
    coast_text = f"{COASTLINES[coast]['label']}, " if coast != DEFAULT_COASTLINE else ""
    return (
        f"{record['name']}: {record['seasons']} seasons, {coast_text}{record['scenario']} sea, {lag}{storms}. "
        f"Damage avoided {record['score']:.0f}, {record['rows_dry']} of {COASTLINE_ROWS} rows dry, "
        f"tier {TIER_BADGES[record['tier']]} {ADAPTATION_TIERS[record['tier']]['name']}."
    )


def library_save_current():
    """D-2: stores the running session (its settings, outcome and the acidity and fish-yield
    series) in this browser. Needs a few seasons so a saved session is worth comparing."""
    if runstate.state.keeps_records_out():  # D-5 / GD-5
        runstate._library_status = "Runs with custom Workshop rules, and Daily Tide runs, are not saved to the library."
        return False
    if runstate.state.season - 1 < LIBRARY_MIN_SEASONS:
        runstate._library_status = f"Play at least {LIBRARY_MIN_SEASONS} seasons before saving a session to the library."
        return False
    records = library_records()
    record_id = max([r["id"] for r in records], default=0) + 1
    record = live_session_record()
    record["id"] = record_id
    record["name"] = runstate.state.settlement_name or f"Session {record_id}"
    records.append(record)
    dropped = max(0, len(records) - LIBRARY_LIMIT)
    records = records[-LIBRARY_LIMIT:]
    _write_library(records)
    if not runstate.library_b:
        runstate.library_b = str(record_id)
    runstate._library_status = (
        f"Saved {record['name']} to the library ({len(records)} of {LIBRARY_LIMIT})."
        + (f" The oldest {dropped} saved session(s) were dropped to stay within the limit." if dropped else "")
    )
    return True


def library_delete(record_id):
    records = library_records()
    kept = [r for r in records if r["id"] != record_id]
    if len(kept) == len(records):
        return False
    _write_library(kept)
    for name in ("library_a", "library_b", "library_overlay_id"):
        if vars(runstate)[name] == str(record_id):
            vars(runstate)[name] = LIBRARY_CURRENT if name == "library_a" else ""
    runstate._library_status = "Removed the saved session."
    return True
