"""Mini temperature graphs (SVG, crosshair, screen-reader summary), trend and status labels, and the Region B/C/D card renderers."""

import json

from js import document

import thaw_runstate as runstate
from thaw_bridge import _escape
from thaw_model import deg, region, region_d
from thaw_presets import PRESET_WEIGHTS, preset_preview_text, preset_tooltip_text, render_custom_preset
from thaw_rules import (
    CATEGORIES, CATEGORY_ICON, CRITICAL_ACCELERATION_FACTOR, INVEST_COST, MELT_THRESHOLD, POLICY_STANCES,
    RESCUE_COST,
)


MINI_GRAPH_WIDTH = 120
MINI_GRAPH_HEIGHT = 40


GRAPH_MAX_POINTS = 120       # G-11: most points any one graph line ever draws
GRAPH_RECENT_FULL = 40       # G-11: the latest rounds are always drawn one by one


def graph_indexes(values, limit=GRAPH_MAX_POINTS, recent=GRAPH_RECENT_FULL):
    """G-11: which rounds of a long history a graph draws. Up to `limit` rounds are drawn one by one
    (exactly as before). Past that, the newest `recent` rounds stay whole and the older ones are
    collapsed into summary points: one per bucket, the bucket's highest value, so a peak is never
    flattened away. The first and last rounds are always kept. Returns ascending indexes."""
    n = len(values)
    if n <= limit:
        return list(range(n))
    old_end = n - recent
    slots = max(1, limit - recent - 1)
    size = -(-(old_end - 1) // slots)
    kept = [0]
    start = 1
    while start < old_end:
        chunk = range(start, min(old_end, start + size))
        kept.append(max(chunk, key=lambda i: (values[i], i)))
        start += size
    kept.extend(range(old_end, n))
    return kept


def _crosshair_points(history, dampening, xs, ys):
    """G-16: [x, y, label] for up to CROSSHAIR_MAX_POINTS evenly spread points (always the last), as
    JSON the page's hover script reads. A point's label is its round, temperature and dampening."""
    n = len(history)
    stride = max(1, -(-n // CROSSHAIR_MAX_POINTS))
    indexes = list(range(0, n, stride))
    if indexes[-1] != n - 1:
        indexes.append(n - 1)
    offset = n - len(dampening) if dampening is not None else None
    points = []
    for i in indexes:
        label = f"Round {i + 1}: {deg(history[i], plus=True)}"
        if dampening is not None and offset is not None and 0 <= i - offset < len(dampening):
            label += f", dampening {dampening[i - offset] * 100:.0f}%"
        elif dampening is not None:
            label += ", dampening not recorded"
        points.append([round(xs[i], 1), round(ys[i], 1), label])
    return json.dumps(points, ensure_ascii=False, separators=(",", ":"))


CROSSHAIR_MAX_POINTS = 80


def mini_temp_graph_svg(history, name=None, dampening=None, pace=None, ghost_note=None):
    """A compact single-line temperature trend for one region's card —
    deliberately tiny and unlabeled beyond its axis-free shape, since the
    point is the divergence *between* regions' graphs, not reading any
    one of them precisely.

    G14: also draws a faint dashed reference line at MELT_THRESHOLD when
    that value falls within the graph's current visible range, so the
    moment a region's curve crosses the melt threshold is legible on the
    mini-graph itself, not just inferable from the melt-status text next
    to it.

    G-16: a named graph is also a hover and keyboard crosshair (see the page script): it carries
    its points as `data-pts` and a hidden cross line and dot the script moves."""
    if len(history) < 2:
        return ""
    n = len(history)
    # G-21: the best earlier run's path over the same rounds (as many as it recorded), drawn behind.
    pace_part = list(pace[:n]) if pace else []
    lo, hi = min(list(history) + pace_part), max(list(history) + pace_part)
    if hi - lo < 1e-9:
        ys = [MINI_GRAPH_HEIGHT / 2 for _ in history]
    else:
        ys = [MINI_GRAPH_HEIGHT - ((v - lo) / (hi - lo)) * MINI_GRAPH_HEIGHT for v in history]
    xs = [i * (MINI_GRAPH_WIDTH / (n - 1)) for i in range(n)]
    keep = graph_indexes(history)  # G-11: long histories are drawn as summary points
    points = " ".join(f"{xs[i]:.1f},{ys[i]:.1f}" for i in keep)

    threshold_line = ""
    if hi - lo >= 1e-9 and lo <= MELT_THRESHOLD <= hi:
        threshold_y = MINI_GRAPH_HEIGHT - ((MELT_THRESHOLD - lo) / (hi - lo)) * MINI_GRAPH_HEIGHT
        threshold_line = (
            f'<line x1="0" y1="{threshold_y:.1f}" x2="{MINI_GRAPH_WIDTH}" y2="{threshold_y:.1f}" '
            f'class="mini-temp-threshold-line" />'
            f'<text x="2" y="{max(threshold_y - 2, 7):.1f}" class="mini-temp-threshold-label">'
            f"{deg(MELT_THRESHOLD, 0, plus=True)}</text>"
        )

    pace_line = ""
    if len(pace_part) >= 2:
        if hi - lo < 1e-9:
            pace_ys = [MINI_GRAPH_HEIGHT / 2 for _ in pace_part]
        else:
            pace_ys = [MINI_GRAPH_HEIGHT - ((v - lo) / (hi - lo)) * MINI_GRAPH_HEIGHT for v in pace_part]
        pace_points = " ".join(f"{xs[i]:.1f},{pace_ys[i]:.1f}" for i in graph_indexes(pace_part))
        # Z-3e3: the shared ghost's drawing rules: dashed and faint, labelled in text (never colour alone), with a title
        # holding the sentence, and a test id.
        title = f"<title>{_escape(ghost_note)}</title>" if ghost_note else ""
        pace_line = (
            f'<g class="ghost-line" data-testid="ghost-line"><polyline points="{pace_points}" class="mini-pace-line">{title}</polyline>'
            f'<text x="{MINI_GRAPH_WIDTH - 2}" y="7" text-anchor="end" class="mini-pace-label">Ghost: best run (dashed)</text></g>'
        )

    aria = ""
    key = ""
    marker = ""
    cross = ""
    if name:
        summary = graph_summary_text(name, history)
        if ghost_note and pace_line:
            summary = f"{summary} {_escape(ghost_note)}"
        aria = (
            f' role="img" aria-label="{summary} Focus the graph and use the left and right arrow keys '
            f'to read each round." tabindex="0" '
            f"data-pts='{_escape(_crosshair_points(history, dampening, xs, ys)).replace(chr(39), '&#39;')}'"
        )
        key = GRAPH_REGION_KEYS.get(name, "")
        if key:
            key = f" graph-region-{key}"
            marker = _graph_end_marker(key[-1], xs[-1], ys[-1])
        cross = (
            f'<line x1="0" y1="0" x2="0" y2="{MINI_GRAPH_HEIGHT}" class="mini-cross" />'
            f'<circle cx="0" cy="0" r="2.2" class="mini-dot" />'
        )
    return (
        f'<svg viewBox="0 0 {MINI_GRAPH_WIDTH} {MINI_GRAPH_HEIGHT}" class="mini-temp-graph-svg{key}"{aria}>'
        f"{threshold_line}{pace_line}"
        f'<polyline points="{points}" class="mini-temp-line" />'
        f"{marker}{cross}"
        f"</svg>"
    )


# G-14: each region's line gets a dash pattern (CSS, by graph-region-<key>) and an end marker shape
# of its own, shown when the "graph patterns" setting is on, so the lines can be told apart
# without colour. The shapes are always drawn and the setting only reveals them.
GRAPH_REGION_KEYS = {"Region A": "a", "Region B": "b", "Region C": "c", "Region D": "d"}


def _graph_end_marker(key, x, y):
    r = 3.2
    x = min(max(x, r), MINI_GRAPH_WIDTH - r)
    y = min(max(y, r), MINI_GRAPH_HEIGHT - r)
    if key == "a":  # circle
        shape = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" />'
    elif key == "b":  # square
        shape = f'<rect x="{x - r:.1f}" y="{y - r:.1f}" width="{2 * r}" height="{2 * r}" />'
    elif key == "c":  # triangle
        shape = f'<polygon points="{x:.1f},{y - r:.1f} {x + r:.1f},{y + r:.1f} {x - r:.1f},{y + r:.1f}" />'
    else:  # diamond
        shape = f'<polygon points="{x:.1f},{y - r:.1f} {x + r:.1f},{y:.1f} {x:.1f},{y + r:.1f} {x - r:.1f},{y:.1f}" />'
    return f'<g class="mini-temp-end mini-temp-end--{key}">{shape}</g>'


def _melt_status_label(r):
    """G3: a third, distinct "critical" state on top of the existing
    binary melting/stable read — once warming has accelerated past
    CRITICAL_ACCELERATION_FACTOR times the background rate, "Melting" no
    longer distinguishes a region that just crossed the threshold from
    one whose feedback loop is now compounding fast."""
    if not r.is_melting():
        return "stable"
    if r.acceleration_factor() >= CRITICAL_ACCELERATION_FACTOR:
        return "critical"
    return "melting"


TREND_TEXT = {
    "up": ("\u25B2", "Rising faster than last round"),
    "down": ("\u25BC", "Rising slower than last round"),
    "flat": ("\u25B6", "Rising at the same pace as last round"),
}


def _render_trend(element_id, r):
    """G16: a small shape-coded arrow (not color-only) next to a region's
    temperature readout, comparing this round's rise to the previous one."""
    element = document.getElementById(element_id)
    trend = r.temperature_trend()
    if trend is None:
        element.innerText = ""
        element.title = ""
        return
    arrow, meaning = TREND_TEXT[trend]
    element.innerText = arrow
    element.title = meaning


def _rescue_status_text(r):
    if r.rescue_active():
        n = r.rescue_rounds_left
        return f"\U0001F6DF Rescue active \u2014 extra dampening for {n} more round{'s' if n != 1 else ''}."
    if r.rescue_used:
        return "Rescue spent \u2014 this region's one emergency lever has been used."
    if r.is_critical():
        if r.funds >= RESCUE_COST:
            return f"Critical \u2014 an emergency rescue ({RESCUE_COST:.0f} funds) is available, once."
        return f"Critical \u2014 an emergency rescue costs {RESCUE_COST:.0f} funds (you have {r.funds:.0f})."
    return ""


def _render_policy_stance():
    """G13: three stance buttons (disabled once the starting choice is made
    or the game has moved past round 1) plus a one-line readout."""
    can_choose = region.can_choose_policy_stance()
    for key, stance in POLICY_STANCES.items():
        button = document.getElementById(f"policy-stance-{key}-button")
        chosen = region.policy_stance == key
        button.innerText = ("\u2713 " if chosen else "") + stance["label"]
        button.title = stance["blurb"]
        button.disabled = not can_choose
    display = document.getElementById("policy-stance-display")
    if region.policy_stance is not None:
        stance = POLICY_STANCES[region.policy_stance]
        display.innerText = f"Policy stance: {stance['label']}. {stance['blurb']}"
    elif can_choose:
        display.innerText = (
            "Optional: pick a starting policy stance before round 1. It is a permanent, "
            "modest weighting \u2014 none is clearly best."
        )
    else:
        display.innerText = "No starting policy stance was chosen for this region."


def _render_restoration(prefix, r):
    """G15: a status line that only appears once restoration is running or
    has ever reversed something, so a stable region carries no clutter."""
    element = document.getElementById(f"{prefix}restoration-status")
    if r.restoration_active():
        element.innerText = (
            f"\U0001F331 Restoration under way \u2014 {deg(r.restored_total)} of melt-driven "
            f"warming pulled back so far."
        )
        element.hidden = False
    elif r.restored_total > 0:
        element.innerText = (
            f"Restoration paused \u2014 {deg(r.restored_total)} pulled back so far; "
            f"it resumes once the feedback loop is held down again."
        )
        element.hidden = False
    else:
        element.innerText = ""
        element.hidden = True


def _render_rescue(prefix, r):
    """G21: shows the rescue button only while it is a live option (critical
    and unspent), and the status line only when there is something to say,
    so a stable region carries no extra clutter."""
    button = document.getElementById(f"{prefix}rescue-button")
    status = document.getElementById(f"{prefix}rescue-status")
    button.innerText = f"\U0001F6DF Emergency rescue ({RESCUE_COST:.0f})"
    button.hidden = not (r.is_critical() and not r.rescue_used)
    button.disabled = not r.can_rescue()
    text = _rescue_status_text(r)
    status.innerText = text
    status.hidden = text == ""


def render_secondary_region(prefix, r):
    """Renders one of the two added regions into its `{prefix}-*`
    elements. Deliberately separate from the primary region's inline
    render code below (rather than a shared helper for all three) so
    the original Pass 1 behavior for "Region A" — including its
    whole-page tipping-flash — stays byte-for-byte unchanged.

    G1/G6: also renders the same dampening/acceleration/temperature-saved
    readouts Region A already had — every one of these is already a
    generic RegionState method, so no new game logic was needed, only
    new elements to write them into."""
    document.getElementById(f"{prefix}-temperature-display").innerText = deg(r.temperature, plus=True)
    _render_trend(f"{prefix}-temperature-trend", r)
    for preset_name in PRESET_WEIGHTS:
        document.getElementById(f"{prefix}-preset-{preset_name}-button").title = (
            preset_tooltip_text(preset_name)
            + ("" if runstate.hard_mode else " " + preset_preview_text(r, preset_name))  # GG-23: no previews
        )
    render_custom_preset(prefix, r)
    document.getElementById(f"{prefix}-funds-display").innerText = f"Funds: {r.funds:.0f}"
    document.getElementById(f"{prefix}-graph").innerHTML = mini_temp_graph_svg(
        r.temperature_history, f"Region {prefix.upper()}", r.dampening_history
    )
    document.getElementById(f"{prefix}-dampening-display").innerText = (
        f"Dampening: {r.feedback_dampening_fraction() * 100:.0f}%"
    )
    document.getElementById(f"{prefix}-acceleration-display").innerText = r.acceleration_message()
    document.getElementById(f"{prefix}-trajectory-display").innerText = r.trajectory_message()
    _render_rescue(f"{prefix}-", r)
    _render_restoration(f"{prefix}-", r)

    status = _melt_status_label(r)
    melt_status_el = document.getElementById(f"{prefix}-melt-status-display")
    melt_status_el.innerText = status.capitalize()
    suffix = {"stable": "", "melting": " melt-status--active", "critical": " melt-status--critical"}[status]
    melt_status_el.className = "region-melt-status" + suffix

    card_el = document.getElementById(f"{prefix}-region-card")
    if r.just_started_melting:
        card_el.className = "region-card tipping-flash"
        r.just_started_melting = False
    else:
        card_el.className = "region-card"

    for category in CATEGORIES:
        document.getElementById(f"{prefix}-{category}-count").innerText = str(r.capacity[category])
        invest_button = document.getElementById(f"{prefix}-{category}-invest-button")
        invest_button.innerText = f"{CATEGORY_ICON[category]} ({INVEST_COST[category]})"
        invest_button.disabled = r.funds < INVEST_COST[category]


def render_worst_case_region():
    """G13: renders Region D's read-only stats into its own elements —
    no invest buttons, since it never receives player input, only the
    same graph/status readouts every other region gets. Always keeps
    its DOM up to date regardless of worst_case_region_revealed, so the
    numbers are correct the instant a player opens the panel rather than
    only starting from whenever they first reveal it."""
    r = region_d
    document.getElementById("d-temperature-display").innerText = deg(r.temperature, plus=True)
    document.getElementById("d-funds-display").innerText = f"Funds: {r.funds:.0f}"
    document.getElementById("d-graph").innerHTML = mini_temp_graph_svg(
        r.temperature_history, "Region D", r.dampening_history
    )

    status = _melt_status_label(r)
    melt_status_el = document.getElementById("d-melt-status-display")
    melt_status_el.innerText = status.capitalize()
    suffix = {"stable": "", "melting": " melt-status--active", "critical": " melt-status--critical"}[status]
    melt_status_el.className = "region-melt-status" + suffix

    card_el = document.getElementById("d-region-card")
    if r.just_started_melting:
        card_el.className = "region-card tipping-flash"
        r.just_started_melting = False
    else:
        card_el.className = "region-card"


def _degrees_word(value, digits=1):
    """Spoken form of a rise in the chosen unit ('+5.0 degrees' in Celsius)."""
    if runstate.temp_unit == "f":
        return f"+{value * 1.8:.{digits}f} degrees Fahrenheit"
    if runstate.temp_unit == "k":
        return f"+{value:.{digits}f} kelvin"
    return f"+{value:.{digits}f} degrees"


def graph_summary_text(name, history):
    """G-10: one plain sentence describing a mini-graph for a screen reader."""
    if len(history) < 2:
        return f"{name} temperature graph: not enough rounds yet."
    first, last = history[0], history[-1]
    threshold = _degrees_word(MELT_THRESHOLD, 0).replace(" degrees", " degree")
    crossed = (
        f"crossed the {threshold} melt threshold"
        if max(history) >= MELT_THRESHOLD
        else f"still under the {threshold} melt threshold"
    )
    return (
        f"{name} temperature over {len(history)} rounds: from {_degrees_word(first)} to "
        f"{_degrees_word(last)}, {crossed}."
    )
