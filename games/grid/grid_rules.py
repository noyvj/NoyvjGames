"""Grid's numbers and tables: costs, capacities, emissions factors, wear tiers, scenarios, grants, the career tree, default
settings. Data only. Ask for this file to change a price, a rate, a threshold or a table.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

import random

import seed as seed_lib


STARTING_FUNDS = 500
STARTING_DEMAND = 100
DEMAND_GROWTH_PER_ROUND = 10
REVENUE_PER_UNIT_MET = 2
REFUND_FRACTION = 0.5

# C3: the regional grid's own demand as a fraction of this grid's demand --
# grows automatically alongside it, no separate growth model needed. It has
# no plants of its own; it leans on this grid's spare capacity instead.
REGIONAL_DEMAND_FRACTION = 0.35
# Selling spare capacity into the regional grid earns less than meeting
# your own demand -- it's surplus that would otherwise go to waste, not a
# second market at full price.
REGIONAL_REVENUE_PER_UNIT_SHARED = 1
# Whatever regional demand your surplus doesn't cover falls back to buying
# power in for it, at a real cost -- the connection is a real decision,
# not a pure bonus.
REGIONAL_SHORTFALL_COST_PER_UNIT = 3

# Order matters for rendering — cheapest/dirtiest first, mirroring the
# real-world build order the game wants players to eventually move away
# from.

# C2 -- "battery" is a grid-storage tier, not a generation tier: it never
# produces power of its own, so it's deliberately excluded from
# GENERATION_TYPES below (total_capacity()/fossil_share()/the plant-mix
# chart all stay generation-only) and from RENEWABLE_TYPES (it doesn't
# offset emissions directly, so it must never count toward the
# clean-capacity-share metric the achievements/callouts are built on --
# that would let a player "go clean" by buying storage instead of
# actually building clean generation, undermining the whole lesson).
# Its mechanical role is scoped narrowly and directly to what real grid
# storage actually does: buffer renewable intermittency -- see
# GridState.effective_capacity_for_revenue()'s weather-variability
# compensation. It deliberately does NOT dampen emissions-driven
# disruption/brownout losses -- that's a different mechanic (grid
# instability from a dirty fleet), and blunting it with a purchasable
# item would dilute the emissions-disruption link Pass 3 confirmed is
# this game's central lesson-carrying mechanism.
PLANT_TYPES = ["coal", "gas", "nuclear", "solar", "wind", "hydro", "battery"]

GENERATION_TYPES = tuple(t for t in PLANT_TYPES if t != "battery")

PLANT_LABEL = {
    "coal": "Coal",
    "gas": "Gas",
    "nuclear": "Nuclear",
    "solar": "Solar",
    "wind": "Wind",
    "hydro": "Hydro",
    "battery": "Battery Storage",
}

PLANT_ICON = {
    "coal": "⚫",  # black circle
    "gas": "\U0001F525",  # fire
    "nuclear": "☢️",  # radioactive
    "solar": "☀️",  # sun
    "wind": "\U0001F4A8",  # dash/wind
    "hydro": "\U0001F4A7",  # droplet
    "battery": "\U0001F50B",  # battery
}

# Flat, un-degraded costs and generation capacity per unit. Renewable
# cost decay off these base costs is applied by plant_cost() below.
# Battery's "capacity" is storage-buffer capacity, not generation --
# see effective_capacity_for_revenue().
PLANT_BASE_COST = {
    "coal": 50,
    "gas": 40,
    "nuclear": 200,
    "solar": 80,
    "wind": 70,
    "hydro": 150,
    "battery": 120,
}

PLANT_CAPACITY = {
    "coal": 20,
    "gas": 15,
    "nuclear": 100,
    "solar": 10,
    "wind": 12,
    "hydro": 40,
    "battery": 15,
}

# Emissions produced per unit of capacity, per round, while that capacity
# is part of the fleet. Nuclear counts as zero-emission but — realistically,
# and per the plan's framing — isn't part of the renewable cost-curve
# below; its cost stays flat. Battery is also zero-emission (it stores,
# doesn't generate).
EMISSIONS_FACTOR = {
    "coal": 3.0,
    "gas": 1.5,
    "nuclear": 0.0,
    "solar": 0.0,
    "wind": 0.0,
    "hydro": 0.0,
    "battery": 0.0,
}

RENEWABLE_TYPES = {"solar", "wind", "hydro"}

# Wright's-law-style learning curve: each renewable unit ever built (not
# just currently standing — retiring one doesn't erase the learning)
# permanently makes the next one of that type a little cheaper, floored so
# it never becomes free.
RENEWABLE_COST_DECAY = 0.95
MIN_COST_MULTIPLIER = 0.4

FOSSIL_TYPES = ("coal", "gas")

# Disruption events: probability AND severity both scale with emissions,
# so a dirty grid gets progressively harder to manage rather than
# suddenly "losing" — there's no funds floor here, only a shrinking gain,
# so this can never bankrupt the player outright (no hard fail-state).
DISRUPTION_PROBABILITY_SCALE = 2000.0
MAX_DISRUPTION_PROBABILITY = 0.9
DISRUPTION_SEVERITY_SCALE = 3000.0
MAX_REVENUE_LOSS_FRACTION = 0.8
DAMAGE_SEVERITY_THRESHOLD = 0.5

# C16 -- opt-in "steeper demand growth" difficulty variant. A separate
# knob from the emissions-driven disruption curve above (see CLAUDE.md's
# Pass 3 note: that curve is the one that has to scale with the mechanic
# that teaches the lesson, emissions, not a bolted-on separate difficulty
# system) -- this only changes how fast demand rises, it never touches
# disruption_probability()/disruption_severity() or their inputs.
STEEP_DEMAND_GROWTH_MULTIPLIER = 2.0

# C4 -- opt-in "weather variability on renewable output" hard mode.
# Explicitly scoped out of Pass 1 as a deliberate deferral (see CLAUDE.md);
# picked back up here as an opt-in extra, never default-on, and -- same
# reasoning as C16 above -- a separate knob from the emissions-driven
# disruption curve. This only ever affects this round's *actual* output
# for revenue purposes; it never touches total_capacity() (the "installed"
# figure used for cost/display elsewhere), emissions, or disruption math.
WEATHER_VARIANCE_FRACTION = 0.2

# Reference point for the emissions meter bar — matches the severity
# scale, so a full bar means disruption severity has hit its own cap.
EMISSIONS_METER_MAX = DISRUPTION_SEVERITY_SCALE

# Iteration Pass 2 — global comparison: a hardcoded real-world-ish
# benchmark (roughly matching global electricity generation's fossil
# share and an average coal/gas emissions factor) so the player's actual
# emissions trajectory has something concrete to be measured against,
# not just "went up" or "went down" in isolation.
GLOBAL_AVG_FOSSIL_SHARE = 0.61
GLOBAL_AVG_FOSSIL_EMISSIONS_FACTOR = (EMISSIONS_FACTOR["coal"] + EMISSIONS_FACTOR["gas"]) / 2

# C17 -- the closing "grid vs. business-as-usual" counterfactual: a
# self-comparison against a hypothetical grid that built the exact same
# total capacity this playthrough did, but entirely as coal, tracked
# round by round in GridState.bau_emissions (see advance_round()).
# Deliberately isolates the fuel-mix decision by holding how much got
# built constant -- a demand-based version would instead reward
# under-building relative to rising demand as if it were "clean," which
# isn't the lesson this is meant to teach. Also distinct from the Pass 2
# global-average-fossil-mix benchmark above: that one answers "how do I
# compare to the real world," this one answers "how much did *my own*
# fuel-mix choices this run actually save."
BAU_EMISSIONS_FACTOR = EMISSIONS_FACTOR["coal"]

# Iteration Pass 2 — infrastructure age/vulnerability: plants accumulate
# age each round; past a grace period, older fleets become progressively
# more failure-prone unless maintained. A separate lever from build/retire,
# and separate from the emissions-driven disruption system above.
AGE_GRACE_PERIOD = 8
AGE_BREAKDOWN_RATE = 0.03
MAX_AGE_BREAKDOWN_PROBABILITY = 0.6
AGING_BREAKDOWN_COST_FRACTION = 0.6
MAINTENANCE_COST_FRACTION = 0.25
MAINTENANCE_AGE_REDUCTION = 6

# (age threshold, CSS class) pairs, ascending — render() applies the
# highest threshold a plant type's age has crossed, so its icon visibly
# degrades before a breakdown actually happens.
AGE_WEAR_THRESHOLDS = [
    (24, "wear-3"),
    (16, "wear-2"),
    (8, "wear-1"),
]

# C10: the exact wear percentage shown next to the existing wear-icon
# states, on the same scale as the top wear tier -- 100% lines up with
# wear-3, not with MAX_AGE_BREAKDOWN_PROBABILITY's own cap (a different
# scale entirely; conflating the two would make the number lie about
# what "100%" means).
WEAR_PERCENT_REFERENCE_AGE = AGE_WEAR_THRESHOLDS[0][0]

# C26 -- three distinct wear-tier glyphs (plus "fresh"), a shape cue that
# reads independently of the wear-1/2/3 CSS desaturation on the name.
WEAR_TIER_GLYPH = {"": "\u25CB", "wear-1": "\u25D4", "wear-2": "\u25D1", "wear-3": "\u25CF"}

# C13 -- starting scenarios, selectable only before anything has been built
# or any round played. Each is a fixed opening fleet + funds.
SCENARIOS = {
    "standard": {"label": "Standard start", "funds": STARTING_FUNDS, "plants": {}},
    "coal_legacy": {
        "label": "Coal-heavy legacy grid",
        "funds": 300,
        "plants": {"coal": 4, "gas": 1},
    },
    "greenfield": {
        "label": "Greenfield renewable-first",
        "funds": 700,
        "plants": {},
    },
    # C27 -- opt-in emergency-response scenario: the grid starts already
    # short of demand after a major disruption. See GridState.emergency.
    "emergency": {
        "label": "Emergency response",
        "funds": 300,
        "plants": {"coal": 3, "gas": 1},
        "demand": 180,
    },
}
SCENARIOS["electrified"] = {
    "label": "Electrified city",
    "funds": STARTING_FUNDS,
    "plants": {},
    "electrification": True,
}
ELECTRIFICATION_NOTICE_ROUNDS = 3
ELECTRIFICATION_EVENTS = [
    {"round": 6, "title": "Bus fleets go electric", "demand": 12},
    {"round": 12, "title": "Heat pumps replace gas boilers", "demand": 18},
    {"round": 18, "title": "Delivery vans and freight depots go electric", "demand": 20},
    {"round": 24, "title": "Factories switch to electric heat", "demand": 25},
]
SCENARIO_ORDER = ["standard", "coal_legacy", "greenfield", "emergency", "electrified"]

# C27 -- the player has EMERGENCY_ROUNDS rounds to bring capacity up to
# demand and hold it there for EMERGENCY_HOLD_ROUNDS rounds in a row. There
# is no game over (root design rule): missing the window just closes the
# emergency as "not stabilized in time" and the run carries on.
EMERGENCY_ROUNDS = 6
EMERGENCY_HOLD_ROUNDS = 2

# C9 -- storage arbitrage. Batteries hold up to ARBITRAGE_STORAGE_MULTIPLE x
# their own capacity, charge/discharge at their own capacity per round, lose
# (1 - ARBITRAGE_EFFICIENCY) of what they charge, and sell discharged energy
# at a peak-price premium. Modes are chosen by the player each round.
ARBITRAGE_MODES = ("idle", "charge", "discharge")
ARBITRAGE_STORAGE_MULTIPLE = 2
ARBITRAGE_EFFICIENCY = 0.85
ARBITRAGE_PEAK_PRICE_MULTIPLIER = 1.5

# C25 -- how far the "grid of the future" projection looks ahead.
PROJECTION_ROUNDS = 20

# Round-3 pass (2026-09-20) additions below -- see CLAUDE.md's own build
# note for the full rationale on each.

# TODO-C7 -- demand response: a fourth lever alongside build/retire/
# maintain. Each purchase permanently trims this round's demand growth by
# a fixed amount, at an escalating cost (mirrors the renewable learning
# curve's shape but in reverse -- each purchase costs more than the last,
# since a grid gets harder to trim further the more efficient it already
# is). Floored so demand growth can never go negative or stall entirely.
DEMAND_RESPONSE_BASE_COST = 150
DEMAND_RESPONSE_COST_GROWTH = 1.35
DEMAND_RESPONSE_REDUCTION_PER_LEVEL = 1.5
DEMAND_RESPONSE_MIN_GROWTH = 3.0

# TODO-C17 -- weather-event log: a running narration of how Weather
# Variability actually affected renewable output round to round, separate
# from the emissions-driven disruption log. Capped the same way
# event_log/ticker-style logs are capped elsewhere in the quartet, so a
# very long run's save doesn't grow this list unboundedly.
WEATHER_LOG_MAX_ENTRIES = 30
SNAPSHOT_MAX = 100

# TODO-C19 -- policy lever: an occasional opt-in choice that temporarily
# shifts the cost curve, offered every POLICY_LEVER_INTERVAL rounds if no
# policy is currently active. Carbon pricing makes fossil more expensive
# to build; a renewable subsidy makes renewables cheaper to build. Both
# are build-time-only price signals -- see GridState.plant_cost()'s
# comment on why Retire deliberately never refunds off the policy price.
POLICY_LEVER_INTERVAL = 6
POLICY_LEVER_DURATION = 4
CARBON_PRICING_FOSSIL_COST_MULTIPLIER = 1.3
RENEWABLE_SUBSIDY_COST_MULTIPLIER = 0.75

# TODO-C23 -- maintenance scheduling: pre-commit a plant type to an
# auto-maintain cadence instead of manually clicking Maintain every time.
# 0 means "off" (manual only, the pre-existing behavior).
MAINTENANCE_SCHEDULE_OPTIONS = (0, 3, 5, 8)


# C1 -- grid operator career: persistent cross-run meta-progression.
# Finishing a run (Career panel) banks Career Points from how it went, and
# points buy small permanent perks for later runs. Perks are deliberately
# modest conveniences -- none touches emissions, disruption or the learning
# curve, so the "invest early, come out ahead" lesson is not bought away.
CAREER_STORAGE_KEY = "grid_career_v1"
CAREER_MIN_ROUNDS = 5
CAREER_GRADE_POINTS = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
CAREER_RESILIENCE_BONUS_THRESHOLD = 60
# GC-2b / GC-1 / GC-11 -- the career is an upgrade TREE (shared/skill_tree.py, drawn by
# shared/skill-tree.js). Four branches: Operations (the original four perks, now the first
# nodes), Projects (named permanent modifiers you pick on purpose -- the deterministic
# replacement for the declined card draw: nothing is drawn or discarded), Starting loadout
# (pick ONE option per run) and Meteorology (the peek forecast). None of it is random, and
# none of it touches the emissions-to-disruption link or the learning-curve lesson itself,
# except the R&D grant, which speeds the cost curve the lesson is about.
CAREER_BRANCHES = [
    {"id": "operations", "title": "Operations", "blurb": "Everyday conveniences: seed money, cheaper upkeep, better storage."},
    {"id": "projects", "title": "Projects", "blurb": "Named permanent modifiers you buy on purpose. They cheapen builds, speed the cost curve and stretch policy offers."},
    {"id": "loadout", "title": "Starting loadout", "blurb": "Buying a loadout makes it a choice for the start of a run. Pick one at the run setup (Difficulty window on Desktop)."},
    {"id": "meteorology", "title": "Meteorology", "blurb": "Pay a small fee to read next round's weather and disruption roll before you commit a build."},
]
_CAREER_NODES = [
    # (id, branch, cost, label, effect text, description, requires)
    ("seed_capital", "operations", 3, "Seed capital", "+75 funds at the start of every run",
     "Start every new run with 75 extra funds.", []),
    ("crew_training", "operations", 4, "Crew training", "-15% maintenance cost", "Maintenance costs 15% less.", []),
    ("storage_partners", "operations", 5, "Storage partnerships", "battery efficiency 85% -> 92%",
     "Battery round-trip efficiency rises from 85% to 92%.", []),
    ("demand_analytics", "operations", 6, "Demand analytics", "-20% demand response cost",
     "Demand response costs 20% less.", []),
    ("wind_sites", "projects", 3, "Wind site leases", "wind plants cost 15% less to build",
     "Pre-agreed ridge leases: every new wind plant costs 15% less.", []),
    ("solar_sites", "projects", 3, "Solar site leases", "solar plants cost 15% less to build",
     "Pre-agreed rooftop and field leases: every new solar plant costs 15% less.", []),
    ("storage_subsidy", "projects", 4, "Storage subsidy", "batteries cost 20% less to build",
     "A standing subsidy: every new battery costs 20% less.", []),
    ("rd_grant", "projects", 5, "R&D grant", "renewable cost curve 5% -> 6% per unit built",
     "Research funding: each renewable unit you build trims that type's next price by 6% instead of 5%.",
     ["wind_sites", "solar_sites"]),
    ("policy_liaison", "projects", 4, "Policy liaison", "renewable subsidy: 30% off, 2 extra rounds",
     "A regulator contact: when you enact the renewable subsidy it takes 30% off instead of 25% and lasts 2 extra rounds.",
     ["wind_sites"]),
    ("old_coal_contract", "loadout", 2, "Old Coal Contract", "start with 2 coal plants already running",
     "Loadout: start the run with 2 aged coal plants (no cost). Early power, early emissions.", []),
    ("storage_startup", "loadout", 3, "Storage Startup", "start with 1 battery installed",
     "Loadout: start the run with one battery already installed.", []),
    ("diplomatic_immunity", "loadout", 4, "Diplomatic Immunity", "the first disruption of the run is waived",
     "Loadout: the first disruption of the run is called off. A waived round counts as a disruption-free round.", []),
    ("weather_station", "meteorology", 2, "Weather station", "unlocks Peek forecast (20 funds)",
     "Pay 20 funds to read next round's weather roll and whether a disruption will hit, before you build.", []),
    ("long_range_outlook", "meteorology", 4, "Long-range outlook", "peek also shows the round after next",
     "Peek forecast also reports the weather roll for the round after next.", ["weather_station"]),
]
CAREER_UNLOCKS = {
    nid: {"label": label, "cost": cost, "effect": effect, "description": desc, "branch": branch, "requires": list(req)}
    for nid, branch, cost, label, effect, desc, req in _CAREER_NODES
}
CAREER_UNLOCK_ORDER = [row[0] for row in _CAREER_NODES]
CAREER_TREE = {
    "id": "grid_career",
    "title": "Operator upgrade tree",
    "currency": "career points",
    "branches": CAREER_BRANCHES,
    "nodes": [
        {"id": nid, "branch": branch, "cost": cost, "label": label,
         "description": desc, "requires": list(req)}
        for nid, branch, cost, label, effect, desc, req in _CAREER_NODES
    ],
}
LOADOUT_NODES = ("old_coal_contract", "storage_startup", "diplomatic_immunity")
PROJECT_PLANT_DISCOUNT = {"wind_sites": ("wind", 0.85), "solar_sites": ("solar", 0.85), "storage_subsidy": ("battery", 0.8)}
RD_GRANT_DECAY = 0.94
POLICY_LIAISON_EXTRA_ROUNDS = 2
POLICY_LIAISON_SUBSIDY_MULTIPLIER = 0.70
OLD_COAL_CONTRACT_PLANTS = 2
OLD_COAL_CONTRACT_AGE = 4.0
# GC-11: the fee for one peek at the coming round, and how far ahead the long-range outlook looks.
PEEK_FEE = 20
SEED_CAPITAL_BONUS = 75

# C-1 / GC-26 -- run history and personal records. The history keeps the last
# CAREER_HISTORY_MAX finished runs, each with its series thinned to at most
# CAREER_SERIES_POINTS points so a save code stays small; lifetime totals are
# kept separately (they are not capped). RECORD_CLEAN_SHARE is the "90% clean"
# line behind the fewest-rounds-to-90%-clean record.
CAREER_HISTORY_MAX = 12
CAREER_SERIES_POINTS = 30
CAREER_CHART_RUNS = 6
RECORD_CLEAN_SHARE = 0.9
CREW_TRAINING_MAINTENANCE_MULTIPLIER = 0.85
STORAGE_PARTNERS_EFFICIENCY = 0.92
DEMAND_ANALYTICS_COST_MULTIPLIER = 0.8


# Seeded runs (the Z-1 helper in shared/seed.py, reused read-only). Grid used to
# draw from random.random(), so a run could not be replayed. Now every run has a
# short seed such as GRID-K7F2Q and every random draw of a round comes from its
# own STATELESS stream derived from (seed, purpose, round number), so the same
# seed and the same choices give the same weather, disruptions and breakdowns
# in Python, in a replay, in the what-if analyzer and in a peek at the forecast.
SEED_GAME = "grid"


def new_run_seed():
    """A fresh seed (not secrets: Python's random, so the test harness can fix it)."""
    return seed_lib.new_seed(SEED_GAME, entropy=lambda n: random.randrange(n))


# GC-15 -- Perfect Round combo: consecutive rounds with no disruption, no aging breakdown and
# demand fully met build a revenue bonus on the round's base revenue.
PERFECT_ROUND_STEP = 0.05
PERFECT_ROUND_MAX_STEPS = 6

# GC-25 -- surprise grants: now and then a two-button offer appears. Rolled from the run's own
# seeded stream, so the same seed offers the same grants in the same rounds.
GRANT_ODDS = 0.15
GRANT_MIN_ROUND = 3
GRANTS = {
    "clean_grant": {
        "title": "Clean-energy grant",
        "text": "A regional fund offers 120 funds. The strings: fossil plants cost 25% more to build for the next 3 rounds.",
        "accept": "Accept the grant", "decline": "Decline",
    },
    "sponsor_deal": {
        "title": "Industrial sponsor",
        "text": "A manufacturer will pay 90 funds up front for a guaranteed supply deal. The strings: demand rises by 6 right away.",
        "accept": "Take the deal", "decline": "Decline",
    },
    "inspection_fine": {
        "title": "Safety inspection",
        "text": "Inspectors found wear problems. Pay a 70-fund fine and repair them (every fleet's wear drops by 3), or contest it for free and risk it: aging breakdown chance doubles for 2 rounds.",
        "accept": "Pay the fine and repair", "decline": "Contest it",
    },
}
GRANT_ORDER = ("clean_grant", "sponsor_deal", "inspection_fine")
GRANT_CLEAN_FUNDS = 120
GRANT_CLEAN_SURCHARGE = 1.25
GRANT_CLEAN_ROUNDS = 3
GRANT_SPONSOR_FUNDS = 90
GRANT_SPONSOR_DEMAND = 6
GRANT_FINE = 70
GRANT_REPAIR_AGE = 3.0
GRANT_CONTEST_ROUNDS = 2

BOSS_ROUND_INTERVAL = 8
BOSS_REWARD_FUNDS = 150

BOSS_ROUNDS = [
    {"id": "heatwave", "name": "Heatwave", "demand_pct": 20, "hydro_penalty_pct": 0, "preview": "Air conditioners everywhere push demand up 20% for one round."},
    {"id": "polar_vortex", "name": "Polar Vortex", "demand_pct": 25, "hydro_penalty_pct": 0, "preview": "A deep freeze pushes demand up 25% for one round."},
    {"id": "dry_summer", "name": "Dry Summer", "demand_pct": 0, "hydro_penalty_pct": 50, "preview": "Low rivers cut Hydro output by half for one round."},
]


def boss_for_round(round_number):
    if round_number < BOSS_ROUND_INTERVAL or round_number % BOSS_ROUND_INTERVAL != 0:
        return None
    return BOSS_ROUNDS[(round_number // BOSS_ROUND_INTERVAL - 1) % len(BOSS_ROUNDS)]


# GC-4 -- plant nicknames, drawn from the run's seed (reproducible), and a eulogy when the last
# coal plant is retired.
PLANT_NAME_POOL = {
    "coal": ["Old Smoky", "Black Betty", "Sooty Pete", "Grandpa Grit", "Cinder", "Big Charcoal", "Dusty", "Ol' Faithful"],
    "gas": ["Blue Flame", "Pilot Light", "Puff", "Steady Eddie", "Torchy", "Hot Stuff", "Gassy Gus", "Ember"],
    "nuclear": ["Atom Ant", "Big Glow", "Reactor Rita", "Fission Chips", "Quiet Giant", "Mr. Core", "Half-Life", "Neutron Nell"],
    "solar": ["Sunny Delight", "Sol Mate", "Bright Idea", "Panel Pal", "Dawn Patrol", "Lumen", "Sunbeam", "Photon Fiona"],
    "wind": ["Breezy", "Gust Buster", "Whirl", "Windy Pete", "Big Fan", "Zephyr", "Sky Spinner", "Gale"],
    "hydro": ["River Run", "Dam Good", "Splash", "Old Faithful Falls", "Flow", "Deep Blue", "Cascade", "Mighty Wet"],
    "battery": ["Juice Box", "Top-Up", "Reserve Rob", "Charge Charlie", "Stash", "Big Bank", "Spark Jar", "Cell Mate"],
}
COAL_EULOGIES = [
    "Farewell, {name}. You kept the lights on, and the sky a little greyer. Rest easy.",
    "{name} has gone quiet. The last coal plant on the grid is switched off.",
    "Goodnight, {name}. Thank you for the long shifts.",
]
NAME_MAX_LEN = 24


def _breakdown_probability_for_age(age):
    """Shared by GridState.aging_breakdown_probability() (the single
    oldest standing plant type, which is the only one actually at risk of
    breaking down a given round) and breakdown_risk_probability() below
    (C19's per-type risk badge, informational for every standing type
    past the grace period, not just the current oldest)."""
    if age <= AGE_GRACE_PERIOD:
        return 0.0
    return min(MAX_AGE_BREAKDOWN_PROBABILITY, (age - AGE_GRACE_PERIOD) * AGE_BREAKDOWN_RATE)


# C5 -- ascending (max emissions/benchmark ratio, letter). Above the last
# limit is an "F".
GRADE_THRESHOLDS = [(0.2, "A"), (0.5, "B"), (0.8, "C"), (1.0, "D")]


# ---- Display preferences (C-12, C-19, C-6, C-21, GC-19, GC-8, GC-9) ----------------------------------------------
# What the player chooses to SEE (which trend lines, tables instead of graphs, number format, the coach, the
# commentary, the skyline). Like the text-size and reduced-motion settings these are a browser preference kept in
# localStorage under their own key; they are never part of get_state(), so a save code stays portable and loading a
# save can never change how the page looks. Nothing here touches the rules.
PREFS_STORAGE_KEY = "grid_prefs_v1"
PREF_DEFAULTS = {
    "trend_emissions": True,
    "trend_cost": True,
    "trend_benchmark": True,
    "trend_funds": False,
    "trend_demand": False,
    "trend_clean": False,
    "trend_ghost": False,
    "table_view": False,
    "number_format": "full",
    "unit": "units",
    "coach": False,
    "gridley": True,
    "skyline": True,
    "gauge_effects": True,
    "rank_theme": "default",
    "chart_theme": "default",
    "unlock_flash": True,
    "round_animation": True,
}
RANK_THEMES = ("default", "teal", "amber", "violet", "rose", "gold")
# C-28: how the trend graph and the plant-mix bars are coloured. "contrast" uses brighter, thicker lines and bars;
# "pattern" drops colour for greys and tells every line and bar apart by its dash or fill pattern.
CHART_THEMES = ("default", "contrast", "pattern")
PREF_CHOICES = {
    "number_format": ("full", "compact"),
    "unit": ("units", "mw"),
    "rank_theme": RANK_THEMES,
    "chart_theme": CHART_THEMES,
}


def _build_incident_files():
    files = {}
    for p in ("coal", "gas"):
        label = PLANT_LABEL[p]
        files[f"brownout_{p}"] = {
            "title": f"Brownout: {label} strain",
            "cause": f"{label} was your biggest source of emissions, and accumulated emissions raise the chance and severity of a disruption.",
            "stops": "Retire fossil plants and build clean capacity: fewer emissions lower both the chance and the severity."
        }
    files["brownout_lingering"] = {
        "title": "Brownout: lingering emissions",
        "cause": "No fossil plant was left standing, but emissions from earlier rounds still raised the disruption chance.",
        "stops": "Keep building clean plants: emissions only fall as capacity gets cleaner."
    }
    for p in ("coal", "gas"):
        label = PLANT_LABEL[p]
        files[f"damage_{p}"] = {
            "title": f"Damage: {label} plant lost",
            "cause": "Disruption severity passed the 50% damage line, so your largest fossil fleet lost a unit.",
            "stops": "Keep accumulated emissions low enough that severity stays under 50%."
        }
    for t in PLANT_TYPES:
        label = PLANT_LABEL[t]
        files[f"aging_{t}"] = {
            "title": f"Aging breakdown: {label}",
            "cause": "The fleet average age passed the 8-round grace period and a worn unit broke down.",
            "stops": "Maintain the fleet (takes 6 rounds off its age) or set an auto-maintenance schedule."
        }
    return files


INCIDENT_FILES = _build_incident_files()


def incident_ids(event, aging_event):
    """Return a list of incident file IDs for the given event and aging breakdown."""
    ids = []
    if event is not None:
        if event["type"] == "brownout":
            ids.append("brownout_" + (event.get("cause_plant") or "lingering"))
        elif event["type"] == "damage":
            ids.append("damage_" + event["damaged_plant"])
    if aging_event is not None:
        ids.append("aging_" + aging_event["plant"])
    return ids
