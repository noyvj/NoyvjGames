"""Dead Reckoning -- the Daily Chart (TODO M-5b-11).

One practice-style chart per UTC date, the same for everybody, derived from the date text ALONE: no clock, no server, no
random source. Every function takes the date as an argument (the view passes "today" in; the tests pass dates explicitly);
this module never asks what day it is.

The chart is made by the practice generator (gen.make_chart), which already SOLVES every chart it returns: a visibility-graph
route shot leg by leg under the true sea lands cleanly (no grounding, no close pass), on time, with the deadline set from it,
and the printed midpoints followed carefully also make landfall. The Daily Chart adds its own bar on top:
the par plan must score three stars with no helper and the naive straight-at-the-flag plan must be a plain, scored attempt.
A seed that fails is skipped for the next seed derived from the same date.

Nothing here is a streak: a result is kept per date (best stars, smallest miss, tries), a missed day costs nothing and any
past date stays open. A daily chart never touches the campaign records or the practice total. The leaderboard is NOT built
here: `leaderboard_entry` shapes the record a future backend board would take, and nothing sends it anywhere.
"""

import copy
import re
from datetime import date as _date, timedelta

import gen
import sim

GENERATOR_VERSION = "v1"
EPOCH = "2026-10-01"
LAST_DATE = "2099-12-31"
SEED_TRIES = 40
ID_RE = re.compile(r"^daily-(\d{4}-\d{2}-\d{2})$")
MAX_DAYS_SAVED = 4000
_cache = {}


# --- dates (strict, and never the clock) -----------------------------------------------------------
def parse_date(text):
    if not isinstance(text, str) or len(text) != 10 or text[4] != "-" or text[7] != "-" or not text.isascii():
        return None
    try:
        return _date.fromisoformat(text)
    except ValueError:
        return None


def valid_date(text):
    return parse_date(text) is not None


def day_number(text):
    return (parse_date(text) - parse_date(EPOCH)).days + 1


def playable(text, today):
    """A date may be played when it is a real date from the epoch up to `today`, both included."""
    a, b = parse_date(text), parse_date(today)
    return a is not None and b is not None and parse_date(EPOCH) <= a <= b


def add_days(text, n):
    return (parse_date(text) + timedelta(days=n)).isoformat()


def chart_id(date_text):
    return "daily-" + date_text


def is_daily_id(text):
    """True for `daily-YYYY-MM-DD` with a real date from the epoch on (nothing else is a daily chart)."""
    m = ID_RE.match(text) if isinstance(text, str) else None
    return bool(m) and parse_date(m.group(1)) is not None and m.group(1) >= EPOCH


def date_of(text):
    return text[len("daily-"):] if is_daily_id(text) else None


# --- generating the chart -----------------------------------------------------------------------------
def _fnv(text):
    h = 2166136261
    for byte in text.encode("utf-8"):
        h = ((h ^ byte) * 16777619) & 0xFFFFFFFF
    return h


def _accept(chart):
    """The Daily Chart's own bar, on top of the generator's: the par plan makes three stars cleanly with no helper."""
    legs = chart["par_legs"]
    res = sim.sail(chart, legs, seed=chart["seed"])
    sc = sim.score(chart, legs, res, used_helpers=False)
    return sc["stars"] == 3 and sc["arrived"] and sc["on_time"] and sc["clear"]


def spec(date_text):
    """{"date", "number", "difficulty", "seed", "tries"} for a date: which generator level and seed the date picks."""
    if parse_date(date_text) is None:
        raise ValueError("daily.spec needs a YYYY-MM-DD date")
    h = _fnv("dead-reckoning-daily-%s|%s" % (GENERATOR_VERSION, date_text))
    difficulty = 1 + (h >> 8) % len(gen.DIFFICULTIES)
    base = _fnv("%s|seed" % date_text + GENERATOR_VERSION) * 7919 % gen.SEED_LIMIT
    return {"date": date_text, "number": day_number(date_text) if date_text >= EPOCH else 0, "difficulty": difficulty, "seed": base}


def chart_for(date_text):
    """The Daily Chart for a date (a fresh deep copy each call; the work is memoised)."""
    if parse_date(date_text) is None:
        raise ValueError("daily.chart_for needs a YYYY-MM-DD date")
    if date_text not in _cache:
        s = spec(date_text)
        built = None
        for k in range(SEED_TRIES):
            seed = (s["seed"] + k) % gen.SEED_LIMIT
            chart = gen.make_chart(s["difficulty"], seed)
            if chart is not None and _accept(chart):
                built = copy.deepcopy(chart)
                built["practice_seed"] = seed
                built["tries"] = k + 1
                break
        if built is None:                       # unreachable with the shipped generator (tests cover hundreds of dates)
            raise RuntimeError("no fair daily chart for %s" % date_text)
        built["id"] = chart_id(date_text)
        built["name"] = "Daily Chart %d" % s["number"]
        built["chapter"] = "daily"
        built["intro"] = ("The daily chart for %s (level %d, %s). Everybody sails the same sea today; any day's chart can be played any time."
                          % (date_text, s["difficulty"], gen.NAMES[s["difficulty"]]))
        if len(_cache) > 60:
            _cache.clear()
        _cache[date_text] = built
    return copy.deepcopy(_cache[date_text])


# --- results ------------------------------------------------------------------------------------------------
def new_record():
    return {"stars": 0, "best_error_nm": None, "tries": 0}


def merge_record(old, stars, miss_nm, arrived):
    """The saved record for a date after another finished passage: best stars, smallest miss (landfalls only), tries + 1."""
    old = old if isinstance(old, dict) else new_record()
    err = old.get("best_error_nm")
    if arrived and (err is None or miss_nm < err):
        err = round(float(miss_nm), 2)
    return {"stars": max(old.get("stars", 0), int(stars)), "best_error_nm": err, "tries": min(99999, old.get("tries", 0) + 1)}


def clean_days(raw):
    """Validated copy of the saved {date: record} map. Junk entries are dropped one by one."""
    out = {}
    if not isinstance(raw, dict):
        return out
    for text, rec in raw.items():
        d = parse_date(text) if isinstance(text, str) else None
        if d is None or not (parse_date(EPOCH) <= d <= parse_date(LAST_DATE)) or not isinstance(rec, dict):
            continue
        stars, err, tries = rec.get("stars"), rec.get("best_error_nm"), rec.get("tries")
        if isinstance(stars, bool) or not isinstance(stars, int) or isinstance(tries, bool) or not isinstance(tries, int):
            continue
        if err is not None and (isinstance(err, bool) or not isinstance(err, (int, float)) or not 0 <= err <= 1000 or err != err):
            continue
        out[text] = {"stars": max(0, min(3, stars)), "best_error_nm": None if err is None else round(float(err), 2),
                     "tries": max(1, min(99999, tries))}
        if len(out) >= MAX_DAYS_SAVED:
            break
    return out


def better(a, b):
    """The better of two records for one date (commutative: the order of two saves never matters)."""
    errs = [e for e in (a["best_error_nm"], b["best_error_nm"]) if e is not None]
    return {"stars": max(a["stars"], b["stars"]), "best_error_nm": min(errs) if errs else None, "tries": max(a["tries"], b["tries"])}


def leaderboard_entry(date_text, record):
    """HOOK for the future opt-in daily board (a separate backend job, NOT built in this pass): the entry a board would
    take for one date. Pure; nothing calls a server with it."""
    return {"board": "dead-reckoning-daily-chart", "date": date_text, "stars": int(record["stars"]),
            "error_nm": record["best_error_nm"]}


def tally(days_done, today):
    """How many of the open dates have been played, and how many earned three stars. No streaks."""
    open_days = day_number(today) if playable(today, today) else 0
    played = [d for d in days_done if playable(d, today)]
    return {"open": open_days, "played": len(played), "three": sum(1 for d in played if days_done[d]["stars"] == 3)}
