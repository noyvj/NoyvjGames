"""Canopy — Deforestation & Carbon Sinks Game.

Runs in-browser via Pyodide. Milestone 1: grid of forest plots with a
state machine (PRESERVED/BARE/REPLANTING/RECOVERED) and click-driven
Clear/Replant actions. Passive value, payout economics, and soil
degradation land in later milestones.
"""

from js import document
from pyodide.ffi import create_proxy

GRID_ROWS = 6
GRID_COLS = 6

PRESERVED = "preserved"
BARE = "bare"
REPLANTING = "replanting"
RECOVERED = "recovered"

STATE_LABEL = {
    PRESERVED: "Preserved",
    BARE: "Bare",
    REPLANTING: "Replanting",
    RECOVERED: "Recovered",
}

# Which of the two actions are valid from each state. Preserve isn't a
# click action — a PRESERVED/RECOVERED plot accrues passive value simply
# by being left alone (see the plan's "preserve = do nothing" framing).
VALID_ACTIONS = {
    PRESERVED: {"clear"},
    RECOVERED: {"clear"},
    BARE: {"replant"},
    REPLANTING: set(),
}


class Plot:
    def __init__(self, index):
        self.index = index
        self.state = PRESERVED

    def clear(self):
        if "clear" not in VALID_ACTIONS[self.state]:
            return False
        self.state = BARE
        return True

    def replant(self):
        if "replant" not in VALID_ACTIONS[self.state]:
            return False
        self.state = REPLANTING
        return True

    def finish_recovery(self):
        """Transitions a REPLANTING plot to RECOVERED (milestone 4 wires up the timer)."""
        if self.state != REPLANTING:
            return False
        self.state = RECOVERED
        return True


plots = [Plot(i) for i in range(GRID_ROWS * GRID_COLS)]
selected_index = None


def _plot_tile_id(index):
    return f"plot-{index}"


def render_grid():
    grid_el = document.getElementById("plot-grid")
    grid_el.innerHTML = ""
    for plot in plots:
        tile = document.createElement("button")
        tile.id = _plot_tile_id(plot.index)
        tile.className = f"plot-tile plot-{plot.state}"
        if plot.index == selected_index:
            tile.className += " plot-selected"
        tile.title = STATE_LABEL[plot.state]
        tile.addEventListener("click", create_proxy(_make_select_handler(plot.index)))
        grid_el.appendChild(tile)


def render_panel():
    panel_state_el = document.getElementById("selected-plot-state")
    clear_button = document.getElementById("clear-button")
    replant_button = document.getElementById("replant-button")

    if selected_index is None:
        panel_state_el.innerText = "No plot selected"
        clear_button.disabled = True
        replant_button.disabled = True
        return

    plot = plots[selected_index]
    panel_state_el.innerText = f"Plot {selected_index}: {STATE_LABEL[plot.state]}"
    clear_button.disabled = "clear" not in VALID_ACTIONS[plot.state]
    replant_button.disabled = "replant" not in VALID_ACTIONS[plot.state]


def render():
    render_grid()
    render_panel()


def _make_select_handler(index):
    def handler(event):
        select_plot(index)
    return handler


def select_plot(index):
    global selected_index
    selected_index = index
    render()


def on_clear(event=None):
    if selected_index is None:
        return
    plots[selected_index].clear()
    render()


def on_replant(event=None):
    if selected_index is None:
        return
    plots[selected_index].replant()
    render()


def setup():
    clear_button = document.getElementById("clear-button")
    replant_button = document.getElementById("replant-button")
    clear_button.innerText = "Clear"
    replant_button.innerText = "Replant"
    clear_button.addEventListener("click", create_proxy(on_clear))
    replant_button.addEventListener("click", create_proxy(on_replant))
    render()


setup()
