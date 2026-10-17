"""Custom plot layouts (B-29): presets, saved layouts, bests and the editor."""

import json

from js import document

import canopy_runstate as runstate
from canopy_carbon import carbon_chart_svg, carbon_status_text, sale_preview
from canopy_helpers import _el, _read_local_storage_item, _write_local_storage_item, plot_coordinate_label
from canopy_lifetime import lifetime_rows
from canopy_rules import BARE
from canopy_valuation import layout_active, standing_forest_value


# B-29 (2026-10-09): custom grid layouts. A layout says which cells of the current grid are plots; the rest are open ground
# (blocked plots that never grow, cannot be selected and are left out of every count). A layout is a string of 1 (plot) and 0
# (open ground), one character per cell, row by row. Presets: island, ring, plus and river-split. Named layouts are kept on
# this device (up to six) each with its own best standing value. Starting a layout begins a new forest with no scenario,
# challenge or level, and a layout forest is kept out of the community comparison.
LAYOUT_MIN_PLOTS = 4
LAYOUT_STORAGE_KEY = "canopy_layouts_v1"
LAYOUT_MAX_SAVED = 6
LAYOUT_PRESET_LABELS = {"island": "Island", "ring": "Ring", "plus": "Plus", "river": "River split"}


def layout_preset_cells(kind, rows=None, cols=None):
    """The cells string for a preset at the given (default: current) grid size."""
    rows = runstate.GRID_ROWS if rows is None else rows
    cols = runstate.GRID_COLS if cols is None else cols
    out = []
    for r in range(rows):
        for c in range(cols):
            if kind == "island":  # an oval of land with a margin of open ground
                dr, dc = (r - (rows - 1) / 2) / (rows / 2), (c - (cols - 1) / 2) / (cols / 2)
                on = dr * dr + dc * dc <= 0.85
            elif kind == "ring":  # a loop of forest around open ground
                on = r in (0, rows - 1) or c in (0, cols - 1)
            elif kind == "plus":
                on = abs(r - (rows - 1) / 2) <= 0.5 or abs(c - (cols - 1) / 2) <= 0.5
            elif kind == "river":  # two banks split by a river with a single ford
                on = abs(c - (cols - 1) / 2) > 0.5 or r == rows // 2
            else:
                on = True
            out.append("1" if on else "0")
    return "".join(out)


def clean_layout_cells(cells, expected=None):
    """The cells string if it is valid for this grid (right length, only 0/1, enough plots), else None."""
    expected = runstate.GRID_ROWS * runstate.GRID_COLS if expected is None else expected
    if not isinstance(cells, str) or len(cells) != expected or set(cells) - {"0", "1"}:
        return None
    return cells if cells.count("1") >= LAYOUT_MIN_PLOTS else None


def apply_layout_to_plots(cells):
    for plot, ch in zip(runstate.plots, cells):
        plot.blocked = ch == "0"
        if plot.blocked:  # open ground holds nothing
            plot.state, plot.value = BARE, 0.0


def layout_bests_key(name):
    return str(name)[:20]


def load_saved_layouts():
    raw = _read_local_storage_item(LAYOUT_STORAGE_KEY)
    try:
        data = json.loads(raw) if raw else []
    except (ValueError, TypeError):
        return []
    out = []
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, dict):
            continue
        cells = clean_layout_cells(item.get("cells"), expected=len(str(item.get("cells", ""))))
        rows, cols = item.get("rows"), item.get("cols")
        if cells is None or not isinstance(rows, int) or not isinstance(cols, int) or rows * cols != len(cells):
            continue
        best = item.get("best")
        out.append({"name": str(item.get("name", "Layout"))[:20] or "Layout", "rows": rows, "cols": cols, "cells": cells,
                    "best": float(best) if isinstance(best, (int, float)) and not isinstance(best, bool) and 0 <= best < 1e12 else 0.0})
    return out[:LAYOUT_MAX_SAVED]


def save_layout(name, cells):
    """Stores a named layout for the current grid size (a same-named one is replaced, keeping its best)."""
    cells = clean_layout_cells(cells)
    if cells is None:
        return None
    name = " ".join(str(name or "").split())[:20] or f"Layout {len(load_saved_layouts()) + 1}"
    layouts = load_saved_layouts()
    previous = next((entry for entry in layouts if entry["name"] == name), None)
    layouts = [entry for entry in layouts if entry["name"] != name]
    layouts.append({"name": name, "rows": runstate.GRID_ROWS, "cols": runstate.GRID_COLS, "cells": cells, "best": previous["best"] if previous else 0.0})
    _write_local_storage_item(LAYOUT_STORAGE_KEY, json.dumps(layouts[-LAYOUT_MAX_SAVED:]))
    return name


def _update_layout_best():
    """Called every render: keeps the running named layout's own best standing value."""
    if runstate.current_layout is None or not runstate.current_layout.get("name"):
        return
    layouts = load_saved_layouts()
    value = standing_forest_value()
    for layout in layouts:
        if layout["name"] == runstate.current_layout["name"] and value > layout["best"]:
            layout["best"] = round(value, 2)
            _write_local_storage_item(LAYOUT_STORAGE_KEY, json.dumps(layouts))
            return


def layout_best_text():
    if runstate.current_layout is None:
        return ""
    name = runstate.current_layout.get("name") or "unnamed"
    layout = next((entry for entry in load_saved_layouts() if entry["name"] == runstate.current_layout.get("name")), None)
    best = layout["best"] if layout else 0.0
    return f"{name}: best standing {best:.1f}" if best > 0 else f"{name}: no best yet"


_layout_grid_signature = {}


def on_layout_grid_click(event):
    """One delegated listener for every cell button (the buttons are rebuilt when the draft changes)."""
    target = getattr(event, "target", None)
    cell = target.closest(".layout-cell") if target is not None and hasattr(target, "closest") else None
    raw = cell.getAttribute("data-index") if cell is not None else None
    try:
        toggle_draft_cell(int(raw))
    except (TypeError, ValueError):
        pass


def _draft_cells():
    if runstate.layout_draft is None or len(runstate.layout_draft) != runstate.GRID_ROWS * runstate.GRID_COLS:
        runstate.layout_draft = runstate.current_layout["cells"] if layout_active() and len(runstate.current_layout["cells"]) == runstate.GRID_ROWS * runstate.GRID_COLS else "1" * (runstate.GRID_ROWS * runstate.GRID_COLS)
    return runstate.layout_draft


def toggle_draft_cell(index):
    cells = _draft_cells()
    if not 0 <= index < len(cells):
        return False
    runstate.layout_draft = cells[:index] + ("0" if cells[index] == "1" else "1") + cells[index + 1:]
    render_layout_editor()
    return True


def on_layout_preset(kind):
    runstate.layout_draft = layout_preset_cells(kind)
    render_layout_editor()


def on_layout_save(event=None):
    name_box = _el("layout-name")
    save_layout(getattr(name_box, "value", ""), _draft_cells())
    render_layout_editor()


def on_layout_load(event=None):
    select = _el("layout-select")
    chosen = next((entry for entry in load_saved_layouts() if entry["name"] == getattr(select, "value", "")), None)
    if chosen is not None and chosen["rows"] == runstate.GRID_ROWS and chosen["cols"] == runstate.GRID_COLS:
        runstate.layout_draft = chosen["cells"]
        name_box = _el("layout-name")
        if name_box is not None:
            name_box.value = chosen["name"]
        render_layout_editor()


def render_layout_editor():
    grid = _el("layout-grid")
    status = _el("layout-status")
    cells = _draft_cells()
    signature = (cells, runstate.GRID_ROWS, runstate.GRID_COLS)
    if grid is not None and _layout_grid_signature.get("sig") != signature:  # rebuilt only on change, so keyboard focus survives the tick
        _layout_grid_signature["sig"] = signature
        grid.innerHTML = ""
        grid.setAttribute("data-cols", str(runstate.GRID_COLS))
        grid.style.gridTemplateColumns = f"repeat({runstate.GRID_COLS}, 1fr)"
        for i, ch in enumerate(cells):
            cell = document.createElement("button")
            cell.type = "button"
            cell.className = "layout-cell layout-cell--on" if ch == "1" else "layout-cell layout-cell--off"
            cell.innerText = "\u25cf" if ch == "1" else "\u25cb"
            cell.setAttribute("data-index", str(i))
            cell.setAttribute("aria-label", f"{plot_coordinate_label(i)}: {'plot' if ch == '1' else 'open ground'}. Press to toggle")
            cell.setAttribute("aria-pressed", "true" if ch == "1" else "false")
            grid.appendChild(cell)
    if status is not None:
        count = cells.count("1")
        problem = "" if count >= LAYOUT_MIN_PLOTS else f" At least {LAYOUT_MIN_PLOTS} plots are needed."
        live = f" Live layout: {layout_best_text()}." if layout_active() else " Live: the full grid."
        status.innerText = f"Draft: {count} plots, {len(cells) - count} open ground.{problem}{live} Apply starts a new forest."
    select = _el("layout-select")
    if select is not None:
        previous = getattr(select, "value", "")
        select.innerHTML = ""
        names = []
        for layout in load_saved_layouts():
            if layout["rows"] == runstate.GRID_ROWS and layout["cols"] == runstate.GRID_COLS:
                option = document.createElement("option")
                option.value = layout["name"]
                option.innerText = f"{layout['name']} (best {layout['best']:.1f})"
                select.appendChild(option)
                names.append(layout["name"])
        if previous in names:
            select.value = previous
    apply_button = _el("layout-apply-button")
    if apply_button is not None:
        apply_button.disabled = cells.count("1") < LAYOUT_MIN_PLOTS


def render_layout_badge():
    badge = _el("layout-banner")
    if badge is not None:
        badge.hidden = not layout_active()
        badge.innerText = (f"Custom layout ({layout_best_text()}). Kept out of the community comparison and the standard best." if layout_active() else "")


def render_carbon():
    status, chart = _el("carbon-status"), _el("carbon-chart")
    if status is not None:
        status.innerText = carbon_status_text()
    if chart is not None:
        chart.innerHTML = carbon_chart_svg()
    preview = sale_preview()
    for button_id, enabled in (("carbon-sell-button", preview["credits"] >= 0.5), ("carbon-sell-half-button", preview["credits"] >= 1.0)):
        button = _el(button_id)
        if button is not None:
            button.disabled = not enabled


def render_lifetime_stats():
    element = _el("lifetime-stats-table")
    if element is not None:
        element.innerText = "\n".join(f"{label}: {value}" for label, value in lifetime_rows())


def _request_snapshot(request, kind):
    """B-14: what to remember about a request at the moment it is answered."""
    idx = request["plot_index"]
    return {"plot": idx, "kind": kind, "value_then": round(float(runstate.plots[idx].value), 2), "tick": runstate.forest_tick}
