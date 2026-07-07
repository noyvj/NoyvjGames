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
}

# Trade is a 2-planet mechanic for now (per the milestone plan); each real
# economy ships to exactly one destination — "the other one."
OTHER_PLANET = {"Earth": "Mars", "Mars": "Earth"}

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
        "trade_route_count": 0,
        "terraform_progress": 0.0,
    }
    for name in PLANETS
}

# --- global (non-planet) state ---
research_progress = 0.0
near_bodies_unlocked = False
current_planet = "Earth"
governor_priority = "balance"  # "growth" | "balance" | "ecology"
governor_budget_pct = 50.0
governor_tick_count = 0

TICK_INTERVAL_MS = 100

ECOLOGY_MAX = 100.0
LOW_ECOLOGY_THRESHOLD = 10.0
LOW_ECOLOGY_PENALTY_MULTIPLIER = 0.75

# Research isn't strictly linear — reaching a distance tier can unlock
# several bodies in parallel rather than one planet at a time.
RESEARCH_FUND_COST = 50  # flat Iron per investment, not a scaling purchase
RESEARCH_TARGET_NEAR_BODIES = 1000
NEAR_BODIES_UNLOCKS = ["Moon", "Mars"]

GOVERNOR_BUDGET_STEP = 10.0
GOVERNOR_BUDGET_MIN = 0.0
GOVERNOR_BUDGET_MAX = 100.0


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


def trade_route_cost(planet):
    cfg = PLANETS[planet]
    count = planet_state[planet]["trade_route_count"]
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
    return state["generator_count"] > 0 or state["recycler_count"] > 0 or state["trade_route_count"] > 0


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
    document.getElementById(_dom_id(planet, "trade-route-count")).innerText = str(state["trade_route_count"])
    document.getElementById(_dom_id(planet, "trade-route-rate")).innerText = str(
        round(state["trade_route_count"] * TRADE_ROUTE_RESTORE_PER_SEC, 2)
    )
    document.getElementById(_dom_id(planet, "trade-route-destination")).innerText = OTHER_PLANET[planet]
    document.getElementById(_dom_id(planet, "buy-trade-route-button")).innerText = (
        f"Build Trade Route ({trade_route_cost(planet)} {cfg['resource_name']})"
    )


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
    progress_pct = (research_progress / RESEARCH_TARGET_NEAR_BODIES) * 100
    document.getElementById("research-bar").style.width = f"{progress_pct}%"

    button = document.getElementById("fund-research-button")
    status = document.getElementById("research-status")

    if near_bodies_unlocked:
        document.getElementById("research-progress").innerText = "Unlocked"
        status.innerText = "Near Bodies unlocked: " + ", ".join(NEAR_BODIES_UNLOCKS)
        button.innerText = "Near Bodies Unlocked"
        button.disabled = True
    else:
        document.getElementById("research-progress").innerText = (
            f"{math.floor(research_progress)} / {RESEARCH_TARGET_NEAR_BODIES}"
        )
        status.innerText = ""
        button.innerText = f"Fund Research ({RESEARCH_FUND_COST} Iron)"
        button.disabled = False


def update_travel_display():
    moon_button = document.getElementById("travel-moon-button")
    mars_button = document.getElementById("travel-mars-button")
    status = document.getElementById("travel-status")
    mars_summary = document.getElementById("mars-summary")
    earth_trade = document.getElementById("earth-trade")

    if near_bodies_unlocked:
        status.innerText = "Choose a destination:"
        for button in (moon_button, mars_button):
            button.hidden = False
            button.disabled = False
        mars_summary.hidden = False
        earth_trade.hidden = False
    else:
        status.innerText = "Reach the Near Bodies tier to unlock travel."
        for button in (moon_button, mars_button):
            button.hidden = True
            button.disabled = True
        mars_summary.hidden = True
        earth_trade.hidden = True


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


def update_mars_summary_on_earth():
    # "Mars (governed)" widget shown on Earth's own view once travel is
    # unlocked — visible proof the governor keeps managing Mars while the
    # player is on Earth, symmetric to the Earth summary shown on Mars.
    state = planet_state["Mars"]
    document.getElementById("mars-summary-resource").innerText = str(math.floor(state["resource_count"] + 1e-9))
    document.getElementById("mars-summary-generators").innerText = str(state["generator_count"])
    document.getElementById("mars-summary-recyclers").innerText = str(state["recycler_count"])
    document.getElementById("mars-summary-ecology").innerText = str(round(state["ecology_health"]))


def update_earth_summary_on_mars():
    state = planet_state["Earth"]
    document.getElementById("earth-summary-resource").innerText = str(math.floor(state["resource_count"] + 1e-9))
    document.getElementById("earth-summary-generators").innerText = str(state["generator_count"])
    document.getElementById("earth-summary-recyclers").innerText = str(state["recycler_count"])
    document.getElementById("earth-summary-ecology").innerText = str(round(state["ecology_health"]))


def update_away_summary():
    # Moon has no economy of its own yet — this placeholder screen just
    # reports on Earth being governed while away, unchanged since Milestone 5.
    state = planet_state["Earth"]
    document.getElementById("away-planet-name").innerText = current_planet.upper()
    document.getElementById("away-iron").innerText = str(math.floor(state["resource_count"] + 1e-9))
    document.getElementById("away-generators").innerText = str(state["generator_count"])
    document.getElementById("away-recyclers").innerText = str(state["recycler_count"])
    document.getElementById("away-ecology").innerText = str(round(state["ecology_health"]))


def _hide_all_views():
    document.getElementById("earth-view").hidden = True
    document.getElementById("mars-view").hidden = True
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


def _buy_trade_route(planet):
    state = planet_state[planet]
    button = document.getElementById(_dom_id(planet, "buy-trade-route-button"))
    cost = trade_route_cost(planet)
    if state["resource_count"] >= cost:
        state["resource_count"] -= cost
        state["trade_route_count"] += 1
        update_resource_display(planet)
        update_trade_display(planet)
        update_terraform_display(planet)
    press_feedback(button)


def on_earth_buy_trade_route(event):
    _buy_trade_route("Earth")


def on_mars_buy_trade_route(event):
    _buy_trade_route("Mars")


def on_fund_research(event):
    global research_progress, near_bodies_unlocked
    button = document.getElementById("fund-research-button")
    earth = planet_state["Earth"]
    if not near_bodies_unlocked and earth["resource_count"] >= RESEARCH_FUND_COST:
        earth["resource_count"] -= RESEARCH_FUND_COST
        research_progress = min(research_progress + RESEARCH_FUND_COST, RESEARCH_TARGET_NEAR_BODIES)
        if research_progress >= RESEARCH_TARGET_NEAR_BODIES:
            near_bodies_unlocked = True
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


def on_travel_moon(event):
    global current_planet
    if near_bodies_unlocked:
        current_planet = "Moon"
        _hide_all_views()
        document.getElementById("away-view").hidden = False
        update_away_summary()
    press_feedback(document.getElementById("travel-moon-button"))


def on_travel_mars(event):
    global current_planet
    if near_bodies_unlocked:
        current_planet = "Mars"
        _hide_all_views()
        document.getElementById("mars-view").hidden = False
        update_resource_display("Mars")
        update_generator_display("Mars")
        update_ecology_display("Mars")
        update_earth_summary_on_mars()
    press_feedback(document.getElementById("travel-mars-button"))


def _return_to_earth():
    global current_planet
    current_planet = "Earth"
    _hide_all_views()
    document.getElementById("earth-view").hidden = False
    update_resource_display("Earth")
    update_generator_display("Earth")
    update_ecology_display("Earth")
    update_mars_summary_on_earth()


def on_return_to_earth_from_moon(event):
    _return_to_earth()
    press_feedback(document.getElementById("return-to-earth-button"))


def on_return_to_earth_from_mars(event):
    _return_to_earth()
    press_feedback(document.getElementById("mars-return-to-earth-button"))


def governor_step():
    # Autonomously manages every real economy the player is currently NOT
    # on, using the shared priority/budget config — e.g. while on Earth,
    # Mars is governed; while on Mars or the still-undeveloped Moon, Earth
    # (and Mars, if that's not where the player is either) keeps running.
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
    # Trade contributions are computed from each planet's trade_route_count
    # before anything mutates this tick, so Earth's and Mars's routes are
    # both based on pre-tick counts rather than an order-dependent mix.
    incoming_trade_restore = {
        planet: (
            planet_state[OTHER_PLANET[planet]]["trade_route_count"]
            * TRADE_ROUTE_RESTORE_PER_SEC
            * (TICK_INTERVAL_MS / 1000)
        )
        for planet in PLANETS
    }

    for planet in PLANETS:
        _simulate_planet(planet, incoming_trade_restore[planet])

    governor_step()

    for planet in PLANETS:
        update_resource_display(planet)
        update_generator_display(planet)
        update_ecology_display(planet)
        update_trade_display(planet)
        update_terraform_display(planet)

    update_mars_summary_on_earth()
    update_earth_summary_on_mars()
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
    document.getElementById("return-to-earth-button").addEventListener(
        "click", create_proxy(on_return_to_earth_from_moon)
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
    update_earth_summary_on_mars()

    setInterval(create_proxy(tick), TICK_INTERVAL_MS)


setup()
