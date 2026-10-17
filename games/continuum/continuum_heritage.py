"""Heritage sites: listing, demolish confirm and the panel."""

from js import document
from pyodide.ffi import create_proxy

import heritage
import sim

import continuum_runstate as runstate
from continuum_achievements import _check_new_achievements_for_toast
from continuum_base import _resting
from continuum_dynasty import _rest_reason

render = None  # placeholder: continuum_renderer fills this in when it is imported (it comes later)

# --- K-5 living ruins (heritage sites) ----------------------------------------------------------------------
_heritage_proxies = []


def _heritage_sites():
    return [] if _resting() else heritage.sites_before(runstate.campaign.furthest_era, runstate.campaign.ui)


def _heritage_summary_text():
    if _resting():
        return "resting (comparable run)"
    kept, cleared = heritage.counts(runstate.campaign.ui, runstate.campaign.furthest_era)
    if kept + cleared == 0:
        return "none yet"
    return f"{kept} kept, {cleared} cleared"


def on_toggle_heritage(event=None):
    runstate.heritage_open = not runstate.heritage_open
    runstate.heritage_confirm = None
    update_heritage_panel()


def _make_heritage_demolish_handler(era):
    def handler(event=None):
        if runstate.heritage_confirm != era:
            runstate.heritage_confirm = era
            runstate.heritage_status = "Clearing a heritage site cannot be undone. Press Confirm to go ahead."
            update_heritage_panel()
            return
        ok, text = heritage.demolish(
            runstate.campaign.ui, runstate.state, runstate.campaign.furthest_era, era, _resting(), runstate.campaign.revisiting is not None
        )
        runstate.heritage_confirm = None
        runstate.heritage_status = text
        if ok:
            runstate.chronicle.log_challenge(runstate.state.season, runstate.state.era, text)
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_heritage_cancel_handler():
    def handler(event=None):
        runstate.heritage_confirm = None
        runstate.heritage_status = "Nothing was cleared."
        update_heritage_panel()
    return handler


def update_heritage_panel():
    toggle = document.getElementById("heritage-toggle-button")
    toggle.innerText = "Hide Heritage" if runstate.heritage_open else "🏛 Heritage Sites"
    panel = document.getElementById("heritage-panel")
    panel.hidden = not runstate.heritage_open
    if not runstate.heritage_open:
        return
    for proxy in _heritage_proxies:
        proxy.destroy()
    del _heritage_proxies[:]
    sites = _heritage_sites()
    locked = runstate.campaign.revisiting is not None or _resting()
    note = document.getElementById("heritage-note")
    if runstate.campaign.revisiting is not None:
        note.innerText = "Return to the present to change a heritage site."
    elif _resting():
        note.innerText = f"Heritage sites rest: {_rest_reason()}"
    else:
        note.innerText = (
            "Each era you leave behind stays standing as a heritage site. Kept, it adds "
            f"{heritage.KEEP_BONUS * 100:.0f}% to culture capacity. Cleared, you gain materials and a little land health "
            f"now, and culture capacity is {heritage.DEMOLISH_PENALTY * 100:.0f}% lower for good. Keeping is the default."
        )
    document.getElementById("heritage-summary").innerText = _heritage_summary_text() + "."
    holder = document.getElementById("heritage-list")
    holder.innerHTML = ""
    if not sites:
        empty = document.createElement("p")
        empty.className = "row-blurb"
        empty.innerText = "No heritage sites yet. The first appears when you leave the Tribal era."
        holder.appendChild(empty)
    for site in sites:
        card = document.createElement("div")
        card.className = "heritage-card" + ("" if site["kept"] else " heritage-card--cleared")
        head = document.createElement("h3")
        head.className = "heritage-name"
        head.innerText = f"{site['name']} ({sim.ERA_LABEL[site['era']]} era)"
        card.appendChild(head)
        blurb = document.createElement("p")
        blurb.className = "row-blurb"
        blurb.innerText = site["blurb"]
        card.appendChild(blurb)
        status = document.createElement("p")
        status.className = "status-line"
        status.innerText = heritage.status_text(site)
        card.appendChild(status)
        if site["kept"]:
            era = site["era"]
            confirming = runstate.heritage_confirm == era
            gain = heritage.demolish_gain(era)
            button = document.createElement("button")
            button.id = f"heritage-{era}-demolish-button"
            button.className = "secondary"
            button.type = "button"
            button.disabled = locked
            button.innerText = (
                f"Confirm: clear it for {gain:.0f} materials" if confirming else f"Clear this site (+{gain:.0f} materials)"
            )
            proxy = create_proxy(_make_heritage_demolish_handler(era))
            _heritage_proxies.append(proxy)
            button.addEventListener("click", proxy)
            card.appendChild(button)
            if confirming:
                cancel = document.createElement("button")
                cancel.id = f"heritage-{era}-cancel-button"
                cancel.className = "secondary"
                cancel.type = "button"
                cancel.innerText = "Keep it"
                cancel_proxy = create_proxy(_make_heritage_cancel_handler())
                _heritage_proxies.append(cancel_proxy)
                cancel.addEventListener("click", cancel_proxy)
                card.appendChild(cancel)
        holder.appendChild(card)
    document.getElementById("heritage-status").innerText = runstate.heritage_status
