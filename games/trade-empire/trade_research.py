"""The research tree (nodes, costs, unlock rules), automation costs and slots, Fleet Priority, and the fleet-wide boosts research gives."""

import trade_runstate as runstate
from trade_colony import ColonyState, colony_states
from trade_rules import DEEP_COLONIES, EXPANSION_COLONIES, RIFT_COLONIES, TRAVEL_TICKS


MAX_AUTOMATED_SHIPS = 2

# J15 — how many consecutive ticks a manual ship can sit docked and
# empty before its status line flags it as idle. ~20 real seconds at
# TICK_INTERVAL_MS, long enough that briefly deciding where to send a
# ship never trips it.
IDLE_WARNING_TICKS = 20

# J10 — player-chosen ship names, capped to keep the panel header tidy.
MAX_SHIP_NAME_LENGTH = 24


def most_urgent_colony():
    return min(colony_states, key=lambda cid: colony_states[cid].need_satisfaction)


def set_fleet_priority(enabled):
    runstate.fleet_priority_enabled = enabled


# Milestone 8 — research tree v1: a small, flat framework (no
# prerequisites yet) gating an automation-slot expansion, a fleet-wide
# speed boost, and a new ship class — spent from a separate currency
# (research points) that accrues passively, independent of trade
# profit, so research and trade are two distinct things to manage
# rather than one pool spent two ways.
RESEARCH_PER_TICK = 0.5
RESEARCH_NODES = {
    "automation_slot": {
        "cost": 20, "label": "Automation Expansion", "description": "+1 automation slot",
    },
    "fast_ships": {
        "cost": 15, "label": "Fast Ships I", "description": "-1 tick travel time, fleet-wide",
    },
    "hauler": {
        "cost": 30, "label": "Hauler-Class Refit", "description": "+50% cargo capacity, fleet-wide",
    },
    # Milestone 13 — galaxy scaling: the priciest node yet, gating an
    # entire second system rather than a fleet-wide modifier.
    "galaxy_expansion": {
        "cost": 80, "label": "Galaxy Expansion",
        "description": "Unlocks the Kepler Cluster — 3 new colonies, a new need-triangle",
    },
    # J7 — a second automation-slot tier. Gated behind the first tier via
    # "requires" (a node id that must already be unlocked) rather than
    # just a steeper cost, so the tree gets its first real prerequisite
    # edge instead of staying flat forever.
    "automation_slot_2": {
        "cost": 150, "label": "Automation Expansion II", "description": "+1 more automation slot",
        "requires": "automation_slot",
    },
    # J13 — gates the Rift Colonies, priced above Galaxy Expansion (a
    # third system, one tier further out) and requiring it first.
    "outer_reaches": {
        "cost": 200, "label": "Outer Reaches",
        "description": "Unlocks the Rift Colonies — 3 new colonies, a new need-triangle",
        "requires": "galaxy_expansion",
    },
    # J1 — the deepest research investment yet: a two-step chain past
    # Outer Reaches. Deep Survey has no effect of its own beyond being the
    # required first step (honestly labelled as such); Umbral Reach is the
    # priciest node in the tree and is what actually opens the fourth
    # system.
    "deep_survey": {
        "cost": 240, "label": "Deep Survey",
        "description": "Long-baseline survey arrays — no direct bonus, but the required first step toward the Umbral Deep",
        "requires": "outer_reaches",
    },
    "umbral_reach": {
        "cost": 360, "label": "Umbral Reach",
        "description": "Unlocks the Umbral Deep — 3 new colonies, a new need-triangle",
        "requires": "deep_survey",
    },
    # J15 -- a specialization fork, unlocked once the tree has grown to
    # Automation Expansion II. Committing to either branch's first tier
    # permanently closes the other branch ("excludes"), so this is a real
    # choice about how the empire is run rather than a to-do list.
    "auto_efficiency": {
        "cost": 120, "label": "Autopilot Optimisation (Automation path)",
        "description": "Automated ships earn +10% on every sale",
        "requires": "automation_slot_2", "excludes": ("market_insight", "market_insight_2"),
    },
    "auto_efficiency_2": {
        "cost": 260, "label": "Autopilot Optimisation II (Automation path)",
        "description": "+1 more automation slot",
        "requires": "auto_efficiency", "excludes": ("market_insight", "market_insight_2"),
    },
    "market_insight": {
        "cost": 120, "label": "Market Insight (Market path)",
        "description": "Sold-down prices recover 50% faster",
        "requires": "automation_slot_2", "excludes": ("auto_efficiency", "auto_efficiency_2"),
    },
    "market_insight_2": {
        "cost": 260, "label": "Market Insight II (Market path)",
        "description": "Each unit sold pushes its price down 30% less",
        "requires": "market_insight", "excludes": ("auto_efficiency", "auto_efficiency_2"),
    },
}
AUTO_EFFICIENCY_BONUS = 0.10
AUTO_EFFICIENCY_2_SLOT_BONUS = 1
MARKET_INSIGHT_RECOVERY_MULTIPLIER = 1.5
MARKET_INSIGHT_2_DECAY_MULTIPLIER = 0.7
AUTOMATION_SLOT_RESEARCH_BONUS = 1
AUTOMATION_SLOT_2_RESEARCH_BONUS = 1
FAST_SHIPS_TICK_REDUCTION = 1
HAULER_CARGO_MULTIPLIER = 1.5


def can_unlock_research(node_id):
    node = RESEARCH_NODES[node_id]
    requires = node.get("requires")
    if requires is not None and requires not in runstate.unlocked_research:
        return False
    if research_node_blocked_by(node_id) is not None:
        return False
    return node_id not in runstate.unlocked_research and runstate.research_points >= node["cost"]


def research_node_blocked_by(node_id):
    """J15 -- the already-unlocked node (if any) that permanently closes
    this one, because the two are opposite sides of a specialization fork."""
    for other in RESEARCH_NODES[node_id].get("excludes", ()):
        if other in runstate.unlocked_research:
            return other
    return None


def unlock_research(node_id):
    if not can_unlock_research(node_id):
        return False
    runstate.research_points -= RESEARCH_NODES[node_id]["cost"]
    runstate.unlocked_research.add(node_id)
    if node_id == "galaxy_expansion":
        # Colony state for the cluster is created only now, on unlock —
        # not eagerly at module load like the home system's. Otherwise
        # it would sit there decaying, unreachable, from tick one, and
        # Milestone 12's most_urgent_colony() (which reads colony_states
        # directly) would fixate on it forever since nothing could ever
        # actually reach it to help.
        for colony_id in EXPANSION_COLONIES:
            colony_states[colony_id] = ColonyState(colony_id)
    elif node_id == "outer_reaches":
        # Same deferred-creation reasoning, one tier further out.
        for colony_id in RIFT_COLONIES:
            colony_states[colony_id] = ColonyState(colony_id)
    elif node_id == "umbral_reach":
        # Same deferred-creation reasoning, one tier further out again.
        for colony_id in DEEP_COLONIES:
            colony_states[colony_id] = ColonyState(colony_id)
    return True


def max_automated_ships():
    bonus = AUTOMATION_SLOT_RESEARCH_BONUS if "automation_slot" in runstate.unlocked_research else 0
    bonus += AUTOMATION_SLOT_2_RESEARCH_BONUS if "automation_slot_2" in runstate.unlocked_research else 0
    bonus += AUTO_EFFICIENCY_2_SLOT_BONUS if "auto_efficiency_2" in runstate.unlocked_research else 0
    return MAX_AUTOMATED_SHIPS + bonus


def travel_ticks():
    reduction = FAST_SHIPS_TICK_REDUCTION if "fast_ships" in runstate.unlocked_research else 0
    return max(1, TRAVEL_TICKS - reduction)


def fleet_cargo_multiplier():
    return HAULER_CARGO_MULTIPLIER if "hauler" in runstate.unlocked_research else 1.0
