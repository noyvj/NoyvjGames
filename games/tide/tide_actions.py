"""Actions that replace the running game and redraw: new run, daily start, rewind, autosave restore."""

import copy
import json

import tide_runstate as runstate
from tide_almanac import almanac_resync
from tide_bridge import _write_local_storage_item
from tide_chrome import announce
from tide_coastline import _resync_previous_flooded_rows
from tide_daily import DAILY_EARLIEST, _daily_ui, daily_plan, daily_plan_text, daily_today
from tide_flavour import _delta_open, _quip
from tide_loading import load_state
from tide_model_season import SettlementState
from tide_renderer import render
from tide_rules import WORKSHOP_DEFAULTS
from tide_savestate import get_state
from tide_seasonflow import _last_action_at, _rewind_snapshot, can_rewind
from tide_workshop import (
    AUTOSAVE_KEY, AUTOSAVE_MAX_BYTES, AUTOSAVE_SLOTS, _autosave_info, clean_workshop_value, load_autosaves,
)


def _install_state(fresh):
    """Swaps in a fresh settlement and resets the per-run helpers (shared by Workshop runs and Daily Tide)."""
    runstate.state = fresh
    _rewind_snapshot[0] = None
    _last_action_at[0] = None
    _quip.update({"text": "", "last": ""})
    _delta_open["kind"] = ""
    _resync_previous_flooded_rows()
    almanac_resync()


def start_daily(date_text):
    """Starts the Daily Tide for a date (today or any past day). The old run is replaced: use the save widget first."""
    plan = daily_plan(date_text)
    if plan is None:
        _daily_ui["message"] = f"Pick a date from {DAILY_EARLIEST} up to today ({daily_today()})."
        return False
    fresh = SettlementState()
    fresh.sea_scenario = plan["scenario"]
    fresh.set_coastline(plan["coast"])
    fresh.storm_mode = True
    fresh.daily = {"date": plan["date"], "seed": plan["seed"], "storms": list(plan["storms"]), "done": False}
    _install_state(fresh)
    _daily_ui["message"] = f"Started the daily for {plan['date']}. {daily_plan_text(plan)}"
    _daily_ui["confirm_date"] = ""
    render()
    return True


def take_rewind_snapshot():
    _rewind_snapshot[0] = copy.deepcopy(get_state())


def rewind_season():
    """Retracts the last Advance click (one charge per run) and marks the run, so records stay honest."""
    if not can_rewind():
        return False
    snapshot = _rewind_snapshot[0]
    _rewind_snapshot[0] = None
    load_state(snapshot)
    runstate.state.rewind_used = True
    runstate.state._log_ticker("\U0001FA96 Rewound the last advance. The run is marked with a tin hat.")
    runstate.state._chronicle_event("The harbour council turned back the clock once.")
    announce("Rewound the last Advance Season. This run now carries a tin hat.")
    render()
    return True


def record_autosave():
    """Keeps the last few per-season states (called after a season resolves). Returns True when one was stored."""
    entry = {"season": runstate.state.season, "funds": round(runstate.state.funds, 1), "state": get_state()}
    encoded = json.dumps(entry)
    if len(encoded) > AUTOSAVE_MAX_BYTES:
        return False
    slots = [s for s in load_autosaves() if s["season"] != entry["season"]] + [entry]
    _write_local_storage_item(AUTOSAVE_KEY, json.dumps(slots[-AUTOSAVE_SLOTS:]))
    return True


def restore_autosave(index):
    slots = load_autosaves()
    if not 0 <= index < len(slots):
        return False
    ok = load_state(copy.deepcopy(slots[index]["state"]))
    if ok:
        _autosave_info["load_failed"] = False
        runstate.state._log_ticker(f"Restored the autosave from Season {slots[index]['season']}.")
        render()
    return ok


def start_new_run(values):
    """Starts a fresh settlement with these Workshop values (the old run is not saved: use the save widget first)."""
    fresh = SettlementState()
    fresh.workshop = {k: clean_workshop_value(k, values.get(k, WORKSHOP_DEFAULTS[k])) for k in WORKSHOP_DEFAULTS}
    fresh.funds = fresh.workshop["funds"]
    fresh.max_funds_ever = fresh.funds
    _install_state(fresh)
    render()
    return True
