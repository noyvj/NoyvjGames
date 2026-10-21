"""GridState, part 1 of 3: the grid being played (setup, costs, capacity, build, retire, maintain, wear). Mixes in
GridStateRound and GridStateExtras so the whole class still reads as game.GridState.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

import seed as seed_lib

from grid_rules import (
    AGE_WEAR_THRESHOLDS, ARBITRAGE_EFFICIENCY, ARBITRAGE_MODES, ARBITRAGE_STORAGE_MULTIPLE,
    CARBON_PRICING_FOSSIL_COST_MULTIPLIER, COAL_EULOGIES, CREW_TRAINING_MAINTENANCE_MULTIPLIER,
    DEMAND_GROWTH_PER_ROUND, DISRUPTION_PROBABILITY_SCALE, DISRUPTION_SEVERITY_SCALE, EMERGENCY_ROUNDS,
    EMISSIONS_FACTOR, FOSSIL_TYPES, GENERATION_TYPES, GRANT_CLEAN_SURCHARGE, LOADOUT_NODES,
    MAINTENANCE_AGE_REDUCTION, MAINTENANCE_COST_FRACTION, MAINTENANCE_SCHEDULE_OPTIONS,
    MAX_AGE_BREAKDOWN_PROBABILITY, MAX_DISRUPTION_PROBABILITY, MIN_COST_MULTIPLIER, NAME_MAX_LEN,
    OLD_COAL_CONTRACT_AGE, OLD_COAL_CONTRACT_PLANTS, PLANT_BASE_COST, PLANT_CAPACITY, PLANT_NAME_POOL,
    PLANT_TYPES, POLICY_LIAISON_SUBSIDY_MULTIPLIER, PROJECT_PLANT_DISCOUNT, RD_GRANT_DECAY, REFUND_FRACTION,
    RENEWABLE_COST_DECAY, RENEWABLE_SUBSIDY_COST_MULTIPLIER, RENEWABLE_TYPES, REVENUE_PER_UNIT_MET, SCENARIOS,
    SEED_CAPITAL_BONUS, SEED_GAME, STARTING_DEMAND, STARTING_FUNDS, STORAGE_PARTNERS_EFFICIENCY,
    WEAR_PERCENT_REFERENCE_AGE, _breakdown_probability_for_age, new_run_seed,
)
from grid_state_round import GridStateRound
from grid_state_extras import GridStateExtras


class GridState(GridStateRound, GridStateExtras):
    """The grid being played: plants, funds, demand, emissions, wear. Part 1 of 3 (setup, costs, capacity, build, retire,
    maintain); GridStateRound and GridStateExtras hold the rest of the methods."""
    # C-27: the numbers the practice sandbox's balance sliders can move. A real run always uses the defaults
    # (the module constants); only SandboxGridState.set_balance() ever changes them, on its own instance.
    revenue_per_unit = REVENUE_PER_UNIT_MET
    base_demand_growth = DEMAND_GROWTH_PER_ROUND
    cost_decay_override = None

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
        self.capacity_history = []
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
        self.incident_files_seen = {}
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
        self.round_snapshots = []
        self.aging_breakdown_count = 0
        self.first_90_clean_round = None
        self.last_round_recap = None
        self.boss_rounds_enabled = False
        self.bosses_beaten = 0
        self.last_boss_message = ""
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

    def connect_regional_grid(self):
        """C3: one-way, like Tide's D3 sister-settlement switch -- its
        history becomes part of this run, so it can't be turned back off."""
        self.regional_grid_connected = True

    def regional_grid_readout_text(self):
        if not self.regional_grid_connected:
            return ""
        net = self.regional_grid_total_revenue - self.regional_grid_total_shortfall_cost
        sign = "+" if net >= 0 else "-"
        return (
            f"Regional grid: {self.regional_grid_total_shared:.0f} units of spare capacity "
            f"shared so far, net {sign}{abs(net):.0f} funds effect."
        )

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
        if self.cost_decay_override is not None:
            decay = self.cost_decay_override
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

    def set_maintenance_schedule(self, plant_type, interval):
        """TODO-C23: pre-commit plant_type to an auto-maintain cadence
        (every `interval` rounds), or pass 0 to go back to manual-only."""
        if plant_type not in self.maintenance_schedule:
            return False
        if interval not in MAINTENANCE_SCHEDULE_OPTIONS:
            return False
        self.maintenance_schedule[plant_type] = interval
        return True
