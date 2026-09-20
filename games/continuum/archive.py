"""Continuum -- K18: the settlement archive's record format and validation.

A player can file a snapshot of their current settlement (stats plus a
small 3D-scene thumbnail) into a browser-local gallery, and later view or
delete the entries or clear the whole archive. Continuum has no forced end
state, so "completed" is the player's call: they archive when they decide
this run is worth keeping.

Storage is the browser's `localStorage` (a per-device keepsake, like the
Settings panel's preferences, not part of the portable save code). Because
anything in `localStorage` can be edited or corrupted, every read goes
through `clean_records()`, which drops anything malformed, coerces nothing
it cannot verify, and caps both the record count and the thumbnail size.

Pure functions only (no DOM, no storage calls): `game.py` does the I/O.
"""

import json
import math
import re

import sim
import summary

STORAGE_KEY = "continuum-archive-v1"
MAX_RECORDS = 12
MAX_THUMB_CHARS = 60000  # a ~240px JPEG is a fraction of this
THUMB_PREFIX = "data:image/jpeg;base64,"
_THUMB_BODY = re.compile(r"^[A-Za-z0-9+/=]*$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RANKS = ("Bronze", "Silver", "Gold")


def clean_thumbnail(value):
    """A thumbnail data URL we are willing to render, else ''."""
    if not isinstance(value, str) or not value.startswith(THUMB_PREFIX):
        return ""
    if len(value) > MAX_THUMB_CHARS or not _THUMB_BODY.match(value[len(THUMB_PREFIX):]):
        return ""
    return value


def _int(value, low=0, high=10**7):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return min(max(int(value), low), high)


def make_record(campaign, achievements, saved_on, thumbnail=""):
    """Builds one archive record from a live campaign."""
    data = summary.summary(campaign)
    peak = data["peak_score"]
    return clean_record(
        {
            "saved_on": saved_on,
            "era": data["furthest_era"],
            "seasons": data["total_seasons"],
            "peak_population": data["peak_population"],
            "peak_score": None if peak is None else round(float(peak), 1),
            "rank": data["rank"],
            "scenario": campaign.state.scenario,
            "hard_mode": bool(campaign.state.hard_mode),
            "achievements": achievements,
            "thumb": thumbnail,
        }
    )


def clean_record(raw):
    """Validates one record; returns a clean dict or None."""
    if not isinstance(raw, dict):
        return None
    saved_on = raw.get("saved_on")
    era = raw.get("era")
    seasons = _int(raw.get("seasons"), 1)
    pop = _int(raw.get("peak_population"), 0)
    achievements = _int(raw.get("achievements"), 0, 999)
    if not isinstance(saved_on, str) or not _DATE.match(saved_on):
        return None
    if era not in sim.ERA_ORDER or seasons is None or pop is None or achievements is None:
        return None
    peak = raw.get("peak_score")
    if peak is not None:
        if isinstance(peak, bool) or not isinstance(peak, (int, float)) or not math.isfinite(peak):
            peak = None
        else:
            peak = min(max(float(peak), 0.0), 100.0)
    rank = raw.get("rank")
    return {
        "saved_on": saved_on,
        "era": era,
        "seasons": seasons,
        "peak_population": pop,
        "peak_score": peak,
        "rank": rank if rank in RANKS else None,
        "scenario": raw.get("scenario") if raw.get("scenario") in sim.SCENARIOS else sim.DEFAULT_SCENARIO,
        "hard_mode": raw.get("hard_mode") is True,
        "achievements": achievements,
        "thumb": clean_thumbnail(raw.get("thumb")),
    }


def clean_records(raw):
    """Validates a stored archive (a JSON string or an already-parsed list)."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, RecursionError):
            return []
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        record = clean_record(item)
        if record is not None:
            out.append(record)
    return out[-MAX_RECORDS:]


def add_record(records, record):
    """Returns a new list with `record` appended, oldest dropped past the cap."""
    cleaned = clean_record(record)
    out = list(records)
    if cleaned is not None:
        out.append(cleaned)
    return out[-MAX_RECORDS:]


def remove_record(records, index):
    """Returns a new list without the record at `index` (out of range is a no-op)."""
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(records):
        return list(records)
    return records[:index] + records[index + 1:]


def serialize(records):
    return json.dumps(clean_records(records))


def card_lines(record):
    """The plain-text stat lines K20's infographic card draws for a record."""
    lines = [
        f"{sim.ERA_LABEL[record['era']]} era, {record['seasons']} seasons",
        f"Peak population {record['peak_population']}",
    ]
    if record["peak_score"] is not None:
        lines.append(f"Peak sustainability {record['peak_score']:.0f} / 100")
    if record["rank"]:
        lines.append(f"{record['rank']} efficiency rank")
    lines.append(f"{sim.SCENARIOS[record['scenario']]['label']}" + (", Hard Mode" if record["hard_mode"] else ""))
    lines.append(f"{record['achievements']} achievements")
    return lines
