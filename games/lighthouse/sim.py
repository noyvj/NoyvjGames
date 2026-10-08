"""Lighthouse -- the night: ticks, lamp, clockwork, weather damage, ships, incidents and the morning report.

Everything here is a deterministic function of the Keep and the seed. `step(keep, n)` advances at most n ticks
and stops at dawn, so running 100 ticks in one call and in 100 calls give the same Keep (the pause and
fast-forward invariance the tests check). Nothing reads the clock, nothing is random except through rng.py.

There is no way to lose: a bad night costs oil, repairs, reputation and comfort; ships can be delayed, damaged
or turn back, and nobody is hurt. A station with no oil at dusk finds its reserve flask.
"""

import clock
import data
import lore
import ships as shipgen
import story
from data import (AUTO_PATCH_HEAL, CLOCK_BASE, CLOCK_WEIGHTS, COND_LABELS, COND_PENALTY, DOCK_MIN, ENERGY_MAX,
                  ENERGY_PATCH, ENERGY_TEND, ENERGY_WIND, EMERGENCY_OIL, FIXED_CONE_DIVISOR, HUNGRY_COST,
                  INCIDENT_CHANCE, INCIDENT_FIX, INCIDENT_KINDS, INCIDENT_LIFE, INCIDENT_TEXT, LEVEL_BURN, LEVEL_REACH,
                  MAIL_WIND_MAX, NIGHT_PATCH, NIGHT_PATCH_HEAL, PART_LABELS, PARTS, REP_CAP, REST_GAIN,
                  SHIP_KINDS, SQUALL_DAMAGE_CHANCE, STORM_DAMAGE_CHANCE, TIRED, WATCH_DRAIN)
from rng import pick, rint, unit
from state import new_night_stats
from weather import weather

WEATHER_UP = {
    1: "A haze creeps over the water.",
    2: "Fog rolls in off the sea.",
    3: "A squall line crosses the water toward the rock.",
    4: "The storm breaks over the rock.",
}
WEATHER_DOWN = {
    0: "The air clears and the stars come out.",
    1: "The fog thins to a haze.",
    2: "The squall passes, and fog hangs behind it.",
    3: "The worst of the storm has passed; squalls are all that is left.",
}
DAMAGE_TEXT = {
    "tower": "Spray hammers the tower",
    "lantern": "Wind-blown grit scours the lantern glass",
    "rail": "A wave of spray tears at the gallery rail",
    "dock": "The sea slaps at the dock timbers",
    "cistern": "Rain finds a seam in the cistern",
}


# ---- helpers -------------------------------------------------------------------------------------------
def max_wind(keep):
    return CLOCK_WEIGHTS if keep.has("weights") else CLOCK_BASE


def tonight_ships(keep):
    """The ships of the current night (cached on the Keep, never saved: it is regenerated from the seed)."""
    key = (keep.seed, keep.night, keep.mail_tonight)
    cached = getattr(keep, "_ships", None)
    if cached is None or cached[0] != key:
        cached = (key, shipgen.ships_for_night(keep.seed, keep.night, keep.mail_tonight))
        keep._ships = cached
    return cached[1]


def mail_expected(keep, night):
    """Whether the mail boat is expected on this night: scheduled or still due, but never on the festival night."""
    if clock.is_festival(night):
        return False
    return keep.boat_due or shipgen.mail_scheduled(keep.seed, night)


def lamp_level(keep, tick):
    """The level the lamp burns at this tick: an override, else the plan for the block, else Dim when the ration
    is spent. -1 means the lamp is out. (Ration only applies to the plan, never to a deliberate override.)"""
    if keep.night_stats["dark"] or keep.oil <= 0:
        return -1
    block = clock.block_of(keep.night, tick)
    if keep.override and tick < keep.override[1]:
        return keep.override[0]
    level = keep.levels[block]
    if keep.ration and keep.night_stats["oil_used"] >= keep.ration:
        if not keep.night_stats["ration_hit"]:
            keep.night_stats["ration_hit"] = True
            keep.add_log("lamp", "The oil ration for the night is spent. The lamp is turned down to Dim.")
        return 0
    return level


def burn_rate(keep, level):
    rate = LEVEL_BURN[level]
    if keep.has("wick"):
        rate *= 0.8
    return rate


def part_penalty(keep):
    glass = keep.structure["lantern"]
    return 2 if glass < 25 else 1 if glass < 50 else 0


def beam_stopped(keep):
    return keep.clock_left <= 0


def effective_reach(keep, level, cond):
    """How far the beam carries right now, after the lamp, lens, glass, weather, incidents and the clockwork."""
    if level < 0:
        return 0
    reach = LEVEL_REACH[level]
    if keep.has("lens"):
        reach += 1
    reach -= part_penalty(keep)
    penalty = COND_PENALTY[cond]
    if cond == 2 and keep.has("bell"):
        penalty -= 1
    reach -= penalty
    if keep.incident and keep.incident["kind"] == "smoke":
        reach -= 1
    if keep.tasks["watch"] and cond in (1, 2) and keep.energy > 0:
        reach += 1
    reach += story.lens_cloth_bonus(keep)
    if beam_stopped(keep):
        reach //= FIXED_CONE_DIVISOR
    return max(0, reach)


def tired(keep):
    return keep.energy < TIRED


def add_rep(keep, amount):
    keep.reputation = max(0, min(REP_CAP, keep.reputation + amount))
    keep.night_stats["rep"] += amount


def event(keep, kind, text):
    keep.night_stats["events"] += 1
    keep.add_log(kind, text)


# ---- evening and the start of the night ----------------------------------------------------------------
def to_evening(keep):
    """Set up the evening of keep.night: the boat roster, the reserve flask, hunger."""
    keep.phase = "evening"
    keep.tick = 0
    keep.progress = {}
    keep.override = None
    keep.incident = None
    if clock.is_festival(keep.night) and (keep.boat_due or shipgen.mail_scheduled(keep.seed, keep.night)):
        keep.boat_due = True            # even the mail boat keeps the festival; she comes the night after
    keep.mail_tonight = mail_expected(keep, keep.night)
    keep.night_stats = new_night_stats()
    keep.report = None
    if keep.oil <= 0:
        keep.oil = float(EMERGENCY_OIL)
        keep.reputation = max(0, keep.reputation - 1)
        keep.add_log("keeper", "The tank is dry. You find the reserve flask the station always keeps, and a note of apology to the harbour.")
    if keep.hungry:
        keep.energy = max(0.0, keep.energy - HUNGRY_COST)
        keep.hungry = False
        keep.add_log("keeper", "You went without a proper meal and the day shows in your hands.")
    if clock.night_in_season(keep.night) == 1:
        keep.season_min_oil = keep.oil


def begin_night(keep):
    """Evening -> night: light the lamp. Returns False if it is not evening."""
    if keep.phase != "evening":
        return False
    keep.phase = "night"
    keep.tick = 0
    keep.progress = {}
    keep.override = None
    keep.incident = None
    keep.clock_left = float(max_wind(keep))
    keep.night_stats = new_night_stats()
    keep.log = []
    keep.report = None
    keep.add_log("lamp", "Dusk. You light the lamp.")
    return True


# ---- one tick ------------------------------------------------------------------------------------------
def advance(keep):
    """Run one tick of the night. Does nothing unless the phase is night."""
    if keep.phase != "night":
        return False
    seed, night, t = keep.seed, keep.night, keep.tick
    length = clock.night_len(night)
    wx = weather(seed, night)
    cond, wind = wx.cond[t], wx.wind[t]
    stats = keep.night_stats
    festival = clock.is_festival(night)

    # weather changes
    prev = wx.cond[t - 1] if t > 0 else 0
    if cond != prev:
        if cond > prev:
            event(keep, "weather", WEATHER_UP[cond])
        elif cond == 0 or cond < prev:
            event(keep, "weather", WEATHER_DOWN[cond] if cond in WEATHER_DOWN else WEATHER_DOWN[0])
    stats["worst_cond"] = max(stats["worst_cond"], cond)
    if cond == 2:
        stats["fog_ticks"] += 1

    # the clockwork
    decay = 1.0
    if keep.structure["tower"] < 40:
        decay *= 1.25
    if keep.incident and keep.incident["kind"] == "sticks":
        decay *= 2.0
    if keep.tasks["wind"] and keep.clock_left <= decay + 1.0 and keep.energy > 0 and keep.clock_left < max_wind(keep) - 1:
        wind_clockwork(keep, auto=True)
    keep.clock_left = max(0.0, keep.clock_left - decay)
    if beam_stopped(keep) and not stats["stopped"]:
        stats["stopped"] = True
        event(keep, "clock", "The clockwork runs down. The beam stops sweeping and holds a fixed cone.")

    # the lamp
    level = lamp_level(keep, t)
    if level >= 0:
        burn = min(burn_rate(keep, level), keep.oil)
        keep.oil = round(keep.oil - burn, 2)
        stats["oil_used"] = round(stats["oil_used"] + burn, 2)
        stats["lamp_ticks"] += 1
        if keep.oil <= 0:
            keep.oil = 0.0
            stats["dark"] = True
            event(keep, "lamp", "The oil is gone. The lamp gutters and goes dark.")
    keep.season_min_oil = min(keep.season_min_oil, keep.oil)
    reach = effective_reach(keep, level, cond)

    # ships
    for ship in tonight_ships(keep):
        rec = keep.progress.get(ship["id"])
        if rec is None:
            if t < ship["arrive"]:
                continue
            rec = keep.progress[ship["id"]] = {"seen": 0, "danger": 0, "state": "pending"}
        if rec["state"] != "pending" or t < ship["arrive"]:
            continue
        if t == ship["arrive"]:
            event(keep, "ship", story.label_ship(keep, ship, "%s %s" % (SHIP_KINDS[ship["kind"]]["label"], ship["name"])) + " rounds the point.")
        if reach >= ship["need"]:
            rec["seen"] += 1
        elif cond >= 3:
            rec["danger"] += 1
        if t == ship["arrive"] + ship["window"] - 1:
            resolve_ship(keep, ship, rec, wind)

    # storm damage
    if cond >= 3:
        chance = SQUALL_DAMAGE_CHANCE if cond == 3 else STORM_DAMAGE_CHANCE + 0.02 * max(0, wind - 3)
        for part in PARTS:
            p = chance
            if keep.has("shutters") and part in ("lantern", "rail"):
                p *= 0.5
            if keep.has("cistern") and part == "cistern":
                p *= 0.5
            if unit(seed, "dmg", night, t, part) < p:
                amount = rint(2, 4, seed, "dmg-amt", night, t, part)
                lost = min(amount, keep.structure[part])
                if lost:
                    keep.structure[part] -= lost
                    stats["damage"] += lost
                    event(keep, "damage", "%s (%s -%d)." % (DAMAGE_TEXT[part], PART_LABELS[part], lost))

    # incidents
    handle_incident(keep, t, wind, festival)

    # the keeper's tasks and rest
    if keep.tasks["repair"] and t % 6 == 5 and keep.energy >= 15:
        auto_patch(keep)
    if keep.tasks["watch"]:
        keep.energy = max(0.0, keep.energy - WATCH_DRAIN)
    else:
        rest = REST_GAIN * (1.25 if keep.has("cistern") else 1.0) * (1.0 + 0.03 * keep.comfort)
        if keep.structure["cistern"] < 25:
            rest *= 0.7
        keep.energy = min(float(ENERGY_MAX), keep.energy + rest)
    keep.energy = round(keep.energy, 2)

    keep.tick = t + 1
    if keep.tick >= length:
        finish_night(keep)
    return True


def step(keep, n=1):
    """Advance up to n ticks, stopping at dawn. Returns how many ticks ran."""
    ran = 0
    while ran < int(n) and keep.phase == "night":
        advance(keep)
        ran += 1
    return ran


# ---- ships ----------------------------------------------------------------------------------------------
def resolve_ship(keep, ship, rec, wind):
    stats = keep.night_stats
    base = SHIP_KINDS[ship["kind"]]
    label = "%s %s" % (base["label"], ship["name"]) if ship["kind"] != "mail" else "The mail boat %s" % ship["name"]
    label = story.label_ship(keep, ship, label)
    if rec["seen"] * 2 >= ship["window"]:
        rec["state"] = "passed"
        stats["passed"] += 1
        keep.meta["ships_passed"] += 1
        if ship["kind"] == "mail":
            if keep.structure["dock"] >= DOCK_MIN and wind <= MAIL_WIND_MAX:
                keep.night_stats["mail_landed"] = True
                event(keep, "ship", "%s found the light and ties up at the dock." % label)
            else:
                keep.boat_due = True
                why = "the dock is too damaged to tie up at" if keep.structure["dock"] < DOCK_MIN else "the water is too rough to land in"
                event(keep, "ship", "%s found the light, but %s. She will wait offshore and come again tomorrow." % (label, why))
                return
        else:
            event(keep, "ship", "%s saw the light and went safely by." % label)
        add_rep(keep, ship["rep"])
        stats["salvage"] += ship["salvage"]
        keep.salvage += ship["salvage"]
    elif rec["seen"] == 0 and rec["danger"] >= 2:
        rec["state"] = "damaged"
        stats["damaged"] += 1
        keep.meta["ships_damaged"] += 1
        add_rep(keep, -2)
        if ship["kind"] == "mail":
            keep.boat_due = True
        if len(keep.waiting) < 6 and not any(w["id"] == ship["id"] for w in keep.waiting):
            keep.waiting.append({"id": ship["id"], "kind": ship["kind"], "name": ship["name"]})
        event(keep, "ship", "%s lost the light in the murk and ran on the shoals. Everyone aboard is safe. She needs help in the morning." % label)
    else:
        rec["state"] = "delayed"
        stats["delayed"] += 1
        keep.meta["ships_delayed"] += 1
        add_rep(keep, -1)
        if ship["kind"] == "mail":
            keep.boat_due = True
        event(keep, "ship", "%s could not make out the light and turned back to wait for morning." % label)


# ---- incidents and keeper actions ------------------------------------------------------------------------
def handle_incident(keep, t, wind, festival):
    stats = keep.night_stats
    inc = keep.incident
    if inc:
        if keep.tasks["watch"] and t > inc["tick"] and keep.energy >= 1:
            keep.energy = max(0.0, keep.energy - 1)
            keep.add_log("keeper", INCIDENT_FIX[inc["kind"]])
            keep.incident = None
            return
        if t >= inc["expires"]:
            expire_incident(keep)
        return
    if festival:
        return
    chance = INCIDENT_CHANCE * (1.6 if wind >= 3 else 1.0) * (0.5 if keep.tasks["watch"] else 1.0)
    if unit(keep.seed, "inc", keep.night, t) < chance:
        kind = pick(INCIDENT_KINDS, keep.seed, "inc-kind", keep.night, t)
        if kind == "shutter" and wind < 1:
            kind = "smoke"
        keep.incident = {"kind": kind, "tick": t, "expires": t + INCIDENT_LIFE[kind]}
        stats["incidents"] += 1
        event(keep, "incident", INCIDENT_TEXT[kind])


def expire_incident(keep):
    inc = keep.incident
    keep.incident = None
    stats = keep.night_stats
    stats["unhandled"] += 1
    if inc["kind"] == "smoke":
        extra = min(2.0, keep.oil)
        keep.oil = round(keep.oil - extra, 2)
        stats["oil_used"] = round(stats["oil_used"] + extra, 2)
        keep.add_log("incident", "The smoke clears by itself, but it cost two measures of oil to burn off.")
    elif inc["kind"] == "shutter":
        for part, amount in (("rail", 3), ("lantern", 2)):
            lost = min(amount, keep.structure[part])
            keep.structure[part] -= lost
            stats["damage"] += lost
        keep.add_log("damage", "The loose shutter banged the gallery rail and the lantern glass (rail -3, lantern -2).")
    else:
        keep.add_log("incident", "The clockwork frees itself with a shudder.")


def wind_clockwork(keep, auto=False):
    full = float(max_wind(keep))
    amount = full * (0.7 if tired(keep) else 1.0)
    keep.clock_left = amount
    keep.energy = max(0.0, keep.energy - ENERGY_WIND)
    keep.night_stats["wound"] += 1
    if keep.night_stats["stopped"] and not auto:
        keep.add_log("clock", "You wind the clockwork and the beam sweeps again.")
    elif not auto:
        keep.add_log("clock", "You wind the clockwork.")
    else:
        keep.add_log("clock", "You wind the clockwork on your round.")


def can_patch(keep, part, table=NIGHT_PATCH):
    return all(keep.supplies[k] >= n for k, n in table[part].items())


def spend(keep, cost):
    for k, n in cost.items():
        keep.supplies[k] -= n


def auto_patch(keep):
    parts = [keep.focus] if keep.focus in PARTS else sorted(PARTS, key=lambda p: (keep.structure[p], PARTS.index(p)))
    for part in parts:
        if keep.structure[part] < 100 and can_patch(keep, part):
            spend(keep, NIGHT_PATCH[part])
            heal = AUTO_PATCH_HEAL // 2 if tired(keep) else AUTO_PATCH_HEAL
            keep.structure[part] = min(100, keep.structure[part] + heal)
            keep.energy = max(0.0, keep.energy - 3)
            keep.add_log("keeper", "Between rounds you patch the %s (+%d)." % (PART_LABELS[part].lower(), heal))
            return True
    return False


def set_level(keep, level):
    """Override the lamp for the rest of the current block of the night."""
    if keep.phase != "night" or level not in (0, 1, 2, 3):
        return False
    block = clock.block_of(keep.night, keep.tick)
    until = clock.block_end(keep.night, block)
    if level == keep.levels[block]:
        keep.override = None
    else:
        keep.override = [level, until]
    keep.night_stats["dark"] = keep.night_stats["dark"] and keep.oil <= 0
    return True


def wind_now(keep):
    if keep.phase != "night":
        return False
    if keep.clock_left >= max_wind(keep) - 1:
        return False
    wind_clockwork(keep)
    return True


def tend_now(keep):
    if keep.phase != "night" or not keep.incident:
        return False
    kind = keep.incident["kind"]
    keep.incident = None
    keep.energy = max(0.0, keep.energy - ENERGY_TEND)
    keep.add_log("keeper", INCIDENT_FIX[kind])
    return True


def patch_now(keep, part):
    if keep.phase != "night" or part not in PARTS or keep.structure[part] >= 100 or not can_patch(keep, part):
        return False
    spend(keep, NIGHT_PATCH[part])
    heal = NIGHT_PATCH_HEAL // 2 if tired(keep) else NIGHT_PATCH_HEAL
    keep.structure[part] = min(100, keep.structure[part] + heal)
    keep.energy = max(0.0, keep.energy - ENERGY_PATCH)
    keep.add_log("keeper", "You patch the %s in the dark (+%d)." % (PART_LABELS[part].lower(), heal))
    return True


# ---- dawn -----------------------------------------------------------------------------------------------
def finish_night(keep):
    """The night is over: settle the ships, deliver the boat, write the morning report."""
    stats = keep.night_stats
    meta = keep.meta
    keep.phase = "morning"
    keep.override = None
    if keep.incident:
        keep.incident = None
    meta["nights_kept"] += 1
    meta["lamp_ticks"] += stats["lamp_ticks"]
    meta["year_lamp_ticks"] += stats["lamp_ticks"]
    meta["oil_used"] = round(meta["oil_used"] + stats["oil_used"], 2)
    ships = tonight_ships(keep)
    outcomes = []
    for ship in ships:
        rec = keep.progress.get(ship["id"], {"state": "pending"})
        state = rec["state"] if rec["state"] != "pending" else "delayed"
        outcomes.append({"name": ship["name"], "kind": ship["kind"], "outcome": state})
    trouble = stats["damage"] + stats["delayed"] + stats["damaged"] + stats["incidents"]
    quiet = trouble == 0
    clean = bool(ships) and stats["delayed"] == 0 and stats["damaged"] == 0
    if clean:
        keep.salvage += 1
        stats["salvage"] += 1
        add_rep(keep, 1)
        meta["clean_streak"] += 1
        meta["best_clean_streak"] = max(meta["best_clean_streak"], meta["clean_streak"])
    elif stats["delayed"] or stats["damaged"]:
        meta["clean_streak"] = 0
    counters = meta["counters"]
    if quiet:
        counters["quiet_nights"] = counters.get("quiet_nights", 0) + 1
    if stats["fog_ticks"] >= 8 and ships and stats["delayed"] == 0 and stats["damaged"] == 0:
        counters["fog_clears"] = counters.get("fog_clears", 0) + 1
    if stats["worst_cond"] == 4 and min(keep.structure.values()) >= 50:
        counters["storm_wardens"] = counters.get("storm_wardens", 0) + 1
    if stats["events"] == 0:
        counters["empty_nights"] = counters.get("empty_nights", 0) + 1
    if stats["stopped"]:
        counters["wound_streak"] = 0
    else:
        counters["wound_streak"] = counters.get("wound_streak", 0) + 1
        counters["best_wound_streak"] = max(counters.get("best_wound_streak", 0), counters["wound_streak"])
    if clock.night_in_season(keep.night) == clock.NIGHTS_PER_SEASON and keep.season_min_oil >= 20:
        counters["frugal_seasons"] = counters.get("frugal_seasons", 0) + 1
    # the boat
    keep.delivery = None
    mail = any(s["kind"] == "mail" for s in ships)
    if mail and stats.get("mail_landed"):
        keep.boat_due = False
        keep.delivery = deliver(keep)
    # breakfast
    if keep.supplies["food"] > 0:
        keep.supplies["food"] -= 1
    else:
        keep.hungry = True
    keep.report = build_report(keep, outcomes, quiet)
    news = story.after_night(keep, ships)
    keep.report["letters"] = [{"id": lid, "from_name": story.sailor_name(lore.LETTERS[lid]["from"]), "subject": lore.LETTERS[lid]["subject"]} for lid in news["letters"]]
    keep.report["met"] = [story.sailor_name(sid) for sid in news["met"]]
    return keep.report


def deliver(keep):
    items = {}
    for kind in data.CRATE_KINDS:
        crates = keep.order.get(kind, 0)
        units = crates * data.CRATE_UNITS[kind]
        if kind == "oil":
            room = int(keep.oil_cap() - keep.oil)
            units = max(0, min(units, room))
            keep.oil = round(keep.oil + units, 2)
        else:
            room = data.SUPPLY_CAP - keep.supplies[kind]
            units = max(0, min(units, room))
            keep.supplies[kind] += units
        items[kind] = units
    return {"items": items, "text": "The %s unloads %d measures of oil and %d crates of other things, stacked on the dock by dawn." % (
        data.MAIL_NAME, items["oil"], sum(v for k, v in items.items() if k != "oil"))}


def build_report(keep, outcomes, quiet):
    stats = keep.night_stats
    passed, delayed, damaged = stats["passed"], stats["delayed"], stats["damaged"]
    hours = round(stats["lamp_ticks"] * data.TICK_MINUTES / 60.0, 1)
    if not outcomes:
        summary = "No ships came by tonight. You kept the light anyway."
    elif delayed == 0 and damaged == 0:
        summary = "Every ship that came by found the light."
    elif passed == 0:
        summary = "A hard night: no ship got safely by."
    else:
        summary = "%d of %d ships got safely by." % (passed, len(outcomes))
    lines = []
    if stats["dark"]:
        lines.append("The oil ran out in the night.")
    if stats["stopped"]:
        lines.append("The clockwork ran down at least once.")
    if stats["damage"]:
        lines.append("The weather and the wind took %d points off the station." % stats["damage"])
    if stats["incidents"]:
        lines.append("%d small trouble%s in the night." % (stats["incidents"], "" if stats["incidents"] == 1 else "s"))
    if stats["worst_cond"] >= 2:
        lines.append("The worst of the weather was %s." % COND_LABELS[stats["worst_cond"]].lower())
    return {
        "night": keep.night, "summary": summary, "ships": outcomes, "lamp_hours": hours, "oil_used": round(stats["oil_used"], 1),
        "damage": stats["damage"], "incidents": stats["incidents"], "rep": stats["rep"], "salvage": stats["salvage"],
        "passed": passed, "delayed": delayed, "damaged": damaged, "worst": stats["worst_cond"], "quiet": quiet, "lines": lines,
    }
