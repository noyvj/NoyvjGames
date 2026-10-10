"""Heist Committee -- the Daily Job (TODO M-1b-10).

One job per UTC date, the same for everybody, derived from the date text ALONE: no clock, no server, no random
source. Every function here takes the date as an argument; the view passes in "today" and the tests pass dates
explicitly, so this module never reads the clock.

A daily job is a standalone night, separate from the career:
  * the target, the job's seed, today's eight candidates (all five roles) and today's three-piece van come from
    the date;
  * crew, gear and scouting are free (nothing is spent, no reputation or friendship changes), every crew member's
    quirk is on the file, so it is a pure planning puzzle;
  * the fairness bar: before a date is accepted, a plain bot (bots.greedy_plan, told the three scouted kinds of
    trouble) must find at least MIN_CLEAN_CREWS different crews among the eight candidates that escape cleanly
    (no alarm) on that exact night, no gear needed. A date whose candidate job fails the bar is replaced by the
    next candidate from the same date, so a daily is never unwinnable and never a needle in a haystack.
  * "par" is the lowest payout among those witness crews; a clean getaway at or above it is the top tier.

Nothing here is a streak: a result is recorded per date, a missed day costs nothing, and any past date stays open.
The leaderboard is NOT built here: `leaderboard_entry` shapes the record a future backend board would take, and
nothing sends it anywhere (see CLAUDE.md, "Daily Job").
"""

import itertools
from datetime import date as _date, timedelta

import bots
import engine

GENERATOR_VERSION = "v1"
EPOCH = "2026-10-01"          # the first playable date; every day since then is open
LAST_DATE = "2099-12-31"
OFFER_SIZE = 8
VAN_SIZE = 3
MIN_CLEAN_CREWS = 3
MAX_ATTEMPTS = 60
TIERS = ("busted", "escaped", "clean", "par")
TIER_LABELS = {"busted": "Came home empty-handed", "escaped": "Got away, loudly", "clean": "A clean getaway",
               "par": "A clean getaway at par or better"}
TIER_SYMBOLS = {"busted": "o", "escaped": "v", "clean": "*", "par": "**"}
MAX_DAYS_SAVED = 4000

_cache = {}


# --- dates (strict, and never the clock) ---------------------------------------------------------------
def parse_date(text):
    """A datetime.date for a strict YYYY-MM-DD string, else None."""
    if not isinstance(text, str) or len(text) != 10 or text[4] != "-" or text[7] != "-":
        return None
    try:
        return _date.fromisoformat(text)
    except ValueError:
        return None


def valid_date(text):
    return parse_date(text) is not None


def day_number(text):
    """Day 1 is the epoch."""
    return (parse_date(text) - parse_date(EPOCH)).days + 1


def playable(text, today):
    """A date may be played when it is a real date between the epoch and `today`, both included."""
    d, t = parse_date(text), parse_date(today)
    return d is not None and t is not None and parse_date(EPOCH) <= d <= t


def add_days(text, n):
    return (parse_date(text) + timedelta(days=n)).isoformat()


# --- generating a job -----------------------------------------------------------------------------------
def _key(date_text):
    return "heist-daily-%s|%s" % (GENERATOR_VERSION, date_text)


def _offer(content, key, k):
    """Eight candidates from the WHOLE roster (the daily ignores career unlocks), all five roles covered."""
    ranked = sorted(content.crew_order, key=lambda cid: engine.roll(key, k, "offer", cid))
    chosen = []
    for role in content.roles:
        for cid in ranked:
            if content.crew[cid]["role"] == role:
                chosen.append(cid)
                break
    for cid in ranked:
        if len(chosen) >= OFFER_SIZE:
            break
        if cid not in chosen:
            chosen.append(cid)
    return sorted(chosen, key=lambda cid: content.crew_order.index(cid))


def _plan_for(content, target_id, crew):
    return bots.greedy_plan(content, target_id, list(crew), kinds=bots.scouted_kinds(content, target_id))


def prove(content, target_id, offer, seed, key=""):
    """The fairness bar. Tries five-crew combinations of the offer in a date-derived order and returns the first
    MIN_CLEAN_CREWS that the greedy bot takes through the night with no alarm, as [{"crew", "net"}], or None."""
    combos = sorted(itertools.combinations(offer, 5), key=lambda c: engine.roll(key, "combo", ",".join(c)))
    found = []
    for combo in combos:
        crew = list(combo)
        out = engine.simulate(content, target_id, crew, _plan_for(content, target_id, crew), (), seed)["outcome"]
        if out["escaped"] and not out["alarm"]:
            found.append({"crew": crew, "net": out["net"]})
            if len(found) >= MIN_CLEAN_CREWS:
                return found
    return None


def spec(content, date_text):
    """The job for a date: {"date", "number", "target", "seed", "offer", "van", "witnesses", "par", "attempt"}.
    Memoised; the same date text always gives the same dict."""
    if parse_date(date_text) is None:
        raise ValueError("daily.spec needs a YYYY-MM-DD date")
    if date_text in _cache:
        return _cache[date_text]
    key = _key(date_text)
    targets = list(content.target_order)
    gear = list(content.gear)
    result = None
    for k in range(MAX_ATTEMPTS):
        target_id = targets[int(engine.roll(key, k, "target") * len(targets))]
        seed = int(engine.roll(key, k, "seed") * 2147483647)
        offer = _offer(content, key, k)
        witnesses = prove(content, target_id, offer, seed, "%s|%d" % (key, k))
        if witnesses is None:
            continue
        van = sorted(sorted(gear, key=lambda g: engine.roll(key, k, "van", g))[:VAN_SIZE], key=gear.index)
        result = {"date": date_text, "number": day_number(date_text) if date_text >= EPOCH else 0, "target": target_id,
                  "seed": seed, "offer": offer, "van": van, "witnesses": witnesses,
                  "par": min(w["net"] for w in witnesses), "attempt": k}
        break
    if result is None:                       # unreachable with the shipped content (tests cover hundreds of dates)
        raise RuntimeError("no fair daily job for %s" % date_text)
    if len(_cache) > 400:
        _cache.clear()
    _cache[date_text] = result
    return result


# --- results ------------------------------------------------------------------------------------------------
def tier_of(outcome, par):
    """busted (did not escape), escaped (alarm raised), clean, or par (clean and at least `par`)."""
    if not outcome["escaped"]:
        return "busted"
    if outcome["alarm"]:
        return "escaped"
    return "par" if outcome["net"] >= par else "clean"


def merge_record(old, tier, net):
    """The saved record for a date after another finished attempt: the best tier, the best payout, tries + 1."""
    old = old if isinstance(old, dict) else {}
    best_tier = max(old.get("tier", 0), TIERS.index(tier))
    return {"tier": best_tier, "net": max(old.get("net", 0), int(net)), "tries": min(999, old.get("tries", 0) + 1)}


def clean_days(raw):
    """Validated copy of the saved {date: {"tier", "net", "tries"}} map. Junk entries are dropped one by one."""
    out = {}
    if not isinstance(raw, dict):
        return out
    for text, rec in raw.items():
        if not isinstance(text, str) or not isinstance(rec, dict):
            continue
        d = parse_date(text)
        if d is None or not (parse_date(EPOCH) <= d <= parse_date(LAST_DATE)):
            continue
        tier, net, tries = rec.get("tier"), rec.get("net"), rec.get("tries")
        if any(isinstance(v, bool) or not isinstance(v, int) for v in (tier, net, tries)):
            continue
        out[text] = {"tier": max(0, min(len(TIERS) - 1, tier)), "net": max(0, min(10 ** 6, net)),
                     "tries": max(1, min(999, tries))}
        if len(out) >= MAX_DAYS_SAVED:
            break
    return out


def leaderboard_entry(date_text, record):
    """HOOK for the future daily board (a separate backend job, NOT built in this pass): the entry a board would
    take for one date. Pure; nothing calls a server with it."""
    return {"board": "heist-daily-job", "date": date_text, "score": int(record.get("net", 0)),
            "tier": TIERS[int(record.get("tier", 0))]}


def tally(days, today):
    """How many of the open days have been played, and how many of those ended in a clean getaway. No streaks."""
    open_days = day_number(today) if playable(today, today) else 0
    played = [d for d in days if playable(d, today)]
    return {"open": open_days, "played": len(played), "clean": sum(1 for d in played if days[d]["tier"] >= 2)}
