"""The advisor council (K-8): advice rows, follow handlers and the panel."""

from js import document
from pyodide.ffi import create_proxy

import advisors

import continuum_runstate as runstate
from continuum_base import current_effects, year_and_season
from continuum_panels import _make_assign_handler, _make_build_handler, _make_unassign_handler

render = None  # placeholder: continuum_renderer fills this in when it is imported (it comes later)

# ===========================================================================
# K-8: the advisor council. Four invented advisors give one piece of advice each, checked by
# running the coming season on a copy (advisors.py). Optional, and hidden by the story toggle.
# The buttons carry out the advice through the same handlers the Work and Build panels use.
# ===========================================================================
_advisors_proxies = []


def _advisor_open_item(advisor_id):
    for item in advisors.get(runstate.campaign.ui)["advice"]:
        if item["id"] == advisor_id:
            return item
    return None


def _make_advisor_follow_handler(advisor_id):
    def handler(event=None):
        if runstate.campaign.revisiting is not None:
            return
        item = _advisor_open_item(advisor_id)
        if item is None or item["status"] != "open" or not advisors.available(runstate.state, item["action"]):
            return
        action = item["action"]
        if action["type"] == "assign":
            _make_assign_handler(action["role"])(None)
        elif action["type"] == "move":
            _make_unassign_handler(action["from"])(None)
            _make_assign_handler(action["role"])(None)
        else:
            _make_build_handler(action["building"])(None)
        advisors.mark_followed(runstate.campaign.ui, advisor_id)
        render()
    return handler


def on_toggle_advisors(event=None):
    runstate.advisors_open = not runstate.advisors_open
    runstate._advisors_signature_seen = None
    update_advisors_panel()


def _advisors_rows(record):
    rows = []
    by_id = {item["id"]: item for item in record["advice"]}
    for advisor_id in advisors.ORDER:
        item = by_id.get(advisor_id)
        can = bool(item and item["status"] == "open" and runstate.campaign.revisiting is None
                   and advisors.available(runstate.state, item["action"]))
        rows.append((advisor_id, item, can))
    return rows


def update_advisors_panel():
    toggle = document.getElementById("advisors-toggle-button")
    panel = document.getElementById("advisors-panel")
    toggle.innerText = "Hide Advisors" if runstate.advisors_open else "🧭 Advisors"
    panel.hidden = not runstate.advisors_open
    if not runstate.advisors_open:
        return
    if runstate.campaign.revisiting is None and advisors.stale(runstate.campaign.ui, runstate.state):
        advisors.issue(runstate.campaign.ui, runstate.state, current_effects())
    record = advisors.get(runstate.campaign.ui)
    rows = _advisors_rows(record)
    signature = (
        record["season"], runstate.campaign.revisiting,
        tuple((a, it["text"] if it else "", it["status"] if it else "", can, record["trust"][a],
               tuple(sorted(record["record"][a].items()))) for a, it, can in rows),
        tuple(h["text"] for h in record["history"]),
    )
    if signature == runstate._advisors_signature_seen:
        return
    runstate._advisors_signature_seen = signature
    for stale_proxy in _advisors_proxies:
        stale_proxy.destroy()
    _advisors_proxies.clear()
    holder = document.getElementById("advisors-list")
    holder.innerHTML = ""
    for advisor_id, item, can in rows:
        info = advisors.ADVISORS[advisor_id]
        card = document.createElement("div")
        card.className = "advisor-card"
        for css, tag, text in (
            ("advisor-name", "h3", f"{info['name']}, {info['title']}"),
            ("advisor-trust status-line", "p", advisors.trust_text(record["trust"][advisor_id])),
            ("advisor-voice row-blurb", "p", f"\u201c{info['voice']}\u201d"),
        ):
            node = document.createElement(tag)
            node.className = css
            node.innerText = text
            card.appendChild(node)
        if item is None:
            node = document.createElement("p")
            node.className = "row-blurb"
            node.innerText = "Nothing to recommend this season."
            card.appendChild(node)
        else:
            for css, text in (("advisor-advice status-line", item["text"]), ("advisor-claim row-blurb", advisors.claim_text(item))):
                node = document.createElement("p")
                node.className = css
                node.innerText = text
                card.appendChild(node)
            button = document.createElement("button")
            button.id = f"advisor-{advisor_id}-follow-button"
            button.className = "secondary"
            button.type = "button"
            followed = item["status"] == "followed"
            button.innerText = "✓ Taken this season" if followed else f"Take {info['name'].split()[0]}'s advice"
            button.disabled = not can
            proxy = create_proxy(_make_advisor_follow_handler(advisor_id))
            _advisors_proxies.append(proxy)
            button.addEventListener("click", proxy)
            card.appendChild(button)
        node = document.createElement("p")
        node.className = "advisor-record row-blurb"
        node.innerText = advisors.record_text(record["record"][advisor_id])
        card.appendChild(node)
        holder.appendChild(card)
    history = document.getElementById("advisors-history")
    history.innerHTML = ""
    if not record["history"]:
        node = document.createElement("p")
        node.className = "row-blurb"
        node.innerText = "No seasons judged yet. After each season the council's advice is scored and shown here."
        history.appendChild(node)
    for entry in reversed(record["history"]):
        node = document.createElement("p")
        node.className = "status-line advisor-history-row"
        year, season_name = year_and_season(max(1, entry["season"]))
        node.innerText = f"Year {year}, {season_name}: {entry['text']}"
        history.appendChild(node)
