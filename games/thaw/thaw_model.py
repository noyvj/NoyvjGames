"""RegionState (one region: funds, temperature, melt feedback, restoration, rescue), the three managed regions and Region D, and the helpers that read the run mode."""

import thaw_runstate as runstate
from thaw_rules import (
    ACCEL_HISTORY_MAX, BASE_TEMP_RISE_PER_ROUND, CATEGORIES, CRITICAL_ACCELERATION_FACTOR,
    DAMPENING_PER_MONITOR_UNIT, DAMPENING_PER_PRESERVE_UNIT, FEEDBACK_RATE_PER_DEGREE_OVER,
    HOLD_LINE_CAP_EROSION, HOLD_LINE_ESCALATION_EVERY, HOLD_LINE_ESCALATION_STEP, HOLD_LINE_EVENTS,
    HOLD_LINE_MIN_CAP, HOLD_LINE_MIN_UNTIPPED, INVEST_COST, LONG_GAME_INCOME_SCALE, LONG_GAME_WARMING_SCALE,
    MAX_FEEDBACK_DAMPENING, MELT_THRESHOLD, OUTPUT_INCOME_PER_UNIT, POLICY_STANCES, RESCUE_COST,
    RESCUE_DAMPENING_BONUS, RESCUE_DURATION_ROUNDS, RESCUE_MAX_DAMPENING, RESTORATION_MAX_ACCELERATION,
    RESTORATION_MAX_PER_ROUND, RESTORATION_PER_PRESERVE_UNIT, RESTORATION_STREAK_ROUNDS,
    SECOND_WARMING_MILESTONE, STARTING_FUNDS,
)


def deg(value, digits=1, plus=False):
    """G-13: a temperature rise as text in the chosen unit. Celsius is the plain degree sign the
    game always used, so existing text is unchanged by default."""
    prefix = "+" if plus else ""
    if runstate.temp_unit == "f":
        return f"{prefix}{value * 1.8:.{digits}f}\u00b0F"
    if runstate.temp_unit == "k":
        return f"{prefix}{value:.{digits}f} K"
    return f"{prefix}{value:.{digits}f}\u00b0"


def warming_scale():
    return LONG_GAME_WARMING_SCALE if runstate.long_game else 1.0


def output_income_per_unit():
    return OUTPUT_INCOME_PER_UNIT * (LONG_GAME_INCOME_SCALE if runstate.long_game else 1.0)


def escalation_level(round_number):
    """GG-2: how many escalation events have happened by the start of this round (0 outside
    Hold the Line). Events land at the start of rounds 5, 9, 13, ..."""
    if not runstate.hold_the_line:
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
        # G-16: the feedback dampening in effect at the end of each round, parallel to
        # temperature_history (older saves have none, which the hover readout says plainly).
        self.dampening_history = []

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
        self.dampening_history.append(round(self.feedback_dampening_fraction(), 3))
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
    return not runstate.run_over and all(r.round_number == 1 for r in (region, region_b, region_c, region_d))


def set_hold_the_line(enabled):
    """Choose the mode. Only before round 1 is played, never together with the long game."""
    if not can_toggle_hold_the_line():
        return False
    if enabled and runstate.long_game:
        return False
    runstate.hold_the_line = bool(enabled)
    return True


def average_saved(regions=None):
    rs = [r for _label, r in _managed()] if regions is None else regions
    return sum(max(0.0, r.temperature_saved()) for r in rs) / len(rs)
