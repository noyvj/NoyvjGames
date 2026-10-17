"""The player's actions (ping, mark, commit, give up, share, settings, stats), finishing a puzzle, and handle() / handle_dict()."""

import json

import signal_runstate as runstate
from signal_puzzle import board_for, daily_puzzle, reading_at
from signal_records import (
    _finished, _practice_stats, achievements_summary, compute_stats, evaluate_achievements,
    overall_best_streak, reset_engine,
)
from signal_rules import (
    CHANGELOG, GAME_ID, PRESETS, PRESET_ORDER, _is_int, cell_label, fnv1a32, puzzle_number, utc_today,
)
from signal_session import (
    _boot, _current_record, _ensure_record, _marks, _open_daily, _open_practice, _response, _today,
)
from signal_share import _pick, build_share_text, flavour_for_reading


# --------------------------------------------------------------------------
# Actions


def _cell_from(req, board):
    r, c = req.get("r"), req.get("c")
    if not (_is_int(r) and _is_int(c)) or not (0 <= r < board.n and 0 <= c < board.n):
        return None
    return r, c


def _action_ping(req, today_text):
    board = board_for(runstate._cur["mode"])
    preset = PRESETS[runstate._cur["mode"]]
    cell_rc = _cell_from(req, board)
    if cell_rc is None:
        return _response(False, "That tile is not on the board.")
    rec = _current_record()
    if rec is not None and _finished(rec):
        return _response(False, "This puzzle is finished.")
    if rec is not None and len(rec["pings"]) >= preset["budget"]:
        return _response(False, "Out of pings. Mark your answer and commit.")
    r, c = cell_rc
    if rec is not None and any(p[0] == r and p[1] == c for p in rec["pings"]):
        return _response(False, "You already pinged %s." % cell_label(r, c))
    rec = _ensure_record(today_text)
    reading = reading_at(board, runstate._cur["puzzle"].transmitters, r * board.n + c)
    rec["pings"].append([r, c, reading])
    rec["pings_used"] = len(rec["pings"])
    salt = fnv1a32("%s:%d:%d" % (runstate._cur["puzzle"].seed, r, c))
    message = "%s reads %d. %s" % (cell_label(r, c), reading, flavour_for_reading(reading, board.radius, salt))
    runstate.S["onboarding_seen"] = True
    newly = evaluate_achievements()
    return _response(message=message, newly=newly, dirty=True)


def _action_mark(req):
    board = board_for(runstate._cur["mode"])
    cell_rc = _cell_from(req, board)
    if cell_rc is None:
        return _response(False, "That tile is not on the board.")
    rec = _current_record()
    if rec is not None and _finished(rec):
        return _response(False, "This puzzle is finished.")
    r, c = cell_rc
    if (r * board.n + c) not in board.interior:
        return _response(False, "Nothing broadcasts from the outer ring.")
    marks = _marks()
    existing = [i for i, m in enumerate(marks) if m[0] == r and m[1] == c]
    if existing:
        del marks[existing[0]]
        return _response(message="Cleared the marker on %s." % cell_label(r, c), dirty=True)
    if len(marks) >= board.k:
        return _response(False, "All %d markers are placed. Clear one first." % board.k)
    marks.append([r, c])
    return _response(message="Marked %s." % cell_label(r, c), dirty=True)


def _action_clear_marks():
    rec = _current_record()
    if rec is not None and _finished(rec):
        return _response(False, "This puzzle is finished.")
    del _marks()[:]
    return _response(message="Markers cleared.", dirty=True)


def _finish(rec, won, today_text, gave_up=False):
    puzzle = runstate._cur["puzzle"]
    rec["result"] = "won" if won else "lost"
    rec["guess"] = [list(m) for m in rec["marks"]]
    rec["pings_used"] = len(rec["pings"])
    rec["par"] = puzzle.par
    events = []
    if rec["kind"] == "practice":
        stats = runstate.S["practice_stats"][rec["mode"]]
        stats["played"] += 1
        if won:
            stats["won"] += 1
            stats["pings_hist"][max(rec["pings_used"], 1) - 1] += 1
    board = board_for(rec["mode"])
    preset = PRESETS[rec["mode"]]
    n = board.n
    truth = set(puzzle.transmitters)
    right = len([1 for r, c in rec["guess"] if r * n + c in truth])
    salt = fnv1a32(puzzle.seed)
    if won:
        if rec["pings_used"] == preset["budget"]:
            line = _pick("win_last", salt)
        elif rec["pings_used"] <= puzzle.par:
            line = _pick("win_par", salt)
        else:
            line = _pick("win", salt)
    elif gave_up:
        line = _pick("gave_up", salt)
    elif right > 0:
        line = "%s %d of %d were right." % (_pick("near", salt), right, board.k)
    else:
        line = _pick("lose", salt)
    newly = evaluate_achievements()
    if rec["kind"] == "daily" and won and runstate.S["settings"].get("show_streaks"):
        best = overall_best_streak(today_text)
        if best >= 1:
            events.append({
                "type": "leaderboard", "game": GAME_ID, "board": "best_streak",
                "score": best, "detail": "%s streak" % rec["mode"],
            })
    return line, newly, events


def _action_commit(today_text):
    board = board_for(runstate._cur["mode"])
    rec = _current_record()
    if rec is not None and _finished(rec):
        return _response(False, "This puzzle is finished.")
    marks = _marks()
    if len(marks) != board.k:
        return _response(False, "Mark exactly %d tiles before committing." % board.k)
    rec = _ensure_record(today_text)
    n = board.n
    won = sorted(r * n + c for r, c in rec["marks"]) == sorted(runstate._cur["puzzle"].transmitters)
    line, newly, events = _finish(rec, won, today_text)
    runstate.S["onboarding_seen"] = True
    return _response(message=line, newly=newly, events=events, dirty=True)


def _action_give_up(today_text):
    rec = _current_record()
    if rec is not None and _finished(rec):
        return _response(False, "This puzzle is finished.")
    rec = _ensure_record(today_text)
    line, newly, events = _finish(rec, False, today_text, gave_up=True)
    return _response(message=line, newly=newly, events=events, dirty=True)


def _action_share(req):
    rec = _current_record()
    if rec is None or not _finished(rec):
        return _response(False, "Finish the puzzle before sharing.")
    if "ascii" in req and isinstance(req["ascii"], bool):
        runstate.S["settings"]["ascii_share"] = req["ascii"]
    number = puzzle_number(runstate._cur["date"]) if runstate._cur["date"] else 0
    text = build_share_text(rec, runstate._cur["mode"], number, runstate.S["settings"]["ascii_share"])
    runstate.S["flags"]["shared"] = True
    newly = evaluate_achievements()
    return _response(message="Result copied.", newly=newly, dirty=True, extra={"text": text})


_SETTING_TYPES = {"assist_shading": bool, "ascii_share": bool, "show_streaks": bool}


def _action_settings(req, today_text=None):
    changed = False
    before_streaks = runstate.S["settings"].get("show_streaks")
    for key, kind in _SETTING_TYPES.items():
        if key in req:
            if not isinstance(req[key], kind):
                return _response(False, "Bad value for %s." % key)
            runstate.S["settings"][key] = req[key]
            changed = True
    if "last_preset" in req:
        value = req["last_preset"]
        if not isinstance(value, str) or value not in PRESETS:
            return _response(False, "Unknown preset.")
        runstate.S["settings"]["last_preset"] = value
        changed = True
    newly = None
    if today_text is not None and runstate.S["settings"].get("show_streaks") and not before_streaks:
        newly = evaluate_achievements()      # AN-11: switching streaks on awards what the history already earned
    return _response(newly=newly, dirty=changed)


def _action_stats(today_text):
    modes = {}
    total_solved = 0
    for m in PRESET_ORDER:
        entry = {"label": PRESETS[m]["label"], "daily_mode": PRESETS[m]["daily"], "practice": _practice_stats(m)}
        if PRESETS[m]["daily"]:
            entry["daily"] = compute_stats(m, "daily", today_text)
            entry["archive"] = compute_stats(m, "archive", today_text)
        modes[m] = entry
    for key, rec in runstate.S["days"].items():
        if rec["result"] == "won":
            total_solved += 1
    for m in PRESET_ORDER:
        total_solved += runstate.S["practice_stats"][m]["won"]
    return _response(extra={"stats": modes, "best_streak": overall_best_streak(today_text) if runstate.S["settings"].get("show_streaks") else None, "total_solved": total_solved})


def handle_dict(req):
    """Dispatch one request dict; returns the response dict."""
    if not isinstance(req, dict) or not isinstance(req.get("action"), str):
        return _response(False, "Bad request.")
    action = req["action"]
    today_text = _today()
    if action == "reset":
        reset_engine()
        err = _boot(_today())
        return _response(err is None, err, dirty=True)
    if action == "boot":
        err = _boot(today_text)
        newly = evaluate_achievements()
        return _response(err is None, err, newly=newly, dirty=bool(newly), extra={"changelog": CHANGELOG})
    if runstate._cur is None:
        return _response(False, "Engine not started: send boot first.")
    if action == "view":
        return _response()
    if action == "open":
        err = _open_daily(req.get("date"), req.get("mode"), today_text)
        return _response(err is None, err, dirty=err is None)
    if action == "practice":
        err = _open_practice(req.get("mode"), req.get("code"), today_text)
        return _response(err is None, err, dirty=err is None)
    if action == "ping":
        return _action_ping(req, today_text)
    if action == "mark":
        return _action_mark(req)
    if action == "clear_marks":
        return _action_clear_marks()
    if action == "commit":
        return _action_commit(today_text)
    if action == "give_up":
        return _action_give_up(today_text)
    if action == "share":
        return _action_share(req)
    if action == "settings":
        return _action_settings(req, today_text)
    if action == "stats":
        return _action_stats(today_text)
    if action == "achievements":
        return _response(extra={"achievements": achievements_summary()})
    if action == "ack_onboarding":
        runstate.S["onboarding_seen"] = True
        return _response(dirty=True)
    return _response(False, "Unknown action.")


def recent_history(mode, n=7):
    """Return last n daily results and par values for a mode."""
    import datetime
    today = utc_today()
    try:
        base = datetime.date.fromisoformat(today)
    except Exception:
        base = datetime.date.today()

    history = []
    for i in range(n):
        d = (base - datetime.timedelta(days=i)).isoformat()
        res = runstate.S["days"].get(d, {}).get(mode)
        if res is None:
            continue
        try:
            puzzle = daily_puzzle(d, mode)
            p = puzzle.par
        except Exception:
            p = "?"
        history.append({"date": d, "result": res, "par": p})
    return history


def handle(request):
    """The one entry point app.js calls: JSON text in, JSON text out."""
    try:
        req = json.loads(request) if isinstance(request, str) else request
        return json.dumps(handle_dict(req))
    except Exception as exc:  # noqa: BLE001 -- the UI must never see a raw traceback
        return json.dumps({"ok": False, "error": "Engine error: %s" % exc, "view": None, "new": [], "events": [], "dirty": False})
