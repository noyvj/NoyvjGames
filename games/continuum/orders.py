"""Continuum -- K-1: Standing Orders.

A **standing order** is an if/then rule the council keeps for you: "If the
food store falls below 2 seasons of eating, move 1 person from Idle people to
Foragers." Rules are chosen from menus (a trigger, below or above, a
threshold, an action); nobody writes code. After each season is run the rules
are checked in order; a rule whose condition holds carries out its action
there and then, and every firing is minuted in the Council Minutes (the
policy log, kind ``order``) so nothing the council does on its own is hidden.

What research unlocks
---------------------
* **Slots.** Five slots, each opened by a community-branch discovery
  (`SLOT_UNLOCKS`): the first by Shared Hearth, which is among the very first
  things you can learn.
* **Trigger types.** Food stored and idle people are free; the others come
  with the discovery that makes the thing worth watching (`TRIGGERS[..]["unlock"]`).
* **Actions.** Moving people between jobs and a "log a notice" action are free;
  the two technical-debt actions come with Smart Utilities.

What an order can and cannot do
-------------------------------
It only does what you could do by hand at that moment: move people between the
roles the era has unlocked, schedule a refactor season, stop quick builds. It
never spends resources, never builds, never researches. It can never make a
season run differently than the same clicks would. If it cannot act (nobody to
move) it says so once in the minutes and then stays quiet until it can.

Where it plugs in. The record lives in `campaign.ui["standing_orders"]` (plain
JSON, validated on every read by `clean()`, written only when non-default, so an
older save simply has none). Pure functions only: no DOM, no storage. `game.py`
owns the panel and calls `run(...)` once after each season.
"""

import math

import sim
import techdebt

KEY = "standing_orders"
MAX_RULES = 5
MAX_MOVE = 3
NO_SOURCE = "idle"
LARGEST = "largest"

# The slots, in order; each is opened by researching the named discovery.
SLOT_UNLOCKS = ["shared_hearth", "kinship_custom", "communal_granaries", "civic_assembly", "municipal_charter"]

# Trigger types. `unlock` is a research node id or None (free); `era` the first era in
# which the thing exists at all; `values` the thresholds the menu offers.
TRIGGERS = {
    "food_seasons": {
        "label": "Food stored", "unit": " seasons of eating", "values": [1, 2, 3, 4, 6],
        "op": "below", "default": 2, "unlock": None, "era": "tribal",
    },
    "idle": {
        "label": "Idle people", "unit": "", "values": [1, 2, 3, 5, 8],
        "op": "above", "default": 2, "unlock": None, "era": "tribal",
    },
    "land_health": {
        "label": "Land health", "unit": "%", "values": [40, 50, 60, 70, 80],
        "op": "below", "default": 50, "unlock": "seasonal_rounds", "era": "tribal",
    },
    "materials": {
        "label": "Materials stored", "unit": "", "values": [5, 10, 20, 40, 80],
        "op": "below", "default": 10, "unlock": "stone_knapping", "era": "tribal",
    },
    "score": {
        "label": "Sustainability score", "unit": "", "values": [40, 50, 60, 70],
        "op": "below", "default": 50, "unlock": "elders_council", "era": "tribal",
    },
    "pollution": {
        "label": "Pollution", "unit": "%", "values": [10, 20, 30, 50],
        "op": "above", "default": 20, "unlock": "smoke_abatement", "era": "industrial",
    },
    "sprawl": {
        "label": "Sprawl", "unit": "%", "values": [10, 20, 30, 50],
        "op": "above", "default": 20, "unlock": "data_driven_zoning", "era": "digital",
    },
    "tech_debt": {
        "label": "Technical debt", "unit": "%", "values": [20, 30, 50, 70],
        "op": "above", "default": 50, "unlock": "smart_utilities", "era": "digital",
    },
}

# Action types.
ACTIONS = {
    "shift": {"label": "Move people between jobs", "unlock": None, "era": "tribal"},
    "notice": {"label": "Only log a notice", "unlock": None, "era": "tribal"},
    "refactor": {"label": "Schedule a refactor season", "unlock": "smart_utilities", "era": "digital"},
    "quick_off": {"label": "Stop quick builds", "unlock": "smart_utilities", "era": "digital"},
}

OPS = ("below", "above")
REPEATS = ("every", "once")
REPEAT_LABEL = {"every": "every season it holds", "once": "once only, then switch off"}


# --- validation ---------------------------------------------------------
def _int(value, low, high, default):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    if isinstance(value, float) and not math.isfinite(value):
        return default
    return max(low, min(high, int(value)))


def _has(value, allowed):
    """`value in allowed` that cannot raise on an unhashable junk value from a save."""
    return isinstance(value, str) and value in allowed


def _num_ok(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)


def fresh_rule(rule_id, trigger="food_seasons"):
    spec = TRIGGERS[trigger]
    return {
        "id": rule_id, "trigger": trigger, "op": spec["op"], "value": spec["default"],
        "action": "shift", "n": 1, "to": "foragers", "from": NO_SOURCE, "repeat": "every",
        "on": True, "fires": 0, "blocked": False,
    }


def clean_rule(raw):
    """A validated rule, or None for junk."""
    if not isinstance(raw, dict):
        return None
    rule_id = raw.get("id")
    if isinstance(rule_id, bool) or not isinstance(rule_id, int) or rule_id < 1:
        return None
    trigger = raw.get("trigger")
    if not _has(trigger, TRIGGERS):
        return None
    spec = TRIGGERS[trigger]
    out = fresh_rule(min(rule_id, 10**6), trigger)
    op = raw.get("op")
    out["op"] = op if _has(op, OPS) else spec["op"]
    value = raw.get("value")
    out["value"] = int(value) if _num_ok(value) and int(value) in spec["values"] else spec["default"]
    action = raw.get("action")
    out["action"] = action if _has(action, ACTIONS) else "shift"
    out["n"] = _int(raw.get("n"), 1, MAX_MOVE, 1)
    to = raw.get("to")
    out["to"] = to if _has(to, sim.ROLES) else "foragers"
    source = raw.get("from")
    out["from"] = source if _has(source, sim.ROLES) or _has(source, (NO_SOURCE, LARGEST)) else NO_SOURCE
    if out["from"] == out["to"]:
        out["from"] = NO_SOURCE
    out["repeat"] = raw.get("repeat") if _has(raw.get("repeat"), REPEATS) else "every"
    out["on"] = raw.get("on") is not False
    out["fires"] = _int(raw.get("fires"), 0, 10**6, 0)
    out["blocked"] = raw.get("blocked") is True
    return out


def fresh():
    return {"on": True, "rules": [], "fired": 0}


def clean(raw):
    """A validated record from whatever a save handed back (may be junk)."""
    out = fresh()
    if not isinstance(raw, dict):
        return out
    out["on"] = raw.get("on") is not False
    out["fired"] = _int(raw.get("fired"), 0, 10**6, 0)
    seen = set()
    rules = raw.get("rules")
    if isinstance(rules, list):
        for item in rules:
            rule = clean_rule(item)
            if rule is None or rule["id"] in seen:
                continue
            seen.add(rule["id"])
            out["rules"].append(rule)
            if len(out["rules"]) >= MAX_RULES:
                break
    return out


def get(ui):
    return clean(ui.get(KEY)) if isinstance(ui, dict) else fresh()


def put(ui, record):
    """Store `record`; the default record (no rules, switched on, nothing fired) is not stored at all."""
    record = clean(record)
    if not record["rules"] and record["on"] and record["fired"] == 0:
        ui.pop(KEY, None)
        return record
    ui[KEY] = record
    return record


# --- what is unlocked ---------------------------------------------------
def slots(researched):
    have = set(researched or ())
    return sum(1 for node in SLOT_UNLOCKS if node in have)


def next_slot_unlock(researched):
    have = set(researched or ())
    for node in SLOT_UNLOCKS:
        if node not in have:
            return node
    return None


def _era_ok(era, needed):
    return era in sim.ERA_ORDER and sim.era_index(era) >= sim.era_index(needed)


def trigger_available(key, researched, era):
    spec = TRIGGERS.get(key)
    if spec is None or not _era_ok(era, spec["era"]):
        return False
    return spec["unlock"] is None or spec["unlock"] in set(researched or ())


def action_available(key, researched, era):
    spec = ACTIONS.get(key)
    if spec is None or not _era_ok(era, spec["era"]):
        return False
    return spec["unlock"] is None or spec["unlock"] in set(researched or ())


def available_triggers(researched, era):
    return [k for k in TRIGGERS if trigger_available(k, researched, era)]


def available_actions(researched, era):
    return [k for k in ACTIONS if action_available(k, researched, era)]


# --- editing ------------------------------------------------------------
def add_rule(ui, researched, era):
    """Add a new rule in the first free slot. Returns (ok, message)."""
    record = get(ui)
    if len(record["rules"]) >= slots(researched):
        node = next_slot_unlock(researched)
        if node is None or len(record["rules"]) >= MAX_RULES:
            return False, "Every slot is in use."
        return False, "No free slot. A new slot opens with the discovery " + node.replace("_", " ").title() + "."
    used = {r["id"] for r in record["rules"]}
    rule_id = next(i for i in range(1, MAX_RULES + 10) if i not in used)
    rule = fresh_rule(rule_id)
    rule["to"] = "foragers"
    record["rules"].append(rule)
    put(ui, record)
    return True, "Order added. Choose its trigger and action."


def remove_rule(ui, rule_id):
    record = get(ui)
    before = len(record["rules"])
    record["rules"] = [r for r in record["rules"] if r["id"] != rule_id]
    put(ui, record)
    return len(record["rules"]) != before


def set_master(ui, on):
    record = get(ui)
    record["on"] = bool(on)
    put(ui, record)
    return record["on"]


def update_rule(ui, rule_id, field, raw, researched, era):
    """Change one field of one rule from a menu choice. Returns (ok, message).

    The menu hands back strings; each field is parsed and checked here, a locked
    choice is refused, and a change of trigger resets the dependent fields.
    """
    record = get(ui)
    rule = next((r for r in record["rules"] if r["id"] == rule_id), None)
    if rule is None:
        return False, "That order no longer exists."
    roles = sim.roles_for_era(era)
    if field == "trigger":
        if not _has(raw, TRIGGERS):
            return False, "Unknown trigger."
        if not trigger_available(raw, researched, era):
            return False, "That trigger is not unlocked yet."
        spec = TRIGGERS[raw]
        rule["trigger"], rule["op"], rule["value"] = raw, spec["op"], spec["default"]
    elif field == "op":
        if not _has(raw, OPS):
            return False, "Choose below or above."
        rule["op"] = raw
    elif field == "value":
        try:
            number = int(raw)
        except (TypeError, ValueError):
            return False, "Choose one of the listed values."
        if number not in TRIGGERS[rule["trigger"]]["values"]:
            return False, "Choose one of the listed values."
        rule["value"] = number
    elif field == "action":
        if not _has(raw, ACTIONS) or not action_available(raw, researched, era):
            return False, "That action is not unlocked yet."
        rule["action"] = raw
    elif field == "n":
        try:
            number = int(raw)
        except (TypeError, ValueError):
            return False, "Choose 1, 2 or 3."
        if not 1 <= number <= MAX_MOVE:
            return False, "Choose 1, 2 or 3."
        rule["n"] = number
    elif field == "to":
        if not _has(raw, roles):
            return False, "That job is not available yet."
        rule["to"] = raw
        if rule["from"] == raw:
            rule["from"] = NO_SOURCE
    elif field == "from":
        if not _has(raw, roles) and not _has(raw, (NO_SOURCE, LARGEST)):
            return False, "That job is not available yet."
        if raw == rule["to"]:
            return False, "An order cannot move people from a job to the same job."
        rule["from"] = raw
    elif field == "repeat":
        if not _has(raw, REPEATS):
            return False, "Choose every season or once."
        rule["repeat"] = raw
        if raw == "every" and not rule["on"] and rule["fires"] > 0:
            rule["on"] = True
    elif field == "on":
        rule["on"] = bool(raw)
    else:
        return False, "Unknown field."
    rule["blocked"] = False
    put(ui, record)
    return True, ""


# --- reading the settlement ---------------------------------------------
def food_seasons(state):
    need = max(1.0, state.population * sim.FOOD_PER_PERSON)
    return state.resources["food"] / need


def metric(key, state, score=None, ui=None):
    """The current value of one trigger metric (None when it does not exist yet)."""
    if key == "food_seasons":
        return food_seasons(state)
    if key == "idle":
        return float(state.idle_workers())
    if key == "land_health":
        return state.land_health * 100.0
    if key == "materials":
        return float(state.resources["materials"])
    if key == "score":
        return score() if callable(score) else score
    if key == "pollution":
        return state.pollution * 100.0
    if key == "sprawl":
        return state.sprawl * 100.0
    if key == "tech_debt":
        return techdebt.get(ui or {})["debt"] * 100.0
    return None


def holds(rule, value):
    if value is None:
        return False
    if rule["op"] == "below":
        return value < rule["value"]
    return value > rule["value"]


def value_text(key, value):
    if value is None:
        return "unknown"
    if key == "food_seasons":
        return f"{value:.1f} seasons of eating"
    if key in ("land_health", "pollution", "sprawl", "tech_debt"):
        return f"{value:.0f}%"
    return f"{value:.0f}"


def role_name(role):
    if role == NO_SOURCE:
        return "Idle people"
    if role == LARGEST:
        return "the biggest group"
    return sim.ROLE_LABEL.get(role, role)


def threshold_text(key, value):
    """A threshold as the menus and sentences show it ("1 season of eating", "50%")."""
    unit = TRIGGERS[key]["unit"]
    if value == 1 and unit.startswith(" seasons"):
        unit = unit.replace("seasons", "season", 1)
    return f"{value}{unit}"


def condition_text(rule):
    spec = TRIGGERS[rule["trigger"]]
    return f"{spec['label'].lower()} is {rule['op']} {threshold_text(rule['trigger'], rule['value'])}"


def action_text(rule):
    action = rule["action"]
    if action == "shift":
        who = "person" if rule["n"] == 1 else "people"
        return f"move up to {rule['n']} {who} from {role_name(rule['from'])} to {role_name(rule['to'])}"
    if action == "refactor":
        return "schedule a refactor season"
    if action == "quick_off":
        return "stop quick builds"
    return "log a notice"


def describe(rule):
    """One plain sentence for the whole rule."""
    state = "" if rule["on"] else " (switched off)"
    return f"If {condition_text(rule)}, then {action_text(rule)}, {REPEAT_LABEL[rule['repeat']]}.{state}"


# --- carrying an order out ----------------------------------------------
def _largest_role(state, roles, excluding):
    best, size = None, 0
    for role in roles:
        if role == excluding:
            continue
        count = state.allocation.get(role, 0)
        if count > size:
            best, size = role, count
    return best


def _do_shift(rule, state):
    """Move up to n people. Returns (moved, text)."""
    roles = sim.roles_for_era(state.era)
    to = rule["to"]
    if to not in roles:
        return 0, f"{role_name(to)} is not a job yet"
    source = rule["from"]
    if source == LARGEST:
        source = _largest_role(state, roles, to)
        if source is None:
            return 0, "nobody was working anywhere else"
    if source != NO_SOURCE and source not in roles:
        return 0, f"{role_name(source)} is not a job yet"
    moved = 0
    for _ in range(rule["n"]):
        if source == NO_SOURCE:
            if state.idle_workers() <= 0:
                break
            state.allocation[to] += 1
        else:
            if state.allocation.get(source, 0) <= 0:
                break
            state.allocation[source] -= 1
            state.allocation[to] += 1
        moved += 1
    if moved == 0:
        return 0, f"nobody was available in {role_name(source)}"
    who = "person" if moved == 1 else "people"
    return moved, f"{moved} {who} moved from {role_name(rule['from'])} to {role_name(to)}"


def _do_action(rule, state, ui):
    action = rule["action"]
    if action == "shift":
        moved, text = _do_shift(rule, state)
        return moved > 0, text
    if action == "refactor":
        record = techdebt.get(ui)
        if not techdebt.active(state.era):
            return False, "technical debt does not exist yet"
        if record["refactor"]:
            return False, "a refactor season is already scheduled"
        if record["debt"] <= 0:
            return False, "there is no debt to pay down"
        techdebt.schedule_refactor(ui, True)
        return True, "a refactor season was scheduled"
    if action == "quick_off":
        record = techdebt.get(ui)
        if not record["quick"]:
            return False, "quick builds were already off"
        techdebt.set_quick(ui, False)
        return True, "quick builds were switched off"
    return True, "noted"


def run(ui, state, researched, score=None):
    """Check every rule once, in order, after a season. Returns the list of things to minute.

    Each item is a dict `{"rule": id, "text": ..., "acted": bool}`. Rules beyond the number of
    open slots, locked triggers/actions and switched-off rules do nothing. State is changed in
    place (people moved, a refactor scheduled); the record is written back.
    """
    record = get(ui)
    if not record["on"] or not record["rules"]:
        return []
    open_slots = slots(researched)
    out = []
    for index, rule in enumerate(record["rules"]):
        if index >= open_slots or not rule["on"]:
            continue
        if not trigger_available(rule["trigger"], researched, state.era):
            continue
        if not action_available(rule["action"], researched, state.era):
            continue
        value = metric(rule["trigger"], state, score, ui)
        if not holds(rule, value):
            rule["blocked"] = False
            continue
        acted, detail = _do_action(rule, state, ui)
        if acted:
            rule["blocked"] = False
            rule["fires"] += 1
            record["fired"] += 1
            if rule["repeat"] == "once":
                rule["on"] = False
            out.append({
                "rule": rule["id"], "acted": True,
                "text": f"{condition_text(rule)} ({value_text(rule['trigger'], value)}), so {detail}.",
            })
        elif not rule["blocked"]:
            rule["blocked"] = True
            out.append({
                "rule": rule["id"], "acted": False,
                "text": f"{condition_text(rule)} ({value_text(rule['trigger'], value)}) but {detail}.",
            })
    put(ui, record)
    return out
