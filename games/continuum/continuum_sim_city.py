"""CityState: one settlement at one point in time (workers, buildings, one season of production, growth, land health, score history).
Ask for this file to change how a season is simulated.
Part of the split of the old single-file sim.py: see "File map" in games/continuum/CLAUDE.md.
"""

from continuum_sim_tables import (
    BUILDING_COST,
    DEFAULT_SCENARIO,
    FARMLAND_YIELD_BONUS,
    FIRST_ERA,
    GRANARY_STORAGE,
    HEARTH_SERVES,
    MIN_POPULATION,
    ROLES,
    SCENARIOS,
    SHELTER_CAPACITY,
    START_ALLOCATION,
    START_BUILDINGS,
    START_KNOWLEDGE,
    START_SURPLUS,
    TOOLWORKS_CRAFT_BONUS,
    era_index,
    roles_for_era,
    scenario_config,
)
from continuum_sim_numbers import (
    ADMINISTRATORS_PER_CANAL,
    ARCHITECTS_PER_RING,
    BASE_FOOD_STORAGE,
    CANAL_YIELD_BONUS,
    FOOD_PER_FARMER,
    FOOD_PER_FORAGER,
    FOOD_PER_PERSON,
    GROWTH_MIN_LAND_HEALTH,
    GROWTH_RATE,
    HOLDING_RESIDENTS_PER_RELAY,
    KNOWLEDGE_PER_KEEPER,
    LAND_DEGRADE_PER_UNIT,
    LAND_REGEN,
    LAND_SUSTAINABLE_YIELD,
    MATERIALS_PER_FACTORY_WORKER,
    MATERIALS_PER_GATHERER,
    MATERIALS_PER_TOOL,
    MIN_LAND_HEALTH,
    OUTLYING_SUPPLY_PER_RESIDENT,
    PLANNER_SPRAWL_MITIGATION,
    POLLUTION_GROWTH_PENALTY_WEIGHT,
    POLLUTION_NATURAL_DECAY,
    POLLUTION_PER_FACTORY_WORKER,
    PUBLIC_WORKS_COVERAGE_PER_BUILDING,
    RELAY_LAND_YIELD,
    RELAY_THROUGHPUT,
    RING_CAPACITY_PER_BUILDING,
    SANITATION_ABSORPTION_PER_BUILDING,
    SCORE_COLLAPSE_THRESHOLD,
    SCORE_HISTORY_MAX_ENTRIES,
    SCORE_RECOVERY_THRESHOLD,
    SPRAWL_EXTRACTION_PENALTY_WEIGHT,
    SPRAWL_NATURAL_DECAY,
    SPRAWL_PER_NEW_RESIDENT,
    STARVATION_SEVERITY,
    SURPLUS_CONVERSION_RATE,
    TOOLS_PER_CRAFTER,
    TOOLS_PER_GUILDMASTER,
    TOOL_DECAY_RATE,
    TOOL_EFFECT,
    TRANSIT_HUB_ABSORPTION_PER_BUILDING,
    WAYFINDER_CARRY,
    effects_or_neutral,
)


class CityState:
    """One settlement, at one point in time, in one era."""

    def __init__(self, era=FIRST_ERA, scenario=DEFAULT_SCENARIO):
        # K12 -- resolved once, at construction, against SCENARIOS' own
        # keys rather than trusted verbatim, so a bogus id (a stale
        # constant from a future build, a hand-edited save value) can
        # never linger as `self.scenario` -- same "validate against the
        # schema's own source of truth" standard save.restore_city() holds
        # `era` to. `scenario_config()` already degrades gracefully for
        # the *values* used below; this is what keeps the *label* honest
        # about which scenario's numbers were actually applied.
        self.scenario = scenario if scenario in SCENARIOS else DEFAULT_SCENARIO
        config = scenario_config(self.scenario)
        # K18 -- opt-in stricter sustainability variant, off by default.
        # Unlike `scenario` (a one-time starting condition), this can be
        # flipped at any time during play, the same "toggle anytime"
        # shape Grid's own steeper-demand-growth/weather-variability
        # toggles use -- see sustainability.py for what it actually
        # tightens.
        self.hard_mode = False
        self.era = era
        self.season = 1
        self.population = config["population"]
        self.growth_progress = 0.0
        self.resources = {
            "food": config["food"],
            "materials": config["materials"],
            "tools": config["tools"],
            # O-8: an optional per-scenario key (only Refuge sets it); every
            # other scenario keeps the old START_KNOWLEDGE, byte for byte.
            "knowledge": config.get("knowledge", START_KNOWLEDGE),
            "surplus": START_SURPLUS,
        }
        self.allocation = dict(START_ALLOCATION)
        self.buildings = dict(START_BUILDINGS)
        self.land_health = config["land_health"]
        # Industrial+ (Milestone 11): a lagged 0..1 stock, same shape as
        # land_health -- see the "pollution and the growth-side cost of
        # industry" constants above. Always 0.0 before Industrial, both
        # because nothing produces it yet and because the season loop's
        # own era guard forces it there defensively.
        self.pollution = 0.0
        # Digital+ (Milestone 12): a second lagged 0..1 stock, same shape as
        # pollution -- see the "sprawl and the growth-side cost of
        # unmanaged density" constants above. Always 0.0 before Digital,
        # both because nothing produces it yet and because the season
        # loop's own era guard forces it there defensively.
        self.sprawl = 0.0
        # Relay Age+ (R2-K26): 0..1, the share of the holdings' supply need
        # the last season's relay delivery actually met -- a lagged stock,
        # same position in the season loop as land_health/pollution/sprawl
        # (this season's land yield reads LAST season's value). 1.0 means
        # "nothing wrong" (also the value with no holdings at all).
        self.outlying_served = 1.0
        # Last-season signals the sustainability score reads. Seeded so the
        # score is meaningful on season 1, before any season has run.
        self.fed_fraction = 1.0
        self.last_extraction = 0.0
        self.last_sustainable_yield = LAND_SUSTAINABLE_YIELD
        self.last_report = None
        # The sustainability score is computed by sustainability.py as a
        # pure function of this state, but its history is state — it gets
        # saved, snapshotted, and eventually graphed — so it lives here.
        # game.py calls record_score() with one value per completed season.
        # Z25: capped at SCORE_HISTORY_MAX_ENTRIES (see record_score below)
        # to stop this list -- and every era_snapshot's own copy of it --
        # from growing unbounded over a very long session.
        self.score_history = []
        # Two facts derived from score_history that must survive the cap
        # above intact, since both are read by real features (the K17
        # peak-score/efficiency-rank readout, and the "ever recovered from
        # collapse" achievement) that need the TRUE lifetime history, not
        # just whatever's left in the capped tail. Updated incrementally by
        # record_score() the instant each score is recorded -- before any
        # later cap-driven truncation could discard the evidence.
        self.peak_score = None
        self.lowest_score_seen = None
        self.ever_recovered_from_collapse = False
        # K11 (challenges.py) -- the opt-in civic-challenge state. Kept as a
        # plain literal here (challenges.py imports sim, so sim can't import
        # it back); save.py validates it on load via challenges.clean().
        self.challenge = {"active": None, "completed": {}, "failed": 0}
        # K19/K13/K25/K8 (trajectory.py) -- one [output_index, era_index,
        # population, livability] point per completed season, capped.
        self.trajectory = []
        # K10 -- completed seasons in a row with everyone fed and nobody
        # dying. Reset by any hunger or death, the same "clean streak" idea
        # as Grid's own.
        self.calm_streak = 0

    # --- allocation -----------------------------------------------------
    def assigned_workers(self):
        return sum(self.allocation.values())

    def idle_workers(self):
        return max(0, self.population - self.assigned_workers())

    def assign_worker(self, role):
        if self.idle_workers() <= 0:
            return False
        self.allocation[role] += 1
        return True

    def unassign_worker(self, role):
        if self.allocation[role] <= 0:
            return False
        self.allocation[role] -= 1
        return True

    def clamp_allocation(self):
        """Trims assignments back into the population, worst-case first.

        Needed because population can fall (starvation) without the player
        touching the allocation, and later because loading a save or
        revisiting an era can drop a smaller population onto an allocation
        sized for a bigger one.
        """
        overflow = self.assigned_workers() - self.population
        if overflow <= 0:
            return
        for role in reversed(ROLES):
            if overflow <= 0:
                break
            take = min(overflow, self.allocation[role])
            self.allocation[role] -= take
            overflow -= take

    def role_diversity(self):
        """0..1 — how evenly the workforce is spread across roles.

        1.0 means every role is staffed equally; 0.0 means everyone does the
        same job. Read by the resilience half of the sustainability score:
        a settlement that does exactly one thing has nothing to fall back on.

        Measured against `roles_for_era(self.era)`, not the flat global
        `ROLES` list — a settlement still in the Tribal era shouldn't have
        its "how evenly spread" denominator diluted by a Farmers slot it
        can't even assign to yet. This is what keeps every Tribal-era
        sustainability number byte-identical to before Milestone 8 added a
        second era's roles onto the same allocation dict.
        """
        assigned = self.assigned_workers()
        if assigned <= 0:
            return 0.0
        unlocked = roles_for_era(self.era)
        shares = [self.allocation[r] / assigned for r in unlocked]
        concentration = sum(s * s for s in shares)
        even = 1.0 / len(unlocked)
        if concentration <= even:
            return 1.0
        return (1.0 - concentration) / (1.0 - even)

    # --- capacities -----------------------------------------------------
    def housing_capacity(self, effects=None):
        effects = effects_or_neutral(effects)
        capacity = self.buildings["shelter"] * SHELTER_CAPACITY + effects["housing_bonus"]
        if era_index(self.era) >= era_index("relay"):
            # Each relay's holding houses its own residents (R2-K26).
            capacity += self.buildings["relay_stations"] * HOLDING_RESIDENTS_PER_RELAY
        return capacity

    def food_storage_capacity(self, effects=None):
        effects = effects_or_neutral(effects)
        return (
            BASE_FOOD_STORAGE
            + self.buildings["granary"] * GRANARY_STORAGE
            + effects["food_storage_bonus"]
        )

    def culture_capacity(self, effects=None):
        """How many people the settlement's social infrastructure serves."""
        effects = effects_or_neutral(effects)
        return self.buildings["hearth"] * HEARTH_SERVES * (1.0 + effects["culture_bonus"])

    def tool_factor(self):
        if self.population <= 0:
            return 1.0
        per_person = min(1.0, self.resources["tools"] / self.population)
        return 1.0 + TOOL_EFFECT * per_person

    def sustainable_yield(self, effects=None):
        effects = effects_or_neutral(effects)
        return (LAND_SUSTAINABLE_YIELD + self.relay_land_yield()) * effects["regen_mult"]

    def relay_land_yield(self):
        """Extra sustainable land yield the outlying holdings open up
        (Relay Age+), scaled by how well they were supplied last season --
        an unsupplied holding contributes nothing, which is what makes an
        over-extended network worse than not expanding."""
        if era_index(self.era) < era_index("relay"):
            return 0.0
        return self.buildings["relay_stations"] * RELAY_LAND_YIELD * max(0.0, min(1.0, self.outlying_served))

    def holdings_residents(self):
        """People living in the outlying holdings (Relay Age+): each relay
        holds up to HOLDING_RESIDENTS_PER_RELAY of them, out of the whole
        population. Zero before the Relay Age."""
        if era_index(self.era) < era_index("relay"):
            return 0
        return min(self.population, self.buildings["relay_stations"] * HOLDING_RESIDENTS_PER_RELAY)

    def relay_throughput(self, effects=None):
        """Surplus the network can move per season: the smaller of what
        Wayfinders can haul and what the stations' ceiling allows."""
        if era_index(self.era) < era_index("relay"):
            return 0.0
        effects = effects_or_neutral(effects)
        hauling = self.allocation["wayfinders"] * WAYFINDER_CARRY
        ceiling = self.buildings["relay_stations"] * RELAY_THROUGHPUT * (1.0 + effects["relay_bonus"])
        return max(0.0, min(hauling, ceiling))

    def public_works_coverage(self, effects=None):
        """How many people Public Works can meaningfully protect against a
        bad season (flood, disease, fire) -- read by the resilience half of
        the sustainability score (Milestone 10), not by anything in the
        season loop below. Same shape as culture_capacity()'s
        `buildings * PER_BUILDING * (1 + bonus)` pattern."""
        effects = effects_or_neutral(effects)
        return (
            self.buildings["public_works"]
            * PUBLIC_WORKS_COVERAGE_PER_BUILDING
            * (1.0 + effects["public_works_bonus"])
        )

    def habitat_capacity(self, effects=None):
        """How many people the settlement's off-world Habitat Rings can
        actually serve WELL -- not merely hold, but serve at the layout
        quality Architects have actually designed into them (Space Age+,
        see the "off-world habitat layout" comment block above). Read only
        by sustainability.py's provisions() from Space Age on; never by
        anything in the season loop below, and deliberately not a growth
        lever the way pollution/sprawl were -- see CLAUDE.md's Milestone 13
        build notes. Forced to 0.0 before Space Age rather than merely
        trusting it stays there by construction -- the same defensive
        era-gate discipline every prior era-specific mechanic in this file
        has been held to."""
        if era_index(self.era) < era_index("space"):
            return 0.0
        effects = effects_or_neutral(effects)
        if self.buildings["habitat_rings"] <= 0:
            return 0.0
        layout_quality = min(
            1.0,
            self.allocation["architects"]
            / (self.buildings["habitat_rings"] * ARCHITECTS_PER_RING),
        )
        return (
            self.buildings["habitat_rings"]
            * RING_CAPACITY_PER_BUILDING
            * layout_quality
            * (1.0 + effects["habitat_layout_bonus"])
        )

    # --- building -------------------------------------------------------
    def can_build(self, building):
        return self.resources["materials"] >= BUILDING_COST[building]

    def build(self, building):
        if not self.can_build(building):
            return False
        self.resources["materials"] -= BUILDING_COST[building]
        self.buildings[building] += 1
        return True

    # --- sustainability score history ------------------------------------
    def _record_score_derivatives(self, score):
        """Updates peak_score/lowest_score_seen/ever_recovered_from_collapse
        for one more observed score. Factored out of record_score() so
        recompute_score_derivatives_from_history() can replay an existing
        list through the exact same logic (used when restoring a save from
        before these fields existed — see save.py's restore_city())."""
        if self.peak_score is None or score > self.peak_score:
            self.peak_score = score
        if not self.ever_recovered_from_collapse:
            if (
                self.lowest_score_seen is not None
                and self.lowest_score_seen < SCORE_COLLAPSE_THRESHOLD
                and score >= SCORE_RECOVERY_THRESHOLD
            ):
                self.ever_recovered_from_collapse = True
            if self.lowest_score_seen is None or score < self.lowest_score_seen:
                self.lowest_score_seen = score

    def record_score(self, score):
        """Appends one season's sustainability score, trimming the front of
        score_history down to SCORE_HISTORY_MAX_ENTRIES once it grows past
        that cap (Z25). Safe to cap because the two facts that actually
        need the full lifetime history (peak_score, ever_recovered_from_
        collapse) are updated here, before the trim, not derived from the
        list afterward."""
        self._record_score_derivatives(score)
        self.score_history.append(score)
        if len(self.score_history) > SCORE_HISTORY_MAX_ENTRIES:
            del self.score_history[: len(self.score_history) - SCORE_HISTORY_MAX_ENTRIES]

    def recompute_score_derivatives_from_history(self):
        """Rebuilds peak_score/lowest_score_seen/ever_recovered_from_collapse
        from whatever's currently in score_history. Only meaningful for a
        save written before these fields existed — see save.py's
        restore_city(), the only caller."""
        self.peak_score = None
        self.lowest_score_seen = None
        self.ever_recovered_from_collapse = False
        for value in self.score_history:
            self._record_score_derivatives(value)

    # --- the season loop ------------------------------------------------
    def advance_season(self, effects=None):
        """Runs one season and returns a report dict describing what happened.

        Order matters and is deliberate: produce, then craft, then eat, then
        spoil, then live or die, then account for what the land took. The
        report is what the UI narrates and what the tests assert against.
        """
        effects = effects_or_neutral(effects)
        self.clamp_allocation()

        tool_factor = self.tool_factor()

        # 1. Harvest. Both gathering yields scale with tools and with how
        #    healthy the land still is — the loop that punishes over-use.
        #    Farmers (Agrarian+) are a second way to get food, not a
        #    separate economy: farmland raises their base yield the same
        #    way a knapping site raises a crafter's, but they still scale
        #    with the same tool_factor/land_health/food_yield_mult as
        #    foraging, and both feed the same extraction total below —
        #    settled agriculture is more productive here, not exempt from
        #    what the land can sustain.
        farm_bonus = 1.0 + self.buildings["farmland"] * FARMLAND_YIELD_BONUS
        # Canals (Classical+): a per-canal bonus on top of farmland, but only
        # in proportion to how fully Administrators staff it (see the
        # CANAL_YIELD_BONUS note above) -- a built-but-unstaffed canal adds
        # nothing, which is the point, not an edge case to special-case away.
        if self.buildings["canals"] > 0:
            canal_staffing = min(
                1.0,
                self.allocation["administrators"]
                / (self.buildings["canals"] * ADMINISTRATORS_PER_CANAL),
            )
        else:
            canal_staffing = 0.0
        canal_bonus = (
            self.buildings["canals"]
            * (CANAL_YIELD_BONUS + effects["canal_yield_bonus"])
            * canal_staffing
        )
        farm_bonus += canal_bonus
        food_gathered = (
            self.allocation["foragers"] * FOOD_PER_FORAGER
            + self.allocation["farmers"] * FOOD_PER_FARMER * farm_bonus
        ) * tool_factor * self.land_health * effects["food_yield_mult"]
        #    Factory Workers (Industrial+) are a second way to get
        #    materials, not a separate economy -- same tool_factor/
        #    land_health/materials_yield_mult chain as Gatherers, and the
        #    same shared extraction total below, the same discipline every
        #    prior era's new production role has been held to.
        materials_gathered = (
            (
                self.allocation["gatherers"] * MATERIALS_PER_GATHERER
                + self.allocation["factory_workers"] * MATERIALS_PER_FACTORY_WORKER
            )
            * tool_factor
            * self.land_health
            * effects["materials_yield_mult"]
        )
        self.resources["materials"] += materials_gathered

        # 2. Craft. Tools cost materials, so crafting competes with building.
        #    Guildmasters (Medieval+) are a second way to make tools, not a
        #    separate economy: the same Knapping Site bonus and the same
        #    tool_yield_mult apply to them, and their output feeds the same
        #    shared tool stock -- specialised training is more productive
        #    here, not exempt from what materials/effects allow.
        craft_bonus = 1.0 + self.buildings["toolworks"] * TOOLWORKS_CRAFT_BONUS
        wanted_tools = (
            (
                self.allocation["crafters"] * TOOLS_PER_CRAFTER
                + self.allocation["guildmasters"] * TOOLS_PER_GUILDMASTER
            )
            * craft_bonus
            * effects["tool_yield_mult"]
        )
        affordable_tools = self.resources["materials"] / MATERIALS_PER_TOOL
        tools_made = max(0.0, min(wanted_tools, affordable_tools))
        self.resources["materials"] -= tools_made * MATERIALS_PER_TOOL
        self.resources["tools"] += tools_made

        # 3. Knowledge — the research tree's currency (spent from Milestone 3).
        knowledge_made = (
            self.allocation["keepers"] * KNOWLEDGE_PER_KEEPER * effects["knowledge_mult"]
        )
        self.resources["knowledge"] += knowledge_made

        # 4. Tools wear out. Neglecting crafting entirely is a slow decline,
        #    not a sudden one.
        self.resources["tools"] *= 1.0 - TOOL_DECAY_RATE

        # 5. Eat.
        self.resources["food"] += food_gathered
        needed = self.population * FOOD_PER_PERSON
        consumed = min(self.resources["food"], needed)
        self.resources["food"] -= consumed
        fed_fraction = 1.0 if needed <= 0 else consumed / needed
        self.fed_fraction = fed_fraction

        # 6. Spoilage — food beyond what the settlement can store is lost.
        #    Agrarian+ (Milestone 8): some of what would spoil is preserved
        #    as trade-ready `surplus` instead, rather than pure waste — see
        #    the SURPLUS_CONVERSION_RATE note above. Either way, everything
        #    beyond storage_capacity leaves `food`; only where it goes
        #    (lost vs. banked) differs by era.
        storage_capacity = self.food_storage_capacity(effects)
        would_spoil = max(0.0, self.resources["food"] - storage_capacity)
        if era_index(self.era) >= era_index("agrarian"):
            conversion_rate = min(1.0, SURPLUS_CONVERSION_RATE + effects["surplus_conversion_bonus"])
            surplus_banked = would_spoil * conversion_rate
        else:
            surplus_banked = 0.0
        spoiled = would_spoil - surplus_banked
        self.resources["food"] -= would_spoil
        self.resources["surplus"] += surplus_banked

        # 7. Population. Starvation kills; surplus plus housing headroom grows.
        births = 0
        deaths = 0
        if fed_fraction < 1.0:
            unfed = (1.0 - fed_fraction) * self.population
            toll = max(1, int(round(unfed * STARVATION_SEVERITY)))
            survivors = max(MIN_POPULATION, self.population - toll)
            deaths = self.population - survivors
            self.population = survivors
            self.growth_progress = 0.0
        else:
            housing = self.housing_capacity(effects)
            has_room = self.population < housing
            surplus_ratio = 0.0 if needed <= 0 else self.resources["food"] / needed
            if has_room and surplus_ratio >= 1.0 and self.land_health > GROWTH_MIN_LAND_HEALTH:
                # Industrial+ (Milestone 11): the growth-side half of the
                # pollution mechanic -- reads self.pollution as it stood at
                # the END of the previous season (this season's own
                # pollution output is computed in step 8b below, same
                # lagged-stock ordering land_health already uses relative
                # to this same growth check). A soft, proportional slow-
                # down, not a hard block -- see the POLLUTION_GROWTH_PENALTY_
                # WEIGHT constant's own comment for why that shape was
                # chosen over copying land_health's hard gate.
                if era_index(self.era) >= era_index("industrial"):
                    pollution_penalty = self.pollution * POLLUTION_GROWTH_PENALTY_WEIGHT
                else:
                    pollution_penalty = 0.0
                effective_growth_rate = GROWTH_RATE * (1.0 - pollution_penalty)
                self.growth_progress += effective_growth_rate * min(1.0, surplus_ratio)
                while self.growth_progress >= 1.0 and self.population < housing:
                    self.population += 1
                    self.growth_progress -= 1.0
                    births += 1
        self.clamp_allocation()

        # 8. What the land gave up, and whether it can take it.
        extraction = (food_gathered + materials_gathered) * effects["extraction_efficiency"]
        # Digital+ (Milestone 12): sprawl amplifies how much land pressure
        # this same extraction total creates -- reads self.sprawl as it
        # stood at the END of the previous season (this season's own sprawl
        # output is computed in step 8c below, the same lagged-stock
        # ordering pollution's own step 8b already uses relative to this
        # same land-pressure calculation). See SPRAWL_EXTRACTION_PENALTY_
        # WEIGHT's own comment for why this is a different lever from
        # pollution's direct GROWTH_RATE multiplier.
        if era_index(self.era) >= era_index("digital"):
            extraction *= 1.0 + self.sprawl * SPRAWL_EXTRACTION_PENALTY_WEIGHT
        sustainable = self.sustainable_yield(effects)
        if extraction > sustainable:
            self.land_health -= (extraction - sustainable) * LAND_DEGRADE_PER_UNIT
        else:
            self.land_health += LAND_REGEN * effects["regen_mult"]
        self.land_health = max(MIN_LAND_HEALTH, min(1.0, self.land_health))
        self.last_extraction = extraction
        self.last_sustainable_yield = sustainable

        # 8b. Industrial pollution (Industrial+) -- updated last, the same
        # lagged-stock position land_health's own update sits in relative
        # to this season's growth check above. Factory Workers are the only
        # source; Sanitation Works (built, never staffed) and a small
        # constant natural decay are the only things that bring it back
        # down. Forced to exactly 0.0 before Industrial rather than merely
        # trusting it stayed there by construction -- the same defensive
        # era-gate discipline surplus_banked/canal_bonus/public_works_
        # coverage were all held to.
        if era_index(self.era) >= era_index("industrial"):
            pollution_produced = (
                self.allocation["factory_workers"]
                * POLLUTION_PER_FACTORY_WORKER
                * effects["pollution_output_mult"]
            )
            pollution_absorbed = (
                self.buildings["sanitation_works"]
                * SANITATION_ABSORPTION_PER_BUILDING
                * (1.0 + effects["sanitation_bonus"])
            )
            self.pollution = max(
                0.0,
                min(
                    1.0,
                    self.pollution
                    + pollution_produced
                    - pollution_absorbed
                    - POLLUTION_NATURAL_DECAY,
                ),
            )
        else:
            self.pollution = 0.0

        # 8c. Digital sprawl (Digital+) -- updated last, same lagged-stock
        # position as pollution's step 8b above, and for the same reason:
        # this season's land-pressure calculation in step 8 already read
        # whatever `self.sprawl` was at the END of the PREVIOUS season, not
        # anything computed here. Produced by unmanaged population growth
        # (`births`, from step 7 above) per the National Geographic source's
        # "urban areas grew 1.28x faster than their populations" finding;
        # Urban Planners work every season regardless of growth (their whole
        # job is managing it before it happens), Transit Hubs (built, never
        # staffed) absorb what has already accumulated, and a small natural
        # decay always pulls it down a little on its own. Forced to exactly
        # 0.0 before Digital rather than merely trusting it stayed there by
        # construction -- the same defensive era-gate discipline pollution/
        # surplus_banked/canal_bonus/public_works_coverage were all held to.
        if era_index(self.era) >= era_index("digital"):
            sprawl_produced = births * SPRAWL_PER_NEW_RESIDENT * effects["sprawl_output_mult"]
            sprawl_mitigated = self.allocation["planners"] * PLANNER_SPRAWL_MITIGATION
            sprawl_absorbed = (
                self.buildings["transit_hubs"]
                * TRANSIT_HUB_ABSORPTION_PER_BUILDING
                * (1.0 + effects["transit_bonus"])
            )
            self.sprawl = max(
                0.0,
                min(
                    1.0,
                    self.sprawl
                    + sprawl_produced
                    - sprawl_mitigated
                    - sprawl_absorbed
                    - SPRAWL_NATURAL_DECAY,
                ),
            )
        else:
            self.sprawl = 0.0

        # 8d. Relay supply (Relay Age+) -- what the relay links carry out to
        # the holdings this season. Updated last, the same lagged-stock
        # position pollution/sprawl use: this season's land yield (step 8)
        # already read LAST season's `outlying_served`. Draws banked
        # `surplus`, the stock Agrarian's spoilage step feeds, so the very
        # thing that used to be only an equity risk if hoarded is now what
        # keeps the holdings alive. Forced to 1.0 ("no problem") before the
        # Relay Age or with no holdings, the same defensive era-gate
        # discipline every earlier mechanic uses.
        relay_delivered = 0.0
        outlying_needed = 0.0
        if era_index(self.era) >= era_index("relay") and self.holdings_residents() > 0:
            outlying_needed = self.holdings_residents() * OUTLYING_SUPPLY_PER_RESIDENT
            relay_delivered = min(
                outlying_needed, self.relay_throughput(effects), self.resources["surplus"]
            )
            self.resources["surplus"] -= relay_delivered
            self.outlying_served = max(0.0, min(1.0, relay_delivered / outlying_needed))
        else:
            self.outlying_served = 1.0

        self.season += 1

        if deaths > 0 or fed_fraction < 1.0:
            self.calm_streak = 0
        else:
            self.calm_streak += 1

        # Public Works coverage (Medieval+) -- purely for narration, the
        # same "convenience fields on the report" precedent Milestone 9 set
        # for canals/canal_staffing_ratio. Not read by any production
        # formula above; sustainability.py computes the same ratio
        # independently via public_works_coverage() for the score itself.
        if self.population > 0:
            public_works_coverage_ratio = min(
                1.0, self.public_works_coverage(effects) / self.population
            )
        else:
            public_works_coverage_ratio = 0.0

        # Habitat layout coverage (Space Age+) -- purely for narration, the
        # same "convenience fields on the report" precedent Milestones 9-10
        # set for canals/public_works. Not read by any production formula
        # above; sustainability.py computes the same ratio independently
        # via habitat_capacity() for the score itself.
        if self.population > 0:
            habitat_layout_ratio = min(1.0, self.habitat_capacity(effects) / self.population)
        else:
            habitat_layout_ratio = 0.0

        report = {
            "season": self.season - 1,
            "food_gathered": food_gathered,
            "materials_gathered": materials_gathered,
            "tools_made": tools_made,
            "knowledge_made": knowledge_made,
            "food_consumed": consumed,
            "fed_fraction": fed_fraction,
            "spoiled": spoiled,
            "surplus_banked": surplus_banked,
            "births": births,
            "deaths": deaths,
            "extraction": extraction,
            "sustainable_yield": sustainable,
            "tool_factor": tool_factor,
            "canals": self.buildings["canals"],
            "canal_staffing_ratio": canal_staffing,
            "public_works": self.buildings["public_works"],
            "public_works_coverage_ratio": public_works_coverage_ratio,
            "pollution": self.pollution,
            "sprawl": self.sprawl,
            "habitat_rings": self.buildings["habitat_rings"],
            "habitat_layout_ratio": habitat_layout_ratio,
            "relay_stations": self.buildings["relay_stations"],
            "holdings_residents": self.holdings_residents(),
            "relay_needed": outlying_needed,
            "relay_delivered": relay_delivered,
            "outlying_served": self.outlying_served,
        }
        self.last_report = report
        return report
