"""Lighthouse -- the engine's single entry point (the Signal and Lexis pattern).

The view (app.js) never reads engine objects: it sends one JSON string to `handle` and draws the JSON that comes
back. `get_state()` / `load_state()` are the shared save widget's contract (planning/SAVE-BUTTON-INTEGRATION.md).
There is no DOM here and no clock: the page calls `step` at whatever pace it likes (or not at all, when paused).

Phases of a night: evening (set the plan) -> night (ticks) -> morning (the report) -> day (five tasks) -> the
next evening. After the last night of the first year there is a year-end screen, then the light runs on in
endless mode.

Actions (every request is {"action": ..., ...}; every answer is the whole view plus "ok" and "message"):
  open                         the current view
  new_game {seed, quiet}       a fresh run (lifetime meta is kept)
  abandon {seed}               same as new_game: give up this run
  reset {seed}                 wipe everything, meta included
  plan {levels, tasks, ration, focus}   edit tonight's plan (any phase but yearend)
  start_night | step {n}       light the lamp | run n ticks (stops at dawn)
  level {level} | wind | tend | patch {part}   the keeper's hands during the night
  end_morning | continue | end_day             move on
  day {task, part, id}         repair | rest | tidy | beachcomb | garden | rescue
  upgrade {id} | order {order} spend salvage | set the next boat's crates
  settings {eerie}             display choices the engine must know about (never saved)
"""

import json

import achievements
import data
import day
import sim
import story
import view
from state import Keep

keep = Keep(1)
settings = {"eerie": True}


def _fresh_seed(request):
    seed = request.get("seed")
    if isinstance(seed, bool) or not isinstance(seed, (int, float)) or seed != seed:
        return 1
    return int(seed) % (2 ** 31 - 1)


def _begin_run(seed, quiet, keep_meta=True):
    global keep
    old_meta = keep.meta
    keep = Keep(seed)
    if keep_meta:
        keep.meta = old_meta
    keep.quiet = bool(quiet)
    sim.to_evening(keep)
    achievements.refresh(keep)


def _start():
    sim.to_evening(keep)


def _plan(request):
    if keep.phase == "yearend":
        return False, "Decide about the light first."
    levels = request.get("levels")
    if levels is not None:
        if not (isinstance(levels, list) and len(levels) == 3 and all(isinstance(x, str) and x in data.LEVELS for x in levels)):
            return False, "A night plan sets a lamp level for each of dusk, deep night and dawn."
        keep.levels = [data.LEVELS.index(x) for x in levels]
    tasks = request.get("tasks")
    if tasks is not None:
        if not isinstance(tasks, dict):
            return False, "Tasks must be on or off."
        for name in ("wind", "watch", "repair"):
            if name in tasks:
                keep.tasks[name] = tasks[name] is True
    if "ration" in request:
        r = request.get("ration")
        if isinstance(r, bool) or not isinstance(r, (int, float)) or r < 0:
            return False, "The ration must be a number of oil measures, or 0 for no ration."
        keep.ration = min(400, int(r))
    if "focus" in request:
        f = request.get("focus")
        if f != "worst" and f not in data.PARTS:
            return False, "The keeper can be asked to patch the worst part or one named part."
        keep.focus = f
    return True, ""


def _day_task(request):
    task = request.get("task")
    if task == "repair":
        return day.repair(keep, request.get("part"))
    if task == "rescue":
        return day.rescue(keep, request.get("id"))
    simple = {"rest": day.rest, "tidy": day.tidy, "beachcomb": day.beachcomb, "garden": day.garden}
    if task in simple:
        return simple[task](keep)
    return False, "That is not a task."


def _act(action, request):
    """Perform one action. Returns (ok, message)."""
    keep._eerie = settings["eerie"]
    if action == "open":
        return True, ""
    if action in ("new_game", "abandon"):
        _begin_run(_fresh_seed(request), request.get("quiet"))
        return True, ""
    if action == "reset":
        _begin_run(_fresh_seed(request), request.get("quiet"), keep_meta=False)
        return True, ""
    if action == "plan":
        return _plan(request)
    if action == "start_night":
        if sim.begin_night(keep):
            return True, ""
        return False, "The night begins from the evening."
    if action == "step":
        n = request.get("n", 1)
        n = n if isinstance(n, int) and not isinstance(n, bool) else 1
        ran = sim.step(keep, max(0, min(n, 400)))
        if keep.phase == "morning":
            achievements.refresh(keep)
        return True, "" if ran else "The night is not running."
    if action == "level":
        lv = request.get("level")
        if lv in data.LEVELS and sim.set_level(keep, data.LEVELS.index(lv)):
            return True, ""
        return False, "The lamp can only be changed in the night."
    if action == "wind":
        return (True, "") if sim.wind_now(keep) else (False, "The clockwork is already wound.")
    if action == "tend":
        return (True, "") if sim.tend_now(keep) else (False, "Nothing needs your hands right now.")
    if action == "patch":
        return (True, "") if sim.patch_now(keep, request.get("part")) else (False, "You cannot patch that now (is it sound, and have you the supplies?).")
    if action == "end_morning":
        return (True, "") if day.end_morning(keep) else (False, "There is no morning to leave.")
    if action == "continue":
        return (True, "") if day.continue_endless(keep) else (False, "The year is not over yet.")
    if action == "end_day":
        ok = day.end_day(keep)
        return (True, "") if ok else (False, "The day is not over.")
    if action == "day":
        return _day_task(request)
    if action == "upgrade":
        return day.buy_upgrade(keep, request.get("id"))
    if action == "order":
        return day.set_order(keep, request.get("order"))
    if action == "read_letter":
        return story.read_letter(keep, request.get("id"))
    if action == "reply":
        return story.reply(keep, request.get("id"), request.get("reply"))
    if action == "settings":
        if "eerie" in request:
            settings["eerie"] = request.get("eerie") is not False
        return True, ""
    return None, "Unknown action"


def handle(request_json):
    try:
        request = json.loads(request_json) if isinstance(request_json, str) else request_json
        if not isinstance(request, dict):
            raise ValueError("a request is an object")
        action = request.get("action", "open")
        ok, message = _act(action, request)
        if ok is None:
            return json.dumps({"error": message})
        out = view.build(keep, settings)
        out["ok"] = bool(ok)
        out["message"] = message
        achievements.refresh(keep)
        out["achievements"] = achievements.view(keep)
        return json.dumps(out)
    except Exception as exc:  # the view must never see an engine fault as anything but a message
        return json.dumps({"error": "%s: %s" % (type(exc).__name__, exc)})


# ---- the save widget's contract -----------------------------------------------------------------------------
def get_state():
    data_out = keep.to_dict()
    # A write-only projection for the hub's achievements dashboard, recomputed here, never read back.
    data_out["achievements_earned"] = achievements.earned_ids(keep)
    return data_out


def load_state(data_in):
    """Replace the run with a saved one. Junk never raises: a field that does not fit keeps its default."""
    global keep
    try:
        keep = Keep.from_dict(data_in)
        if keep.phase == "morning" and keep.report is None:
            keep.phase = "evening"
            sim.to_evening(keep)
        achievements.refresh(keep)
    except Exception:  # noqa: BLE001 -- a bad save never blocks play
        keep = Keep(1)
        sim.to_evening(keep)
    _refresh_view()
    return True


def copy_result_fields():
    """The save widget's one-line summary and the shared Copy result button."""
    m = keep.meta
    return {
        "game": "Lighthouse",
        "score": "Night %d" % keep.night,
        "stats": [
            {"n": m["ships_passed"], "one": "ship passed safely", "many": "ships passed safely"},
            {"n": m["nights_kept"], "one": "night kept", "many": "nights kept"},
        ],
    }


def _refresh_view():
    """Ask the page to redraw after a save is loaded (the save widget calls load_state directly and knows nothing
    about this game's view). Under plain CPython there is no page, so this is a no-op."""
    try:
        import js  # noqa: WPS433
        refresh = getattr(js.window, "lighthouseRefresh", None)
        if refresh is not None:
            refresh()
    except Exception:  # noqa: BLE001
        pass


sim.to_evening(keep)
