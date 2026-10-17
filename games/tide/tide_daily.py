"""The Daily Tide: fixed daily plan, records, hub tracking, start and copy."""

import datetime
import json
import re
import time

import js as _js
import seed as shared_seed
from js import document

import tide_runstate as runstate
from tide_bridge import _finite_number, _read_local_storage_item, _write_local_storage_item
from tide_rules import COASTLINES, COASTLINE_IDS, COASTLINE_ROWS, SEA_SCENARIOS
from tide_runcode import RUN_CODE_GAME


# ---- GD-5 Daily Tide -----------------------------------------------------------------------------------------------
# An opt-in, fixed run: DAILY_SEASONS seasons on a coastline, sea scenario and storm timing taken from the UTC date's
# seed (shared/seed.py, the same seed everybody gets). No streak, nothing lost by missing a day, and any past date can be
# played from the archive. A finished day keeps its result in this browser and offers a one-line result to copy.
DAILY_SEASONS = 12
DAILY_KEY = "tide_daily_v1"
DAILY_EARLIEST = "2026-01-01"
DAILY_STORM_WINDOWS = ((3, 3), (7, 3), (10, 3))  # (first season, how many seasons it may start within)
DAILY_RECORD_LIMIT = 400
HUB_TRACK_KEY = "hub_today_track_dailies"
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_daily_today_override = [None]  # tests set a date here
_daily_ui = {"message": "", "confirm_date": ""}


def daily_today():
    """Today's date in UTC (the day changes at 00:00 UTC for everybody)."""
    return _daily_today_override[0] or time.strftime("%Y-%m-%d", time.gmtime())


def daily_date_ok(text):
    """True for a real date between DAILY_EARLIEST and today (UTC): the archive never reaches into the future."""
    if not isinstance(text, str) or not _DATE_PATTERN.match(text):
        return False
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        return False
    return DAILY_EARLIEST <= text <= daily_today()


def daily_plan(date_text):
    """The day's run, or None for a date that is not allowed: {"date", "seed", "scenario", "coast", "storms"}."""
    if not daily_date_ok(date_text):
        return None
    seed = shared_seed.daily_seed(RUN_CODE_GAME, date_text)
    rng = shared_seed.Rng(seed)
    scenario = rng.choice(list(SEA_SCENARIOS))
    coast = rng.choice(list(COASTLINE_IDS))
    weather = rng.fork("weather")
    storms = [first + weather.below(spread) for first, spread in DAILY_STORM_WINDOWS]
    return {"date": date_text, "seed": seed, "scenario": scenario, "coast": coast, "storms": storms}


def daily_plan_text(plan):
    return (f"{plan['date']}: {COASTLINES[plan['coast']]['label']}, {plan['scenario']} sea, "
            f"storms forecast for seasons {', '.join(str(s) for s in plan['storms'])}. {DAILY_SEASONS} seasons.")


def _daily_clean_result(item):
    if not isinstance(item, dict):
        return None
    seasons, rows, sites = item.get("seasons"), item.get("rows_lost"), item.get("sites_saved")
    score = item.get("score")
    if (not all(isinstance(v, int) and not isinstance(v, bool) for v in (seasons, rows, sites))
            or not 0 <= seasons <= 999 or not 0 <= rows <= COASTLINE_ROWS or not 0 <= sites <= 20
            or not _finite_number(score, -1e9, 1e9)):
        return None
    return {"seasons": seasons, "rows_lost": rows, "sites_saved": sites, "score": round(float(score), 1)}


def daily_records():
    """{date: result} of the days finished in this browser (damaged entries are skipped)."""
    raw = _read_local_storage_item(DAILY_KEY)
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    days = data.get("days") if isinstance(data, dict) else None
    if not isinstance(days, dict):
        return {}
    out = {}
    for date_text, item in days.items():
        if isinstance(date_text, str) and _DATE_PATTERN.match(date_text):
            result = _daily_clean_result(item)
            if result is not None:
                out[date_text] = result
    return out


def daily_record_save(date_text, result):
    records = daily_records()
    records[date_text] = result
    keep = dict(sorted(records.items())[-DAILY_RECORD_LIMIT:])
    _write_local_storage_item(DAILY_KEY, json.dumps({"days": keep}, separators=(",", ":")))


def _plural(n, one, many):
    return f"{n} {one if n == 1 else many}"


def daily_result_line(date_text, result):
    """'Tide daily 2026-10-11: 12 seasons, 2 rows lost, 1 site saved'."""
    return (f"Tide daily {date_text}: {_plural(result['seasons'], 'season', 'seasons')}, "
            f"{_plural(result['rows_lost'], 'row lost', 'rows lost')}, {_plural(result['sites_saved'], 'site saved', 'sites saved')}")


def daily_current_result():
    return {
        "seasons": max(0, runstate.state.season - 1), "rows_lost": COASTLINE_ROWS - runstate.state.rows_dry_count(),
        "sites_saved": runstate.state.protected_heritage_count(), "score": round(runstate.state.damage_saved(), 1),
    }


def clean_daily(item):
    """Save-field validator: a live Daily Tide run, or None."""
    if not isinstance(item, dict):
        return None
    date_text, seed, storms = item.get("date"), item.get("seed"), item.get("storms")
    if not isinstance(date_text, str) or not _DATE_PATTERN.match(date_text) or not isinstance(seed, str):
        return None
    try:
        datetime.date.fromisoformat(date_text)
    except ValueError:
        return None
    if not isinstance(storms, list) or not 1 <= len(storms) <= 6 or not all(
            isinstance(s, int) and not isinstance(s, bool) and 1 <= s <= 99 for s in storms):
        return None
    cleaned = {"date": date_text, "seed": seed[:24], "storms": sorted(set(storms)), "done": item.get("done") is True}
    result = _daily_clean_result(item.get("result"))
    if cleaned["done"] and result is not None:
        cleaned["result"] = result
    return cleaned


def _daily_mark_hub(date_text, seed):
    """Tells the shared hub Today record that today's daily is done, but only when the player has switched dailies
    tracking on at the hub, only for today's own seed, and never for an archive day."""
    try:
        window = getattr(_js, "window", None)
        if window is None or date_text != daily_today():
            return False
        if window.localStorage.getItem(HUB_TRACK_KEY) != "1":
            return False
        seed_js = getattr(window, "NoyvjSeed", None)
        if seed_js is None or not seed_js.daily.isDaily(RUN_CODE_GAME, seed):
            return False
        result = runstate.state.daily.get("result") or daily_current_result()
        info = window.JSON.parse(json.dumps({"score": result["score"], "text": daily_result_line(date_text, result)[:120]}))
        seed_js.daily.markCompleted(RUN_CODE_GAME, info)
        return True
    except Exception:  # noqa: BLE001 -- the hub's Today strip is a nicety
        return False


def daily_check_complete():
    """Called from render(): books the day's result once its seasons have been played (idempotent)."""
    daily = runstate.state.daily
    if not daily or daily.get("done") or runstate.state.season - 1 < DAILY_SEASONS:
        return False
    result = daily_current_result()
    result["seasons"] = DAILY_SEASONS
    daily["done"] = True
    daily["result"] = result
    daily_record_save(daily["date"], result)
    runstate.state._log_ticker(f"Daily Tide {daily['date']} complete. {daily_result_line(daily['date'], result)}. You can keep playing; the result is kept.")
    _daily_mark_hub(daily["date"], daily["seed"])
    return True


def daily_copy_fields():
    """For the shared Copy result button: the finished day's line (empty before it is finished)."""
    daily = runstate.state.daily
    if not daily or not daily.get("done") or not daily.get("result"):
        return {}
    result = daily["result"]
    return {
        "game": f"Tide daily {daily['date']}",
        "stats": [{"n": result["seasons"], "one": "season", "many": "seasons"},
                  {"n": result["rows_lost"], "one": "row lost", "many": "rows lost"},
                  {"n": result["sites_saved"], "one": "site saved", "many": "sites saved"}],
        "seed": daily["seed"],
    }


def daily_status_text():
    daily = runstate.state.daily
    if not daily:
        return "No daily is running. Pick a day below to start one; your current run is replaced, so save it first if you want it."
    if daily.get("done") and daily.get("result"):
        return (f"Finished: {daily_result_line(daily['date'], daily['result'])}. "
                "Keep playing if you like; this result stays as it was.")
    left = max(0, DAILY_SEASONS - (runstate.state.season - 1))
    return (f"Daily {daily['date']} (seed {daily['seed']}): {left} season(s) left. Storms are on and follow the day's forecast "
            f"(seasons {', '.join(str(s) for s in daily['storms'])}). Not counted in the Almanac, bests or library.")


def render_daily():
    toggle = document.getElementById("daily-toggle-button")
    panel = document.getElementById("daily-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide Daily Tide" if runstate.daily_open else "📅 Daily Tide"
    panel.hidden = not runstate.daily_open
    if not runstate.daily_open:
        return
    today = daily_today()
    picker = document.getElementById("daily-date-input")
    if picker is not None:
        picker.setAttribute("min", DAILY_EARLIEST)
        picker.setAttribute("max", today)
        if not getattr(picker, "value", ""):
            picker.value = today
    chosen = str(getattr(picker, "value", "") or today)
    plan = daily_plan(chosen)
    records = daily_records()
    info = document.getElementById("daily-plan")
    if info is not None:
        if plan is None:
            info.innerText = f"Pick a date from {DAILY_EARLIEST} up to today ({today}); the future is not available."
        else:
            done = records.get(chosen)
            info.innerText = daily_plan_text(plan) + (f" Finished before: {daily_result_line(chosen, done)}." if done else "")
    start = document.getElementById("daily-start-button")
    if start is not None:
        start.disabled = plan is None
        pending = _daily_ui["confirm_date"] == chosen and runstate.state.season > 1
        start.innerText = ("Press again to replace the current run" if pending
                           else ("Play today's daily" if chosen == today else f"Play the daily for {chosen}"))
    status = document.getElementById("daily-status")
    if status is not None:
        status.innerText = daily_status_text()
    message = document.getElementById("daily-message")
    if message is not None:
        message.innerText = _daily_ui["message"]
    archive = document.getElementById("daily-archive")
    if archive is not None:
        if records:
            archive.innerText = "Days you have finished: " + "; ".join(
                daily_result_line(d, r).replace("Tide daily ", "") for d, r in sorted(records.items(), reverse=True)[:10]
            ) + "."
        else:
            archive.innerText = "No finished days yet. Any past day is open whenever you like, and skipping a day costs nothing."
    copy_host = document.getElementById("daily-copy")
    if copy_host is not None:
        copy_host.hidden = not (runstate.state.daily and runstate.state.daily.get("done"))
