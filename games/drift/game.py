"""Drift — Climate Migration & Displacement Game.

Runs in-browser via Pyodide. Milestone 1: the core allocation loop — a
receiving region invests its budget across housing, integration
services, and infrastructure capacity, round by round. Displacement
pressure, strain, integration payoff, and composite scoring land in
later milestones; this milestone is just "can the region build
capacity at all."
"""

import copy
import json
import re

import info_page
from js import document, setTimeout
from pyodide.ffi import create_proxy

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


def render_pending_pipeline():
    bands = pending_age_bands(region)
    total = sum(bands.values())
    pipeline = document.getElementById("pending-pipeline")
    text = document.getElementById("pending-pipeline-text")
    pipeline.hidden = total < 0.5
    text.hidden = False
    text.innerText = pending_pipeline_text(bands)
    for key in ("new", "recent", "old"):
        share = bands[key] / total * 100 if total >= 0.5 else 0
        segment = document.getElementById(f"pending-band-{key}")
        segment.style.width = f"{share:.1f}%"
        segment.title = f"{bands[key]:.0f} people"


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


class RegionState:
    def __init__(self):
        self.round_number = 1
        self.funds = STARTING_FUNDS
        self.capacity = {t: 0.0 for t in CAPACITY_TYPES}
        # I3: level (0..POLICY_MAX_LEVEL) of each policy lever.
        self.policy_level = {p: 0 for p in POLICIES}
        # I29: whether lessons from an earlier Thriving region apply here,
        # fixed when the region begins.
        self.learning_active = cross_region_learning
        # I25: second wave state. status: None (not yet), "warned" (lands next
        # round), "active", "done". peak_strain is the worst strain seen while
        # it was active; result is "held" or "strained" once done.
        self.second_wave_status = None
        self.second_wave_rounds_left = 0
        self.second_wave_peak_strain = 0.0
        self.second_wave_result = None
        self.background_severity = 0.0
        self.total_arrivals = 0.0
        self.arrivals_log = []
        self.strain_log = []
        # Z25: strain_log's two real consumers (average_strain()'s
        # lifetime average, the "ever reached critical strain"
        # achievement gate) need the full history's sum/count and a
        # sticky ever-true flag, not the raw list itself. Both are
        # updated once per round in advance_round() alongside the append
        # to strain_log, so the log can be capped (DRIFT_LOG_MAX_ENTRIES)
        # without either of them silently going wrong. Recomputed from
        # strain_log on load for an old save that predates this refactor
        # (see load_state()).
        self._strain_sum = 0.0
        self._strain_count = 0
        self._ever_critical_strain = False
        # I1: per-round wellbeing history for the trend graph, logged the
        # same way strain_log/arrivals_log already are -- wellbeing_score()
        # depends on cumulative funds/integration paths, not just the
        # current snapshot, so a past round's value can't be recomputed
        # after the fact and has to be recorded when it happens.
        self.wellbeing_log = []
        self.integrated_population = 0.0
        # Iteration Pass 3 — turning-point tracking: cumulative funds
        # integrated arrivals have contributed back, vs. cumulative funds
        # spent on the services investment that enabled that integration.
        # Once the former catches up to the latter, the region has
        # durably crossed from net strain to net contribution.
        self.cumulative_services_investment = 0.0
        self.cumulative_integration_contribution = 0.0
        self.net_positive_round = None
        # Achievements-framework tracked state (see the Achievements
        # section below) -- genuinely new, not derivable from anything
        # else already tracked here (ACHIEVEMENTS-SYSTEM-DESIGN.md §4's
        # "some achievements will genuinely need new tracked state" case).
        # A round's strain classifies as "stable" the same way
        # strain_level() does (below STRAIN_LEVEL_THRESHOLDS[1][0]);
        # best_stable_streak is a sticky maximum, mirroring Grid's own
        # best_clean_streak -- it only ever grows, so an achievement
        # gated on it stays earned even if a later round breaks the
        # streak.
        self.current_stable_streak = 0
        self.best_stable_streak = 0
        # I5/I19: the round the region first crossed into the "thriving"
        # wellbeing band, mirroring net_positive_round's shape exactly --
        # recorded once, stays true for the rest of the run.
        self.thriving_round = None
        # Set the moment the player ever opens the Long-Horizon Outcomes
        # coda -- coda_visible itself toggles on/off, so it can't answer
        # "has this ever been viewed" on its own.
        self.coda_ever_viewed = False
        # I13 -- opt-in "accelerated background severity" difficulty
        # variant, off by default. Persisted so it stays set across a
        # save/load, same as Grid's steeper_demand_growth_enabled.
        self.accelerated_severity_enabled = False
        # I20 -- a one-time callout the first time the arrival-dot stream's
        # visible density actually changes because of the severity toggle,
        # not just because arrivals grow on their own over time. Captured
        # once, the very first time the toggle is switched on: the dot
        # count *at that exact moment* becomes the baseline to compare
        # future renders against, so the callout is attributable to the
        # toggle rather than firing on ordinary background growth. Both
        # fields are permanent once set (never reset by toggling off/on
        # again), matching the "recorded once, stays true" shape
        # thriving_round/net_positive_round already use above.
        self.severity_toggle_dot_baseline = None
        self.severity_density_callout_shown = False
        # I15 -- a transient one-time flag, set in advance_round() the
        # round has_long_horizon_story() first flips from False to True,
        # consumed and reset by render() the next time it draws --
        # same pattern as Thaw's just_started_melting. Not part of the
        # save contract: it only ever needs to live long enough for one
        # render() call to see it.
        self.coda_just_became_available = False
        # I11 -- periodic (every SESSION_MILESTONE_INTERVAL rounds) session-
        # milestone summary: a frozen snapshot of a few headline stats as
        # of that round, not a live-updating readout, so a player can look
        # back at exactly where the run stood at a fixed checkpoint rather
        # than only ever seeing "right now" (every other display here
        # already covers that). None until the first interval completes.
        self.last_milestone_round = None
        self.last_milestone_snapshot = None
        # Transient one-time flag, same "consumed and reset by render()"
        # shape as coda_just_became_available above -- not part of the
        # save contract.
        self.milestone_just_updated = False
        # I24: per-round sub-score history (service/economy/cohesion), so
        # each gauge can show a trend arrow -- same "logged when it
        # happens" reason as wellbeing_log above.
        self.subscore_log = []
        # I23 / I5: light customization carried through the run and coda.
        self.region_name = ""
        self.coda_legacy_choice = None
        # I15: opt-in already-strained starting state; only togglable
        # before any round is played.
        self.crisis_start_enabled = False
        # I1/I7: people pushed on from a neighbouring region in critical
        # strain. Derived each round from the neighbour's state (see
        # _sync_spillover), never saved.
        self.spillover_arrivals = 0.0
        # I-8: what the funds went on. spend_by_type is lifetime (it feeds
        # the region-personality titles), round_spend is this round only
        # (reset at each Advance Round), ledger is the capped per-round table.
        self.spend_by_type = {key: 0.0 for key in SPEND_KEYS}
        self.round_spend = {key: 0.0 for key in SPEND_KEYS}
        self.ledger = []
        # I-15: decisions made since the round began (transient, never saved).
        self.round_buys = 0
        # GI-18: the round the one-per-run Rewind Token was used (None = unused).
        self.rewind_used_round = None
        # GI-13: consecutive Perfect Fit rounds and the best streak this region reached.
        self.perfect_fit_streak = 0
        self.best_perfect_fit_streak = 0
        # GI-2 / GI-11: the opt-in Crisis Calendar. braced_rounds are the event
        # rounds the player paid to brace; calendar_log records each event that hit.
        self.calendar_enabled = False
        self.braced_rounds = []
        self.calendar_log = []
        # GI-1: program ids chosen at the Mayor's Council, in order.
        self.council_picks = []
        # GI-5: the Budget Autopilot's standing rules (see AUTOPILOT_DEFAULT_RULES).
        self.autopilot = dict(AUTOPILOT_DEFAULT_RULES)
        # GI-21: the round the run's stars were banked into the run history (None = not yet).
        self.stars_banked = None
        # I-12: per-round ROI (integration paid back per fund invested) for the trend graph's ROI layer, and
        # the round the second wave began (for its event marker).
        self.roi_log = []
        self.second_wave_start_round = None

    def total_capacity(self):
        return sum(self.capacity[t] for t in CAPACITY_TYPES)

    def policy_effect(self, policy):
        """The summed effect of a policy at its current level (a fraction for
        the two multiplier policies, capacity units for sponsorship)."""
        return POLICIES[policy]["effect_per_level"] * self.policy_level[policy]

    def policy_cost(self, policy):
        return POLICY_BASE_COST * (self.policy_level[policy] + 1)

    def program_effect(self, key):
        """GI-1: the summed council effect (programs and their trade-offs) for one key."""
        total = 0.0
        for pid in self.council_picks:
            program = COUNCIL_BY_ID.get(pid)
            if program is not None:
                total += program["effect"].get(key, 0.0) + program["tradeoff"].get(key, 0.0)
        return total

    def coverage_bonus(self):
        """Capacity-equivalent units counted against arrivals without being built:
        sponsorship plus whatever the council programs add (or take away)."""
        return self.policy_effect("sponsorship") + self.program_effect("coverage")

    # ---- GI-2 / GI-11: the Crisis Calendar ----
    def calendar_event(self, round_number=None):
        """The event on a round (default: the current one), or None when the calendar is off."""
        if not self.calendar_enabled:
            return None
        return calendar_event_for_round(self.round_number if round_number is None else round_number)

    def brace_target(self):
        """The braceable, unbraced event the player can still pay to soften: the current
        round's first, else the next round's. None if there is none."""
        for target in (self.round_number, self.round_number + 1):
            event = self.calendar_event(target)
            if event and CALENDAR_KINDS[event["kind"]]["braceable"] and target not in self.braced_rounds:
                return event
        return None

    def brace(self):
        event = self.brace_target()
        if event is None:
            return False
        cost = CALENDAR_KINDS[event["kind"]]["brace_cost"]
        if self.funds < cost:
            return False
        self.funds -= cost
        self.braced_rounds.append(event["round"])
        self.round_buys += 1
        return True

    def _event_arrivals_multiplier(self):
        event = self.calendar_event()
        if event is None:
            return 1.0
        spec = CALENDAR_KINDS[event["kind"]]
        if "arrivals_mult" not in spec:
            return 1.0
        return spec["braced_arrivals_mult"] if self.round_number in self.braced_rounds else spec["arrivals_mult"]

    # ---- GI-13: Perfect Fit ----
    def is_perfect_fit(self):
        """Capacity covers everyone who has arrived with at most PERFECT_FIT_MARGIN to spare."""
        if self.total_arrivals <= 0 or self.total_capacity() <= 0:
            return False
        slack = self.total_capacity() + self.coverage_bonus() - self.total_arrivals
        return 0.0 <= slack <= PERFECT_FIT_MARGIN

    def invest_policy(self, policy):
        if policy not in POLICIES or self.policy_level[policy] >= POLICY_MAX_LEVEL:
            return False
        cost = self.policy_cost(policy)
        if self.funds < cost:
            return False
        self.funds -= cost
        self.policy_level[policy] += 1
        self._record_spend("policy", cost)
        return True

    def invest(self, capacity_type):
        cost = INVEST_COST[capacity_type]
        if self.funds < cost:
            return False
        self.funds -= cost
        self.capacity[capacity_type] += CAPACITY_PER_INVESTMENT[capacity_type]
        if capacity_type == "services":
            self.cumulative_services_investment += cost
        self._record_spend(capacity_type, cost)
        return True

    def _record_spend(self, key, amount):
        self.spend_by_type[key] += amount
        self.round_spend[key] += amount
        self.round_buys += 1

    def arrivals_this_round(self):
        """People arriving this round, rising with background severity —
        loosely tied to it, not a hard function the player can reverse-
        engineer to zero, but predictable enough to plan capacity around."""
        base = BASE_ARRIVALS_PER_ROUND + self.background_severity * ARRIVALS_PER_SEVERITY_POINT
        if self.second_wave_status == "active":
            base *= SECOND_WAVE_ARRIVALS_MULTIPLIER
        base *= self._event_arrivals_multiplier()
        return base + self.spillover_arrivals

    def strain_fraction(self):
        """0..1 — the share of the region's arrived population that
        current capacity fails to cover. Zero while capacity keeps pace
        with arrivals; rises toward (but never reaches) 1 as arrivals
        outrun capacity."""
        if self.total_arrivals <= 0:
            return 0.0
        shortfall = max(0.0, self.total_arrivals - self.total_capacity() - self.coverage_bonus())
        return min(1.0, shortfall / self.total_arrivals)

    def strain_level(self):
        level = STRAIN_LEVEL_THRESHOLDS[0][1]
        for threshold, label in STRAIN_LEVEL_THRESHOLDS:
            if self.strain_fraction() >= threshold:
                level = label
        return level

    def pending_population(self):
        """Arrived people not yet integrated — still waiting on services
        throughput to reach them."""
        return max(0.0, self.total_arrivals - self.integrated_population)

    def integration_this_round(self):
        """People who move from pending to integrated this round, capped
        by services throughput and by how many people are actually
        waiting — this cap is the lag: a region can only integrate as
        fast as its services capacity allows, regardless of funds."""
        throughput = (
            self.capacity["services"] * INTEGRATION_RATE_PER_SERVICES_UNIT
            * max(0.1, 1.0 + self.policy_effect("language_access") + (LEARNING_INTEGRATION_BONUS if self.learning_active else 0.0)
                  + self.program_effect("throughput"))
        )
        return min(self.pending_population(), throughput)

    def integration_contribution(self):
        """Funds integrated people contribute back each round — the
        net-positive core of the hope angle: integration isn't a
        permanent drain, it eventually pays for the services investment
        that enabled it and keeps paying after that."""
        return (
            self.integrated_population * INTEGRATION_CONTRIBUTION_PER_PERSON
            * max(0.1, 1.0 + self.policy_effect("credentialing") + self.program_effect("contribution"))
        )

    def has_crossed_to_net_positive(self):
        """Iteration Pass 3: once integrated arrivals' contributions have
        paid back the services investment that enabled their
        integration, the region has durably turned from net strain to
        net contribution. Stays True for the rest of the run once
        reached (see advance_round) -- a milestone the player crosses,
        not a live ratio that could flicker if a later services
        investment temporarily raises the payback bar again."""
        return self.net_positive_round is not None

    def average_strain(self):
        """Sustained strain across the whole run so far, not just the
        current snapshot — a late recovery can't fully erase an early
        crisis, mirroring Grid's average_clean_fraction. Reads the
        running _strain_sum/_strain_count (Z25) rather than summing
        strain_log itself -- strain_log is capped at
        DRIFT_LOG_MAX_ENTRIES, so summing it directly would silently
        turn this lifetime average into a rolling-window one instead."""
        if self._strain_count == 0:
            return 0.0
        return self._strain_sum / self._strain_count

    def integration_fraction(self):
        if self.total_arrivals <= 0:
            return 0.0
        return self.integrated_population / self.total_arrivals

    def service_quality(self):
        """0-100 — how well services have kept pace with arrivals over
        the whole run, not just right now."""
        return (1 - self.average_strain()) * 100

    def economic_health(self):
        """0-100 — regional funds relative to a reference scale, capped
        both ends so a very poor or very rich region reads as a clean
        floor/ceiling rather than an unbounded number."""
        return min(100.0, max(0.0, self.funds / WELLBEING_FUNDS_SCALE * 100))

    def social_cohesion(self):
        """0-100 — the share of everyone who's arrived that's actually
        been integrated so far."""
        return self.integration_fraction() * 100

    def wellbeing_score(self):
        return (self.service_quality() + self.economic_health() + self.social_cohesion()) / 3

    def has_long_horizon_story(self):
        return self.integrated_population > 0

    def projected_generational_contribution(self):
        """Extrapolates today's integration_contribution() forward a few
        generations of compounding workforce/community participation —
        the institutional version of "this pays off," on a longer
        timeline than the session itself covers."""
        contribution = self.integration_contribution()
        for _ in range(GENERATIONS_PROJECTED):
            contribution *= GENERATION_GROWTH_MULTIPLIER
        return contribution

    def projected_service_quality(self):
        current = self.service_quality()
        return current + (100 - current) * GENERATIONAL_GAP_CLOSURE

    def projected_social_cohesion(self):
        current = self.social_cohesion()
        return current + (100 - current) * GENERATIONAL_GAP_CLOSURE

    def projected_economic_health(self):
        projected_funds = self.funds + (
            self.projected_generational_contribution() * GENERATIONAL_FUNDS_ROUNDS_EQUIVALENT
        )
        return min(100.0, max(0.0, projected_funds / WELLBEING_FUNDS_SCALE * 100))

    def projected_wellbeing_score(self):
        return (
            self.projected_service_quality()
            + self.projected_economic_health()
            + self.projected_social_cohesion()
        ) / 3

    def advance_round(self, auto=False):
        completed_round = self.round_number
        spent_this_round = dict(self.round_spend)
        strain = self.strain_fraction()
        self.strain_log.append(strain)
        del self.strain_log[:-DRIFT_LOG_MAX_ENTRIES]
        # Z25: running totals + a sticky flag, updated alongside the
        # (now-capped) log above so average_strain()/
        # _ever_reached_critical_strain() never need the raw list itself.
        self._strain_sum += strain
        self._strain_count += 1
        if strain >= STRAIN_LEVEL_THRESHOLDS[2][0]:
            self._ever_critical_strain = True

        # Achievements: "stable" streak tracking, same band strain_level()
        # itself uses (below STRAIN_LEVEL_THRESHOLDS[1][0]) so this always
        # agrees with what the strain display already calls "stable".
        if strain < STRAIN_LEVEL_THRESHOLDS[1][0]:
            self.current_stable_streak += 1
        else:
            self.current_stable_streak = 0
        self.best_stable_streak = max(self.best_stable_streak, self.current_stable_streak)

        # GI-13: Perfect Fit, judged on the same standing as the strain just measured.
        if self.is_perfect_fit():
            self.perfect_fit_streak += 1
            self.best_perfect_fit_streak = max(self.best_perfect_fit_streak, self.perfect_fit_streak)
        else:
            self.perfect_fit_streak = 0

        contribution = self.integration_contribution()
        income = BASE_REGIONAL_INCOME_PER_ROUND * (1 - strain)
        income += contribution
        self.cumulative_integration_contribution += contribution
        income += self.program_effect("income")  # GI-1: council programs and their trade-offs
        income += PERFECT_FIT_FUNDS_PER_STREAK * min(self.perfect_fit_streak, PERFECT_FIT_STREAK_CAP)
        event = self.calendar_event(completed_round)  # GI-2 / GI-11
        braced = completed_round in self.braced_rounds
        if event is not None:
            spec = CALENDAR_KINDS[event["kind"]]
            if "income_mult" in spec:
                income *= spec["braced_income_mult"] if braced else spec["income_mult"]
            income += spec.get("income_bonus", 0.0)
        income = max(0.0, income)

        # I15: detect the exact round the long-horizon coda first becomes
        # available, before integrated_population actually changes below.
        coda_was_available = self.has_long_horizon_story()
        integrated_new = self.integration_this_round()
        self.integrated_population += integrated_new
        if not coda_was_available and self.has_long_horizon_story():
            self.coda_just_became_available = True

        self._advance_second_wave(strain, completed_round)
        arrivals = self.arrivals_this_round()
        self.total_arrivals += arrivals
        self.arrivals_log.append(arrivals)
        del self.arrivals_log[:-DRIFT_LOG_MAX_ENTRIES]
        severity_rise = BACKGROUND_SEVERITY_RISE_PER_ROUND
        if self.accelerated_severity_enabled:
            severity_rise *= ACCELERATED_SEVERITY_MULTIPLIER
        self.background_severity += severity_rise
        self.funds += income
        if event is not None:
            self._finish_calendar_event(event, braced)
        self.round_number += 1

        # Iteration Pass 3 — turning-point detection: the first round
        # cumulative integration contribution catches up to what was
        # spent on services is the legible moment the region flips from
        # net strain to net contribution. Recorded once and kept.
        if (
            self.net_positive_round is None
            and self.cumulative_services_investment > 0
            and self.cumulative_integration_contribution >= self.cumulative_services_investment
        ):
            self.net_positive_round = completed_round

        # I5/I19 — same "recorded once, stays true" shape as the
        # net-positive turning point above, just gated on the composite
        # wellbeing score crossing into the "thriving" band instead.
        if self.thriving_round is None and self.wellbeing_score() >= THRIVING_WELLBEING_SCORE:
            self.thriving_round = completed_round

        # I-12: ROI after this round's settled numbers, for the trend graph's ROI layer.
        self.roi_log.append(round(self.investment_roi() or 0.0, 3))
        del self.roi_log[:-DRIFT_LOG_MAX_ENTRIES]

        # I1: logged last, once every other round-end value is final.
        self.wellbeing_log.append(self.wellbeing_score())
        del self.wellbeing_log[:-DRIFT_LOG_MAX_ENTRIES]
        self.subscore_log.append(
            {
                "service": self.service_quality(),
                "economy": self.economic_health(),
                "cohesion": self.social_cohesion(),
            }
        )
        del self.subscore_log[:-DRIFT_LOG_MAX_ENTRIES]

        # I-8: the round ledger row, written once every value is final.
        self._append_ledger_row(completed_round, spent_this_round, income, arrivals, integrated_new, auto)

        # I11 -- session-milestone snapshot, taken last of all so it
        # captures this round's fully-settled values (matches wellbeing_log
        # above, which is also appended last for the same reason).
        if completed_round % SESSION_MILESTONE_INTERVAL == 0:
            self.last_milestone_round = completed_round
            self.last_milestone_snapshot = {
                "total_arrivals": self.total_arrivals,
                "integrated_population": self.integrated_population,
                "average_strain": self.average_strain(),
                "wellbeing_score": self.wellbeing_score(),
                "trend": trend_indicator(self.wellbeing_log),
            }
            self.milestone_just_updated = True

    def _finish_calendar_event(self, event, braced):
        """Apply an event's after-effects and log it. `held` is only meaningful for surges
        and Surge Tests: capacity (plus coverage) covered everyone who has now arrived."""
        spec = CALENDAR_KINDS[event["kind"]]
        if "infrastructure_loss" in spec:
            loss = spec["braced_infrastructure_loss"] if braced else spec["infrastructure_loss"]
            self.capacity["infrastructure"] = max(0.0, self.capacity["infrastructure"] - loss)
        held = None
        if "arrivals_mult" in spec:
            held = self.total_capacity() + self.coverage_bonus() >= self.total_arrivals
        self.calendar_log.append(
            {"round": event["round"], "kind": event["kind"], "braced": bool(braced), "held": held}
        )
        del self.calendar_log[:-CALENDAR_LOG_MAX]

    def _append_ledger_row(self, completed_round, spent, income, arrivals, integrated_new, auto):
        shortfall = max(
            0.0, self.total_arrivals - self.total_capacity() - self.coverage_bonus()
        )
        row = {
            "round": completed_round,
            "income": income,
            "spent": sum(spent.values()),
            "housing": spent["housing"],
            "services": spent["services"],
            "infrastructure": spent["infrastructure"],
            "policy": spent["policy"],
            "realloc": spent["realloc"],
            "arrivals": arrivals,
            "integrated_new": integrated_new,
            "integrated": self.integrated_population,
            "pending": self.pending_population(),
            "shortfall": shortfall,
            "strain": self.strain_fraction(),
            "service": self.service_quality(),
            "economy": self.economic_health(),
            "cohesion": self.social_cohesion(),
            "wellbeing": self.wellbeing_score(),
            "funds": self.funds,
            "auto": bool(auto),
        }
        for key in LEDGER_FIELDS:
            if isinstance(row[key], float):
                row[key] = round(row[key], 2)
        self.ledger.append(row)
        del self.ledger[:-LEDGER_MAX_ENTRIES]
        self.round_spend = {key: 0.0 for key in SPEND_KEYS}
        self.round_buys = 0

    def _advance_second_wave(self, strain, completed_round):
        """I25: called once per round before this round's arrivals are added,
        with the strain measured at the start of the round. Warns one round
        ahead, runs the wave, then records the verdict."""
        if self.second_wave_status == "active":
            self.second_wave_peak_strain = max(self.second_wave_peak_strain, strain)
            self.second_wave_rounds_left -= 1
            if self.second_wave_rounds_left <= 0:
                self.second_wave_status = "done"
                self.second_wave_result = (
                    "held" if self.second_wave_peak_strain < STRAIN_LEVEL_THRESHOLDS[2][0] else "strained"
                )
        elif self.second_wave_status == "warned":
            self.second_wave_status = "active"
            self.second_wave_start_round = completed_round
            self.second_wave_rounds_left = SECOND_WAVE_ROUNDS
            self.second_wave_peak_strain = strain
        elif (
            self.second_wave_status is None
            and completed_round >= SECOND_WAVE_MIN_ROUND
            and self.integration_fraction() >= SECOND_WAVE_TRIGGER_INTEGRATION
        ):
            self.second_wave_status = "warned"

    def second_wave_message(self):
        if self.second_wave_status == "warned":
            return (
                f"A second, larger wave is on its way: about {SECOND_WAVE_ARRIVALS_MULTIPLIER:.0f}x the usual arrivals "
                f"for {SECOND_WAVE_ROUNDS} rounds, starting next round. Build now."
            )
        if self.second_wave_status == "active":
            return (
                f"The second wave is here: {self.second_wave_rounds_left} round(s) left. "
                f"Worst strain so far: {self.second_wave_peak_strain * 100:.0f}%."
            )
        if self.second_wave_status == "done":
            if self.second_wave_result == "held":
                return "The second wave has passed and your capacity held: strain never reached critical."
            return "The second wave has passed. Strain went critical at its worst: what you built wasn't enough this time."
        return ""

    # I27: total funds spent across every capacity type. Each type is
    # bought at a fixed cost per fixed capacity step, so spend is exactly
    # recoverable from standing capacity -- no separate counter needed.
    def total_invested(self):
        return sum(
            self.capacity[t] / CAPACITY_PER_INVESTMENT[t] * INVEST_COST[t] for t in CAPACITY_TYPES
        )

    def investment_roi(self):
        """Integration contribution returned per fund invested (all
        capacity types), or None before anything's been invested."""
        invested = self.total_invested()
        if invested <= 0:
            return None
        return self.cumulative_integration_contribution / invested

    # I15: an already-strained start, applied only before round 1 resolves.
    def can_toggle_crisis_start(self):
        return self.round_number == 1 and self.total_capacity() == 0 and not self.strain_log

    def set_crisis_start(self, enabled):
        if not self.can_toggle_crisis_start():
            return False
        self.crisis_start_enabled = bool(enabled)
        if enabled:
            self.funds = CRISIS_START_FUNDS
            self.total_arrivals = CRISIS_START_ARRIVALS
            self.background_severity = CRISIS_START_SEVERITY
        else:
            self.funds = STARTING_FUNDS
            self.total_arrivals = 0.0
            self.background_severity = 0.0
        return True

    # I19: shift already-committed capacity between types at a small cost.
    def reallocate(self, from_type, to_type):
        if from_type == to_type or from_type not in CAPACITY_TYPES or to_type not in CAPACITY_TYPES:
            return False
        if self.capacity[from_type] < REALLOCATION_UNITS or self.funds < REALLOCATION_FUNDS_COST:
            return False
        self.funds -= REALLOCATION_FUNDS_COST
        self.capacity[from_type] -= REALLOCATION_UNITS
        self.capacity[to_type] += REALLOCATION_UNITS * (1 - REALLOCATION_LOSS_FRACTION)
        self._record_spend("realloc", REALLOCATION_FUNDS_COST)
        return True


def _load_cross_region_learning():
    """I29: reads the per-browser flag. Same lazy-import and broad-except
    posture as the personal best's storage helpers further down (defined
    after this point, hence the small standalone reader): storage can be
    refused outright in some browsers, and this is a nice-to-have."""
    try:
        import js  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return False
    storage = getattr(js, "localStorage", None)
    if storage is None:
        return False
    try:
        return storage.getItem(LEARNING_STORAGE_KEY) == "1"
    except Exception:  # noqa: BLE001
        return False


cross_region_learning = _load_cross_region_learning()
region = RegionState()

# I1/I7: the optional neighbouring region (None until opened) and how much
# support the main region has sent it.
neighbor = None
neighbor_support_sent = 0.0


def neighbor_available():
    return neighbor is not None or region.round_number >= NEIGHBOR_MIN_ROUND


def _new_neighbor_region():
    """A fresh neighbouring region: housing-rich but with no integration
    services, little money and a higher background pressure. Its own second
    wave and cross-region learning are switched off so it stays a simple
    second dial, not a second copy of every system."""
    other = RegionState()
    other.funds = NEIGHBOR_START_FUNDS
    other.capacity["housing"] = NEIGHBOR_START_HOUSING
    other.total_arrivals = NEIGHBOR_START_ARRIVALS
    other.background_severity = NEIGHBOR_START_SEVERITY
    other.learning_active = False
    other.second_wave_status = "done"
    other.second_wave_result = "held"
    return other


def open_neighbor():
    global neighbor
    if neighbor is not None or region.round_number < NEIGHBOR_MIN_ROUND:
        return False
    neighbor = _new_neighbor_region()
    _sync_spillover()
    return True


def invest_neighbor(capacity_type):
    if neighbor is None or capacity_type not in CAPACITY_TYPES:
        return False
    bought = neighbor.invest(capacity_type)
    if bought:
        region.round_buys += 1  # I-15: counts as a decision this round
    return bought


def main_region_well_prepared():
    """I7: the main region can spare help only while it is not strained and
    would still hold a reserve after sending it."""
    return (
        region.strain_fraction() < STRAIN_LEVEL_THRESHOLDS[1][0]
        and region.funds >= NEIGHBOR_SUPPORT_AMOUNT + NEIGHBOR_SUPPORT_RESERVE
    )


def support_neighbor():
    global neighbor_support_sent
    if neighbor is None or not main_region_well_prepared():
        return False
    region.funds -= NEIGHBOR_SUPPORT_AMOUNT
    neighbor.funds += NEIGHBOR_SUPPORT_AMOUNT
    neighbor_support_sent += NEIGHBOR_SUPPORT_AMOUNT
    region.round_buys += 1  # I-15
    return True


def neighbor_spillover():
    if neighbor is not None and neighbor.strain_fraction() >= STRAIN_LEVEL_THRESHOLDS[2][0]:
        return NEIGHBOR_SPILLOVER_ARRIVALS
    return 0.0


def _sync_spillover():
    region.spillover_arrivals = neighbor_spillover()


coda_visible = False


# I1: a small two-line strain/wellbeing trend graph, same rendering
# approach as Grid's own trend_graph_svg -- an HTML string built in
# Python and assigned via .innerHTML, no createElementNS/DOM-building
# needed for an SVG.
TREND_GRAPH_WIDTH = 280
TREND_GRAPH_HEIGHT = 70


def _normalize_series(series, height, lo=None, hi=None):
    """Maps a series of values to y-coordinates in [0, height], flipped so
    a higher value draws higher on the graph. An explicit lo/hi lets a
    series be normalized against a fixed scale (0-100 for wellbeing/
    strain-as-percent) rather than its own min/max, so the line's shape
    reads on an absolute scale round to round rather than always filling
    the full height."""
    if lo is None:
        lo = min(series)
    if hi is None:
        hi = max(series)
    if hi - lo < 1e-9:
        return [height / 2 for _ in series]
    return [height - ((v - lo) / (hi - lo)) * height for v in series]


TREND_LAYER_ORDER = ["strain", "wellbeing", "control", "roi", "events"]
TREND_LAYER_LABEL = {
    "strain": "Strain", "wellbeing": "Wellbeing", "control": "Passive region", "roi": "ROI", "events": "Events",
}
TREND_LAYER_DEFAULT = {"strain": True, "wellbeing": True, "control": True, "roi": False, "events": True}
TREND_RANGES = {"10": 10, "25": 25, "all": None}
TREND_ROI_SCALE = 8.0  # the ROI layer draws 0 to this many funds back per fund invested, or to its own peak if higher
TREND_TOP_MARGIN = 10  # room above the lines for the event markers
TREND_EVENT_KINDS = {
    "net_positive": "first net-positive round",
    "band": "wellbeing band change",
    "strain_peak": "strain peak",
    "realloc": "capacity moved",
    "second_wave": "second wave began",
}
TREND_EVENT_SYMBOL = {"net_positive": "◆", "band": "▲", "strain_peak": "■", "realloc": "✚", "second_wave": "⚑"}


def _trend_event_path(kind, x):
    """A small shape per kind (different outlines, so the markers read without colour)."""
    if kind == "net_positive":
        return f"M{x:.1f},-9 L{x + 4:.1f},-5 L{x:.1f},-1 L{x - 4:.1f},-5 Z"
    if kind == "band":
        return f"M{x - 4:.1f},-1 L{x + 4:.1f},-1 L{x:.1f},-9 Z"
    if kind == "strain_peak":
        return f"M{x - 3.5:.1f},-8.5 h7 v7 h-7 Z"
    if kind == "realloc":
        return f"M{x - 4:.1f},-5 h8 M{x:.1f},-9 v8"
    return f"M{x - 3:.1f},-1 L{x - 3:.1f},-9 L{x + 4:.1f},-6 L{x - 3:.1f},-3"  # second_wave: a pennant


def trend_events(region_state):
    """I-12: the run's notable rounds as [{"round", "kind", "text"}], oldest first: the first net-positive
    round, each change of wellbeing band, the strain peak, every capacity move and the second wave's start."""
    events = []
    first = region_state.round_number - len(region_state.wellbeing_log)
    previous = None
    for index, score in enumerate(region_state.wellbeing_log):
        band = wellbeing_band(score)
        if previous is not None and band != previous:
            events.append({
                "round": first + index, "kind": "band",
                "text": f"wellbeing moved from {previous} to {band} ({score:.0f})",
            })
        previous = band
    if region_state.net_positive_round is not None:
        events.append({
            "round": region_state.net_positive_round, "kind": "net_positive",
            "text": "integration became a net gain: contributions have paid back the services investment",
        })
    strain = region_state.strain_log
    if strain and max(strain) >= STRAIN_LEVEL_THRESHOLDS[1][0]:
        peak_index = strain.index(max(strain))
        events.append({
            "round": region_state.round_number - len(strain) + peak_index, "kind": "strain_peak",
            "text": f"strain peaked at {max(strain) * 100:.0f}%",
        })
    for row in region_state.ledger:
        if row.get("realloc", 0) > 0:
            events.append({"round": row["round"], "kind": "realloc", "text": "capacity moved between types"})
    if region_state.second_wave_start_round is not None:
        events.append({"round": region_state.second_wave_start_round, "kind": "second_wave", "text": "the second wave began"})
    events.sort(key=lambda event: (event["round"], list(TREND_EVENT_KINDS).index(event["kind"])))
    return events


def trend_legend_text(layers):
    parts = []
    if layers.get("strain", True):
        parts.append("Solid line: strain.")
    if layers.get("wellbeing", True):
        parts.append("Dashed: your wellbeing.")
    if layers.get("control", True):
        parts.append("Dotted grey: the passive unmanaged region's wellbeing.")
    if layers.get("roi"):
        parts.append(f"Thin dash-dot line: ROI, funds paid back per fund invested (drawn from 0 up to {TREND_ROI_SCALE:.0f} or its own peak, whichever is higher).")
    if layers.get("events", True):
        shapes = ", ".join(f"{TREND_EVENT_SYMBOL[kind]} {label}" for kind, label in TREND_EVENT_KINDS.items())
        parts.append(f"Markers along the top: {shapes}.")
    return " ".join(parts)


def trend_graph_svg(
    strain_history, wellbeing_history, control_wellbeing_history=None,
    first_round=1, layers=None, events=None, roi_history=None, view_rounds=None,
):
    """Trend graph: strain (0-100%, rising is worse) vs. composite wellbeing (0-100, rising is better) —
    both already on a 0-100 scale, so they're normalized against that fixed range rather than each other's
    min/max, keeping round-to-round shape meaningful rather than always stretched to fill the graph.

    I-12/I-16 add, all optional: `layers` (which lines and the event strip to draw), `events` (see
    trend_events), `roi_history` (right-aligned to the other series), `view_rounds` (only the last N rounds)
    and `first_round` (the round number of the first history entry, for labels). Invisible hit columns carry
    the exact values per round for the crosshair tooltip (ui.js)."""
    n_all = len(strain_history)
    if n_all < 2:
        return ""
    layers = dict(TREND_LAYER_DEFAULT, **(layers or {}))
    start = max(0, n_all - max(2, view_rounds)) if view_rounds else 0
    n = n_all - start
    strain_series = list(strain_history[start:])
    wellbeing_series = list(wellbeing_history[start:])
    xs = [i * (TREND_GRAPH_WIDTH / (n - 1)) for i in range(n)]
    strain_pct = [s * 100 for s in strain_series]
    strain_ys = _normalize_series(strain_pct, TREND_GRAPH_HEIGHT, 0, 100)
    wellbeing_ys = _normalize_series(wellbeing_series, TREND_GRAPH_HEIGHT, 0, 100)
    round_of = [first_round + start + i for i in range(n)]

    def _points(ys):
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))

    def _markers(ys, values, css_class, label):
        return "".join(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" class="trend-point {css_class}">'
            f"<title>Round {round_of[i]} -- {label}: {v:.0f}</title>"
            f"</circle>"
            for i, (x, y, v) in enumerate(zip(xs, ys, values))
        )

    drawn = []
    if layers["strain"]:
        drawn.append(f'<polyline points="{_points(strain_ys)}" class="trend-line trend-line--strain" />')
    if layers["wellbeing"]:
        drawn.append(f'<polyline points="{_points(wellbeing_ys)}" class="trend-line trend-line--wellbeing" />')

    # I2: the passive unmanaged control region's wellbeing, drawn as a third, muted dotted line (no point
    # markers -- context, not a second thing to inspect). Needs 2+ points to be a line.
    control_series = None
    if layers["control"] and control_wellbeing_history and len(control_wellbeing_history) >= 2:
        if len(control_wellbeing_history) == n_all:
            control_series = list(control_wellbeing_history[start:])
        else:
            control_series = list(control_wellbeing_history[:min(n, len(control_wellbeing_history))])
        control_ys = _normalize_series(control_series, TREND_GRAPH_HEIGHT, 0, 100)
        drawn.append(
            f'<polyline points="{_points(control_ys)}" class="trend-line trend-line--control" />'
        )

    # I-12: the ROI layer, right-aligned when an older save has fewer entries than rounds.
    roi_series = [None] * n
    if layers["roi"] and roi_history:
        padded = [None] * max(0, n_all - len(roi_history)) + list(roi_history[-n_all:])
        roi_series = padded[start:]
        roi_top = max([TREND_ROI_SCALE] + [v for v in roi_series if v is not None])
        roi_points = [
            (x, TREND_GRAPH_HEIGHT - max(0.0, v) / roi_top * TREND_GRAPH_HEIGHT)
            for x, v in zip(xs, roi_series) if v is not None
        ]
        if len(roi_points) >= 2:
            joined = " ".join(f"{x:.1f},{y:.1f}" for x, y in roi_points)
            drawn.append(f'<polyline points="{joined}" class="trend-line trend-line--roi" />')

    if layers["strain"]:
        drawn.append(_markers(strain_ys, strain_pct, "trend-point--strain", "Strain"))
    if layers["wellbeing"]:
        drawn.append(_markers(wellbeing_ys, wellbeing_series, "trend-point--wellbeing", "Wellbeing"))

    # I-12: event markers along the top strip, one shape per kind; each also lists in its round's tooltip.
    events_by_round = {}
    if layers["events"]:
        for event in events or []:
            index = event["round"] - first_round - start
            if 0 <= index < n:
                events_by_round.setdefault(index, []).append(event)
                x = xs[index]
                drawn.append(
                    f'<g class="trend-event trend-event--{event["kind"]}">'
                    f'<title>Round {event["round"]}: {event["text"]}</title>'
                    f'<path d="{_trend_event_path(event["kind"], x)}" /></g>'
                )

    # I-16: invisible hit columns + a crosshair line (ui.js moves it and shows data-tip).
    step = TREND_GRAPH_WIDTH / (n - 1)
    hits = []
    for i in range(n):
        parts = [f"Round {round_of[i]}"]
        if layers["strain"]:
            parts.append(f"strain {strain_pct[i]:.0f}%")
        if layers["wellbeing"] and i < len(wellbeing_series):
            parts.append(f"wellbeing {wellbeing_series[i]:.0f}")
        if control_series is not None and i < len(control_series):
            parts.append(f"passive region {control_series[i]:.0f}")
        if roi_series[i] is not None:
            parts.append(f"ROI {roi_series[i]:.1f}")
        for event in events_by_round.get(i, []):
            parts.append(event["text"])
        left = max(0.0, xs[i] - step / 2)
        right = min(float(TREND_GRAPH_WIDTH), xs[i] + step / 2)
        tip = "; ".join(parts[:1] + [", ".join(parts[1:])]) if len(parts) > 1 else parts[0]
        hits.append(
            f'<rect class="trend-hit" x="{left:.1f}" y="{-TREND_TOP_MARGIN}" width="{right - left:.1f}" '
            f'height="{TREND_GRAPH_HEIGHT + TREND_TOP_MARGIN}" data-x="{xs[i]:.1f}" data-round="{round_of[i]}" '
            f'data-tip="{tip}" />'
        )

    return (
        f'<svg viewBox="0 {-TREND_TOP_MARGIN} {TREND_GRAPH_WIDTH} {TREND_GRAPH_HEIGHT + TREND_TOP_MARGIN}" '
        f'class="trend-graph-svg">'
        + "".join(drawn)
        + f'<line class="trend-crosshair" x1="0" x2="0" y1="{-TREND_TOP_MARGIN}" y2="{TREND_GRAPH_HEIGHT}" />'
        + "".join(hits)
        + "</svg>"
    )


# I2: scale the region skyline's building count/height with real capacity,
# so the ambient visual reflects institutional growth instead of always
# rendering the same fixed six buildings regardless of state. Six buildings
# are authored in the markup (each with its own distinct height, see
# style.css); they're revealed one at a time as capacity grows, and every
# revealed building is scaled toward its own authored height by one shared
# vertical scale factor -- via a CSS transform, not a duplicated pixel
# height, so this file never needs to know the authored heights themselves.
REGION_VISUAL_BUILDING_IDS = ["a", "b", "c", "d", "e", "f"]
REGION_VISUAL_CAPACITY_PER_BUILDING = 20.0
REGION_VISUAL_MIN_HEIGHT_SCALE = 0.35
REGION_VISUAL_FULL_HEIGHT_CAPACITY = 150.0


def region_visual_building_count(total_capacity):
    """How many of the six authored buildings are currently revealed --
    always at least one (a region exists from round 1), one more per
    REGION_VISUAL_CAPACITY_PER_BUILDING of total capacity built, capped at
    the six actually authored in the markup."""
    unlocked = 1 + int(total_capacity // REGION_VISUAL_CAPACITY_PER_BUILDING)
    return min(unlocked, len(REGION_VISUAL_BUILDING_IDS))


def region_visual_height_scale(total_capacity):
    """A shared vertical scale (never below a visible floor, so a fresh
    region reads as "just starting out" rather than invisible) applied to
    every revealed building's own authored height -- grows smoothly toward
    REGION_VISUAL_FULL_HEIGHT_CAPACITY rather than only jumping in discrete
    steps when a new building is revealed."""
    fraction = total_capacity / REGION_VISUAL_FULL_HEIGHT_CAPACITY
    return max(REGION_VISUAL_MIN_HEIGHT_SCALE, min(1.0, fraction))


# GI-14: each capacity investment makes one building on the skyline rise and settle with a tiny dust
# puff (pure CSS, drawn in style.css; Reduce Motion and the Animation speed "Off" setting stop it).
# A building that has just been revealed pops first; otherwise the pops take turns along the skyline.
BUILDING_POP_MS = 1100
building_pop_count = 0  # transient, never saved: how many pops have run this page load


def building_to_pop(count_before, count_after, pops_so_far):
    """Index (0-based) of the skyline building that pops for an investment that took the visible
    building count from count_before to count_after."""
    count_after = max(1, min(count_after, len(REGION_VISUAL_BUILDING_IDS)))
    if count_after > count_before:
        return count_after - 1
    return pops_so_far % count_after


def _pop_building(count_before):
    global building_pop_count
    count_after = region_visual_building_count(region.total_capacity())
    index = building_to_pop(count_before, count_after, building_pop_count)
    building_pop_count += 1
    element_id = f"region-visual-building-{REGION_VISUAL_BUILDING_IDS[index]}"
    element = document.getElementById(element_id)
    # Two identical animations under two class names: swapping to the other one restarts the pop
    # when the player buys again before the last pop has finished.
    css_class = "building-pop-b" if element.classList.contains("building-pop-a") else "building-pop-a"
    _pulse(element_id, css_class, BUILDING_POP_MS)


# GI-19: a soft pulse on the strain readout whose beat quickens with the strain level and calms
# as it falls. Seconds per beat; style.css multiplies it by the Animation speed setting.
STRAIN_HEARTBEAT_SECONDS = {"stable": 6.0, "strained": 2.6, "critical": 1.2}


def strain_heartbeat_seconds(level):
    return STRAIN_HEARTBEAT_SECONDS.get(level, STRAIN_HEARTBEAT_SECONDS["stable"])


def scaled_seconds(seconds):
    """A CSS duration that follows the player's Animation speed setting (settings.js sets
    --drift-anim-scale on the page: 2 slow, 1 normal, 0.5 fast)."""
    return f"calc({seconds:.2f}s * var(--drift-anim-scale, 1))"


# I6: a one-line plain-language consequence description per strain level,
# not just the existing colour/label change on the strain bar -- so a
# player who hasn't opened the pressure section's info-toggle still knows
# what "critical" actually costs them.
STRAIN_LEVEL_CONSEQUENCE = {
    "stable": "Services are keeping pace with arrivals — no meaningful drag on income.",
    "strained": "Shortfalls are starting to bite: strain is cutting into this region's income each round.",
    "critical": "Services are badly outpaced: strain is cutting deep into income, and it will stay elevated even after you catch up.",
}


def strain_consequence_message(region_state):
    return STRAIN_LEVEL_CONSEQUENCE[region_state.strain_level()]


# I16: tie the decorative arrival-dot stream's density/speed to real
# arrivals-per-round, so the ambient visual communicates rising pressure
# instead of always animating the same fixed seven dots at a fixed
# speed. Seven dots are authored in the markup; how many are visible and
# how fast they drift both scale with arrivals_this_round().
ARRIVAL_STREAM_MAX_DOTS = 7
ARRIVAL_STREAM_ARRIVALS_PER_DOT = 5.0
ARRIVAL_STREAM_MAX_DURATION_S = 3.2  # slowest -- matches the original fixed speed
ARRIVAL_STREAM_MIN_DURATION_S = 1.2  # fastest, at/above the reference arrivals level
ARRIVAL_STREAM_DURATION_REFERENCE_ARRIVALS = 40.0


def arrival_stream_dot_count(arrivals_this_round):
    count = 1 + int(arrivals_this_round // ARRIVAL_STREAM_ARRIVALS_PER_DOT)
    return max(1, min(ARRIVAL_STREAM_MAX_DOTS, count))


def arrival_stream_animation_duration(arrivals_this_round):
    fraction = min(1.0, arrivals_this_round / ARRIVAL_STREAM_DURATION_REFERENCE_ARRIVALS)
    return ARRIVAL_STREAM_MAX_DURATION_S - fraction * (
        ARRIVAL_STREAM_MAX_DURATION_S - ARRIVAL_STREAM_MIN_DURATION_S
    )


# I20: a one-time callout the first time the arrival-dot stream's density
# visibly changes because of the accelerated-severity toggle specifically,
# not just because arrivals grow on their own over time. See RegionState's
# severity_toggle_dot_baseline/severity_density_callout_shown fields.
SEVERITY_DENSITY_CALLOUT_TEXT = (
    "You can see it: since you turned on Accelerated Severity, the "
    "arrival-dot stream above has visibly changed (more dots, moving "
    "faster) as background pressure rises quicker."
)


def maybe_flag_severity_density_change(region, visible_dot_count):
    """Sets the one-time I20 callout flag if the dot count has moved away
    from the baseline captured when the severity toggle was first switched
    on. A no-op once the flag is already set, or if no baseline exists
    (the toggle has never been turned on)."""
    if region.severity_density_callout_shown:
        return
    if region.severity_toggle_dot_baseline is None:
        return
    if visible_dot_count != region.severity_toggle_dot_baseline:
        region.severity_density_callout_shown = True


def wellbeing_message(score):
    if score >= THRIVING_WELLBEING_SCORE:
        return "This region is turning displacement into a manageable — even thriving — transition."
    if score >= 40:
        return "This region is managing, but strain and slow integration are holding it back."
    return "This region is struggling: capacity hasn't kept pace with arrivals."


# I3: an explicit in-play comparison tying the player's own integration
# coverage back to the Uganda policy model already referenced in the
# static context blurb (index.html's .context-blurb) -- previously that
# reference was flavor text only, never actually compared against the
# player's live numbers. This deliberately doesn't invent a precise
# Ugandan numeric coverage figure this game has no real source for (see
# CLAUDE.md's sensitivity note) -- it compares social_cohesion() (the
# share of arrivals actually integrated so far) against the *structural*
# standard Uganda's model is cited for: broad, near-universal access
# rather than a narrow, capacity-rationed one.
UGANDA_MODEL_COVERAGE_DESCRIPTION = (
    "near-universal access to land, work rights, and freedom of movement for arrivals"
)
UGANDA_COMPARISON_HIGH_COVERAGE = 80.0
UGANDA_COMPARISON_MID_COVERAGE = 40.0


# I20: surfaces the funds-to-economic-health scale reference point
# (economic_health()'s WELLBEING_FUNDS_SCALE denominator) directly in the
# UI, so that 0-100 scale isn't a black box the player can only infer
# from watching the number move.
def economic_health_reference_note():
    return f"Reaches 100 at {WELLBEING_FUNDS_SCALE:.0f}+ funds."


def uganda_comparison_message(region_state):
    coverage = region_state.social_cohesion()
    if coverage >= UGANDA_COMPARISON_HIGH_COVERAGE:
        standing = "matching the broad-access standard Uganda's model is cited for"
    elif coverage >= UGANDA_COMPARISON_MID_COVERAGE:
        standing = "partway toward the broad-access standard Uganda's model is cited for"
    else:
        standing = "still well short of the broad-access standard Uganda's model is cited for"
    return (
        f"Your region has integrated {coverage:.0f}% of arrivals so far — {standing}, "
        f"which extends {UGANDA_MODEL_COVERAGE_DESCRIPTION}."
    )


# I9: a real-world resettlement-outcome benchmark comparison, distinct
# from the structural Uganda-policy comparison above -- this one is a
# genuine, sourced statistic rather than a qualitative structural
# standard. Source: Migration Policy Institute, "How Are Refugees
# Faring? Integration at U.S. and State Levels" -- as of 2023, 89% of
# working-age refugees resettled in the U.S. within the previous five
# years were employed. That's a real, institutional/statistical figure
# (per this game's own sensitivity note in CLAUDE.md's Tech notes
# section), kept factual rather than editorialized: the message below
# explicitly flags that "employed" and Drift's own broader
# integration metric (language, employment, education access combined)
# aren't literally the same measurement, rather than implying a false
# apples-to-apples equivalence.
REAL_WORLD_RESETTLEMENT_EMPLOYMENT_BENCHMARK = 89.0  # percent


def resettlement_benchmark_message(region_state):
    coverage = region_state.social_cohesion()
    standing = "at or above" if coverage >= REAL_WORLD_RESETTLEMENT_EMPLOYMENT_BENCHMARK else "below"
    return (
        f"Real-world benchmark: as of 2023, {REAL_WORLD_RESETTLEMENT_EMPLOYMENT_BENCHMARK:.0f}% of "
        "working-age refugees resettled in the U.S. within the previous five years were employed "
        "(Migration Policy Institute) — a genuine, sourced outcome statistic for real resettlement "
        "systems, not the same measurement as this game's own broader integration metric (language, "
        f"employment, and education access combined). Your region has integrated {coverage:.0f}% of "
        f"arrivals so far, {standing} that reference point."
    )


# I12: once the lagging dimension is named, also note whenever a *different*
# dimension is comfortably ahead rather than always naming only the
# weak point -- so a player who's actually doing well on two of the three
# fronts hears that too, not just what still needs work.
CHECKPOINT_AHEAD_SCORE_THRESHOLD = 80.0
CHECKPOINT_AHEAD_NOTE = {
    "services": "Service quality is comfortably ahead, though — strain has stayed low across the run.",
    "economy": "Economic health is comfortably ahead, though — funds are in good shape.",
    "cohesion": "Social cohesion is comfortably ahead, though — most arrivals are already integrated.",
}


def checkpoint_message(region_state):
    """Iteration-pass addition: a plain-language read on which of the
    three wellbeing dimensions is currently lagging most, given how
    systems-dense this game is compared to the rest of the hub."""
    scores = {
        "services": (
            region_state.service_quality(),
            "Services are lagging arrival pressure this round — capacity hasn't kept up.",
        ),
        "economy": (
            region_state.economic_health(),
            "Economic health is the region's weakest point right now — funds are stretched thin.",
        ),
        "cohesion": (
            region_state.social_cohesion(),
            "Social cohesion is lagging — most arrivals still haven't been integrated yet.",
        ),
    }
    lowest_key = min(scores, key=lambda k: scores[k][0])
    message = scores[lowest_key][1]

    highest_key = max(scores, key=lambda k: scores[k][0])
    if highest_key != lowest_key and scores[highest_key][0] >= CHECKPOINT_AHEAD_SCORE_THRESHOLD:
        message += " " + CHECKPOINT_AHEAD_NOTE[highest_key]

    return message


def session_milestone_message(region_state):
    """I11: a periodic recap taken every SESSION_MILESTONE_INTERVAL rounds
    -- reads from the frozen snapshot RegionState.advance_round() took at
    that checkpoint (see its comment above), not from the region's
    current live values, so this deliberately stays fixed between
    milestones rather than quietly turning into just another live
    readout. Returns None until the first interval completes."""
    if region_state.last_milestone_round is None:
        return None
    snapshot = region_state.last_milestone_snapshot
    return (
        f"Session milestone, round {region_state.last_milestone_round}: "
        f"{snapshot['total_arrivals']:.0f} people had arrived, "
        f"{snapshot['integrated_population']:.0f} integrated, "
        f"average strain {snapshot['average_strain'] * 100:.0f}%, "
        f"wellbeing {snapshot['wellbeing_score']:.0f}"
        + (f" ({snapshot['trend']})." if snapshot.get("trend") else ".")
    )


# I17 -- a passive "unmanaged control region" for contrast: an entirely
# unmanaged region (no investment of any kind, ever) advancing through
# the exact same background-severity trajectory as the player's own
# region, including whether accelerated severity is on, so the
# comparison stays apples-to-apples. With zero player input of any kind,
# its whole trajectory is a pure function of how many rounds have
# completed plus that one toggle -- so it's recomputed fresh from round 1
# every render rather than tracked as separate live/save state (a
# simplification: if the player toggles accelerated severity mid-run,
# this recomputes as though it had been on/off for the whole run, since
# it's a passive ambient contrast, not a precise parallel save).
def _simulate_control_region(round_number, accelerated_severity_enabled, calendar_enabled=False):
    control = RegionState()
    control.accelerated_severity_enabled = accelerated_severity_enabled
    control.calendar_enabled = calendar_enabled  # the unmanaged region meets the same fixed events, unbraced
    for _ in range(round_number - 1):
        control.advance_round()
    return control


def control_region_contrast_message(control):
    return (
        "For contrast, a passive region facing the exact same arrival pressure but never "
        f"investing in any capacity would be sitting at wellbeing {control.wellbeing_score():.0f} "
        f"({control.strain_level()} strain, {control.social_cohesion():.0f}% integrated) after the "
        "same number of rounds."
    )


# I28: what triggers each strain-consequence description (tooltip text,
# built from the same thresholds strain_level() uses).
def strain_consequence_tooltip():
    strained = STRAIN_LEVEL_THRESHOLDS[1][0] * 100
    critical = STRAIN_LEVEL_THRESHOLDS[2][0] * 100
    return (
        "Strain is the share of everyone who has arrived that your total capacity doesn't "
        f"cover. This message changes with the level: stable below {strained:.0f}%, strained "
        f"from {strained:.0f}%, critical from {critical:.0f}%."
    )


CONTROL_REGION_TOOLTIP = (
    "The unmanaged control region is a passive comparison: the same arrivals and severity "
    "as yours, but with no investment ever made. It shows what preparation is worth -- it is "
    "not a forecast for your region."
)


# I9: capacity-planning forecast over the next few rounds.
FORECAST_ROUNDS = 5


def forecast_arrivals(region_state, rounds=FORECAST_ROUNDS):
    severity = region_state.background_severity
    rise = BACKGROUND_SEVERITY_RISE_PER_ROUND
    if region_state.accelerated_severity_enabled:
        rise *= ACCELERATED_SEVERITY_MULTIPLIER
    out = []
    for _ in range(rounds):
        out.append(BASE_ARRIVALS_PER_ROUND + severity * ARRIVALS_PER_SEVERITY_POINT)
        severity += rise
    return out


def forecast_message(region_state):
    arrivals = forecast_arrivals(region_state)
    needed = region_state.total_arrivals + sum(arrivals)
    have = region_state.total_capacity()
    listed = ", ".join(f"{a:.0f}" for a in arrivals)
    if have >= needed:
        verdict = f"Your {have:.0f} total capacity already covers that horizon."
    else:
        verdict = (
            f"To keep strain at zero through then, total capacity would need to reach about "
            f"{needed:.0f} (you have {have:.0f})."
        )
    return (
        f"Projected arrivals over the next {len(arrivals)} rounds, at the current background "
        f"severity trajectory: {listed} people. {verdict}"
    )


# I30: rounds until the next capacity milestone, at the pace so far.
CAPACITY_MILESTONE_STEP = 50.0


def capacity_milestone_message(region_state):
    total = region_state.total_capacity()
    target = (int(total // CAPACITY_MILESTONE_STEP) + 1) * CAPACITY_MILESTONE_STEP
    rounds_played = region_state.round_number - 1
    if rounds_played <= 0 or total <= 0:
        return f"Next capacity milestone: {target:.0f} total capacity (invest to set a pace)."
    pace = total / rounds_played
    rounds_left = max(1, int(-(-(target - total) // pace)))
    unit = "round" if rounds_left == 1 else "rounds"
    return (
        f"Next capacity milestone: {target:.0f} total capacity — about {rounds_left} {unit} "
        f"at your average pace of {pace:.1f}/round."
    )


# I27: what each fund invested has returned.
def roi_message(region_state):
    roi = region_state.investment_roi()
    if roi is None:
        return "No capacity invested yet, so nothing has been returned yet."
    services_spent = region_state.cumulative_services_investment
    services_part = ""
    if services_spent > 0:
        services_part = (
            f" Counting only Integration Services spending, {region_state.cumulative_integration_contribution / services_spent:.2f} "
            "funds returned per fund spent."
        )
    return (
        f"Across all {region_state.total_invested():.0f} funds invested, integrated arrivals have "
        f"contributed {region_state.cumulative_integration_contribution:.0f} funds back — "
        f"{roi:.2f} per fund invested.{services_part} Housing and infrastructure return nothing "
        "directly; they hold strain down so income isn't lost."
    )


# I16: a "from behind" Model Region badge.
def recovery_badge_text(region_state, ever_critical):
    if ever_critical and region_state.wellbeing_score() >= MODEL_REGION_WELLBEING_SCORE:
        return "🌟 Model Region by recovery — reached this tier after a critical-strain stretch"
    return None


# I11: thriving-band vignette, institutional framing only.
THRIVING_VIGNETTE = (
    "A thriving receiving region looks unremarkable from the outside: language classes that "
    "run at the times people can attend, credential recognition that moves in weeks not "
    "years, clinics and transit sized for the population that actually lives there. Nothing "
    "about it is a miracle -- it is the visible result of capacity built before the pressure "
    "arrived."
)


def thriving_vignette_message(region_state):
    if region_state.thriving_round is None:
        return None
    return THRIVING_VIGNETTE


# I21: coda comparison against the passive control region.
def coda_control_message(region_state, control):
    if not control.has_long_horizon_story():
        return (
            "The passive region never integrated anyone, so it has no long-horizon story: "
            f"nothing accrues generations from now. Yours projects to wellbeing "
            f"{region_state.projected_wellbeing_score():.0f}."
        )
    return (
        f"Side by side, generations from now: your region projects to wellbeing "
        f"{region_state.projected_wellbeing_score():.0f}; the passive region, "
        f"{control.projected_wellbeing_score():.0f}."
    )


# I5: symbolic final choice -- flavors the epilogue text only.
CODA_LEGACY_CHOICES = {
    "community": "Community institutions: schools, associations, and local governance reflect everyone who settled here.",
    "services": "Public services: the systems built for arrivals turned out to serve the whole region better.",
    "economy": "Local economy: new industries and trades grew from the region's expanded workforce.",
}


def coda_legacy_message(choice):
    if choice not in CODA_LEGACY_CHOICES:
        return "Choose what this region's institutions carry forward (flavor only -- it changes no numbers)."
    return "What this region carries forward — " + CODA_LEGACY_CHOICES[choice]


def region_name_prefix(name):
    return f"{name}: " if name else ""


def integration_turning_point_message(region_state):
    """Iteration Pass 3 fix: shares Loop's "dry abstraction" risk and
    Thaw's "fear without efficacy" risk -- the net-positive integration
    mechanic needs a clear, legible moment where the player notices the
    shift from strain to contribution, not just a background formula.
    Same "make the payoff felt" fix as Thaw's, applied to Drift's
    institutional-capacity frame instead of a feedback-loop frame.
    Returns None until the region has actually crossed the threshold."""
    if not region_state.has_crossed_to_net_positive():
        return None
    return (
        f"Turning point, round {region_state.net_positive_round}: this region's "
        "integrated arrivals have paid back the services investment that got "
        "them there. From here, integration is a net gain for regional "
        "capacity, not a cost."
    )


def thriving_callout_message(region_state):
    """I5: a one-time callout for the second explicit milestone this game
    tracks (thriving_round, set in advance_round the round wellbeing_score()
    first crosses THRIVING_WELLBEING_SCORE) -- same "recorded once, stays
    true, surfaced the moment it happens" shape as
    integration_turning_point_message's net-positive milestone above.
    Returns None until the region has actually reached that band."""
    if region_state.thriving_round is None:
        return None
    return (
        f"Milestone, round {region_state.thriving_round}: this region's wellbeing crossed into "
        "the thriving band. Preparedness turned displacement pressure into a genuinely good "
        "outcome here, not just a survived one."
    )


# I19: a small persistent badge for the same net-positive milestone
# integration_turning_point_message() already announces once, kept
# visible in the top status readouts for the rest of the run -- so the
# milestone stays legible even after the player has scrolled past the
# one-off callout in the Integration section, rather than only living in
# a sentence they might forget happened.
def net_positive_badge_text(region_state):
    if not region_state.has_crossed_to_net_positive():
        return None
    return f"🌱 Net-positive since round {region_state.net_positive_round}"


def _render_coda_comparison(dimension, current, projected):
    """I8 -- replaces the coda's three bare meter bars with a legible
    before/after comparison: the fill bar keeps showing the projected
    (generations-from-now) value exactly as before (same element ids,
    same width contract existing tests already check), a thin marker
    now shows where that same dimension stands today, and a values line
    spells both numbers out -- so the long-horizon payoff reads as a
    jump from a known starting point rather than an unlabeled single
    bar."""
    document.getElementById(f"coda-{dimension}-bar").style.width = f"{projected:.0f}%"
    document.getElementById(f"coda-{dimension}-before-marker").style.left = f"{current:.0f}%"
    document.getElementById(f"coda-{dimension}-values").innerText = (
        f"Today {current:.0f} → generations from now {projected:.0f}"
    )


def long_horizon_coda_message(region_state):
    return (
        f"{region_name_prefix(region_state.region_name)}Generations from now, the descendants of the {region_state.integrated_population:.0f} "
        "people this region integrated are woven into its workforce, institutions, and community "
        "leadership — not a footnote to the region's history, but a working part of it. What "
        f"started as {region_state.integration_contribution():.0f} funds/round of contribution "
        f"has grown into roughly {region_state.projected_generational_contribution():.0f} "
        "funds/round of ongoing regional participation."
    )


# ===========================================================================
# Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md) — following SOL's reference
# integration and Grid/Canopy's rollouts. Every achievement's earned
# status is a pure function of state that already exists elsewhere in
# this module, recomputed fresh every call — never a separately
# hand-maintained "earned" flag. Two achievements (steady_ground,
# long_horizon_reached) needed genuinely new tracked state
# (current_stable_streak/best_stable_streak and coda_ever_viewed,
# declared on RegionState above) — nothing else in this module records
# a stable-strain streak or whether the coda has ever been opened.
# Kept institutional/systems-level throughout, consistent with this
# game's sensitivity note in CLAUDE.md's Tech notes section: labels and
# descriptions are about regional capacity and process counts, not
# individual migrant stories.
# ===========================================================================
ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    """Same loading contract as SOL's `_read_achievements_json()` / Le
    Champ de Mots' `_read_json_asset()`: the boot script fetches
    achievements.json and hands it to Python as a window global before
    this file runs; the pytest harness's fake `js` module has no such
    attribute, so this falls through to reading the file straight off
    disk, keeping the module importable outside a real browser."""
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
# whole import — achievements are additive, not core to Drift's gameplay.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []


# ===========================================================================
# Changelog panel (site-wide goal, planning/TODO.md, origin K16: "Per-game
# in-game changelog panel, for every game"). A quick highlights view, not a
# full duplicate of CLAUDE.md/BCM114-DEV-LOG.md -- same loading contract as
# ACHIEVEMENTS above: the boot script fetches changelog.json and hands it to
# Python as a window global before this file runs, with a filesystem
# fallback for the pytest harness (no real `js.CHANGELOG_JSON` there).
# Unlike ACHIEVEMENTS, this is a flat list (no wrapping key) -- see
# changelog.json itself.
# ===========================================================================
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    """Same loading contract as `_read_achievements_json()` above."""
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


# Degrades to an empty list rather than crashing this module's whole
# import -- the changelog panel is purely informational, not core to
# Drift's gameplay.
try:
    CHANGELOG = json.loads(_read_changelog_json())
except (ValueError, OSError, NameError):
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
    # Newest first -- entries are authored newest-first in changelog.json
    # already, but sort defensively so a future out-of-order edit can't
    # silently invert the panel.
    for entry in sorted(CHANGELOG, key=lambda e: e["date"], reverse=True):
        card = document.createElement("div")
        card.className = "changelog-entry"

        date = document.createElement("p")
        date.className = "changelog-date"
        date.innerText = entry["date"]
        card.appendChild(date)

        text = document.createElement("p")
        text.className = "changelog-text"
        text.innerText = entry["entry"]
        card.appendChild(text)

        panel.appendChild(card)


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


def _services_investment_count():
    """Integration Services is invested in for a fixed cost every time
    (INVEST_COST["services"] never changes), so the number of times it's
    been bought is exactly recoverable from the cumulative funds spent on
    it -- no separate counter needed."""
    return round(region.cumulative_services_investment / INVEST_COST["services"])


def _standing_capacity_type_count():
    return sum(1 for t in CAPACITY_TYPES if region.capacity[t] > 0)


def _ever_reached_critical_strain():
    """Z25: reads the sticky _ever_critical_strain flag rather than
    scanning strain_log -- the log itself is capped at
    DRIFT_LOG_MAX_ENTRIES, so scanning it directly would make this
    achievement un-earnable once the round that crossed critical strain
    rolls off the capped list."""
    return region._ever_critical_strain


# Each checker is a zero-argument predicate read fresh off live state —
# nothing here is ever cached or hand-flagged.
ACHIEVEMENT_CHECKS = {
    "first_investment": lambda: sum(region.capacity.values()) > 0,
    "full_capacity_portfolio": lambda: all(region.capacity[t] > 0 for t in CAPACITY_TYPES),
    "services_backbone": lambda: _services_investment_count() >= SERVICES_BACKBONE_TARGET,
    "built_to_scale": lambda: region.total_capacity() >= BUILT_TO_SCALE_TARGET,
    "century_arrivals": lambda: region.total_arrivals >= CENTURY_ARRIVALS_TARGET,
    "crisis_averted": lambda: (
        region.round_number >= CRISIS_AVERTED_MIN_ROUND and not _ever_reached_critical_strain()
    ),
    "full_recovery": lambda: _ever_reached_critical_strain() and region.strain_level() == "stable",
    "turning_point_reached": lambda: region.has_crossed_to_net_positive(),
    "ahead_of_schedule": lambda: (
        region.net_positive_round is not None and region.net_positive_round <= AHEAD_OF_SCHEDULE_MAX_ROUND
    ),
    "century_integrated": lambda: region.integrated_population >= CENTURY_INTEGRATED_TARGET,
    "backlog_cleared": lambda: (
        region.total_arrivals >= BACKLOG_CLEARED_MIN_ARRIVALS and region.pending_population() <= 0.01
    ),
    "balanced_region": lambda: (
        region.service_quality() >= BALANCED_REGION_MIN_SCORE
        and region.economic_health() >= BALANCED_REGION_MIN_SCORE
        and region.social_cohesion() >= BALANCED_REGION_MIN_SCORE
    ),
    "thriving_region": lambda: region.wellbeing_score() >= THRIVING_WELLBEING_SCORE,
    "model_region": lambda: region.wellbeing_score() >= MODEL_REGION_WELLBEING_SCORE,
    "economic_engine": lambda: (
        region.cumulative_services_investment > 0
        and region.cumulative_integration_contribution >= region.cumulative_services_investment * 2
    ),
    "steady_ground": lambda: region.best_stable_streak >= STEADY_GROUND_STREAK_TARGET,
    "long_horizon_reached": lambda: region.coda_ever_viewed,
    "sustained_transition": lambda: (
        region.round_number >= SUSTAINED_TRANSITION_MIN_ROUND
        and region.wellbeing_score() >= SUSTAINED_TRANSITION_MIN_SCORE
    ),
}

# Progress readouts, only for achievements with a natural numeric
# scale-up -- a plain earned/not-yet is the honest shape for a one-shot
# or multi-condition milestone (e.g. "reach round 21 with strain never
# critical" doesn't get a fake progress bar, same judgment call Grid's
# ahead_of_the_curve/no_damage_20 make).
ACHIEVEMENT_PROGRESS = {
    "full_capacity_portfolio": lambda: (_standing_capacity_type_count(), len(CAPACITY_TYPES)),
    "services_backbone": lambda: (
        min(_services_investment_count(), SERVICES_BACKBONE_TARGET),
        SERVICES_BACKBONE_TARGET,
    ),
    "built_to_scale": lambda: (
        min(round(region.total_capacity()), round(BUILT_TO_SCALE_TARGET)),
        round(BUILT_TO_SCALE_TARGET),
    ),
    "century_arrivals": lambda: (
        min(round(region.total_arrivals), round(CENTURY_ARRIVALS_TARGET)),
        round(CENTURY_ARRIVALS_TARGET),
    ),
    "century_integrated": lambda: (
        min(round(region.integrated_population), round(CENTURY_INTEGRATED_TARGET)),
        round(CENTURY_INTEGRATED_TARGET),
    ),
    "thriving_region": lambda: (
        min(round(region.wellbeing_score()), round(THRIVING_WELLBEING_SCORE)),
        round(THRIVING_WELLBEING_SCORE),
    ),
    "model_region": lambda: (
        min(round(region.wellbeing_score()), round(MODEL_REGION_WELLBEING_SCORE)),
        round(MODEL_REGION_WELLBEING_SCORE),
    ),
    "steady_ground": lambda: (
        min(region.best_stable_streak, STEADY_GROUND_STREAK_TARGET),
        STEADY_GROUND_STREAK_TARGET,
    ),
}


def achievement_ids_earned():
    """Every achievement id currently satisfied, in catalog order — the
    value that rides the existing save/sync mechanism via get_state()'s
    "achievements_earned" field (ACHIEVEMENTS-SYSTEM-DESIGN.md). Always
    recomputed, never itself a save input."""
    return [entry["id"] for entry in ACHIEVEMENTS if ACHIEVEMENT_CHECKS[entry["id"]]()]


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

# Unlock toast + hub-dashboard link (TODO.md "roll achievements out
# everywhere" — required on top of the base per-game rollout, per
# ACHIEVEMENTS-SYSTEM-DESIGN.md's site-wide goal). Same pattern as
# SOL/Grid/Canopy's own retrofit: a snapshot of which ids were already
# earned as of the last seed point, so a fresh load or a loaded save
# doesn't flood the player with toasts for achievements it already
# satisfies.
_achievements_seen_ids = set()


# ---- B-7 screen-reader announcements ------------------------------------------------------------
# What a sighted player sees change after an action is also said, in plain short sentences, through the shared
# announcer (shared/announcer.js) when the page has it, otherwise through the game's own #sr-announcer region.
# Only player actions and round results announce; render() never does (the shared announcer joins one tick's
# messages, so an invest that also unlocks an achievement is read as one announcement).
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


_EMOJI_RE = re.compile("[\U0001F000-\U0001FFFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D]")


def _plain(text):
    """Drops emoji and symbol pictographs so a screen reader does not read their names aloud."""
    return re.sub(r"\s+", " ", _EMOJI_RE.sub("", str(text))).strip()


def announce(text):
    """Says text for a screen reader (shared announcer first, the game's own polite region otherwise)."""
    text = _plain(text) if text else ""
    if not text:
        return
    if _shared_announce(text):
        return
    region_el = document.getElementById("sr-announcer")
    if region_el is not None:
        region_el.innerText = text


def _round_marks():
    """The one-time round-end facts worth saying only when they change: second-wave status and the two
    milestone rounds. Taken before a round and compared after."""
    return (region.second_wave_status, region.net_positive_round, region.thriving_round)


def round_announcement_text(marks_before=None):
    """What a player sees change after a round resolves, as short sentences built from the game's own readouts:
    the round recap line, a calendar event's result, a second wave or milestone that just changed, the new
    round's arrivals, funds and wellbeing. Empty before the first round."""
    recap = latest_recap()
    if recap is None:
        return ""
    parts = [recap]
    if region.calendar_enabled and region.calendar_log:
        last = region.calendar_log[-1]
        if last["round"] == region.round_number - 1:
            parts.append(calendar_result_message(last))
    before = marks_before if marks_before is not None else _round_marks()
    if region.second_wave_status != before[0] and region.second_wave_message():
        parts.append(region.second_wave_message())
    if before[1] is None and region.net_positive_round is not None:
        parts.append(integration_turning_point_message(region))
    if before[2] is None and region.thriving_round is not None:
        parts.append(thriving_callout_message(region))
    parts.append(
        f"Round {region.round_number} begins: {region.arrivals_this_round():.0f} people arriving. "
        f"Funds {region.funds:.0f}. Strain {region.strain_fraction() * 100:.0f}% ({region.strain_level()}). "
        f"Wellbeing score {region.wellbeing_score():.0f}"
    )
    return " ".join(p.strip() if p.strip().endswith((".", "!", "?")) else p.strip() + "." for p in parts if p)


def _seed_achievement_toast_baseline():
    global _achievements_seen_ids
    _achievements_seen_ids = set(achievement_ids_earned())
    _story_reach_all(_achievements_seen_ids)  # W1: a loaded save's earned chapters come back too
    if unlock_skins(_achievements_seen_ids):  # GI-25: a loaded save earns its skins quietly
        render_skins()


# I15 -- lightweight, reusable pulse feedback: adds a CSS animation class
# to an element for a fixed short duration, then removes it. Same
# setTimeout+create_proxy technique as Herd's F19 _pulse()/this file's
# own achievement toast above.
def _pulse(element_id, css_class, duration_ms=1600):
    element = document.getElementById(element_id)
    element.classList.add(css_class)

    def _unpulse(*args):
        element.classList.remove(css_class)
        proxy.destroy()

    proxy = create_proxy(_unpulse)
    setTimeout(proxy, duration_ms)


def _story_reach_all(earned_ids):
    """W1: unlocks the story chapter for every earned achievement (and the
    opening one) via the shared story-chapters.js. Idempotent and silent: no
    story script, or a chapter id it does not know, simply does nothing.
    Story progress lives in the browser's localStorage, never in the save."""
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


def _check_new_achievements_for_toast():
    """Called after every player action that could change earned status
    (invest/advance round/toggle coda) — never from render() itself,
    since load_state() also calls render() and a loaded save with
    several achievements already earned must not flood the player with
    toasts for all of them at once (see _seed_achievement_toast_baseline)."""
    global _achievements_seen_ids
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
    _note_new_skins(earned_now)
    _achievements_seen_ids = earned_now
    if newly:
        fresh_glyph_ids.update(newly)
        if achievements_open:
            update_achievements_display()  # draw the new badge in now, while the panel is open


def _note_new_skins(earned_ids):
    """GI-25: an achievement that opens a region skin says so (Settings note and a spoken line)."""
    global skin_note
    newly = unlock_skins(earned_ids)
    if newly:
        names = ", ".join(skin["label"] for skin in newly)
        skin_note = f"New region skin unlocked: {names}. Choose it in Settings."
        announce(skin_note)
        render_skins()


def on_toggle_achievements(event=None):
    global achievements_open
    achievements_open = not achievements_open
    update_achievements_display()


# I-31: a small code-drawn glyph on every achievement card, one route or milestone picture per badge in the
# region's own skyline language (36 by 36, currentColour strokes). Earned badges are drawn solid in the
# earned green, locked ones dashed and dim; a badge earned this session draws itself in once when the
# panel next shows it (a short flourish that Reduce Motion and Animation speed Off remove).
GLYPH_GROUND = '<path class="g-ground" d="M3,30 H33" />'
ACHIEVEMENT_GLYPHS = {
    "first_investment": '<rect x="13" y="12" width="10" height="18" /><path d="M16,17 h1 M19,17 h1 M16,22 h1 M19,22 h1" />',
    "full_capacity_portfolio": '<rect x="5" y="20" width="7" height="10" /><rect x="14" y="11" width="8" height="19" /><rect x="24" y="16" width="7" height="14" />',
    "services_backbone": '<rect x="10" y="26" width="16" height="4" /><rect x="10" y="22" width="16" height="4" /><rect x="10" y="18" width="16" height="4" /><rect x="10" y="14" width="16" height="4" /><rect x="10" y="10" width="16" height="4" />',
    "built_to_scale": '<rect x="4" y="24" width="4" height="6" /><rect x="9" y="21" width="4" height="9" /><rect x="14" y="17" width="4" height="13" /><rect x="19" y="13" width="4" height="17" /><rect x="24" y="9" width="4" height="21" /><rect x="29" y="5" width="4" height="25" />',
    "century_arrivals": ''.join(f'<circle cx="{5 + i * 4.3:.1f}" cy="{22 if i % 2 else 17}" r="1.7" />' for i in range(7)),
    "crisis_averted": '<path d="M18,5 L29,10 V19 C29,25 24,28 18,30 C12,28 7,25 7,19 V10 Z" /><path d="M12,18 L16.5,22 L24,13" />',
    "full_recovery": '<path d="M5,12 L12,25 L18,21 L25,11 L31,7" /><path d="M26,6 H31.5 V11.5" />',
    "turning_point_reached": '<path class="g-dash" d="M4,20 H32" /><path d="M5,29 C14,28 18,22 31,8" /><circle cx="20" cy="20" r="2.6" />',
    "ahead_of_schedule": '<path d="M26,30 V7 L33,11 L26,15" /><path class="g-dash" d="M4,26 H22" />',
    "century_integrated": '<circle cx="9" cy="18" r="5" /><circle cx="18" cy="18" r="5" /><circle cx="27" cy="18" r="5" />',
    "backlog_cleared": '<circle cx="8" cy="24" r="2" /><circle cx="15" cy="24" r="2" /><circle cx="22" cy="24" r="2" /><circle cx="29" cy="24" r="2" /><path d="M9,13 L15,19 L28,6" />',
    "balanced_region": '<rect x="5" y="14" width="6" height="16" /><rect x="15" y="14" width="6" height="16" /><rect x="25" y="14" width="6" height="16" /><path class="g-dash" d="M3,10 H33" />',
    "thriving_region": '<circle cx="18" cy="12" r="4.5" /><path d="M18,3 v2 M18,19 v2 M9,12 h2 M25,12 h2 M11.5,5.5 l1.4,1.4 M23.1,17.1 l1.4,1.4 M24.5,5.5 l-1.4,1.4 M12.9,17.1 l-1.4,1.4" /><rect x="8" y="23" width="6" height="7" /><rect x="22" y="21" width="6" height="9" />',
    "model_region": '<polygon points="18.0,4.0 20.6,10.4 27.5,10.9 22.2,15.4 23.9,22.1 18.0,18.4 12.1,22.1 13.8,15.4 8.5,10.9 15.4,10.4" /><rect x="7" y="24" width="6" height="6" /><rect x="15" y="21" width="6" height="9" /><rect x="23" y="24" width="6" height="6" />',
    "economic_engine": '<circle cx="18" cy="17" r="11" /><path d="M18,24 V11 M12,17 L18,11 L24,17" />',
    "steady_ground": '<path d="M4,19 H32" /><path d="M7,15 v8 M12.5,15 v8 M18,15 v8 M23.5,15 v8 M29,15 v8" />',
    "long_horizon_reached": '<path d="M3,20 C9,9 27,9 33,20 C27,29 9,29 3,20 Z" /><circle cx="18" cy="19.5" r="3.4" />',
    "sustained_transition": '<path d="M5,28 L14,22 L22,16 L31,8" /><circle cx="5" cy="28" r="2" /><circle cx="14" cy="22" r="2" /><circle cx="22" cy="16" r="2" /><circle cx="31" cy="8" r="2" />',
}
fresh_glyph_ids = set()  # badges earned this session whose glyph has not been drawn in yet (transient)


def achievement_glyph_svg(achievement_id, earned=False, fresh=False):
    """The card glyph for one achievement ("" for an id with no drawing)."""
    body = ACHIEVEMENT_GLYPHS.get(achievement_id)
    if body is None:
        return ""
    state = "earned" if earned else "locked"
    extra = " achievement-glyph--fresh" if fresh and earned else ""
    return (
        f'<svg viewBox="0 0 36 36" width="36" height="36" class="achievement-glyph achievement-glyph--{state}{extra}" '
        f'focusable="false" aria-hidden="true">{GLYPH_GROUND}{body}</svg>'
    )


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

        glyph = document.createElement("span")
        glyph.className = "achievement-glyph-slot"
        glyph.innerHTML = achievement_glyph_svg(entry["id"], entry["earned"], entry["id"] in fresh_glyph_ids)
        card.appendChild(glyph)

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
    fresh_glyph_ids.clear()  # each new badge's flourish plays once

    # A link out to the hub-wide achievements dashboard (root index.html's
    # #account-achievements-dashboard, ACHIEVEMENTS-SYSTEM-DESIGN.md §5).
    # Relative path, no leading "/" (site-level milestone 7's GitHub
    # Pages subpath fix). Rebuilt each open alongside the cards since the
    # panel is cleared first. Note: the hub-side script.js registration
    # that makes Drift's save data actually show up on that dashboard is
    # a root-file change, out of scope for this games/drift/-only
    # dispatch — see CLAUDE.md.
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


# Info Page — optional, player-triggered supplement (never forced
# mid-session). Framing is written fresh, not copied from any source;
# sources are the curated real-world backing for the game's mechanics.
# Kept institutional/systems-level per this game's sensitivity note in
# CLAUDE.md's Tech notes section
# — about regional capacity, not individual migrant stories.
INFO_PAGE = {
    "framing": (
        "Climate-driven displacement is already happening at scale, and "
        "how well it goes depends far more on a receiving region's "
        "institutional preparedness than on the number of people "
        "arriving — real projections vary by tens of millions depending "
        "on how much the world invests in resilience now. Drift's "
        "capacity-vs-pressure system is modeled on that same "
        "institutional framing, deliberately kept impersonal rather than "
        "told through individual stories."
    ),
    "mechanic_tie_in": (
        "Drift's long-horizon coda is grounded in real evidence that "
        "early institutional investment in integration converts "
        "displacement pressure into a net-positive contribution over "
        "time, not just crisis management."
    ),
    "sources": [
        {
            "label": "UNHCR — Climate change and displacement",
            "url": "https://www.unhcr.org/us/what-we-do/build-better-futures/climate-change-and-displacement",
            "note": "The authoritative agency perspective, framing displacement institutionally — consistent with Drift's own framing.",
        },
        {
            "label": "Migration Policy Institute — Climate Migration 101: An Explainer",
            "url": "https://www.migrationpolicy.org/journal/feature/climate-migration-101-explainer",
            "note": "Real projections (44-216 million internal migrants by 2050) that echo Drift's \"preparedness changes the outcome\" hope angle.",
        },
        {
            "label": "Migration Policy Institute — Who Counts as a Climate Migrant?",
            "url": "https://www.migrationpolicy.org/article/who-is-a-climate-migrant",
            "note": "Explains the legal/definitional gap behind why Drift frames this as a systems/capacity problem, not a legal one.",
        },
        {
            "label": "Brookings — The climate crisis, migration, and refugees",
            "url": "https://www.brookings.edu/articles/the-climate-crisis-migration-and-refugees/",
            "note": "Policy-level analysis of the institutional response gap, grounding Drift's receiving-region capacity mechanic.",
        },
        {
            "label": "Migration Policy Institute — How Are Refugees Faring? Integration at U.S. and State Levels",
            "url": "https://www.migrationpolicy.org/publication/how-are-refugees-faring-integration-us-and-state-levels",
            "note": "Source for the in-game real-world resettlement-outcome benchmark (89% employment among recently-resettled working-age refugees, 2023).",
        },
    ],
}
info_page_open = False


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


# I10: a per-browser "best run" stat -- the highest wellbeing_score() any
# session on this device has ever reached, persisted via localStorage.
# Same distinguishing rationale as Thaw's G19/Canopy's B14/Tide's D13:
# this tracks the best this *browser* has ever seen across every
# session/save on this device, not one save's snapshot, so it's
# deliberately NOT part of get_state()/the save-code system.
PERSONAL_BEST_STORAGE_KEY = "drift_personal_best_v1"


def _read_local_storage_item(key):
    """Lazy `import js` (same convention as _read_achievements_json()) so
    this file stays importable outside a real browser. Broad except on
    the actual read/write below is deliberate: a real browser can refuse
    localStorage access entirely (private-browsing mode in some
    browsers), surfaced as a JS exception with no stable Python type to
    catch narrowly -- this feature is a nice-to-have, not core gameplay,
    so it degrades to "no personal best recorded" rather than crashing
    the module import."""
    try:
        import js  # noqa: PLC0415 -- Pyodide-only import, deliberately lazy
    except ImportError:
        return None
    storage = getattr(js, "localStorage", None)
    if storage is None:
        return None
    try:
        return storage.getItem(key)
    except Exception:  # noqa: BLE001 -- see docstring above
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
    except Exception:  # noqa: BLE001 -- see _read_local_storage_item's docstring
        pass


def load_personal_best():
    """Reads the stored best wellbeing_score(), defaulting to 0.0 if
    nothing is stored yet, storage is unavailable, or the stored value is
    malformed (e.g. hand-edited or from a future incompatible format)."""
    raw = _read_local_storage_item(PERSONAL_BEST_STORAGE_KEY)
    if not raw:
        return {"wellbeing_score": 0.0}
    try:
        data = json.loads(raw)
        return {"wellbeing_score": float(data.get("wellbeing_score", 0.0))}
    except (ValueError, TypeError, AttributeError):
        return {"wellbeing_score": 0.0}


personal_best = load_personal_best()


def _maybe_update_personal_best():
    """Called every render(); bumps + persists personal_best whenever the
    live session exceeds it."""
    score = region.wellbeing_score()
    if score > personal_best["wellbeing_score"]:
        personal_best["wellbeing_score"] = score
        _write_local_storage_item(PERSONAL_BEST_STORAGE_KEY, json.dumps(personal_best))


def _maybe_record_learning():
    """I29: once any region has reached Thriving, remember it for every
    region that begins afterwards."""
    global cross_region_learning
    if cross_region_learning or region.thriving_round is None:
        return
    cross_region_learning = True
    _write_local_storage_item(LEARNING_STORAGE_KEY, "1")


def render_learning():
    element = document.getElementById("learning-display")
    if element is None:
        return
    if region.learning_active:
        element.innerText = (
            f"Lessons from an earlier thriving region: +{LEARNING_INTEGRATION_BONUS * 100:.0f}% faster integration here."
        )
    elif cross_region_learning:
        element.innerText = (
            f"Thriving reached: every region you start from now on begins with "
            f"+{LEARNING_INTEGRATION_BONUS * 100:.0f}% faster integration."
        )
    else:
        element.innerText = (
            f"Bring any region to Thriving once and every future region starts with "
            f"+{LEARNING_INTEGRATION_BONUS * 100:.0f}% faster integration."
        )


def render_personal_best():
    element = document.getElementById("personal-best-display")
    if element is None:
        return
    element.innerText = f"Personal best wellbeing: {personal_best['wellbeing_score']:.0f}"


# ===========================================================================
# W2-drift -- "In the real world": a collapsible note that pairs the region's
# current situation with one real, sourced example of institutions handling
# the same thing. Every figure below was read from the linked page on
# 2026-09-27 (nothing recalled from memory); where a page gave no number, none
# is quoted. Kept institutional and neutral, in line with this game's
# sensitivity note: programmes, laws and documented figures, never individual
# stories or advocacy. The choice is a pure function of run state, with no RNG:
#   * a warned or active second wave -> the 2022 EU temporary-protection surge,
#   * else any strain above "stable" -> Jordan's services under pressure,
#   * else the funded policies (language access, credentialing, sponsorship)
#     rotate by round, one example per funded policy,
#   * else all examples rotate by round.
# It never changes any number in a run.
# ===========================================================================
REAL_WORLD_READ_DATE = "2026-09-27"
REAL_WORLD_ORDER = ["settlement", "language_access", "credentialing", "sponsorship", "surge", "services_strain"]
REAL_WORLD_POLICY_TOPICS = ["language_access", "credentialing", "sponsorship"]  # POLICIES keys that have an example
REAL_WORLD_EXAMPLES = {
    "settlement": {
        "title": "Uganda's settlement approach",
        "text": "Uganda's 2006 Refugee Act granted freedom of movement, the right to work and access to public services, and households in settlements were allotted a uniform plot of 30 by 30 metres. The page also records that implementation gaps remained, and reports about 1.95 million refugees in the country by October 2025.",
        "source": "Wikipedia, Refugees in Uganda", "url": "https://en.wikipedia.org/wiki/Refugees_in_Uganda",
    },
    "language_access": {
        "title": "Germany's integration courses",
        "text": "Germany introduced state-funded integration courses in 2005: 600 hours of language instruction plus 100 hours of orientation (as of 2016). About 94,020 people started one in 2012 and 142,439 in 2014; the page notes one evaluation found a 53% pass rate in 2012.",
        "source": "Wikipedia, Integration course", "url": "https://en.wikipedia.org/wiki/Integration_course",
    },
    "credentialing": {
        "title": "Recognising qualifications gained abroad (Germany)",
        "text": "Germany's federal migration office describes a recognition process in which qualifications obtained abroad are compared with German requirements. Nationality is not decisive and no residence permit is needed, and as a rule the process should not take longer than three months if all documents are complete.",
        "source": "BAMF (German Federal Office for Migration and Refugees), Recognition of foreign professional qualifications", "url": "https://www.bamf.de/EN/Themen/Integration/ZugewanderteTeilnehmende/AnerkennungBerufsabschluesse/anerkennungberufsabschluesse-node.html",
    },
    "sponsorship": {
        "title": "Canada's Private Sponsorship of Refugees Program",
        "text": "Established in 1978, the programme lets groups of citizens and organisations provide social, emotional, residential and financial support for one year or until a refugee becomes self-sufficient. The page counts nearly 300,000 refugees resettled through it since 1979 (as of January 2020).",
        "source": "Wikipedia, Private Sponsorship of Refugees Program", "url": "https://en.wikipedia.org/wiki/Private_Sponsorship_of_Refugees_Program",
    },
    "surge": {
        "title": "The EU's temporary protection for Ukraine (2022)",
        "text": "The EU invoked its Temporary Protection Directive on 3 March 2022: people covered can get a residence permit without the complicated bureaucracy normally associated with asylum, may work and access social welfare, and children can attend school as EU residents do. Protection can last up to three years.",
        "source": "Wikipedia, Temporary Protection Directive", "url": "https://en.wikipedia.org/wiki/Temporary_Protection_Directive",
    },
    "services_strain": {
        "title": "Jordan's public services under pressure",
        "text": "By November 2015, 630,776 Syrian refugees were registered in Jordan according to UNHCR data cited by the page, which describes the added pressure on Jordan's infrastructure, specifically water supplies, sanitation, housing and energy.",
        "source": "Wikipedia, Syrian refugees in Jordan", "url": "https://en.wikipedia.org/wiki/Syrian_refugees_in_Jordan",
    },
}


def real_world_topic():
    """Which example the note shows right now (pure function of run state)."""
    if region.second_wave_status in ("warned", "active"):
        return "surge"
    if region.strain_level() != STRAIN_LEVEL_THRESHOLDS[0][1]:
        return "services_strain"
    funded = [p for p in REAL_WORLD_POLICY_TOPICS if region.policy_level.get(p, 0) > 0]
    if funded:
        return funded[region.round_number % len(funded)]
    return REAL_WORLD_ORDER[region.round_number % len(REAL_WORLD_ORDER)]


def render_real_world():
    box = document.getElementById("real-world-note")
    if box is None:
        return
    example = REAL_WORLD_EXAMPLES[real_world_topic()]
    box.hidden = False
    document.getElementById("real-world-text").innerText = f"{example['title']}. {example['text']}"
    link = document.getElementById("real-world-source")
    link.innerText = f"Source: {example['source']} (read {REAL_WORLD_READ_DATE})"
    link.href = example["url"]


# ===========================================================================
# Round-3 batch (2026-10-07): the Round Ledger and recap line (I-8, I-17), the
# undo family (I-15 Reset this round, GI-18 Rewind Token), Play 5 rounds
# (GI-30), the Region Collection (GI-15 personality titles, GI-22 civic
# milestones) and a live tab title (I-24). None of it changes a rule or a
# number in a run: the ledger and collection only record, undo only restores
# an earlier state, and Play 5 rounds is five ordinary Advance Rounds.
# ===========================================================================

# ---- I-8 / I-17: Round Ledger ---------------------------------------------
LEDGER_SORTS = {
    "round_desc": ("Newest first", lambda r: (-r["round"],)),
    "round_asc": ("Oldest first", lambda r: (r["round"],)),
    "strain": ("Highest strain", lambda r: (-r["strain"], -r["round"])),
    "wellbeing": ("Highest wellbeing", lambda r: (-r["wellbeing"], -r["round"])),
    "arrivals": ("Most arrivals", lambda r: (-r["arrivals"], -r["round"])),
    "spent": ("Most spent", lambda r: (-r["spent"], -r["round"])),
}
LEDGER_FILTERS = {
    "all": ("All rounds", lambda r: True),
    "purchases": ("Rounds with purchases", lambda r: r["spent"] > 0),
    "no_purchases": ("Rounds with no purchases", lambda r: r["spent"] <= 0),
    "strained": ("Strained or critical", lambda r: r["strain"] >= STRAIN_LEVEL_THRESHOLDS[1][0]),
    "auto": ("Rounds from Play 5 rounds", lambda r: r["auto"]),
}
ledger_open = False
ledger_sort = "round_desc"
ledger_filter = "all"


def strain_label(fraction):
    label = STRAIN_LEVEL_THRESHOLDS[0][1]
    for threshold, name in STRAIN_LEVEL_THRESHOLDS:
        if fraction >= threshold:
            label = name
    return label


def ledger_rows(sort_key="round_desc", filter_key="all"):
    """The ledger rows after filtering and sorting (copies, newest first by default)."""
    keep = LEDGER_FILTERS.get(filter_key, LEDGER_FILTERS["all"])[1]
    order = LEDGER_SORTS.get(sort_key, LEDGER_SORTS["round_desc"])[1]
    return sorted((dict(row) for row in region.ledger if keep(row)), key=order)


def ledger_csv():
    """CSV text of the whole ledger, oldest round first (strain as a percentage)."""
    header = ["strain_pct" if name == "strain" else name for name in LEDGER_FIELDS]
    lines = [",".join(header)]
    for row in region.ledger:
        cells = []
        for name in LEDGER_FIELDS:
            value = row[name]
            if name == "auto":
                cells.append("yes" if value else "no")
            elif name == "strain":
                cells.append(f"{value * 100:.1f}")
            elif name == "round":
                cells.append(str(int(value)))
            else:
                cells.append(f"{value:.2f}")
        lines.append(",".join(cells))
    return "\n".join(lines)


def round_recap_message(row, previous_strain=0.0):
    """I-17: one plain line about the round that just resolved."""
    delta = row["strain"] - previous_strain
    if abs(delta) < 0.02:
        trend = "steady"
    else:
        trend = "up" if delta > 0 else "down"
    cover = (
        f"{row['shortfall']:.0f} people beyond capacity"
        if row["shortfall"] >= 0.5
        else "capacity covered everyone"
    )
    return (
        f"Round {row['round']}: {row['arrivals']:.0f} arrived, {row['integrated_new']:.0f} integrated, "
        f"{cover}; strain {trend} at {row['strain'] * 100:.0f}% ({strain_label(row['strain'])}); "
        f"income {row['income']:.0f}, spent {row['spent']:.0f}."
    )


def latest_recap():
    if not region.ledger:
        return None
    previous = region.ledger[-2]["strain"] if len(region.ledger) > 1 else 0.0
    return round_recap_message(region.ledger[-1], previous)


def _ledger_table_html(rows):
    head = (
        "<tr><th>Rd</th><th>Spent (H/S/I/P)</th><th>Income</th><th>Arrived</th><th>Integr.</th>"
        "<th>Pending</th><th>Strain</th><th>Svc / Eco / Coh</th><th>Wellbeing</th><th>Funds</th></tr>"
    )
    body = []
    for r in rows:
        auto = " (auto)" if r["auto"] else ""
        body.append(
            f"<tr><td>{r['round']}{auto}</td>"
            f"<td>{r['spent']:.0f} ({r['housing']:.0f}/{r['services']:.0f}/{r['infrastructure']:.0f}/{r['policy']:.0f})</td>"
            f"<td>{r['income']:.0f}</td><td>{r['arrivals']:.0f}</td><td>{r['integrated_new']:.0f}</td>"
            f"<td>{r['pending']:.0f}</td><td>{r['strain'] * 100:.0f}% {strain_label(r['strain'])}</td>"
            f"<td>{r['service']:.0f} / {r['economy']:.0f} / {r['cohesion']:.0f}</td>"
            f"<td>{r['wellbeing']:.0f}</td><td>{r['funds']:.0f}</td></tr>"
        )
    return f"<table class=\"ledger-table\"><thead>{head}</thead><tbody>{''.join(body)}</tbody></table>"


def render_ledger():
    count = len(region.ledger)
    toggle = document.getElementById("ledger-toggle-button")
    toggle.innerText = "Hide Round Ledger" if ledger_open else f"📒 Round Ledger ({count})"
    panel = document.getElementById("ledger-panel")
    panel.hidden = not ledger_open
    if not ledger_open:
        return
    rows = ledger_rows(ledger_sort, ledger_filter)
    summary = document.getElementById("ledger-summary")
    if count == 0:
        summary.innerText = "No rounds resolved yet. Every Advance Round adds a row here."
        document.getElementById("ledger-table").innerHTML = ""
    else:
        total_spent = sum(r["spent"] for r in region.ledger)
        summary.innerText = (
            f"{count} round(s) recorded (the latest {LEDGER_MAX_ENTRIES} are kept), showing {len(rows)}. "
            f"Total spent: {total_spent:.0f}. H/S/I/P = Housing / Services / Infrastructure / Policy spending."
        )
        document.getElementById("ledger-table").innerHTML = _ledger_table_html(rows)
    document.getElementById("copy-ledger-csv-button").disabled = count == 0


def on_toggle_ledger(event=None):
    global ledger_open
    ledger_open = not ledger_open
    render_ledger()


def on_ledger_sort(event=None):
    global ledger_sort
    value = getattr(document.getElementById("ledger-sort-select"), "value", ledger_sort)
    ledger_sort = value if value in LEDGER_SORTS else "round_desc"
    render_ledger()


def on_ledger_filter(event=None):
    global ledger_filter
    value = getattr(document.getElementById("ledger-filter-select"), "value", ledger_filter)
    ledger_filter = value if value in LEDGER_FILTERS else "all"
    render_ledger()


def _copy_to_clipboard(text):
    try:
        import js as _js  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return False
    navigator = getattr(_js, "navigator", None)
    clipboard = getattr(navigator, "clipboard", None) if navigator is not None else None
    if clipboard is None:
        return False
    try:
        clipboard.writeText(text)
        return True
    except Exception:  # noqa: BLE001 -- a refused clipboard just falls back to the text box
        return False


def on_copy_ledger_csv(event=None):
    text = ledger_csv()
    status = document.getElementById("ledger-copy-status")
    area = document.getElementById("ledger-copy-area")
    if _copy_to_clipboard(text):
        area.hidden = True
        status.innerText = "Copied the ledger as CSV to the clipboard."
    else:
        area.hidden = False
        area.value = text
        status.innerText = "Could not copy automatically. Select the text below and copy it yourself."


# ---- I-15 / GI-18: undo family ---------------------------------------------
round_start_snapshot = None  # what Reset this round returns to
rewind_snapshot = None  # the state just before the last Advance Round
rewind_armed = False
round_tools_message = ""


def _clone_region(saved_dict):
    other = RegionState()
    other.__dict__.clear()
    other.__dict__.update(copy.deepcopy(saved_dict))
    return other


def _take_round_start_snapshot():
    return {
        "funds": region.funds,
        "capacity": dict(region.capacity),
        "policy_level": dict(region.policy_level),
        "cumulative_services_investment": region.cumulative_services_investment,
        "spend_by_type": dict(region.spend_by_type),
        "round_spend": dict(region.round_spend),
        "braced_rounds": list(region.braced_rounds),
        "neighbor": copy.deepcopy(neighbor.__dict__) if neighbor is not None else None,
        "support_sent": neighbor_support_sent,
    }


def _take_full_snapshot():
    return {
        "region": copy.deepcopy(region.__dict__),
        "neighbor": copy.deepcopy(neighbor.__dict__) if neighbor is not None else None,
        "support_sent": neighbor_support_sent,
        "round_start": copy.deepcopy(round_start_snapshot),
    }


def reset_round():
    """I-15: refund everything decided since the round began (capacity, policies,
    reallocations and neighbour moves). Returns False if there is nothing to undo."""
    global neighbor, neighbor_support_sent
    snap = round_start_snapshot
    if snap is None or region.round_buys <= 0:
        return False
    region.funds = snap["funds"]
    region.capacity = dict(snap["capacity"])
    region.policy_level = dict(snap["policy_level"])
    region.cumulative_services_investment = snap["cumulative_services_investment"]
    region.spend_by_type = dict(snap["spend_by_type"])
    region.round_spend = dict(snap["round_spend"])
    region.braced_rounds = list(snap.get("braced_rounds", region.braced_rounds))
    region.round_buys = 0
    neighbor = _clone_region(snap["neighbor"]) if snap["neighbor"] is not None else None
    neighbor_support_sent = snap["support_sent"]
    return True


def rewind_available():
    return region.rewind_used_round is None and rewind_snapshot is not None


def use_rewind_token():
    """GI-18: one take-back per region. Restores the whole state to just before the
    last Advance Round (anything decided since is refunded with it)."""
    global neighbor, neighbor_support_sent, round_start_snapshot, rewind_snapshot
    if not rewind_available():
        return False
    snap = rewind_snapshot
    region.__dict__.clear()
    region.__dict__.update(copy.deepcopy(snap["region"]))
    region.rewind_used_round = region.round_number
    neighbor = _clone_region(snap["neighbor"]) if snap["neighbor"] is not None else None
    neighbor_support_sent = snap["support_sent"]
    round_start_snapshot = copy.deepcopy(snap["round_start"]) if snap["round_start"] is not None else _take_round_start_snapshot()
    rewind_snapshot = None
    return True


def _reset_undo_state():
    """After a load or a fresh start: nothing earlier than now can be undone."""
    global round_start_snapshot, rewind_snapshot, rewind_armed
    region.round_buys = 0
    round_start_snapshot = _take_round_start_snapshot()
    rewind_snapshot = None
    rewind_armed = False


def on_reset_round(event=None):
    global round_tools_message
    if reset_round():
        round_tools_message = "This round's decisions were refunded. Funds and capacity are back to the start of the round."
        _seed_achievement_toast_baseline()
        render()
        announce(round_tools_message)
        return
    render()
    announce("Nothing to reset: you have not made a decision this round")


def on_rewind(event=None):
    global rewind_armed, round_tools_message
    if not rewind_available():
        return
    if not rewind_armed:
        rewind_armed = True
        render_round_tools()
        announce("Press Rewind again to confirm undoing the last Advance Round")
        return
    use_rewind_token()
    round_tools_message = (
        f"Rewound: round {region.round_number} is open again exactly as it was before you advanced. "
        "The Rewind Token is spent for this region."
    )
    _seed_achievement_toast_baseline()
    render()
    announce(round_tools_message)


# ---- GI-30: Play 5 rounds ----------------------------------------------------
PLAY_ROUNDS_COUNT = 5


def _strain_rank(fraction):
    rank = 0
    for index, (threshold, _label) in enumerate(STRAIN_LEVEL_THRESHOLDS):
        if fraction >= threshold:
            rank = index
    return rank


def _auto_block_reason():
    """Why an automatic run must not start the current round, or None. A braceable
    calendar event due this round has to be braced by hand, or advanced by hand."""
    event = region.calendar_event()
    if (
        event is not None
        and CALENDAR_KINDS[event["kind"]]["braceable"]
        and region.round_number not in region.braced_rounds
    ):
        return f"{event['name']} is due this round: brace for it, or press Advance Round yourself"
    return None


def _run_auto_rounds(count, before_round=None):
    """Advance up to `count` rounds as automatic rounds. `before_round` (optional) makes
    purchases first (the Budget Autopilot). Stops early, after the round that caused it, if
    strain moves up a level, a second-wave event arrives, the neighbouring district starts
    sending people, or the Crisis Calendar shows a braceable event for next round; and
    refuses to start a round whose braceable event is unbraced. Returns (advanced, reason)."""
    global rewind_snapshot, round_start_snapshot
    advanced = 0
    reason = None
    for _ in range(count):
        blocked = _auto_block_reason()
        if blocked:
            reason = blocked
            break
        level_before = _strain_rank(region.strain_fraction())
        wave_before = region.second_wave_status
        spill_before = neighbor_spillover()
        _sync_spillover()
        if before_round is not None:
            before_round()
        rewind_snapshot = _take_full_snapshot()
        completed = region.round_number
        region.advance_round(auto=True)
        if neighbor is not None:
            neighbor.advance_round()
        _sync_spillover()
        _collect_after_round(completed)
        advanced += 1
        upcoming = region.calendar_event(region.round_number + 1)
        if _strain_rank(region.strain_fraction()) > level_before:
            reason = f"strain rose to {region.strain_level()}"
        elif region.second_wave_status != wave_before:
            reason = {
                "warned": "a second wave was announced",
                "active": "the second wave arrived",
                "done": "the second wave ended",
            }.get(region.second_wave_status, "a forecast event arrived")
        elif spill_before == 0.0 and neighbor_spillover() > 0.0:
            reason = "the neighbouring district went critical and is sending people your way"
        elif (
            upcoming is not None
            and CALENDAR_KINDS[upcoming["kind"]]["braceable"]
            and upcoming["round"] not in region.braced_rounds
        ):
            reason = f"the Crisis Calendar shows {upcoming['name']} next round"
        if reason:
            break
    round_start_snapshot = _take_round_start_snapshot()
    return advanced, reason


def play_rounds(count=PLAY_ROUNDS_COUNT):
    """Advance up to `count` rounds with the current allocation (no purchases).
    Returns (rounds advanced, reason or None)."""
    return _run_auto_rounds(count)


def on_play_rounds(event=None):
    global round_tools_message, collection_note
    collection_note = ""
    marks_before = _round_marks()
    advanced, reason = play_rounds()
    unit = "round" if advanced == 1 else "rounds"
    if reason:
        round_tools_message = f"Played {advanced} {unit} and stopped early: {reason}."
    else:
        round_tools_message = f"Played {advanced} {unit} with your current allocation."
    render()
    announce(round_tools_message)
    if advanced:
        announce(round_announcement_text(marks_before))
    _check_new_achievements_for_toast()


def render_round_tools():
    buys = region.round_buys
    reset_button = document.getElementById("reset-round-button")
    reset_button.disabled = not (buys > 0 and round_start_snapshot is not None)
    reset_button.innerText = (
        f"↩️ Reset this round ({buys} decision{'s' if buys != 1 else ''})" if buys > 0 else "↩️ Reset this round"
    )
    rewind_button = document.getElementById("rewind-button")
    if region.rewind_used_round is not None:
        rewind_button.innerText = f"⏪ Rewind Token used in round {region.rewind_used_round}"
        rewind_button.disabled = True
    elif rewind_snapshot is None:
        rewind_button.innerText = "⏪ Rewind Token (1 left)"
        rewind_button.disabled = True
    elif rewind_armed:
        rewind_button.innerText = "Confirm: undo the last Advance Round"
        rewind_button.disabled = False
    else:
        rewind_button.innerText = "⏪ Rewind Token (1 left)"
        rewind_button.disabled = False
    document.getElementById("play-rounds-button").innerText = f"⏩ Play {PLAY_ROUNDS_COUNT} rounds"
    note = document.getElementById("round-tools-note")
    note.innerText = round_tools_message
    note.hidden = round_tools_message == ""
    recap = latest_recap()
    details = document.getElementById("round-recap-details")
    details.hidden = recap is None
    document.getElementById("round-recap-display").innerText = recap or ""


# ---- GI-15 / GI-22: Region Collection (personality titles, civic milestones) -----
COLLECTION_STORAGE_KEY = "drift_collection_v1"
TITLE_MIN_ROUND = 8
TITLE_MIN_SPEND = 100.0
REGION_TITLES = {
    "builder": {
        "label": "The Builder",
        "hint": "Put at least half of everything you spend into Housing.",
        "text": "This region's funds went mostly into homes: roof first, everything else after.",
    },
    "educator": {
        "label": "The Educator",
        "hint": "Put at least half of everything you spend into Integration Services.",
        "text": "This region's funds went mostly into language, work and school access for newcomers.",
    },
    "engineer": {
        "label": "The Engineer",
        "hint": "Put at least 40% of everything you spend into Infrastructure.",
        "text": "This region's funds went mostly into the pipes, roads and clinics everyone shares.",
    },
    "reformer": {
        "label": "The Reformer",
        "hint": "Put at least 30% of everything you spend into the policy toolkit.",
        "text": "This region leaned on rules and programmes: credentialing, language access and sponsorship.",
    },
    "balancer": {
        "label": "The Balancer",
        "hint": "Keep Housing, Services and Infrastructure each above 15% of your spending, with no other title fitting.",
        "text": "This region spread its funds evenly and never bet on one lever.",
    },
}
TITLE_ORDER = ["builder", "educator", "engineer", "reformer", "balancer"]
_TITLE_THRESHOLDS = {"builder": 0.5, "educator": 0.5, "engineer": 0.4, "reformer": 0.3}
_TITLE_SPEND_KEY = {"builder": "housing", "educator": "services", "engineer": "infrastructure", "reformer": "policy"}


def region_title_key(region_state):
    """The personality title fitted by the lifetime spending split (capacity and
    policy spending; reallocation fees do not count), or None while too little
    has been spent to say."""
    parts = {k: region_state.spend_by_type[k] for k in ("housing", "services", "infrastructure", "policy")}
    total = sum(parts.values())
    if total < TITLE_MIN_SPEND:
        return None
    shares = {k: v / total for k, v in parts.items()}
    best = None
    best_margin = 0.0
    for key in ("builder", "educator", "engineer", "reformer"):
        margin = shares[_TITLE_SPEND_KEY[key]] - _TITLE_THRESHOLDS[key]
        if margin >= 0 and (best is None or margin > best_margin):
            best, best_margin = key, margin
    if best is not None:
        return best
    if min(shares["housing"], shares["services"], shares["infrastructure"]) >= 0.15:
        return "balancer"
    return None


# Each civic milestone: id, name, a hint shown while locked, one line shown once
# found, and a test (region, completed_round) -> bool. "By round N" means the
# round that just resolved is N or earlier. Cosmetic: they change no number.
CIVIC_MILESTONES = [
    {
        "id": "first_roof_fund", "name": "First Roof Fund",
        "hint": "Reach 100 Housing capacity by round 5.",
        "text": "A dedicated housing fund opened before most arrivals had even landed.",
        "test": lambda r, n: n <= 5 and r.capacity["housing"] >= 100,
    },
    {
        "id": "night_classes", "name": "Night Classes",
        "hint": "Reach 48 Integration Services capacity by round 8.",
        "text": "Evening language and skills classes were running before the first backlog formed.",
        "test": lambda r, n: n <= 8 and r.capacity["services"] >= 48,
    },
    {
        "id": "three_pillars", "name": "Three Pillars Compact",
        "hint": "Reach 60 capacity in Housing, Services and Infrastructure by round 12.",
        "text": "Homes, services and shared infrastructure were agreed as one package, not three separate fights.",
        "test": lambda r, n: n <= 12 and all(r.capacity[t] >= 60 for t in CAPACITY_TYPES),
    },
    {
        "id": "open_charter", "name": "Open Charter",
        "hint": "Have 80% of arrivals integrated by round 15 (at least 100 arrived).",
        "text": "The region's charter gave newcomers a clear route to work, school and services.",
        "test": lambda r, n: n <= 15 and r.total_arrivals >= 100 and r.integration_fraction() >= 0.8,
    },
    {
        "id": "ring_road", "name": "Ring Road",
        "hint": "Reach 120 Infrastructure capacity by round 20.",
        "text": "A ring road and shared clinics took the load off the old centre.",
        "test": lambda r, n: n <= 20 and r.capacity["infrastructure"] >= 120,
    },
    {
        "id": "skilled_welcome", "name": "Skilled Welcome",
        "hint": "Fund all three policies at least once by round 20.",
        "text": "Qualification recognition, language funding and sponsorship all opened in the same few years.",
        "test": lambda r, n: n <= 20 and all(level >= 1 for level in r.policy_level.values()),
    },
    {
        "id": "good_neighbours", "name": "Good Neighbours",
        "hint": "Send support to the neighbouring district by round 25.",
        "text": "A calm region shared its cushion with a district under more pressure.",
        "test": lambda r, n: n <= 25 and neighbor_support_sent > 0,
    },
    {
        "id": "harbour_lights", "name": "Harbour Lights",
        "hint": "Reach 100 Services and 100 Infrastructure capacity by round 30.",
        "text": "Services and infrastructure both passed a hundred: the lights stayed on at every hour.",
        "test": lambda r, n: n <= 30 and r.capacity["services"] >= 100 and r.capacity["infrastructure"] >= 100,
    },
    {
        "id": "steady_hands", "name": "Steady Hands",
        "hint": "Hold strain at stable for 20 rounds in a row by round 30.",
        "text": "Twenty calm rounds in a row: planning, not reacting.",
        "test": lambda r, n: n <= 30 and r.best_stable_streak >= 20,
    },
    {
        "id": "quiet_weather", "name": "Quiet Weather",
        "hint": "Hold through the second wave without strain reaching critical.",
        "text": "The second wave came and the region's institutions simply absorbed it.",
        "test": lambda r, n: r.second_wave_result == "held",
    },
]
CIVIC_BY_ID = {entry["id"]: entry for entry in CIVIC_MILESTONES}


def _clean_collection(raw):
    """A well-formed collection dict from anything, dropping unknown ids and bad values."""
    out = {"titles": [], "civic": {}}
    if not isinstance(raw, dict):
        return out
    titles = raw.get("titles")
    if isinstance(titles, list):
        for key in TITLE_ORDER:
            if key in titles:
                out["titles"].append(key)
    civic = raw.get("civic")
    if isinstance(civic, dict):
        for entry in CIVIC_MILESTONES:
            found = civic.get(entry["id"])
            if isinstance(found, int) and not isinstance(found, bool) and found >= 1:
                out["civic"][entry["id"]] = found
    return out


def _load_collection():
    raw = _read_local_storage_item(COLLECTION_STORAGE_KEY)
    if not raw:
        return _clean_collection(None)
    try:
        return _clean_collection(json.loads(raw))
    except (ValueError, TypeError):
        return _clean_collection(None)


def _store_collection():
    _write_local_storage_item(COLLECTION_STORAGE_KEY, json.dumps(collection))


def merge_collection(other):
    """Union a (validated) collection into the live one; returns True if it grew."""
    other = _clean_collection(other)
    grew = False
    for key in other["titles"]:
        if key not in collection["titles"]:
            collection["titles"].append(key)
            grew = True
    collection["titles"].sort(key=TITLE_ORDER.index)
    for found_id, found_round in other["civic"].items():
        if found_id not in collection["civic"]:
            collection["civic"][found_id] = found_round
            grew = True
    if grew:
        _store_collection()
    return grew


collection = _load_collection()
collection_open = False
collection_note = ""


def _collect_after_round(completed_round):
    """Record any civic milestone newly met and the personality title once the
    region has played TITLE_MIN_ROUND rounds. Returns the list of new names."""
    global collection_note
    found = []
    for entry in CIVIC_MILESTONES:
        if entry["id"] in collection["civic"]:
            continue
        if entry["test"](region, completed_round):
            collection["civic"][entry["id"]] = completed_round
            found.append(f"Civic milestone: {entry['name']}")
    if completed_round >= TITLE_MIN_ROUND:
        title = region_title_key(region)
        if title is not None and title not in collection["titles"]:
            collection["titles"].append(title)
            collection["titles"].sort(key=TITLE_ORDER.index)
            found.append(f"Title: {REGION_TITLES[title]['label']}")
    if found:
        _store_collection()
        collection_note = "New in your collection: " + "; ".join(found) + "."
        _display_achievement_toast("🗂️ " + found[0] + (f" (+{len(found) - 1} more)" if len(found) > 1 else ""))
    banked = _bank_run_stars(completed_round)
    if banked:
        found.append(banked)
        collection_note = (collection_note + " " if collection_note else "") + banked
        _display_achievement_toast("⭐ " + banked)
    return found


def collection_counts():
    return len(collection["civic"]), len(CIVIC_MILESTONES), len(collection["titles"]), len(REGION_TITLES)


def share_result():
    """Z-20: the headline numbers for the shared "Copy result" button, as a JSON string the page
    reads (it calls this by name through window.pyodide). Wellbeing score, the projected
    long-horizon wellbeing the coda shows, people integrated and rounds played."""
    stats = []
    if region.has_long_horizon_story():
        stats.append(f"{region.projected_wellbeing_score():.0f} projected generations from now")
    stats.append({"n": round(region.integrated_population), "one": "person integrated", "many": "people integrated"})
    stats.append({"n": max(0, region.round_number - 1), "one": "round", "many": "rounds"})
    return json.dumps({
        "game": "Drift",
        "score": round(region.wellbeing_score()),
        "unit": "wellbeing",
        "stats": stats,
    })


def render_collection_summary():
    civic, civic_total, titles, titles_total = collection_counts()
    document.getElementById("collection-summary-display").innerText = (
        f"Collection: {civic}/{civic_total} civic milestones, {titles}/{titles_total} titles."
    )
    title_key = region_title_key(region)
    title_el = document.getElementById("region-title-display")
    if title_key is None:
        title_el.innerText = "Region personality: still forming (spend about 100 funds to see it)."
    else:
        extra = " In your collection." if title_key in collection["titles"] else f" Added to your collection at round {TITLE_MIN_ROUND}."
        title_el.innerText = f"Region personality: {REGION_TITLES[title_key]['label']}.{extra}"
    toggle = document.getElementById("collection-toggle-button")
    toggle.innerText = "Hide Collection" if collection_open else f"🗂️ Collection ({civic + titles}/{civic_total + titles_total})"
    panel = document.getElementById("collection-panel")
    panel.hidden = not collection_open
    if not collection_open:
        return
    lines = []
    note = collection_note
    if note:
        lines.append(f"<p class=\"collection-note\">{note}</p>")
    lines.append(f"<p class=\"meter-label\">Civic milestones ({civic}/{civic_total})</p><ul class=\"collection-list\">")
    for entry in CIVIC_MILESTONES:
        found = collection["civic"].get(entry["id"])
        if found is not None:
            lines.append(
                f"<li class=\"collection-found\"><strong>✓ {entry['name']}</strong> (round {found}): {entry['text']}</li>"
            )
        else:
            lines.append(f"<li class=\"collection-locked\"><strong>🔒 Locked</strong>. Hint: {entry['hint']}</li>")
    lines.append(f"</ul><p class=\"meter-label\">Region personality titles ({titles}/{titles_total})</p><ul class=\"collection-list\">")
    for key in TITLE_ORDER:
        info = REGION_TITLES[key]
        if key in collection["titles"]:
            lines.append(f"<li class=\"collection-found\"><strong>✓ {info['label']}</strong>: {info['text']}</li>")
        else:
            lines.append(f"<li class=\"collection-locked\"><strong>🔒 Locked</strong>. Hint: {info['hint']}</li>")
    lines.append("</ul>")
    lines.append(run_history_html())
    document.getElementById("collection-list").innerHTML = "".join(lines)


def on_toggle_collection(event=None):
    global collection_open
    collection_open = not collection_open
    render_collection_summary()


# ---- GI-13 / GI-2 / GI-11 / GI-1 / GI-5 / GI-21 / I-18: civic tools ----------------
# Perfect Fit streak, Crisis Calendar and Surge Tests, Mayor's Council, Budget
# Autopilot, star ratings and the copy-able run summary. See the constants above
# the RegionState class for the rules.
calendar_note_text = ""
autopilot_log = []
council_note_text = ""
summary_note_text = ""


# ---- GI-25: region skins (cosmetic building palettes for the skyline) --------------------------------
# Dusk is always there; each other skin unlocks when its achievement is earned in any region on this browser,
# and stays unlocked (kept like the collection, per browser). The choice is a display preference in
# localStorage, never part of a save. The palettes themselves are CSS (`.region-visual[data-skin=...]`).
SKIN_STORAGE_KEY = "drift_skins_v1"
SKIN_CHOICE_KEY = "drift-skin"
SKINS = [
    {"id": "dusk", "label": "Dusk", "unlock": None},
    {"id": "seaside", "label": "Seaside", "unlock": "full_capacity_portfolio"},
    {"id": "alpine", "label": "Alpine", "unlock": "turning_point_reached"},
    {"id": "desert", "label": "Desert", "unlock": "crisis_averted"},
    {"id": "neon", "label": "Neon Future", "unlock": "thriving_region"},
]
SKIN_BY_ID = {skin["id"]: skin for skin in SKINS}


def _clean_skin_unlocks(raw):
    """The skin ids (other than the always-open Dusk) that a stored value says are unlocked."""
    if not isinstance(raw, list):
        return []
    return [skin["id"] for skin in SKINS if skin["unlock"] and skin["id"] in raw]


def _load_skin_unlocks():
    raw = _read_local_storage_item(SKIN_STORAGE_KEY)
    if not raw:
        return []
    try:
        return _clean_skin_unlocks(json.loads(raw))
    except (ValueError, TypeError):
        return []


def skin_unlocked(skin_id):
    skin = SKIN_BY_ID.get(skin_id)
    return skin is not None and (skin["unlock"] is None or skin_id in skins_unlocked)


def _load_skin_choice():
    raw = _read_local_storage_item(SKIN_CHOICE_KEY)
    return raw if raw in SKIN_BY_ID and (SKIN_BY_ID[raw]["unlock"] is None or raw in skins_unlocked) else "dusk"


skins_unlocked = _load_skin_unlocks()
skin_choice = _load_skin_choice()
skin_note = ""


def skin_lock_hint(skin):
    """What to do to unlock a skin: the achievement's own name."""
    by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
    entry = by_id.get(skin["unlock"])
    return f"Locked: earn the achievement {entry['label'] if entry else skin['unlock']}"


def unlock_skins(earned_ids):
    """Unlocks every skin whose achievement is in `earned_ids`; returns the newly unlocked skins."""
    newly = [
        skin for skin in SKINS
        if skin["unlock"] and skin["unlock"] in earned_ids and skin["id"] not in skins_unlocked
    ]
    for skin in newly:
        skins_unlocked.append(skin["id"])
    if newly:
        _write_local_storage_item(SKIN_STORAGE_KEY, json.dumps(skins_unlocked))
    return newly


def choose_skin(skin_id):
    global skin_choice
    if not skin_unlocked(skin_id):
        return False
    skin_choice = skin_id
    _write_local_storage_item(SKIN_CHOICE_KEY, skin_id)
    return True


def render_skins():
    document.getElementById("region-visual").dataset.skin = skin_choice
    for skin in SKINS:
        button = document.getElementById(f"skin-{skin['id']}-button")
        open_ = skin_unlocked(skin["id"])
        button.disabled = not open_
        button.title = "" if open_ else skin_lock_hint(skin)
        button.innerText = skin["label"] if open_ else f"🔒 {skin['label']}"
        _set_pressed(button, skin["id"] == skin_choice)
    document.getElementById("skin-note").innerText = skin_note


def _make_skin_handler(skin_id):
    def handler(event=None):
        if choose_skin(skin_id):
            announce(f"{SKIN_BY_ID[skin_id]['label']} skin chosen")
        render_skins()
    return handler


def perfect_fit_message():
    """GI-13: the streak line shown beside the forecast."""
    streak = region.perfect_fit_streak
    bonus = PERFECT_FIT_FUNDS_PER_STREAK * min(streak, PERFECT_FIT_STREAK_CAP)
    best = region.best_perfect_fit_streak
    if region.total_capacity() > 0 and region.total_arrivals > 0:
        slack = region.total_capacity() + region.coverage_bonus() - region.total_arrivals
        if region.is_perfect_fit():
            now = f"Holding a Perfect Fit right now ({slack:.0f} spare)."
        elif slack < 0:
            now = f"Not a Perfect Fit right now: {-slack:.0f} short."
        else:
            now = f"Not a Perfect Fit right now: {slack:.0f} spare (the limit is {PERFECT_FIT_MARGIN:.0f})."
    else:
        now = "Build some capacity to start."
    if streak > 0:
        head = f"Perfect Fit streak: {streak} round(s), +{bonus:.0f} funds a round."
    else:
        head = (
            f"Perfect Fit: end a round with capacity covering everyone who has arrived and no more than "
            f"{PERFECT_FIT_MARGIN:.0f} to spare. Each round in a row adds {PERFECT_FIT_FUNDS_PER_STREAK:.0f} funds of "
            f"income, up to {PERFECT_FIT_FUNDS_PER_STREAK * PERFECT_FIT_STREAK_CAP:.0f}."
        )
    tail = f" Best streak this region: {best}." if best > 0 else ""
    return f"{head} {now}{tail}"


def calendar_next_event(after_round):
    """The first scheduled event on a round after `after_round`, or None."""
    for r in range(after_round + 1, CALENDAR_LAST_ROUND + 1):
        event = calendar_event_for_round(r)
        if event is not None:
            return event
    return None


def calendar_describe(event, braced=False):
    spec = CALENDAR_KINDS[event["kind"]]
    label = event["name"] if event["kind"] == "boss" else spec["label"]
    if event["kind"] == "boss":
        label = f"Surge Test, {event['name']}"
    tag = " Braced." if braced else ""
    return f"{spec['icon']} {label}: {spec['text']}.{tag}"


def calendar_message():
    """GI-2: the Next Round preview, from fixed data only."""
    if not region.calendar_enabled:
        return (
            "Off. Switch it on for a fixed, visible schedule of events: surges, budget cuts, floods and bumper "
            "harvests every 4 rounds from round 8, and three named Surge Tests at rounds 25, 50 and 75. Each "
            "is shown a round ahead and can be softened by paying to brace. Nothing is random and nothing ends a run."
        )
    lines = []
    here = region.calendar_event()
    if here is not None:
        lines.append(f"This round (round {region.round_number}): " + calendar_describe(here, region.round_number in region.braced_rounds))
    ahead = region.calendar_event(region.round_number + 1)
    if ahead is not None:
        lines.append(f"Next round (round {ahead['round']}): " + calendar_describe(ahead, ahead["round"] in region.braced_rounds))
    if not lines:
        later = calendar_next_event(region.round_number)
        if later is None:
            lines.append("No more events are scheduled in this run.")
        else:
            lines.append(f"Nothing this round or next. Next event: round {later['round']}, {later['name']}.")
    return " ".join(lines)


def calendar_result_message(entry):
    """What the most recent event did, with the Surge Test 'held the line' card."""
    kind = entry["kind"]
    spec = CALENDAR_KINDS[kind]
    if kind == "boss":
        name = BOSS_ROUNDS.get(entry["round"], "Surge Test")
        if entry["held"]:
            return (
                f"🏛️ Held the line! {name} (round {entry['round']}) came and your capacity covered "
                "everyone who arrived. That is what preparing ahead of a surge looks like."
            )
        return (
            f"🏛️ {name} (round {entry['round']}) outran your capacity this time, so strain will show it. "
            "Nothing is lost for good: build and it recovers."
        )
    if entry["held"] is True:
        return f"{spec['icon']} {spec['label']} at round {entry['round']}: capacity still covers everyone who has arrived."
    if entry["held"] is False:
        return f"{spec['icon']} {spec['label']} at round {entry['round']}: it outran capacity for now. Build and it recovers."
    return f"{spec['icon']} {spec['label']} at round {entry['round']}: done."


def _reset_civic_notes():
    global calendar_note_text, council_note_text
    calendar_note_text = ""
    council_note_text = ""


def on_toggle_calendar(event=None):
    global calendar_note_text
    region.calendar_enabled = not region.calendar_enabled
    calendar_note_text = ""
    render()


def on_brace(event=None):
    global calendar_note_text
    target = region.brace_target()
    if target is not None and region.brace():
        calendar_note_text = f"Braced for {target['name']}. {CALENDAR_KINDS[target['kind']]['brace_cost']:.0f} funds spent."
        announce(calendar_note_text)
    elif target is None:
        announce("Nothing to brace for right now")
    else:
        announce(
            f"Cannot brace for {target['name']}: it costs {CALENDAR_KINDS[target['kind']]['brace_cost']:.0f} "
            f"and you have {region.funds:.0f}"
        )
    render()


def render_calendar():
    toggle = document.getElementById("calendar-toggle-button")
    toggle.innerText = "Crisis Calendar: ON" if region.calendar_enabled else "Crisis Calendar: OFF"
    if region.calendar_enabled:
        toggle.classList.add("active")
    else:
        toggle.classList.remove("active")
    document.getElementById("calendar-display").innerText = calendar_message()
    brace = document.getElementById("calendar-brace-button")
    target = region.brace_target()
    brace.hidden = not region.calendar_enabled
    if target is not None:
        cost = CALENDAR_KINDS[target["kind"]]["brace_cost"]
        brace.innerText = f"Brace for {target['name']} ({cost:.0f} funds)"
        brace.disabled = region.funds < cost
    else:
        brace.innerText = "Nothing to brace for"
        brace.disabled = True
    note = document.getElementById("calendar-note")
    text = calendar_note_text
    if not text and region.calendar_enabled and region.calendar_log:
        last = region.calendar_log[-1]
        if last["round"] == region.round_number - 1:
            text = calendar_result_message(last)
    note.innerText = text
    note.hidden = text == ""


# -- GI-1: Mayor's Council --
def council_pending_picks(r=None):
    r = region if r is None else r
    completed = max(0, r.round_number - 1)
    earned = min(completed // COUNCIL_INTERVAL, len(COUNCIL_PROGRAMS))
    return max(0, earned - len(r.council_picks))


def council_options(r=None):
    r = region if r is None else r
    options = {}
    for branch in COUNCIL_BRANCHES:
        program = council_next_program(branch, r.council_picks)
        if program is not None:
            options[branch] = program
    return options


def council_pick(branch):
    if council_pending_picks() <= 0:
        return False
    program = council_options().get(branch)
    if program is None:
        return False
    region.council_picks.append(program["id"])
    return True


def council_status_message():
    if len(region.council_picks) >= len(COUNCIL_PROGRAMS):
        return "Every program has been adopted."
    pending = council_pending_picks()
    if pending > 0:
        return f"The council meets: choose one program ({pending} pick{'s' if pending != 1 else ''} waiting)."
    completed = max(0, region.round_number - 1)
    next_at = (completed // COUNCIL_INTERVAL + 1) * COUNCIL_INTERVAL
    return f"Next council pick after round {next_at}. Programs adopted: {len(region.council_picks)} of {len(COUNCIL_PROGRAMS)}."


def council_tree_html():
    rows = []
    for branch, label in COUNCIL_BRANCHES.items():
        rows.append(f"<li><strong>{label}</strong><ul>")
        for program in COUNCIL_PROGRAMS:
            if program["branch"] != branch:
                continue
            mark = "✓" if program["id"] in region.council_picks else "○"
            rows.append(f"<li>{mark} <strong>{program['name']}</strong> (tier {program['tier']}): {program['text']}</li>")
        rows.append("</ul></li>")
    return "<ul class=\"council-tree\">" + "".join(rows) + "</ul>"


def on_council_pick(branch):
    global council_note_text
    program = council_options().get(branch)
    if program is not None and council_pick(branch):
        council_note_text = f"Adopted: {program['name']}. {program['text']}."
    render()


def _make_council_handler(branch):
    def handler(event=None):
        on_council_pick(branch)

    return handler


def render_council():
    document.getElementById("council-status").innerText = (council_note_text + " " if council_note_text else "") + council_status_message()
    pending = council_pending_picks()
    options = council_options()
    for branch, label in COUNCIL_BRANCHES.items():
        button = document.getElementById(f"council-pick-{branch}")
        program = options.get(branch)
        if program is None:
            button.innerText = f"{label}: complete"
            button.disabled = True
            button.title = "Every program on this branch has been adopted."
        else:
            button.innerText = f"{label}: {program['name']}"
            button.disabled = pending <= 0
            button.title = program["text"]
    document.getElementById("council-tree").innerHTML = council_tree_html()


# -- GI-5: Budget Autopilot --
def _clean_autopilot(raw):
    """A valid rules dict from anything (unknown or bad values fall back to the defaults)."""
    out = dict(AUTOPILOT_DEFAULT_RULES)
    if not isinstance(raw, dict):
        return out
    if "services_share" in raw and raw["services_share"] in AUTOPILOT_SERVICES_SHARES:
        out["services_share"] = raw["services_share"]
    if "surplus" in raw and raw["surplus"] in AUTOPILOT_SURPLUS_CHOICES:
        out["surplus"] = raw["surplus"]
    reserve = raw.get("reserve")
    if isinstance(reserve, (int, float)) and not isinstance(reserve, bool) and reserve in AUTOPILOT_RESERVES:
        out["reserve"] = int(reserve)
    rounds = raw.get("rounds")
    if isinstance(rounds, int) and not isinstance(rounds, bool) and rounds in AUTOPILOT_ROUND_CHOICES:
        out["rounds"] = rounds
    return out


def _autopilot_log(line):
    autopilot_log.append(line)
    del autopilot_log[:-AUTOPILOT_LOG_MAX]


def _autopilot_pick():
    """The next purchase the rules call for, as (capacity type, reason), or (None, None)."""
    rules = region.autopilot
    spare = region.funds - rules["reserve"]
    target = rules["services_share"]
    if target is not None and spare >= INVEST_COST["services"]:
        total = region.total_capacity()
        share = region.capacity["services"] / total if total > 0 else 0.0
        if share < target:
            return "services", f"services were {share * 100:.0f}% of capacity, target {target * 100:.0f}%"
    surplus = rules["surplus"]
    if surplus is not None and spare >= INVEST_COST[surplus]:
        return surplus, "surplus above the reserve"
    return None, None


def _autopilot_buy_round():
    rules = region.autopilot
    bought = {}
    reasons = {}
    for _ in range(AUTOPILOT_MAX_BUYS_PER_ROUND):
        capacity_type, reason = _autopilot_pick()
        if capacity_type is None or not region.invest(capacity_type):
            break
        bought[capacity_type] = bought.get(capacity_type, 0) + 1
        reasons.setdefault(capacity_type, reason)
    if bought:
        parts = [f"{n} {CAPACITY_LABEL[t]} ({reasons[t]})" for t, n in bought.items()]
        _autopilot_log(f"Round {region.round_number}: bought " + "; ".join(parts) + ".")
    else:
        _autopilot_log(f"Round {region.round_number}: nothing to buy (funds {region.funds:.0f}, reserve {rules['reserve']}).")


def autopilot_run():
    """Run the Budget Autopilot for the set number of rounds. Returns (rounds, reason)."""
    rounds = region.autopilot["rounds"]
    advanced, reason = _run_auto_rounds(rounds, before_round=_autopilot_buy_round)
    unit = "round" if advanced == 1 else "rounds"
    _autopilot_log(f"Stopped after {advanced} {unit}: " + (reason if reason else "the run finished."))
    return advanced, reason


def autopilot_rules_text():
    rules = region.autopilot
    share = "no services-share rule" if rules["services_share"] is None else f"keep services at {rules['services_share'] * 100:.0f}% of capacity"
    surplus = "hold the surplus" if rules["surplus"] is None else f"spend surplus on {CAPACITY_LABEL[rules['surplus']].lower()}"
    return f"Rules: {share}; {surplus}; always keep {rules['reserve']} funds back; run {rules['rounds']} rounds."


def on_autopilot_change(event=None):
    def value(element_id, default):
        return getattr(document.getElementById(element_id), "value", default)

    share_raw = str(value("autopilot-share-select", "50"))
    surplus_raw = str(value("autopilot-surplus-select", "housing"))
    raw = {
        "services_share": None if share_raw == "off" else _to_float(share_raw, 50.0) / 100.0,
        "surplus": None if surplus_raw == "hold" else surplus_raw,
        "reserve": _to_int(value("autopilot-reserve-select", "40"), 40),
        "rounds": _to_int(value("autopilot-rounds-select", "10"), 10),
    }
    if raw["services_share"] is not None:
        raw["services_share"] = round(raw["services_share"], 2)
    region.autopilot = _clean_autopilot(raw)
    render_autopilot()


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


def on_autopilot_run(event=None):
    global round_tools_message, collection_note
    collection_note = ""
    marks_before = _round_marks()
    advanced, reason = autopilot_run()
    unit = "round" if advanced == 1 else "rounds"
    round_tools_message = (
        f"Autopilot ran {advanced} {unit} and stopped early: {reason}." if reason
        else f"Autopilot ran {advanced} {unit}."
    )
    render()
    announce(round_tools_message)
    if advanced:
        announce(round_announcement_text(marks_before))
    _check_new_achievements_for_toast()


def render_autopilot():
    rules = region.autopilot
    share = rules["services_share"]
    document.getElementById("autopilot-share-select").value = "off" if share is None else str(int(round(share * 100)))
    document.getElementById("autopilot-surplus-select").value = "hold" if rules["surplus"] is None else rules["surplus"]
    document.getElementById("autopilot-reserve-select").value = str(rules["reserve"])
    document.getElementById("autopilot-rounds-select").value = str(rules["rounds"])
    document.getElementById("autopilot-run-button").innerText = f"▶ Run Autopilot ({rules['rounds']} rounds)"
    document.getElementById("autopilot-note").innerText = autopilot_rules_text()
    log = document.getElementById("autopilot-log")
    log.innerHTML = "".join(f"<li>{line}</li>" for line in reversed(autopilot_log[-12:]))


# -- GI-21: star ratings --
def star_goals(r=None):
    """Stars (0 to 3) on the three goals: wellbeing, speed to net-positive, efficiency of funds."""
    r = region if r is None else r
    wellbeing = sum(1 for bound in RUN_STARS_WELLBEING if r.wellbeing_score() >= bound)
    speed = 0
    if r.net_positive_round is not None:
        speed = sum(1 for bound in RUN_STARS_NET_POSITIVE_ROUND if r.net_positive_round <= bound)
    roi = r.investment_roi()
    efficiency = 0 if roi is None else sum(1 for bound in RUN_STARS_ROI if roi >= bound)
    return {"wellbeing": wellbeing, "speed": speed, "efficiency": efficiency}


def stars_text(count):
    return "★" * count + "☆" * (3 - count)


def run_stars_message():
    goals = star_goals()
    parts = (
        f"Wellbeing {stars_text(goals['wellbeing'])}  Speed {stars_text(goals['speed'])}  "
        f"Efficiency {stars_text(goals['efficiency'])}"
    )
    if region.stars_banked is not None:
        return f"Run stars: {parts}. Banked into your run history at round {region.stars_banked}."
    return f"Run stars so far: {parts}. They are banked into your run history when round {RUN_STARS_ROUND} finishes."


def _clean_run_history(raw):
    out = []
    if not isinstance(raw, list):
        return out
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        stars = entry.get("stars")
        token = entry.get("token")
        if (
            not isinstance(stars, list) or len(stars) != 3 or not isinstance(token, str)
            or not all(isinstance(n, int) and not isinstance(n, bool) and 0 <= n <= 3 for n in stars)
        ):
            continue
        name = entry.get("name")
        rounds = entry.get("round")
        out.append({
            "name": name[:REGION_NAME_MAX_LENGTH] if isinstance(name, str) else "",
            "round": rounds if isinstance(rounds, int) and not isinstance(rounds, bool) and rounds >= 1 else RUN_STARS_ROUND,
            "stars": list(stars),
            "token": token[:80],
        })
    return out[-RUN_HISTORY_MAX:]


def _load_run_history():
    raw = _read_local_storage_item(RUN_HISTORY_STORAGE_KEY)
    if not raw:
        return []
    try:
        return _clean_run_history(json.loads(raw))
    except (ValueError, TypeError):
        return []


run_history = _load_run_history()


def _run_token():
    return f"{region.region_name}|{region.total_arrivals:.1f}|{region.cumulative_integration_contribution:.1f}"


def _bank_run_stars(completed_round):
    """Bank the run's stars once, when round RUN_STARS_ROUND has finished. Returns a message or None."""
    if completed_round < RUN_STARS_ROUND or region.stars_banked is not None:
        return None
    region.stars_banked = completed_round
    goals = star_goals()
    token = _run_token()
    if any(entry["token"] == token for entry in run_history):
        return None
    run_history.append({
        "name": region.region_name, "round": completed_round,
        "stars": [goals["wellbeing"], goals["speed"], goals["efficiency"]], "token": token,
    })
    del run_history[:-RUN_HISTORY_MAX]
    _write_local_storage_item(RUN_HISTORY_STORAGE_KEY, json.dumps(run_history))
    total = sum(run_history[-1]["stars"])
    return f"Run banked at round {completed_round}: {total} of 9 stars."


def run_history_html():
    if not run_history:
        return "<p class=\"collection-locked\">No banked runs yet. Reach the end of round " + str(RUN_STARS_ROUND) + " to bank your first.</p>"
    best = sorted(run_history, key=lambda e: (-sum(e["stars"]), run_history.index(e)))[:5]
    items = []
    for entry in best:
        label = entry["name"] or "Unnamed region"
        s = entry["stars"]
        items.append(
            f"<li><strong>{stars_text(s[0])} {stars_text(s[1])} {stars_text(s[2])}</strong> "
            f"({sum(s)} of 9) {label}, round {entry['round']}</li>"
        )
    return (
        "<p class=\"meter-label\">Best star combinations (wellbeing, speed, efficiency)</p>"
        "<ul class=\"collection-list\">" + "".join(items) + "</ul>"
    )


# -- I-18: copy run summary --
CURVE_BLOCKS = "▁▂▃▄▅▆▇█"
CURVE_WIDTH = 30


def wellbeing_band(score):
    if score >= MODEL_REGION_WELLBEING_SCORE:
        return "Model Region"
    if score >= THRIVING_WELLBEING_SCORE:
        return "Thriving"
    if score >= 40:
        return "Managing"
    return "Struggling"


def wellbeing_curve(values, width=CURVE_WIDTH):
    """A block-character curve (0 to 100) of up to `width` evenly spaced samples."""
    if not values:
        return ""
    if len(values) > width:
        picks = [values[round(i * (len(values) - 1) / (width - 1))] for i in range(width)]
    else:
        picks = list(values)
    out = []
    for v in picks:
        index = int(max(0.0, min(99.999, v)) / 100.0 * len(CURVE_BLOCKS))
        out.append(CURVE_BLOCKS[index])
    return "".join(out)


def run_summary_text():
    name = region.region_name or "Unnamed region"
    completed = max(0, region.round_number - 1)
    score = region.wellbeing_score()
    tags = []
    if region.accelerated_severity_enabled:
        tags.append(f"Accelerated Severity ({ACCELERATED_SEVERITY_MULTIPLIER:.0f}x)")
    if region.crisis_start_enabled:
        tags.append("Crisis Start")
    if region.calendar_enabled:
        tags.append("Crisis Calendar")
    if region.council_picks:
        tags.append("Council: " + ", ".join(COUNCIL_BY_ID[pid]["name"] for pid in region.council_picks))
    goals = star_goals()
    lines = [
        f"Drift: {name}",
        f"After {completed} rounds: {wellbeing_band(score)}, wellbeing {score:.0f}, strain {region.strain_level()}",
        f"Wellbeing curve: {wellbeing_curve(region.wellbeing_log)}",
        "Setup: " + ("; ".join(tags) if tags else "standard"),
        f"Stars: wellbeing {stars_text(goals['wellbeing'])} speed {stars_text(goals['speed'])} efficiency {stars_text(goals['efficiency'])}",
    ]
    return "\n".join(lines)


def on_copy_summary(event=None):
    global summary_note_text
    text = run_summary_text()
    area = document.getElementById("summary-copy-area")
    if _copy_to_clipboard(text):
        area.hidden = True
        summary_note_text = "Copied the run summary to the clipboard."
    else:
        area.hidden = False
        area.value = text
        summary_note_text = "Could not copy automatically. Select the text below and copy it yourself."
    document.getElementById("round-tools-note").innerText = summary_note_text
    document.getElementById("round-tools-note").hidden = False


def render_civic_tools():
    document.getElementById("perfect-fit-display").innerText = perfect_fit_message()
    render_calendar()
    render_council()
    render_autopilot()
    document.getElementById("run-stars-display").innerText = run_stars_message()


# ---- I-24: live tab title ----------------------------------------------------
# I-12 / I-16: what the trend graph shows. Display choices only: never saved, back to the defaults on reload.
trend_range = "all"
trend_layers = dict(TREND_LAYER_DEFAULT)


def render_trend_graph():
    control_wellbeing = None
    if region.round_number > 2:
        control_wellbeing = _simulate_control_region(
            region.round_number, region.accelerated_severity_enabled, region.calendar_enabled
        ).wellbeing_log
    trend_svg = trend_graph_svg(
        region.strain_log, region.wellbeing_log, control_wellbeing,
        first_round=region.round_number - len(region.strain_log),
        layers=trend_layers,
        events=trend_events(region) if trend_layers["events"] else [],
        roi_history=region.roi_log,
        view_rounds=TREND_RANGES[trend_range],
    )
    document.getElementById("trend-graph").innerHTML = trend_svg
    document.getElementById("trend-graph-message").innerText = (
        "" if trend_svg else "Not enough rounds yet to show a trend."
    )
    document.getElementById("trend-legend").innerText = trend_legend_text(trend_layers)
    for key in TREND_RANGES:
        button = document.getElementById(f"trend-range-{key}-button")
        _set_pressed(button, key == trend_range)
    for key in TREND_LAYER_ORDER:
        _set_pressed(document.getElementById(f"trend-layer-{key}-button"), trend_layers[key])


def _set_pressed(button, on):
    button.setAttribute("aria-pressed", "true" if on else "false")
    if on:
        button.classList.add("active")
    else:
        button.classList.remove("active")


def _make_trend_range_handler(key):
    def handler(event=None):
        global trend_range
        trend_range = key
        render_trend_graph()
        label = "all rounds" if TREND_RANGES[key] is None else f"the last {TREND_RANGES[key]} rounds"
        announce(f"Trend graph shows {label}")
    return handler


def _make_trend_layer_handler(key):
    def handler(event=None):
        trend_layers[key] = not trend_layers[key]
        render_trend_graph()
        announce(f"{TREND_LAYER_LABEL[key]} {'shown' if trend_layers[key] else 'hidden'} on the trend graph")
    return handler


def tab_title():
    name = f" - {region.region_name}" if region.region_name else ""
    return f"Drift - R{region.round_number} - {region.strain_level().capitalize()}{name}"


def render():
    global rewind_armed
    rewind_armed = False  # any other action cancels a half-confirmed rewind
    _sync_spillover()
    render_info_page()
    render_neighbor()
    render_policies()
    render_second_wave()
    render_real_world()
    _maybe_record_learning()
    render_learning()
    update_achievements_display()
    _maybe_update_personal_best()
    render_personal_best()
    document.getElementById("round-display").innerText = f"Round {region.round_number}"
    document.getElementById("funds-display").innerText = f"Funds: {region.funds:.0f}"
    document.getElementById("total-capacity-display").innerText = (
        f"Total capacity: {region.total_capacity():.0f}"
    )
    # I19: persistent net-positive badge in the top status readouts.
    net_positive_badge = document.getElementById("net-positive-badge")
    badge_text = net_positive_badge_text(region)
    net_positive_badge.hidden = badge_text is None
    net_positive_badge.innerText = badge_text or ""

    document.getElementById("arrivals-display").innerText = (
        f"Arrivals this round: {region.arrivals_this_round():.0f} people "
        f"(background severity: {region.background_severity:.1f})"
    )
    # I16: arrival-dot stream density/speed tracking real arrivals.
    arrivals_now = region.arrivals_this_round()
    visible_dot_count = arrival_stream_dot_count(arrivals_now)
    dot_duration = arrival_stream_animation_duration(arrivals_now)
    for dot_index in range(1, ARRIVAL_STREAM_MAX_DOTS + 1):
        dot_el = document.getElementById(f"arrival-dot-{dot_index}")
        dot_el.hidden = dot_index > visible_dot_count
        dot_el.style.animationDuration = scaled_seconds(dot_duration)
    # I20: one-time callout once the stream's density has genuinely moved
    # since the severity toggle was first switched on.
    maybe_flag_severity_density_change(region, visible_dot_count)
    density_callout = document.getElementById("severity-density-callout")
    density_callout.hidden = not region.severity_density_callout_shown
    if region.severity_density_callout_shown:
        density_callout.innerText = SEVERITY_DENSITY_CALLOUT_TEXT
    document.getElementById("total-arrivals-display").innerText = (
        f"Total arrivals (lifetime): {region.total_arrivals:.0f} people"
    )
    document.getElementById("strain-display").innerText = (
        f"Strain: {region.strain_fraction() * 100:.0f}% ({region.strain_level()})"
    )
    strain_bar = document.getElementById("strain-bar")
    strain_bar.style.width = f"{region.strain_fraction() * 100:.0f}%"
    strain_bar.className = f"meter-fill meter-fill--strain strain-heartbeat strain--{region.strain_level()}"
    # GI-19: the readout and its bar pulse at a beat that follows the strain level.
    heartbeat = scaled_seconds(strain_heartbeat_seconds(region.strain_level()))
    strain_bar.style.animationDuration = heartbeat
    strain_display = document.getElementById("strain-display")
    strain_display.className = "status-line strain-heartbeat-text"
    strain_display.style.animationDuration = heartbeat
    # I6: one-line consequence description per strain level.
    document.getElementById("strain-consequence-display").innerText = strain_consequence_message(region)

    document.getElementById("integrated-display").innerText = (
        f"Integrated: {region.integrated_population:.0f} people "
        f"(contributing {region.integration_contribution():.0f} funds/round)"
    )
    document.getElementById("pending-display").innerText = (
        f"Pending integration: {region.pending_population():.0f} people"
    )
    render_pending_pipeline()
    turning_point_display = document.getElementById("integration-turning-point-display")
    turning_point_message = integration_turning_point_message(region)
    turning_point_display.hidden = turning_point_message is None
    turning_point_display.innerText = turning_point_message or ""

    # I3: explicit in-play comparison to the Uganda policy model.
    document.getElementById("uganda-comparison-display").innerText = uganda_comparison_message(region)
    # I9: real-world resettlement-outcome benchmark comparison.
    document.getElementById("resettlement-benchmark-display").innerText = resettlement_benchmark_message(
        region
    )

    document.getElementById("service-quality-display").innerText = (
        f"Service quality: {region.service_quality():.0f}"
    )
    document.getElementById("service-quality-bar").style.width = f"{region.service_quality():.0f}%"
    document.getElementById("economic-health-display").innerText = (
        f"Economic health: {region.economic_health():.0f}"
    )
    document.getElementById("economic-health-bar").style.width = f"{region.economic_health():.0f}%"
    # I20: economic health's funds-to-score scale reference point.
    document.getElementById("economic-health-reference-display").innerText = economic_health_reference_note()
    document.getElementById("social-cohesion-display").innerText = (
        f"Social cohesion: {region.social_cohesion():.0f}"
    )
    document.getElementById("social-cohesion-bar").style.width = f"{region.social_cohesion():.0f}%"
    document.getElementById("wellbeing-display").innerText = (
        f"Wellbeing score: {region.wellbeing_score():.0f}"
    )
    # I-22: short sources for the phone's sticky bar: round and funds (the coin stands for funds), strain, wellbeing with its band name.
    document.getElementById("hud-round-display").innerText = f"R{region.round_number} 💰 {region.funds:.0f}"
    document.getElementById("hud-strain-display").innerText = (
        f"{region.strain_fraction() * 100:.0f}% {region.strain_level()}"
    )
    document.getElementById("hud-wellbeing-display").innerText = (
        f"{region.wellbeing_score():.0f} {wellbeing_band(region.wellbeing_score())}"
    )
    document.getElementById("wellbeing-message-display").innerText = wellbeing_message(
        region.wellbeing_score()
    )

    # I5: one-time thriving-band callout.
    thriving_display = document.getElementById("thriving-callout-display")
    thriving_message = thriving_callout_message(region)
    thriving_display.hidden = thriving_message is None
    thriving_display.innerText = thriving_message or ""

    document.getElementById("checkpoint-display").innerText = checkpoint_message(region)

    # I11: periodic session-milestone summary.
    milestone_display = document.getElementById("session-milestone-display")
    milestone_message = session_milestone_message(region)
    milestone_display.hidden = milestone_message is None
    milestone_display.innerText = milestone_message or ""
    if region.milestone_just_updated:
        region.milestone_just_updated = False
        _pulse("session-milestone-display", "session-milestone--pulse")

    # I17: passive unmanaged control region, for contrast -- not enough
    # signal to show anything meaningful before at least one round has
    # completed.
    control_display = document.getElementById("control-region-contrast-display")
    if region.round_number > 1:
        control_region = _simulate_control_region(region.round_number, region.accelerated_severity_enabled, region.calendar_enabled)
        control_display.hidden = False
        control_display.innerText = control_region_contrast_message(control_region)
    else:
        control_display.hidden = True
        control_display.innerText = ""

    control_display.title = CONTROL_REGION_TOOLTIP  # I12

    # I28: what triggers the strain-consequence messages.
    document.getElementById("strain-consequence-display").title = strain_consequence_tooltip()
    # I9: capacity-planning forecast. I30: next capacity milestone.
    document.getElementById("forecast-display").innerText = forecast_message(region)
    document.getElementById("capacity-milestone-display").innerText = capacity_milestone_message(region)
    # I27: capacity-investment ROI.
    document.getElementById("roi-display").innerText = roi_message(region)
    # I16: recovery-path Model Region badge.
    recovery_badge = document.getElementById("recovery-badge")
    recovery_text = recovery_badge_text(region, _ever_reached_critical_strain())
    recovery_badge.hidden = recovery_text is None
    recovery_badge.innerText = recovery_text or ""
    # I11: thriving vignette.
    vignette_box = document.getElementById("thriving-vignette-box")
    vignette_text = thriving_vignette_message(region)
    vignette_box.hidden = vignette_text is None
    document.getElementById("thriving-vignette-display").innerText = vignette_text or ""
    # I24: per-sub-score trend arrows. I14: threshold number on the target marker.
    for key, arrow_id, target_id in (
        ("service", "service-quality-trend", "service-quality-target"),
        ("economy", "economic-health-trend", "economic-health-target"),
        ("cohesion", "social-cohesion-trend", "social-cohesion-target"),
    ):
        arrow_el = document.getElementById(arrow_id)
        arrow = subscore_arrow(region.subscore_log, key)
        arrow_el.innerText = arrow
        arrow_el.title = {"▲": "improving", "▶": "plateauing", "▼": "declining"}.get(arrow, "")
        document.getElementById(arrow_id.replace("-trend", "-spark")).innerHTML = subscore_sparkline(
            region.subscore_log, key
        )
        document.getElementById(target_id).innerText = (
            f"Thriving marker: {THRIVING_WELLBEING_SCORE:.0f}"
        )

    # I23: region name, I15 crisis start, I19 reallocation controls.
    crisis_button = document.getElementById("crisis-start-toggle-button")
    crisis_button.innerText = (
        "Crisis Start: ON" if region.crisis_start_enabled else "Crisis Start: OFF"
    )
    crisis_button.disabled = not region.can_toggle_crisis_start()
    crisis_button.title = (
        "Optional harder start, choosable only before round 1: begin with fewer funds and a "
        "backlog of people already arrived, to try recovering from behind."
    )
    if region.crisis_start_enabled:
        crisis_button.classList.add("active")
    else:
        crisis_button.classList.remove("active")
    document.getElementById("realloc-button").disabled = not (
        region.funds >= REALLOCATION_FUNDS_COST
        and any(region.capacity[t] >= REALLOCATION_UNITS for t in CAPACITY_TYPES)
    )
    document.getElementById("realloc-note").innerText = (
        f"Move {REALLOCATION_UNITS:.0f} capacity between types for {REALLOCATION_FUNDS_COST:.0f} funds; "
        f"{REALLOCATION_LOSS_FRACTION * 100:.0f}% of the moved capacity is lost in the transition."
    )
    # I5 coda legacy line, I21 side-by-side control comparison.
    document.getElementById("coda-legacy-display").innerText = coda_legacy_message(
        region.coda_legacy_choice
    )
    if coda_visible and region.has_long_horizon_story():
        document.getElementById("coda-control-display").innerText = coda_control_message(
            region, _simulate_control_region(region.round_number, region.accelerated_severity_enabled, region.calendar_enabled)
        )

    # I2: skyline building count/height tracking real capacity.
    visible_building_count = region_visual_building_count(region.total_capacity())
    building_height_scale = region_visual_height_scale(region.total_capacity())
    for index, building_id in enumerate(REGION_VISUAL_BUILDING_IDS):
        building_el = document.getElementById(f"region-visual-building-{building_id}")
        building_el.hidden = index >= visible_building_count
        building_el.style.transform = f"scaleY({building_height_scale:.2f})"

    # I1: strain/wellbeing trend graph (I-12 layers and event markers, I-16 range and crosshair).
    render_trend_graph()

    coda_button = document.getElementById("coda-button")
    coda_button.hidden = not region.has_long_horizon_story()
    coda_button.innerText = "Hide Long-Horizon Outcomes" if coda_visible else "View Long-Horizon Outcomes"
    # I15: one-time highlight/pulse the moment the coda first becomes
    # available -- consume-and-reset, so it only ever fires once.
    if region.coda_just_became_available:
        region.coda_just_became_available = False
        _pulse("coda-button", "coda-button--pulse")

    coda_section = document.getElementById("coda-section")
    coda_section.hidden = not (coda_visible and region.has_long_horizon_story())
    if coda_visible and region.has_long_horizon_story():
        document.getElementById("coda-message-display").innerText = long_horizon_coda_message(region)
        _render_coda_comparison(
            "service-quality", region.service_quality(), region.projected_service_quality()
        )
        _render_coda_comparison(
            "economic-health", region.economic_health(), region.projected_economic_health()
        )
        _render_coda_comparison(
            "social-cohesion", region.social_cohesion(), region.projected_social_cohesion()
        )
        document.getElementById("coda-wellbeing-display").innerText = (
            f"Projected long-horizon wellbeing: {region.projected_wellbeing_score():.0f} "
            f"(from {region.wellbeing_score():.0f} today)"
        )

    for capacity_type in CAPACITY_TYPES:
        document.getElementById(f"{capacity_type}-name").innerText = (
            f"{CAPACITY_ICON[capacity_type]} {CAPACITY_LABEL[capacity_type]}"
        )
        document.getElementById(f"{capacity_type}-count").innerText = (
            f"{region.capacity[capacity_type]:.0f}"
        )
        button = document.getElementById(f"{capacity_type}-invest-button")
        button.innerText = f"{CAPACITY_LABEL[capacity_type]} ({INVEST_COST[capacity_type]:.0f})"
        button.disabled = region.funds < INVEST_COST[capacity_type]
        # I7: one-line effect summary directly on each investment row.
        document.getElementById(f"{capacity_type}-effect-display").innerText = (
            CAPACITY_EFFECT_SUMMARY[capacity_type]
        )

    # I13: opt-in difficulty toggle -- purely reflects the current
    # setting, never touches strain/arrivals math directly (see
    # ACCELERATED_SEVERITY_MULTIPLIER's comment above).
    accelerated_button = document.getElementById("accelerated-severity-toggle-button")
    accelerated_button.innerText = (
        f"🔥 Accelerated Severity: ON ({ACCELERATED_SEVERITY_MULTIPLIER:.0f}x)"
        if region.accelerated_severity_enabled
        else "Accelerated Severity: OFF"
    )
    if region.accelerated_severity_enabled:
        accelerated_button.classList.add("active")
    else:
        accelerated_button.classList.remove("active")
    # Onboarding-tooltip coverage (planning/TODO.md, origin A14): this
    # toggle isn't in DRIFT_TUTORIAL_STEPS at all, so it's covered by
    # neither the one-time walkthrough nor the auto-generated How to Play
    # read-through (shared/tutorial.js builds that page from the same
    # steps array). The label alone ("Accelerated Severity: ON/OFF") never
    # says what it actually changes, so a returning player has nowhere to
    # find out. A `title` states the real effect directly from the same
    # constant the game logic uses.
    accelerated_button.title = (
        f"Optional difficulty variant: multiplies background displacement-pressure "
        f"severity growth by {ACCELERATED_SEVERITY_MULTIPLIER:.0f}x. Only affects how fast "
        f"arrival pressure rises — never your capacity or funds math directly."
    )
    render_skins()
    render_round_tools()
    render_civic_tools()
    render_ledger()
    render_collection_summary()
    document.title = tab_title()


def on_advance_round(event=None):
    global rewind_snapshot, round_start_snapshot, round_tools_message, collection_note
    round_tools_message = ""
    collection_note = ""
    _reset_civic_notes()
    _sync_spillover()
    rewind_snapshot = _take_full_snapshot()  # GI-18: the state just before this advance
    completed_round = region.round_number
    marks_before = _round_marks()
    region.advance_round()
    if neighbor is not None:
        neighbor.advance_round()
    round_start_snapshot = _take_round_start_snapshot()  # I-15: the new round's starting point
    _collect_after_round(completed_round)
    render()
    announce(round_announcement_text(marks_before))
    _check_new_achievements_for_toast()


def render_second_wave():
    element = document.getElementById("second-wave-display")
    if element is None:
        return
    text = region.second_wave_message()
    element.innerText = text
    element.hidden = text == ""


def render_policies():
    for policy, spec in POLICIES.items():
        level = region.policy_level[policy]
        document.getElementById(f"policy-{policy.replace('_', '-')}-name").innerText = (
            f"{spec['icon']} {spec['label']} ({level}/{POLICY_MAX_LEVEL})"
        )
        button = document.getElementById(f"policy-{policy.replace('_', '-')}-button")
        if level >= POLICY_MAX_LEVEL:
            button.innerText = "Maxed"
            button.disabled = True
        else:
            button.innerText = f"Fund ({region.policy_cost(policy):.0f})"
            button.disabled = region.funds < region.policy_cost(policy)


def neighbor_message():
    if neighbor is None:
        return (
            "A neighbouring district has plenty of housing but no integration services, little money and a "
            "higher background pressure. Open it to run both regions side by side."
        )
    text = (
        f"Neighbouring district, round {neighbor.round_number}: funds {neighbor.funds:.0f}, "
        f"capacity {neighbor.total_capacity():.0f}, strain {neighbor.strain_fraction() * 100:.0f}% "
        f"({neighbor.strain_level()}), integrated {neighbor.integrated_population:.0f} of "
        f"{neighbor.total_arrivals:.0f} arrivals, wellbeing {neighbor.wellbeing_score():.0f}."
    )
    if neighbor_spillover():
        text += (
            f" Its strain is critical, so {NEIGHBOR_SPILLOVER_ARRIVALS:.0f} extra people a round are "
            "reaching your region."
        )
    if neighbor_support_sent:
        text += f" You have sent it {neighbor_support_sent:.0f} funds so far."
    return text


def render_neighbor():
    panel = document.getElementById("neighbor-panel")
    available = neighbor_available()
    panel.hidden = not available
    if not available:
        return
    document.getElementById("neighbor-display").innerText = neighbor_message()
    open_button = document.getElementById("neighbor-open-button")
    open_button.hidden = neighbor is not None
    for capacity_type in CAPACITY_TYPES:
        button = document.getElementById(f"neighbor-{capacity_type}-button")
        button.hidden = neighbor is None
        button.innerText = f"{CAPACITY_LABEL[capacity_type]} ({INVEST_COST[capacity_type]:.0f})"
        button.disabled = neighbor is None or neighbor.funds < INVEST_COST[capacity_type]
    support_button = document.getElementById("neighbor-support-button")
    support_button.hidden = neighbor is None
    support_button.innerText = f"Send support ({NEIGHBOR_SUPPORT_AMOUNT:.0f})"
    support_button.disabled = not main_region_well_prepared()


def on_open_neighbor(event=None):
    if open_neighbor():
        announce("Neighbouring district opened. It runs beside your region every round")
    render()


def on_support_neighbor(event=None):
    if support_neighbor():
        announce(f"Sent {NEIGHBOR_SUPPORT_AMOUNT:.0f} funds to the neighbouring district. Funds {region.funds:.0f}")
    else:
        announce("Cannot send support: your region must be calm and keep a cushion of funds first")
    render()


def _make_neighbor_invest_handler(capacity_type):
    def handler(event=None):
        if invest_neighbor(capacity_type):
            announce(
                f"Neighbouring district invested in {CAPACITY_LABEL[capacity_type]}. "
                f"Its funds are {neighbor.funds:.0f}"
            )
        else:
            announce(f"The neighbouring district cannot afford {CAPACITY_LABEL[capacity_type]}")
        render()
    return handler


def _make_policy_handler(policy):
    def handler(event=None):
        label = POLICIES[policy]["label"]
        if region.invest_policy(policy):
            announce(
                f"Funded {label}, level {region.policy_level[policy]} of {POLICY_MAX_LEVEL}. Funds {region.funds:.0f}"
            )
        elif region.policy_level[policy] >= POLICY_MAX_LEVEL:
            announce(f"{label} is already at its top level")
        else:
            announce(f"Cannot fund {label}: it costs {region.policy_cost(policy):.0f} and you have {region.funds:.0f}")
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_invest_handler(capacity_type):
    def handler(event=None):
        label = CAPACITY_LABEL[capacity_type]
        count_before = region_visual_building_count(region.total_capacity())
        if region.invest(capacity_type):
            _pop_building(count_before)
            announce(
                f"Invested in {label}: now {region.capacity[capacity_type]:.0f}. "
                f"Total capacity {region.total_capacity():.0f}. Funds {region.funds:.0f}. "
                f"Strain {region.strain_fraction() * 100:.0f}% ({region.strain_level()})"
            )
        else:
            announce(
                f"Cannot invest in {label}: it costs {INVEST_COST[capacity_type]:.0f} and you have {region.funds:.0f}"
            )
        render()
        _check_new_achievements_for_toast()
    return handler


def on_toggle_coda(event=None):
    global coda_visible
    coda_visible = not coda_visible
    if coda_visible:
        region.coda_ever_viewed = True
    render()
    _check_new_achievements_for_toast()


# I13: opt-in accelerated-severity difficulty toggle -- a settings-style
# flip, same as on_toggle_info_page/on_toggle_achievements, not a player
# action achievements can key off of, so no toast check here.
def on_toggle_accelerated_severity(event=None):
    region.accelerated_severity_enabled = not region.accelerated_severity_enabled
    # I20: capture the dot-density baseline the very first time the toggle
    # is ever switched on, so a later render can tell whether the stream's
    # density has genuinely moved since then. Never re-captured on a later
    # toggle -- the callout is a one-time "here's the effect" moment, not a
    # per-toggle reminder.
    if (
        region.accelerated_severity_enabled
        and region.severity_toggle_dot_baseline is None
        and not region.severity_density_callout_shown
    ):
        region.severity_toggle_dot_baseline = arrival_stream_dot_count(
            region.arrivals_this_round()
        )
    render()


def on_toggle_crisis_start(event=None):
    global round_start_snapshot
    region.set_crisis_start(not region.crisis_start_enabled)
    round_start_snapshot = _take_round_start_snapshot()  # the new starting funds are the round's start
    render()


def on_reallocate(event=None):
    from_type = getattr(document.getElementById("realloc-from"), "value", "housing")
    to_type = getattr(document.getElementById("realloc-to"), "value", "services")
    if region.reallocate(from_type, to_type):
        announce(
            f"Moved {REALLOCATION_UNITS:.0f} capacity from {CAPACITY_LABEL[from_type]} to {CAPACITY_LABEL[to_type]}. "
            f"Cost {REALLOCATION_FUNDS_COST:.0f} funds. Funds {region.funds:.0f}"
        )
    elif from_type == to_type:
        announce("Choose two different capacity types to move capacity between")
    elif region.capacity.get(from_type, 0) < REALLOCATION_UNITS:
        announce(f"Cannot move capacity: {CAPACITY_LABEL.get(from_type, from_type)} has less than {REALLOCATION_UNITS:.0f}")
    else:
        announce(f"Cannot move capacity: it costs {REALLOCATION_FUNDS_COST:.0f} funds and you have {region.funds:.0f}")
    render()


def on_region_name_input(event=None):
    raw = getattr(document.getElementById("region-name-input"), "value", "") or ""
    region.region_name = str(raw).strip()[:REGION_NAME_MAX_LENGTH]
    render()


def _make_legacy_handler(choice):
    def handler(event=None):
        region.coda_legacy_choice = choice
        render()
    return handler


# --- Save system (SAVE-BUTTON-INTEGRATION.md contract for the shared
# shared/save-widget.js) ---
# get_state() packages every module-level mutable global into one plain,
# JSON-safe dict; load_state() is its exact inverse. `region` is a
# RegionState instance rather than a plain dict, so its attributes are
# unpacked/restored by hand. `capacity`, `arrivals_log`, and `strain_log`
# are deep-copied on the way out (and back in) so a live reference isn't
# leaked into the saved snapshot -- continued play after taking a
# "snapshot" would otherwise silently mutate it, same reasoning as SOL's
# serialize_state() docstring. `net_positive_round` (Iteration Pass 3's
# turning-point milestone) is either `None` or an int, already JSON-safe.
#
# `capacity`'s key set (housing/services/infrastructure) belongs to
# CAPACITY_TYPES in this file, not to the save -- it's restored key-by-key
# into the live dict rather than wholesale-replaced, so a save missing one
# of those keys (an older save format from before a capacity type existed,
# or a hand-edited/corrupted payload) can't wipe that type out of the live
# dict entirely. total_capacity() and render() both do
# `region.capacity[t]` for every `t in CAPACITY_TYPES` unconditionally, so
# a missing key there would crash the very next render -- same bug shape
# as SOL's planet_state and Continuum's resources/allocation/buildings.
#
# Every other field below is restored via `.get(key, <current live
# value>)` rather than bare `data[key]` indexing, for the same reason:
# a save written before a field existed (e.g. one from before Iteration
# Pass 3 added cumulative_services_investment/
# cumulative_integration_contribution/net_positive_round, or before the
# info-page feature added info_page_open) must not KeyError outright --
# it should fall back to whatever the live region already has, same
# graceful-degradation contract as capacity's per-key merge above. This
# mirrors the exact fix Tide's load_state() needed for the identical bug
# shape (see BCM114-DEV-LOG.md 2026-09-02).
def _neighbor_state_fields():
    """I1/I7: the neighbouring region, written only once it has been opened."""
    if neighbor is None:
        return {}
    return {"neighbor": {
        "round_number": neighbor.round_number,
        "funds": neighbor.funds,
        "capacity": dict(neighbor.capacity),
        "background_severity": neighbor.background_severity,
        "total_arrivals": neighbor.total_arrivals,
        "integrated_population": neighbor.integrated_population,
        "strain_sum": neighbor._strain_sum,
        "strain_count": neighbor._strain_count,
        "cumulative_services_investment": neighbor.cumulative_services_investment,
        "cumulative_integration_contribution": neighbor.cumulative_integration_contribution,
        "support_sent": neighbor_support_sent,
    }}


def _finite_number(value, default, low=0.0):
    """A finite non-bool number >= low, else default."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    if value != value or value in (float("inf"), float("-inf")):
        return default
    return max(low, float(value))


def _load_roi_log(saved):
    """I-12: a list of finite non-negative numbers (anything else is dropped), at most DRIFT_LOG_MAX_ENTRIES."""
    if not isinstance(saved, list):
        return []
    values = [_finite_number(v, None) for v in saved]
    return [round(v, 3) for v in values if v is not None and v <= 1e6][-DRIFT_LOG_MAX_ENTRIES:]


def _load_neighbor(saved):
    global neighbor, neighbor_support_sent
    if not isinstance(saved, dict):
        neighbor = None
        neighbor_support_sent = 0.0
        return
    other = _new_neighbor_region()
    other.round_number = int(_finite_number(saved.get("round_number"), 1, 1))
    other.funds = _finite_number(saved.get("funds"), other.funds)
    saved_capacity = saved.get("capacity")
    if isinstance(saved_capacity, dict):
        for capacity_type in CAPACITY_TYPES:
            other.capacity[capacity_type] = _finite_number(saved_capacity.get(capacity_type), other.capacity[capacity_type])
    other.background_severity = _finite_number(saved.get("background_severity"), other.background_severity)
    other.total_arrivals = _finite_number(saved.get("total_arrivals"), other.total_arrivals)
    other.integrated_population = min(other.total_arrivals, _finite_number(saved.get("integrated_population"), 0.0))
    other._strain_count = int(_finite_number(saved.get("strain_count"), 0))
    other._strain_sum = min(float(other._strain_count), _finite_number(saved.get("strain_sum"), 0.0))
    other.cumulative_services_investment = _finite_number(saved.get("cumulative_services_investment"), 0.0)
    other.cumulative_integration_contribution = _finite_number(saved.get("cumulative_integration_contribution"), 0.0)
    neighbor = other
    neighbor_support_sent = _finite_number(saved.get("support_sent"), 0.0)


def _ledger_state_fields():
    """I-8, GI-18, GI-15/22: written only once there is something to write, so a
    fresh region's save is unchanged. Ledger rows ride as plain lists in
    LEDGER_FIELDS order to keep the payload small."""
    out = {}
    if any(region.spend_by_type.values()):
        out["spend_by_type"] = dict(region.spend_by_type)
    if any(region.round_spend.values()):
        out["round_spend"] = dict(region.round_spend)
    if region.ledger:
        out["ledger"] = [[row[name] for name in LEDGER_FIELDS] for row in region.ledger]
    if region.rewind_used_round is not None:
        out["rewind_used_round"] = region.rewind_used_round
    if collection["titles"] or collection["civic"]:
        out["collection"] = copy.deepcopy(collection)
    if region.best_perfect_fit_streak > 0:
        out["perfect_fit"] = {"streak": region.perfect_fit_streak, "best": region.best_perfect_fit_streak}
    if region.calendar_enabled or region.braced_rounds or region.calendar_log:
        out["calendar"] = {
            "enabled": region.calendar_enabled,
            "braced": list(region.braced_rounds),
            "log": [dict(entry) for entry in region.calendar_log],
        }
    if region.council_picks:
        out["council"] = list(region.council_picks)
    if region.autopilot != AUTOPILOT_DEFAULT_RULES:
        out["autopilot"] = dict(region.autopilot)
    if region.stars_banked is not None:
        out["stars_banked"] = region.stars_banked
    return out


def _load_spend_dict(saved):
    out = {key: 0.0 for key in SPEND_KEYS}
    if isinstance(saved, dict):
        for key in SPEND_KEYS:
            out[key] = _finite_number(saved.get(key), 0.0)
    return out


def _load_ledger(saved):
    rows = []
    if not isinstance(saved, list):
        return rows
    for entry in saved:
        if not isinstance(entry, list) or len(entry) != len(LEDGER_FIELDS):
            continue
        row = {}
        ok = True
        for name, value in zip(LEDGER_FIELDS, entry):
            if name == "auto":
                row[name] = bool(value) if isinstance(value, bool) else False
            elif name == "round":
                if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                    ok = False
                    break
                row[name] = value
            else:
                number = _finite_number(value, None)
                if number is None:
                    ok = False
                    break
                row[name] = number
        if ok:
            rows.append(row)
    return rows[-LEDGER_MAX_ENTRIES:]


def _small_int(value, low=0):
    return isinstance(value, int) and not isinstance(value, bool) and value >= low


def _load_civic_state(data):
    """GI-13 / GI-2 / GI-1 / GI-5 / GI-21: every field optional and validated; bad values reset to the default."""
    fit = data.get("perfect_fit")
    region.perfect_fit_streak = 0
    region.best_perfect_fit_streak = 0
    if isinstance(fit, dict) and _small_int(fit.get("best")) and _small_int(fit.get("streak")):
        region.best_perfect_fit_streak = fit["best"]
        region.perfect_fit_streak = min(fit["streak"], fit["best"])
    region.calendar_enabled = False
    region.braced_rounds = []
    region.calendar_log = []
    cal = data.get("calendar")
    if isinstance(cal, dict):
        region.calendar_enabled = cal.get("enabled") is True
        braced = cal.get("braced")
        if isinstance(braced, list):
            region.braced_rounds = sorted({r for r in braced if _small_int(r, 1) and calendar_event_for_round(r) is not None})
        log = cal.get("log")
        if isinstance(log, list):
            for entry in log:
                if (
                    isinstance(entry, dict) and _small_int(entry.get("round"), 1)
                    and entry.get("kind") in CALENDAR_KINDS and isinstance(entry.get("braced"), bool)
                    and (entry.get("held") is None or isinstance(entry.get("held"), bool))
                ):
                    region.calendar_log.append(
                        {"round": entry["round"], "kind": entry["kind"], "braced": entry["braced"], "held": entry["held"]}
                    )
            region.calendar_log = region.calendar_log[-CALENDAR_LOG_MAX:]
    region.council_picks = []
    picks = data.get("council")
    if isinstance(picks, list):
        for pid in picks:
            program = COUNCIL_BY_ID.get(pid) if isinstance(pid, str) else None
            # a pick is only valid if it is the next tier of its branch, so a hand-edited save cannot skip tiers
            if program is not None and council_next_program(program["branch"], region.council_picks) is program:
                region.council_picks.append(pid)
    region.autopilot = _clean_autopilot(data.get("autopilot"))
    banked = data.get("stars_banked")
    region.stars_banked = banked if _small_int(banked, 1) else None


def get_state():
    return {
        "round_number": region.round_number,
        "funds": region.funds,
        "capacity": copy.deepcopy(region.capacity),
        "background_severity": region.background_severity,
        "total_arrivals": region.total_arrivals,
        "arrivals_log": copy.deepcopy(region.arrivals_log),
        "strain_log": copy.deepcopy(region.strain_log),
        # Z25: strain_log's decoupled running consumers -- see
        # RegionState.__init__'s comment and load_state()'s recompute
        # fallback for an old save that predates these three fields.
        "strain_sum": region._strain_sum,
        "strain_count": region._strain_count,
        "ever_critical_strain": region._ever_critical_strain,
        "wellbeing_log": copy.deepcopy(region.wellbeing_log),
        "integrated_population": region.integrated_population,
        "cumulative_services_investment": region.cumulative_services_investment,
        "cumulative_integration_contribution": region.cumulative_integration_contribution,
        "net_positive_round": region.net_positive_round,
        "current_stable_streak": region.current_stable_streak,
        "best_stable_streak": region.best_stable_streak,
        "thriving_round": region.thriving_round,
        "coda_ever_viewed": region.coda_ever_viewed,
        "last_milestone_round": region.last_milestone_round,
        "last_milestone_snapshot": copy.deepcopy(region.last_milestone_snapshot),
        "accelerated_severity_enabled": region.accelerated_severity_enabled,
        "severity_toggle_dot_baseline": region.severity_toggle_dot_baseline,
        "severity_density_callout_shown": region.severity_density_callout_shown,
        "subscore_log": copy.deepcopy(region.subscore_log),
        "region_name": region.region_name,
        "coda_legacy_choice": region.coda_legacy_choice,
        "crisis_start_enabled": region.crisis_start_enabled,
        **({"policy_level": dict(region.policy_level)} if any(region.policy_level.values()) else {}),
        **({"learning_active": True} if region.learning_active else {}),
        **(
            {"second_wave": {
                "status": region.second_wave_status, "rounds_left": region.second_wave_rounds_left,
                "peak_strain": region.second_wave_peak_strain, "result": region.second_wave_result,
                **({"start_round": region.second_wave_start_round} if region.second_wave_start_round is not None else {}),
            }}
            if region.second_wave_status is not None else {}
        ),
        **({"roi_log": list(region.roi_log)} if region.roi_log else {}),
        **_neighbor_state_fields(),
        **_ledger_state_fields(),
        "coda_visible": coda_visible,
        "info_page_open": info_page_open,
        # I17: a write-only number for the community capacity index; never read back.
        "wellbeing_score": region.wellbeing_score(),
        # Write-only projection (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) — always
        # freshly recomputed, never read back in load_state() below.
        "summary": steward_summary(),  # B-23: write-only, never read back
        "achievements_earned": achievement_ids_earned(),
    }


# B-23: a few honest, already-computed numbers for the hub's Climate Steward page. Written into the save as a
# read-only `summary` list ({label, value, unit, note?}); never read back by load_state().
def steward_summary():
    return [
        {"label": "Newcomers integrated", "value": round(region.integration_fraction() * 100), "unit": "%"},
        {"label": "Wellbeing score", "value": round(region.wellbeing_score()), "unit": "of 100"},
        {"label": "Rounds played", "value": max(0, int(region.round_number) - 1), "unit": ""},
    ]


def load_state(data):
    global coda_visible, info_page_open

    if not isinstance(data, dict):
        return False

    region.round_number = data.get("round_number", region.round_number)
    region.funds = data.get("funds", region.funds)
    saved_capacity = data.get("capacity")
    if isinstance(saved_capacity, dict):
        for capacity_type in CAPACITY_TYPES:
            if capacity_type in saved_capacity:
                region.capacity[capacity_type] = copy.deepcopy(saved_capacity[capacity_type])
    region.background_severity = data.get("background_severity", region.background_severity)
    region.total_arrivals = data.get("total_arrivals", region.total_arrivals)
    saved_arrivals_log = data.get("arrivals_log")
    if isinstance(saved_arrivals_log, list):
        region.arrivals_log = copy.deepcopy(saved_arrivals_log)
    saved_strain_log = data.get("strain_log")
    if isinstance(saved_strain_log, list):
        region.strain_log = copy.deepcopy(saved_strain_log)
    # Z25: _strain_sum/_strain_count/_ever_critical_strain ride the save
    # from here on; an old save from before this refactor won't have
    # them, so recompute all three from whatever strain_log that old
    # save still has (its full, not-yet-capped history) rather than
    # defaulting to 0/False and silently losing the correct lifetime
    # average / achievement-earned state.
    if "strain_sum" in data and "strain_count" in data:
        region._strain_sum = data.get("strain_sum", region._strain_sum)
        region._strain_count = data.get("strain_count", region._strain_count)
    else:
        region._strain_sum = sum(region.strain_log)
        region._strain_count = len(region.strain_log)
    if "ever_critical_strain" in data:
        region._ever_critical_strain = bool(
            data.get("ever_critical_strain", region._ever_critical_strain)
        )
    else:
        region._ever_critical_strain = any(
            s >= STRAIN_LEVEL_THRESHOLDS[2][0] for s in region.strain_log
        )
    saved_wellbeing_log = data.get("wellbeing_log")
    if isinstance(saved_wellbeing_log, list):
        region.wellbeing_log = copy.deepcopy(saved_wellbeing_log)
    region.integrated_population = data.get("integrated_population", region.integrated_population)
    region.cumulative_services_investment = data.get(
        "cumulative_services_investment", region.cumulative_services_investment
    )
    region.cumulative_integration_contribution = data.get(
        "cumulative_integration_contribution", region.cumulative_integration_contribution
    )
    region.net_positive_round = data.get("net_positive_round", region.net_positive_round)
    region.current_stable_streak = data.get("current_stable_streak", region.current_stable_streak)
    region.best_stable_streak = data.get("best_stable_streak", region.best_stable_streak)
    region.thriving_round = data.get("thriving_round", region.thriving_round)
    region.coda_ever_viewed = data.get("coda_ever_viewed", region.coda_ever_viewed)
    region.last_milestone_round = data.get("last_milestone_round", region.last_milestone_round)
    saved_milestone_snapshot = data.get("last_milestone_snapshot")
    if isinstance(saved_milestone_snapshot, dict):
        region.last_milestone_snapshot = copy.deepcopy(saved_milestone_snapshot)
    region.accelerated_severity_enabled = data.get(
        "accelerated_severity_enabled", region.accelerated_severity_enabled
    )
    saved_dot_baseline = data.get("severity_toggle_dot_baseline")
    if isinstance(saved_dot_baseline, int) and not isinstance(saved_dot_baseline, bool):
        region.severity_toggle_dot_baseline = saved_dot_baseline
    region.severity_density_callout_shown = bool(
        data.get("severity_density_callout_shown", region.severity_density_callout_shown)
    )
    saved_subscores = data.get("subscore_log")
    if isinstance(saved_subscores, list):
        region.subscore_log = [e for e in copy.deepcopy(saved_subscores) if isinstance(e, dict)]
    saved_name = data.get("region_name")
    if isinstance(saved_name, str):
        region.region_name = saved_name.strip()[:REGION_NAME_MAX_LENGTH]
    saved_choice = data.get("coda_legacy_choice")
    if saved_choice in CODA_LEGACY_CHOICES or saved_choice is None:
        region.coda_legacy_choice = saved_choice
    region.crisis_start_enabled = bool(data.get("crisis_start_enabled", region.crisis_start_enabled))
    # I29: a loaded region keeps whatever it began with; a save without the key began without it.
    region.learning_active = data.get("learning_active") is True
    region.second_wave_status = None
    region.second_wave_rounds_left = 0
    region.second_wave_peak_strain = 0.0
    region.second_wave_result = None
    region.second_wave_start_round = None
    saved_wave = data.get("second_wave")
    if isinstance(saved_wave, dict):
        status = saved_wave.get("status")
        left = saved_wave.get("rounds_left")
        peak = saved_wave.get("peak_strain")
        result = saved_wave.get("result")
        if status in ("warned", "active", "done"):
            region.second_wave_status = status
            if isinstance(left, int) and not isinstance(left, bool) and 0 <= left <= SECOND_WAVE_ROUNDS:
                region.second_wave_rounds_left = left
            elif status == "active":
                region.second_wave_rounds_left = SECOND_WAVE_ROUNDS
            if isinstance(peak, (int, float)) and not isinstance(peak, bool) and peak == peak and 0.0 <= peak <= 1.0:
                region.second_wave_peak_strain = float(peak)
            if status == "done":
                region.second_wave_result = result if result in ("held", "strained") else "strained"
            start_round = saved_wave.get("start_round")
            if _small_int(start_round, 1):
                region.second_wave_start_round = start_round
    region.roi_log = _load_roi_log(data.get("roi_log"))
    region.policy_level = {p: 0 for p in POLICIES}
    saved_policies = data.get("policy_level")
    if isinstance(saved_policies, dict):
        for p in POLICIES:
            level = saved_policies.get(p)
            if isinstance(level, int) and not isinstance(level, bool) and 0 <= level <= POLICY_MAX_LEVEL:
                region.policy_level[p] = level
    _load_neighbor(data.get("neighbor"))
    region.spend_by_type = _load_spend_dict(data.get("spend_by_type"))
    region.round_spend = _load_spend_dict(data.get("round_spend"))
    region.ledger = _load_ledger(data.get("ledger"))
    used_round = data.get("rewind_used_round")
    region.rewind_used_round = (
        used_round if isinstance(used_round, int) and not isinstance(used_round, bool) and used_round >= 1 else None
    )
    merge_collection(data.get("collection"))
    _load_civic_state(data)
    autopilot_log.clear()
    _reset_civic_notes()
    _reset_undo_state()
    name_input = document.getElementById("region-name-input")
    name_input.value = region.region_name
    coda_visible = data.get("coda_visible", coda_visible)
    info_page_open = data.get("info_page_open", info_page_open)
    # "achievements_earned" is intentionally never read back here — see
    # get_state()'s comment and ACHIEVEMENTS-SYSTEM-DESIGN.md §1.

    render()
    _seed_achievement_toast_baseline()
    return True


def setup():
    # index.html already marks this hidden via the `hidden` attribute, but
    # that markup default doesn't exist for the pytest fake-DOM harness (a
    # FakeElement starts with hidden=False) -- setting it explicitly here
    # keeps both environments consistent and costs nothing in a real
    # browser, where it's already true.
    document.getElementById("achievement-toast").hidden = True
    document.getElementById("advance-round-button").addEventListener(
        "click", create_proxy(on_advance_round)
    )
    for capacity_type in CAPACITY_TYPES:
        document.getElementById(f"{capacity_type}-invest-button").addEventListener(
            "click", create_proxy(_make_invest_handler(capacity_type))
        )
    for policy in POLICIES:
        document.getElementById(f"policy-{policy.replace('_', '-')}-button").addEventListener(
            "click", create_proxy(_make_policy_handler(policy))
        )
    document.getElementById("coda-button").addEventListener(
        "click", create_proxy(on_toggle_coda)
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
    document.getElementById("accelerated-severity-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_accelerated_severity)
    )
    document.getElementById("crisis-start-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_crisis_start)
    )
    document.getElementById("realloc-button").addEventListener("click", create_proxy(on_reallocate))
    document.getElementById("neighbor-open-button").addEventListener("click", create_proxy(on_open_neighbor))
    document.getElementById("neighbor-support-button").addEventListener("click", create_proxy(on_support_neighbor))
    for capacity_type in CAPACITY_TYPES:
        document.getElementById(f"neighbor-{capacity_type}-button").addEventListener(
            "click", create_proxy(_make_neighbor_invest_handler(capacity_type))
        )
    document.getElementById("region-name-input").addEventListener(
        "change", create_proxy(on_region_name_input)
    )
    for legacy_choice in CODA_LEGACY_CHOICES:
        document.getElementById(f"coda-legacy-{legacy_choice}-button").addEventListener(
            "click", create_proxy(_make_legacy_handler(legacy_choice))
        )
    for button_id, handler in (
        ("reset-round-button", on_reset_round),
        ("rewind-button", on_rewind),
        ("play-rounds-button", on_play_rounds),
        ("ledger-toggle-button", on_toggle_ledger),
        ("collection-toggle-button", on_toggle_collection),
        ("copy-ledger-csv-button", on_copy_ledger_csv),
        ("calendar-toggle-button", on_toggle_calendar),
        ("calendar-brace-button", on_brace),
        ("autopilot-run-button", on_autopilot_run),
        ("copy-summary-button", on_copy_summary),
    ):
        document.getElementById(button_id).addEventListener("click", create_proxy(handler))
    for branch in COUNCIL_BRANCHES:
        document.getElementById(f"council-pick-{branch}").addEventListener(
            "click", create_proxy(_make_council_handler(branch))
        )
    for select_id in (
        "autopilot-share-select", "autopilot-surplus-select", "autopilot-reserve-select", "autopilot-rounds-select",
    ):
        document.getElementById(select_id).addEventListener("change", create_proxy(on_autopilot_change))
    for skin in SKINS:
        document.getElementById(f"skin-{skin['id']}-button").addEventListener(
            "click", create_proxy(_make_skin_handler(skin["id"]))
        )
    for range_key in TREND_RANGES:
        document.getElementById(f"trend-range-{range_key}-button").addEventListener(
            "click", create_proxy(_make_trend_range_handler(range_key))
        )
    for layer_key in TREND_LAYER_ORDER:
        document.getElementById(f"trend-layer-{layer_key}-button").addEventListener(
            "click", create_proxy(_make_trend_layer_handler(layer_key))
        )
    document.getElementById("summary-copy-area").hidden = True
    document.getElementById("ledger-sort-select").addEventListener("change", create_proxy(on_ledger_sort))
    document.getElementById("ledger-filter-select").addEventListener("change", create_proxy(on_ledger_filter))
    document.getElementById("ledger-copy-area").hidden = True
    _reset_undo_state()
    update_changelog_display()
    render()
    _seed_achievement_toast_baseline()


setup()
