"""The opt-in coach (C-21): picks one observation about your grid.
Part of the split of the old single-file game.py: see "File map" in games/grid/CLAUDE.md.
"""

from js import document

import grid_runstate as runstate
from grid_rules import (
    GENERATION_TYPES, MAINTENANCE_AGE_REDUCTION, PLANT_BASE_COST, PLANT_CAPACITY, PLANT_LABEL, PLANT_TYPES,
    RENEWABLE_TYPES,
)
from grid_achievements import renewable_capacity_share


# ---- C-21 opt-in coach -------------------------------------------------------------------------------------------
# One plain-language observation per look, read from numbers the game already shows (capacity against demand, the
# aging risks, the disruption chance, idle funds, falling renewable prices, open offers). It never blocks anything,
# never changes a rule and is off until the player turns it on. The first matching line wins, most urgent first.
COACH_RISK_THRESHOLD = 0.15
COACH_DISRUPTION_THRESHOLD = 0.2
COACH_IDLE_FUNDS_MULTIPLE = 3


def _coach_cheapest_generation():
    """The generation type that adds capacity at the lowest price per unit right now."""
    return min(GENERATION_TYPES, key=lambda t: runstate.state.plant_cost(t) / PLANT_CAPACITY[t])


def coach_observation():
    s = runstate.state
    capacity = s.total_capacity()
    next_demand = s.demand + s.demand_growth_this_round()
    if capacity <= 0:
        pick = _coach_cheapest_generation()
        return (
            f"You have no generation yet and demand is {s.demand:.0f}. {PLANT_LABEL[pick]} gives the most capacity "
            f"for the price right now ({s.plant_cost(pick):.0f} for {PLANT_CAPACITY[pick]}). Solar, wind and hydro "
            "get cheaper every time you build one."
        )
    if capacity < s.demand:
        gap = s.demand - capacity
        pick = _coach_cheapest_generation()
        units = -(-gap // PLANT_CAPACITY[pick])
        return (
            f"Capacity {capacity} is {gap:.0f} short of demand {s.demand:.0f}, so revenue is capped at what you can "
            f"supply. About {units:.0f} more {PLANT_LABEL[pick]} would close the gap."
        )
    risky = [
        t for t in PLANT_TYPES
        if s.plant_counts[t] > 0 and s.breakdown_risk_probability(t) >= COACH_RISK_THRESHOLD
    ]
    if risky:
        oldest = max(risky, key=lambda t: s.plant_age[t])
        return (
            f"Your {PLANT_LABEL[oldest]} fleet is {s.wear_percent(oldest)}% worn and a breakdown there is "
            f"{s.breakdown_risk_probability(oldest) * 100:.0f}% likely. Maintaining it costs "
            f"{s.maintenance_cost(oldest):.0f} and takes {MAINTENANCE_AGE_REDUCTION} rounds off its age."
        )
    if s.disruption_probability() >= COACH_DISRUPTION_THRESHOLD:
        source = s.primary_emissions_source()
        blame = f" Most of it comes from {PLANT_LABEL[source]}." if source else ""
        return (
            f"Emissions give a {s.disruption_probability() * 100:.0f}% chance of a disruption next round.{blame} "
            "Replacing fossil capacity with clean capacity lowers it."
        )
    if capacity < next_demand:
        return (
            f"Demand is covered now, but it rises to {next_demand:.0f} next round and your capacity is {capacity}. "
            "Building a little ahead of demand keeps revenue from being capped."
        )
    cheapest = _coach_cheapest_generation()
    if s.funds >= COACH_IDLE_FUNDS_MULTIPLE * s.plant_cost(cheapest) and s.fossil_share() > 0:
        renewable = min(RENEWABLE_TYPES, key=lambda t: s.plant_cost(t) / PLANT_CAPACITY[t])
        return (
            f"You are holding {s.funds:.0f} funds with demand covered. Spare funds can go into {PLANT_LABEL[renewable]} "
            f"({s.plant_cost(renewable):.0f} now against {PLANT_BASE_COST[renewable]} when new), which keeps getting "
            "cheaper, or into retiring fossil plants."
        )
    if s.weather_variability_enabled and s.plant_counts["battery"] == 0 and renewable_capacity_share() > 0.3:
        return (
            f"Weather variability is on and renewables are {renewable_capacity_share() * 100:.0f}% of your capacity. "
            "A battery buffers the bad-weather rounds."
        )
    if s.policy_lever_available:
        return "A policy lever is on offer this round. Carbon pricing makes fossil builds dearer, a renewable subsidy makes clean ones cheaper."
    return (
        f"Nothing urgent. Demand {s.demand:.0f} is covered by capacity {capacity}, and it will grow to "
        f"{next_demand:.0f}. Keep adding clean capacity ahead of it."
    )


def render_coach():
    panel = document.getElementById("coach-panel")
    panel.hidden = not runstate.prefs["coach"]
    document.getElementById("pref-coach").checked = runstate.prefs["coach"]
    if runstate.prefs["coach"]:
        document.getElementById("coach-text").innerText = coach_observation()
