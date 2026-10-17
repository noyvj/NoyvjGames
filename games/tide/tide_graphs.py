"""SVG graphs (sparklines, acidity and fish history, delayed consequence) and the graph range and marker controls."""

import html
import json
import math

from js import document

import tide_runstate as runstate
from tide_bridge import _read_local_storage_item, _write_local_storage_item
from tide_library import library_overlay_record
from tide_rules import FISH_DAMAGE_SCALE, GRAPH_MARKER_LIMIT, GRAPH_PREFS_KEY, GRAPH_RANGES


# D15: a Grid-style historical mini-graph -- a small inline SVG built
# directly as a markup string (assigned via innerHTML), same technique
# Canopy's own session sparkline uses, charting acidity and fish yield
# together over the session so the delayed-consequence relationship
# between them is visible as a shape, not just two separate numbers.
SPARKLINE_WIDTH = 260
SPARKLINE_HEIGHT = 60
SPARKLINE_ACIDITY_COLOR = "#b06fd6"
SPARKLINE_FISH_COLOR = "#4c9c6e"

# Series styles used when markers are on: acidity is solid with circles, fish yield long-dashed
# with squares, damage dotted with triangles, so no series is told apart by colour alone.
SERIES_STYLES = {
    "acidity": {"color": SPARKLINE_ACIDITY_COLOR, "dash": None, "shape": "circle"},
    "fish": {"color": SPARKLINE_FISH_COLOR, "dash": "6 3", "shape": "square"},
    "damage": {"color": "#d8c088", "dash": "2 2", "shape": "triangle"},
    "risk": {"color": "#e8a03c", "dash": "2 2", "shape": "triangle"},
}


def graph_window_start(total):
    """First index of the seasons the graphs show for `total` recorded seasons."""
    if runstate.graph_range == "all":
        return 0
    return max(0, total - int(runstate.graph_range))


def _xy(values, step, max_value=1.0):
    denominator = max(max_value, 1e-9)
    return [
        (i * step, SPARKLINE_HEIGHT - min(1.0, max(0.0, v / denominator)) * SPARKLINE_HEIGHT)
        for i, v in enumerate(values)
    ]


def _poly_points(xy):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)


def _marker_svg(xy, shape, color):
    """D-23: a small shape at (up to GRAPH_MARKER_LIMIT of) the series' points."""
    if not runstate.graph_markers or not xy:
        return ""
    every = max(1, math.ceil(len(xy) / GRAPH_MARKER_LIMIT))
    out = []
    for i, (x, y) in enumerate(xy):
        if i % every and i != len(xy) - 1:
            continue
        if shape == "circle":
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.3" fill="{color}" stroke="#fff" stroke-width="0.4"/>')
        elif shape == "square":
            out.append(
                f'<rect x="{x - 2.1:.1f}" y="{y - 2.1:.1f}" width="4.2" height="4.2" fill="{color}" '
                f'stroke="#fff" stroke-width="0.4"/>'
            )
        else:
            out.append(
                f'<polygon points="{x:.1f},{y - 2.8:.1f} {x - 2.6:.1f},{y + 2.0:.1f} {x + 2.6:.1f},{y + 2.0:.1f}" '
                f'fill="{color}" stroke="#fff" stroke-width="0.4"/>'
            )
    return "".join(out)


def _series_svg(xy, style_key, dash=None, width=2, opacity=None, always_dash=False):
    """One polyline (plus markers when the toggle is on). The style's own dash is only used
    with markers on; `dash` forces a dash (a compared session) whatever the toggle says."""
    style = SERIES_STYLES[style_key]
    chosen = dash or (style["dash"] if runstate.graph_markers else None)
    attrs = f' stroke-dasharray="{chosen}"' if chosen else ""
    if opacity is not None:
        attrs += f' opacity="{opacity}"'
    line = (
        f'<polyline points="{_poly_points(xy)}" fill="none" stroke="{style["color"]}" '
        f'stroke-width="{width}"{attrs} />'
    )
    return line + _marker_svg(xy, style["shape"], style["color"])


def _crosshair_attr(lines):
    """D-21: the per-position readout strings ui.js shows at the crosshair."""
    return f' data-crosshair="{html.escape(json.dumps(lines, separators=(",", ":")), quote=True)}"'


def graph_range_text():
    return "all seasons" if runstate.graph_range == "all" else f"the last {runstate.graph_range} seasons"


def then_vs_now_sparkline_svg():
    """D14: tiny per-season damage sparkline since the baseline; "" until
    there are two points to draw a line between."""
    series = runstate.state.then_vs_now_damage_series()
    if len(series) < 2:
        return ""
    top = max(max(series), 1e-9)
    step = SPARKLINE_WIDTH / max(1, len(series) - 1)
    xy = _xy(series, step, top)
    first = runstate.state.baseline_season
    lines = [f"Season {first + i}: damage {value:.0f}" for i, value in enumerate(series)]
    return (
        f'<svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}" '
        f'class="acidity-fish-sparkline" role="img" tabindex="0"{_crosshair_attr(lines)} '
        f'aria-label="Damage per season since the baseline">'
        f"{_series_svg(xy, 'damage', width=2)}"
        f"</svg>"
    )


def _sparkline_points(series, max_value):
    """Maps a list of values onto SVG viewport coordinates -- x spread
    evenly left-to-right, y scaled so 0 sits on the baseline and
    `max_value` sits at the top. An empty series returns "" rather than
    dividing by zero."""
    if not series:
        return ""
    step = SPARKLINE_WIDTH / max(1, len(series) - 1)
    return _poly_points(_xy(series, step, max_value))


def _funds_by_season():
    return {e["season"]: e["funds"] for e in runstate.state.season_ledger}


def acidity_fish_history_svg():
    """Returns "" once there's no history yet -- render() shows a plain
    "not enough data" message instead in that case. Acidity is charted as
    a fraction of FISH_DAMAGE_SCALE (its own natural ceiling) and fish
    yield as a fraction of 1.0 (already 0..1), so both lines share one
    0..1 vertical scale despite being different units.

    D-22 draws only the chosen range, D-23 optionally adds dash styles and point
    shapes, D-21 attaches a readout per season for the crosshair, and D-2 can draw a
    saved session from the library as dashed lines behind the live ones."""
    if not runstate.state.acidity_history:
        return ""
    overlay = library_overlay_record()
    live_acid = [min(1.0, a / FISH_DAMAGE_SCALE) for a in runstate.state.acidity_history]
    live_fish = list(runstate.state.fish_yield_history)
    over_acid = overlay["acidity"] if overlay else []
    over_fish = overlay["fish"] if overlay else []
    full = max(len(live_acid), len(over_acid))
    start = graph_window_start(full)
    count = full - start
    step = SPARKLINE_WIDTH / max(1, count - 1)
    acid_view, fish_view = live_acid[start:], live_fish[start:]
    # D10: dashed reference line at the average acidity of the seasons in view, like
    # Thaw's melt-threshold gridline.
    average = sum(acid_view) / len(acid_view) if acid_view else 0.0
    average_y = SPARKLINE_HEIGHT - average * SPARKLINE_HEIGHT
    reference = (
        f'<line x1="0" y1="{average_y:.1f}" x2="{SPARKLINE_WIDTH}" y2="{average_y:.1f}" '
        f'stroke="{SPARKLINE_ACIDITY_COLOR}" stroke-width="1" stroke-dasharray="4 3" '
        f'opacity="0.6"><title>Average acidity, {graph_range_text()}</title></line>'
    )
    # D18: a marker at the season the comparison baseline was set (when it is in view).
    marker = ""
    baseline_index = runstate.state.baseline_season - 1 - start
    if runstate.state.baseline_season > 1 and count > 1 and baseline_index >= 0:
        marker_x = min(SPARKLINE_WIDTH, baseline_index * step)
        marker = (
            f'<line x1="{marker_x:.1f}" y1="0" x2="{marker_x:.1f}" y2="{SPARKLINE_HEIGHT}" '
            f'stroke="#d8c088" stroke-width="1" stroke-dasharray="2 2">'
            f'<title>Baseline set here (Season {runstate.state.baseline_season})</title></line>'
        )
    funds = _funds_by_season()
    lines = []
    for j in range(count):
        season = start + j + 1
        index = start + j
        parts = []
        if index < len(live_acid):
            parts.append(f"acidity {runstate.state.acidity_history[index]:.1f}")
            if index < len(live_fish):
                parts.append(f"fishing yield {live_fish[index] * 100:.0f}%")
            if index < len(runstate.state.damage_log):
                parts.append(f"damage {runstate.state.damage_log[index]:.0f}")
            if season in funds:
                parts.append(f"funds {funds[season]:.0f}")
        text = f"Season {season}: " + (", ".join(parts) if parts else "no data")
        if overlay and index < len(over_acid):
            extra = f"acidity {over_acid[index] * FISH_DAMAGE_SCALE:.1f}"
            if index < len(over_fish):
                extra += f", fishing yield {over_fish[index] * 100:.0f}%"
            text += f" | {overlay['name']}: {extra}"
        lines.append(text)
    drawn = ""
    if overlay:
        drawn += _series_svg(_xy(over_acid[start:], step), "acidity", dash="3 3", width=1.4, opacity=0.75)
        drawn += _series_svg(_xy(over_fish[start:], step), "fish", dash="3 3", width=1.4, opacity=0.75)
    drawn += _series_svg(_xy(acid_view, step), "acidity")
    drawn += _series_svg(_xy(fish_view, step), "fish")
    compare_note = f" Dashed lines: the saved session {overlay['name']}." if overlay else ""
    return (
        f'<svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}" '
        f'class="acidity-fish-sparkline" role="img" tabindex="0"{_crosshair_attr(lines)} '
        f'aria-label="Ocean acidity and fishing yield over {graph_range_text()}. Latest: acidity '
        f'{runstate.state.acidity:.1f}, fishing yield {runstate.state.fish_yield_multiplier() * 100:.0f} percent.'
        f'{html.escape(compare_note, quote=True)} Left and right arrow keys read each season.">'
        f"{reference}{marker}{drawn}"
        f"</svg>"
    )


def delayed_consequence_svg():
    """D7: acidity (purple) plotted at the season it was banked, against
    the fish yield it will cause (green, dashed) plotted `lag` seasons
    later -- the horizontal gap between the two lines is the lag. "" with
    no history yet. D-22 limits it to the chosen range; D-21 and D-23 as above."""
    rows_all = runstate.state.delayed_consequence_rows()
    if not rows_all:
        return ""
    lag = runstate.state._effective_fish_lag()
    start = graph_window_start(len(rows_all))
    rows = rows_all[start:]
    first = rows[0][0]
    total_seasons = len(rows) + lag
    step = SPARKLINE_WIDTH / max(1, total_seasons - 1)
    acidity_xy = [
        ((season - first) * step, SPARKLINE_HEIGHT - fraction * SPARKLINE_HEIGHT)
        for season, fraction, _arrival, _yield in rows
    ]
    fish_xy = [
        ((arrival - first) * step, SPARKLINE_HEIGHT - projected * SPARKLINE_HEIGHT)
        for _season, _fraction, arrival, projected in rows
    ]
    now_x = (runstate.state.season - first) * step
    now_line = (
        f'<line x1="{now_x:.1f}" y1="0" x2="{now_x:.1f}" y2="{SPARKLINE_HEIGHT}" '
        f'stroke="#d8c088" stroke-width="1" stroke-dasharray="2 2">'
        f"<title>Now (Season {runstate.state.season}): everything right of here has not happened yet</title></line>"
    )
    lines = []
    arrivals = {arrival: projected for _s, _f, arrival, projected in rows}
    for j in range(total_seasons):
        season = first + j
        parts = []
        if j < len(rows):
            parts.append(f"acidity banked {runstate.state.acidity_history[season - 1]:.1f}")
        if season in arrivals:
            parts.append(f"fish yield from earlier acidity about {arrivals[season] * 100:.0f}%")
        if season >= runstate.state.season:
            parts.append("not yet played")
        lines.append(f"Season {season}: " + (", ".join(parts) if parts else "nothing recorded"))
    return (
        f'<svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}" '
        f'class="acidity-fish-sparkline" role="img" tabindex="0"{_crosshair_attr(lines)} '
        f'aria-label="Acidity banked each season and the fish yield it causes {lag} seasons later, '
        f'over {graph_range_text()}">'
        f"{now_line}"
        f'{_series_svg(acidity_xy, "acidity")}'
        f'{_series_svg(fish_xy, "fish", dash="5 3")}'
        f"</svg>"
    )


# ---- D-22 / D-23 graph controls ----------------------------------------
def _load_graph_prefs():
    raw = _read_local_storage_item(GRAPH_PREFS_KEY)
    if not raw:
        return
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return
    if isinstance(data, dict):
        if data.get("range") in dict(GRAPH_RANGES):
            runstate.graph_range = data["range"]
        if isinstance(data.get("markers"), bool):
            runstate.graph_markers = data["markers"]


def _save_graph_prefs():
    _write_local_storage_item(
        GRAPH_PREFS_KEY, json.dumps({"range": runstate.graph_range, "markers": runstate.graph_markers})
    )


def render_graphs():
    """Redraws the trend graphs (they follow the range and marker options)."""
    graph_container = document.getElementById("acidity-fish-graph")
    if graph_container is not None:
        svg = acidity_fish_history_svg()
        if svg:
            graph_container.innerHTML = svg
        else:
            graph_container.innerHTML = ""
            graph_container.innerText = "Not enough seasons yet to chart a trend."
    consequence_graph = document.getElementById("delayed-consequence-graph")
    if consequence_graph is not None:
        consequence_graph.innerHTML = delayed_consequence_svg()
    then_vs_now_graph = document.getElementById("then-vs-now-graph")
    if then_vs_now_graph is not None:
        then_vs_now_graph.innerHTML = then_vs_now_sparkline_svg()
