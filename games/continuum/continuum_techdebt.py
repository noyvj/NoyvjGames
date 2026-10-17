"""Technical debt (K-4): Quick builds, the refactor button and the panel."""

from js import document

import sim
import techdebt

import continuum_runstate as runstate
from continuum_base import _pc_layout

render = None  # placeholder: continuum_renderer fills this in when it is imported (it comes later)

# ===========================================================================
# K-4: technical debt (Digital Age and later). The rules live in techdebt.py;
# this is the DOM half: the Quick builds toggle, the refactor button and the
# status lines. The section is its own block (not inside #buildings) so it is
# still reachable in the Hamlet view and the Desktop boot, which hide the
# ordinary Build panel.
# ===========================================================================
def _easter_egg(found):
    """K-23: writes a once-only flavour line into the log (hidden with the story toggle)."""
    if found is not None:
        runstate.chronicle.log_challenge(runstate.state.season, runstate.state.era, found[1])


def _debt_hazard():
    """0/1/2: the civic map's technical-debt tint band for the live settlement."""
    if runstate.campaign.revisiting is not None or not techdebt.active(runstate.state.era):
        return 0
    return techdebt.hazard_level(techdebt.get(runstate.campaign.ui)["debt"])


def _book_quick_build(building):
    """Called after a build succeeded at full price: refunds the quick-build
    discount and books the debt. Does nothing outside the Digital Age on, in a
    Look Back, or with Quick builds off."""
    if runstate.campaign.revisiting is not None or not techdebt.active(runstate.state.era):
        return False
    refund = techdebt.quick_build(runstate.campaign.ui, sim.BUILDING_COST[building])
    if refund > 0:
        runstate.state.resources["materials"] += refund
    return refund > 0


def on_toggle_quick_build(event=None):
    if runstate.campaign.revisiting is not None or not techdebt.active(runstate.state.era):
        return
    record = techdebt.get(runstate.campaign.ui)
    techdebt.set_quick(runstate.campaign.ui, not record["quick"])
    render()


def on_toggle_refactor(event=None):
    if runstate.campaign.revisiting is not None or not techdebt.active(runstate.state.era):
        return
    record = techdebt.get(runstate.campaign.ui)
    techdebt.schedule_refactor(runstate.campaign.ui, not record["refactor"])
    render()


def update_techdebt_display():
    section = document.getElementById("techdebt")
    active = techdebt.active(runstate.state.era)
    section.hidden = not (active or _pc_layout())
    record = techdebt.get(runstate.campaign.ui)
    quick = document.getElementById("quick-build-toggle-button")
    refactor = document.getElementById("refactor-button")
    status = document.getElementById("techdebt-status-display")
    note = document.getElementById("techdebt-note-display")
    quick.hidden = not active
    refactor.hidden = not active
    if not active:
        status.innerText = "Technical debt begins in the Digital Age."
        note.innerText = (
            "From then on you can build quickly and cheaply, at the price of debt that "
            "costs upkeep and output until you schedule a refactor season."
        )
        return
    locked = runstate.campaign.revisiting is not None
    quick.innerText = f"⚡ Quick builds: {'ON' if record['quick'] else 'OFF'}"
    quick.classList.toggle("active", record["quick"])
    quick.setAttribute("aria-pressed", "true" if record["quick"] else "false")
    quick.disabled = locked
    refactor.innerText = (
        "🔧 Refactor season scheduled: cancel" if record["refactor"] else "🔧 Schedule a refactor season"
    )
    refactor.setAttribute("aria-pressed", "true" if record["refactor"] else "false")
    refactor.disabled = locked or (record["debt"] <= 0 and not record["refactor"])
    status.innerText = " ".join(techdebt.status_lines(runstate.state, record))
    cost = min(sim.BUILDING_COST[b] for b in sim.buildings_for_era(runstate.state.era))
    note.innerText = techdebt.build_note(record, cost)
