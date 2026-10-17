"""Constants and presets, the achievement and changelog catalogs, date and clock helpers, the FNV hash, the seeded Rng and tile labels: the pure helpers every other module uses."""

import datetime
import json
import re

import signal_runstate as runstate


GAME_ID = "signal"
SCHEMA = 1
SEED_VERSION = "v1"

# Puzzle #1 is the UTC day the game first shipped, fixed in the release
# commit and never changed afterwards (planning/signal-plan.md, decision 5).
# app.js mirrors this constant for the engine-less archive calendar, and a
# test asserts the two agree.
EPOCH = "2026-09-27"

# Presets. "top" is only a display ceiling (readings above it draw as the
# tallest bar), tuned so typical readings use the whole glyph range.
PRESETS = {
    "easy": {
        "label": "Easy", "letter": "E", "size": 9, "k": 2, "radius": 4, "spacing": 3,
        "budget": 8, "top": 5, "assist": True, "daily": True,
    },
    "hard": {
        "label": "Hard", "letter": "H", "size": 9, "k": 4, "radius": 4, "spacing": 2,
        "budget": 9, "top": 8, "assist": False, "daily": True,
    },
    "wide": {
        "label": "Wide", "letter": "W", "size": 13, "k": 4, "radius": 5, "spacing": 3,
        "budget": 12, "top": 10, "assist": False, "daily": False, "sample": 100,
    },
    "bigsky": {
        "label": "Big Sky", "letter": "B", "size": 15, "k": 5, "radius": 6, "spacing": 3,
        "budget": 14, "top": 12, "assist": False, "daily": False, "sample": 100,
    },
}
PRESET_ORDER = ("easy", "hard", "wide", "bigsky")
DAILY_MODES = tuple(k for k in PRESET_ORDER if PRESETS[k]["daily"])
LETTER_TO_PRESET = {p["letter"]: key for key, p in PRESETS.items()}

# A puzzle is accepted only if a greedy solver identifies it in at most
# budget - PAR_MARGIN pings, so a sensible player always has slack.
PAR_MARGIN = 2
MAX_ATTEMPTS = 80
SOLUTION_SAMPLE = 200
MAX_DAYS = 800

GLYPHS = "▁▂▃▄▅▆▇█"  # low bar .. full block
ASCII_GLYPHS = ".:+#"
COLUMN_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

CODE_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CODE_LENGTH = 5


# --------------------------------------------------------------------------
# Static assets (achievements.json / changelog.json). The boot script fetches
# them and sets window globals; the filesystem fallback keeps the module
# importable and testable outside a browser with no test-only special-casing
# (ACHIEVEMENTS-SYSTEM-DESIGN.md section 2).


def _read_json_asset(name, global_name):
    raw = None
    try:
        import js  # noqa: WPS433 (only exists inside Pyodide)
        raw = getattr(js, global_name, None)
        if raw is not None:
            raw = str(raw)
    except ImportError:
        raw = None
    if raw is None:
        import os
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, name), encoding="utf-8") as handle_:
            raw = handle_.read()
    return json.loads(raw)


def _load_catalogs():
    ach = _read_json_asset("achievements.json", "ACHIEVEMENTS_JSON")["achievements"]
    log = _read_json_asset("changelog.json", "CHANGELOG_JSON")
    if isinstance(log, dict):
        log = log["changelog"]
    log = sorted(log, key=lambda entry: entry["date"], reverse=True)
    return ach, log


ACHIEVEMENTS, CHANGELOG = _load_catalogs()
ACHIEVEMENT_IDS = [a["id"] for a in ACHIEVEMENTS]


# --------------------------------------------------------------------------
# Pure helpers: dates, RNG, coordinates


_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


def parse_date(text):
    """A datetime.date for a strict YYYY-MM-DD string, else None."""
    if not isinstance(text, str) or not _DATE_RE.match(text):
        return None
    try:
        return datetime.date.fromisoformat(text)
    except ValueError:
        return None


def puzzle_number(date_text):
    """Days since EPOCH + 1 (the launch day is puzzle #1)."""
    return (parse_date(date_text) - parse_date(EPOCH)).days + 1


def _real_clock():
    return datetime.datetime.now(datetime.timezone.utc).date()


runstate._clock = _real_clock


def set_clock(func):
    """Tests inject a fixed UTC date; None restores the real clock."""
    runstate._clock = func or _real_clock


def utc_today():
    return runstate._clock().isoformat()


def fnv1a32(text):
    """32-bit FNV-1a of the UTF-8 bytes (integer-only, so identical everywhere)."""
    h = 0x811C9DC5
    for byte in text.encode("utf-8"):
        h ^= byte
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


class Rng:
    """mulberry32. Integer-only so every Python (and any port) agrees."""

    def __init__(self, seed):
        self.state = seed & 0xFFFFFFFF

    def random(self):
        self.state = (self.state + 0x6D2B79F5) & 0xFFFFFFFF
        t = self.state
        t = ((t ^ (t >> 15)) * (t | 1)) & 0xFFFFFFFF
        t ^= (t + (((t ^ (t >> 7)) * (t | 61)) & 0xFFFFFFFF)) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296

    def below(self, n):
        return int(self.random() * n)


def cell_label(r, c):
    """Spreadsheet-style label: column letter then 1-based row, e.g. D4."""
    return "%s%d" % (COLUMN_LETTERS[c], r + 1)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)
