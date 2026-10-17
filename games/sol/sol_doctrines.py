"""Governor Doctrines: rules, conditions, actions and the per-tick doctrine step."""

import sol_runstate as runstate
from sol_econ import (
    generator_cost, recycler_cost, trade_route_cost, update_ecology_display, update_generator_display,
)
from sol_rules import (
    ECOLOGY_MAX, PLANETS, PLANET_DISPLAY_NAMES, TICK_INTERVAL_MS, planet_state, prestige_has,
    researched_nodes,
)
from sol_util import _overview_planets, clamp


# --- A-7 / A-8: Governor Doctrines ------------------------------------------------
# Per-world if/then rules the Governor follows on worlds you are NOT standing on
# (it governs nothing else). Unlocked by researching Automation Basics (a Near
# Bodies node), 3 rules, 5 with the Prestige Tree's Standing Orders. Rules are
# kept when you prestige but sleep until Automation Basics is researched again.
# Each tick, for each governed world, the rules run in order; a "pause" rule that
# holds stops the Governor's own buying there that tick, the others buy or ship
# something when they can afford it. The Governor Report shows the rule that
# fired last on each world. A-8: "Try for 30 ticks" runs the rules headless on a
# copy of the numbers (nothing real changes) and says how often each would fire.
DOCTRINE_UNLOCK_NODE = "automation_basics"
DOCTRINE_BASE_RULES = 3
DOCTRINE_MAX_RULES = 5
DRY_RUN_TICKS = 30
DOCTRINE_RELIEF_COST = 100
DOCTRINE_RELIEF_ECOLOGY = 10.0
DOCTRINE_RELIEF_COOLDOWN_TICKS = 200
DOCTRINE_CONDITIONS = {
    "ecology_below": {"levels": [30, 50, 70], "label": "ecology is below {level}%"},
    "stock_above": {"levels": [500, 2000, 5000], "label": "its stock is above {level} {resource}"},
}
DOCTRINE_ACTIONS = {
    "pause": "pause the Governor's own buying",
    "recycler": "buy a Recycler",
    "generator": "buy an Auto-Miner",
    "relief": f"ship relief (+{round(DOCTRINE_RELIEF_ECOLOGY)}% ecology, costs {DOCTRINE_RELIEF_COST} of your biggest pile)",
    "route": "start a trade route to the neediest world",
}
doctrine_rules = []  # [{"planet", "cond", "level", "action"}], in priority order

_doctrine_draft = {"planet": "Earth", "cond": "ecology_below", "level": 30, "action": "recycler"}

_doctrine_refs = {}


def doctrines_unlocked():
    return DOCTRINE_UNLOCK_NODE in researched_nodes


def doctrine_rule_limit():
    return DOCTRINE_MAX_RULES if prestige_has("standing_orders") else DOCTRINE_BASE_RULES


def _doctrine_reset_runtime():
    runstate._doctrine_fired_counts.clear()
    runstate._doctrine_last_fired.clear()
    runstate._doctrine_relief_ready.clear()
    runstate._doctrine_dry_text = ""


def _clean_doctrine_rules(raw):
    cleaned = []
    if isinstance(raw, list):
        for rule in raw:
            if not isinstance(rule, dict):
                continue
            planet, cond, level, action = rule.get("planet"), rule.get("cond"), rule.get("level"), rule.get("action")
            if (planet in PLANETS and cond in DOCTRINE_CONDITIONS and action in DOCTRINE_ACTIONS
                    and isinstance(level, int) and not isinstance(level, bool)
                    and level in DOCTRINE_CONDITIONS[cond]["levels"]):
                cleaned.append({"planet": planet, "cond": cond, "level": level, "action": action})
    return cleaned[:DOCTRINE_MAX_RULES]


def doctrine_rule_text(rule):
    name = PLANET_DISPLAY_NAMES.get(rule["planet"], rule["planet"])
    cond = DOCTRINE_CONDITIONS[rule["cond"]]["label"].format(
        level=f"{rule['level']:,}", resource=PLANETS[rule["planet"]]["resource_name"])
    return f"On {name}, if {cond}, {DOCTRINE_ACTIONS[rule['action']]}."


def _doctrine_holds(rule):
    state = planet_state[rule["planet"]]
    if rule["cond"] == "ecology_below":
        return state["ecology_health"] < rule["level"]
    return state["resource_count"] > rule["level"]


def _doctrine_mark_fired(index, rule):
    runstate._doctrine_fired_counts[index] = runstate._doctrine_fired_counts.get(index, 0) + 1
    runstate._doctrine_last_fired[rule["planet"]] = (doctrine_rule_text(rule), runstate.total_ticks)


def _doctrine_buy(planet, kind):
    state = planet_state[planet]
    if kind == "generator":
        cost = generator_cost(planet)
        if state["resource_count"] < cost:
            return False
        state["resource_count"] -= cost
        state["generator_count"] += 1
        runstate.lifetime_generators_built += 1
        runstate.any_generator_ever_built = True
    else:
        cost = recycler_cost(planet)
        if state["resource_count"] < cost:
            return False
        state["resource_count"] -= cost
        state["recycler_count"] += 1
        runstate.lifetime_recyclers_built += 1
    runstate.governor_purchase_count += 1
    if not runstate._dry_run:
        update_generator_display(planet)
        update_ecology_display(planet)
    return True


def _doctrine_relief(planet):
    ready = runstate._doctrine_relief_ready.get(planet, 0)
    if runstate.total_ticks < ready:
        return False
    sources = [p for p in _overview_planets() if p != planet and planet_state[p]["resource_count"] >= DOCTRINE_RELIEF_COST]
    if not sources:
        return False
    source = max(sources, key=lambda p: planet_state[p]["resource_count"])
    planet_state[source]["resource_count"] -= DOCTRINE_RELIEF_COST
    state = planet_state[planet]
    state["ecology_health"] = clamp(state["ecology_health"] + DOCTRINE_RELIEF_ECOLOGY, 0.0, ECOLOGY_MAX)
    runstate._doctrine_relief_ready[planet] = runstate.total_ticks + DOCTRINE_RELIEF_COOLDOWN_TICKS
    return True


def _doctrine_route(planet):
    others = [p for p in _overview_planets() if p != planet]
    if not others:
        return False
    destination = min(others, key=lambda p: planet_state[p]["ecology_health"])
    cost = trade_route_cost(planet, destination)
    state = planet_state[planet]
    if state["resource_count"] < cost:
        return False
    state["resource_count"] -= cost
    state["trade_routes"][destination] = state["trade_routes"].get(destination, 0) + 1
    runstate.lifetime_trade_routes_built += 1
    return True


def _doctrine_step(planet):
    """Runs this world's rules for one tick. Returns True when a pause rule holds (the Governor then skips its own buying)."""
    if not doctrines_unlocked():
        return False
    paused = False
    for index, rule in enumerate(doctrine_rules[:doctrine_rule_limit()]):
        if rule["planet"] != planet or not _doctrine_holds(rule):
            continue
        action = rule["action"]
        if action == "pause":
            paused = True
            fired = True
        elif action in ("recycler", "generator"):
            fired = _doctrine_buy(planet, action)
        elif action == "relief":
            fired = _doctrine_relief(planet)
        else:
            fired = _doctrine_route(planet)
        if fired:
            _doctrine_mark_fired(index, rule)
    return paused


def doctrine_report_line(planet):
    last = runstate._doctrine_last_fired.get(planet)
    if last is None:
        return "Doctrine: no rule has fired here yet."
    seconds = max(0, (runstate.total_ticks - last[1]) * TICK_INTERVAL_MS // 1000)
    return f"Doctrine fired {seconds}s ago: {last[0]}"
