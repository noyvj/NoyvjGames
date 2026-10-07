"""Continuum -- K-18: data export (CSV and JSON of the run).

Builds the text of three downloads from the per-season stat history
(`statlog.py`) and the policy log (Council Minutes, `minutes.py`):

- `stats_csv`: one row per completed season, one column per tracked stat.
- `minutes_csv`: one row per Council Minutes motion.
- `run_json`: everything above in one JSON document, with the settlement's
  name and a small header.

Pure functions of plain data (no DOM, no storage, no clock): `game.py` gathers
the inputs and hands the finished text to the download helper in `card.js`.

Safety. Every text cell goes through `csv_cell`, which (a) quotes anything
containing a comma, quote or line break, and (b) defuses spreadsheet formula
injection: a value that starts with `=`, `+`, `-`, `@`, a tab or a carriage
return gets a leading apostrophe, so opening the file in a spreadsheet can
never run something a hand-edited save put in a name or a motion. Numbers are
written as plain decimals (never `nan`/`inf`: the history is validated on
read, and a non-finite value would be written as an empty cell anyway).
"""

import json
import math

import minutes
import sim
import statlog

CSV_MIME = "text/csv"
JSON_MIME = "application/json"
_FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")


def csv_cell(value):
    """One CSV cell as text."""
    if value is None or isinstance(value, bool):
        return "" if value is None else ("true" if value else "false")
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            return ""
        if isinstance(value, float):
            text = f"{value:.3f}".rstrip("0").rstrip(".")
            return "0" if text in ("", "-0") else text
        return str(value)
    text = str(value)
    if text.startswith(_FORMULA_STARTS):
        text = "'" + text
    if any(ch in text for ch in ',"\n\r'):
        text = '"' + text.replace('"', '""') + '"'
    return text


def _line(cells):
    return ",".join(csv_cell(c) for c in cells)


def _era_name(index):
    try:
        return sim.ERA_LABEL[sim.ERA_ORDER[int(index)]]
    except (IndexError, ValueError, TypeError):
        return ""


def stats_header():
    """Column titles: the three leading context columns, then every stat label."""
    return ["Year", "Season of year", "Era name"] + [statlog.COLUMN_LABEL[k] for k in statlog.COLUMN_KEYS]


def stats_csv(history):
    """The per-season stats as CSV text (header plus one row per season)."""
    rows = statlog.clean(history)
    seasons_per_year = 4
    names = ["Spring", "Summer", "Autumn", "Winter"]
    lines = [_line(stats_header())]
    for row in rows:
        season = int(statlog.value(row, "season"))
        index = max(1, season) - 1
        lead = [index // seasons_per_year + 1, names[index % seasons_per_year], _era_name(statlog.value(row, "era"))]
        lines.append(_line(lead + list(row)))
    return "\r\n".join(lines) + "\r\n"


def minutes_csv(entries):
    """The Council Minutes (policy log) as CSV text."""
    seasons_per_year = 4
    names = ["Spring", "Summer", "Autumn", "Winter"]
    lines = [_line(["Season", "Year", "Season of year", "Era", "Kind", "Minute"])]
    for entry in minutes.clean(entries):
        index = entry["season"] - 1
        lines.append(_line([
            entry["season"],
            index // seasons_per_year + 1,
            names[index % seasons_per_year],
            sim.ERA_LABEL[entry["era"]],
            entry["kind"],
            entry["text"],
        ]))
    return "\r\n".join(lines) + "\r\n"


def _typed_row(row):
    """A season row as a dict, whole-number columns written as integers."""
    out = {}
    for key, number in statlog.row_dict(row).items():
        out[key] = int(round(number)) if statlog.COLUMN_KIND.get(key) == "int" else number
    return out


def run_json(name, scenario, hard_mode, history, entries):
    """Everything in one JSON document (indent 2, UTF-8 safe, no NaN)."""
    rows = statlog.clean(history)
    document = {
        "game": "continuum",
        "format": 1,
        "settlement": name or None,
        "scenario": scenario if scenario in sim.SCENARIOS else sim.DEFAULT_SCENARIO,
        "hard_mode": bool(hard_mode),
        "seasons": [_typed_row(row) for row in rows],
        "council_minutes": minutes.clean(entries),
    }
    return json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False)


def filename(kind, name, today):
    """A safe download name like `continuum-reed-ford-stats-2026-10-07.csv`."""
    slug = "".join(ch.lower() if ch.isascii() and ch.isalnum() else "-" for ch in (name or "settlement"))
    slug = "-".join(part for part in slug.split("-") if part)[:24] or "settlement"
    ext = "json" if kind == "run" else "csv"
    day = today if isinstance(today, str) and len(today) == 10 else "undated"
    return f"continuum-{slug}-{kind}-{day}.{ext}"
