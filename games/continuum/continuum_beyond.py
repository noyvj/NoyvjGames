"""The Beyond (K-13, the endless mode after the Relay Age): the ladder kept in localStorage, banking a result after each season, and the panel."""

import json

from js import document

import beyond

import continuum_runstate as runstate
from continuum_archive import _today
from continuum_base import _js_window, _resting, current_effects
from continuum_dynasty import _rest_reason
from continuum_founders import settlement_name

render = None  # placeholder: continuum_renderer fills this in when it is imported (it comes later)

# --- K-13 the Beyond ------------------------------------------------------------------------------------------


def beyond_ladder_load():
    window = _js_window()
    if window is None:
        return []
    try:
        raw = window.localStorage.getItem(beyond.LADDER_KEY)
    except Exception:  # noqa: BLE001
        return []
    return beyond.clean_ladder(raw) if isinstance(raw, str) else []


def beyond_ladder_store(rows):
    window = _js_window()
    if window is None or runstate.sandbox_active:  # Z-18
        return False
    try:
        window.localStorage.setItem(beyond.LADDER_KEY, json.dumps(beyond.clean_ladder(rows)))
        return True
    except Exception:  # noqa: BLE001
        return False


def _bank_beyond_result(survived):
    """A run ended: put its result on the ladder (a run that survived no era is not listed)."""
    if survived and survived >= 1:
        beyond_ladder_store(beyond.add_to_ladder(beyond_ladder_load(), _today(), survived, settlement_name()))


def _beyond_after_season(score):
    event = beyond.after_season(runstate.campaign.ui, score)
    runstate._beyond_signature = None
    if event is None:
        return
    if event["kind"] == "survived":
        runstate.beyond_status = f"Beyond era {event['era']} survived. Next: {event['next_theme']}."
        runstate.chronicle.log_challenge(runstate.state.season, runstate.state.era, f"Beyond era {event['era']} survived. Next comes {event['next_theme']}.")
    else:
        runstate.beyond_status = (
            f"The Beyond run ended after {event['survived']} era(s) survived. The settlement carries on as it is; "
            "you can begin a new run whenever you like."
        )
        runstate.chronicle.log_challenge(runstate.state.season, runstate.state.era, runstate.beyond_status)
        _bank_beyond_result(event["survived"])


def _beyond_summary_text():
    record = beyond.get(runstate.campaign.ui)
    if not beyond.available(runstate.campaign.furthest_era):
        return "opens at the Relay Age"
    if record["on"]:
        return f"era {record['era']} under way, best {record['best']}"
    return f"best {record['best']} era(s) survived"


def on_toggle_beyond(event=None):
    runstate.beyond_open = not runstate.beyond_open
    runstate._beyond_signature = None
    update_beyond_panel()


def on_beyond_start(event=None):
    ok, text = beyond.start(runstate.campaign.ui, runstate.campaign.furthest_era, _resting(), runstate.campaign.revisiting is not None)
    runstate.beyond_status = text
    runstate._beyond_signature = None
    if ok:
        runstate.chronicle.log_challenge(runstate.state.season, runstate.state.era, text)
        render()
    else:
        update_beyond_panel()


def on_beyond_stop(event=None):
    survived = beyond.stop(runstate.campaign.ui)
    runstate._beyond_signature = None
    if survived is None:
        return
    _bank_beyond_result(survived)
    runstate.beyond_status = f"You ended the run with {survived} Beyond era(s) survived. The pressure is lifted."
    render()


def update_beyond_panel():
    toggle = document.getElementById("beyond-toggle-button")
    toggle.innerText = "Hide the Beyond" if runstate.beyond_open else "🌌 The Beyond"
    panel = document.getElementById("beyond-panel")
    panel.hidden = not runstate.beyond_open
    if not runstate.beyond_open:
        return
    record = beyond.get(runstate.campaign.ui)
    ladder = beyond_ladder_load()
    signature = (json.dumps(record, sort_keys=True), runstate.campaign.revisiting, runstate.campaign.furthest_era, runstate.beyond_status,
                 json.dumps(ladder), _resting(), round(runstate.state.land_health, 2), runstate.state.population)
    if signature == runstate._beyond_signature:
        return
    runstate._beyond_signature = signature
    available = beyond.available(runstate.campaign.furthest_era)
    note = document.getElementById("beyond-note")
    if not available:
        note.innerText = "The Beyond opens once the settlement reaches the Relay Age."
    elif _resting():
        note.innerText = f"The Beyond is not offered: {_rest_reason()}"
    elif runstate.campaign.revisiting is not None:
        note.innerText = "Return to the present to take part in the Beyond."
    else:
        note.innerText = (
            "An optional endless mode. Each Beyond era has a named pressure that grows with entropy; keep the "
            "sustainability score up for 10 of its 12 seasons to survive it. A run that falls short simply ends: "
            "nothing is lost and you can begin again."
        )
    start = document.getElementById("beyond-start-button")
    start.disabled = (not available) or record["on"] or _resting() or runstate.campaign.revisiting is not None
    stop = document.getElementById("beyond-stop-button")
    stop.hidden = not record["on"]
    holder = document.getElementById("beyond-lines")
    holder.innerHTML = ""
    for line in beyond.status_lines(record, runstate.state, current_effects()):
        node = document.createElement("p")
        node.className = "row-blurb"
        node.innerText = line
        holder.appendChild(node)
    document.getElementById("beyond-status").innerText = runstate.beyond_status
    rows = document.getElementById("beyond-ladder")
    rows.innerHTML = ""
    if not ladder:
        none = document.createElement("p")
        none.className = "row-blurb"
        none.innerText = "No finished runs yet. Your furthest runs on this device are listed here."
        rows.appendChild(none)
    for index, row in enumerate(ladder, start=1):
        line = document.createElement("p")
        line.className = "status-line"
        line.innerText = beyond.ladder_text(row, index)
        rows.appendChild(line)
