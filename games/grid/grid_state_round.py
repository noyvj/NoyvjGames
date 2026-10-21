"""GridState, part 2 of 3 (a mixin): the round itself. advance_round and what it runs: arbitrage, the regional grid, the
emergency, scheduled maintenance, revenue-capacity and weather maths.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

from grid_rules import (
    AGING_BREAKDOWN_COST_FRACTION, ARBITRAGE_PEAK_PRICE_MULTIPLIER, BAU_EMISSIONS_FACTOR,
    DAMAGE_SEVERITY_THRESHOLD, EMERGENCY_HOLD_ROUNDS, EMISSIONS_FACTOR, FOSSIL_TYPES, GENERATION_TYPES,
    GLOBAL_AVG_FOSSIL_EMISSIONS_FACTOR, GLOBAL_AVG_FOSSIL_SHARE, MAX_REVENUE_LOSS_FRACTION, PLANT_BASE_COST,
    PLANT_CAPACITY, PLANT_TYPES, POLICY_LEVER_INTERVAL, RECORD_CLEAN_SHARE, REGIONAL_DEMAND_FRACTION,
    REGIONAL_REVENUE_PER_UNIT_SHARED, REGIONAL_SHORTFALL_COST_PER_UNIT, RENEWABLE_TYPES,
    WEATHER_LOG_MAX_ENTRIES, WEATHER_VARIANCE_FRACTION, SCENARIOS, ELECTRIFICATION_EVENTS,
    ELECTRIFICATION_NOTICE_ROUNDS,
)


class GridStateRound:
    """GridState, part 2 of 3: the round itself (advance_round and what it runs: arbitrage, the regional grid,
    the emergency, scheduled maintenance, the revenue-capacity and weather maths). GridState (in grid_state.py) mixes the parts together."""

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
        revenue = sold * self.revenue_per_unit * ARBITRAGE_PEAK_PRICE_MULTIPLIER
        self.stored_energy -= sold
        self.arbitrage_revenue_total += revenue
        self.last_arbitrage = {"mode": "discharge", "units": sold, "revenue": revenue}
        return revenue

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
        revenue = met_demand * self.revenue_per_unit
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
        self.demand += self.electrification_jump(self.round_number)

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
        self.capacity_history.append(self.total_capacity())
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

    def renewable_weather_factors(self, round_number=None):
        """The output factor each renewable type gets in a round with weather variability on, in the
        same order and from the same stream advance_round() uses (so a peek is exact)."""
        rng = self.stream("weather", round_number)
        out = {}
        for plant_type in GENERATION_TYPES:
            if plant_type in RENEWABLE_TYPES:
                out[plant_type] = 1 + (rng.random() * 2 - 1) * WEATHER_VARIANCE_FRACTION
        return out

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

    def electrification_active(self):
        """Returns True if the current scenario has electrification enabled."""
        return bool(SCENARIOS[self.scenario].get("electrification"))

    def electrification_jump(self, round_number):
        """Returns the demand increase for an electrification event at `round_number`, or 0."""
        if not self.electrification_active():
            return 0
        for event in ELECTRIFICATION_EVENTS:
            if event["round"] == round_number:
                return event["demand"]
        return 0

    def electrification_notice(self):
        """Returns (event, rounds_away) for the earliest upcoming electrification event within notice range, or None."""
        if not self.electrification_active():
            return None
        for event in ELECTRIFICATION_EVENTS:
            diff = event["round"] - self.round_number
            if 0 <= diff <= ELECTRIFICATION_NOTICE_ROUNDS:
                return (event, diff)
        return None
