"""The region board (sortable table) and the focus view."""

from js import document

import thaw_runstate as runstate
from thaw_bridge import _escape
from thaw_graphs import (
    _graph_end_marker, _melt_status_label, _rescue_status_text, graph_indexes, graph_summary_text,
)
from thaw_model import REGION_FLAVOR, deg, region, region_b, region_c, region_d
from thaw_records import climate_archive
from thaw_rules import (
    CATEGORIES, CATEGORY_ICON, CATEGORY_LABEL, INVEST_COST, MELT_THRESHOLD, RESCUE_COST,
    SECOND_WARMING_MILESTONE,
)


# ===========================================================================
# G-12: the board-room table. All four regions in one sortable table: temperature, acceleration,
# dampening, funds, rounds since the last tipping event and the best degrees saved ever recorded on
# this device, each row with a small temperature sparkline. Region D is a greyed row at the bottom
# (only once its reveal button has been used, like everywhere else) and is never part of the sort.
# ===========================================================================
BOARD_COLUMNS = (
    ("region", "Region"),
    ("temp", "Temperature"),
    ("accel", "Acceleration"),
    ("damp", "Dampening"),
    ("funds", "Funds"),
    ("since", "Rounds since tipping"),
    ("best", "Best saved"),
)

TINY_WIDTH = 60
TINY_HEIGHT = 16


def board_rows():
    """One dict per region (A, B, C, then D when revealed) with raw sortable values and display text."""
    rows = []
    regions = [("A", region), ("B", region_b), ("C", region_c)]
    if runstate.worst_case_region_revealed:
        regions.append(("D", region_d))
    for label, r in regions:
        managed = label != "D"
        best = climate_archive[label]["best_saved"] if managed else None
        rows.append({
            "label": label,
            "managed": managed,
            "region": label,
            "temp": r.temperature,
            "accel": r.acceleration_factor(),
            "damp": r.feedback_dampening_fraction(),
            "funds": r.funds,
            "since": r.rounds_since_tipping_event,
            "best": best,
            "history": list(r.temperature_history),
            "text": {
                "region": f"Region {label}" + ("" if managed else " (worst case)"),
                "temp": deg(r.temperature, plus=True),
                "accel": f"{r.acceleration_factor():.2f}x",
                "damp": f"{r.feedback_dampening_fraction() * 100:.0f}%",
                "funds": f"{r.funds:.0f}",
                "since": str(r.rounds_since_tipping_event) + ("" if r.tipping_events else " (none yet)"),
                "best": deg(best) if best is not None else "\u2014",
            },
        })
    return rows


def sorted_board_rows():
    """Managed regions sorted by the chosen column (ties keep A, B, C order); D always last."""
    rows = board_rows()
    managed = [row for row in rows if row["managed"]]
    managed.sort(key=lambda row: row[runstate.board_sort], reverse=runstate.board_descending)
    return managed + [row for row in rows if not row["managed"]]


def set_board_sort(key):
    """Picks a column; picking the current one again flips the direction. Returns True if valid."""
    if key not in dict(BOARD_COLUMNS):
        return False
    if key == runstate.board_sort:
        runstate.board_descending = not runstate.board_descending
    else:
        runstate.board_sort, runstate.board_descending = key, False
    return True


def tiny_line_svg(values, label):
    """A small, axis-free temperature line for a table row (no marker, no threshold)."""
    if len(values) < 2:
        return ""
    lo, hi = min(values), max(values)
    span = hi - lo
    ys = [TINY_HEIGHT / 2 if span < 1e-9 else TINY_HEIGHT - 1 - ((v - lo) / span) * (TINY_HEIGHT - 2) for v in values]
    xs = [i * (TINY_WIDTH / (len(values) - 1)) for i in range(len(values))]
    points = " ".join(f"{xs[i]:.1f},{ys[i]:.1f}" for i in graph_indexes(values))  # G-11
    return (
        f'<svg viewBox="0 0 {TINY_WIDTH} {TINY_HEIGHT}" class="board-spark" role="img" aria-label="{_escape(label)}">'
        f'<polyline points="{points}" class="board-spark-line" /></svg>'
    )


def board_html():
    parts = []
    for row in sorted_board_rows():
        cells = [f'<th scope="row">{_escape(row["text"]["region"])}</th>']
        for key, _label in BOARD_COLUMNS[1:]:
            cells.append(f"<td>{_escape(row['text'][key])}</td>")
        spark = tiny_line_svg(
            row["history"], graph_summary_text(f"Region {row['label']}", row["history"])
        ) or '<span class="board-nospark">after round 2</span>'
        cells.append(f"<td>{spark}</td>")
        parts.append(f'<tr class="{"board-row" if row["managed"] else "board-row board-row--grey"}">{"".join(cells)}</tr>')
    return "".join(parts)


def render_board():
    direction = "descending" if runstate.board_descending else "ascending"
    for key, label in BOARD_COLUMNS:
        th = document.getElementById(f"board-th-{key}")
        button = document.getElementById(f"board-sort-{key}")
        if key == runstate.board_sort:
            th.setAttribute("aria-sort", direction)
            arrow = "\u25BC" if runstate.board_descending else "\u25B2"
            button.innerText = f"{label} {arrow}"
            button.className = "board-sort board-sort--on"
        else:
            th.setAttribute("aria-sort", "none")
            button.innerText = label
            button.className = "board-sort"
    document.getElementById("board-body").innerHTML = board_html()
    document.getElementById("board-caption").innerText = (
        f"Sorted by {dict(BOARD_COLUMNS)[runstate.board_sort].lower()}, {direction}. Click a heading to re-sort; "
        f"click it again to reverse."
        + ("" if runstate.worst_case_region_revealed else " Region D joins the table, greyed out, once you reveal it.")
    )


# ===========================================================================
# G-17: the single-region focus view. One region's graph at full width with axis labels, the
# melt threshold and the second milestone marked, all its readouts in a list and its lever buttons
# right underneath, so a long look at one region needs no scrolling between graph and controls.
# ===========================================================================
FOCUS_W = 320
FOCUS_H = 120
FOCUS_PAD_LEFT = 34
FOCUS_PAD_BOTTOM = 16
FOCUS_KEYS = ("a", "b", "c")


def _focus_region_for(key):
    return {"a": region, "b": region_b, "c": region_c}.get(key, region)


def _focus_key():
    key = document.getElementById("focus-region").value
    return key if key in FOCUS_KEYS else "a"


def focus_graph_svg(values, name, key):
    """A larger, labelled version of the region's temperature line: y labels in the chosen unit,
    first and last round, the melt threshold and the second milestone as dashed lines."""
    if len(values) < 2:
        return ""
    top = max(max(values), SECOND_WARMING_MILESTONE) * 1.08
    plot_w = FOCUS_W - FOCUS_PAD_LEFT - 4
    plot_h = FOCUS_H - FOCUS_PAD_BOTTOM - 4

    def y_of(v):
        return 4 + plot_h - (v / top) * plot_h

    n = len(values)
    xs = [FOCUS_PAD_LEFT + i * plot_w / (n - 1) for i in range(n)]
    points = " ".join(f"{xs[i]:.1f},{y_of(values[i]):.1f}" for i in graph_indexes(values))  # G-11
    guides = ""
    for value, css in ((MELT_THRESHOLD, "focus-guide focus-guide--melt"), (SECOND_WARMING_MILESTONE, "focus-guide focus-guide--second")):
        y = y_of(value)
        guides += (
            f'<line x1="{FOCUS_PAD_LEFT}" y1="{y:.1f}" x2="{FOCUS_W - 4}" y2="{y:.1f}" class="{css}" />'
            f'<text x="{FOCUS_PAD_LEFT - 3}" y="{y + 3:.1f}" class="focus-tick" text-anchor="end">{deg(value, 0, plus=True)}</text>'
        )
    base_y = y_of(0)
    ticks = (
        f'<line x1="{FOCUS_PAD_LEFT}" y1="{base_y:.1f}" x2="{FOCUS_W - 4}" y2="{base_y:.1f}" class="focus-axis" />'
        f'<text x="{FOCUS_PAD_LEFT - 3}" y="{base_y + 3:.1f}" class="focus-tick" text-anchor="end">{deg(0, 0, plus=True)}</text>'
        f'<text x="{FOCUS_PAD_LEFT}" y="{FOCUS_H - 3}" class="focus-tick" text-anchor="start">R1</text>'
        f'<text x="{FOCUS_W - 4}" y="{FOCUS_H - 3}" class="focus-tick" text-anchor="end">R{n}</text>'
    )
    summary = _escape(graph_summary_text(name, values))
    end_marker = _graph_end_marker(key, xs[-1], y_of(values[-1]))
    return (
        f'<svg viewBox="0 0 {FOCUS_W} {FOCUS_H}" class="focus-graph-svg mini-temp-graph-svg graph-region-{key}" '
        f'role="img" aria-label="{summary}"><title>{summary}</title>'
        f"{ticks}{guides}"
        f'<polyline points="{points}" class="mini-temp-line" />'
        f"{end_marker}</svg>"
    )


def focus_readouts(r):
    """The focus list: (label, value) pairs for one region."""
    status = _melt_status_label(r)
    rows = [
        ("Temperature", deg(r.temperature, plus=True)),
        ("Status", status.capitalize()),
        ("Funds", f"{r.funds:.0f}"),
        ("Warming rate", f"{deg(r.current_rise_rate(), 2)}/round ({r.acceleration_factor():.2f}x background)"),
        ("Feedback dampening", f"{r.feedback_dampening_fraction() * 100:.0f}%"),
        ("Saved versus no action", deg(max(0.0, r.temperature_saved()))),
        ("Units", " / ".join(f"{r.capacity[c]} {c}" for c in CATEGORIES)),
        ("Rounds since a tipping event", str(r.rounds_since_tipping_event) + ("" if r.tipping_events else " (none yet)")),
    ]
    rescue = _rescue_status_text(r)
    if rescue:
        rows.append(("Emergency rescue", rescue))
    if r.restored_total > 0:
        rows.append(("Restoration", f"{deg(r.restored_total)} pulled back so far"))
    return rows


def render_focus():
    key = _focus_key()
    r = _focus_region_for(key)
    name = f"Region {key.upper()}"
    document.getElementById("focus-graph").innerHTML = focus_graph_svg(r.temperature_history, name, key) or (
        '<p class="comparison-message">The graph appears after the second round.</p>'
    )
    document.getElementById("focus-readouts").innerHTML = "".join(
        f"<li><span>{_escape(label)}</span><span>{_escape(value)}</span></li>" for label, value in focus_readouts(r)
    )
    for category in CATEGORIES:
        button = document.getElementById(f"focus-invest-{category}")
        button.innerText = f"{CATEGORY_ICON[category]} {CATEGORY_LABEL[category]} ({INVEST_COST[category]})"
        button.disabled = r.funds < INVEST_COST[category] or runstate.run_over
    rescue = document.getElementById("focus-rescue-button")
    rescue.hidden = not (r.is_critical() and not r.rescue_used)
    rescue.disabled = not r.can_rescue()
    rescue.innerText = f"\U0001F6DF Emergency rescue ({RESCUE_COST:.0f})"
    document.getElementById("focus-title").innerText = f"{name}: {REGION_FLAVOR_FOR_FOCUS[key]}"


REGION_FLAVOR_FOR_FOCUS = {
    "a": "high-arctic peatland, your home region",
    "b": REGION_FLAVOR["b"].split(" \u2014 ")[0].lower(),
    "c": REGION_FLAVOR["c"].split(" \u2014 ")[0].lower(),
}
