"""Lighthouse -- the day: the morning's turn into daylight, the five day tasks, upgrades, the boat order and
the turn into the next evening. Every action returns (ok, message): a refusal is a line of in-world text, never
an error, and never costs anything.
"""

import clock
from data import (BOAT_CRATES, COMFORT_MAX, CRATE_KINDS, DAY_REPAIR, DAY_REPAIR_ENERGY, DAY_REPAIR_HEAL, DAY_REST_GAIN,
                  DAY_SLOTS, ENERGY_MAX, NIGHTS_PER_YEAR, PART_LABELS, PARTS, SUPPLY_CAP, SUPPLY_LABELS, UPGRADES)
from rng import pick
from sim import tired, to_evening

COMB_FINDS = ("timber", "tar", "glass", "food")
UPGRADE_BY_ID = {u["id"]: u for u in UPGRADES}


def end_morning(keep):
    """Morning report read: on to the day (or, after the year's last night, to the year's end)."""
    if keep.phase != "morning":
        return False
    year_ended = clock.year_night(keep.night) == NIGHTS_PER_YEAR
    if year_ended:
        keep.meta["years"] += 1
        ticks = keep.meta["year_lamp_ticks"]
        keep.meta["best_lamp_hours_year"] = max(keep.meta["best_lamp_hours_year"], int(round(ticks * 10 / 60.0)))
        keep.meta["year_lamp_ticks"] = 0
        if keep.mode == "year":
            keep.phase = "yearend"
            return True
        keep.add_log("note", "Another year at the rock is done.")
    keep.phase = "day"
    keep.day_slots = DAY_SLOTS
    keep.repaired_today = []
    keep.combed = False
    return True


def continue_endless(keep):
    """Year one is done; keep the light for as long as you like."""
    if keep.phase != "yearend":
        return False
    keep.mode = "endless"
    keep.phase = "day"
    keep.day_slots = DAY_SLOTS
    keep.repaired_today = []
    keep.combed = False
    return True


def end_day(keep):
    if keep.phase != "day":
        return False
    keep.night += 1
    keep.day_slots = 0
    to_evening(keep)
    return True


def _slot(keep):
    if keep.phase != "day":
        return "That can only be done in the daylight."
    if keep.day_slots <= 0:
        return "The daylight is spent."
    return None


def repair(keep, part):
    problem = _slot(keep)
    if problem:
        return False, problem
    if part not in PARTS:
        return False, "There is no such part of the station."
    if keep.structure[part] >= 100:
        return False, "The %s is already sound." % PART_LABELS[part].lower()
    cost = DAY_REPAIR[part]
    missing = [SUPPLY_LABELS[k].lower() for k, n in cost.items() if keep.supplies[k] < n]
    if missing:
        return False, "You need more %s for that." % " and ".join(missing)
    for k, n in cost.items():
        keep.supplies[k] -= n
    heal = DAY_REPAIR_HEAL // 2 if tired(keep) else DAY_REPAIR_HEAL
    keep.structure[part] = min(100, keep.structure[part] + heal)
    keep.energy = max(0.0, keep.energy - DAY_REPAIR_ENERGY)
    keep.day_slots -= 1
    if part not in keep.repaired_today:
        keep.repaired_today.append(part)
        if len(keep.repaired_today) == len(PARTS):
            keep.meta["counters"]["tidy_days"] = keep.meta["counters"].get("tidy_days", 0) + 1
    return True, "You mend the %s (+%d)." % (PART_LABELS[part].lower(), heal)


def rest(keep):
    problem = _slot(keep)
    if problem:
        return False, problem
    gain = DAY_REST_GAIN + keep.comfort
    keep.energy = min(float(ENERGY_MAX), keep.energy + gain)
    keep.day_slots -= 1
    return True, "You sleep through the bright hours (+%d energy)." % gain


def tidy(keep):
    problem = _slot(keep)
    if problem:
        return False, problem
    if keep.comfort >= COMFORT_MAX:
        return False, "The keeper's room could not be cosier."
    keep.comfort += 1
    keep.energy = max(0.0, keep.energy - 2)
    keep.day_slots -= 1
    return True, "You air the room and set it right (comfort %d of %d)." % (keep.comfort, COMFORT_MAX)


def beachcomb(keep):
    problem = _slot(keep)
    if problem:
        return False, problem
    if keep.combed:
        return False, "You have already walked the tideline today."
    keep.combed = True
    find = pick(COMB_FINDS, keep.seed, "comb", keep.night)
    if keep.supplies[find] < SUPPLY_CAP:
        keep.supplies[find] += 1
    keep.salvage += 1
    keep.energy = max(0.0, keep.energy - 3)
    keep.day_slots -= 1
    return True, "You walk the tideline and bring back some salvage and a bit of %s." % SUPPLY_LABELS[find].lower()


def garden(keep):
    problem = _slot(keep)
    if problem:
        return False, problem
    if not keep.has("greenhouse"):
        return False, "You have no greenhouse box yet."
    keep.supplies["food"] = min(SUPPLY_CAP, keep.supplies["food"] + 2)
    keep.energy = max(0.0, keep.energy - 2)
    keep.day_slots -= 1
    return True, "You tend the greenhouse box and pick two days' worth of vegetables."


def rescue_cost(keep):
    return {"timber": 1} if keep.has("boat") else {"timber": 1, "tar": 1}


def rescue(keep, ship_id):
    problem = _slot(keep)
    if problem:
        return False, problem
    ship = next((w for w in keep.waiting if w["id"] == ship_id), None)
    if ship is None:
        return False, "No ship is waiting for help."
    cost = rescue_cost(keep)
    missing = [SUPPLY_LABELS[k].lower() for k, n in cost.items() if keep.supplies[k] < n]
    if missing:
        return False, "You need more %s to help her off the shoals." % " and ".join(missing)
    for k, n in cost.items():
        keep.supplies[k] -= n
    keep.waiting.remove(ship)
    keep.reputation += 2
    keep.salvage += 1
    keep.energy = max(0.0, keep.energy - 5)
    keep.day_slots -= 1
    keep.meta["rescues"] += 1
    return True, "You row out and help %s off the shoals. Her crew send their thanks (+2 reputation)." % ship["name"]


def buy_upgrade(keep, upgrade_id):
    """Spend salvage. The page asks the player to confirm a dear one first; the engine only checks the rules."""
    upgrade = UPGRADE_BY_ID.get(upgrade_id)
    if upgrade is None:
        return False, "There is no such upgrade."
    if upgrade_id in keep.upgrades:
        return False, "You already have that."
    if keep.phase not in ("evening", "day", "morning", "yearend"):
        return False, "Not in the middle of the night."
    if keep.salvage < upgrade["cost"]:
        return False, "You need %d salvage for that (you have %d)." % (upgrade["cost"], keep.salvage)
    keep.salvage -= upgrade["cost"]
    keep.upgrades.append(upgrade_id)
    return True, "%s is fitted." % upgrade["name"]


def set_order(keep, order):
    """The next boat's order: five crate counts that add up to the boat's twelve crates."""
    if not isinstance(order, dict):
        return False, "That is not an order."
    clean = {}
    for kind in CRATE_KINDS:
        v = order.get(kind)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0 or v != int(v):
            return False, "Each line of the order must be a whole number of crates."
        clean[kind] = int(v)
    if sum(clean.values()) != BOAT_CRATES:
        return False, "The boat carries exactly %d crates (this order has %d)." % (BOAT_CRATES, sum(clean.values()))
    keep.order = clean
    return True, "Order sent ashore."
