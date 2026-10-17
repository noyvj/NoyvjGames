"""The report card and timeline charts, the forest log panels and the ghost toggle."""

from js import document

import canopy_runstate as runstate
from canopy_forestlog import WILDLIFE_SPECIES, _rare_entry, forest_log_lines, species_seen
from canopy_ghost import GHOST_PREF_KEY, ghost_chart_points, ghost_enabled, ghost_note_text
from canopy_helpers import (
    SPARKLINE_HEIGHT, SPARKLINE_WIDTH, _el, _sparkline_points, _svg_text, _write_local_storage_item,
    plot_coordinate_label,
)
from canopy_rules import SEASONS, SEASON_CYCLE_TICKS, SEASON_LABEL
from canopy_valuation import BADGE_ICON, playstyle_badge
from canopy_worldvars import RARE_WILDLIFE, _report_history, request_history


def on_toggle_ghost(event=None):
    toggle = _el("ghost-toggle")
    on = True if toggle is None else bool(toggle.checked)
    _write_local_storage_item(GHOST_PREF_KEY, "1" if on else "0")
    render_timeline_chart()


# B13 ------------------------------------------------------------------------

REPORT_CARD_GRAPHS = [
    ("report-card-biodiversity", "Biodiversity", 0, "#4caf50"),
    ("report-card-standing", "Standing value", 1, "#66b2e8"),
    ("report-card-relations", "Community relations", 2, "#e8a33d"),
]


def _report_graph_svg(index, label, color):
    series = [point[index] for point in _report_history]
    if not series:
        return ""
    points = _sparkline_points(series, max(max(series), 1e-9))
    return (
        f'<svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}" class="session-sparkline" '
        f'role="img" aria-label="{label} over the session, now {series[-1]:.1f}">'
        f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2" /></svg>'
    )


def render_report_card():
    for element_id, label, index, color in REPORT_CARD_GRAPHS:
        container = document.getElementById(element_id)
        if container is None:
            continue
        svg = _report_graph_svg(index, label, color)
        if svg:
            container.innerHTML = svg
        else:
            container.innerHTML = ""
            container.innerText = "Not enough time has passed yet to chart a trend."


# B-21 (2026-10-09): a larger, interactive timeline chart joining the report-card series with the forest log and the
# request history. Window = the same capped history the report card keeps (the last VALUE_HISTORY_MAX_POINTS ticks).
TIMELINE_WIDTH = 640
TIMELINE_HEIGHT = 200
TIMELINE_PAD_LEFT = 38
TIMELINE_PAD_BOTTOM = 18
TIMELINE_METRICS = {
    "biodiversity": ("Biodiversity", 0, "#4caf50"),
    "standing": ("Standing value", 1, "#66b2e8"),
    "relations": ("Community relations", 2, "#e8a33d"),
}
# Marker kind -> (label, SVG shape). Shapes differ so the chart never relies on colour alone.
TIMELINE_MARKERS = {
    "clear": ("Clear", "cross"),
    "replant": ("Replant", "triangle"),
    "specialize": ("Specialist choice", "diamond"),
    "granted": ("Request granted", "square"),
    "declined": ("Request declined", "square"),
    "countered": ("Request countered", "square"),
}


def timeline_model(metric="standing"):
    """Pure data for the chart: points (tick, value), season bands and event markers inside the window."""
    if metric not in TIMELINE_METRICS:
        metric = "standing"
    _label, index, _color = TIMELINE_METRICS[metric]
    count = len(_report_history)
    first_tick = runstate.forest_tick - count + 1
    points = [(first_tick + i, float(row[index])) for i, row in enumerate(_report_history)]
    bands = []
    if count:
        tick = first_tick
        while tick <= runstate.forest_tick:
            season = SEASONS[(tick // SEASON_CYCLE_TICKS) % len(SEASONS)]
            end = min(runstate.forest_tick, (tick // SEASON_CYCLE_TICKS + 1) * SEASON_CYCLE_TICKS - 1)
            bands.append({"season": season, "start": tick, "end": end})
            tick = end + 1
    markers = []
    if count:
        for entry in runstate.forest_log:
            if entry["kind"] in ("clear", "replant", "specialize") and first_tick <= entry["tick"] <= runstate.forest_tick:
                markers.append({"tick": entry["tick"], "kind": entry["kind"], "plot": entry["plot"], "text": entry["text"]})
        for entry in request_history:
            if entry["choice"] in TIMELINE_MARKERS and first_tick <= entry["tick"] <= runstate.forest_tick:
                markers.append({"tick": entry["tick"], "kind": entry["choice"], "plot": entry["plot"],
                                "text": f"{TIMELINE_MARKERS[entry['choice']][0]} on {plot_coordinate_label(entry['plot'])}"})
    markers.sort(key=lambda m: (m["tick"], m["kind"]))
    return {"metric": metric, "points": points, "bands": bands, "markers": markers}


def _marker_shape_svg(shape, x, y, title):
    safe = _svg_text(title)
    if shape == "cross":
        body = f'<path d="M{x-4:.1f},{y-4:.1f}L{x+4:.1f},{y+4:.1f}M{x+4:.1f},{y-4:.1f}L{x-4:.1f},{y+4:.1f}" stroke="currentColor" stroke-width="2" fill="none"/>'
    elif shape == "triangle":
        body = f'<path d="M{x:.1f},{y-5:.1f}L{x+5:.1f},{y+4:.1f}L{x-5:.1f},{y+4:.1f}Z" fill="currentColor"/>'
    elif shape == "diamond":
        body = f'<path d="M{x:.1f},{y-5:.1f}L{x+5:.1f},{y:.1f}L{x:.1f},{y+5:.1f}L{x-5:.1f},{y:.1f}Z" fill="currentColor"/>'
    else:
        body = f'<rect x="{x-4:.1f}" y="{y-4:.1f}" width="8" height="8" fill="currentColor"/>'
    return f'<g class="timeline-marker" tabindex="0">{body}<title>{safe}</title></g>'


def timeline_chart_svg(metric="standing"):
    """The chart as an SVG string, or "" before there is any history."""
    model = timeline_model(metric)
    points = model["points"]
    if not points:
        return ""
    label, _index, color = TIMELINE_METRICS[model["metric"]]
    width, height = TIMELINE_WIDTH, TIMELINE_HEIGHT
    plot_w, plot_h = width - TIMELINE_PAD_LEFT, height - TIMELINE_PAD_BOTTOM
    first_tick, last_tick = points[0][0], points[-1][0]
    span = max(1, last_tick - first_tick)
    ghost_points = ghost_chart_points(len(points)) if model["metric"] == "standing" else []   # Z-3e
    top = max(max(v for _t, v in points), max((v for _i, v in ghost_points), default=0.0), 1e-9)

    def x_of(tick):
        return TIMELINE_PAD_LEFT + (tick - first_tick) / span * plot_w

    def y_of(value):
        return plot_h - value / top * plot_h

    parts = [f'<svg viewBox="0 0 {width} {height}" class="timeline-svg" role="img" '
             f'aria-label="{label} timeline from tick {first_tick} to {last_tick}, now {points[-1][1]:.1f}'
             f'{". " + _svg_text(ghost_note_text()) if ghost_points else ""}">']
    for i, band in enumerate(model["bands"]):
        x0, x1 = x_of(band["start"]), x_of(band["end"] + 1 if band["end"] < last_tick else band["end"])
        opacity = "0.10" if i % 2 == 0 else "0.04"
        parts.append(f'<rect x="{x0:.1f}" y="0" width="{max(0.0, x1 - x0):.1f}" height="{plot_h}" fill="currentColor" opacity="{opacity}"/>')
        parts.append(f'<text x="{x0 + 3:.1f}" y="11" font-size="10" fill="currentColor">{SEASON_LABEL[band["season"]]}</text>')
    parts.append(f'<text x="2" y="12" font-size="10" fill="currentColor">{top:.0f}</text>')
    parts.append(f'<text x="2" y="{plot_h}" font-size="10" fill="currentColor">0</text>')
    line = " ".join(f"{x_of(t):.1f},{y_of(v):.1f}" for t, v in points)
    if ghost_points:   # Z-3e: dashed, faint and labelled, so it never relies on colour alone
        ghost_line = " ".join(f"{x_of(points[i][0]):.1f},{y_of(v):.1f}" for i, v in ghost_points)
        parts.append(f'<g class="ghost-line" data-testid="ghost-line"><polyline points="{ghost_line}" fill="none" stroke="currentColor" '
                     f'stroke-width="2" stroke-dasharray="6 4" opacity="0.55"><title>{_svg_text(ghost_note_text())}</title></polyline>'
                     f'<text x="{width - 4}" y="12" font-size="10" text-anchor="end" fill="currentColor" opacity="0.8">Ghost: best session (dashed)</text></g>')
    parts.append(f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="2"/>')
    for t, v in points:  # invisible hover targets giving each tick's exact value
        parts.append(f'<circle cx="{x_of(t):.1f}" cy="{y_of(v):.1f}" r="3" fill="{color}" opacity="0"><title>Tick {t}: {v:.1f}</title></circle>')
    value_at = dict(points)
    for marker in model["markers"]:
        shape = TIMELINE_MARKERS[marker["kind"]][1]
        parts.append(_marker_shape_svg(shape, x_of(marker["tick"]), y_of(value_at.get(marker["tick"], 0.0)),
                                       f"Tick {marker['tick']}: {marker['text']}"))
    parts.append(f'<text x="{TIMELINE_PAD_LEFT}" y="{height - 4}" font-size="10" fill="currentColor">tick {first_tick}</text>')
    parts.append(f'<text x="{width - 4}" y="{height - 4}" font-size="10" text-anchor="end" fill="currentColor">tick {last_tick}</text>')
    parts.append("</svg>")
    return "".join(parts)


def timeline_marker_lines(metric="standing"):
    """Text version of the markers, newest last, for screen readers and the legend."""
    return [f"t{m['tick']}: {m['text']}" for m in timeline_model(metric)["markers"]]


def render_timeline_chart():
    container = _el("timeline-chart")
    if container is None:
        return
    select = _el("timeline-metric")
    metric = getattr(select, "value", "standing") or "standing"
    svg = timeline_chart_svg(metric)
    if not svg:
        container.innerHTML = ""
        container.innerText = "Not enough time has passed yet to chart a timeline."
    else:
        container.innerHTML = svg
    note, toggle = _el("ghost-note"), _el("ghost-toggle")   # Z-3e
    if toggle is not None:
        toggle.checked = ghost_enabled()
    if note is not None:
        text = ghost_note_text() if ghost_enabled() and metric == "standing" else ""
        note.innerText = text
        note.hidden = not text
    legend = _el("timeline-legend")
    if legend is not None:
        lines = timeline_marker_lines(metric)
        shapes = "; ".join(f"{label} = {shape}" for label, shape in TIMELINE_MARKERS.values())
        legend.innerText = (f"Markers ({shapes}). " + ("Events: " + " | ".join(lines[-12:]) if lines else "No events in this window yet."))


def render_forest_log_panels():
    badge_el = document.getElementById("session-summary-badge")
    if badge_el is not None:
        badge = playstyle_badge()
        badge_el.innerText = f"{BADGE_ICON[badge]} Playstyle badge: {badge}" + (f" ({runstate.clear_cuts_total} clear-cut{'s' if runstate.clear_cuts_total != 1 else ''})" if runstate.clear_cuts_total else "")
    seen = species_seen()
    wildlife_el = document.getElementById("wildlife-log-list")
    if wildlife_el is not None:
        head = (
            "Species seen ({}/{}): ".format(len(seen), len(WILDLIFE_SPECIES))
            + (" ".join(f"{icon} {name}" for icon, name in seen) if seen else "none yet")
        )
        rare_head = "\nRare sightings ({}/{}): ".format(len(runstate.rare_wildlife_found), len(RARE_WILDLIFE)) + (
            " ".join(f"{_rare_entry(r)[1]} {_rare_entry(r)[2]}" for r in runstate.rare_wildlife_found)
            if runstate.rare_wildlife_found else "none yet"
        )
        lines = forest_log_lines(kinds={"wildlife", "rare", "discovery"})  # GB-20/GB-8: rare finds live here too
        wildlife_el.innerText = head + rare_head + ("\n" + "\n".join(lines) if lines else "")
    history_el = document.getElementById("forest-history-list")
    if history_el is not None:
        lines = forest_log_lines()
        story_line = f"The story of {runstate.forest_name}\n" if runstate.forest_name else ""  # GB-14
        history_el.innerText = story_line + ("\n".join(lines) if lines else "No decisions yet: clear, replant, or decline a request to start the log.")
