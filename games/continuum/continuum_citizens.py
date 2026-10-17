"""Notable citizens (K-15/K-28) and the neighbour settlements panel (trade, share, bid)."""

from js import document
from pyodide.ffi import create_proxy

import citizens
import minutes
import naming
import neighbours
import sim

import continuum_runstate as runstate
from continuum_base import _citizens_on, _resting, year_and_season
from continuum_dynasty import _neighbour_proxies, _rest_reason, _seed_hint
from continuum_founders import settlement_name

render = None  # placeholder: continuum_renderer fills this in when it is imported (it comes later)

# --- K-15 / K-28 citizens ---------------------------------------------------------------------------------


def on_toggle_citizens(event=None):
    runstate.citizens_open = not runstate.citizens_open
    if runstate.citizens_open and runstate.campaign.revisiting is None and _citizens_on() and runstate.state.season > 1:
        citizens.ensure_roster(runstate.campaign.ui, runstate.campaign.furthest_era, _seed_hint())
    update_citizens_panel()


def on_citizens_off(event=None):
    citizens.set_off(runstate.campaign.ui, _citizens_on())
    render()


def _citizen_effects_text():
    return citizens.bonus_text(citizens.bonus_deltas(runstate.campaign.ui, runstate.state.era, _resting())) or "none right now"


def update_spotlight_card():
    card = document.getElementById("citizen-spotlight")
    spot = citizens.latest_spot(runstate.campaign.ui) if _citizens_on() else None
    card.hidden = spot is None
    if spot is not None:
        year, season_name = year_and_season(max(1, spot["season"]))
        card.innerText = f"Citizen of the season, Year {year} {season_name}: {spot['name']}. {spot['line']}"


def update_citizens_panel():
    toggle = document.getElementById("citizens-toggle-button")
    toggle.innerText = "Hide Citizens" if runstate.citizens_open else "🧑 Citizens"
    panel = document.getElementById("citizens-panel")
    panel.hidden = not runstate.citizens_open
    if not runstate.citizens_open:
        return
    on = _citizens_on()
    off_button = document.getElementById("citizens-off-button")
    off_button.innerText = f"Notable citizens: {'ON' if on else 'OFF'}"
    off_button.setAttribute("aria-pressed", "true" if on else "false")
    holder = document.getElementById("citizens-list")
    holder.innerHTML = ""
    record = citizens.get(runstate.campaign.ui)
    if not on:
        text = "Notable citizens are switched off: no citizens appear and none give a bonus."
    elif not record["roster"]:
        text = "Citizens appear as the settlement lives its first seasons. They are invented people."
    else:
        text = (
            f"Invented people who follow the settlement from era to era. Their standing bonus right now: "
            f"{_citizen_effects_text()}." + (" (Resting during a challenge run or consulting case.)" if _resting() else "")
        )
    document.getElementById("citizens-bonus").innerText = text
    for citizen in reversed(record["roster"]) if on else []:
        stage = citizens.stage_of(citizen, runstate.state.era)
        card = document.createElement("div")
        card.className = "citizen-card"
        title = document.createElement("h3")
        title.className = "citizen-name"
        title.innerText = f"{citizen['name']}, {stage['title']}"
        card.appendChild(title)
        for line in citizens.thread(citizen, runstate.state.era):
            node = document.createElement("p")
            node.className = "row-blurb citizen-thread"
            node.innerText = line
            card.appendChild(node)
        holder.appendChild(card)
    spots = document.getElementById("citizens-spots")
    spots.innerHTML = ""
    for spot in reversed(record["spots"]) if on else []:
        year, season_name = year_and_season(max(1, spot["season"]))
        node = document.createElement("p")
        node.className = "status-line"
        node.innerText = f"Year {year} {season_name}: {spot['name']}. {spot['line']}"
        spots.appendChild(node)


def _citizens_after_season(report):
    """New children for new eras, and the citizen of the season."""
    if runstate.campaign.revisiting is not None or not _citizens_on():
        return
    added = citizens.ensure_roster(runstate.campaign.ui, runstate.campaign.furthest_era, _seed_hint())
    for citizen in added:
        runstate.chronicle.log_challenge(
            runstate.state.season, runstate.state.era,
            f"{citizen['name']} is born among the {citizens.ERA_TRADES[citizen['born']]['household']}.",
        )
    citizens.make_spotlight(runstate.campaign.ui, runstate.state.era, report.get("season", runstate.state.season - 1), report, minutes.entries(runstate.campaign.ui))


# --- K-7 neighbours ---------------------------------------------------------------------------------------
def on_toggle_neighbours(event=None):
    runstate.neighbours_open = not runstate.neighbours_open
    if runstate.neighbours_open:
        neighbours.ensure(runstate.campaign.ui, _seed_hint()) if runstate.campaign.revisiting is None else None
    update_neighbours_panel()


def _neighbours_allowed():
    return runstate.campaign.revisiting is None and not _resting()


def _player_era_index():
    return sim.era_index(runstate.state.era)


def _make_trade_handler(sid):
    def handler(event=None):
        if not _neighbours_allowed():
            return
        ok, text = neighbours.apply_trade(runstate.campaign.ui, sid, runstate.state.season, runstate.state.resources, _player_era_index())
        runstate.neighbours_status = text
        render()
    return handler


def _make_share_handler(sid):
    def handler(event=None):
        if not _neighbours_allowed():
            return
        costs = {nid: node.cost for nid, node in runstate.tree.nodes.items()}
        names = {nid: node.name for nid, node in runstate.tree.nodes.items()}
        ok, text, gained = neighbours.apply_share(
            runstate.campaign.ui, sid, runstate.state.season, list(runstate.tree.researched), costs, names, _player_era_index()
        )
        if ok:
            runstate.state.resources["knowledge"] += gained
        runstate.neighbours_status = text
        render()
    return handler


def _make_bid_handler(amount):
    def handler(event=None):
        if not _neighbours_allowed():
            return
        ok, text = neighbours.place_bid(runstate.campaign.ui, amount, runstate.state.resources, runstate.state.season, _player_era_index())
        runstate.neighbours_status = text
        render()
    return handler


def _neighbour_button(parent, button_id, text, handler, disabled=False, title=""):
    button = document.createElement("button")
    button.id = button_id
    button.className = "secondary"
    button.type = "button"
    button.innerText = text
    button.disabled = disabled
    if title:
        button.title = title
    proxy = create_proxy(handler)
    _neighbour_proxies.append(proxy)
    button.addEventListener("click", proxy)
    parent.appendChild(button)
    return button


def update_neighbours_panel():
    toggle = document.getElementById("neighbours-toggle-button")
    toggle.innerText = "Hide Neighbours" if runstate.neighbours_open else "🗺 Neighbours"
    panel = document.getElementById("neighbours-panel")
    panel.hidden = not runstate.neighbours_open
    if not runstate.neighbours_open:
        return
    for proxy in _neighbour_proxies:
        proxy.destroy()
    del _neighbour_proxies[:]
    record = neighbours.get(runstate.campaign.ui)
    era_index = _player_era_index()
    season = runstate.state.season
    slot_views = [neighbours.view(record, sid, season, era_index) for sid in neighbours.SLOT_IDS]
    allowed = _neighbours_allowed()
    label = naming.title(settlement_name()) if settlement_name() else "Your settlement"
    document.getElementById("neighbours-map").innerHTML = neighbours.map_svg(slot_views, record, season, label[:20])
    document.getElementById("neighbours-caption").innerText = neighbours.map_caption(slot_views)
    if not allowed:
        note = (
            "Return to the present to deal with your neighbours." if runstate.campaign.revisiting is not None
            else f"Neighbours rest: {_rest_reason()}"
        )
    else:
        note = "Three computer-controlled neighbours. They never attack; you trade, share discoveries and bid for the lease on the Salt Flats."
    document.getElementById("neighbours-note").innerText = note
    holder = document.getElementById("neighbours-list")
    holder.innerHTML = ""
    resources = runstate.state.resources
    costs = {nid: node.cost for nid, node in runstate.tree.nodes.items()}
    for v in slot_views:
        card = document.createElement("div")
        card.className = "neighbour-card"
        head = document.createElement("h3")
        head.className = "neighbour-name"
        head.innerText = f"{v['name']}: {v['era_label']} era, {v['population']} people, {v['attitude_word']}"
        card.appendChild(head)
        need = document.createElement("p")
        need.className = "row-blurb"
        need.innerText = f"Needs {v['need']}; offers {v['offer']}. A trade: you give {v['give']} {v['need']}, you receive {v['get']} {v['offer']}."
        card.appendChild(need)
        ok_trade, why_trade = neighbours.can_trade(record, v["id"], season, resources, era_index)
        _neighbour_button(
            card, f"neighbour-{v['id']}-trade-button", f"Trade with {v['name']}",
            _make_trade_handler(v["id"]), disabled=not (allowed and ok_trade), title=why_trade,
        )
        candidate = neighbours.next_share_candidate(record, v["id"], list(runstate.tree.researched), costs)
        why_share = ""
        if v["share_ready_in"]:
            why_share = f"Ready in {v['share_ready_in']} seasons."
        elif candidate is None:
            why_share = "No discovery they have not heard."
        share_label = "Share a discovery"
        if candidate is not None:
            share_label = f"Share {runstate.tree.nodes[candidate].name}"
        _neighbour_button(
            card, f"neighbour-{v['id']}-share-button", share_label,
            _make_share_handler(v["id"]), disabled=not (allowed and not why_share), title=why_share,
        )
        holder.appendChild(card)
    document.getElementById("neighbours-lease").innerText = neighbours.lease_text(record, season)
    bids = document.getElementById("neighbours-bids")
    bids.innerHTML = ""
    low, high = neighbours.rival_range(record, season, era_index)
    hint = document.createElement("p")
    hint.className = "row-blurb"
    hint.innerText = (
        f"Rival bids usually fall between {low} and {high} materials; friendlier neighbours ask a little less. "
        f"The lease pays {neighbours.lease_income(era_index)} materials a season for {neighbours.LEASE_LENGTH} seasons. "
        "A bid is paid only if you win; otherwise it is returned."
    )
    bids.appendChild(hint)
    for name, amount in neighbours.bid_options(era_index):
        _neighbour_button(
            bids, f"neighbours-bid-{name}-button", f"Bid {amount} ({name})", _make_bid_handler(amount),
            disabled=not allowed or bool(record["lease"]["pending"]) or resources.get("materials", 0.0) < amount,
        )
    document.getElementById("neighbours-status").innerText = runstate.neighbours_status
    events = document.getElementById("neighbours-events")
    events.innerHTML = ""
    for entry in reversed(record["events"]):
        node = document.createElement("p")
        node.className = "status-line"
        year, season_name = year_and_season(max(1, entry["season"]))
        node.innerText = f"Year {year} {season_name}: {entry['text']}"
        events.appendChild(node)
