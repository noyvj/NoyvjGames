"""The player's state (settings, days, practice), record validation, derived stats and streaks, achievements and the leaderboard number."""

import signal_runstate as runstate
from signal_puzzle import board_for, parse_practice_code, reading_at
from signal_rules import (
    ACHIEVEMENTS, ACHIEVEMENT_IDS, DAILY_MODES, PRESETS, PRESET_ORDER, _is_int, parse_date, puzzle_number,
    utc_today,
)


# --------------------------------------------------------------------------
# Engine state

_DEFAULT_SETTINGS = {"mode": "easy", "assist_shading": True, "ascii_share": False, "show_streaks": False, "last_preset": "easy"}


def _fresh_state():
    return {
        "days": {},
        "practice": None,
        "practice_stats": {key: {"played": 0, "won": 0, "pings_hist": [0] * PRESETS[key]["budget"]} for key in PRESET_ORDER},
        "settings": dict(_DEFAULT_SETTINGS),
        "earned": {},
        "flags": {"shared": False},
        "onboarding_seen": False,
        "session": {"type": "daily", "date": None, "mode": "easy", "marks": []},
    }


runstate.S = _fresh_state()


def reset_engine():
    """Back to a brand-new player (also used by the in-game reset)."""
    runstate.S = _fresh_state()
    runstate._cur = None
    runstate._last_today = None


def _day_key(date_text, mode):
    return "%s:%s" % (date_text, mode)


def _parse_day_key(key):
    if not isinstance(key, str):
        return None
    parts = key.split(":")
    if len(parts) != 2 or parse_date(parts[0]) is None:
        return None
    if parts[1] not in PRESETS or not PRESETS[parts[1]]["daily"]:
        return None
    return parts[0], parts[1]


def _new_record(kind, mode, code=None):
    rec = {
        "mode": mode, "kind": kind, "pings": [], "marks": [], "guess": [],
        "result": "inprogress", "pings_used": 0, "par": None,
    }
    if code is not None:
        rec["code"] = code
    return rec


# ---- record validation (used on load and when re-opening a puzzle) --------


def _clean_cell_list(value, board, max_len, interior_only):
    if not isinstance(value, list) or len(value) > max_len:
        return None
    out = []
    seen = set()
    for item in value:
        if not isinstance(item, list) or len(item) != 2:
            return None
        r, c = item
        if not (_is_int(r) and _is_int(c)) or not (0 <= r < board.n and 0 <= c < board.n):
            return None
        cell = r * board.n + c
        if cell in seen or (interior_only and cell not in board.interior):
            return None
        seen.add(cell)
        out.append([r, c])
    return out


def _clean_record(raw, expected_kinds, expected_mode=None):
    """A validated deep copy of a record, or None if it is unusable."""
    if not isinstance(raw, dict):
        return None
    mode = raw.get("mode")
    if not isinstance(mode, str) or mode not in PRESETS:
        return None
    if expected_mode is not None and mode != expected_mode:
        return None
    kind = raw.get("kind")
    if not isinstance(kind, str) or kind not in expected_kinds:
        return None
    preset = PRESETS[mode]
    board = board_for(mode)
    pings = raw.get("pings")
    if not isinstance(pings, list) or len(pings) > preset["budget"]:
        return None
    clean_pings = []
    seen = set()
    max_reading = preset["k"] * preset["radius"]
    for item in pings:
        if not isinstance(item, list) or len(item) != 3:
            return None
        r, c, v = item
        if not (_is_int(r) and _is_int(c) and _is_int(v)):
            return None
        if not (0 <= r < board.n and 0 <= c < board.n and 0 <= v <= max_reading):
            return None
        if (r, c) in seen:
            return None
        seen.add((r, c))
        clean_pings.append([r, c, v])
    marks = _clean_cell_list(raw.get("marks", []), board, preset["k"], True)
    guess = _clean_cell_list(raw.get("guess", []), board, preset["k"], True)
    if marks is None or guess is None:
        return None
    result = raw.get("result")
    if not isinstance(result, str) or result not in ("inprogress", "won", "lost"):
        return None
    if result == "inprogress":
        guess = []
    par = raw.get("par")
    if par is not None and not (_is_int(par) and 1 <= par <= preset["budget"]):
        return None
    if result == "won" and len(guess) != preset["k"]:
        return None
    rec = {
        "mode": mode, "kind": kind, "pings": clean_pings, "marks": marks, "guess": guess,
        "result": result, "pings_used": len(clean_pings), "par": par,
    }
    if kind == "practice":
        parsed = parse_practice_code(raw.get("code"))
        if parsed is None or parsed[0] != mode:
            return None
        rec["code"] = parsed[1]
    return rec


def _verify_against_puzzle(rec, puzzle):
    """Lazy repair when a stored record is opened and its puzzle regenerated:
    stored readings are recomputed from the true transmitters, and a 'won'
    that does not match the truth is downgraded to 'lost'. (A hand-edited
    save cannot improve a result this way; it stays a local toy either way.)"""
    board = board_for(rec["mode"])
    n = board.n
    for ping in rec["pings"]:
        ping[2] = reading_at(board, puzzle.transmitters, ping[0] * n + ping[1])
    truth = sorted(puzzle.transmitters)
    if rec["result"] == "won":
        guess = sorted(r * n + c for r, c in rec["guess"])
        if guess != truth:
            rec["result"] = "lost"
    if rec["result"] != "inprogress":
        rec["par"] = puzzle.par


# ---- stats (derived, never trusted from a save) ---------------------------


def _finished(rec):
    return rec["result"] in ("won", "lost")


def _mode_records(mode, kind):
    for key, rec in runstate.S["days"].items():
        if rec["mode"] == mode and rec["kind"] == kind and _parse_day_key(key):
            yield key, rec


def _streaks(win_dates, today, lost_today):
    """(current, best) run lengths over a set of date ordinals."""
    if not win_dates:
        return 0, 0
    ordered = sorted(win_dates)
    best = run = 1
    for prev, cur in zip(ordered, ordered[1:]):
        run = run + 1 if cur == prev + 1 else 1
        best = max(best, run)
    if lost_today:
        return 0, best
    today_ord = today.toordinal()
    anchor = today_ord if today_ord in win_dates else (today_ord - 1 if today_ord - 1 in win_dates else None)
    if anchor is None:
        return 0, best
    length = 0
    while anchor - length in win_dates:
        length += 1
    return length, best


def compute_stats(mode, kind, today_text):
    """Stats for one mode and one kind ("daily" or "archive"), from `days`."""
    budget = PRESETS[mode]["budget"]
    today = parse_date(today_text)
    hist = [0] * budget
    played = won = 0
    win_dates = set()
    last_played = None
    lost_today = False
    for key, rec in _mode_records(mode, kind):
        if not _finished(rec):
            continue
        date_text = key.split(":")[0]
        played += 1
        if last_played is None or date_text > last_played:
            last_played = date_text
        if rec["result"] == "won":
            won += 1
            hist[max(rec["pings_used"], 1) - 1] += 1
            win_dates.add(parse_date(date_text).toordinal())
        elif date_text == today_text and kind == "daily":
            lost_today = True
    streak, best = _streaks(win_dates, today, lost_today) if kind == "daily" else (0, 0)
    return {
        "played": played, "won": won, "streak": streak, "best_streak": best,
        "last_played_utc": last_played, "pings_hist": hist,
    }


def _practice_stats(mode):
    stats = runstate.S["practice_stats"][mode]
    return {"played": stats["played"], "won": stats["won"], "pings_hist": list(stats["pings_hist"])}


# ---- achievements ---------------------------------------------------------


def _earn(achievement_id, newly):
    if achievement_id in ACHIEVEMENT_IDS and achievement_id not in runstate.S["earned"]:
        runstate.S["earned"][achievement_id] = runstate._last_today or utc_today()
        newly.append(achievement_id)


def _rec_meta(rec):
    preset = PRESETS[rec["mode"]]
    return preset["budget"], preset["radius"]


def evaluate_achievements():
    """Recompute what is earned from all recorded play; returns the ids that
    are newly earned. Earned status is permanent once granted (a save that
    later prunes old days never loses one)."""
    newly = []
    today = runstate._last_today or utc_today()
    records = [rec for _key, rec in runstate.S["days"].items()]
    if runstate.S["practice"] is not None:
        records.append(runstate.S["practice"])

    for rec in records:
        budget, radius = _rec_meta(rec)
        zeros = sum(1 for p in rec["pings"] if p[2] == 0)
        if zeros >= 3:
            _earn("silent_night", newly)
        if any(p[2] > radius for p in rec["pings"]):
            _earn("overlap", newly)
        if not _finished(rec):
            continue
        _earn("first_contact", newly)
        if rec["result"] == "lost":
            _earn("static", newly)
            continue
        used = rec["pings_used"]
        par = rec.get("par")
        if par is not None and used <= par:
            _earn("clean_signal", newly)
        if par is not None and used < par:
            _earn("under_par", newly)
        if budget - used >= 4:
            _earn("lucky_guess", newly)
        if used == budget:
            _earn("last_gasp", newly)
        if rec["mode"] == "hard":
            _earn("hard_copy", newly)
        if rec["mode"] in ("wide", "bigsky"):
            _earn("wide_open", newly)

    total_practice = sum(runstate.S["practice_stats"][m]["played"] for m in PRESET_ORDER)
    if total_practice >= 1:
        _earn("first_contact", newly)
    if total_practice >= 5:
        _earn("dial_practice", newly)
    for m in PRESET_ORDER:
        stats = runstate.S["practice_stats"][m]
        if stats["won"] >= 1:
            if m == "hard":
                _earn("hard_copy", newly)
            if m in ("wide", "bigsky"):
                _earn("wide_open", newly)
    if any(runstate.S["practice_stats"][m]["played"] - runstate.S["practice_stats"][m]["won"] > 0 for m in PRESET_ORDER):
        _earn("static", newly)

    archive_finished = sum(1 for _k, rec in runstate.S["days"].items() if rec["kind"] == "archive" and _finished(rec))
    if archive_finished >= 10:
        _earn("archivist", newly)

    # AN-11: no streak by default. The three streak badges are earned only while "Show my daily streak" is on
    # (they are recomputed from the played days, so switching it on later awards what the history already earned).
    if runstate.S["settings"].get("show_streaks"):
        best = 0
        for m in DAILY_MODES:
            best = max(best, compute_stats(m, "daily", today)["best_streak"])
        if best >= 3:
            _earn("three_in_a_row", newly)
        if best >= 7:
            _earn("week_on_air", newly)
        if best >= 30:
            _earn("month_on_air", newly)

    won_by_date = {}
    for key, rec in runstate.S["days"].items():
        parsed = _parse_day_key(key)
        if parsed and rec["kind"] == "daily" and rec["result"] == "won":
            won_by_date.setdefault(parsed[0], set()).add(rec["mode"])
        if parsed and rec["kind"] == "daily" and _finished(rec) and puzzle_number(parsed[0]) >= 100:
            _earn("puzzle_100", newly)
    if any({"easy", "hard"} <= modes for modes in won_by_date.values()):
        _earn("both_bands", newly)
    if runstate.S["flags"].get("shared"):
        _earn("show_off", newly)
    return newly


def achievement_ids_earned():
    return [a for a in ACHIEVEMENT_IDS if a in runstate.S["earned"]]


def achievements_summary():
    return [
        {
            "id": a["id"], "label": a["label"], "description": a["description"],
            "earned": a["id"] in runstate.S["earned"], "date": runstate.S["earned"].get(a["id"]),
        }
        for a in ACHIEVEMENTS
    ]


# ---- the leaderboard number ----------------------------------------------


def overall_best_streak(today_text):
    return max(compute_stats(m, "daily", today_text)["best_streak"] for m in DAILY_MODES)
