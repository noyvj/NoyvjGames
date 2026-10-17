"""Standing orders: running them each season and the orders panel."""

import json

from js import document
from pyodide.ffi import create_proxy

import minutes
import orders
import sim
import sustainability

import continuum_runstate as runstate
from continuum_base import year_and_season
from continuum_founders import record_motion, update_minutes_panel


# --- K-1 standing orders ------------------------------------------------------------------------------------
_orders_proxies = []


def _run_standing_orders(effects):
    """After a season: check every order once; each firing is minuted in the Council Minutes."""
    fired = orders.run(runstate.campaign.ui, runstate.state, list(runstate.tree.researched), lambda: sustainability.score(runstate.state, effects))
    for item in fired:
        record_motion("order", item["text"])
    if fired:
        update_minutes_panel()
        acted = [item for item in fired if item["acted"]]
        runstate.orders_status = f"Last season the council carried out {len(acted)} standing order(s)." if acted else (
            "A standing order could not act last season; see the Council Minutes."
        )


def on_toggle_orders(event=None):
    runstate.orders_open = not runstate.orders_open
    runstate._orders_signature = None
    update_orders_panel()


def on_orders_master(event=None):
    if runstate.campaign.revisiting is not None:
        return
    on = orders.set_master(runstate.campaign.ui, not orders.get(runstate.campaign.ui)["on"])
    runstate.orders_status = "Standing orders are on." if on else "Standing orders are paused: none will fire until you switch them on."
    runstate._orders_signature = None
    update_orders_panel()


def on_orders_add(event=None):
    if runstate.campaign.revisiting is not None:
        return
    ok, text = orders.add_rule(runstate.campaign.ui, list(runstate.tree.researched), runstate.state.era)
    runstate.orders_status = text
    runstate._orders_signature = None
    update_orders_panel()


def orders_set(rule_id, field, raw):
    """Apply one menu choice to one order (also what the menus call)."""
    if runstate.campaign.revisiting is not None:
        return False
    ok, text = orders.update_rule(runstate.campaign.ui, rule_id, field, raw, list(runstate.tree.researched), runstate.state.era)
    runstate.orders_status = text
    runstate._orders_signature = None
    update_orders_panel()
    return ok


def orders_remove(rule_id):
    if runstate.campaign.revisiting is not None:
        return False
    removed = orders.remove_rule(runstate.campaign.ui, rule_id)
    runstate.orders_status = "Order removed." if removed else ""
    runstate._orders_signature = None
    update_orders_panel()
    return removed


def _unlock_hint(node_id):
    node = runstate.tree.nodes.get(node_id)
    return f"research {node.name}" if node is not None else "research a later discovery"


def _orders_select(parent, select_id, label, options, current, field, rule_id, locked=False):
    """One menu: options are (value, text, disabled). The chosen value is applied by orders_set()."""
    wrap = document.createElement("label")
    wrap.className = "orders-field"
    caption = document.createElement("span")
    caption.className = "orders-field-label"
    caption.innerText = label
    wrap.appendChild(caption)
    select = document.createElement("select")
    select.id = select_id
    select.setAttribute("aria-label", label)
    for value, text, disabled in options:
        option = document.createElement("option")
        option.value = str(value)
        option.innerText = text
        option.disabled = bool(disabled)
        select.appendChild(option)
    select.value = str(current)
    select.disabled = locked

    def handler(event=None):
        orders_set(rule_id, field, select.value)

    proxy = create_proxy(handler)
    _orders_proxies.append(proxy)
    select.addEventListener("change", proxy)
    wrap.appendChild(select)
    parent.appendChild(wrap)
    return select


def _orders_button(parent, button_id, text, handler, disabled=False):
    button = document.createElement("button")
    button.id = button_id
    button.className = "secondary"
    button.type = "button"
    button.innerText = text
    button.disabled = disabled
    proxy = create_proxy(handler)
    _orders_proxies.append(proxy)
    button.addEventListener("click", proxy)
    parent.appendChild(button)
    return button


def _make_orders_toggle(rule_id, on):
    def handler(event=None):
        orders_set(rule_id, "on", on)
    return handler


def _make_orders_remove(rule_id):
    def handler(event=None):
        orders_remove(rule_id)
    return handler


def _orders_menu_values(rule, researched, era):
    """The option lists for one rule's menus."""
    roles = sim.roles_for_era(era)
    triggers = []
    for key, spec in orders.TRIGGERS.items():
        if not orders._era_ok(era, spec["era"]):
            continue
        open_ = orders.trigger_available(key, researched, era)
        text = spec["label"] if open_ else f"{spec['label']} (locked: {_unlock_hint(spec['unlock'])})"
        triggers.append((key, text, not open_))
    spec = orders.TRIGGERS[rule["trigger"]]
    values = [(v, orders.threshold_text(rule["trigger"], v), False) for v in spec["values"]]
    actions = []
    for key, aspec in orders.ACTIONS.items():
        if not orders._era_ok(era, aspec["era"]):
            continue
        open_ = orders.action_available(key, researched, era)
        text = aspec["label"] if open_ else f"{aspec['label']} (locked: {_unlock_hint(aspec['unlock'])})"
        actions.append((key, text, not open_))
    sources = [(orders.NO_SOURCE, "Idle people", False), (orders.LARGEST, "The biggest group", False)]
    sources += [(r, sim.ROLE_LABEL[r], r == rule["to"]) for r in roles]
    targets = [(r, sim.ROLE_LABEL[r], False) for r in roles]
    return triggers, values, actions, sources, targets


def _orders_signature_now():
    record = orders.get(runstate.campaign.ui)
    return (
        json.dumps(record, sort_keys=True), runstate.orders_open, runstate.state.era, len(runstate.tree.researched), runstate.campaign.revisiting,
        runstate.orders_status, tuple(e["season"] for e in minutes.entries(runstate.campaign.ui) if e["kind"] == "order"),
        tuple(sorted(runstate.tree.researched)),
    )


def update_orders_panel():
    toggle = document.getElementById("orders-toggle-button")
    toggle.innerText = "Hide Standing Orders" if runstate.orders_open else "📌 Standing Orders"
    panel = document.getElementById("orders-panel")
    panel.hidden = not runstate.orders_open
    if not runstate.orders_open:
        return
    signature = _orders_signature_now()
    if signature == runstate._orders_signature:
        return
    runstate._orders_signature = signature
    for proxy in _orders_proxies:
        proxy.destroy()
    del _orders_proxies[:]
    researched = list(runstate.tree.researched)
    record = orders.get(runstate.campaign.ui)
    open_slots = orders.slots(researched)
    revisiting = runstate.campaign.revisiting is not None
    master = document.getElementById("orders-master-button")
    master.innerText = f"Standing orders: {'ON' if record['on'] else 'OFF'}"
    master.setAttribute("aria-pressed", "true" if record["on"] else "false")
    master.disabled = revisiting
    nxt = orders.next_slot_unlock(researched)
    summary = f"{len(record['rules'])} of {open_slots} slot(s) in use ({orders.MAX_RULES} possible)."
    if nxt is not None:
        summary += f" The next slot opens when you {_unlock_hint(nxt)}."
    if open_slots == 0:
        summary = f"No slot yet. The first opens when you {_unlock_hint(orders.SLOT_UNLOCKS[0])}."
    if record["fired"]:
        summary += f" The council has carried out {record['fired']} order(s) so far."
    document.getElementById("orders-summary").innerText = summary
    add = document.getElementById("orders-add-button")
    add.disabled = revisiting or len(record["rules"]) >= open_slots
    note = document.getElementById("orders-note")
    note.innerText = (
        "Return to the present to change orders; they do not run during a Look Back." if revisiting else
        "After every season the council checks each order from the top. A matching order does its job at once and "
        "is written into the Council Minutes. Orders only do what you could do by hand: move people between jobs, "
        "schedule a refactor season, stop quick builds."
    )
    holder = document.getElementById("orders-list")
    holder.innerHTML = ""
    if not record["rules"]:
        empty = document.createElement("p")
        empty.className = "row-blurb"
        empty.innerText = "No orders yet. Press Add an order, then choose from the menus."
        holder.appendChild(empty)
    for index, rule in enumerate(record["rules"]):
        rid = rule["id"]
        dormant = index >= open_slots
        card = document.createElement("div")
        card.className = "orders-card" + ("" if rule["on"] and not dormant else " orders-card--off")
        title = document.createElement("p")
        title.className = "orders-sentence"
        title.innerText = f"Order {index + 1}. {orders.describe(rule)}" + (
            f" Carried out {rule['fires']} time(s)." if rule["fires"] else ""
        )
        card.appendChild(title)
        triggers, values, actions, sources, targets = _orders_menu_values(rule, researched, runstate.state.era)
        controls = document.createElement("div")
        controls.className = "orders-controls"
        lock = revisiting
        _orders_select(controls, f"orders-{rid}-trigger", "If", triggers, rule["trigger"], "trigger", rid, lock)
        _orders_select(
            controls, f"orders-{rid}-op", "is", [("below", "below", False), ("above", "above", False)],
            rule["op"], "op", rid, lock,
        )
        _orders_select(controls, f"orders-{rid}-value", "this value", values, rule["value"], "value", rid, lock)
        _orders_select(controls, f"orders-{rid}-action", "Then", actions, rule["action"], "action", rid, lock)
        if rule["action"] == "shift":
            _orders_select(
                controls, f"orders-{rid}-n", "people", [(n, str(n), False) for n in range(1, orders.MAX_MOVE + 1)],
                rule["n"], "n", rid, lock,
            )
            _orders_select(controls, f"orders-{rid}-from", "from", sources, rule["from"], "from", rid, lock)
            _orders_select(controls, f"orders-{rid}-to", "to", targets, rule["to"], "to", rid, lock)
        _orders_select(
            controls, f"orders-{rid}-repeat", "Run",
            [(k, orders.REPEAT_LABEL[k], False) for k in orders.REPEATS], rule["repeat"], "repeat", rid, lock,
        )
        card.appendChild(controls)
        buttons = document.createElement("div")
        buttons.className = "orders-buttons"
        _orders_button(
            buttons, f"orders-{rid}-toggle", "Pause this order" if rule["on"] else "Resume this order",
            _make_orders_toggle(rid, not rule["on"]), disabled=revisiting,
        )
        _orders_button(buttons, f"orders-{rid}-remove", "Remove", _make_orders_remove(rid), disabled=revisiting)
        card.appendChild(buttons)
        holder.appendChild(card)
    document.getElementById("orders-status").innerText = runstate.orders_status
    recent = document.getElementById("orders-recent")
    recent.innerHTML = ""
    fired = [e for e in minutes.entries(runstate.campaign.ui) if e["kind"] == "order"]
    if not fired:
        none = document.createElement("p")
        none.className = "row-blurb"
        none.innerText = "Nothing yet. When an order fires it appears here and in the Council Minutes."
        recent.appendChild(none)
    for entry in reversed(fired[-6:]):
        year, season_name = year_and_season(entry["season"])
        line = document.createElement("p")
        line.className = "status-line"
        line.innerText = f"Year {year}, {season_name}: {entry['text']}"
        recent.appendChild(line)
