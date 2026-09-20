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
        # A7: per-planet Governor personality preset ("default" = follow the
        # global priority/budget dial). A23: an optional specialization
        # ("output" / "stability" / None), only choosable once the planet is
        # well developed (see SPECIALIZATION_MIN_TERRAFORM).
        "governor_personality": "default",
        "specialization": None,
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


# --- Prestige tree (A1 second tier + A3 New Game+ variant) ---
# Each prestige earns 1 point (2 if the New Game+ Challenge below was active
# when you prestiged); points are spent on tree nodes that never reset.
# Tier 2 is a genuine second branch: gated on Prestige LEVEL (how many times
# you have prestiged), not just on points. The New Game+ Challenge (A3) is a
# node INSIDE this tree that unlocks a harder-replay toggle.
prestige_points_earned = 0
prestige_nodes = set()
ng_challenge_active = False
# A15: sandbox mode (only ever effective while every world is terraformed).
sandbox_mode = False

PRESTIGE_TIER_2_LEVEL = 3
NG_CHALLENGE_COST_GROWTH_BONUS = 0.05
PRESTIGE_TREE = [
    {"id": "head_start", "tier": 1, "cost": 1, "min_level": 1, "label": "Head Start",
     "desc": "Every run starts with 50 Iron on Earth."},
    {"id": "cheaper_machinery", "tier": 1, "cost": 1, "min_level": 1, "label": "Cheaper Machinery",
     "desc": "Generators and Recyclers cost 10% less."},
    {"id": "eco_conscious", "tier": 1, "cost": 1, "min_level": 1, "label": "Eco-Conscious",
     "desc": "Ecology loss from generators is 15% lower."},
    {"id": "deep_research", "tier": 2, "cost": 2, "min_level": PRESTIGE_TIER_2_LEVEL, "label": "Deep Research",
     "desc": "Each research investment adds 50% more progress."},
    {"id": "governors_mandate", "tier": 2, "cost": 2, "min_level": PRESTIGE_TIER_2_LEVEL,
     "label": "Governor's Mandate", "desc": "Worlds you are not standing on produce 20% more."},
    {"id": "ng_challenge", "tier": 3, "cost": 2, "min_level": 2, "label": "New Game+ Challenge",
     "desc": "Unlocks a harder-replay toggle: generators and Recyclers get pricier faster, "
             "and prestiging while it is on earns 1 extra point."},
]
PRESTIGE_TREE_BY_ID = {node["id"]: node for node in PRESTIGE_TREE}
PRESTIGE_TIER_LABELS = {
    1: "Tier 1 - Foundations",
    2: f"Tier 2 - Advanced (unlocks at Prestige Level {PRESTIGE_TIER_2_LEVEL})",
    3: "Replay Variant",
}


def prestige_has(node_id):
    return node_id in prestige_nodes


def prestige_points_spent():
    return sum(PRESTIGE_TREE_BY_ID[n]["cost"] for n in prestige_nodes if n in PRESTIGE_TREE_BY_ID)


def prestige_points_available():
    return max(0, prestige_points_earned - prestige_points_spent())


def _challenge_on():
    return ng_challenge_active and prestige_has("ng_challenge")


def _sandbox_active():
    return sandbox_mode and _prestige_available()


def _cost_growth(cfg, key):
    growth = cfg[key]
    if _challenge_on():
        growth += NG_CHALLENGE_COST_GROWTH_BONUS
    return growth


# --- Governor personalities (A7) + planet specializations (A23) ---
# personality -> (priority, budget %), or None for "follow the global dial".
GOVERNOR_PERSONALITIES = {
    "default": None,
    "aggressive": ("growth", 80.0),
    "balanced": ("balance", 50.0),
    "conservative": ("ecology", 30.0),
}
GOVERNOR_PERSONALITY_LABELS = {
    "default": "Global",
    "aggressive": "Aggressive",
    "balanced": "Balanced",
    "conservative": "Conservative",
}
GOVERNOR_PERSONALITY_TIPS = {
    "default": "Follows the global Governor priority and budget on the Earth screen.",
    "aggressive": "Growth priority, 80% budget: buys generators every turn, spending up to 80% of this world's resources.",
    "balanced": "Balance priority, 50% budget: alternates generators and Recyclers, spending up to 50%.",
    "conservative": "Ecology priority, 30% budget: builds only Recyclers, spending up to 30%.",
}
SPECIALIZATION_MIN_TERRAFORM = 75.0
SPECIALIZATION_OUTPUT_BONUS = 0.25
SPECIALIZATION_OUTPUT_DECAY_PENALTY = 0.25
SPECIALIZATION_STABILITY_DECAY_CUT = 0.30
SPECIALIZATION_LABELS = {"output": "Output", "stability": "Stability"}
SPECIALIZATION_TIPS = {
    "output": "Output focus: +25% production here, but ecology decays 25% faster.",
    "stability": "Stability focus: ecology decays 30% slower here.",
}


def governor_settings(planet):
    """(priority, budget_pct) the Governor uses for `planet`: its own
    personality preset if it has one, else the global dial."""
    preset = GOVERNOR_PERSONALITIES.get(planet_state[planet].get("governor_personality", "default"))
    if preset is None:
        return governor_priority, governor_budget_pct
    return preset


def specialization_eligible(planet):
    return planet_state[planet]["terraform_progress"] >= SPECIALIZATION_MIN_TERRAFORM


def _specialization(planet):
    # Only counts while the planet is still developed enough to have earned
    # it (a reset world drops back below the bar and loses the bonus).
    spec = planet_state[planet].get("specialization")
    return spec if spec in SPECIALIZATION_LABELS and specialization_eligible(planet) else None


# --- Build-order planner (A13), close-call tracking (A19) ---
BUILD_PLAN_MAX_STEPS = 30
BUILD_PLAN_MAX_LEN = 80
BUILD_PLAN_SUGGESTED = [
    "Mine 10 Iron by hand",
    "Buy the first Auto-Miner",
    "Build a Recycler before ecology drops",
    "Fund Near Bodies research",
    "Travel to Mars and start a second economy",
    "Open a trade route to lift a struggling world",
    "Fund Far Bodies research",
]
build_plan = []  # [{"text": str, "done": bool}]

CLOSE_CALL_FLOOR = 3.0
CLOSE_CALL_RECOVERY = 50.0
close_call_hit = False
back_from_brink_hit = False
_ecology_low_seen = set()
_ecology_zero_seen = set()


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


def _machinery_discount():
    return 0.9 if prestige_has("cheaper_machinery") else 1.0


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
    return math.ceil(cfg["trade_route_base_cost"] * (cfg["trade_route_cost_growth"] ** count))


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
    button.innerText = f"Fund Research ({research_fund_cost()} Iron)"
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
    document.getElementById("travel-progress").innerText = f"{len(visited_bodies)}/{len(PLANETS)} bodies visited"


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
    _update_travel_progress()


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

    # A2: prestige badge next to the title. A24: the exact bonus next to each
    # world's resource label, where the gains actually show up.
    badge = document.getElementById("prestige-badge")
    badge.hidden = prestige_level <= 0
    badge.innerText = f"Prestige {prestige_level}" if prestige_level > 0 else ""
    bonus_text = f"+{round(PRESTIGE_BONUS_PER_LEVEL * prestige_level * 100)}% Prestige bonus on yields"
    for planet in PLANETS:
        tag = document.getElementById(_dom_id(planet, "prestige-bonus"))
        tag.hidden = prestige_level <= 0
        tag.innerText = bonus_text if prestige_level > 0 else ""

    sandbox_button = document.getElementById("sandbox-toggle-button")
    sandbox_button.hidden = not complete
    sandbox_button.innerText = "🧪 Sandbox: On" if sandbox_mode else "🧪 Sandbox: Off"
    document.getElementById("epilogue-button").hidden = not complete
    update_prestige_tree_display(rebuild=False)


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
    # A19: "close call" family. One-shot historical flags for the same reason
    # as the wave above: "fell to near zero and recovered" is play history.
    "close_call": lambda: close_call_hit,
    "back_from_the_brink": lambda: back_from_brink_hit,
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
# "What's New" changelog panel (site-wide goal, planning/TODO.md, origin K16)
# ===========================================================================
# Same static-JSON-asset loading contract as ACHIEVEMENTS above (and Le
# Champ de Mots' own precedent): the boot script fetches changelog.json and
# hands it to Python as a window global before this module runs; the
# pytest harness's fake `js` has no such attribute, so this falls through
# to reading the file straight off disk. A flat, hand-written list of
# highlights pulled from CLAUDE.md's own milestone table and build notes —
# not a full duplicate of the dev logs, just a quick "what's new" view.
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        js = None

    raw = getattr(js, "CHANGELOG_JSON", None) if js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 — only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, CHANGELOG_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Same defensive posture as ACHIEVEMENTS above: the changelog is additive,
# not core to gameplay, so any loading failure degrades to "no changelog"
# instead of crashing the whole module import.
try:
    CHANGELOG = json.loads(_read_changelog_json())["changelog"]
except (ValueError, OSError, NameError, KeyError):
    CHANGELOG = []

changelog_open = False


def on_toggle_changelog(event=None):
    global changelog_open
    changelog_open = not changelog_open
    update_changelog_display()


def update_changelog_display():
    toggle = document.getElementById("changelog-toggle-button")
    panel = document.getElementById("changelog-panel")
    toggle.innerText = "Hide What's New" if changelog_open else "📋 What's New"
    panel.hidden = not changelog_open
    if not changelog_open:
        return

    panel.innerHTML = ""
    # changelog.json is authored newest-first already, so no re-sort needed
    # here — same "trust the JSON's own order" posture ACHIEVEMENTS takes.
    for entry in CHANGELOG:
        row = document.createElement("div")
        row.className = "changelog-entry"

        date = document.createElement("p")
        date.className = "changelog-entry-date"
        date.innerText = entry["date"]
        row.appendChild(date)

        text = document.createElement("p")
        text.className = "changelog-entry-text"
        text.innerText = entry["entry"]
        row.appendChild(text)

        panel.appendChild(row)


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
        _flash_copy_button(document.getElementById("copy-share-card-button"), "✓ Copied!")
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
        (
            "Generated while governed (all worlds)",
            str(math.floor(sum(planet_state[p]["governed_resource_generated"] for p in PLANETS) + 1e-9)),
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


def _mine(planet, event=None):
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
    button = document.getElementById(_dom_id(planet, "click-button"))
    _spawn_floater(button, "✦", "floater--spark", event)
    press_feedback(button)


def on_earth_click(event):
    _mine("Earth", event)


def on_mars_click(event):
    _mine("Mars", event)


def on_moon_click(event):
    _mine("Moon", event)


def on_venus_click(event):
    _mine("Venus", event)


def on_asteroid_belt_click(event):
    _mine("AsteroidBelt", event)


def on_pluto_click(event):
    _mine("Pluto", event)


def on_jupiter_moons_click(event):
    _mine("JupiterMoons", event)


def on_saturn_moons_click(event):
    _mine("SaturnMoons", event)


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
        _spawn_floater(button, "⚙️", "floater--build")
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
        _spawn_floater(button, "♻️", "floater--build")
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
            _spawn_floater(button, "🚀", "floater--build")
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
        _spawn_floater(button, "🏙️", "floater--build")
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
    cost = research_fund_cost()
    if tier is not None and earth["resource_count"] >= cost:
        earth["resource_count"] -= cost
        gain = RESEARCH_FUND_COST * (1.5 if prestige_has("deep_research") else 1)
        research_progress = min(research_progress + gain, tier["target"])
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


# --- Travel (shared by the Travel buttons, Return-to-Earth, and the A9
# overview dashboard) plus A5's "while you were away" report ---
AWAY_REPORT_MIN_TICKS = 100  # 10 seconds of simulated play; shorter hops aren't worth a report
_departure_snapshots = {}  # planet -> what its state looked like when the player left it


def _show_planet_view(planet):
    _hide_all_views()
    document.getElementById(f"{planet.lower()}-view").hidden = False
    update_resource_display(planet)
    update_generator_display(planet)
    update_ecology_display(planet)
    update_trade_display(planet)
    if planet in GAS_GIANT_BODIES:
        update_sky_city_display(planet)
    update_terraform_display(planet)
    update_all_cross_summaries()


def _snapshot_departure(planet):
    state = planet_state[planet]
    _departure_snapshots[planet] = {
        "tick": total_ticks,
        "generated": state["governed_resource_generated"],
        "generators": state["generator_count"],
        "recyclers": state["recycler_count"],
        "ecology": state["ecology_health"],
    }


def _report_arrival(planet):
    """A5: on returning to a world, report what happened there while the
    player was elsewhere: resources its automation generated (real, already
    tracked as governed_resource_generated), what the Governor built, and
    how its ecology moved. Reports elapsed simulated play-time and never
    gates or advances anything, so it doesn't touch the no-idle-timer rule."""
    snap = _departure_snapshots.pop(planet, None)
    if snap is None:
        return
    elapsed = total_ticks - snap["tick"]
    if elapsed < AWAY_REPORT_MIN_TICKS:
        return
    state = planet_state[planet]
    gained = math.floor(state["governed_resource_generated"] - snap["generated"] + 1e-9)
    generators = state["generator_count"] - snap["generators"]
    recyclers = state["recycler_count"] - snap["recyclers"]
    name = PLANET_DISPLAY_NAMES.get(planet, planet)
    parts = [f"+{max(gained, 0)} {PLANETS[planet]['resource_name']}"]
    if generators > 0 or recyclers > 0:
        parts.append(f"the Governor built {max(generators, 0)} generator(s) and {max(recyclers, 0)} Recycler(s)")
    else:
        parts.append("no Governor purchases")
    parts.append(f"ecology {round(snap['ecology'])}% to {round(state['ecology_health'])}%")
    document.getElementById("away-report-text").innerText = (
        f"While you were away from {name} ({_format_duration(elapsed * TICK_INTERVAL_MS / 1000)}): "
        + "; ".join(parts) + "."
    )
    document.getElementById("away-report").hidden = False


def on_dismiss_away_report(event=None):
    document.getElementById("away-report").hidden = True


def _travel_to(planet):
    global current_planet
    if planet != "Earth" and planet not in unlocked_bodies:
        return False
    if planet == current_planet:
        return True
    if current_planet in planet_state:
        _snapshot_departure(current_planet)
    current_planet = planet
    _mark_visited(planet)
    _update_travel_progress()
    _show_planet_view(planet)
    _report_arrival(planet)
    return True


def _travel_from_button(planet, button_id):
    _travel_to(planet)
    press_feedback(document.getElementById(button_id))


def on_travel_moon(event):
    _travel_from_button("Moon", "travel-moon-button")


def on_travel_venus(event):
    _travel_from_button("Venus", "travel-venus-button")


def on_travel_asteroid_belt(event):
    _travel_from_button("AsteroidBelt", "travel-asteroid-belt-button")


def on_travel_pluto(event):
    _travel_from_button("Pluto", "travel-pluto-button")


def on_travel_jupiter_moons(event):
    _travel_from_button("JupiterMoons", "travel-jupiter-moons-button")


def on_travel_saturn_moons(event):
    _travel_from_button("SaturnMoons", "travel-saturn-moons-button")


def on_travel_mars(event):
    _travel_from_button("Mars", "travel-mars-button")


def _return_to_earth():
    _travel_to("Earth")


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
        "governor_personality": "default",
        "specialization": None,
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
    _forget_close_call_history(planet)
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


# ===========================================================================
# Session additions (planning/TODO.md "Per-game: SOL": A2, A4-A9, A12-A21,
# A23, A24, A27, A28, A30). Panels that carry BUTTONS (overview, build plan,
# prestige tree) use one delegated listener bound once in setup() and read
# `data-*` attributes off event.target, and are only rebuilt when their
# structure actually changes -- never every tick -- so a click can never land
# on a button that was just swapped out from under the cursor.
# ===========================================================================


def _target_attr(event, name):
    """Reads a data-* attribute off a delegated click's target, tolerating a
    text-node/None target (returns None rather than raising)."""
    try:
        target = event.target
        if target is None:
            return None
        value = target.getAttribute(name)
        return None if value is None else str(value)
    except (AttributeError, TypeError):
        return None


def _make_button(text, attrs, tip=None, selected=False, disabled=False):
    button = document.createElement("button")
    button.type = "button"
    button.className = "secondary mini-button" + (" selected" if selected else "")
    button.innerText = text
    for key, value in attrs.items():
        button.setAttribute(key, value)
    if tip:
        button.title = tip
    button.disabled = disabled
    return button


def _make_text(class_name, text, tag="p"):
    element = document.createElement(tag)
    element.className = class_name
    element.innerText = text
    return element


# --- A12 / A30: floating spark on a manual click, floating icon on a build ---
_MAX_FLOATERS = 14
_active_floaters = 0


def _spawn_floater(anchor, glyph, css_class, event=None):
    global _active_floaters
    if _active_floaters >= _MAX_FLOATERS:
        return
    try:
        rect = anchor.getBoundingClientRect()
        x = rect.left + rect.width / 2
        y = rect.top + rect.height / 2
        if event is not None:
            client_x = getattr(event, "clientX", None)
            client_y = getattr(event, "clientY", None)
            if client_x and client_y:
                x, y = client_x, client_y
        layer = document.getElementById("spark-layer")
        floater = document.createElement("span")
    except (AttributeError, TypeError, KeyError):
        return  # no layout/DOM available (headless): visual polish only, skip silently
    floater.className = f"floater {css_class}"
    floater.innerText = glyph
    floater.style.left = f"{x}px"
    floater.style.top = f"{y}px"
    layer.appendChild(floater)
    _active_floaters += 1

    def _remove(*args):
        global _active_floaters
        _active_floaters = max(0, _active_floaters - 1)
        layer.removeChild(floater)
        proxy.destroy()

    proxy = create_proxy(_remove)
    setTimeout(proxy, 700)


# --- A9: multi-planet overview dashboard (+ A7 personalities, A23 specializations) ---
overview_open = False
_overview_signature = None
_overview_refs = {}


def on_toggle_overview(event=None):
    global overview_open
    overview_open = not overview_open
    update_overview_display()


def _overview_planets():
    return [p for p in PLANETS if p == "Earth" or p in unlocked_bodies]


def _overview_structure_signature():
    return (
        current_planet,
        tuple(
            (
                p,
                planet_state[p].get("governor_personality", "default"),
                planet_state[p].get("specialization"),
                specialization_eligible(p),
            )
            for p in _overview_planets()
        ),
    )


def _build_overview():
    panel = document.getElementById("overview-panel")
    panel.innerHTML = ""
    _overview_refs.clear()

    summary = _make_text("overview-summary", "")
    panel.appendChild(summary)
    _overview_refs["_summary"] = summary

    for planet in _overview_planets():
        state = planet_state[planet]
        card = document.createElement("div")
        card.className = "overview-card" + (" overview-card--current" if planet == current_planet else "")

        title = _make_text(
            "overview-card-title",
            PLANET_DISPLAY_NAMES.get(planet, planet) + (" (you are here)" if planet == current_planet else ""),
        )
        card.appendChild(title)
        stats = _make_text("overview-card-stats", "")
        card.appendChild(stats)

        eco_row = document.createElement("div")
        eco_row.className = "overview-bar-row"
        eco_label = _make_text("overview-bar-label", "Ecology", "span")
        eco_meter = document.createElement("div")
        eco_meter.className = "meter overview-meter"
        eco_fill = document.createElement("div")
        eco_fill.className = "meter-fill"
        eco_meter.appendChild(eco_fill)
        eco_row.appendChild(eco_label)
        eco_row.appendChild(eco_meter)
        card.appendChild(eco_row)

        tf_row = document.createElement("div")
        tf_row.className = "overview-bar-row"
        tf_label = _make_text("overview-bar-label", "Terraform", "span")
        tf_meter = document.createElement("div")
        tf_meter.className = "meter overview-meter"
        tf_fill = document.createElement("div")
        tf_fill.className = "meter-fill terraform-fill"
        tf_meter.appendChild(tf_fill)
        tf_row.appendChild(tf_label)
        tf_row.appendChild(tf_meter)
        card.appendChild(tf_row)

        extras = _make_text("overview-card-extras", "")
        card.appendChild(extras)

        actions = document.createElement("div")
        actions.className = "overview-actions"
        if planet != current_planet:
            actions.appendChild(
                _make_button("Travel here", {"data-action": "travel", "data-planet": planet},
                             "Fly to this world without going back through Earth.")
            )
        card.appendChild(actions)

        personality_row = document.createElement("div")
        personality_row.className = "overview-actions"
        personality_row.appendChild(_make_text("overview-actions-label", "Governor:", "span"))
        current_personality = state.get("governor_personality", "default")
        for key, label in GOVERNOR_PERSONALITY_LABELS.items():
            personality_row.appendChild(
                _make_button(label, {"data-action": "personality", "data-planet": planet, "data-value": key},
                             GOVERNOR_PERSONALITY_TIPS[key], selected=(key == current_personality))
            )
        card.appendChild(personality_row)

        if specialization_eligible(planet):
            spec_row = document.createElement("div")
            spec_row.className = "overview-actions"
            spec_row.appendChild(_make_text("overview-actions-label", "Focus:", "span"))
            for key, label in SPECIALIZATION_LABELS.items():
                spec_row.appendChild(
                    _make_button(label, {"data-action": "specialize", "data-planet": planet, "data-value": key},
                                 SPECIALIZATION_TIPS[key], selected=(state.get("specialization") == key))
                )
            card.appendChild(spec_row)

        panel.appendChild(card)
        _overview_refs[planet] = {"stats": stats, "eco": eco_fill, "tf": tf_fill, "extras": extras}


def _refresh_overview_values():
    planets = _overview_planets()
    summary = _overview_refs.get("_summary")
    if summary is not None:
        avg_tf = sum(planet_state[p]["terraform_progress"] for p in planets) / len(planets)
        gens = sum(planet_state[p]["generator_count"] for p in planets)
        summary.innerText = (
            f"{len(planets)}/{len(PLANETS)} worlds unlocked · {gens} generators total · "
            f"average terraforming {round(avg_tf)}%"
        )
    for planet in planets:
        refs = _overview_refs.get(planet)
        if refs is None:
            continue
        state = planet_state[planet]
        cfg = PLANETS[planet]
        refs["stats"].innerText = (
            f"{cfg['resource_name']}: {math.floor(state['resource_count'] + 1e-9)} · "
            f"{state['generator_count']} generators · {state['recycler_count']} Recyclers"
        )
        refs["eco"].style.width = f"{state['ecology_health']}%"
        refs["tf"].style.width = f"{state['terraform_progress']}%"
        routes = sum(state["trade_routes"].values())
        bits = [
            f"Ecology {round(state['ecology_health'])}%",
            f"Terraform {round(state['terraform_progress'])}%",
            f"Output {round(production_multiplier(planet) * 100)}%",
            f"{routes} trade route(s)",
        ]
        if planet in GAS_GIANT_BODIES:
            bits.append(f"{state.get('sky_city_count', 0)} Sky City(ies)")
        spec = _specialization(planet)
        if spec:
            bits.append(f"Focus: {SPECIALIZATION_LABELS[spec]}")
        refs["extras"].innerText = " · ".join(bits)


def update_overview_display():
    global _overview_signature
    toggle = document.getElementById("overview-toggle-button")
    panel = document.getElementById("overview-panel")
    toggle.innerText = "Hide Overview" if overview_open else "🌍 Overview"
    panel.hidden = not overview_open
    if not overview_open:
        _overview_signature = None
        return
    signature = _overview_structure_signature()
    if signature != _overview_signature:
        _build_overview()
        _overview_signature = signature
    _refresh_overview_values()


def on_overview_click(event):
    action = _target_attr(event, "data-action")
    planet = _target_attr(event, "data-planet")
    value = _target_attr(event, "data-value")
    if action is None or planet not in PLANETS:
        return
    if action == "travel":
        _travel_to(planet)
    elif action == "personality" and value in GOVERNOR_PERSONALITIES:
        planet_state[planet]["governor_personality"] = value
    elif action == "specialize" and value in SPECIALIZATION_LABELS and specialization_eligible(planet):
        state = planet_state[planet]
        state["specialization"] = None if state.get("specialization") == value else value
    update_overview_display()
    update_governor_report_display()


# --- A13: build-order planner ---
build_plan_open = False


def on_toggle_build_plan(event=None):
    global build_plan_open
    build_plan_open = not build_plan_open
    update_build_plan_display()


def _add_build_step(text):
    text = str(text).strip()[:BUILD_PLAN_MAX_LEN]
    if not text or len(build_plan) >= BUILD_PLAN_MAX_STEPS:
        return False
    build_plan.append({"text": text, "done": False})
    return True


def on_build_plan_add(event=None):
    field = document.getElementById("build-plan-input")
    if _add_build_step(getattr(field, "value", "") or ""):
        field.value = ""
    update_build_plan_display()


def on_build_plan_suggest(event=None):
    for text in BUILD_PLAN_SUGGESTED:
        if not any(step["text"] == text for step in build_plan):
            _add_build_step(text)
    update_build_plan_display()


def on_build_plan_clear_done(event=None):
    build_plan[:] = [step for step in build_plan if not step["done"]]
    update_build_plan_display()


def on_build_plan_click(event):
    action = _target_attr(event, "data-action")
    raw = _target_attr(event, "data-step")
    try:
        index = int(raw)
    except (TypeError, ValueError):
        return
    if not 0 <= index < len(build_plan):
        return
    if action == "toggle":
        build_plan[index]["done"] = not build_plan[index]["done"]
    elif action == "remove":
        del build_plan[index]
    update_build_plan_display()


def update_build_plan_display():
    toggle = document.getElementById("build-plan-toggle-button")
    panel = document.getElementById("build-plan-panel")
    done = sum(1 for step in build_plan if step["done"])
    label = f"📝 Build Plan ({done}/{len(build_plan)})" if build_plan else "📝 Build Plan"
    toggle.innerText = "Hide Build Plan" if build_plan_open else label
    panel.hidden = not build_plan_open
    if not build_plan_open:
        return
    listing = document.getElementById("build-plan-list")
    listing.innerHTML = ""
    if not build_plan:
        listing.appendChild(_make_text("build-plan-empty", "No steps yet. Add your own, or start from the suggested opening."))
    for index, step in enumerate(build_plan):
        row = document.createElement("div")
        row.className = "build-plan-row" + (" build-plan-row--done" if step["done"] else "")
        row.appendChild(
            _make_button("☑" if step["done"] else "☐", {"data-action": "toggle", "data-step": str(index)},
                         "Tick this step off")
        )
        row.appendChild(_make_text("build-plan-text", step["text"], "span"))
        row.appendChild(
            _make_button("✕", {"data-action": "remove", "data-step": str(index)}, "Remove this step")
        )
        listing.appendChild(row)


# --- A1 / A3: prestige tree panel ---
prestige_tree_open = False


def on_toggle_prestige_tree(event=None):
    global prestige_tree_open
    prestige_tree_open = not prestige_tree_open
    update_prestige_tree_display()


def _node_unlockable(node):
    return (
        node["id"] not in prestige_nodes
        and prestige_level >= node["min_level"]
        and prestige_points_available() >= node["cost"]
    )


def update_prestige_tree_display(rebuild=True):
    toggle = document.getElementById("prestige-tree-toggle-button")
    panel = document.getElementById("prestige-tree-panel")
    toggle.hidden = prestige_level <= 0
    available = prestige_points_available()
    toggle.innerText = "Hide Prestige Tree" if prestige_tree_open else f"🌳 Prestige Tree ({available})"
    panel.hidden = not (prestige_tree_open and prestige_level > 0)
    if panel.hidden or not rebuild:
        return
    panel.innerHTML = ""
    panel.appendChild(
        _make_text(
            "prestige-tree-points",
            f"Prestige Points: {available} available ({prestige_points_earned} earned). "
            "Each prestige earns 1; unlocks are permanent and survive every prestige.",
        )
    )
    for tier in (1, 2, 3):
        panel.appendChild(_make_text("stats-panel-heading", PRESTIGE_TIER_LABELS[tier]))
        for node in [n for n in PRESTIGE_TREE if n["tier"] == tier]:
            unlocked = node["id"] in prestige_nodes
            card = document.createElement("div")
            card.className = "prestige-node" + (" prestige-node--unlocked" if unlocked else "")
            card.appendChild(_make_text("prestige-node-name", f"{node['label']} ({node['cost']} pt)"))
            card.appendChild(_make_text("prestige-node-desc", node["desc"]))
            if unlocked:
                card.appendChild(_make_text("prestige-node-status", "Unlocked"))
                if node["id"] == "ng_challenge":
                    card.appendChild(
                        _make_button(
                            "Challenge: On" if ng_challenge_active else "Challenge: Off",
                            {"data-action": "challenge"},
                            "Applies at the moment you next Prestige, and to the run after it.",
                            selected=ng_challenge_active,
                        )
                    )
            elif prestige_level < node["min_level"]:
                card.appendChild(
                    _make_text("prestige-node-status", f"Locked: reach Prestige Level {node['min_level']}")
                )
            else:
                card.appendChild(
                    _make_button(f"Unlock ({node['cost']} pt)", {"data-action": "unlock", "data-node": node["id"]},
                                 None, disabled=not _node_unlockable(node))
                )
            panel.appendChild(card)


def on_prestige_tree_click(event):
    global ng_challenge_active
    action = _target_attr(event, "data-action")
    if action == "unlock":
        node = PRESTIGE_TREE_BY_ID.get(_target_attr(event, "data-node"))
        if node is not None and _node_unlockable(node):
            prestige_nodes.add(node["id"])
    elif action == "challenge" and prestige_has("ng_challenge"):
        ng_challenge_active = not ng_challenge_active
    update_prestige_tree_display()
    _refresh_all_cost_displays()


def _refresh_all_cost_displays():
    for planet in PLANETS:
        update_generator_display(planet)
        update_ecology_display(planet)
        update_trade_display(planet)
        if planet in GAS_GIANT_BODIES:
            update_sky_city_display(planet)
    update_research_display()


# --- A15: sandbox mode + A27: epilogue ---
epilogue_open = False


def on_toggle_sandbox(event=None):
    global sandbox_mode
    if not _prestige_available():
        return
    sandbox_mode = not sandbox_mode
    _refresh_all_cost_displays()
    update_win_display()


def on_toggle_epilogue(event=None):
    global epilogue_open
    if not _prestige_available():
        epilogue_open = False
    else:
        epilogue_open = not epilogue_open
    update_epilogue_display()


def update_epilogue_display():
    panel = document.getElementById("epilogue-panel")
    panel.hidden = not (epilogue_open and _prestige_available())
    if panel.hidden:
        return
    body = document.getElementById("epilogue-body")
    body.innerHTML = ""
    paragraphs = [
        "The last survey drones report in. On every world you touched, the air holds, the water runs, "
        "and the ledgers finally balance against the ground they were drawn from.",
        f"It took {_format_duration(_lifetime_playtime_seconds())} of simulated time, "
        f"{total_manual_clicks} hand-mined loads, and {lifetime_generators_built} machines that never tired.",
        f"{len(visited_bodies)} of {len(PLANETS)} worlds saw your boots, and {len(achievement_ids_earned())} of "
        f"{len(ACHIEVEMENTS)} milestones are in the log.",
        "Nothing here has to end. The sandbox stays open, and a New Game+ waits for anyone who wants to do it "
        "all again a little better.",
    ]
    if prestige_level > 0:
        paragraphs.insert(3, f"You have started over {prestige_level} time(s) already, and each run left the system tidier.")
    for text in paragraphs:
        body.appendChild(_make_text("epilogue-paragraph", text))


# --- A6 / A17 / A21 / A8-support: stats-panel extras ---
STATS_CODE_PREFIX = "SOLSTATS1:"
_STATS_CODE_FIELDS = (
    "total_ticks",
    "total_manual_clicks",
    "lifetime_resources_mined_by_click",
    "lifetime_resources_generated_by_automation",
    "lifetime_generators_built",
    "lifetime_recyclers_built",
    "lifetime_trade_routes_built",
    "lifetime_sky_cities_built",
)
COMPARE_FIELDS = (
    "prestige_level",
    "total_ticks",
    "total_manual_clicks",
    "lifetime_generators_built",
    "lifetime_recyclers_built",
    "lifetime_trade_routes_built",
    "lifetime_sky_cities_built",
    "governor_purchase_count",
)


def export_stats_code():
    import base64  # noqa: PLC0415

    payload = {name: globals()[name] for name in _STATS_CODE_FIELDS}
    payload["prestige_level"] = prestige_level
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    return STATS_CODE_PREFIX + base64.b64encode(raw).decode("ascii")


def import_stats_code(code):
    """Returns (ok, message). Only ever raises a counter, never lowers one, so
    a stale code from an old device can't undo newer progress."""
    import base64  # noqa: PLC0415

    code = (code or "").strip()
    if not code.startswith(STATS_CODE_PREFIX):
        return False, "That doesn't look like a SOL stats code."
    try:
        payload = json.loads(base64.b64decode(code[len(STATS_CODE_PREFIX):]).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return False, "That stats code couldn't be read."
    if not isinstance(payload, dict):
        return False, "That stats code couldn't be read."
    for name in _STATS_CODE_FIELDS:
        value = payload.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            return False, "That stats code has invalid values."
    for name in _STATS_CODE_FIELDS:
        globals()[name] = max(globals()[name], payload[name])
    return True, "Stats imported. Counters only ever go up."


def on_export_stats(event=None):
    document.getElementById("stats-code-output").value = export_stats_code()
    document.getElementById("stats-code-status").innerText = "Copy this code and keep it somewhere safe."


def on_import_stats(event=None):
    field = document.getElementById("stats-code-input")
    ok, message = import_stats_code(getattr(field, "value", ""))
    document.getElementById("stats-code-status").innerText = message
    if ok:
        update_stats_panel_display()


def compare_values():
    values = {name: globals().get(name, 0) for name in COMPARE_FIELDS}
    values["governor_purchase_count"] = governor_purchase_count
    return values


def on_compare_run(event=None):
    try:
        import js  # noqa: PLC0415

        js.SolCompare.run(json.dumps(compare_values()))
    except (ImportError, AttributeError):
        document.getElementById("compare-run-results").innerText = "Comparison isn't available right now."


def _flash_copy_button(button, done_text):
    original = "📋 Copy to Clipboard"
    button.innerText = done_text

    def _restore(*args):
        button.innerText = original
        proxy.destroy()

    proxy = create_proxy(_restore)
    setTimeout(proxy, 1500)


# --- A14: research tree tier collapse ---
research_tree_collapsed = set()


def on_research_tree_click(event):
    raw = _target_attr(event, "data-tier")
    try:
        index = int(raw)
    except (TypeError, ValueError):
        return
    if not 0 <= index < len(RESEARCH_TIERS):
        return
    if index in research_tree_collapsed:
        research_tree_collapsed.discard(index)
    else:
        research_tree_collapsed.add(index)
    update_research_tree_display()


# --- A19: "close call" tracking ---
def _track_close_calls():
    global close_call_hit, back_from_brink_hit
    for planet in PLANETS:
        health = planet_state[planet]["ecology_health"]
        if health < CLOSE_CALL_FLOOR:
            _ecology_low_seen.add(planet)
            if health <= 0:
                _ecology_zero_seen.add(planet)
        elif health >= CLOSE_CALL_RECOVERY:
            if planet in _ecology_low_seen:
                close_call_hit = True
            if planet in _ecology_zero_seen:
                back_from_brink_hit = True


def _forget_close_call_history(planet=None):
    if planet is None:
        _ecology_low_seen.clear()
        _ecology_zero_seen.clear()
    else:
        _ecology_low_seen.discard(planet)
        _ecology_zero_seen.discard(planet)


# --- Prestige / New Game+ (A1) ---
def _prestige_available():
    return all(planet_state[p]["terraform_progress"] >= TERRAFORM_MAX for p in PLANETS)


def on_prestige(event=None):
    global prestige_level, research_progress, completed_tiers, unlocked_bodies, visited_bodies
    global current_planet, governor_priority, governor_budget_pct, governor_tick_count
    global governor_purchase_count, any_generator_ever_built, prestige_points_earned, sandbox_mode
    global epilogue_open

    if not _prestige_available():
        return

    next_level = prestige_level + 1
    next_bonus_pct = round(PRESTIGE_BONUS_PER_LEVEL * next_level * 100)
    if not _confirm(
        f"Prestige into a New Game+? Every world resets to its starting state -- "
        f"research, travel, and the Governor included -- and you keep a permanent "
        f"+{next_bonus_pct}% resource yield (Prestige Level {next_level}) and a Prestige Tree "
        "point. Lifetime stats, tree unlocks and every achievement you've already earned are kept. "
        "This cannot be undone."
    ):
        return

    prestige_level = next_level
    # A1/A3: 1 tree point per prestige, +1 if the New Game+ Challenge was on.
    prestige_points_earned += 1 + (1 if _challenge_on() else 0)
    sandbox_mode = False
    epilogue_open = False
    _forget_close_call_history()
    _departure_snapshots.clear()
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
    if prestige_has("head_start"):
        planet_state["Earth"]["resource_count"] = 50.0

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

    for planet in governed_planets:
        if _sandbox_active():
            continue  # A15: costs are zero in sandbox, so the Governor would buy without limit
        # A7: each world may carry its own personality preset; otherwise it
        # follows the global dial exactly as before.
        priority, budget_pct = governor_settings(planet)
        if priority == "growth":
            buy_generator_turn = True
        elif priority == "ecology":
            buy_generator_turn = False
        else:  # "balance" — alternate turns between the two buildings
            buy_generator_turn = governor_tick_count % 2 == 0
        state = planet_state[planet]
        budget = state["resource_count"] * (budget_pct / 100)

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
            spec = _specialization(planet)
            produced = (
                state["generator_count"]
                * cfg["generator_rate"]
                * sky_city_bonus
                * (TICK_INTERVAL_MS / 1000)
                * multiplier
                * prestige_multiplier()
                * (1 + SPECIALIZATION_OUTPUT_BONUS if spec == "output" else 1)
                * (1.2 if prestige_has("governors_mandate") and planet != current_planet else 1)
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
    if prestige_has("eco_conscious"):
        decay *= 0.85
    spec = _specialization(planet)
    if spec == "output":
        decay *= 1 + SPECIALIZATION_OUTPUT_DECAY_PENALTY
    elif spec == "stability":
        decay *= 1 - SPECIALIZATION_STABILITY_DECAY_CUT
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
    _track_close_calls()

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
    update_changelog_display()
    update_overview_display()
    update_epilogue_display()
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
    update_changelog_display()
    update_overview_display()
    update_build_plan_display()
    update_prestige_tree_display()
    update_epilogue_display()
    _refresh_all_cost_displays()
    document.getElementById("away-report").hidden = True
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
        # Prestige tree (A1/A3), sandbox (A15), build plan (A13), close calls (A19).
        "prestige_points_earned": prestige_points_earned,
        "prestige_nodes": sorted(prestige_nodes),
        "ng_challenge_active": ng_challenge_active,
        "sandbox_mode": sandbox_mode,
        "build_plan": copy.deepcopy(build_plan),
        "close_call_hit": close_call_hit,
        "back_from_brink_hit": back_from_brink_hit,
        "ecology_low_seen": sorted(_ecology_low_seen),
        "ecology_zero_seen": sorted(_ecology_zero_seen),
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
    _load_session_additions(data)


def _load_session_additions(data):
    """Loads the fields added with the A1-A30 batch, each defensively: a
    missing key keeps the current value, a wrongly-typed one is ignored, so
    an old save (or a hand-edited one) can never crash the load."""
    global prestige_points_earned, prestige_nodes, ng_challenge_active, sandbox_mode
    global close_call_hit, back_from_brink_hit, _departure_snapshots

    # Legacy saves: prestige_level existed before points did, and each
    # prestige is worth 1 point, so an old save's points equal its level.
    earned = data.get("prestige_points_earned", prestige_level)
    prestige_points_earned = earned if isinstance(earned, int) and not isinstance(earned, bool) and earned >= 0 else prestige_level
    nodes = data.get("prestige_nodes", sorted(prestige_nodes))
    if isinstance(nodes, list):
        prestige_nodes = {n for n in nodes if isinstance(n, str) and n in PRESTIGE_TREE_BY_ID}
    ng_challenge_active = data.get("ng_challenge_active", ng_challenge_active) is True
    sandbox_mode = data.get("sandbox_mode", sandbox_mode) is True
    close_call_hit = data.get("close_call_hit", close_call_hit) is True
    back_from_brink_hit = data.get("back_from_brink_hit", back_from_brink_hit) is True
    for key, target in (("ecology_low_seen", _ecology_low_seen), ("ecology_zero_seen", _ecology_zero_seen)):
        raw = data.get(key)
        if isinstance(raw, list):
            target.clear()
            target.update(p for p in raw if p in PLANETS)
    plan = data.get("build_plan")
    if isinstance(plan, list):
        cleaned = []
        for step in plan[:BUILD_PLAN_MAX_STEPS]:
            if isinstance(step, dict) and isinstance(step.get("text"), str) and step["text"].strip():
                cleaned.append({"text": step["text"].strip()[:BUILD_PLAN_MAX_LEN], "done": step.get("done") is True})
        build_plan[:] = cleaned
    # A run-scoped, in-memory report baseline: never meaningful across a load.
    _departure_snapshots = {}
    for state in planet_state.values():
        if state.get("governor_personality") not in GOVERNOR_PERSONALITIES:
            state["governor_personality"] = "default"
        if state.get("specialization") not in (None, *SPECIALIZATION_LABELS):
            state["specialization"] = None


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
    document.getElementById("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    document.getElementById("prestige-button").addEventListener("click", create_proxy(on_prestige))
    document.getElementById("sandbox-toggle-button").addEventListener("click", create_proxy(on_toggle_sandbox))
    document.getElementById("epilogue-button").addEventListener("click", create_proxy(on_toggle_epilogue))
    document.getElementById("epilogue-close-button").addEventListener("click", create_proxy(on_toggle_epilogue))
    document.getElementById("overview-toggle-button").addEventListener("click", create_proxy(on_toggle_overview))
    document.getElementById("overview-panel").addEventListener("click", create_proxy(on_overview_click))
    document.getElementById("build-plan-toggle-button").addEventListener("click", create_proxy(on_toggle_build_plan))
    document.getElementById("build-plan-add-button").addEventListener("click", create_proxy(on_build_plan_add))
    document.getElementById("build-plan-suggest-button").addEventListener(
        "click", create_proxy(on_build_plan_suggest)
    )
    document.getElementById("build-plan-clear-done-button").addEventListener(
        "click", create_proxy(on_build_plan_clear_done)
    )
    document.getElementById("build-plan-list").addEventListener("click", create_proxy(on_build_plan_click))
    document.getElementById("prestige-tree-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_prestige_tree)
    )
    document.getElementById("prestige-tree-panel").addEventListener("click", create_proxy(on_prestige_tree_click))
    document.getElementById("away-report-dismiss-button").addEventListener(
        "click", create_proxy(on_dismiss_away_report)
    )
    document.getElementById("compare-run-button").addEventListener("click", create_proxy(on_compare_run))
    document.getElementById("stats-export-button").addEventListener("click", create_proxy(on_export_stats))
    document.getElementById("stats-import-button").addEventListener("click", create_proxy(on_import_stats))
    document.getElementById("research-tree").addEventListener("click", create_proxy(on_research_tree_click))

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
