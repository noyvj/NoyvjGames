"""Dead Reckoning -- the chart registry. A chart is a plain dict (see chartkit.py and CLAUDE.md for the schema). Charts are
content, not state: a save never contains one, only the id of the chart played.

Campaign charts live in charts_<chapter>.py; their par plans (the authored solutions) are generated into pars.py by
tools/check_charts.py --write. The practice generator's charts are made on demand (gen.py)."""

from charts_open import CHARTS as _OPEN
from charts_wind import CHARTS as _WIND
from charts_fixes import CHARTS as _FIXES
from charts_fog import CHARTS as _FOG
from charts_tides import CHARTS as _TIDES
from charts_compass import CHARTS as _COMPASS
from pars import PARS
import gen

CHAPTERS = [
    {"id": "open", "name": "Open water", "blurb": "Heading, speed and time. Then charted hazards, a stream, and land to go round.",
     "charts": _OPEN},
    {"id": "wind", "name": "Wind and leeway", "blurb": "A sailing ship slides a little downwind of her heading. Allow for it, and for the rocks it sets you toward.",
     "charts": _WIND},
    {"id": "fixes", "name": "Fixes and landmarks", "blurb": "Watch by watch: sail a leg, take a bearing and a distance off a landmark, correct your plot, plan the next.",
     "charts": _FIXES},
    {"id": "fog", "name": "Fog and unmarked dangers", "blurb": "No landmark is visible and some dangers are not on the chart. Find one, and it is charted for good.",
     "charts": _FOG},
    {"id": "tides", "name": "Tides", "blurb": "A stream that runs, slackens and turns. Read the timetable, and lie at anchor for a fair one.",
     "charts": _TIDES},
    {"id": "compass", "name": "Compass error", "blurb": "The compass does not read true. Steer the heading that is already corrected.",
     "charts": _COMPASS},
]
CLEAR_TO_OPEN_NEXT = 4          # charts cleared (one star or more) in a chapter before the next chapter opens

CHARTS = {c["id"]: c for chapter in CHAPTERS for c in chapter["charts"]}
ORDER = [c["id"] for chapter in CHAPTERS for c in chapter["charts"]]
CHAPTER_OF = {c["id"]: chapter["id"] for chapter in CHAPTERS for c in chapter["charts"]}


def get_chart(chart_id):
    """A campaign chart, or a practice chart made on demand from its id (practice-<difficulty>-<seed in base 36>)."""
    chart = CHARTS.get(chart_id)
    if chart is None and gen.is_practice_id(chart_id):
        chart = gen.from_id(chart_id)
    return chart


def all_charts():
    return [CHARTS[cid] for cid in ORDER]


def par_legs(chart_id):
    """The authored solution, as a list of legs (a fresh copy), or None."""
    legs = PARS.get(chart_id)
    if legs is None and gen.is_practice_id(chart_id):
        made = gen.from_id(chart_id)
        legs = made["par_legs"] if made else None
    return [dict(leg) for leg in legs] if legs else None


def hazard_ids():
    """chart id -> the ids of its hazards (used to validate a loaded save's `discovered` lists)."""
    return {cid: {h["id"] for h in c.get("hazards", ())} for cid, c in CHARTS.items()}


def next_chart_id(chart_id):
    if chart_id not in ORDER:
        return None
    i = ORDER.index(chart_id)
    return ORDER[i + 1] if i + 1 < len(ORDER) else None


def chapter_cleared(chapter, records):
    """How many of a chapter's charts have at least one star in the given records (chart id -> record)."""
    return sum(1 for c in chapter["charts"] if records.get(c["id"], {}).get("stars", 0) >= 1)


def unlocked_chapters(records):
    """The ids of the chapters the player may play: the first always, each next one after CLEAR_TO_OPEN_NEXT in the last."""
    out = []
    for i, chapter in enumerate(CHAPTERS):
        if i == 0:
            out.append(chapter["id"])
            continue
        prev = CHAPTERS[i - 1]
        if CHAPTERS[i - 1]["id"] in out and chapter_cleared(prev, records) >= min(CLEAR_TO_OPEN_NEXT, len(prev["charts"])):
            out.append(chapter["id"])
    return out


def is_unlocked(chart_id, records):
    if gen.is_practice_id(chart_id):
        return True
    return CHAPTER_OF.get(chart_id) in unlocked_chapters(records)
