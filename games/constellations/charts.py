"""Constellations -- the chart set and its gating (pure functions of the solved set, so state only ever goes up).

The chart data itself lives in the generated modules charts_s1.py, charts_s2.py, ... (one per sky season); this module collects them,
builds the rules object (sky.Chart) for each chart on first use, and decides which seasons are open.
"""

import charts_s1
import charts_s2
import charts_s3
import charts_s4
import charts_s5
import sky

_MODULES = (charts_s1, charts_s2, charts_s3, charts_s4, charts_s5)
OPEN_AT = 5                                  # season n+1 opens when this many charts of season n are done (any five)
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

SEASONS = [dict(m.SEASON, charts=m.CHARTS) for m in _MODULES]
ALL = [c for season in SEASONS for c in season["charts"]]
BY_ID = {c["id"]: c for c in ALL}
ORDER = [c["id"] for c in ALL]

_RULES = {}


def rules(chart_id):
    """The sky.Chart (rules, conflicts) of a chart, built once."""
    if chart_id not in _RULES:
        _RULES[chart_id] = sky.Chart(BY_ID[chart_id])
    return _RULES[chart_id]


def season_done(solved, s):
    return sum(1 for c in SEASONS[s]["charts"] if c["id"] in solved)


def season_need(s):
    """How many charts of the season before must be done to open season s (0 for the first)."""
    return 0 if s == 0 else min(OPEN_AT, len(SEASONS[s - 1]["charts"]))


def season_open(solved, s):
    return s == 0 or season_done(solved, s - 1) >= season_need(s)


def chart_open(solved, chart_id):
    return chart_id in BY_ID and season_open(solved, BY_ID[chart_id]["season"])


def seasons_finished(solved):
    return sum(1 for s in range(len(SEASONS)) if season_done(solved, s) == len(SEASONS[s]["charts"]))


def star_total(solved):
    return sum(len(BY_ID[cid]["stars"]) for cid in solved)
