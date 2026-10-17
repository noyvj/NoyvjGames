"""ColonyState (one colony: need, development, temperament, demands), the colony table, which systems are open and who needs or makes a good."""

import trade_runstate as runstate
from trade_charter import charter_decay_multiplier, development_threshold, founding_output_multiplier
from trade_rules import (
    ALL_COLONIES, CARGO_CAPACITY, COLONIES, DEEP_COLONIES, DEFAULT_TEMPERAMENT, DEMANDING_LAPSED_DEMANDS,
    DEMAND_COOLDOWN_TICKS, DEMAND_WINDOW_TICKS, EXPANSION_COLONIES, GRATEFUL_DELIVERED,
    MAX_OUTPUT_MULTIPLIER, MIN_OUTPUT_MULTIPLIER, NEED_DECAY_PER_TICK, NEED_SATISFACTION_PER_UNIT_DELIVERED,
    NEGLECT_DEMAND_TICKS, NEGLECT_THRESHOLD, RIFT_COLONIES, SECONDARY_NEED, SPECIALIZATION,
    STARTING_NEED_SATISFACTION, TEMPERAMENTS, TEMPERAMENT_COUNT_MAX,
)


class ColonyState:
    def __init__(self, colony_id):
        self.id = colony_id
        self.neglect_ticks = 0
        self.demand_ticks_left = 0
        self.demand_cooldown = 0
        self.need_satisfaction = STARTING_NEED_SATISFACTION
        self.development_level = 1
        self.cumulative_delivered = 0.0
        self.secondary_need_satisfaction = STARTING_NEED_SATISFACTION
        # J-25 -- trade history that decides the colony's temperament.
        self.demands_made = 0
        self.concessions_granted = 0

    def secondary_need(self):
        return SECONDARY_NEED[self.id]

    def is_developed(self):
        return self.development_level >= 2

    def output_multiplier(self):
        if not self.is_developed():
            satisfaction = self.need_satisfaction
        else:
            satisfaction = (self.need_satisfaction + self.secondary_need_satisfaction) / 2
        base = MIN_OUTPUT_MULTIPLIER + satisfaction * (MAX_OUTPUT_MULTIPLIER - MIN_OUTPUT_MULTIPLIER)
        if self.is_developed():
            base *= 1 + SPECIALIZATION[self.id]["output_bonus"]
        return base * founding_output_multiplier(self.id)

    def cargo_capacity(self):
        return round(CARGO_CAPACITY * self.output_multiplier())

    def decay(self):
        decay_rate = NEED_DECAY_PER_TICK * charter_decay_multiplier(self.id)
        if self.is_developed():
            decay_rate *= SPECIALIZATION[self.id]["decay_multiplier"]
        self.need_satisfaction = max(0.0, self.need_satisfaction - decay_rate)
        if self.is_developed():
            self.secondary_need_satisfaction = max(0.0, self.secondary_need_satisfaction - decay_rate)

    def has_demand(self):
        return self.demand_ticks_left > 0

    def update_loyalty(self):
        """One tick of loyalty bookkeeping (called from tick())."""
        if self.demand_cooldown > 0:
            self.demand_cooldown -= 1
        if self.has_demand():
            self.demand_ticks_left -= 1
            if self.demand_ticks_left == 0:
                self.demand_cooldown = DEMAND_COOLDOWN_TICKS
                self.neglect_ticks = 0
            return
        if self.need_satisfaction < NEGLECT_THRESHOLD:
            self.neglect_ticks += 1
        else:
            self.neglect_ticks = 0
        if self.neglect_ticks >= NEGLECT_DEMAND_TICKS and self.demand_cooldown == 0:
            self.demand_ticks_left = DEMAND_WINDOW_TICKS
            self.demands_made = min(TEMPERAMENT_COUNT_MAX, self.demands_made + 1)

    def lapsed_demands(self):
        """J-25 -- demands this colony made that were never granted (an open
        demand is not lapsed yet)."""
        return max(0, self.demands_made - self.concessions_granted - (1 if self.has_demand() else 0))

    def temperament(self):
        """J-25 -- derived purely from this colony's history, so it can never
        be tampered into a state the history does not support. Demanding:
        two or more demands went unanswered. Grateful: well supplied (50+
        units delivered or invested) or helped by a concession. Anything
        else, including every new colony, is Opportunistic."""
        if self.lapsed_demands() >= DEMANDING_LAPSED_DEMANDS:
            return "demanding"
        if self.cumulative_delivered >= GRATEFUL_DELIVERED or self.concessions_granted >= 1:
            return "grateful"
        return DEFAULT_TEMPERAMENT

    def concession_boost(self):
        return TEMPERAMENTS[self.temperament()]["concession_boost"]

    def grant_concession(self):
        boost = self.concession_boost()  # judged before this concession changes the history
        self.concessions_granted = min(TEMPERAMENT_COUNT_MAX, self.concessions_granted + 1)
        self.need_satisfaction = min(1.0, self.need_satisfaction + boost)
        self.demand_ticks_left = 0
        self.demand_cooldown = DEMAND_COOLDOWN_TICKS
        self.neglect_ticks = 0

    def add_development(self, units):
        self.cumulative_delivered += units
        if self.cumulative_delivered >= development_threshold() and self.development_level < 2:
            self.development_level = 2

    def deliver(self, qty):
        gain = qty * NEED_SATISFACTION_PER_UNIT_DELIVERED
        self.need_satisfaction = min(1.0, self.need_satisfaction + gain)
        self.add_development(qty)

    def deliver_secondary(self, qty):
        gain = qty * NEED_SATISFACTION_PER_UNIT_DELIVERED
        self.secondary_need_satisfaction = min(1.0, self.secondary_need_satisfaction + gain)


colony_states = {colony_id: ColonyState(colony_id) for colony_id in COLONIES}


def colony_needing(good):
    """The one colony whose need this good satisfies — every good in the
    galaxy (both systems combined) is needed by exactly one colony, so
    there's always a single unambiguous "correct" destination for a
    load of it. Milestone 6's autopilot uses this to decide where to
    send itself. Searches ALL_COLONIES rather than just the reachable
    ones -- a ship can only ever be carrying a Kepler good if it's
    already reached the Kepler Cluster, which itself requires the
    system to be unlocked, so this never resolves to an unreachable
    destination in practice."""
    for colony_id, colony in ALL_COLONIES.items():
        if colony["needs"] == good:
            return colony_id
    return None


def colony_producing(good):
    """Reverse of colony_needing() — the one colony that makes this good.
    Milestone 12 uses this to find where an idle automated ship should
    reposition to when repointing itself at the fleet's most urgent
    need."""
    for colony_id, colony in ALL_COLONIES.items():
        if colony["produces"] == good:
            return colony_id
    return None


def galaxy_expansion_unlocked():
    return "galaxy_expansion" in runstate.unlocked_research


def outer_reaches_unlocked():
    return "outer_reaches" in runstate.unlocked_research


def umbral_reach_unlocked():
    return "umbral_reach" in runstate.unlocked_research


def active_colony_ids():
    """Every colony ID the player can currently interact with — the home
    system always, the Kepler Cluster once Galaxy Expansion is unlocked,
    the Rift Colonies once Outer Reaches is, and the Umbral Deep once
    Umbral Reach is. Everything reachability-
    sensitive (route drawing, depart-button validity, a ship's list of
    possible destinations) is scoped to this rather than to ALL_COLONIES
    directly."""
    ids = list(COLONIES)
    if galaxy_expansion_unlocked():
        ids += list(EXPANSION_COLONIES)
    if outer_reaches_unlocked():
        ids += list(RIFT_COLONIES)
    if umbral_reach_unlocked():
        ids += list(DEEP_COLONIES)
    return ids


# J27 — a trade almanac: a static-ish reference of each good's baseline
# price, the range the market can push it through, and which colony makes
# it and which needs it. Only goods from systems the player can reach are
# listed, so it never spoils the systems that are still locked.
def _system_label_for_colony(colony_id):
    if colony_id in COLONIES:
        return "Home system"
    if colony_id in EXPANSION_COLONIES:
        return "Kepler Cluster"
    if colony_id in RIFT_COLONIES:
        return "Rift Colonies"
    return "Umbral Deep"
