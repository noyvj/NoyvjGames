"""The peer-settlement comparison graph (R-33): publish plan, show, hide and metric."""

import json

from js import document

import peers
import sim
import statlog

import continuum_runstate as runstate
from continuum_base import _js_window, _resting


# --- R-33: the "another settlement" ghost (peers.py; the fetch() calls and the Settings switch are peers.js) ---


def _peer_history():
    """The stat history of the real, running settlement (empty during a Look Back)."""
    return statlog.rows(runstate.campaign.ui) if runstate.campaign.revisiting is None else []


def _peer_may_publish():
    """Only the real settlement is ever shared: not a practice sandbox, a Look Back, a challenge run or a
    consulting case (those start from fixed set-ups and would not compare fairly)."""
    return not runstate.sandbox_active and runstate.campaign.revisiting is None and not _resting()


def peer_publish_plan(last_season=-1, last_era=-1):
    """JSON for POST /ghosts, or "" when nothing is due (called by peers.js). Only the numbers in peers.py."""
    if not _peer_may_publish():
        return ""
    history = statlog.rows(runstate.campaign.ui)
    last = None if last_season is None or last_season < 0 else last_season
    if not peers.due_to_publish(history, last, last_era):
        return ""
    return peers.publish_json(history, runstate.state.scenario, runstate.state.hard_mode)


def peer_query_json(exclude=""):
    """JSON for the GET /ghosts/continuum/peer query string: scenario, era, hard (and the ghost on screen)."""
    return json.dumps(peers.peer_query(sim.era_index(runstate.state.era), runstate.state.scenario, runstate.state.hard_mode, exclude or None))


def peer_show(raw):
    """Takes the server's ghost (a JSON string), checks it and draws it. True when it was valid."""
    ghost = peers.clean_ghost(raw)
    if ghost is None:
        return False
    runstate._peer_ghost = ghost
    render_peers()
    return True


def peer_ghost_id():
    return runstate._peer_ghost["id"] if runstate._peer_ghost else ""


def peer_message(kind):
    return peers.message(kind)


def on_peer_hide(event=None):
    runstate._peer_ghost = None
    render_peers()


def on_peer_metric(event=None):
    runstate._peer_metric = peers.next_metric(runstate._peer_metric)
    render_peers()


def render_peers():
    """The "Another settlement" comparison: a dashed line beside yours, the one-line comparison, and the
    same information as text. With no ghost on screen only the Show button is visible."""
    ghost = runstate._peer_ghost["series"] if runstate._peer_ghost else None
    mine = peers.my_series(_peer_history())
    has = ghost is not None
    for element_id in ("peer-legend", "peer-hide-button", "peer-report-button", "peer-metric-button"):
        document.getElementById(element_id).hidden = not has
    if not has:
        document.getElementById("peer-graph").innerHTML = ""
        document.getElementById("peer-summary").innerText = ""
        document.getElementById("peer-text").innerText = ""
        return
    document.getElementById("peer-graph").innerHTML = peers.compare_svg(mine, ghost, runstate._peer_metric)
    document.getElementById("peer-summary").innerText = peers.comparison_line(mine, ghost)
    document.getElementById("peer-text").innerText = peers.text_equivalent(mine, ghost, runstate._peer_metric)
    document.getElementById("peer-metric-button").innerText = peers.metric_button_text(runstate._peer_metric)


def _notify_peers():
    """Tells peers.js a season finished, so it can re-share when sharing is switched on and a re-send is due."""
    window = _js_window()
    hook = getattr(getattr(window, "ContinuumPeers", None), "seasonDone", None) if window is not None else None
    if hook is not None:
        try:
            hook()
        except Exception:  # noqa: BLE001 -- sharing must never break a season
            pass
