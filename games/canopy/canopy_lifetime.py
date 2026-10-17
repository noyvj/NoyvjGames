"""Lifetime stats, the Forest Rank (XP, frames, palettes) and My Forests comparison."""

import json

from js import document

import canopy_runstate as runstate
from canopy_helpers import (
    SPARKLINE_HEIGHT, SPARKLINE_WIDTH, _el, _read_local_storage_item, _sparkline_points, _svg_text,
    _write_local_storage_item, ui_pref,
)
from canopy_records import legacy_bonus_for
from canopy_rules import TICK_INTERVAL_MS, lab_active
from canopy_valuation import (
    BADGE_UNDECIDED, layout_active, playstyle_badge, seasons_survived, standing_forest_value,
    total_biodiversity,
)
from canopy_worldvars import _report_history


# B-9 (2026-10-09): lifetime statistics across every finished session on this browser. A session is banked
# when it ends (the same moment the legacy bonus is banked); the panel adds the live session on top.
LIFETIME_STORAGE_KEY = "canopy_lifetime_stats_v1"
LIFETIME_MAX_DIFFICULTIES = 12


def _empty_lifetime():
    return {"sessions": 0, "clears": 0, "replants": 0, "ticks": 0, "by_difficulty": {}, "xp": 0, "badges": []}


def _nonneg_int(value):
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _sanitize_lifetime(raw):
    out = _empty_lifetime()
    if not isinstance(raw, dict):
        return out
    for key in ("sessions", "clears", "replants", "ticks", "xp"):
        out[key] = _nonneg_int(raw.get(key))
    badges = raw.get("badges")
    if isinstance(badges, list):
        out["badges"] = [str(b)[:24] for b in badges if isinstance(b, str)][:12]
    by = raw.get("by_difficulty")
    if isinstance(by, dict):
        for name, row in list(by.items())[:LIFETIME_MAX_DIFFICULTIES]:
            if not isinstance(row, dict):
                continue
            try:
                out["by_difficulty"][str(name)[:20]] = {
                    "n": _nonneg_int(row.get("n")),
                    "sum": max(0.0, float(row.get("sum", 0.0))),
                    "best": max(0.0, float(row.get("best", 0.0))),
                }
            except (TypeError, ValueError):
                continue
    return out


def load_lifetime():
    raw = _read_local_storage_item(LIFETIME_STORAGE_KEY)
    if not raw:
        return _empty_lifetime()
    try:
        return _sanitize_lifetime(json.loads(raw))
    except ValueError:
        return _empty_lifetime()


def _session_lifetime_numbers():
    return {
        "clears": sum(p.clear_count for p in runstate.plots),
        "replants": runstate.total_replants,
        "ticks": runstate._session_ticks,
        "standing": standing_forest_value(),
        "difficulty": runstate.current_difficulty,
        "seasons": seasons_survived(),
        "badge": playstyle_badge(),
    }


def _bank_lifetime():
    """Adds the session that is about to end to the stored lifetime totals (skipped when nothing happened)."""
    now = _session_lifetime_numbers()
    if now["ticks"] <= 0 or lab_active():  # B-5: sandbox forests never count
        return
    life = load_lifetime()
    life["sessions"] += 1
    life["clears"] += now["clears"]
    life["replants"] += now["replants"]
    life["ticks"] += now["ticks"]
    life["xp"] += session_xp(now["standing"], now["seasons"])  # B-19
    if now["badge"] != BADGE_UNDECIDED and now["badge"] not in life["badges"]:
        life["badges"] = (life["badges"] + [now["badge"]])[:12]
    if not layout_active():  # B-29: a custom shape's numbers are not comparable with the standard grid's averages
        row = life["by_difficulty"].setdefault(now["difficulty"], {"n": 0, "sum": 0.0, "best": 0.0})
        row["n"] += 1
        row["sum"] += now["standing"]
        row["best"] = max(row["best"], now["standing"])
    _write_local_storage_item(LIFETIME_STORAGE_KEY, json.dumps(life))
    _bank_my_forest()  # B-1


def lifetime_rows():
    """The statistics table lines: finished sessions banked plus the live session's clears, replants and time."""
    life = load_lifetime()
    now = _session_lifetime_numbers()
    seconds = (life["ticks"] + now["ticks"]) * TICK_INTERVAL_MS / 1000
    hours = seconds / 3600
    rows = [
        ("Finished sessions", str(life["sessions"])),
        ("Plots cleared (all time)", str(life["clears"] + now["clears"])),
        ("Plots replanted (all time)", str(life["replants"] + now["replants"])),
        ("Time in the forest", f"{hours:.1f} hours" if hours >= 0.1 else f"{seconds / 60:.0f} minutes"),
    ]
    for name in sorted(life["by_difficulty"]):
        row = life["by_difficulty"][name]
        if row["n"]:
            rows.append((f"Average standing value, {name}", f"{row['sum'] / row['n']:.1f} over {row['n']} (best {row['best']:.1f})"))
    return rows


# B-19 (2026-10-09): a long-term Forest Rank. Lifetime XP comes from standing value, seasons survived and how many
# different playstyle badges you have earned. Ranks unlock cosmetic frames and palettes only: no gameplay effect.
XP_PER_STANDING_POINT = 0.1
XP_PER_SEASON = 5
XP_PER_BADGE_TYPE = 25
FOREST_RANKS = (
    (0, "Sapling Warden"),
    (100, "Grove Tender"),
    (300, "Canopy Keeper"),
    (700, "Heartwood Ranger"),
    (1500, "Old-Growth Steward"),
    (3000, "Grove Keeper"),
)
FRAME_UNLOCKS = {"none": 0, "leaf": 1, "vine": 3, "crest": 5}      # option -> rank index needed
PALETTE_UNLOCKS = {"default": 0, "dusk": 2, "meadow": 4}
UI_PREF_FRAME = "canopy-forest-frame"
UI_PREF_PALETTE = "canopy-forest-palette"


def session_xp(standing, seasons):
    return int(max(0.0, standing) * XP_PER_STANDING_POINT) + XP_PER_SEASON * max(0, int(seasons))


def rank_for_xp(xp):
    """(rank index, name, xp needed for the next rank or None at the top)."""
    index = 0
    for i, (needed, _name) in enumerate(FOREST_RANKS):
        if xp >= needed:
            index = i
    nxt = FOREST_RANKS[index + 1][0] if index + 1 < len(FOREST_RANKS) else None
    return index, FOREST_RANKS[index][1], nxt


def forest_rank_info():
    life = load_lifetime()
    now = _session_lifetime_numbers()
    badges = set(life["badges"])
    if now["badge"] != BADGE_UNDECIDED:
        badges.add(now["badge"])
    xp = life["xp"] + session_xp(now["standing"], now["seasons"]) + XP_PER_BADGE_TYPE * len(badges)
    index, name, nxt = rank_for_xp(xp)
    return {"xp": xp, "rank_index": index, "rank": name, "next_at": nxt, "badge_types": len(badges)}


def chosen_cosmetic(pref_key, unlocks, default, rank_index):
    value = ui_pref(pref_key, default)
    return value if value in unlocks and unlocks[value] <= rank_index else default


def render_forest_rank():
    info = forest_rank_info()
    text_el = _el("forest-rank-text")
    if text_el is not None:
        to_next = "top rank reached" if info["next_at"] is None else f"{info['next_at'] - info['xp']} XP to the next rank"
        text_el.innerText = (
            f"Forest Rank: {info['rank']} ({info['rank_index'] + 1}/{len(FOREST_RANKS)}), {info['xp']} XP, {to_next}. "
            f"XP comes from standing value, seasons survived and {XP_PER_BADGE_TYPE} for each playstyle badge type ({info['badge_types']} so far)."
        )
    frame = chosen_cosmetic(UI_PREF_FRAME, FRAME_UNLOCKS, "none", info["rank_index"])
    palette = chosen_cosmetic(UI_PREF_PALETTE, PALETTE_UNLOCKS, "default", info["rank_index"])
    root = getattr(document, "documentElement", None)
    if root is not None and hasattr(root, "setAttribute"):
        root.setAttribute("data-forest-frame", frame)
        root.setAttribute("data-forest-palette", palette)
    for select_id, unlocks, current in (("forest-frame-select", FRAME_UNLOCKS, frame), ("forest-palette-select", PALETTE_UNLOCKS, palette)):
        select = _el(select_id)
        if select is None:
            continue
        select.value = current
        for option in getattr(select, "children", []) or []:
            needed = unlocks.get(getattr(option, "value", ""), 0)
            option.disabled = needed > info["rank_index"]
            if option.disabled:
                option.title = f"Unlocks at rank {needed + 1}: {FOREST_RANKS[needed][1]}"


def on_forest_frame_change(event=None):
    select = _el("forest-frame-select")
    if select is not None and getattr(select, "value", "") in FRAME_UNLOCKS:
        _write_local_storage_item(UI_PREF_FRAME, select.value)
        render_forest_rank()


def on_forest_palette_change(event=None):
    select = _el("forest-palette-select")
    if select is not None and getattr(select, "value", "") in PALETTE_UNLOCKS:
        _write_local_storage_item(UI_PREF_PALETTE, select.value)
        render_forest_rank()


# B-1 (2026-10-09): "My Forests", a library of finished sessions kept on this device so any two can be compared.
MY_FORESTS_KEY = "canopy_my_forests_v1"
MY_FORESTS_MAX = 12
MY_FORESTS_SERIES_POINTS = 30
MY_FORESTS_SERIES = (("biodiversity", "Biodiversity", "#4caf50"), ("standing", "Standing value", "#66b2e8"),
                     ("relations", "Community relations", "#e8a33d"))


def _downsample(series, count=MY_FORESTS_SERIES_POINTS):
    """At most `count` evenly spaced values, always ending on the last one."""
    series = [round(float(v), 1) for v in series]
    if len(series) <= count:
        return series
    step = (len(series) - 1) / (count - 1)
    return [series[round(i * step)] for i in range(count)]


def _clean_series(raw):
    if not isinstance(raw, list):
        return []
    out = []
    for value in raw[:MY_FORESTS_SERIES_POINTS]:
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value == value and abs(value) < 1e9:
            out.append(round(float(value), 1))
    return out


def _clean_forest_record(raw):
    if not isinstance(raw, dict):
        return None

    def number(key):
        value = raw.get(key)
        return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and abs(value) < 1e9 else 0.0

    series = raw.get("series") if isinstance(raw.get("series"), dict) else {}
    return {
        "id": _nonneg_int(raw.get("id")),
        "name": str(raw.get("name", ""))[:28],
        "difficulty": str(raw.get("difficulty", ""))[:16],
        "grid": str(raw.get("grid", ""))[:8],
        "badge": str(raw.get("badge", ""))[:24],
        "standing": number("standing"), "income": number("income"), "biodiversity": number("biodiversity"),
        "relations": number("relations"), "seasons": _nonneg_int(raw.get("seasons")), "ticks": _nonneg_int(raw.get("ticks")),
        "legacy_pct": number("legacy_pct"),
        "series": {key: _clean_series(series.get(key)) for key, _l, _c in MY_FORESTS_SERIES},
    }


def load_my_forests():
    raw = _read_local_storage_item(MY_FORESTS_KEY)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    records = [r for r in (_clean_forest_record(item) for item in data) if r is not None]
    return records[-MY_FORESTS_MAX:]


def _bank_my_forest():
    """Called only when a session with at least one tick is banked (see _bank_lifetime)."""
    records = load_my_forests()
    next_id = max((r["id"] for r in records), default=0) + 1
    standing = standing_forest_value()
    records.append({
        "id": next_id, "name": runstate.forest_name or f"Forest {next_id}", "difficulty": runstate.current_difficulty,
        "grid": f"{runstate.GRID_ROWS}x{runstate.GRID_COLS}", "badge": playstyle_badge(), "standing": round(standing, 1),
        "income": round(runstate.total_income, 1), "biodiversity": round(total_biodiversity(), 1),
        "relations": round(runstate.community_relations, 1), "seasons": seasons_survived(), "ticks": runstate._session_ticks,
        "legacy_pct": round((legacy_bonus_for(standing) - 1.0) * 100, 1),
        "series": {key: _downsample([row[i] for row in _report_history]) for i, (key, _l, _c) in enumerate(MY_FORESTS_SERIES)},
    })
    _write_local_storage_item(MY_FORESTS_KEY, json.dumps(records[-MY_FORESTS_MAX:]))


def my_forest_option_label(record):
    return f"#{record['id']} {record['name']}: {record['difficulty']} {record['grid']}, {record['standing']:.1f}"


def my_forests_compare_rows(a, b):
    """(label, value A, value B) rows for the side-by-side table."""
    def line(label, key, fmt=str):
        return (label, fmt(a[key]), fmt(b[key]))
    return [
        line("Difficulty", "difficulty"), line("Grid", "grid"), line("Playstyle badge", "badge"),
        line("Standing value", "standing", lambda v: f"{v:.1f}"), line("Harvested", "income", lambda v: f"{v:.1f}"),
        line("Biodiversity", "biodiversity", lambda v: f"{v:.1f}"), line("Community relations", "relations", lambda v: f"{v:.1f}"),
        line("Seasons survived", "seasons"), line("Time (ticks)", "ticks"), line("Legacy bonus earned", "legacy_pct", lambda v: f"+{v:.1f}%"),
    ]


def _forest_graph_block(record, heading):
    parts = [f'<div class="my-forests-column"><p class="summary-graph-label">{_svg_text(heading)}</p>']
    for key, label, color in MY_FORESTS_SERIES:
        series = record["series"].get(key, [])
        parts.append(f'<p class="summary-graph-label">{label}</p>')
        if series:
            points = _sparkline_points(series, max(max(series), 1e-9))
            parts.append(
                f'<svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}" class="session-sparkline" role="img" '
                f'aria-label="{_svg_text(label)} for {_svg_text(heading)}, ending at {series[-1]:.1f}">'
                f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/></svg>'
            )
        else:
            parts.append("<p>No trend recorded.</p>")
    parts.append("</div>")
    return "".join(parts)


def render_my_forests():
    records = load_my_forests()
    note = _el("my-forests-note")
    compare = _el("my-forests-compare")
    selects = [_el("my-forests-a"), _el("my-forests-b")]
    if note is not None:
        note.innerText = (f"{len(records)} saved forest{'s' if len(records) != 1 else ''} on this device (the latest {MY_FORESTS_MAX} are kept)."
                          if records else "Nothing saved yet: a forest is saved here when you start a new one.")
    for position, select in enumerate(selects):
        if select is None:
            continue
        previous = getattr(select, "value", "")
        select.innerHTML = ""
        for record in reversed(records):
            option = document.createElement("option")
            option.value = str(record["id"])
            option.innerText = my_forest_option_label(record)
            select.appendChild(option)
        ids = [str(r["id"]) for r in reversed(records)]
        if previous in ids:
            select.value = previous
        elif ids:
            select.value = ids[min(position, len(ids) - 1)]
    graphs = _el("my-forests-graphs")
    if compare is None:
        return
    by_id = {str(r["id"]): r for r in records}
    a = by_id.get(getattr(selects[0], "value", "")) if selects[0] is not None else None
    b = by_id.get(getattr(selects[1], "value", "")) if selects[1] is not None else None
    if a is None or b is None:
        compare.innerHTML = ""
        if graphs is not None:
            graphs.innerHTML = ""
        return
    head_a, head_b = f"A: #{a['id']} {a['name']}", f"B: #{b['id']} {b['name']}"
    rows = "".join(
        f"<tr><th scope=\"row\">{_svg_text(label)}</th><td>{_svg_text(va)}</td><td>{_svg_text(vb)}</td></tr>"
        for label, va, vb in my_forests_compare_rows(a, b)
    )
    compare.innerHTML = (f'<table class="my-forests-table"><thead><tr><th></th><th>{_svg_text(head_a)}</th>'
                         f'<th>{_svg_text(head_b)}</th></tr></thead><tbody>{rows}</tbody></table>')
    if graphs is not None:
        graphs.innerHTML = _forest_graph_block(a, head_a) + _forest_graph_block(b, head_b)


def on_my_forests_change(event=None):
    render_my_forests()
