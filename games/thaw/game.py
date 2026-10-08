"""Thaw — Permafrost Feedback Loop Game.

Runs in-browser via Pyodide. Milestone 1: the background trajectory and
core loop — global temperature rises on a fixed schedule each round,
independent of the player, while the player allocates regional resources
across output/preserve/monitor. The permafrost melt + methane feedback
loop (the entire point of this game) lands in Milestone 2.
"""

import json
import math

import info_page
import narrative_log
from js import document, setTimeout
from pyodide.ffi import create_proxy

STARTING_FUNDS = 300.0

CATEGORIES = ["output", "preserve", "monitor"]

CATEGORY_LABEL = {
    "output": "Output",
    "preserve": "Permafrost Preservation",
    "monitor": "Monitoring & Response",
}

CATEGORY_ICON = {
    "output": "\U0001F3ED",  # factory
    "preserve": "\U0001F332",  # evergreen tree
    "monitor": "\U0001F4E1",  # satellite antenna
}

TEMPERATURE_METER_MAX = 30.0

INVEST_COST = {
    "output": 20,
    "preserve": 25,
    "monitor": 20,
}

OUTPUT_INCOME_PER_UNIT = 6

# Global temperature rises this much every round, no matter what the
# player does — it's a background trajectory, not something the player
# directly drives. This is the thing that makes Thaw different from
# Herd/Grid: the player isn't the primary cause of the central meter.
BASE_TEMP_RISE_PER_ROUND = 1.0

# Permafrost melt + methane feedback: once temperature crosses this
# threshold, melt releases methane that ADDS to next round's rise —
# warming causes melt causes more warming. This is the entire lesson of
# the game: a slow, linear problem tipping into a runaway one.
MELT_THRESHOLD = 10.0
FEEDBACK_RATE_PER_DEGREE_OVER = 0.15

# G9: the optional "long game" mode. Chosen once, before any round is
# played, it stretches the whole trajectory: the background rise, the melt
# feedback and the restoration pull-back all run at LONG_GAME_WARMING_SCALE
# of their normal speed, while Output income runs at LONG_GAME_INCOME_SCALE,
# so reaching the same milestones takes roughly two and a half times as many
# rounds. Income is cut by less than warming, so a longer game is also a
# slightly gentler one per degree of warming. Off by default; the flag lives
# in the module (`long_game`, below) because it applies to every region.
LONG_GAME_WARMING_SCALE = 0.4
LONG_GAME_INCOME_SCALE = 0.6

# G3/G10: a second, further warming milestone past the initial melt
# threshold. Crossing +10.0 is "the tipping point" (Pass 1's flash);
# crossing this second, higher milestone while accelerating hard is what
# G3's "critical" visual state calls out, and it's also the milestone G10
# watches to announce the first time intervention has measurably delayed
# reaching it relative to the undampened counterfactual.
SECOND_WARMING_MILESTONE = 15.0
CRITICAL_ACCELERATION_FACTOR = 2.0

# Intervention: preserve/monitor investment dampens the FEEDBACK
# contribution only — never the background BASE_TEMP_RISE_PER_ROUND,
# which stays outside player control by design. "A real lever that
# measurably slows the loop, even if it can't fully stop the background
# trajectory" — the plan's hope-angle requirement, made literal.
DAMPENING_PER_PRESERVE_UNIT = 0.08
DAMPENING_PER_MONITOR_UNIT = 0.04
MAX_FEEDBACK_DAMPENING = 0.85

# G21: the region rescue — a costly, one-time-per-region emergency lever
# available only while that region is in the critical tier. It is a
# temporary dampening boost layered ON TOP of investment dampening (and
# allowed to push past MAX_FEEDBACK_DAMPENING, up to RESCUE_MAX_DAMPENING)
# for a fixed number of rounds, buying a stricken region breathing room
# but never a permanent fix: once it lapses, only real preserve/monitor
# investment keeps the feedback loop in check.
# G15: permafrost restoration. Once a melting region has held the feedback
# loop under RESTORATION_MAX_ACCELERATION on investment alone (a temporary
# rescue boost doesn't count) for RESTORATION_STREAK_ROUNDS rounds in a row,
# every Preservation unit starts pulling melt-driven warming back each
# round, up to RESTORATION_MAX_PER_ROUND. It removes real accumulated
# temperature but never outruns the fixed background rise, so it slows the
# climb rather than reversing it -- "some melt", per the design note.
RESTORATION_MAX_ACCELERATION = 1.3
RESTORATION_STREAK_ROUNDS = 3
RESTORATION_PER_PRESERVE_UNIT = 0.05
RESTORATION_MAX_PER_ROUND = 0.5

# G13: the optional starting policy stance for Region A -- a real-world-
# inspired framing chosen once, before the first round is played, that
# subtly weights the region's starting position. Each stance trades a
# little starting funds against a little permanent baseline dampening;
# none is a clearly best pick. `dampening` counts toward the region's
# feedback dampening exactly like investment does (so it is subject to
# MAX_FEEDBACK_DAMPENING), but never counts as an investment: it doesn't
# earn the "first intervention" achievement or the pre-emptive-investment
# praise. Region B/C already model strategies through their presets, and
# Region D is the deliberately-unmanaged baseline, so only A gets a stance.
POLICY_STANCES = {
    "growth": {
        "label": "Growth-led (stated policies)",
        "blurb": "Bank on the economy first: +100 starting funds, no head start on dampening.",
        "funds": 100.0,
        "dampening": 0.0,
    },
    "balanced": {
        "label": "Balanced (transition pathway)",
        "blurb": "A middle path: +40 starting funds and a 3% permafrost-protection head start.",
        "funds": 40.0,
        "dampening": 0.03,
    },
    "mitigation": {
        "label": "Mitigation-led (Paris-aligned)",
        "blurb": "Protect the peat from day one: a 6% permafrost-protection head start, no extra funds.",
        "funds": 0.0,
        "dampening": 0.06,
    },
}

RESCUE_COST = 200.0
RESCUE_DURATION_ROUNDS = 5
RESCUE_DAMPENING_BONUS = 0.5
RESCUE_MAX_DAMPENING = 0.95

# GG-13: the "Ice Age" streak medal. Consecutive rounds Region A goes without
# a tipping event (melt starting, or the critical tier) earn a frostier medal
# at each tier: (rounds needed, name, icon), ascending.
ICE_AGE_TIERS = (
    (5, "Frost", "\u2744\uFE0F"),
    (10, "Glacier", "\U0001F9CA"),
    (15, "Ice Age", "\U0001F3D4\uFE0F"),
)

# G-24: how many recent rounds of acceleration readings each region keeps for
# the sparkline next to the acceleration readout.
ACCEL_HISTORY_MAX = 30


# GG-2: "Hold the Line", the run-based mode. Keep at least HOLD_LINE_MIN_UNTIPPED of the three
# managed regions out of the critical tier for as many rounds as you can. A region counts as
# tipped while it is critical (its methane feedback is at least as large as the background rise).
# The background gets harsher in steps: every HOLD_LINE_ESCALATION_EVERY rounds a new escalation
# event adds HOLD_LINE_ESCALATION_STEP degrees to every round's background rise AND erodes the
# ceiling on how much dampening investment can hold (by HOLD_LINE_CAP_EROSION, never below
# HOLD_LINE_MIN_CAP), so even a fully invested region eventually cannot hold. The events are
# stylised game events, not forecasts, and are fixed by the round number (no luck). Score is rounds
# survived. HOLD_LINE_MAX_ROUNDS ends a run that is still standing, as a completed run.
HOLD_LINE_MIN_UNTIPPED = 2
HOLD_LINE_ESCALATION_EVERY = 5
HOLD_LINE_ESCALATION_STEP = 0.2
HOLD_LINE_CAP_EROSION = 0.02
HOLD_LINE_MIN_CAP = 0.3
HOLD_LINE_MAX_ROUNDS = 100
HOLD_LINE_EVENTS = (
    "Heat dome",
    "Boreal wildfire season",
    "Marine heatwave",
    "Early snowmelt",
    "Dry summer",
    "Soot on the ice",
)

# GG-24: run titles by average degrees saved across Regions A-C at the end of a run,
# (minimum saved, title), ascending. The escalating counterfactual makes saved figures large, so
# the bands are set from the three stewards' fixed plans (about 14, 150 and 260).
RUN_TITLES = (
    (0.0, "Ice Cube"),
    (10.0, "Snowflake Counter"),
    (40.0, "Frost Warden"),
    (90.0, "Permafrost Keeper"),
    (150.0, "Glacier Steward"),
    (220.0, "Tundra Guardian"),
    (300.0, "Cryosphere Guardian"),
)

# G-13: display units for temperature. Every figure in this game is a rise above the starting
# level, so a Fahrenheit reading multiplies by 1.8 (no 32 offset) and Kelvin equals Celsius.
TEMP_UNITS = ("c", "f", "k")
TEMP_UNIT_STORAGE_KEY = "thaw_temp_unit_v1"

long_game = False
hold_the_line = False
temp_unit = "c"


def deg(value, digits=1, plus=False):
    """G-13: a temperature rise as text in the chosen unit. Celsius is the plain degree sign the
    game always used, so existing text is unchanged by default."""
    prefix = "+" if plus else ""
    if temp_unit == "f":
        return f"{prefix}{value * 1.8:.{digits}f}\u00b0F"
    if temp_unit == "k":
        return f"{prefix}{value:.{digits}f} K"
    return f"{prefix}{value:.{digits}f}\u00b0"


def warming_scale():
    return LONG_GAME_WARMING_SCALE if long_game else 1.0


def output_income_per_unit():
    return OUTPUT_INCOME_PER_UNIT * (LONG_GAME_INCOME_SCALE if long_game else 1.0)


def escalation_level(round_number):
    """GG-2: how many escalation events have happened by the start of this round (0 outside
    Hold the Line). Events land at the start of rounds 5, 9, 13, ..."""
    if not hold_the_line:
        return 0
    return max(0, (int(round_number) - 1) // HOLD_LINE_ESCALATION_EVERY)


def escalation_event_name(level):
    return HOLD_LINE_EVENTS[(level - 1) % len(HOLD_LINE_EVENTS)] if level > 0 else ""


def max_dampening(round_number):
    """The ceiling on investment dampening this round: MAX_FEEDBACK_DAMPENING, less the erosion
    from escalation events in Hold the Line."""
    level = escalation_level(round_number)
    if level == 0:
        return MAX_FEEDBACK_DAMPENING
    return max(HOLD_LINE_MIN_CAP, MAX_FEEDBACK_DAMPENING - HOLD_LINE_CAP_EROSION * level)


def base_rise_per_round(round_number=None):
    """The background warming rate this round (scaled in the long game, stepped up by
    escalation events in Hold the Line)."""
    if round_number is None:
        round_number = region.round_number
    return (
        BASE_TEMP_RISE_PER_ROUND * warming_scale()
        + HOLD_LINE_ESCALATION_STEP * escalation_level(round_number)
    )


class RegionState:
    def __init__(self):
        self.round_number = 1
        self.funds = STARTING_FUNDS
        self.capacity = {c: 0 for c in CATEGORIES}
        self.temperature = 0.0
        self.melt_started_round = None
        # One-tick flag: true only for the single render right after the
        # feedback loop crosses its tipping threshold — the visual cue
        # for that moment, consumed (and cleared) by the next render.
        self.just_started_melting = False
        # A parallel, fully undampened trajectory — same background rise,
        # same feedback mechanics, but zero intervention ever. The gap
        # between this and the real temperature is the hope-angle payoff.
        self.counterfactual_temperature = 0.0
        # Iteration Pass 2 — per-round temperature log, feeding this
        # region's mini-graph in the multi-region comparison.
        self.temperature_history = []
        # Iteration Pass 3 — one-tick flag: true only for the single
        # render right after preserve/monitor is invested, so the
        # dampening readout can flash instead of silently ticking up.
        # See feedback_dampening_fraction() below for why this matters:
        # pre-melt, that number has zero effect on anything else visible,
        # so without a cue of its own the lever reads as doing nothing.
        self.just_invested_intervention = False
        # G4: an optional, player-typed label for what strategy this
        # region is meant to represent ("aggressive growth", "heavy
        # preservation", ...) — purely descriptive, never read by any
        # game logic, so an empty string is always a safe default.
        self.strategy_label = ""
        # G10: the feedback-dampening fraction in effect at the exact
        # moment melt started (None until then) — lets early_investor
        # check "was meaningful dampening already in place *before* melt
        # began" rather than "is it in place right now," which could be
        # invested well after melt started and still read as true.
        self.dampening_at_melt_start = None
        # G10: one-time callout — true only for the single render right
        # after this region's real temperature first lags behind its own
        # undampened counterfactual crossing SECOND_WARMING_MILESTONE,
        # i.e. the first concrete proof intervention delayed reaching a
        # further warming milestone. `milestone_delay_announced` prevents
        # re-firing once already shown, the same one-shot-flag shape as
        # SOL/Grid's own achievement-adjacent "first time" trackers.
        self.just_delayed_milestone = False
        self.milestone_delay_announced = False
        # G24: one-tick flag, true only for the render right after this
        # region's warming first crosses into the critical tier (and again
        # only if it later drops out and re-crosses).
        self.just_became_critical = False
        # G28: rounds since this region last had a "tipping event" (melt
        # starting, or warming entering the critical tier); tipping_events
        # counts how many have happened so the UI can tell "none yet" from
        # "reset just now".
        self.rounds_since_tipping_event = 0
        self.tipping_events = 0
        # G12: one-tick flag for the pre-emptive-dampening praise callout.
        self.just_preempted_melt = False
        # G16/G19: transient per-round event tags ("melt", "critical",
        # "milestone_delay", "preempt") for the scientist's log. Rebuilt
        # every advance_round(), never saved.
        self.round_events = []
        # G11: lifetime running average of acceleration_factor() across
        # every round actually played -- distinct from that method's own
        # instantaneous current-round reading, and the metric the
        # community-comparison panel asks the shared stats backend to
        # rank. Updated via Welford's incremental-mean formula in
        # advance_round() (see _record_acceleration_sample()) rather than
        # a second unbounded history list the way temperature_history
        # already tracks the raw trajectory. Starts at 1.0 -- the same
        # steady-state reading acceleration_factor() itself returns
        # before any rounds have been played.
        self.average_acceleration_factor = 1.0
        self.acceleration_samples = 0
        # G21: one rescue per region, ever. `rescue_rounds_left` counts down
        # the boost's remaining rounds; `rescue_used` stays true afterwards.
        self.rescue_used = False
        self.rescue_rounds_left = 0
        # G13: the chosen POLICY_STANCES key (None until chosen) and the
        # baseline dampening it grants (derived from the key, never saved).
        self.policy_stance = None
        self.policy_dampening = 0.0
        # G15: consecutive rounds the loop has been held down by investment
        # alone, and the running total of warming pulled back so far.
        self.stabilized_rounds = 0
        self.restored_total = 0.0
        # GG-13: the longest run of rounds without a tipping event so far.
        self.best_stable_streak = 0
        # G-24: the last ACCEL_HISTORY_MAX acceleration readings, one per round.
        self.acceleration_history = []
        # GG-20: one-tick flag, set when the latest preserve/monitor investment
        # (or rescue) pulled the projected next-round acceleration back under
        # the critical tier. Transient: never saved.
        self.just_pulled_back = False

    def base_rise(self):
        """The background rise for this region's current round."""
        return base_rise_per_round(self.round_number)

    def projected_next_acceleration(self):
        """The acceleration factor the region would read after the coming
        round's warming lands, on its current effective dampening. Melt
        itself can't be pulled back (below the threshold the feedback bonus
        is zero whatever you invest), so this is what an investment can
        actually change: whether next round tips into the critical tier."""
        next_temperature = self.temperature + self.current_rise_rate()
        excess = max(0.0, next_temperature - MELT_THRESHOLD)
        bonus = excess * FEEDBACK_RATE_PER_DEGREE_OVER * warming_scale() * (1 - self.effective_dampening_fraction())
        return (self.base_rise() + bonus) / self.base_rise()

    def restoration_active(self):
        return self.stabilized_rounds >= RESTORATION_STREAK_ROUNDS and self.is_melting()

    def _investment_acceleration_factor(self):
        """acceleration_factor() as it would read on investment dampening
        alone, so a temporary rescue can't count toward stabilization."""
        excess = max(0.0, self.temperature - MELT_THRESHOLD)
        bonus = excess * FEEDBACK_RATE_PER_DEGREE_OVER * warming_scale() * (1 - self.feedback_dampening_fraction())
        return (self.base_rise() + bonus) / self.base_rise()

    def _apply_restoration(self):
        """Advances the stabilization streak and, once it has held long
        enough, pulls some melt-driven warming back. Called once per
        advance_round(), after that round's warming has landed."""
        if self.is_melting() and self._investment_acceleration_factor() <= RESTORATION_MAX_ACCELERATION:
            self.stabilized_rounds += 1
        else:
            self.stabilized_rounds = 0
        if not self.restoration_active():
            return
        amount = min(
            self.capacity["preserve"] * RESTORATION_PER_PRESERVE_UNIT * warming_scale(),
            RESTORATION_MAX_PER_ROUND * warming_scale(),
            self.temperature - MELT_THRESHOLD,
        )
        if amount <= 0:
            return
        if self.stabilized_rounds == RESTORATION_STREAK_ROUNDS:
            self.round_events.append("restoration")
        self.temperature -= amount
        self.restored_total += amount

    def can_choose_policy_stance(self):
        """G13: only once, and only before the first round is played or
        anything is invested -- a starting stance, not a mid-game lever."""
        return (
            self.policy_stance is None
            and self.round_number == 1
            and sum(self.capacity.values()) == 0
        )

    def choose_policy_stance(self, key):
        if key not in POLICY_STANCES or not self.can_choose_policy_stance():
            return False
        stance = POLICY_STANCES[key]
        self.policy_stance = key
        self.policy_dampening = stance["dampening"]
        self.funds += stance["funds"]
        return True

    def is_critical(self):
        return self.is_melting() and self.acceleration_factor() >= CRITICAL_ACCELERATION_FACTOR

    def temperature_trend(self):
        """G16: "up"/"down"/"flat" comparing the most recent round's rise to
        the one before it, or None until at least one round has elapsed."""
        series = [0.0] + list(self.temperature_history)
        if len(series) < 3:
            return None
        last = series[-1] - series[-2]
        prev = series[-2] - series[-3]
        if last > prev + 0.005:
            return "up"
        if last < prev - 0.005:
            return "down"
        return "flat"

    def invest(self, category):
        cost = INVEST_COST[category]
        if self.funds < cost:
            return False
        intervention = category in ("preserve", "monitor")
        was_headed_critical = intervention and self.projected_next_acceleration() >= CRITICAL_ACCELERATION_FACTOR
        self.funds -= cost
        self.capacity[category] += 1
        if intervention:
            self.just_invested_intervention = True
            if was_headed_critical and self.projected_next_acceleration() < CRITICAL_ACCELERATION_FACTOR:
                self.just_pulled_back = True
        return True

    def is_melting(self):
        return self.temperature >= MELT_THRESHOLD

    def feedback_dampening_fraction(self):
        total = (
            self.capacity["preserve"] * DAMPENING_PER_PRESERVE_UNIT
            + self.capacity["monitor"] * DAMPENING_PER_MONITOR_UNIT
            + self.policy_dampening
        )
        return min(max_dampening(self.round_number), total)

    def rescue_active(self):
        return self.rescue_rounds_left > 0

    def can_rescue(self):
        """G21: true only while critical, not already spent, and affordable."""
        return self.is_critical() and not self.rescue_used and self.funds >= RESCUE_COST

    def rescue(self):
        """Spends RESCUE_COST for RESCUE_DURATION_ROUNDS of extra dampening.
        Returns False (changing nothing) if the rescue isn't available."""
        if not self.can_rescue():
            return False
        was_headed_critical = self.projected_next_acceleration() >= CRITICAL_ACCELERATION_FACTOR
        self.funds -= RESCUE_COST
        self.rescue_used = True
        self.rescue_rounds_left = RESCUE_DURATION_ROUNDS
        if was_headed_critical and self.projected_next_acceleration() < CRITICAL_ACCELERATION_FACTOR:
            self.just_pulled_back = True
        return True

    def effective_dampening_fraction(self):
        """What the feedback loop actually feels this round: investment
        dampening plus any active rescue boost. Deliberately separate from
        feedback_dampening_fraction() (investment only), which the
        dampening achievements and readouts keep using so a temporary
        emergency boost can't earn a permanent-protection achievement."""
        base = self.feedback_dampening_fraction()
        if self.rescue_active():
            return max(base, min(RESCUE_MAX_DAMPENING, base + RESCUE_DAMPENING_BONUS))
        return base

    def intervention_feedback_message(self):
        """Iteration Pass 3 fix: an immediate, legible efficacy readout
        for the intervention lever, true from the very first preserve/
        monitor investment — unlike trajectory_message()/
        acceleration_message(), it doesn't need melt to have started yet
        to say something real. Flow principle #2 (immediate feedback):
        without this, a player who invests early gets no visible sign
        their action did anything until a feedback loop they may never
        trigger this session finally kicks in.

        G18: phrasing now varies by dampening magnitude rather than one
        fixed sentence regardless of how much protection is actually in
        place — a player at 8% and a player at 80% were reading
        identical text before this, which undersold how much stronger a
        heavily-invested lever really is."""
        dampening = self.feedback_dampening_fraction()
        if dampening <= 0.0:
            return "No preservation or monitoring investment yet — a future melt would hit at full force."
        pct = dampening * 100
        if self.capacity["preserve"] + self.capacity["monitor"] == 0:
            return (
                f"Your policy stance is already dampening the feedback loop by {pct:.0f}% "
                f"\u2014 a head start, before any preservation or monitoring investment."
            )
        if dampening < 0.3:
            tier = "\U0001F331 a modest start"
        elif dampening < 0.6:
            tier = "\U0001F6E1\uFE0F a meaningful buffer"
        else:
            tier = "\U0001F3F0 a strong shield"
        return (
            f"Preservation & monitoring investment is already dampening the feedback loop by "
            f"{pct:.0f}% — {tier}, in place now, whether or not melt has started yet."
        )

    def feedback_bonus(self):
        """Extra warming this round from methane released by permafrost
        melt — zero until the melt threshold is crossed, then grows with
        how far past it the temperature has climbed. Intervention
        investment dampens this, never the background rise itself."""
        excess = max(0.0, self.temperature - MELT_THRESHOLD)
        raw_bonus = excess * FEEDBACK_RATE_PER_DEGREE_OVER * warming_scale()
        return raw_bonus * (1 - self.effective_dampening_fraction())

    def current_rise_rate(self):
        return self.base_rise() + self.feedback_bonus()

    def _record_acceleration_sample(self):
        """G11: folds this round's acceleration_factor() into the running
        lifetime average via Welford's incremental-mean update. Called
        once per advance_round(), before temperature updates for the
        round, so the sample averaged in is the exact same reading
        acceleration_message() would report to the player as "this
        round's" rate -- not the rate that will be current *after* the
        round's rise lands."""
        self.acceleration_samples += 1
        sample = self.acceleration_factor()
        self.average_acceleration_factor += (
            sample - self.average_acceleration_factor
        ) / self.acceleration_samples

    def advance_round(self):
        self.funds += self.capacity["output"] * output_income_per_unit()
        current_round = self.round_number
        self.round_events = []
        base_rise_at_start = self.base_rise()
        was_critical = self.is_critical()
        self._record_acceleration_sample()
        self.temperature += self.current_rise_rate()
        if self.rescue_rounds_left > 0:
            self.rescue_rounds_left -= 1
        if self.melt_started_round is None and self.is_melting():
            self.melt_started_round = current_round
            self.just_started_melting = True
            # G10 (early_investor): snapshot dampening at the exact
            # moment melt begins, so the achievement can ask "was
            # meaningful protection already in place *before* melt
            # started" rather than just "is it in place right now."
            self.dampening_at_melt_start = self.feedback_dampening_fraction()
            self.round_events.append("melt")
            if self.capacity["preserve"] + self.capacity["monitor"] > 0:
                self.just_preempted_melt = True
                self.round_events.append("preempt")
        if not was_critical and self.is_critical():
            self.just_became_critical = True
            self.round_events.append("critical")
        if "melt" in self.round_events or "critical" in self.round_events:
            self.tipping_events += 1
            self.rounds_since_tipping_event = 0
        else:
            self.rounds_since_tipping_event += 1
        self.best_stable_streak = max(self.best_stable_streak, self.rounds_since_tipping_event)

        self._apply_restoration()

        counterfactual_excess = max(0.0, self.counterfactual_temperature - MELT_THRESHOLD)
        counterfactual_rate = base_rise_at_start + (
            counterfactual_excess * FEEDBACK_RATE_PER_DEGREE_OVER * warming_scale()
        )
        self.counterfactual_temperature += counterfactual_rate

        self.round_number += 1
        self.temperature_history.append(self.temperature)
        self.acceleration_history.append(round(self.acceleration_factor(), 3))
        del self.acceleration_history[:-ACCEL_HISTORY_MAX]

        # G10: the first time the undampened counterfactual has reached
        # SECOND_WARMING_MILESTONE while this (dampened) region hasn't —
        # concrete, one-time proof that intervention delayed reaching a
        # further warming milestone, not just slowed the rate in the
        # abstract. Only meaningful once some dampening has actually been
        # invested; a region with zero dampening never differs from its
        # own counterfactual, so the condition naturally never fires for
        # it (see feedback_bonus()/counterfactual math above — identical
        # for both when feedback_dampening_fraction() is 0).
        if (
            not self.milestone_delay_announced
            and self.counterfactual_temperature >= SECOND_WARMING_MILESTONE
            and self.temperature < SECOND_WARMING_MILESTONE
        ):
            self.milestone_delay_announced = True
            self.just_delayed_milestone = True
            self.round_events.append("milestone_delay")

    def temperature_saved(self):
        """The hope-angle payoff, as a direct number: how much lower
        temperature is right now than the fully-undampened counterfactual
        trajectory would have reached by this round."""
        return self.counterfactual_temperature - self.temperature

    def trajectory_message(self):
        saved = self.temperature_saved()
        if saved <= 0.01:
            return "No meaningful difference from intervention yet."
        return (
            f"Early intervention has kept warming {deg(saved)} lower than an "
            f"unmitigated trajectory would have reached by now."
        )

    def acceleration_factor(self):
        """How many times faster than the background baseline warming is
        rising right now — 1.0x when stable, growing once melt kicks in."""
        return self.current_rise_rate() / self.base_rise()

    def acceleration_message(self):
        if not self.is_melting():
            return "Warming is rising at a steady, linear rate."
        return (
            f"Warming has accelerated to {self.acceleration_factor():.1f}x the background "
            f"rate since permafrost began melting in round {self.melt_started_round}."
        )


region = RegionState()

# Iteration Pass 2 — multi-region comparison: two more player-managed
# regions run alongside the original ("Region A", left entirely as-is
# above — same object, same element IDs, same behavior, so every Pass 1
# test keeps passing unchanged). Each can be given a different strategy,
# so the feedback-loop consequences of intervention vs. neglect are
# visible side-by-side within one session rather than only across
# separate playthroughs.
region_b = RegionState()
region_c = RegionState()
SECONDARY_REGIONS = {"b": region_b, "c": region_c}

REGION_FLAVOR = {
    "b": "Coastal tundra — closer to the sea, slightly more exposed to storm-driven erosion.",
    "c": "Boreal interior — deeper permafrost, slower to feel changes at first.",
}

# G13: a fourth, optional region that always neglects intervention —
# every round it auto-invests every affordable unit of funds straight
# into Output and never touches Preservation/Monitoring, so its feedback
# dampening stays permanently at 0%. Its temperature trajectory ends up
# numerically identical to the primary region's own
# counterfactual_temperature (both use the undampened feedback formula),
# which makes it a concrete, playable stand-in for "what if nobody
# intervened" rather than only an abstract number on Region A's card.
# Hidden behind a reveal toggle (worst_case_region_revealed) so it never
# clutters the default screen — the toggle itself doubles as the
# "worst_case_witnessed" achievement's tracked state, since revealing it
# is the one genuinely new player action involved.
region_d = RegionState()
worst_case_region_revealed = False
# G30: the "Region D is fully automated" first-reveal note shows until the
# player closes the panel once, then never again.
worst_case_intro_seen = False

# G19: scientist's log -- a running, per-round record of key moments in the
# three managed regions. Newest last; capped so a long session (and the
# save payload) stays small.
#
# Z11 (planning/TODO.md, site-wide goal): the append-and-cap bookkeeping
# below delegates to shared/narrative_log.py -- the shared component this
# game's own pattern (alongside Continuum's "Chronicle") helped generalize.
# A pure refactor, not a behavior change: narrative_log.add_entry() trims
# exactly the way the old `del science_log[:-SCIENCE_LOG_MAX]` line always
# trimmed. This game's own rendering (science_log_html(), an HTML-string
# builder feeding a `<ol>`/`<li>` list inside a <details> disclosure) is
# deliberately NOT migrated onto the shared module's DOM-based `render()` --
# see this file's own CLAUDE.md Z11 build note for why forcing that
# render shape onto this already-shipped, differently-structured markup
# would be a rewrite, not a drop-in.
SCIENCE_LOG_MAX = 40
science_log = []

_EVENT_TEXT = {
    "melt": "permafrost began melting at {temp}.",
    "critical": "the feedback loop went critical ({accel:.1f}x background warming).",
    "milestone_delay": "intervention delayed reaching {milestone} warming.",
    "preempt": "pre-emptive protection ({damp:.0f}% dampening) was already in place when melt began.",
    "cascade": "a tipping cascade from the neighboring region added {bump} of warming.",
    "restoration": "the feedback loop held steady long enough for restoration to begin pulling warming back.",
}


def _record_round_events():
    for label, r in (("A", region), ("B", region_b), ("C", region_c)):
        for event in r.round_events:
            text = _EVENT_TEXT[event].format(
                temp=deg(r.temperature, plus=True),
                accel=r.acceleration_factor(),
                milestone=deg(SECOND_WARMING_MILESTONE, 0, plus=True),
                damp=(r.dampening_at_melt_start or 0.0) * 100,
                bump=deg(CASCADE_BUMP),
            )
            science_log.append({"region": label, "round": r.round_number - 1, "text": text})
    narrative_log.cap_entries(science_log, SCIENCE_LOG_MAX)


def science_log_html():
    if not science_log:
        return "<li>No key moments recorded yet.</li>"
    items = []
    for entry in reversed(science_log):
        text = (
            str(entry["text"]).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        items.append(f"<li>Round {entry['round']} \u2014 Region {entry['region']}: {text}</li>")
    return "".join(items)


def _auto_play_worst_case_region():
    """Called once per Advance Round: spends every affordable unit of
    Region D's funds on Output only, then advances it — pure neglect,
    replayed automatically every round regardless of whether the panel
    revealing it is currently open.

    Region D's own neglect is what makes it a worst case: every round's
    income is `capacity["output"] * OUTPUT_INCOME_PER_UNIT`, all of which
    gets reinvested straight back into more output at a flat per-unit
    cost — a compounding ~30% growth in capacity every round. That
    exponential growth is the intended story ("look how much worse doing
    nothing gets"), but spending it one unit at a time via a `while
    region_d.invest("output"): pass` loop meant the SIMULATION cost grew
    exponentially with round count too — a long session's Advance Round
    click could take seconds by round 50+. Buying the affordable unit
    count directly is O(1) regardless of how large the region has grown,
    with the exact same end state `invest()` would have produced one unit
    at a time (same flat per-unit cost, no partial-unit spend)."""
    cost = INVEST_COST["output"]
    units = int(region_d.funds // cost)
    if units:
        region_d.funds -= units * cost
        region_d.capacity["output"] += units
    region_d.advance_round()


# G11: one-click preset strategies for Region B/C, so a player can set up
# a comparison strategy without manually clicking each category several
# times. Each preset spends as much of the region's *current* funds as
# it can afford in one go, repeatedly picking whichever weighted
# category is currently furthest behind its target share — a simple,
# deterministic way to approximate the named ratio without needing
# fractional investments (which don't exist in this game).
PRESET_WEIGHTS = {
    "growth": {"output": 1.0},
    "preservation": {"preserve": 0.6, "monitor": 0.4},
    "balanced": {"output": 1 / 3, "preserve": 1 / 3, "monitor": 1 / 3},
}

preset_used_ever = False


def preset_tooltip_text(preset_name):
    """Onboarding-tooltip audit fix: a preset button's own label ("Preset:
    Growth") names the strategy but not what clicking it actually does —
    it immediately spends everything the region can currently afford, in
    one go, rather than setting an ongoing policy. Built from
    PRESET_WEIGHTS directly so the tooltip text can't drift out of sync
    with the real weighting if it's ever tuned."""
    weights = PRESET_WEIGHTS[preset_name]
    if len(weights) == 1:
        (only_category,) = weights.keys()
        what = f"on {CATEGORY_LABEL[only_category]}"
    else:
        parts = [f"{CATEGORY_LABEL[c]} ({w * 100:.0f}%)" for c, w in weights.items()]
        what = "split roughly " + ", ".join(parts)
    return (
        f"Spends everything this region can currently afford right now, {what} "
        "— a one-time action, not an ongoing policy."
    )


def apply_preset(r, preset_name):
    """Applies one named preset's weighting to region `r`, spending as
    much as it can afford right now. Returns True if at least one
    investment was actually made (used by the caller to decide whether
    to flip preset_used_ever, and by tests to check a no-op call did
    nothing)."""
    global preset_used_ever
    weights = PRESET_WEIGHTS.get(preset_name)
    if not weights:
        return False
    invested_any = _run_preset(r, weights)
    if invested_any:
        preset_used_ever = True
    return invested_any


def _run_preset(r, weights):
    categories = list(weights.keys())
    spent = dict.fromkeys(categories, 0.0)
    invested_any = False
    while True:
        affordable = [c for c in categories if r.funds >= INVEST_COST[c]]
        if not affordable:
            break
        target = min(affordable, key=lambda c: spent[c] / weights[c])
        if not r.invest(target):
            break
        spent[target] += INVEST_COST[target]
        invested_any = True
    return invested_any


def preset_preview_text(r, preset_name):
    """G14: what clicking a preset would buy right now, computed on a
    scratch RegionState so nothing is committed. Used in the button's
    hover tooltip alongside the static explanation."""
    weights = PRESET_WEIGHTS.get(preset_name)
    if not weights:
        return ""
    scratch = RegionState()
    scratch.funds = r.funds
    if not _run_preset(scratch, weights):
        return "Right now: not enough funds for anything."
    parts = [
        f"{scratch.capacity[c]}x {CATEGORY_LABEL[c]}" for c in CATEGORIES if scratch.capacity[c]
    ]
    return "Right now this would buy: " + ", ".join(parts) + "."


def best_region_identifier():
    """G2/G15: which of the three player-managed regions (never Region D
    — it's a deliberate worst-case baseline, not a competitor for
    "best") currently has the lowest temperature. Ties resolve to
    whichever region is listed first (Region A), which is an acceptable,
    documented tie-break rather than a meaningful ranking."""
    candidates = [("A", region), ("B", region_b), ("C", region_c)]
    best_label, _ = min(candidates, key=lambda pair: pair[1].temperature)
    return best_label


def best_region_message():
    """G2: an explicit end-of-session (or any-time) "which region did
    best" line, comparing current temperature across the three
    player-managed regions."""
    label = best_region_identifier()
    best = {"A": region, "B": region_b, "C": region_c}[label]
    cap = best.capacity
    return (
        f"Region {label} currently has the lowest temperature ({deg(best.temperature, plus=True)}) "
        f"among your three managed regions, with an investment mix of "
        f"{cap['preserve']} preserve / {cap['monitor']} monitor / {cap['output']} output."
    )


MINI_GRAPH_WIDTH = 120
MINI_GRAPH_HEIGHT = 40


def mini_temp_graph_svg(history, name=None):
    """A compact single-line temperature trend for one region's card —
    deliberately tiny and unlabeled beyond its axis-free shape, since the
    point is the divergence *between* regions' graphs, not reading any
    one of them precisely.

    G14: also draws a faint dashed reference line at MELT_THRESHOLD when
    that value falls within the graph's current visible range, so the
    moment a region's curve crosses the melt threshold is legible on the
    mini-graph itself, not just inferable from the melt-status text next
    to it."""
    if len(history) < 2:
        return ""
    n = len(history)
    lo, hi = min(history), max(history)
    if hi - lo < 1e-9:
        ys = [MINI_GRAPH_HEIGHT / 2 for _ in history]
    else:
        ys = [MINI_GRAPH_HEIGHT - ((v - lo) / (hi - lo)) * MINI_GRAPH_HEIGHT for v in history]
    xs = [i * (MINI_GRAPH_WIDTH / (n - 1)) for i in range(n)]
    points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))

    threshold_line = ""
    if hi - lo >= 1e-9 and lo <= MELT_THRESHOLD <= hi:
        threshold_y = MINI_GRAPH_HEIGHT - ((MELT_THRESHOLD - lo) / (hi - lo)) * MINI_GRAPH_HEIGHT
        threshold_line = (
            f'<line x1="0" y1="{threshold_y:.1f}" x2="{MINI_GRAPH_WIDTH}" y2="{threshold_y:.1f}" '
            f'class="mini-temp-threshold-line" />'
            f'<text x="2" y="{max(threshold_y - 2, 7):.1f}" class="mini-temp-threshold-label">'
            f"{deg(MELT_THRESHOLD, 0, plus=True)}</text>"
        )

    aria = ""
    key = ""
    marker = ""
    if name:
        summary = graph_summary_text(name, history)
        aria = f' role="img" aria-label="{summary}"'
        key = GRAPH_REGION_KEYS.get(name, "")
        if key:
            key = f" graph-region-{key}"
            marker = _graph_end_marker(key[-1], xs[-1], ys[-1])
    return (
        f'<svg viewBox="0 0 {MINI_GRAPH_WIDTH} {MINI_GRAPH_HEIGHT}" class="mini-temp-graph-svg{key}"{aria}>'
        f"{threshold_line}"
        f'<polyline points="{points}" class="mini-temp-line" />'
        f"{marker}"
        f"</svg>"
    )


# G-14: each region's line gets a dash pattern (CSS, by graph-region-<key>) and an end marker shape
# of its own, shown when the "graph patterns" setting is on, so the lines can be told apart
# without colour. The shapes are always drawn and the setting only reveals them.
GRAPH_REGION_KEYS = {"Region A": "a", "Region B": "b", "Region C": "c", "Region D": "d"}


def _graph_end_marker(key, x, y):
    r = 3.2
    x = min(max(x, r), MINI_GRAPH_WIDTH - r)
    y = min(max(y, r), MINI_GRAPH_HEIGHT - r)
    if key == "a":  # circle
        shape = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" />'
    elif key == "b":  # square
        shape = f'<rect x="{x - r:.1f}" y="{y - r:.1f}" width="{2 * r}" height="{2 * r}" />'
    elif key == "c":  # triangle
        shape = f'<polygon points="{x:.1f},{y - r:.1f} {x + r:.1f},{y + r:.1f} {x - r:.1f},{y + r:.1f}" />'
    else:  # diamond
        shape = f'<polygon points="{x:.1f},{y - r:.1f} {x + r:.1f},{y:.1f} {x:.1f},{y + r:.1f} {x - r:.1f},{y:.1f}" />'
    return f'<g class="mini-temp-end mini-temp-end--{key}">{shape}</g>'


def _melt_status_label(r):
    """G3: a third, distinct "critical" state on top of the existing
    binary melting/stable read — once warming has accelerated past
    CRITICAL_ACCELERATION_FACTOR times the background rate, "Melting" no
    longer distinguishes a region that just crossed the threshold from
    one whose feedback loop is now compounding fast."""
    if not r.is_melting():
        return "stable"
    if r.acceleration_factor() >= CRITICAL_ACCELERATION_FACTOR:
        return "critical"
    return "melting"


TREND_TEXT = {
    "up": ("\u25B2", "Rising faster than last round"),
    "down": ("\u25BC", "Rising slower than last round"),
    "flat": ("\u25B6", "Rising at the same pace as last round"),
}


def _render_trend(element_id, r):
    """G16: a small shape-coded arrow (not color-only) next to a region's
    temperature readout, comparing this round's rise to the previous one."""
    element = document.getElementById(element_id)
    trend = r.temperature_trend()
    if trend is None:
        element.innerText = ""
        element.title = ""
        return
    arrow, meaning = TREND_TEXT[trend]
    element.innerText = arrow
    element.title = meaning


def _rescue_status_text(r):
    if r.rescue_active():
        n = r.rescue_rounds_left
        return f"\U0001F6DF Rescue active \u2014 extra dampening for {n} more round{'s' if n != 1 else ''}."
    if r.rescue_used:
        return "Rescue spent \u2014 this region's one emergency lever has been used."
    if r.is_critical():
        if r.funds >= RESCUE_COST:
            return f"Critical \u2014 an emergency rescue ({RESCUE_COST:.0f} funds) is available, once."
        return f"Critical \u2014 an emergency rescue costs {RESCUE_COST:.0f} funds (you have {r.funds:.0f})."
    return ""


def _render_policy_stance():
    """G13: three stance buttons (disabled once the starting choice is made
    or the game has moved past round 1) plus a one-line readout."""
    can_choose = region.can_choose_policy_stance()
    for key, stance in POLICY_STANCES.items():
        button = document.getElementById(f"policy-stance-{key}-button")
        chosen = region.policy_stance == key
        button.innerText = ("\u2713 " if chosen else "") + stance["label"]
        button.title = stance["blurb"]
        button.disabled = not can_choose
    display = document.getElementById("policy-stance-display")
    if region.policy_stance is not None:
        stance = POLICY_STANCES[region.policy_stance]
        display.innerText = f"Policy stance: {stance['label']}. {stance['blurb']}"
    elif can_choose:
        display.innerText = (
            "Optional: pick a starting policy stance before round 1. It is a permanent, "
            "modest weighting \u2014 none is clearly best."
        )
    else:
        display.innerText = "No starting policy stance was chosen for this region."


def _render_restoration(prefix, r):
    """G15: a status line that only appears once restoration is running or
    has ever reversed something, so a stable region carries no clutter."""
    element = document.getElementById(f"{prefix}restoration-status")
    if r.restoration_active():
        element.innerText = (
            f"\U0001F331 Restoration under way \u2014 {deg(r.restored_total)} of melt-driven "
            f"warming pulled back so far."
        )
        element.hidden = False
    elif r.restored_total > 0:
        element.innerText = (
            f"Restoration paused \u2014 {deg(r.restored_total)} pulled back so far; "
            f"it resumes once the feedback loop is held down again."
        )
        element.hidden = False
    else:
        element.innerText = ""
        element.hidden = True


def _render_rescue(prefix, r):
    """G21: shows the rescue button only while it is a live option (critical
    and unspent), and the status line only when there is something to say,
    so a stable region carries no extra clutter."""
    button = document.getElementById(f"{prefix}rescue-button")
    status = document.getElementById(f"{prefix}rescue-status")
    button.innerText = f"\U0001F6DF Emergency rescue ({RESCUE_COST:.0f})"
    button.hidden = not (r.is_critical() and not r.rescue_used)
    button.disabled = not r.can_rescue()
    text = _rescue_status_text(r)
    status.innerText = text
    status.hidden = text == ""


def render_secondary_region(prefix, r):
    """Renders one of the two added regions into its `{prefix}-*`
    elements. Deliberately separate from the primary region's inline
    render code below (rather than a shared helper for all three) so
    the original Pass 1 behavior for "Region A" — including its
    whole-page tipping-flash — stays byte-for-byte unchanged.

    G1/G6: also renders the same dampening/acceleration/temperature-saved
    readouts Region A already had — every one of these is already a
    generic RegionState method, so no new game logic was needed, only
    new elements to write them into."""
    document.getElementById(f"{prefix}-temperature-display").innerText = deg(r.temperature, plus=True)
    _render_trend(f"{prefix}-temperature-trend", r)
    for preset_name in PRESET_WEIGHTS:
        document.getElementById(f"{prefix}-preset-{preset_name}-button").title = (
            preset_tooltip_text(preset_name) + " " + preset_preview_text(r, preset_name)
        )
    document.getElementById(f"{prefix}-funds-display").innerText = f"Funds: {r.funds:.0f}"
    document.getElementById(f"{prefix}-graph").innerHTML = mini_temp_graph_svg(
        r.temperature_history, f"Region {prefix.upper()}"
    )
    document.getElementById(f"{prefix}-dampening-display").innerText = (
        f"Dampening: {r.feedback_dampening_fraction() * 100:.0f}%"
    )
    document.getElementById(f"{prefix}-acceleration-display").innerText = r.acceleration_message()
    document.getElementById(f"{prefix}-trajectory-display").innerText = r.trajectory_message()
    _render_rescue(f"{prefix}-", r)
    _render_restoration(f"{prefix}-", r)

    status = _melt_status_label(r)
    melt_status_el = document.getElementById(f"{prefix}-melt-status-display")
    melt_status_el.innerText = status.capitalize()
    suffix = {"stable": "", "melting": " melt-status--active", "critical": " melt-status--critical"}[status]
    melt_status_el.className = "region-melt-status" + suffix

    card_el = document.getElementById(f"{prefix}-region-card")
    if r.just_started_melting:
        card_el.className = "region-card tipping-flash"
        r.just_started_melting = False
    else:
        card_el.className = "region-card"

    for category in CATEGORIES:
        document.getElementById(f"{prefix}-{category}-count").innerText = str(r.capacity[category])
        invest_button = document.getElementById(f"{prefix}-{category}-invest-button")
        invest_button.innerText = f"{CATEGORY_ICON[category]} ({INVEST_COST[category]})"
        invest_button.disabled = r.funds < INVEST_COST[category]


def render_worst_case_region():
    """G13: renders Region D's read-only stats into its own elements —
    no invest buttons, since it never receives player input, only the
    same graph/status readouts every other region gets. Always keeps
    its DOM up to date regardless of worst_case_region_revealed, so the
    numbers are correct the instant a player opens the panel rather than
    only starting from whenever they first reveal it."""
    r = region_d
    document.getElementById("d-temperature-display").innerText = deg(r.temperature, plus=True)
    document.getElementById("d-funds-display").innerText = f"Funds: {r.funds:.0f}"
    document.getElementById("d-graph").innerHTML = mini_temp_graph_svg(r.temperature_history, "Region D")

    status = _melt_status_label(r)
    melt_status_el = document.getElementById("d-melt-status-display")
    melt_status_el.innerText = status.capitalize()
    suffix = {"stable": "", "melting": " melt-status--active", "critical": " melt-status--critical"}[status]
    melt_status_el.className = "region-melt-status" + suffix

    card_el = document.getElementById("d-region-card")
    if r.just_started_melting:
        card_el.className = "region-card tipping-flash"
        r.just_started_melting = False
    else:
        card_el.className = "region-card"


# Info Page — optional, player-triggered supplement (never forced
# mid-session). Framing is written fresh, not copied from any source;
# sources are the curated real-world backing for the game's mechanics.
INFO_PAGE = {
    "framing": (
        "Arctic permafrost holds thousands of years of stored carbon and "
        "methane, and as it thaws that store starts releasing — a "
        "feedback loop where warming causes more warming. But real "
        "climate scientists describe it as a dimmer switch, not an "
        "on/off switch: every bit of avoided warming keeps more "
        "permafrost frozen. That framing is the backbone of Thaw's whole "
        "design."
    ),
    "mechanic_tie_in": (
        "Thaw's tipping-point moment is grounded in real observed "
        "evidence of accelerating Arctic methane emissions, not a purely "
        "speculative mechanic."
    ),
    "sources": [
        {
            "label": "MIT Climate Portal — Is methane release from the Arctic unstoppable?",
            "url": "https://climate.mit.edu/ask-mit/methane-release-arctic-unstoppable",
            "note": "The clearest source for Thaw's hope angle — frames the feedback loop as a dimmer switch, not an on/off switch.",
        },
        {
            "label": "Nature Climate Change — Seasonal increase of methane emissions linked to warming in Siberian tundra",
            "url": "https://www.nature.com/articles/s41558-022-01512-4",
            "note": "Real observational evidence (not just modeling) of the feedback loop already measurably happening.",
        },
        {
            "label": "WWF Arctic — Thawing permafrost",
            "url": "https://www.arcticwwf.org/the-circle/stories/thawing-permafrost/",
            "note": "An accessible explainer connecting permafrost thaw to real Arctic communities' lived experience.",
        },
        {
            "label": "PMC/NCBI — 21st-century modeled permafrost carbon emissions accelerated by abrupt thaw beneath lakes",
            "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC6093858/",
            "note": "A more technical source on abrupt (not just gradual) thaw mechanisms, tying to Thaw's tipping-point moment.",
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


# ===========================================================================
# G5: the tipping cascade. When Region A or Region B tips into melt, there is
# a small chance the shock spreads down the chain (A to B, B to C) as a
# one-time CASCADE_BUMP of warming. The game has no random number source
# (every round is reproducible), so the "chance" is a fixed pseudo-random
# roll derived from the round and source region: the same run always
# cascades the same way, but a player cannot predict or reroll it. The bump
# lands on both the receiving region's temperature and its own
# counterfactual, because no intervention could have prevented it (so
# "degrees saved" is unaffected). The chain is deliberately one-way and
# never reaches Region A or Region D, keeping D identical to A's
# counterfactual.
# ===========================================================================
CASCADE_CHANCE = 0.25
CASCADE_BUMP = 0.5


def cascade_roll(source_label, round_number):
    """A deterministic roll in [0, 1) for one (source region, round) pair."""
    mixed = (round_number * 2654435761 + ord(source_label) * 40503) % (2 ** 32)
    return (mixed % 1000) / 1000.0


def apply_tipping_cascades():
    """Called once per Advance Round after every region has advanced. A
    source region that started melting this very round may cascade onto
    the next region in the chain."""
    for label, source, target in (("A", region, region_b), ("B", region_b, region_c)):
        if "melt" not in source.round_events:
            continue
        if cascade_roll(label, source.round_number - 1) >= CASCADE_CHANCE:
            continue
        target.temperature += CASCADE_BUMP
        target.counterfactual_temperature += CASCADE_BUMP
        if target.temperature_history:
            target.temperature_history[-1] += CASCADE_BUMP
        target.round_events.append("cascade")


# ===========================================================================
# G3: the permafrost carbon bank. A region that keeps warming acceleration
# under CARBON_BANK_MAX_ACCELERATION while actively protecting its peat
# (at least one Preservation unit) banks one carbon credit per round into a
# shared bank. CARBON_CREDITS_PER_GRANT credits can be spent for a one-time
# CARBON_GRANT_FUNDS grant to any one of Regions A-C: sustained good play in
# one place funds a push somewhere else. Region D never earns or receives.
# ===========================================================================
CARBON_BANK_MAX_ACCELERATION = 1.2
CARBON_CREDITS_PER_GRANT = 10
CARBON_GRANT_FUNDS = 120.0
CARBON_BANK_CAP = 50

carbon_bank = 0


def _carbon_target(key):
    return {"a": region, "b": region_b, "c": region_c}[key]


def bank_carbon_credits():
    """Called once per Advance Round after the regions have advanced.
    Returns how many credits this round added (before the cap)."""
    global carbon_bank
    earned = 0
    for r in (region, region_b, region_c):
        if r.capacity["preserve"] >= 1 and r._investment_acceleration_factor() <= CARBON_BANK_MAX_ACCELERATION:
            earned += 1
    carbon_bank = min(CARBON_BANK_CAP, carbon_bank + earned)
    return earned


def spend_carbon_credits(key):
    """Spends one grant's worth of credits to give region `key` extra funds.
    Returns True if it happened."""
    global carbon_bank
    if key not in ("a", "b", "c") or carbon_bank < CARBON_CREDITS_PER_GRANT:
        return False
    carbon_bank -= CARBON_CREDITS_PER_GRANT
    _carbon_target(key).funds += CARBON_GRANT_FUNDS
    return True


def render_carbon_bank():
    document.getElementById("carbon-bank-display").innerText = (
        f"Carbon bank: {carbon_bank} credit{'s' if carbon_bank != 1 else ''} "
        f"(cap {CARBON_BANK_CAP}). A region earns 1 a round by holding warming under "
        f"{CARBON_BANK_MAX_ACCELERATION}x with Preservation in place; "
        f"{CARBON_CREDITS_PER_GRANT} credits fund a one-time +{CARBON_GRANT_FUNDS:.0f} grant."
    )
    for key in ("a", "b", "c"):
        document.getElementById(f"carbon-bank-{key}-button").disabled = carbon_bank < CARBON_CREDITS_PER_GRANT


def _make_carbon_handler(key):
    def handler(event=None):
        if spend_carbon_credits(key):
            render()
    return handler


# ===========================================================================
# G17: "four regions, one story". A light narrative thread tying the four
# regions together through one shared research station: every Monitoring &
# Response unit funded in Regions A, B or C feeds a common pool of
# observations, and as the pool grows the story advances a chapter. Region D
# (the unmanaged what-if) contributes nothing but is written into the final
# chapter as the control every paper cites. Derived entirely from live
# capacity -- no state of its own, nothing to save -- and it never feeds
# back into any region's mechanics, so the four stay independent.
# ===========================================================================
SHARED_RESEARCH_CHAPTERS = (  # (units needed, title, text), ascending
    (
        0,
        "The shared station",
        "Four regions, one research station. Every Monitoring & Response unit any "
        "region funds adds to a common pool of observations.",
    ),
    (
        3,
        "Chapter 1 \u2014 The network hums",
        "With a few monitors reporting in, the station can line the regions up "
        "side by side: permafrost thaw in one place turns out to rhyme with the others.",
    ),
    (
        8,
        "Chapter 2 \u2014 The joint paper",
        "Enough shared data to publish. The paper shows the same feedback loop at work "
        "in every region, and that early, steady investment blunts it in each one.",
    ),
    (
        15,
        "Chapter 3 \u2014 A shared warning system",
        "The network becomes an early-warning system. Region D, the one region nobody "
        "funded, is the control every paper cites: proof of what the others avoided.",
    ),
)


def shared_research_units():
    """Total Monitoring & Response capacity across the three managed regions."""
    return sum(r.capacity["monitor"] for r in (region, region_b, region_c))


def shared_research_chapters_reached():
    units = shared_research_units()
    return [c for c in SHARED_RESEARCH_CHAPTERS if units >= c[0]]


def render_shared_research():
    units = shared_research_units()
    reached = shared_research_chapters_reached()
    upcoming = [c for c in SHARED_RESEARCH_CHAPTERS if c[0] > units]
    if upcoming:
        progress = f"Shared observations: {units} monitoring units (next chapter at {upcoming[0][0]})."
    else:
        progress = f"Shared observations: {units} monitoring units \u2014 every chapter unlocked."
    document.getElementById("shared-research-progress").innerText = progress
    document.getElementById("shared-research-story").innerHTML = "".join(
        f"<li><strong>{title}</strong> {text}</li>" for _, title, text in reached
    )


# ===========================================================================
# G29: the "global vs. regional" framing toggle. The same three regions and
# the same numbers, reframed: "regional" reads them as the player's own
# region's choices; "global" reads Regions A-C together as one aggregate
# planet. Presentation only -- no mechanic reads it, and Region D (the
# unmanaged what-if) is never part of either summary.
# ===========================================================================
FRAMINGS = ("regional", "global")
framing = "regional"


def framing_summary_text():
    if framing == "global":
        regions = [region, region_b, region_c]
        mean_temp = sum(r.temperature for r in regions) / len(regions)
        mean_saved = sum(r.temperature_saved() for r in regions) / len(regions)
        melting = sum(1 for r in regions if r.is_melting())
        return (
            f"Global picture, Regions A\u2013C together: {deg(mean_temp, plus=True)} average warming, "
            f"{melting} of {len(regions)} regions melting, {deg(mean_saved)} saved on average "
            f"versus no action."
        )
    return (
        f"Your region's choices (Region A): {deg(region.temperature, plus=True)} warming, "
        f"{deg(region.temperature_saved())} saved versus no action."
    )


def _render_framing():
    document.getElementById("framing-toggle-button").innerText = (
        "Framing: global aggregate" if framing == "global" else "Framing: my region's choices"
    )
    document.getElementById("framing-summary").innerText = framing_summary_text()


def on_toggle_framing(event=None):
    global framing
    framing = "global" if framing == "regional" else "regional"
    render()


# ===========================================================================
# G9: the long-game toggle. Only available before any region has played a
# round, since switching mid-run would change the meaning of every number
# already on screen.
# ===========================================================================
def can_toggle_long_game():
    return all(r.round_number == 1 for r in (region, region_b, region_c, region_d))


def set_long_game(enabled):
    global long_game
    if not can_toggle_long_game():
        return False
    if enabled and hold_the_line:
        return False
    long_game = bool(enabled)
    return True


def long_game_text():
    if long_game:
        return (
            f"Long game is on: warming runs at {LONG_GAME_WARMING_SCALE * 100:.0f}% speed and Output pays "
            f"{LONG_GAME_INCOME_SCALE * 100:.0f}% as much, so the full trajectory takes about "
            f"{1 / LONG_GAME_WARMING_SCALE:.1f}x as many rounds."
        )
    return "Standard game. A long game stretches the whole trajectory over roughly two and a half times as many rounds."


def _render_long_game():
    button = document.getElementById("long-game-toggle-button")
    button.innerText = "Long game: on" if long_game else "Long game: off"
    button.disabled = not can_toggle_long_game() or (hold_the_line and not long_game)
    document.getElementById("long-game-display").innerText = long_game_text() + (
        "" if can_toggle_long_game() else " (Locked once the first round has been played.)"
    )


def on_toggle_long_game(event=None):
    set_long_game(not long_game)
    render()


# ===========================================================================
# G27: the "thaw forecast" mini-game. Before advancing, the player may lock
# in a guess of Region A's temperature after the coming round; on advance
# the guess is scored against the real number. Purely cosmetic: a running
# record and a title, no effect on any mechanic. The game is deterministic,
# so a careful player can hit every forecast from the displayed warming
# rate alone -- deliberately, since the point is engaging with that number
# (restoration and rescue make the arithmetic a little less obvious).
# ===========================================================================
FORECAST_TOLERANCE = 0.2
FORECAST_MIN = -100.0
FORECAST_MAX = 1000.0
FORECAST_TITLES = (  # (min attempts, min hit rate, title), best first
    (10, 0.75, "Master Forecaster"),
    (5, 0.5, "Seasoned Forecaster"),
    (1, 0.0, "Apprentice Forecaster"),
)

forecast_guess = None      # the locked-in guess for the coming round, or None
forecast_total = 0         # forecasts ever scored
forecast_hits = 0          # of those, how many landed within FORECAST_TOLERANCE
forecast_last = None       # (guess, actual, hit) from the most recent scoring, transient


def forecast_title():
    if forecast_total <= 0:
        return None
    rate = forecast_hits / forecast_total
    for min_attempts, min_rate, title in FORECAST_TITLES:
        if forecast_total >= min_attempts and rate >= min_rate:
            return title
    return None


def lock_forecast(raw):
    """Parses and stores a guess. Returns True if it was accepted."""
    global forecast_guess
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return False
    if not math.isfinite(value) or not (FORECAST_MIN <= value <= FORECAST_MAX):
        return False
    forecast_guess = value
    return True


def resolve_forecast():
    """Scores a locked-in guess against Region A's temperature now (call
    right after the region has advanced). No guess, no-op."""
    global forecast_guess, forecast_total, forecast_hits, forecast_last
    if forecast_guess is None:
        return
    actual = region.temperature
    hit = abs(actual - forecast_guess) <= FORECAST_TOLERANCE
    forecast_total += 1
    if hit:
        forecast_hits += 1
    forecast_last = (forecast_guess, actual, hit)
    forecast_guess = None


def _render_forecast():
    status = document.getElementById("forecast-status")
    record = document.getElementById("forecast-record")
    if forecast_guess is not None:
        status.innerText = f"Forecast locked in: {deg(forecast_guess, plus=True)} after the next round."
    elif forecast_last is not None:
        guess, actual, hit = forecast_last
        verdict = "Nailed it" if hit else "Not quite"
        status.innerText = (
            f"{verdict} \u2014 you forecast {deg(guess, plus=True)}, the real figure was {deg(actual, plus=True)}."
        )
    else:
        status.innerText = (
            f"Optional: forecast Region A's temperature after the next round "
            f"(within {deg(FORECAST_TOLERANCE)} counts)."
        )
    title = forecast_title()
    if title is None:
        record.innerText = ""
        record.hidden = True
    else:
        record.innerText = f"{title} \u2014 {forecast_hits} of {forecast_total} forecasts on target."
        record.hidden = False
    document.getElementById("forecast-lock-button").innerText = (
        "Change forecast" if forecast_guess is not None else "Lock in forecast"
    )


def on_lock_forecast(event=None):
    """The box is read in the unit chosen in Settings, then stored in the game's own degrees."""
    raw = document.getElementById("forecast-input").value
    try:
        raw = str(float(str(raw).strip()) / (1.8 if temp_unit == "f" else 1.0))
    except (TypeError, ValueError):
        pass  # lock_forecast() rejects it
    if lock_forecast(raw):
        render()


# ===========================================================================
# Achievements (ACHIEVEMENTS-SYSTEM-DESIGN.md) — following SOL's reference
# integration, as also built out for Canopy/Grid/Continuum. Every
# achievement's earned status is a pure function of state that already
# exists elsewhere in this module, recomputed fresh every call — never a
# separately hand-maintained "earned" flag. A handful of achievements
# genuinely needed new tracked state (dampening_at_melt_start on
# RegionState, and the module-level preset_used_ever/
# worst_case_region_revealed flags above) because "was this true at some
# specific past moment" or "has the player ever done X" can't be derived
# from state that only remembers the present.
# ===========================================================================
ACHIEVEMENTS_FILENAME = "achievements.json"


def _read_achievements_json():
    """Same loading contract as SOL's/Grid's `_read_achievements_json()`:
    the boot script fetches achievements.json and hands it to Python as a
    window global before this file runs; the pytest harness's fake `js`
    module has no such attribute, so this falls through to reading the
    file straight off disk, keeping the module importable outside a real
    browser."""
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
# whole import — achievements are additive, not core to Thaw's gameplay.
try:
    ACHIEVEMENTS = json.loads(_read_achievements_json())["achievements"]
except (ValueError, OSError, NameError, KeyError):
    ACHIEVEMENTS = []

EARLY_INVESTOR_MIN_DAMPENING = 0.25
SLOW_BURN_ROUNDS_AFTER_MELT = 15
SLOW_BURN_MAX_ACCELERATION = 1.5
WELL_FUNDED_TARGET = 500
LONG_HAUL_ROUND_TARGET = 25
BEAT_BOTH_REGIONS_MIN_ROUND = 15


def _all_categories_invested():
    return all(region.capacity[c] >= 1 for c in CATEGORIES)


def _invested_count():
    return sum(1 for c in CATEGORIES if region.capacity[c] >= 1)


def _both_secondary_regions_invested():
    return sum(region_b.capacity.values()) >= 1 and sum(region_c.capacity.values()) >= 1


# Each checker is a zero-argument predicate read fresh off live state —
# nothing here is ever cached or hand-flagged.
ACHIEVEMENT_CHECKS = {
    "first_output": lambda: region.capacity["output"] >= 1,
    "first_intervention": lambda: region.capacity["preserve"] >= 1 or region.capacity["monitor"] >= 1,
    "triple_threat": _all_categories_invested,
    "quarter_dampening": lambda: region.feedback_dampening_fraction() >= 0.25,
    "half_dampening": lambda: region.feedback_dampening_fraction() >= 0.5,
    "max_dampening": lambda: region.feedback_dampening_fraction() >= MAX_FEEDBACK_DAMPENING - 1e-9,
    "tipping_point_witnessed": lambda: region.melt_started_round is not None,
    "early_investor": lambda: (
        region.dampening_at_melt_start is not None
        and region.dampening_at_melt_start >= EARLY_INVESTOR_MIN_DAMPENING
    ),
    "degree_saved_5": lambda: region.temperature_saved() >= 5,
    "degree_saved_10": lambda: region.temperature_saved() >= 10,
    "degree_saved_20": lambda: region.temperature_saved() >= 20,
    "slow_burn": lambda: (
        region.melt_started_round is not None
        and (region.round_number - region.melt_started_round) >= SLOW_BURN_ROUNDS_AFTER_MELT
        and region.acceleration_factor() < SLOW_BURN_MAX_ACCELERATION
    ),
    "well_funded": lambda: region.funds >= WELL_FUNDED_TARGET,
    "long_haul": lambda: region.round_number >= LONG_HAUL_ROUND_TARGET,
    "beat_both_regions": lambda: (
        region.round_number >= BEAT_BOTH_REGIONS_MIN_ROUND
        and region.temperature < region_b.temperature
        and region.temperature < region_c.temperature
    ),
    "comparison_engaged": _both_secondary_regions_invested,
    "preset_strategist": lambda: preset_used_ever,
    "worst_case_witnessed": lambda: worst_case_region_revealed,
}

# Progress readouts, only for achievements with a genuine numeric scale-up
# — a one-shot milestone (e.g. "witness the tipping point") gets no
# progress row at all, the honest shape for it per the design doc.
ACHIEVEMENT_PROGRESS = {
    "triple_threat": lambda: (_invested_count(), len(CATEGORIES)),
    "quarter_dampening": lambda: (min(100, round(region.feedback_dampening_fraction() * 100)), 25),
    "half_dampening": lambda: (min(100, round(region.feedback_dampening_fraction() * 100)), 50),
    "max_dampening": lambda: (
        min(100, round(region.feedback_dampening_fraction() * 100)),
        round(MAX_FEEDBACK_DAMPENING * 100),
    ),
    "degree_saved_5": lambda: (max(0, min(5, round(region.temperature_saved()))), 5),
    "degree_saved_10": lambda: (max(0, min(10, round(region.temperature_saved()))), 10),
    "degree_saved_20": lambda: (max(0, min(20, round(region.temperature_saved()))), 20),
    "well_funded": lambda: (max(0, min(WELL_FUNDED_TARGET, round(region.funds))), WELL_FUNDED_TARGET),
    "long_haul": lambda: (min(region.round_number, LONG_HAUL_ROUND_TARGET), LONG_HAUL_ROUND_TARGET),
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

    # A link out to the hub-wide achievements dashboard
    # (ACHIEVEMENTS-SYSTEM-DESIGN.md §5), same convention as every other
    # game's reference retrofit. Relative path, no leading "/" (site-level
    # milestone 7's GitHub Pages subpath fix). The hub-side script.js
    # registration that makes Thaw's save data actually show up on that
    # dashboard is a root-file change, out of scope for this
    # games/thaw/-only dispatch.
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


# Unlock toast (TODO.md "roll achievements out everywhere" — required on
# top of the base per-game rollout). Same pattern as every other game's
# reference retrofit: a snapshot of which ids were already earned as of
# the last seed point, so a fresh load or a loaded save doesn't flood the
# player with toasts for achievements it already satisfies.
_achievements_seen_ids = set()


def _seed_achievement_toast_baseline():
    global _achievements_seen_ids
    _achievements_seen_ids = set(achievement_ids_earned())


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
    (invest/preset/advance round/reveal worst-case region) — never from
    render() itself, since load_state() also calls render() and a loaded
    save with several achievements already earned must not flood the
    player with toasts for all of them at once."""
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


# G19: a per-browser "best run" — the highest temperature_saved()
# (the hope-angle payoff stat, per CLAUDE.md) any session on this device
# has ever reached, persisted via localStorage. Deliberately NOT part of
# get_state()/the save-code system — this tracks the best this *browser*
# has ever seen across every session/save on this device, not one save's
# snapshot, the same distinction Canopy's B14/Tide's D13 personal-best
# features already draw.
PERSONAL_BEST_STORAGE_KEY = "thaw_personal_best_v1"

# Z6 (planning/TODO.md "Z. Games"): duration of the shared
# .personal-best-display.just-improved pulse (shared/personal-best.css) --
# matches the CSS animation's own length so the class is gone right as
# the pulse finishes. Same value Canopy uses for the same reason.
PERSONAL_BEST_BADGE_MS = 1800


def _read_local_storage_item(key):
    """Lazy `import js` (same convention as _read_achievements_json()) so
    this file stays importable outside a real browser. Broad except on
    the actual read/write below is deliberate: a real browser can refuse
    localStorage access entirely (private-browsing mode in some
    browsers), surfaced as a JS exception with no stable Python type to
    catch narrowly — this feature is a nice-to-have, not core gameplay,
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
    """Reads the stored best temperature_saved(), defaulting to 0.0 if
    nothing is stored yet, storage is unavailable, or the stored value is
    malformed (e.g. hand-edited or from a future incompatible format)."""
    raw = _read_local_storage_item(PERSONAL_BEST_STORAGE_KEY)
    if not raw:
        return {"temperature_saved": 0.0, "region": None}
    try:
        data = json.loads(raw)
        region_label = data.get("region")
        if region_label not in ("A", "B", "C"):
            region_label = None
        return {
            "temperature_saved": float(data.get("temperature_saved", 0.0)),
            "region": region_label,
        }
    except (ValueError, TypeError, AttributeError):
        return {"temperature_saved": 0.0, "region": None}


personal_best = load_personal_best()


def _maybe_update_personal_best():
    """Called every render(); bumps + persists personal_best whenever the
    live session exceeds it."""
    # G22: consider all three player-managed regions and remember which
    # one earned the record.
    label, saved = max(
        (("A", region.temperature_saved()), ("B", region_b.temperature_saved()),
         ("C", region_c.temperature_saved())),
        key=lambda pair: pair[1],
    )
    if saved > personal_best["temperature_saved"]:
        personal_best["temperature_saved"] = saved
        personal_best["region"] = label
        _write_local_storage_item(PERSONAL_BEST_STORAGE_KEY, json.dumps(personal_best))
        _flash_personal_best_badge()


def _flash_personal_best_badge():
    """Z6: briefly adds the shared .just-improved class (see
    shared/personal-best.css) right when a session beats its stored best.
    Same setTimeout+create_proxy shape as this game's other one-shot UI
    cues (e.g. the achievement toast)."""
    element = document.getElementById("personal-best-display")
    if element is None:
        return
    element.classList.add("just-improved")

    def _unflash():
        el = document.getElementById("personal-best-display")
        if el is not None:
            el.classList.remove("just-improved")

    setTimeout(create_proxy(_unflash), PERSONAL_BEST_BADGE_MS)


def render_personal_best():
    element = document.getElementById("personal-best-display")
    if element is None:
        return
    text = f"Personal best: {deg(personal_best['temperature_saved'])} saved"
    if personal_best.get("region"):
        text += f" (Region {personal_best['region']})"
    element.innerText = text


# ===========================================================================
# G23: the climate archive -- a persistent, per-browser record across many
# sessions of each player-managed region's best-ever performance (the most
# degrees saved, the furthest round reached, the highest dampening built).
# Same storage rules as personal_best above (localStorage, never part of
# get_state()/the save code, every read validated), but per region rather
# than one overall best. Region D is the unmanaged baseline and has no
# archive entry.
# ===========================================================================
ARCHIVE_STORAGE_KEY = "thaw_climate_archive_v1"
ARCHIVE_REGIONS = ("A", "B", "C")
ARCHIVE_MAX_ROUND = 1000000


def _blank_archive_entry():
    return {"best_saved": 0.0, "furthest_round": 1, "peak_dampening": 0.0}


def _clean_archive_entry(raw):
    """One region's stored record, with every field forced back into range
    (a malformed or hand-edited value falls back to that field's default)."""
    entry = _blank_archive_entry()
    if not isinstance(raw, dict):
        return entry
    saved = raw.get("best_saved")
    if isinstance(saved, (int, float)) and not isinstance(saved, bool) and math.isfinite(saved) and saved >= 0:
        entry["best_saved"] = float(saved)
    rounds = raw.get("furthest_round")
    if isinstance(rounds, int) and not isinstance(rounds, bool) and 1 <= rounds <= ARCHIVE_MAX_ROUND:
        entry["furthest_round"] = rounds
    damp = raw.get("peak_dampening")
    if (
        isinstance(damp, (int, float)) and not isinstance(damp, bool)
        and math.isfinite(damp) and 0 <= damp <= 1
    ):
        entry["peak_dampening"] = float(damp)
    return entry


def load_climate_archive():
    archive = {label: _blank_archive_entry() for label in ARCHIVE_REGIONS}
    raw = _read_local_storage_item(ARCHIVE_STORAGE_KEY)
    if not raw:
        return archive
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return archive
    if isinstance(data, dict):
        for label in ARCHIVE_REGIONS:
            archive[label] = _clean_archive_entry(data.get(label))
    return archive


climate_archive = load_climate_archive()
archive_open = False


def _maybe_update_climate_archive():
    """Called every render(); raises and persists any record the live
    session has beaten."""
    changed = False
    for label, r in (("A", region), ("B", region_b), ("C", region_c)):
        entry = climate_archive[label]
        saved = max(0.0, r.temperature_saved())
        if saved > entry["best_saved"]:
            entry["best_saved"] = saved
            changed = True
        if r.round_number > entry["furthest_round"]:
            entry["furthest_round"] = min(r.round_number, ARCHIVE_MAX_ROUND)
            changed = True
        damp = r.feedback_dampening_fraction()
        if damp > entry["peak_dampening"]:
            entry["peak_dampening"] = damp
            changed = True
    if changed:
        _write_local_storage_item(ARCHIVE_STORAGE_KEY, json.dumps(climate_archive))


def render_climate_archive():
    toggle = document.getElementById("archive-toggle-button")
    panel = document.getElementById("archive-panel")
    toggle.innerText = "Hide climate archive" if archive_open else "\U0001F5C4\uFE0F Climate archive"
    panel.hidden = not archive_open
    for label in ARCHIVE_REGIONS:
        entry = climate_archive[label]
        document.getElementById(f"archive-row-{label.lower()}").innerText = (
            f"Region {label} \u2014 best {deg(entry['best_saved'])} saved, "
            f"furthest round {entry['furthest_round']}, "
            f"peak dampening {entry['peak_dampening'] * 100:.0f}%"
        )


def on_toggle_archive(event=None):
    global archive_open
    archive_open = not archive_open
    render_climate_archive()


# ===========================================================================
# K16 (planning/TODO.md "What's New" changelog, site-wide goal): a small
# in-game "what's new" panel, same shape as the achievements catalog above
# -- a flat JSON list fetched into the Pyodide boot sequence and handed to
# Python as a window global (see index.html), rendered into a
# hidden-until-opened panel. Unlike achievements.json this catalog isn't a
# set of checkable conditions -- it's just curated highlight text -- so
# there's no earned/unearned state, only a newest-first list.
# ===========================================================================
CHANGELOG_FILENAME = "changelog.json"


def _read_changelog_json():
    """Same loading contract as _read_achievements_json(): the boot script
    fetches changelog.json and hands it to Python as a window global before
    this file runs; the pytest harness's fake `js` module has no such
    attribute, so this falls through to reading the file straight off disk,
    keeping the module importable outside a real browser."""
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


# Degrades to "no changelog" rather than crashing this module's whole
# import -- same defensive shape as ACHIEVEMENTS above, since a "what's
# new" panel is additive, not core to Thaw's gameplay.
try:
    CHANGELOG = sorted(json.loads(_read_changelog_json()), key=lambda entry: entry["date"], reverse=True)
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
    toggle.innerText = "Hide What's New" if changelog_open else f"\U0001f4cb What's New ({len(CHANGELOG)})"
    panel.hidden = not changelog_open
    if not changelog_open:
        return

    panel.innerHTML = ""
    if not CHANGELOG:
        empty = document.createElement("p")
        empty.innerText = "Nothing logged yet."
        panel.appendChild(empty)
        return

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
# G11 -- community "average acceleration factor" comparison
# (planning/TODO.md, needs Z1). Follows Grid's C15 architecture exactly
# (games/grid/game.py/index.html): a Python-side optional JS hook call,
# guarded so it's a safe no-op outside a real browser (the pytest fake-DOM
# harness's `js` module never provides `window` by default), and the real
# fetch()/percentile-phrasing lives entirely in index.html's own inline
# <script>. Region A only -- this game's Pass 3 note already scoped the
# primary intervention lever to Region A, not the B/C comparison regions
# or D's auto-played worst case, and that same scoping applies here.
#
# "region.average_acceleration_factor" is registered in app/stats.py's
# per-game STATS_FIELDS whitelist for "thaw" (added alongside this
# feature), so GET /stats/games/thaw/percentile?field=region.average_
# acceleration_factor is live once the backend is deployed with it.
# ===========================================================================
COMMUNITY_COMPARE_FALLBACK = "Community comparison isn't available yet."

community_compare_open = False


def on_toggle_community_compare(event=None):
    global community_compare_open
    community_compare_open = not community_compare_open
    update_community_compare_panel()


def update_community_compare_panel():
    toggle = document.getElementById("community-compare-toggle-button")
    panel = document.getElementById("community-compare-panel")
    toggle.innerText = (
        "Hide Community Comparison" if community_compare_open else "\U0001F30D Community Comparison"
    )
    panel.hidden = not community_compare_open
    if not community_compare_open:
        return
    panel.innerHTML = (
        f'<p id="community-compare-display" class="comparison-message">{COMMUNITY_COMPARE_FALLBACK}</p>'
    )
    _request_community_comparison()


def _request_community_comparison():
    """G11: asks the page's optional JS hook (window.thawCompare, see
    index.html) to fill #community-compare-display with a cross-player
    percentile of average_acceleration_factor. Absent hook (pytest, or a
    page without it) leaves the fallback text in place -- mirrors Grid's
    _request_comparison() exactly."""
    try:
        from js import window  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
    except ImportError:
        return
    hook = getattr(window, "thawCompare", None)
    if hook is not None:
        hook(float(region.average_acceleration_factor))


# G7: an optional "deeper data view" -- real published atmospheric methane
# data shown ALONGSIDE the in-game graph, not overlaid onto it (Thaw's
# rounds have no real calendar-time axis to align against a real dataset
# without implying false precision). Source: NOAA Global Monitoring
# Laboratory, "Trends in Atmospheric Methane (CH4)"
# (https://gml.noaa.gov/ccgg/trends_ch4/, accessed 2026-09-26, page's own
# "Last updated: Sep 05, 2026") -- the real annual increase in globally-
# averaged atmospheric methane, continuously measured since 1983. This is
# the TOTAL real-world growth rate (agriculture, wetlands, fossil-fuel
# leaks, and permafrost all contribute); it is not a permafrost-only
# figure, and the panel says so plainly rather than implying a 1:1 match
# with this game's own feedback-loop mechanic.
REAL_METHANE_GROWTH_PPB_PER_YEAR = [
    (1984, 12.89), (1985, 12.18), (1986, 12.90), (1987, 11.43), (1988, 10.74),
    (1989, 11.12), (1990, 8.71), (1991, 13.99), (1992, 2.43), (1993, 3.85),
    (1994, 7.30), (1995, 3.82), (1996, 2.47), (1997, 6.36), (1998, 12.13),
    (1999, 2.25), (2000, -1.34), (2001, -0.66), (2002, 3.17), (2003, 4.84),
    (2004, -4.72), (2005, 0.21), (2006, 1.85), (2007, 7.85), (2008, 6.52),
    (2009, 4.77), (2010, 5.03), (2011, 5.02), (2012, 5.01), (2013, 5.70),
    (2014, 12.69), (2015, 10.03), (2016, 7.13), (2017, 6.83), (2018, 8.72),
    (2019, 9.64), (2020, 14.78), (2021, 17.70), (2022, 13.01), (2023, 8.32),
    (2024, 7.91), (2025, 5.14),
]

CLIMATE_SCIENTIST_SOURCE_URL = "https://gml.noaa.gov/ccgg/trends_ch4/"
CLIMATE_SCIENTIST_FRAMING = (
    "Real-world atmospheric methane has been measured continuously since 1983 "
    "(NOAA's Global Monitoring Laboratory). The chart below is the real annual "
    "growth rate — how much the global average rose that year, in parts "
    "per billion. This is the TOTAL real-world increase from every source "
    "combined (agriculture, wetlands, fossil-fuel leaks, and permafrost thaw "
    "all contribute) — it is not a permafrost-only figure, and Thaw's own "
    "feedback-loop mechanic is a simplified stand-in for one piece of this "
    "larger, real picture, not a literal model of it. Notice the recent run: "
    "2020-2022 saw the three highest annual increases on record."
)

METHANE_CHART_WIDTH = 320
METHANE_CHART_HEIGHT = 90
METHANE_CHART_BASELINE_YEARS = 30  # 1984-2013, before the recent acceleration


def real_methane_growth_chart_svg():
    """A labeled real-data line chart -- deliberately a bigger, more
    legible sibling of mini_temp_graph_svg above (this one is meant to be
    read, not just glanced at for shape): year tick labels plus a dashed
    reference line at the pre-acceleration baseline average, so the
    recent run reads clearly against its own real historical range."""
    years = [y for y, _ in REAL_METHANE_GROWTH_PPB_PER_YEAR]
    values = [v for _, v in REAL_METHANE_GROWTH_PPB_PER_YEAR]
    n = len(values)
    lo, hi = min(values), max(values)
    span = hi - lo if hi - lo > 1e-9 else 1.0
    pad_top, pad_bottom = 10, 16
    plot_h = METHANE_CHART_HEIGHT - pad_top - pad_bottom
    xs = [i * (METHANE_CHART_WIDTH / (n - 1)) for i in range(n)]
    ys = [pad_top + plot_h - ((v - lo) / span) * plot_h for v in values]
    points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))

    baseline = sum(values[:METHANE_CHART_BASELINE_YEARS]) / METHANE_CHART_BASELINE_YEARS
    baseline_y = pad_top + plot_h - ((baseline - lo) / span) * plot_h

    # The first/last ticks sit right at the SVG's own edges, so a centered
    # anchor there would clip half the label outside the viewBox -- anchor
    # those two to their own inside edge instead, interior ticks stay
    # centered on their point.
    tick_indices = sorted({0, 10, 20, 30, n - 1})
    ticks = []
    for i in tick_indices:
        if i == 0:
            anchor = "start"
        elif i == n - 1:
            anchor = "end"
        else:
            anchor = "middle"
        ticks.append(
            f'<text x="{xs[i]:.1f}" y="{METHANE_CHART_HEIGHT - 2}" '
            f'style="text-anchor:{anchor}" class="methane-chart-tick">{years[i]}</text>'
        )
    ticks = "".join(ticks)

    return (
        f'<svg viewBox="0 0 {METHANE_CHART_WIDTH} {METHANE_CHART_HEIGHT}" class="methane-chart-svg" '
        f'role="img" aria-label="Real annual growth in atmospheric methane, '
        f'1984 to 2025, in parts per billion per year">'
        f'<line x1="0" y1="{baseline_y:.1f}" x2="{METHANE_CHART_WIDTH}" y2="{baseline_y:.1f}" '
        f'class="methane-chart-baseline" />'
        f'<text x="2" y="{max(baseline_y - 2, 9):.1f}" class="methane-chart-baseline-label">'
        f"1984–2013 average</text>"
        f'<polyline points="{points}" class="methane-chart-line" />'
        f"{ticks}"
        f"</svg>"
    )


climate_scientist_open = False


def on_toggle_climate_scientist(event=None):
    global climate_scientist_open
    climate_scientist_open = not climate_scientist_open
    render_climate_scientist()


def render_climate_scientist():
    toggle = document.getElementById("climate-scientist-toggle-button")
    panel = document.getElementById("climate-scientist-panel")
    toggle.innerText = (
        "Hide Climate Scientist" if climate_scientist_open else "\U0001F52C Climate Scientist"
    )
    panel.hidden = not climate_scientist_open
    if not climate_scientist_open:
        return
    panel.innerHTML = (
        f'<p class="climate-scientist-framing">{CLIMATE_SCIENTIST_FRAMING}</p>'
        f"{real_methane_growth_chart_svg()}"
        f'<p class="climate-scientist-source">Source: '
        f'<a href="{CLIMATE_SCIENTIST_SOURCE_URL}" target="_blank" rel="noopener">'
        f"NOAA Global Monitoring Laboratory, Trends in Atmospheric Methane</a>.</p>"
    )


# ===========================================================================
# GG-5: resource routing. A convoy moves a fixed parcel of funds from one
# managed region (A, B or C) to another, minus a transport tax, so the player
# triages between rescuing a stricken region and feeding a healthy one. Region
# D never takes part (it is the untouched baseline). The tax is the whole
# price: nothing is random and nothing is hidden. The visible stat is the
# convoy count and the funds the tax has swallowed.
# ===========================================================================
ROUTING_CONVOY_FUNDS = 50.0
ROUTING_TAX = 0.2
ROUTING_KEYS = ("a", "b", "c")

convoys_sent = 0
convoy_tax_lost = 0.0


def _routing_region(key):
    return {"a": region, "b": region_b, "c": region_c}[key]


def can_route_funds(src_key, dst_key):
    return (
        src_key in ROUTING_KEYS
        and dst_key in ROUTING_KEYS
        and src_key != dst_key
        and _routing_region(src_key).funds >= ROUTING_CONVOY_FUNDS
    )


def route_funds(src_key, dst_key):
    """Sends one convoy. Returns True if it happened."""
    global convoys_sent, convoy_tax_lost
    if not can_route_funds(src_key, dst_key):
        return False
    tax = ROUTING_CONVOY_FUNDS * ROUTING_TAX
    _routing_region(src_key).funds -= ROUTING_CONVOY_FUNDS
    _routing_region(dst_key).funds += ROUTING_CONVOY_FUNDS - tax
    convoys_sent += 1
    convoy_tax_lost += tax
    return True


def _routing_selection():
    src = document.getElementById("routing-source").value
    dst = document.getElementById("routing-dest").value
    return (src if src in ROUTING_KEYS else "a", dst if dst in ROUTING_KEYS else "b")


def routing_preview_text(src_key, dst_key):
    if src_key == dst_key:
        return "Pick two different regions."
    received = ROUTING_CONVOY_FUNDS * (1 - ROUTING_TAX)
    text = (
        f"A convoy takes {ROUTING_CONVOY_FUNDS:.0f} funds from Region {src_key.upper()} and delivers "
        f"{received:.0f} to Region {dst_key.upper()} ({ROUTING_TAX * 100:.0f}% transport tax)."
    )
    if _routing_region(src_key).funds < ROUTING_CONVOY_FUNDS:
        text += f" Region {src_key.upper()} has only {_routing_region(src_key).funds:.0f} funds."
    return text


def render_routing():
    src, dst = _routing_selection()
    document.getElementById("routing-send-button").disabled = not can_route_funds(src, dst)
    document.getElementById("routing-send-button").innerText = (
        f"Send convoy: {src.upper()} → {dst.upper()}"
    )
    document.getElementById("routing-preview").innerText = routing_preview_text(src, dst)
    document.getElementById("routing-display").innerText = (
        f"Convoys sent: {convoys_sent}. Funds lost to the transport tax: {convoy_tax_lost:.0f}."
    )


def on_routing_change(event=None):
    render()


def on_send_convoy(event=None):
    src, dst = _routing_selection()
    if route_funds(src, dst):
        render()


# ===========================================================================
# GG-27: the perfect-balance bonus. When all three managed regions are
# melting and end a round within BALANCE_TOLERANCE degrees of each other, each
# gets BALANCE_BONUS_FUNDS and the comparison card pulses. It is only offered
# once every region is melting, because before melt all three regions climb at
# the same background rate whatever you do (so "balance" would be free).
# ===========================================================================
BALANCE_TOLERANCE = 1.0
BALANCE_BONUS_FUNDS = 20.0

balance_bonuses = 0
just_balanced = False


def regions_balanced():
    managed = (region, region_b, region_c)
    if not all(r.is_melting() for r in managed):
        return False
    temps = [r.temperature for r in managed]
    return max(temps) - min(temps) <= BALANCE_TOLERANCE


def apply_balance_bonus():
    """Called once per Advance Round after every region has advanced."""
    global balance_bonuses, just_balanced
    if not regions_balanced():
        return False
    for r in (region, region_b, region_c):
        r.funds += BALANCE_BONUS_FUNDS
    balance_bonuses += 1
    just_balanced = True
    science_log.append({
        "region": "ABC",
        "round": region.round_number - 1,
        "text": (
            f"all three regions finished within {deg(BALANCE_TOLERANCE)} of each other: "
            f"a perfect-balance bonus of +{BALANCE_BONUS_FUNDS:.0f} funds each."
        ),
    })
    return True


def render_balance():
    global just_balanced
    document.getElementById("balance-display").innerText = (
        f"Perfect-balance bonuses: {balance_bonuses}. When all three regions are melting and end a "
        f"round within {deg(BALANCE_TOLERANCE, 0)} of each other, each gets +{BALANCE_BONUS_FUNDS:.0f} funds."
    )
    callout = document.getElementById("balance-callout")
    card = document.getElementById("region-comparison")
    if just_balanced:
        callout.innerText = (
            f"Perfect balance: all three regions finished within {deg(BALANCE_TOLERANCE, 0)} of each "
            f"other. +{BALANCE_BONUS_FUNDS:.0f} funds each."
        )
        callout.hidden = False
        card.className = "section region-comparison balance-pulse"
        just_balanced = False
    else:
        callout.hidden = True
        card.className = "section region-comparison"


# ===========================================================================
# GG-13: the Ice Age streak medal for Region A: rounds without a tipping
# event, grown into a frostier medal at 5, 10 and 15.
# ===========================================================================
def ice_age_tier(streak):
    """The (needed, name, icon) of the highest tier `streak` reaches, or None."""
    earned = None
    for tier in ICE_AGE_TIERS:
        if streak >= tier[0]:
            earned = tier
    return earned


def ice_age_text(r):
    streak = r.rounds_since_tipping_event
    best = r.best_stable_streak
    tier = ice_age_tier(streak)
    best_tier = ice_age_tier(best)
    nxt = next((t for t in ICE_AGE_TIERS if streak < t[0]), None)
    if tier is not None:
        head = f"{tier[2]} {tier[1]} medal: {streak} rounds without a tipping event."
    elif best_tier is not None:
        head = f"No medal right now ({streak} rounds since a tipping event). Best so far: {best_tier[2]} {best_tier[1]}."
    else:
        head = f"No medal yet: {streak} rounds without a tipping event."
    if nxt is not None:
        head += f" Next: {nxt[2]} {nxt[1]} at {nxt[0]}."
    else:
        head += " The top medal."
    if best > streak and tier is not None:
        head += f" Best run: {best}."
    return head


# ===========================================================================
# G-24: acceleration sparkline, and G-10: summary sentences for the graphs.
# ===========================================================================
SPARK_WIDTH = 100
SPARK_HEIGHT = 20


def accel_sparkline_text(history):
    if len(history) < 2:
        return "Acceleration history appears after the second round."
    first, last = history[0], history[-1]
    if last > first + 0.05:
        direction = "rising"
    elif last < first - 0.05:
        direction = "falling"
    else:
        direction = "steady"
    return (
        f"Acceleration over the last {len(history)} rounds: from {first:.1f}x to {last:.1f}x, "
        f"{direction}; peak {max(history):.1f}x."
    )


def accel_sparkline_svg(history):
    if len(history) < 2:
        return ""
    lo, hi = min(1.0, min(history)), max(history)
    span = max(hi - lo, 0.25)
    n = len(history)
    ys = [SPARK_HEIGHT - ((v - lo) / span) * (SPARK_HEIGHT - 2) - 1 for v in history]
    xs = [i * (SPARK_WIDTH / (n - 1)) for i in range(n)]
    points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    base_y = SPARK_HEIGHT - ((1.0 - lo) / span) * (SPARK_HEIGHT - 2) - 1
    label = accel_sparkline_text(history)
    return (
        f'<svg viewBox="0 0 {SPARK_WIDTH} {SPARK_HEIGHT}" preserveAspectRatio="none" class="accel-sparkline-svg" role="img" '
        f'aria-label="{label}"><title>{label}</title>'
        f'<line x1="0" y1="{base_y:.1f}" x2="{SPARK_WIDTH}" y2="{base_y:.1f}" class="accel-sparkline-base" />'
        f'<polyline points="{points}" class="accel-sparkline-line" />'
        f"</svg>"
    )


def _degrees_word(value, digits=1):
    """Spoken form of a rise in the chosen unit ('+5.0 degrees' in Celsius)."""
    if temp_unit == "f":
        return f"+{value * 1.8:.{digits}f} degrees Fahrenheit"
    if temp_unit == "k":
        return f"+{value:.{digits}f} kelvin"
    return f"+{value:.{digits}f} degrees"


def graph_summary_text(name, history):
    """G-10: one plain sentence describing a mini-graph for a screen reader."""
    if len(history) < 2:
        return f"{name} temperature graph: not enough rounds yet."
    first, last = history[0], history[-1]
    threshold = _degrees_word(MELT_THRESHOLD, 0).replace(" degrees", " degree")
    crossed = (
        f"crossed the {threshold} melt threshold"
        if max(history) >= MELT_THRESHOLD
        else f"still under the {threshold} melt threshold"
    )
    return (
        f"{name} temperature over {len(history)} rounds: from {_degrees_word(first)} to "
        f"{_degrees_word(last)}, {crossed}."
    )


def round_announcement():
    """G-10: the sentence an aria-live region reads after each Advance Round."""
    parts = [f"Round {region.round_number}."]
    for label, r in (("A", region), ("B", region_b), ("C", region_c)):
        parts.append(f"Region {label} +{r.temperature:.1f} degrees, {_melt_status_label(r)}.")
    for label, r in (("A", region), ("B", region_b), ("C", region_c)):
        if "melt" in r.round_events:
            parts.append(f"Region {label} started melting.")
        if "critical" in r.round_events:
            parts.append(f"Region {label} went critical.")
    if just_balanced:
        parts.append("Perfect balance bonus earned.")
    if just_escalated and hold_the_line:
        parts.append(f"Escalation: {escalation_event_name(just_escalated)}.")
    if run_over:
        parts.append(f"The run is over after {run_result['survived']} rounds held.")
    return " ".join(parts)


# ===========================================================================
# G-4: "explain this number". A breakdown of one region's current warming rate
# into the background rise, the raw methane feedback, and what each lever takes
# off it.
# ===========================================================================
def rate_breakdown(r):
    """Returns a dict: base, raw_feedback, preserve/monitor/stance/rescue (each
    the part of raw_feedback that lever removes), net_feedback and total. The
    investment dampening is split between its sources in proportion to their
    uncapped contributions (the 85% cap is applied to the total)."""
    base = r.base_rise()
    excess = max(0.0, r.temperature - MELT_THRESHOLD)
    raw = excess * FEEDBACK_RATE_PER_DEGREE_OVER * warming_scale()
    invest_fraction = r.feedback_dampening_fraction()
    uncapped = {
        "preserve": r.capacity["preserve"] * DAMPENING_PER_PRESERVE_UNIT,
        "monitor": r.capacity["monitor"] * DAMPENING_PER_MONITOR_UNIT,
        "stance": r.policy_dampening,
    }
    total_uncapped = sum(uncapped.values())
    removed = {}
    for key, value in uncapped.items():
        share = (value / total_uncapped) if total_uncapped > 0 else 0.0
        removed[key] = raw * invest_fraction * share
    removed["rescue"] = raw * (r.effective_dampening_fraction() - invest_fraction)
    net = raw - sum(removed.values())
    return {
        "base": base, "raw_feedback": raw, "net_feedback": net,
        "preserve": removed["preserve"], "monitor": removed["monitor"],
        "stance": removed["stance"], "rescue": removed["rescue"],
        "total": base + net, "acceleration": (base + net) / base,
    }


def rate_breakdown_rows(b):
    rows = [
        ("Background rise (fixed)", b["base"], ""),
        ("Methane feedback before any lever", b["raw_feedback"], "+"),
    ]
    for key, label in (
        ("preserve", "Permafrost Preservation takes off"),
        ("monitor", "Monitoring & Response takes off"),
        ("stance", "Policy stance takes off"),
        ("rescue", "Emergency rescue takes off"),
    ):
        if b[key] > 0.0005:
            rows.append((label, b[key], "-"))
    rows.append(("Warming rate this round", b["total"], "="))
    return rows


def rate_breakdown_svg(b):
    """A stacked bar: background (solid), feedback that still lands, and the
    feedback the levers removed (outlined). Numbers in the list carry the
    meaning; the bar is only a shape cue."""
    whole = b["base"] + b["raw_feedback"]
    if whole <= 0:
        return ""
    base_w = 100 * b["base"] / whole
    net_w = 100 * b["net_feedback"] / whole
    cut_w = max(0.0, 100 - base_w - net_w)
    label = (
        f"Of {whole:.2f} degrees a round before any lever, {b['base']:.2f} is the fixed background, "
        f"{b['net_feedback']:.2f} is feedback that still lands and {whole - b['base'] - b['net_feedback']:.2f} "
        f"was removed by your levers."
    )
    return (
        f'<svg viewBox="0 0 100 8" class="rate-breakdown-svg" role="img" aria-label="{label}"><title>{label}</title>'
        f'<rect x="0" y="0" width="{base_w:.1f}" height="8" class="rate-seg-base" />'
        f'<rect x="{base_w:.1f}" y="0" width="{net_w:.1f}" height="8" class="rate-seg-net" />'
        f'<rect x="{base_w + net_w:.1f}" y="0.5" width="{max(cut_w - 0.5, 0):.1f}" height="7" class="rate-seg-cut" />'
        f"</svg>"
    )


def _inspector_region():
    key = document.getElementById("rate-inspector-region").value
    return {"a": region, "b": region_b, "c": region_c}.get(key, region), (key if key in ("a", "b", "c") else "a")


def render_rate_inspector():
    r, key = _inspector_region()
    b = rate_breakdown(r)
    rows = "".join(
        f'<li class="rate-row rate-row--{sign or "base"}"><span>{label}</span>'
        f"<span>{sign} {deg(value, 2)}</span></li>"
        for label, value, sign in rate_breakdown_rows(b)
    )
    document.getElementById("rate-inspector-body").innerHTML = (
        f"{rate_breakdown_svg(b)}<ul class=\"rate-rows\">{rows}</ul>"
        f'<p class="comparison-message">Region {key.upper()}: acceleration is this rate divided by the '
        f'background rise ({deg(b["base"], 2)}), so {b["total"]:.2f} / {b["base"]:.2f} = '
        f'{b["acceleration"]:.2f}x.</p>'
    )


def on_rate_inspector_region_change(event=None):
    render_rate_inspector()


# ===========================================================================
# GG-28: a three-line highlights recap, built from the regions' own records
# (when each tipped, what recovered, what the levers saved) so it stays right
# after the 40-entry scientist's log has scrolled.
# ===========================================================================
def highlights_lines():
    managed = (("A", region), ("B", region_b), ("C", region_c))
    tipped = [f"Region {label} tipped in round {r.melt_started_round}" for label, r in managed
              if r.melt_started_round is not None]
    line1 = ("; ".join(tipped) + ".") if tipped else "No region has tipped into melt yet."
    restored = [(label, r) for label, r in managed if r.restored_total > 0]
    rescued = [label for label, r in managed if r.rescue_used]
    if restored:
        total = sum(r.restored_total for _label, r in restored)
        names = ", ".join(label for label, _r in restored)
        line2 = f"Recovery: restoration pulled back {deg(total)} of melt-driven warming in Region {names}."
    elif rescued:
        line2 = f"Recovery: Region {', '.join(rescued)} used its one emergency rescue."
    else:
        line2 = "Recovery: no region has needed (or earned) one yet."
    saved = ", ".join(f"{label} {deg(r.temperature_saved())}" for label, r in managed)
    line3 = (
        f"Degrees saved versus no action: {saved}. {best_region_message()}"
    )
    return [line1, line2, line3]


def highlights_text():
    return f"Thaw highlights (round {region.round_number}): " + " ".join(highlights_lines())


def share_result():
    """Z-20: the headline numbers for the shared "Copy result" button, as a JSON string the page
    reads (the page calls this by name through window.pyodide). Rounds played, regions that
    tipped into melt and the degrees all three regions saved against no action."""
    managed = (region, region_b, region_c)
    tipped = sum(1 for r in managed if r.melt_started_round is not None)
    saved = sum(r.temperature_saved() for r in managed)
    played = max(0, region.round_number - 1)
    return json.dumps({
        "game": "Thaw",
        "score": f"{played} round{'' if played == 1 else 's'}",
        "stats": [
            {"n": tipped, "one": "region tipped", "many": "regions tipped"},
            f"{deg(max(0.0, saved))} saved vs no action",
        ],
    })


def render_highlights():
    items = "".join(f"<li>{line}</li>" for line in highlights_lines())
    document.getElementById("highlights-list").innerHTML = items


def on_copy_highlights(event=None):
    status = document.getElementById("highlights-status")
    try:
        from js import navigator  # noqa: PLC0415 -- Pyodide-only, deliberately lazy
        navigator.clipboard.writeText(highlights_text())
        status.innerText = "Copied to the clipboard."
    except Exception:  # noqa: BLE001 -- no clipboard (tests, or a blocked page)
        status.innerText = "Copy isn't available here: select the three lines above instead."


# ===========================================================================
# G-13: temperature unit (Celsius, Fahrenheit, Kelvin) for every displayed rise. A per-browser
# preference kept in localStorage, never part of the save.
# ===========================================================================
def load_temp_unit():
    raw = _read_local_storage_item(TEMP_UNIT_STORAGE_KEY)
    return raw if raw in TEMP_UNITS else "c"


def set_temp_unit(unit):
    global temp_unit
    if unit not in TEMP_UNITS:
        return False
    temp_unit = unit
    _write_local_storage_item(TEMP_UNIT_STORAGE_KEY, unit)
    return True


def render_temp_unit():
    document.getElementById("temp-unit-select").value = temp_unit


def on_temp_unit_change(event=None):
    if set_temp_unit(document.getElementById("temp-unit-select").value):
        render()


temp_unit = load_temp_unit()


# ===========================================================================
# GG-2: Hold the Line. The run-based mode: keep at least two of the three managed regions out of
# the critical tier for as many rounds as possible while escalation events make the background
# harsher. This is the one place a Thaw run has an end, so it also feeds GG-24 (title ladder),
# GG-21 (the three AI stewards) and G-1/G-2 (Field Notes and the run overlay). There is no in-game
# reset (owner decision R24): a finished run stays on screen and a new one starts from the
# opening screen's New Game.
# ===========================================================================
run_over = False
run_result = None  # {"survived": int, "saved": float, "reason": "tipped" | "limit"}
just_escalated = 0  # the escalation level announced by the latest Advance Round, else 0


def _managed():
    return (("A", region), ("B", region_b), ("C", region_c))


def untipped_count(regions=None):
    rs = [r for _label, r in _managed()] if regions is None else regions
    return sum(1 for r in rs if not r.is_critical())


def tipped_labels():
    return [label for label, r in _managed() if r.is_critical()]


def line_holds(regions=None):
    return untipped_count(regions) >= HOLD_LINE_MIN_UNTIPPED


def can_toggle_hold_the_line():
    return not run_over and all(r.round_number == 1 for r in (region, region_b, region_c, region_d))


def set_hold_the_line(enabled):
    """Choose the mode. Only before round 1 is played, never together with the long game."""
    global hold_the_line
    if not can_toggle_hold_the_line():
        return False
    if enabled and long_game:
        return False
    hold_the_line = bool(enabled)
    return True


def average_saved(regions=None):
    rs = [r for _label, r in _managed()] if regions is None else regions
    return sum(max(0.0, r.temperature_saved()) for r in rs) / len(rs)


def run_title(saved):
    """GG-24: (title, next title or None, saved needed for the next title or None)."""
    index = 0
    for i, (minimum, _name) in enumerate(RUN_TITLES):
        if saved >= minimum:
            index = i
    title = RUN_TITLES[index][1]
    if index + 1 < len(RUN_TITLES):
        return title, RUN_TITLES[index + 1][1], RUN_TITLES[index + 1][0]
    return title, None, None


def escalation_text():
    """The status of the escalation track: what is in force and what is coming."""
    level = escalation_level(region.round_number)
    nxt = HOLD_LINE_ESCALATION_EVERY * (level + 1) + 1 - region.round_number
    upcoming = escalation_event_name(level + 1)
    rise = base_rise_per_round(region.round_number)
    cap = max_dampening(region.round_number)
    if level == 0:
        now = f"No escalation yet: background rise {deg(rise, 2)}/round, dampening ceiling {cap * 100:.0f}%."
    else:
        now = (
            f"Escalation level {level} ({escalation_event_name(level)}): background rise "
            f"{deg(rise, 2)}/round, dampening ceiling {cap * 100:.0f}%."
        )
    return f"{now} Next: {upcoming} in {nxt} round{'' if nxt == 1 else 's'}."


def _announce_escalation(level):
    global just_escalated
    just_escalated = level
    narrative_log.cap_entries(science_log, SCIENCE_LOG_MAX - 1)
    science_log.append({
        "region": "ALL",
        "round": region.round_number - 1,
        "text": (
            f"escalation level {level}, {escalation_event_name(level)}: the background rise is now "
            f"{deg(base_rise_per_round(region.round_number), 2)}/round and the dampening ceiling "
            f"{max_dampening(region.round_number) * 100:.0f}%."
        ),
    })


def finish_run(reason):
    """Ends the run. 'tipped': two or more regions went critical this round, so the round does not
    count. 'limit': HOLD_LINE_MAX_ROUNDS rounds all held."""
    global run_over, run_result
    played = region.round_number - 1
    survived = played if reason == "limit" else max(0, played - 1)
    run_result = {"survived": survived, "saved": round(average_saved(), 3), "reason": reason}
    run_over = True
    record_field_note()
    title = run_title(run_result["saved"])[0]
    narrative_log.cap_entries(science_log, SCIENCE_LOG_MAX - 1)
    science_log.append({
        "region": "ALL",
        "round": played,
        "text": f"the run is over after {survived} rounds held: you are a {title}.",
    })


def check_run_end():
    """Called once per Advance Round after every region has advanced."""
    if not hold_the_line or run_over:
        return
    if not line_holds():
        finish_run("tipped")
    elif region.round_number - 1 >= HOLD_LINE_MAX_ROUNDS:
        finish_run("limit")


# --- GG-21: three fixed AI stewards play the same mode with a fixed plan -----------------------
STEWARDS = (
    ("Cautious Kai", "kai", "buys Preservation first and keeps buying it until the ceiling"),
    ("Rash Rasmus", "rasmus", "pours everything into Output for 14 rounds, then scrambles to protect"),
    ("Balanced Bea", "bea", "protects up to half the ceiling and puts the rest into Output"),
)
STEWARD_RASH_ROUNDS = 14
_steward_cache = {}


def _steward_move(policy, r):
    """One steward's spending for one region this round (no rescue/convoy/carbon/cascade: a
    deliberately simple, fixed plan so the scoreboard is the same for everyone)."""
    if policy == "kai":
        while r.funds >= INVEST_COST["preserve"] and r.feedback_dampening_fraction() < max_dampening(r.round_number):
            r.invest("preserve")
    elif policy == "rasmus":
        if r.round_number <= STEWARD_RASH_ROUNDS:
            while r.funds >= INVEST_COST["output"]:
                r.invest("output")
        else:
            while r.funds >= INVEST_COST["preserve"] and r.feedback_dampening_fraction() < max_dampening(r.round_number):
                r.invest("preserve")
    else:
        # Bea aims for about half of the ceiling in protection and puts the rest into Output, so
        # she can afford the occasional rescue.
        while r.funds >= INVEST_COST["preserve"] and r.feedback_dampening_fraction() < max_dampening(r.round_number) * 0.5:
            r.invest("preserve")
        while r.funds >= INVEST_COST["output"]:
            r.invest("output")
    if r.can_rescue():
        r.rescue()


def simulate_steward(policy):
    """Plays a whole Hold the Line run for one steward on three fresh regions. Returns
    {"survived", "saved"} using the same rules as the player's run."""
    global hold_the_line, long_game
    saved_flags = (hold_the_line, long_game)
    hold_the_line, long_game = True, False
    try:
        rs = [RegionState() for _ in range(3)]
        survived = 0
        for _ in range(HOLD_LINE_MAX_ROUNDS):
            for r in rs:
                _steward_move(policy, r)
            for r in rs:
                r.advance_round()
            if not line_holds(rs):
                break
            survived += 1
        return {"survived": survived, "saved": round(average_saved(rs), 3)}
    finally:
        hold_the_line, long_game = saved_flags


def steward_scores():
    """Cached: the stewards are deterministic, so each plan only needs playing once."""
    for _name, policy, _blurb in STEWARDS:
        if policy not in _steward_cache:
            _steward_cache[policy] = simulate_steward(policy)
    return {policy: dict(_steward_cache[policy]) for _name, policy, _blurb in STEWARDS}


def stewards_beaten(survived):
    scores = steward_scores()
    return sum(1 for _name, policy, _blurb in STEWARDS if survived > scores[policy]["survived"])


def steward_lines():
    scores = steward_scores()
    return [
        f"{name} {scores[policy]['survived']} rounds ({deg(scores[policy]['saved'])} saved on average): {blurb}."
        for name, policy, blurb in STEWARDS
    ]


# --- G-1 / G-2: Field Notes, a per-run history kept on this device ---------------------------
FIELD_NOTES_KEY = "thaw_field_notes_v1"
FIELD_NOTES_MAX = 30
FIELD_NOTES_CURVE_POINTS = 60


def _decimate(values, limit=FIELD_NOTES_CURVE_POINTS):
    """Keeps at most `limit` points, evenly spaced, always including the last one."""
    values = [round(float(v), 3) for v in values]
    if len(values) <= limit:
        return values
    step = (len(values) - 1) / (limit - 1)
    return [values[round(i * step)] for i in range(limit)]


def _num(value, low, high):
    return (
        isinstance(value, (int, float)) and not isinstance(value, bool)
        and math.isfinite(value) and low <= value <= high
    )


def _clean_curve(raw):
    if not isinstance(raw, list):
        return []
    return _decimate([float(v) for v in raw if _num(v, -1000000, 1000000000)])


def _clean_note(raw):
    """One stored run summary with every field forced into range; None when it is unusable."""
    if not isinstance(raw, dict) or not _num(raw.get("survived"), 0, 1000000):
        return None
    mix_raw = raw.get("mix") if isinstance(raw.get("mix"), dict) else {}
    saved_raw = raw.get("region_saved") if isinstance(raw.get("region_saved"), dict) else {}
    best = raw.get("best_region")
    return {
        "survived": int(raw["survived"]),
        "saved": float(raw["saved"]) if _num(raw.get("saved"), -1000000, 1000000000) else 0.0,
        "tipped": int(raw["tipped"]) if _num(raw.get("tipped"), 0, 3) else 0,
        "avg_accel": float(raw["avg_accel"]) if _num(raw.get("avg_accel"), 0, 1000000) else 1.0,
        "mix": {c: int(mix_raw[c]) if _num(mix_raw.get(c), 0, 1000000) else 0 for c in CATEGORIES},
        "region_saved": {
            label: float(saved_raw[label]) if _num(saved_raw.get(label), -1000000, 1000000000) else 0.0
            for label in ARCHIVE_REGIONS
        },
        "best_region": best if best in ARCHIVE_REGIONS else "A",
        "curve": _clean_curve(raw.get("curve")),
        "baseline": _clean_curve(raw.get("baseline")),
    }


def load_field_notes():
    raw = _read_local_storage_item(FIELD_NOTES_KEY)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    notes = [n for n in (_clean_note(item) for item in data) if n is not None]
    return notes[-FIELD_NOTES_MAX:]


field_notes = load_field_notes()


def _build_note():
    managed = _managed()
    saved_by = {label: max(0.0, r.temperature_saved()) for label, r in managed}
    best = max(saved_by, key=lambda label: (saved_by[label], -ord(label)))
    return {
        "survived": run_result["survived"],
        "saved": run_result["saved"],
        "tipped": sum(1 for _label, r in managed if r.melt_started_round is not None),
        "avg_accel": round(sum(r.average_acceleration_factor for _label, r in managed) / 3, 3),
        "mix": {c: sum(r.capacity[c] for _label, r in managed) for c in CATEGORIES},
        "region_saved": {label: round(v, 3) for label, v in saved_by.items()},
        "best_region": best,
        "curve": _decimate(region.temperature_history),
        "baseline": _decimate(region_d.temperature_history),
    }


def record_field_note():
    """Appends this run's summary and saves the list (keeping the newest FIELD_NOTES_MAX)."""
    field_notes.append(_clean_note(_build_note()))
    del field_notes[:-FIELD_NOTES_MAX]
    _write_local_storage_item(FIELD_NOTES_KEY, json.dumps(field_notes))


def field_note_bests():
    """Best degrees saved per region across every stored run (all zero with no runs)."""
    return {
        label: max([n["region_saved"][label] for n in field_notes] or [0.0])
        for label in ARCHIVE_REGIONS
    }


def field_note_rows():
    rows = []
    for i, n in enumerate(field_notes, start=1):
        mix = n["mix"]
        rows.append(
            f"Run {i}: held {n['survived']} rounds, {deg(n['saved'])} saved, {n['tipped']} region"
            f"{'' if n['tipped'] == 1 else 's'} melted, average acceleration {n['avg_accel']:.2f}x, "
            f"units Output {mix['output']} / Preservation {mix['preserve']} / Monitoring {mix['monitor']}, "
            f"best Region {n['best_region']}."
        )
    return rows


def field_notes_chart_svg():
    """Degrees saved per finished run, as bars (a shape the numbers in the list repeat)."""
    if not field_notes:
        return ""
    width, height = 160, 44
    top = max([n["saved"] for n in field_notes] + [0.001])
    slot = width / len(field_notes)
    bars = "".join(
        f'<rect x="{i * slot + 1:.1f}" y="{height - n["saved"] / top * (height - 4):.1f}" '
        f'width="{min(max(slot - 2, 1), 12):.1f}" height="{n["saved"] / top * (height - 4):.1f}" class="field-bar" />'
        for i, n in enumerate(field_notes)
    )
    label = f"Degrees saved in each of {len(field_notes)} finished run{'' if len(field_notes) == 1 else 's'}, best {deg(top)}."
    return (
        f'<svg viewBox="0 0 {width} {height}" class="field-notes-svg" role="img" aria-label="{label}">'
        f"<title>{label}</title>{bars}</svg>"
    )


def render_field_notes():
    rows = field_note_rows()
    bests = field_note_bests()
    document.getElementById("field-notes-count").innerText = str(len(field_notes))
    document.getElementById("field-notes-list").innerHTML = (
        "".join(f"<li>{row}</li>" for row in rows) if rows
        else "<li>No finished runs yet. Finish a Hold the Line run to start your field notes.</li>"
    )
    document.getElementById("field-notes-bests").innerText = (
        "Best degrees saved per region: "
        + ", ".join(f"Region {label} {deg(bests[label])}" for label in ARCHIVE_REGIONS)
        + "."
    )
    document.getElementById("field-notes-chart").innerHTML = field_notes_chart_svg()
    _render_compare_options()
    render_compare()


# G-2: overlay any two stored runs (or a run against its own no-action baseline) on one graph.
COMPARE_W, COMPARE_H = 160, 70
_compare_option_count = -1


def compare_choices():
    """[(value, label)] for the two selects: each stored run and each run's no-action baseline."""
    choices = []
    for i in range(1, len(field_notes) + 1):
        choices.append((f"run:{i}", f"Run {i}"))
    for i in range(1, len(field_notes) + 1):
        choices.append((f"base:{i}", f"Run {i} if nobody intervened"))
    return choices


def compare_curve(choice):
    """The stored curve a choice names, or None when the choice does not name a stored run."""
    if not isinstance(choice, str) or ":" not in choice:
        return None
    kind, _sep, index = choice.partition(":")
    if kind not in ("run", "base") or not index.isdigit():
        return None
    i = int(index)
    if not 1 <= i <= len(field_notes):
        return None
    return field_notes[i - 1]["curve" if kind == "run" else "baseline"]


def compare_divergence(a, b):
    """Per-round gaps between two curves over the rounds both cover (empty if either is empty)."""
    return [round(abs(x - y), 3) for x, y in zip(a, b)]


def compare_readout(a, b):
    gaps = compare_divergence(a, b)
    if not gaps:
        return "Pick two runs that have recorded rounds to compare."
    biggest = max(gaps)
    at = gaps.index(biggest) + 1
    first = next((i + 1 for i, g in enumerate(gaps) if g >= 1.0), None)
    parts = [
        f"Over the {len(gaps)} rounds both cover, the gap ends at {deg(gaps[-1])} and peaks at "
        f"{deg(biggest)} in round {at}."
    ]
    parts.append(
        f"They first differ by a degree or more in round {first}." if first
        else "They never differ by a full degree."
    )
    return " ".join(parts)


def compare_chart_svg(a, b):
    if not a or not b:
        return ""
    values = list(a) + list(b)
    lo, hi = min(values + [0.0]), max(values + [MELT_THRESHOLD])
    span = max(hi - lo, 1e-9)
    longest = max(len(a), len(b))

    def points(curve):
        return " ".join(
            f"{(i / max(longest - 1, 1)) * COMPARE_W:.1f},{COMPARE_H - (v - lo) / span * COMPARE_H:.1f}"
            for i, v in enumerate(curve)
        )

    melt_y = COMPARE_H - (MELT_THRESHOLD - lo) / span * COMPARE_H
    label = (
        f"Two temperature curves over up to {longest} rounds. The first ends at {deg(a[-1], plus=True)} "
        f"and the second at {deg(b[-1], plus=True)}. The dashed line is the +{MELT_THRESHOLD:.0f} degree melt threshold."
    )
    return (
        f'<svg viewBox="0 0 {COMPARE_W} {COMPARE_H}" class="compare-svg" role="img" aria-label="{label}">'
        f"<title>{label}</title>"
        f'<line x1="0" y1="{melt_y:.1f}" x2="{COMPARE_W}" y2="{melt_y:.1f}" class="mini-temp-threshold-line" />'
        f'<polyline points="{points(a)}" class="compare-line compare-line--first" />'
        f'<polyline points="{points(b)}" class="compare-line compare-line--second" />'
        f"</svg>"
    )


def _render_compare_options():
    global _compare_option_count
    if _compare_option_count == len(field_notes):
        return
    _compare_option_count = len(field_notes)
    choices = compare_choices()
    options = "".join(f'<option value="{value}">{label}</option>' for value, label in choices)
    select_a = document.getElementById("compare-run-a")
    select_b = document.getElementById("compare-run-b")
    select_a.innerHTML = options
    select_b.innerHTML = options
    if choices:
        newest = len(field_notes)
        select_a.value = f"run:{newest}"
        select_b.value = f"base:{newest}"


def render_compare():
    a = compare_curve(document.getElementById("compare-run-a").value)
    b = compare_curve(document.getElementById("compare-run-b").value)
    document.getElementById("compare-chart").innerHTML = compare_chart_svg(a, b) if a and b else ""
    document.getElementById("compare-readout").innerText = (
        compare_readout(a, b) if a is not None and b is not None
        else "Finish a run to compare it with another run or with what would have happened with no action."
    )


def on_compare_change(event=None):
    render_compare()


# --- rendering and handlers for the mode itself ---------------------------------------------
def result_lines():
    """The end-of-run panel as a list of text lines (empty until the run is over)."""
    if not run_over or run_result is None:
        return []
    survived, saved = run_result["survived"], run_result["saved"]
    title, nxt, needed = run_title(saved)
    beaten = stewards_beaten(survived)
    if run_result["reason"] == "limit":
        head = f"You held the line for all {survived} rounds, the limit of a run."
    else:
        tipped = ", ".join(tipped_labels()) or "two regions"
        head = f"The line broke: Regions {tipped} went critical. You held it for {survived} rounds."
    lines = [head, f"Average saved across Regions A to C: {deg(saved)}. Your title: {title}."]
    if nxt is not None:
        lines.append(f"Next title: {nxt} at {deg(needed)} saved ({deg(max(0.0, needed - saved))} to go).")
    else:
        lines.append("That is the top title.")
    lines.append(f"You beat {beaten} of 3 stewards.")
    lines += steward_lines()
    return lines


def hold_line_status():
    if not hold_the_line:
        if long_game:
            return "Hold the Line is off (the long game is on; the two modes cannot be combined)."
        return (
            "Hold the Line is off. Turn it on before round 1 to play a run: keep at least two of "
            "the three regions out of the critical tier for as many rounds as you can while escalation "
            "events make the background harsher."
        )
    if run_over:
        return "Hold the Line: the run is over. Start a new game from the opening screen to try again."
    held = untipped_count()
    return (
        f"Hold the Line, round {region.round_number}: {held} of 3 regions are out of the critical tier "
        f"(you need {HOLD_LINE_MIN_UNTIPPED}). {escalation_text()}"
    )


def render_hold_line():
    global just_escalated
    button = document.getElementById("hold-line-toggle-button")
    button.innerText = "Hold the Line: on" if hold_the_line else "Hold the Line: off"
    button.disabled = not (can_toggle_hold_the_line() and (hold_the_line or not long_game))
    status = hold_line_status()
    if not can_toggle_hold_the_line() and not hold_the_line:
        status += " (Locked once the first round has been played.)"
    document.getElementById("hold-line-display").innerText = status
    callout = document.getElementById("escalation-callout")
    if just_escalated and hold_the_line:
        callout.innerText = (
            f"Escalation: {escalation_event_name(just_escalated)}. The background rise is now "
            f"{deg(base_rise_per_round(region.round_number), 2)}/round and the most dampening "
            f"investment can hold is {max_dampening(region.round_number) * 100:.0f}%."
        )
        callout.hidden = False
    else:
        callout.hidden = True
    just_escalated = 0
    result = document.getElementById("hold-line-result")
    lines = result_lines()
    result.hidden = not lines
    result.innerHTML = "".join(f"<li>{line}</li>" for line in lines)
    advance = document.getElementById("advance-round-button")
    advance.disabled = run_over
    advance.innerText = "Run over" if run_over else "Advance Round"


def on_toggle_hold_the_line(event=None):
    set_hold_the_line(not hold_the_line)
    render()


def render():
    render_info_page()
    document.getElementById("round-display").innerText = f"Round {region.round_number}"
    document.getElementById("funds-display").innerText = f"Funds: {region.funds:.0f}"
    document.getElementById("temperature-display").innerText = (
        f"Global temperature: {deg(region.temperature, plus=True)}"
    )
    # G9: the temperature bar visually caps at TEMPERATURE_METER_MAX
    # (+30°) even though temperature itself keeps climbing past it —
    # without this note a maxed-out bar reads as "capped for real,"
    # which understates how far past +30° a long, unmanaged session can
    # actually reach.
    cap_note_el = document.getElementById("temperature-cap-note")
    if region.temperature > TEMPERATURE_METER_MAX:
        cap_note_el.innerText = (
            f"(meter shown capped at {deg(TEMPERATURE_METER_MAX, 0, plus=True)} — actual temperature is "
            f"{deg(region.temperature, plus=True)})"
        )
        cap_note_el.hidden = False
    else:
        cap_note_el.hidden = True
    _render_trend("temperature-trend", region)
    _render_rescue("", region)
    _render_restoration("", region)
    _render_policy_stance()
    _render_forecast()
    _render_framing()
    _render_long_game()
    render_shared_research()
    render_carbon_bank()
    render_routing()
    render_balance()
    render_rate_inspector()
    render_highlights()
    render_hold_line()
    render_field_notes()
    render_temp_unit()
    document.getElementById("rise-rate-display").innerText = (
        f"Current warming rate: {deg(region.current_rise_rate(), 2)}/round"
    )
    melt_status_el = document.getElementById("melt-status-display")
    status = _melt_status_label(region)
    if status == "critical":
        melt_status_el.innerText = (
            "Permafrost melt has reached a critical, fast-compounding pace — the feedback "
            "loop is running away."
        )
    elif status == "melting":
        melt_status_el.innerText = (
            "Permafrost is actively melting — methane feedback is accelerating warming."
        )
    else:
        melt_status_el.innerText = "Permafrost stable — no feedback yet."
    status_suffix = {
        "stable": "",
        "melting": " melt-status--active",
        "critical": " melt-status--critical",
    }[status]
    melt_status_el.className = "comparison-message" + status_suffix

    game_el = document.getElementById("game")
    if region.just_started_melting:
        game_el.className = "tipping-flash"
        region.just_started_melting = False
    else:
        game_el.className = ""

    # G10: the one-tick "intervention delayed a further warming
    # milestone" callout — a separate banner from the tipping-flash
    # above, since it can fire many rounds after melt already started.
    milestone_delay_el = document.getElementById("milestone-delay-callout")
    if region.just_delayed_milestone:
        milestone_delay_el.innerText = (
            f"Your preservation & monitoring investments just delayed reaching "
            f"{deg(SECOND_WARMING_MILESTONE, 0, plus=True)} warming — the unmitigated counterfactual has "
            f"already passed it."
        )
        milestone_delay_el.hidden = False
        region.just_delayed_milestone = False
    else:
        milestone_delay_el.hidden = True

    # G12: one-time praise the round melt begins with protection already
    # in place -- can only ever fire once per region (melt starts once).
    preempt_el = document.getElementById("preemptive-callout")
    if region.just_preempted_melt:
        preempt_el.innerText = (
            f"Well done: {(region.dampening_at_melt_start or 0) * 100:.0f}% feedback dampening was "
            "already in place before melt began. Pre-emptive investment is the strongest "
            "lever there is."
        )
        preempt_el.hidden = False
        region.just_preempted_melt = False
    else:
        preempt_el.hidden = True

    # GG-20: "phew" -- an investment (or rescue) just pulled a region back from
    # a projected critical tier next round.
    phew_el = document.getElementById("phew-callout")
    pulled = [label for label, r in (("A", region), ("B", region_b), ("C", region_c)) if r.just_pulled_back]
    for _label, r in (("A", region), ("B", region_b), ("C", region_c)):
        r.just_pulled_back = False
    if pulled:
        phew_el.innerText = (
            f"Phew: without that last move Region {', '.join(pulled)} was on course to go critical "
            f"next round. It isn't now."
        )
        phew_el.hidden = False
    else:
        phew_el.hidden = True

    # G28: stability streak.
    streak_el = document.getElementById("tipping-streak-display")
    if region.tipping_events == 0:
        streak_el.innerText = (
            f"No tipping event yet: {region.rounds_since_tipping_event} rounds stable."
        )
    else:
        streak_el.innerText = (
            f"{region.rounds_since_tipping_event} rounds since the last tipping event "
            f"({region.tipping_events} so far)."
        )

    dampening_el = document.getElementById("dampening-display")
    dampening_el.innerText = f"Feedback dampening: {region.feedback_dampening_fraction() * 100:.0f}%"
    if region.just_invested_intervention:
        dampening_el.className = "status-line dampening-flash"
        region.just_invested_intervention = False
    else:
        dampening_el.className = "status-line"
    document.getElementById("intervention-feedback-display").innerText = (
        region.intervention_feedback_message()
    )
    acceleration_el = document.getElementById("acceleration-display")
    acceleration_el.innerText = region.acceleration_message()
    # G24: a brief pulse the instant the region crosses into the critical tier.
    if region.just_became_critical:
        acceleration_el.className = "comparison-message acceleration-pulse"
        region.just_became_critical = False
    else:
        acceleration_el.className = "comparison-message"
    document.getElementById("acceleration-bar").style.width = (
        f"{min(1.0, (region.acceleration_factor() - 1) / 2) * 100:.0f}%"
    )
    document.getElementById("trajectory-display").innerText = region.trajectory_message()

    document.getElementById("temperature-bar").style.width = (
        f"{min(1.0, region.temperature / TEMPERATURE_METER_MAX) * 100:.0f}%"
    )
    document.getElementById("graph").innerHTML = mini_temp_graph_svg(region.temperature_history, "Region A")
    document.getElementById("acceleration-sparkline").innerHTML = accel_sparkline_svg(region.acceleration_history)
    document.getElementById("ice-age-display").innerText = ice_age_text(region)

    for category in CATEGORIES:
        document.getElementById(f"{category}-name").innerText = (
            f"{CATEGORY_ICON[category]} {CATEGORY_LABEL[category]}"
        )
        document.getElementById(f"{category}-count").innerText = str(region.capacity[category])
        invest_button = document.getElementById(f"{category}-invest-button")
        invest_button.innerText = f"Invest ({INVEST_COST[category]})"
        invest_button.disabled = region.funds < INVEST_COST[category]

    # G12: a small inline forecast of each investment's effect, so a
    # player can see what a click would do before making it rather than
    # inferring it from the constants tables in How to Play.
    document.getElementById("output-forecast").innerText = f"+{output_income_per_unit():g} funds/round"
    document.getElementById("preserve-forecast").innerText = (
        f"+{DAMPENING_PER_PRESERVE_UNIT * 100:.0f}% dampening"
    )
    document.getElementById("monitor-forecast").innerText = (
        f"+{DAMPENING_PER_MONITOR_UNIT * 100:.0f}% dampening"
    )

    for prefix, r in SECONDARY_REGIONS.items():
        render_secondary_region(prefix, r)

    worst_case_panel = document.getElementById("worst-case-panel")
    worst_case_panel.hidden = not worst_case_region_revealed
    if worst_case_region_revealed:
        render_worst_case_region()
    worst_case_toggle = document.getElementById("worst-case-toggle-button")
    worst_case_toggle.innerText = (
        "Hide the worst-case region" if worst_case_region_revealed else "Reveal a worst-case region"
    )
    # G4: explain "worst case" before the player reveals it.
    worst_case_toggle.title = (
        "Region D is a fully automated stand-in for pure neglect: every round it spends "
        "everything on Output and never invests in Preservation or Monitoring. It shows "
        "what warming looks like if nobody intervenes."
    )
    # G30: first-reveal-only note that D needs no input.
    document.getElementById("d-intro-note").hidden = not (
        worst_case_region_revealed and not worst_case_intro_seen
    )

    # G19: scientist's log.
    document.getElementById("science-log-count").innerText = str(len(science_log))
    document.getElementById("science-log-list").innerHTML = science_log_html()

    # G2: an explicit "which region did best" comparison line, always
    # visible (not gated on an end-of-session state, since this game has
    # none) rather than only inferable by eyeballing three separate cards.
    document.getElementById("region-comparison-best-display").innerText = best_region_message()
    # G15: a hidden, machine-readable echo of the same comparison for the
    # plain-JS feedback-submission script below to fold into its rating
    # payload as an aggregate stat.
    document.getElementById("best-region-hidden").innerText = best_region_identifier()

    # G17: a next-round forecast, available as a hover tooltip on Advance
    # Round rather than a permanent line, since it's a "before you click"
    # preview rather than information about the current state.
    # G10: one combined tooltip covering all three managed regions, each
    # with its projected temperature after the coming round.
    document.getElementById("advance-round-button").title = "\n".join(
        ["Next round preview"]
        + [
            f"Region {label}: {deg(r.current_rise_rate(), 2, plus=True)} "
            f"(to {deg(r.temperature + r.current_rise_rate(), plus=True)})"
            for label, r in (("A", region), ("B", region_b), ("C", region_c))
        ]
    )

    _maybe_update_personal_best()
    _maybe_update_climate_archive()
    render_personal_best()
    render_climate_archive()
    update_achievements_display()
    update_changelog_display()
    update_community_compare_panel()
    render_climate_scientist()


def _make_invest_handler(category):
    def handler(event=None):
        region.invest(category)
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_secondary_invest_handler(prefix, category):
    def handler(event=None):
        SECONDARY_REGIONS[prefix].invest(category)
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_policy_stance_handler(key):
    def handler(event=None):
        if region.choose_policy_stance(key):
            render()
            _check_new_achievements_for_toast()
    return handler


def _make_rescue_handler(prefix):
    """G21: prefix "" is Region A, "b"/"c" the secondary regions."""
    def handler(event=None):
        target = region if prefix == "" else SECONDARY_REGIONS[prefix]
        if target.rescue():
            render()
            _check_new_achievements_for_toast()
    return handler


def _make_preset_handler(prefix, preset_name):
    def handler(event=None):
        apply_preset(SECONDARY_REGIONS[prefix], preset_name)
        render()
        _check_new_achievements_for_toast()
    return handler


def _make_strategy_label_handler(prefix):
    """G4: reads the input's current value straight off the DOM into
    state on every "input" event. Deliberately does NOT call render() —
    render() never writes this input's .value back (see setup()'s own
    comment), but avoiding the call entirely also sidesteps ever needing
    to reason about it, and there's nothing else on screen this label
    needs to update."""
    def handler(event=None):
        SECONDARY_REGIONS[prefix].strategy_label = document.getElementById(
            f"{prefix}-strategy-label-input"
        ).value
    return handler


def on_toggle_worst_case_region(event=None):
    global worst_case_region_revealed, worst_case_intro_seen
    if worst_case_region_revealed:
        worst_case_intro_seen = True  # closing it after the first look retires the note
    worst_case_region_revealed = not worst_case_region_revealed
    render()
    _check_new_achievements_for_toast()


def on_advance_round(event=None):
    if run_over:
        return
    level_before = escalation_level(region.round_number)
    region.advance_round()
    resolve_forecast()
    for r in SECONDARY_REGIONS.values():
        r.advance_round()
    apply_tipping_cascades()
    bank_carbon_credits()
    apply_balance_bonus()
    _auto_play_worst_case_region()
    _record_round_events()
    if escalation_level(region.round_number) > level_before:
        _announce_escalation(escalation_level(region.round_number))
    check_run_end()
    # G-10: announce before render() so the balance flag is still set.
    document.getElementById("sr-announcer").innerText = round_announcement()
    render()
    _check_new_achievements_for_toast()


# --- Save system (SAVE-BUTTON-INTEGRATION.md contract) ---
# Bridges to the shared shared/save-widget.js: get_state() returns a
# plain JSON-safe dict (the widget does its own JS<->Pyodide dict
# conversion), and load_state() is its exact inverse. SOL is the
# reference integration for this contract. Thaw tracks THREE independent
# regions (the original primary region, plus Pass 2's Region B and
# Region C) — all three must round-trip, not just the primary one.


def _region_state_dict(r):
    """One RegionState's fields as a plain, JSON-safe dict. `capacity`
    and `temperature_history` are copied here (dict()/list()), not just
    referenced, so continued play after taking a snapshot can't silently
    mutate a saved copy — same reasoning as SOL's serialize_state()
    docstring."""
    data = {
        "round_number": r.round_number,
        "funds": r.funds,
        "capacity": dict(r.capacity),
        "temperature": r.temperature,
        "melt_started_round": r.melt_started_round,
        "just_started_melting": r.just_started_melting,
        "counterfactual_temperature": r.counterfactual_temperature,
        "temperature_history": list(r.temperature_history),
        "just_invested_intervention": r.just_invested_intervention,
        "strategy_label": r.strategy_label,
        "dampening_at_melt_start": r.dampening_at_melt_start,
        "just_delayed_milestone": r.just_delayed_milestone,
        "milestone_delay_announced": r.milestone_delay_announced,
        "just_became_critical": r.just_became_critical,
        "rounds_since_tipping_event": r.rounds_since_tipping_event,
        "tipping_events": r.tipping_events,
        "just_preempted_melt": r.just_preempted_melt,
        # G11: the community-comparison metric -- see RegionState.__init__'s
        # comment on why this rides get_state() as a plain running average
        # rather than being recomputed from temperature_history.
        "average_acceleration_factor": r.average_acceleration_factor,
        "acceleration_samples": r.acceleration_samples,
    }
    # G21: written only once a rescue has actually been used, so a save
    # from a region that never needed one is byte-identical to before.
    if r.rescue_used:
        data["rescue_used"] = True
        data["rescue_rounds_left"] = r.rescue_rounds_left
    # G13: only the key is saved; the dampening it grants is re-derived on
    # load, so retuning a stance can never leave a stale number in a save.
    if r.policy_stance is not None:
        data["policy_stance"] = r.policy_stance
    # G15: likewise written only once restoration has actually started.
    if r.stabilized_rounds or r.restored_total:
        data["stabilized_rounds"] = r.stabilized_rounds
        data["restored_total"] = r.restored_total
    # GG-13 / G-24: written only once there is something to write.
    if r.best_stable_streak:
        data["best_stable_streak"] = r.best_stable_streak
    if r.acceleration_history:
        data["acceleration_history"] = list(r.acceleration_history)
    return data


def _apply_region_state(r, data):
    """The exact inverse of _region_state_dict() — restores one
    RegionState's fields in place from a previously-saved dict.

    Every field is read with `.get(key, <current live value>)` rather than
    a bare `data["key"]` — a save may be a hand-edited/truncated payload,
    or simply come from a different build of this game with a different
    field set (an older save from before some field existed, or a newer
    one this build doesn't know about yet). A bare index raised a
    KeyError partway through these assignments, leaving some fields
    already overwritten from the save and others still at their pre-load
    values — worse than either a clean load or leaving the field alone.
    Falling back to the field's current value keeps a partial/malformed
    save loading everything it safely can instead of crashing outright.

    `capacity` is merged into the live dict key-by-key rather than
    replaced wholesale, same reasoning as above but at the nested-dict
    level: a save whose capacity is missing a category (an older save
    format from before that category existed, or a hand-edited/corrupted
    payload) must not wipe that category's key out of the live dict
    entirely — invest(), feedback_dampening_fraction() and render() all do
    unconditional capacity["monitor"]-style key access, so a missing key
    would crash the game on the very next call, including the re-render
    load_state() itself triggers. Same fix shape as SOL's planet_state and
    Continuum's resources/allocation/buildings dicts. Also mirrors Tide's
    load_state(), which already used this exact `.get()` pattern
    throughout (see that file's REVIEW(patterns) comment flagging Thaw,
    among others, as still doing bare data["key"] indexing)."""
    r.round_number = data.get("round_number", r.round_number)
    r.funds = data.get("funds", r.funds)
    saved_capacity = data.get("capacity")
    if isinstance(saved_capacity, dict):
        for category in CATEGORIES:
            if category in saved_capacity:
                r.capacity[category] = saved_capacity[category]
    r.temperature = data.get("temperature", r.temperature)
    r.melt_started_round = data.get("melt_started_round", r.melt_started_round)
    r.just_started_melting = data.get("just_started_melting", r.just_started_melting)
    r.counterfactual_temperature = data.get(
        "counterfactual_temperature", r.counterfactual_temperature
    )
    saved_history = data.get("temperature_history")
    if isinstance(saved_history, list):
        r.temperature_history = list(saved_history)
    r.just_invested_intervention = data.get(
        "just_invested_intervention", r.just_invested_intervention
    )
    r.strategy_label = data.get("strategy_label", r.strategy_label)
    r.dampening_at_melt_start = data.get("dampening_at_melt_start", r.dampening_at_melt_start)
    r.just_delayed_milestone = data.get("just_delayed_milestone", r.just_delayed_milestone)
    r.milestone_delay_announced = data.get(
        "milestone_delay_announced", r.milestone_delay_announced
    )
    r.just_became_critical = data.get("just_became_critical", r.just_became_critical)
    r.rounds_since_tipping_event = data.get(
        "rounds_since_tipping_event", r.rounds_since_tipping_event
    )
    r.tipping_events = data.get("tipping_events", r.tipping_events)
    r.just_preempted_melt = data.get("just_preempted_melt", r.just_preempted_melt)
    r.average_acceleration_factor = data.get(
        "average_acceleration_factor", r.average_acceleration_factor
    )
    r.acceleration_samples = data.get("acceleration_samples", r.acceleration_samples)
    # G21: validated -- a bool and an int in range, else the safe default.
    saved_rescue_used = data.get("rescue_used")
    if isinstance(saved_rescue_used, bool):
        r.rescue_used = saved_rescue_used
    saved_rescue_rounds = data.get("rescue_rounds_left")
    if (
        isinstance(saved_rescue_rounds, int)
        and not isinstance(saved_rescue_rounds, bool)
        and 0 <= saved_rescue_rounds <= RESCUE_DURATION_ROUNDS
    ):
        r.rescue_rounds_left = saved_rescue_rounds
    if r.rescue_rounds_left > 0:
        r.rescue_used = True
    saved_streak = data.get("stabilized_rounds")
    if isinstance(saved_streak, int) and not isinstance(saved_streak, bool) and 0 <= saved_streak <= 100000:
        r.stabilized_rounds = saved_streak
    else:
        r.stabilized_rounds = 0
    saved_restored = data.get("restored_total")
    if (
        isinstance(saved_restored, (int, float))
        and not isinstance(saved_restored, bool)
        and math.isfinite(saved_restored)
        and 0 <= saved_restored <= 1000000
    ):
        r.restored_total = float(saved_restored)
    else:
        r.restored_total = 0.0
    saved_best = data.get("best_stable_streak")
    if isinstance(saved_best, int) and not isinstance(saved_best, bool) and 0 <= saved_best <= 100000:
        r.best_stable_streak = saved_best
    else:
        r.best_stable_streak = 0
    r.best_stable_streak = max(r.best_stable_streak, r.rounds_since_tipping_event)
    saved_accel = data.get("acceleration_history")
    if isinstance(saved_accel, list):
        r.acceleration_history = [
            float(v) for v in saved_accel
            if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and 0 <= v <= 1000000
        ][-ACCEL_HISTORY_MAX:]
    else:
        r.acceleration_history = []
    r.just_pulled_back = False
    saved_stance = data.get("policy_stance")
    if isinstance(saved_stance, str) and saved_stance in POLICY_STANCES:
        r.policy_stance = saved_stance
        r.policy_dampening = POLICY_STANCES[saved_stance]["dampening"]
    else:
        r.policy_stance = None
        r.policy_dampening = 0.0


def get_state():
    """Return every module-level mutable global needed to fully
    reconstruct the game — all four regions (primary + Region B/C/D) plus
    the info-page toggle and the two achievement-only flags — as a plain,
    JSON-serialisable dict. No custom objects, no functions: just numbers,
    strings, lists, dicts, booleans.

    "achievements_earned" is a write-only projection
    (ACHIEVEMENTS-SYSTEM-DESIGN.md §1) — always freshly recomputed here,
    never read back in load_state()."""
    state = {
        "region": _region_state_dict(region),
        "region_b": _region_state_dict(region_b),
        "region_c": _region_state_dict(region_c),
        "region_d": _region_state_dict(region_d),
        "info_page_open": info_page_open,
        "worst_case_region_revealed": worst_case_region_revealed,
        "preset_used_ever": preset_used_ever,
        "worst_case_intro_seen": worst_case_intro_seen,
        "science_log": [dict(entry) for entry in science_log],
        "achievements_earned": achievement_ids_earned(),
    }
    # G27: the forecast record is written only once a forecast has been scored.
    if forecast_total > 0:
        state["forecast"] = {"total": forecast_total, "hits": forecast_hits}
    # G3: the carbon bank is written only when it holds credits.
    if carbon_bank > 0:
        state["carbon_bank"] = carbon_bank
    # G29: only the non-default framing is written.
    if framing != "regional":
        state["framing"] = framing
    # G9: only written when the long game is on.
    if long_game:
        state["long_game"] = True
    # GG-2: only written when Hold the Line is on; the result only once the run is over.
    if hold_the_line:
        state["hold_the_line"] = True
        if run_over and run_result is not None:
            state["run"] = dict(run_result)
    # GG-5 / GG-27: only written once a convoy or a balance bonus has happened.
    if convoys_sent > 0:
        state["routing"] = {"convoys": convoys_sent, "tax_lost": convoy_tax_lost}
    if balance_bonuses > 0:
        state["balance_bonuses"] = balance_bonuses
    return state


def load_state(data):
    """Take the dict from get_state() (possibly from a previous session)
    and restore the game to that point, across all four regions, then
    re-render so the UI reflects the loaded state immediately. The exact
    inverse of get_state() (except "achievements_earned" -- see
    get_state()'s own comment, that key is never read back).

    A non-dict payload is rejected outright rather than raising. A dict
    missing "region_b"/"region_c"/"region_d" entirely — e.g. a save made
    before that region existed — leaves that region's live state
    untouched instead of crashing, same reasoning as every other
    per-field fallback in _apply_region_state()."""
    global info_page_open, worst_case_region_revealed, preset_used_ever
    global worst_case_intro_seen, forecast_guess, forecast_total, forecast_hits, forecast_last
    global framing, carbon_bank, long_game, convoys_sent, convoy_tax_lost, balance_bonuses, just_balanced
    global hold_the_line, run_over, run_result, just_escalated
    if not isinstance(data, dict):
        return False
    long_game = data.get("long_game") is True
    # GG-2: strict bool; never together with the long game; the run result only counts if the mode
    # is on and every field is in range.
    hold_the_line = data.get("hold_the_line") is True and not long_game
    run_over = False
    run_result = None
    just_escalated = 0
    saved_run = data.get("run")
    if hold_the_line and isinstance(saved_run, dict):
        survived = saved_run.get("survived")
        saved_avg = saved_run.get("saved")
        reason = saved_run.get("reason")
        if (
            _num(survived, 0, 1000000) and isinstance(survived, int)
            and _num(saved_avg, -1000000, 1000000000) and reason in ("tipped", "limit")
        ):
            run_over = True
            run_result = {"survived": survived, "saved": float(saved_avg), "reason": reason}
    region_data = data.get("region")
    if isinstance(region_data, dict):
        _apply_region_state(region, region_data)
    region_b_data = data.get("region_b")
    if isinstance(region_b_data, dict):
        _apply_region_state(region_b, region_b_data)
    region_c_data = data.get("region_c")
    if isinstance(region_c_data, dict):
        _apply_region_state(region_c, region_c_data)
    region_d_data = data.get("region_d")
    if isinstance(region_d_data, dict):
        _apply_region_state(region_d, region_d_data)
    info_page_open = data.get("info_page_open", info_page_open)
    worst_case_region_revealed = data.get(
        "worst_case_region_revealed", worst_case_region_revealed
    )
    preset_used_ever = data.get("preset_used_ever", preset_used_ever)
    worst_case_intro_seen = data.get("worst_case_intro_seen", worst_case_intro_seen)
    # G27: validated -- non-negative ints with hits never above total; the
    # locked-in guess and last result are per-session and reset on load.
    forecast_guess = None
    forecast_last = None
    forecast_total = 0
    forecast_hits = 0
    saved_bank = data.get("carbon_bank")
    if isinstance(saved_bank, int) and not isinstance(saved_bank, bool) and 0 <= saved_bank <= CARBON_BANK_CAP:
        carbon_bank = saved_bank
    else:
        carbon_bank = 0
    convoys_sent = 0
    convoy_tax_lost = 0.0
    saved_routing = data.get("routing")
    if isinstance(saved_routing, dict):
        convoys = saved_routing.get("convoys")
        lost = saved_routing.get("tax_lost")
        if (
            isinstance(convoys, int) and not isinstance(convoys, bool) and 0 <= convoys <= 1000000
            and isinstance(lost, (int, float)) and not isinstance(lost, bool)
            and math.isfinite(lost) and 0 <= lost <= 100000000
        ):
            convoys_sent = convoys
            convoy_tax_lost = float(lost)
    saved_balance = data.get("balance_bonuses")
    if isinstance(saved_balance, int) and not isinstance(saved_balance, bool) and 0 <= saved_balance <= 1000000:
        balance_bonuses = saved_balance
    else:
        balance_bonuses = 0
    just_balanced = False
    saved_framing = data.get("framing")
    framing = saved_framing if saved_framing in FRAMINGS else "regional"
    saved_forecast = data.get("forecast")
    if isinstance(saved_forecast, dict):
        total = saved_forecast.get("total")
        hits = saved_forecast.get("hits")
        if (
            isinstance(total, int) and not isinstance(total, bool)
            and isinstance(hits, int) and not isinstance(hits, bool)
            and 0 <= hits <= total <= 1000000
        ):
            forecast_total = total
            forecast_hits = hits
    saved_log = data.get("science_log")
    if isinstance(saved_log, list):
        science_log[:] = [
            {"region": str(e.get("region", "A"))[:3], "round": int(e.get("round", 0)),
             "text": str(e.get("text", ""))}
            for e in saved_log
            if isinstance(e, dict) and isinstance(e.get("round", 0), (int, float))
        ][-SCIENCE_LOG_MAX:]
    document.getElementById("b-strategy-label-input").value = region_b.strategy_label
    document.getElementById("c-strategy-label-input").value = region_c.strategy_label
    render()
    _seed_achievement_toast_baseline()
    return True


def setup():
    for key in ("a", "b", "c"):
        document.getElementById(f"carbon-bank-{key}-button").addEventListener(
            "click", create_proxy(_make_carbon_handler(key))
        )
    document.getElementById("archive-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_archive)
    )
    document.getElementById("routing-send-button").addEventListener(
        "click", create_proxy(on_send_convoy)
    )
    for select_id in ("routing-source", "routing-dest"):
        document.getElementById(select_id).addEventListener("change", create_proxy(on_routing_change))
    document.getElementById("rate-inspector-region").addEventListener(
        "change", create_proxy(on_rate_inspector_region_change)
    )
    document.getElementById("highlights-copy-button").addEventListener(
        "click", create_proxy(on_copy_highlights)
    )
    document.getElementById("long-game-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_long_game)
    )
    document.getElementById("hold-line-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_hold_the_line)
    )
    for select_id in ("compare-run-a", "compare-run-b"):
        document.getElementById(select_id).addEventListener("change", create_proxy(on_compare_change))
    document.getElementById("temp-unit-select").addEventListener(
        "change", create_proxy(on_temp_unit_change)
    )
    document.getElementById("framing-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_framing)
    )
    document.getElementById("forecast-lock-button").addEventListener(
        "click", create_proxy(on_lock_forecast)
    )
    for key in POLICY_STANCES:
        document.getElementById(f"policy-stance-{key}-button").addEventListener(
            "click", create_proxy(_make_policy_stance_handler(key))
        )
    document.getElementById("rescue-button").addEventListener(
        "click", create_proxy(_make_rescue_handler(""))
    )
    for prefix in SECONDARY_REGIONS:
        document.getElementById(f"{prefix}-rescue-button").addEventListener(
            "click", create_proxy(_make_rescue_handler(prefix))
        )
    for category in CATEGORIES:
        document.getElementById(f"{category}-invest-button").addEventListener(
            "click", create_proxy(_make_invest_handler(category))
        )
    for prefix in SECONDARY_REGIONS:
        for category in CATEGORIES:
            document.getElementById(f"{prefix}-{category}-invest-button").addEventListener(
                "click", create_proxy(_make_secondary_invest_handler(prefix, category))
            )
        for preset_name in PRESET_WEIGHTS:
            preset_button = document.getElementById(f"{prefix}-preset-{preset_name}-button")
            preset_button.addEventListener(
                "click", create_proxy(_make_preset_handler(prefix, preset_name))
            )
            # Onboarding-tooltip audit: presets were added (G11) after the
            # tutorial/How to Play copy was written, so a returning player
            # has no permanent explanation of what a preset click actually
            # does. title= is set once here since the text is static per
            # preset, not state-dependent.
            preset_button.title = preset_tooltip_text(preset_name)
        # G4: "input" (not "change") so the label updates live as the
        # player types, without waiting for the field to lose focus.
        document.getElementById(f"{prefix}-strategy-label-input").addEventListener(
            "input", create_proxy(_make_strategy_label_handler(prefix))
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
    document.getElementById("worst-case-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_worst_case_region)
    )
    document.getElementById("changelog-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_changelog)
    )
    document.getElementById("community-compare-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_community_compare)
    )
    document.getElementById("climate-scientist-toggle-button").addEventListener(
        "click", create_proxy(on_toggle_climate_scientist)
    )
    # Belt-and-suspenders: the toast starts hidden via the static
    # `hidden` attribute in index.html, but every other stateful element
    # in this file has its shown/hidden state actively driven by code
    # rather than left to rely on markup alone (matches Continuum's own
    # documented fix for exactly this gap).
    document.getElementById("achievement-toast").hidden = True
    render()
    _seed_achievement_toast_baseline()


setup()
