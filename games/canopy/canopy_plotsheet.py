"""Plot notes and the phone bottom sheet."""

import canopy_runstate as runstate
from canopy_helpers import _el, plot_coordinate_label
from canopy_rules import STATE_LABEL, VALID_ACTIONS
from canopy_worldvars import PLOT_NOTE_MAX, plot_notes


def clean_plot_note(text):
    """A note as stored: control characters dropped, whitespace collapsed, at most PLOT_NOTE_MAX characters."""
    text = "".join(ch for ch in str(text or "") if ch.isprintable())
    return " ".join(text.split())[:PLOT_NOTE_MAX]


def set_plot_note(index, text):
    """Saves (or, with empty text, removes) the note on a main-grid plot. Returns the stored note."""
    if not 0 <= index < len(runstate.plots):
        return ""
    note = clean_plot_note(text)
    if note:
        plot_notes[index] = note
    else:
        plot_notes.pop(index, None)
    return note


def plot_index_from_tile_id(tile_id):
    """'plot-12' -> 12; anything else (highland and wetland tiles, junk) -> None."""
    text = str(tile_id or "")
    if text.startswith("plot-") and text[5:].isdigit():
        index = int(text[5:])
        return index if 0 <= index < len(runstate.plots) else None
    return None


# B-28 (2026-10-09): on a phone-width screen a long-press (or right-click) on a plot opens a bottom sheet with large
# Clear / Replant / Adopt / Note buttons. The sheet only calls the ordinary handlers on the selected plot, and the
# desktop layout never opens it.
PHONE_MAX_WIDTH_PX = 700


def is_phone_layout():
    try:
        import js  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        return bool(js.window.matchMedia(f"(max-width: {PHONE_MAX_WIDTH_PX}px)").matches)
    except Exception:  # noqa: BLE001 -- outside a browser there is no media query, so it is not a phone
        return False


def open_plot_sheet():
    if runstate.selected_index is None:
        return
    runstate.plot_sheet_open = True
    render_plot_sheet()


def close_plot_sheet(event=None):
    runstate.plot_sheet_open = False
    render_plot_sheet()


def plot_sheet_actions():
    """Which of the sheet's buttons are usable for the selected plot, and what to call them."""
    if runstate.selected_index is None:
        return {"clear": (False, "Clear"), "cut": (False, "Clear-cut"), "replant": (False, "Replant"), "adopt": (False, "Adopt"), "note": (False, "Note")}
    plot = runstate.plots[runstate.selected_index]
    can_clear = "clear" in VALID_ACTIONS[plot.state] and plot.index != runstate.heart_tree_index
    can_replant = "replant" in VALID_ACTIONS[plot.state]
    adopted = runstate.adopted_plot_index == runstate.selected_index
    return {
        "clear": (can_clear, "Clear"),
        "cut": (can_clear and not runstate.survey_mode and not plot.blocked, "Clear-cut"),  # GB-21
        "replant": (can_replant, "Replant"),
        "adopt": (True, "Release plot" if adopted else "Adopt plot"),
        "note": (True, "Edit note"),
    }


def render_plot_sheet():
    sheet = _el("plot-sheet")
    if sheet is None:
        return
    sheet.hidden = not (runstate.plot_sheet_open and runstate.selected_index is not None)
    if sheet.hidden:
        return
    title = _el("plot-sheet-title")
    if title is not None:
        plot = runstate.plots[runstate.selected_index]
        title.innerText = f"Plot {plot_coordinate_label(runstate.selected_index)}: {STATE_LABEL[plot.state]}, value {plot.value:.1f}"
    for name, (enabled, text) in plot_sheet_actions().items():
        button = _el(f"plot-sheet-{name}")
        if button is not None:
            button.disabled = not enabled
            button.innerText = text


def render_plot_note_input():
    """Keeps the note box showing the selected plot's note, without overwriting what is being typed on a re-render."""
    box = _el("plot-note-input")
    if box is None or runstate.selected_index == runstate._note_input_for:
        return
    runstate._note_input_for = runstate.selected_index
    box.value = plot_notes.get(runstate.selected_index, "") if runstate.selected_index is not None else ""
