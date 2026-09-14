import copy
import json
import math
from js import document, setInterval, setTimeout
from pyodide.ffi import create_proxy

# --- static per-planet config ---
# Every entry here is a full economy: click resource, auto-generator building,
# and a Recycler that restores ecological health — a direct reuse of the
# Milestone 2/3 systems, just reskinned per planet (the same pattern was
# reused again for the gas giant moons' Sky City building in Milestone 10;
# see GAS_GIANT_BODIES below).
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
    "AsteroidBelt": {
        "resource_name": "Platinum",
        "generator_singular": "Auto-Prospector",
        "generator_plural": "Auto-Prospectors",
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
    "Pluto": {
        "resource_name": "Tholins",
        "generator_singular": "Auto-Sublimator",
        "generator_plural": "Auto-Sublimators",
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
    "JupiterMoons": {
        "resource_name": "Helium-3",
        "generator_singular": "Auto-Skimmer",
        "generator_plural": "Auto-Skimmers",
        "generator_base_cost": 10,
        "generator_cost_growth": 1.15,
        "generator_rate": 1,
        "ecology_decay_per_generator_per_sec": 1.0,
        "recycler_base_cost": 15,
        "recycler_cost_growth": 1.15,
        "recycler_restore_per_sec": 2.0,
        "trade_route_base_cost": 30,
        "trade_route_cost_growth": 1.15,
        # Milestone 10: Sky City, a fourth building type unique to the gas
        # giant moons — see GAS_GIANT_BODIES below.
        "sky_city_local_base_cost": 50,
        "sky_city_local_cost_growth": 1.15,
        "sky_city_mars_base_cost": 20,
        "sky_city_mars_cost_growth": 1.15,
        "sky_city_production_bonus_per_city": 0.1,
    },
    "SaturnMoons": {
        "resource_name": "Methane",
        "generator_singular": "Auto-Condenser",
        "generator_plural": "Auto-Condensers",
        "generator_base_cost": 10,
        "generator_cost_growth": 1.15,
        "generator_rate": 1,
        "ecology_decay_per_generator_per_sec": 1.0,
        "recycler_base_cost": 15,
        "recycler_cost_growth": 1.15,
        "recycler_restore_per_sec": 2.0,
        "trade_route_base_cost": 30,
        "trade_route_cost_growth": 1.15,
        # Milestone 10: Sky City, a fourth building type unique to the gas
        # giant moons — see GAS_GIANT_BODIES below.
        "sky_city_local_base_cost": 50,
        "sky_city_local_cost_growth": 1.15,
        "sky_city_mars_base_cost": 20,
        "sky_city_mars_cost_growth": 1.15,
        "sky_city_production_bonus_per_city": 0.1,
    },
}

# Milestone 10: the two Far Bodies whose parent bodies are gas giants get a
# fourth building type, "Sky City" — Jupiter and Saturn themselves are not
# separate travel destinations, this is additive to the existing
# JupiterMoons/SaturnMoons economies. A Sky City costs both the local
# resource AND Mars's Water Ice, making it the payoff for the trade system
# existing at all (per the game's design doc: "gas giant buildings need Mars
# materials"). No other planet has this concept, structurally — not just
# hidden in the UI.
GAS_GIANT_BODIES = ["JupiterMoons", "SaturnMoons"]

# Ecology restored on the DESTINATION planet, per Trade Route, per second.
# Deliberately weaker than a local Recycler (2.0/s) — shipping materials
# across planets is a supplementary lever, not a replacement for local
# investment. Reviewed in the Milestone 11 balance pass against the full
# 8-planet roster: that framing still holds, so the value is unchanged.
TRADE_ROUTE_RESTORE_PER_SEC = 0.5

# Terraforming accrues only while a planet is under genuine sustained
# balance — ecology health above a real "thriving" bar (not just clear of
# the crisis threshold) AND actual economic investment present. Below that
# bar, progress simply pauses; it never regresses, per the project's
# "always recoverable, no dead-end states" rule. Rate scales with ecology
# health above the bar. Reviewed in the Milestone 11 balance pass: at
# sustained full ecology health this is 100 seconds per 10% (~1000s / ~16.7
# minutes to fully terraform a planet), and since _simulate_planet() runs
# every planet every tick regardless of current_planet, all 8 real
# economies progress in parallel once each is established — so a full
# 100%-completion win is reachable in roughly that same ~17 minutes, not
# 8x it. That's a reasonable idle-game endgame pace, so the values are
# unchanged.
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
        "trade_destination": None,  # player-selected; lazily defaulted by current_trade_destination()
        "terraform_progress": 0.0,
        # A11 (TODO.md): lifetime resource total produced by this planet's
        # own automation while it was NOT current_planet, i.e. genuinely
        # "generated by the governor while the player was elsewhere" as
        # opposed to production that happened while the player was
        # actively on that planet themselves. Never decreases.
        "governed_resource_generated": 0.0,
    }
    for name in PLANETS
}

# Sky City count only exists on the gas giant moons (Milestone 10) — every
# other planet's state dict simply has no such key, making it structurally
# impossible to buy one there rather than merely hidden in the UI.
for _gas_giant in GAS_GIANT_BODIES:
    planet_state[_gas_giant]["sky_city_count"] = 0

# --- research tiers ---
# Research isn't strictly linear — reaching a distance tier can unlock
# several bodies in parallel rather than one planet at a time. Tiers are
# researched in sequence (you can't fund tier 2 before tier 1 is done);
# "unlocks" only grants travel access — each of these bodies got its own
# economy in its own later milestone (Moon: 9b, Venus: 9c, Asteroid Belt:
# 9d, Pluto: 9e, Jupiter's Moons: 9f, Saturn's Moons: 9g), and as of 9g
# every one of them is built, so unlocking a body and it having a real
# economy happen together now. See UNDEVELOPED_BODIES below for the
# (now-empty) placeholder path that covered the gap while that was true.
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
# shared #away-view placeholder rather than a dedicated view. Empty as of
# Milestone 9g: every Far Body now has its own real economy. Left in place
# (rather than deleted) since the #away-view machinery it drives is still
# generic infrastructure other systems (e.g. update_away_summary) rely on.
UNDEVELOPED_BODIES = []

# Human-readable heading text for the away-view placeholder (internal
# identifiers avoid spaces/apostrophes so they're safe to use in DOM ids).
BODY_DISPLAY_NAMES = {}

# Mixed-case display names for any planet whose internal PLANETS/PLANETS-
# like key isn't already clean human-readable text (e.g. "AsteroidBelt" has
# no space) — used wherever a planet name is shown inline rather than as a
# standalone all-caps heading (currently: the trade destination display,
# Milestone 9f). Planets not listed here (Earth, Mars, Moon, Venus, Pluto)
# already have a clean single-word key, so they fall back to the key itself.
PLANET_DISPLAY_NAMES = {
    "AsteroidBelt": "Asteroid Belt",
    "JupiterMoons": "Jupiter's Moons",
    "SaturnMoons": "Saturn's Moons",
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
# New tracked state (ACHIEVEMENTS-SYSTEM-DESIGN.md §4's "add new state only
# where genuinely necessary" case): governor_tick_count increments on every
# tick the moment ANY other planet exists to govern, which is true from the
# very first tick of a brand-new game -- it's a measure of time elapsed, not
# of the governor having actually done anything. governor_purchase_count
# only increments inside governor_step()'s own buy branches below, i.e. the
# governor genuinely spent resources managing a world while the player was
# elsewhere -- the real thing the "Governor Appointed" achievement means to
# reward.
governor_purchase_count = 0

# --- Prestige / New Game+ (A1, TODO.md) ---
# TODO.md's own note leaned toward starting simple -- a permanent flat
# bonus on restart -- over a full skill-tree prestige layer, since the
# latter is genuinely its own milestone-sized feature. Going with that: one
# integer that only ever goes up, and one flat production multiplier
# derived from it. prestige_level survives a prestige reset by design (see
# _prestige() below) -- it's the one piece of state a prestige is FOR
# keeping, everything else about the run is what gets cleared.
prestige_level = 0
PRESTIGE_BONUS_PER_LEVEL = 0.10  # +10% resource yield (manual clicks and automation) per level


def prestige_multiplier():
    return 1 + PRESTIGE_BONUS_PER_LEVEL * prestige_level


# --- Lifetime stats (A4) + second achievement wave (A2/A13) tracked state ---
# All of these only ever go up (or, for the *_hit booleans, flip False->True
# once and stay there) -- "lifetime" means lifetime, including across a
# prestige reset (see _prestige() below, which deliberately does NOT touch
# any of this block). total_ticks is an in-game clock (ticks * 100ms), not
# a wall-clock timestamp -- deterministic under test, immune to a
# backgrounded/throttled browser tab counting differently than active play,
# and exactly what the two speedrun achievements below mean to measure
# ("how much simulated play-time did this take", not "how much real time
# has passed since first opening the page").
total_ticks = 0
total_manual_clicks = 0
lifetime_resources_mined_by_click = 0.0
lifetime_resources_generated_by_automation = 0.0
lifetime_generators_built = 0
lifetime_recyclers_built = 0
lifetime_trade_routes_built = 0
lifetime_sky_cities_built = 0

# Whether a generator has EVER existed anywhere -- from a manual buy or a
# governor purchase, either counts, and it never resets. This is what makes
# "never automated" checkable at all: generator_count alone only tells you
# the CURRENT count, which a live check can't use to mean "was ever built"
# once one is later scrapped-and-rebuilt-free by a world reset (A18).
any_generator_ever_built = False

# Second achievement wave (A2/A13) -- each a one-shot historical flag set at
# the exact moment its condition first becomes true, not a live-derived
# check, because "before you ever built a generator" and "within N minutes
# of play" both describe something about PLAY HISTORY that current state
# alone can't reconstruct after the fact (see ACHIEVEMENTS-SYSTEM-DESIGN.md
# §4's own second worked example for the same class of exception).
# Thresholds are deliberately generous per the brief's explicit constraint
# ("keep 100% achievable without extreme grinding or huge time investment")
# -- both speedrun windows assume ordinary active play, not frame-perfect
# optimization, and both pure-clicker achievements ask for a playstyle
# choice, not any grind beyond what the base game already asks of a
# manual-only playthrough.
QUICK_START_TICKS = 6_000  # 10 minutes of ticks
SWIFT_EXPANSION_TICKS = 18_000  # 30 minutes of ticks
MANUAL_LABOR_THRESHOLD = 100  # Earth Iron, by hand, before any generator ever existed

quick_start_hit = False
swift_expansion_hit = False
manual_labor_hit = False
off_the_grid_hit = False

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


def _cycle_trade_destination(planet):
    others = other_real_planets(planet)
    if others:
        current = current_trade_destination(planet)
        next_index = (others.index(current) + 1) % len(others) if current in others else 0
        planet_state[planet]["trade_destination"] = others[next_index]
        update_trade_display(planet)
    press_feedback(document.getElementById(_dom_id(planet, "cycle-trade-destination-button")))


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


def sky_city_local_cost(planet):
    cfg = PLANETS[planet]
    count = planet_state[planet]["sky_city_count"]
    return math.ceil(cfg["sky_city_local_base_cost"] * (cfg["sky_city_local_cost_growth"] ** count))


def sky_city_mars_cost(planet):
    cfg = PLANETS[planet]
    count = planet_state[planet]["sky_city_count"]
    return math.ceil(cfg["sky_city_mars_base_cost"] * (cfg["sky_city_mars_cost_growth"] ** count))


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
    bonus_pct = round(state["sky_city_count"] * cfg["sky_city_production_bonus_per_city"] * 100)

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

        if index < completed_tiers:
            tier_status = "completed"
            status_text = "Completed"
        elif index == completed_tiers:
            tier_status = "current"
            status_text = "In Progress"
        else:
            tier_status = "locked"
            status_text = "Locked"

        node = document.createElement("div")
        node.className = f"research-tree-node research-tree-node--{tier_status}"

        name = document.createElement("p")
        name.className = "research-tree-node-name"
        name.innerText = tier["name"]
        node.appendChild(name)

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


def update_travel_display():
    for body, button_id in TRAVEL_BUTTON_ID.items():
        button = document.getElementById(button_id)
        unlocked = body in unlocked_bodies
        button.hidden = not unlocked
        button.disabled = not unlocked

    # Every "<target> (governed)" cross-summary widget's own hidden state is
    # handled generically in update_cross_summary() instead (so every view
    # gets the same not-yet-unlocked gating Earth's view always had, not
    # just Earth's) — earth-trade is a separate concern (the Trade Route
    # section itself, not a cross-summary widget) so it's still handled here.
    earth_trade = document.getElementById("earth-trade")
    earth_trade.hidden = "Mars" not in unlocked_bodies

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


def update_win_display():
    # Milestone 11: the win condition is recomputed fresh every call rather
    # than tracked with a separate "achieved" flag -- simpler than keeping a
    # flag in sync, and necessary now that terraform_progress CAN regress
    # again: A18's "reset this world" and A1's prestige both zero a
    # planet's terraform_progress back out on purpose. The banner is a
    # sibling of every per-planet view in the HTML (not inside any of
    # them), so it stays visible regardless of current_planet and isn't
    # touched by _hide_all_views().
    complete = all(planet_state[p]["terraform_progress"] >= TERRAFORM_MAX for p in PLANETS)
    document.getElementById("win-banner").hidden = not complete

    readout = document.getElementById("prestige-level-readout")
    if prestige_level > 0:
        readout.innerText = (
            f"Prestige Level {prestige_level} — "
            f"+{round(PRESTIGE_BONUS_PER_LEVEL * prestige_level * 100)}% resource yield"
        )
    else:
        readout.innerText = "Prestige into a New Game+ for a permanent resource bonus."


# ===========================================================================
# Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md) — SOL is the reference
# integration for the hub-wide achievements framework.
# ===========================================================================
#
# Every achievement's earned status is a pure function of state that already
# exists elsewhere in this module (planet_state, unlocked_bodies,
# completed_tiers, ...), recomputed fresh on every call — never a separately
# hand-maintained "earned" flag that could drift out of sync with the state
# that actually justifies it (same discipline Le Champ de Mots' own
# achievements established: "derive, don't track"). Two small exceptions
# needed one new piece of genuinely new tracked state each, both added
# defensively (safe default, merged in on load, never crashes an older save
# missing the field):
#
# - `visited_bodies` just below: SOL has no existing record of which worlds
#   a player has ever physically traveled to (current_planet only remembers
#   *where you are now*, and unlocked_bodies means research access, not an
#   actual visit — a player can unlock every Far Body and still never have
#   flown to one), so two achievements here ("Off-World", "Grand Tour")
#   genuinely need it.
# - `governor_purchase_count`, defined next to `governor_tick_count` at the
#   top of this module and incremented inside governor_step()'s own buy
#   branches: `governor_tick_count` increments the instant ANY other planet
#   exists to govern, which is true from the very first tick of a brand-new
#   game — it measures ticks elapsed, not the governor having actually
#   bought anything. "Governor Appointed" needs the latter, so it checks
#   `governor_purchase_count` instead — caught during this feature's own
#   live verification pass, where a fresh, untouched game showed the
#   achievement already earned after under a second of real time.
#
ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    """Same loading contract Le Champ de Mots' game.py established for its
    own static JSON assets (see that game's `_read_json_asset()`): the
    page's boot script fetches achievements.json and hands it to Python as
    a window global before this file runs; the pytest harness's fake `js`
    module simply has no such attribute, so this falls through to reading
    the file straight off disk, which keeps the module importable outside
    a real browser."""
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        js = None

    raw = getattr(js, "ACHIEVEMENTS_JSON", None) if js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 — only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, ACHIEVEMENTS_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Defensive per Le Champ de Mots' own live-incident writeup: the real
# Pyodide runtime executes this file's fetched text via
# `pyodide.runPythonAsync(code)`, which never defines `__file__` the way a
# normal file-based import does -- if `_read_achievements_json()`'s
# window-global read ever comes back empty (a boot-script regression, a
# renamed global, a fetch failure), its filesystem fallback crashes with a
# bare, uncaught `NameError` that takes down this ENTIRE module import,
# not just achievements -- exactly the bug that silently broke Le Champ de
# Mots' whole page for every player until it was diagnosed live. Achievements
# are additive, not core to SOL's own gameplay, so this degrades to "no
# achievements catalog" instead, the same posture that game's own
# supplementary-notes loading now takes.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []

# New tracked state (see the module docstring above): every body the player
# has ever actually traveled to, Earth included from the start since that's
# where every game begins. Mutated in place (never reassigned) from each
# on_travel_* handler below via `_mark_visited()`, so no `global` declaration
# is needed at those call sites — only deserialize_state() below, which does
# reassign it wholesale from a loaded save, needs one.
visited_bodies = {"Earth"}

RESOURCE_BARON_THRESHOLD = 1_000_000
ECOLOGICAL_BALANCE_MIN_HEALTH = 95.0
TRADE_NETWORK_MIN_ROUTES = 5
PLANETARY_RENAISSANCE_MIN_TERRAFORMED = 4


def _total_trade_routes():
    return sum(sum(state["trade_routes"].values()) for state in planet_state.values())


def _terraformed_planet_count():
    return sum(1 for state in planet_state.values() if state["terraform_progress"] >= TERRAFORM_MAX)


def _max_single_resource():
    return max((state["resource_count"] for state in planet_state.values()), default=0.0)


# Each checker is a zero-argument predicate read fresh off live state —
# nothing here is ever cached or hand-flagged. "Earth" counts as always
# unlocked and always visited from the start (see PLANETS/visited_bodies
# above), so every len(PLANETS)-based target below is expressed relative to
# that the same way update_cross_summary() already treats Earth as a given.
ACHIEVEMENT_CHECKS = {
    "first_ore": lambda: planet_state["Earth"]["resource_count"] >= 1,
    "automated": lambda: planet_state["Earth"]["generator_count"] >= 1,
    "recycler_online": lambda: any(state["recycler_count"] >= 1 for state in planet_state.values()),
    "off_world": lambda: len(visited_bodies) >= 2,
    "trade_route_established": lambda: any(state["trade_routes"] for state in planet_state.values()),
    "tier_one_cleared": lambda: completed_tiers >= 1,
    "solar_system_unlocked": lambda: len(unlocked_bodies) >= len(PLANETS) - 1,
    "tier_two_cleared": lambda: completed_tiers >= len(RESEARCH_TIERS),
    "grand_tour": lambda: len(visited_bodies) >= len(PLANETS),
    "governor_appointed": lambda: governor_purchase_count >= 1,
    "sky_city_founder": lambda: any(
        planet_state[p].get("sky_city_count", 0) >= 1 for p in GAS_GIANT_BODIES
    ),
    "trade_network": lambda: _total_trade_routes() >= TRADE_NETWORK_MIN_ROUTES,
    "ecological_balance": lambda: any(
        state["generator_count"] >= 1 and state["ecology_health"] >= ECOLOGICAL_BALANCE_MIN_HEALTH
        for state in planet_state.values()
    ),
    "resource_baron": lambda: _max_single_resource() >= RESOURCE_BARON_THRESHOLD,
    "terraformer": lambda: _terraformed_planet_count() >= 1,
    "eight_economies": lambda: all(state["generator_count"] >= 1 for state in planet_state.values()),
    "planetary_renaissance": lambda: _terraformed_planet_count() >= PLANETARY_RENAISSANCE_MIN_TERRAFORMED,
    "full_system_terraformed": lambda: _terraformed_planet_count() >= len(PLANETS),
    # Second achievement wave (A2/A13) -- all four are one-shot historical
    # flags (module-level globals near total_ticks/any_generator_ever_built
    # above), not live-derived from current state, because "within N
    # minutes" and "before a generator ever existed" both describe
    # something about PLAY HISTORY a live check can't reconstruct after
    # the fact (see that block's own comment for the full reasoning).
    "quick_start": lambda: quick_start_hit,
    "swift_expansion": lambda: swift_expansion_hit,
    "manual_labor": lambda: manual_labor_hit,
    "off_the_grid": lambda: off_the_grid_hit,
}

# Progress readouts, only for achievements with a natural numeric scale-up —
# a plain earned/not-yet is the honest shape for the rest, rather than
# inventing fractional progress for a one-shot milestone like "build your
# first Recycler somewhere".
ACHIEVEMENT_PROGRESS = {
    "solar_system_unlocked": lambda: (len(unlocked_bodies), len(PLANETS) - 1),
    "grand_tour": lambda: (len(visited_bodies), len(PLANETS)),
    "tier_two_cleared": lambda: (completed_tiers, len(RESEARCH_TIERS)),
    "trade_network": lambda: (_total_trade_routes(), TRADE_NETWORK_MIN_ROUTES),
    "resource_baron": lambda: (math.floor(_max_single_resource()), RESOURCE_BARON_THRESHOLD),
    "planetary_renaissance": lambda: (_terraformed_planet_count(), PLANETARY_RENAISSANCE_MIN_TERRAFORMED),
    "full_system_terraformed": lambda: (_terraformed_planet_count(), len(PLANETS)),
}


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field (ACHIEVEMENTS-SYSTEM-DESIGN.md). Always
    recomputed, never itself a save input."""
    return [entry["id"] for entry in ACHIEVEMENTS if ACHIEVEMENT_CHECKS[entry["id"]]()]


def achievements_summary():
    """The full catalog, in order, each entry annotated with whether it's
    currently earned and (where one exists) a live progress readout — the
    shape the in-game panel wants without re-deriving it from ACHIEVEMENTS +
    ACHIEVEMENT_CHECKS + ACHIEVEMENT_PROGRESS itself."""
    earned_ids = set(achievement_ids_earned())
    summary = []
    for entry in ACHIEVEMENTS:
        progress_fn = ACHIEVEMENT_PROGRESS.get(entry["id"])
        summary.append(
            {
                "id": entry["id"],
                "label": entry["label"],
                "description": entry["description"],
                "earned": entry["id"] in earned_ids,
                "progress": progress_fn() if progress_fn else None,
            }
        )
    return summary


achievements_open = False

# Achievements retrofit (TODO.md "roll achievements out everywhere" — SOL's
# own toast/hub-link retrofit, built after the base 18-achievement rollout
# shipped): a snapshot of which achievement ids were already earned as of
# the last full render, so tick()'s live check can tell "newly earned this
# tick" apart from "already earned before this page load/save load" and
# only toast for the former. Seeded (never diffed-against-empty) inside
# _full_render() -- both the fresh-game path (setup()) and the loaded-save
# path (load_state()/load_save_state_json()) call _full_render(), so a save
# that already has 12 achievements earned never floods the player with 12
# toasts the instant it loads.
_achievements_seen_ids = set()


def _seed_achievement_toast_baseline():
    global _achievements_seen_ids
    _achievements_seen_ids = set(achievement_ids_earned())


def _display_toast(message):
    # Shared by both the achievement-unlock toast and the welcome-back toast
    # (A3) -- same fixed-position element, same show-then-auto-hide timing,
    # just different message text. A second toast firing before the first's
    # timeout clears simply replaces the visible text and restarts the
    # timer's effect (the old timeout still fires and finds the toast
    # already hidden-by-the-new-one's-own-timeout is harmless: both timeouts
    # just set hidden = True).
    toast = document.getElementById("achievement-toast")
    text = document.getElementById("achievement-toast-text")
    text.innerText = message
    toast.hidden = False
    toast.classList.add("visible")

    def _hide(*args):
        toast.hidden = True
        toast.classList.remove("visible")
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, 4000)


def _check_new_achievements_for_toast():
    """Called every tick(): compares the live earned set against the last
    snapshot, and pops a toast for anything newly earned since then. Never
    called from _full_render() itself -- see _seed_achievement_toast_baseline
    above for why a load must never diff against a stale/empty baseline."""
    global _achievements_seen_ids
    earned_now = set(achievement_ids_earned())
    newly = earned_now - _achievements_seen_ids
    if newly:
        by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
        labels = [by_id[aid]["label"] for aid in newly if aid in by_id]
        if labels:
            if len(labels) == 1:
                _display_toast(f"🏆 Achievement unlocked: {labels[0]}")
            else:
                _display_toast(f"🏆 {len(labels)} achievements unlocked: " + ", ".join(labels))
    _achievements_seen_ids = earned_now


def _mark_visited(planet):
    visited_bodies.add(planet)


def on_toggle_achievements(event=None):
    global achievements_open
    achievements_open = not achievements_open
    update_achievements_display()


def update_achievements_display():
    toggle = document.getElementById("achievements-toggle-button")
    panel = document.getElementById("achievements-panel")
    earned_count = len(achievement_ids_earned())
    toggle.innerText = (
        f"Hide Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
        if achievements_open
        else f"🏆 Achievements ({earned_count}/{len(ACHIEVEMENTS)})"
    )
    panel.hidden = not achievements_open
    if not achievements_open:
        return

    panel.innerHTML = ""
    for entry in achievements_summary():
        card = document.createElement("div")
        card.className = "achievement-card achievement-card--earned" if entry["earned"] else "achievement-card"

        label = document.createElement("p")
        label.className = "achievement-card-label"
        label.innerText = f"🏆 {entry['label']}" if entry["earned"] else entry["label"]
        card.appendChild(label)

        description = document.createElement("p")
        description.className = "achievement-card-description"
        description.innerText = entry["description"]
        card.appendChild(description)

        if not entry["earned"] and entry["progress"] is not None:
            current, target = entry["progress"]
            progress = document.createElement("p")
            progress.className = "achievement-card-progress"
            progress.innerText = f"{current} of {target}"
            card.appendChild(progress)

        panel.appendChild(card)

    # Retrofit: a link out to the hub-wide achievements dashboard
    # (root index.html's #account-achievements-dashboard, ACHIEVEMENTS-
    # SYSTEM-DESIGN.md §5) — signed-in players can see SOL's progress
    # alongside every other game's there. Relative path, no leading "/"
    # (site-level milestone 7's GitHub Pages subpath fix), rebuilt each
    # open alongside the cards since the whole panel is cleared first.
    hub_link = document.createElement("a")
    hub_link.innerText = "View the hub-wide achievements dashboard →"
    hub_link.href = "../../index.html#account-achievements-dashboard"
    hub_link.className = "achievements-hub-link"
    panel.appendChild(hub_link)


# ===========================================================================
# Governor Report (A11) — a visible "governor efficiency" readout.
# ===========================================================================
# Efficiency here means the same production_multiplier() every planet's own
# automation already runs on every tick (100% at healthy ecology, 75% under
# the 25%-output penalty, 0% during a full collapse) -- surfaced explicitly
# per governed world rather than left implicit in how fast its resource
# count climbs. "Generated while governed" is governed_resource_generated
# (see planet_state's own comment above and _simulate_planet), a lifetime
# total that only counts production that happened while that world was NOT
# current_planet, i.e. genuinely produced by the governor while the player
# was elsewhere.
governor_report_open = False


def on_toggle_governor_report(event=None):
    global governor_report_open
    governor_report_open = not governor_report_open
    update_governor_report_display()


def update_governor_report_display():
    toggle = document.getElementById("governor-report-toggle-button")
    panel = document.getElementById("governor-report-panel")
    toggle.innerText = "Hide Governor Report" if governor_report_open else "🎛️ Governor Report"
    panel.hidden = not governor_report_open
    if not governor_report_open:
        return

    panel.innerHTML = ""

    intro = document.createElement("p")
    intro.className = "governor-report-intro"
    intro.innerText = (
        f"Priority: {governor_priority.title()} · Budget: {round(governor_budget_pct)}% "
        "of each governed world's own resources"
    )
    panel.appendChild(intro)

    governed_planets = [planet for planet in PLANETS if planet != current_planet]
    total_generated = 0.0
    for planet in governed_planets:
        state = planet_state[planet]
        generated = state["governed_resource_generated"]
        total_generated += generated

        card = document.createElement("div")
        card.className = "governor-report-card"

        name = document.createElement("p")
        name.className = "governor-report-card-name"
        name.innerText = PLANET_DISPLAY_NAMES.get(planet, planet)
        card.appendChild(name)

        efficiency = document.createElement("p")
        efficiency.className = "governor-report-card-efficiency"
        if state["generator_count"] == 0:
            efficiency.innerText = "No automation yet"
        else:
            efficiency.innerText = f"Efficiency: {round(production_multiplier(planet) * 100)}%"
        card.appendChild(efficiency)

        generated_el = document.createElement("p")
        generated_el.className = "governor-report-card-generated"
        generated_el.innerText = (
            f"Generated while governed: {math.floor(generated + 1e-9)} {PLANETS[planet]['resource_name']}"
        )
        card.appendChild(generated_el)

        panel.appendChild(card)

    if not governed_planets:
        empty = document.createElement("p")
        empty.className = "governor-report-empty"
        empty.innerText = "No other worlds exist yet for the Governor to manage."
        panel.appendChild(empty)
        return

    total = document.createElement("p")
    total.className = "governor-report-total"
    total.innerText = f"Total generated across every governed world: {math.floor(total_generated + 1e-9)}"
    panel.appendChild(total)


# ===========================================================================
# Lifetime Stats + Shareable Summary Card (A4 + A8) — one consolidated
# toolbar panel rather than two, since both are read-only "look back at
# your progress" views and the toolbar already carries four other buttons.
# ===========================================================================
stats_open = False


def on_toggle_stats(event=None):
    global stats_open
    stats_open = not stats_open
    update_stats_panel_display()


def _lifetime_playtime_seconds():
    # total_ticks is in-game simulated time (ticks * TICK_INTERVAL_MS), not
    # a wall-clock reading -- see its own module-level comment for why.
    return total_ticks * (TICK_INTERVAL_MS / 1000)


def _format_duration(seconds):
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def build_share_card_text():
    """A8: a shareable "my solar system" end-state summary card. Plain
    text, not a rendered image -- this project has no asset/image pipeline
    (A6's own build note), and plain text is trivially "shareable" (paste
    it anywhere) without inventing one just for this."""
    terraform_values = [planet_state[p]["terraform_progress"] for p in PLANETS]
    avg_terraform = sum(terraform_values) / len(terraform_values)
    lines = [
        "🌌 My Solar System — SOL",
        f"Worlds visited: {len(visited_bodies)}/{len(PLANETS)}",
        f"Worlds unlocked: {min(len(unlocked_bodies) + 1, len(PLANETS))}/{len(PLANETS)}",
        f"Average terraforming: {round(avg_terraform)}%",
        f"Fully terraformed worlds: {_terraformed_planet_count()}/{len(PLANETS)}",
        f"Achievements: {len(achievement_ids_earned())}/{len(ACHIEVEMENTS)}",
        f"Prestige level: {prestige_level}",
    ]
    return "\n".join(lines)


def on_copy_share_card(event=None):
    # Clipboard access is browser-only (no navigator in the pytest fake-DOM
    # harness) -- guarded the same lazy-import-and-degrade way
    # _read_achievements_json() guards its own browser-only access, so this
    # stays importable/callable under test even though the actual copy
    # can't happen there.
    text = build_share_card_text()
    status = document.getElementById("copy-share-card-status")
    try:
        import js  # noqa: PLC0415

        js.navigator.clipboard.writeText(text)
        status.innerText = "Copied to clipboard!"
    except (ImportError, AttributeError):
        status.innerText = "Couldn't access the clipboard — copy the text above manually."
    press_feedback(document.getElementById("copy-share-card-button"))


def update_stats_panel_display():
    toggle = document.getElementById("stats-toggle-button")
    panel = document.getElementById("stats-panel")
    toggle.innerText = "Hide Stats & Share" if stats_open else "📊 Stats & Share"
    panel.hidden = not stats_open
    if not stats_open:
        return

    content = document.getElementById("stats-panel-content")
    content.innerHTML = ""

    heading = document.createElement("p")
    heading.className = "stats-panel-heading"
    heading.innerText = "Lifetime Stats"
    content.appendChild(heading)

    stat_lines = [
        ("Time played", _format_duration(_lifetime_playtime_seconds())),
        ("Manual clicks", str(total_manual_clicks)),
        ("Resources mined by hand", str(math.floor(lifetime_resources_mined_by_click + 1e-9))),
        (
            "Resources generated by automation",
            str(math.floor(lifetime_resources_generated_by_automation + 1e-9)),
        ),
        ("Generators built", str(lifetime_generators_built)),
        ("Recyclers built", str(lifetime_recyclers_built)),
        ("Trade routes built", str(lifetime_trade_routes_built)),
        ("Sky cities built", str(lifetime_sky_cities_built)),
        ("Research tiers completed", f"{completed_tiers}/{len(RESEARCH_TIERS)}"),
        ("Worlds visited", f"{len(visited_bodies)}/{len(PLANETS)}"),
        ("Achievements earned", f"{len(achievement_ids_earned())}/{len(ACHIEVEMENTS)}"),
        ("Prestige level", str(prestige_level)),
    ]
    for label, value in stat_lines:
        row = document.createElement("p")
        row.className = "stats-panel-row"
        row.innerText = f"{label}: {value}"
        content.appendChild(row)

    # The share card text (a static <pre>) and its Copy button live outside
    # this rebuilt content div (index.html) so the button's own click
    # listener is bound exactly once in setup() -- rebuilding it every tick
    # the panel is open, the same way the rows above are rebuilt, would
    # leak a new create_proxy() listener each time (press_feedback's own
    # module docstring already flags this exact class of leak).
    document.getElementById("share-card-text").innerText = build_share_card_text()


def update_cross_summary(viewer, target):
    # Shows `target`'s governed stats on `viewer`'s own view — e.g. Earth's
    # view shows a "Mars (governed)" widget, Mars's view shows an "Earth
    # (governed)" widget, and so on for every pair of real economies, once
    # there are more than two. Ids are viewer-prefixed (via _dom_id) so each
    # view's widget for the same target doesn't collide with any other
    # view's widget for that same target.
    #
    # The widget is hidden until `target` is unlocked (Earth is always
    # treated as unlocked, since it's the home planet and never appears in
    # unlocked_bodies) — enforced here so every view is consistent, not just
    # Earth's own (which used to be the only one gated, via
    # update_travel_display(), leaking every other view's not-yet-unlocked
    # bodies' names/existence).
    state = planet_state[target]

    def widget_id(field):
        return _dom_id(viewer, f"{target.lower()}-summary-{field}")

    document.getElementById(_dom_id(viewer, f"{target.lower()}-summary")).hidden = (
        target != "Earth" and target not in unlocked_bodies
    )
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
    document.getElementById("asteroidbelt-view").hidden = True
    document.getElementById("pluto-view").hidden = True
    document.getElementById("jupitermoons-view").hidden = True
    document.getElementById("saturnmoons-view").hidden = True
    document.getElementById("away-view").hidden = True


def press_feedback(button):
    # Called on essentially every player interaction (every click, buy,
    # travel, governor, and destination-cycle button), so the one-shot
    # setTimeout proxy created here must be destroyed once it fires —
    # otherwise each press leaks a PyProxy for the rest of the session,
    # a slow memory leak that never gets cleaned up on its own since
    # Pyodide can't garbage-collect a JsProxy-wrapped Python callable
    # until .destroy() is called explicitly.
    button.classList.add("pressed")

    def _clear(*args):
        button.classList.remove("pressed")
        proxy.destroy()
    proxy = create_proxy(_clear)
    setTimeout(proxy, 120)


def _mine(planet):
    # Manual mining always works, even during an ecological collapse that
    # halts automated production on that planet — otherwise a player who
    # lets health hit 0% with no resources banked could get permanently
    # stuck with no way to earn the resources needed to build a recovery
    # Recycler. Per the project's "no dead-end/unwinnable states" balance
    # rule, there must always be a lever.
    global total_manual_clicks, lifetime_resources_mined_by_click, manual_labor_hit
    state = planet_state[planet]
    gained = 1 * prestige_multiplier()
    state["resource_count"] += gained
    total_manual_clicks += 1
    lifetime_resources_mined_by_click += gained
    if (
        planet == "Earth"
        and not manual_labor_hit
        and not any_generator_ever_built
        and state["resource_count"] >= MANUAL_LABOR_THRESHOLD
    ):
        manual_labor_hit = True
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


def on_asteroid_belt_click(event):
    _mine("AsteroidBelt")


def on_pluto_click(event):
    _mine("Pluto")


def on_jupiter_moons_click(event):
    _mine("JupiterMoons")


def on_saturn_moons_click(event):
    _mine("SaturnMoons")


def _buy_generator(planet):
    global lifetime_generators_built, any_generator_ever_built
    state = planet_state[planet]
    button = document.getElementById(_dom_id(planet, "buy-generator-button"))
    cost = generator_cost(planet)
    if state["resource_count"] >= cost:
        state["resource_count"] -= cost
        state["generator_count"] += 1
        lifetime_generators_built += 1
        any_generator_ever_built = True
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


def on_asteroid_belt_buy_generator(event):
    _buy_generator("AsteroidBelt")


def on_pluto_buy_generator(event):
    _buy_generator("Pluto")


def on_jupiter_moons_buy_generator(event):
    _buy_generator("JupiterMoons")


def on_saturn_moons_buy_generator(event):
    _buy_generator("SaturnMoons")


def _buy_recycler(planet):
    global lifetime_recyclers_built
    state = planet_state[planet]
    button = document.getElementById(_dom_id(planet, "buy-recycler-button"))
    cost = recycler_cost(planet)
    if state["resource_count"] >= cost:
        state["resource_count"] -= cost
        state["recycler_count"] += 1
        lifetime_recyclers_built += 1
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


def on_asteroid_belt_buy_recycler(event):
    _buy_recycler("AsteroidBelt")


def on_pluto_buy_recycler(event):
    _buy_recycler("Pluto")


def on_jupiter_moons_buy_recycler(event):
    _buy_recycler("JupiterMoons")


def on_saturn_moons_buy_recycler(event):
    _buy_recycler("SaturnMoons")


def _buy_trade_route(planet):
    global lifetime_trade_routes_built
    state = planet_state[planet]
    button = document.getElementById(_dom_id(planet, "buy-trade-route-button"))
    destination = current_trade_destination(planet)
    if destination is not None:
        cost = trade_route_cost(planet, destination)
        if state["resource_count"] >= cost:
            state["resource_count"] -= cost
            state["trade_routes"][destination] = state["trade_routes"].get(destination, 0) + 1
            lifetime_trade_routes_built += 1
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


def on_asteroid_belt_buy_trade_route(event):
    _buy_trade_route("AsteroidBelt")


def on_pluto_buy_trade_route(event):
    _buy_trade_route("Pluto")


def on_jupiter_moons_buy_trade_route(event):
    _buy_trade_route("JupiterMoons")


def on_saturn_moons_buy_trade_route(event):
    _buy_trade_route("SaturnMoons")


def _buy_sky_city(planet):
    # Milestone 10: only ever called for JupiterMoons/SaturnMoons. Requires
    # BOTH the local resource AND Mars's Water Ice — the trade system's
    # payoff. Press feedback always fires; state only changes if both costs
    # are affordable.
    global lifetime_sky_cities_built
    state = planet_state[planet]
    mars_state = planet_state["Mars"]
    button = document.getElementById(_dom_id(planet, "buy-sky-city-button"))
    local_cost = sky_city_local_cost(planet)
    mars_cost = sky_city_mars_cost(planet)
    if state["resource_count"] >= local_cost and mars_state["resource_count"] >= mars_cost:
        state["resource_count"] -= local_cost
        mars_state["resource_count"] -= mars_cost
        state["sky_city_count"] += 1
        lifetime_sky_cities_built += 1
        update_resource_display(planet)
        update_resource_display("Mars")
        update_sky_city_display(planet)
        update_terraform_display(planet)
    press_feedback(button)


def on_jupiter_moons_buy_sky_city(event):
    _buy_sky_city("JupiterMoons")


def on_saturn_moons_buy_sky_city(event):
    _buy_sky_city("SaturnMoons")


def on_earth_cycle_trade_destination(event):
    _cycle_trade_destination("Earth")


def on_mars_cycle_trade_destination(event):
    _cycle_trade_destination("Mars")


def on_moon_cycle_trade_destination(event):
    _cycle_trade_destination("Moon")


def on_venus_cycle_trade_destination(event):
    _cycle_trade_destination("Venus")


def on_asteroid_belt_cycle_trade_destination(event):
    _cycle_trade_destination("AsteroidBelt")


def on_pluto_cycle_trade_destination(event):
    _cycle_trade_destination("Pluto")


def on_jupiter_moons_cycle_trade_destination(event):
    _cycle_trade_destination("JupiterMoons")


def on_saturn_moons_cycle_trade_destination(event):
    _cycle_trade_destination("SaturnMoons")


def on_fund_research(event):
    global research_progress, completed_tiers, quick_start_hit, swift_expansion_hit, off_the_grid_hit
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
            update_all_cross_summaries()
            update_research_tree_display()
            # Second achievement wave (A2/A13) -- checked at the exact
            # moment each tier completes, since that's the one instant
            # both "how many ticks has this playthrough taken" and
            # "has a generator ever existed anywhere" are both meaningful
            # to compare against a fixed line.
            if completed_tiers == 1:
                if total_ticks <= QUICK_START_TICKS:
                    quick_start_hit = True
                if not any_generator_ever_built:
                    off_the_grid_hit = True
            if completed_tiers == len(RESEARCH_TIERS) and total_ticks <= SWIFT_EXPANSION_TICKS:
                swift_expansion_hit = True
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
    if "Moon" in unlocked_bodies:
        current_planet = "Moon"
        _mark_visited("Moon")
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
        _mark_visited("Venus")
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
    global current_planet
    if "AsteroidBelt" in unlocked_bodies:
        current_planet = "AsteroidBelt"
        _mark_visited("AsteroidBelt")
        _hide_all_views()
        document.getElementById("asteroidbelt-view").hidden = False
        update_resource_display("AsteroidBelt")
        update_generator_display("AsteroidBelt")
        update_ecology_display("AsteroidBelt")
        update_trade_display("AsteroidBelt")
        update_terraform_display("AsteroidBelt")
        update_all_cross_summaries()
    press_feedback(document.getElementById("travel-asteroid-belt-button"))


def on_travel_pluto(event):
    global current_planet
    if "Pluto" in unlocked_bodies:
        current_planet = "Pluto"
        _mark_visited("Pluto")
        _hide_all_views()
        document.getElementById("pluto-view").hidden = False
        update_resource_display("Pluto")
        update_generator_display("Pluto")
        update_ecology_display("Pluto")
        update_trade_display("Pluto")
        update_terraform_display("Pluto")
        update_all_cross_summaries()
    press_feedback(document.getElementById("travel-pluto-button"))


def on_travel_jupiter_moons(event):
    global current_planet
    if "JupiterMoons" in unlocked_bodies:
        current_planet = "JupiterMoons"
        _mark_visited("JupiterMoons")
        _hide_all_views()
        document.getElementById("jupitermoons-view").hidden = False
        update_resource_display("JupiterMoons")
        update_generator_display("JupiterMoons")
        update_ecology_display("JupiterMoons")
        update_trade_display("JupiterMoons")
        update_sky_city_display("JupiterMoons")
        update_terraform_display("JupiterMoons")
        update_all_cross_summaries()
    press_feedback(document.getElementById("travel-jupiter-moons-button"))


def on_travel_saturn_moons(event):
    global current_planet
    if "SaturnMoons" in unlocked_bodies:
        current_planet = "SaturnMoons"
        _mark_visited("SaturnMoons")
        _hide_all_views()
        document.getElementById("saturnmoons-view").hidden = False
        update_resource_display("SaturnMoons")
        update_generator_display("SaturnMoons")
        update_ecology_display("SaturnMoons")
        update_trade_display("SaturnMoons")
        update_sky_city_display("SaturnMoons")
        update_terraform_display("SaturnMoons")
        update_all_cross_summaries()
    press_feedback(document.getElementById("travel-saturn-moons-button"))


def on_travel_mars(event):
    global current_planet
    if "Mars" in unlocked_bodies:
        current_planet = "Mars"
        _mark_visited("Mars")
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


def on_return_to_earth_from_asteroid_belt(event):
    _return_to_earth()
    press_feedback(document.getElementById("asteroidbelt-return-to-earth-button"))


def on_return_to_earth_from_pluto(event):
    _return_to_earth()
    press_feedback(document.getElementById("pluto-return-to-earth-button"))


def on_return_to_earth_from_jupiter_moons(event):
    _return_to_earth()
    press_feedback(document.getElementById("jupitermoons-return-to-earth-button"))


def on_return_to_earth_from_saturn_moons(event):
    _return_to_earth()
    press_feedback(document.getElementById("saturnmoons-return-to-earth-button"))


# --- Reset this world only (A18) ---
# Distinct from a full save wipe (which the save-widget's own UI already
# offers): this only clears ONE planet's own economy -- resources,
# buildings, ecology, trade routes, terraforming -- back to its fresh-game
# defaults. Research/unlocked_bodies/visited_bodies/achievements/current_
# planet are all untouched, since re-locking a world you already unlocked
# via research (or "unvisiting" it) isn't what "reset this world" means.
def _confirm(message):
    # Lazy import, same convention as _read_achievements_json()'s own
    # optional `import js` -- a plain top-level `from js import confirm`
    # would bind this module's own name to whatever js.confirm WAS at
    # import time, which the pytest fake-DOM harness can no longer swap out
    # afterward (game_env.set_confirm_response() replaces
    # sys.modules["js"].confirm, not this module's own already-bound
    # copy of it). Importing `js` fresh here and reading its `.confirm`
    # attribute live sidesteps that entirely, in both the real browser and
    # under test.
    import js  # noqa: PLC0415

    return js.confirm(message)


def _fresh_planet_state(planet):
    fresh = {
        "resource_count": 0.0,
        "generator_count": 0,
        "recycler_count": 0,
        "ecology_health": 100.0,
        "trade_routes": {},
        "trade_destination": None,
        "terraform_progress": 0.0,
        "governed_resource_generated": 0.0,
    }
    if planet in GAS_GIANT_BODIES:
        fresh["sky_city_count"] = 0
    return fresh


def _reset_world(planet):
    display_name = PLANET_DISPLAY_NAMES.get(planet, planet)
    if not _confirm(
        f"Reset {display_name}? This clears its resources, buildings, ecology, "
        "trade routes, and terraforming progress. Research, travel, and "
        "achievements are not affected. This cannot be undone."
    ):
        return
    planet_state[planet] = _fresh_planet_state(planet)
    update_resource_display(planet)
    update_generator_display(planet)
    update_ecology_display(planet)
    update_trade_display(planet)
    if planet in GAS_GIANT_BODIES:
        update_sky_city_display(planet)
    update_terraform_display(planet)
    update_all_cross_summaries()
    update_win_display()
    press_feedback(document.getElementById(_dom_id(planet, "reset-world-button")))


def on_reset_earth(event):
    _reset_world("Earth")


def on_reset_mars(event):
    _reset_world("Mars")


def on_reset_moon(event):
    _reset_world("Moon")


def on_reset_venus(event):
    _reset_world("Venus")


def on_reset_asteroid_belt(event):
    _reset_world("AsteroidBelt")


def on_reset_pluto(event):
    _reset_world("Pluto")


def on_reset_jupiter_moons(event):
    _reset_world("JupiterMoons")


def on_reset_saturn_moons(event):
    _reset_world("SaturnMoons")


# --- Prestige / New Game+ (A1) ---
def _prestige_available():
    return all(planet_state[p]["terraform_progress"] >= TERRAFORM_MAX for p in PLANETS)


def on_prestige(event=None):
    global prestige_level, research_progress, completed_tiers, unlocked_bodies, visited_bodies
    global current_planet, governor_priority, governor_budget_pct, governor_tick_count
    global governor_purchase_count, any_generator_ever_built

    if not _prestige_available():
        return

    next_level = prestige_level + 1
    next_bonus_pct = round(PRESTIGE_BONUS_PER_LEVEL * next_level * 100)
    if not _confirm(
        f"Prestige into a New Game+? Every world resets to its starting state -- "
        f"research, travel, and the Governor included -- and you keep a permanent "
        f"+{next_bonus_pct}% resource yield (Prestige Level {next_level}). Lifetime "
        "stats and every achievement you've already earned are kept. This cannot be undone."
    ):
        return

    prestige_level = next_level
    for planet in PLANETS:
        planet_state[planet] = _fresh_planet_state(planet)
    research_progress = 0.0
    completed_tiers = 0
    unlocked_bodies = set()
    # Prestige is a genuine "run reset", not a lifetime wipe: visited_bodies
    # goes back to just Earth (matching a fresh planet_state, since nothing
    # else has been visited yet in this new run), current_planet returns to
    # Earth, and the Governor's own run-scoped counters (not the lifetime
    # ones in the stats panel) reset to their fresh-game defaults.
    # any_generator_ever_built resets too -- deliberately -- so a player who
    # already automated everything pre-prestige gets a genuine second shot
    # at the pure-clicker achievements (A2/A13) in their New Game+, without
    # touching manual_labor_hit/off_the_grid_hit themselves, which (once
    # True) never reset.
    visited_bodies = {"Earth"}
    current_planet = "Earth"
    governor_priority = "balance"
    governor_budget_pct = 50.0
    governor_tick_count = 0
    governor_purchase_count = 0
    any_generator_ever_built = False

    _full_render()
    press_feedback(document.getElementById("prestige-button"))


def governor_step():
    # Autonomously manages every real economy the player is currently NOT
    # on, using the shared priority/budget config — e.g. while on Earth,
    # Mars is governed; while on Mars or any undeveloped body, Earth (and
    # Mars, if that's not where the player is either) keeps running. This
    # loop is already N-planet generic: it governs everything in PLANETS
    # except current_planet, however many real economies that ends up being.
    global governor_tick_count, governor_purchase_count, lifetime_generators_built
    global lifetime_recyclers_built, any_generator_ever_built
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
                governor_purchase_count += 1
                lifetime_generators_built += 1
                any_generator_ever_built = True
                update_generator_display(planet)
        else:
            cost = recycler_cost(planet)
            if cost <= budget:
                state["resource_count"] -= cost
                state["recycler_count"] += 1
                governor_purchase_count += 1
                lifetime_recyclers_built += 1
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
    global lifetime_resources_generated_by_automation
    cfg = PLANETS[planet]
    state = planet_state[planet]

    if state["generator_count"] > 0:
        multiplier = production_multiplier(planet)
        if multiplier > 0:
            # Sky City bonus (Milestone 10): a no-op multiplier of exactly 1
            # on planets without the sky city keys (the other six planets).
            sky_city_bonus = 1 + cfg.get("sky_city_production_bonus_per_city", 0) * state.get(
                "sky_city_count", 0
            )
            produced = (
                state["generator_count"]
                * cfg["generator_rate"]
                * sky_city_bonus
                * (TICK_INTERVAL_MS / 1000)
                * multiplier
                * prestige_multiplier()
            )
            state["resource_count"] += produced
            lifetime_resources_generated_by_automation += produced
            # A11: only counts as "governed" (generated while away) when this
            # ISN'T the planet the player is currently standing on -- the
            # Governor Report panel's whole point is showing what happened
            # elsewhere while you were busy somewhere else.
            if planet != current_planet:
                state["governed_resource_generated"] += produced

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
    global total_ticks
    total_ticks += 1

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
        if planet in GAS_GIANT_BODIES:
            update_sky_city_display(planet)
        update_terraform_display(planet)

    update_all_cross_summaries()
    update_away_summary()
    update_win_display()
    update_achievements_display()
    update_stats_panel_display()
    update_governor_report_display()
    _check_new_achievements_for_toast()


def _full_render():
    """Switches the visible view to match `current_planet` and refreshes
    every display once. Used both by setup() on first load and by
    load_save_state() after restoring a save — tick() (already running
    on its own interval by the time a save loads mid-session) handles
    ongoing per-planet numeric updates from here on, but the one-off
    view-switch and the displays tick() doesn't touch (research,
    governor, travel-button unlock gating) need an explicit pass."""
    _hide_all_views()
    view_id = "away-view" if current_planet not in PLANETS else f"{current_planet.lower()}-view"
    document.getElementById(view_id).hidden = False

    for planet in PLANETS:
        update_resource_display(planet)
        update_generator_display(planet)
        update_ecology_display(planet)
        update_trade_display(planet)
        if planet in GAS_GIANT_BODIES:
            update_sky_city_display(planet)
        update_terraform_display(planet)
    update_research_display()
    update_research_tree_display()
    update_governor_display()
    update_travel_display()
    update_all_cross_summaries()
    update_win_display()
    update_achievements_display()
    update_stats_panel_display()
    update_governor_report_display()
    # A full render (fresh setup, or a save/load round-trip) always starts
    # with no toast showing and re-seeds the "already earned" baseline to
    # whatever's true right now -- see _seed_achievement_toast_baseline's
    # own docstring for why loading a save must never replay its whole
    # earned history as a burst of toasts.
    document.getElementById("achievement-toast").hidden = True
    _seed_achievement_toast_baseline()


# --- Save system (SAVE-SYSTEM-DESIGN.md Phase 1) ---
# Bridges to the plain-JS block in index.html: Python only ever crosses
# the Pyodide/JS boundary as a plain string (json.dumps/json.loads),
# never a raw dict/set — Pyodide auto-converts a returned `str` to a
# native JS string with no proxy involved, and the reverse on the way
# in, which sidesteps PyProxy lifetime/conversion entirely. The JS side
# owns the actual fetch() calls to the /saves API (documented plain-JS
# exception, same pattern as every other game's feedback prompt).


def serialize_state():
    """Every module-level mutable global, packaged as one JSON-safe
    dict. `planet_state` is deep-copied — it's a dict of dicts (each
    with its own nested `trade_routes` dict), and a shallow copy would
    still alias those inner dicts, so continued play after taking a
    "snapshot" would silently mutate it. `unlocked_bodies`/`visited_bodies`
    are the only non-JSON-native types in the state (sets) — converted to a
    list here and back to a set on load.

    `achievements_earned` (ACHIEVEMENTS-SYSTEM-DESIGN.md) is a write-only
    projection, not part of this game's own state: it rides the existing
    save/sync mechanism purely so the hub's aggregate dashboard can read a
    signed-in player's progress without a new backend endpoint, and it is
    always recomputed fresh here rather than read back on load — see
    deserialize_state() below, which doesn't reference this key at all."""
    return {
        "planet_state": copy.deepcopy(planet_state),
        "research_progress": research_progress,
        "completed_tiers": completed_tiers,
        "unlocked_bodies": sorted(unlocked_bodies),
        "visited_bodies": sorted(visited_bodies),
        "current_planet": current_planet,
        "governor_priority": governor_priority,
        "governor_budget_pct": governor_budget_pct,
        "governor_tick_count": governor_tick_count,
        "governor_purchase_count": governor_purchase_count,
        # A1 (Prestige / New Game+): the one piece of state a prestige is
        # FOR keeping -- see _prestige()'s own comment for what does and
        # doesn't reset.
        "prestige_level": prestige_level,
        # A4 (lifetime stats) + A2/A13 (second achievement wave): all of
        # these only ever go up (or, for the *_hit flags, flip once), and
        # none of them are touched by a world reset (A18) or reset by
        # prestige (A1) except any_generator_ever_built -- see _prestige().
        "total_ticks": total_ticks,
        "total_manual_clicks": total_manual_clicks,
        "lifetime_resources_mined_by_click": lifetime_resources_mined_by_click,
        "lifetime_resources_generated_by_automation": lifetime_resources_generated_by_automation,
        "lifetime_generators_built": lifetime_generators_built,
        "lifetime_recyclers_built": lifetime_recyclers_built,
        "lifetime_trade_routes_built": lifetime_trade_routes_built,
        "lifetime_sky_cities_built": lifetime_sky_cities_built,
        "any_generator_ever_built": any_generator_ever_built,
        "quick_start_hit": quick_start_hit,
        "swift_expansion_hit": swift_expansion_hit,
        "manual_labor_hit": manual_labor_hit,
        "off_the_grid_hit": off_the_grid_hit,
        "achievements_earned": achievement_ids_earned(),
    }


def deserialize_state(data):
    global research_progress, completed_tiers, unlocked_bodies, visited_bodies, current_planet
    global governor_priority, governor_budget_pct, governor_tick_count, governor_purchase_count
    global prestige_level, total_ticks, total_manual_clicks, lifetime_resources_mined_by_click
    global lifetime_resources_generated_by_automation, lifetime_generators_built
    global lifetime_recyclers_built, lifetime_trade_routes_built, lifetime_sky_cities_built
    global any_generator_ever_built, quick_start_hit, swift_expansion_hit, manual_labor_hit
    global off_the_grid_hit

    # Merge in place rather than clear()+update(): a save whose
    # planet_state is missing a body (an older save format from before
    # that body's economy existed, or a corrupted payload) must not wipe
    # that body's freshly-initialized state out of the dict entirely --
    # every other function (tick() in particular) does `planet_state[p]`
    # for every `p in PLANETS` unconditionally, so a missing key would
    # crash the whole game on the very next tick.
    #
    # The same reasoning applies one level down: a body's own saved dict
    # must be merged key-by-key too, not swapped in wholesale. A save
    # made before a later milestone added a new per-planet field (e.g.
    # "trade_destination" pre-9f, "terraform_progress" pre-8,
    # "sky_city_count" pre-10) would otherwise wipe that planet's
    # freshly-initialized default for the missing field, and the very
    # next access (tick()'s terraform step, current_trade_destination(),
    # _buy_sky_city()) would KeyError and crash the game.
    #
    # And the same reasoning applies one level further OUT: every
    # top-level scalar (plus "planet_state" itself) is read with a
    # `.get(..., <current live value>)` fallback rather than bare `[...]`
    # indexing, so a save missing any single top-level field -- a
    # corrupted payload, or a hand-edited/truncated save code -- falls
    # back to whatever is already running instead of KeyError-ing inside
    # deserialize_state() itself, before the game even gets as far as the
    # next tick().
    for planet, saved_planet_state in data.get("planet_state", {}).items():
        if planet in planet_state:
            planet_state[planet].update(saved_planet_state)
        else:
            planet_state[planet] = saved_planet_state
    research_progress = data.get("research_progress", research_progress)
    completed_tiers = data.get("completed_tiers", completed_tiers)
    unlocked_bodies = set(data.get("unlocked_bodies", unlocked_bodies))
    # A save made before this field existed simply has no key here, so this
    # falls back to whatever's already running (the module default,
    # {"Earth"}, on a fresh load) — same defensive fallback as every other
    # top-level field in this function, per the reasoning above.
    visited_bodies = set(data.get("visited_bodies", visited_bodies))
    current_planet = data.get("current_planet", current_planet)
    # Wherever the save says the player currently is, they have — by
    # definition — actually been there, even if this is an old save from
    # before "visited_bodies" existed at all. Without this, such a save
    # loaded mid-Mars-trip would forget Mars was ever visited until the
    # player traveled again.
    visited_bodies.add(current_planet)
    governor_priority = data.get("governor_priority", governor_priority)
    governor_budget_pct = data.get("governor_budget_pct", governor_budget_pct)
    governor_tick_count = data.get("governor_tick_count", governor_tick_count)
    governor_purchase_count = data.get("governor_purchase_count", governor_purchase_count)
    prestige_level = data.get("prestige_level", prestige_level)
    total_ticks = data.get("total_ticks", total_ticks)
    total_manual_clicks = data.get("total_manual_clicks", total_manual_clicks)
    lifetime_resources_mined_by_click = data.get(
        "lifetime_resources_mined_by_click", lifetime_resources_mined_by_click
    )
    lifetime_resources_generated_by_automation = data.get(
        "lifetime_resources_generated_by_automation", lifetime_resources_generated_by_automation
    )
    lifetime_generators_built = data.get("lifetime_generators_built", lifetime_generators_built)
    lifetime_recyclers_built = data.get("lifetime_recyclers_built", lifetime_recyclers_built)
    lifetime_trade_routes_built = data.get("lifetime_trade_routes_built", lifetime_trade_routes_built)
    lifetime_sky_cities_built = data.get("lifetime_sky_cities_built", lifetime_sky_cities_built)
    any_generator_ever_built = data.get("any_generator_ever_built", any_generator_ever_built)
    quick_start_hit = data.get("quick_start_hit", quick_start_hit)
    swift_expansion_hit = data.get("swift_expansion_hit", swift_expansion_hit)
    manual_labor_hit = data.get("manual_labor_hit", manual_labor_hit)
    off_the_grid_hit = data.get("off_the_grid_hit", off_the_grid_hit)


def _show_welcome_back_toast():
    """A3: a "welcome back" return-visit summary toast. Fires whenever a
    save is loaded -- the only situation SOL can actually call "a
    returning player" (see load_state()/load_save_state_json() below, the
    two entry points a loaded save ever arrives through). SOL has no
    offline-production system (the project's own "no idle/wait-timer
    mechanics" rule means nothing advances while the tab is closed), so
    there's no real "here's what changed while you were away" delta to
    report -- this is a snapshot recap of where the save stands, using the
    same toast mechanism as an achievement unlock."""
    earned = len(achievement_ids_earned())
    _display_toast(
        f"👋 Welcome back! {len(visited_bodies)}/{len(PLANETS)} worlds visited, "
        f"{earned}/{len(ACHIEVEMENTS)} achievements earned."
    )


def get_save_state_json():
    return json.dumps(serialize_state())


def load_save_state_json(json_str):
    deserialize_state(json.loads(json_str))
    _full_render()
    _show_welcome_back_toast()
    return True


# SAVE-BUTTON-INTEGRATION.md contract for the shared shared/save-widget.js:
# get_state() returns the same JSON-safe dict as serialize_state() (not a
# string this time — the shared widget does its own JS<->Pyodide dict
# conversion), and load_state() is deserialize_state()'s exact inverse.
# SOL is the reference integration for this contract; save codes created
# under the old bespoke UI keep working, since the dict shape is unchanged.
def get_state():
    return serialize_state()


def load_state(data):
    deserialize_state(data)
    _full_render()
    _show_welcome_back_toast()
    return True


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

    earth_cycle_trade_destination = document.getElementById("cycle-trade-destination-button")
    earth_cycle_trade_destination.innerText = "Change Destination"
    earth_cycle_trade_destination.disabled = False
    earth_cycle_trade_destination.addEventListener("click", create_proxy(on_earth_cycle_trade_destination))

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

    mars_cycle_trade_destination = document.getElementById("mars-cycle-trade-destination-button")
    mars_cycle_trade_destination.innerText = "Change Destination"
    mars_cycle_trade_destination.disabled = False
    mars_cycle_trade_destination.addEventListener("click", create_proxy(on_mars_cycle_trade_destination))

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

    moon_cycle_trade_destination = document.getElementById("moon-cycle-trade-destination-button")
    moon_cycle_trade_destination.innerText = "Change Destination"
    moon_cycle_trade_destination.disabled = False
    moon_cycle_trade_destination.addEventListener("click", create_proxy(on_moon_cycle_trade_destination))

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

    venus_cycle_trade_destination = document.getElementById("venus-cycle-trade-destination-button")
    venus_cycle_trade_destination.innerText = "Change Destination"
    venus_cycle_trade_destination.disabled = False
    venus_cycle_trade_destination.addEventListener("click", create_proxy(on_venus_cycle_trade_destination))

    document.getElementById("venus-return-to-earth-button").addEventListener(
        "click", create_proxy(on_return_to_earth_from_venus)
    )

    asteroid_belt_click = document.getElementById("asteroidbelt-click-button")
    asteroid_belt_click.innerText = "Prospect Platinum"
    asteroid_belt_click.disabled = False
    asteroid_belt_click.addEventListener("click", create_proxy(on_asteroid_belt_click))

    asteroid_belt_buy_generator = document.getElementById("asteroidbelt-buy-generator-button")
    asteroid_belt_buy_generator.disabled = False
    asteroid_belt_buy_generator.addEventListener("click", create_proxy(on_asteroid_belt_buy_generator))

    asteroid_belt_buy_recycler = document.getElementById("asteroidbelt-buy-recycler-button")
    asteroid_belt_buy_recycler.disabled = False
    asteroid_belt_buy_recycler.addEventListener("click", create_proxy(on_asteroid_belt_buy_recycler))

    asteroid_belt_buy_trade_route = document.getElementById("asteroidbelt-buy-trade-route-button")
    asteroid_belt_buy_trade_route.disabled = False
    asteroid_belt_buy_trade_route.addEventListener("click", create_proxy(on_asteroid_belt_buy_trade_route))

    asteroid_belt_cycle_trade_destination = document.getElementById("asteroidbelt-cycle-trade-destination-button")
    asteroid_belt_cycle_trade_destination.innerText = "Change Destination"
    asteroid_belt_cycle_trade_destination.disabled = False
    asteroid_belt_cycle_trade_destination.addEventListener(
        "click", create_proxy(on_asteroid_belt_cycle_trade_destination)
    )

    document.getElementById("asteroidbelt-return-to-earth-button").addEventListener(
        "click", create_proxy(on_return_to_earth_from_asteroid_belt)
    )

    pluto_click = document.getElementById("pluto-click-button")
    pluto_click.innerText = "Collect Tholins"
    pluto_click.disabled = False
    pluto_click.addEventListener("click", create_proxy(on_pluto_click))

    pluto_buy_generator = document.getElementById("pluto-buy-generator-button")
    pluto_buy_generator.disabled = False
    pluto_buy_generator.addEventListener("click", create_proxy(on_pluto_buy_generator))

    pluto_buy_recycler = document.getElementById("pluto-buy-recycler-button")
    pluto_buy_recycler.disabled = False
    pluto_buy_recycler.addEventListener("click", create_proxy(on_pluto_buy_recycler))

    pluto_buy_trade_route = document.getElementById("pluto-buy-trade-route-button")
    pluto_buy_trade_route.disabled = False
    pluto_buy_trade_route.addEventListener("click", create_proxy(on_pluto_buy_trade_route))

    pluto_cycle_trade_destination = document.getElementById("pluto-cycle-trade-destination-button")
    pluto_cycle_trade_destination.innerText = "Change Destination"
    pluto_cycle_trade_destination.disabled = False
    pluto_cycle_trade_destination.addEventListener("click", create_proxy(on_pluto_cycle_trade_destination))

    document.getElementById("pluto-return-to-earth-button").addEventListener(
        "click", create_proxy(on_return_to_earth_from_pluto)
    )

    jupiter_moons_click = document.getElementById("jupitermoons-click-button")
    jupiter_moons_click.innerText = "Skim Helium-3"
    jupiter_moons_click.disabled = False
    jupiter_moons_click.addEventListener("click", create_proxy(on_jupiter_moons_click))

    jupiter_moons_buy_generator = document.getElementById("jupitermoons-buy-generator-button")
    jupiter_moons_buy_generator.disabled = False
    jupiter_moons_buy_generator.addEventListener("click", create_proxy(on_jupiter_moons_buy_generator))

    jupiter_moons_buy_recycler = document.getElementById("jupitermoons-buy-recycler-button")
    jupiter_moons_buy_recycler.disabled = False
    jupiter_moons_buy_recycler.addEventListener("click", create_proxy(on_jupiter_moons_buy_recycler))

    jupiter_moons_buy_trade_route = document.getElementById("jupitermoons-buy-trade-route-button")
    jupiter_moons_buy_trade_route.disabled = False
    jupiter_moons_buy_trade_route.addEventListener("click", create_proxy(on_jupiter_moons_buy_trade_route))

    jupiter_moons_cycle_trade_destination = document.getElementById("jupitermoons-cycle-trade-destination-button")
    jupiter_moons_cycle_trade_destination.innerText = "Change Destination"
    jupiter_moons_cycle_trade_destination.disabled = False
    jupiter_moons_cycle_trade_destination.addEventListener(
        "click", create_proxy(on_jupiter_moons_cycle_trade_destination)
    )

    jupiter_moons_buy_sky_city = document.getElementById("jupitermoons-buy-sky-city-button")
    jupiter_moons_buy_sky_city.disabled = False
    jupiter_moons_buy_sky_city.addEventListener("click", create_proxy(on_jupiter_moons_buy_sky_city))

    document.getElementById("jupitermoons-return-to-earth-button").addEventListener(
        "click", create_proxy(on_return_to_earth_from_jupiter_moons)
    )

    saturn_moons_click = document.getElementById("saturnmoons-click-button")
    saturn_moons_click.innerText = "Condense Methane"
    saturn_moons_click.disabled = False
    saturn_moons_click.addEventListener("click", create_proxy(on_saturn_moons_click))

    saturn_moons_buy_generator = document.getElementById("saturnmoons-buy-generator-button")
    saturn_moons_buy_generator.disabled = False
    saturn_moons_buy_generator.addEventListener("click", create_proxy(on_saturn_moons_buy_generator))

    saturn_moons_buy_recycler = document.getElementById("saturnmoons-buy-recycler-button")
    saturn_moons_buy_recycler.disabled = False
    saturn_moons_buy_recycler.addEventListener("click", create_proxy(on_saturn_moons_buy_recycler))

    saturn_moons_buy_trade_route = document.getElementById("saturnmoons-buy-trade-route-button")
    saturn_moons_buy_trade_route.disabled = False
    saturn_moons_buy_trade_route.addEventListener("click", create_proxy(on_saturn_moons_buy_trade_route))

    saturn_moons_cycle_trade_destination = document.getElementById("saturnmoons-cycle-trade-destination-button")
    saturn_moons_cycle_trade_destination.innerText = "Change Destination"
    saturn_moons_cycle_trade_destination.disabled = False
    saturn_moons_cycle_trade_destination.addEventListener(
        "click", create_proxy(on_saturn_moons_cycle_trade_destination)
    )

    saturn_moons_buy_sky_city = document.getElementById("saturnmoons-buy-sky-city-button")
    saturn_moons_buy_sky_city.disabled = False
    saturn_moons_buy_sky_city.addEventListener("click", create_proxy(on_saturn_moons_buy_sky_city))

    document.getElementById("saturnmoons-return-to-earth-button").addEventListener(
        "click", create_proxy(on_return_to_earth_from_saturn_moons)
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

    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("stats-toggle-button").addEventListener("click", create_proxy(on_toggle_stats))
    document.getElementById("copy-share-card-button").addEventListener(
        "click", create_proxy(on_copy_share_card)
    )
    document.getElementById("governor-report-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_governor_report)
    )
    document.getElementById("prestige-button").addEventListener("click", create_proxy(on_prestige))

    document.getElementById("reset-world-button").addEventListener("click", create_proxy(on_reset_earth))
    document.getElementById("mars-reset-world-button").addEventListener("click", create_proxy(on_reset_mars))
    document.getElementById("moon-reset-world-button").addEventListener("click", create_proxy(on_reset_moon))
    document.getElementById("venus-reset-world-button").addEventListener("click", create_proxy(on_reset_venus))
    document.getElementById("asteroidbelt-reset-world-button").addEventListener(
        "click", create_proxy(on_reset_asteroid_belt)
    )
    document.getElementById("pluto-reset-world-button").addEventListener("click", create_proxy(on_reset_pluto))
    document.getElementById("jupitermoons-reset-world-button").addEventListener(
        "click", create_proxy(on_reset_jupiter_moons)
    )
    document.getElementById("saturnmoons-reset-world-button").addEventListener(
        "click", create_proxy(on_reset_saturn_moons)
    )

    _full_render()

    setInterval(create_proxy(tick), TICK_INTERVAL_MS)


setup()
