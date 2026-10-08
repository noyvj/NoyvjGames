"""Continuum -- K-9: the time-lapse run replay.

Scrub back through the settlement's own history. Every completed season already
leaves one row in the per-season stat history (`statlog.py`), including how many
of every building stood, how many people lived there and the sustainability
score. This module turns those rows into **frames**, draws each as the civic
map, pins the moments that mattered on a timeline (eras entered, discoveries
studied, the first of each building raised, the founder's own notes) and builds
an exportable **image strip**.

What it is not. The 3D scene cannot be rebuilt for a past season (only counts
were recorded, and the scene builders read live state), so the replay is drawn
as the 2D civic map; and it exports a still image strip (an SVG file), not a
video clip. Both are honest limits, stated in the panel.

The replay covers the last `statlog.MAX_ROWS` seasons (the history is capped), a
run started before the history existed simply begins at its first recorded
season, and a settlement with fewer than two recorded seasons has nothing to
scrub yet.

Pure functions only: no DOM, no storage. `game.py` owns the panel and the timer.
"""

import types

import minutes
import sim
import statlog
import views

MIN_FRAMES = 2
STRIP_FRAMES = 6
PIN_KINDS = ("era", "research", "build", "note")
PIN_GLYPH = {"era": "◆", "research": "▲", "build": "■", "note": "●"}
PIN_LABEL = {"era": "Era", "research": "Discovery", "build": "First built", "note": "Founder's note"}
TEXT_MAX = 90


# --- frames --------------------------------------------------------------------
def frames(ui):
    """One dict per recorded season, oldest first."""
    out = []
    for row in statlog.rows(ui):
        data = statlog.row_dict(row)
        era_i = int(max(0, min(len(sim.ERA_ORDER) - 1, round(data["era"]))))
        out.append({
            "season": int(data["season"]),
            "era": sim.ERA_ORDER[era_i],
            "population": int(data["population"]),
            "score": float(data["score"]),
            "food": float(data["food"]),
            "land": float(data["land"]),
            "researched": int(data["researched"]),
            "buildings": {b: int(data.get(f"bld_{b}", 0)) for b in sim.BUILDINGS},
        })
    return out


def usable(frame_list):
    return len(frame_list) >= MIN_FRAMES


def caption(frame):
    return (
        f"Season {frame['season']}, {sim.ERA_LABEL[frame['era']]}: {frame['population']} people, "
        f"sustainability {frame['score']:.0f}, {frame['researched']} discoveries."
    )


# --- pins ------------------------------------------------------------------------
def _short(text):
    text = " ".join(str(text).split())
    return text if len(text) <= TEXT_MAX else text[: TEXT_MAX - 1] + "…"


def pins(ui, frame_list):
    """Events to pin on the timeline, as [{season, kind, text}], oldest first.

    Era changes come from the frames themselves; discoveries, the first
    building of each type and the era entries the player minuted come from the
    Council Minutes; the founder's notes from the founder's log. Only seasons
    inside the recorded range are kept.
    """
    if not frame_list:
        return []
    lo, hi = frame_list[0]["season"], frame_list[-1]["season"]
    found = []
    previous = None
    for frame in frame_list:
        if previous is not None and frame["era"] != previous:
            found.append({"season": frame["season"], "kind": "era", "text": f"Entered the {sim.ERA_LABEL[frame['era']]}."})
        previous = frame["era"]
    seen_builds = set()
    for entry in minutes.entries(ui):
        season = entry["season"]
        if entry["kind"] == "research" and lo <= season <= hi:
            found.append({"season": season, "kind": "research", "text": _short(entry["text"].replace("Motion carried: ", ""))})
        elif entry["kind"] == "build":
            subject = entry["text"]
            if subject not in seen_builds:
                seen_builds.add(subject)
                if lo <= season <= hi:
                    found.append({"season": season, "kind": "build", "text": _short(subject.replace("Motion carried: ", ""))})
    raw = ui.get("founders_log") if isinstance(ui, dict) else None
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            note, season = item.get("note"), item.get("season")
            if isinstance(note, str) and note.strip() and isinstance(season, int) and not isinstance(season, bool) and lo <= season <= hi:
                found.append({"season": season, "kind": "note", "text": _short(note)})
    order = {kind: i for i, kind in enumerate(PIN_KINDS)}
    found.sort(key=lambda p: (p["season"], order[p["kind"]]))
    return found


def pins_at(pin_list, season):
    return [p for p in pin_list if p["season"] == season]


def pin_text(pin):
    return f"{PIN_GLYPH[pin['kind']]} {PIN_LABEL[pin['kind']]}, season {pin['season']}: {pin['text']}"


# --- drawings ----------------------------------------------------------------------
def _shim(frame):
    return types.SimpleNamespace(era=frame["era"], buildings=dict(frame["buildings"]), population=frame["population"])


def map_svg(frame):
    """The civic map as it stood in that frame's season."""
    return views.civic_map_svg(_shim(frame))


CHART_W = 360
CHART_H = 110
PAD_L, PAD_R, PAD_T, PAD_B = 26, 8, 8, 24


def chart_svg(frame_list, index, pin_list=()):
    """Sustainability (solid) and people (dashed) over the run, with a cursor at
    `index` and a shape-coded marker per pin along the bottom. Every number is
    also in the SVG's text alternative."""
    n = len(frame_list)
    if n < MIN_FRAMES:
        return ""
    index = max(0, min(n - 1, int(index)))
    x0, x1 = PAD_L, CHART_W - PAD_R
    y_top, y_bot = PAD_T, CHART_H - PAD_B

    def x_of(i):
        return x0 + (x1 - x0) * i / (n - 1)

    pops = [f["population"] for f in frame_list]
    pop_hi = max(pops) or 1

    def y_score(v):
        return y_bot - (y_bot - y_top) * max(0.0, min(100.0, v)) / 100.0

    def y_pop(v):
        return y_bot - (y_bot - y_top) * v / pop_hi

    score_pts = " ".join(f"{x_of(i):.1f},{y_score(f['score']):.1f}" for i, f in enumerate(frame_list))
    pop_pts = " ".join(f"{x_of(i):.1f},{y_pop(f['population']):.1f}" for i, f in enumerate(frame_list))
    first, last, cur = frame_list[0], frame_list[-1], frame_list[index]
    label = (
        f"Timeline of {n} seasons, season {first['season']} to {last['season']}. Sustainability went from "
        f"{first['score']:.0f} to {last['score']:.0f}; people from {first['population']} to {last['population']}. "
        f"Cursor at season {cur['season']}."
    )
    parts = [
        f'<svg viewBox="0 0 {CHART_W} {CHART_H}" class="views-svg timelapse-chart" role="img" aria-label="{label}">',
        f'<title>{label}</title>',
        f'<rect x="0" y="0" width="{CHART_W}" height="{CHART_H}" class="map-bg"/>',
        f'<line x1="{x0}" y1="{y_bot}" x2="{x1}" y2="{y_bot}" class="tl-axis"/>',
        f'<text x="2" y="{y_top + 8}" class="tl-label">100</text><text x="2" y="{y_bot}" class="tl-label">0</text>',
        f'<polyline points="{score_pts}" class="tl-score"/>',
        f'<polyline points="{pop_pts}" class="tl-pop"/>',
    ]
    by_season = {f["season"]: i for i, f in enumerate(frame_list)}
    for pin in pin_list:
        i = by_season.get(pin["season"])
        if i is None:
            continue
        parts.append(_pin_shape(pin["kind"], x_of(i), y_bot + 9))
    cx = x_of(index)
    parts.append(f'<line x1="{cx:.1f}" y1="{y_top}" x2="{cx:.1f}" y2="{y_bot}" class="tl-cursor"/>')
    parts.append(
        f'<text x="{x0}" y="{CHART_H - 2}" class="tl-label">season {first["season"]}</text>'
        f'<text x="{x1}" y="{CHART_H - 2}" class="tl-label" text-anchor="end">season {last["season"]}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def _pin_shape(kind, x, y):
    r = 3.6
    if kind == "era":
        return f'<polygon points="{x:.1f},{y - r:.1f} {x + r:.1f},{y:.1f} {x:.1f},{y + r:.1f} {x - r:.1f},{y:.1f}" class="tl-pin tl-pin--era"/>'
    if kind == "research":
        return f'<polygon points="{x:.1f},{y - r:.1f} {x + r:.1f},{y + r:.1f} {x - r:.1f},{y + r:.1f}" class="tl-pin tl-pin--research"/>'
    if kind == "build":
        return f'<rect x="{x - r:.1f}" y="{y - r:.1f}" width="{2 * r:.1f}" height="{2 * r:.1f}" class="tl-pin tl-pin--build"/>'
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" class="tl-pin tl-pin--note"/>'


def sample_indexes(count, wanted=STRIP_FRAMES):
    """Evenly spaced indexes, always including the first and the last frame."""
    if count <= 0:
        return []
    if count <= wanted:
        return list(range(count))
    return sorted({round(i * (count - 1) / (wanted - 1)) for i in range(wanted)})


def strip_svg(frame_list, name=""):
    """The exportable image strip: a few evenly spaced frames side by side, each a
    civic map with its caption, under a title. A standalone SVG document."""
    if not frame_list:
        return ""
    picks = [frame_list[i] for i in sample_indexes(len(frame_list))]
    cell_w, cell_h = 360, 330
    total_w = cell_w * len(picks)
    title = (name.strip() or "A Continuum settlement") + ": a time-lapse"
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total_w} {cell_h + 46}" width="{total_w}" height="{cell_h + 46}" '
        'font-family="system-ui, sans-serif">',
        f'<rect x="0" y="0" width="{total_w}" height="{cell_h + 46}" fill="#14101c"/>',
        f'<text x="12" y="26" fill="#f2e6d0" font-size="20" font-weight="700">{_esc(title)}</text>',
    ]
    parts.append(_style_for_strip())
    for k, frame in enumerate(picks):
        inner = map_svg(frame)
        inner = inner.replace("<svg ", f'<svg x="{k * cell_w + 8}" y="40" width="{cell_w - 16}" height="{cell_h - 70}" ', 1)
        parts.append(inner)
        parts.append(
            f'<text x="{k * cell_w + 12}" y="{cell_h - 14}" fill="#f2e6d0" font-size="14" font-weight="700">'
            f'Season {frame["season"]} · {_esc(sim.ERA_LABEL[frame["era"]])}</text>'
            f'<text x="{k * cell_w + 12}" y="{cell_h + 6}" fill="#d8c9a8" font-size="12">'
            f'{frame["population"]} people · sustainability {frame["score"]:.0f} · {frame["researched"]} discoveries</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _style_for_strip():
    # the map's classes are styled by the page; a downloaded file has no page, so inline them once.
    return (
        "<style>.map-bg{fill:#1c1610}.map-district{fill:rgba(201,147,84,.1);stroke:rgba(201,147,84,.6);stroke-width:1}"
        ".map-district--empty{stroke-dasharray:4 3;fill:none}.map-label{fill:#f2e6d0;font-size:9px}.map-count{fill:#d8c9a8;font-size:9px}"
        ".map-glyph{fill:#e0b374;stroke:#2a1f10;stroke-width:.6}.map-glyph--line{fill:none;stroke:#e0b374;stroke-width:1.8;stroke-linecap:round}"
        ".map-glyph--hollow{fill:none;stroke:#e0b374;stroke-width:1.6}</style>"
    )


def _esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def strip_filename(name, frame_list):
    base = "".join(ch.lower() if ch.isalnum() else "-" for ch in (name or "settlement")).strip("-") or "settlement"
    last = frame_list[-1]["season"] if frame_list else 0
    return f"continuum-{base[:30]}-timelapse-season-{last}.svg"
