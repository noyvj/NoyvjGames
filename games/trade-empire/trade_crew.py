"""Assigning and releasing captains, captain status text and the automated ships' run_automation()."""

import trade_runstate as runstate
from trade_captains import CAPTAINS, CAPTAIN_SWAPS_PER_CHARTER
from trade_colony import colony_needing, colony_producing
from trade_hub import fleet_priority_target
from trade_rules import ALL_COLONIES
from trade_ships import ships


def captain_ship_for(perk_id):
    """The ship currently serving under this captain, or None."""
    for ship in ships.values():
        if ship.captain == perk_id:
            return ship
    return None


def captain_note_veterans():
    """A ship that is a veteran hauler right now has earned a captain's seat
    for the rest of the charter (called every tick)."""
    for ship in ships.values():
        if ship.purchased and ship.is_veteran:
            runstate.captain_earned.add(ship.id)


def captain_is_earned(ship_id):
    return ship_id in runstate.captain_earned and ships[ship_id].purchased


def can_assign_captain(perk_id, ship_id):
    if not isinstance(perk_id, str) or not isinstance(ship_id, str):
        return False
    if perk_id not in CAPTAINS or ship_id not in ships or not captain_is_earned(ship_id):
        return False
    if ships[ship_id].captain is not None:
        return False
    if runstate.captain_assignments[perk_id] >= 1 + CAPTAIN_SWAPS_PER_CHARTER:
        return False
    return True


def is_captain_swap(perk_id):
    """True when posting this captain again would use up its once-per-charter move."""
    return runstate.captain_assignments[perk_id] >= 1


def assign_captain(perk_id, ship_id):
    if not can_assign_captain(perk_id, ship_id):
        return False
    current = captain_ship_for(perk_id)
    if current is not None:
        current.captain = None
        current.captain_deliveries = 0
    ship = ships[ship_id]
    ship.captain = perk_id
    ship.captain_deliveries = 0
    runstate.captain_assignments[perk_id] += 1
    runstate.captains_met.add(perk_id)
    return True


def can_release_captain(perk_id):
    return isinstance(perk_id, str) and perk_id in CAPTAINS and captain_ship_for(perk_id) is not None


def release_captain(perk_id):
    ship = captain_ship_for(perk_id)
    if ship is None:
        return False
    ship.captain = None
    ship.captain_deliveries = 0
    return True


def captain_status_text(perk_id):
    captain = CAPTAINS[perk_id]
    ship = captain_ship_for(perk_id)
    where = f"serving on {ship.name}" if ship is not None else "waiting in the roster"
    moves = max(0, 1 + CAPTAIN_SWAPS_PER_CHARTER - runstate.captain_assignments[perk_id])
    return (
        f"{captain['name']}, {captain['label']} ({where}). {captain['perk']} Trade-off: {captain['tradeoff']} "
        f"{moves} posting(s) left this charter."
    )


def captains_summary_text():
    earned = sorted(ship_id for ship_id in runstate.captain_earned if ships[ship_id].purchased)
    employed = sum(1 for ship in ships.values() if ship.captain)
    seats = ", ".join(ships[ship_id].name for ship_id in earned) if earned else "none yet"
    return (
        f"Seats earned (veteran haulers): {seats}. {employed} of {len(CAPTAINS)} captains posted. "
        f"{len(runstate.captains_met)} of {len(CAPTAINS)} captains met across every charter."
    )


def run_automation():
    """Gives every automated, docked ship one autopilot action this
    tick: load if empty, depart for whichever colony needs its cargo if
    loaded. Runs after transit resolution, so a ship that just arrived
    this tick doesn't sit idle for a full extra tick before restarting."""
    for ship in ships.values():
        if not ship.automated or not ship.docked:
            continue
        if not ship.loaded:
            if runstate.fleet_priority_enabled:
                urgent_good = ALL_COLONIES[fleet_priority_target(ship)]["needs"]
                producer = colony_producing(urgent_good)
                if producer and producer != ship.location and ship.reposition(producer):
                    runstate.ever_repositioned = True
                    continue
            ship.load()
        else:
            destination = colony_needing(ship.cargo_good)
            if destination and destination != ship.location:
                ship.depart(destination)
