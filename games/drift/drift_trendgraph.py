"""The trend graph (layers, ranges, event markers, SVG) and the wellbeing band and curve helpers."""

from drift_rules import MODEL_REGION_WELLBEING_SCORE, STRAIN_LEVEL_THRESHOLDS, THRIVING_WELLBEING_SCORE


# I1: a small two-line strain/wellbeing trend graph, same rendering
# approach as Grid's own trend_graph_svg -- an HTML string built in
# Python and assigned via .innerHTML, no createElementNS/DOM-building
# needed for an SVG.
TREND_GRAPH_WIDTH = 280
TREND_GRAPH_HEIGHT = 70


def _normalize_series(series, height, lo=None, hi=None):
    """Maps a series of values to y-coordinates in [0, height], flipped so
    a higher value draws higher on the graph. An explicit lo/hi lets a
    series be normalized against a fixed scale (0-100 for wellbeing/
    strain-as-percent) rather than its own min/max, so the line's shape
    reads on an absolute scale round to round rather than always filling
    the full height."""
    if lo is None:
        lo = min(series)
    if hi is None:
        hi = max(series)
    if hi - lo < 1e-9:
        return [height / 2 for _ in series]
    return [height - ((v - lo) / (hi - lo)) * height for v in series]


TREND_LAYER_ORDER = ["strain", "wellbeing", "control", "roi", "events"]
TREND_LAYER_LABEL = {
    "strain": "Strain", "wellbeing": "Wellbeing", "control": "Passive region", "roi": "ROI", "events": "Events",
}
TREND_LAYER_DEFAULT = {"strain": True, "wellbeing": True, "control": True, "roi": False, "events": True}
TREND_RANGES = {"10": 10, "25": 25, "all": None}
TREND_ROI_SCALE = 8.0  # the ROI layer draws 0 to this many funds back per fund invested, or to its own peak if higher
TREND_TOP_MARGIN = 10  # room above the lines for the event markers
TREND_EVENT_KINDS = {
    "net_positive": "first net-positive round",
    "band": "wellbeing band change",
    "strain_peak": "strain peak",
    "realloc": "capacity moved",
    "second_wave": "second wave began",
}
TREND_EVENT_SYMBOL = {"net_positive": "◆", "band": "▲", "strain_peak": "■", "realloc": "✚", "second_wave": "⚑"}


def _trend_event_path(kind, x):
    """A small shape per kind (different outlines, so the markers read without colour)."""
    if kind == "net_positive":
        return f"M{x:.1f},-9 L{x + 4:.1f},-5 L{x:.1f},-1 L{x - 4:.1f},-5 Z"
    if kind == "band":
        return f"M{x - 4:.1f},-1 L{x + 4:.1f},-1 L{x:.1f},-9 Z"
    if kind == "strain_peak":
        return f"M{x - 3.5:.1f},-8.5 h7 v7 h-7 Z"
    if kind == "realloc":
        return f"M{x - 4:.1f},-5 h8 M{x:.1f},-9 v8"
    return f"M{x - 3:.1f},-1 L{x - 3:.1f},-9 L{x + 4:.1f},-6 L{x - 3:.1f},-3"  # second_wave: a pennant


def trend_events(region_state):
    """I-12: the run's notable rounds as [{"round", "kind", "text"}], oldest first: the first net-positive
    round, each change of wellbeing band, the strain peak, every capacity move and the second wave's start."""
    events = []
    first = region_state.round_number - len(region_state.wellbeing_log)
    previous = None
    for index, score in enumerate(region_state.wellbeing_log):
        band = wellbeing_band(score)
        if previous is not None and band != previous:
            events.append({
                "round": first + index, "kind": "band",
                "text": f"wellbeing moved from {previous} to {band} ({score:.0f})",
            })
        previous = band
    if region_state.net_positive_round is not None:
        events.append({
            "round": region_state.net_positive_round, "kind": "net_positive",
            "text": "integration became a net gain: contributions have paid back the services investment",
        })
    strain = region_state.strain_log
    if strain and max(strain) >= STRAIN_LEVEL_THRESHOLDS[1][0]:
        peak_index = strain.index(max(strain))
        events.append({
            "round": region_state.round_number - len(strain) + peak_index, "kind": "strain_peak",
            "text": f"strain peaked at {max(strain) * 100:.0f}%",
        })
    for row in region_state.ledger:
        if row.get("realloc", 0) > 0:
            events.append({"round": row["round"], "kind": "realloc", "text": "capacity moved between types"})
    if region_state.second_wave_start_round is not None:
        events.append({"round": region_state.second_wave_start_round, "kind": "second_wave", "text": "the second wave began"})
    events.sort(key=lambda event: (event["round"], list(TREND_EVENT_KINDS).index(event["kind"])))
    return events


def trend_legend_text(layers):
    parts = []
    if layers.get("strain", True):
        parts.append("Solid line: strain.")
    if layers.get("wellbeing", True):
        parts.append("Dashed: your wellbeing.")
    if layers.get("control", True):
        parts.append("Dotted grey: the passive unmanaged region's wellbeing.")
    if layers.get("roi"):
        parts.append(f"Thin dash-dot line: ROI, funds paid back per fund invested (drawn from 0 up to {TREND_ROI_SCALE:.0f} or its own peak, whichever is higher).")
    if layers.get("events", True):
        shapes = ", ".join(f"{TREND_EVENT_SYMBOL[kind]} {label}" for kind, label in TREND_EVENT_KINDS.items())
        parts.append(f"Markers along the top: {shapes}.")
    return " ".join(parts)


def trend_graph_svg(
    strain_history, wellbeing_history, control_wellbeing_history=None,
    first_round=1, layers=None, events=None, roi_history=None, view_rounds=None,
):
    """Trend graph: strain (0-100%, rising is worse) vs. composite wellbeing (0-100, rising is better) —
    both already on a 0-100 scale, so they're normalized against that fixed range rather than each other's
    min/max, keeping round-to-round shape meaningful rather than always stretched to fill the graph.

    I-12/I-16 add, all optional: `layers` (which lines and the event strip to draw), `events` (see
    trend_events), `roi_history` (right-aligned to the other series), `view_rounds` (only the last N rounds)
    and `first_round` (the round number of the first history entry, for labels). Invisible hit columns carry
    the exact values per round for the crosshair tooltip (ui.js)."""
    n_all = len(strain_history)
    if n_all < 2:
        return ""
    layers = dict(TREND_LAYER_DEFAULT, **(layers or {}))
    start = max(0, n_all - max(2, view_rounds)) if view_rounds else 0
    n = n_all - start
    strain_series = list(strain_history[start:])
    wellbeing_series = list(wellbeing_history[start:])
    xs = [i * (TREND_GRAPH_WIDTH / (n - 1)) for i in range(n)]
    strain_pct = [s * 100 for s in strain_series]
    strain_ys = _normalize_series(strain_pct, TREND_GRAPH_HEIGHT, 0, 100)
    wellbeing_ys = _normalize_series(wellbeing_series, TREND_GRAPH_HEIGHT, 0, 100)
    round_of = [first_round + start + i for i in range(n)]

    def _points(ys):
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))

    def _markers(ys, values, css_class, label):
        return "".join(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" class="trend-point {css_class}">'
            f"<title>Round {round_of[i]} -- {label}: {v:.0f}</title>"
            f"</circle>"
            for i, (x, y, v) in enumerate(zip(xs, ys, values))
        )

    drawn = []
    if layers["strain"]:
        drawn.append(f'<polyline points="{_points(strain_ys)}" class="trend-line trend-line--strain" />')
    if layers["wellbeing"]:
        drawn.append(f'<polyline points="{_points(wellbeing_ys)}" class="trend-line trend-line--wellbeing" />')

    # I2: the passive unmanaged control region's wellbeing, drawn as a third, muted dotted line (no point
    # markers -- context, not a second thing to inspect). Needs 2+ points to be a line.
    control_series = None
    if layers["control"] and control_wellbeing_history and len(control_wellbeing_history) >= 2:
        if len(control_wellbeing_history) == n_all:
            control_series = list(control_wellbeing_history[start:])
        else:
            control_series = list(control_wellbeing_history[:min(n, len(control_wellbeing_history))])
        control_ys = _normalize_series(control_series, TREND_GRAPH_HEIGHT, 0, 100)
        drawn.append(
            f'<polyline points="{_points(control_ys)}" class="trend-line trend-line--control" />'
        )

    # I-12: the ROI layer, right-aligned when an older save has fewer entries than rounds.
    roi_series = [None] * n
    if layers["roi"] and roi_history:
        padded = [None] * max(0, n_all - len(roi_history)) + list(roi_history[-n_all:])
        roi_series = padded[start:]
        roi_top = max([TREND_ROI_SCALE] + [v for v in roi_series if v is not None])
        roi_points = [
            (x, TREND_GRAPH_HEIGHT - max(0.0, v) / roi_top * TREND_GRAPH_HEIGHT)
            for x, v in zip(xs, roi_series) if v is not None
        ]
        if len(roi_points) >= 2:
            joined = " ".join(f"{x:.1f},{y:.1f}" for x, y in roi_points)
            drawn.append(f'<polyline points="{joined}" class="trend-line trend-line--roi" />')

    if layers["strain"]:
        drawn.append(_markers(strain_ys, strain_pct, "trend-point--strain", "Strain"))
    if layers["wellbeing"]:
        drawn.append(_markers(wellbeing_ys, wellbeing_series, "trend-point--wellbeing", "Wellbeing"))

    # I-12: event markers along the top strip, one shape per kind; each also lists in its round's tooltip.
    events_by_round = {}
    if layers["events"]:
        for event in events or []:
            index = event["round"] - first_round - start
            if 0 <= index < n:
                events_by_round.setdefault(index, []).append(event)
                x = xs[index]
                drawn.append(
                    f'<g class="trend-event trend-event--{event["kind"]}">'
                    f'<title>Round {event["round"]}: {event["text"]}</title>'
                    f'<path d="{_trend_event_path(event["kind"], x)}" /></g>'
                )

    # I-16: invisible hit columns + a crosshair line (ui.js moves it and shows data-tip).
    step = TREND_GRAPH_WIDTH / (n - 1)
    hits = []
    for i in range(n):
        parts = [f"Round {round_of[i]}"]
        if layers["strain"]:
            parts.append(f"strain {strain_pct[i]:.0f}%")
        if layers["wellbeing"] and i < len(wellbeing_series):
            parts.append(f"wellbeing {wellbeing_series[i]:.0f}")
        if control_series is not None and i < len(control_series):
            parts.append(f"passive region {control_series[i]:.0f}")
        if roi_series[i] is not None:
            parts.append(f"ROI {roi_series[i]:.1f}")
        for event in events_by_round.get(i, []):
            parts.append(event["text"])
        left = max(0.0, xs[i] - step / 2)
        right = min(float(TREND_GRAPH_WIDTH), xs[i] + step / 2)
        tip = "; ".join(parts[:1] + [", ".join(parts[1:])]) if len(parts) > 1 else parts[0]
        hits.append(
            f'<rect class="trend-hit" x="{left:.1f}" y="{-TREND_TOP_MARGIN}" width="{right - left:.1f}" '
            f'height="{TREND_GRAPH_HEIGHT + TREND_TOP_MARGIN}" data-x="{xs[i]:.1f}" data-round="{round_of[i]}" '
            f'data-tip="{tip}" />'
        )

    return (
        f'<svg viewBox="0 {-TREND_TOP_MARGIN} {TREND_GRAPH_WIDTH} {TREND_GRAPH_HEIGHT + TREND_TOP_MARGIN}" '
        f'class="trend-graph-svg">'
        + "".join(drawn)
        + f'<line class="trend-crosshair" x1="0" x2="0" y1="{-TREND_TOP_MARGIN}" y2="{TREND_GRAPH_HEIGHT}" />'
        + "".join(hits)
        + "</svg>"
    )


# -- I-18: copy run summary --
CURVE_BLOCKS = "▁▂▃▄▅▆▇█"
CURVE_WIDTH = 30


def wellbeing_band(score):
    if score >= MODEL_REGION_WELLBEING_SCORE:
        return "Model Region"
    if score >= THRIVING_WELLBEING_SCORE:
        return "Thriving"
    if score >= 40:
        return "Managing"
    return "Struggling"


def wellbeing_curve(values, width=CURVE_WIDTH):
    """A block-character curve (0 to 100) of up to `width` evenly spaced samples."""
    if not values:
        return ""
    if len(values) > width:
        picks = [values[round(i * (len(values) - 1) / (width - 1))] for i in range(width)]
    else:
        picks = list(values)
    out = []
    for v in picks:
        index = int(max(0.0, min(99.999, v)) / 100.0 * len(CURVE_BLOCKS))
        out.append(CURVE_BLOCKS[index])
    return "".join(out)
