"""The ghost of the best charter (Z-3e5): recording, banking, comparison and the note under the ledger."""

import copy

import ghost as ghost_lib
from js import document

import trade_runstate as runstate


# ---------------------------------------------------------------------------
# Z-3e5 -- the ghost of your best charter (shared/ghost.py).
# Measure: the highest credit balance reached so far this charter (`max_profit_ever`, which never dips when you buy
# something), one number per tick, recorded by ghost.Recorder from the first tick of a charter until the endgame is
# reached (the path to the endgame is the ghost's whole length). Renewing the charter keeps that path as the best one
# for its mode ("standard" or "hard") when it reached the endgame in FEWER ticks than the stored best (a tie keeps the
# older one). While the next charter runs, #ghost-note says in words whether you are ahead of it; once the endgame is
# reached it compares the two times. Words only: Trade Empire has no chart for this. Nothing about the economy changes.
# Saved only once there is something to save, under "ghost": {"best": {mode: {"ticks", "trace"}}, "live": {...}}; the
# live path travels with the save so a reload in the middle of a charter does not lose it, every trace is cleaned
# through ghost.load and every number is checked on load. A charter the ghost cannot fairly describe is never kept: one
# joined part-way (an older save with no live path), one that used Blackout or any other tainting at any tick.
# The Settings checkbox "Show the ghost of my best charter" (settings.js adds `.ghost-off` to <html>) hides the note.
# ---------------------------------------------------------------------------
GHOST_MODES = ("standard", "hard")
GHOST_MIN_TICKS = 30        # a shorter charter is never kept
GHOST_NOTE_EVERY = 20       # ticks between two refreshes of the note, so a screen reader is not chatty
GHOST_STRIDE_MAX = 1 << 20
_ghost_rec = ghost_lib.Recorder()
_ghost_state = {"tainted": False, "endgame": None, "shown": None}   # endgame: the tick count when it was reached
ghost_best = {}             # mode -> {"ticks": int, "trace": shared trace}


def _ghost_mode():
    return "hard" if runstate.hard_charter_active else "standard"


def _ghost_on():
    """The Settings checkbox (settings.js adds `.ghost-off` to <html>); on when there is no page to ask."""
    try:
        return not document.documentElement.classList.contains("ghost-off")
    except Exception:
        return True


def _ghost_reset_live():
    _ghost_rec.reset()
    _ghost_state.update(tainted=False, endgame=None, shown=None)


def _ghost_record_tick():
    """Called from tick(): one number per tick until the endgame, never in the sandbox."""
    if runstate.sandbox_active or runstate.chain_active is not None or _ghost_state["tainted"] or _ghost_state["endgame"] is not None:
        return
    if _ghost_rec.turns == 0 and runstate.total_sales_count > 0:
        _ghost_state["tainted"] = True      # joined part-way (a save from before the ghost): the path would not start at the start
        return
    if runstate.blackout_enabled:
        _ghost_state["tainted"] = True      # Blackout is a different game; the charter is not comparable
        return
    _ghost_rec.record(runstate.max_profit_ever)
    if runstate.endgame_reached:
        _ghost_state["endgame"] = _ghost_rec.turns


def _ghost_bank():
    """Keep the charter that is about to be renewed as the ghost for its mode when it reached the endgame sooner than
    the stored best. Returns True when it was kept."""
    ticks = _ghost_state["endgame"]
    if _ghost_state["tainted"] or ticks is None or ticks < GHOST_MIN_TICKS or ticks != _ghost_rec.turns:
        return False
    trace = _ghost_rec.trace("best charter")
    if trace is None:
        return False
    mode = _ghost_mode()
    old = ghost_best.get(mode)
    if old is not None and ticks >= old["ticks"]:
        return False
    ghost_best[mode] = {"ticks": ticks, "trace": trace}
    return True


def _ghost_for_save():
    out = {}
    if ghost_best:
        out["best"] = {mode: {"ticks": entry["ticks"], "trace": copy.deepcopy(entry["trace"])} for mode, entry in ghost_best.items()}
    if _ghost_state["tainted"]:
        out["live"] = {"tainted": True}
    elif _ghost_rec.turns:
        live = {"turns": _ghost_rec.turns, "stride": _ghost_rec.stride, "values": list(_ghost_rec.values)}
        if _ghost_state["endgame"] is not None:
            live["endgame"] = _ghost_state["endgame"]
        out["live"] = live
    return out


def ghost_result():
    """The shared comparison (the same keys as ghost.compare) between this charter now and the stored best path for
    its mode, or None when there is no ghost or no live path. Built from ghost.value_at because the recorder thins the
    live path (so a full per-tick list is never kept); a test pins that it agrees with ghost.compare on a full list."""
    entry = ghost_best.get(_ghost_mode())
    turn = _ghost_rec.turns
    if entry is None or turn < 1 or _ghost_state["tainted"]:
        return None
    mine = ghost_lib.clean_number(runstate.max_profit_ever)
    if mine is None:
        return None
    ghost = ghost_lib.value_at(entry["trace"], turn)
    if ghost is None:
        return {"turn": turn, "live": mine, "ghost": None, "gap": None, "status": "ended", "lead": 0, "best_turn": None, "best_gap": 0}
    gap = round(mine - ghost, 2)
    lead = abs(gap)
    status = "level" if lead < ghost_lib.LEVEL_EPSILON else ("ahead" if gap > 0 else "behind")
    return {"turn": turn, "live": mine, "ghost": ghost, "gap": gap, "status": status, "lead": 0 if status == "level" else lead,
            "best_turn": None, "best_gap": 0}


def ghost_note_text():
    """The words under the ledger: the shared ghost sentence while racing, a plain comparison once the endgame is
    reached, or one plain line saying what the ghost is. '' when the ghost is off for this moment (sandbox, Chain Builder)."""
    if runstate.sandbox_active or runstate.chain_active is not None:
        return ""
    mode = _ghost_mode()
    entry = ghost_best.get(mode)
    kind = "harder " if mode == "hard" else ""
    if _ghost_state["tainted"]:
        return f"Ghost: this {kind}charter is not compared with your best, because it started part-way or used Blackout."
    if entry is None:
        return (f"Ghost: when you renew the charter after reaching the endgame, this {kind}charter's credits are kept here as a "
                f"faint path to race next time, one number per tick (kept only if it took at least {GHOST_MIN_TICKS} ticks).")
    ticks = _ghost_state["endgame"]
    if ticks is not None:
        diff = entry["ticks"] - ticks
        if diff > 0:
            how = f"{diff} tick{'' if diff == 1 else 's'} sooner than"
        elif diff < 0:
            how = f"{-diff} tick{'' if diff == -1 else 's'} after"
        else:
            how = "the same tick as"
        return f"Ghost: you reached the endgame at tick {ticks}, {how} your best {kind}charter (tick {entry['ticks']})."
    if _ghost_rec.turns == 0:
        return (f"Ghost: your best {kind}charter reached the endgame at tick {entry['ticks']}. "
                "This charter is compared with its credits every tick.")
    result = ghost_result()
    if result is None:
        return ""
    if result["status"] == "ended":
        return f"Ghost: your best {kind}charter had reached the endgame by tick {entry['ticks']}; this one is still on its way."
    text = ghost_lib.summary(result, label=f"your best {kind}charter", unit=" credits")
    return "Ghost: " + text[len("ghost: "):].replace(" at turn ", " at tick ") + "."


def render_ghost():
    """Fill #ghost-note, refreshed every GHOST_NOTE_EVERY ticks and whenever what it says changes kind."""
    note = document.getElementById("ghost-note")
    if note is None:
        return
    on = _ghost_on() and not runstate.sandbox_active and runstate.chain_active is None
    key = (on, _ghost_mode(), _ghost_rec.turns // GHOST_NOTE_EVERY, _ghost_state["endgame"], _ghost_state["tainted"],
           tuple(sorted((m, e["ticks"]) for m, e in ghost_best.items())))
    if key == _ghost_state["shown"]:
        return
    _ghost_state["shown"] = key
    text = ghost_note_text() if on else ""
    note.innerText = text
    note.hidden = not text
