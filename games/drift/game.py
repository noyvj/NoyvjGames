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


class RegionState:
    def __init__(self):
        self.round_number = 1
        self.funds = STARTING_FUNDS
        self.capacity = {t: 0.0 for t in CAPACITY_TYPES}
        self.background_severity = 0.0
        self.total_arrivals = 0.0
        self.arrivals_log = []
        self.strain_log = []
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
        # I15 -- a transient one-time flag, set in advance_round() the
        # round has_long_horizon_story() first flips from False to True,
        # consumed and reset by render() the next time it draws --
        # same pattern as Thaw's just_started_melting. Not part of the
        # save contract: it only ever needs to live long enough for one
        # render() call to see it.
        self.coda_just_became_available = False

    def total_capacity(self):
        return sum(self.capacity[t] for t in CAPACITY_TYPES)

    def invest(self, capacity_type):
        cost = INVEST_COST[capacity_type]
        if self.funds < cost:
            return False
        self.funds -= cost
        self.capacity[capacity_type] += CAPACITY_PER_INVESTMENT[capacity_type]
        if capacity_type == "services":
            self.cumulative_services_investment += cost
        return True

    def arrivals_this_round(self):
        """People arriving this round, rising with background severity —
        loosely tied to it, not a hard function the player can reverse-
        engineer to zero, but predictable enough to plan capacity around."""
        return BASE_ARRIVALS_PER_ROUND + self.background_severity * ARRIVALS_PER_SEVERITY_POINT

    def strain_fraction(self):
        """0..1 — the share of the region's arrived population that
        current capacity fails to cover. Zero while capacity keeps pace
        with arrivals; rises toward (but never reaches) 1 as arrivals
        outrun capacity."""
        if self.total_arrivals <= 0:
            return 0.0
        shortfall = max(0.0, self.total_arrivals - self.total_capacity())
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
        throughput = self.capacity["services"] * INTEGRATION_RATE_PER_SERVICES_UNIT
        return min(self.pending_population(), throughput)

    def integration_contribution(self):
        """Funds integrated people contribute back each round — the
        net-positive core of the hope angle: integration isn't a
        permanent drain, it eventually pays for the services investment
        that enabled it and keeps paying after that."""
        return self.integrated_population * INTEGRATION_CONTRIBUTION_PER_PERSON

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
        crisis, mirroring Grid's average_clean_fraction."""
        if not self.strain_log:
            return 0.0
        return sum(self.strain_log) / len(self.strain_log)

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

    def advance_round(self):
        completed_round = self.round_number
        strain = self.strain_fraction()
        self.strain_log.append(strain)

        # Achievements: "stable" streak tracking, same band strain_level()
        # itself uses (below STRAIN_LEVEL_THRESHOLDS[1][0]) so this always
        # agrees with what the strain display already calls "stable".
        if strain < STRAIN_LEVEL_THRESHOLDS[1][0]:
            self.current_stable_streak += 1
        else:
            self.current_stable_streak = 0
        self.best_stable_streak = max(self.best_stable_streak, self.current_stable_streak)

        contribution = self.integration_contribution()
        income = BASE_REGIONAL_INCOME_PER_ROUND * (1 - strain)
        income += contribution
        self.cumulative_integration_contribution += contribution

        # I15: detect the exact round the long-horizon coda first becomes
        # available, before integrated_population actually changes below.
        coda_was_available = self.has_long_horizon_story()
        self.integrated_population += self.integration_this_round()
        if not coda_was_available and self.has_long_horizon_story():
            self.coda_just_became_available = True

        arrivals = self.arrivals_this_round()
        self.total_arrivals += arrivals
        self.arrivals_log.append(arrivals)
        severity_rise = BACKGROUND_SEVERITY_RISE_PER_ROUND
        if self.accelerated_severity_enabled:
            severity_rise *= ACCELERATED_SEVERITY_MULTIPLIER
        self.background_severity += severity_rise
        self.funds += income
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

        # I1: logged last, once every other round-end value is final.
        self.wellbeing_log.append(self.wellbeing_score())


region = RegionState()
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


def trend_graph_svg(strain_history, wellbeing_history):
    """Two-line trend graph: strain (0-100%, rising is worse) vs.
    composite wellbeing (0-100, rising is better) — both already on a
    0-100 scale, so they're normalized against that fixed range rather
    than each other's min/max, keeping round-to-round shape meaningful
    rather than always stretched to fill the graph."""
    if len(strain_history) < 2:
        return ""

    n = len(strain_history)
    xs = [i * (TREND_GRAPH_WIDTH / (n - 1)) for i in range(n)]
    strain_pct = [s * 100 for s in strain_history]
    strain_ys = _normalize_series(strain_pct, TREND_GRAPH_HEIGHT, 0, 100)
    wellbeing_ys = _normalize_series(wellbeing_history, TREND_GRAPH_HEIGHT, 0, 100)

    strain_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, strain_ys))
    wellbeing_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, wellbeing_ys))

    def _markers(ys, values, css_class, label):
        return "".join(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" class="trend-point {css_class}">'
            f"<title>Round {i + 1} -- {label}: {v:.0f}</title>"
            f"</circle>"
            for i, (x, y, v) in enumerate(zip(xs, ys, values))
        )

    markers = _markers(strain_ys, strain_pct, "trend-point--strain", "Strain") + _markers(
        wellbeing_ys, wellbeing_history, "trend-point--wellbeing", "Wellbeing"
    )

    return (
        f'<svg viewBox="0 0 {TREND_GRAPH_WIDTH} {TREND_GRAPH_HEIGHT}" class="trend-graph-svg">'
        f'<polyline points="{strain_points}" class="trend-line trend-line--strain" />'
        f'<polyline points="{wellbeing_points}" class="trend-line trend-line--wellbeing" />'
        f"{markers}"
        f"</svg>"
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


def long_horizon_coda_message(region_state):
    return (
        f"Generations from now, the descendants of the {region_state.integrated_population:.0f} "
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
    critical_threshold = STRAIN_LEVEL_THRESHOLDS[2][0]
    return any(s >= critical_threshold for s in region.strain_log)


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


def _seed_achievement_toast_baseline():
    global _achievements_seen_ids
    _achievements_seen_ids = set(achievement_ids_earned())


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
    newly = earned_now - _achievements_seen_ids
    if newly:
        by_id = {entry["id"]: entry for entry in ACHIEVEMENTS}
        labels = [by_id[aid]["label"] for aid in newly if aid in by_id]
        if labels:
            if len(labels) == 1:
                _display_achievement_toast(f"🏆 Achievement unlocked: {labels[0]}")
            else:
                _display_achievement_toast(f"🏆 {len(labels)} achievements unlocked: " + ", ".join(labels))
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
    global personal_best
    score = region.wellbeing_score()
    if score > personal_best["wellbeing_score"]:
        personal_best["wellbeing_score"] = score
        _write_local_storage_item(PERSONAL_BEST_STORAGE_KEY, json.dumps(personal_best))


def render_personal_best():
    element = document.getElementById("personal-best-display")
    if element is None:
        return
    element.innerText = f"Personal best wellbeing: {personal_best['wellbeing_score']:.0f}"


def render():
    render_info_page()
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
        dot_el.style.animationDuration = f"{dot_duration:.2f}s"
    document.getElementById("total-arrivals-display").innerText = (
        f"Total arrivals (lifetime): {region.total_arrivals:.0f} people"
    )
    document.getElementById("strain-display").innerText = (
        f"Strain: {region.strain_fraction() * 100:.0f}% ({region.strain_level()})"
    )
    strain_bar = document.getElementById("strain-bar")
    strain_bar.style.width = f"{region.strain_fraction() * 100:.0f}%"
    strain_bar.className = f"meter-fill meter-fill--strain strain--{region.strain_level()}"
    # I6: one-line consequence description per strain level.
    document.getElementById("strain-consequence-display").innerText = strain_consequence_message(region)

    document.getElementById("integrated-display").innerText = (
        f"Integrated: {region.integrated_population:.0f} people "
        f"(contributing {region.integration_contribution():.0f} funds/round)"
    )
    document.getElementById("pending-display").innerText = (
        f"Pending integration: {region.pending_population():.0f} people"
    )
    turning_point_display = document.getElementById("integration-turning-point-display")
    turning_point_message = integration_turning_point_message(region)
    turning_point_display.hidden = turning_point_message is None
    turning_point_display.innerText = turning_point_message or ""

    # I3: explicit in-play comparison to the Uganda policy model.
    document.getElementById("uganda-comparison-display").innerText = uganda_comparison_message(region)

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
    document.getElementById("wellbeing-message-display").innerText = wellbeing_message(
        region.wellbeing_score()
    )

    # I5: one-time thriving-band callout.
    thriving_display = document.getElementById("thriving-callout-display")
    thriving_message = thriving_callout_message(region)
    thriving_display.hidden = thriving_message is None
    thriving_display.innerText = thriving_message or ""

    document.getElementById("checkpoint-display").innerText = checkpoint_message(region)

    # I2: skyline building count/height tracking real capacity.
    visible_building_count = region_visual_building_count(region.total_capacity())
    building_height_scale = region_visual_height_scale(region.total_capacity())
    for index, building_id in enumerate(REGION_VISUAL_BUILDING_IDS):
        building_el = document.getElementById(f"region-visual-building-{building_id}")
        building_el.hidden = index >= visible_building_count
        building_el.style.transform = f"scaleY({building_height_scale:.2f})"

    # I1: strain/wellbeing trend graph.
    trend_svg = trend_graph_svg(region.strain_log, region.wellbeing_log)
    document.getElementById("trend-graph").innerHTML = trend_svg
    document.getElementById("trend-graph-message").innerText = (
        "" if trend_svg else "Not enough rounds yet to show a trend."
    )

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
        document.getElementById("coda-service-quality-bar").style.width = (
            f"{region.projected_service_quality():.0f}%"
        )
        document.getElementById("coda-economic-health-bar").style.width = (
            f"{region.projected_economic_health():.0f}%"
        )
        document.getElementById("coda-social-cohesion-bar").style.width = (
            f"{region.projected_social_cohesion():.0f}%"
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
        "🔥 Accelerated Severity: ON"
        if region.accelerated_severity_enabled
        else "Accelerated Severity: OFF"
    )
    if region.accelerated_severity_enabled:
        accelerated_button.classList.add("active")
    else:
        accelerated_button.classList.remove("active")


def on_advance_round(event=None):
    region.advance_round()
    render()
    _check_new_achievements_for_toast()


def _make_invest_handler(capacity_type):
    def handler(event=None):
        region.invest(capacity_type)
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
    render()


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
def get_state():
    return {
        "round_number": region.round_number,
        "funds": region.funds,
        "capacity": copy.deepcopy(region.capacity),
        "background_severity": region.background_severity,
        "total_arrivals": region.total_arrivals,
        "arrivals_log": copy.deepcopy(region.arrivals_log),
        "strain_log": copy.deepcopy(region.strain_log),
        "wellbeing_log": copy.deepcopy(region.wellbeing_log),
        "integrated_population": region.integrated_population,
        "cumulative_services_investment": region.cumulative_services_investment,
        "cumulative_integration_contribution": region.cumulative_integration_contribution,
        "net_positive_round": region.net_positive_round,
        "current_stable_streak": region.current_stable_streak,
        "best_stable_streak": region.best_stable_streak,
        "thriving_round": region.thriving_round,
        "coda_ever_viewed": region.coda_ever_viewed,
        "accelerated_severity_enabled": region.accelerated_severity_enabled,
        "coda_visible": coda_visible,
        "info_page_open": info_page_open,
        # Write-only projection (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) — always
        # freshly recomputed, never read back in load_state() below.
        "achievements_earned": achievement_ids_earned(),
    }


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
    region.accelerated_severity_enabled = data.get(
        "accelerated_severity_enabled", region.accelerated_severity_enabled
    )
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
    document.getElementById("coda-button").addEventListener(
        "click", create_proxy(on_toggle_coda)
    )
    document.getElementById("info-page-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_info_page)
    )
    document.getElementById("achievements-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_achievements)
    )
    document.getElementById("accelerated-severity-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_accelerated_severity)
    )
    render()
    _seed_achievement_toast_baseline()


setup()
