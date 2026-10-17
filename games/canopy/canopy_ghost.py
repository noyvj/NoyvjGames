"""The best-session ghost (Z-3e): recording, banking and comparison."""

import json

import ghost as ghost_lib

import canopy_runstate as runstate
from canopy_helpers import _read_local_storage_item, _write_local_storage_item
from canopy_rules import SCENARIO_NONE, lab_active
from canopy_valuation import layout_active
from canopy_worldvars import CHALLENGE_NONE, GHOST_LIVE_CAP, _ghost_live, _ghost_state


# Z-3e: the ghost of your best session (shared/ghost.py) ----------------------------------------------------------
# One number per tick: the standing forest value. When a session ends (Reset Session, or any setting that starts a new
# forest) and it ran at least GHOST_MIN_TICKS ticks, its trace is kept per device (localStorage, like the personal best
# and lifetime totals; the key exists only once a ghost does) when its highest standing value is at least as high as the
# stored one for the same settings. The Timeline chart (standing value) then draws it as a faint dashed line and
# `#ghost-note` says in the shared wording whether you are ahead of it. Challenges, levels, Expeditions, scenarios, custom
# layouts and the Forest Lab are left out (their forests are not comparable). The ghost never changes any number.
GHOST_STORAGE_KEY = "canopy_ghost_v1"
GHOST_PREF_KEY = "canopy_ghost_on"
GHOST_MIN_TICKS = 30
GHOST_MAX_MODES = 24
GHOST_LABEL = "your best session"


def ghost_mode_key():
    """The settings a session must share to be compared ("normal:normal:normal" = difficulty:grid size:request pace),
    or None when this session is not comparable."""
    if (lab_active() or layout_active() or runstate.current_challenge != CHALLENGE_NONE or runstate.current_scenario != SCENARIO_NONE
            or runstate.current_level is not None or runstate.current_expedition is not None):
        return None
    return f"{runstate.current_difficulty}:{runstate.current_grid_size}:{runstate.current_pace}"


def _valid_ghost_key(key):
    return (isinstance(key, str) and len(key) <= 40 and key.count(":") == 2
            and all(part and part.replace("_", "").replace("-", "").isalnum() for part in key.split(":")))


def load_ghosts():
    """The stored best sessions, {mode key: {"score", "trace"}}, every entry cleaned through ghost.load; anything
    unreadable, over-long or hand-edited is dropped (no ghost, nothing breaks)."""
    raw = _read_local_storage_item(GHOST_STORAGE_KEY)
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    out = {}
    if not isinstance(data, dict):
        return out
    for key, item in list(data.items())[:GHOST_MAX_MODES]:
        if not _valid_ghost_key(key) or not isinstance(item, dict):
            continue
        trace = ghost_lib.load(item.get("trace"))
        score = ghost_lib.clean_number(item.get("score"))
        if trace is not None and score is not None and trace["turns"] <= GHOST_LIVE_CAP:
            out[key] = {"score": score, "trace": trace}
    return out


def ghost_entry():
    key = ghost_mode_key()
    return None if key is None else load_ghosts().get(key)


def _reset_ghost_session():
    _ghost_live.clear()
    _ghost_state["peak"] = 0.0
    _ghost_state["tainted"] = False


def _record_ghost_tick(value):
    if ghost_mode_key() is None:
        _ghost_state["tainted"] = True   # a session that was ever not comparable is never kept
        return
    number = ghost_lib.clean_number(value)
    if number is None or len(_ghost_live) >= GHOST_LIVE_CAP:
        return
    _ghost_live.append(number)
    _ghost_state["peak"] = max(_ghost_state["peak"], number)


def _bank_ghost():
    """Keep the session that is about to end as the ghost for its settings when it is long enough and its highest
    standing value is at least as high as the stored one (the latest wins a tie). Returns True when it was kept."""
    key = ghost_mode_key()
    if key is None or _ghost_state["tainted"] or len(_ghost_live) < GHOST_MIN_TICKS:
        return False
    recorder = ghost_lib.Recorder()
    for value in _ghost_live:
        recorder.record(value)
    trace = recorder.trace("best session")
    peak = ghost_lib.clean_number(_ghost_state["peak"])
    if trace is None or peak is None:
        return False
    ghosts = load_ghosts()
    if key in ghosts and peak < ghosts[key]["score"]:
        return False
    ghosts[key] = {"score": peak, "trace": trace}
    if len(ghosts) > GHOST_MAX_MODES:
        ghosts = dict(list(ghosts.items())[-GHOST_MAX_MODES:])
    _write_local_storage_item(GHOST_STORAGE_KEY, json.dumps(ghosts))
    return True


def ghost_enabled():
    return _read_local_storage_item(GHOST_PREF_KEY) != "0"


def ghost_result():
    """ghost.compare for this session so far against the stored ghost, or None."""
    entry = ghost_entry()
    if entry is None or not _ghost_live:
        return None
    return ghost_lib.compare(_ghost_live, entry["trace"])


def _rounded_result(result, digits):
    """A ghost.compare result with its lead rounded the way the game shows its numbers; under half a unit is level."""
    if result is None or result["status"] not in ("ahead", "behind"):
        return result
    lead = round(result["lead"], digits)
    return dict(result, status="level", lead=0) if lead == 0 else dict(result, lead=lead)


def ghost_note_text():
    """The sentence under the timeline chart: the shared ghost wording, or a plain reason there is none."""
    if ghost_mode_key() is None:
        return "Ghost: not kept for challenges, levels, expeditions, scenarios, custom layouts or the Forest Lab, because those forests are not comparable."
    entry = ghost_entry()
    if entry is None:
        return (f"Ghost: when you start a new forest after a session of {GHOST_MIN_TICKS} ticks or more, its standing value "
                "is kept here as a faint line to race next time, one number per tick.")
    if not _ghost_live:
        return (f"Ghost: your best session on these settings peaked at {ghost_lib.format_number(entry['score'])} standing value "
                f"over {entry['trace']['turns']} ticks. This session is compared with it every tick.")
    return ghost_lib.summary(_rounded_result(ghost_result(), 1), label=GHOST_LABEL).replace("ghost: ", "Ghost: ", 1) + "."


def ghost_chart_points(count):
    """[(index into the chart's last `count` points, ghost value)] for the points the ghost has a number for. Chart point
    i of `count` is session tick `turns - (count - 1 - i)`; points before this session started (a loaded save) get none."""
    entry = ghost_entry()
    if entry is None or not _ghost_live or not ghost_enabled():
        return []
    turns = len(_ghost_live)
    out = []
    for i in range(count):
        session_tick = turns - (count - 1 - i)
        if session_tick < 1:
            continue
        value = ghost_lib.value_at(entry["trace"], session_tick)
        if value is not None:
            out.append((i, value))
    return out
