"""Drawings and markers: the coupling gauge, the record-coupling-ratio marker, the methane trend graph, the real-world
comparison chart, the season calendar, the poultry-versus-cattle card and the breeding rings.
Part of the split of the old single-file game.py: see "File map" in games/herd/CLAUDE.md.
"""

import html
import json
import math

import comparison_chart
import ghost as ghost_lib  # Z-3e: the shared best-farm ghost (shared/ghost.py)
from js import document, setTimeout
from pyodide.ffi import create_proxy

import herd_runstate as runstate
from herd_rules import (
    BASE_COUPLING_RATIO, GAUGE_HIGH_COLOR, GAUGE_LOW_COLOR, GENETICS_MATURE_ROUNDS, HERD_INCOME_PER_UNIT,
    POULTRY_INCOME_PER_UNIT, POULTRY_UPKEEP_PER_UNIT, REAL_WORLD_REDUCTION_FRACTION, WELFARE_CAPS,
    WELFARE_FEED, WELFARE_GENETICS,
)
from herd_util import _read_local_storage_item, _write_local_storage_item
from herd_model import demand_surge_active, season_for_round
from herd_blind import blind_hidden


# REVIEW(reuse): byte-identical implementation in games/canopy/game.py.
# Low urgency at only 2 occurrences, but worth a shared color-utility module
# if a third game ever needs a hex-color lerp.
def _lerp_color(start_hex, end_hex, t):
    """Linear-interpolates between two #rrggbb colors at t in [0, 1]."""
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(start_hex[1:3], 16), int(start_hex[3:5], 16), int(start_hex[5:7], 16)
    r2, g2, b2 = int(end_hex[1:3], 16), int(end_hex[3:5], 16), int(end_hex[5:7], 16)
    r = round(r1 + (r2 - r1) * t)
    g = round(g1 + (g2 - g1) * t)
    b = round(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _gauge_point(fraction):
    """The (x, y) point on the coupling gauge's semicircle arc (same path
    coupling_gauge_svg() draws below) at the given 0..1 fraction along it
    -- shared by the live fill and the F8 record marker so both agree on
    the exact same geometry. Arc: center (60, 60), radius 50, running
    from 180 degrees (fraction 0, the CLEAN end) down to 0 degrees
    (fraction 1, the HIGH end), matching the path's own
    "M 10 60 A 50 50 0 0 1 110 60" sweep."""
    fraction = max(0.0, min(1.0, fraction))
    angle = math.radians(180 - fraction * 180)
    return 60 + 50 * math.cos(angle), 60 - 50 * math.sin(angle)


def coupling_gauge_svg(fraction, record_ratio=None):
    """Semi-circle dial gauge: 0 = fully decoupled (green), 1 = fully
    coupled at baseline (red). Iteration-pass addition — the single
    most prominent UI element, replacing a plain ratio number with an
    at-a-glance dial for the mechanic the whole lesson depends on.

    F8 (planning/TODO.md) — record_ratio, when given, draws a small
    diamond marker on the arc at the best (lowest) coupling ratio this
    browser has ever reached across every session/save on this device.
    Distinct from the live .gauge-fill arc, which only ever reflects the
    current farm's state -- a fresh session starts back at
    BASE_COUPLING_RATIO, so the two genuinely diverge once a player has
    played before. Same "shape, not just color" marker technique as
    Grid's own best-round diamond on its trend graph (see
    trend_graph_svg() there)."""
    fraction = max(0.0, min(1.0, fraction))
    color = _lerp_color(GAUGE_LOW_COLOR, GAUGE_HIGH_COLOR, fraction)
    dash = fraction * 100
    record_marker = ""
    if record_ratio is not None:
        record_fraction = max(0.0, min(1.0, record_ratio / BASE_COUPLING_RATIO))
        rx, ry = _gauge_point(record_fraction)
        record_marker = (
            f'<polygon points="{rx:.1f},{ry - 4:.1f} {rx + 4:.1f},{ry:.1f} '
            f'{rx:.1f},{ry + 4:.1f} {rx - 4:.1f},{ry:.1f}" class="gauge-record-marker">'
            f"<title>Best ever (this browser): {record_ratio:.2f} methane/herd/round</title>"
            "</polygon>"
        )
    return (
        '<svg viewBox="0 0 120 66" class="coupling-gauge-svg">'
        '<path d="M 10 60 A 50 50 0 0 1 110 60" class="gauge-track" pathLength="100" />'
        f'<path d="M 10 60 A 50 50 0 0 1 110 60" class="gauge-fill" pathLength="100" '
        f'stroke="{color}" stroke-dasharray="{dash:.1f} 100" />'
        f"{record_marker}"
        "</svg>"
    )


# F8 (planning/TODO.md) — a small per-browser "record decoupling ratio"
# marker on the coupling gauge, like Grid's best-round marker. F14's own
# comment above (in render()) already explains why a *session* best would
# be redundant: coupling_ratio() only ever falls within a single session
# (investment counts never go down), so it always equals the session's
# current value -- a fact the Round-2 pass explicitly used to skip this
# exact idea at the time. This is a different axis: the best ratio this
# browser has EVER reached, across every session/save on this device, via
# localStorage. A fresh session starts back at BASE_COUPLING_RATIO, so
# once a player has played before, "best ever" and "current" genuinely
# diverge -- that's what makes a persistent marker meaningful here. Same
# _read/_write_local_storage_item lazy-import pattern as Canopy's
# personal_best / Tide's best_coastline_saved / Thaw's G19.
RECORD_COUPLING_RATIO_STORAGE_KEY = "herd_record_coupling_ratio_v1"

# Z6 (planning/TODO.md "Z. Games"): duration of the shared
# .personal-best-display.just-improved pulse (shared/personal-best.css) --
# same value every other game using that shared badge uses.
RECORD_COUPLING_RATIO_BADGE_MS = 1800


def load_record_coupling_ratio():
    """None means "no record yet" -- deliberately distinct from any real
    ratio value, since both BASE_COUPLING_RATIO (1.0) and
    MIN_COUPLING_RATIO (0.1) are real, reachable numbers and neither
    would be a safe "nothing recorded" sentinel the way 0.0 is for a
    "higher is better" stat like Tide's best_coastline_saved."""
    raw = _read_local_storage_item(RECORD_COUPLING_RATIO_STORAGE_KEY)
    if not raw:
        return None
    try:
        return float(json.loads(raw))
    except (ValueError, TypeError):
        return None


def _maybe_update_record_coupling_ratio():
    """Called every render(); bumps + persists the record whenever the
    live farm's coupling_ratio() drops below it. Lower is better here --
    coupling_ratio() is methane per herd unit, and the gauge's own
    CLEAN/HIGH labels run green-at-0/red-at-baseline -- so a new record is
    a *drop* below whatever's stored, the opposite direction from every
    other game's "higher is better" personal-best stat.

    A fresh, never-decoupled farm sits exactly at BASE_COUPLING_RATIO --
    that's the starting point, not an achievement, so it must never get
    written as a "record" on its own. Only an actual improvement over
    baseline counts, which is also what keeps a brand-new browser (no
    localStorage entry, no decoupling investment yet) showing no marker
    at all, per this feature's own "record only appears once a record
    exists" requirement."""
    if runstate.sandbox_active:  # GF-24: a practice farm never sets a record
        return
    current = runstate.farm.coupling_ratio()
    if current >= BASE_COUPLING_RATIO - 1e-9:
        return
    if runstate.record_coupling_ratio is None or current < runstate.record_coupling_ratio - 1e-9:
        runstate.record_coupling_ratio = current
        _write_local_storage_item(RECORD_COUPLING_RATIO_STORAGE_KEY, json.dumps(runstate.record_coupling_ratio))
        _flash_record_coupling_ratio_badge()


def _flash_record_coupling_ratio_badge():
    """Z6: briefly adds the shared .just-improved class (see
    shared/personal-best.css) right when a new record is set. Same
    setTimeout+create_proxy shape as Canopy/Tide/Thaw's equivalent."""
    element = document.getElementById("coupling-gauge-record-display")
    if element is None:
        return
    element.classList.add("just-improved")

    def _unflash():
        el = document.getElementById("coupling-gauge-record-display")
        if el is not None:
            el.classList.remove("just-improved")

    setTimeout(create_proxy(_unflash), RECORD_COUPLING_RATIO_BADGE_MS)


def render_record_coupling_ratio():
    """The record only ever appears once one actually exists -- a brand
    new browser with no play history shows nothing here, matching the
    marker's own behavior on the gauge SVG (coupling_gauge_svg() draws no
    diamond at all when record_ratio is None)."""
    element = document.getElementById("coupling-gauge-record-display")
    if element is None:
        return
    if runstate.record_coupling_ratio is None or blind_hidden():
        element.hidden = True
        return
    element.hidden = False
    element.innerText = f"Best ever (this browser): {runstate.record_coupling_ratio:.2f} methane/herd/round"


# F7 — a compact methane-over-rounds trend line, same technique as
# Thaw's mini_temp_graph_svg: unlabeled beyond its axis-free shape, since
# the point is the shape of the curve (accelerating vs. flattening),
# not reading any one round's value precisely.
TREND_GRAPH_WIDTH = 240
TREND_GRAPH_HEIGHT = 48


def methane_trend_graph_svg(history, ghost=None):
    """The methane-over-rounds line. Z-3e: `ghost` (a dict from ghost_graph_data(), or None) adds your best earlier
    farm's methane as a faint dashed line under it, on the same scale (the range grows to include it)."""
    if len(history) < 2:
        return ""
    n = len(history)
    ghost_values = [] if not ghost else [(i, v) for i, v in ((i, ghost_lib.value_at(ghost["trace"], i)) for i in range(1, n)) if v is not None]
    lo = min([min(history)] + [v for _i, v in ghost_values])
    hi = max([max(history)] + [v for _i, v in ghost_values])
    if hi - lo < 1e-9:
        ys = [TREND_GRAPH_HEIGHT / 2 for _ in history]
    else:
        ys = [TREND_GRAPH_HEIGHT - ((v - lo) / (hi - lo)) * TREND_GRAPH_HEIGHT for v in history]
    xs = [i * (TREND_GRAPH_WIDTH / (n - 1)) for i in range(n)]
    points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    ghost_svg, head = "", '<svg viewBox="0 0 %d %d" class="methane-trend-graph-svg">' % (TREND_GRAPH_WIDTH, TREND_GRAPH_HEIGHT)
    if len(ghost_values) >= 2:
        def y_of(value):
            return TREND_GRAPH_HEIGHT / 2 if hi - lo < 1e-9 else TREND_GRAPH_HEIGHT - ((value - lo) / (hi - lo)) * TREND_GRAPH_HEIGHT
        ghost_points = " ".join(f"{xs[i]:.1f},{y_of(v):.1f}" for i, v in ghost_values)
        sentence = html.escape(ghost["sentence"], quote=True)
        head = (f'<svg viewBox="0 0 {TREND_GRAPH_WIDTH} {TREND_GRAPH_HEIGHT}" class="methane-trend-graph-svg" role="img" '
                f'aria-label="Methane over time. {sentence}">')
        ghost_svg = (
            f'<g class="ghost-line" data-testid="ghost-line" pointer-events="none"><polyline points="{ghost_points}" fill="none" '
            f'stroke="currentColor" stroke-width="1.5" stroke-dasharray="4 3" opacity="0.5"><title>{sentence}</title></polyline>'
            f'<text x="{TREND_GRAPH_WIDTH - 2}" y="9" font-size="8" text-anchor="end" fill="currentColor" opacity="0.8">Ghost: best farm (dashed)</text></g>'
        )
    return (
        f"{head}{ghost_svg}"
        f'<polyline points="{points}" class="methane-trend-line" />'
        f"{trend_markers_svg(xs, ys, history)}"
        f"</svg>"
    )


def trend_markers_svg(xs, ys, history):
    """F-14: shape markers on the methane trend graph, drawn always but only visible when the
    pattern-fills setting is on (style.css). A square marks a round that added LESS methane than
    the round before (the curve flattening), a circle any other round, and the latest round is a
    larger diamond. Shape, never colour, carries the meaning. Rounds are capped to the last 40 so
    a long game does not draw hundreds of tiny shapes."""
    n = len(history)
    first = max(0, n - 40)
    marks = []
    for i in range(first, n):
        x, y = xs[i], ys[i]
        if i == n - 1:
            marks.append(
                f'<polygon class="trend-marker trend-marker--latest" '
                f'points="{x:.1f},{y - 4:.1f} {x + 4:.1f},{y:.1f} {x:.1f},{y + 4:.1f} {x - 4:.1f},{y:.1f}" />'
            )
            continue
        flattened = i >= 2 and (history[i] - history[i - 1]) < (history[i - 1] - history[i - 2]) - 1e-9
        if flattened:
            marks.append(f'<rect class="trend-marker trend-marker--flat" x="{x - 2.5:.1f}" y="{y - 2.5:.1f}" width="5" height="5" />')
        else:
            marks.append(f'<circle class="trend-marker trend-marker--rise" cx="{x:.1f}" cy="{y:.1f}" r="2.5" />')
    return "".join(marks)


def real_world_comparison_chart_svg():
    """Z17 (site-wide goal): a small bar chart alongside the F15 text
    sentence above -- this comparison previously had no chart at all,
    only prose. Built on the shared shared/comparison_chart.py component
    (the same module Grid's own C15/global-comparison line and
    Continuum's K13 "vs. history" chart now share), via its
    bar_comparison_svg() -- the simplest chart shape in that module, for
    a single current value against a single hardcoded real-world
    reference rather than a round-by-round history."""
    return comparison_chart.bar_comparison_svg(
        runstate.farm.decoupled_fraction() * 100,
        REAL_WORLD_REDUCTION_FRACTION * 100,
        unit="%",
        your_label="You",
        reference_label="Real farms (documented)",
        aria_label="Your emissions-intensity reduction against the documented real-world benchmark",
    )


# ---- F-21 season calendar --------------------------------------------------------------
CALENDAR_ROUNDS = 12
SEASON_MARKS = {-0.10: "▼▼", -0.05: "▼", 0.0: "■", 0.05: "▲", 0.10: "▲▲"}


def season_calendar_cells(count=CALENDAR_ROUNDS):
    """The next `count` rounds starting with the current one: each cell's season name,
    income swing and whether a plant-based demand surge is running."""
    cells = []
    for number in range(runstate.farm.round_number, runstate.farm.round_number + count):
        name, raw = season_for_round(number)
        cells.append({
            "round": number, "name": name, "mod": runstate.farm.season_modifier(number), "raw": raw,
            "surge": demand_surge_active(number),
        })
    return cells


def season_calendar_html():
    items = []
    for cell in season_calendar_cells():
        mark = SEASON_MARKS.get(cell["raw"], "■")
        tone = "up" if cell["mod"] > 0 else ("down" if cell["mod"] < 0 else "flat")
        surge = '<span class="season-surge" aria-hidden="true">\U0001F331</span>' if cell["surge"] else ""
        label = f"Round {cell['round']}: {cell['name']}, income {cell['mod'] * 100:+.0f}%"
        if cell["surge"]:
            label += ", plant-based demand surge"
        now = " season-cell--now" if cell["round"] == runstate.farm.round_number else ""
        items.append(
            f'<li class="season-cell season-cell--{tone}{now}" title="{label}" aria-label="{label}">'
            f'<span class="season-round">R{cell["round"]}</span>'
            f'<span class="season-mark" aria-hidden="true">{mark}</span>'
            f'<span class="season-pct">{cell["mod"] * 100:+.0f}%</span>{surge}</li>'
        )
    return "".join(items)


def render_season_calendar():
    calendar = document.getElementById("season-calendar")
    calendar.hidden = not runstate.farm.variation_enabled
    calendar.innerHTML = season_calendar_html() if runstate.farm.variation_enabled else ""


# ---- F-22 poultry vs cattle -------------------------------------------------------------
def poultry_compare_rows():
    """Per-unit, per-round figures side by side: (label, cattle text, poultry text)."""
    cattle_income = HERD_INCOME_PER_UNIT * runstate.farm.welfare_multiplier() * runstate.farm.certification_multiplier()
    poultry_income = POULTRY_INCOME_PER_UNIT - POULTRY_UPKEEP_PER_UNIT
    cattle_ratio = runstate.farm.coupling_ratio()
    poultry_ratio = runstate.farm.poultry_coupling_ratio()
    return [
        ("Income per unit (before pressure)", f"{cattle_income:.2f}", f"{poultry_income:.2f} after upkeep"),
        ("Methane-equivalent per unit", f"{cattle_ratio:.2f}", f"{poultry_ratio:.2f}"),
        ("Income per methane", f"{cattle_income / cattle_ratio:.1f}", f"{poultry_income / poultry_ratio:.1f}"),
        (
            "Welfare effect",
            f"Feed +{WELFARE_FEED:g}, Caps +{WELFARE_CAPS:g}, Breeding +{WELFARE_GENETICS:g} per lever",
            "None: flock levers do not move the welfare score",
        ),
    ]


def poultry_compare_html():
    rows = "".join(
        f"<tr><th scope=\"row\">{label}</th><td>{cattle}</td><td>{poultry}</td></tr>"
        for label, cattle, poultry in poultry_compare_rows()
    )
    return (
        '<table class="compare-table"><caption>Cattle against poultry, per unit per round</caption>'
        '<thead><tr><th scope="col"></th><th scope="col">\U0001F404 Cattle</th>'
        f'<th scope="col">\U0001F414 Poultry</th></tr></thead><tbody>{rows}</tbody></table>'
    )


# ---- F-23 breeding rings ----------------------------------------------------------------
def genetics_rings_html():
    """One small ring per breeding line still maturing: a quarter of the ring per round
    done, the rounds left written in the middle (so it is never a colour-only cue)."""
    if not runstate.farm.genetics_pending:
        return '<span class="ring-empty">No line maturing</span>'
    radius = 11
    circumference = 2 * math.pi * radius
    rings = []
    for left in sorted(runstate.farm.genetics_pending):
        left = max(0, min(GENETICS_MATURE_ROUNDS, left))
        done = (GENETICS_MATURE_ROUNDS - left) / GENETICS_MATURE_ROUNDS
        label = f"Breeding line: {left} round{'s' if left != 1 else ''} left of {GENETICS_MATURE_ROUNDS}"
        rings.append(
            f'<svg class="breed-ring" viewBox="0 0 30 30" width="30" height="30" role="img" aria-label="{label}">'
            f'<title>{label}</title>'
            f'<circle class="breed-ring-track" cx="15" cy="15" r="{radius}" fill="none" stroke-width="3"/>'
            f'<circle class="breed-ring-fill" cx="15" cy="15" r="{radius}" fill="none" stroke-width="3" '
            f'stroke-dasharray="{done * circumference:.2f} {circumference:.2f}" transform="rotate(-90 15 15)"/>'
            f'<text x="15" y="19" text-anchor="middle" class="breed-ring-text">{left}</text></svg>'
        )
    return "".join(rings)
