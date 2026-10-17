"""The Distribution Hub (J-21, J-22): choosing a hub colony, stockpile capacity, trip times, the fleet priority target and the hub panel."""

from js import document

import trade_runstate as runstate
from trade_colony import _system_label_for_colony, active_colony_ids, colony_producing, colony_states
from trade_market import HUB_STOCKPILE_CAP, STOCKPILE_CAPACITY
from trade_records import RECORDS_COUNT_MAX, records
from trade_research import most_urgent_colony, travel_ticks
from trade_rules import ALL_COLONIES, GOOD_LABEL


# ---------------------------------------------------------------------------
# J-21 / J-22 -- Hub & Spoke (Fleet Lab window): designate one colony as the Distribution Hub (a one-
# time fee, free to clear, the same fee to move it). A trip between the hub and another colony of the
# SAME system takes half as long (rounded up, never under one tick); the price is that the hub's own
# good can only be stockpiled up to HUB_STOCKPILE_CAP units instead of 15. Which colony makes the best
# hub depends on the network you run, so the choice is yours. Fleet Priority accounts for it: when
# several colonies are about equally urgent (within URGENCY_TIE of the lowest need), an idle automated
# ship goes to serve the one it can reach soonest, and a hub makes its neighbours quick to reach. With
# no hub set that function returns exactly most_urgent_colony(), so nothing changes. The hub is drawn
# with a thick ring and the word HUB, and the map's tooltip states its bonus.
# ---------------------------------------------------------------------------
HUB_COST = 120

HUB_RESEARCH = "automation_slot"
URGENCY_TIE = 0.05
HUB_RING_WIDTH = 5


def hub_open():
    return HUB_RESEARCH in runstate.unlocked_research


def can_set_hub(colony_id):
    return (
        hub_open() and isinstance(colony_id, str) and colony_id in active_colony_ids() and colony_id != runstate.hub_colony
        and runstate.total_profit >= HUB_COST
    )


def set_hub(colony_id):
    if not can_set_hub(colony_id):
        return False
    runstate.total_profit -= HUB_COST
    runstate.hub_colony = colony_id
    records["hubs_set"] = min(RECORDS_COUNT_MAX, records["hubs_set"] + 1)
    return True


def clear_hub():
    if runstate.hub_colony is None:
        return False
    runstate.hub_colony = None
    return True


def hub_trip_ticks(origin, destination, ticks):
    """A trip between the hub and a neighbour in its own system takes half as long (rounded up, at least one)."""
    if runstate.hub_colony is None or runstate.hub_colony not in (origin, destination) or origin == destination:
        return ticks
    if origin not in ALL_COLONIES or destination not in ALL_COLONIES:
        return ticks
    if _system_label_for_colony(origin) != _system_label_for_colony(destination):
        return ticks
    return max(1, (ticks + 1) // 2)


def fleet_priority_target(ship):
    """The colony an idle automated ship should serve: the most urgent one, or among the nearly-as-urgent ones
    the one it can reach soonest (hub trips are quick). Exactly most_urgent_colony() when no hub is set."""
    urgent = most_urgent_colony()
    if runstate.hub_colony is None:
        return urgent
    floor = colony_states[urgent].need_satisfaction
    best, best_key = urgent, None
    for colony_id, state in colony_states.items():
        if state.need_satisfaction - floor > URGENCY_TIE:
            continue
        producer = colony_producing(ALL_COLONIES[colony_id]["needs"])
        if producer is None:
            continue
        ticks = 0 if producer == ship.location else hub_trip_ticks(ship.location, producer, travel_ticks())
        key = (ticks, state.need_satisfaction, colony_id)
        if best_key is None or key < best_key:
            best, best_key = colony_id, key
    return best


def hub_text():
    if runstate.hub_colony is None:
        return (
            f"No hub set. A hub costs {HUB_COST} credits: trips between it and its neighbours in the same system take "
            f"half as long, and its own good can only be stockpiled up to {HUB_STOCKPILE_CAP} (instead of {STOCKPILE_CAPACITY})."
        )
    name = ALL_COLONIES[runstate.hub_colony]["name"]
    return (
        f"Distribution Hub: {name}. Trips between {name} and the other colonies of its system take half as long; "
        f"{GOOD_LABEL[ALL_COLONIES[runstate.hub_colony]['produces']]} stockpile capped at {HUB_STOCKPILE_CAP}."
    )


def hub_map_tooltip():
    if runstate.hub_colony is None:
        return ""
    return (
        f" Thick ring marked HUB: {ALL_COLONIES[runstate.hub_colony]['name']}, the Distribution Hub (trips to neighbours in its "
        f"system take half as long; its stockpile holds {HUB_STOCKPILE_CAP})."
    )


def render_hub():
    status = document.getElementById("hub-status")
    if status is None:
        return
    if not hub_open():
        status.innerText = "Locked: research the Automation Expansion to open Hub & Spoke."
    else:
        status.innerText = hub_text()
    clear = document.getElementById("hub-clear-button")
    if clear is not None:
        clear.hidden = runstate.hub_colony is None
    for colony_id, colony in ALL_COLONIES.items():
        button = document.getElementById(f"hub-set-{colony_id}-button")
        if button is None:
            continue
        shown = hub_open() and colony_id in active_colony_ids() and colony_id != runstate.hub_colony
        button.hidden = not shown
        button.disabled = not can_set_hub(colony_id)
        verb = "Move the hub to" if runstate.hub_colony is not None else "Make hub"
        button.innerText = f"{verb} {colony['name']} ({HUB_COST})"
