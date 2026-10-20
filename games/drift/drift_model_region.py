"""RegionState (the receiving region: capacity, arrivals, strain, integration, wellbeing, the round advance) and the creation of the one live region."""

import drift_runstate as runstate
from drift_rules import (
    ACCELERATED_SEVERITY_MULTIPLIER, ARRIVALS_PER_SEVERITY_POINT, AUTOPILOT_DEFAULT_RULES,
    BACKGROUND_SEVERITY_RISE_PER_ROUND, BASE_ARRIVALS_PER_ROUND, BASE_REGIONAL_INCOME_PER_ROUND,
    CALENDAR_KINDS, CALENDAR_LOG_MAX, CAPACITY_PER_INVESTMENT, CAPACITY_TYPES, COUNCIL_BY_ID,
    CRISIS_START_ARRIVALS, CRISIS_START_FUNDS, CRISIS_START_SEVERITY, DRIFT_LOG_MAX_ENTRIES,
    GENERATIONAL_FUNDS_ROUNDS_EQUIVALENT, GENERATIONAL_GAP_CLOSURE, GENERATIONS_PROJECTED,
    GENERATION_GROWTH_MULTIPLIER, INTEGRATION_CONTRIBUTION_PER_PERSON, INTEGRATION_RATE_PER_SERVICES_UNIT,
    INVEST_COST, LEARNING_INTEGRATION_BONUS, LEARNING_STORAGE_KEY, LEDGER_FIELDS, LEDGER_MAX_ENTRIES,
    PERFECT_FIT_FUNDS_PER_STREAK, PERFECT_FIT_MARGIN, PERFECT_FIT_STREAK_CAP, POLICIES, POLICY_BASE_COST,
    POLICY_MAX_LEVEL, REALLOCATION_FUNDS_COST, REALLOCATION_LOSS_FRACTION, REALLOCATION_UNITS,
    SECOND_WAVE_ARRIVALS_MULTIPLIER, SECOND_WAVE_MIN_ROUND, SECOND_WAVE_ROUNDS,
    SECOND_WAVE_TRIGGER_INTEGRATION, SESSION_MILESTONE_INTERVAL, SPEND_KEYS, STARTING_FUNDS,
    STRAIN_LEVEL_THRESHOLDS, THRIVING_WELLBEING_SCORE, WELLBEING_FUNDS_SCALE, calendar_event_for_round,
    trend_indicator,
)


class RegionState:
    def __init__(self, starting_capacity=None, starting_funds=None, severity_rise_override=None, horizon_target=None):
        self.round_number = 1
        self.funds = STARTING_FUNDS if starting_funds is None else starting_funds
        self.capacity = {t: 0.0 for t in CAPACITY_TYPES}
        # I3: level (0..POLICY_MAX_LEVEL) of each policy lever.
        self.policy_level = {p: 0 for p in POLICIES}
        # I29: whether lessons from an earlier Thriving region apply here,
        # fixed when the region begins.
        self.learning_active = runstate.cross_region_learning
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
        # I-2: Scenario Builder overrides
        self.severity_rise_override = severity_rise_override if severity_rise_override is not None else BACKGROUND_SEVERITY_RISE_PER_ROUND
        self.horizon_target = horizon_target or 50

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
        # I-2: use override if set, otherwise default
        severity_rise = self.severity_rise_override if hasattr(self, 'severity_rise_override') else BACKGROUND_SEVERITY_RISE_PER_ROUND
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


runstate.cross_region_learning = _load_cross_region_learning()
region = RegionState()


def start_scenario(starting_capacity, starting_funds, severity_rise_override, horizon_target):
    """I-2: reset region to a fresh state with custom scenario parameters."""
    region.round_number = 1
    region.funds = starting_funds
    region.capacity = {t: starting_capacity.get(t, 0.0) for t in CAPACITY_TYPES}
    region.severity_rise_override = severity_rise_override
    region.horizon_target = horizon_target
    region.background_severity = 0.0
    region.total_arrivals = 0.0
    region.arrivals_log = []
    region.strain_log = []
    region._strain_sum = 0.0
    region._strain_count = 0
    region._ever_critical_strain = False
    region.wellbeing_log = []
    region.integrated_population = 0.0
    region.cumulative_services_investment = 0.0
    region.cumulative_integration_contribution = 0.0
    region.net_positive_round = None
    region.current_stable_streak = 0
    region.best_stable_streak = 0
    region.thriving_round = None
    region.coda_ever_viewed = False
    region.accelerated_severity_enabled = False
    region.severity_toggle_dot_baseline = None
    region.severity_density_callout_shown = False
    region.coda_just_became_available = False
    region.last_milestone_round = None
    region.last_milestone_snapshot = None
    region.milestone_just_updated = False
    region.subscore_log = []
    region.region_name = ""
    region.coda_legacy_choice = None
    region.crisis_start_enabled = False
    region.spillover_arrivals = 0.0
    region.spend_by_type = {key: 0.0 for key in SPEND_KEYS}
    region.round_spend = {key: 0.0 for key in SPEND_KEYS}
    region.ledger = []
    region.round_buys = 0
    region.rewind_used_round = None
    region.perfect_fit_streak = 0
    region.best_perfect_fit_streak = 0
    region.calendar_enabled = False
    region.braced_rounds = []
    region.calendar_log = []
    region.council_picks = []
    region.autopilot = dict(AUTOPILOT_DEFAULT_RULES)
    region.stars_banked = None
    region.roi_log = []
    region.second_wave_start_round = None
    region.second_wave_status = None
    region.second_wave_rounds_left = 0
    region.second_wave_peak_strain = 0.0
    region.second_wave_result = None
    runstate.coda_visible = False
    runstate.calendar_note_text = ""
    runstate.summary_note_text = ""
    runstate.load_note_text = ""
    runstate.tier_note_text = ""
    runstate.assist_mode = "off"
    runstate.confirm_threshold = 0
    runstate.save_baseline_round = 1
    runstate.nudge_snooze_round = 0
    runstate.glossary_open = None
    runstate.glossary_pinned = False
    runstate.report_open = False
    runstate.report_note_text = ""
    runstate.band_note_text = ""
    runstate.non_visual_mode = False
    runstate.scenario_custom_run = True
