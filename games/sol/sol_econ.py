"""Research effects and costs, production, terraforming, close-call tracking and the display updaters for each world (resource, generators, ecology, trade, sky cities, terraforming, research, travel, Governor)."""

import math

from js import document

import sol_runstate as runstate
from sol_rules import (
    CLOSE_CALL_FLOOR, CLOSE_CALL_RECOVERY, LOW_ECOLOGY_PENALTY_MULTIPLIER, LOW_ECOLOGY_THRESHOLD, PLANETS,
    PLANET_DISPLAY_NAMES, RESEARCH_FUND_COST, RESEARCH_NODES, RESEARCH_NODE_BY_ID, RESEARCH_TIERS,
    TERRAFORM_BASE_RATE_PER_SEC, TERRAFORM_ECOLOGY_THRESHOLD, TRADE_ROUTE_RESTORE_PER_SEC, TRAVEL_BUTTON_ID,
    _cost_growth, _ecology_low_seen, _ecology_zero_seen, _sandbox_active, planet_state, prestige_has,
    prestige_multiplier, researched_nodes,
)
from sol_runmods import (
    MUTATOR_COSTLY_FACTOR, anomaly_factor, megaproject_factor, mutator_active, sky_city_bonus_per_city,
)
from sol_scarcity import scarcity_cost, scarcity_terraform
from sol_util import _dom_id


def research_effect(key):
    """Summed effect of every researched node for `key`, as a fraction."""
    cache = runstate._research_effect_cache
    if cache is not None and key in cache:
        return cache[key]
    value = sum(RESEARCH_NODE_BY_ID[n]["effects"].get(key, 0) for n in researched_nodes) / 100.0
    if cache is not None:
        cache[key] = value
    return value


def research_yield_multiplier():
    return 1.0 + research_effect("yield_pct")


def _yield_multiplier():
    """Everything that scales resource yield: the prestige bonus and research."""
    return prestige_multiplier() * research_yield_multiplier()


def research_node_cost(node):
    if _sandbox_active():
        return 0
    if prestige_has("deep_research"):
        return math.ceil(node["cost"] / 1.5)
    return node["cost"]


def research_node_status(node):
    """"researched", "available" (can be bought if affordable) or "locked"."""
    if node["id"] in researched_nodes:
        return "researched"
    if node["tier"] > runstate.completed_tiers:
        return "locked"
    if all(req in researched_nodes for req in node["requires"]):
        return "available"
    return "locked"


def _recompute_research():
    """Derives completed_tiers and research_progress from researched_nodes."""
    done = 0
    for tier in RESEARCH_TIERS:
        if tier["final"] in researched_nodes:
            done += 1
        else:
            break
    runstate.completed_tiers = done
    runstate.research_progress = float(sum(
        node["cost"] for node in RESEARCH_NODES
        if node["tier"] == done and node["id"] in researched_nodes
    ))


def _clean_researched_nodes(candidates):
    """Only real nodes whose prerequisites (and earlier level) are also
    present survive: a tampered or partial save can never grant a node the
    tree wouldn't let you buy."""
    wanted = {n for n in candidates if isinstance(n, str) and n in RESEARCH_NODE_BY_ID}
    changed = True
    while changed:
        changed = False
        for node_id in list(wanted):
            node = RESEARCH_NODE_BY_ID[node_id]
            prior_final = RESEARCH_TIERS[node["tier"] - 1]["final"] if node["tier"] > 0 else None
            if any(req not in wanted for req in node["requires"]) or (prior_final and prior_final not in wanted):
                wanted.discard(node_id)
                changed = True
    return wanted


def _migrate_legacy_research(tiers_done, progress):
    """A save from before the tree stored research as (completed tiers,
    Iron progress in the current tier). Convert it without losing anything:
    every node of a completed level, then as many of the current level's
    nodes as the saved progress paid for, in tree order; any Iron left over
    is returned. Returns (nodes, refund)."""
    nodes = set()
    for level in range(min(int(tiers_done), len(RESEARCH_TIERS))):
        nodes.update(n["id"] for n in RESEARCH_NODES if n["tier"] == level)
    remaining = float(progress) if isinstance(progress, (int, float)) and progress == progress else 0.0
    level = min(int(tiers_done), len(RESEARCH_TIERS) - 1)
    if int(tiers_done) < len(RESEARCH_TIERS):
        for node in RESEARCH_NODES:
            if node["tier"] != level:
                continue
            if node["id"] == RESEARCH_TIERS[level]["final"]:
                continue  # never finish a level from a partial migration
            if all(req in nodes or RESEARCH_NODE_BY_ID[req]["tier"] < level for req in node["requires"]) \
                    and node["cost"] <= remaining:
                nodes.add(node["id"])
                remaining -= node["cost"]
    return nodes, max(0.0, remaining)


def current_tier():
    if runstate.completed_tiers < len(RESEARCH_TIERS):
        return RESEARCH_TIERS[runstate.completed_tiers]
    return None


def other_real_planets(planet):
    return [p for p in PLANETS if p != planet]


def current_trade_destination(planet):
    # Milestone 9f: the destination is now player-selectable (via the
    # "Change Destination" button/_cycle_trade_destination) rather than
    # always resolving to the first other real planet. It's lazily
    # defaulted here — the first time it's asked for — to that same first
    # other real planet, so pre-9f behavior (and pre-9f tests) still holds
    # for anyone who's never cycled it, and it keeps working automatically
    # as later milestones add more real economies.
    state = planet_state[planet]
    if state["trade_destination"] is None:
        others = other_real_planets(planet)
        state["trade_destination"] = others[0] if others else None
    return state["trade_destination"]


def _machinery_discount():
    base = 0.9 if prestige_has("cheaper_machinery") else 1.0
    if mutator_active("costly_machinery"):
        base *= MUTATOR_COSTLY_FACTOR  # A-3: an opt-in rule twist, paid for in prestige points
    return base * (1.0 - research_effect("machinery_discount")) * scarcity_cost()


def generator_cost(planet):
    if _sandbox_active():
        return 0
    cfg = PLANETS[planet]
    count = planet_state[planet]["generator_count"]
    return math.ceil(
        cfg["generator_base_cost"] * (_cost_growth(cfg, "generator_cost_growth") ** count) * _machinery_discount()
    )


def recycler_cost(planet):
    if _sandbox_active():
        return 0
    cfg = PLANETS[planet]
    count = planet_state[planet]["recycler_count"]
    return math.ceil(
        cfg["recycler_base_cost"] * (_cost_growth(cfg, "recycler_cost_growth") ** count) * _machinery_discount()
    )


def trade_route_cost(planet, destination):
    if _sandbox_active():
        return 0
    cfg = PLANETS[planet]
    count = planet_state[planet]["trade_routes"].get(destination, 0)
    return math.ceil(
        cfg["trade_route_base_cost"] * (cfg["trade_route_cost_growth"] ** count)
        * (1.0 - research_effect("route_discount"))
    )


def sky_city_local_cost(planet):
    if _sandbox_active():
        return 0
    cfg = PLANETS[planet]
    count = planet_state[planet]["sky_city_count"]
    return math.ceil(cfg["sky_city_local_base_cost"] * (cfg["sky_city_local_cost_growth"] ** count))


def sky_city_mars_cost(planet):
    if _sandbox_active():
        return 0
    cfg = PLANETS[planet]
    count = planet_state[planet]["sky_city_count"]
    return math.ceil(cfg["sky_city_mars_base_cost"] * (cfg["sky_city_mars_cost_growth"] ** count))


def research_fund_cost():
    return 0 if _sandbox_active() else RESEARCH_FUND_COST


def production_multiplier(planet):
    health = planet_state[planet]["ecology_health"]
    if health <= 0:
        return 0.0
    if health < LOW_ECOLOGY_THRESHOLD:
        return LOW_ECOLOGY_PENALTY_MULTIPLIER
    return 1.0


def has_economic_investment(planet):
    state = planet_state[planet]
    return (
        state["generator_count"] > 0
        or state["recycler_count"] > 0
        or bool(state["trade_routes"])
        or state.get("sky_city_count", 0) > 0
    )


def terraform_rate(planet):
    state = planet_state[planet]
    if not has_economic_investment(planet):
        return 0.0
    health = state["ecology_health"]
    if health < TERRAFORM_ECOLOGY_THRESHOLD:
        return 0.0
    return (TERRAFORM_BASE_RATE_PER_SEC * (health / 100) * anomaly_factor("terraform") * megaproject_factor("terraform")
            * scarcity_terraform())


def update_resource_display(planet):
    # Repeated fractional += from tick() accumulates float error (e.g. ten
    # 0.1 additions land on 0.9999999999999999, not 1.0), which would make
    # the floored display lag a whole unit behind the real total. A tiny
    # epsilon nudge keeps the display honest without affecting real progress.
    state = planet_state[planet]
    document.getElementById(_dom_id(planet, "resource-count")).innerText = str(
        math.floor(state["resource_count"] + 1e-9)
    )


def update_generator_display(planet):
    cfg = PLANETS[planet]
    state = planet_state[planet]
    document.getElementById(_dom_id(planet, "generator-count")).innerText = str(state["generator_count"])
    document.getElementById(_dom_id(planet, "generator-rate")).innerText = str(
        state["generator_count"] * cfg["generator_rate"]
    )
    document.getElementById(_dom_id(planet, "buy-generator-button")).innerText = (
        f"Buy {cfg['generator_singular']} ({generator_cost(planet)} {cfg['resource_name']})"
    )


def update_ecology_display(planet):
    cfg = PLANETS[planet]
    state = planet_state[planet]
    health = state["ecology_health"]

    document.getElementById(_dom_id(planet, "ecology-percent")).innerText = f"{round(health)}%"
    document.getElementById(_dom_id(planet, "ecology-bar")).style.width = f"{health}%"
    document.getElementById(_dom_id(planet, "recycler-count")).innerText = str(state["recycler_count"])
    document.getElementById(_dom_id(planet, "recycler-rate")).innerText = str(
        round(state["recycler_count"] * cfg["recycler_restore_per_sec"], 2)
    )
    document.getElementById(_dom_id(planet, "buy-recycler-button")).innerText = (
        f"Build Recycler ({recycler_cost(planet)} {cfg['resource_name']})"
    )

    status = document.getElementById(_dom_id(planet, "ecology-status"))
    if health <= 0:
        status.innerText = "⚠ Production halted — ecological collapse"
    elif health < LOW_ECOLOGY_THRESHOLD:
        status.innerText = "⚠ Output reduced 25% — ecological health critical"
    else:
        status.innerText = ""

    # A17: a visible warning banner at the 25%-output-penalty threshold,
    # not just the plain status text above -- .ecology-status--warning
    # (style.css) turns the same paragraph into a bordered, colored banner
    # exactly while a real penalty (or full collapse) is in effect.
    if health < LOW_ECOLOGY_THRESHOLD:
        status.classList.add("ecology-status--warning")
    else:
        status.classList.remove("ecology-status--warning")


def update_trade_display(planet):
    cfg = PLANETS[planet]
    state = planet_state[planet]
    destination = current_trade_destination(planet)
    count = state["trade_routes"].get(destination, 0) if destination else 0

    document.getElementById(_dom_id(planet, "trade-route-count")).innerText = str(count)
    document.getElementById(_dom_id(planet, "trade-route-rate")).innerText = str(
        round(count * TRADE_ROUTE_RESTORE_PER_SEC, 2)
    )
    document.getElementById(_dom_id(planet, "trade-route-destination")).innerText = (
        PLANET_DISPLAY_NAMES.get(destination, destination) if destination else "—"
    )

    button = document.getElementById(_dom_id(planet, "buy-trade-route-button"))
    if destination:
        button.innerText = f"Build Trade Route ({trade_route_cost(planet, destination)} {cfg['resource_name']})"
    else:
        button.innerText = "No destination available"


def update_sky_city_display(planet):
    # Only ever called for JupiterMoons/SaturnMoons (Milestone 10) — the
    # dual-cost button text is the visible reminder that gas giant buildings
    # need Mars materials, not just the local resource.
    cfg = PLANETS[planet]
    state = planet_state[planet]
    bonus_pct = round(state["sky_city_count"] * sky_city_bonus_per_city(planet) * 100)

    document.getElementById(_dom_id(planet, "sky-city-count")).innerText = str(state["sky_city_count"])
    document.getElementById(_dom_id(planet, "sky-city-bonus")).innerText = str(bonus_pct)
    document.getElementById(_dom_id(planet, "buy-sky-city-button")).innerText = (
        f"Build Sky City ({sky_city_local_cost(planet)} {cfg['resource_name']} "
        f"+ {sky_city_mars_cost(planet)} {PLANETS['Mars']['resource_name']})"
    )


TERRAFORM_VISUAL_TIER_COUNT = 5  # tiers 0-4, i.e. 25 percentage points per tier


def update_terraform_display(planet):
    state = planet_state[planet]
    progress = state["terraform_progress"]

    document.getElementById(_dom_id(planet, "terraform-percent")).innerText = f"{round(progress)}%"
    document.getElementById(_dom_id(planet, "terraform-bar")).style.width = f"{progress}%"

    status = document.getElementById(_dom_id(planet, "terraform-status"))
    if not has_economic_investment(planet):
        status.innerText = "Paused — build at least one generator or Recycler"
    elif state["ecology_health"] < TERRAFORM_ECOLOGY_THRESHOLD:
        status.innerText = (
            f"Paused — ecology {round(state['ecology_health'])}% "
            f"(needs {int(TERRAFORM_ECOLOGY_THRESHOLD)}%+)"
        )
    else:
        status.innerText = ""

    # A15: a color shift on the planet's own visual as terraform_progress
    # climbs -- style.css defines an increasingly lush green tint per tier,
    # from bare (tier 0) to fully terraformed (tier 4, TERRAFORM_MAX). Only
    # ever a class swap on the existing planet-visual container, no new
    # elements, so it composes with whatever else is already layered onto
    # that div (glow, rings, rocks) per planet.
    visual = document.getElementById(_dom_id(planet, "planet-visual"))
    tier = min(TERRAFORM_VISUAL_TIER_COUNT - 1, int(progress // 25))
    for i in range(TERRAFORM_VISUAL_TIER_COUNT):
        visual.classList.remove(f"terraform-tier-{i}")
    visual.classList.add(f"terraform-tier-{tier}")


def update_research_display():
    tier = current_tier()
    status = document.getElementById("research-status")
    label = document.getElementById("research-label")
    progress_el = document.getElementById("research-progress")

    if tier is None:
        label.innerText = "Research"
        document.getElementById("research-bar").style.width = "100%"
        progress_el.innerText = "All Tiers Unlocked"
        status.innerText = "Every distance tier has been researched."
        update_research_node_list()
        return

    label.innerText = f"Research \u2014 {tier['name']} Tier"
    progress_pct = (runstate.research_progress / tier["target"]) * 100
    document.getElementById("research-bar").style.width = f"{progress_pct}%"
    progress_el.innerText = f"{math.floor(runstate.research_progress)} / {tier['target']}"
    status.innerText = "Each node costs Iron; splits in the tree rejoin, and the last node unlocks the bodies."
    update_research_node_list()


def _research_effect_text(node):
    parts = []
    effects = node["effects"]
    if effects.get("yield_pct"):
        parts.append(f"+{effects['yield_pct']}% yield")
    if effects.get("machinery_discount"):
        parts.append(f"miners {effects['machinery_discount']}% cheaper")
    if effects.get("route_discount"):
        parts.append(f"trade routes {effects['route_discount']}% cheaper")
    if node["id"] == RESEARCH_TIERS[node["tier"]]["final"]:
        parts.append("unlocks " + ", ".join(PLANET_DISPLAY_NAMES.get(b, b) for b in RESEARCH_TIERS[node["tier"]]["unlocks"]))
    return ", ".join(parts) if parts else "a step on the path"


# PC-17: the buy buttons of the "available" nodes in the list currently on
# screen, as (button, node) pairs. update_research_node_list() rebuilds the
# rows (so their affordability is only right at that moment); tick() calls
# update_research_node_flags() to keep each button's `disabled` flag in step
# with the Iron count WITHOUT rebuilding the list, because replacing the
# buttons every 100 ms would swallow a click that lands between mousedown and
# mouseup. Never part of any save.
_research_node_buttons = []


def update_research_node_flags():
    """PC-17: refresh only the `disabled` flag of each available research
    node's button from the current Iron, never the rows themselves."""
    if not _research_node_buttons:
        return
    earth_iron = planet_state["Earth"]["resource_count"]
    for button, node in _research_node_buttons:
        want = earth_iron < research_node_cost(node)
        if bool(button.disabled) != want:
            button.disabled = want


def update_research_node_list():
    """U10: the current level's nodes, one row each, in tree order."""
    container = document.getElementById("research-node-list")
    container.innerHTML = ""
    del _research_node_buttons[:]
    tier_index = runstate.completed_tiers
    if tier_index >= len(RESEARCH_TIERS):
        return
    earth_iron = planet_state["Earth"]["resource_count"]
    for node in RESEARCH_NODES:
        if node["tier"] != tier_index:
            continue
        status = research_node_status(node)
        row = document.createElement("div")
        row.className = f"research-node research-node--{status}"
        title = document.createElement("p")
        title.className = "research-node-name"
        title.innerText = node["name"]
        row.appendChild(title)
        detail = document.createElement("p")
        detail.className = "research-node-detail"
        needs = [RESEARCH_NODE_BY_ID[r]["name"] for r in node["requires"] if r not in researched_nodes]
        if status == "researched":
            detail.innerText = "Researched \u2014 " + _research_effect_text(node)
        elif status == "locked":
            detail.innerText = "Needs: " + ", ".join(needs) + " \u2014 " + _research_effect_text(node)
        else:
            detail.innerText = _research_effect_text(node)
        row.appendChild(detail)
        if status != "researched":
            cost = research_node_cost(node)
            button = document.createElement("button")
            button.type = "button"
            button.className = "secondary research-node-button"
            button.innerText = f"Research ({cost} Iron)"
            button.setAttribute("data-node", node["id"])
            button.disabled = status == "locked" or earth_iron < cost
            if status == "available":
                _research_node_buttons.append((button, node))
            row.appendChild(button)
        container.appendChild(row)


def update_research_tree_display():
    """A16: a small diagram of every research tier instead of a single
    flat progress bar -- each tier is its own card (name, status, which
    bodies it unlocks), rendered left-to-right in research order and
    connected by a plain CSS arrow (.research-tree-arrow), same
    dynamic-DOM-building pattern the achievements panel already
    established (ACHIEVEMENTS-SYSTEM-DESIGN.md §3's fake-DOM note)."""
    tree = document.getElementById("research-tree")
    tree.innerHTML = ""

    for index, tier in enumerate(RESEARCH_TIERS):
        if index > 0:
            arrow = document.createElement("span")
            arrow.className = "research-tree-arrow"
            arrow.innerText = "→"
            tree.appendChild(arrow)

        if index < runstate.completed_tiers:
            tier_status = "completed"
            status_text = "Completed"
        elif index == runstate.completed_tiers:
            tier_status = "current"
            status_text = "In Progress"
        else:
            tier_status = "locked"
            status_text = "Locked"

        node = document.createElement("div")
        node.className = f"research-tree-node research-tree-node--{tier_status}"

        collapsed = index in research_tree_collapsed
        name = document.createElement("button")
        name.type = "button"
        name.className = "research-tree-node-name research-tree-node-toggle"
        name.innerText = ("▸ " if collapsed else "▾ ") + tier["name"]
        name.setAttribute("data-tier", str(index))
        name.title = "Click to expand or collapse this tier"
        node.appendChild(name)
        if collapsed:
            tree.appendChild(node)
            continue

        status_el = document.createElement("p")
        status_el.className = "research-tree-node-status"
        status_el.innerText = status_text
        node.appendChild(status_el)

        unlocks = document.createElement("p")
        unlocks.className = "research-tree-node-unlocks"
        unlocks.innerText = "Unlocks: " + ", ".join(
            PLANET_DISPLAY_NAMES.get(body, body) for body in tier["unlocks"]
        )
        node.appendChild(unlocks)

        tree.appendChild(node)


def _update_travel_progress():
    document.getElementById("travel-progress").innerText = f"{len(runstate.visited_bodies)}/{len(PLANETS)} bodies visited"


def update_travel_display():
    for body, button_id in TRAVEL_BUTTON_ID.items():
        button = document.getElementById(button_id)
        unlocked = body in runstate.unlocked_bodies
        button.hidden = not unlocked
        button.disabled = not unlocked

    # Every "<target> (governed)" cross-summary widget's own hidden state is
    # handled generically in update_cross_summary() instead (so every view
    # gets the same not-yet-unlocked gating Earth's view always had, not
    # just Earth's) — earth-trade is a separate concern (the Trade Route
    # section itself, not a cross-summary widget) so it's still handled here.
    earth_trade = document.getElementById("earth-trade")
    earth_trade.hidden = "Mars" not in runstate.unlocked_bodies

    status = document.getElementById("travel-status")
    status.innerText = "Choose a destination:" if runstate.unlocked_bodies else "Reach the Near Bodies tier to unlock travel."
    _update_travel_progress()


def update_governor_display():
    priority_buttons = {
        "growth": document.getElementById("priority-growth-button"),
        "balance": document.getElementById("priority-balance-button"),
        "ecology": document.getElementById("priority-ecology-button"),
    }
    for priority, button in priority_buttons.items():
        if priority == runstate.governor_priority:
            button.classList.add("selected")
        else:
            button.classList.remove("selected")

    document.getElementById("governor-budget-value").innerText = str(round(runstate.governor_budget_pct))


research_tree_collapsed = set()


# --- A14: research tree tier collapse ---


# --- A19: "close call" tracking ---
def _track_close_calls():
    for planet in PLANETS:
        health = planet_state[planet]["ecology_health"]
        if health < CLOSE_CALL_FLOOR:
            _ecology_low_seen.add(planet)
            if health <= 0:
                _ecology_zero_seen.add(planet)
        elif health >= CLOSE_CALL_RECOVERY:
            if planet in _ecology_low_seen:
                runstate.close_call_hit = True
            if planet in _ecology_zero_seen:
                runstate.back_from_brink_hit = True


def _forget_close_call_history(planet=None):
    if planet is None:
        _ecology_low_seen.clear()
        _ecology_zero_seen.clear()
    else:
        _ecology_low_seen.discard(planet)
        _ecology_zero_seen.discard(planet)
