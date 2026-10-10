import copy
import export_progress
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
        # A-22: how many times the player has mined or bought something on this
        # world by hand; only ever read for the Governor's mood line.
        "player_actions": 0,
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
# U10: research is a real tree now, not a bar filled 50 Iron at a time. Each
# LEVEL (Near Bodies, then Far Bodies) is a 20-node tree that splits into
# branches and rejoins, ending at that level's own final node (researching it
# is what unlocks the bodies). Node costs vary but every level adds up to the
# total the old bars asked for (1000 and 5000 Iron), so the overall pace is
# unchanged. Most nodes carry a small real bonus (effects, in percent):
#   yield_pct           -- more of every resource, manual and automated
#   machinery_discount  -- cheaper Auto-Miners and Recyclers
#   route_discount      -- cheaper trade routes
# Rows: (id, name, cost, requires, effects).
_RESEARCH_LEVEL_ROWS = [
    {
        "name": "Near Bodies",
        "unlocks": ["Moon", "Mars"],
        "rows": [
            ("survey", "Basic Survey", 20, [], {}),
            ("better_picks", "Better Picks", 40, ["survey"], {"yield_pct": 1}),
            ("ore_scanners", "Ore Scanners", 40, ["survey"], {"yield_pct": 1}),
            ("pneumatic_drills", "Pneumatic Drills", 50, ["better_picks"], {"yield_pct": 2}),
            ("smelter_design", "Smelter Design", 50, ["ore_scanners"], {"machinery_discount": 5}),
            ("automation_basics", "Automation Basics", 60, ["pneumatic_drills", "smelter_design"], {"machinery_discount": 5}),
            ("water_recycling", "Water Recycling", 40, ["survey"], {}),
            ("soil_science", "Soil Science", 40, ["survey"], {}),
            ("greenhouses", "Greenhouses", 50, ["water_recycling"], {"yield_pct": 1}),
            ("closed_loop_air", "Closed-Loop Air", 50, ["soil_science", "greenhouses"], {}),
            ("materials_lab", "Materials Lab", 50, ["survey"], {}),
            ("composites", "Composites", 50, ["materials_lab"], {"machinery_discount": 5}),
            ("lightweight_hulls", "Lightweight Hulls", 50, ["composites"], {}),
            ("launch_theory", "Launch Theory", 50, ["automation_basics"], {}),
            ("life_support_certification", "Life-Support Certification", 50, ["closed_loop_air"], {}),
            ("heat_shields", "Heat Shields", 50, ["lightweight_hulls"], {}),
            ("orbital_mechanics", "Orbital Mechanics", 60, ["launch_theory"], {"yield_pct": 1}),
            ("guidance_systems", "Guidance Systems", 60, ["heat_shields", "life_support_certification"], {"yield_pct": 1}),
            ("space_travel", "Space Travel", 70, ["orbital_mechanics", "guidance_systems"], {}),
            ("near_bodies", "Near Bodies", 70, ["space_travel"], {}),
        ],
    },
    {
        "name": "Far Bodies",
        "unlocks": ["Venus", "AsteroidBelt", "Pluto", "JupiterMoons", "SaturnMoons"],
        "rows": [
            ("far_survey", "Far Survey", 100, ["near_bodies"], {}),
            ("heat_resistant_alloys", "Heat-Resistant Alloys", 200, ["far_survey"], {"machinery_discount": 5}),
            ("atmospheric_probes", "Atmospheric Probes", 220, ["far_survey"], {}),
            ("belt_prospecting", "Belt Prospecting", 220, ["far_survey"], {"yield_pct": 1}),
            ("mining_drones", "Mining Drones", 260, ["belt_prospecting"], {"yield_pct": 2}),
            ("aerobraking", "Aerobraking", 240, ["heat_resistant_alloys", "atmospheric_probes"], {}),
            ("deep_space_comms", "Deep-Space Comms", 200, ["far_survey"], {}),
            ("radioisotope_power", "Radioisotope Power", 240, ["deep_space_comms"], {"yield_pct": 1}),
            ("cryo_materials", "Cryo Materials", 240, ["far_survey"], {"machinery_discount": 5}),
            ("ion_drives", "Ion Drives", 280, ["radioisotope_power", "cryo_materials"], {}),
            ("fusion_research", "Fusion Research", 320, ["ion_drives"], {"yield_pct": 2}),
            ("regolith_bricks", "Regolith Bricks", 200, ["far_survey"], {"route_discount": 5}),
            ("radiation_shielding", "Radiation Shielding", 240, ["regolith_bricks"], {}),
            ("closed_ecosystems", "Closed Ecosystems", 260, ["radiation_shielding"], {"yield_pct": 1}),
            ("sky_habitats", "Sky Habitats", 300, ["closed_ecosystems"], {"route_discount": 5}),
            ("long_haul_logistics", "Long-Haul Logistics", 300, ["aerobraking", "mining_drones"], {"route_discount": 5}),
            ("autonomous_refineries", "Autonomous Refineries", 300, ["fusion_research", "sky_habitats"], {"yield_pct": 2}),
            ("grand_navigation", "Grand Navigation", 340, ["long_haul_logistics", "ion_drives"], {}),
            ("outer_system_charts", "Outer-System Charts", 340, ["autonomous_refineries", "grand_navigation"], {}),
            ("far_bodies", "Far Bodies", 200, ["outer_system_charts"], {}),
        ],
    },
]

RESEARCH_NODES = []
RESEARCH_TIERS = []
for _level_index, _level in enumerate(_RESEARCH_LEVEL_ROWS):
    for _id, _name, _cost, _requires, _effects in _level["rows"]:
        RESEARCH_NODES.append({
            "id": _id, "name": _name, "cost": _cost, "requires": list(_requires),
            "effects": dict(_effects), "tier": _level_index,
        })
    RESEARCH_TIERS.append({
        "name": _level["name"],
        "target": sum(row[2] for row in _level["rows"]),
        "unlocks": list(_level["unlocks"]),
        "final": _level["rows"][-1][0],  # the last row of a level is always its final node
    })
RESEARCH_NODE_BY_ID = {node["id"]: node for node in RESEARCH_NODES}
RESEARCH_FUND_COST = 50  # legacy: the old flat per-click cost, kept for reference only

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
research_progress = 0.0  # Iron invested in the current level's researched nodes (derived, see _recompute_research())
completed_tiers = 0      # derived from researched_nodes, kept as a variable for its many readers
researched_nodes = set()
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
    {"id": "standing_orders", "tier": 2, "cost": 2, "min_level": PRESTIGE_TIER_2_LEVEL, "label": "Standing Orders",
     "desc": "Governor Doctrines hold 5 rules instead of 3."},
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
# A29: the total_ticks reading the first time every world was terraformed
# (None until then). Kept for life, like the other lifetime counters, so a
# later reset can't erase it. It is the score for the opt-in community
# "fastest full completion" leaderboard (shared/leaderboard.js).
full_system_completed_tick = None
_leaderboard_reported = False
# R-10: the fastest full playthrough, per RUN. `run_start_tick` is the
# total_ticks reading when this run began (0 at the start, reset by each
# prestige); `run_completed` marks that this run's completion has been
# recorded; `best_run_ticks` is the shortest completed run so far, kept for life.
run_start_tick = 0
run_completed = False
best_run_ticks = None
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


def research_effect(key):
    """Summed effect of every researched node for `key`, as a fraction."""
    return sum(RESEARCH_NODE_BY_ID[n]["effects"].get(key, 0) for n in researched_nodes) / 100.0


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
    if node["tier"] > completed_tiers:
        return "locked"
    if all(req in researched_nodes for req in node["requires"]):
        return "available"
    return "locked"


def _recompute_research():
    """Derives completed_tiers and research_progress from researched_nodes."""
    global completed_tiers, research_progress
    done = 0
    for tier in RESEARCH_TIERS:
        if tier["final"] in researched_nodes:
            done += 1
        else:
            break
    completed_tiers = done
    research_progress = float(sum(
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


def research_node_action(node_id):
    """Buys one node. Returns True if it was bought."""
    global quick_start_hit, swift_expansion_hit, off_the_grid_hit
    node = RESEARCH_NODE_BY_ID.get(node_id)
    if node is None or research_node_status(node) != "available":
        return False
    earth = planet_state["Earth"]
    cost = research_node_cost(node)
    if earth["resource_count"] < cost:
        return False
    earth["resource_count"] -= cost
    before = completed_tiers
    researched_nodes.add(node_id)
    _recompute_research()
    if completed_tiers > before:
        tier = RESEARCH_TIERS[before]
        unlocked_bodies.update(tier["unlocks"])
        for body in tier["unlocks"]:
            _note_split(body)
        update_travel_display()
        update_all_cross_summaries()
        # Second achievement wave (A2/A13) -- checked at the exact moment
        # each level completes, since that's the one instant both "how many
        # ticks has this playthrough taken" and "has a generator ever
        # existed anywhere" are meaningful to compare against a fixed line.
        if completed_tiers == 1:
            if total_ticks <= QUICK_START_TICKS:
                quick_start_hit = True
            if not any_generator_ever_built:
                off_the_grid_hit = True
        if completed_tiers == len(RESEARCH_TIERS) and total_ticks <= SWIFT_EXPANSION_TICKS:
            swift_expansion_hit = True
    _player_action("research", "Earth")
    return True


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
    base = 0.9 if prestige_has("cheaper_machinery") else 1.0
    if mutator_active("costly_machinery"):
        base *= MUTATOR_COSTLY_FACTOR  # A-3: an opt-in rule twist, paid for in prestige points
    return base * (1.0 - research_effect("machinery_discount"))


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
    return TERRAFORM_BASE_RATE_PER_SEC * (health / 100) * anomaly_factor("terraform") * megaproject_factor("terraform")


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
    progress_pct = (research_progress / tier["target"]) * 100
    document.getElementById("research-bar").style.width = f"{progress_pct}%"
    progress_el.innerText = f"{math.floor(research_progress)} / {tier['target']}"
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
    tier_index = completed_tiers
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
    badge.innerText = (
        f"{era_for_level(prestige_level)['label']} \u00b7 Prestige {prestige_level}{mutator_glyphs(mutators_run)}"
        if prestige_level > 0 else ""
    )
    _apply_era()
    badge.title = ("Your current Prestige level" + mutator_rules_text(mutators_run)) if prestige_level > 0 else ""
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
    # Round-3 batch: both are lifetime records, so a prestige never un-earns them.
    "in_rhythm": lambda: best_click_streak >= IN_RHYTHM_STREAK,
    "chain_reactor": lambda: chains_found() >= len(CHAINS),
    # Round-4 batch: all four are lifetime collections, so a prestige never un-earns them.
    "codex_keeper": lambda: len(codex_found) >= len(CLUES),
    "weather_watcher": lambda: len(anomalies_seen) >= len(ANOMALIES),
    "charter_member": lambda: len(mission_stamps) >= CHARTER_MEMBER_STAMPS,
    "great_works": lambda: megaprojects_all_ever,
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
    "in_rhythm": lambda: (min(best_click_streak, IN_RHYTHM_STREAK), IN_RHYTHM_STREAK),
    "chain_reactor": lambda: (chains_found(), len(CHAINS)),
    "codex_keeper": lambda: (len(codex_found), len(CLUES)),
    "weather_watcher": lambda: (len(anomalies_seen), len(ANOMALIES)),
    "charter_member": lambda: (min(len(mission_stamps), CHARTER_MEMBER_STAMPS), CHARTER_MEMBER_STAMPS),
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


def _report_full_completion():
    """A29: hands the completion time to the shared leaderboard widget, which
    only submits when this player has opted in and is signed in. Reported once
    per page load; the server keeps just the best score anyway."""
    global _leaderboard_reported
    if full_system_completed_tick is None or _leaderboard_reported:
        return
    _leaderboard_reported = True
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    board = getattr(window, "NoyvjLeaderboard", None)
    if board is None:
        return
    seconds = full_system_completed_tick * (TICK_INTERVAL_MS / 1000)
    board.report("sol", "fastest_completion", seconds, f"prestige {prestige_level}")


def _note_full_completion():
    global full_system_completed_tick, run_completed, best_run_ticks
    finished = _terraformed_planet_count() >= len(PLANETS)
    if full_system_completed_tick is None and finished:
        full_system_completed_tick = total_ticks
    if finished and not run_completed:
        run_completed = True
        duration = max(0, total_ticks - run_start_tick)
        _note_split("full")
        if best_run_ticks is None or duration < best_run_ticks:
            pb_splits.clear()
            pb_splits.update(run_splits)  # A-30: the new personal-best run's splits
        best_run_ticks = duration if best_run_ticks is None else min(best_run_ticks, duration)
    _report_full_completion()


def best_run_text():
    """R-10: the personal-best playthrough line for the stats panel."""
    if best_run_ticks is None:
        return "not yet (terraform every world to set it)"
    return _format_duration(best_run_ticks * (TICK_INTERVAL_MS / 1000))


# ===========================================================================
# Round-3 SOL batch: rhythm streak (A-26), speedrun splits (A-30), trophy
# shelf (A-31), chain reactions (A-25), Governor mood (A-22). None of it
# changes a cost, a cap or an unlock; the two small yield effects (the streak
# and a chain's bonus) are capped, and both have an off switch in Settings.
# ===========================================================================

# Browser preferences from the Settings panel (settings.js keeps them in
# localStorage as "on"/"off"; anything but "off" counts as on, so a fresh
# browser gets the defaults and a locked-down one that cannot read storage
# does too).
CLICK_STREAK_KEY = "sol-click-streak"
CHAIN_BONUS_KEY = "sol-chain-bonus"


def _setting_on(key):
    return _read_local_storage_item(key) != "off"


# --- A-26: a soft click-rhythm meter ---------------------------------------
# Manual clicks that follow each other within STREAK_WINDOW_TICKS (1.5 s of
# game time) build a streak; every STREAK_CLICKS_PER_PCT clicks of it adds 1%
# to a manual click's yield, up to STREAK_MAX_BONUS_PCT. Automation is never
# touched, so it stays a nudge for hands that are already clicking, never a
# reason to click. The streak itself is transient; only the best one is saved.
STREAK_WINDOW_TICKS = 15
STREAK_CLICKS_PER_PCT = 10
STREAK_MAX_BONUS_PCT = 5
STREAK_SHOW_AT = 3
IN_RHYTHM_STREAK = 40
click_streak = 0
best_click_streak = 0
_streak_last_tick = None


def streak_bonus_pct():
    return min(STREAK_MAX_BONUS_PCT, click_streak // STREAK_CLICKS_PER_PCT)


def render_click_streak():
    el = document.getElementById("click-streak")
    visible = click_streak >= STREAK_SHOW_AT
    el.hidden = not visible
    if not visible:
        el.innerText = ""
        return
    pct = streak_bonus_pct()
    bonus = f"+{pct}% mining yield" if pct else f"bonus starts at {STREAK_CLICKS_PER_PCT}"
    el.innerText = f"Rhythm streak: {click_streak} ({bonus})"


def _streak_click():
    """Registers one manual click and returns its yield multiplier."""
    global click_streak, best_click_streak, _streak_last_tick
    if not _setting_on(CLICK_STREAK_KEY):
        if click_streak:
            click_streak = 0
            render_click_streak()
        _streak_last_tick = None
        return 1.0
    if _streak_last_tick is not None and total_ticks - _streak_last_tick <= STREAK_WINDOW_TICKS:
        click_streak += 1
    else:
        click_streak = 1
    _streak_last_tick = total_ticks
    best_click_streak = max(best_click_streak, click_streak)
    render_click_streak()
    return 1.0 + streak_bonus_pct() / 100.0


def _decay_click_streak():
    """Called every tick: a streak ends once the player stops clicking."""
    global click_streak
    if click_streak and (_streak_last_tick is None or total_ticks - _streak_last_tick > STREAK_WINDOW_TICKS):
        click_streak = 0
        render_click_streak()


# --- A-30: speedrun splits --------------------------------------------------
# A split is how far into the current run (in game time, the same clock the
# other run records use) a world was first unlocked; "full" is the whole
# system terraformed. The personal best is the splits of the fastest completed
# run, so a run is compared against one real run rather than a patchwork of
# best segments. Both are shown only when "Show timing" is on in Settings.
SPLIT_KEYS = ["Moon", "Mars", "Venus", "AsteroidBelt", "Pluto", "JupiterMoons", "SaturnMoons", "full"]
run_splits = {}
pb_splits = {}
splits_open = False


def _note_split(key):
    if key in SPLIT_KEYS and key not in run_splits:
        run_splits[key] = max(0, total_ticks - run_start_tick)


def _clean_splits(raw):
    cleaned = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            if key in SPLIT_KEYS and isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 10 ** 12:
                cleaned[key] = value
    return cleaned


def _split_time(ticks):
    return _format_duration(ticks * (TICK_INTERVAL_MS / 1000))


def _split_delta(ticks, best_ticks):
    """Signed difference as text ('+0m 12s', '-5s', 'same'), never colour alone."""
    diff = (ticks - best_ticks) * (TICK_INTERVAL_MS / 1000)
    if abs(diff) < 0.5:
        return "same as best"
    return ("+" if diff > 0 else "-") + _format_duration(abs(diff))


def split_label(key):
    return "Whole system terraformed" if key == "full" else PLANET_DISPLAY_NAMES.get(key, key)


def on_toggle_splits(event=None):
    global splits_open
    splits_open = not splits_open
    update_splits_display()


def update_splits_display():
    toggle = document.getElementById("splits-toggle-button")
    panel = document.getElementById("splits-panel")
    toggle.innerText = "Hide Splits" if splits_open else "⏱️ Splits"
    panel.hidden = not splits_open
    if not splits_open:
        return
    panel.innerHTML = ""
    heading = document.createElement("h2")
    heading.className = "stats-panel-heading"
    heading.innerText = "Speedrun splits"
    panel.appendChild(heading)
    intro = document.createElement("p")
    intro.className = "splits-intro"
    intro.innerText = (
        "Time into this run when each world was unlocked, in game time. Your personal best is the "
        "run with the fastest full playthrough; each row says how far ahead (-) or behind (+) it you are."
    )
    panel.appendChild(intro)
    for key in SPLIT_KEYS:
        row = document.createElement("p")
        row.className = "splits-row"
        mine = run_splits.get(key)
        best = pb_splits.get(key)
        if mine is None:
            text = f"{split_label(key)}: not yet"
            if best is not None:
                text += f" (best {_split_time(best)})"
        elif best is None:
            text = f"{split_label(key)}: {_split_time(mine)} (no personal best yet)"
        else:
            text = f"{split_label(key)}: {_split_time(mine)} (best {_split_time(best)}, {_split_delta(mine, best)})"
        row.innerText = text
        panel.appendChild(row)


# --- A-31: trophy shelf ------------------------------------------------------
TROPHY_SHELF_SIZE = 5
TROPHY_HISTORY_MAX = 12
TROPHY_GLYPHS = ["🥇", "🏅", "⭐", "🌟", "🪐", "🚀", "☄️", "🛰️"]
recent_trophies = []  # achievement ids, oldest first
_trophy_fresh_id = None  # the badge to flourish, only for an unlock this session


def _trophy_ids_for_shelf():
    earned = set(achievement_ids_earned())
    return [aid for aid in reversed(recent_trophies) if aid in earned][:TROPHY_SHELF_SIZE]


def render_trophy_shelf():
    shelf = document.getElementById("trophy-shelf")
    shown = _trophy_ids_for_shelf()
    shelf.hidden = not shown
    shelf.innerHTML = ""
    by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
    index_of = {entry["id"]: i for i, entry in enumerate(ACHIEVEMENTS)}
    for aid in shown:
        entry = by_id[aid]
        badge = document.createElement("span")
        badge.className = "trophy-badge" + (" trophy-badge--new" if aid == _trophy_fresh_id else "")
        badge.setAttribute("role", "listitem")
        badge.title = entry["description"]
        glyph = document.createElement("span")
        glyph.className = "trophy-glyph"
        glyph.setAttribute("aria-hidden", "true")
        glyph.innerText = TROPHY_GLYPHS[index_of[aid] % len(TROPHY_GLYPHS)]
        badge.appendChild(glyph)
        label = document.createElement("span")
        label.className = "trophy-label"
        label.innerText = entry["label"]
        badge.appendChild(label)
        shelf.appendChild(badge)


def _note_trophies(new_ids):
    global _trophy_fresh_id
    order = {entry["id"]: i for i, entry in enumerate(ACHIEVEMENTS)}
    for aid in sorted(new_ids, key=lambda a: order.get(a, 0)):
        if aid in recent_trophies:
            recent_trophies.remove(aid)
        recent_trophies.append(aid)
        _trophy_fresh_id = aid
    del recent_trophies[:-TROPHY_HISTORY_MAX]
    render_trophy_shelf()


# --- A-25: chain reactions ----------------------------------------------------
# Doing the right short sequence of actions inside CHAIN_WINDOW_TICKS (60 s of
# game time) fires a small bonus. Only your own actions count (the Governor's
# purchases do not). Mining many times in a row is a single "mine" entry;
# every other action is its own entry. A step's world is a name, None (anywhere) or
# "*" (anywhere, but every "*" step in the chain must be a different world).
# Each chain can fire again after CHAIN_COOLDOWN_TICKS, so the page is a
# collection to complete rather than a farm. Every chain shows a hint until
# found and its full recipe afterwards.
CHAIN_WINDOW_TICKS = 600
CHAIN_COOLDOWN_TICKS = 1200
CHAIN_REWARD_BASE = 40
CHAIN_REWARD_PER_GENERATOR = 4
ACTION_LOG_MAX = 24
CHAINS = [
    {
        "id": "spin_up", "name": "Spin-Up",
        "steps": [("mine", "Earth"), ("gen", "Earth"), ("mine", "Earth")],
        "recipe": "On Earth: mine, buy an Auto-Miner, then mine again.",
        "hint": "Warm up the first world: dig, build, dig.",
    },
    {
        "id": "whistle_stop", "name": "Whistle-Stop",
        "steps": [("travel", None), ("travel", None), ("travel", None)],
        "recipe": "Make three trips between worlds within a minute.",
        "hint": "Three trips in one minute.",
    },
    {
        "id": "closed_loop", "name": "Closed Loop",
        "steps": [("route", None), ("rec", None), ("research", None)],
        "recipe": "Open a trade route, build a Recycler (anywhere), then buy a research node.",
        "hint": "Open a route, clean up after yourself, then think about the future.",
    },
    {
        "id": "mars_landing", "name": "Mars Landing",
        "steps": [("travel", "Mars"), ("mine", "Mars"), ("gen", "Mars")],
        "recipe": "Travel to Mars, mine there, then buy an Auto-Extractor.",
        "hint": "Land on the red planet and get to work straight away.",
    },
    {
        "id": "spread_thin", "name": "Spread Thin",
        "steps": [("gen", "*"), ("gen", "*"), ("gen", "*")],
        "recipe": "Buy an automation building on three different worlds within a minute (travelling between them).",
        "hint": "Automation on three different worlds in one minute.",
    },
    {
        "id": "skyward", "name": "Skyward",
        "steps": [("sky", None), ("route", None)],
        "recipe": "Build a Sky City, then open a trade route.",
        "hint": "After the clouds get a city, the cargo ships follow.",
    },
    {
        "id": "scholars_dash", "name": "Scholar's Dash",
        "steps": [("research", None), ("research", None), ("research", None)],
        "recipe": "Buy three research nodes within a minute.",
        "hint": "Three research nodes in one minute.",
    },
]
CHAIN_BY_ID = {chain["id"]: chain for chain in CHAINS}
chain_counts = {}  # chain id -> times fired, for life
chains_open = False
_action_log = []  # (tick, kind, planet), oldest first, collapsed, never saved
_chain_cooldown_until = {}


def chains_found():
    return sum(1 for chain in CHAINS if chain_counts.get(chain["id"], 0) > 0)


def _step_matches(step, record, used):
    kind, planet = step
    if record[1] != kind:
        return False
    if planet is None:
        return True
    if planet == "*":
        return record[2] not in used
    return record[2] == planet


def _chain_match(steps, records):
    """True when `steps` occur in order among `records` (not necessarily
    adjacent), the last step on the newest record."""
    if len(records) < len(steps) or not _step_matches(steps[-1], records[-1], frozenset()):
        return False

    def search(step_index, record_index, used):
        if step_index < 0:
            return True
        for i in range(record_index, -1, -1):
            if _step_matches(steps[step_index], records[i], used):
                next_used = used | {records[i][2]} if steps[step_index][1] == "*" else used
                if search(step_index - 1, i - 1, next_used):
                    return True
        return False

    last_used = frozenset({records[-1][2]}) if steps[-1][1] == "*" else frozenset()
    return search(len(steps) - 2, len(records) - 2, last_used)


def _chain_reward(planet):
    state = planet_state[planet]
    return (CHAIN_REWARD_BASE + CHAIN_REWARD_PER_GENERATOR * state["generator_count"]) * _yield_multiplier()


def _fire_chain(chain, planet):
    _chain_cooldown_until[chain["id"]] = total_ticks + CHAIN_COOLDOWN_TICKS
    first = chain_counts.get(chain["id"], 0) == 0
    chain_counts[chain["id"]] = chain_counts.get(chain["id"], 0) + 1
    bonus = _chain_reward(planet)
    planet_state[planet]["resource_count"] += bonus
    update_resource_display(planet)
    unit = PLANETS[planet]["resource_name"]
    prefix = "⚡ New chain reaction" if first else "⚡ Chain reaction"
    _display_toast(f"{prefix}: {chain['name']}! +{math.floor(bonus)} {unit}")
    update_chains_display()


def _check_chains(planet):
    for chain in CHAINS:
        if total_ticks < _chain_cooldown_until.get(chain["id"], -1):
            continue
        records = [r for r in _action_log if r[0] >= total_ticks - CHAIN_WINDOW_TICKS]
        if _chain_match(chain["steps"], records):
            _fire_chain(chain, planet)


def _player_action(kind, planet):
    """Every action the player takes themselves passes through here: it
    counts towards that world's 'micromanagement' (A-22) and feeds the chain
    reactions. kind: mine | gen | rec | route | sky | travel | research."""
    if kind not in ("travel", "research"):
        state = planet_state[planet]
        state["player_actions"] = state.get("player_actions", 0) + 1
    if kind == "mine" and _action_log and _action_log[-1][1] == kind and _action_log[-1][2] == planet:
        _action_log[-1] = (total_ticks, kind, planet)
    else:
        _action_log.append((total_ticks, kind, planet))
        del _action_log[:-ACTION_LOG_MAX]
    if _setting_on(CHAIN_BONUS_KEY):
        _check_chains(planet)


def on_toggle_chains(event=None):
    global chains_open
    chains_open = not chains_open
    update_chains_display()


def update_chains_display():
    toggle = document.getElementById("chains-toggle-button")
    panel = document.getElementById("chains-panel")
    found = chains_found()
    toggle.innerText = (
        f"Hide Chain Reactions ({found}/{len(CHAINS)})" if chains_open else f"⚡ Chain Reactions ({found}/{len(CHAINS)})"
    )
    panel.hidden = not chains_open
    if not chains_open:
        return
    panel.innerHTML = ""
    heading = document.createElement("h2")
    heading.className = "stats-panel-heading"
    heading.innerText = f"Chain reactions: {found} of {len(CHAINS)} found"
    panel.appendChild(heading)
    intro = document.createElement("p")
    intro.className = "chains-intro"
    intro.innerText = (
        "Do the right actions in the right order within a minute and a small bonus drops into that world. "
        "Each one can fire again after a couple of minutes. The Governor's purchases do not count. "
        "Turn the bonus off in Settings if you would rather not."
    )
    panel.appendChild(intro)
    for chain in CHAINS:
        count = chain_counts.get(chain["id"], 0)
        card = document.createElement("div")
        card.className = "chain-card chain-card--found" if count else "chain-card"
        name = document.createElement("p")
        name.className = "chain-card-name"
        name.innerText = f"⚡ {chain['name']}" if count else "Not found yet"
        card.appendChild(name)
        detail = document.createElement("p")
        detail.className = "chain-card-detail"
        detail.innerText = chain["recipe"] if count else f"Hint: {chain['hint']}"
        card.appendChild(detail)
        if count:
            times = document.createElement("p")
            times.className = "chain-card-count"
            times.innerText = f"Found, fired {count} time{'s' if count != 1 else ''}"
            card.appendChild(times)
        panel.appendChild(card)


# --- A-22: the Governor's mood ---------------------------------------------------
MOOD_ATTENTIVE_ACTIONS = 10
MOOD_HOVERING_ACTIONS = 100
GOVERNOR_MOODS = {
    "aggressive": (
        "Delighted to be left alone: has already ordered three more Auto-Miners and is not sorry.",
        "Tolerates your visits, as long as you do not touch the throttle.",
        "Says this is the fourth time you have rearranged its crates today.",
    ),
    "balanced": (
        "Serene. Has made a spreadsheet about it and the spreadsheet is happy.",
        "Notes your fingerprints on the ledger, politely.",
        "Is pretending not to notice you hovering over the buttons.",
    ),
    "conservative": (
        "Quietly pleased. Has recycled the paperwork twice already.",
        "Would like to remind you that every click has an ecological cost.",
        "Sighs, and files a complaint about unscheduled enthusiasm.",
    ),
}
GLOBAL_PRIORITY_PERSONALITY = {"growth": "aggressive", "balance": "balanced", "ecology": "conservative"}


def governor_mood(planet):
    state = planet_state[planet]
    personality = state.get("governor_personality", "default")
    if personality not in GOVERNOR_MOODS:
        personality = GLOBAL_PRIORITY_PERSONALITY.get(governor_priority, "balanced")
    actions = state.get("player_actions", 0)
    level = 0 if actions < MOOD_ATTENTIVE_ACTIONS else (1 if actions < MOOD_HOVERING_ACTIONS else 2)
    return GOVERNOR_MOODS[personality][level]


def _check_new_achievements_for_toast():
    """Called every tick(): compares the live earned set against the last
    snapshot, and pops a toast for anything newly earned since then. Never
    called from _full_render() itself -- see _seed_achievement_toast_baseline
    above for why a load must never diff against a stale/empty baseline."""
    global _achievements_seen_ids
    _note_full_completion()
    if _note_story_beats():
        render_story_log()
    earned_now = set(achievement_ids_earned())
    newly = earned_now - _achievements_seen_ids
    if newly:
        for aid in sorted(newly):
            story_note(f"ach:{aid}")
        render_story_log()
        _note_trophies(newly)
        by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
        labels = [by_id[aid]["label"] for aid in newly if aid in by_id]
        if labels:
            if len(labels) == 1:
                _display_toast(f"🏆 Achievement unlocked: {labels[0]}")
            else:
                _display_toast(f"🏆 {len(labels)} achievements unlocked: " + ", ".join(labels))
    _achievements_seen_ids = earned_now


# ===========================================================================
# A25 -- the captain's log: a light narrative thread through the run. Every
# first arrival at a world and every achievement earned adds one line to a log
# (recorded whether or not story text is showing, so switching the "Story"
# pill on later reveals the whole history). The latest line sits under the title
# as a banner and the full log is a collapsible list; both are listed as story
# elements for shared/story-toggle.js, so the existing Story pill turns them on
# and off. The lines are the achievements' own descriptions plus one short
# arrival line per world; nothing here changes any number or unlock.
# ===========================================================================
STORY_LOG_MAX = 80
STORY_ARRIVAL_LINES = {
    "Earth": "Log opened. One planet, one pile of iron, and a long way to go.",
    "Mars": "Mars: red dust, thin air, and the first place that feels like somewhere else.",
    "Moon": "The Moon: quiet, close, and a good place to keep the ledger honest.",
    "Venus": "Venus: hot enough to teach patience, thick enough to hide a lot of possibilities.",
    "AsteroidBelt": "The Belt: no ground to stand on, just rock to mine and a lot of room.",
    "Pluto": "Pluto: the edge of the map, cold and slow, and yours anyway.",
    "JupiterMoons": "Jupiter's moons: a small system inside the system, with a giant for a neighbour.",
    "SaturnMoons": "Saturn's moons: rings overhead, and one more world that needs a plan.",
}
# W1-sol: the deeper story. Longer beats for the things that mark a run's arc,
# noted by _note_story_beats() (called every tick from the achievement check):
# each world finished terraforming, the first trade route, and each prestige.
STORY_TERRAFORM_LINES = {
    "Earth": "Earth is finished. The oceans hold, the air is clean, and the pile of iron you started with is now a planet that looks after itself. It only took the whole rest of the system to get here.",
    "Mars": "Mars is green at the edges. The first rain in four billion years is only a drizzle, but the crews stand out in it anyway, and no one mentions the cost.",
    "Moon": "The Moon has an atmosphere now, thin and borrowed, and a horizon that finally looks lived in. From Earth it is a little brighter at night.",
    "Venus": "Venus has cooled. The furnace that scared everyone off is a warm, cloudy world with rivers where nobody expected them, and the patience paid off exactly as slowly as promised.",
    "AsteroidBelt": "The Belt is not a wasteland any more. Its rock is worked, its habitats are lit and its people are numerous enough to have opinions about the rest of the system.",
    "Pluto": "Pluto is warm enough to stand on without a second thought. At the far edge of everything, someone has hung a light in a window.",
    "JupiterMoons": "Jupiter's moons are a system of their own now, with cities under the ice and harbours in the shadow of a giant that does not seem to mind.",
    "SaturnMoons": "Saturn's moons are settled. The rings hang overhead like a promise kept, and the last world on the list has a name and a home in it.",
}
STORY_ROUTE_LINE = "The first trade route runs. A world that only ever produced one thing now has a customer, and the ledger stops being a private matter between you and the ground."
STORY_PRESTIGE_LINE = "You start again, but not from nothing. The routes are gone and the machines are dust, and yet you remember exactly what worked, and the new run begins with that instead of hope."
story_log = []


def story_note(entry_id):
    """Adds an entry id ("arrive:<world>" or "ach:<achievement id>") once."""
    if entry_id in story_log:
        return False
    story_log.append(entry_id)
    del story_log[:-STORY_LOG_MAX]
    return True


def story_line(entry_id):
    """The display text for a log entry id, or None if it is not a known one."""
    kind, _, key = entry_id.partition(":")
    if kind == "arrive":
        return STORY_ARRIVAL_LINES.get(key)
    if kind == "terraform":
        return STORY_TERRAFORM_LINES.get(key)
    if entry_id == "route:first":
        return STORY_ROUTE_LINE
    if kind == "prestige" and key == "1":
        return STORY_PRESTIGE_LINE
    if kind == "ach":
        for entry in ACHIEVEMENTS:
            if entry["id"] == key:
                return f"{entry['label']}: {entry['description']}"
    return None


def story_log_lines():
    """Every log line, oldest first (unknown ids skipped)."""
    return [line for line in (story_line(e) for e in story_log) if line]


def _note_story_beats():
    """Notes the longer beats (idempotent): a finished world, the first trade
    route, the first prestige."""
    changed = False
    for planet, planet_data in planet_state.items():
        if planet_data["terraform_progress"] >= TERRAFORM_MAX:
            changed = story_note(f"terraform:{planet}") or changed
    if _total_trade_routes_built_now():
        changed = story_note("route:first") or changed
    if prestige_level >= 1:
        changed = story_note("prestige:1") or changed
    return changed


def _total_trade_routes_built_now():
    return sum(sum(data["trade_routes"].values()) for data in planet_state.values()) > 0


def render_story_log():
    latest = document.getElementById("captains-log-latest")
    panel = document.getElementById("captains-log")
    list_el = document.getElementById("captains-log-list")
    lines = story_log_lines()
    latest.hidden = not lines
    latest.innerText = f"Captain's log: {lines[-1]}" if lines else ""
    panel.hidden = not lines
    list_el.innerHTML = ""
    for line in reversed(lines):
        item = document.createElement("li")
        item.innerText = line
        list_el.appendChild(item)


def _mark_visited(planet):
    first_visit = planet not in visited_bodies
    visited_bodies.add(planet)
    if first_visit or planet == "Earth":
        story_note(f"arrive:{planet}")
        render_story_log()


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
        card.dataset.achievementId = entry["id"]

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

    _request_achievement_stats()


def _request_achievement_stats():
    """Z27b: asks the page's optional JS hook (window.applyAchievementStats,
    shared/achievement-stats.js) to fill in each achievement card's own
    "Earned by N% of players" line from the cross-player stats endpoint
    (planning/TODO.md Z1). Absent hook (pytest, or a page without the
    shared script) leaves the cards exactly as rendered above -- same
    fails-soft shape as Grid's C15 window.gridCompare."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "applyAchievementStats", None)
    if hook is not None:
        hook()


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

        mood = document.createElement("p")
        mood.className = "governor-report-card-mood"
        mood.innerText = f"Mood: {governor_mood(planet)}"
        card.appendChild(mood)

        if doctrines_unlocked():
            doctrine_line = document.createElement("p")
            doctrine_line.className = "governor-report-card-doctrine"
            doctrine_line.innerText = doctrine_report_line(planet)
            card.appendChild(doctrine_line)

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
    if mutators_run:
        lines.append(f"Run rules: {mutator_glyphs(mutators_run).strip()} " + ", ".join(
            MUTATOR_BY_ID[m_id]["label"] for m_id in mutators_run))
    return "\n".join(lines)


def copy_result_fields():
    """Z-20: the fields shared/copy-result.js turns into one pasteable line,
    e.g. "SOL, 100% terraformed, 9/9 worlds fully terraformed, ...". Read by
    the page's own inline script through pyodide.globals when the shared
    Copy result button is pressed, so it always matches the run right now."""
    terraform_values = [planet_state[p]["terraform_progress"] for p in PLANETS]
    average = round(sum(terraform_values) / len(terraform_values))
    stats = [
        f"{_terraformed_planet_count()}/{len(PLANETS)} worlds fully terraformed",
        f"{len(achievement_ids_earned())}/{len(ACHIEVEMENTS)} achievements",
        "played " + _format_duration(_lifetime_playtime_seconds()),
    ]
    if prestige_level > 0:
        stats.append(f"prestige {prestige_level}")
    if mutators_run:
        stats.append("rules: " + ", ".join(MUTATOR_BY_ID[m_id]["label"] for m_id in mutators_run))
    return {"game": "SOL", "score": f"{average}%", "unit": "terraformed", "stats": stats}


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
        ("Fastest full playthrough", best_run_text()),
        ("Best rhythm streak", str(best_click_streak)),
        ("Chain reactions found", f"{chains_found()}/{len(CHAINS)}"),
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
    gained = 1 * _yield_multiplier() * _streak_click() * anomaly_factor("click") * (1 + stamp_bonus(planet))
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
    _player_action("mine", planet)


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
        _player_action("gen", planet)
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
        _player_action("rec", planet)
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
            _player_action("route", planet)
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
        _player_action("sky", planet)
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


def on_research_node_click(event):
    node_id = _target_attr(event, "data-node")
    if not node_id:
        return
    if research_node_action(node_id):
        update_resource_display("Earth")
        update_research_display()
        update_research_tree_display()


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
    _player_action("travel", planet)
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
#
# Z22 cross-game audit: this used to gate on a native browser confirm()
# dialog (`_confirm()`, a lazy `import js` per call). That predated
# shared/confirm-dialog.js entirely -- SOL is one of two games flagged as
# such (Aftermath's skill-tree reset is the other). Migrated to the shared
# ConfirmDialog for the same reasons every other game's reset/retire-style
# action already gets it: a native confirm() blocks Pyodide's whole event
# loop, can't offer "don't ask me again," and looks nothing like the rest
# of this site. Same `_confirm_dialog_ask()` helper shape as Grid's/Herd's/
# Loop's/Trade Empire's own copies (lazy `from js import window`, fall
# through to calling on_confirm() immediately when `window` or
# `window.ConfirmDialog` isn't available -- which is what the pytest
# fake-DOM harness's `js` module does by default, and what a page that
# somehow loaded without confirm-dialog.js would do too).
def _confirm_dialog_ask(action_id, message, confirm_label, on_confirm):
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        on_confirm()
        return
    confirm_dialog = getattr(window, "ConfirmDialog", None)
    if confirm_dialog is None:
        on_confirm()
        return
    confirm_dialog.ask(
        id=action_id,
        message=message,
        confirmLabel=confirm_label,
        onConfirm=create_proxy(on_confirm),
    )


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
        "player_actions": 0,
    }
    if planet in GAS_GIANT_BODIES:
        fresh["sky_city_count"] = 0
    return fresh


def _reset_world(planet):
    display_name = PLANET_DISPLAY_NAMES.get(planet, planet)

    def _do_reset():
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

    _confirm_dialog_ask(
        action_id=f"sol-reset-world-{planet}",
        message=(
            f"Reset {display_name}? This clears its resources, buildings, ecology, "
            "trade routes, and terraforming progress. Research, travel, and "
            "achievements are not affected. This cannot be undone."
        ),
        confirm_label=f"Reset {display_name}",
        on_confirm=_do_reset,
    )


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
    panel.appendChild(_make_text(
        "overview-card-note",
        "Field notes: a few worlds end their note with an odd sentence. Somebody should try doing what it says."))
    # A-14: one progress ring per megaproject, so the whole system's effort shows at a glance.
    rings = document.createElement("div")
    rings.className = "overview-rings"
    rings.setAttribute("aria-label", "Megaproject progress")
    _overview_refs["_rings"] = {}
    for project in MEGAPROJECTS:
        cell = document.createElement("span")
        cell.className = "overview-ring-cell"
        ring = _ring(megaproject_percent(project["id"]))
        cell.appendChild(ring)
        cell.appendChild(_make_text("overview-ring-name", project["label"], "span"))
        rings.appendChild(cell)
        _overview_refs["_rings"][project["id"]] = ring
    panel.appendChild(rings)

    for planet in _overview_planets():
        state = planet_state[planet]
        card = document.createElement("div")
        card.className = "overview-card" + (" overview-card--current" if planet == current_planet else "")

        title = _make_text(
            "overview-card-title",
            PLANET_DISPLAY_NAMES.get(planet, planet) + (" (you are here)" if planet == current_planet else ""),
        )
        card.appendChild(title)
        if planet in WORLD_NOTES:
            card.appendChild(_make_text("overview-card-note", WORLD_NOTES[planet]))
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
    for pid, ring in _overview_refs.get("_rings", {}).items():
        percent = megaproject_percent(pid)
        ring.style.background = (
            f"conic-gradient(var(--mega-ring-fill, #6fb3ff) {percent * 3.6}deg, var(--mega-ring-rest, #2a3350) 0)")
        ring.innerText = f"{round(percent)}%"
        ring.setAttribute("aria-label", f"{round(percent)} percent built")
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
        stamps = stamps_for(planet)
        if stamps:
            bits.append(f"Charter stamps: {STAMP_STAR * stamps} (+{stamps}% yield)")
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


def build_plan_tsv():
    """A-24: the plan as tab-separated rows (step number, text, done) that
    paste straight into a spreadsheet; tabs and line breaks inside a step are
    flattened to spaces so every step stays on its own row."""
    rows = ["Step\tWhat\tDone"]
    for number, step in enumerate(build_plan, start=1):
        text = " ".join(step["text"].replace("\t", " ").split())
        rows.append(f"{number}\t{text}\t{'yes' if step['done'] else 'no'}")
    return "\n".join(rows)


def on_build_plan_copy(event=None):
    text = build_plan_tsv()
    status = document.getElementById("build-plan-copy-status")
    output = document.getElementById("build-plan-copy-output")
    output.value = text

    def _manual(*args):
        output.hidden = False
        status.innerText = "Could not reach the clipboard: select the text below and copy it yourself."

    if not build_plan:
        output.hidden = True
        status.innerText = "Nothing to copy yet: add a step first."
        return
    try:
        import js  # noqa: PLC0415

        promise = js.navigator.clipboard.writeText(text)
        output.hidden = True
        status.innerText = "Copied as tab-separated rows: paste into a spreadsheet."
        catch = getattr(promise, "catch", None)
        if catch is not None:
            def _failed(*args):
                proxy.destroy()
                _manual()

            proxy = create_proxy(_failed)
            catch(proxy)
    except (ImportError, AttributeError):
        _manual()


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
    # A-3: the mutator picks are made here, so the panel is also open to a player who is about to prestige.
    toggle.hidden = prestige_level <= 0 and not _prestige_available()
    available = prestige_points_available()
    toggle.innerText = "Hide Prestige Tree" if prestige_tree_open else f"🌳 Prestige Tree ({available})"
    panel.hidden = not (prestige_tree_open and not toggle.hidden)
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
    _build_mutator_cards(panel)
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
    elif action == "mutator":
        _toggle_mutator_pick(_target_attr(event, "data-mutator"))
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
    if megaprojects_all_ever:
        paragraphs.insert(1, (
            "And above it all hang the four great works: the Orbital Mirror, the Ring Habitat, the Dyson Sail "
            "and the Deep Core Tap, built with something from every world. Seen from Pluto, the inner system "
            "is one slow, patient light."))
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
    # Z8: codec now lives in shared/export_progress.py (the "portable
    # progress-code" pattern shared with Aftermath's E12) -- behavior is
    # unchanged, same STATS_CODE_PREFIX, same flat-counter payload.
    payload = {name: globals()[name] for name in _STATS_CODE_FIELDS}
    payload["prestige_level"] = prestige_level
    return export_progress.encode_progress_code(payload, prefix=STATS_CODE_PREFIX)


def import_stats_code(code):
    """Returns (ok, message). Only ever raises a counter, never lowers one, so
    a stale code from an old device can't undo newer progress."""
    ok, payload = export_progress.decode_progress_code(
        code, prefix=STATS_CODE_PREFIX, bad_format_message="That doesn't look like a SOL stats code."
    )
    if not ok:
        return False, payload
    if not export_progress.validate_numeric_fields(payload, _STATS_CODE_FIELDS):
        return False, "That stats code has invalid values."
    merged = export_progress.merge_counters_max(
        {name: globals()[name] for name in _STATS_CODE_FIELDS}, payload, _STATS_CODE_FIELDS
    )
    for name in _STATS_CODE_FIELDS:
        globals()[name] = merged[name]
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
    # No `global` needed here -- `prestige_level` is only read (for
    # `next_level`/`next_bonus_pct`'s preview text below); every actual
    # mutation happens inside `_do_prestige()`, which declares its own.
    if not _prestige_available():
        return

    next_level = prestige_level + 1
    next_bonus_pct = round(PRESTIGE_BONUS_PER_LEVEL * next_level * 100)

    def _do_prestige():
        global prestige_level, unlocked_bodies, visited_bodies
        global current_planet, governor_priority, governor_budget_pct, governor_tick_count
        global governor_purchase_count, any_generator_ever_built, prestige_points_earned, sandbox_mode
        global epilogue_open, run_start_tick, run_completed, mutators_run
        megaproject_progress.clear()  # A-13: a megaproject belongs to the run that built it
        megaprojects_built.clear()

        prestige_level = next_level
        run_start_tick = total_ticks  # R-10: a new run starts its own clock
        run_completed = False
        run_splits.clear()  # A-30: a new run starts new splits (the personal best stays)
        del _action_log[:]
        _chain_cooldown_until.clear()
        # A1/A3: 1 tree point per prestige, +1 if the New Game+ Challenge was on.
        prestige_points_earned += 1 + (1 if _challenge_on() else 0) + mutator_points(mutators_run)
        mutators_run = list(mutators_next)  # A-3: the picks are locked in the moment a new run starts
        sandbox_mode = False
        epilogue_open = False
        _forget_close_call_history()
        _departure_snapshots.clear()
        for planet in PLANETS:
            planet_state[planet] = _fresh_planet_state(planet)
        researched_nodes.clear()
        _recompute_research()
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

    # Z22 cross-game audit: migrated from a native browser confirm() (see
    # `_confirm_dialog_ask()`'s own comment above `_reset_world`) to the
    # shared ConfirmDialog, same as reset-this-world.
    _confirm_dialog_ask(
        action_id="sol-prestige",
        message=(
            f"Prestige into a New Game+? Every world resets to its starting state -- "
            f"research, travel, and the Governor included -- and you keep a permanent "
            f"+{next_bonus_pct}% resource yield (Prestige Level {next_level}) and a Prestige Tree "
            "point" + _mutator_confirm_note() + ". Lifetime stats, tree unlocks and every achievement you've "
            "already earned are kept. This cannot be undone."
        ),
        confirm_label="Prestige into New Game+",
        on_confirm=_do_prestige,
    )


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
        if _doctrine_step(planet):
            continue  # A-7: a Doctrine rule paused the Governor's own buying here
        # A7: each world may carry its own personality preset; otherwise it
        # follows the global dial exactly as before.
        priority, budget_pct = governor_settings(planet)
        if mutator_active("blind_governor"):
            priority, budget_pct = "balance", min(budget_pct, MUTATOR_BLIND_BUDGET_CAP)
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
                if not _dry_run:
                    update_generator_display(planet)
        else:
            cost = recycler_cost(planet)
            if cost <= budget:
                state["resource_count"] -= cost
                state["recycler_count"] += 1
                governor_purchase_count += 1
                lifetime_recyclers_built += 1
                if not _dry_run:
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
    if mutator_active("one_way_trade"):
        total *= MUTATOR_ONE_WAY_FACTOR
    return total * anomaly_factor("trade")


def _simulate_planet(planet, incoming_trade_restore):
    global lifetime_resources_generated_by_automation
    cfg = PLANETS[planet]
    state = planet_state[planet]

    if state["generator_count"] > 0:
        multiplier = production_multiplier(planet)
        if multiplier > 0:
            # Sky City bonus (Milestone 10): a no-op multiplier of exactly 1
            # on planets without the sky city keys (the other six planets).
            sky_city_bonus = 1 + sky_city_bonus_per_city(planet) * state.get("sky_city_count", 0)
            spec = _specialization(planet)
            produced = (
                state["generator_count"]
                * cfg["generator_rate"]
                * sky_city_bonus
                * (TICK_INTERVAL_MS / 1000)
                * multiplier
                * _yield_multiplier()
                * anomaly_factor("produce")
                * megaproject_factor("produce")
                * (1 + stamp_bonus(planet))
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
    if mutator_active("thin_atmosphere"):
        decay *= MUTATOR_THIN_DECAY_FACTOR
    decay *= anomaly_factor("decay")
    spec = _specialization(planet)
    if spec == "output":
        decay *= 1 + SPECIALIZATION_OUTPUT_DECAY_PENALTY
    elif spec == "stability":
        decay *= 1 - SPECIALIZATION_STABILITY_DECAY_CUT
    restore = state["recycler_count"] * cfg["recycler_restore_per_sec"] * (TICK_INTERVAL_MS / 1000) * anomaly_factor("recycle") * megaproject_factor("recycle")
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
    _update_anomaly()

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

    update_research_node_flags()
    _decay_click_streak()
    update_all_cross_summaries()
    update_away_summary()
    update_win_display()
    update_achievements_display()
    update_stats_panel_display()
    update_governor_report_display()
    update_changelog_display()
    update_overview_display()
    update_epilogue_display()
    update_splits_display()
    update_chains_display()
    update_anomaly_strip()
    _check_missions()
    _check_codex()
    update_charter_display()
    update_doctrine_display()
    _check_new_achievements_for_toast()
    if total_ticks % 10 == 0:
        _refresh_goals_panel()  # FY-53: once a second is plenty for a progress bar


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
    render_story_log()
    update_build_plan_display()
    update_prestige_tree_display()
    update_epilogue_display()
    update_splits_display()
    update_chains_display()
    _update_anomaly()
    update_anomaly_strip()
    _terraform_done_seen.update(p for p in PLANETS if planet_state[p]["terraform_progress"] >= TERRAFORM_MAX)
    _refill_mission_slots()
    update_charter_display()
    update_doctrine_display()
    render_trophy_shelf()
    render_click_streak()
    _refresh_all_cost_displays()
    _refresh_goals_panel()
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
        "researched_nodes": sorted(researched_nodes),
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
        **({"full_system_completed_tick": full_system_completed_tick} if full_system_completed_tick is not None else {}),
        **({"run_start_tick": run_start_tick} if run_start_tick else {}),
        **({"run_completed": True} if run_completed else {}),
        **({"best_run_ticks": best_run_ticks} if best_run_ticks is not None else {}),
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
        **({"story_log": list(story_log)} if story_log else {}),
        **({"best_click_streak": best_click_streak} if best_click_streak else {}),
        **({"chain_counts": dict(chain_counts)} if chain_counts else {}),
        **({"recent_trophies": list(recent_trophies)} if recent_trophies else {}),
        **({"run_splits": dict(run_splits)} if run_splits else {}),
        **({"pb_splits": dict(pb_splits)} if pb_splits else {}),
        **({"anomalies_seen": sorted(anomalies_seen)} if anomalies_seen else {}),
        **({"codex_found": list(codex_found)} if codex_found else {}),
        **({"doctrine_rules": [dict(rule) for rule in doctrine_rules]} if doctrine_rules else {}),
        **({"stress_best_margin": stress_best_margin} if stress_best_margin is not None else {}),
        **({"megaproject_progress": {k: dict(v) for k, v in megaproject_progress.items()}} if megaproject_progress else {}),
        **({"megaprojects_built": list(megaprojects_built)} if megaprojects_built else {}),
        **({"megaprojects_all_ever": True} if megaprojects_all_ever else {}),
        **({"mission_stamps": list(mission_stamps)} if mission_stamps else {}),
        **({"mission_slots": list(mission_slots)} if mission_slots and not _slots_are_default() else {}),
        **({"mutators_next": list(mutators_next)} if mutators_next else {}),
        **({"mutators_run": list(mutators_run)} if mutators_run else {}),
    }


def deserialize_state(data):
    global unlocked_bodies, visited_bodies, current_planet
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
    # U10: research is a set of nodes now. A save from before the tree only
    # has (completed_tiers, research_progress); convert it without losing
    # anything, refunding any Iron the partial progress can't buy a node with.
    saved_nodes = data.get("researched_nodes")
    if isinstance(saved_nodes, list):
        researched_nodes.clear()
        researched_nodes.update(_clean_researched_nodes(saved_nodes))
    else:
        legacy_tiers = data.get("completed_tiers", 0)
        legacy_tiers = legacy_tiers if isinstance(legacy_tiers, int) and not isinstance(legacy_tiers, bool) else 0
        migrated, refund = _migrate_legacy_research(max(0, legacy_tiers), data.get("research_progress", 0.0))
        researched_nodes.clear()
        researched_nodes.update(_clean_researched_nodes(migrated))
        if refund > 0:
            planet_state["Earth"]["resource_count"] += refund
    _recompute_research()
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
    global full_system_completed_tick, _leaderboard_reported
    global run_start_tick, run_completed, best_run_ticks, best_click_streak, _trophy_fresh_id, stress_best_margin

    def _tick_count(value):
        return value if isinstance(value, int) and not isinstance(value, bool) and 0 <= value < 10 ** 12 else None

    run_start_tick = _tick_count(data.get("run_start_tick")) or 0
    run_completed = data.get("run_completed") is True
    best_run_ticks = _tick_count(data.get("best_run_ticks"))
    # Round-3 batch: every field optional and defensively typed.
    best_click_streak = _tick_count(data.get("best_click_streak")) or 0
    run_splits.clear()
    run_splits.update(_clean_splits(data.get("run_splits")))
    pb_splits.clear()
    pb_splits.update(_clean_splits(data.get("pb_splits")))
    chain_counts.clear()
    saved_chains = data.get("chain_counts")
    if isinstance(saved_chains, dict):
        for chain_id, count in saved_chains.items():
            if chain_id in CHAIN_BY_ID and isinstance(count, int) and not isinstance(count, bool) and 0 < count < 10 ** 6:
                chain_counts[chain_id] = count
    del _action_log[:]
    _chain_cooldown_until.clear()
    _trophy_fresh_id = None
    saved_trophies = data.get("recent_trophies")
    recent_trophies.clear()
    if isinstance(saved_trophies, list):
        known = {entry["id"] for entry in ACHIEVEMENTS}
        for aid in saved_trophies:
            if isinstance(aid, str) and aid in known and aid not in recent_trophies:
                recent_trophies.append(aid)
        del recent_trophies[:-TROPHY_HISTORY_MAX]
    else:
        # A save from before the shelf existed: the most recent earned ones, in catalog order.
        recent_trophies.extend(achievement_ids_earned()[-TROPHY_HISTORY_MAX:])

    anomalies_seen.clear()
    saved_anomalies = data.get("anomalies_seen")
    if isinstance(saved_anomalies, list):
        anomalies_seen.update(a for a in saved_anomalies if isinstance(a, str) and a in ANOMALY_BY_ID)
    _load_megaprojects(data)
    codex_found[:] = _clean_ids(data.get("codex_found"), CLUE_BY_ID)
    doctrine_rules[:] = _clean_doctrine_rules(data.get("doctrine_rules"))
    saved_margin = data.get("stress_best_margin")
    stress_best_margin = (
        round(float(saved_margin), 1)
        if isinstance(saved_margin, (int, float)) and not isinstance(saved_margin, bool)
        and -100.0 <= saved_margin <= 100.0 and saved_margin == saved_margin
        else None
    )
    _doctrine_reset_runtime()
    mission_stamps[:] = _clean_ids(data.get("mission_stamps"), MISSION_BY_ID)
    mission_slots[:] = [m_id for m_id in _clean_ids(data.get("mission_slots"), MISSION_BY_ID)
                        if m_id not in mission_stamps][:MISSION_SLOTS]
    mutators_next[:] = _clean_mutators(data.get("mutators_next"))
    mutators_run[:] = _clean_mutators(data.get("mutators_run"))

    saved_story = data.get("story_log")
    story_log.clear()
    if isinstance(saved_story, list):
        for entry_id in saved_story:
            if isinstance(entry_id, str) and story_line(entry_id) and entry_id not in story_log:
                story_log.append(entry_id)
        del story_log[:-STORY_LOG_MAX]

    saved_completion = data.get("full_system_completed_tick")
    full_system_completed_tick = (
        saved_completion
        if isinstance(saved_completion, int) and not isinstance(saved_completion, bool) and saved_completion >= 0
        else None
    )
    _leaderboard_reported = False

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
        actions = state.get("player_actions", 0)
        if not isinstance(actions, int) or isinstance(actions, bool) or actions < 0:
            state["player_actions"] = 0
        if state.get("governor_personality") not in GOVERNOR_PERSONALITIES:
            state["governor_personality"] = "default"
        if state.get("specialization") not in (None, *SPECIALIZATION_LABELS):
            state["specialization"] = None


# V-CD-4 (planning/TODO.md, from the completion audit's A3 follow-up):
# the welcome-back toast's "last time" reference point, persisted PER
# BROWSER via localStorage -- deliberately NOT part of get_state()/the
# save-code payload, since a save code is meant to be portable across
# devices/browsers while "what this browser last saw" is a per-browser
# fact, not a save-state fact. Same lazy `import js`/getattr-defaulting
# pattern as Canopy's personal_best / Tide's best_coastline_saved
# (`_read_local_storage_item()`/`_write_local_storage_item()`), SOL's
# first use of Python-side localStorage (settings.js's text-scale/
# reduced-motion prefs use the same storage but from plain JS, outside
# Pyodide entirely).
WELCOME_BACK_SNAPSHOT_STORAGE_KEY = "sol_welcome_back_snapshot_v1"


def _read_local_storage_item(key):
    """Broad except on the actual read is deliberate: a real browser can
    refuse localStorage access entirely (private-browsing mode in some
    browsers), surfaced as a JS exception with no stable Python type to
    catch narrowly -- this feature is a nice-to-have, not core gameplay,
    so it degrades to "nothing stored" rather than crashing the toast."""
    try:
        import js  # noqa: PLC0415 — Pyodide-only import, deliberately lazy
    except ImportError:
        return None
    storage = getattr(js, "localStorage", None)
    if storage is None:
        return None
    try:
        return storage.getItem(key)
    except Exception:  # noqa: BLE001 — see docstring above
        return None


def _write_local_storage_item(key, value):
    try:
        import js  # noqa: PLC0415
    except ImportError:
        return
    storage = getattr(js, "localStorage", None)
    if storage is None:
        return
    try:
        storage.setItem(key, value)
    except Exception:  # noqa: BLE001 — see _read_local_storage_item's docstring
        pass


def _load_welcome_back_snapshot():
    """Reads the (worlds_visited, achievements_earned) pair this browser
    recorded the last time a save loaded here. Returns None if nothing is
    stored yet, storage is unavailable, or the stored value is
    malformed."""
    raw = _read_local_storage_item(WELCOME_BACK_SNAPSHOT_STORAGE_KEY)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        snapshot = {
            "worlds_visited": int(data["worlds_visited"]),
            "achievements_earned": int(data["achievements_earned"]),
        }
        # R-9: machines built and hand-mined clicks were added later; an older
        # snapshot simply lacks them (None = nothing to diff against).
        for key in ("machines_built", "manual_clicks"):
            value = data.get(key)
            snapshot[key] = int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
        return snapshot
    except (ValueError, TypeError, KeyError):
        return None


def _save_welcome_back_snapshot(worlds_visited, achievements_earned):
    _write_local_storage_item(
        WELCOME_BACK_SNAPSHOT_STORAGE_KEY,
        json.dumps({
            "worlds_visited": worlds_visited,
            "achievements_earned": achievements_earned,
            "machines_built": int(lifetime_generators_built),
            "manual_clicks": int(total_manual_clicks),
        }),
    )


def _show_welcome_back_toast():
    """A3: a "welcome back" return-visit summary toast. Fires whenever a
    save is loaded -- the only situation SOL can actually call "a
    returning player" (see load_state()/load_save_state_json() below, the
    two entry points a loaded save ever arrives through).

    Originally a static current-standing snapshot: SOL has no
    offline-production system (the project's own "no idle/wait-timer
    mechanics" rule means nothing advances while the tab is closed), so
    there was no real "here's what changed while you were away" delta to
    report against the save's own numbers. Revised per V-CD-4 to a
    genuine "+X since last time" delta by comparing this load's numbers
    against what this same BROWSER last recorded (`_load_welcome_back_
    snapshot()`), not the save code itself -- so the delta is meaningful
    per browser while the save stays portable across devices. Falls back
    to the original static wording when there's nothing sensible to
    diff against: this browser's first-ever load (nothing stored yet),
    or the just-loaded save's numbers sitting at or below the stored
    snapshot (an older or different save code loaded into the same
    browser) -- never shows a negative "-N" as though something was
    lost. The stored snapshot is updated to this load's numbers only
    AFTER computing the delta against the OLD stored values, so next
    time compares against this visit, not some frozen baseline."""
    worlds = len(visited_bodies)
    earned = len(achievement_ids_earned())
    previous = _load_welcome_back_snapshot()

    message = None
    if previous is not None:
        delta_worlds = worlds - previous["worlds_visited"]
        delta_achievements = earned - previous["achievements_earned"]
        delta_machines = (
            int(lifetime_generators_built) - previous["machines_built"] if previous.get("machines_built") is not None else 0
        )
        delta_clicks = (
            int(total_manual_clicks) - previous["manual_clicks"] if previous.get("manual_clicks") is not None else 0
        )
        if (
            delta_worlds >= 0 and delta_achievements >= 0 and delta_machines >= 0 and delta_clicks >= 0
            and (delta_worlds > 0 or delta_achievements > 0 or delta_machines > 0 or delta_clicks > 0)
        ):
            message = (
                f"👋 Welcome back! +{delta_worlds} world(s) visited, "
                f"+{delta_achievements} achievement(s)"
            )
            if delta_machines > 0:
                message += f", +{delta_machines} machine(s) built"
            if delta_clicks > 0:
                message += f", +{delta_clicks} hand-mined load(s)"
            message += " since you were last here."

    if message is None:
        message = (
            f"👋 Welcome back! {worlds}/{len(PLANETS)} worlds visited, "
            f"{earned}/{len(ACHIEVEMENTS)} achievements earned."
        )

    _display_toast(message)
    _save_welcome_back_snapshot(worlds, earned)


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


# ===========================================================================
# Round-4 batch (2026-10-10). FY-53 goals queue first; the Charter, mutators,
# anomalies, megaprojects, codex, eras and doctrines are appended below it.
# ===========================================================================

# --- A-3 / A-4 / FY-49: prestige mutators -----------------------------------
# Before a New Game+ run the player may pick 0-3 opt-in rule twists. The picks
# (`mutators_next`) are locked in when the next run starts (`mutators_run`), and
# the points are paid when that run is prestiged out of, so a twist can never be
# switched off mid-run to keep the reward. Balance is the owner's "you write it"
# (FY-49): every twist is worth exactly 1 point, none stacks with itself, and
# none can lock a world (the worst case is a slower run; ecology and trade keep
# their usual floors). Nothing here is luck.
MUTATOR_MAX_PICKS = 3
MUTATOR_THIN_DECAY_FACTOR = 1.4  # ecology decays 40% faster
MUTATOR_ONE_WAY_FACTOR = 0.5  # trade routes restore half as much ecology
MUTATOR_BLIND_BUDGET_CAP = 25.0  # the Governor spends at most a quarter of a world's stock
MUTATOR_COSTLY_FACTOR = 1.15  # Auto-Miners and Recyclers cost 15% more
MUTATORS = [
    {"id": "thin_atmosphere", "label": "Thin Atmosphere", "glyph": "\u2601", "points": 1,
     "desc": "Ecology decays 40% faster on every world."},
    {"id": "one_way_trade", "label": "One-Way Trade", "glyph": "\u2192", "points": 1,
     "desc": "Trade routes restore only half as much ecology."},
    {"id": "blind_governor", "label": "Blind Governor", "glyph": "\u25d0", "points": 1,
     "desc": "The Governor ignores your priority and its personalities, alternates its buys and spends "
             "at most a quarter of a world's stock."},
    {"id": "costly_machinery", "label": "Costly Machinery", "glyph": "\u2699", "points": 1,
     "desc": "Auto-Miners and Recyclers cost 15% more."},
]
MUTATOR_BY_ID = {entry["id"]: entry for entry in MUTATORS}
mutators_next = []  # the picks for the run that starts at the next prestige
mutators_run = []  # the rules the run in progress is being played under


def mutator_active(mutator_id):
    return mutator_id in mutators_run


def mutator_points(ids):
    return sum(MUTATOR_BY_ID[m_id]["points"] for m_id in ids if m_id in MUTATOR_BY_ID)


def mutator_glyphs(ids):
    """A tiny glyph per rule, with a leading space, for the badge and the share card ("" when none)."""
    return "".join(" " + MUTATOR_BY_ID[m_id]["glyph"] for m_id in ids if m_id in MUTATOR_BY_ID)


def mutator_rules_text(ids):
    names = [MUTATOR_BY_ID[m_id]["label"] for m_id in ids if m_id in MUTATOR_BY_ID]
    return (". Run rules: " + ", ".join(names)) if names else ""


def _clean_mutators(raw):
    cleaned = []
    if isinstance(raw, list):
        for m_id in raw:
            if isinstance(m_id, str) and m_id in MUTATOR_BY_ID and m_id not in cleaned:
                cleaned.append(m_id)
    return cleaned[:MUTATOR_MAX_PICKS]


def _mutator_confirm_note():
    if not mutators_next:
        return ""
    return (f" and, for the new run, the rule twists you picked ({', '.join(MUTATOR_BY_ID[m]['label'] for m in mutators_next)}), "
            f"which pay {mutator_points(mutators_next)} extra point(s) when you prestige out of that run")


def _toggle_mutator_pick(mutator_id):
    if mutator_id not in MUTATOR_BY_ID:
        return
    if mutator_id in mutators_next:
        mutators_next.remove(mutator_id)
    elif len(mutators_next) < MUTATOR_MAX_PICKS:
        mutators_next.append(mutator_id)


def _build_mutator_cards(panel):
    panel.appendChild(_make_text("stats-panel-heading", "Mutators for your next run (optional)"))
    panel.appendChild(_make_text(
        "prestige-node-desc",
        f"Pick up to {MUTATOR_MAX_PICKS} rule twists. They apply from the moment your next New Game+ starts, "
        "and each pays 1 extra Prestige Point when you prestige out of that run. Nothing is luck, "
        "no world can be locked out, and you can change the picks any time before you prestige.",
    ))
    if mutators_run:
        panel.appendChild(_make_text(
            "prestige-node-status",
            "This run is being played with: " + ", ".join(MUTATOR_BY_ID[m]["label"] for m in mutators_run)
            + f" (worth {mutator_points(mutators_run)} point(s) when you prestige).",
        ))
    for entry in MUTATORS:
        picked = entry["id"] in mutators_next
        card = document.createElement("div")
        card.className = "prestige-node" + (" prestige-node--unlocked" if picked else "")
        card.appendChild(_make_text("prestige-node-name", f"{entry['glyph']} {entry['label']} (+{entry['points']} pt)"))
        card.appendChild(_make_text("prestige-node-desc", entry["desc"]))
        full = not picked and len(mutators_next) >= MUTATOR_MAX_PICKS
        card.appendChild(_make_button(
            "Picked for next run" if picked else ("Limit reached" if full else "Pick for next run"),
            {"data-action": "mutator", "data-mutator": entry["id"]}, None, selected=picked, disabled=full))
        panel.appendChild(card)


# --- A-21: prestige Eras --------------------------------------------------------
# The flat "Prestige N" counter gains a name by level: Pioneer (never prestiged),
# Steward (1-2), Architect (3-5), Custodian (6+). From Steward on, the shell
# shifts hue a little, the dimmer stars get a touch quieter and a one-line
# tagline appears under the title. All of it is static styling (nothing moves, so
# Reduce motion needs no special case) and Settings "Era look" turns the look
# off; the name stays in the badge either way. No rule or number changes.
ERA_LOOK_KEY = "sol-era-look"
ERAS = [
    {"min_level": 0, "id": "pioneer", "label": "Pioneer", "tagline": ""},
    {"min_level": 1, "id": "steward", "label": "Steward",
     "tagline": "Era of the Steward: you came back to tend what you built."},
    {"min_level": 3, "id": "architect", "label": "Architect",
     "tagline": "Era of the Architect: every world is a drawing you can redraw."},
    {"min_level": 6, "id": "custodian", "label": "Custodian",
     "tagline": "Era of the Custodian: nothing to prove, a great deal to keep."},
]


def era_for_level(level):
    chosen = ERAS[0]
    for era in ERAS:
        if level >= era["min_level"]:
            chosen = era
    return chosen


def _apply_era():
    """Sets `data-era` on <html> (read by style.css) and the tagline under the title."""
    era = era_for_level(prestige_level)
    themed = _setting_on(ERA_LOOK_KEY) and era["tagline"] != ""
    try:
        document.documentElement.setAttribute("data-era", era["id"])
    except AttributeError:
        pass  # the fake DOM of older tests has no <html> element
    tagline = document.getElementById("era-tagline")
    tagline.innerText = era["tagline"] if themed else ""
    tagline.hidden = not themed


# --- A-2 / FY-50: System Anomalies on a fixed schedule ------------------------
# Plain timed modifiers, never random and never blocking: the run clock
# (game ticks since this run began, so a pause or a hidden tab adds nothing)
# starts calm for ANOMALY_FIRST_AT ticks, then one anomaly of ANOMALY_LENGTH ticks
# opens every ANOMALY_PERIOD ticks, walking the same six in the same order
# (boon, strain, boon, strain, boon, strain). The forecast strip says what is
# next and for how long, in words, so nothing is a surprise. Off switch:
# Settings "Timed anomalies" (`localStorage["sol-anomalies"]`); not applied in the
# post-win sandbox.
ANOMALY_FIRST_AT = 3000  # 5 minutes of game time
ANOMALY_PERIOD = 3000  # one every 5 minutes
ANOMALY_LENGTH = 600  # lasting 1 minute
ANOMALY_KEY = "sol-anomalies"
ANOMALIES = [
    {"id": "comet_pass", "label": "Comet Pass", "kind": "boon", "effects": {"produce": 1.25},
     "text": "every Auto-Miner produces 25% more"},
    {"id": "solar_flare", "label": "Solar Flare", "kind": "strain", "effects": {"decay": 1.5},
     "text": "ecology decays 50% faster everywhere"},
    {"id": "meteor_shower", "label": "Meteor Shower", "kind": "boon", "effects": {"click": 2.0},
     "text": "every hand-mined click gives double"},
    {"id": "magnetic_storm", "label": "Magnetic Storm", "kind": "strain", "effects": {"trade": 0.5},
     "text": "trade routes restore half as much ecology"},
    {"id": "clear_skies", "label": "Clear Skies", "kind": "boon", "effects": {"recycle": 1.5},
     "text": "Recyclers restore 50% more ecology"},
    {"id": "dust_cloud", "label": "Dust Cloud", "kind": "strain", "effects": {"terraform": 0.5},
     "text": "terraforming advances at half speed (it never goes backwards)"},
]
ANOMALY_BY_ID = {entry["id"]: entry for entry in ANOMALIES}
anomalies_seen = set()  # lifetime collection; saved only when non-empty
_stress_factors = {}  # A-27: the cascade's multipliers while a headless Stress Test run is going
_active_anomaly = None  # id of the anomaly in effect this tick, or None


def _run_ticks():
    return max(0, total_ticks - run_start_tick)


def anomaly_schedule(run_ticks):
    """(active_id or None, ticks left in it, next_id, ticks until the next one starts)."""
    if run_ticks < ANOMALY_FIRST_AT:
        return None, 0, ANOMALIES[0]["id"], ANOMALY_FIRST_AT - run_ticks
    index, offset = divmod(run_ticks - ANOMALY_FIRST_AT, ANOMALY_PERIOD)
    if offset < ANOMALY_LENGTH:
        nxt = ANOMALIES[(index + 1) % len(ANOMALIES)]["id"]
        return ANOMALIES[index % len(ANOMALIES)]["id"], ANOMALY_LENGTH - offset, nxt, ANOMALY_PERIOD - offset
    return None, 0, ANOMALIES[(index + 1) % len(ANOMALIES)]["id"], ANOMALY_PERIOD - offset


def _anomalies_enabled():
    return _setting_on(ANOMALY_KEY) and not _sandbox_active()


def _update_anomaly():
    global _active_anomaly
    if not _anomalies_enabled():
        _active_anomaly = None
        return
    _active_anomaly = anomaly_schedule(_run_ticks())[0]
    if _active_anomaly is not None:
        anomalies_seen.add(_active_anomaly)


def anomaly_factor(key):
    factor = _stress_factors.get(key, 1.0)  # only ever non-empty inside a headless Stress Test run
    if _active_anomaly is None:
        return factor
    return factor * ANOMALY_BY_ID[_active_anomaly]["effects"].get(key, 1.0)


def _mmss(ticks):
    seconds = int(math.ceil(ticks * TICK_INTERVAL_MS / 1000))
    return f"{seconds // 60}:{seconds % 60:02d}"


def anomaly_strip_text():
    """The one-line forecast ("" when anomalies are off)."""
    if not _anomalies_enabled():
        return ""
    active, left, nxt, until = anomaly_schedule(_run_ticks())
    next_entry = ANOMALY_BY_ID[nxt]
    if active is not None:
        entry = ANOMALY_BY_ID[active]
        mark = "\u25b2 Boon" if entry["kind"] == "boon" else "\u25bc Strain"
        return (f"{mark}: {entry['label']} for {_mmss(left)} more, {entry['text']}. "
                f"Next: {next_entry['label']} in {_mmss(until)}.")
    return (f"Next anomaly: {next_entry['label']} in {_mmss(until)} "
            f"({'a boon' if next_entry['kind'] == 'boon' else 'a strain'}: {next_entry['text']}, for {_mmss(ANOMALY_LENGTH)}).")


def update_anomaly_strip():
    strip = document.getElementById("anomaly-strip")
    text = anomaly_strip_text()
    if strip.innerText != text:
        strip.innerText = text
    strip.hidden = not text
    strip.className = "anomaly-strip" + (
        " anomaly-strip--boon" if _active_anomaly and ANOMALY_BY_ID[_active_anomaly]["kind"] == "boon"
        else " anomaly-strip--strain" if _active_anomaly else ""
    )


# --- A-5 / A-6: the Mission Board and Charter stamps ---------------------------
# Three optional objectives are posted at a time; finishing one stamps the
# Charter (kept for life) and posts the next. Nothing is random: missions are
# offered in catalogue order (worlds you can reach first) and a reroll just moves
# on to the next one. A stamp is a small permanent perk (+1% yield on its world,
# +0.5% everywhere for the world-spanning ones) and shows on the Overview card.
MISSION_SLOTS = 3
CHARTER_MEMBER_STAMPS = 5
STAMP_STAR = "\u2605"
MISSION_REROLL_COST = 100  # of whichever resource pile is biggest right now
_STAMP_BONUS_WORLD = 0.01
_STAMP_BONUS_ALL = 0.005


def _routes(planet):
    return sum(planet_state[planet]["trade_routes"].values())


def _governed_healthy_worlds():
    return sum(
        1 for p in PLANETS
        if p != current_planet and planet_state[p]["generator_count"] >= 1 and planet_state[p]["ecology_health"] >= 60
    )


MISSIONS = [
    {"id": "earth_crew", "world": "Earth", "target": 8, "label": "Run Earth with 5 Auto-Miners and 3 Recyclers",
     "measure": lambda: min(planet_state["Earth"]["generator_count"], 5) + min(planet_state["Earth"]["recycler_count"], 3)},
    {"id": "earth_hoard", "world": "Earth", "target": 2000, "label": "Bank 2,000 Iron on Earth",
     "measure": lambda: planet_state["Earth"]["resource_count"]},
    {"id": "earth_lean", "world": "Earth", "target": 25,
     "label": "Terraform Earth to 25% with no Auto-Miners at all (Recyclers only)",
     "measure": lambda: planet_state["Earth"]["terraform_progress"] if planet_state["Earth"]["generator_count"] == 0 else 0},
    {"id": "mars_routes", "world": "Mars", "target": 2, "label": "Build 2 trade routes out of Mars",
     "measure": lambda: _routes("Mars")},
    {"id": "mars_calm", "world": "Mars", "target": 6,
     "label": "Run 6 Auto-Miners on Mars with ecology at 90% or more",
     "measure": lambda: planet_state["Mars"]["generator_count"] if planet_state["Mars"]["ecology_health"] >= 90 else 0},
    {"id": "moon_stock", "world": "Moon", "target": 1500, "label": "Bank 1,500 Regolith on the Moon",
     "measure": lambda: planet_state["Moon"]["resource_count"]},
    {"id": "moon_green", "world": "Moon", "target": 50,
     "label": "Terraform the Moon to 50% with 6 Auto-Miners or fewer",
     "measure": lambda: planet_state["Moon"]["terraform_progress"] if planet_state["Moon"]["generator_count"] <= 6 else 0},
    {"id": "venus_sixty", "world": "Venus", "target": 60, "label": "Terraform Venus to 60% with ecology at 50% or more",
     "measure": lambda: planet_state["Venus"]["terraform_progress"] if planet_state["Venus"]["ecology_health"] >= 50 else 0},
    {"id": "belt_bank", "world": "AsteroidBelt", "target": 2500, "label": "Bank 2,500 Platinum in the Asteroid Belt",
     "measure": lambda: planet_state["AsteroidBelt"]["resource_count"]},
    {"id": "belt_routes", "world": "AsteroidBelt", "target": 3, "label": "Build 3 trade routes out of the Asteroid Belt",
     "measure": lambda: _routes("AsteroidBelt")},
    {"id": "pluto_green", "world": "Pluto", "target": 40,
     "label": "Terraform Pluto to 40% with at least 2 Recyclers",
     "measure": lambda: planet_state["Pluto"]["terraform_progress"] if planet_state["Pluto"]["recycler_count"] >= 2 else 0},
    {"id": "jupiter_sky", "world": "JupiterMoons", "target": 2, "label": "Build 2 Sky Cities over Jupiter's Moons",
     "measure": lambda: planet_state["JupiterMoons"].get("sky_city_count", 0)},
    {"id": "saturn_sky", "world": "SaturnMoons", "target": 2, "label": "Build 2 Sky Cities over Saturn's Moons",
     "measure": lambda: planet_state["SaturnMoons"].get("sky_city_count", 0)},
    {"id": "web_of_routes", "world": "all", "target": 6, "label": "Run 6 trade routes in total",
     "measure": lambda: _total_trade_routes()},
    {"id": "governed_well", "world": "all", "target": 3,
     "label": "Have 3 worlds you are not standing on, each with an Auto-Miner and ecology at 60% or more",
     "measure": lambda: _governed_healthy_worlds()},
]
MISSION_BY_ID = {entry["id"]: entry for entry in MISSIONS}
mission_stamps = []  # lifetime, in the order earned
mission_slots = []  # the missions on the board right now
charter_open = False
_charter_signature = None
_charter_refs = {}


def _clean_ids(raw, known):
    cleaned = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str) and item in known and item not in cleaned:
                cleaned.append(item)
    return cleaned


def stamps_for(world):
    return sum(1 for m_id in mission_stamps if MISSION_BY_ID[m_id]["world"] == world)


def stamp_bonus(planet):
    return _STAMP_BONUS_WORLD * stamps_for(planet) + _STAMP_BONUS_ALL * stamps_for("all")


def mission_progress(mission):
    return min(max(0, mission["measure"]()), mission["target"])


def _mission_world_open(mission):
    if mission["world"] == "all":
        return len(_overview_planets()) >= 3
    return _world_available(mission["world"])


def _mission_candidates():
    return [m for m in MISSIONS
            if m["id"] not in mission_stamps and m["id"] not in mission_slots and _mission_world_open(m)]


def _slots_are_default():
    """True while the board is exactly what refilling it from scratch would post (so nothing needs saving)."""
    fresh = [m["id"] for m in MISSIONS if m["id"] not in mission_stamps and _mission_world_open(m)][:MISSION_SLOTS]
    return list(mission_slots) == fresh


def _refill_mission_slots():
    while len(mission_slots) < MISSION_SLOTS:
        candidates = _mission_candidates()
        if not candidates:
            break
        mission_slots.append(candidates[0]["id"])


def _mission_label_world(mission):
    return "the whole system" if mission["world"] == "all" else PLANET_DISPLAY_NAMES.get(mission["world"], mission["world"])


def _check_missions():
    _refill_mission_slots()
    for m_id in list(mission_slots):
        mission = MISSION_BY_ID[m_id]
        if mission["measure"]() >= mission["target"]:
            mission_slots.remove(m_id)
            mission_stamps.append(m_id)
            _display_toast(f"Charter stamp earned: {mission['label']}")
            _refill_mission_slots()


def reroll_source():
    """(planet, amount) the next reroll would spend, or None when no pile has enough."""
    best = max(_overview_planets(), key=lambda p: planet_state[p]["resource_count"])
    if planet_state[best]["resource_count"] >= MISSION_REROLL_COST:
        return best, MISSION_REROLL_COST
    return None


def reroll_mission(mission_id):
    """Swaps a posted mission for the next one in catalogue order. Returns True when it happened."""
    if mission_id not in mission_slots:
        return False
    source = reroll_source()
    candidates = _mission_candidates()
    if source is None or not candidates:
        return False
    here = MISSIONS.index(MISSION_BY_ID[mission_id])
    later = [m for m in candidates if MISSIONS.index(m) > here]
    chosen = (later or candidates)[0]
    planet_state[source[0]]["resource_count"] -= source[1]
    mission_slots[mission_slots.index(mission_id)] = chosen["id"]
    return True


def on_toggle_charter(event=None):
    global charter_open
    charter_open = not charter_open
    update_charter_display()


def on_charter_click(event):
    action = _target_attr(event, "data-action")
    if action == "reroll":
        reroll_mission(_target_attr(event, "data-mission"))
    elif action == "stress":
        run_stress_test()
    elif action == "hint":
        clue_id = _target_attr(event, "data-clue")
        if clue_id in CLUE_BY_ID:
            _codex_hints.add(clue_id)
    elif action == "send":
        send_to_megaproject(_target_attr(event, "data-project"), _target_attr(event, "data-planet"))
    update_charter_display()


def _charter_structure_signature():
    return (tuple(mission_slots), tuple(mission_stamps), tuple(sorted(anomalies_seen)),
            tuple(_overview_planets()), tuple(megaprojects_built), tuple(codex_found), tuple(sorted(_codex_hints)),
            _stress_run_id, stress_best_margin, _prestige_available(),
            tuple((pid, tuple(sorted(v.items()))) for pid, v in sorted(megaproject_progress.items())))


def _build_charter():
    panel = document.getElementById("charter-panel")
    panel.innerHTML = ""
    _charter_refs.clear()
    panel.appendChild(_make_text("stats-panel-heading", "Charter"))
    panel.appendChild(_make_text(
        "chains-intro",
        "Optional objectives. Finish a mission and the Charter is stamped for good: a small permanent yield "
        "bonus on that world, shown on its Overview card. Nothing here is timed or random.",
    ))
    panel.appendChild(_make_text("stats-panel-heading", "Mission Board"))
    for m_id in mission_slots:
        mission = MISSION_BY_ID[m_id]
        card = document.createElement("div")
        card.className = "chain-card"
        card.appendChild(_make_text("chain-card-name", f"{mission['label']}"))
        card.appendChild(_make_text("chain-card-detail", f"World: {_mission_label_world(mission)}"))
        meter = document.createElement("div")
        meter.className = "meter overview-meter"
        fill = document.createElement("div")
        fill.className = "meter-fill"
        meter.appendChild(fill)
        card.appendChild(meter)
        text = _make_text("chain-card-count", "")
        card.appendChild(text)
        reroll = _make_button("Swap for another mission", {"data-action": "reroll", "data-mission": m_id}, None)
        card.appendChild(reroll)
        panel.appendChild(card)
        _charter_refs[m_id] = {"fill": fill, "text": text, "reroll": reroll}
    if len(mission_slots) < MISSION_SLOTS:
        panel.appendChild(_make_text(
            "chains-intro", "More missions are posted as you unlock worlds and finish these."))
    _build_megaproject_section(panel)
    _build_codex_section(panel)
    _build_stress_section(panel)
    _charter_refs["_stamps"] = _make_text("chain-card-count", "")
    panel.appendChild(_make_text("stats-panel-heading", "Stamps"))
    panel.appendChild(_charter_refs["_stamps"])
    panel.appendChild(_make_text("stats-panel-heading", "Anomalies seen"))
    names = [ANOMALY_BY_ID[a]["label"] if a in anomalies_seen else "?" for a in (e["id"] for e in ANOMALIES)]
    panel.appendChild(_make_text(
        "chain-card-detail", f"{len(anomalies_seen)} of {len(ANOMALIES)}: " + ", ".join(names)))


def _refresh_charter_values():
    for m_id in mission_slots:
        refs = _charter_refs.get(m_id)
        if refs is None:
            continue
        mission = MISSION_BY_ID[m_id]
        current = mission_progress(mission)
        pct = 100.0 * current / mission["target"]
        refs["fill"].style.width = f"{pct}%"
        shown = math.floor(current + 1e-9) if mission["target"] >= 100 else round(current)
        refs["text"].innerText = f"{shown} of {mission['target']}"
        source = reroll_source()
        refs["reroll"].disabled = source is None or not _mission_candidates()
        refs["reroll"].innerText = (
            f"Swap for another mission ({source[1]} {PLANETS[source[0]]['resource_name']})" if source
            else f"Swap for another mission (needs {MISSION_REROLL_COST} of any resource)"
        )
    _refresh_megaproject_values()
    stamps = _charter_refs.get("_stamps")
    if stamps is not None:
        per_world = [f"{PLANET_DISPLAY_NAMES.get(p, p)} {STAMP_STAR * stamps_for(p)}" for p in PLANETS if stamps_for(p)]
        if stamps_for("all"):
            per_world.append("System " + STAMP_STAR * stamps_for("all"))
        stamps.innerText = f"{len(mission_stamps)} of {len(MISSIONS)} stamps" + (
            ": " + ", ".join(per_world) if per_world else ". Finish a mission to earn the first.")


def update_charter_display():
    global _charter_signature
    toggle = document.getElementById("charter-toggle-button")
    panel = document.getElementById("charter-panel")
    count = f" ({len(mission_stamps)}/{len(MISSIONS)})"
    toggle.innerText = ("Hide Charter" if charter_open else "\U0001f4dc Charter") + count
    panel.hidden = not charter_open
    if not charter_open:
        _charter_signature = None
        return
    signature = _charter_structure_signature()
    if signature != _charter_signature:
        _build_charter()
        _charter_signature = signature
    _refresh_charter_values()


# --- A-13 / A-14: Megaprojects --------------------------------------------------
# Four late-game works, each fed by resources from several worlds at once. You
# send what a world has banked ("Send what you can" per line), the ring fills by
# whichever worlds have contributed, and a finished work gives a game-warping
# perk for the rest of that run. Building all four (in one run) keeps a secret
# epilogue variant for good. Per run, so each New Game+ can build them again.
MEGAPROJECTS = [
    {"id": "orbital_mirror", "label": "Orbital Mirror", "perk": "Terraforming advances 25% faster everywhere.",
     "needs": [("Earth", 4000), ("Mars", 2500), ("AsteroidBelt", 1500)]},
    {"id": "ring_habitat", "label": "Ring Habitat", "perk": "Sky Cities count double.",
     "needs": [("Moon", 3000), ("Venus", 3000), ("Mars", 3000), ("AsteroidBelt", 2000)]},
    {"id": "dyson_sail", "label": "Dyson Sail", "perk": "Every Auto-Miner produces 20% more.",
     "needs": [("AsteroidBelt", 4000), ("JupiterMoons", 2500), ("Earth", 6000), ("Pluto", 1500)]},
    {"id": "deep_core_tap", "label": "Deep Core Tap", "perk": "Recyclers restore 50% more ecology.",
     "needs": [("SaturnMoons", 3000), ("Pluto", 2500), ("Venus", 3500), ("JupiterMoons", 2500), ("Moon", 2500)]},
]
MEGAPROJECT_BY_ID = {entry["id"]: entry for entry in MEGAPROJECTS}
megaproject_progress = {}  # project id -> {planet: amount sent}
megaprojects_built = []  # ids built in this run
megaprojects_all_ever = False  # lifetime: all four built in one run once


def _mega_need(project_id, planet):
    return dict(MEGAPROJECT_BY_ID[project_id]["needs"]).get(planet, 0)


def megaproject_sent(project_id, planet):
    if project_id in megaprojects_built:
        return _mega_need(project_id, planet)
    return megaproject_progress.get(project_id, {}).get(planet, 0.0)


def megaproject_percent(project_id):
    needs = MEGAPROJECT_BY_ID[project_id]["needs"]
    return 100.0 * sum(min(1.0, megaproject_sent(project_id, p) / amount) for p, amount in needs) / len(needs)


def megaproject_factor(key):
    factor = 1.0
    if "orbital_mirror" in megaprojects_built and key == "terraform":
        factor *= 1.25
    if "dyson_sail" in megaprojects_built and key == "produce":
        factor *= 1.2
    if "deep_core_tap" in megaprojects_built and key == "recycle":
        factor *= 1.5
    return factor


def sky_city_bonus_per_city(planet):
    base = PLANETS[planet].get("sky_city_production_bonus_per_city", 0)
    return base * (2 if "ring_habitat" in megaprojects_built else 1)


def send_to_megaproject(project_id, planet):
    """Moves what `planet` has banked toward its line of a project. Returns the amount sent."""
    global megaprojects_all_ever
    if project_id not in MEGAPROJECT_BY_ID or project_id in megaprojects_built or not _world_available(planet or ""):
        return 0
    need = _mega_need(project_id, planet)
    if need <= 0:
        return 0
    sent = megaproject_progress.setdefault(project_id, {}).get(planet, 0.0)
    amount = min(math.floor(planet_state[planet]["resource_count"] + 1e-9), need - sent)
    if amount <= 0:
        return 0
    planet_state[planet]["resource_count"] -= amount
    megaproject_progress[project_id][planet] = sent + amount
    if all(megaproject_progress[project_id].get(p, 0.0) >= a for p, a in MEGAPROJECT_BY_ID[project_id]["needs"]):
        megaprojects_built.append(project_id)
        _display_toast(f"Megaproject built: {MEGAPROJECT_BY_ID[project_id]['label']}. {MEGAPROJECT_BY_ID[project_id]['perk']}")
        if len(megaprojects_built) == len(MEGAPROJECTS):
            megaprojects_all_ever = True
    return amount


def _load_megaprojects(data):
    global megaprojects_all_ever
    megaproject_progress.clear()
    raw = data.get("megaproject_progress")
    if isinstance(raw, dict):
        for project_id, lines in raw.items():
            if project_id not in MEGAPROJECT_BY_ID or not isinstance(lines, dict):
                continue
            cleaned = {}
            for planet, amount in lines.items():
                need = _mega_need(project_id, planet)
                if need and isinstance(amount, (int, float)) and not isinstance(amount, bool) and 0 < amount < 10 ** 9:
                    cleaned[planet] = min(float(amount), float(need))
            if cleaned:
                megaproject_progress[project_id] = cleaned
    megaprojects_built[:] = [
        pid for pid in _clean_ids(data.get("megaprojects_built"), MEGAPROJECT_BY_ID)
    ]
    megaprojects_all_ever = data.get("megaprojects_all_ever") is True or len(megaprojects_built) == len(MEGAPROJECTS)


def _ring(percent):
    """A progress ring made from a conic gradient, with the percent as plain text inside."""
    ring = document.createElement("span")
    ring.className = "mega-ring"
    ring.setAttribute("role", "img")
    ring.setAttribute("aria-label", f"{round(percent)} percent built")
    ring.style.background = f"conic-gradient(var(--mega-ring-fill, #6fb3ff) {percent * 3.6}deg, var(--mega-ring-rest, #2a3350) 0)"
    ring.innerText = f"{round(percent)}%"
    return ring


def _build_megaproject_section(panel):
    panel.appendChild(_make_text("stats-panel-heading", f"Megaprojects ({len(megaprojects_built)}/{len(MEGAPROJECTS)} built this run)"))
    panel.appendChild(_make_text(
        "chains-intro",
        "Each work needs resources from several worlds at once. Send what a world has banked and the ring fills; "
        "a finished work keeps its perk for the rest of the run. Build all four for a secret ending line.",
    ))
    for project in MEGAPROJECTS:
        pid = project["id"]
        built = pid in megaprojects_built
        card = document.createElement("div")
        card.className = "chain-card chain-card--found" if built else "chain-card"
        head = document.createElement("div")
        head.className = "mega-head"
        ring = _ring(megaproject_percent(pid))
        head.appendChild(ring)
        title = document.createElement("div")
        title.appendChild(_make_text("chain-card-name", project["label"] + (" (built)" if built else "")))
        title.appendChild(_make_text("chain-card-detail", "Perk: " + project["perk"]))
        head.appendChild(title)
        card.appendChild(head)
        refs = {"ring": ring, "lines": {}}
        if not built:
            for planet, amount in project["needs"]:
                row = document.createElement("div")
                row.className = "mega-line"
                text = _make_text("chain-card-count", "")
                row.appendChild(text)
                button = _make_button("Send what you can",
                                      {"data-action": "send", "data-project": pid, "data-planet": planet}, None)
                row.appendChild(button)
                card.appendChild(row)
                refs["lines"][planet] = (text, button)
        panel.appendChild(card)
        _charter_refs["mega:" + pid] = refs


def _refresh_megaproject_values():
    for project in MEGAPROJECTS:
        pid = project["id"]
        refs = _charter_refs.get("mega:" + pid)
        if refs is None:
            continue
        percent = megaproject_percent(pid)
        refs["ring"].style.background = (
            f"conic-gradient(var(--mega-ring-fill, #6fb3ff) {percent * 3.6}deg, var(--mega-ring-rest, #2a3350) 0)")
        refs["ring"].innerText = f"{round(percent)}%"
        refs["ring"].setAttribute("aria-label", f"{round(percent)} percent built")
        for planet, amount in project["needs"]:
            line = refs["lines"].get(planet)
            if line is None:
                continue
            text, button = line
            name = PLANET_DISPLAY_NAMES.get(planet, planet)
            sent = megaproject_sent(pid, planet)
            resource = PLANETS[planet]["resource_name"]
            if _world_available(planet):
                banked = math.floor(planet_state[planet]["resource_count"] + 1e-9)
                text.innerText = f"{resource} from {name}: {math.floor(sent)} of {amount} sent ({banked} banked)"
                button.disabled = banked < 1 or sent >= amount
            else:
                text.innerText = f"{resource} from {name}: {math.floor(sent)} of {amount} sent (reach {name} first)"
                button.disabled = True


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
doctrine_open = False
_doctrine_draft = {"planet": "Earth", "cond": "ecology_below", "level": 30, "action": "recycler"}
_doctrine_fired_counts = {}  # rule index -> times fired (per session; reset when the list changes)
_doctrine_last_fired = {}  # planet -> (rule text, game tick)
_doctrine_relief_ready = {}  # planet -> tick when relief may fire again
_doctrine_dry_text = ""
_doctrine_signature = None
_doctrine_refs = {}
_dry_run = False


def doctrines_unlocked():
    return DOCTRINE_UNLOCK_NODE in researched_nodes


def doctrine_rule_limit():
    return DOCTRINE_MAX_RULES if prestige_has("standing_orders") else DOCTRINE_BASE_RULES


def _doctrine_reset_runtime():
    global _doctrine_dry_text
    _doctrine_fired_counts.clear()
    _doctrine_last_fired.clear()
    _doctrine_relief_ready.clear()
    _doctrine_dry_text = ""


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
    _doctrine_fired_counts[index] = _doctrine_fired_counts.get(index, 0) + 1
    _doctrine_last_fired[rule["planet"]] = (doctrine_rule_text(rule), total_ticks)


def _doctrine_buy(planet, kind):
    global governor_purchase_count, lifetime_generators_built, lifetime_recyclers_built, any_generator_ever_built
    state = planet_state[planet]
    if kind == "generator":
        cost = generator_cost(planet)
        if state["resource_count"] < cost:
            return False
        state["resource_count"] -= cost
        state["generator_count"] += 1
        lifetime_generators_built += 1
        any_generator_ever_built = True
    else:
        cost = recycler_cost(planet)
        if state["resource_count"] < cost:
            return False
        state["resource_count"] -= cost
        state["recycler_count"] += 1
        lifetime_recyclers_built += 1
    governor_purchase_count += 1
    if not _dry_run:
        update_generator_display(planet)
        update_ecology_display(planet)
    return True


def _doctrine_relief(planet):
    ready = _doctrine_relief_ready.get(planet, 0)
    if total_ticks < ready:
        return False
    sources = [p for p in _overview_planets() if p != planet and planet_state[p]["resource_count"] >= DOCTRINE_RELIEF_COST]
    if not sources:
        return False
    source = max(sources, key=lambda p: planet_state[p]["resource_count"])
    planet_state[source]["resource_count"] -= DOCTRINE_RELIEF_COST
    state = planet_state[planet]
    state["ecology_health"] = clamp(state["ecology_health"] + DOCTRINE_RELIEF_ECOLOGY, 0.0, ECOLOGY_MAX)
    _doctrine_relief_ready[planet] = total_ticks + DOCTRINE_RELIEF_COOLDOWN_TICKS
    return True


def _doctrine_route(planet):
    global lifetime_trade_routes_built
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
    lifetime_trade_routes_built += 1
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
    last = _doctrine_last_fired.get(planet)
    if last is None:
        return "Doctrine: no rule has fired here yet."
    seconds = max(0, (total_ticks - last[1]) * TICK_INTERVAL_MS // 1000)
    return f"Doctrine fired {seconds}s ago: {last[0]}"


def _run_headless(ticks, on_tick=None, all_governed=False):
    """Runs `ticks` of simulate plus Governor (and Doctrines) on a copy of the numbers: the DOM is never touched
    and every number is put back in a `finally`. `on_tick(i)` is called after each tick. With `all_governed`
    nobody is standing anywhere, so the Governor runs every world (and the sandbox is off). Returns the
    per-rule fire counts of the run."""
    global _dry_run, _doctrine_fired_counts, _doctrine_last_fired, _doctrine_relief_ready, _active_anomaly
    global governor_purchase_count, governor_tick_count, lifetime_generators_built, lifetime_recyclers_built
    global lifetime_trade_routes_built, lifetime_resources_generated_by_automation, any_generator_ever_built
    global total_ticks, current_planet, sandbox_mode
    snapshot = (
        copy.deepcopy(planet_state), governor_purchase_count, governor_tick_count, lifetime_generators_built,
        lifetime_recyclers_built, lifetime_trade_routes_built, lifetime_resources_generated_by_automation,
        any_generator_ever_built, dict(_doctrine_fired_counts), dict(_doctrine_last_fired),
        dict(_doctrine_relief_ready), total_ticks, current_planet, sandbox_mode, _active_anomaly,
    )
    _doctrine_fired_counts = {}
    _dry_run = True
    try:
        if all_governed:
            current_planet, sandbox_mode, _active_anomaly = "Deep space", False, None
        for index in range(ticks):
            total_ticks += 1
            incoming = {p: _incoming_trade_restore(p) for p in PLANETS}
            for planet in PLANETS:
                _simulate_planet(planet, incoming[planet])
            governor_step()
            if on_tick is not None:
                on_tick(index)
        counts = dict(_doctrine_fired_counts)
    finally:
        _dry_run = False
        _stress_factors.clear()
        (saved_state, governor_purchase_count, governor_tick_count, lifetime_generators_built,
         lifetime_recyclers_built, lifetime_trade_routes_built, lifetime_resources_generated_by_automation,
         any_generator_ever_built, _doctrine_fired_counts, _doctrine_last_fired, _doctrine_relief_ready,
         total_ticks, current_planet, sandbox_mode, _active_anomaly) = snapshot
        for planet, values in saved_state.items():
            planet_state[planet].clear()
            planet_state[planet].update(values)
    return counts


def doctrine_dry_run():
    """A-8: runs the rules for DRY_RUN_TICKS on a copy of the numbers. Returns (total fires, per-rule counts)."""
    counts = _run_headless(DRY_RUN_TICKS)
    return sum(counts.values()), counts


def on_toggle_doctrine(event=None):
    global doctrine_open
    doctrine_open = not doctrine_open
    update_doctrine_display()


def on_doctrine_click(event):
    global _doctrine_dry_text, _doctrine_signature
    action = _target_attr(event, "data-action")
    value = _target_attr(event, "data-value")
    if action == "draft-planet" and value in PLANETS:
        _doctrine_draft["planet"] = value
    elif action == "draft-cond" and value and ":" in value:
        cond, _, level = value.partition(":")
        if cond in DOCTRINE_CONDITIONS and level.isdigit() and int(level) in DOCTRINE_CONDITIONS[cond]["levels"]:
            _doctrine_draft["cond"], _doctrine_draft["level"] = cond, int(level)
    elif action == "draft-action" and value in DOCTRINE_ACTIONS:
        _doctrine_draft["action"] = value
    elif action == "add":
        if len(doctrine_rules) < doctrine_rule_limit():
            doctrine_rules.append(dict(_doctrine_draft))
            _doctrine_reset_runtime()
    elif action == "remove":
        index = int(value) if value and value.isdigit() else -1
        if 0 <= index < len(doctrine_rules):
            del doctrine_rules[index]
            _doctrine_reset_runtime()
    elif action == "dry-run":
        total, counts = doctrine_dry_run()
        _doctrine_dry_text = (
            f"Over the next {DRY_RUN_TICKS} ticks ({DRY_RUN_TICKS * TICK_INTERVAL_MS / 1000:g} seconds) these rules "
            f"would have fired {total} time{'s' if total != 1 else ''}"
            + (": " + ", ".join(f"rule {i + 1} x{n}" for i, n in sorted(counts.items())) if counts else "")
            + ". Nothing was changed."
        )
    _doctrine_signature = None
    update_doctrine_display()


def _doctrine_structure_signature():
    return (doctrines_unlocked(), doctrine_rule_limit(), tuple(tuple(sorted(r.items())) for r in doctrine_rules),
            tuple(sorted(_doctrine_draft.items())), tuple(_overview_planets()), _doctrine_dry_text, current_planet)


def _doctrine_pill(text, attrs, selected):
    return _make_button(text, attrs, None, selected=selected)


def _build_doctrine_panel():
    panel = document.getElementById("doctrine-panel")
    panel.innerHTML = ""
    _doctrine_refs.clear()
    panel.appendChild(_make_text("stats-panel-heading", f"Governor Doctrines ({len(doctrine_rules)}/{doctrine_rule_limit()} rules)"))
    panel.appendChild(_make_text(
        "chains-intro",
        "If/then rules for worlds you are not standing on, checked in order every tick. They kept in a save and "
        "sleep until Automation Basics is researched again after a prestige. Standing Orders in the Prestige "
        "Tree raises the limit from 3 to 5."))
    for index, rule in enumerate(doctrine_rules):
        card = document.createElement("div")
        card.className = "chain-card chain-card--found"
        card.appendChild(_make_text("chain-card-name", f"{index + 1}. {doctrine_rule_text(rule)}"))
        fired = _make_text("chain-card-count", "")
        card.appendChild(fired)
        if rule["planet"] == current_planet:
            card.appendChild(_make_text("chain-card-detail", "You are standing here, so the Governor is not running this rule right now."))
        if index >= doctrine_rule_limit():
            card.appendChild(_make_text("chain-card-detail", "Over the limit, so this rule is not running."))
        card.appendChild(_make_button("Remove", {"data-action": "remove", "data-value": str(index)}, None))
        panel.appendChild(card)
        _doctrine_refs[index] = fired
    if not doctrine_rules:
        panel.appendChild(_make_text("chains-intro", "No rules yet. Build one below."))
    panel.appendChild(_make_text("stats-panel-heading", "New rule"))
    row = document.createElement("div")
    row.className = "overview-actions"
    row.appendChild(_make_text("overview-actions-label", "World:", "span"))
    for planet in _overview_planets():
        row.appendChild(_doctrine_pill(PLANET_DISPLAY_NAMES.get(planet, planet),
                                       {"data-action": "draft-planet", "data-value": planet},
                                       _doctrine_draft["planet"] == planet))
    panel.appendChild(row)
    row = document.createElement("div")
    row.className = "overview-actions"
    row.appendChild(_make_text("overview-actions-label", "When:", "span"))
    resource = PLANETS[_doctrine_draft["planet"]]["resource_name"] if _doctrine_draft["planet"] in PLANETS else "stock"
    for cond, spec in DOCTRINE_CONDITIONS.items():
        for level in spec["levels"]:
            label = spec["label"].format(level=f"{level:,}", resource=resource)
            row.appendChild(_doctrine_pill(label[0].upper() + label[1:],
                                           {"data-action": "draft-cond", "data-value": f"{cond}:{level}"},
                                           _doctrine_draft["cond"] == cond and _doctrine_draft["level"] == level))
    panel.appendChild(row)
    row = document.createElement("div")
    row.className = "overview-actions"
    row.appendChild(_make_text("overview-actions-label", "Then:", "span"))
    for key, text in DOCTRINE_ACTIONS.items():
        row.appendChild(_doctrine_pill(text[0].upper() + text[1:], {"data-action": "draft-action", "data-value": key},
                                       _doctrine_draft["action"] == key))
    panel.appendChild(row)
    panel.appendChild(_make_text("chain-card-detail", "Preview: " + doctrine_rule_text(_doctrine_draft)))
    actions = document.createElement("div")
    actions.className = "overview-actions"
    actions.appendChild(_make_button("Add rule", {"data-action": "add"}, None,
                                     disabled=len(doctrine_rules) >= doctrine_rule_limit()))
    actions.appendChild(_make_button(f"Try for {DRY_RUN_TICKS} ticks", {"data-action": "dry-run"},
                                     "Runs your rules on a copy of the numbers and says how often each would fire. Nothing real changes."))
    panel.appendChild(actions)
    if _doctrine_dry_text:
        dry = _make_text("chain-card-count", _doctrine_dry_text)
        dry.setAttribute("role", "status")
        panel.appendChild(dry)


def update_doctrine_display():
    global _doctrine_signature
    toggle = document.getElementById("doctrine-toggle-button")
    panel = document.getElementById("doctrine-panel")
    toggle.hidden = not doctrines_unlocked()
    toggle.innerText = "Hide Doctrines" if doctrine_open else f"\U0001f4d0 Doctrines ({len(doctrine_rules)}/{doctrine_rule_limit()})"
    panel.hidden = not (doctrine_open and doctrines_unlocked())
    if panel.hidden:
        _doctrine_signature = None
        return
    signature = _doctrine_structure_signature()
    if signature != _doctrine_signature:
        _build_doctrine_panel()
        _doctrine_signature = signature
    for index, element in _doctrine_refs.items():
        n = _doctrine_fired_counts.get(index, 0)
        element.innerText = f"Fired {n} time{'s' if n != 1 else ''} this session"


# --- A-27 / A-28: Ecology Stress Test ------------------------------------------
# An optional endgame arena, open once every world is terraformed. It runs on a
# copy of your numbers (nothing real changes, no achievements or boards are
# touched): for three minutes of game time a cascade of anomalies hits every world
# (decay x1.5, then x2 with trade restore halved, then x2.5), nobody is standing
# anywhere, and only your Governor settings and Doctrines act. The line is an
# average ecology of STRESS_LINE% across all eight worlds; the score is how far
# above the line the worst moment stayed (negative = it dipped under). A-28: a
# strip per world of 12 blocks (the lowest ecology in each 15 seconds), height
# plus "!" under 10% and "x" at 0%, so it reads without colour.
STRESS_TICKS = 1800
STRESS_SAMPLE_EVERY = 150
STRESS_LINE = 40.0
STRESS_PHASES = [(0, {"decay": 1.5}), (600, {"decay": 2.0, "trade": 0.5}), (1200, {"decay": 2.5, "trade": 0.5})]
STRESS_BLOCKS = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"
stress_best_margin = None  # lifetime best margin, saved when set
_stress_last = None
_stress_run_id = 0


def stress_block(ecology):
    if ecology <= 0:
        return "x"
    if ecology < LOW_ECOLOGY_THRESHOLD:
        return "!"
    return STRESS_BLOCKS[min(len(STRESS_BLOCKS) - 1, int(ecology / (ECOLOGY_MAX / len(STRESS_BLOCKS))))]


def run_stress_test():
    """Runs the test. Returns the result dict, or None when the system is not fully terraformed yet."""
    global stress_best_margin, _stress_last, _stress_run_id
    if not _prestige_available():
        return None
    buckets = STRESS_TICKS // STRESS_SAMPLE_EVERY
    lows = {p: [100.0] * buckets for p in PLANETS}
    worst = [100.0]

    def sample(index):
        for phase_start, factors in STRESS_PHASES:
            if index >= phase_start:
                _stress_factors.clear()
                _stress_factors.update(factors)
        bucket = min(buckets - 1, index // STRESS_SAMPLE_EVERY)
        total = 0.0
        for planet in PLANETS:
            ecology = planet_state[planet]["ecology_health"]
            total += ecology
            lows[planet][bucket] = min(lows[planet][bucket], ecology)
        worst[0] = min(worst[0], total / len(PLANETS))

    _stress_factors.update(STRESS_PHASES[0][1])
    _run_headless(STRESS_TICKS, on_tick=sample, all_governed=True)
    margin = round(worst[0] - STRESS_LINE, 1)
    _stress_last = {"margin": margin, "lowest": round(worst[0], 1), "rows": lows}
    if stress_best_margin is None or margin > stress_best_margin:
        stress_best_margin = margin
    _stress_run_id += 1
    return _stress_last


def _build_stress_section(panel):
    panel.appendChild(_make_text("stats-panel-heading", "Ecology Stress Test"))
    panel.appendChild(_make_text(
        "chains-intro",
        f"An optional endgame arena. For {STRESS_TICKS * TICK_INTERVAL_MS // 60000} minutes of game time a cascade of "
        "anomalies hits every world and only your Governor settings and Doctrines act: no clicking. The line is an "
        f"average ecology of {round(STRESS_LINE)}% across all worlds. It runs on a copy, so nothing in your game "
        "changes."))
    if stress_best_margin is not None:
        panel.appendChild(_make_text("chain-card-count", f"Best so far: {stress_best_margin:+.1f} points from the line."))
    ready = _prestige_available()
    panel.appendChild(_make_button("Run the stress test" if ready else "Opens when every world is terraformed",
                                   {"data-action": "stress"}, None, disabled=not ready))
    if _stress_last is None:
        return
    verdict = "held the line" if _stress_last["margin"] >= 0 else "dipped under the line"
    result = _make_text(
        "chain-card-count",
        f"Result: {verdict}. Worst average ecology {_stress_last['lowest']}%, which is "
        f"{_stress_last['margin']:+.1f} points from the line.")
    result.setAttribute("role", "status")
    panel.appendChild(result)
    panel.appendChild(_make_text(
        "chain-card-detail",
        "Each block is the lowest ecology in 15 seconds: taller is healthier, ! is under 10% (output penalty), x is 0%."))
    for planet in PLANETS:
        values = _stress_last["rows"][planet]
        strip = "".join(stress_block(v) for v in values)
        panel.appendChild(_make_text(
            "stress-strip", f"{PLANET_DISPLAY_NAMES.get(planet, planet)}: {strip} lowest {round(min(values))}%"))


# --- A-23: Blueprint Swap ------------------------------------------------------
# One short text code holds a build plan (the step texts, never the ticks), the
# Doctrine rules and the mutator picks. Importing never changes anything by
# itself: the code shows up as a faint "ghost" list under the Build Plan, and each
# part is adopted with its own button (steps are added to the end of your plan,
# rules only up to your limit, mutator picks replace the picks for the next run).
# Local only: no backend, nothing is saved, the ghost is gone on reload.
BLUEPRINT_PREFIX = "SOLPLAN1:"
_ghost = {"steps": [], "rules": [], "mutators": []}


def blueprint_code():
    payload = {
        "p": [step["text"] for step in build_plan],
        "d": [dict(rule) for rule in doctrine_rules],
        "m": list(mutators_next),
    }
    return export_progress.encode_progress_code(payload, prefix=BLUEPRINT_PREFIX)


def parse_blueprint(code):
    """Returns (True, {"steps", "rules", "mutators"}) or (False, message). Never raises."""
    ok, payload = export_progress.decode_progress_code(
        (code or "").strip(), prefix=BLUEPRINT_PREFIX, bad_format_message="That does not look like a SOL blueprint code.")
    if not ok:
        return False, payload
    steps = []
    raw_steps = payload.get("p")
    if isinstance(raw_steps, list):
        for text in raw_steps[:BUILD_PLAN_MAX_STEPS]:
            if isinstance(text, str) and text.strip():
                steps.append(text.strip()[:BUILD_PLAN_MAX_LEN])
    rules = _clean_doctrine_rules(payload.get("d"))
    mutators = _clean_mutators(payload.get("m"))
    if not (steps or rules or mutators):
        return False, "That blueprint is empty."
    return True, {"steps": steps, "rules": rules, "mutators": mutators}


def _blueprint_status(text):
    document.getElementById("blueprint-status").innerText = text


def on_blueprint_make(event=None):
    code = blueprint_code()
    output = document.getElementById("blueprint-output")
    output.value = code
    output.hidden = False
    try:
        import js  # noqa: PLC0415

        js.navigator.clipboard.writeText(code)
        _blueprint_status("Blueprint made and copied. Share the code; the other player pastes it under Import.")
    except (ImportError, AttributeError):
        _blueprint_status("Blueprint made: select the code below and copy it.")


def on_blueprint_import(event=None):
    ok, result = parse_blueprint(document.getElementById("blueprint-input").value)
    if not ok:
        _blueprint_status(result)
        return
    _ghost["steps"], _ghost["rules"], _ghost["mutators"] = result["steps"], result["rules"], result["mutators"]
    _blueprint_status("Blueprint loaded as a ghost below. Nothing has changed in your game yet.")
    update_blueprint_ghost()


def on_blueprint_ghost_click(event):
    action = _target_attr(event, "data-action")
    if action == "clear":
        _ghost["steps"], _ghost["rules"], _ghost["mutators"] = [], [], []
    elif action == "add-step":
        raw = _target_attr(event, "data-step")
        index = int(raw) if raw and raw.isdigit() else -1
        if 0 <= index < len(_ghost["steps"]):
            _add_build_step(_ghost["steps"][index])
    elif action == "add-all":
        for text in _ghost["steps"]:
            if text not in {step["text"] for step in build_plan}:
                _add_build_step(text)
    elif action == "adopt-rules":
        room = DOCTRINE_MAX_RULES - len(doctrine_rules)
        have = {tuple(sorted(rule.items())) for rule in doctrine_rules}
        added = 0
        for rule in _ghost["rules"]:
            if added < room and tuple(sorted(rule.items())) not in have:
                doctrine_rules.append(dict(rule))
                added += 1
        if added:
            _doctrine_reset_runtime()
        _blueprint_status(f"Added {added} rule(s) to your Doctrines. Rules above your limit wait until it is raised.")
    elif action == "use-mutators":
        mutators_next[:] = list(_ghost["mutators"])
        _blueprint_status("Your mutator picks for the next run now match the blueprint.")
    update_blueprint_ghost()
    update_build_plan_display()
    update_doctrine_display()


def update_blueprint_ghost():
    box = document.getElementById("blueprint-ghost")
    box.innerHTML = ""
    if not (_ghost["steps"] or _ghost["rules"] or _ghost["mutators"]):
        box.hidden = True
        return
    box.hidden = False
    box.appendChild(_make_text("stats-panel-heading", "Ghost blueprint (not part of your game yet)"))
    mine = {step["text"] for step in build_plan}
    for index, text in enumerate(_ghost["steps"]):
        row = document.createElement("div")
        row.className = "build-plan-row build-plan-row--ghost"
        row.appendChild(_make_text("build-plan-text", ("\u2713 " if text in mine else "\u25cb ") + text, "span"))
        if text not in mine:
            row.appendChild(_make_button("Add to my plan", {"data-action": "add-step", "data-step": str(index)}, None))
        box.appendChild(row)
    if _ghost["steps"]:
        box.appendChild(_make_button("Add every step", {"data-action": "add-all"}, None))
    for rule in _ghost["rules"]:
        box.appendChild(_make_text("build-plan-text", "Rule: " + doctrine_rule_text(rule)))
    if _ghost["rules"]:
        box.appendChild(_make_button("Add these rules to my Doctrines", {"data-action": "adopt-rules"}, None))
    if _ghost["mutators"]:
        names = ", ".join(MUTATOR_BY_ID[m_id]["label"] for m_id in _ghost["mutators"])
        box.appendChild(_make_text("build-plan-text", f"Mutator picks: {names}"))
        box.appendChild(_make_button("Use these mutator picks", {"data-action": "use-mutators"}, None))
    box.appendChild(_make_button("Clear the ghost", {"data-action": "clear"}, None))


# --- A-19 / A-20: the hidden Codex -----------------------------------------------
# Seven worlds end their Overview note with one odd sentence. Doing what it
# hints at (nothing is timed, random or lost) records a silly Codex curio. The
# Codex section of the Charter stays hidden, and so does its "found n/7" count,
# until the first clue is found; after that every clue that is still open shows
# its odd sentence and a "Show a hint" button that spells out what to do. All
# seven are live conditions on state, except Venus-last, which watches worlds
# finishing terraforming in order (a loaded save counts worlds already done as
# earlier). Collector achievement: Codex Keeper.
WORLD_NOTES = {
    "Moon": "Low gravity, long shadows, patient dust. Thirteen is a number that keeps its promises.",
    "Mars": "Red dust and an old riverbed. Seven kettles will always find Earth.",
    "Venus": "A furnace under a cloud deck. Venus would like to be remembered as the last to finish.",
    "AsteroidBelt": "Rubble that never became a planet. The Belt always counts one short, and likes it.",
    "Pluto": "Cold, far and a little offended. When Pluto goes quiet, it will tell you it is fine.",
    "JupiterMoons": "Floating cities over a storm. A choir with no Recycler hums the loudest.",
    "SaturnMoons": "Ring dust and methane lakes. Round numbers are a kind of respect.",
}
CLUES = [
    {"id": "bakers_dozen", "world": "Moon", "name": "The Baker's Dozen",
     "curio": "Thirteen Auto-Miners on one world. Nobody asked, and it ran fine.",
     "hint": "Own exactly 13 Auto-Miners on a single world.",
     "check": lambda: any(planet_state[p]["generator_count"] == 13 for p in PLANETS)},
    {"id": "seven_kettles", "world": "Mars", "name": "Seven Kettles",
     "curio": "Seven routes lead into Earth. The kettle is always on.",
     "hint": "Have at least 7 trade routes in total that all deliver to Earth.",
     "check": lambda: sum(planet_state[p]["trade_routes"].get("Earth", 0) for p in PLANETS if p != "Earth") >= 7},
    {"id": "last_on_purpose", "world": "Venus", "name": "Last, On Purpose",
     "curio": "Venus finished after everyone else, and has not stopped mentioning it.",
     "hint": "Terraform every other world to 100% first, then finish Venus.",
     "check": lambda: False},  # decided by _check_codex() watching the order worlds finish
    {"id": "off_by_one", "world": "AsteroidBelt", "name": "Off By One",
     "curio": "One Recycler fewer than machines. The Belt counted twice.",
     "hint": "On the Asteroid Belt, own at least 5 Auto-Miners and exactly one fewer Recycler.",
     "check": lambda: planet_state["AsteroidBelt"]["generator_count"] >= 5
     and planet_state["AsteroidBelt"]["recycler_count"] == planet_state["AsteroidBelt"]["generator_count"] - 1},
    {"id": "pluto_is_fine", "world": "Pluto", "name": "Pluto Is Fine",
     "curio": "Ecology at zero and the log says everything is fine. Restore it before it says that again.",
     "hint": "Let Pluto's ecology fall to 0% (it recovers; production just pauses until you rebuild it).",
     "check": lambda: planet_state["Pluto"]["generator_count"] >= 1 and planet_state["Pluto"]["ecology_health"] <= 0},
    {"id": "quiet_choir", "world": "JupiterMoons", "name": "The Quiet Choir",
     "curio": "Three Sky Cities and not one Recycler. They hum anyway.",
     "hint": "Over Jupiter's Moons, build 3 Sky Cities while owning no Recyclers there.",
     "check": lambda: planet_state["JupiterMoons"].get("sky_city_count", 0) >= 3
     and planet_state["JupiterMoons"]["recycler_count"] == 0},
    {"id": "round_number", "world": "SaturnMoons", "name": "Round Number",
     "curio": "Ten thousand Methane in the bank, on purpose.",
     "hint": "Hold 10,000 Methane on Saturn's Moons at once (the Governor spends banked stock, so turn its budget down first).",
     "check": lambda: planet_state["SaturnMoons"]["resource_count"] >= 10000},
]
CLUE_BY_ID = {entry["id"]: entry for entry in CLUES}
codex_found = []  # lifetime, in the order found
_codex_hints = set()  # clues whose hint the player asked for this session
_terraform_done_seen = set()  # worlds already at 100% as of the last tick (transient)


def _check_codex():
    global _terraform_done_seen
    done_now = {p for p in PLANETS if planet_state[p]["terraform_progress"] >= TERRAFORM_MAX}
    others = set(PLANETS) - {"Venus"}
    venus_last = "Venus" in done_now and "Venus" not in _terraform_done_seen and others <= _terraform_done_seen
    _terraform_done_seen = done_now
    for clue in CLUES:
        if clue["id"] in codex_found:
            continue
        if (venus_last if clue["id"] == "last_on_purpose" else clue["check"]()):
            codex_found.append(clue["id"])
            _display_toast(f"Codex entry found: {clue['name']}")


def _build_codex_section(panel):
    if not codex_found:
        return  # the whole section, and its count, stay hidden until the first clue is found
    panel.appendChild(_make_text("stats-panel-heading", f"Codex: {len(codex_found)} of {len(CLUES)} clues found"))
    for clue in CLUES:
        found = clue["id"] in codex_found
        card = document.createElement("div")
        card.className = "chain-card chain-card--found" if found else "chain-card"
        if found:
            card.appendChild(_make_text("chain-card-name", f"\U0001f4d6 {clue['name']}"))
            card.appendChild(_make_text("chain-card-detail", clue["curio"]))
        else:
            card.appendChild(_make_text("chain-card-name", "Not found yet"))
            note = WORLD_NOTES[clue["world"]]
            card.appendChild(_make_text(
                "chain-card-detail", f"{PLANET_DISPLAY_NAMES.get(clue['world'], clue['world'])} note: \u201c{note.split('. ')[-1]}\u201d"))
            if clue["id"] in _codex_hints:
                card.appendChild(_make_text("chain-card-count", "Hint: " + clue["hint"]))
            else:
                card.appendChild(_make_button("Show a hint", {"data-action": "hint", "data-clue": clue["id"]}, None))
        panel.appendChild(card)


# --- FY-53: "three goals at all times" (shared/goals-panel.js) ---------------
# The game owns the queue; the panel shows the first three that are not done.
# Every goal maps to something SOL already measures, so nothing here is new
# state: it is all derived from planet_state, research and visited_bodies.
def _research_level_progress(tier_index):
    nodes = [n for n in RESEARCH_NODES if n["tier"] == tier_index]
    return sum(1 for n in nodes if n["id"] in researched_nodes), len(nodes)


def _world_available(planet):
    return planet == "Earth" or planet in unlocked_bodies


def goals_list():
    """The ordered goal queue as plain dicts (id, label, current, target, reward, done)."""
    goals = []
    earth = planet_state["Earth"]
    goals.append({"id": "first_miner", "label": "Build your first Auto-Miner on Earth",
                  "current": min(1, earth["generator_count"]), "target": 1,
                  "reward": "Iron starts mining itself"})
    goals.append({"id": "first_recycler", "label": "Build a Recycler on Earth",
                  "current": min(1, earth["recycler_count"]), "target": 1,
                  "reward": "Slows the ecology decline"})
    done, total = _research_level_progress(0)
    goals.append({"id": "research_near", "label": "Research the Near Bodies level",
                  "current": done, "target": total, "reward": "Opens the Moon and Mars"})
    for planet in ("Mars", "Moon"):
        goals.append({"id": "visit_" + planet.lower(), "label": f"Visit {PLANET_DISPLAY_NAMES.get(planet, planet)}",
                      "current": 1 if planet in visited_bodies else 0, "target": 1,
                      "reward": "Counts toward Grand Tour"})
    done, total = _research_level_progress(1)
    goals.append({"id": "research_far", "label": "Research the Far Bodies level",
                  "current": done, "target": total, "reward": "Opens five more worlds"})
    goals.append({"id": "first_route", "label": "Build a trade route",
                  "current": min(1, lifetime_trade_routes_built), "target": 1,
                  "reward": "Ships ecology help to another world"})
    for planet in PLANETS:
        if _world_available(planet):
            name = PLANET_DISPLAY_NAMES.get(planet, planet)
            goals.append({"id": "terraform_" + planet.lower(), "label": f"Terraform {name} to 100%",
                          "current": int(planet_state[planet]["terraform_progress"]), "target": 100,
                          "reward": "Counts toward the whole-system win"})
    for planet in GAS_GIANT_BODIES:
        if _world_available(planet):
            name = PLANET_DISPLAY_NAMES.get(planet, planet)
            goals.append({"id": "sky_" + planet.lower(), "label": f"Build a Sky City over {name}",
                          "current": min(1, planet_state[planet].get("sky_city_count", 0)), "target": 1,
                          "reward": "Boosts that world's output"})
    return goals


def goals_json():
    return json.dumps(goals_list())


def _refresh_goals_panel():
    """Asks the shared panel (when the page has it) to redraw. Cheap; the fake-js
    test environment has no NoyvjGoals so this is a no-op there."""
    try:
        import js  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        panel = getattr(js, "NoyvjGoals", None)
        if panel is not None:
            panel.refreshAll()
    except ImportError:
        pass


def _start_tick_loop():
    """W-2: hands `tick` to shared/time-controls.js (pause and 1x/2x/4x) when the
    page has it, otherwise falls back to the plain setInterval this game always
    used (fake-js test environments and any page without the shared script).
    Either way the tick itself is untouched: the controller only changes how
    often it is called, and not at all while paused or while the tab is hidden
    (shared/pause-hidden.js). Returns "shared" or "interval"."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        controls = getattr(window, "NoyvjTime", None)
    except ImportError:
        controls = None
    if controls is not None and getattr(controls, "start", None) is not None:
        controls.start("sol", create_proxy(tick), TICK_INTERVAL_MS)
        return "shared"
    setInterval(create_proxy(tick), TICK_INTERVAL_MS)
    return "interval"


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

    document.getElementById("research-node-list").addEventListener("click", create_proxy(on_research_node_click))

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
    document.getElementById("build-plan-copy-button").addEventListener("click", create_proxy(on_build_plan_copy))
    document.getElementById("splits-toggle-button").addEventListener("click", create_proxy(on_toggle_splits))
    document.getElementById("chains-toggle-button").addEventListener("click", create_proxy(on_toggle_chains))
    document.getElementById("blueprint-make-button").addEventListener("click", create_proxy(on_blueprint_make))
    document.getElementById("blueprint-import-button").addEventListener("click", create_proxy(on_blueprint_import))
    document.getElementById("blueprint-ghost").addEventListener("click", create_proxy(on_blueprint_ghost_click))
    document.getElementById("doctrine-toggle-button").addEventListener("click", create_proxy(on_toggle_doctrine))
    document.getElementById("doctrine-panel").addEventListener("click", create_proxy(on_doctrine_click))
    document.getElementById("charter-toggle-button").addEventListener("click", create_proxy(on_toggle_charter))
    document.getElementById("charter-panel").addEventListener("click", create_proxy(on_charter_click))
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

    _start_tick_loop()


setup()
