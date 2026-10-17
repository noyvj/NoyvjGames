"""The current puzzle: opening a daily, archive or practice puzzle, the engine boot, the view dict and the response dict."""

import datetime

import signal_runstate as runstate
from signal_puzzle import (
    board_for, daily_puzzle, new_practice_code, parse_practice_code, possible_cells, practice_seed,
    puzzle_for_seed,
)
from signal_records import _day_key, _new_record, _verify_against_puzzle, compute_stats
from signal_rules import (
    ACHIEVEMENTS, DAILY_MODES, EPOCH, MAX_DAYS, PRESETS, PRESET_ORDER, cell_label, parse_date,
    puzzle_number, utc_today,
)
from signal_share import glyph_for, reading_fill, reading_level


# --------------------------------------------------------------------------
# Session / record plumbing


def _today():
    """Today's UTC date, clamped to launch day (before EPOCH the game behaves
    as if it were launch day, so a pre-launch dev build still works)."""
    runstate._last_today = max(utc_today(), EPOCH)
    return runstate._last_today


def _current_record():
    """The stored record for the open puzzle, or None if nothing is stored yet."""
    if runstate._cur is None:
        return None
    if runstate._cur["type"] == "practice":
        rec = runstate.S["practice"]
        return rec if rec is not None and rec.get("code") == runstate._cur["code"] else None
    return runstate.S["days"].get(_day_key(runstate._cur["date"], runstate._cur["mode"]))


def _pending_marks():
    return runstate.S["session"]["marks"]


def _marks():
    rec = _current_record()
    return rec["marks"] if rec is not None else _pending_marks()


def _ensure_record(today_text):
    """Create the stored record on the first ping/commit/give-up, deciding
    daily-vs-archive right then: a puzzle is a daily only if its first ping
    happens on its own UTC date."""
    rec = _current_record()
    if rec is not None:
        return rec
    if runstate._cur["type"] == "practice":
        raise RuntimeError("practice record missing")
    kind = "daily" if runstate._cur["date"] == today_text else "archive"
    rec = _new_record(kind, runstate._cur["mode"])
    rec["marks"] = [list(m) for m in _pending_marks()]
    runstate.S["days"][_day_key(runstate._cur["date"], runstate._cur["mode"])] = rec
    runstate.S["session"]["marks"] = []
    _prune_days()
    return rec


def _prune_days():
    if len(runstate.S["days"]) <= MAX_DAYS:
        return
    keep_open = _day_key(runstate._cur["date"], runstate._cur["mode"]) if runstate._cur and runstate._cur["type"] != "practice" else None
    ordered = sorted(runstate.S["days"], key=lambda k: (k.split(":")[0], k))
    excess = len(runstate.S["days"]) - MAX_DAYS
    for key in ordered:
        if excess <= 0:
            break
        if key == keep_open:
            continue
        del runstate.S["days"][key]
        excess -= 1


def _open_daily(date_text, mode, today_text):
    if not isinstance(mode, str) or mode not in DAILY_MODES:
        return "That mode has no daily puzzle."
    date = parse_date(date_text)
    if date is None:
        return "That is not a valid date."
    if date_text < EPOCH:
        return "There is no puzzle before %s." % EPOCH
    if date_text > today_text:
        return "That puzzle has not been broadcast yet."
    puzzle = daily_puzzle(date_text, mode)
    runstate._cur = {"type": "daily" if date_text == today_text else "archive", "date": date_text, "mode": mode, "puzzle": puzzle}
    rec = runstate.S["days"].get(_day_key(date_text, mode))
    if rec is not None:
        _verify_against_puzzle(rec, puzzle)
    runstate.S["session"] = {"type": runstate._cur["type"], "date": date_text, "mode": mode, "marks": []}
    runstate.S["settings"]["mode"] = mode
    return None


def _open_practice(mode, code, today_text):
    if code is None:
        if not isinstance(mode, str) or mode not in PRESETS:
            return "Unknown preset."
        code = new_practice_code(mode)
    else:
        parsed = parse_practice_code(code)
        if parsed is None:
            return "That practice code is not valid."
        mode, code = parsed
    puzzle = puzzle_for_seed(mode, practice_seed(mode, code))
    runstate._cur = {"type": "practice", "date": None, "mode": mode, "puzzle": puzzle, "code": code}
    rec = runstate.S["practice"]
    if rec is None or rec.get("code") != code:
        runstate.S["practice"] = _new_record("practice", mode, code)
    else:
        _verify_against_puzzle(rec, puzzle)
    runstate.S["session"] = {"type": "practice", "date": None, "mode": mode, "marks": []}
    runstate.S["settings"]["last_preset"] = mode
    return None


def _label_for_cur():
    p = PRESETS[runstate._cur["mode"]]
    if runstate._cur["type"] == "practice":
        return "Practice %s · %s" % (runstate._cur["code"], p["label"])
    kind = "Daily" if runstate._cur["type"] == "daily" else "Archive"
    return "Signal #%d · %s · %s" % (puzzle_number(runstate._cur["date"]), p["label"], kind)


def _boot(today_text):
    """Resume the saved session; a stale daily becomes today's daily."""
    session = runstate.S["session"]
    mode = session["mode"] if session["mode"] in PRESETS else "easy"
    err = None
    if session["type"] == "practice" and runstate.S["practice"] is not None:
        err = _open_practice(runstate.S["practice"]["mode"], runstate.S["practice"]["code"], today_text)
    elif session["type"] == "archive" and session["date"] and EPOCH <= session["date"] < today_text and mode in DAILY_MODES:
        err = _open_daily(session["date"], mode, today_text)
    else:
        daily_mode = runstate.S["settings"]["mode"] if runstate.S["settings"]["mode"] in DAILY_MODES else "easy"
        err = _open_daily(today_text, daily_mode, today_text)
    return err


# --------------------------------------------------------------------------
# View (what the UI draws)


def _view():
    today = runstate._last_today or utc_today()
    mode = runstate._cur["mode"]
    preset = PRESETS[mode]
    board = board_for(mode)
    puzzle = runstate._cur["puzzle"]
    rec = _current_record()
    pings = rec["pings"] if rec is not None else []
    marks = _marks()
    result = rec["result"] if rec is not None else "inprogress"
    finished = result in ("won", "lost")
    ascii_mode = runstate.S["settings"]["ascii_share"]
    ping_views = []
    for r, c, v in pings:
        level = reading_level(v, preset["top"])
        ping_views.append({
            "r": r, "c": c, "v": v, "level": level, "fill": reading_fill(v, preset["top"]),
            "glyph": glyph_for(level), "label": cell_label(r, c),
        })
    assist_on = (
        preset["assist"] and runstate.S["settings"]["assist_shading"] and not finished and bool(pings)
    )
    possible = None
    if assist_on:
        n = board.n
        cells = possible_cells(board, [(r * n + c, v) for r, c, v in pings])
        possible = [[cell // n, cell % n] for cell in cells]
    result_view = None
    truth = None
    if finished:
        n = board.n
        truth = [[t // n, t % n] for t in puzzle.transmitters]
        used = rec["pings_used"]
        won = result == "won"
        result_view = {
            "won": won, "pings_used": used, "budget": preset["budget"], "par": puzzle.par,
            "under_par": won and used < puzzle.par, "at_par": won and used <= puzzle.par,
            "share_ready": True,
        }
    stats = None
    if runstate._cur["type"] != "practice":
        stats = compute_stats(mode, "daily", today)
    number = puzzle_number(runstate._cur["date"]) if runstate._cur["date"] else None
    tomorrow = (parse_date(today) + datetime.timedelta(days=1)).isoformat()
    return {
        "session": {
            "type": runstate._cur["type"], "date": runstate._cur["date"], "mode": mode, "label": _label_for_cur(),
            "number": number, "code": runstate._cur.get("code"),
        },
        "board": {
            "n": board.n, "k": board.k, "radius": board.radius, "budget": preset["budget"],
            "par": puzzle.par, "top": preset["top"], "assist": preset["assist"],
            "spacing": board.spacing, "mode_label": preset["label"],
        },
        "pings": ping_views,
        "marks": [list(m) for m in marks],
        "status": result,
        "pings_left": preset["budget"] - len(pings),
        "can_commit": (not finished) and len(marks) == board.k,
        "possible": possible,
        "truth": truth,
        "guess": [list(g) for g in rec["guess"]] if (rec is not None and finished) else None,
        "result": result_view,
        "stats": stats,
        "ach": {"earned": len(runstate.S["earned"]), "total": len(ACHIEVEMENTS)},
        "presets": [
            {"key": k, "label": PRESETS[k]["label"], "size": PRESETS[k]["size"], "k": PRESETS[k]["k"],
             "budget": PRESETS[k]["budget"], "daily": PRESETS[k]["daily"]}
            for k in PRESET_ORDER
        ],
        "settings": dict(runstate.S["settings"]),
        "today": today,
        "epoch": EPOCH,
        "next_utc": tomorrow,
        "first_run": not runstate.S["onboarding_seen"] and not pings,
        "ascii": ascii_mode,
    }


def _response(ok=True, error=None, message=None, newly=None, events=None, dirty=False, extra=None):
    payload = {
        "ok": ok, "error": error, "message": message,
        "view": _view() if runstate._cur is not None else None,
        "new": [
            {"id": a["id"], "label": a["label"], "description": a["description"]}
            for a in ACHIEVEMENTS if a["id"] in (newly or [])
        ],
        "events": events or [],
        "dirty": dirty,
    }
    if extra:
        payload.update(extra)
    return payload
