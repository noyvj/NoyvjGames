"""The storage-arbitrage mode and the emergency messages, and their render.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

from js import document

import grid_runstate as runstate
from grid_rules import EMERGENCY_HOLD_ROUNDS


ARBITRAGE_MODE_LABEL = {"idle": "Idle", "charge": "Charge", "discharge": "Discharge"}


def arbitrage_status_message():
    """C9: one plain-text line -- stored level plus what last round did."""
    cap = runstate.state.storage_cap()
    text = f"Stored {runstate.state.stored_energy:.0f}/{cap:.0f}."
    last = runstate.state.last_arbitrage
    if last is not None:
        if last["mode"] == "charge":
            text += f" Last round: banked {last['units']:.0f} surplus."
        else:
            text += f" Last round: sold {last['units']:.0f} for +{last['revenue']:.0f} funds."
    return text


def emergency_message():
    """C27: banner text for the emergency scenario, or '' outside it."""
    em = runstate.state.emergency
    if em is None:
        return ""
    if em["status"] == "stabilized":
        return "Emergency over: the grid is stabilized. The run carries on as normal."
    if em["status"] == "missed":
        return (
            "Emergency window closed without stabilizing. There is no game over -- "
            "keep building; demand still has to be met."
        )
    return (
        f"EMERGENCY: a major disruption left capacity {runstate.state.total_capacity()} against demand {runstate.state.demand}. "
        f"Get capacity to at least demand for {EMERGENCY_HOLD_ROUNDS} rounds in a row "
        f"(held {em['hold']}/{EMERGENCY_HOLD_ROUNDS}, {em['rounds_left']} round(s) left)."
    )


def _render_arbitrage_and_emergency():
    has_battery = runstate.state.plant_counts["battery"] > 0
    mode_button = document.getElementById("arbitrage-mode-button")
    mode_button.innerText = f"Storage: {ARBITRAGE_MODE_LABEL[runstate.state.arbitrage_mode]}"
    mode_button.disabled = not has_battery
    mode_button.title = (
        "Click to cycle Idle / Charge / Discharge for the next round."
        if has_battery
        else "Build a battery to use storage arbitrage."
    )
    status_el = document.getElementById("arbitrage-status-display")
    status_el.hidden = not has_battery
    status_el.innerText = arbitrage_status_message() if has_battery else ""
    emergency_el = document.getElementById("emergency-status-display")
    text = emergency_message()
    emergency_el.hidden = not text
    emergency_el.innerText = text
