"""Fixed numbers and content tables: costs, capacity and policy definitions, strain levels, the Crisis Calendar and Council tables, autopilot choices, star goals, plus the small pure helpers (trend arrows, sparklines, number checks). No state."""


STARTING_FUNDS = 300.0

# A receiving region has some baseline economic activity of its own,
# independent of any arrivals — this is what lets a region build capacity
# ahead of pressure, not just react to it once people are already arriving.
BASE_REGIONAL_INCOME_PER_ROUND = 50.0

CAPACITY_TYPES = ["housing", "services", "infrastructure"]

CAPACITY_LABEL = {
    "housing": "Housing",
    "services": "Integration Services",
    "infrastructure": "Infrastructure",
}

CAPACITY_ICON = {
    "housing": "\U0001F3E0",
    "services": "\U0001F4DA",
    "infrastructure": "\U0001F6E0️",
}

# I7: a one-line effect summary per capacity investment row, since
# previously this was only explained inside the pressure section's info
# toggle -- easy to miss from the investment row itself, where the
# decision actually gets made.
CAPACITY_EFFECT_SUMMARY = {
    "housing": "Reduces strain. Doesn't speed up integration.",
    "services": "Reduces strain, and is the only capacity that moves pending arrivals to integrated.",
    "infrastructure": "Reduces strain. Doesn't speed up integration.",
}

INVEST_COST = {
    "housing": 20.0,
    "services": 20.0,
    "infrastructure": 25.0,
}

# Capacity units gained per investment — infrastructure is the most
# expensive but also the most durable/broadly useful, which M3's strain
# system will lean on.
CAPACITY_PER_INVESTMENT = {
    "housing": 10.0,
    "services": 8.0,
    "infrastructure": 6.0,
}

# I1 (planning/TODO.md "Per-game: Drift"): a second receiving region, a
# neighbouring district with a different starting profile -- plenty of
# housing already but no integration services, little money, and a higher
# background pressure -- that the player runs alongside the main region
# (opens after NEIGHBOR_MIN_ROUND rounds, so the core loop comes first).
# I7 links the two: a well-prepared main region can send funds to the
# neighbour (NEIGHBOR_SUPPORT_AMOUNT each time, only while its own strain is
# below "strained" and it keeps a NEIGHBOR_SUPPORT_RESERVE cushion), and it
# has a reason to: a neighbour left in critical strain pushes
# NEIGHBOR_SPILLOVER_ARRIVALS extra people per round on into the main region.
NEIGHBOR_MIN_ROUND = 3
NEIGHBOR_START_FUNDS = 100.0
NEIGHBOR_START_HOUSING = 30.0
NEIGHBOR_START_ARRIVALS = 20.0
NEIGHBOR_START_SEVERITY = 3.0
NEIGHBOR_SUPPORT_AMOUNT = 40.0
NEIGHBOR_SUPPORT_RESERVE = 60.0
NEIGHBOR_SPILLOVER_ARRIVALS = 4.0

# I3: the policy toolkit -- three named, real-world-grounded institutional
# levers, offered beside (not instead of) the abstract housing/services/
# infrastructure split. Each can be strengthened POLICY_MAX_LEVEL times for a
# growing price; the effects are small, permanent and specific:
#   credentialing   -- streamlined recognition of foreign qualifications puts
#                      arrivals' skills to work sooner: integrated people
#                      contribute more funds back each round.
#   language_access -- funded language classes and interpreters let services
#                      reach people faster: higher integration throughput.
#   sponsorship     -- community and private sponsorship networks absorb part of
#                      the load informally: extra effective capacity against
#                      strain.
POLICIES = {
    "credentialing": {
        "label": "Streamlined Credentialing", "icon": "\U0001F4DC",
        "blurb": "+15% funds contributed back by integrated people, per level.",
        "effect_per_level": 0.15,
    },
    "language_access": {
        "label": "Language-Access Funding", "icon": "\U0001F5E3\uFE0F",
        "blurb": "+15% integration throughput, per level.",
        "effect_per_level": 0.15,
    },
    "sponsorship": {
        "label": "Community Sponsorship", "icon": "\U0001F91D",
        "blurb": "+6 effective capacity against strain, per level.",
        "effect_per_level": 6.0,
    },
}
# I29: cross-region learning. Bringing any region to Thriving once teaches the
# player's institutions something that carries over: every region started after
# that gets LEARNING_INTEGRATION_BONUS faster integration, permanently. Kept per
# browser (like the personal best, deliberately not part of a save code), and
# only for regions that BEGIN after the unlock, so the region that earned it
# doesn't double-dip.
LEARNING_STORAGE_KEY = "drift_cross_region_learning_v1"
LEARNING_INTEGRATION_BONUS = 0.10

# I25: the second wave. Once the first arrivals have largely integrated (and at
# least SECOND_WAVE_MIN_ROUND rounds have passed) a larger wave arrives for
# SECOND_WAVE_ROUNDS rounds at SECOND_WAVE_ARRIVALS_MULTIPLIER times the usual
# arrivals: a test of whether the capacity and services you built actually
# hold, not a punishment. It is announced the round before it lands, happens
# once per region, and ends with a plain verdict. The verdict is "held" if
# strain never left the stable/strained bands during the wave.
SECOND_WAVE_MIN_ROUND = 10
SECOND_WAVE_TRIGGER_INTEGRATION = 0.7
SECOND_WAVE_ROUNDS = 5
SECOND_WAVE_ARRIVALS_MULTIPLIER = 2.0

POLICY_BASE_COST = 60.0
POLICY_MAX_LEVEL = 3

# Displacement pressure: background climate severity rises steadily and
# largely outside the player's control (mirrors Thaw's background
# trajectory), and arrivals each round scale with it. This is the
# pressure the region's capacity gets measured against starting in
# Milestone 3 — not something the player causes or can dial down, only
# something they can prepare for.
BACKGROUND_SEVERITY_RISE_PER_ROUND = 0.5
BASE_ARRIVALS_PER_ROUND = 5.0
ARRIVALS_PER_SEVERITY_POINT = 3.0

# I13 -- opt-in "accelerated background severity" difficulty variant, same
# pattern as Grid's C16/C4 opt-in toggles: off by default, persisted
# across save/load, and it only ever changes how fast background_severity
# itself rises -- never touches arrivals_this_round()/strain math directly
# (those already scale off background_severity, so this one knob is
# enough to make the whole run harder without a second parallel system).
ACCELERATED_SEVERITY_MULTIPLIER = 2.0

# Strain: how much cumulative arrivals outrun cumulative capacity. Soft
# consequence only — strain eats into the region's own income (service
# shortfalls and friction cost money) but never blocks play or zeroes
# funds outright, since strain_fraction is naturally capped at 1.0.
STRAIN_LEVEL_THRESHOLDS = [
    (0.0, "stable"),
    (0.25, "strained"),
    (0.6, "critical"),
]

# Integration payoff: services capacity is the region's throughput for
# moving arrived people from "pending" to "integrated" — language,
# employment, education access. Integrated people contribute back to
# the regional economy every round after that, which is what makes
# integration net-positive rather than a permanent drain: a services
# investment (cost 20, +8 capacity) pays for itself in about 6 rounds
# once integration ramps up (8 * 0.3 = 2.4 people/round * 1.5/person =
# 3.6 funds/round), and keeps paying indefinitely after that.
INTEGRATION_RATE_PER_SERVICES_UNIT = 0.3
INTEGRATION_CONTRIBUTION_PER_PERSON = 1.5

# Composite wellbeing: three separately-tracked sub-scores (0-100 each)
# rather than one blended number, per the plan's explicit instruction —
# keeps the end-state legible ("service quality is fine but cohesion is
# lagging" reads very differently from one number). Wellbeing score is
# their simple average.
WELLBEING_FUNDS_SCALE = 1000.0

# The "thriving" wellbeing band -- shared by wellbeing_message(), the I5
# one-time thriving callout, and the "thriving_region" achievement, so all
# three agree on exactly the same threshold rather than three separately
# hand-copied literals.
THRIVING_WELLBEING_SCORE = 70.0

# Iteration Pass 2 — long-horizon outcomes coda: a player-triggered
# epilogue projecting the current integrated population's descendants
# forward a few generations. Framed institutionally (workforce,
# community roles, regional contribution) per this game's sensitivity
# note in CLAUDE.md's Tech notes section — this is about the region's
# long-run outcome, not any one family's story. Deliberately a rough,
# modest projection
# (not "everything reaches 100"), so it reads as hopeful rather than
# implausible.
GENERATIONS_PROJECTED = 3
GENERATION_GROWTH_MULTIPLIER = 1.4
GENERATIONAL_GAP_CLOSURE = 0.75
GENERATIONAL_FUNDS_ROUNDS_EQUIVALENT = 20

# I11 -- how often a session-milestone snapshot is taken (every N
# completed rounds).
SESSION_MILESTONE_INTERVAL = 20


# Z25 save-payload audit: per-round history logs (arrivals_log/strain_log/
# wellbeing_log/subscore_log) previously grew by one entry per round with
# no cap at all -- unlike every sibling "rolling history" field elsewhere
# in this hub (Canopy's FOREST_LOG_MAX_ENTRIES, Tide's
# TICKER_FULL_HISTORY_LIMIT, Grid's WEATHER_LOG_MAX_ENTRIES, Trade
# Empire's TREND_HISTORY_MAX_POINTS). 200 matches the Canopy/Tide order of
# magnitude for a log meant to back a full-run trend graph rather than
# just a short recent window (Grid/Trade Empire's 30-entry caps back a
# much shorter recent-window display instead). A naive cap alone wasn't
# safe here: strain_log has two real consumers that need the FULL
# history, not a recent window -- average_strain()'s lifetime average
# and the "ever reached critical strain" achievement gate. Both are
# decoupled from the raw list below (see RegionState._strain_sum/
# _strain_count/_ever_critical_strain), so capping strain_log here can't
# silently turn the lifetime average into a rolling-window one or make
# the achievement un-earnable once the critical round rolls off the list.
DRIFT_LOG_MAX_ENTRIES = 200

REGION_NAME_MAX_LENGTH = 30

# I15 -- opt-in "crisis start": an already-strained region (fewer funds,
# people already arrived and waiting, severity already elevated).
CRISIS_START_FUNDS = 150.0
CRISIS_START_ARRIVALS = 60.0
CRISIS_START_SEVERITY = 2.0

# I19 -- mid-run reallocation: move a fixed block of committed capacity
# between types for a small funds fee, losing a fraction in the move.
REALLOCATION_UNITS = 10.0
REALLOCATION_FUNDS_COST = 10.0
REALLOCATION_LOSS_FRACTION = 0.2

# I6/I24 -- trend labelling.
TREND_WINDOW_ROUNDS = 5
TREND_TOLERANCE = 2.0


def trend_indicator(values, window=TREND_WINDOW_ROUNDS, tolerance=TREND_TOLERANCE):
    """improving / plateauing / declining, from the change across the
    last `window` entries. Too little history reads as plateauing."""
    if len(values) < 2:
        return "plateauing"
    delta = values[-1] - values[max(0, len(values) - 1 - window)]
    if delta > tolerance:
        return "improving"
    if delta < -tolerance:
        return "declining"
    return "plateauing"


TREND_ARROW = {"improving": "▲", "plateauing": "▶", "declining": "▼"}


def subscore_arrow(subscore_log, key):
    """I24: arrow for one sub-score, or '' before two rounds exist."""
    if len(subscore_log) < 2:
        return ""
    values = [entry.get(key, 0.0) for entry in subscore_log if isinstance(entry, dict)]
    return TREND_ARROW[trend_indicator(values, tolerance=1.0)]


SPARKLINE_ROUNDS = 20
SPARKLINE_WIDTH = 56
SPARKLINE_HEIGHT = 14


def sparkline_svg(values, rounds=SPARKLINE_ROUNDS, width=SPARKLINE_WIDTH, height=SPARKLINE_HEIGHT):
    """I-26: a tiny inline line chart of the last `rounds` values of a 0-100 score, on the fixed 0-100
    scale (so its shape reads the same round to round). Empty until two rounds exist."""
    recent = [float(v) for v in values[-rounds:]]
    if len(recent) < 2:
        return ""
    step = width / (len(recent) - 1)
    points = " ".join(
        f"{i * step:.1f},{height - max(0.0, min(100.0, v)) / 100.0 * (height - 2) - 1:.1f}"
        for i, v in enumerate(recent)
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" class="sparkline-svg" focusable="false">'
        f'<polyline points="{points}" class="sparkline-line" /></svg>'
    )


def subscore_sparkline(subscore_log, key):
    return sparkline_svg([entry.get(key, 0.0) for entry in subscore_log if isinstance(entry, dict)])


def pending_age_bands(region_state):
    """I-23: how long the people still pending have waited, as if the longest-waiting are integrated
    first (integration here takes people from the backlog, never the newest). The arrivals log gives
    each round's batch: 'new' is the latest round's arrivals, 'recent' the two before it, 'old' the rest
    (including any backlog the region started with). The three always sum to the pending population."""
    pending = region_state.pending_population()
    log = list(region_state.arrivals_log)
    bands = {}
    for key, rounds_back in (("new", 1), ("recent", 2)):
        batch = sum(log[-rounds_back:]) if log else 0.0
        del log[-rounds_back:]
        bands[key] = min(pending, batch)
        pending -= bands[key]
    bands["old"] = max(0.0, pending)
    return bands


def pending_pipeline_text(bands):
    total = sum(bands.values())
    if total < 0.5:
        return "Nobody is waiting for integration."
    return (
        f"Waiting for integration: {bands['new']:.0f} from the latest round, {bands['recent']:.0f} who have waited "
        f"2 to 3 rounds, {bands['old']:.0f} who have waited 4 or more (as if the longest-waiting are integrated first)."
    )


# I-8: spend categories (the lifetime split feeds the region-personality
# titles) and the capped per-round ledger.
SPEND_KEYS = ["housing", "services", "infrastructure", "policy", "realloc"]
LEDGER_MAX_ENTRIES = 120
LEDGER_FIELDS = [
    "round", "income", "spent", "housing", "services", "infrastructure", "policy", "realloc",
    "arrivals", "integrated_new", "integrated", "pending", "shortfall", "strain",
    "service", "economy", "cohesion", "wellbeing", "funds", "auto",
]

# ---------------------------------------------------------------------------
# Round-3 batch 2 (2026-10-08): Perfect Fit streak (GI-13), the Crisis Calendar
# with named Surge Tests (GI-2, GI-11) and the Mayor's Council upgrade tree
# (GI-1). Everything below is fixed and visible: no cards, no randomness.
# ---------------------------------------------------------------------------

# GI-13: capacity (plus sponsorship and council coverage) covers the people who
# have arrived, with at most this many units to spare. Each round in the streak
# adds PERFECT_FIT_FUNDS_PER_STREAK funds of income (streak counted up to
# PERFECT_FIT_STREAK_CAP), which lifts economic health, so precise building
# pays a little.
PERFECT_FIT_MARGIN = 12.0
PERFECT_FIT_FUNDS_PER_STREAK = 3.0
PERFECT_FIT_STREAK_CAP = 5

# GI-2 / GI-11: the Crisis Calendar. Opt-in (a toggle, off by default, like
# Accelerated Severity) so the baseline game and every record stay as they were.
# Events are on a fixed schedule: every CALENDAR_SPACING rounds from
# CALENDAR_FIRST_ROUND through round 100 the kind cycles through
# CALENDAR_CYCLE, and rounds 25, 50 and 75 are named Surge Tests. An event hits
# while the round of that number resolves; it is previewed from the round before.
# Paying the brace cost (in the preview round or the event round) softens it.
# Nothing here can end a run.
CALENDAR_FIRST_ROUND = 8
CALENDAR_SPACING = 4
CALENDAR_LAST_ROUND = 100
CALENDAR_CYCLE = ["bumper_harvest", "surge", "budget_cut", "flood"]
CALENDAR_LOG_MAX = 40
BOSS_ROUNDS = {25: "The Long Queue", 50: "The Winter Crossing", 75: "The Great Intake"}
CALENDAR_KINDS = {
    "bumper_harvest": {
        "label": "Bumper harvest", "icon": "🌾", "braceable": False, "brace_cost": 0.0,
        "income_bonus": 40.0,
        "text": "a bumper harvest adds 40 funds to the round's income",
    },
    "surge": {
        "label": "Arrivals surge", "icon": "🌊", "braceable": True, "brace_cost": 25.0,
        "arrivals_mult": 1.4, "braced_arrivals_mult": 1.2,
        "text": "40% more people arrive (20% more if you brace)",
    },
    "budget_cut": {
        "label": "Budget cut", "icon": "✂️", "braceable": True, "brace_cost": 20.0,
        "income_mult": 0.7, "braced_income_mult": 0.9,
        "text": "the round's income is cut by 30% (10% if you brace)",
    },
    "flood": {
        "label": "Flood damage", "icon": "🌧️", "braceable": True, "brace_cost": 25.0,
        "infrastructure_loss": 12.0, "braced_infrastructure_loss": 4.0,
        "text": "a flood damages 12 infrastructure capacity (4 if you brace)",
    },
    "boss": {
        "label": "Surge Test", "icon": "🏛️", "braceable": True, "brace_cost": 40.0,
        "arrivals_mult": 1.8, "braced_arrivals_mult": 1.5,
        "text": "80% more people arrive (50% more if you brace)",
    },
}


def calendar_event_for_round(round_number):
    """The fixed event for a round as a dict {round, kind, name}, or None."""
    if round_number in BOSS_ROUNDS:
        return {"round": round_number, "kind": "boss", "name": BOSS_ROUNDS[round_number]}
    if (
        CALENDAR_FIRST_ROUND <= round_number <= CALENDAR_LAST_ROUND
        and (round_number - CALENDAR_FIRST_ROUND) % CALENDAR_SPACING == 0
    ):
        index = ((round_number - CALENDAR_FIRST_ROUND) // CALENDAR_SPACING) % len(CALENDAR_CYCLE)
        kind = CALENDAR_CYCLE[index]
        return {"round": round_number, "kind": kind, "name": CALENDAR_KINDS[kind]["label"]}
    return None


# GI-1: the Mayor's Council. After every COUNCIL_INTERVAL completed rounds the
# council offers a pick; the player chooses which of three branches to deepen
# (the next tier of that branch). All nine programs are listed up front. Each is
# permanent for the run and has a trade-off. Effect keys: throughput (added to
# integration throughput), contribution (added to what integrated people pay
# back), coverage (flat units counted against arrivals, like sponsorship),
# income (flat funds per round).
COUNCIL_INTERVAL = 10
COUNCIL_BRANCHES = {
    "education": "Learning",
    "housing": "Housing",
    "transit": "Transit",
}
COUNCIL_PROGRAMS = [
    {"id": "night_school", "branch": "education", "tier": 1, "name": "Night-School Network",
     "effect": {"throughput": 0.15}, "tradeoff": {"income": -3.0},
     "text": "+15% integration throughput; -3 funds per round for teachers' wages"},
    {"id": "language_cafes", "branch": "education", "tier": 2, "name": "Language Cafes",
     "effect": {"throughput": 0.20}, "tradeoff": {"coverage": -8.0},
     "text": "+20% integration throughput; the cafes take over rooms, so -8 coverage"},
    {"id": "credential_bridge", "branch": "education", "tier": 3, "name": "Credential Bridge",
     "effect": {"contribution": 0.20}, "tradeoff": {"throughput": -0.05},
     "text": "integrated people pay back 20% more; -5% integration throughput"},
    {"id": "rapid_housing", "branch": "housing", "tier": 1, "name": "Rapid Housing Modules",
     "effect": {"coverage": 12.0}, "tradeoff": {"income": -3.0},
     "text": "+12 coverage; -3 funds per round maintenance"},
    {"id": "modular_retrofit", "branch": "housing", "tier": 2, "name": "Modular Retrofit",
     "effect": {"coverage": 18.0}, "tradeoff": {"contribution": -0.05},
     "text": "+18 coverage; integrated people pay back 5% less while neighbourhoods adjust"},
    {"id": "pattern_book", "branch": "housing", "tier": 3, "name": "Pattern Book Zoning",
     "effect": {"coverage": 25.0}, "tradeoff": {"income": -5.0},
     "text": "+25 coverage; -5 funds per round in permitting costs"},
    {"id": "transit_expansion", "branch": "transit", "tier": 1, "name": "Transit Expansion",
     "effect": {"contribution": 0.10}, "tradeoff": {"coverage": -5.0},
     "text": "integrated people pay back 10% more; -5 coverage for corridor land"},
    {"id": "commuter_corridors", "branch": "transit", "tier": 2, "name": "Commuter Corridors",
     "effect": {"contribution": 0.15}, "tradeoff": {"throughput": -0.05},
     "text": "integrated people pay back 15% more; -5% integration throughput"},
    {"id": "regional_hub", "branch": "transit", "tier": 3, "name": "Regional Hub",
     "effect": {"income": 8.0}, "tradeoff": {"coverage": -10.0},
     "text": "+8 funds per round; -10 coverage"},
]
COUNCIL_BY_ID = {p["id"]: p for p in COUNCIL_PROGRAMS}


def council_next_program(branch, picks):
    """The next unpicked tier of a branch, or None once it is complete."""
    taken = [COUNCIL_BY_ID[pid]["tier"] for pid in picks if COUNCIL_BY_ID[pid]["branch"] == branch]
    tier = (max(taken) if taken else 0) + 1
    for program in COUNCIL_PROGRAMS:
        if program["branch"] == branch and program["tier"] == tier:
            return program
    return None


# GI-5: the Budget Autopilot. Standing rules the player sets, then runs for a
# stretch of rounds. services_share: keep Integration Services at least this
# share of total capacity (None = off); surplus: where money above the reserve
# goes (None = hold it); reserve: funds always left unspent; rounds: how many
# rounds one run covers. A run stops early if strain rises a level or a
# braceable calendar event is due. Autopilot rounds are ordinary rounds (flagged
# auto in the ledger); the mode never gates an achievement.
AUTOPILOT_SERVICES_SHARES = [None, 0.4, 0.5, 0.6]
AUTOPILOT_SURPLUS_CHOICES = [None, "housing", "services", "infrastructure"]
AUTOPILOT_RESERVES = [0, 40, 100]
AUTOPILOT_ROUND_CHOICES = [5, 10, 25]
AUTOPILOT_DEFAULT_RULES = {"services_share": 0.5, "surplus": "housing", "reserve": 40, "rounds": 10}
AUTOPILOT_LOG_MAX = 40
AUTOPILOT_MAX_BUYS_PER_ROUND = 25

# GI-21: star ratings. Three independent goals, 0 to 3 stars each, judged on the
# live region; the run is banked into the run history when round
# RUN_STARS_ROUND finishes.
RUN_STARS_ROUND = 50
RUN_STARS_WELLBEING = [50.0, 70.0, 90.0]
RUN_STARS_NET_POSITIVE_ROUND = [16, 10, 7]  # first round at or under each bound
RUN_STARS_ROI = [2.0, 4.0, 8.0]  # integration paid back per fund invested
RUN_HISTORY_STORAGE_KEY = "drift_run_stars_v1"
RUN_HISTORY_MAX = 12


SERVICES_BACKBONE_TARGET = 5
BUILT_TO_SCALE_TARGET = 200.0
CENTURY_ARRIVALS_TARGET = 100.0
CRISIS_AVERTED_MIN_ROUND = 21
CENTURY_INTEGRATED_TARGET = 100.0
BACKLOG_CLEARED_MIN_ARRIVALS = 50.0
MODEL_REGION_WELLBEING_SCORE = 90.0
AHEAD_OF_SCHEDULE_MAX_ROUND = 15
STEADY_GROUND_STREAK_TARGET = 15
SUSTAINED_TRANSITION_MIN_ROUND = 40
SUSTAINED_TRANSITION_MIN_SCORE = 60.0
BALANCED_REGION_MIN_SCORE = 50.0

# I-2: Scenario Builder constants
SCENARIO_HORIZONS = [50, 100, 150]
SCENARIO_MIN_CAPACITY = 0
SCENARIO_MAX_CAPACITY = 100
SCENARIO_MIN_INCOME = 0
SCENARIO_MAX_INCOME = 200
SCENARIO_MIN_SEVERITY_RATE = 0.0
SCENARIO_MAX_SEVERITY_RATE = 2.0


def _to_float(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value, default):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _finite_number(value, default, low=0.0):
    """A finite non-bool number >= low, else default."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    if value != value or value in (float("inf"), float("-inf")):
        return default
    return max(low, float(value))


def _small_int(value, low=0):
    return isinstance(value, int) and not isinstance(value, bool) and value >= low


def _is_number(value, low=0.0):
    return (
        isinstance(value, (int, float)) and not isinstance(value, bool)
        and value == value and value not in (float("inf"), float("-inf")) and value >= low
    )


def _number_list(value):
    """A list whose every entry is a finite number (no junk to silently drop)."""
    return isinstance(value, list) and all(
        isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and v not in (float("inf"), float("-inf"))
        for v in value
    )
