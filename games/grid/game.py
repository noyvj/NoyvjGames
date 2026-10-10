"""Grid — Energy Transition Game.

Runs in-browser via Pyodide. Turn-based loop across demand growth, funds,
six plant types to build/retire/maintain, capacity-based revenue on round
advance, an emissions meter and renewable cost curve, and emissions-driven
disruption events plus infrastructure aging — see CLAUDE.md's milestone
table for how each system landed.
"""

import copy
import json
import random

import comparison_chart
import info_page
import seed as seed_lib
import skill_tree
from js import document, setTimeout
from pyodide.ffi import create_proxy

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
SCENARIO_ORDER = ["standard", "coal_legacy", "greenfield", "emergency"]

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


class GridState:
    def __init__(self):
        self.round_number = 1
        self.demand = STARTING_DEMAND
        self.funds = STARTING_FUNDS
        self.plant_counts = {t: 0 for t in PLANT_TYPES}
        self.cumulative_built = {t: 0 for t in PLANT_TYPES}
        self.emissions = 0.0
        self.event_log = []
        self.last_event = None
        self.clean_fraction_log = []
        self.emissions_history = []
        self.avg_renewable_cost_history = []
        self.renewable_unlocked = False
        self.plant_age = {t: 0.0 for t in PLANT_TYPES}
        self.global_reference_emissions = 0.0
        self.global_reference_emissions_history = []
        # C17 -- cumulative emissions for the business-as-usual
        # counterfactual: what this exact same installed capacity would
        # have emitted had it all been built as coal. Evolves
        # independently each round in advance_round(), the same "shadow
        # trajectory" pattern as global_reference_emissions above -- never
        # recomputed from history, so it survives save/load exactly like
        # every other running total.
        self.bau_emissions = 0.0
        self.last_aging_event = None
        # New tracked state for the achievements framework (see the
        # "Achievements" section below) -- nothing else in this module
        # records how many times Maintain has actually been used, or how
        # long a streak of disruption-free rounds has run, so these three
        # need genuine new tracked fields rather than being derivable from
        # what's already here. Each is mutated only at the real event it
        # measures (a successful maintain_plant() call; a round advancing
        # with or without a disruption event), never hand-set elsewhere.
        self.maintenance_actions_count = 0
        self.current_clean_streak = 0
        self.best_clean_streak = 0
        # C20 -- one-time first-use callouts for Retire's refund math and
        # Maintain's cost math, so the explanation isn't left only inside
        # the small "i" tooltip. Persisted so a returning player who's
        # already seen it doesn't get it again after a save/load.
        self.seen_retire_callout = False
        self.seen_maintain_callout = False
        # C8 -- one-time callout the first time cumulative renewable
        # capacity crosses 50% of the grid's total. Persisted so it
        # doesn't re-trigger every session once already reached.
        self.renewable_50_reached = False
        # C13 -- lifetime running totals per spend/income category, for
        # the funds-breakdown display. Mutated only where funds already
        # change for that reason -- no new call sites invented, and
        # nothing here changes what any of those existing debits/credits
        # actually are (see build_plant()/retire_plant()'s own comments
        # on the flat-refund exploit this game already audited and fixed
        # once -- this is pure additive bookkeeping alongside that math,
        # not a second implementation of it).
        self.lifetime_revenue = 0.0
        self.lifetime_build_spend = 0.0
        self.lifetime_maintenance_spend = 0.0
        self.lifetime_disruption_spend = 0.0
        # C16 -- opt-in "steeper demand growth" difficulty variant, off by
        # default. Persisted so it stays set across a save/load.
        self.steeper_demand_growth_enabled = False
        # C4 -- opt-in weather-variability hard mode, off by default.
        self.weather_variability_enabled = False
        # C3 -- optional interconnected regional grid, a lighter multi-grid
        # mode than a fully independent second grid to manage (same "shares
        # a resource with its own separate exposure" shape as Tide's D3
        # sister settlement). One-way once connected, like that toggle.
        self.regional_grid_connected = False
        self.regional_grid_total_shared = 0.0
        self.regional_grid_total_shortfall_cost = 0.0
        self.regional_grid_total_revenue = 0.0
        # C13 -- which starting scenario was applied (see SCENARIOS).
        self.scenario = "standard"
        # TODO-C7 -- demand-response investment level (see constants above).
        self.demand_response_level = 0
        # TODO-C17 -- weather-event log entries, newest last (rendered
        # newest-first). Also two scratch fields effective_capacity_for_
        # revenue() fills in each call so advance_round() can narrate what
        # actually happened without re-consuming weather_rng a second time.
        self.weather_log = []
        self.last_weather_renewable_nameplate = 0.0
        self.last_weather_renewable_actual = 0.0
        # TODO-C19 -- policy lever: offered periodically, opt-in, one at a
        # time (see constants above).
        self.policy_lever_available = False
        self.active_policy = None
        self.last_policy_lever_round_offered = 0
        # TODO-C23 -- per-plant-type auto-maintain cadence, 0 = manual only.
        self.maintenance_schedule = {t: 0 for t in PLANT_TYPES}
        # C9 -- storage arbitrage: stored energy units, the player's chosen
        # mode for the next round, and the last round's result for display.
        self.stored_energy = 0.0
        self.arbitrage_mode = "idle"
        self.last_arbitrage = None
        self.arbitrage_revenue_total = 0.0
        # C27 -- None outside the emergency scenario, else a dict
        # {"status": "active"|"stabilized"|"missed", "rounds_left", "hold"}.
        self.emergency = None
        # C1 -- permanent career perks in force for this run (ids from
        # CAREER_UNLOCKS); assigned by _sync_perks(), never saved per-run.
        self.perks = set()
        # C-1 -- per-round funds and demand series (alongside the existing
        # clean-share/emissions histories) so a finished run can be filed in
        # the career's run history; GC-26 -- aging breakdown count and the
        # first round the grid reached 90% clean capacity; C-8 -- a
        # structured breakdown of the last round, for the round recap line.
        self.funds_history = []
        self.demand_history = []
        self.aging_breakdown_count = 0
        self.first_90_clean_round = None
        self.last_round_recap = None
        # Seeded run (see SEED_GAME): the run's seed, the chosen starting loadout (GC-2b), whether
        # Diplomatic Immunity is still unspent, the round of the last paid peek (GC-11).
        self.seed = new_run_seed()
        self.start_option = None
        self.immunity_available = False
        self.immunity_used = False
        self.peeked_round = 0
        # GC-15 Perfect Round combo.
        self.perfect_streak = 0
        self.best_perfect_streak = 0
        # GC-21 undo last build (same round) and the opt-in Ironman toggle.
        self.undo_record = None
        self.ironman = False
        # GC-4 nicknames: standing units' names per type, and how many names were ever drawn.
        self.plant_names = {t: [] for t in PLANT_TYPES}
        self.name_serial = {t: 0 for t in PLANT_TYPES}
        self.last_eulogy = None
        # GC-25 surprise grants: the open offer (or None), strings still running, count taken.
        self.grant_offer = None
        self.grant_effects = {"fossil_surcharge": 0, "breakdown_risk": 0}
        self.last_grant_message = ""

    # ---- seeded streams (the Z-1 helper) -------------------------------------------------
    def stream(self, label, round_number=None):
        """A fresh stateless generator for one purpose in one round: it depends only on the run's
        seed, the label and the round number, never on how many draws happened before."""
        n = self.round_number if round_number is None else round_number
        return seed_lib.Rng(f"{self.seed}#{label}#{n}")

    def set_seed(self, text):
        """Use a typed seed for this run. Only before anything is built or advanced."""
        if self.round_number != 1 or any(self.cumulative_built.values()):
            return False
        result = seed_lib.validate(text, SEED_GAME)
        if not result["ok"]:
            return False
        self.seed = result["seed"]
        self.plant_names = {t: [] for t in PLANT_TYPES}
        self.name_serial = {t: 0 for t in PLANT_TYPES}
        return True

    def unstarted(self):
        """True while nothing has been built or advanced (setup choices are still allowed)."""
        return self.round_number == 1 and not any(self.cumulative_built.values()) and self.demand_response_level == 0

    def arbitrage_efficiency(self):
        return STORAGE_PARTNERS_EFFICIENCY if "storage_partners" in self.perks else ARBITRAGE_EFFICIENCY

    def storage_cap(self):
        """C9: max stored energy the battery fleet can hold."""
        return self.battery_capacity() * ARBITRAGE_STORAGE_MULTIPLE

    def set_arbitrage_mode(self, mode):
        if mode not in ARBITRAGE_MODES:
            return False
        self.arbitrage_mode = mode
        return True

    def _run_arbitrage(self, effective_capacity):
        """C9: called from advance_round() with this round's effective
        generation. Charging banks surplus (generation above demand, which
        earns nothing otherwise) at ARBITRAGE_EFFICIENCY; discharging sells
        stored energy into a shortfall at a peak-price premium. Returns the
        extra revenue. Never touches emissions/disruption math."""
        # A retired battery shrinks the cap; anything above it is lost.
        self.stored_energy = min(self.stored_energy, self.storage_cap())
        rate = self.battery_capacity()
        self.last_arbitrage = None
        if rate <= 0 or self.arbitrage_mode == "idle":
            return 0.0
        if self.arbitrage_mode == "charge":
            surplus = max(0.0, effective_capacity - self.demand)
            taken = min(surplus, rate, (self.storage_cap() - self.stored_energy) / self.arbitrage_efficiency())
            self.stored_energy += taken * self.arbitrage_efficiency()
            self.last_arbitrage = {"mode": "charge", "units": taken, "revenue": 0.0}
            return 0.0
        shortfall = max(0.0, self.demand - effective_capacity)
        sold = min(shortfall, rate, self.stored_energy)
        revenue = sold * REVENUE_PER_UNIT_MET * ARBITRAGE_PEAK_PRICE_MULTIPLIER
        self.stored_energy -= sold
        self.arbitrage_revenue_total += revenue
        self.last_arbitrage = {"mode": "discharge", "units": sold, "revenue": revenue}
        return revenue

    def connect_regional_grid(self):
        """C3: one-way, like Tide's D3 sister-settlement switch -- its
        history becomes part of this run, so it can't be turned back off."""
        self.regional_grid_connected = True

    def _advance_regional_grid(self, available_surplus):
        """C3: called from advance_round() with whatever main-grid surplus
        capacity this round's arbitrage charging didn't already claim. A
        lighter multi-grid mode: the regional grid has no plants of its own
        to build or retire, just its own demand (a fixed fraction of this
        grid's, so it grows on its own). Surplus capacity you already own
        serves it for a little revenue; whatever it still needs falls back
        to buying power in for it, at shared funds' expense. Never touches
        this grid's own emissions/disruption math."""
        regional_demand = self.demand * REGIONAL_DEMAND_FRACTION
        shared = min(available_surplus, regional_demand)
        shortfall = regional_demand - shared
        revenue = shared * REGIONAL_REVENUE_PER_UNIT_SHARED
        shortfall_cost = shortfall * REGIONAL_SHORTFALL_COST_PER_UNIT
        self.funds = max(0.0, self.funds - shortfall_cost)
        self.regional_grid_total_shared += shared
        self.regional_grid_total_shortfall_cost += shortfall_cost
        self.regional_grid_total_revenue += revenue
        return revenue

    def regional_grid_readout_text(self):
        if not self.regional_grid_connected:
            return ""
        net = self.regional_grid_total_revenue - self.regional_grid_total_shortfall_cost
        sign = "+" if net >= 0 else "-"
        return (
            f"Regional grid: {self.regional_grid_total_shared:.0f} units of spare capacity "
            f"shared so far, net {sign}{abs(net):.0f} funds effect."
        )

    def _update_emergency(self):
        """C27: called at the end of advance_round() (demand already grown)."""
        em = self.emergency
        if em is None or em["status"] != "active":
            return
        em["rounds_left"] -= 1
        if self.total_capacity() >= self.demand:
            em["hold"] += 1
        else:
            em["hold"] = 0
        if em["hold"] >= EMERGENCY_HOLD_ROUNDS:
            em["status"] = "stabilized"
        elif em["rounds_left"] <= 0:
            em["status"] = "missed"

    def apply_scenario(self, scenario_id):
        """C13: only allowed before anything has been built/advanced, so a
        scenario can never be used to reset progress mid-run."""
        if scenario_id not in SCENARIOS:
            return False
        if self.round_number != 1 or any(self.cumulative_built.values()):
            return False
        scenario = SCENARIOS[scenario_id]
        self.plant_counts = {t: 0 for t in PLANT_TYPES}
        self.plant_age = {t: 0.0 for t in PLANT_TYPES}
        self.plant_names = {t: [] for t in PLANT_TYPES}
        self.name_serial = {t: 0 for t in PLANT_TYPES}
        for plant_type, count in scenario["plants"].items():
            self.plant_counts[plant_type] = count
        self.funds = scenario["funds"] + (SEED_CAPITAL_BONUS if "seed_capital" in self.perks else 0)
        self.demand = scenario.get("demand", STARTING_DEMAND)
        self.emergency = (
            {"status": "active", "rounds_left": EMERGENCY_ROUNDS, "hold": 0}
            if scenario_id == "emergency"
            else None
        )
        self.scenario = scenario_id
        self._apply_start_option()
        return True

    def _apply_start_option(self):
        """GC-2b: the starting loadout chosen for this run, applied on top of the scenario's
        opening fleet. Only ever called from apply_scenario(), so it can only happen before the
        first build or round."""
        option = self.start_option if self.start_option in self.perks else None
        self.immunity_available = option == "diplomatic_immunity"
        if option == "old_coal_contract":
            old = self.plant_counts["coal"]
            self.plant_counts["coal"] = old + OLD_COAL_CONTRACT_PLANTS
            self.plant_age["coal"] = OLD_COAL_CONTRACT_AGE * OLD_COAL_CONTRACT_PLANTS / (old + OLD_COAL_CONTRACT_PLANTS)
        elif option == "storage_startup":
            self.plant_counts["battery"] += 1

    def set_start_option(self, option):
        """GC-2b: choose (or clear, with None) this run's starting loadout. Needs the loadout
        bought in the upgrade tree, and a run that has not started."""
        if option is not None and (option not in LOADOUT_NODES or option not in self.perks):
            return False
        if not self.unstarted():
            return False
        self.start_option = option
        self.apply_scenario(self.scenario)
        return True

    def set_ironman(self, flag):
        """GC-21: Ironman can only be switched at the start of a run; once play begins it is fixed."""
        if not self.unstarted():
            return False
        self.ironman = bool(flag)
        if self.ironman:
            self.undo_record = None
        return True

    def _learning_curve_cost(self, plant_type):
        """The plant's cost before any temporary TODO-C19 policy-lever
        adjustment -- base cost adjusted only by the renewable learning
        curve. retire_plant() refunds off *this*, never off plant_cost()'s
        policy-adjusted price: a policy multiplier is a build-time-only
        price signal, not a permanent value change, and basing a refund on
        it would open an exploit in one direction (build cheap during a
        renewable subsidy, retire later for a refund based on the same
        discounted price is fine and symmetric -- but the concern is
        whether *any* combination nets a profit). It never can: the
        refund fraction is a flat 50%, and neither the subsidy (25% off)
        nor stacking it with the learning-curve floor discount pushes the
        price a player actually paid below double what a 50%-of-base-cost
        refund would return, so there's no direction where this pays out
        more than it cost -- same reasoning already documented on
        REFUND_FRACTION's fix elsewhere in this file, just re-verified
        against this new temporary-price case."""
        base = PLANT_BASE_COST[plant_type]
        if plant_type not in RENEWABLE_TYPES:
            return base
        decay = RD_GRANT_DECAY if "rd_grant" in self.perks else RENEWABLE_COST_DECAY
        multiplier = max(MIN_COST_MULTIPLIER, decay ** self.cumulative_built[plant_type])
        return base * multiplier

    def plant_cost(self, plant_type):
        """The actual price to build this plant type right now, including
        any active TODO-C19 policy-lever adjustment. Use
        _learning_curve_cost() instead when computing a Retire refund --
        see that method's docstring."""
        cost = self._learning_curve_cost(plant_type)
        if self.active_policy is not None:
            policy_type = self.active_policy["type"]
            if policy_type == "carbon_pricing" and plant_type in FOSSIL_TYPES:
                cost *= CARBON_PRICING_FOSSIL_COST_MULTIPLIER
            elif policy_type == "renewable_subsidy" and plant_type in RENEWABLE_TYPES:
                cost *= (
                    POLICY_LIAISON_SUBSIDY_MULTIPLIER if "policy_liaison" in self.perks
                    else RENEWABLE_SUBSIDY_COST_MULTIPLIER
                )
        # GC-1: permanent Projects from the upgrade tree (build-time price signals, like policies,
        # so they never feed a retire refund).
        for project, (target, factor) in PROJECT_PLANT_DISCOUNT.items():
            if project in self.perks and target == plant_type:
                cost *= factor
        # GC-25: the strings of an accepted clean-energy grant.
        if self.grant_effects["fossil_surcharge"] > 0 and plant_type in FOSSIL_TYPES:
            cost *= GRANT_CLEAN_SURCHARGE
        return cost

    def total_capacity(self):
        # Generation only -- battery is storage, not generation (see
        # GENERATION_TYPES' comment above PLANT_TYPES).
        return sum(self.plant_counts[t] * PLANT_CAPACITY[t] for t in GENERATION_TYPES)

    def battery_capacity(self):
        """C2: total storage-buffer capacity, in the same units as
        PLANT_CAPACITY -- used only by effective_capacity_for_revenue()'s
        weather-variability compensation, never counted as generation."""
        return self.plant_counts["battery"] * PLANT_CAPACITY["battery"]

    def fossil_capacity(self):
        return sum(self.plant_counts[t] * PLANT_CAPACITY[t] for t in ("coal", "gas"))

    def fossil_share(self):
        total = self.total_capacity()
        if total == 0:
            return 0.0
        return self.fossil_capacity() / total

    def capacity_share(self, plant_type):
        """C7: this type's share of total standing capacity, 0..1 -- the
        per-type generalization of fossil_share()/renewable_capacity_share(),
        for the plant-mix bar chart."""
        total = self.total_capacity()
        if total == 0:
            return 0.0
        return (self.plant_counts[plant_type] * PLANT_CAPACITY[plant_type]) / total

    def emissions_this_round(self):
        return sum(
            self.plant_counts[t] * PLANT_CAPACITY[t] * EMISSIONS_FACTOR[t]
            for t in PLANT_TYPES
        )

    def disruption_probability(self):
        return min(MAX_DISRUPTION_PROBABILITY, self.emissions / DISRUPTION_PROBABILITY_SCALE)

    def disruption_severity(self):
        """0..1 — how bad a disruption event is, if one occurs this round."""
        return min(1.0, self.emissions / DISRUPTION_SEVERITY_SCALE)

    def _fossil_plant_to_damage(self):
        """Picks a standing fossil plant type to damage, biased toward
        whichever fossil type has the most units standing. None if the
        grid has no fossil plants left to damage."""
        candidates = [t for t in FOSSIL_TYPES if self.plant_counts[t] > 0]
        if not candidates:
            return None
        return max(candidates, key=lambda t: self.plant_counts[t])

    def average_renewable_cost(self):
        """Average current cost across the three renewable types — falls
        as cumulative renewable investment grows, thanks to the cost
        curve. Tracked over time as one half of the iteration-pass trend
        graph, so the "investing early makes things cheaper" lesson is
        visible as a line, not just felt in individual build costs."""
        return sum(self.plant_cost(t) for t in RENEWABLE_TYPES) / len(RENEWABLE_TYPES)

    def build_plant(self, plant_type):
        cost = self.plant_cost(plant_type)
        if self.funds < cost:
            return False
        self.plant_name_list(plant_type)  # name the units already standing before the new one
        previous = {
            "round": self.round_number,
            "plant": plant_type,
            "cost": cost,
            "age": self.plant_age[plant_type],
            "unlocked": self.renewable_unlocked,
        }
        self.funds -= cost
        self.lifetime_build_spend += cost
        old_count = self.plant_counts[plant_type]
        # A freshly built unit has age 0, so it dilutes the type's average
        # fleet age proportionally rather than the average staying put.
        self.plant_age[plant_type] = self.plant_age[plant_type] * old_count / (old_count + 1)
        self.plant_counts[plant_type] += 1
        self.cumulative_built[plant_type] += 1
        if plant_type in RENEWABLE_TYPES:
            self.renewable_unlocked = True
        self.plant_name_list(plant_type)
        # GC-21: remember this build so it can be taken back free this round (not in Ironman).
        self.undo_record = None if self.ironman else previous
        return True

    # ---- GC-21 undo last build ---------------------------------------------------------
    def can_undo_build(self):
        record = self.undo_record
        return (
            not self.ironman
            and record is not None
            and record["round"] == self.round_number
            and self.plant_counts[record["plant"]] > 0
        )

    def undo_last_build(self):
        """Take back the most recent build, free, as long as it is still the last thing done this
        round (any retire, maintenance, demand response or round advance closes the window)."""
        if not self.can_undo_build():
            return False
        record = self.undo_record
        plant_type = record["plant"]
        self.plant_names[plant_type] = self.plant_name_list(plant_type)[:-1]
        self.funds += record["cost"]
        self.lifetime_build_spend -= record["cost"]
        self.plant_counts[plant_type] -= 1
        self.cumulative_built[plant_type] -= 1
        self.plant_age[plant_type] = record["age"]
        self.renewable_unlocked = record["unlocked"]
        self.undo_record = None
        return True

    # ---- GC-4 nicknames ----------------------------------------------------------------
    def _new_plant_name(self, plant_type):
        serial = self.name_serial[plant_type]
        self.name_serial[plant_type] = serial + 1
        pool = PLANT_NAME_POOL[plant_type]
        rng = seed_lib.Rng(f"{self.seed}#name#{plant_type}#{serial}")
        name = rng.choice(pool)
        taken = set(self.plant_names[plant_type])
        suffix = 1
        candidate = name
        while candidate in taken:
            suffix += 1
            candidate = f"{name} {'I' * suffix if suffix <= 3 else suffix}"
        return candidate[:NAME_MAX_LEN]

    def plant_name_list(self, plant_type):
        """The nicknames of this type's standing units, oldest first. Kept in step with the count
        on every call: missing names are drawn from the run's seed, extras (lost to damage or an
        aging breakdown) are dropped from the newest end."""
        names = self.plant_names[plant_type]
        count = self.plant_counts[plant_type]
        while len(names) < count:
            names.append(self._new_plant_name(plant_type))
        del names[count:]
        return names

    def retire_plant(self, plant_type):
        if self.plant_counts[plant_type] <= 0:
            return False
        names = self.plant_name_list(plant_type)
        retired_name = names[-1] if names else None
        self.undo_record = None
        self.plant_counts[plant_type] -= 1
        self.plant_name_list(plant_type)
        if plant_type == "coal" and self.plant_counts["coal"] == 0 and retired_name:
            line = self.stream("eulogy").choice(COAL_EULOGIES)
            self.last_eulogy = {"round": self.round_number, "text": line.format(name=retired_name)}
        # Refund off the plant's *current* (possibly learning-curve-discounted)
        # cost, not its flat base cost — once a renewable's discount passes
        # 50% off base, a flat base-cost refund would pay out more than the
        # plant just cost to build, turning build+retire into a risk-free
        # money exploit. plant_cost() already equals the base cost for
        # non-renewables, so this changes nothing for fossil/nuclear.
        self.funds += self._learning_curve_cost(plant_type) * REFUND_FRACTION
        return True

    def maintenance_cost(self, plant_type):
        cost = PLANT_BASE_COST[plant_type] * MAINTENANCE_COST_FRACTION
        if "crew_training" in self.perks:
            cost *= CREW_TRAINING_MAINTENANCE_MULTIPLIER
        return cost

    def maintain_plant(self, plant_type):
        """Spends funds to refurbish a plant type's fleet, knocking its
        average age down rather than resetting it to zero — maintenance
        extends a fleet's life, it doesn't make it new again."""
        if self.plant_counts[plant_type] <= 0:
            return False
        cost = self.maintenance_cost(plant_type)
        if self.funds < cost:
            return False
        self.undo_record = None
        self.funds -= cost
        self.lifetime_maintenance_spend += cost
        self.plant_age[plant_type] = max(0.0, self.plant_age[plant_type] - MAINTENANCE_AGE_REDUCTION)
        self.maintenance_actions_count += 1
        return True

    def oldest_vulnerable_plant(self):
        """The standing plant type with the highest average age — the one
        at risk of an aging breakdown this round, if any exist at all."""
        candidates = [t for t in PLANT_TYPES if self.plant_counts[t] > 0]
        if not candidates:
            return None
        return max(candidates, key=lambda t: self.plant_age[t])

    def aging_breakdown_probability(self):
        oldest = self.oldest_vulnerable_plant()
        if oldest is None:
            return 0.0
        probability = _breakdown_probability_for_age(self.plant_age[oldest])
        if self.grant_effects["breakdown_risk"] > 0:
            probability = min(MAX_AGE_BREAKDOWN_PROBABILITY, probability * 2)
        return probability

    def breakdown_risk_probability(self, plant_type):
        """C19: this specific type's own risk of an aging breakdown, past
        the grace period -- unlike aging_breakdown_probability() above,
        this isn't gated on being the single oldest standing type. Only
        the oldest ever actually breaks down in a given round (see
        advance_round()), but the badge this drives is informational: it
        flags every type that HAS crossed the risk threshold, so a player
        watching a second-oldest fleet age up sees the warning coming
        before it becomes "the" oldest and its risk becomes live."""
        return _breakdown_probability_for_age(self.plant_age[plant_type])

    def wear_class(self, plant_type):
        age = self.plant_age[plant_type]
        for threshold, css_class in AGE_WEAR_THRESHOLDS:
            if age >= threshold:
                return css_class
        return ""

    def wear_percent(self, plant_type):
        """C10: the exact aging/wear percentage, shown as a number next to
        the existing wear-icon states rather than leaving wear legible
        only as a coarse three-step visual. Capped at 100 -- past the
        top wear tier, "more than fully worn" isn't a meaningful distinct
        reading, it's still just wear-3."""
        return min(100, round(self.plant_age[plant_type] / WEAR_PERCENT_REFERENCE_AGE * 100))

    def effective_capacity_for_revenue(self, weather_rng=None):
        """C4: this round's actual output for revenue purposes -- equal to
        total_capacity() unless weather_variability_enabled, in which case
        each renewable type's contribution is scaled by an independent
        random factor in [1 - WEATHER_VARIANCE_FRACTION, 1 +
        WEATHER_VARIANCE_FRACTION] (fossil/nuclear are dispatchable and
        unaffected). Never mutates total_capacity()'s own inputs -- this is
        purely how much of the installed fleet actually generated this
        round, not a change to what's installed.

        C2: battery buffer capacity compensates for a *shortfall* below
        renewables' combined nameplate (a bad-weather round), up to the
        battery fleet's own capacity -- this is the one place battery
        capacity ever contributes to revenue, and only when there's
        something to buffer against. It never adds capacity beyond
        covering that shortfall (no free generation), and never touches
        the emissions-driven disruption/brownout math at all (see
        PLANT_TYPES' comment on why that's a deliberately separate axis).
        """
        if weather_rng is None:
            weather_rng = self.stream("weather").random
        if not self.weather_variability_enabled:
            # TODO-C17: no weather effect this call -- reset the scratch
            # fields so advance_round() never narrates a stale reading
            # from a round where the toggle was on.
            self.last_weather_renewable_nameplate = 0.0
            self.last_weather_renewable_actual = 0.0
            return self.total_capacity()

        dispatchable_total = 0.0
        renewable_nameplate = 0.0
        renewable_actual = 0.0
        for plant_type in GENERATION_TYPES:
            capacity = self.plant_counts[plant_type] * PLANT_CAPACITY[plant_type]
            if plant_type in RENEWABLE_TYPES:
                renewable_nameplate += capacity
                factor = 1 + (weather_rng() * 2 - 1) * WEATHER_VARIANCE_FRACTION
                renewable_actual += capacity * max(0.0, factor)
            else:
                dispatchable_total += capacity

        # TODO-C17: stash this round's nameplate/actual renewable output so
        # advance_round() can narrate it into weather_log without spending
        # a second, non-deterministic call against weather_rng.
        self.last_weather_renewable_nameplate = renewable_nameplate
        self.last_weather_renewable_actual = renewable_actual

        shortfall = max(0.0, renewable_nameplate - renewable_actual)
        compensation = min(self.battery_capacity(), shortfall)
        return dispatchable_total + renewable_actual + compensation

    def primary_emissions_source(self):
        """C3: which standing fossil type is most responsible for this
        round's emissions -- the type a generic brownout message should
        actually name, rather than reading as an unattributed "the grid"
        event. None when there's no fossil plant standing at all (a
        brownout can still occur from *historical* accumulated emissions
        even after the player has fully retired fossil capacity -- see
        event_message()'s fallback for that case)."""
        candidates = [t for t in FOSSIL_TYPES if self.plant_counts[t] > 0]
        if not candidates:
            return None
        return max(candidates, key=lambda t: self.plant_counts[t] * PLANT_CAPACITY[t] * EMISSIONS_FACTOR[t])

    def advance_round(self, rng=None, age_rng=None, weather_rng=None):
        # Seeded run: each purpose draws from its own stateless stream for this round (see stream()).
        # Tests and the shadow grid pass their own callables instead.
        if rng is None:
            rng = self.stream("disruption").random
        if age_rng is None:
            age_rng = self.stream("aging").random
        if weather_rng is None:
            weather_rng = self.stream("weather").random
        self.undo_record = None
        # GC-25: an offer nobody answered lapses as declined when the round moves on.
        if self.grant_offer is not None:
            self.decline_grant()
        # TODO-C23: run any pre-committed auto-maintenance before this
        # round's own aging/breakdown roll, so a scheduled type actually
        # gets the benefit this round rather than one round late.
        funds_before_round = self.funds
        round_played = self.round_number
        demand_played = self.demand
        scheduled_actions = self._run_scheduled_maintenance()

        effective_capacity = self.effective_capacity_for_revenue(weather_rng)
        met_demand = min(effective_capacity, self.demand)
        revenue = met_demand * REVENUE_PER_UNIT_MET
        base_revenue = revenue
        # GC-15: the Perfect Round combo's bonus on this round's base revenue (earned by the
        # streak so far, so it applies before this round's own result is known).
        perfect_bonus = base_revenue * self.perfect_bonus_fraction()
        revenue += perfect_bonus
        # C9: optional storage arbitrage on top of ordinary revenue.
        arbitrage_revenue = self._run_arbitrage(effective_capacity)
        revenue += arbitrage_revenue
        regional_revenue = 0.0
        regional_shortfall_before = self.regional_grid_total_shortfall_cost

        # C3: the regional grid (if connected) gets first claim on whatever
        # surplus capacity arbitrage charging didn't already use this round
        # -- reads _run_arbitrage's own record of what it took, rather than
        # recomputing a second independent guess, so the same idle capacity
        # is never counted for both.
        if self.regional_grid_connected:
            raw_surplus = max(0.0, effective_capacity - self.demand)
            claimed_by_arbitrage = (
                self.last_arbitrage["units"]
                if self.last_arbitrage and self.last_arbitrage["mode"] == "charge"
                else 0.0
            )
            available_surplus = max(0.0, raw_surplus - claimed_by_arbitrage)
            regional_revenue = self._advance_regional_grid(available_surplus)
            revenue += regional_revenue

        # TODO-C17: narrate this round's weather effect on renewable
        # output, using the nameplate/actual figures
        # effective_capacity_for_revenue() just stashed above -- no second
        # weather_rng call, so this never changes the round's own outcome,
        # only whether it gets written down. Skipped when there's no
        # renewable nameplate capacity to have varied in the first place.
        weather_delta_pct = None
        if self.weather_variability_enabled and self.last_weather_renewable_nameplate > 0:
            delta_pct = (
                (self.last_weather_renewable_actual - self.last_weather_renewable_nameplate)
                / self.last_weather_renewable_nameplate
                * 100
            )
            weather_delta_pct = delta_pct
            direction = "above" if delta_pct >= 0 else "below"
            self.weather_log.append(
                f"Round {self.round_number}: weather variability put renewable "
                f"output {abs(delta_pct):.0f}% {direction} nameplate capacity."
            )
            if len(self.weather_log) > WEATHER_LOG_MAX_ENTRIES:
                self.weather_log = self.weather_log[-WEATHER_LOG_MAX_ENTRIES:]

        event = None
        immunity_round = False
        disruption_hit = rng() < self.disruption_probability()
        if disruption_hit and self.immunity_available:
            # GC-2b Diplomatic Immunity: the first disruption of the run is called off.
            self.immunity_available = False
            self.immunity_used = True
            immunity_round = True
            disruption_hit = False
        if disruption_hit:
            severity = self.disruption_severity()
            revenue_loss = revenue * severity * MAX_REVENUE_LOSS_FRACTION
            revenue -= revenue_loss
            event = {
                "type": "brownout",
                "severity": severity,
                "revenue_loss": revenue_loss,
                # C3: attach a specific cause even for a generic brownout,
                # rather than leaving it as an unattributed message --
                # None only when no fossil plant is currently standing to
                # blame (see event_message()'s "lingering" fallback text).
                "cause_plant": self.primary_emissions_source(),
            }

            if severity >= DAMAGE_SEVERITY_THRESHOLD:
                damaged_type = self._fossil_plant_to_damage()
                if damaged_type:
                    self.plant_counts[damaged_type] -= 1
                    event["type"] = "damage"
                    event["damaged_plant"] = damaged_type

        self.funds += revenue
        self.lifetime_revenue += revenue
        if event is not None:
            self.lifetime_disruption_spend += event["revenue_loss"]
        self.emissions += self.emissions_this_round()
        self.global_reference_emissions += (
            self.total_capacity() * GLOBAL_AVG_FOSSIL_SHARE * GLOBAL_AVG_FOSSIL_EMISSIONS_FACTOR
        )
        # C17 -- same installed capacity this round, same basis
        # emissions_this_round() itself uses, priced against "what if
        # this had all just been coal" instead of whatever mix the player
        # actually built. Deliberately total_capacity()-based rather than
        # demand-based: the counterfactual isolates the *fuel-mix*
        # decision specifically, holding how much got built constant, so
        # a grid that's genuinely all-coal correctly nets to zero avoided
        # emissions instead of showing a misleading "savings" purely from
        # under-building relative to rising demand.
        self.bau_emissions += self.total_capacity() * BAU_EMISSIONS_FACTOR

        aging_event = None
        oldest = self.oldest_vulnerable_plant()
        for plant_type in PLANT_TYPES:
            if self.plant_counts[plant_type] > 0:
                self.plant_age[plant_type] += 1
        if oldest is not None and age_rng() < self.aging_breakdown_probability():
            self.plant_counts[oldest] -= 1
            repair_cost = PLANT_BASE_COST[oldest] * AGING_BREAKDOWN_COST_FRACTION
            self.funds = max(0.0, self.funds - repair_cost)
            self.lifetime_disruption_spend += repair_cost
            self.aging_breakdown_count += 1
            aging_event = {"type": "aging_breakdown", "plant": oldest, "repair_cost": repair_cost}

        # TODO-C19: advance the currently-active policy lever's clock, and
        # -- once no policy is active and the offer isn't already sitting
        # open -- check whether it's time to offer a fresh one. Checked
        # against the round that's *about to* start (round_number is still
        # pre-increment here), so "every POLICY_LEVER_INTERVAL rounds"
        # reads the same way a player experiences round numbers in the UI.
        if self.active_policy is not None:
            self.active_policy["rounds_remaining"] -= 1
            if self.active_policy["rounds_remaining"] <= 0:
                self.active_policy = None
        if (
            self.active_policy is None
            and not self.policy_lever_available
            and self.round_number > self.last_policy_lever_round_offered
            and self.round_number % POLICY_LEVER_INTERVAL == 0
        ):
            self.policy_lever_available = True

        self.round_number += 1
        # TODO-C7: demand_growth_this_round() is the single source of truth
        # for how much demand rises this round, including any demand-
        # response investment -- see that method's own docstring.
        demand_growth = self.demand_growth_this_round()
        self.demand += demand_growth

        self.last_event = event
        if event:
            self.event_log.append(event)
            self.current_clean_streak = 0
        else:
            self.current_clean_streak += 1
            self.best_clean_streak = max(self.best_clean_streak, self.current_clean_streak)
        self.last_aging_event = aging_event
        self._update_emergency()
        # GC-15: a Perfect Round has no disruption (a waived one counts), no aging breakdown and
        # demand fully met; the streak of them raises next round's revenue bonus.
        perfect_round = event is None and aging_event is None and effective_capacity >= demand_played
        if perfect_round:
            self.perfect_streak += 1
            self.best_perfect_streak = max(self.best_perfect_streak, self.perfect_streak)
        else:
            self.perfect_streak = 0
        # GC-25: strings of an accepted grant run down by one round; then maybe a new offer.
        for key in self.grant_effects:
            if self.grant_effects[key] > 0:
                self.grant_effects[key] -= 1
        self._maybe_offer_grant(round_played)

        self.clean_fraction_log.append(1 - self.fossil_share())
        self.emissions_history.append(self.emissions)
        self.avg_renewable_cost_history.append(self.average_renewable_cost())
        self.global_reference_emissions_history.append(self.global_reference_emissions)
        self.funds_history.append(self.funds)
        self.demand_history.append(self.demand)
        # GC-26: the first round the standing grid was at least 90% clean.
        if (
            self.first_90_clean_round is None
            and self.total_capacity() > 0
            and 1 - self.fossil_share() >= RECORD_CLEAN_SHARE
        ):
            self.first_90_clean_round = len(self.clean_fraction_log)
        # C-8: one structured record of what this round did to the books.
        self.last_round_recap = {
            "round": round_played,
            "net": self.funds - funds_before_round,
            "base_revenue": base_revenue,
            "arbitrage": arbitrage_revenue,
            "regional": regional_revenue,
            "regional_shortfall": self.regional_grid_total_shortfall_cost - regional_shortfall_before,
            "scheduled": scheduled_actions,
            "weather_pct": weather_delta_pct,
            "disruption_loss": event["revenue_loss"] if event else 0.0,
            "repair_cost": aging_event["repair_cost"] if aging_event else 0.0,
            "aging_plant": aging_event["plant"] if aging_event else None,
            "disruption_type": event["type"] if event else None,
            "demand_growth": demand_growth,
            "perfect_bonus": perfect_bonus,
            "perfect": perfect_round,
            "immunity": immunity_round,
        }

    # ---- GC-15 Perfect Round combo ---------------------------------------------------------
    def perfect_bonus_fraction(self):
        """The revenue bonus the current Perfect Round streak earns on the next round."""
        return PERFECT_ROUND_STEP * min(self.perfect_streak, PERFECT_ROUND_MAX_STEPS)

    # ---- GC-25 surprise grants ---------------------------------------------------------------
    def _maybe_offer_grant(self, round_played):
        if self.grant_offer is not None or self.policy_lever_available:
            return
        if self.round_number < GRANT_MIN_ROUND:
            return
        rng = self.stream("grant", round_played)
        if rng.random() >= GRANT_ODDS:
            return
        self.grant_offer = {"id": rng.choice(GRANT_ORDER), "round": self.round_number}

    def accept_grant(self):
        """Take the open offer, strings and all."""
        offer = self.grant_offer
        if offer is None:
            return False
        kind = offer["id"]
        self.grant_offer = None
        self.undo_record = None
        if kind == "clean_grant":
            self.funds += GRANT_CLEAN_FUNDS
            self.grant_effects["fossil_surcharge"] = GRANT_CLEAN_ROUNDS
            self.last_grant_message = (
                f"Grant accepted: +{GRANT_CLEAN_FUNDS} funds. Fossil plants cost 25% more to build for {GRANT_CLEAN_ROUNDS} rounds."
            )
        elif kind == "sponsor_deal":
            self.funds += GRANT_SPONSOR_FUNDS
            self.demand += GRANT_SPONSOR_DEMAND
            self.last_grant_message = f"Deal taken: +{GRANT_SPONSOR_FUNDS} funds, and demand rose by {GRANT_SPONSOR_DEMAND}."
        else:
            paid = min(self.funds, GRANT_FINE)
            self.funds -= paid
            for plant_type in PLANT_TYPES:
                self.plant_age[plant_type] = max(0.0, self.plant_age[plant_type] - GRANT_REPAIR_AGE)
            self.last_grant_message = f"Fine paid ({paid:.0f} funds) and the wear problems repaired: every fleet's wear dropped."
        return True

    def decline_grant(self):
        offer = self.grant_offer
        if offer is None:
            return False
        kind = offer["id"]
        self.grant_offer = None
        if kind == "inspection_fine":
            self.grant_effects["breakdown_risk"] = GRANT_CONTEST_ROUNDS
            self.last_grant_message = (
                f"Fine contested. Aging breakdown chance is doubled for {GRANT_CONTEST_ROUNDS} rounds."
            )
        else:
            self.last_grant_message = "Offer declined. No strings, no money."
        return True

    # ---- GC-11 peek forecast (meteorology branch of the upgrade tree) -----------------------
    def peek_unlocked(self):
        return "weather_station" in self.perks

    def peek_active(self):
        return self.peeked_round == self.round_number and self.peek_unlocked()

    def buy_peek(self):
        """Pay PEEK_FEE once per round to read the coming round's rolls."""
        if not self.peek_unlocked() or self.peeked_round == self.round_number or self.funds < PEEK_FEE:
            return False
        self.funds -= PEEK_FEE
        self.lifetime_build_spend += PEEK_FEE
        self.undo_record = None
        self.peeked_round = self.round_number
        return True

    def renewable_weather_factors(self, round_number=None):
        """The output factor each renewable type gets in a round with weather variability on, in the
        same order and from the same stream advance_round() uses (so a peek is exact)."""
        rng = self.stream("weather", round_number)
        out = {}
        for plant_type in GENERATION_TYPES:
            if plant_type in RENEWABLE_TYPES:
                out[plant_type] = 1 + (rng.random() * 2 - 1) * WEATHER_VARIANCE_FRACTION
        return out

    def peek_forecast(self):
        """What the coming round holds: the disruption roll (given the emissions it will be rolled
        against) and, with weather variability on, each renewable's output factor; with the
        long-range outlook, the round after next's weather too."""
        probability = self.disruption_probability()
        will_hit = self.stream("disruption").random() < probability
        waived = will_hit and self.immunity_available
        forecast = {
            "round": self.round_number,
            "probability": probability,
            "disruption": "waived" if waived else ("hit" if will_hit else "none"),
            "weather": self.renewable_weather_factors() if self.weather_variability_enabled else None,
            "weather_next": None,
        }
        if "long_range_outlook" in self.perks and self.weather_variability_enabled:
            forecast["weather_next"] = self.renewable_weather_factors(self.round_number + 1)
        return forecast

    def average_clean_fraction(self):
        """Sustained cleanliness across the whole run so far — every round
        played counts equally, so a late clean sprint can't fully erase a
        dirty start. This is the "not just final snapshot" scoring rule."""
        if not self.clean_fraction_log:
            return 0.0
        return sum(self.clean_fraction_log) / len(self.clean_fraction_log)

    def score(self):
        return self.average_clean_fraction() * 100

    def emissions_avoided(self):
        """C17: cumulative emissions saved vs. the business-as-usual
        coal-only counterfactual in bau_emissions -- the closing summary's
        headline "hope angle" number. Floored at zero so a player who did
        worse than the counterfactual (e.g. never invested at all, so the
        two trajectories are ~equal) never sees a misleading negative."""
        return max(0.0, self.bau_emissions - self.emissions)

    def clean_trend(self):
        """Compares the first half of rounds played to the second half —
        the hope-angle payoff: a visibly improving trend is the direct
        reward for early renewable investment, not just a good final number."""
        n = len(self.clean_fraction_log)
        if n < 4:
            return None
        half = n // 2
        first_half_avg = sum(self.clean_fraction_log[:half]) / half
        second_half_avg = sum(self.clean_fraction_log[half:]) / (n - half)
        return first_half_avg, second_half_avg

    def resilience_score(self):
        """C11: diversification as its own axis, 0..100 -- normalized
        Shannon entropy of the generation-capacity shares across the six
        generation types. All-one-type (all-renewable OR all-fossil) scores
        0; an even spread across every type scores 100. Deliberately
        independent of clean share: it rewards not depending on a single
        source, not cleanliness."""
        import math  # noqa: PLC0415

        shares = [self.capacity_share(t) for t in GENERATION_TYPES]
        entropy = -sum(x * math.log(x) for x in shares if x > 0)
        return round(entropy / math.log(len(GENERATION_TYPES)) * 100)

    def projection(self, rounds=PROJECTION_ROUNDS):
        """C25: extrapolates the current fleet unchanged for `rounds` more
        rounds -- emissions if nothing changes, versus the all-coal
        business-as-usual line over the same window, plus where demand
        will be against today's capacity. A straight-line extrapolation,
        deliberately not a forecast of what the player would do. Uses
        demand_growth_this_round() (TODO-C7) so an active demand-response
        investment correctly flattens the projected demand line too."""
        base_growth = self.demand_growth_this_round()
        return {
            "rounds": rounds,
            "emissions": self.emissions + self.emissions_this_round() * rounds,
            "bau_emissions": self.emissions + self.total_capacity() * BAU_EMISSIONS_FACTOR * rounds,
            "demand": self.demand + base_growth * rounds,
            "capacity": self.total_capacity(),
        }

    def benchmark_grade(self):
        """C5: a letter grade of cumulative emissions against the
        real-world benchmark line (global_reference_emissions). None until
        a round has been played (no benchmark to compare against yet)."""
        if self.global_reference_emissions <= 0:
            return None
        ratio = self.emissions / self.global_reference_emissions
        for limit, letter in GRADE_THRESHOLDS:
            if ratio <= limit:
                return letter
        return "F"

    def demand_response_cost(self):
        """TODO-C7: escalating cost for the next demand-response purchase."""
        cost = DEMAND_RESPONSE_BASE_COST * (DEMAND_RESPONSE_COST_GROWTH ** self.demand_response_level)
        if "demand_analytics" in self.perks:
            cost *= DEMAND_ANALYTICS_COST_MULTIPLIER
        return cost

    def invest_demand_response(self):
        """TODO-C7: the fourth lever -- spend funds to permanently trim
        this grid's demand growth, rather than build/retire/maintain
        capacity to meet whatever demand turns out to be."""
        cost = self.demand_response_cost()
        if self.funds < cost:
            return False
        self.undo_record = None
        self.funds -= cost
        # Counted alongside build spend in the funds breakdown -- it's the
        # same category of "spent on infrastructure," just demand-side
        # instead of supply-side.
        self.lifetime_build_spend += cost
        self.demand_response_level += 1
        return True

    def demand_growth_this_round(self):
        """TODO-C7: DEMAND_GROWTH_PER_ROUND (doubled if the steeper-demand
        difficulty toggle is on), trimmed by demand-response investment,
        floored so growth can never go negative or stall out entirely.
        Single source of truth for advance_round()/projection()/the
        demand-growth-arrow tooltip, so all three always agree."""
        growth = DEMAND_GROWTH_PER_ROUND
        if self.steeper_demand_growth_enabled:
            growth *= STEEP_DEMAND_GROWTH_MULTIPLIER
        growth -= self.demand_response_level * DEMAND_RESPONSE_REDUCTION_PER_LEVEL
        return max(DEMAND_RESPONSE_MIN_GROWTH, growth)

    def enact_policy(self, policy_type):
        """TODO-C19: opt into the currently-offered policy lever. Only one
        can be active at a time; enacting one clears the offer until the
        next POLICY_LEVER_INTERVAL passes."""
        if not self.policy_lever_available:
            return False
        if policy_type not in ("carbon_pricing", "renewable_subsidy"):
            return False
        self.policy_lever_available = False
        duration = POLICY_LEVER_DURATION
        if policy_type == "renewable_subsidy" and "policy_liaison" in self.perks:
            duration += POLICY_LIAISON_EXTRA_ROUNDS
        self.active_policy = {"type": policy_type, "rounds_remaining": duration}
        self.last_policy_lever_round_offered = self.round_number
        return True

    def decline_policy(self):
        """TODO-C19: opt out of the currently-offered lever without
        enacting either option -- it won't be offered again until the
        next interval."""
        if not self.policy_lever_available:
            return False
        self.policy_lever_available = False
        self.last_policy_lever_round_offered = self.round_number
        return True

    def set_maintenance_schedule(self, plant_type, interval):
        """TODO-C23: pre-commit plant_type to an auto-maintain cadence
        (every `interval` rounds), or pass 0 to go back to manual-only."""
        if plant_type not in self.maintenance_schedule:
            return False
        if interval not in MAINTENANCE_SCHEDULE_OPTIONS:
            return False
        self.maintenance_schedule[plant_type] = interval
        return True

    def _run_scheduled_maintenance(self):
        """TODO-C23: called once at the start of advance_round(), before
        this round's aging/breakdown roll -- so a scheduled maintenance
        pass actually pre-empts the risk it's meant to manage, the same
        round it fires, rather than lagging a round behind. Best-effort:
        a type whose schedule fires but can't afford maintenance this
        round is silently skipped (maintain_plant() already returns False
        for that, same as a manual click on an unaffordable Maintain
        button would). Returns the passes that actually ran, as
        {"plant", "cost"} dicts, for the C-8 round recap."""
        done = []
        for plant_type in PLANT_TYPES:
            interval = self.maintenance_schedule[plant_type]
            if interval <= 0:
                continue
            if self.plant_counts[plant_type] <= 0:
                continue
            if self.round_number % interval != 0:
                continue
            cost = self.maintenance_cost(plant_type)
            if self.maintain_plant(plant_type):
                done.append({"plant": plant_type, "cost": cost})
        return done


# C5 -- ascending (max emissions/benchmark ratio, letter). Above the last
# limit is an "F".
GRADE_THRESHOLDS = [(0.2, "A"), (0.5, "B"), (0.8, "C"), (1.0, "D")]

state = GridState()


# --- Z-18: the practice sandbox -------------------------------------------------------------------
# An opt-in mode with no fail states, every tool open and the real game and its achievements left
# alone. The rules, in one place:
#   - unlimited funds (the balance never drops below SANDBOX_FUNDS, so every build, maintenance pass and
#     demand-response purchase is free);
#   - no disruptions, no aging breakdowns, no surprise grants or fines and an emergency that cannot be
#     missed: nothing the player does can break the grid;
#   - every upgrade-tree node is switched on (loadouts, peek forecast, cheaper builds and upkeep), and the
#     starting scenario can be changed at any time (which starts the sandbox grid over);
#   - the real game is set aside whole (see sandbox_enter) and put back unchanged on leaving.
# The sandbox grid is a separate SandboxGridState object, so nothing it does can touch the real one.
SANDBOX_FUNDS = 1_000_000
SANDBOX_ALL_PERKS = frozenset(skill_tree.effects(CAREER_TREE, CAREER_UNLOCK_ORDER))


class SandboxGridState(GridState):
    """A grid that cannot fail: see the Z-18 note above."""

    sandbox = True

    @property
    def funds(self):
        return self._funds

    @funds.setter
    def funds(self, value):
        self._funds = max(float(value), float(SANDBOX_FUNDS))

    def disruption_probability(self):
        return 0.0

    def aging_breakdown_probability(self):
        return 0.0

    def breakdown_risk_probability(self, plant_type):
        return 0.0

    def _maybe_offer_grant(self, round_played):
        return None

    def _update_emergency(self):
        """The emergency scenario can still be stabilized, but its clock never runs out."""
        em = self.emergency
        if em is None or em["status"] != "active":
            return
        em["hold"] = em["hold"] + 1 if self.total_capacity() >= self.demand else 0
        if em["hold"] >= EMERGENCY_HOLD_ROUNDS:
            em["status"] = "stabilized"


def new_sandbox_state(scenario_id="standard"):
    """A fresh sandbox grid on the given starting scenario, with every perk on."""
    fresh = SandboxGridState()
    fresh.perks = set(SANDBOX_ALL_PERKS)
    fresh.apply_scenario(scenario_id if scenario_id in SCENARIOS else "standard")
    return fresh


# --- C1: grid operator career ------------------------------------------------
# Persisted in the browser's localStorage (survives across runs, unlike the
# per-run save code) and mirrored into get_state() so a save code carries it
# to another device; load_state() only adopts a saved career that has
# completed at least as many runs as the live one (never rolls it back).

def _default_lifetime():
    return {
        "rounds": 0,
        "built": {t: 0 for t in PLANT_TYPES},
        "brownouts": 0,
        "damages": 0,
        "aging": 0,
        "scenario_grades": {},
    }


def _default_career():
    return {
        "runs": 0,
        "points": 0,
        "best_score": 0.0,
        "best_grade": None,
        "unlocked": [],
        "achievements": [],
        # C-1: the last CAREER_HISTORY_MAX finished runs (oldest first).
        "history": [],
        # C-7: uncapped lifetime totals behind the lifetime statistics.
        "lifetime": _default_lifetime(),
        # GC-26: personal records (None = not set yet).
        "best_streak": 0,
        "best_rounds_to_90": None,
        # GC-2b: the starting loadout chosen for the next run (None = none).
        "loadout": None,
    }


career = _default_career()
# GC-26: records the most recent Finish run broke (empty = none); shown as a
# "New record!" line in the Career panel until the next round is advanced.
last_finish_records = []


def _career_number(value, default, lo, hi):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return default
    return max(lo, min(hi, value))


def _clean_series(raw, lo, hi):
    """C-1: a saved per-round series -> a list of at most
    CAREER_SERIES_POINTS finite numbers clamped into [lo, hi]."""
    if not isinstance(raw, list):
        return []
    out = []
    for value in raw[:CAREER_SERIES_POINTS]:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
            return []
        out.append(max(lo, min(hi, int(round(value)))))
    return out


def _clean_seed(raw):
    if not isinstance(raw, str):
        return ""
    return seed_lib.normalize(raw, SEED_GAME)


def _validate_whatif(raw):
    """C-3: the saved what-if rows -> at most one row per known strategy."""
    out = []
    if not isinstance(raw, list):
        return out
    known = {key for key, _label in WHATIF_STRATEGIES}
    for entry in raw:
        if not isinstance(entry, dict) or entry.get("id") not in known or entry["id"] in [o["id"] for o in out]:
            continue
        grade = entry.get("grade")
        out.append({
            "id": entry["id"],
            "grade": grade if grade in CAREER_GRADE_POINTS else "F",
            "funds": int(_career_number(entry.get("funds"), 0, 0, 10 ** 9)),
            "score": round(float(_career_number(entry.get("score"), 0.0, 0.0, 100.0)), 1),
        })
    return out


def _validate_run_record(raw):
    """C-1: one finished-run record, or None if it is not usable."""
    if not isinstance(raw, dict):
        return None
    scenario = raw.get("scenario")
    grade = raw.get("grade")
    if scenario not in SCENARIOS or grade not in CAREER_GRADE_POINTS:
        return None
    built = raw.get("built") if isinstance(raw.get("built"), dict) else {}
    r90 = raw.get("r90")
    return {
        "scenario": scenario,
        "grade": grade,
        "points": int(_career_number(raw.get("points"), 0, 0, 100)),
        "rounds": int(_career_number(raw.get("rounds"), 0, 0, 100000)),
        "score": round(float(_career_number(raw.get("score"), 0.0, 0.0, 100.0)), 1),
        "resilience": int(_career_number(raw.get("resilience"), 0, 0, 100)),
        "funds": int(_career_number(raw.get("funds"), 0, 0, 10 ** 9)),
        "emissions": int(_career_number(raw.get("emissions"), 0, 0, 10 ** 9)),
        "streak": int(_career_number(raw.get("streak"), 0, 0, 100000)),
        "brownouts": int(_career_number(raw.get("brownouts"), 0, 0, 100000)),
        "damages": int(_career_number(raw.get("damages"), 0, 0, 100000)),
        "aging": int(_career_number(raw.get("aging"), 0, 0, 100000)),
        "r90": (
            int(_career_number(r90, 1, 1, 100000))
            if isinstance(r90, (int, float)) and not isinstance(r90, bool) and r90 == r90
            else None
        ),
        "built": {t: int(_career_number(built.get(t), 0, 0, 100000)) for t in PLANT_TYPES},
        "clean": _clean_series(raw.get("clean"), 0, 100),
        "funds_series": _clean_series(raw.get("funds_series"), 0, 10 ** 9),
        "demand_series": _clean_series(raw.get("demand_series"), 0, 10 ** 9),
        # 2026-10-08: the run's seed, whether it was Ironman, and the C-3 what-if results.
        "seed": _clean_seed(raw.get("seed")),
        "ironman": bool(raw.get("ironman", False)),
        "whatif": _validate_whatif(raw.get("whatif")),
    }


def _validate_lifetime(raw):
    out = _default_lifetime()
    if not isinstance(raw, dict):
        return out
    out["rounds"] = int(_career_number(raw.get("rounds"), 0, 0, 10 ** 7))
    built = raw.get("built") if isinstance(raw.get("built"), dict) else {}
    out["built"] = {t: int(_career_number(built.get(t), 0, 0, 10 ** 7)) for t in PLANT_TYPES}
    for key in ("brownouts", "damages", "aging"):
        out[key] = int(_career_number(raw.get(key), 0, 0, 10 ** 7))
    grades = raw.get("scenario_grades")
    if isinstance(grades, dict):
        for scenario, entry in grades.items():
            if scenario in SCENARIOS and isinstance(entry, dict):
                runs = int(_career_number(entry.get("n"), 0, 0, 100000))
                if runs > 0:
                    out["scenario_grades"][scenario] = {
                        "n": runs,
                        "points": int(_career_number(entry.get("points"), 0, 0, 100000 * 4)),
                    }
    return out


def validate_career(raw):
    """Coerce anything (corrupt JSON, hand-edited save) into a valid career
    dict; every bad field falls back to its default."""
    out = _default_career()
    if not isinstance(raw, dict):
        return out
    out["runs"] = int(_career_number(raw.get("runs"), 0, 0, 100000))
    out["points"] = int(_career_number(raw.get("points"), 0, 0, 1000000))
    out["best_score"] = float(_career_number(raw.get("best_score"), 0.0, 0.0, 100.0))
    grade = raw.get("best_grade")
    out["best_grade"] = grade if grade in CAREER_GRADE_POINTS else None
    unlocked = raw.get("unlocked")
    if isinstance(unlocked, list):
        out["unlocked"] = [u for u in unlocked if isinstance(u, str)]
    banked = raw.get("achievements")
    if isinstance(banked, list):
        out["achievements"] = [a for a in banked if isinstance(a, str)][:200]
    out["best_streak"] = int(_career_number(raw.get("best_streak"), 0, 0, 100000))
    r90 = raw.get("best_rounds_to_90")
    out["best_rounds_to_90"] = (
        int(_career_number(r90, 1, 1, 100000))
        if isinstance(r90, (int, float)) and not isinstance(r90, bool) and r90 == r90
        else None
    )
    history = raw.get("history")
    if isinstance(history, list):
        valid = [_validate_run_record(entry) for entry in history]
        out["history"] = [entry for entry in valid if entry is not None][-CAREER_HISTORY_MAX:]
    out["lifetime"] = _validate_lifetime(raw.get("lifetime"))
    # Never let unlocks exceed what the earned points could have paid for: unknown ids, repeats and
    # nodes whose prerequisites are not owned are dropped, and an overspend is trimmed from the newest end.
    out["unlocked"] = skill_tree.sanitize_owned(CAREER_TREE, out["unlocked"], out["points"], overspend="trim")
    loadout = raw.get("loadout")
    out["loadout"] = loadout if loadout in LOADOUT_NODES and loadout in out["unlocked"] else None
    return out


def career_points_available():
    return skill_tree.points_left(CAREER_TREE, career["unlocked"], career["points"])


def _career_storage():
    try:
        import js  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return None
    return getattr(js, "localStorage", None)


def load_career_from_storage():
    storage = _career_storage()
    if storage is None:
        return _default_career()
    try:
        raw = storage.getItem(CAREER_STORAGE_KEY)
        return validate_career(json.loads(raw)) if raw else _default_career()
    except Exception:  # noqa: BLE001 -- private mode / corrupt JSON: start fresh
        return _default_career()


def save_career_to_storage():
    if sandbox_active:  # Z-18: the sandbox never writes the career
        return
    storage = _career_storage()
    if storage is None:
        return
    try:
        storage.setItem(CAREER_STORAGE_KEY, json.dumps(career))
    except Exception:  # noqa: BLE001 -- a refused write must never break play
        pass


def _sync_perks():
    if sandbox_active:  # Z-18: every upgrade-tree node is on in the sandbox
        state.perks = set(SANDBOX_ALL_PERKS)
        return
    state.perks = set(skill_tree.effects(CAREER_TREE, career["unlocked"]))


def run_career_points():
    """Points finishing the current run would bank, with a short breakdown
    list; (0, [reason]) if the run is too short to count."""
    rounds_played = state.round_number - 1
    if rounds_played < CAREER_MIN_ROUNDS:
        return 0, [f"Play at least {CAREER_MIN_ROUNDS} rounds ({rounds_played} so far) for a run to count."]
    grade = state.benchmark_grade() or "F"
    parts = ["1 for finishing", f"{CAREER_GRADE_POINTS[grade]} for operator grade {grade}"]
    total = 1 + CAREER_GRADE_POINTS[grade]
    if state.resilience_score() >= CAREER_RESILIENCE_BONUS_THRESHOLD:
        total += 1
        parts.append("1 for resilience 60+")
    if state.emergency is not None and state.emergency["status"] == "stabilized":
        total += 1
        parts.append("1 for stabilizing the emergency")
    return total, parts


def finish_run():
    """Bank this run into the career and start a fresh run. Returns the
    points banked, or None if the run is too short to count (nothing
    changes in that case)."""
    if sandbox_active:  # Z-18: a sandbox run never counts towards the career
        return None
    points, _ = run_career_points()
    if points <= 0 and state.round_number - 1 < CAREER_MIN_ROUNDS:
        return None
    global last_finish_records
    grade = state.benchmark_grade() or "F"
    record = run_record(points, grade)
    broken = []
    first_run = career["runs"] == 0
    career["runs"] += 1
    career["points"] += points
    score = round(state.score(), 1)
    if score > career["best_score"]:
        if not first_run:
            broken.append(f"best clean score {score:.0f}/100")
        career["best_score"] = score
    order = "ABCDF"
    best = career["best_grade"]
    if best is None or order.index(grade) < order.index(best):
        if best is not None:
            broken.append(f"best operator grade {grade}")
        career["best_grade"] = grade
    if record["streak"] > career["best_streak"]:
        if not first_run:
            broken.append(f"longest disruption-free streak {record['streak']} rounds")
        career["best_streak"] = record["streak"]
    r90 = record["r90"]
    if r90 is not None and (career["best_rounds_to_90"] is None or r90 < career["best_rounds_to_90"]):
        if career["best_rounds_to_90"] is not None:
            broken.append(f"fewest rounds to 90% clean: {r90}")
        career["best_rounds_to_90"] = r90
    banked = set(career["achievements"]) | set(achievement_ids_earned())
    career["achievements"] = [e["id"] for e in ACHIEVEMENTS if e["id"] in banked]
    career["history"] = (career["history"] + [record])[-CAREER_HISTORY_MAX:]
    _add_to_lifetime(record)
    last_finish_records = broken
    save_career_to_storage()
    _start_new_run()
    return points


def _thin(values, scale=1.0):
    """C-1: at most CAREER_SERIES_POINTS evenly spaced, rounded points."""
    n = len(values)
    if n == 0:
        return []
    if n > CAREER_SERIES_POINTS:
        idx = [round(i * (n - 1) / (CAREER_SERIES_POINTS - 1)) for i in range(CAREER_SERIES_POINTS)]
        values = [values[i] for i in idx]
    return [int(round(v * scale)) for v in values]


def run_record(points, grade):
    """C-1: the current run, filed as one history record (what the Career
    panel's history list, stacked charts and lifetime statistics read)."""
    brownouts = sum(1 for e in state.event_log if e.get("type") == "brownout")
    damages = sum(1 for e in state.event_log if e.get("type") == "damage")
    return {
        "scenario": state.scenario,
        "grade": grade,
        "points": points,
        "rounds": state.round_number - 1,
        "score": round(state.score(), 1),
        "resilience": state.resilience_score(),
        "funds": max(0, int(round(state.funds))),
        "emissions": max(0, int(round(state.emissions))),
        "streak": state.best_clean_streak,
        "brownouts": brownouts,
        "damages": damages,
        "aging": state.aging_breakdown_count,
        "r90": state.first_90_clean_round,
        "built": {t: state.cumulative_built.get(t, 0) for t in PLANT_TYPES},
        "clean": _thin(state.clean_fraction_log, 100.0),
        "funds_series": _thin([max(0, v) for v in state.funds_history]),
        "demand_series": _thin(state.demand_history),
        "seed": state.seed,
        "ironman": state.ironman,
        "whatif": what_if_results(state),
    }


# C-3 -- the post-run "what if" analyzer. Because every random draw of a run comes from the run's
# seed (see SEED_GAME), a finished run can be replayed on a fresh grid with the same seed, scenario,
# toggles and loadout under three canned strategies and see how each would have ended, facing the
# same weather and disruption rolls. The strategies are simple bots, not optimal play: they are
# there to show what a different philosophy would have cost or earned.
WHATIF_STRATEGIES = [
    ("renewables_early", "All-renewable early"),
    ("no_retire", "Never retire, grow with fossil"),
    ("storage_first", "Storage first"),
]
WHATIF_MAX_ROUNDS = 100
WHATIF_BUILDS_PER_ROUND = 12


def _whatif_grid(source):
    grid = GridState()
    grid.seed = source.seed
    grid.perks = set(source.perks)
    grid.start_option = source.start_option
    grid.steeper_demand_growth_enabled = source.steeper_demand_growth_enabled
    grid.weather_variability_enabled = source.weather_variability_enabled
    grid.apply_scenario(source.scenario)
    return grid


def _cost_per_capacity(grid, plant_type):
    return grid.plant_cost(plant_type) / PLANT_CAPACITY[plant_type]


def _whatif_build_toward(grid, candidates):
    """Build the cheapest-per-capacity candidate while capacity is short of next round's demand."""
    target = grid.demand + grid.demand_growth_this_round()
    for _ in range(WHATIF_BUILDS_PER_ROUND):
        if grid.total_capacity() >= target:
            return
        pick = min(candidates, key=lambda t: _cost_per_capacity(grid, t))
        if not grid.build_plant(pick):
            return


def _whatif_upkeep(grid):
    oldest = grid.oldest_vulnerable_plant()
    if oldest is not None and grid.plant_age[oldest] >= AGE_GRACE_PERIOD:
        if grid.funds >= grid.maintenance_cost(oldest) * 3:
            grid.maintain_plant(oldest)


def _whatif_turn(grid, key):
    if grid.policy_lever_available:
        if key == "no_retire":
            grid.decline_policy()
        else:
            grid.enact_policy("renewable_subsidy")
    if grid.grant_offer is not None:
        grid.decline_grant()
    _whatif_upkeep(grid)
    renewables = [t for t in GENERATION_TYPES if t in RENEWABLE_TYPES]
    if key == "no_retire":
        # Business as usual: keep every plant and meet new demand with the cheapest fossil capacity.
        _whatif_build_toward(grid, list(FOSSIL_TYPES))
        return
    if key == "storage_first" and grid.cumulative_built["battery"] == 0:
        grid.build_plant("battery")
    if key == "renewables_early" and grid.round_number >= 3:
        # Retire a fossil unit once the rest of the fleet still covers demand without it.
        for fossil in ("coal", "gas"):
            if grid.plant_counts[fossil] > 0 and grid.total_capacity() - PLANT_CAPACITY[fossil] >= grid.demand:
                grid.retire_plant(fossil)
                break
    _whatif_build_toward(grid, renewables)
    if key == "storage_first" and grid.plant_counts["battery"] > 0:
        grid.set_arbitrage_mode("discharge" if grid.total_capacity() < grid.demand else "charge")


def simulate_strategy(source, key, rounds):
    """Replay `rounds` rounds of the run `source` (a GridState) under one canned strategy."""
    grid = _whatif_grid(source)
    for _ in range(max(0, min(rounds, WHATIF_MAX_ROUNDS))):
        _whatif_turn(grid, key)
        grid.advance_round()
    return {
        "id": key,
        "grade": grid.benchmark_grade() or "F",
        "funds": max(0, int(round(grid.funds))),
        "score": round(grid.score(), 1),
    }


def what_if_results(source):
    """The three what-if rows for a run, or [] when it is too short to count."""
    rounds = source.round_number - 1
    if rounds < CAREER_MIN_ROUNDS:
        return []
    return [simulate_strategy(source, key, rounds) for key, _label in WHATIF_STRATEGIES]


def career_whatif_rows(record):
    """(label, grade, funds, score) rows: the run itself first, then each strategy."""
    if record is None or not record.get("whatif"):
        return []
    labels = dict(WHATIF_STRATEGIES)
    rows = [("You", record["grade"], record["funds"], record["score"])]
    for entry in record["whatif"]:
        rows.append((labels[entry["id"]], entry["grade"], entry["funds"], entry["score"]))
    return rows


def career_whatif_verdict(record):
    rows = career_whatif_rows(record)
    if not rows:
        return "Finish a run of at least 5 rounds and the same seed is replayed here under three other strategies."
    order = "ABCDF"
    best = min(rows, key=lambda r: (order.index(r[1]), -r[3], -r[2]))
    if best[0] == "You":
        return "Your own play beat all three canned strategies on grade and clean score."
    return f"{best[0]} would have done best: grade {best[1]}, clean score {best[3]:.0f}/100, final funds {best[2]}."


def render_career_whatif(history):
    container = document.getElementById("career-whatif")
    verdict_el = document.getElementById("career-whatif-verdict")
    container.innerHTML = ""
    latest = next((r for r in reversed(history) if r.get("whatif")), None)
    verdict_el.innerText = career_whatif_verdict(latest)
    if latest is None:
        return
    seed_note = f" (seed {latest['seed']})" if latest.get("seed") else ""
    head = document.createElement("div")
    head.className = "shadow-row shadow-row--head"
    for text in (f"Strategy{seed_note}", "Grade", "Funds", "Clean score"):
        cell = document.createElement("span")
        cell.innerText = text
        head.appendChild(cell)
    container.appendChild(head)
    for label, grade, funds, score in career_whatif_rows(latest):
        line = document.createElement("div")
        line.className = "shadow-row"
        for text in (label, grade, str(funds), f"{score:.0f}/100"):
            cell = document.createElement("span")
            cell.innerText = text
            line.appendChild(cell)
        container.appendChild(line)


def _add_to_lifetime(record):
    life = career["lifetime"]
    life["rounds"] += record["rounds"]
    for t in PLANT_TYPES:
        life["built"][t] += record["built"][t]
    life["brownouts"] += record["brownouts"]
    life["damages"] += record["damages"]
    life["aging"] += record["aging"]
    entry = life["scenario_grades"].setdefault(record["scenario"], {"n": 0, "points": 0})
    entry["n"] += 1
    entry["points"] += CAREER_GRADE_POINTS[record["grade"]]


def unlock_career_perk(perk_id):
    """Buy one node of the upgrade tree with career points (prerequisites must be owned)."""
    if sandbox_active:  # Z-18: everything is already on, and the career is not touched
        return False
    result = skill_tree.buy(CAREER_TREE, career["unlocked"], perk_id, career["points"])
    if not result["ok"]:
        return False
    career["unlocked"] = result["owned"]
    save_career_to_storage()
    _refresh_unstarted_run()
    return True


def _refresh_unstarted_run():
    """A run that has not started yet picks up newly bought nodes at once (seed money, a loadout
    choice); a run in progress keeps its rules until the next run, as before."""
    if state.unstarted():
        _sync_perks()
        if state.start_option not in state.perks:
            state.start_option = None
        state.apply_scenario(state.scenario)


def set_loadout(option):
    """GC-2b: choose the starting loadout for this run and the next ones (None = no loadout)."""
    if sandbox_active:  # Z-18: any loadout may be tried; the career's chosen loadout is not touched
        if option is not None and option not in LOADOUT_NODES:
            return False
        if state.unstarted():
            state.start_option = option
            state.apply_scenario(state.scenario)
        return True
    if option is not None and option not in career["unlocked"]:
        return False
    if option is not None and option not in LOADOUT_NODES:
        return False
    career["loadout"] = option
    save_career_to_storage()
    if state.unstarted():
        _sync_perks()
        state.start_option = option
        state.apply_scenario(state.scenario)
    return True


def event_message(event):
    if event is None:
        return "No disruptions last round."
    if event["type"] == "damage":
        plant_name = PLANT_LABEL[event["damaged_plant"]]
        return (
            f"Damage! A {plant_name} plant went offline "
            f"(lost {event['revenue_loss']:.0f} funds in the disruption)."
        )
    # C3: name the specific plant type most responsible, rather than a
    # generic "the grid" message -- falls back to a lingering-emissions
    # framing for the (rarer) case of a brownout with no fossil plant
    # currently standing to attribute it to (historical emissions from
    # fossil capacity retired earlier this run can still be driving risk).
    cause_plant = event.get("cause_plant")
    if cause_plant:
        plant_name = PLANT_LABEL[cause_plant]
        return (
            f"Brownout! {plant_name} generation strained the grid "
            f"(lost {event['revenue_loss']:.0f} funds to instability)."
        )
    return f"Brownout! Lost {event['revenue_loss']:.0f} funds to lingering historical emissions."


def disruption_reason(event):
    """C10: a 'why this happened' line tied to the specific plant behind the
    event, for the disruption toast."""
    severity_pct = event["severity"] * 100
    if event["type"] == "damage":
        plant = PLANT_LABEL[event["damaged_plant"]]
        return (
            f"Why: accumulated emissions put disruption severity at {severity_pct:.0f}%, past the "
            f"{DAMAGE_SEVERITY_THRESHOLD * 100:.0f}% damage line -- your largest fossil fleet ({plant}) took the hit."
        )
    cause = event.get("cause_plant")
    if cause:
        return (
            f"Why: emissions put disruption severity at {severity_pct:.0f}%, and {PLANT_LABEL[cause]} "
            "is your biggest emissions source."
        )
    return f"Why: historical emissions still put disruption severity at {severity_pct:.0f}%."


def event_severity_class(event):
    """CSS class for the event notification — visually distinct so a real
    disruption doesn't read the same as "nothing happened"."""
    if event is None:
        return "event-display"
    if event["type"] == "damage":
        return "event-display event-display--danger"
    return "event-display event-display--warning"


TREND_GRAPH_WIDTH = 280
TREND_GRAPH_HEIGHT = 80

# Shown once, the first time a player builds any renewable plant —
# grounds the cost-curve mechanic (Milestone 2) in the real trend it's
# modeling. Iteration-pass addition: a light factual anchor, not a
# lecture, per the cross-cutting note in CLAUDE.md.
RENEWABLE_UNLOCK_BLURB = (
    "In the real world, each doubling of solar deployment has "
    "historically cut its cost by roughly 20% — economists call this a "
    "learning curve, and it's exactly what's driving your renewable "
    "prices down here."
)

# Info Page — optional, player-triggered supplement (never forced
# mid-session). Framing is written fresh, not copied from any source;
# sources are the curated real-world backing for the game's mechanics.
INFO_PAGE = {
    "framing": (
        "Electricity generation is one of the largest single sources of "
        "global emissions, and the fastest way to cut it is building out "
        "cleaner capacity — not rationing power. Renewables have gotten "
        "dramatically cheaper the more of them get built, a real economic "
        "trend called a learning curve. That's the same tension Grid asks "
        "you to manage: lean into that cheaper long-run path, or lean on "
        "familiar fossil capacity."
    ),
    "mechanic_tie_in": (
        "Grid's cost curve and its global-comparison line are grounded in "
        "published wind/solar learning-rate data (roughly 15%/24% cost "
        "decline per capacity doubling), not an invented number."
    ),
    "sources": [
        {
            "label": "IEA — Rapid rollout of clean technologies makes energy cheaper, not more costly",
            "url": "https://www.iea.org/news/rapid-rollout-of-clean-technologies-makes-energy-cheaper-not-more-costly",
            "note": "Real-world backing for Grid's central claim: leaning renewable is the cheaper long-run path, not a sacrifice.",
        },
        {
            "label": "Oxford Institute for Energy Studies — A critical assessment of learning curves for solar and wind",
            "url": "https://www.oxfordenergy.org/publications/a-critical-assessment-of-learning-curves-for-solar-and-wind-power-technologies/",
            "note": "A balanced, critical look at the same cost-decline concept Grid's core mechanic is built on.",
        },
        {
            "label": "US DOE / Lawrence Berkeley National Lab — Learning a Better Way To Forecast Wind and Solar Energy Costs",
            "url": "https://www.energy.gov/cmei/solar/articles/learning-better-way-forecast-wind-and-solar-energy-costs",
            "note": "The actual learning-rate figures (wind ~15%, solar ~24% per capacity doubling) behind Grid's cost curve.",
        },
        {
            "label": "IEA — Breakthrough Agenda Report 2025: Power",
            "url": "https://www.iea.org/reports/breakthrough-agenda-report-2025/power",
            "note": "Current real-world electricity cost figures, grounding the global-comparison line.",
        },
    ],
}
info_page_open = False


def _normalize_series(series, height, lo=None, hi=None):
    """Maps a series to SVG y-coordinates within [0, height]. Defaults to
    scaling against its own min/max so differently-scaled series
    (emissions counts, renewable costs) can share one chart; an explicit
    lo/hi lets two series (a player's emissions vs. the global-reference
    benchmark) share one scale instead, so they stay directly comparable."""
    if lo is None:
        lo = min(series)
    if hi is None:
        hi = max(series)
    if hi - lo < 1e-9:
        return [height / 2 for _ in series]
    return [height - ((v - lo) / (hi - lo)) * height for v in series]


def trend_graph_svg(emissions_history, cost_history, global_reference_history, clean_fraction_history=None):
    """Three-line trend graph: emissions (rising, red) vs. average
    renewable cost (falling as investment compounds, green) vs. a
    hardcoded global-average emissions benchmark (dashed grey) — the
    Pass 2 addition that gives the player's own emissions line something
    concrete to be measured against, not just a shape in isolation.
    Capped at three lines so it stays legible.

    C15: every point on every line also gets a small hoverable marker
    carrying the exact round/value in a native <title> tooltip, so a
    player who wants a precise number isn't limited to reading it off
    the shape of the line.

    Z17 (site-wide goal): the emissions-vs-global-reference pair -- this
    game's own C15/Pass-2 "global comparison" line, the feature the
    shared shared/comparison_chart.py component was generalized FROM --
    is now built by composing that module's normalize_together()/
    marker_fragment() building blocks rather than this file's own
    (now-removed) combined-min-max/marker code. The avg-renewable-cost
    line stays local: it's a third, unrelated series, not part of the
    "you vs. a reference" comparison shape the shared component covers,
    so this function doesn't use the module's higher-level
    two_series_chart_svg() wrapper (Continuum's/Herd's simpler two-series
    charts do -- see those games' own code)."""
    if len(emissions_history) < 2:
        return ""

    n = len(emissions_history)
    xs = comparison_chart.xs_for(n, TREND_GRAPH_WIDTH)
    # Normalized together (not each series against its own min/max) so
    # the player's emissions line and the global-reference line stay
    # comparable to each other on the same scale.
    emissions_ys, global_ys = comparison_chart.normalize_together(
        emissions_history, global_reference_history, TREND_GRAPH_HEIGHT
    )
    cost_ys = _normalize_series(cost_history, TREND_GRAPH_HEIGHT)

    emissions_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, emissions_ys))
    cost_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, cost_ys))
    global_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, global_ys))

    # C15: a small hoverable marker at every data point, each carrying a
    # native SVG <title> tooltip with that round's exact value. No JS
    # event wiring needed -- the browser's own hover-title behavior does
    # the work, consistent with this module keeping real logic in Python
    # rather than adding a parallel JS layer for something this simple.
    markers = (
        comparison_chart.marker_fragment(
            xs, global_ys, global_reference_history, "trend-point trend-point--global",
            "Global-average benchmark", index_label="Round", value_format="{:.0f}",
        )
        + comparison_chart.marker_fragment(
            xs, emissions_ys, emissions_history, "trend-point trend-point--emissions",
            "Your emissions", index_label="Round", value_format="{:.0f}",
        )
        + comparison_chart.marker_fragment(
            xs, cost_ys, cost_history, "trend-point trend-point--cost",
            "Avg renewable cost", index_label="Round", value_format="{:.0f}",
        )
    )

    # C12: a diamond marker (shape, not just color) on the emissions line at
    # the player's best round -- highest clean share, earliest on ties.
    best_marker = ""
    if clean_fraction_history and len(clean_fraction_history) == n and max(clean_fraction_history) > 0:
        best_i = clean_fraction_history.index(max(clean_fraction_history))
        bx, by = xs[best_i], emissions_ys[best_i]
        best_marker = (
            f'<polygon points="{bx:.1f},{by - 6:.1f} {bx + 5:.1f},{by:.1f} {bx:.1f},{by + 6:.1f} {bx - 5:.1f},{by:.1f}" '
            f'class="trend-best-marker"><title>Best round: Round {best_i + 1} '
            f"({clean_fraction_history[best_i] * 100:.0f}% clean)</title></polygon>"
        )

    return (
        f'<svg viewBox="0 0 {TREND_GRAPH_WIDTH} {TREND_GRAPH_HEIGHT}" class="trend-graph-svg">'
        f'<polyline points="{global_points}" class="trend-line trend-line--global" />'
        f'<polyline points="{emissions_points}" class="trend-line trend-line--emissions" />'
        f'<polyline points="{cost_points}" class="trend-line trend-line--cost" />'
        f"{markers}"
        f"{best_marker}"
        f"</svg>"
    )


def global_comparison_message(emissions, global_reference_emissions):
    """Z17: delegates its ahead/behind/tie branching to the shared
    shared/comparison_chart.py's comparison_message() -- this game's own
    wording is kept verbatim via the ahead_text/behind_text/tie_text
    overrides, so this is a pure refactor with no player-visible change."""
    return comparison_chart.comparison_message(
        emissions,
        global_reference_emissions,
        subject="grid's emissions",
        higher_is_better=False,
        ahead_text=(
            f"Your grid has emitted {emissions:.0f} vs. an estimated {global_reference_emissions:.0f} "
            "for a grid built to the global-average fossil mix — you're ahead of the curve."
        ),
        behind_text=(
            f"Your grid has emitted {emissions:.0f} vs. an estimated {global_reference_emissions:.0f} "
            "for a grid built to the global-average fossil mix — you're behind the curve."
        ),
        tie_text="Your grid is tracking almost exactly the global-average fossil mix so far.",
    )


def business_as_usual_message(emissions, bau_emissions):
    """C17: the closing counterfactual -- what this exact same installed
    capacity would have emitted had it all been built as coal, compared
    to what this grid actually emitted with its real fuel mix. Distinct
    from global_comparison_message() above: that one benchmarks against a
    real-world-ish average mix, this one isolates this player's own
    fuel-mix decisions specifically, holding how much got built constant."""
    if bau_emissions <= 0:
        return "Not enough rounds yet to compare against a business-as-usual grid."
    avoided = max(0.0, bau_emissions - emissions)
    if avoided <= 0:
        return (
            f"A business-as-usual grid built entirely from coal would have emitted "
            f"{bau_emissions:.0f} by now -- yours has emitted {emissions:.0f}, "
            "no better than staying all-coal so far."
        )
    pct_avoided = (avoided / bau_emissions) * 100
    return (
        f"A business-as-usual grid built entirely from coal would have emitted "
        f"{bau_emissions:.0f} by now. Yours has emitted {emissions:.0f} -- "
        f"{avoided:.0f} avoided ({pct_avoided:.0f}% less)."
    )


def disruption_risk_message(probability, severity):
    """Iteration Pass 3: makes the emissions-meter -> disruption-risk
    coupling explicit in words. The probability/severity math already
    scales directly off the emissions meter (Milestone 3) — this just
    makes sure the player can *read* that connection instead of only
    inferring it after the fact from event timing, so the meter reads as
    the actual mechanism gating success, not a side-score next to it."""
    if probability <= 0.0:
        return "No disruption risk yet — emissions are still at zero."
    pct = probability * 100
    if severity >= DAMAGE_SEVERITY_THRESHOLD:
        return (
            f"Rising emissions mean a {pct:.0f}% chance of a disruption next round — "
            "severe enough to damage a fossil plant if it hits."
        )
    return f"Rising emissions mean a {pct:.0f}% chance of a disruption next round."


def clean_trend_message(trend):
    if trend is None:
        return "Not enough rounds yet to show a trend."
    first_half_avg, second_half_avg = trend
    first_pct, second_pct = first_half_avg * 100, second_half_avg * 100
    if second_half_avg > first_half_avg:
        return f"Your grid is getting cleaner over time ({first_pct:.0f}% → {second_pct:.0f}%) — the transition is paying off."
    if second_half_avg < first_half_avg:
        return f"Your grid has gotten dirtier over time ({first_pct:.0f}% → {second_pct:.0f}%)."
    return f"Your grid's cleanliness has held steady at {second_pct:.0f}%."


# ===========================================================================
# Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md) — following SOL's reference
# integration (games/sol/game.py). Every achievement's earned status is a
# pure function of state that already exists elsewhere in this module,
# recomputed fresh every call — never a separately hand-maintained "earned"
# flag. Three exceptions needed genuinely new tracked state (declared on
# GridState above, mutated only where the real event happens: a successful
# maintain_plant() call, or a round advancing with/without a disruption
# event) — nothing else in this module records how many times Maintain has
# been used, or how long a streak of disruption-free rounds has run.
# ===========================================================================
ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    """Same loading contract as SOL's `_read_achievements_json()` / Le
    Champ de Mots' `_read_json_asset()`: the boot script fetches
    achievements.json and hands it to Python as a window global before this
    file runs; the pytest harness's fake `js` module has no such attribute,
    so this falls through to reading the file straight off disk, keeping
    the module importable outside a real browser."""
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        _js = None

    raw = getattr(_js, "ACHIEVEMENTS_JSON", None) if _js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 -- only needed on this filesystem-fallback path

    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, ACHIEVEMENTS_FILENAME), encoding="utf-8") as handle:
        return handle.read()


# Degrades to "no achievements catalog" rather than crashing this module's
# whole import — achievements are additive, not core to Grid's gameplay
# (same posture SOL/Le Champ de Mots take for their own optional assets).
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []

MAINTENANCE_ACHIEVEMENT_TARGET = 5
CLEAN_STREAK_TARGET = 15
NO_DAMAGE_ROUND_TARGET = 21
SCORE_50_MIN_ROUNDS = 10
SCORE_80_MIN_ROUNDS = 20
AHEAD_OF_CURVE_MIN_ROUND = 11
GRID_AT_SCALE_TARGET = 300


def renewable_capacity_share():
    """Renewables' share of total standing capacity, 0..1. Shared by the
    achievements below and (later) the one-time 50%-crossing callout."""
    total = state.total_capacity()
    if total == 0:
        return 0.0
    renewable_capacity = sum(state.plant_counts[t] * PLANT_CAPACITY[t] for t in RENEWABLE_TYPES)
    return renewable_capacity / total


def _standing_plant_type_count():
    return sum(1 for t in PLANT_TYPES if state.plant_counts[t] >= 1)


def _any_renewable_at_cost_floor():
    return any(
        state.plant_cost(t) <= PLANT_BASE_COST[t] * MIN_COST_MULTIPLIER * 1.0001
        for t in RENEWABLE_TYPES
    )


# Each checker is a zero-argument predicate read fresh off live state —
# nothing here is ever cached or hand-flagged.
ACHIEVEMENT_CHECKS = {
    "first_watt": lambda: sum(state.plant_counts.values()) >= 1,
    "renewable_pioneer": lambda: any(state.plant_counts[t] >= 1 for t in RENEWABLE_TYPES),
    "first_storage": lambda: state.cumulative_built["battery"] >= 1,
    "clean_quarter": lambda: renewable_capacity_share() >= 0.25,
    "clean_half": lambda: renewable_capacity_share() >= 0.5,
    "clean_three_quarters": lambda: renewable_capacity_share() >= 0.75,
    "fully_renewable": lambda: state.total_capacity() > 0 and state.fossil_share() == 0.0,
    "learning_curve_floored": _any_renewable_at_cost_floor,
    "diverse_grid": lambda: _standing_plant_type_count() >= len(PLANT_TYPES),
    "fossil_phase_out": lambda: (
        state.cumulative_built["coal"] + state.cumulative_built["gas"] >= 3
        and state.plant_counts["coal"] == 0
        and state.plant_counts["gas"] == 0
        and state.total_capacity() > 0
    ),
    "clean_streak_15": lambda: state.best_clean_streak >= CLEAN_STREAK_TARGET,
    "no_damage_20": lambda: (
        state.round_number >= NO_DAMAGE_ROUND_TARGET
        and not any(e.get("type") == "damage" for e in state.event_log)
    ),
    "score_50": lambda: state.score() >= 50 and len(state.clean_fraction_log) >= SCORE_50_MIN_ROUNDS,
    "score_80": lambda: state.score() >= 80 and len(state.clean_fraction_log) >= SCORE_80_MIN_ROUNDS,
    "well_maintained": lambda: state.maintenance_actions_count >= MAINTENANCE_ACHIEVEMENT_TARGET,
    "ahead_of_the_curve": lambda: (
        state.round_number >= AHEAD_OF_CURVE_MIN_ROUND
        and state.emissions < state.global_reference_emissions
    ),
    "grid_at_scale": lambda: state.total_capacity() >= GRID_AT_SCALE_TARGET,
}

# Progress readouts, only for achievements with a natural numeric scale-up
# — a plain earned/not-yet is the honest shape for a one-shot milestone
# like "retire every fossil plant you built".
ACHIEVEMENT_PROGRESS = {
    "clean_quarter": lambda: (min(100, round(renewable_capacity_share() * 100)), 25),
    "clean_half": lambda: (min(100, round(renewable_capacity_share() * 100)), 50),
    "clean_three_quarters": lambda: (min(100, round(renewable_capacity_share() * 100)), 75),
    "diverse_grid": lambda: (_standing_plant_type_count(), len(PLANT_TYPES)),
    "clean_streak_15": lambda: (min(state.best_clean_streak, CLEAN_STREAK_TARGET), CLEAN_STREAK_TARGET),
    "score_50": lambda: (min(100, round(state.score())), 50),
    "score_80": lambda: (min(100, round(state.score())), 80),
    "well_maintained": lambda: (
        min(state.maintenance_actions_count, MAINTENANCE_ACHIEVEMENT_TARGET),
        MAINTENANCE_ACHIEVEMENT_TARGET,
    ),
    "grid_at_scale": lambda: (min(state.total_capacity(), GRID_AT_SCALE_TARGET), GRID_AT_SCALE_TARGET),
}


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field (ACHIEVEMENTS-SYSTEM-DESIGN.md). Always
    recomputed, never itself a save input."""
    if sandbox_active:  # Z-18: nothing in the sandbox earns anything; the real game's list is shown as it was
        return list(_sandbox_real["earned"])
    banked = set(career["achievements"])
    return [entry["id"] for entry in ACHIEVEMENTS if entry["id"] in banked or ACHIEVEMENT_CHECKS[entry["id"]]()]


def achievements_summary():
    """The full catalog, in order, each entry annotated with whether it's
    currently earned and (where one exists) a live progress readout."""
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

# C5 -- a dedicated, player-triggered "Run Summary" panel: a score
# breakdown (score, average clean share, the clean-trend comparison) plus
# the existing funds-breakdown numbers restated in one place, closing
# with the C17 business-as-usual counterfactual. Not tied to any hard
# "game over" state (Grid has none, by design -- see CLAUDE.md's "No hard
# fail-state" note) -- it's a summary of the run *so far*, available at
# any point, the same "on-demand panel" shape as the achievements panel
# above rather than a one-time end screen. Deliberately not persisted
# across save/load, same as achievements_open -- purely a this-session
# display preference, not game state.
summary_panel_open = False


def on_toggle_summary_panel(event=None):
    global summary_panel_open
    summary_panel_open = not summary_panel_open
    update_summary_panel()


COMPARE_FALLBACK = "Comparison with other players isn't available yet."


def _request_comparison():
    """C15: asks the page's optional JS hook (window.gridCompare, see
    index.html) to fill #summary-compare with a cross-player percentile.
    Absent hook (pytest, or a page without it) leaves the fallback text."""
    if sandbox_active:  # Z-18: a practice grid is never compared with real players
        return
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "gridCompare", None)
    if hook is not None:
        hook(float(state.emissions), state.round_number)


def grade_message():
    """C5: operator-report letter grade vs. the real-world benchmark line."""
    grade = state.benchmark_grade()
    if grade is None:
        return "Operator grade: not graded yet -- play a round to get a benchmark to compare against."
    pct = state.emissions / state.global_reference_emissions * 100
    return (
        f"Operator grade: {grade} -- cumulative emissions are {pct:.0f}% of a "
        "global-average-mix grid's (A: under 20%, B: under 50%, C: under 80%, D: under 100%)."
    )


def projection_message(projection):
    """C25: the 'grid of the future' line."""
    shortfall = projection["demand"] - projection["capacity"]
    demand_note = (
        f"demand would reach {projection['demand']:.0f} against {projection['capacity']} capacity "
        f"({shortfall:.0f} short)"
        if shortfall > 0
        else f"capacity {projection['capacity']} would still cover demand of {projection['demand']:.0f}"
    )
    return (
        f"If you changed nothing for {projection['rounds']} more rounds: emissions would reach "
        f"{projection['emissions']:.0f} (all-coal would be {projection['bau_emissions']:.0f}), and {demand_note}."
    )


def copy_result_fields():
    """Z-20: the fields shared/copy-result.js turns into one pasteable line,
    e.g. "Grid, 62 clean-grid score, round 14, operator grade B, ...". Read by
    the page's own inline script through pyodide.globals when the shared Copy
    result button is pressed, so it always matches the run as it stands."""
    stats = [f"round {state.round_number}"]
    grade = state.benchmark_grade()
    if grade is not None:
        stats.append(f"operator grade {grade}")
    stats.append(f"{state.emissions_avoided():.0f} emissions avoided")
    stats.append(f"resilience {state.resilience_score()}/100")
    return {
        "game": "Grid (practice sandbox)" if sandbox_active else "Grid",
        "score": round(state.score()),
        "unit": "clean-grid score",
        "stats": stats,
    }


def summary_panel_html():
    """C5: the Run Summary panel's content -- pure read of existing
    state/score/funds-breakdown/C17-counterfactual math, no new
    calculations invented here beyond formatting."""
    avg_clean_pct = state.average_clean_fraction() * 100
    lines = [
        f"Round {state.round_number} — sustained clean-grid score: {state.score():.0f}/100",
        f"Average clean share across every round played: {avg_clean_pct:.0f}%",
        clean_trend_message(state.clean_trend()),
        (
            f"Funds so far — revenue: {state.lifetime_revenue:.0f}, spent building: "
            f"{state.lifetime_build_spend:.0f}, spent maintaining: "
            f"{state.lifetime_maintenance_spend:.0f}, lost to disruptions: "
            f"{state.lifetime_disruption_spend:.0f}."
        ),
        f"Best disruption-free streak so far: {state.best_clean_streak} round(s).",
        business_as_usual_message(state.emissions, state.bau_emissions),
        grade_message(),
        f"Grid resilience (diversification, separate from clean share): {state.resilience_score()}/100.",
        projection_message(state.projection()),
    ]
    body = "".join(f'<p class="status-line summary-line">{line}</p>' for line in lines)
    # C15: filled in by index.html's window.gridCompare() when the shared
    # stats endpoint (planning/TODO.md Z1) is reachable; otherwise this
    # fallback text simply stays.
    return body + f'<p id="summary-compare" class="status-line summary-line">{COMPARE_FALLBACK}</p>'


def update_summary_panel():
    toggle = document.getElementById("summary-toggle-button")
    panel = document.getElementById("summary-panel")
    toggle.innerText = "Hide Run Summary" if summary_panel_open else "📊 Run Summary"
    panel.hidden = not summary_panel_open
    if not summary_panel_open:
        return
    panel.innerHTML = summary_panel_html()
    _request_comparison()


# Unlock toast + hub-dashboard link (TODO.md "roll achievements out
# everywhere" — required on top of the base per-game rollout, per
# ACHIEVEMENTS-SYSTEM-DESIGN.md's site-wide goal). Same pattern as SOL's
# reference retrofit: a snapshot of which ids were already earned as of
# the last seed point, so a fresh load or a loaded save doesn't flood the
# player with toasts for achievements it already satisfies.
_achievements_seen_ids = set()


# ---- B-7 screen-reader announcements ------------------------------------------------------------
# What a sighted player sees change after an action is also said, in plain short sentences, through the shared
# announcer (shared/announcer.js) when the page has it, otherwise through the game's own #sr-announcer region.
# Only player actions and round results announce; render() never does (the shared announcer joins one tick's
# messages, so a build that also unlocks an achievement is read as one announcement).
def _shared_announce(text):
    """Speak through shared/announcer.js when the page has it (returns True); otherwise the game's own live
    region is used. Never both, so a screen reader does not read a message twice."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return False
    shared = getattr(window, "NoyvjAnnounce", None)
    if shared is None:
        return False
    try:
        shared.say(str(text))
    except Exception:  # noqa: BLE001 -- an announcement must never break the game
        return False
    return True


def announce(text):
    """Says text for a screen reader (shared announcer first, the game's own polite region otherwise)."""
    if not text:
        return
    if _shared_announce(text):
        return
    region = document.getElementById("sr-announcer")
    if region is not None:
        region.innerText = text


def _funds_phrase():
    return "Funds unlimited, sandbox" if sandbox_active else f"Funds {state.funds:.0f}"


def round_announcement_text(milestone_new=False):
    """What a player sees change after a round resolves, as short sentences built from the game's own readouts:
    the recap line, any disruption or breakdown, the new demand and capacity, the renewable and fossil shares,
    funds, and any policy lever or grant now on offer. Empty before the first round."""
    if state.last_round_recap is None:
        return ""
    summary, _details = round_recap_text()
    parts = [f"{summary}. Now round {state.round_number}"]
    if state.last_event is not None:
        parts.append(event_message(state.last_event))
    if state.last_aging_event is not None:
        plant_name = PLANT_LABEL[state.last_aging_event["plant"]]
        parts.append(
            f"Aging breakdown! A {plant_name} plant failed from wear "
            f"(repair cost {state.last_aging_event['repair_cost']:.0f})"
        )
    if state.last_round_recap.get("perfect"):
        parts.append("A Perfect Round: no disruption, no breakdown, demand fully met")
    parts.append(f"Demand is now {state.demand:g} against capacity {state.total_capacity():g}")
    parts.append(
        f"Renewables are {renewable_capacity_share() * 100:.0f}% of capacity, "
        f"fossil share {state.fossil_share() * 100:.0f}%"
    )
    parts.append(_funds_phrase())
    if state.policy_lever_available:
        parts.append("A policy lever is on offer")
    if state.grant_offer is not None:
        info = GRANTS[state.grant_offer["id"]]
        parts.append(f"Offer: {info['title']}. {info['text']}")
    if milestone_new:
        parts.append("More than half your grid's capacity is now renewable")
    return ". ".join(p.rstrip(". ") for p in parts if p) + "."


def _seed_achievement_toast_baseline():
    global _achievements_seen_ids
    _achievements_seen_ids = set(achievement_ids_earned())
    _story_reach_all(_achievements_seen_ids)  # W1: a loaded save's earned chapters come back too


def _display_achievement_toast(message):
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


def _story_reach_all(earned_ids):
    """W1: unlocks the story chapter for every earned achievement (and the
    opening one) via the shared story-chapters.js. Idempotent and silent: no
    story script, or a chapter id it does not know, simply does nothing."""
    if sandbox_active:  # Z-18: chapters belong to the real game
        return
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    story = getattr(window, "NoyvjStory", None)
    if story is None:
        return
    story.reach("begin")
    for achievement_id in sorted(earned_ids):
        story.reach(achievement_id)


def _check_new_achievements_for_toast():
    """Called after every player action that could change earned status
    (build/retire/maintain/advance round) — never from render() itself,
    since load_state() also calls render() and a loaded save with several
    achievements already earned must not flood the player with toasts for
    all of them at once (see _seed_achievement_toast_baseline)."""
    global _achievements_seen_ids
    if sandbox_active:  # Z-18: no toasts, no new chapters
        return
    earned_now = set(achievement_ids_earned())
    _story_reach_all(earned_now)
    newly = earned_now - _achievements_seen_ids
    if newly:
        by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
        labels = [by_id[aid]["label"] for aid in newly if aid in by_id]
        if labels:
            if len(labels) == 1:
                _display_achievement_toast(f"🏆 Achievement unlocked: {labels[0]}")
                announce(f"Achievement unlocked: {labels[0]}")
            else:
                _display_achievement_toast(f"🏆 {len(labels)} achievements unlocked: " + ", ".join(labels))
                announce(f"{len(labels)} achievements unlocked: " + ", ".join(labels))
    _achievements_seen_ids = earned_now


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

    # A link out to the hub-wide achievements dashboard (root index.html's
    # #account-achievements-dashboard, ACHIEVEMENTS-SYSTEM-DESIGN.md §5),
    # same convention as SOL's reference retrofit. Relative path, no
    # leading "/" (site-level milestone 7's GitHub Pages subpath fix).
    # Rebuilt each open alongside the cards since the panel is cleared
    # first. Note: the hub-side script.js registration that makes Grid's
    # save data actually show up on that dashboard is a root-file change,
    # out of scope for this games/grid/-only dispatch — see CLAUDE.md.
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
    fails-soft shape as this file's own C15 window.gridCompare."""
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
# Same static-JSON-asset loading contract as ACHIEVEMENTS above (and SOL's
# reference integration): the boot script fetches changelog.json and hands
# it to Python as a window global before this module runs; the pytest
# harness's fake `js` has no such attribute, so this falls through to
# reading the file straight off disk. A flat, hand-written list of
# highlights pulled from this game's own CLAUDE.md milestone table and
# build notes — not a full duplicate of the dev logs, just a quick
# "what's new" view.
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        _js = None

    raw = getattr(_js, "CHANGELOG_JSON", None) if _js is not None else None
    if raw is not None:
        return str(raw)

    import os  # noqa: PLC0415 -- only needed on this filesystem-fallback path

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
    note_text = load_report_text()
    if note_text:
        note = document.createElement("p")
        note.className = "changelog-load-note"
        note.innerText = note_text
        panel.appendChild(note)
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


# TODO-C17 -- weather-event log panel, same hidden-until-opened .section
# idiom as the changelog panel just above.
weather_log_open = False


def on_toggle_weather_log(event=None):
    global weather_log_open
    weather_log_open = not weather_log_open
    update_weather_log_display()


def update_weather_log_display():
    toggle = document.getElementById("weather-log-toggle-button")
    panel = document.getElementById("weather-log-panel")
    toggle.innerText = "Hide Weather Log" if weather_log_open else "🌦️ Weather Log"
    panel.hidden = not weather_log_open
    if not weather_log_open:
        return

    panel.innerHTML = ""
    if not state.weather_log:
        empty = document.createElement("p")
        empty.className = "weather-log-empty"
        empty.innerText = (
            "No weather-variability effects recorded yet -- turn on Weather Variability "
            "above and advance a round with renewables built to see entries here."
        )
        panel.appendChild(empty)
        return

    # Newest first, matching the achievements/changelog panels' convention.
    for message in reversed(state.weather_log):
        row = document.createElement("p")
        row.className = "weather-log-entry"
        row.innerText = message
        panel.appendChild(row)


# Rendering/toggle logic lives in shared/info_page.py now (see that
# module's docstring) -- this used to be a ~25+4 line implementation
# byte-identical across all 8 climate games. info_page_open stays local
# here since it's part of this game's save contract.
def render_info_page():
    info_page.render(INFO_PAGE, info_page_open)


def on_toggle_info_page(event=None):
    global info_page_open
    info_page_open = info_page.toggle(info_page_open)
    render_info_page()


def demand_growth_arrow():
    """C20 (extended by TODO-C7): demand's per-round growth against the
    standard pace -- up when net growth is faster than standard, flat
    when unchanged, and (new) down once demand-response investment has
    pulled net growth below standard, regardless of the Steeper Demand
    Growth toggle."""
    growth = state.demand_growth_this_round()
    if growth > DEMAND_GROWTH_PER_ROUND:
        return "\u25B2"
    if growth < DEMAND_GROWTH_PER_ROUND:
        return "\u25BC"
    return "\u25AC"


def demand_growth_title():
    growth = state.demand_growth_this_round()
    if state.demand_response_level > 0:
        baseline = DEMAND_GROWTH_PER_ROUND * (
            STEEP_DEMAND_GROWTH_MULTIPLIER if state.steeper_demand_growth_enabled else 1
        )
        return (
            f"Demand is rising +{growth:.1f} per round -- demand-response investment "
            f"(level {state.demand_response_level}) has trimmed it down from the "
            f"otherwise-{baseline:.0f}-per-round pace."
        )
    if state.steeper_demand_growth_enabled:
        return f"Demand is rising +{growth:.0f} per round -- faster than the standard +{DEMAND_GROWTH_PER_ROUND} (Steeper Demand Growth is on)."
    return f"Demand is rising at the standard +{DEMAND_GROWTH_PER_ROUND} per round."


def wear_tooltip(plant_type):
    """C4: what the wear percentage means numerically."""
    age = state.plant_age[plant_type]
    return (
        f"Average fleet age {age:.1f} rounds. Wear % = age / {WEAR_PERCENT_REFERENCE_AGE} rounds (100% is the "
        f"top wear tier). Breakdown risk starts past {AGE_GRACE_PERIOD} rounds: +{AGE_BREAKDOWN_RATE * 100:.0f}% "
        f"per extra round, capped at {MAX_AGE_BREAKDOWN_PROBABILITY * 100:.0f}%. Maintain takes "
        f"{MAINTENANCE_AGE_REDUCTION} rounds off the average age."
    )


def render():
    render_info_page()
    render_shadow()
    render_real_grid()
    render_regional_grid()
    update_achievements_display()
    update_changelog_display()
    update_weather_log_display()
    update_summary_panel()
    document.getElementById("round-display").innerText = f"Round {state.round_number}"
    demand_el = document.getElementById("demand-display")
    demand_el.innerText = f"Demand: {state.demand} {demand_growth_arrow()}"
    demand_el.title = demand_growth_title()
    document.getElementById("streak-display").innerText = (
        f"Clean streak: {state.current_clean_streak} round(s) without a disruption "
        f"(best {state.best_clean_streak})"
    )
    document.getElementById("funds-display").innerText = (
        "Funds: unlimited (sandbox)" if sandbox_active else f"Funds: {state.funds:.0f}"
    )
    document.getElementById("capacity-display").innerText = f"Capacity: {state.total_capacity()}"
    document.getElementById("emissions-display").innerText = f"Emissions: {state.emissions:.0f}"
    document.getElementById("fossil-share-display").innerText = (
        f"Fossil share of grid: {state.fossil_share() * 100:.0f}%"
    )
    event_el = document.getElementById("event-display")
    event_el.innerText = event_message(state.last_event)
    event_el.className = event_severity_class(state.last_event)

    document.getElementById("score-display").innerText = f"Sustained clean-grid score: {state.score():.0f}"
    document.getElementById("trend-display").innerText = clean_trend_message(state.clean_trend())

    emissions_fraction = min(1.0, state.emissions / EMISSIONS_METER_MAX)
    document.getElementById("emissions-bar").style.width = f"{emissions_fraction * 100:.0f}%"
    document.getElementById("score-bar").style.width = f"{state.score():.0f}%"
    document.getElementById("disruption-risk-display").innerText = disruption_risk_message(
        state.disruption_probability(), state.disruption_severity()
    )

    # C16: opt-in difficulty toggle -- purely reflects the current setting,
    # never touches disruption math (see STEEP_DEMAND_GROWTH_MULTIPLIER's
    # comment above).
    steep_button = document.getElementById("steeper-demand-toggle-button")
    steep_button.innerText = (
        f"🔥 Steeper Demand Growth (x{STEEP_DEMAND_GROWTH_MULTIPLIER:g}): ON"
        if state.steeper_demand_growth_enabled
        else f"Steeper Demand Growth (x{STEEP_DEMAND_GROWTH_MULTIPLIER:g}): OFF"
    )
    if state.steeper_demand_growth_enabled:
        steep_button.classList.add("active")
    else:
        steep_button.classList.remove("active")

    weather_button = document.getElementById("weather-variability-toggle-button")
    weather_button.innerText = (
        "🌩️ Weather Variability: ON" if state.weather_variability_enabled else "Weather Variability: OFF"
    )
    if state.weather_variability_enabled:
        weather_button.classList.add("active")
    else:
        weather_button.classList.remove("active")

    svg = trend_graph_svg(
        state.emissions_history,
        state.avg_renewable_cost_history,
        state.global_reference_emissions_history,
        state.clean_fraction_log,
    )
    document.getElementById("trend-graph").innerHTML = svg
    document.getElementById("trend-graph-message").innerText = (
        "Your emissions (red) vs. a global-average-fossil-mix benchmark (dashed grey) vs. average renewable cost (green) over time."
        if svg else "Not enough rounds yet to show an emissions/cost trend."
    )
    document.getElementById("global-comparison-message").innerText = global_comparison_message(
        state.emissions, state.global_reference_emissions
    )

    blurb_el = document.getElementById("renewable-blurb")
    blurb_el.innerText = RENEWABLE_UNLOCK_BLURB
    blurb_el.hidden = not state.renewable_unlocked

    aging_el = document.getElementById("aging-event-display")
    if state.last_aging_event is None:
        aging_el.innerText = "No aging breakdowns last round."
        aging_el.className = "event-display"
    else:
        plant_name = PLANT_LABEL[state.last_aging_event["plant"]]
        cost = state.last_aging_event["repair_cost"]
        aging_el.innerText = f"Aging breakdown! A {plant_name} plant failed from wear (repair cost {cost:.0f})."
        aging_el.className = "event-display event-display--danger"

    # C13: a funds breakdown across the run so far, for transparency --
    # pure additive read of the lifetime_* totals above, no change to any
    # actual cost/refund math itself.
    document.getElementById("funds-breakdown-revenue").innerText = f"{state.lifetime_revenue:.0f}"
    document.getElementById("funds-breakdown-build").innerText = f"{state.lifetime_build_spend:.0f}"
    document.getElementById("funds-breakdown-maintenance").innerText = f"{state.lifetime_maintenance_spend:.0f}"
    document.getElementById("funds-breakdown-disruption").innerText = f"{state.lifetime_disruption_spend:.0f}"

    funds_values = {
        "revenue": state.lifetime_revenue,
        "build": state.lifetime_build_spend,
        "maintenance": state.lifetime_maintenance_spend,
        "disruption": state.lifetime_disruption_spend,
    }
    funds_max = max(funds_values.values()) or 1.0
    for key, value in funds_values.items():
        document.getElementById(f"funds-bar-{key}").style.width = f"{value / funds_max * 100:.0f}%"

    scenario_button = document.getElementById("scenario-toggle-button")
    scenario_button.innerText = f"Scenario: {SCENARIOS[state.scenario]['label']}"
    scenario_locked = (state.round_number != 1 or any(state.cumulative_built.values())) and not sandbox_active
    scenario_button.disabled = scenario_locked
    scenario_button.title = (
        "Starting scenario -- locked once you build anything or advance a round."
        if scenario_locked
        else (
            "Sandbox: click to cycle the scenario and start the practice grid over."
            if sandbox_active
            else "Click to cycle the starting scenario (only available before your first build or round)."
        )
    )

    document.getElementById("renewable-milestone-callout").hidden = not renewable_milestone_visible
    document.getElementById("retire-callout").hidden = not retire_callout_visible
    document.getElementById("maintain-callout").hidden = not maintain_callout_visible

    # TODO-C7: demand-response lever -- a fourth build/retire/maintain-
    # style action, but acting on demand growth instead of the fleet.
    dr_cost = state.demand_response_cost()
    dr_button = document.getElementById("demand-response-button")
    dr_button.innerText = f"Invest in Demand Response ({dr_cost:.0f})"
    dr_button.disabled = state.funds < dr_cost
    dr_button.title = (
        f"Permanently trims demand growth by {DEMAND_RESPONSE_REDUCTION_PER_LEVEL:g}/round "
        f"(floor {DEMAND_RESPONSE_MIN_GROWTH:g}/round). Each purchase costs more than the last."
    )
    document.getElementById("demand-response-level-display").innerText = (
        f"Demand response level: {state.demand_response_level}"
        if state.demand_response_level > 0
        else "Demand response: not yet invested"
    )

    # TODO-C19: policy lever -- offered periodically, opt-in.
    policy_banner = document.getElementById("policy-lever-banner")
    policy_banner.hidden = not state.policy_lever_available
    active_policy_el = document.getElementById("active-policy-display")
    if state.active_policy is None:
        active_policy_el.innerText = ""
        active_policy_el.hidden = True
    else:
        active_policy_el.hidden = False
        label = (
            "Carbon Pricing" if state.active_policy["type"] == "carbon_pricing" else "Renewable Subsidy"
        )
        effect = (
            f"fossil build costs +{(CARBON_PRICING_FOSSIL_COST_MULTIPLIER - 1) * 100:.0f}%"
            if state.active_policy["type"] == "carbon_pricing"
            else f"renewable build costs -{(1 - RENEWABLE_SUBSIDY_COST_MULTIPLIER) * 100:.0f}%"
        )
        active_policy_el.innerText = (
            f"Active policy: {label} -- {effect} ({state.active_policy['rounds_remaining']} round(s) left)."
        )

    _render_arbitrage_and_emergency()
    render_auto_advance()
    render_round_recap()
    render_difficulty_preset()
    render_run_setup_and_extras()
    update_career_panel()

    for plant_type in PLANT_TYPES:
        count = state.plant_counts[plant_type]
        cost = state.plant_cost(plant_type)
        document.getElementById(f"{plant_type}-count").innerText = str(count)
        name_el = document.getElementById(f"{plant_type}-name")
        name_el.innerText = f"{PLANT_ICON[plant_type]} {PLANT_LABEL[plant_type]}"
        for _, wear_css_class in AGE_WEAR_THRESHOLDS:
            name_el.classList.remove(wear_css_class)
        wear_css_class = state.wear_class(plant_type)
        if wear_css_class:
            name_el.classList.add(wear_css_class)

        # C10: the exact wear percentage next to the coarse wear-icon
        # state -- only meaningful once a unit is actually standing.
        wear_pct_el = document.getElementById(f"{plant_type}-wear-pct")
        wear_pct_el.innerText = (
            f"{WEAR_TIER_GLYPH[wear_css_class]} {state.wear_percent(plant_type)}% worn" if count > 0 else ""
        )
        wear_pct_el.title = wear_tooltip(plant_type) if count > 0 else ""

        # C19: a breakdown-risk badge once this type's own average age
        # has crossed the risk threshold, independent of whether it's
        # currently *the* oldest type (the one actually at risk this
        # round -- see breakdown_risk_probability()'s docstring).
        risk_badge = document.getElementById(f"{plant_type}-risk-badge")
        risk_probability = state.breakdown_risk_probability(plant_type) if count > 0 else 0.0
        risk_badge.hidden = risk_probability <= 0.0
        if not risk_badge.hidden:
            risk_badge.innerText = f"⚠ Aging risk ({risk_probability * 100:.0f}%)"

        build_button = document.getElementById(f"{plant_type}-build-button")
        build_button.innerText = f"Build ({cost:.0f})"
        build_button.disabled = state.funds < cost

        retire_button = document.getElementById(f"{plant_type}-retire-button")
        retire_button.disabled = count <= 0

        maintenance_cost = state.maintenance_cost(plant_type)
        maintain_button = document.getElementById(f"{plant_type}-maintain-button")
        maintain_button.innerText = f"Maintain ({maintenance_cost:.0f})"
        maintain_button.disabled = count <= 0 or state.funds < maintenance_cost

        # TODO-C23: keep the select's own displayed value in sync with
        # state (e.g. after a load_state() or a grid-size reset), same
        # reasoning as the difficulty/grid-size <select>s elsewhere in
        # this file -- disabled whenever there's no plant of this type to
        # schedule anything for, same gating as Maintain itself.
        schedule_select = document.getElementById(f"{plant_type}-maintenance-schedule-select")
        schedule_select.value = str(state.maintenance_schedule[plant_type])
        schedule_select.disabled = count <= 0

    # C7: plant-mix bar chart -- composition of *generation* capacity by
    # type. Battery has no row here (see GENERATION_TYPES' comment) --
    # it's storage, not part of "what's generating," so it has no
    # meaningful share of a generation-mix chart.
    for plant_type in GENERATION_TYPES:
        mix_pct = state.capacity_share(plant_type) * 100
        document.getElementById(f"{plant_type}-mix-bar").style.width = f"{mix_pct:.0f}%"
        document.getElementById(f"{plant_type}-mix-pct").innerText = f"{mix_pct:.0f}%"


career_open = False


def _start_new_run():
    """C1: replace the live GridState with a fresh one carrying the
    career's unlocked perks (seed capital is applied via the standard
    scenario so it uses the same funds path as every other start)."""
    global state, renewable_milestone_visible, retire_callout_visible, maintain_callout_visible
    state = GridState()
    _sync_perks()
    state.start_option = career["loadout"]
    state.apply_scenario("standard")
    renewable_milestone_visible = False
    retire_callout_visible = False
    maintain_callout_visible = False
    _seed_achievement_toast_baseline()


def career_panel_lines():
    """Plain-text lines for the Career panel's stat blocks."""
    best = career["best_grade"] or "none yet"
    stats = (
        f"Runs finished: {career['runs']}. Best sustained clean score: {career['best_score']:.0f}/100. "
        f"Best operator grade: {best}. Career points: {career_points_available()} to spend "
        f"({career['points']} earned in total)."
    )
    points, parts = run_career_points()
    if points > 0:
        preview = f"Finishing this run now would bank {points} point(s): " + ", ".join(parts) + "."
    else:
        preview = parts[0]
    return stats, preview


def career_perk_progress_text(perk_id):
    """C-2: what a perk button says about its price -- the numeric effect,
    and for a locked perk how many points away it is (or that it can be
    bought now)."""
    info = CAREER_UNLOCKS[perk_id]
    if perk_id in career["unlocked"]:
        return f"Unlocked: {info['label']} ({info['effect']}) -- {info['description']}"
    missing = skill_tree.missing_requirements(CAREER_TREE, career["unlocked"], perk_id)
    if missing:
        names = ", ".join(CAREER_UNLOCKS[m]["label"] for m in missing)
        return f"{info['label']} ({info['cost']} pts, needs {names} first): {info['effect']} -- {info['description']}"
    gap = info["cost"] - career_points_available()
    status = "ready to unlock" if gap <= 0 else f"{gap} more point(s) needed"
    return f"{info['label']} ({info['cost']} pts, {status}): {info['effect']} -- {info['description']}"


def career_next_perk_text():
    """C-2: one line naming the cheapest perk still locked and its gap."""
    locked = [
        u for u in CAREER_UNLOCK_ORDER
        if u not in career["unlocked"] and not skill_tree.missing_requirements(CAREER_TREE, career["unlocked"], u)
    ]
    if not locked:
        if all(u in career["unlocked"] for u in CAREER_UNLOCK_ORDER):
            return "Every career upgrade is unlocked."
        return "Next upgrades need an earlier node in their branch first."
    perk_id = min(locked, key=lambda u: CAREER_UNLOCKS[u]["cost"])
    info = CAREER_UNLOCKS[perk_id]
    gap = info["cost"] - career_points_available()
    if gap <= 0:
        return f"Next perk: {info['label']} ({info['effect']}) -- you can unlock it now."
    return f"Next perk: {info['label']} ({info['effect']}) -- {gap} point(s) away."


def career_records_text():
    """GC-26: the career's personal records, spelled out in words."""
    r90 = career["best_rounds_to_90"]
    return (
        f"Records: best clean score {career['best_score']:.0f}/100, best grade {career['best_grade'] or 'none yet'}, "
        f"fewest rounds to 90% clean {r90 if r90 is not None else 'not reached yet'}, "
        f"longest disruption-free streak {career['best_streak']} round(s)."
    )


# C-1: the six line styles of the stacked run-comparison charts. Colour is
# never the only cue -- style.css gives each slot its own dash pattern too,
# and the legend repeats each run's line.
RUN_CHART_WIDTH = 280
RUN_CHART_HEIGHT = 64


def _run_label(history, index):
    return f"Run {max(0, career['runs'] - len(history)) + index + 1}"


def career_history_charts_html(history):
    """C-1: three stacked small charts (clean share, funds, demand) with one
    line per run, the six most recent runs, each plotted from its own start
    to its own end so runs of different length stay comparable. Returns ""
    until at least one run has a usable series."""
    runs = [(i, r) for i, r in enumerate(history) if len(r["clean"]) >= 2][-CAREER_CHART_RUNS:]
    if not runs:
        return ""
    charts = [
        ("Clean share of capacity (%)", "clean", 0, 100),
        ("Funds", "funds_series", None, None),
        ("Demand", "demand_series", None, None),
    ]
    out = []
    for title, key, fixed_lo, fixed_hi in charts:
        series = [(i, r[key]) for i, r in runs if len(r[key]) >= 2]
        if not series:
            continue
        lo = fixed_lo if fixed_lo is not None else min(min(v) for _, v in series)
        hi = fixed_hi if fixed_hi is not None else max(max(v) for _, v in series)
        if hi <= lo:
            hi = lo + 1
        lines = []
        for slot, (i, values) in enumerate(series):
            n = len(values)
            points = " ".join(
                f"{j / (n - 1) * RUN_CHART_WIDTH:.1f},{RUN_CHART_HEIGHT - (v - lo) / (hi - lo) * RUN_CHART_HEIGHT:.1f}"
                for j, v in enumerate(values)
            )
            latest = " run-line--latest" if slot == len(series) - 1 else ""
            lines.append(
                f'<polyline points="{points}" class="run-line run-line--{slot}{latest}">'
                f"<title>{_run_label(history, i)}: {values[0]} to {values[-1]}</title></polyline>"
            )
        out.append(
            f'<div class="run-chart"><p class="meter-label">{title} ({lo} to {hi})</p>'
            f'<svg viewBox="0 0 {RUN_CHART_WIDTH} {RUN_CHART_HEIGHT}" class="run-chart-svg" role="img" '
            f'aria-label="{title}, one line per run, start to end of each run">{"".join(lines)}</svg></div>'
        )
    legend = []
    for slot, (i, r) in enumerate(runs):
        legend.append(
            f'<span class="run-legend-item"><svg class="run-legend-swatch" viewBox="0 0 24 6" aria-hidden="true">'
            f'<line x1="0" y1="3" x2="24" y2="3" class="run-line run-line--{slot}" /></svg>'
            f"{_run_label(history, i)} ({r['grade']}, {r['score']:.0f}/100)</span>"
        )
    return "".join(out) + f'<div class="run-legend">{"".join(legend)}</div>'


def career_heatmap_html(history):
    """C-7: clean-share-by-round heatmap, one row per saved run, one cell per
    saved point. A single hue whose strength is the clean share, with the
    exact figure in each cell's tooltip (not colour alone)."""
    rows = []
    for i, r in enumerate(history):
        if not r["clean"]:
            continue
        cells = "".join(
            f'<span class="heat-cell" style="opacity:{0.08 + 0.92 * v / 100:.2f}" '
            f'title="{_run_label(history, i)}, point {j + 1} of {len(r["clean"])}: {v}% clean"></span>'
            for j, v in enumerate(r["clean"])
        )
        rows.append(f'<div class="heat-row"><span class="heat-label">{_run_label(history, i)}</span>'
                    f'<span class="heat-cells">{cells}</span></div>')
    return "".join(rows)


def _grade_from_average(points):
    return "ABCDF"[4 - max(0, min(4, int(round(points))))]


def career_lifetime_lines():
    """C-7: lifetime statistics, in words, from the career's uncapped totals."""
    life = career["lifetime"]
    if career["runs"] <= 0:
        return ["No finished runs yet. Finish a run to start your lifetime statistics."]
    lines = [f"Rounds played across {career['runs']} finished run(s): {life['rounds']}."]
    grades = []
    for scenario in SCENARIO_ORDER:
        entry = life["scenario_grades"].get(scenario)
        if entry:
            letter = _grade_from_average(entry["points"] / entry["n"])
            grades.append(f"{SCENARIOS[scenario]['label']} {letter} ({entry['n']} run(s))")
    lines.append("Average grade per scenario: " + (", ".join(grades) if grades else "none yet") + ".")
    built = life["built"]
    top = max(PLANT_TYPES, key=lambda t: built[t])
    lines.append(
        f"Most-built plant: {PLANT_LABEL[top]} ({built[top]} built)." if built[top] > 0 else "Most-built plant: none yet."
    )
    lines.append(
        f"Disruptions by cause: {life['brownouts']} brownout(s) from emissions, {life['damages']} plant(s) knocked "
        f"offline by emissions, {life['aging']} aging breakdown(s)."
    )
    return lines


def career_history_rows(history):
    """C-1: one plain-text line per saved run, newest first."""
    rows = []
    for i in range(len(history) - 1, -1, -1):
        r = history[i]
        r90 = f", 90% clean by round {r['r90']}" if r["r90"] is not None else ""
        rows.append(
            f"{_run_label(history, i)}: {SCENARIOS[r['scenario']]['label']}, grade {r['grade']}, "
            f"clean score {r['score']:.0f}/100, {r['rounds']} rounds, {r['points']} pt(s) banked, "
            f"final funds {r['funds']}, emissions {r['emissions']}, resilience {r['resilience']}, "
            f"best streak {r['streak']}{r90}."
            + (f" Seed {r['seed']}." if r.get("seed") else "")
            + (" Ironman." if r.get("ironman") else "")
        )
    return rows


def _copy_to_clipboard(text):
    """C-16: best effort -- a browser may refuse (insecure page, no focus),
    in which case the text box is the fallback."""
    try:
        import js  # noqa: PLC0415 -- Pyodide-only, deliberately lazy

        clipboard = getattr(getattr(js, "navigator", None), "clipboard", None)
        if clipboard is None:
            return False
        clipboard.writeText(text)
        return True
    except Exception:  # noqa: BLE001
        return False


career_data_message = ""


def export_career_to_field():
    """C-16: puts the career JSON in the text box (and on the clipboard when
    allowed). Returns the text."""
    global career_data_message
    text = json.dumps(career)
    document.getElementById("career-data-field").value = text
    copied = _copy_to_clipboard(text)
    career_data_message = (
        "Career data copied to the clipboard and shown in the box." if copied
        else "Career data is in the box below. Select it and copy it to keep a backup."
    )
    return text


def import_career_from_text(text):
    """C-16: replace the career with pasted JSON. Anything that is not a Grid
    career is refused with a message, and nothing changes."""
    global career, career_data_message
    if sandbox_active:
        career_data_message = "Career backups are switched off in the sandbox."
        return False
    try:
        raw = json.loads(text)
    except (ValueError, TypeError):
        career_data_message = "That is not valid career data, so nothing was changed."
        return False
    if not isinstance(raw, dict) or not any(k in raw for k in ("runs", "points", "history", "unlocked")):
        career_data_message = "That does not look like Grid career data, so nothing was changed."
        return False
    career = validate_career(raw)
    _sync_perks()
    save_career_to_storage()
    career_data_message = f"Career restored: {career['runs']} run(s), {career['points']} point(s) earned."
    return True


def reset_career():
    """C-16: wipe the whole career (points, perks, records, history,
    banked achievements) and return to a fresh start."""
    global career, last_finish_records, career_data_message
    if sandbox_active:
        career_data_message = "The career cannot be reset from the sandbox."
        return
    career = _default_career()
    last_finish_records = []
    _sync_perks()
    save_career_to_storage()
    career_data_message = "Career reset. A copy of the old data stays in the box until you reload the page."


def update_career_panel():
    toggle = document.getElementById("career-toggle-button")
    panel = document.getElementById("career-panel")
    toggle.innerText = "Hide Career" if career_open else f"🎖️ Career ({career_points_available()} pts)"
    panel.hidden = not career_open
    if not career_open:
        return
    stats, preview = career_panel_lines()
    document.getElementById("career-stats-display").innerText = stats
    document.getElementById("career-preview-display").innerText = preview
    document.getElementById("career-records-display").innerText = career_records_text()
    flash = document.getElementById("career-record-flash")
    flash.hidden = not last_finish_records
    flash.innerText = ("New record! " + "; ".join(last_finish_records) + ".") if last_finish_records else ""
    document.getElementById("career-next-perk-display").innerText = career_next_perk_text()
    finish = document.getElementById("career-finish-button")
    finish.disabled = sandbox_active or state.round_number - 1 < CAREER_MIN_ROUNDS
    document.getElementById("career-tree-summary").innerText = career_tree_summary_text()
    _render_career_tree()

    history = career["history"]
    list_el = document.getElementById("career-history-list")
    list_el.innerHTML = ""
    rows = career_history_rows(history)
    if not rows:
        empty = document.createElement("p")
        empty.className = "comparison-message"
        empty.innerText = "No finished runs yet. Finish a run and it is filed here."
        list_el.appendChild(empty)
    for row_text in rows:
        row = document.createElement("p")
        row.className = "career-history-row"
        row.innerText = row_text
        list_el.appendChild(row)
    document.getElementById("career-history-chart").innerHTML = career_history_charts_html(history)
    document.getElementById("career-lifetime-display").innerText = "\n".join(career_lifetime_lines())
    document.getElementById("career-heatmap").innerHTML = career_heatmap_html(history)
    render_career_whatif(history)
    document.getElementById("career-data-status").innerText = career_data_message


def on_toggle_career(event=None):
    global career_open
    career_open = not career_open
    render()


def on_finish_run(event=None):
    def do_finish():
        finish_run()
        render()

    if sandbox_active or state.round_number - 1 < CAREER_MIN_ROUNDS:
        return
    points, _ = run_career_points()
    _confirm_dialog_ask(
        action_id="grid-finish-run",
        message=(
            f"Finish this run and bank {points} career point(s)? "
            "Your grid resets to a fresh start; career points, unlocked perks and earned achievements stay."
        ),
        confirm_label="Finish run",
        on_confirm=do_finish,
    )


# --- GC-2b / GC-1 / GC-11: the upgrade tree's view --------------------------------------------------------
_career_view = None
_career_proxies = []


def _js_window():
    try:
        import js  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return None
    return getattr(js, "window", None)


def _to_js(value):
    try:
        from js import Object  # noqa: PLC0415
        from pyodide.ffi import to_js  # noqa: PLC0415
    except ImportError:
        return None
    return to_js(value, dict_converter=Object.fromEntries)


def _on_tree_buy(node_id, node=None):
    unlock_career_perk(str(node_id))
    render()


def _render_career_tree():
    """Draws (or updates) the shared skill-tree widget into #career-tree. Without the script (the
    tests, or a failed load) the tree is simply not drawn; the plain-text summary above it stays."""
    global _career_view
    window = _js_window()
    widget = getattr(window, "NoyvjSkillTree", None) if window is not None else None
    container = document.getElementById("career-tree")
    if widget is None or container is None:
        return
    if _career_view is None:
        if not _career_proxies:
            _career_proxies.append(create_proxy(_on_tree_buy))
        options = _to_js({
            "tree": CAREER_TREE, "owned": list(career["unlocked"]), "earned": career["points"],
            "refundNodes": False, "onBuy": _career_proxies[0],
        })
        if options is not None:
            _career_view = widget.render(container, options)
        return
    update = _to_js({"owned": list(career["unlocked"]), "earned": career["points"]})
    if update is not None:
        _career_view.update(update)


def career_tree_summary_text():
    totals = skill_tree.totals(CAREER_TREE, career["unlocked"], career["points"])
    return (
        f"{career_points_available()} career points to spend ({career['points']} earned in all). "
        f"{totals['owned_count']} of {totals['node_count']} upgrades owned. "
        "Upgrades are permanent and apply to your next run (a run you have not started picks them up at once)."
    )


# --- run setup: starting loadout, run seed, Ironman -------------------------------------------------------
run_setup_message = ""
START_OPTION_NONE = "none"


def on_start_option_change(event=None):
    global run_setup_message
    value = document.getElementById("start-option-select").value
    option = None if value in (START_OPTION_NONE, "", None) else value
    if set_loadout(option):
        run_setup_message = ""
    else:
        run_setup_message = "That loadout is not available."
    render()


def on_apply_run_seed(event=None):
    global run_setup_message
    text = document.getElementById("run-seed-input").value or ""
    result = seed_lib.validate(text, SEED_GAME)
    if not result["ok"]:
        run_setup_message = result["message"]
    elif not state.set_seed(result["seed"]):
        run_setup_message = "The seed can only be changed before you build or advance a round."
    else:
        run_setup_message = f"Seed {state.seed} set."
    render()


def on_toggle_ironman(event=None):
    global run_setup_message
    if state.set_ironman(not state.ironman):
        run_setup_message = (
            "Ironman on: no undo, every action is final." if state.ironman else "Ironman off."
        )
    else:
        run_setup_message = "Ironman can only be switched before you build or advance a round."
    render()


def on_undo_build(event=None):
    if state.can_undo_build():
        record = state.undo_record
        last = shadow_actions[-1] if shadow_actions else None
        if last is not None and last.get("kind") == "build" and last.get("type") == record["plant"] \
                and last.get("round") == record["round"]:
            shadow_actions.pop()
    record = state.undo_record
    if state.undo_last_build():
        announce(
            f"Took back the {PLANT_LABEL[record['plant']]} build. Refunded {record['cost']:.0f}. {_funds_phrase()}"
        )
    else:
        announce("Nothing to undo: only the last build this round can be taken back")
    render()


def on_accept_grant(event=None):
    if state.accept_grant():
        announce(state.last_grant_message)
    render()


def on_decline_grant(event=None):
    if state.decline_grant():
        announce(state.last_grant_message)
    render()


def on_peek_forecast(event=None):
    state.buy_peek()
    render()


def peek_text():
    """The peek forecast spelled out in words (and numbers), or the reason it is not showing."""
    if not state.peek_unlocked():
        return "Peek forecast: buy Weather station in the Career upgrade tree (Meteorology) to read next round's rolls."
    if not state.peek_active():
        return f"Peek forecast: pay {PEEK_FEE} funds to read next round's weather roll and whether a disruption hits."
    f = state.peek_forecast()
    outcome = {
        "hit": f"A disruption WILL hit next round (the chance was {f['probability'] * 100:.0f}%).",
        "waived": "A disruption would hit next round, but Diplomatic Immunity calls it off.",
        "none": f"No disruption next round (the chance was {f['probability'] * 100:.0f}%).",
    }[f["disruption"]]
    if f["weather"] is None:
        weather = "Weather variability is off, so renewable output stays at nameplate."
    else:
        weather = "Next round's renewable output: " + ", ".join(
            f"{PLANT_LABEL[t]} {(v - 1) * 100:+.0f}%" for t, v in f["weather"].items()
        ) + "."
    text = f"Peek forecast: {outcome} {weather}"
    if f["weather_next"] is not None:
        text += " The round after: " + ", ".join(
            f"{PLANT_LABEL[t]} {(v - 1) * 100:+.0f}%" for t, v in f["weather_next"].items()
        ) + "."
    return text


def render_run_setup_and_extras():
    """Everything the 2026-10-08 batch added to the main screen: run setup (loadout, seed, Ironman),
    the undo button, the Perfect Round streak, the grant offer, the peek forecast, plant nicknames."""
    owned_loadouts = list(LOADOUT_NODES) if sandbox_active else [n for n in LOADOUT_NODES if n in career["unlocked"]]
    select = document.getElementById("start-option-select")
    select.value = state.start_option if state.start_option in owned_loadouts else START_OPTION_NONE
    select.disabled = not state.unstarted() or not owned_loadouts
    options = getattr(select, "options", None)  # the fake DOM has none; the browser marks unowned loadouts unavailable
    if options is not None:
        for index in range(int(options.length)):
            option = options.item(index)
            option.disabled = option.value != START_OPTION_NONE and option.value not in owned_loadouts
    select.title = (
        "Buy a loadout in the Career upgrade tree (Starting loadout branch) to choose one here."
        if not owned_loadouts else "Choose one starting loadout per run, before you build or advance a round."
    )
    note = document.getElementById("start-option-note")
    if state.start_option in owned_loadouts:
        note.innerText = f"Loadout: {CAREER_UNLOCKS[state.start_option]['label']} -- {CAREER_UNLOCKS[state.start_option]['effect']}."
    elif owned_loadouts:
        note.innerText = "Loadout: none chosen."
    else:
        note.innerText = "No loadout bought yet (Career upgrade tree, Starting loadout)."
    document.getElementById("run-seed-display").innerText = f"Run seed: {state.seed}"
    document.getElementById("run-seed-apply-button").disabled = not state.unstarted()
    document.getElementById("run-seed-input").disabled = not state.unstarted()
    document.getElementById("run-seed-note").innerText = run_setup_message
    iron = document.getElementById("ironman-toggle-button")
    iron.innerText = "Ironman: ON (no undo)" if state.ironman else "Ironman: OFF"
    iron.disabled = not state.unstarted() and not state.ironman
    iron.title = "Opt-in challenge: every action is final and Undo last build is off. Fixed once the run starts."
    undo = document.getElementById("undo-build-button")
    undo.disabled = not state.can_undo_build()
    if state.ironman:
        undo.innerText = "Undo last build (off in Ironman)"
    elif state.can_undo_build():
        record = state.undo_record
        undo.innerText = f"Undo last build ({PLANT_LABEL[record['plant']]}, refunds {record['cost']:.0f})"
    else:
        undo.innerText = "Undo last build"
    bonus = state.perfect_bonus_fraction()
    document.getElementById("perfect-streak-display").innerText = (
        f"\U0001F525 Perfect Round streak: {state.perfect_streak} (revenue bonus +{bonus * 100:.0f}%, best {state.best_perfect_streak})"
        if state.perfect_streak > 0
        else f"Perfect Round streak: 0 (best {state.best_perfect_streak}). Rounds with no disruption and demand fully met build a revenue bonus."
    )
    offer = state.grant_offer
    banner = document.getElementById("grant-banner")
    banner.hidden = offer is None
    if offer is not None:
        info = GRANTS[offer["id"]]
        document.getElementById("grant-text").innerText = f"{info['title']}: {info['text']}"
        document.getElementById("grant-accept-button").innerText = info["accept"]
        document.getElementById("grant-decline-button").innerText = info["decline"]
    message = document.getElementById("grant-message-display")
    message.innerText = state.last_grant_message
    message.hidden = not state.last_grant_message
    peek = document.getElementById("peek-forecast-button")
    peek.hidden = not state.peek_unlocked()
    peek.innerText = f"Peek forecast ({PEEK_FEE} funds)"
    peek.disabled = state.peeked_round == state.round_number or state.funds < PEEK_FEE
    document.getElementById("peek-forecast-display").innerText = peek_text()
    for plant_type in PLANT_TYPES:
        names = state.plant_name_list(plant_type)
        document.getElementById(f"{plant_type}-names").innerText = ", ".join(names)
    eulogy = document.getElementById("eulogy-display")
    eulogy.hidden = state.last_eulogy is None
    eulogy.innerText = state.last_eulogy["text"] if state.last_eulogy else ""


def on_export_career(event=None):
    export_career_to_field()
    render()


def on_import_career(event=None):
    text = document.getElementById("career-data-field").value or ""

    def do_import():
        import_career_from_text(text)
        render()

    _confirm_dialog_ask(
        action_id="grid-import-career",
        message="Replace your whole career (points, perks, records and run history) with the pasted data?",
        confirm_label="Replace career",
        on_confirm=do_import,
        allow_skip=False,
    )


def on_reset_career(event=None):
    # Offer the backup first: the JSON goes into the box (and the clipboard)
    # before the question is asked, so it is there whatever the answer is.
    export_career_to_field()

    def do_reset():
        reset_career()
        render()

    _confirm_dialog_ask(
        action_id="grid-reset-career",
        message=(
            "Reset your whole career? Points, perks, records, run history and banked achievements are erased. "
            "A copy of the current career has just been copied or placed in the box so you can restore it later."
        ),
        confirm_label="Reset career",
        on_confirm=do_reset,
        allow_skip=False,
    )
    render()


ARBITRAGE_MODE_LABEL = {"idle": "Idle", "charge": "Charge", "discharge": "Discharge"}


def arbitrage_status_message():
    """C9: one plain-text line -- stored level plus what last round did."""
    cap = state.storage_cap()
    text = f"Stored {state.stored_energy:.0f}/{cap:.0f}."
    last = state.last_arbitrage
    if last is not None:
        if last["mode"] == "charge":
            text += f" Last round: banked {last['units']:.0f} surplus."
        else:
            text += f" Last round: sold {last['units']:.0f} for +{last['revenue']:.0f} funds."
    return text


def emergency_message():
    """C27: banner text for the emergency scenario, or '' outside it."""
    em = state.emergency
    if em is None:
        return ""
    if em["status"] == "stabilized":
        return "Emergency over: the grid is stabilized. The run carries on as normal."
    if em["status"] == "missed":
        return (
            "Emergency window closed without stabilizing. There is no game over -- "
            "keep building; demand still has to be met."
        )
    return (
        f"EMERGENCY: a major disruption left capacity {state.total_capacity()} against demand {state.demand}. "
        f"Get capacity to at least demand for {EMERGENCY_HOLD_ROUNDS} rounds in a row "
        f"(held {em['hold']}/{EMERGENCY_HOLD_ROUNDS}, {em['rounds_left']} round(s) left)."
    )


def _render_arbitrage_and_emergency():
    has_battery = state.plant_counts["battery"] > 0
    mode_button = document.getElementById("arbitrage-mode-button")
    mode_button.innerText = f"Storage: {ARBITRAGE_MODE_LABEL[state.arbitrage_mode]}"
    mode_button.disabled = not has_battery
    mode_button.title = (
        "Click to cycle Idle / Charge / Discharge for the next round."
        if has_battery
        else "Build a battery to use storage arbitrage."
    )
    status_el = document.getElementById("arbitrage-status-display")
    status_el.hidden = not has_battery
    status_el.innerText = arbitrage_status_message() if has_battery else ""
    emergency_el = document.getElementById("emergency-status-display")
    text = emergency_message()
    emergency_el.hidden = not text
    emergency_el.innerText = text


def on_cycle_arbitrage_mode(event=None):
    """C9: cycle Idle -> Charge -> Discharge for the next round."""
    modes = ARBITRAGE_MODES
    state.set_arbitrage_mode(modes[(modes.index(state.arbitrage_mode) + 1) % len(modes)])
    render()


def _load_arbitrage_and_emergency(data):
    """Validated restore of C9/C27 fields (defaults if malformed)."""
    stored = data.get("stored_energy", state.stored_energy)
    ok = isinstance(stored, (int, float)) and not isinstance(stored, bool) and stored == stored
    state.stored_energy = max(0.0, min(float(stored), state.storage_cap())) if ok else 0.0
    mode = data.get("arbitrage_mode", state.arbitrage_mode)
    state.arbitrage_mode = mode if mode in ARBITRAGE_MODES else "idle"
    total = data.get("arbitrage_revenue_total", state.arbitrage_revenue_total)
    ok = isinstance(total, (int, float)) and not isinstance(total, bool) and total == total
    state.arbitrage_revenue_total = max(0.0, float(total)) if ok else 0.0
    state.last_arbitrage = None
    em = data.get("emergency", state.emergency)
    if (
        state.scenario == "emergency"
        and isinstance(em, dict)
        and em.get("status") in ("active", "stabilized", "missed")
    ):
        state.emergency = {
            "status": em["status"],
            "rounds_left": _as_int(em.get("rounds_left"), 0, 0, EMERGENCY_ROUNDS),
            "hold": _as_int(em.get("hold"), 0, 0, EMERGENCY_HOLD_ROUNDS),
        }
    else:
        state.emergency = None


def _make_build_handler(plant_type):
    def handler(event=None):
        cost = state.plant_cost(plant_type)
        funds_before = state.funds
        if state.build_plant(plant_type):
            record_shadow_action("build", plant_type)
            announce(
                f"Built a {PLANT_LABEL[plant_type]} plant, {state.plant_name_list(plant_type)[-1]}. "
                f"{state.plant_counts[plant_type]} {PLANT_LABEL[plant_type]} standing. {_funds_phrase()}"
            )
        else:
            announce(
                f"Cannot build {PLANT_LABEL[plant_type]}: it costs {cost:.0f} and you have {funds_before:.0f}"
            )
        reached_before = state.renewable_50_reached
        _check_renewable_milestone()
        if state.renewable_50_reached and not reached_before:
            announce("More than half your grid's capacity is now renewable")
        render()
        _check_new_achievements_for_toast()
    return handler


# C8 -- transient (never saved) "currently showing" flag for the one-time
# 50%-renewable-capacity callout, same reasoning as C20's callouts below:
# state.renewable_50_reached is the persisted "has this ever happened"
# gate, this is just whether it's visible in this session right now.
renewable_milestone_visible = False


def _pulse_emissions_meter():
    """C24: a brief pulse on the emissions meter the instant renewables
    cross 50% of capacity. Pure CSS class, removed by timer."""
    meter = document.getElementById("emissions-bar")
    meter.classList.add("meter-pulse")

    def _clear(*args):
        meter.classList.remove("meter-pulse")
        proxy.destroy()

    proxy = create_proxy(_clear)
    setTimeout(proxy, 1600)


def on_cycle_scenario(event=None):
    """C13: cycle to the next starting scenario (only before any build)."""
    global state
    next_id = SCENARIO_ORDER[(SCENARIO_ORDER.index(state.scenario) + 1) % len(SCENARIO_ORDER)]
    if sandbox_active:  # Z-18: any time; the practice grid starts over on the new scenario
        state = new_sandbox_state(next_id)
    else:
        state.apply_scenario(next_id)
    render()


def _check_renewable_milestone():
    """Called after every action that could change capacity composition
    (build/retire/advance round) -- not from render() itself, so a loaded
    save doesn't flash the callout purely from being rendered once."""
    global renewable_milestone_visible
    if not state.renewable_50_reached and renewable_capacity_share() >= 0.5:
        state.renewable_50_reached = True
        renewable_milestone_visible = True
        _pulse_emissions_meter()


def on_dismiss_renewable_milestone(event=None):
    global renewable_milestone_visible
    renewable_milestone_visible = False
    render()


# C20 -- transient (never saved) "currently showing" flags for the
# first-use callouts below. state.seen_retire_callout/seen_maintain_callout
# are the persisted "have we ever shown this" gate; these two control
# whether it's visible *right now* in this session, so a loaded save that
# already has the persisted flag set doesn't re-flash the callout on load.
retire_callout_visible = False
maintain_callout_visible = False


def _confirm_dialog_ask(action_id, message, confirm_label, on_confirm, allow_skip=True):
    """Routes a guarded action through the shared shared/confirm-dialog.js
    widget when it's available, or runs the action immediately when it
    isn't -- same lazy `from js import window`/getattr-default shape as
    every other optional-JS-hook call in this hub (e.g. continuum's
    `_notify_visual_layer()`, champ-de-mots' `_dispatch_report()`). The
    pytest fake-DOM harness's `js` module only ever fakes `document`/
    `setTimeout` (see tests/conftest.py), never `window`, so `from js
    import window` raises ImportError there and this falls straight
    through to calling on_confirm() synchronously -- which is exactly
    what every existing test that drives a retire click already expects."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        on_confirm()
        return
    confirm_dialog = getattr(window, "ConfirmDialog", None)
    if confirm_dialog is None:
        on_confirm()
        return
    options = {} if allow_skip else {"allowSkip": False}
    confirm_dialog.ask(
        id=action_id,
        message=message,
        confirmLabel=confirm_label,
        onConfirm=create_proxy(on_confirm),
        **options,
    )


def _play_demolition_puff():
    """GC-4: replays the little smoke puff on the eulogy line (CSS only; off under reduced motion)."""
    line = document.getElementById("eulogy-display")
    line.classList.remove("eulogy-puff")

    def _start(*args):
        line.classList.add("eulogy-puff")
        proxy.destroy()

    proxy = create_proxy(_start)
    setTimeout(proxy, 30)


def _make_retire_handler(plant_type):
    def do_retire():
        global retire_callout_visible
        eulogy_before = state.last_eulogy
        funds_before = state.funds
        succeeded = state.retire_plant(plant_type)
        if succeeded:
            record_shadow_action("retire", plant_type)
            announce(
                f"Retired a {PLANT_LABEL[plant_type]} plant. {state.plant_counts[plant_type]} "
                f"{PLANT_LABEL[plant_type]} standing. Refund {state.funds - funds_before:.0f}. {_funds_phrase()}"
            )
        else:
            announce(f"Cannot retire {PLANT_LABEL[plant_type]}: none are standing")
        if succeeded and state.last_eulogy is not eulogy_before:
            _play_demolition_puff()
        if succeeded and not state.seen_retire_callout:
            state.seen_retire_callout = True
            retire_callout_visible = True
        _check_renewable_milestone()
        render()
        _check_new_achievements_for_toast()

    def handler(event=None):
        # C14 (planning/TODO.md's shared confirmation-dialog goal) --
        # retiring a plant type's very last unit is a real, not-quite-free
        # decision (refund_plant() only rebates REFUND_FRACTION of the
        # current cost -- rebuilding costs full price again), so that one
        # case alone is gated behind the shared confirm dialog. Retiring
        # down from 2+ units stays exactly as instant as it always was.
        if state.plant_counts[plant_type] <= 0:
            do_retire()  # already 0 -- retire_plant() is a no-op; let it report False as usual
            return
        if state.plant_counts[plant_type] == 1:
            _confirm_dialog_ask(
                action_id=f"grid-retire-last-{plant_type}",
                message=(
                    f"Retire your last {PLANT_LABEL[plant_type]} plant "
                    f"(wear {state.wear_percent(plant_type)}%, average age {state.plant_age[plant_type]:.1f} rounds)? "
                    "You'll lose that capacity, and rebuilding later costs "
                    "full price again."
                ),
                confirm_label="Retire it",
                on_confirm=do_retire,
            )
        else:
            do_retire()
    return handler


# C-4 -- plant-mix hover/focus readout: one plant type's share of capacity, of the round's revenue and of
# its emissions, plus a highlight on its row. Pure display; no new state.
def mix_hover_text(plant_type):
    share = state.capacity_share(plant_type)
    total_capacity = state.total_capacity()
    if total_capacity <= 0:
        return f"{PLANT_LABEL[plant_type]}: no generation on the grid yet, so no share of capacity, revenue or emissions."
    paid_units = min(total_capacity, state.demand)
    revenue = share * paid_units * REVENUE_PER_UNIT_MET
    revenue_total = paid_units * REVENUE_PER_UNIT_MET
    emissions = state.plant_counts[plant_type] * PLANT_CAPACITY[plant_type] * EMISSIONS_FACTOR[plant_type]
    emissions_total = sum(
        state.plant_counts[t] * PLANT_CAPACITY[t] * EMISSIONS_FACTOR[t] for t in GENERATION_TYPES
    )
    emissions_part = (
        f"{emissions / emissions_total * 100:.0f}% of emissions ({emissions:.0f} of {emissions_total:.0f} per round)"
        if emissions_total > 0
        else "0% of emissions (the grid emits nothing)"
    )
    return (
        f"{PLANT_LABEL[plant_type]}: {share * 100:.0f}% of capacity, "
        f"about {share * 100:.0f}% of revenue ({revenue:.0f} of {revenue_total:.0f} funds per round, "
        f"every unit of output sold earns the same), {emissions_part}."
    )


def _make_mix_hover_handler(plant_type, entering):
    def handler(event=None):
        readout = document.getElementById("mix-hover-readout")
        row = document.getElementById(f"{plant_type}-row")
        mix_row = document.getElementById(f"{plant_type}-mix-row")
        if entering:
            readout.innerText = mix_hover_text(plant_type)
            row.classList.add("plant-row--highlight")
            mix_row.classList.add("mix-row--active")
        else:
            readout.innerText = MIX_HOVER_HINT
            row.classList.remove("plant-row--highlight")
            mix_row.classList.remove("mix-row--active")
    return handler


MIX_HOVER_HINT = "Hover or focus a bar to see that plant type's share of capacity, revenue and emissions."


def _make_maintain_handler(plant_type):
    def handler(event=None):
        global maintain_callout_visible
        succeeded = state.maintain_plant(plant_type)
        if succeeded:
            announce(
                f"Maintained the {PLANT_LABEL[plant_type]} fleet. Wear now {state.wear_percent(plant_type)}%. "
                f"{_funds_phrase()}"
            )
        elif state.plant_counts[plant_type] <= 0:
            announce(f"Cannot maintain {PLANT_LABEL[plant_type]}: none are standing")
        else:
            announce(
                f"Cannot maintain {PLANT_LABEL[plant_type]}: it costs {state.maintenance_cost(plant_type):.0f} "
                f"and you have {state.funds:.0f}"
            )
        if succeeded and not state.seen_maintain_callout:
            state.seen_maintain_callout = True
            maintain_callout_visible = True
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_maintenance_schedule_handler(plant_type):
    """TODO-C23: the per-plant-type auto-maintain cadence <select>'s own
    change handler -- reads the just-changed value straight off the
    event's target, same convention as on_grid_size_change() elsewhere in
    this file."""
    def handler(event):
        state.set_maintenance_schedule(plant_type, int(event.target.value))
        render()
    return handler


def on_dismiss_retire_callout(event=None):
    global retire_callout_visible
    retire_callout_visible = False
    render()


def on_dismiss_maintain_callout(event=None):
    global maintain_callout_visible
    maintain_callout_visible = False
    render()


DISRUPTION_TOAST_SEVERITY_CLASSES = ("disruption-toast--warning", "disruption-toast--danger")


def _display_disruption_toast(message, severity_class):
    """C12: a visible toast/banner for a disruption or aging-breakdown
    event, on top of the persistent #event-display/#aging-event-display
    status lines -- those require scrolling to notice; this surfaces the
    same information immediately regardless of scroll position. Same
    show-then-auto-hide shape as the achievement-unlock toast, styled by
    severity rather than always the same color."""
    toast = document.getElementById("disruption-toast")
    text = document.getElementById("disruption-toast-text")
    text.innerText = message
    for cls in DISRUPTION_TOAST_SEVERITY_CLASSES:
        toast.classList.remove(cls)
    toast.classList.add(severity_class)
    toast.hidden = False
    toast.classList.add("visible")

    def _hide(*args):
        toast.hidden = True
        toast.classList.remove("visible")
        proxy.destroy()

    proxy = create_proxy(_hide)
    setTimeout(proxy, 5000)


def _check_disruption_toast():
    """Called only from on_advance_round(), right after a round resolves:
    a disruption event takes priority over an aging breakdown when both
    land the same round, matching render()'s own priority (a "damage"
    disruption event already implies a plant went offline this round, the
    more urgent read)."""
    if state.last_event is not None:
        severity_class = (
            "disruption-toast--danger" if state.last_event["type"] == "damage" else "disruption-toast--warning"
        )
        _display_disruption_toast(
            f"{event_message(state.last_event)} {disruption_reason(state.last_event)}", severity_class
        )
    elif state.last_aging_event is not None:
        plant_name = PLANT_LABEL[state.last_aging_event["plant"]]
        cost = state.last_aging_event["repair_cost"]
        _display_disruption_toast(
            f"Aging breakdown! A {plant_name} plant failed from wear (repair cost {cost:.0f}).",
            "disruption-toast--danger",
        )


def on_toggle_steeper_demand(event=None):
    state.steeper_demand_growth_enabled = not state.steeper_demand_growth_enabled
    render()


def on_toggle_weather_variability(event=None):
    state.weather_variability_enabled = not state.weather_variability_enabled
    render()


def on_invest_demand_response(event=None):
    """TODO-C7: the demand-response lever's own button click."""
    cost = state.demand_response_cost()
    if state.invest_demand_response():
        announce(
            f"Invested in demand response, level {state.demand_response_level}. Demand now grows by "
            f"{state.demand_growth_this_round():g} a round. {_funds_phrase()}"
        )
    else:
        announce(f"Cannot invest in demand response: it costs {cost:.0f} and you have {state.funds:.0f}")
    render()


def on_enact_carbon_pricing(event=None):
    """TODO-C19: accept the currently-offered policy lever as carbon pricing."""
    if state.enact_policy("carbon_pricing"):
        announce(f"Carbon pricing enacted: fossil plants cost more to build for {state.active_policy['rounds_remaining']} rounds")
    else:
        announce("No policy lever is on offer right now")
    render()


def on_enact_renewable_subsidy(event=None):
    """TODO-C19: accept the currently-offered policy lever as a renewable subsidy."""
    if state.enact_policy("renewable_subsidy"):
        announce(f"Renewable subsidy enacted: renewable plants cost less to build for {state.active_policy['rounds_remaining']} rounds")
    else:
        announce("No policy lever is on offer right now")
    render()


def on_decline_policy(event=None):
    """TODO-C19: turn down the currently-offered policy lever entirely."""
    if state.decline_policy():
        announce("Policy lever declined")
    else:
        announce("No policy lever is on offer right now")
    render()


# ===========================================================================
# C21: the shadow grid ("grid twin", the lighter version). A second,
# NON-interactive grid that copies every build and retire you make onto a
# DIFFERENT starting scenario, so the two outcomes can be compared side by side
# ("what would the same choices have done from a coal-heavy start?"). It is
# not a second game to play: it is derived by replaying your recorded actions,
# round by round, on a fresh grid with its own fixed random stream, so it is
# reproducible, can never affect your grid, and needs only the scenario name
# and the action log to save. A mirrored action the shadow cannot afford is
# simply skipped and counted. It sits beside the C15 global comparison.
# ===========================================================================
SHADOW_SEED = 20260926
SHADOW_MAX_ACTIONS = 400
shadow_scenario = None   # None = off; otherwise a key of SCENARIOS
shadow_actions = []      # [{"round": int, "kind": "build"|"retire", "type": plant type}]


def default_shadow_scenario():
    """A contrasting start to the one being played."""
    return "standard" if state.scenario != "standard" else "coal_legacy"


def set_shadow_scenario(scenario_id):
    """Turns the shadow on for a scenario (or off with None). Existing actions
    are kept, so switching scenario replays the same choices somewhere else."""
    global shadow_scenario
    if scenario_id is not None and not (isinstance(scenario_id, str) and scenario_id in SCENARIOS):
        return False
    shadow_scenario = scenario_id
    return True


def record_shadow_action(kind, plant_type):
    if shadow_scenario is None:
        return
    shadow_actions.append({"round": state.round_number, "kind": kind, "type": plant_type})
    del shadow_actions[:-SHADOW_MAX_ACTIONS]


def replay_shadow():
    """Returns (shadow_grid, skipped_actions) for the player's current round."""
    grid_copy = GridState()
    grid_copy.apply_scenario(shadow_scenario)
    rng = random.Random(SHADOW_SEED)
    skipped = 0
    by_round = {}
    for action in shadow_actions:
        by_round.setdefault(action["round"], []).append(action)
    for round_number in range(1, state.round_number + 1):
        for action in by_round.get(round_number, []):
            ok = (
                grid_copy.build_plant(action["type"]) if action["kind"] == "build"
                else grid_copy.retire_plant(action["type"])
            )
            if not ok:
                skipped += 1
        if round_number < state.round_number:
            grid_copy.advance_round(rng=rng.random, age_rng=rng.random, weather_rng=rng.random)
    return grid_copy, skipped


def shadow_rows():
    """Comparison rows for the page: (metric, yours, shadow's)."""
    if shadow_scenario is None:
        return None
    twin, skipped = replay_shadow()
    rows = [
        ("Score", f"{state.score():.0f}", f"{twin.score():.0f}"),
        ("Funds", f"{state.funds:.0f}", f"{twin.funds:.0f}"),
        ("Clean share of capacity", f"{(1 - state.fossil_share()) * 100:.0f}%", f"{(1 - twin.fossil_share()) * 100:.0f}%"),
        ("Emissions avoided", f"{state.emissions_avoided():.0f}", f"{twin.emissions_avoided():.0f}"),
    ]
    if state.score() > twin.score() + 0.5:
        verdict = f"You are ahead of the {SCENARIOS[shadow_scenario]['label']} twin."
    elif twin.score() > state.score() + 0.5:
        verdict = f"The {SCENARIOS[shadow_scenario]['label']} twin is ahead of you."
    else:
        verdict = f"You and the {SCENARIOS[shadow_scenario]['label']} twin are level."
    if skipped:
        verdict += f" (The twin could not afford {skipped} of your mirrored moves.)"
    return rows, verdict


def render_shadow():
    select = document.getElementById("shadow-select")
    table = document.getElementById("shadow-table")
    verdict_el = document.getElementById("shadow-verdict")
    select.value = shadow_scenario or "off"
    table.innerHTML = ""
    result = shadow_rows()
    if result is None:
        verdict_el.innerText = "Pick a starting scenario to compare your choices against a shadow grid that copies every build and retire."
        return
    rows, verdict = result
    verdict_el.innerText = verdict
    header = document.createElement("div")
    header.className = "shadow-row shadow-row--head"
    for text in ("", "You", f"Twin ({SCENARIOS[shadow_scenario]['label']})"):
        cell = document.createElement("span")
        cell.innerText = text
        header.appendChild(cell)
    table.appendChild(header)
    for metric, yours, theirs in rows:
        line = document.createElement("div")
        line.className = "shadow-row"
        for text in (metric, yours, theirs):
            cell = document.createElement("span")
            cell.innerText = text
            line.appendChild(cell)
        table.appendChild(line)


def on_shadow_change(event=None):
    value = document.getElementById("shadow-select").value
    set_shadow_scenario(None if value == "off" else value)
    render()


# ===========================================================================
# C29 -- real-grid comparison: set your plant mix beside the published
# electricity-generation mix of a real region. The figures are read from
# public sources (below) and are the SHARE OF GENERATION in the stated year;
# your bars are the share of standing CAPACITY, which is what this game
# tracks, so a source with a low capacity factor (solar) shows a smaller real
# share than its capacity share would. The panel says so. "Clean" means
# nuclear, solar, wind and hydro, the same non-fossil idea the game's own score
# uses; the real regions' "other" (biomass, oil) is counted as neither.
# ===========================================================================
REAL_GRIDS = {
    "us": {
        "label": "United States", "year": 2025,
        "source": "U.S. Energy Information Administration, Electricity in the U.S. (utility-scale generation, rounded 'about' figures)",
        "shares": {"coal": 17.0, "gas": 41.0, "nuclear": 18.0, "solar": 7.0, "wind": 11.0, "hydro": 6.0, "other": 0.9},
    },
    "de": {
        "label": "Germany", "year": 2025,
        "source": "Net public generation as tabulated on Wikipedia's Energy in Germany (lignite 16.3% + hard coal 6.3% shown as coal; biomass 8.7% shown as other)",
        "shares": {"coal": 22.6, "gas": 13.0, "nuclear": 0.0, "solar": 17.0, "wind": 31.8, "hydro": 4.1, "other": 8.7},
    },
    "fr": {
        "label": "France", "year": 2020,
        "source": "Wikipedia's Electricity sector in France, 2020 production table (oil 0.43% + bioenergies 1.84% shown as other); the page carried no newer full-year table when this was added",
        "shares": {"coal": 0.3, "gas": 7.18, "nuclear": 70.58, "solar": 2.16, "wind": 6.34, "hydro": 11.16, "other": 2.27},
    },
}
REAL_GRID_CLEAN_TYPES = ("nuclear", "solar", "wind", "hydro")
real_grid_choice = None   # None = off; otherwise a key of REAL_GRIDS


def set_real_grid(choice):
    """Turns the comparison on for a known region, or off (None). Returns
    whether the value was accepted."""
    global real_grid_choice
    if choice is None:
        real_grid_choice = None
        return True
    if not isinstance(choice, str) or choice not in REAL_GRIDS:
        return False
    real_grid_choice = choice
    return True


def real_grid_clean_share(shares):
    return sum(shares.get(t, 0.0) for t in REAL_GRID_CLEAN_TYPES)


def real_grid_rows(choice=None):
    """None when off or the player has no capacity yet; otherwise
    (rows, verdict) where rows are (label, yours, theirs, difference) strings
    for each generation type plus other and the clean total."""
    choice = real_grid_choice if choice is None else choice
    if choice not in REAL_GRIDS:
        return None
    if state.total_capacity() <= 0:
        return None
    region = REAL_GRIDS[choice]
    theirs = region["shares"]
    mine = {t: state.capacity_share(t) * 100 for t in GENERATION_TYPES}
    rows = []
    for plant_type in GENERATION_TYPES:
        rows.append((
            PLANT_LABEL[plant_type], f"{mine[plant_type]:.0f}%", f"{theirs.get(plant_type, 0.0):.0f}%",
            f"{mine[plant_type] - theirs.get(plant_type, 0.0):+.0f}",
        ))
    rows.append(("Other (biomass, oil)", "0%", f"{theirs.get('other', 0.0):.0f}%", f"{-theirs.get('other', 0.0):+.0f}"))
    my_clean, their_clean = real_grid_clean_share(mine), real_grid_clean_share(theirs)
    rows.append(("Clean total", f"{my_clean:.0f}%", f"{their_clean:.0f}%", f"{my_clean - their_clean:+.0f}"))
    gap = my_clean - their_clean
    if abs(gap) < 0.5:
        verdict = f"Your clean share matches {region['label']} ({region['year']}) at about {their_clean:.0f}%."
    else:
        verdict = (
            f"Your grid is {abs(gap):.0f} points {'cleaner' if gap > 0 else 'dirtier'} than {region['label']}'s "
            f"real grid ({their_clean:.0f}% clean in {region['year']}, against your {my_clean:.0f}%)."
        )
    return rows, verdict


def render_real_grid():
    select = document.getElementById("real-grid-select")
    table = document.getElementById("real-grid-table")
    verdict_el = document.getElementById("real-grid-verdict")
    source_el = document.getElementById("real-grid-source")
    select.value = real_grid_choice or "off"
    table.innerHTML = ""
    if real_grid_choice is None:
        verdict_el.innerText = "Pick a real region to compare your plant mix against its published generation mix."
        source_el.hidden = True
        return
    region = REAL_GRIDS[real_grid_choice]
    source_el.hidden = False
    source_el.innerText = (
        f"Source: {region['source']}. Real figures are shares of generation; yours are shares of capacity, "
        "so low-capacity-factor sources such as solar read differently."
    )
    result = real_grid_rows()
    if result is None:
        verdict_el.innerText = "Build some generation to see how it compares."
        return
    rows, verdict = result
    verdict_el.innerText = verdict
    header = document.createElement("div")
    header.className = "shadow-row shadow-row--head"
    for text in ("", "You", f"{region['label']} {region['year']}", "Gap"):
        cell = document.createElement("span")
        cell.innerText = text
        header.appendChild(cell)
    table.appendChild(header)
    for label, yours, theirs, gap in rows:
        line = document.createElement("div")
        line.className = "shadow-row"
        for text in (label, yours, theirs, gap):
            cell = document.createElement("span")
            cell.innerText = text
            line.appendChild(cell)
        table.appendChild(line)


def on_real_grid_change(event=None):
    value = document.getElementById("real-grid-select").value
    set_real_grid(None if value == "off" else value)
    render()


def render_regional_grid():
    button = document.getElementById("regional-grid-connect-button")
    display = document.getElementById("regional-grid-display")
    if state.regional_grid_connected:
        button.innerText = "Regional grid: connected"
        button.disabled = True
        display.hidden = False
        display.innerText = state.regional_grid_readout_text()
    else:
        button.innerText = "Connect a regional grid"
        button.disabled = False
        display.hidden = True


def on_connect_regional_grid(event=None):
    if state.regional_grid_connected:
        return
    state.connect_regional_grid()
    render()


auto_advance_message = ""


def on_advance_round(event=None):
    global auto_advance_message, last_finish_records
    auto_advance_message = ""
    last_finish_records = []
    reached_before = state.renewable_50_reached
    state.advance_round()
    _check_renewable_milestone()
    render()
    announce(round_announcement_text(milestone_new=state.renewable_50_reached and not reached_before))
    _check_disruption_toast()
    _check_new_achievements_for_toast()


# GC-17 -- auto-advance: play up to AUTO_ADVANCE_ROUNDS rounds in one click,
# stopping early at the first disruption, aging breakdown or policy-lever
# offer, so there is always a pause at the moments that call for a decision.
# No builds, retires or maintenance happen in between (that is the point:
# "let it run"), and an open policy offer must be answered first.
AUTO_ADVANCE_ROUNDS = 5


def auto_advance(max_rounds=AUTO_ADVANCE_ROUNDS, **rngs):
    """Advance up to max_rounds rounds. Returns (rounds_played, message).
    rngs are passed straight to GridState.advance_round (tests use them)."""
    if state.policy_lever_available:
        return 0, "A policy lever is waiting for your decision first."
    if state.grant_offer is not None:
        return 0, "A grant offer is waiting for your decision first."
    played = 0
    reason = f"Played all {max_rounds} rounds with nothing needing a decision."
    for _ in range(max_rounds):
        state.advance_round(**rngs)
        played += 1
        _check_renewable_milestone()
        if state.last_event is not None:
            reason = "Stopped: a disruption hit."
            break
        if state.last_aging_event is not None:
            reason = "Stopped: an aging breakdown took a plant offline."
            break
        if state.policy_lever_available:
            reason = "Stopped: a policy lever is on offer."
            break
        if state.grant_offer is not None:
            reason = "Stopped: a grant offer is waiting."
            break
    return played, f"Auto-advanced {played} round(s). {reason}"


def on_auto_advance(event=None):
    global auto_advance_message, last_finish_records
    last_finish_records = []
    reached_before = state.renewable_50_reached
    played, message = auto_advance()
    auto_advance_message = message
    if played:
        render()
        announce(message)
        announce(round_announcement_text(milestone_new=state.renewable_50_reached and not reached_before))
        _check_disruption_toast()
        _check_new_achievements_for_toast()
    else:
        render()
        announce(message)


def render_auto_advance():
    button = document.getElementById("auto-advance-button")
    button.innerText = f"Auto-advance up to {AUTO_ADVANCE_ROUNDS} rounds"
    button.disabled = state.policy_lever_available or state.grant_offer is not None
    button.title = (
        "Answer the policy lever or grant on offer first."
        if state.policy_lever_available or state.grant_offer is not None
        else "Plays rounds back to back with no building in between. Stops at the first disruption, "
        "aging breakdown or policy offer."
    )
    status = document.getElementById("auto-advance-status")
    status.innerText = auto_advance_message
    status.hidden = not auto_advance_message


# C-8 -- round recap: one expandable entry collating where last round's
# funds went and came from (revenue, arbitrage, regional grid, scheduled
# maintenance, weather, disruption, aging, demand growth).
def round_recap_text():
    """Returns (summary, details) for the last round played."""
    r = state.last_round_recap
    if r is None:
        return "Round recap: no round played yet.", "Advance a round and its funds story appears here."
    lines = [f"Revenue earned: +{r['base_revenue']:.0f}"]
    if r.get("perfect_bonus", 0) > 0:
        lines.append(f"Perfect Round bonus: +{r['perfect_bonus']:.0f}")
    if r.get("immunity"):
        lines.append("Diplomatic Immunity: a disruption was called off")
    if r["arbitrage"] > 0:
        lines.append(f"Storage arbitrage sales: +{r['arbitrage']:.0f}")
    if state.regional_grid_connected:
        lines.append(f"Regional grid: +{r['regional']:.0f} earned, -{r['regional_shortfall']:.0f} bought in")
    if r["scheduled"]:
        spent = ", ".join(f"{PLANT_LABEL[a['plant']]} (-{a['cost']:.0f})" for a in r["scheduled"])
        lines.append(f"Scheduled maintenance: {spent}")
    if r["weather_pct"] is not None:
        direction = "above" if r["weather_pct"] >= 0 else "below"
        lines.append(f"Weather: renewable output {abs(r['weather_pct']):.0f}% {direction} nameplate")
    if r["disruption_loss"] > 0:
        lines.append(f"Disruption: -{r['disruption_loss']:.0f} revenue lost")
    elif r["disruption_type"] is not None:
        lines.append("Disruption: no revenue lost")
    if r["aging_plant"] in PLANT_LABEL:
        lines.append(f"Aging breakdown: {PLANT_LABEL[r['aging_plant']]} unit lost, repair -{r['repair_cost']:.0f}")
    growth_note = f"Demand grew by {r['demand_growth']:g}"
    if state.demand_response_level > 0:
        growth_note += f" (demand response level {state.demand_response_level})"
    lines.append(growth_note)
    if r.get("perfect"):
        lines.append("This was a Perfect Round: no disruption, no breakdown, demand fully met")
    sign = "+" if r["net"] >= 0 else "-"
    return f"Round {r['round']} recap: net {sign}{abs(r['net']):.0f} funds", "\n".join(lines)


def render_round_recap():
    summary, details = round_recap_text()
    document.getElementById("round-recap-summary").innerText = summary
    document.getElementById("round-recap-body").innerText = details


# C-10 -- difficulty presets: one choice that sets the three existing
# difficulty controls together (steeper demand, weather variability and the
# starting scenario). The preset is derived from those controls, never stored,
# so it can never disagree with them; any other combination reads "Custom".
DIFFICULTY_PRESETS = {
    "relaxed": {
        "label": "Relaxed",
        "steeper": False,
        "weather": False,
        "scenario": "greenfield",
        "blurb": "Greenfield start with extra funds, steady demand, no weather swings.",
    },
    "standard": {
        "label": "Standard",
        "steeper": False,
        "weather": False,
        "scenario": "standard",
        "blurb": "The default: standard start, steady demand, no weather swings.",
    },
    "operator": {
        "label": "Operator",
        "steeper": True,
        "weather": True,
        "scenario": "standard",
        "blurb": "Standard start with steeper demand growth and weather variability on renewables.",
    },
}
DIFFICULTY_PRESET_ORDER = ("relaxed", "standard", "operator")
difficulty_note = ""


def difficulty_preset_key():
    for key in DIFFICULTY_PRESET_ORDER:
        preset = DIFFICULTY_PRESETS[key]
        if (
            state.steeper_demand_growth_enabled == preset["steeper"]
            and state.weather_variability_enabled == preset["weather"]
            and state.scenario == preset["scenario"]
        ):
            return key
    return "custom"


def apply_difficulty_preset(key):
    """Sets the two toggles, and the starting scenario while it is still
    allowed to change. Returns True if the whole preset applied, False if the
    scenario part was locked (the toggles still changed)."""
    if key not in DIFFICULTY_PRESETS:
        return False
    preset = DIFFICULTY_PRESETS[key]
    state.steeper_demand_growth_enabled = preset["steeper"]
    state.weather_variability_enabled = preset["weather"]
    if state.scenario == preset["scenario"]:
        return True
    return state.apply_scenario(preset["scenario"])


def on_difficulty_preset_change(event=None):
    global difficulty_note
    key = getattr(getattr(event, "target", None), "value", None)
    if key not in DIFFICULTY_PRESETS:
        render()
        return
    applied = apply_difficulty_preset(key)
    difficulty_note = (
        "" if applied
        else "The starting scenario is locked once you build or advance, so only the toggles changed."
    )
    render()


def render_difficulty_preset():
    key = difficulty_preset_key()
    select = document.getElementById("difficulty-preset-select")
    select.value = key
    label = DIFFICULTY_PRESETS[key]["label"] if key != "custom" else "Custom"
    header = document.getElementById("difficulty-header-display")
    header.innerText = f"Difficulty: {label}" + (" | Ironman" if state.ironman else "")
    header.title = DIFFICULTY_PRESETS[key]["blurb"] if key != "custom" else "A mix of the difficulty controls."
    document.getElementById("difficulty-preset-note").innerText = difficulty_note


# SAVE-BUTTON-INTEGRATION.md contract for the shared shared/save-widget.js:
# get_state() returns every module-level mutable global (the GridState
# instance's attributes, plus the info-page toggle) as one plain,
# JSON-safe dict. get_state() deep-copies every nested mutable container
# (plant_counts, cumulative_built, plant_age, event_log, last_event, the
# history lists, last_aging_event) on the way out, so a live reference is
# never shared between the saved snapshot and continued play — same
# reasoning as SOL's serialize_state() docstring. Grid has no non-JSON-
# native types (no sets) in its state, unlike SOL's unlocked_bodies.
# load_state() is its inverse, but not a blind mirror: plant_counts,
# cumulative_built and plant_age are merged into the live dicts key-by-key
# (_merge_plant_dict) rather than replacing them wholesale, so a save
# missing a plant-type key can't drop that key from live state entirely.
def get_state():
    if sandbox_active:  # Z-18: a save, an autosave or a leaderboard read while the sandbox is on is the REAL game
        return copy.deepcopy(_sandbox_real["snapshot"])
    return {
        "round_number": state.round_number,
        "demand": state.demand,
        "funds": state.funds,
        "plant_counts": copy.deepcopy(state.plant_counts),
        "cumulative_built": copy.deepcopy(state.cumulative_built),
        "emissions": state.emissions,
        "event_log": copy.deepcopy(state.event_log),
        "last_event": copy.deepcopy(state.last_event),
        "clean_fraction_log": list(state.clean_fraction_log),
        "emissions_history": list(state.emissions_history),
        "avg_renewable_cost_history": list(state.avg_renewable_cost_history),
        "renewable_unlocked": state.renewable_unlocked,
        "plant_age": copy.deepcopy(state.plant_age),
        "global_reference_emissions": state.global_reference_emissions,
        "global_reference_emissions_history": list(state.global_reference_emissions_history),
        "bau_emissions": state.bau_emissions,
        "last_aging_event": copy.deepcopy(state.last_aging_event),
        "info_page_open": info_page_open,
        "maintenance_actions_count": state.maintenance_actions_count,
        "current_clean_streak": state.current_clean_streak,
        "best_clean_streak": state.best_clean_streak,
        "seen_retire_callout": state.seen_retire_callout,
        "seen_maintain_callout": state.seen_maintain_callout,
        "renewable_50_reached": state.renewable_50_reached,
        "lifetime_revenue": state.lifetime_revenue,
        "lifetime_build_spend": state.lifetime_build_spend,
        "lifetime_maintenance_spend": state.lifetime_maintenance_spend,
        "lifetime_disruption_spend": state.lifetime_disruption_spend,
        "steeper_demand_growth_enabled": state.steeper_demand_growth_enabled,
        "weather_variability_enabled": state.weather_variability_enabled,
        **(
            {
                "regional_grid": {
                    "total_shared": state.regional_grid_total_shared,
                    "total_shortfall_cost": state.regional_grid_total_shortfall_cost,
                    "total_revenue": state.regional_grid_total_revenue,
                }
            }
            if state.regional_grid_connected else {}
        ),
        "scenario": state.scenario,
        **(
            {"shadow": {"scenario": shadow_scenario, "actions": [dict(a) for a in shadow_actions]}}
            if shadow_scenario is not None else {}
        ),
        **({"real_grid": real_grid_choice} if real_grid_choice is not None else {}),
        "demand_response_level": state.demand_response_level,
        "weather_log": list(state.weather_log),
        "policy_lever_available": state.policy_lever_available,
        "active_policy": copy.deepcopy(state.active_policy),
        "last_policy_lever_round_offered": state.last_policy_lever_round_offered,
        "maintenance_schedule": dict(state.maintenance_schedule),
        "stored_energy": state.stored_energy,
        "arbitrage_mode": state.arbitrage_mode,
        "arbitrage_revenue_total": state.arbitrage_revenue_total,
        "emergency": copy.deepcopy(state.emergency),
        "career": copy.deepcopy(career),
        "funds_history": list(state.funds_history),
        "demand_history": list(state.demand_history),
        "aging_breakdown_count": state.aging_breakdown_count,
        "first_90_clean_round": state.first_90_clean_round,
        "last_round_recap": copy.deepcopy(state.last_round_recap),
        # 2026-10-08 batch: the seeded run, loadout, peek, Perfect Round streak, Ironman, nicknames, grants.
        "seed": state.seed,
        "start_option": state.start_option,
        "immunity_available": state.immunity_available,
        "immunity_used": state.immunity_used,
        "peeked_round": state.peeked_round,
        "perfect_streak": state.perfect_streak,
        "best_perfect_streak": state.best_perfect_streak,
        "ironman": state.ironman,
        "plant_names": {t: list(state.plant_name_list(t)) for t in PLANT_TYPES},
        "name_serial": dict(state.name_serial),
        "last_eulogy": copy.deepcopy(state.last_eulogy),
        "grant_offer": copy.deepcopy(state.grant_offer),
        "grant_effects": dict(state.grant_effects),
        "last_grant_message": state.last_grant_message,
        # Write-only projection (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) — always
        # freshly recomputed, never read back in load_state() below.
        "summary": steward_summary(),  # B-23: write-only, never read back
        "achievements_earned": achievement_ids_earned(),
    }


def _merge_plant_dict(live, saved):
    """Writes a saved per-plant-type dict into the live one key-by-key,
    rather than replacing it wholesale. The key set (PLANT_TYPES) belongs
    to game.py, not to the save: a save written before a plant type
    existed (or a hand-edited/truncated payload) can be missing one of
    those keys, and every consumer (render(), total_capacity(),
    plant_cost(), ...) does live[plant_type] unconditionally for every
    type in PLANT_TYPES — a wholesale replace would drop the missing key
    from the dict entirely and crash on the very next access, after the
    save widget already reported a successful load. Keys the save doesn't
    know about simply keep their current live value."""
    for plant_type in live:
        if plant_type in saved:
            live[plant_type] = saved[plant_type]


def _as_int(value, default, minimum=0, maximum=None):
    """Validation helper for hand-edited/corrupt saves: bool and non-numeric
    values fall back to the default, numbers are clamped into range."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return default
    value = int(value)
    if value < minimum:
        return minimum
    if maximum is not None and value > maximum:
        return maximum
    return value


def _as_finite_nonneg_float(value, default):
    """Same spirit as _as_int, for a plain non-negative float total (C3's
    regional-grid running totals): bool/non-numeric/NaN/inf all fall back
    to the default, and a negative value is floored at 0."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    value = float(value)
    if value != value or value in (float("inf"), float("-inf")):
        return default
    return max(0.0, value)


def _load_shadow(data):
    """C21: the shadow grid's saved config; anything malformed loads as off."""
    global shadow_scenario
    shadow_actions.clear()
    shadow_scenario = None
    saved = data.get("shadow")
    if not isinstance(saved, dict):
        return
    scenario = saved.get("scenario")
    if not isinstance(scenario, str) or scenario not in SCENARIOS:
        return
    shadow_scenario = scenario
    actions = saved.get("actions")
    if isinstance(actions, list):
        for action in actions:
            if not isinstance(action, dict):
                continue
            rnd, kind, plant = action.get("round"), action.get("kind"), action.get("type")
            if (
                isinstance(rnd, int) and not isinstance(rnd, bool) and rnd >= 1
                and kind in ("build", "retire") and isinstance(plant, str) and plant in PLANT_TYPES
            ):
                shadow_actions.append({"round": rnd, "kind": kind, "type": plant})
        del shadow_actions[:-SHADOW_MAX_ACTIONS]


def _load_round3_fields(data):
    """Validated restore of the round-3 fields (C7/C17/C19/C23) that
    get_state() previously never saved, so they silently reset on every
    load. Anything malformed falls back to that field's default."""
    state.demand_response_level = _as_int(data.get("demand_response_level"), state.demand_response_level, 0, 200)
    log = data.get("weather_log", state.weather_log)
    if isinstance(log, list):
        state.weather_log = [str(x) for x in log if isinstance(x, str)][-WEATHER_LOG_MAX_ENTRIES:]
    available = data.get("policy_lever_available", state.policy_lever_available)
    state.policy_lever_available = available if isinstance(available, bool) else False
    policy = data.get("active_policy", state.active_policy)
    if (
        isinstance(policy, dict)
        and policy.get("type") in ("carbon_pricing", "renewable_subsidy")
        and _as_int(policy.get("rounds_remaining"), 0, 0, POLICY_LEVER_DURATION) > 0
    ):
        state.active_policy = {
            "type": policy["type"],
            "rounds_remaining": _as_int(policy["rounds_remaining"], 1, 1, POLICY_LEVER_DURATION),
        }
    else:
        state.active_policy = None
    state.last_policy_lever_round_offered = _as_int(
        data.get("last_policy_lever_round_offered"), state.last_policy_lever_round_offered, 0
    )
    schedule = data.get("maintenance_schedule")
    if isinstance(schedule, dict):
        for plant_type in PLANT_TYPES:
            interval = schedule.get(plant_type)
            if isinstance(interval, int) and not isinstance(interval, bool) and interval in MAINTENANCE_SCHEDULE_OPTIONS:
                state.maintenance_schedule[plant_type] = interval
    _load_arbitrage_and_emergency(data)


def _load_regional_grid(data):
    """C3: `regional_grid` is only ever present in a save when the switch
    was on (get_state()'s own convention, matching the C21 `shadow` field
    right above it) -- its absence means "never connected", not "reset to
    off", so a save from before this connected the grid stays connected."""
    payload = data.get("regional_grid")
    if not isinstance(payload, dict):
        return
    state.regional_grid_connected = True
    state.regional_grid_total_shared = _as_finite_nonneg_float(
        payload.get("total_shared"), state.regional_grid_total_shared
    )
    state.regional_grid_total_shortfall_cost = _as_finite_nonneg_float(
        payload.get("total_shortfall_cost"), state.regional_grid_total_shortfall_cost
    )
    state.regional_grid_total_revenue = _as_finite_nonneg_float(
        payload.get("total_revenue"), state.regional_grid_total_revenue
    )


def _finite_number(value, default=0.0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
        return default
    if value in (float("inf"), float("-inf")):
        return default
    return value


def _number_list(raw, fallback):
    if not isinstance(raw, list) or not all(
        not isinstance(v, bool) and isinstance(v, (int, float)) and v == v for v in raw
    ):
        return list(fallback)
    return list(raw)


def _load_round_recap(raw):
    """C-8: adopt a saved recap only as a fully validated dict; anything
    else (missing, wrong shape) leaves no recap rather than crashing render()."""
    if not isinstance(raw, dict):
        return None
    scheduled = []
    for entry in raw.get("scheduled") if isinstance(raw.get("scheduled"), list) else []:
        if isinstance(entry, dict) and entry.get("plant") in PLANT_LABEL:
            scheduled.append({"plant": entry["plant"], "cost": max(0.0, _finite_number(entry.get("cost")))})
    weather = raw.get("weather_pct")
    plant = raw.get("aging_plant")
    kind = raw.get("disruption_type")
    return {
        "round": _as_int(raw.get("round"), 1, 1),
        "net": _finite_number(raw.get("net")),
        "base_revenue": max(0.0, _finite_number(raw.get("base_revenue"))),
        "arbitrage": max(0.0, _finite_number(raw.get("arbitrage"))),
        "regional": max(0.0, _finite_number(raw.get("regional"))),
        "regional_shortfall": max(0.0, _finite_number(raw.get("regional_shortfall"))),
        "scheduled": scheduled,
        "weather_pct": None if weather is None else _finite_number(weather),
        "disruption_loss": max(0.0, _finite_number(raw.get("disruption_loss"))),
        "repair_cost": max(0.0, _finite_number(raw.get("repair_cost"))),
        "aging_plant": plant if plant in PLANT_LABEL else None,
        "disruption_type": kind if kind in ("brownout", "damage") else None,
        "demand_growth": max(0.0, _finite_number(raw.get("demand_growth"))),
        "perfect_bonus": max(0.0, _finite_number(raw.get("perfect_bonus"))),
        "perfect": bool(raw.get("perfect")),
        "immunity": bool(raw.get("immunity")),
    }


def _load_round_history_fields(data):
    """C-1/GC-26/C-8: the funds and demand series, aging count, first 90%-clean
    round and last-round recap -- each defaults safely for an older save."""
    state.funds_history = _number_list(data.get("funds_history"), [])
    state.demand_history = _number_list(data.get("demand_history"), [])
    state.aging_breakdown_count = _as_int(data.get("aging_breakdown_count"), 0, 0)
    first = data.get("first_90_clean_round")
    state.first_90_clean_round = _as_int(first, 1, 1) if first is not None and not isinstance(first, bool) else None
    state.last_round_recap = _load_round_recap(data.get("last_round_recap"))


def _load_round6_fields(data):
    """2026-10-08 batch: every field validated, each defaulting safely for an older save."""
    saved_seed = seed_lib.normalize(data.get("seed", "") if isinstance(data.get("seed"), str) else "", SEED_GAME)
    if saved_seed and saved_seed.split("-")[0] == seed_lib.prefix_for(SEED_GAME):
        state.seed = saved_seed
    option = data.get("start_option")
    state.start_option = option if option in LOADOUT_NODES else None
    state.immunity_available = bool(data.get("immunity_available", False)) and state.start_option == "diplomatic_immunity"
    state.immunity_used = bool(data.get("immunity_used", False))
    state.peeked_round = _as_int(data.get("peeked_round"), 0, 0)
    state.perfect_streak = _as_int(data.get("perfect_streak"), 0, 0)
    state.best_perfect_streak = max(state.perfect_streak, _as_int(data.get("best_perfect_streak"), 0, 0))
    state.ironman = bool(data.get("ironman", False))
    state.undo_record = None
    names = data.get("plant_names") if isinstance(data.get("plant_names"), dict) else {}
    serial = data.get("name_serial") if isinstance(data.get("name_serial"), dict) else {}
    for plant_type in PLANT_TYPES:
        raw_names = names.get(plant_type) if isinstance(names.get(plant_type), list) else []
        state.plant_names[plant_type] = [n[:NAME_MAX_LEN] for n in raw_names if isinstance(n, str) and n][:300]
        state.name_serial[plant_type] = _as_int(serial.get(plant_type), len(state.plant_names[plant_type]), 0, 10 ** 6)
    eulogy = data.get("last_eulogy")
    state.last_eulogy = (
        {"round": _as_int(eulogy.get("round"), 1, 1), "text": str(eulogy.get("text", ""))[:200]}
        if isinstance(eulogy, dict) and isinstance(eulogy.get("text"), str) and eulogy.get("text")
        else None
    )
    offer = data.get("grant_offer")
    state.grant_offer = (
        {"id": offer["id"], "round": _as_int(offer.get("round"), 1, 1)}
        if isinstance(offer, dict) and offer.get("id") in GRANTS
        else None
    )
    effects = data.get("grant_effects") if isinstance(data.get("grant_effects"), dict) else {}
    state.grant_effects = {
        "fossil_surcharge": _as_int(effects.get("fossil_surcharge"), 0, 0, GRANT_CLEAN_ROUNDS),
        "breakdown_risk": _as_int(effects.get("breakdown_risk"), 0, 0, GRANT_CONTEST_ROUNDS),
    }
    message = data.get("last_grant_message")
    state.last_grant_message = message[:200] if isinstance(message, str) else ""


def _load_career(data):
    """C1: adopt a saved career only if it has finished at least as many
    runs as the live one (a stale save never rolls progress back), after
    full validation; then refresh perks."""
    global career
    saved = validate_career(data.get("career"))
    if "career" in data and saved["runs"] >= career["runs"]:
        # Keep any achievements/unlocks the live career already has.
        saved["achievements"] = sorted(set(saved["achievements"]) | set(career["achievements"]))
        saved["achievements"] = [e["id"] for e in ACHIEVEMENTS if e["id"] in saved["achievements"]]
        career = validate_career(saved)
        save_career_to_storage()
    _sync_perks()


# C-26 -- what the last load had to repair. A save missing fields (an older format, or a hand-edited or
# truncated one) used to fall back to defaults silently; now the "What's New" panel says how many and which.
LOAD_REPORT_IGNORED_KEYS = {"achievements_earned"}  # write-only: never read back
load_report = {"loaded": False, "fields": []}


def compute_load_report(data):
    """The saved fields a load had to fill in with defaults: whole keys the save lacks, and plant types
    missing inside the three per-plant dicts."""
    expected = set(get_state().keys()) - LOAD_REPORT_IGNORED_KEYS
    fields = sorted(key for key in expected if key not in data)
    for key in ("plant_counts", "cumulative_built", "plant_age"):
        saved = data.get(key)
        if isinstance(saved, dict):
            fields.extend(f"{key}.{plant_type}" for plant_type in PLANT_TYPES if plant_type not in saved)
    return fields


def load_report_text():
    if not load_report["loaded"]:
        return ""
    fields = load_report["fields"]
    if not fields:
        return "Last save loaded: complete, nothing had to be repaired."
    shown = ", ".join(fields[:8]) + (f" and {len(fields) - 8} more" if len(fields) > 8 else "")
    return (
        f"Last save loaded: repaired {len(fields)} missing field{'s' if len(fields) != 1 else ''} "
        f"with safe defaults ({shown})."
    )


# B-23: a few honest, already-computed numbers for the hub's Climate Steward page. Written into the save as a
# read-only `summary` list ({label, value, unit, note?}); never read back by load_state().
def steward_summary():
    played = len(state.clean_fraction_log)
    return [
        {"label": "Renewable share of capacity", "value": round(renewable_capacity_share() * 100), "unit": "%"},
        {"label": "Rounds played", "value": played, "unit": ""},
        {"label": "Plants built", "value": int(sum(state.cumulative_built.values())), "unit": ""},
    ]


def load_state(data):
    global info_page_open
    if sandbox_active:  # Z-18: loading a save always lands in the real game
        _sandbox_restore_real()
    load_report["fields"] = compute_load_report(data) if isinstance(data, dict) else []
    load_report["loaded"] = True

    # Every field is pulled with .get(..., <current live value>) rather
    # than bare data["key"] indexing, so a save written before a later
    # milestone/pass added a field (global_reference_emissions and
    # global_reference_emissions_history, last_aging_event and plant_age
    # all landed in Pass 2, after Milestone 1/2 saves already existed)
    # can't crash load_state() with a KeyError -- a missing key just
    # leaves that field at whatever the live state already had, the same
    # "don't drop what the save doesn't know about" philosophy
    # _merge_plant_dict already applies one level deeper.
    state.round_number = data.get("round_number", state.round_number)
    state.demand = data.get("demand", state.demand)
    state.funds = data.get("funds", state.funds)
    _merge_plant_dict(state.plant_counts, data.get("plant_counts", {}))
    _merge_plant_dict(state.cumulative_built, data.get("cumulative_built", {}))
    state.emissions = data.get("emissions", state.emissions)
    state.event_log = copy.deepcopy(data.get("event_log", state.event_log))
    state.last_event = copy.deepcopy(data.get("last_event", state.last_event))
    state.clean_fraction_log = list(data.get("clean_fraction_log", state.clean_fraction_log))
    state.emissions_history = list(data.get("emissions_history", state.emissions_history))
    state.avg_renewable_cost_history = list(
        data.get("avg_renewable_cost_history", state.avg_renewable_cost_history)
    )
    state.renewable_unlocked = data.get("renewable_unlocked", state.renewable_unlocked)
    _merge_plant_dict(state.plant_age, data.get("plant_age", {}))
    state.global_reference_emissions = data.get(
        "global_reference_emissions", state.global_reference_emissions
    )
    state.global_reference_emissions_history = list(
        data.get("global_reference_emissions_history", state.global_reference_emissions_history)
    )
    state.bau_emissions = data.get("bau_emissions", state.bau_emissions)
    state.last_aging_event = copy.deepcopy(data.get("last_aging_event", state.last_aging_event))
    info_page_open = data.get("info_page_open", info_page_open)
    state.maintenance_actions_count = data.get("maintenance_actions_count", state.maintenance_actions_count)
    state.current_clean_streak = data.get("current_clean_streak", state.current_clean_streak)
    state.best_clean_streak = data.get("best_clean_streak", state.best_clean_streak)
    state.seen_retire_callout = data.get("seen_retire_callout", state.seen_retire_callout)
    state.seen_maintain_callout = data.get("seen_maintain_callout", state.seen_maintain_callout)
    state.renewable_50_reached = data.get("renewable_50_reached", state.renewable_50_reached)
    state.lifetime_revenue = data.get("lifetime_revenue", state.lifetime_revenue)
    state.lifetime_build_spend = data.get("lifetime_build_spend", state.lifetime_build_spend)
    state.lifetime_maintenance_spend = data.get("lifetime_maintenance_spend", state.lifetime_maintenance_spend)
    state.lifetime_disruption_spend = data.get("lifetime_disruption_spend", state.lifetime_disruption_spend)
    state.steeper_demand_growth_enabled = data.get(
        "steeper_demand_growth_enabled", state.steeper_demand_growth_enabled
    )
    state.weather_variability_enabled = data.get(
        "weather_variability_enabled", state.weather_variability_enabled
    )
    _load_regional_grid(data)
    saved_scenario = data.get("scenario", state.scenario)
    state.scenario = saved_scenario if saved_scenario in SCENARIOS else "standard"
    _load_shadow(data)
    global real_grid_choice
    saved_real = data.get("real_grid")
    real_grid_choice = saved_real if isinstance(saved_real, str) and saved_real in REAL_GRIDS else None
    _load_round3_fields(data)
    _load_round_history_fields(data)
    _load_career(data)
    _load_round6_fields(data)
    # "achievements_earned" is intentionally never read back here — see
    # get_state()'s comment and ACHIEVEMENTS-SYSTEM-DESIGN.md §1.

    render()
    _seed_achievement_toast_baseline()
    _sandbox_notify_page()
    return True


# --- Z-18: entering and leaving the practice sandbox ---------------------------------------------
# shared/sandbox-mode.js calls sandbox_enter() / sandbox_leave() / sandbox_is_active() through Pyodide and
# draws the "Sandbox: nothing here is saved" banner. The real game is set aside, never edited: the
# module-level `state` is simply pointed at a SandboxGridState, and every other piece of module state a
# save reads (career, the shadow twin, the real-grid compare, the info page flag) is stashed and put back.
sandbox_active = False
_sandbox_real = None
_SANDBOX_STASHED = (
    "info_page_open", "shadow_scenario", "shadow_actions", "real_grid_choice", "last_finish_records",
    "auto_advance_message", "run_setup_message", "difficulty_note", "career_data_message",
    "renewable_milestone_visible", "retire_callout_visible", "maintain_callout_visible", "career",
)


def _sandbox_fresh_globals():
    return {
        "shadow_scenario": None, "shadow_actions": [], "real_grid_choice": None, "last_finish_records": [],
        "auto_advance_message": "", "run_setup_message": "", "difficulty_note": "", "career_data_message": "",
        "renewable_milestone_visible": False, "retire_callout_visible": False, "maintain_callout_visible": False,
    }


def _sandbox_notify_page():
    """Tells shared/sandbox-mode.js to re-read sandbox_active() (the banner and button follow it)."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    shared = getattr(window, "NoyvjSandbox", None)
    if shared is not None:
        shared.sync()


def sandbox_is_active():
    return sandbox_active


def sandbox_enter():
    """Sets the real game aside and starts a practice grid. True when the sandbox is on."""
    global state, sandbox_active, _sandbox_real
    if sandbox_active:
        return True
    snapshot = get_state()
    _sandbox_real = {
        "state": state,
        "snapshot": snapshot,
        "earned": list(snapshot["achievements_earned"]),
        "globals": {name: globals()[name] for name in _SANDBOX_STASHED},
    }
    sandbox_active = True
    state = new_sandbox_state("standard")
    globals().update(_sandbox_fresh_globals())
    render()
    return True


def _sandbox_restore_real():
    """Puts the real game back exactly as it was (no render; callers do that)."""
    global state, sandbox_active, _sandbox_real
    real = _sandbox_real
    sandbox_active = False
    _sandbox_real = None
    if real is None:
        return
    state = real["state"]
    globals().update(real["globals"])
    _seed_achievement_toast_baseline()


def sandbox_leave():
    """Leaves the sandbox; the real game is back and untouched. True when it is."""
    if not sandbox_active:
        return True
    _sandbox_restore_real()
    render()
    return True


def setup():
    global career
    career = load_career_from_storage()
    _sync_perks()
    state.apply_scenario("standard")
    # index.html already marks this hidden via the `hidden` attribute, but
    # that markup default doesn't exist for the pytest fake-DOM harness (a
    # FakeElement starts with hidden=False) -- setting it explicitly here
    # keeps both environments consistent and costs nothing in a real
    # browser, where it's already true.
    document.getElementById("achievement-toast").hidden = True
    document.getElementById("disruption-toast").hidden = True
    for plant_type in PLANT_TYPES:
        document.getElementById(f"{plant_type}-build-button").addEventListener(
            "click", create_proxy(_make_build_handler(plant_type))
        )
        document.getElementById(f"{plant_type}-retire-button").addEventListener(
            "click", create_proxy(_make_retire_handler(plant_type))
        )
        document.getElementById(f"{plant_type}-maintain-button").addEventListener(
            "click", create_proxy(_make_maintain_handler(plant_type))
        )
        document.getElementById(f"{plant_type}-maintenance-schedule-select").addEventListener(
            "change", create_proxy(_make_maintenance_schedule_handler(plant_type))
        )
    document.getElementById("shadow-select").addEventListener("change", create_proxy(on_shadow_change))
    document.getElementById("real-grid-select").addEventListener("change", create_proxy(on_real_grid_change))
    document.getElementById("regional-grid-connect-button").addEventListener(
        "click", create_proxy(on_connect_regional_grid)
    )
    document.getElementById("advance-round-button").addEventListener(
        "click", create_proxy(on_advance_round)
    )
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    document.getElementById("summary-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_summary_panel)
    )
    document.getElementById("renewable-milestone-dismiss-button").addEventListener(
        "click", create_proxy(on_dismiss_renewable_milestone)
    )
    document.getElementById("retire-callout-dismiss-button").addEventListener(
        "click", create_proxy(on_dismiss_retire_callout)
    )
    document.getElementById("maintain-callout-dismiss-button").addEventListener(
        "click", create_proxy(on_dismiss_maintain_callout)
    )
    document.getElementById("steeper-demand-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_steeper_demand)
    )
    document.getElementById("weather-variability-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_weather_variability)
    )
    document.getElementById("scenario-toggle-button").addEventListener(
        "click", create_proxy(on_cycle_scenario)
    )
    document.getElementById("weather-log-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_weather_log)
    )
    document.getElementById("career-toggle-button").addEventListener("click", create_proxy(on_toggle_career))
    document.getElementById("career-finish-button").addEventListener("click", create_proxy(on_finish_run))
    for plant_type in GENERATION_TYPES:
        mix_row = document.getElementById(f"{plant_type}-mix-row")
        for event_name, entering in (("mouseenter", True), ("focus", True), ("mouseleave", False), ("blur", False)):
            mix_row.addEventListener(event_name, create_proxy(_make_mix_hover_handler(plant_type, entering)))
    document.getElementById("start-option-select").addEventListener("change", create_proxy(on_start_option_change))
    document.getElementById("run-seed-apply-button").addEventListener("click", create_proxy(on_apply_run_seed))
    document.getElementById("ironman-toggle-button").addEventListener("click", create_proxy(on_toggle_ironman))
    document.getElementById("undo-build-button").addEventListener("click", create_proxy(on_undo_build))
    document.getElementById("grant-accept-button").addEventListener("click", create_proxy(on_accept_grant))
    document.getElementById("grant-decline-button").addEventListener("click", create_proxy(on_decline_grant))
    document.getElementById("peek-forecast-button").addEventListener("click", create_proxy(on_peek_forecast))
    document.getElementById("career-export-button").addEventListener("click", create_proxy(on_export_career))
    document.getElementById("career-import-button").addEventListener("click", create_proxy(on_import_career))
    document.getElementById("career-reset-button").addEventListener("click", create_proxy(on_reset_career))
    document.getElementById("auto-advance-button").addEventListener("click", create_proxy(on_auto_advance))
    document.getElementById("difficulty-preset-select").addEventListener(
        "change", create_proxy(on_difficulty_preset_change)
    )
    document.getElementById("arbitrage-mode-button").addEventListener(
        "click", create_proxy(on_cycle_arbitrage_mode)
    )
    document.getElementById("demand-response-button").addEventListener(
        "click", create_proxy(on_invest_demand_response)
    )
    document.getElementById("policy-accept-carbon-pricing-button").addEventListener(
        "click", create_proxy(on_enact_carbon_pricing)
    )
    document.getElementById("policy-accept-renewable-subsidy-button").addEventListener(
        "click", create_proxy(on_enact_renewable_subsidy)
    )
    document.getElementById("policy-decline-button").addEventListener(
        "click", create_proxy(on_decline_policy)
    )
    render()
    _seed_achievement_toast_baseline()


setup()
