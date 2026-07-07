import math
from js import document, setInterval, setTimeout
from pyodide.ffi import create_proxy

# --- static per-planet config ---
# Every entry here is a full economy: click resource, auto-generator building,
# and a Recycler that restores ecological health — a direct reuse of the
# Milestone 2/3 systems, just reskinned per planet (same pattern the project
# plans to reuse again for gas giants later).
PLANETS = {
    "Earth": {
        "resource_name": "Iron",
        "generator_singular": "Auto-Miner",
        "generator_plural": "Auto-Miners",
        "generator_base_cost": 10,
        "generator_cost_growth": 1.15,
        "generator_rate": 1,  # resource per second, per generator
        "ecology_decay_per_generator_per_sec": 1.0,
        "recycler_base_cost": 15,
        "recycler_cost_growth": 1.15,
        "recycler_restore_per_sec": 2.0,
        "trade_route_base_cost": 30,
        "trade_route_cost_growth": 1.15,
    },
    "Mars": {
        "resource_name": "Water Ice",
        "generator_singular": "Auto-Extractor",
        "generator_plural": "Auto-Extractors",
        "generator_base_cost": 10,
        "generator_cost_growth": 1.15,
        "generator_rate": 1,
        "ecology_decay_per_generator_per_sec": 1.0,
        "recycler_base_cost": 15,
        "recycler_cost_growth": 1.15,
        "recycler_restore_per_sec": 2.0,
        "trade_route_base_cost": 30,
        "trade_route_cost_growth": 1.15,
    },
    "Moon": {
        "resource_name": "Regolith",
        "generator_singular": "Auto-Harvester",
        "generator_plural": "Auto-Harvesters",
        "generator_base_cost": 10,
        "generator_cost_growth": 1.15,
        "generator_rate": 1,
        "ecology_decay_per_generator_per_sec": 1.0,
        "recycler_base_cost": 15,
        "recycler_cost_growth": 1.15,
        "recycler_restore_per_sec": 2.0,
        "trade_route_base_cost": 30,
        "trade_route_cost_growth": 1.15,
    },
    "Venus": {
        "resource_name": "Sulfur",
        "generator_singular": "Auto-Scrubber",
        "generator_plural": "Auto-Scrubbers",
        "generator_base_cost": 10,
        "generator_cost_growth": 1.15,
        "generator_rate": 1,
        "ecology_decay_per_generator_per_sec": 1.0,
        "recycler_base_cost": 15,
        "recycler_cost_growth": 1.15,
        "recycler_restore_per_sec": 2.0,
        "trade_route_base_cost": 30,
        "trade_route_cost_growth": 1.15,
    },
}

# Ecology restored on the DESTINATION planet, per Trade Route, per second.
# Deliberately weaker than a local Recycler (2.0/s) — shipping materials
# across planets is a supplementary lever, not a replacement for local
# investment. Subject to the Milestone 11 balance pass.
TRADE_ROUTE_RESTORE_PER_SEC = 0.5

# Terraforming accrues only while a planet is under genuine sustained
# balance — ecology health above a real "thriving" bar (not just clear of
# the crisis threshold) AND actual economic investment present. Below that
# bar, progress simply pauses; it never regresses, per the project's
# "always recoverable, no dead-end states" rule. Rate scales with ecology
# health above the bar. Numbers are an initial guess, subject to the
# Milestone 11 balance pass.
TERRAFORM_ECOLOGY_THRESHOLD = 50.0
TERRAFORM_BASE_RATE_PER_SEC = 0.1
TERRAFORM_MAX = 100.0

# --- mutable per-planet state ---
planet_state = {
    name: {
        "resource_count": 0.0,
        "generator_count": 0,
        "recycler_count": 0,
        "ecology_health": 100.0,
        "trade_routes": {},  # destination planet name -> route count
        "terraform_progress": 0.0,
    }
    for name in PLANETS
}

# --- research tiers ---
# Research isn't strictly linear — reaching a distance tier can unlock
# several bodies in parallel rather than one planet at a time. Tiers are
# researched in sequence (you can't fund tier 2 before tier 1 is done);
# "unlocks" only grants travel access — most of these bodies get their own
# economy in a later milestone (Moon: 9b, Venus: 9c, Asteroid Belt: 9d,
# Pluto: 9e, Jupiter's Moons: 9f, Saturn's Moons: 9g). Until then, visiting
# one shows the shared "undeveloped destination" placeholder.
RESEARCH_TIERS = [
    {"name": "Near Bodies", "target": 1000, "unlocks": ["Moon", "Mars"]},
    {
        "name": "Far Bodies",
        "target": 5000,
        "unlocks": ["Venus", "AsteroidBelt", "Pluto", "JupiterMoons", "SaturnMoons"],
    },
]
RESEARCH_FUND_COST = 50  # flat Iron per investment, same across every tier, not a scaling purchase

# Bodies with no economy of their own yet — visiting any of these shows the
# shared #away-view placeholder rather than a dedicated view.
UNDEVELOPED_BODIES = ["AsteroidBelt", "Pluto", "JupiterMoons", "SaturnMoons"]

# Human-readable heading text for the away-view placeholder (internal
# identifiers avoid spaces/apostrophes so they're safe to use in DOM ids).
BODY_DISPLAY_NAMES = {
    "AsteroidBelt": "ASTEROID BELT",
    "Pluto": "PLUTO",
    "JupiterMoons": "JUPITER'S MOONS",
    "SaturnMoons": "SATURN'S MOONS",
}

TRAVEL_BUTTON_ID = {
    "Moon": "travel-moon-button",
    "Mars": "travel-mars-button",
    "Venus": "travel-venus-button",
    "AsteroidBelt": "travel-asteroid-belt-button",
    "Pluto": "travel-pluto-button",
    "JupiterMoons": "travel-jupiter-moons-button",
    "SaturnMoons": "travel-saturn-moons-button",
}

# --- global (non-planet) state ---
research_progress = 0.0  # progress toward the current (next incomplete) tier
completed_tiers = 0
unlocked_bodies = set()
current_planet = "Earth"
governor_priority = "balance"  # "growth" | "balance" | "ecology"
governor_budget_pct = 50.0
governor_tick_count = 0

TICK_INTERVAL_MS = 100

ECOLOGY_MAX = 100.0
LOW_ECOLOGY_THRESHOLD = 10.0
LOW_ECOLOGY_PENALTY_MULTIPLIER = 0.75

GOVERNOR_BUDGET_STEP = 10.0
GOVERNOR_BUDGET_MIN = 0.0
GOVERNOR_BUDGET_MAX = 100.0


def current_tier():
    if completed_tiers < len(RESEARCH_TIERS):
        return RESEARCH_TIERS[completed_tiers]
    return None


def other_real_planets(planet):
    return [p for p in PLANETS if p != planet]


def primary_trade_destination(planet):
    # Trade only has one possible destination per planet for now (Earth
    # and Mars are the only two real economies) — this is computed rather
    # than a hardcoded pair, so it keeps working once Milestones 9b+ add
    # more real economies; picking among multiple destinations is a UI
    # decision for whichever milestone first makes that ambiguous.
    others = other_real_planets(planet)
    return others[0] if others else None


def _dom_id(planet, suffix):
    # Earth's ids are unprefixed (predate multi-planet support); every other
    # real economy gets a "<planet>-" prefix.
    prefix = "" if planet == "Earth" else f"{planet.lower()}-"
    return f"{prefix}{suffix}"


def generator_cost(planet):
    cfg = PLANETS[planet]
    count = planet_state[planet]["generator_count"]
    return math.ceil(cfg["generator_base_cost"] * (cfg["generator_cost_growth"] ** count))


def recycler_cost(planet):
    cfg = PLANETS[planet]
    count = planet_state[planet]["recycler_count"]
    return math.ceil(cfg["recycler_base_cost"] * (cfg["recycler_cost_growth"] ** count))


def trade_route_cost(planet, destination):
    cfg = PLANETS[planet]
    count = planet_state[planet]["trade_routes"].get(destination, 0)
    return math.ceil(cfg["trade_route_base_cost"] * (cfg["trade_route_cost_growth"] ** count))


def production_multiplier(planet):
    health = planet_state[planet]["ecology_health"]
    if health <= 0:
        return 0.0
    if health < LOW_ECOLOGY_THRESHOLD:
        return LOW_ECOLOGY_PENALTY_MULTIPLIER
    return 1.0


def clamp(value, low, high):
    return max(low, min(high, value))


def has_economic_investment(planet):
    state = planet_state[planet]
    return state["generator_count"] > 0 or state["recycler_count"] > 0 or bool(state["trade_routes"])


def terraform_rate(planet):
    state = planet_state[planet]
    if not has_economic_investment(planet):
        return 0.0
    health = state["ecology_health"]
    if health < TERRAFORM_ECOLOGY_THRESHOLD:
        return 0.0
    return TERRAFORM_BASE_RATE_PER_SEC * (health / 100)


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
        status.innerText = "Production halted — ecological collapse"
    elif health < LOW_ECOLOGY_THRESHOLD:
        status.innerText = "Output reduced 25% — ecological health critical"
    else:
        status.innerText = ""


def update_trade_display(planet):
    cfg = PLANETS[planet]
    state = planet_state[planet]
    destination = primary_trade_destination(planet)
    count = state["trade_routes"].get(destination, 0) if destination else 0

    document.getElementById(_dom_id(planet, "trade-route-count")).innerText = str(count)
    document.getElementById(_dom_id(planet, "trade-route-rate")).innerText = str(
        round(count * TRADE_ROUTE_RESTORE_PER_SEC, 2)
    )
    document.getElementById(_dom_id(planet, "trade-route-destination")).innerText = destination or "—"

    button = document.getElementById(_dom_id(planet, "buy-trade-route-button"))
    if destination:
        button.innerText = f"Build Trade Route ({trade_route_cost(planet, destination)} {cfg['resource_name']})"
    else:
        button.innerText = "No destination available"


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


def update_research_display():
    tier = current_tier()
    button = document.getElementById("fund-research-button")
    status = document.getElementById("research-status")
    label = document.getElementById("research-label")
    progress_el = document.getElementById("research-progress")

    if tier is None:
        label.innerText = "Research"
        document.getElementById("research-bar").style.width = "100%"
        progress_el.innerText = "All Tiers Unlocked"
        status.innerText = "Every distance tier has been researched."
        button.innerText = "All Tiers Unlocked"
        button.disabled = True
        return

    label.innerText = f"Research — {tier['name']} Tier"
    progress_pct = (research_progress / tier["target"]) * 100
    document.getElementById("research-bar").style.width = f"{progress_pct}%"
    progress_el.innerText = f"{math.floor(research_progress)} / {tier['target']}"
    status.innerText = ""
    button.innerText = f"Fund Research ({RESEARCH_FUND_COST} Iron)"
    button.disabled = False


def update_travel_display():
    for body, button_id in TRAVEL_BUTTON_ID.items():
        button = document.getElementById(button_id)
        unlocked = body in unlocked_bodies
        button.hidden = not unlocked
        button.disabled = not unlocked

    mars_summary = document.getElementById("mars-summary")
    earth_trade = document.getElementById("earth-trade")
    mars_unlocked = "Mars" in unlocked_bodies
    mars_summary.hidden = not mars_unlocked
    earth_trade.hidden = not mars_unlocked

    moon_summary = document.getElementById("moon-summary")
    moon_summary.hidden = "Moon" not in unlocked_bodies

    venus_summary = document.getElementById("venus-summary")
    venus_summary.hidden = "Venus" not in unlocked_bodies

    status = document.getElementById("travel-status")
    status.innerText = "Choose a destination:" if unlocked_bodies else "Reach the Near Bodies tier to unlock travel."


def update_governor_display():
    priority_buttons = {
        "growth": document.getElementById("priority-growth-button"),
        "balance": document.getElementById("priority-balance-button"),
        "ecology": document.getElementById("priority-ecology-button"),
    }
    for priority, button in priority_buttons.items():
        if priority == governor_priority:
            button.classList.add("selected")
        else:
            button.classList.remove("selected")

    document.getElementById("governor-budget-value").innerText = str(round(governor_budget_pct))


def update_cross_summary(viewer, target):
    # Shows `target`'s governed stats on `viewer`'s own view — e.g. Earth's
    # view shows a "Mars (governed)" widget, Mars's view shows an "Earth
    # (governed)" widget, and so on for every pair of real economies, once
    # there are more than two. Ids are viewer-prefixed (via _dom_id) so each
    # view's widget for the same target doesn't collide with any other
    # view's widget for that same target.
    state = planet_state[target]

    def widget_id(field):
        return _dom_id(viewer, f"{target.lower()}-summary-{field}")

    document.getElementById(widget_id("resource")).innerText = str(math.floor(state["resource_count"] + 1e-9))
    document.getElementById(widget_id("generators")).innerText = str(state["generator_count"])
    document.getElementById(widget_id("recyclers")).innerText = str(state["recycler_count"])
    document.getElementById(widget_id("ecology")).innerText = str(round(state["ecology_health"]))


def update_all_cross_summaries():
    for viewer in PLANETS:
        for target in PLANETS:
            if viewer != target:
                update_cross_summary(viewer, target)


def update_away_summary():
    # Every undeveloped body (Moon, Venus, Asteroid Belt, Pluto, Jupiter's
    # Moons, Saturn's Moons) shares this one placeholder screen, showing
    # ALL real economies as "governed" — not just Earth's, a gap flagged
    # (and left as a known simplification) back in Milestone 6. Each future
    # milestone that turns one of these bodies into a real economy needs to
    # add its own summary block here too, same as Mars's was just added.
    document.getElementById("away-planet-name").innerText = BODY_DISPLAY_NAMES.get(
        current_planet, current_planet.upper()
    )
    for planet in PLANETS:
        state = planet_state[planet]
        prefix = f"away-{planet.lower()}"
        document.getElementById(f"{prefix}-resource").innerText = str(math.floor(state["resource_count"] + 1e-9))
        document.getElementById(f"{prefix}-generators").innerText = str(state["generator_count"])
        document.getElementById(f"{prefix}-recyclers").innerText = str(state["recycler_count"])
        document.getElementById(f"{prefix}-ecology").innerText = str(round(state["ecology_health"]))


def _hide_all_views():
    document.getElementById("earth-view").hidden = True
    document.getElementById("mars-view").hidden = True
    document.getElementById("moon-view").hidden = True
    document.getElementById("venus-view").hidden = True
    document.getElementById("away-view").hidden = True


def press_feedback(button):
    button.classList.add("pressed")

    def _clear(*args):
        button.classList.remove("pressed")
    setTimeout(create_proxy(_clear), 120)


def _mine(planet):
    # Manual mining always works, even during an ecological collapse that
    # halts automated production on that planet — otherwise a player who
    # lets health hit 0% with no resources banked could get permanently
    # stuck with no way to earn the resources needed to build a recovery
    # Recycler. Per the project's "no dead-end/unwinnable states" balance
    # rule, there must always be a lever.
    state = planet_state[planet]
    state["resource_count"] += 1
    update_resource_display(planet)
    press_feedback(document.getElementById(_dom_id(planet, "click-button")))


def on_earth_click(event):
    _mine("Earth")


def on_mars_click(event):
    _mine("Mars")


def on_moon_click(event):
    _mine("Moon")


def on_venus_click(event):
    _mine("Venus")


def _buy_generator(planet):
    state = planet_state[planet]
    button = document.getElementById(_dom_id(planet, "buy-generator-button"))
    cost = generator_cost(planet)
    if state["resource_count"] >= cost:
        state["resource_count"] -= cost
        state["generator_count"] += 1
        update_resource_display(planet)
        update_generator_display(planet)
        update_terraform_display(planet)
    press_feedback(button)


def on_earth_buy_generator(event):
    _buy_generator("Earth")


def on_mars_buy_generator(event):
    _buy_generator("Mars")


def on_moon_buy_generator(event):
    _buy_generator("Moon")


def on_venus_buy_generator(event):
    _buy_generator("Venus")


def _buy_recycler(planet):
    state = planet_state[planet]
    button = document.getElementById(_dom_id(planet, "buy-recycler-button"))
    cost = recycler_cost(planet)
    if state["resource_count"] >= cost:
        state["resource_count"] -= cost
        state["recycler_count"] += 1
        update_resource_display(planet)
        update_ecology_display(planet)
        update_terraform_display(planet)
    press_feedback(button)


def on_earth_buy_recycler(event):
    _buy_recycler("Earth")


def on_mars_buy_recycler(event):
    _buy_recycler("Mars")


def on_moon_buy_recycler(event):
    _buy_recycler("Moon")


def on_venus_buy_recycler(event):
    _buy_recycler("Venus")


def _buy_trade_route(planet):
    state = planet_state[planet]
    button = document.getElementById(_dom_id(planet, "buy-trade-route-button"))
    destination = primary_trade_destination(planet)
    if destination is not None:
        cost = trade_route_cost(planet, destination)
        if state["resource_count"] >= cost:
            state["resource_count"] -= cost
            state["trade_routes"][destination] = state["trade_routes"].get(destination, 0) + 1
            update_resource_display(planet)
            update_trade_display(planet)
            update_terraform_display(planet)
    press_feedback(button)


def on_earth_buy_trade_route(event):
    _buy_trade_route("Earth")


def on_mars_buy_trade_route(event):
    _buy_trade_route("Mars")


def on_moon_buy_trade_route(event):
    _buy_trade_route("Moon")


def on_venus_buy_trade_route(event):
    _buy_trade_route("Venus")


def on_fund_research(event):
    global research_progress, completed_tiers
    button = document.getElementById("fund-research-button")
    earth = planet_state["Earth"]
    tier = current_tier()
    if tier is not None and earth["resource_count"] >= RESEARCH_FUND_COST:
        earth["resource_count"] -= RESEARCH_FUND_COST
        research_progress = min(research_progress + RESEARCH_FUND_COST, tier["target"])
        if research_progress >= tier["target"]:
            unlocked_bodies.update(tier["unlocks"])
            completed_tiers += 1
            research_progress = 0.0
            update_travel_display()
        update_resource_display("Earth")
        update_research_display()
    press_feedback(button)


def on_priority_growth(event):
    global governor_priority
    governor_priority = "growth"
    update_governor_display()
    press_feedback(document.getElementById("priority-growth-button"))


def on_priority_balance(event):
    global governor_priority
    governor_priority = "balance"
    update_governor_display()
    press_feedback(document.getElementById("priority-balance-button"))


def on_priority_ecology(event):
    global governor_priority
    governor_priority = "ecology"
    update_governor_display()
    press_feedback(document.getElementById("priority-ecology-button"))


def on_budget_increase(event):
    global governor_budget_pct
    governor_budget_pct = clamp(governor_budget_pct + GOVERNOR_BUDGET_STEP, GOVERNOR_BUDGET_MIN, GOVERNOR_BUDGET_MAX)
    update_governor_display()
    press_feedback(document.getElementById("budget-increase-button"))


def on_budget_decrease(event):
    global governor_budget_pct
    governor_budget_pct = clamp(governor_budget_pct - GOVERNOR_BUDGET_STEP, GOVERNOR_BUDGET_MIN, GOVERNOR_BUDGET_MAX)
    update_governor_display()
    press_feedback(document.getElementById("budget-decrease-button"))


def _travel_to_undeveloped(body):
    global current_planet
    current_planet = body
    _hide_all_views()
    document.getElementById("away-view").hidden = False
    update_away_summary()


def on_travel_moon(event):
    global current_planet
    if "Moon" in unlocked_bodies:
        current_planet = "Moon"
        _hide_all_views()
        document.getElementById("moon-view").hidden = False
        update_resource_display("Moon")
        update_generator_display("Moon")
        update_ecology_display("Moon")
        update_trade_display("Moon")
        update_terraform_display("Moon")
        update_all_cross_summaries()
    press_feedback(document.getElementById("travel-moon-button"))


def on_travel_venus(event):
    global current_planet
    if "Venus" in unlocked_bodies:
        current_planet = "Venus"
        _hide_all_views()
        document.getElementById("venus-view").hidden = False
        update_resource_display("Venus")
        update_generator_display("Venus")
        update_ecology_display("Venus")
        update_trade_display("Venus")
        update_terraform_display("Venus")
        update_all_cross_summaries()
    press_feedback(document.getElementById("travel-venus-button"))


def on_travel_asteroid_belt(event):
    if "AsteroidBelt" in unlocked_bodies:
        _travel_to_undeveloped("AsteroidBelt")
    press_feedback(document.getElementById("travel-asteroid-belt-button"))


def on_travel_pluto(event):
    if "Pluto" in unlocked_bodies:
        _travel_to_undeveloped("Pluto")
    press_feedback(document.getElementById("travel-pluto-button"))


def on_travel_jupiter_moons(event):
    if "JupiterMoons" in unlocked_bodies:
        _travel_to_undeveloped("JupiterMoons")
    press_feedback(document.getElementById("travel-jupiter-moons-button"))


def on_travel_saturn_moons(event):
    if "SaturnMoons" in unlocked_bodies:
        _travel_to_undeveloped("SaturnMoons")
    press_feedback(document.getElementById("travel-saturn-moons-button"))


def on_travel_mars(event):
    global current_planet
    if "Mars" in unlocked_bodies:
        current_planet = "Mars"
        _hide_all_views()
        document.getElementById("mars-view").hidden = False
        update_resource_display("Mars")
        update_generator_display("Mars")
        update_ecology_display("Mars")
        update_trade_display("Mars")
        update_terraform_display("Mars")
        update_all_cross_summaries()
    press_feedback(document.getElementById("travel-mars-button"))


def _return_to_earth():
    global current_planet
    current_planet = "Earth"
    _hide_all_views()
    document.getElementById("earth-view").hidden = False
    update_resource_display("Earth")
    update_generator_display("Earth")
    update_ecology_display("Earth")
    update_trade_display("Earth")
    update_terraform_display("Earth")
    update_all_cross_summaries()


def on_return_to_earth_from_away_view(event):
    _return_to_earth()
    press_feedback(document.getElementById("return-to-earth-button"))


def on_return_to_earth_from_mars(event):
    _return_to_earth()
    press_feedback(document.getElementById("mars-return-to-earth-button"))


def on_return_to_earth_from_moon(event):
    _return_to_earth()
    press_feedback(document.getElementById("moon-return-to-earth-button"))


def on_return_to_earth_from_venus(event):
    _return_to_earth()
    press_feedback(document.getElementById("venus-return-to-earth-button"))


def governor_step():
    # Autonomously manages every real economy the player is currently NOT
    # on, using the shared priority/budget config — e.g. while on Earth,
    # Mars is governed; while on Mars or any undeveloped body, Earth (and
    # Mars, if that's not where the player is either) keeps running. This
    # loop is already N-planet generic: it governs everything in PLANETS
    # except current_planet, however many real economies that ends up being.
    global governor_tick_count
    governed_planets = [planet for planet in PLANETS if planet != current_planet]
    if not governed_planets:
        return

    governor_tick_count += 1
    if governor_priority == "growth":
        buy_generator_turn = True
    elif governor_priority == "ecology":
        buy_generator_turn = False
    else:  # "balance" — alternate turns between the two buildings
        buy_generator_turn = governor_tick_count % 2 == 0

    for planet in governed_planets:
        state = planet_state[planet]
        budget = state["resource_count"] * (governor_budget_pct / 100)

        if buy_generator_turn:
            cost = generator_cost(planet)
            if cost <= budget:
                state["resource_count"] -= cost
                state["generator_count"] += 1
                update_generator_display(planet)
        else:
            cost = recycler_cost(planet)
            if cost <= budget:
                state["resource_count"] -= cost
                state["recycler_count"] += 1
                update_ecology_display(planet)


def _incoming_trade_restore(planet):
    # Sums contributions from every OTHER real economy that has routes
    # targeting this planet — generic over however many senders exist,
    # not just a single hardcoded partner.
    total = 0.0
    for sender in PLANETS:
        if sender == planet:
            continue
        count = planet_state[sender]["trade_routes"].get(planet, 0)
        total += count * TRADE_ROUTE_RESTORE_PER_SEC * (TICK_INTERVAL_MS / 1000)
    return total


def _simulate_planet(planet, incoming_trade_restore):
    cfg = PLANETS[planet]
    state = planet_state[planet]

    if state["generator_count"] > 0:
        multiplier = production_multiplier(planet)
        if multiplier > 0:
            state["resource_count"] += (
                state["generator_count"] * cfg["generator_rate"] * (TICK_INTERVAL_MS / 1000) * multiplier
            )

    decay = state["generator_count"] * cfg["ecology_decay_per_generator_per_sec"] * (TICK_INTERVAL_MS / 1000)
    restore = state["recycler_count"] * cfg["recycler_restore_per_sec"] * (TICK_INTERVAL_MS / 1000)
    state["ecology_health"] = clamp(
        state["ecology_health"] - decay + restore + incoming_trade_restore, 0.0, ECOLOGY_MAX
    )

    state["terraform_progress"] = clamp(
        state["terraform_progress"] + terraform_rate(planet) * (TICK_INTERVAL_MS / 1000),
        0.0,
        TERRAFORM_MAX,
    )


def tick(*args):
    # Trade contributions are computed from pre-tick trade_routes before
    # anything mutates this tick, so every planet's routes are based on
    # pre-tick counts rather than an order-dependent mix.
    incoming_trade_restore = {planet: _incoming_trade_restore(planet) for planet in PLANETS}

    for planet in PLANETS:
        _simulate_planet(planet, incoming_trade_restore[planet])

    governor_step()

    for planet in PLANETS:
        update_resource_display(planet)
        update_generator_display(planet)
        update_ecology_display(planet)
        update_trade_display(planet)
        update_terraform_display(planet)

    update_all_cross_summaries()
    update_away_summary()


def setup():
    earth_click = document.getElementById("click-button")
    earth_click.innerText = "Mine Iron"
    earth_click.disabled = False
    earth_click.addEventListener("click", create_proxy(on_earth_click))

    earth_buy_generator = document.getElementById("buy-generator-button")
    earth_buy_generator.disabled = False
    earth_buy_generator.addEventListener("click", create_proxy(on_earth_buy_generator))

    earth_buy_recycler = document.getElementById("buy-recycler-button")
    earth_buy_recycler.disabled = False
    earth_buy_recycler.addEventListener("click", create_proxy(on_earth_buy_recycler))

    earth_buy_trade_route = document.getElementById("buy-trade-route-button")
    earth_buy_trade_route.disabled = False
    earth_buy_trade_route.addEventListener("click", create_proxy(on_earth_buy_trade_route))

    mars_click = document.getElementById("mars-click-button")
    mars_click.innerText = "Extract Ice"
    mars_click.disabled = False
    mars_click.addEventListener("click", create_proxy(on_mars_click))

    mars_buy_generator = document.getElementById("mars-buy-generator-button")
    mars_buy_generator.disabled = False
    mars_buy_generator.addEventListener("click", create_proxy(on_mars_buy_generator))

    mars_buy_recycler = document.getElementById("mars-buy-recycler-button")
    mars_buy_recycler.disabled = False
    mars_buy_recycler.addEventListener("click", create_proxy(on_mars_buy_recycler))

    mars_buy_trade_route = document.getElementById("mars-buy-trade-route-button")
    mars_buy_trade_route.disabled = False
    mars_buy_trade_route.addEventListener("click", create_proxy(on_mars_buy_trade_route))

    document.getElementById("mars-return-to-earth-button").addEventListener(
        "click", create_proxy(on_return_to_earth_from_mars)
    )

    moon_click = document.getElementById("moon-click-button")
    moon_click.innerText = "Mine Regolith"
    moon_click.disabled = False
    moon_click.addEventListener("click", create_proxy(on_moon_click))

    moon_buy_generator = document.getElementById("moon-buy-generator-button")
    moon_buy_generator.disabled = False
    moon_buy_generator.addEventListener("click", create_proxy(on_moon_buy_generator))

    moon_buy_recycler = document.getElementById("moon-buy-recycler-button")
    moon_buy_recycler.disabled = False
    moon_buy_recycler.addEventListener("click", create_proxy(on_moon_buy_recycler))

    moon_buy_trade_route = document.getElementById("moon-buy-trade-route-button")
    moon_buy_trade_route.disabled = False
    moon_buy_trade_route.addEventListener("click", create_proxy(on_moon_buy_trade_route))

    document.getElementById("moon-return-to-earth-button").addEventListener(
        "click", create_proxy(on_return_to_earth_from_moon)
    )

    venus_click = document.getElementById("venus-click-button")
    venus_click.innerText = "Collect Sulfur"
    venus_click.disabled = False
    venus_click.addEventListener("click", create_proxy(on_venus_click))

    venus_buy_generator = document.getElementById("venus-buy-generator-button")
    venus_buy_generator.disabled = False
    venus_buy_generator.addEventListener("click", create_proxy(on_venus_buy_generator))

    venus_buy_recycler = document.getElementById("venus-buy-recycler-button")
    venus_buy_recycler.disabled = False
    venus_buy_recycler.addEventListener("click", create_proxy(on_venus_buy_recycler))

    venus_buy_trade_route = document.getElementById("venus-buy-trade-route-button")
    venus_buy_trade_route.disabled = False
    venus_buy_trade_route.addEventListener("click", create_proxy(on_venus_buy_trade_route))

    document.getElementById("venus-return-to-earth-button").addEventListener(
        "click", create_proxy(on_return_to_earth_from_venus)
    )

    research_button = document.getElementById("fund-research-button")
    research_button.disabled = False
    research_button.addEventListener("click", create_proxy(on_fund_research))

    document.getElementById("priority-growth-button").addEventListener(
        "click", create_proxy(on_priority_growth)
    )
    document.getElementById("priority-balance-button").addEventListener(
        "click", create_proxy(on_priority_balance)
    )
    document.getElementById("priority-ecology-button").addEventListener(
        "click", create_proxy(on_priority_ecology)
    )
    document.getElementById("budget-increase-button").addEventListener(
        "click", create_proxy(on_budget_increase)
    )
    document.getElementById("budget-decrease-button").addEventListener(
        "click", create_proxy(on_budget_decrease)
    )

    document.getElementById("travel-moon-button").addEventListener("click", create_proxy(on_travel_moon))
    document.getElementById("travel-mars-button").addEventListener("click", create_proxy(on_travel_mars))
    document.getElementById("travel-venus-button").addEventListener("click", create_proxy(on_travel_venus))
    document.getElementById("travel-asteroid-belt-button").addEventListener(
        "click", create_proxy(on_travel_asteroid_belt)
    )
    document.getElementById("travel-pluto-button").addEventListener("click", create_proxy(on_travel_pluto))
    document.getElementById("travel-jupiter-moons-button").addEventListener(
        "click", create_proxy(on_travel_jupiter_moons)
    )
    document.getElementById("travel-saturn-moons-button").addEventListener(
        "click", create_proxy(on_travel_saturn_moons)
    )
    document.getElementById("return-to-earth-button").addEventListener(
        "click", create_proxy(on_return_to_earth_from_away_view)
    )

    _hide_all_views()
    document.getElementById("earth-view").hidden = False

    for planet in PLANETS:
        update_resource_display(planet)
        update_generator_display(planet)
        update_ecology_display(planet)
        update_trade_display(planet)
        update_terraform_display(planet)
    update_research_display()
    update_governor_display()
    update_travel_display()
    update_all_cross_summaries()

    setInterval(create_proxy(tick), TICK_INTERVAL_MS)


setup()
