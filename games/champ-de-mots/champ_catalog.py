"""Loading the course data: the combined FREN151/FREN152 catalog, the supplementary notes (cultural notes, liaison questions,
pronunciation risks) and the chapter titles. Read once when the game starts.
Part of the split of the old single-file game.py: see "File map" in games/champ-de-mots/CLAUDE.md.
"""

import json

from champ_rules import CATALOG_FILENAME, SUPPLEMENTARY_NOTES_FILENAME


def _read_json_asset(filename, window_attr):
    """The page's boot script fetches each JSON asset and hands it to Python
    as a window global before running this file; the pytest harness sets
    the same attribute on its fake `js` module. A filesystem fallback keeps
    the module importable outside both. Shared by the catalog and the
    supplementary-notes file below -- same loading contract, different
    filename/global name."""
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        js = None

    raw = getattr(js, window_attr, None) if js is not None else None
    if raw is not None:
        return str(raw)

    import os

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, filename), encoding="utf-8") as handle:
        return handle.read()


def _read_catalog_json():
    return _read_json_asset(CATALOG_FILENAME, "CATALOG_JSON")


def _read_supplementary_notes_json():
    return _read_json_asset(SUPPLEMENTARY_NOTES_FILENAME, "SUPPLEMENTARY_NOTES_JSON")


CATALOG = json.loads(_read_catalog_json())

CHAPTER_TITLES = {str(c["number"]): c["title"] for c in CATALOG.get("chapters", [])}

# Improvement Ideas §4: optional cultural/usage notes, sourced from the
# slideshow cross-check's supplementary file (2026-09-13 merge). Keyed by
# `sequence` (a week can have at most one note in the source data today;
# a list-of-notes-per-sequence would be the natural extension if that ever
# changes). A missing/unparseable file degrades to "no cultural notes"
# rather than crashing the whole game -- this is optional flavor, not core
# gameplay, the same posture _dispatch_report() already takes for a failed
# report send.
try:
    SUPPLEMENTARY_NOTES = json.loads(_read_supplementary_notes_json())
except (ValueError, OSError, NameError):
    # NameError included defensively: `_read_json_asset()`'s filesystem
    # fallback (for running outside both Pyodide and the pytest harness)
    # reads `__file__`, which a plain `pyodide.runPythonAsync(code)` string
    # exec never defines -- if the boot script's own window global for this
    # file is ever missing again (as it genuinely was, live-breaking the
    # whole page on load, before this file's own boot script was fixed to
    # actually set window.SUPPLEMENTARY_NOTES_JSON), this must degrade to
    # "no cultural notes/liaison drill/pronunciation notes" exactly as
    # already documented above, not crash the entire module import.
    SUPPLEMENTARY_NOTES = {}

CULTURAL_NOTES_BY_SEQUENCE = {
    entry["sequence"]: entry["note"]
    for entry in SUPPLEMENTARY_NOTES.get("cultural_notes", [])
}

# Improvement Ideas addendum: liaison/elision as a real practice type. Unlike
# every other practice question, these aren't generated from a plot -- they're
# hand-authored (same posture as Milestone 13's bonus sentences: some content
# genuinely needs a human, not a mechanical recombination of catalog facts),
# grounded one-for-one in the TTS pronunciation watchlist half of the same
# supplementary-notes file (the other half of that file, cultural_notes, is
# already wired up above). Not every watchlist entry became a question --
# "travailler is commonly mispronounced" (sequence 4) is a tutor's listen-check
# flag, not a testable mechanical fact, so it stayed a note rather than being
# forced into a quiz.
LIAISON_DRILL_QUESTIONS = SUPPLEMENTARY_NOTES.get("liaison_drill", [])

# Milestone 24: a mispronunciation-risk report button. Most of the TTS
# watchlist's 11 entries describe a *rule* (liaison, an ending pattern) with
# no single catalog item to attach a note to -- those are already covered
# abstractly by the liaison drill above. A handful, though, name one exact
# catalog item by its own fr text ("travailler", flagged by the tutor as
# commonly mispronounced by learners) -- computed by membership rather than
# hardcoded, so a future catalog/watchlist edit that makes another entry
# resolve cleanly picks it up automatically instead of needing a second,
# parallel list kept in sync by hand.
_CATALOG_FR_TEXTS = {
    item["fr"]
    for week in CATALOG["weeks"]
    for topic in week["topics"]
    for item in topic.get("items", [])
    if item.get("fr")
}
PRONUNCIATION_RISK_NOTES = {
    entry["item"]: entry["note"]
    for entry in SUPPLEMENTARY_NOTES.get("tts_watchlist", [])
    if entry["item"] in _CATALOG_FR_TEXTS
}
