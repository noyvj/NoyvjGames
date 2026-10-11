"""Dead Reckoning -- the chart registry. A chart is a plain dict (see chartkit.py and CLAUDE.md for the schema). Charts are
content, not state: a save never contains one, only the id of the chart played.

Campaign charts live in charts_<chapter>.py; their par plans (the authored solutions) are generated into pars.py by
tools/check_charts.py --write. The practice generator's charts are made on demand (gen.py)."""

import importlib
import os
import sys

from charts_open import CHARTS as _OPEN
from charts_index import HAZARDS as _HAZARDS, INDEX as _INDEX
from pars import PARS, PARS2
import daily
import gen

# Lazy content packs (planning/LAZY-LOAD-REPORT.md, modules.json): chapter 1 is always here; the charts of chapters 2 to 7 live in
# their own module files, which the page fetches the first time the chapter is opened. What the chooser, the progress totals, the save
# cleaner and the achievements need from every chapter (ids, names, hazard ids) is the small generated charts_index.py, so none of
# them waits for a pack. On the page (Pyodide) a chapter is loaded on demand; under plain CPython (the tests, the authoring tools)
# every chapter is imported at once, through the very same ensure_chapter(), unless DR_LAZY=1 is set (the lazy-boot tests).
LAZY = sys.platform == "emscripten" or os.environ.get("DR_LAZY") == "1"

_DEFS = [
    {"id": "open", "name": "Open water", "blurb": "Heading, speed and time. Then charted hazards, a stream, and land to go round.",
     "module": None, "pack": None},
    {"id": "wind", "name": "Wind and leeway", "blurb": "A sailing ship slides a little downwind of her heading. Allow for it, and for the rocks it sets you toward.",
     "module": "charts_wind", "pack": "chapter-wind"},
    {"id": "fixes", "name": "Fixes and landmarks", "blurb": "Watch by watch: sail a leg, take a bearing and a distance off a landmark, correct your plot, plan the next.",
     "module": "charts_fixes", "pack": "chapter-fixes"},
    {"id": "fog", "name": "Fog and unmarked dangers", "blurb": "No landmark is visible and some dangers are not on the chart. Find one, and it is charted for good.",
     "module": "charts_fog", "pack": "chapter-fog"},
    {"id": "tides", "name": "Tides", "blurb": "A stream that runs, slackens and turns. Read the timetable, and lie at anchor for a fair one.",
     "module": "charts_tides", "pack": "chapter-tides"},
    {"id": "compass", "name": "Compass error", "blurb": "The compass does not read true. Steer the heading that is already corrected.",
     "module": "charts_compass", "pack": "chapter-compass"},
    {"id": "ships", "name": "Two ships", "blurb": "Plan two vessels on one chart. Each has its own flag and deadline; keep them clear of each other while both are under way.",
     "module": "charts_two", "pack": "chapter-ships"},
]
PRACTICE_PACK = "practice"       # genmake.py: the practice and daily chart generator
TWO_SHIPS_PACK = "two-ships"     # gentwo.py: the second ship of a two-ship practice chart

# A chapter's "charts" list holds {"id", "name"} stubs from the index until the chapter is loaded, then the full chart dicts (the same
# list object, filled in place). Code that needs a chart's body asks get_chart(), which loads the chapter if it can.
CHAPTERS = [dict(d, charts=[{"id": cid, "name": name} for cid, name in _INDEX[d["id"]]], loaded=False) for d in _DEFS]
_BY_ID = {c["id"]: c for c in CHAPTERS}
CLEAR_TO_OPEN_NEXT = 4          # charts cleared (one star or more) in a chapter before the next chapter opens

CHARTS = {}                     # chart id -> the chart dict, for every chapter that is loaded
ORDER = [cid for chapter in CHAPTERS for cid, _name in _INDEX[chapter["id"]]]
CHAPTER_OF = {cid: chapter["id"] for chapter in CHAPTERS for cid, _name in _INDEX[chapter["id"]]}
_NAME_OF = {cid: name for rows in _INDEX.values() for cid, name in rows}


def ensure_chapter(chapter_id):
    """Load a chapter's charts into CHARTS if its module is on the page. True when the chapter is loaded. Never raises: a pack that has
    not arrived (ImportError), or one that no longer matches the index, simply leaves the chapter unloaded."""
    chapter = _BY_ID.get(chapter_id)
    if chapter is None:
        return False
    if chapter["loaded"]:
        return True
    if chapter["module"] is None:
        full = _OPEN
    else:
        try:
            importlib.invalidate_caches()           # a file written after start-up is invisible to import otherwise
            full = importlib.import_module(chapter["module"]).CHARTS
        except (ImportError, AttributeError):
            return False
    if [c["id"] for c in full] != [cid for cid, _name in _INDEX[chapter_id]]:
        return False
    chapter["charts"][:] = full
    for c in full:
        CHARTS[c["id"]] = c
    chapter["loaded"] = True
    return True


def chapter_loaded(chapter_id):
    return bool(_BY_ID.get(chapter_id, {}).get("loaded"))


def pack_of_chapter(chapter_id):
    return _BY_ID.get(chapter_id, {}).get("pack")


def packs_for(chart_id):
    """The lazy packs a chart (campaign, practice or daily id) needs on the page, whether or not they are loaded yet."""
    chapter = CHAPTER_OF.get(chart_id)
    if chapter is not None:
        pack = _BY_ID[chapter]["pack"]
        return [pack] if pack else []
    parsed = gen.parse_ex(chart_id) if gen.is_practice_id(chart_id) else None
    if parsed is not None:
        return [PRACTICE_PACK] + ([TWO_SHIPS_PACK] if parsed[2] else [])
    if daily.is_daily_id(chart_id):
        return [PRACTICE_PACK]
    return []


def packs_for_code(code):
    """The packs a practice share code needs (the chart is made from the code), or []."""
    parsed = gen.parse_ex(code)
    return [PRACTICE_PACK] + ([TWO_SHIPS_PACK] if parsed and parsed[2] else []) if parsed else []


def pack_ready(pack_id):
    """True when the pack's module is on the page (a chapter is loaded into CHARTS as a side effect)."""
    if pack_id == PRACTICE_PACK:
        return gen.ready()
    if pack_id == TWO_SHIPS_PACK:
        try:
            importlib.invalidate_caches()
            importlib.import_module("gentwo")
            return True
        except ImportError:
            return False
    for chapter in CHAPTERS:
        if chapter["pack"] == pack_id:
            return ensure_chapter(chapter["id"])
    return False


def name_of(chart_id):
    """A campaign chart's name, from the index (no pack needed), or None."""
    return _NAME_OF.get(chart_id)


def is_campaign_id(chart_id):
    return chart_id in CHAPTER_OF


def get_chart(chart_id):
    """A campaign chart, or a practice or daily chart made on demand from its id. None when it is unknown, or when the lazy pack it
    needs (a chapter, the practice generator, the two-ship option) is not on the page yet: see packs_for()."""
    chart = CHARTS.get(chart_id)
    if chart is None and chart_id in CHAPTER_OF and ensure_chapter(CHAPTER_OF[chart_id]):
        chart = CHARTS.get(chart_id)
    if chart is None and gen.is_practice_id(chart_id):
        chart = gen.from_id(chart_id)
    if chart is None and daily.is_daily_id(chart_id) and gen.ready():
        chart = daily.chart_for(daily.date_of(chart_id))
    return chart


def all_charts():
    """Every campaign chart that is loaded (all of them under CPython; on the page, the chapters opened so far)."""
    for chapter in CHAPTERS:
        ensure_chapter(chapter["id"])
    return [CHARTS[cid] for cid in ORDER if cid in CHARTS]


def par_legs(chart_id):
    """The authored solution, as a list of legs (a fresh copy), or None."""
    legs = PARS.get(chart_id)
    if legs is None and (gen.is_practice_id(chart_id) or daily.is_daily_id(chart_id)):
        made = get_chart(chart_id)
        legs = made["par_legs"] if made else None
    return [dict(leg) for leg in legs] if legs else None


def par_legs2(chart_id):
    """Ship B's authored solution on a two-ship chart (a fresh copy), or None."""
    legs = PARS2.get(chart_id)
    if legs is None and (gen.is_practice_id(chart_id) or daily.is_daily_id(chart_id)):
        made = get_chart(chart_id)
        legs = (made.get("ship2") or {}).get("par_legs") if made else None
    return [dict(leg) for leg in legs] if legs else None


def hazard_ids():
    """chart id -> the ids of its hazards (used to validate a loaded save's `discovered` lists). From the index: no pack needed."""
    return {cid: set(ids) for cid, ids in _HAZARDS.items()}


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
    if gen.is_practice_id(chart_id) or daily.is_daily_id(chart_id):
        return True
    return CHAPTER_OF.get(chart_id) in unlocked_chapters(records)


ensure_chapter("open")          # chapter 1 is part of the core
if not LAZY:
    for _chapter in CHAPTERS:
        ensure_chapter(_chapter["id"])
