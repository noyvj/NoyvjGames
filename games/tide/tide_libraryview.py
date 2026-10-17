"""The session library panel and its comparison graph."""

import html

from js import document
from pyodide.ffi import create_proxy

import tide_runstate as runstate
from tide_graphs import (
    SPARKLINE_HEIGHT, SPARKLINE_WIDTH, _crosshair_attr, _series_svg, _xy, graph_range_text,
    graph_window_start, render_graphs,
)
from tide_library import _ghosts, library_delete, library_get, library_records, library_summary_text
from tide_rules import FISH_DAMAGE_SCALE, LIBRARY_CURRENT
from tide_runcode import render_run_code_box


# render() is defined in tide_renderer, which comes later in the module list; that module puts it here when it
# loads (see the end of tide_renderer.py). Calls below find it at run time.
render = None


def library_compare_svg(rec_a, rec_b):
    """A solid, B dashed; acidity purple, fish yield green. "" if either is missing."""
    if rec_a is None or rec_b is None or not rec_a["acidity"] or not rec_b["acidity"]:
        return ""
    full = max(len(rec_a["acidity"]), len(rec_b["acidity"]))
    start = graph_window_start(full)
    count = full - start
    step = SPARKLINE_WIDTH / max(1, count - 1)
    lines = []
    for j in range(count):
        index = start + j
        parts = []
        for label, record in (("A", rec_a), ("B", rec_b)):
            if index < len(record["acidity"]):
                piece = f"{label} {record['name']}: acidity {record['acidity'][index] * FISH_DAMAGE_SCALE:.1f}"
                if index < len(record["fish"]):
                    piece += f", fishing yield {record['fish'][index] * 100:.0f}%"
                parts.append(piece)
        lines.append(f"Season {index + 1}: " + (" | ".join(parts) if parts else "no data"))
    drawn = ""
    for record, dash in ((rec_a, None), (rec_b, "4 3")):
        drawn += _series_svg(_xy(record["acidity"][start:], step), "acidity", dash=dash)
        drawn += _series_svg(_xy(record["fish"][start:], step), "fish", dash=dash)
    label = html.escape(f"Session A {rec_a['name']} (solid) against session B {rec_b['name']} (dashed)", quote=True)
    return (
        f'<svg viewBox="0 0 {SPARKLINE_WIDTH} {SPARKLINE_HEIGHT}" class="acidity-fish-sparkline" '
        f'role="img" tabindex="0"{_crosshair_attr(lines)} '
        f'aria-label="Acidity and fishing yield over {graph_range_text()}: {label}. '
        f'Left and right arrow keys read each season.">{drawn}</svg>'
    )


def _session_options(records, blank=None, include_current=True):
    options = []
    if blank is not None:
        options.append(f'<option value="">{html.escape(blank)}</option>')
    if include_current:
        options.append(f'<option value="{LIBRARY_CURRENT}">Current session (Season {runstate.state.season})</option>')
    for record in list(records) + list(_ghosts.values()):
        options.append(
            f'<option value="{record["id"]}">{html.escape(record["name"])} '
            f"({record['seasons']} seasons)</option>"
        )
    return "".join(options)


def render_library():
    toggle = document.getElementById("library-toggle-button")
    panel = document.getElementById("library-panel")
    if toggle is None or panel is None:
        return
    toggle.innerText = "Hide Session Library" if runstate.library_open else "📚 Session Library"
    panel.hidden = not runstate.library_open
    if not runstate.library_open:
        return
    records = library_records()
    valid = {str(r["id"]) for r in records} | set(_ghosts)
    if runstate.library_a != LIBRARY_CURRENT and runstate.library_a not in valid:
        runstate.library_a = LIBRARY_CURRENT
    if runstate.library_b not in valid:
        runstate.library_b = next((str(r["id"]) for r in reversed(records)), "")
    if runstate.library_overlay_id and runstate.library_overlay_id not in valid:
        runstate.library_overlay_id = ""
    for select_id, options, value in (
        ("library-select-a", _session_options(records), runstate.library_a),
        ("library-select-b", _session_options(records, blank="(choose a session)"), runstate.library_b),
        ("library-overlay-select", _session_options(records, blank="(none)", include_current=False), runstate.library_overlay_id),
    ):
        select = document.getElementById(select_id)
        if select is not None:
            select.innerHTML = options
            select.value = value
    status = document.getElementById("library-status")
    if status is not None:
        status.innerText = runstate._library_status or (
            f"{len(records)} saved session(s). Sessions are kept in this browser only."
        )
    listing = document.getElementById("library-list")
    if listing is not None:
        for proxy in runstate._library_proxies:
            proxy.destroy()
        runstate._library_proxies = []
        listing.innerHTML = ""
        if not records:
            listing.innerText = "Nothing saved yet. Play a few seasons, then save the session here."
        for record in records:
            item = document.createElement("li")
            item.className = "library-item"
            text = document.createElement("span")
            text.innerText = library_summary_text(record)
            remove = document.createElement("button")
            remove.className = "secondary library-delete"
            remove.type = "button"
            remove.innerText = "Delete"
            remove.setAttribute("aria-label", f"Delete saved session {record['name']}")
            proxy = create_proxy(_make_library_delete_handler(record["id"]))
            runstate._library_proxies.append(proxy)
            remove.addEventListener("click", proxy)
            item.appendChild(text)
            item.appendChild(remove)
            listing.appendChild(item)
    render_run_code_box()
    compare = document.getElementById("library-compare-graph")
    if compare is not None:
        svg = library_compare_svg(library_get(runstate.library_a), library_get(runstate.library_b) if runstate.library_b else None)
        compare.innerHTML = svg
        if not svg:
            compare.innerText = "Choose two sessions to overlay them: A is drawn solid, B dashed."
    caption = document.getElementById("library-compare-caption")
    if caption is not None:
        a, b = library_get(runstate.library_a), library_get(runstate.library_b) if runstate.library_b else None
        caption.innerText = (
            f"A (solid): {library_summary_text(a)} B (dashed): {library_summary_text(b)}" if a and b else ""
        )


def _make_library_delete_handler(record_id):
    def handler(event=None):
        library_delete(record_id)
        render()
    return handler


def _make_library_select_handler(name):
    def handler(event=None):
        value = str(getattr(getattr(event, "target", None), "value", ""))
        vars(runstate)[name] = value
        if name == "library_overlay_id":
            render_graphs()
        render_library()
    return handler
