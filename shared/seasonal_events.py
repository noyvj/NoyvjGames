"""Shared seasonal-events engine (planning/TODO.md W-4 / N).

Pure date logic for "the site has an event on" moments: big, widely known
holidays, each a short window around a date, doable in about fifteen minutes.
This module only answers WHICH events are active on a date and what a badge is
called; a game decides what its small event task is, draws its own banner and
grants the badge (see `badge_id`). Nothing here needs a backend.

An event is a plain dict:
    {"id": "halloween", "name": "Halloween",
     "when": {"kind": "fixed", "month": 10, "day": 31, "before": 6, "after": 1}}
`when.kind` is one of
    fixed        month, day
    easter       (Easter Sunday; offsets via before/after)
    nth_weekday  month, weekday (0=Monday), n (1-based; -1 = last)
    table        key into seasonal-dates.json ("hanukkah", "lunar_new_year",
                 "diwali"): the window is the listed range (or the listed day
                 with before/after); years the table lacks are never active.
`before`/`after` widen the window by that many days either side of the anchor.

Dates are compared as datetime.date, so the caller passes the player's local
"today" (a game gets it from the browser). `DEFAULT_EVENTS` is the starting set
of big, internationally spread dates; a game lists the ids it supports.
"""

import json
import os
from datetime import date, timedelta

DEFAULT_EVENTS = [
    {"id": "new_year", "name": "New Year", "when": {"kind": "fixed", "month": 1, "day": 1, "before": 2, "after": 3}},
    {"id": "valentines", "name": "Valentine's Day", "when": {"kind": "fixed", "month": 2, "day": 14, "before": 3, "after": 1}},
    {"id": "lunar_new_year", "name": "Lunar New Year", "when": {"kind": "table", "table": "lunar_new_year", "before": 1, "after": 5}},
    {"id": "easter", "name": "Easter", "when": {"kind": "easter", "before": 3, "after": 1}},
    {"id": "independence_day", "name": "4th of July", "when": {"kind": "fixed", "month": 7, "day": 4, "before": 3, "after": 1}},
    {"id": "halloween", "name": "Halloween", "when": {"kind": "fixed", "month": 10, "day": 31, "before": 6, "after": 1}},
    {"id": "diwali", "name": "Diwali", "when": {"kind": "table", "table": "diwali", "before": 3, "after": 2}},
    {"id": "thanksgiving", "name": "Thanksgiving", "when": {"kind": "nth_weekday", "month": 11, "weekday": 3, "n": 4, "before": 3, "after": 1}},
    {"id": "hanukkah", "name": "Hanukkah", "when": {"kind": "table", "table": "hanukkah"}},
    {"id": "christmas", "name": "Christmas", "when": {"kind": "fixed", "month": 12, "day": 25, "before": 7, "after": 1}},
]

_DATES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seasonal-dates.json")
_dates_cache = None


def load_dates(text=None):
    """The moving-holiday tables (parsed once; `text` lets a game hand in the
    JSON it fetched, since Pyodide has no shared/ folder on its file system)."""
    global _dates_cache
    if text is not None:
        try:
            _dates_cache = json.loads(text)
        except (ValueError, TypeError):
            _dates_cache = {}
        return _dates_cache
    if _dates_cache is None:
        try:
            with open(_DATES_PATH, encoding="utf-8") as handle:
                _dates_cache = json.load(handle)
        except (OSError, ValueError):
            _dates_cache = {}
    return _dates_cache


def easter_sunday(year):
    """Western (Gregorian) Easter Sunday, by the anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    ell = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ell) // 451
    month, day = divmod(h + ell - 7 * m + 114, 31)
    return date(year, month, day + 1)


def nth_weekday(year, month, weekday, n):
    """The nth (1-based) given weekday of a month; n=-1 means the last one."""
    if n == -1:
        last = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
        return last - timedelta(days=(last.weekday() - weekday) % 7)
    first = date(year, month, 1)
    return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))


def _parse(text):
    try:
        year, month, day = (int(part) for part in str(text).split("-"))
        return date(year, month, day)
    except (ValueError, TypeError):
        return None


def event_window(event, year, dates=None):
    """(start, end) dates of this event in `year`, or None (bad rule, or a
    moving holiday the tables do not cover for that year)."""
    when = event.get("when") if isinstance(event, dict) else None
    if not isinstance(when, dict):
        return None
    kind = when.get("kind")
    before, after = int(when.get("before", 0)), int(when.get("after", 0))
    try:
        if kind == "fixed":
            anchor_start = anchor_end = date(year, int(when["month"]), int(when["day"]))
        elif kind == "easter":
            anchor_start = anchor_end = easter_sunday(year)
        elif kind == "nth_weekday":
            anchor_start = anchor_end = nth_weekday(year, int(when["month"]), int(when["weekday"]), int(when["n"]))
        elif kind == "table":
            table = (dates if dates is not None else load_dates()).get(when.get("table"), {})
            entry = table.get("years", {}).get(str(year)) if isinstance(table, dict) else None
            if isinstance(entry, list) and len(entry) == 2:
                anchor_start, anchor_end = _parse(entry[0]), _parse(entry[1])
            else:
                anchor_start = anchor_end = _parse(entry)
            if anchor_start is None or anchor_end is None:
                return None
        else:
            return None
    except (KeyError, ValueError, TypeError):
        return None
    return anchor_start - timedelta(days=before), anchor_end + timedelta(days=after)


def active_events(today, events=None, dates=None):
    """The events whose window includes `today`, in list order. The window is
    tried in today's year and the year before/after so New Year style windows
    that straddle December and January work from either side."""
    events = DEFAULT_EVENTS if events is None else events
    found = []
    for event in events:
        for year in (today.year - 1, today.year, today.year + 1):
            window = event_window(event, year, dates)
            if window and window[0] <= today <= window[1]:
                found.append(dict(event, year=year))
                break
    return found


def badge_id(event, year=None):
    """The badge a completed event grants, e.g. 'halloween-2026' (the year is
    the one the event's window started in, so a New Year window that runs into
    January still counts for the year it began)."""
    return f"{event['id']}-{event.get('year') if year is None else year}"


def hub_badge_id(event, year=None):
    """`badge_id` as the hub accepts it: lowercase slug with hyphens only
    (`new_year` becomes `new-year-2027`; the hub's event-badge contract is
    /^[a-z0-9-]{1,64}$/). `shared/seasonal-events.js` `badgeId` returns exactly this."""
    slug = "".join(ch if ch.isalnum() and ch.isascii() or ch == "-" else "-" for ch in badge_id(event, year).lower())
    return slug[:64]


def badge_entry(event, earned_at, year=None, label=None):
    """The `{id, label, earned_at}` dict a game stores in its save's
    `event_badges` list (hub contract R2-Z23b). `earned_at` is an ISO date such
    as today's `date.isoformat()`; the label defaults to "<name> <year>"."""
    shown_year = event.get("year") if year is None else year
    text = (label if label else f"{event.get('name', event['id'])} {shown_year}")[:60]
    return {"id": hub_badge_id(event, year), "label": text, "earned_at": str(earned_at)[:32]}
