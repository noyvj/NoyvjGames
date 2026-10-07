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

import naming
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


def make_record(campaign, achievements, saved_on, thumbnail="", name="", researched=None, minutes=None):
    """Builds one archive record from a live campaign.

    `name` (K-24), `researched` (discoveries made) and `minutes` (time played)
    are optional extras, stored only when given, so older records and callers
    stay valid.
    """
    data = summary.summary(campaign)
    peak = data["peak_score"]
    return clean_record(
        {
            "name": name,
            "researched": researched,
            "minutes": minutes,
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
    record = {
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
    # Optional extras: present only when valid, so a record without them is still a valid record.
    name = naming.clean(raw.get("name"))
    if name:
        record["name"] = name
    researched = _int(raw.get("researched"), 0, 10**4)
    if researched is not None:
        record["researched"] = researched
    minutes = _int(raw.get("minutes"), 0, 10**6)
    if minutes is not None:
        record["minutes"] = minutes
    return record


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


_SAME_KEYS = ("era", "seasons", "peak_population", "peak_score", "rank", "scenario", "hard_mode", "achievements", "name")


def same_settlement(a, b):
    """True when two records describe the same settlement in the same state
    (everything but the filing date and the picture), so filing it twice in
    a row does not add a duplicate."""
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
    return all(a.get(key) == b.get(key) for key in _SAME_KEYS)


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
    if "researched" in record:
        lines.append(f"{record['researched']} discoveries")
    if "minutes" in record:
        lines.append(f"{record['minutes']} minutes played")
    return lines


def title_of(record):
    """The settlement's name for a heading (the game's own name when it has none)."""
    return naming.title(record.get("name", "") if isinstance(record, dict) else "")


def record_label(record, index=None):
    """A short label that tells two archive entries apart: the name, else the era and filing date."""
    name = record.get("name", "")
    where = f"{sim.ERA_LABEL[record['era']]} era, season {record['seasons']}, filed {record['saved_on']}"
    if name:
        return f"{name} ({where})"
    return f"Settlement {index + 1} ({where})" if isinstance(index, int) else where


# --- K-19: compare two archived settlements --------------------------------
_RANK_ORDER = {"Bronze": 1, "Silver": 2, "Gold": 3}


def _delta_text(diff, unit="", digits=0):
    if diff == 0:
        return "\u25AC same"
    sign = "+" if diff > 0 else "\u2212"
    arrow = "\u25B2" if diff > 0 else "\u25BC"
    return f"{arrow} {sign}{abs(diff):.{digits}f}{unit}"


def _number_row(label, a, b, unit="", digits=0):
    """One comparable number row; `a`/`b` may be None (missing on an older record)."""
    if a is None or b is None:
        return {"label": label, "a": _show(a, unit, digits), "b": _show(b, unit, digits), "delta": "no comparison", "lead": None}
    diff = b - a
    lead = None if diff == 0 else ("b" if diff > 0 else "a")
    return {"label": label, "a": _show(a, unit, digits), "b": _show(b, unit, digits), "delta": _delta_text(diff, unit, digits), "lead": lead}


def _show(value, unit="", digits=0):
    return "not recorded" if value is None else f"{value:.{digits}f}{unit}"


def compare(a, b):
    """Rows comparing two cleaned archive records, A against B.

    Each row is {"label", "a", "b", "delta", "lead"} where `delta` is B minus A
    as text (the arrow and sign are words and symbols, never colour alone) and
    `lead` names the larger side ("a", "b") or is None when equal or unknown.
    Returns [] unless both are valid records.
    """
    if clean_record(a) is None or clean_record(b) is None:
        return []
    era_a, era_b = sim.era_index(a["era"]), sim.era_index(b["era"])
    rank_a, rank_b = _RANK_ORDER.get(a.get("rank")), _RANK_ORDER.get(b.get("rank"))
    rows = [
        {
            "label": "Furthest era",
            "a": sim.ERA_LABEL[a["era"]],
            "b": sim.ERA_LABEL[b["era"]],
            "delta": _delta_text(era_b - era_a, " eras" if abs(era_b - era_a) != 1 else " era"),
            "lead": None if era_a == era_b else ("b" if era_b > era_a else "a"),
        },
        _number_row("Seasons played", a["seasons"], b["seasons"]),
        _number_row("Peak population", a["peak_population"], b["peak_population"]),
        _number_row("Peak sustainability", a["peak_score"], b["peak_score"], " / 100", 0),
        {
            "label": "Efficiency rank",
            "a": a.get("rank") or "none",
            "b": b.get("rank") or "none",
            "delta": "no comparison" if rank_a is None or rank_b is None else _delta_text(rank_b - rank_a, " steps" if abs(rank_b - rank_a) != 1 else " step"),
            "lead": None if rank_a is None or rank_b is None or rank_a == rank_b else ("b" if rank_b > rank_a else "a"),
        },
        _number_row("Achievements", a["achievements"], b["achievements"]),
        _number_row("Discoveries researched", a.get("researched"), b.get("researched")),
        _number_row("Minutes played", a.get("minutes"), b.get("minutes")),
    ]
    scen_a = sim.SCENARIOS[a["scenario"]]["label"] + (", Hard Mode" if a["hard_mode"] else "")
    scen_b = sim.SCENARIOS[b["scenario"]]["label"] + (", Hard Mode" if b["hard_mode"] else "")
    rows.append({"label": "Opening", "a": scen_a, "b": scen_b, "delta": "same" if scen_a == scen_b else "different", "lead": None})
    return rows
