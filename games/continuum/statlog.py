"""Continuum -- K-27/K-16/K-18/K-14: the per-season stat history.

One small, saved record per completed season, so the City Views dashboard
can draw a sparkline next to every stat (K-27), explain the last change
(K-16, `explain.py`), the player can export the run (K-18, `dataexport.py`)
and the post-mortem can find where a run went wrong (K-14, `postmortem.py`).

It rides in `campaign.ui["stat_history"]` exactly like the policy log
(`minutes.py`) and the founder's log: a plain list stored in the existing
`ui` dict, so there is NO save-schema change. The key is only written once a
season has been played (a fresh settlement, or a save from before this
module existed, has no key at all), and every read goes through `clean()`,
so a hand-edited or junk value reads as "no history" and can never break a
panel. A row has exactly `len(COLUMNS)` finite numbers (bools are rejected,
values are clamped); a row of any other length (a save from a build with a
different column list) is dropped rather than guessed at.

The history is capped at `MAX_ROWS` seasons (30 years); the oldest rows drop
first, so a very long run never grows the save without bound. The record is
per settlement (founding a new settlement starts a fresh `ui`).

Pure functions only: no DOM, no storage. `game.py` calls `record()` once per
season and passes `campaign.ui` in.
"""

import math

import sim
import sustainability

KEY = "stat_history"
MAX_ROWS = 120
VALUE_LIMIT = 1e9

# (column key, human label, kind). `kind` is how a value is shown:
# "int" whole numbers, "pct" a 0..100 number shown with a % sign,
# "num" one decimal place.
_BASE_COLUMNS = [
    ("season", "Season", "int"),
    ("era", "Era (index)", "int"),
    ("population", "People", "int"),
    ("housing", "Shelter capacity", "int"),
    ("idle", "Unassigned workers", "int"),
    ("growth", "Growth progress", "pct"),
    ("calm", "Calm seasons in a row", "int"),
    ("food", "Food", "num"),
    ("food_storage", "Food storage capacity", "int"),
    ("materials", "Materials", "num"),
    ("tools", "Tools", "num"),
    ("knowledge", "Knowledge", "num"),
    ("surplus", "Surplus", "num"),
    ("land", "Land health", "pct"),
    ("extraction", "Taken from the land", "num"),
    ("sust_yield", "Sustainable yield", "num"),
    ("score", "Sustainability score", "num"),
    ("livability", "Livability", "num"),
    ("equity", "Equity", "num"),
    ("balance", "Resource balance", "num"),
    ("resilience", "Resilience", "num"),
    ("food_gathered", "Food gathered", "num"),
    ("materials_gathered", "Materials gathered", "num"),
    ("tools_made", "Tools made", "num"),
    ("knowledge_made", "Knowledge made", "num"),
    ("fed_pct", "People fed", "pct"),
    ("shelter_pct", "Shelter adequacy", "pct"),
    ("social_pct", "Gathering-place adequacy", "pct"),
    ("habitat_pct", "Habitat layout adequacy", "pct"),
    ("births", "Born", "int"),
    ("deaths", "Lost", "int"),
    ("spoiled", "Food spoiled", "num"),
    ("pollution", "Pollution", "pct"),
    ("sprawl", "Sprawl", "pct"),
    ("canal_staffing", "Canal staffing", "pct"),
    ("public_works", "Public works cover", "pct"),
    ("habitat_layout", "Habitat layout", "pct"),
    ("holdings_residents", "Holdings' residents", "int"),
    ("holdings_served", "Holdings supplied", "pct"),
    ("researched", "Discoveries researched", "int"),
]
COLUMNS = (
    _BASE_COLUMNS
    + [(f"role_{r}", f"{sim.ROLE_LABEL[r]} (workers)", "int") for r in sim.ROLES]
    + [(f"bld_{b}", f"{sim.BUILDING_LABEL[b]} (built)", "int") for b in sim.BUILDINGS]
)
COLUMN_KEYS = [c[0] for c in COLUMNS]
COLUMN_LABEL = {c[0]: c[1] for c in COLUMNS}
COLUMN_KIND = {c[0]: c[2] for c in COLUMNS}
_INDEX = {key: i for i, key in enumerate(COLUMN_KEYS)}


def _num(value, default=0.0):
    """A finite float, or `default` for anything else (None, bool, NaN)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    value = float(value)
    return value if math.isfinite(value) else default


def _rep(report, key):
    return _num(report.get(key, 0.0)) if isinstance(report, dict) else 0.0


def snapshot(state, effects, report, researched=0):
    """This season's values as {column key: float}. Never raises on odd state."""
    effects = sim.effects_or_neutral(effects)
    ev = sustainability.evaluate(state, effects)
    comps = ev["components"]
    report = report if isinstance(report, dict) else {}
    era_i = sim.era_index(state.era)
    habitat = (
        sustainability.habitat_usability(state, effects) * 100.0
        if era_i >= sim.era_index("space")
        else 100.0
    )
    values = {
        "season": _rep(report, "season") or max(1, state.season - 1),
        "era": float(era_i),
        "population": state.population,
        "housing": state.housing_capacity(effects),
        "idle": state.idle_workers(),
        "growth": state.growth_progress * 100.0,
        "calm": state.calm_streak,
        "food": state.resources["food"],
        "food_storage": state.food_storage_capacity(effects),
        "materials": state.resources["materials"],
        "tools": state.resources["tools"],
        "knowledge": state.resources["knowledge"],
        "surplus": state.resources["surplus"],
        "land": state.land_health * 100.0,
        "extraction": state.last_extraction,
        "sust_yield": state.last_sustainable_yield,
        "score": ev["score"],
        "livability": comps["livability"],
        "equity": comps["equity"],
        "balance": comps["balance"],
        "resilience": comps["resilience"],
        "food_gathered": _rep(report, "food_gathered"),
        "materials_gathered": _rep(report, "materials_gathered"),
        "tools_made": _rep(report, "tools_made"),
        "knowledge_made": _rep(report, "knowledge_made"),
        "fed_pct": sustainability.food_security(state) * 100.0,
        "shelter_pct": sustainability.shelter_adequacy(state, effects) * 100.0,
        "social_pct": sustainability.social_provision(state, effects) * 100.0,
        "habitat_pct": habitat,
        "births": _rep(report, "births"),
        "deaths": _rep(report, "deaths"),
        "spoiled": _rep(report, "spoiled"),
        "pollution": state.pollution * 100.0,
        "sprawl": state.sprawl * 100.0,
        "canal_staffing": _rep(report, "canal_staffing_ratio") * 100.0,
        "public_works": _rep(report, "public_works_coverage_ratio") * 100.0,
        "habitat_layout": _rep(report, "habitat_layout_ratio") * 100.0,
        "holdings_residents": state.holdings_residents(),
        "holdings_served": state.outlying_served * 100.0,
        "researched": researched,
    }
    for role in sim.ROLES:
        values[f"role_{role}"] = state.allocation.get(role, 0)
    for building in sim.BUILDINGS:
        values[f"bld_{building}"] = state.buildings.get(building, 0)
    return values


def _row_from(values):
    row = []
    for key in COLUMN_KEYS:
        value = max(-VALUE_LIMIT, min(VALUE_LIMIT, _num(values.get(key, 0.0))))
        row.append(round(value, 2))
    return row


def clean(raw):
    """Validated rows from whatever a save handed back (may be junk)."""
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw[-MAX_ROWS:]:
        if not isinstance(item, (list, tuple)) or len(item) != len(COLUMN_KEYS):
            continue
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in item):
            continue
        row = [round(max(-VALUE_LIMIT, min(VALUE_LIMIT, float(v))), 2) for v in item]
        if row[_INDEX["season"]] < 1:
            continue
        out.append(row)
    return out


def rows(ui):
    return clean(ui.get(KEY)) if isinstance(ui, dict) else []


def record(ui, state, effects, report, researched=0):
    """Appends one season's row (capped). Returns the row."""
    row = _row_from(snapshot(state, effects, report, researched))
    history = rows(ui)
    history.append(row)
    ui[KEY] = history[-MAX_ROWS:]
    return row


def value(row, key):
    return row[_INDEX[key]]


def series(history, key, count=20):
    """The last `count` values of one column, oldest first."""
    if key not in _INDEX:
        return []
    index = _INDEX[key]
    return [row[index] for row in history[-count:]]


def row_dict(row):
    return {key: row[i] for i, key in enumerate(COLUMN_KEYS)}


def format_value(key, number):
    kind = COLUMN_KIND.get(key, "num")
    if kind == "int":
        return f"{number:.0f}"
    if kind == "pct":
        return f"{number:.0f}%"
    return f"{number:.1f}"


def format_delta(key, number):
    """A signed delta as text. The arrow is part of the text so the direction
    never depends on colour."""
    kind = COLUMN_KIND.get(key, "num")
    digits = 0 if kind in ("int", "pct") else 1
    rounded = round(number, digits)
    if rounded == 0:
        return "▬ 0"
    sign = "+" if rounded > 0 else "−"
    arrow = "▲" if rounded > 0 else "▼"
    suffix = "%" if kind == "pct" else ""
    return f"{arrow} {sign}{abs(rounded):.{digits}f}{suffix}"
