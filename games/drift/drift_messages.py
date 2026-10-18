"""The arrival dot stream sizes and the plain-language messages the page shows: wellbeing, Uganda comparison, resettlement benchmark, checkpoint, forecast, ROI, coda, thriving and turning-point lines."""

from js import document

from drift_model_region import RegionState
from drift_rules import (
    ACCELERATED_SEVERITY_MULTIPLIER, ARRIVALS_PER_SEVERITY_POINT, BACKGROUND_SEVERITY_RISE_PER_ROUND,
    BASE_ARRIVALS_PER_ROUND, MODEL_REGION_WELLBEING_SCORE, STRAIN_LEVEL_THRESHOLDS,
    THRIVING_WELLBEING_SCORE, WELLBEING_FUNDS_SCALE,
)


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
