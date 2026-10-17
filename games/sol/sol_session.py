"""Loading a save and starting or leaving a Scarcity Run: things that replace the running game and redraw."""

import json

import challenges

import sol_runstate as runstate
from sol_ghost import _ghost_reload_live, _refresh_ghost_strip, _resolve_scarcity_ghost
from sol_run import _full_render
from sol_savestate import _show_welcome_back_toast, deserialize_state, serialize_state
from sol_scarcity import _scarcity_mean_progress, scarcity_days
from sol_scarcity_panel import update_scarcity_display
from sol_scarcity_run import _scarcity_discard, _scarcity_swap_in, _scarcity_swap_out, scarcity_spec
from sol_util import _today_utc


def get_save_state_json():
    return json.dumps(serialize_state())


def load_save_state_json(json_str):
    _scarcity_discard()
    deserialize_state(json.loads(json_str))
    _ghost_reload_live()
    _full_render()
    _show_welcome_back_toast()
    return True


# SAVE-BUTTON-INTEGRATION.md contract for the shared shared/save-widget.js:
# get_state() returns the same JSON-safe dict as serialize_state() (not a
# string this time — the shared widget does its own JS<->Pyodide dict
# conversion), and load_state() is deserialize_state()'s exact inverse.
# SOL is the reference integration for this contract; save codes created
# under the old bespoke UI keep working, since the dict shape is unchanged.
def get_state():
    if runstate._scarcity is not None:
        # A Scarcity Run is on: the save is the real game as it was when the run began, plus the run records.
        data = json.loads(runstate._scarcity["stash"])
        data.pop("scarcity_days", None)
        if scarcity_days:
            data["scarcity_days"] = {d: dict(r) for d, r in scarcity_days.items()}
        return data
    return serialize_state()


def load_state(data):
    _scarcity_discard()
    deserialize_state(data)
    _ghost_reload_live()
    _full_render()
    _show_welcome_back_toast()
    return True


# --- the run itself ---------------------------------------------------------------------
def start_scarcity_run(date_text, today=None):
    """Starts (or restarts) a day on a copy. Returns True, or False with a reason in `_scarcity_notice`."""
    today = today or _today_utc()
    if today is None or not challenges.playable(date_text, today):
        runstate._scarcity_notice = "That day is not open yet. Any day from 1 October 2026 up to today is."
        return False
    if runstate._scarcity is not None:
        leave_scarcity_run(render=False)
    spec = scarcity_spec(date_text)
    _scarcity_swap_in(spec)
    run = runstate._scarcity
    run["samples"].append(round(_scarcity_mean_progress() * 10))
    run["ghost"], run["ghost_label"] = _resolve_scarcity_ghost(spec)
    runstate._scarcity_selected = date_text
    runstate._scarcity_notice = ""
    _full_render()
    update_scarcity_display(force=True)
    _refresh_ghost_strip()
    return True


def leave_scarcity_run(render=True):
    """Ends the run and restores the real game exactly. Returns True if a run was on."""
    if runstate._scarcity is None:
        return False
    _scarcity_swap_out()
    runstate._scarcity_notice = ""
    if render:
        _full_render()
        update_scarcity_display(force=True)
        _refresh_ghost_strip()
    return True
