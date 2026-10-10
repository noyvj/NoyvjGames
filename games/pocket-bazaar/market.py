"""Pocket Bazaar -- the Daily Market (TODO M-4b-9).

One market day per UTC date, the same for everybody, worked out from the date text ALONE: no clock, no server, no
random source. Every function takes the date as an argument (the view passes "today" in, the tests pass dates
explicitly), and this module has no date or time library at all: the calendar maths below is plain arithmetic.

The Daily Market is an ordinary market day with a fixed, fair stall: no upgrades, no shelf, no regulars, the three
base crates (plus one more for some dates) and the festival the date picks. It is a plain optional day:
  * it pays NOTHING extra: no coins, renown, tally, achievement or personal best changes (the pledge: no login
    reward, no streak, no penalty for a missed day);
  * a date is just a date: any date from the epoch to today can be played, in any order, and skipping costs nothing;
  * the only record is the best result per date (stars, customers served, coins taken that day).

Fairness bar: before a date's market is accepted, (a) every customer's order can be built on that day's counter, and
(b) a plain greedy player (marketbot.py, the same bot the campaign's fairness test uses) serves at least
MIN_SERVED_PCT of the customers. A candidate that fails is replaced by the next one derived from the same date.

The leaderboard is NOT built here: `leaderboard_entry` shapes the record a future backend board would take, and
nothing sends it anywhere (see CLAUDE.md, "Daily Market").
"""

import days
import festival
import marketbot
import orders
from board import Board
from day import Day
from rng import Rng, mix

GENERATOR_VERSION = "v1"
EPOCH = "2026-10-01"           # the first playable date
LAST_DATE = "2099-12-31"
BASE_FAMILIES = ("produce", "textiles", "ceramics")
EXTRA_FAMILIES = ("spices", "sweets")
EXTRA_ARCHETYPES = ((), ("child",), ("tourist",), ("child", "tourist"))
RUNGS = (2, 10)                # the campaign's recipes the market borrows (day 2 .. day 10)
MIN_SERVED_PCT = 75
MAX_ATTEMPTS = 40
MAX_DAYS_SAVED = 4000

_DIM = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
_cache = {}


# --- the calendar, as plain arithmetic ---------------------------------------------------------------------------
def _leap(y):
    return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)


def parse_date(text):
    """(y, m, d) for a strict, real YYYY-MM-DD string, else None."""
    if not isinstance(text, str) or len(text) != 10 or text[4] != "-" or text[7] != "-":
        return None
    digits = text[:4] + text[5:7] + text[8:]
    if not digits.isascii() or not digits.isdigit():
        return None
    y, m, d = int(text[:4]), int(text[5:7]), int(text[8:])
    if not 1 <= m <= 12 or not 1 <= d <= _DIM[m - 1] + (1 if m == 2 and _leap(y) else 0):
        return None
    return y, m, d


def valid_date(text):
    return parse_date(text) is not None


def _ordinal(ymd):
    """Days since 0001-01-01 (the proleptic Gregorian count)."""
    y, m, d = ymd
    before = y - 1
    n = before * 365 + before // 4 - before // 100 + before // 400
    n += sum(_DIM[:m - 1]) + (1 if m > 2 and _leap(y) else 0)
    return n + d


def day_number(text):
    """Market 1 is the epoch."""
    return _ordinal(parse_date(text)) - _ordinal(parse_date(EPOCH)) + 1


def playable(text, today):
    """A date may be played when it is a real date from the epoch up to `today`, both included."""
    a, b = parse_date(text), parse_date(today)
    return a is not None and b is not None and _ordinal(parse_date(EPOCH)) <= _ordinal(a) <= _ordinal(b)


def add_days(text, n):
    """The date `n` days after `text` (tests walk consecutive dates with it)."""
    target = _ordinal(parse_date(text)) + n
    y = max(1, target // 366)
    while _ordinal((y + 1, 1, 1)) <= target:
        y += 1
    while _ordinal((y, 1, 1)) > target:
        y -= 1
    left = target - _ordinal((y, 1, 1))
    for m in range(1, 13):
        length = _DIM[m - 1] + (1 if m == 2 and _leap(y) else 0)
        if left < length:
            return "%04d-%02d-%02d" % (y, m, left + 1)
        left -= length
    raise ValueError("date out of range")


# --- generating a market ------------------------------------------------------------------------------------------
def _fnv(text):
    h = 2166136261
    for byte in text.encode("utf-8"):
        h = ((h ^ byte) * 16777619) & 0xFFFFFFFF
    return h


def _build(date_text, attempt):
    """The candidate market for (date, attempt): returns (spec dict, the freshly built Day)."""
    base = _fnv("pocket-bazaar-market-%s|%s|%d" % (GENERATOR_VERSION, date_text, attempt))
    pick = Rng(mix(base, 1))
    rung = pick.between(*RUNGS)
    fest = pick.choice(festival.ORDER)
    families = list(BASE_FAMILIES)
    if pick.chance(1, 3):
        families.append(pick.choice(EXTRA_FAMILIES))
    extras = pick.choice(EXTRA_ARCHETYPES)
    number = day_number(date_text) if date_text >= EPOCH else 0
    rng = Rng(mix(base, 2))
    rules = festival.day_rules(fest)
    rules["festival"] = fest
    day_spec = festival.apply_spec(days.spec(rung, extras=set(extras)), fest)
    queue = orders.make_queue(rng, day_spec, families)
    board = Board(5, rules.get("board_height", 6), False)
    spec = {"date": date_text, "number": number, "festival": fest, "families": families, "extras": list(extras),
            "rung": rung, "attempt": attempt, "customers": len(queue)}
    return spec, Day(number, board, queue, rng, rules)


def _fair(spec, day):
    """The fairness bar for a freshly built day: reachable orders, and a plain greedy player serves enough."""
    for customer in day.queue:
        if not orders.order_is_reachable(customer, day.board):
            return None
    marketbot.play(day, spec["families"])
    pct = day.served * 100 // day.total
    return pct if pct >= MIN_SERVED_PCT else None


def spec(date_text):
    """The market for a date: {"date", "number", "festival", "families", "extras", "rung", "attempt", "customers",
    "bot_pct"}. Memoised; the same date text always gives the same dict."""
    if parse_date(date_text) is None:
        raise ValueError("market.spec needs a YYYY-MM-DD date")
    if date_text in _cache:
        return _cache[date_text]
    for attempt in range(MAX_ATTEMPTS):
        candidate, day = _build(date_text, attempt)
        pct = _fair(candidate, day)
        if pct is not None:
            candidate["bot_pct"] = pct
            if len(_cache) > 400:
                _cache.clear()
            _cache[date_text] = candidate
            return candidate
    raise RuntimeError("no fair market for %s" % date_text)      # unreachable with the shipped content (tested)


def new_day(date_text):
    """A fresh Day for the date's market, ready to play, and the rules it was built with."""
    candidate = spec(date_text)
    _spec, day = _build(date_text, candidate["attempt"])
    return day


def rules_for(date_text):
    """The Day's rules for a saved market day (the festival's own, never the stall's upgrades)."""
    fest = spec(date_text)["festival"]
    rules = festival.day_rules(fest)
    rules["festival"] = fest
    return rules


# --- results --------------------------------------------------------------------------------------------------------
def rank(record):
    return (record["stars"], record["served"], record["coins"])


def merge_record(old, summary):
    """The best result per date: more stars, then more customers served, then more coins that day."""
    new = {"stars": int(summary["stars"]), "served": int(summary["served"]), "total": int(summary["total"]),
           "coins": int(summary["coins"])}
    if isinstance(old, dict) and rank(old) >= rank(new):
        return dict(old)
    return new


def clean_days(raw):
    """Validated copy of the saved {date: {"stars", "served", "total", "coins"}} map; junk dropped entry by entry."""
    out = {}
    if not isinstance(raw, dict):
        return out
    for text, rec in raw.items():
        if not isinstance(text, str) or not isinstance(rec, dict) or parse_date(text) is None:
            continue
        if not _ordinal(parse_date(EPOCH)) <= _ordinal(parse_date(text)) <= _ordinal(parse_date(LAST_DATE)):
            continue
        vals = [rec.get(k) for k in ("stars", "served", "total", "coins")]
        if any(isinstance(v, bool) or not isinstance(v, int) for v in vals):
            continue
        stars, served, total, coins = vals
        if not 1 <= stars <= 3 or not 1 <= total <= 64 or not 0 <= served <= total or not 0 <= coins <= 10 ** 7:
            continue
        out[text] = {"stars": stars, "served": served, "total": total, "coins": coins}
        if len(out) >= MAX_DAYS_SAVED:
            break
    return out


def leaderboard_entry(date_text, record):
    """HOOK for the future opt-in board (a separate backend job, NOT built in this pass): the entry a board would
    take for one date. Pure; nothing calls a server with it."""
    return {"board": "pocket-bazaar-market", "date": date_text, "score": int(record["coins"]),
            "stars": int(record["stars"]), "served": int(record["served"])}


def tally(days_done, today):
    """How many of the open dates have been played, and with how many three-star days. No streaks."""
    open_days = day_number(today) if playable(today, today) else 0
    played = [d for d in days_done if playable(d, today)]
    return {"open": open_days, "played": len(played), "perfect": sum(1 for d in played if days_done[d]["stars"] == 3)}
