"""GridState, part 3 of 3 (a mixin): surprise grants, the peek forecast, scoring and projection, demand response and
policy levers.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

from grid_rules import (
    BAU_EMISSIONS_FACTOR, DEMAND_ANALYTICS_COST_MULTIPLIER, DEMAND_RESPONSE_BASE_COST,
    DEMAND_RESPONSE_COST_GROWTH, DEMAND_RESPONSE_MIN_GROWTH, DEMAND_RESPONSE_REDUCTION_PER_LEVEL,
    GENERATION_TYPES, GRADE_THRESHOLDS, GRANT_CLEAN_FUNDS, GRANT_CLEAN_ROUNDS, GRANT_CONTEST_ROUNDS,
    GRANT_FINE, GRANT_MIN_ROUND, GRANT_ODDS, GRANT_ORDER, GRANT_REPAIR_AGE, GRANT_SPONSOR_DEMAND,
    GRANT_SPONSOR_FUNDS, PEEK_FEE, PERFECT_ROUND_MAX_STEPS, PERFECT_ROUND_STEP, PLANT_TYPES,
    POLICY_LEVER_DURATION, POLICY_LIAISON_EXTRA_ROUNDS, PROJECTION_ROUNDS, STEEP_DEMAND_GROWTH_MULTIPLIER,
)


class GridStateExtras:
    """GridState, part 3 of 3: grants, the peek forecast, scoring and projection, demand response and policy levers."""

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
        growth = self.base_demand_growth
        if self.steeper_demand_growth_enabled:
            growth *= STEEP_DEMAND_GROWTH_MULTIPLIER
        growth -= self.demand_response_level * DEMAND_RESPONSE_REDUCTION_PER_LEVEL
        # The floor is the normal 3, or lower when a sandbox slider sets the base pace below it.
        return max(min(DEMAND_RESPONSE_MIN_GROWTH, self.base_demand_growth), growth)

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
