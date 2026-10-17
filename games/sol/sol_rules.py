"""Fixed numbers and content tables: planets, research nodes and tiers, the prestige tree, Governor personalities, specialisations, build-plan limits, rumours, ghost and scarcity storage keys, and the small pure checks on them. No browser calls and no live state."""

import sol_runstate as runstate


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
researched_nodes = set()

# --- Prestige / New Game+ (A1, TODO.md) ---
PRESTIGE_BONUS_PER_LEVEL = 0.10  # +10% resource yield (manual clicks and automation) per level


def prestige_multiplier():
    return 1 + PRESTIGE_BONUS_PER_LEVEL * runstate.prestige_level


# --- Prestige tree (A1 second tier + A3 New Game+ variant) ---

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
    return node_id in runstate.prestige_nodes


def prestige_points_spent():
    return sum(PRESTIGE_TREE_BY_ID[n]["cost"] for n in runstate.prestige_nodes if n in PRESTIGE_TREE_BY_ID)


def prestige_points_available():
    return max(0, runstate.prestige_points_earned - prestige_points_spent())


def _challenge_on():
    return runstate.ng_challenge_active and prestige_has("ng_challenge")


def _sandbox_active():
    return runstate.sandbox_mode and _prestige_available()


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
        return runstate.governor_priority, runstate.governor_budget_pct
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

_ecology_low_seen = set()
_ecology_zero_seen = set()


# --- Lifetime stats (A4) + second achievement wave (A2/A13) tracked state ---

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

TICK_INTERVAL_MS = 100

ECOLOGY_MAX = 100.0
LOW_ECOLOGY_THRESHOLD = 10.0
LOW_ECOLOGY_PENALTY_MULTIPLIER = 0.75

GOVERNOR_BUDGET_STEP = 10.0
GOVERNOR_BUDGET_MIN = 0.0
GOVERNOR_BUDGET_MAX = 100.0


def _prestige_available():
    return runstate._scarcity is None and all(planet_state[p]["terraform_progress"] >= TERRAFORM_MAX for p in PLANETS)


# One-line ticker gossip with zero mechanical effect; each line is noted once, in the captain's log.
RUMORS = [
    {"id": "met:helios", "text": "Helios Combine has run a flag up at Cairn and is telling anyone who will listen that it was always theirs."},
    {"id": "met:ceres", "text": "Ceres Freight Guild has painted its name on Meridian. The paint is still wet, and somehow already peeling."},
    {"id": "met:outer", "text": "Outer Reach Syndicate calls Far Anchor home, mostly because nobody else has the patience to go that far."},
    {"id": "partner:helios", "text": "Helios Combine and you now share Cairn. Their newsletter calls it a strategic friendship."},
    {"id": "partner:ceres", "text": "Ceres Freight Guild shares Meridian with you and has stopped calling the arrangement temporary."},
    {"id": "partner:outer", "text": "Outer Reach Syndicate shares Far Anchor with you and sends a very polite message about the shared fridge."},
    {"id": "contest:helios", "text": "Helios Combine has moved its flag off Cairn and says it had been meaning to for a while."},
    {"id": "contest:ceres", "text": "Ceres Freight Guild has left Meridian with its schedule intact and its feelings, it says, unhurt."},
    {"id": "contest:outer", "text": "Outer Reach Syndicate has taken its lamp down from Far Anchor and mentioned the view will be missed."},
    {"id": "world:Mars", "rival": "helios", "text": "Helios Combine reports record Mars freight, and has asked that the word record not be checked."},
    {"id": "world:AsteroidBelt", "rival": "ceres", "text": "Ceres Freight Guild reports record Belt yields and a new kind of lunch."},
    {"id": "world:JupiterMoons", "rival": "outer", "text": "Outer Reach Syndicate says the clouds over Jupiter's moons have started to look like a view."},
]
RUMOR_BY_ID = {entry["id"]: entry for entry in RUMORS}

SCARCITY_OFF_KEYS = ("sol-click-streak", "sol-chain-bonus", "sol-anomalies", "sol-rivals")

GHOST_PB_KEY = "sol-ghost-pb-v1"
GHOST_LIVE_KEY = "sol-ghost-live-v1"
GHOST_DAILY_KEY = "sol-ghost-daily-v1"
GHOST_ON_KEY = "sol-ghost-on"
GHOST_DAILY_KEEP = 40
GHOST_SAVE_EVERY = 8  # samples between writes of the in-progress recording (200 ticks)
TODAY_OVERRIDE = None  # tests (and nothing else) may set this to a YYYY-MM-DD text
