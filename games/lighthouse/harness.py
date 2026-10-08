"""Lighthouse -- a text harness that plays nights with no page at all, and the policies the tests and balance
bots use. Run `python3 harness.py [seed] [nights]` to read a few nights as plain text.

Not loaded by the page (the page loads only the engine modules listed in app.js)."""

import sys

import clock
import data
import day
import sim
from state import Keep


def standard_day(keep, upgrades=("lens", "wick", "weights", "vane", "bell", "shutters", "cistern", "boat", "greenhouse")):
    """A sensible default day: mend the worst parts, sleep if tired, buy what salvage allows, then end the day."""
    if keep.phase == "morning":
        day.end_morning(keep)
    if keep.phase == "yearend":
        day.continue_endless(keep)
    for uid in upgrades:
        if uid not in keep.upgrades:
            day.buy_upgrade(keep, uid)
    while keep.phase == "day" and keep.day_slots > 0:
        for ship in list(keep.waiting):
            if day.rescue(keep, ship["id"])[0]:
                break
        else:
            worst = min(data.PARTS, key=lambda p: (keep.structure[p], data.PARTS.index(p)))
            if keep.energy < 45 and day.rest(keep)[0]:
                continue
            if keep.structure[worst] < 70 and day.repair(keep, worst)[0]:
                continue
            if keep.has("greenhouse") and keep.supplies["food"] < 6 and day.garden(keep)[0]:
                continue
            if day.beachcomb(keep)[0]:
                continue
            if day.tidy(keep)[0]:
                continue
            if day.rest(keep)[0]:
                continue
            break
    if keep.phase == "day":
        day.end_day(keep)


def plan_for(keep, style="careful"):
    """Set tonight's plan the way a player might: enough light for the ships the harbour board lists, thin
    when no ship is near, and a margin for the weather the barometer promises."""
    import ships as shipgen
    from weather import forecast
    lo, hi = forecast(keep.seed, keep.night, keep.has("vane"))
    if style == "miser":
        keep.levels = [0, 0, 0]
    elif style == "idle":
        keep.levels = [1, 1, 1]
    else:
        length = clock.night_len(keep.night)
        mail = keep.boat_due or shipgen.mail_scheduled(keep.seed, keep.night)
        margin = {0: 0, 1: 1, 2: 2, 3: 3}[hi]
        levels = []
        for block in range(3):
            first, last = (length * block + 2) // 3 if block else 0, clock.block_end(keep.night, block)
            need = 0
            for ship in shipgen.ships_for_night(keep.seed, keep.night, mail):
                if ship["arrive"] < last and ship["arrive"] + ship["window"] > first:
                    need = max(need, ship["need"] + margin)
            level = 0
            while level < 3 and data.LEVEL_REACH[level] + (1 if keep.has("lens") else 0) < need:
                level += 1
            levels.append(level)
        keep.levels = levels
    keep.tasks = {"wind": True, "watch": style == "careful" and keep.energy > 60, "repair": style == "careful" and keep.energy > 50}


def play(keep, nights, style="careful"):
    """Play `nights` whole nights (evening, night, morning, day) with the given policy."""
    for _ in range(nights):
        if keep.phase == "evening":
            plan_for(keep, style)
            sim.begin_night(keep)
        sim.step(keep, 10 ** 6)
        standard_day(keep, upgrades=() if style == "idle" else ("lens", "wick", "weights", "vane", "bell", "shutters", "cistern", "boat", "greenhouse"))
    return keep


def describe(keep):
    r = keep.report
    lines = ["Night %d (%s, %s) -- %s" % (r["night"], clock.season_name(r["night"]), "year %d" % clock.year_of(r["night"]), r["summary"])]
    for e in keep.log:
        lines.append("  %s %-8s %s" % (clock.clock_label(r["night"], e[0]), e[1], e[2]))
    lines.append("  oil %.0f  energy %.0f  rep %d  salvage %d  structure %s" % (keep.oil, keep.energy, keep.reputation, keep.salvage, keep.structure))
    return "\n".join(lines)


def main(argv):
    seed = int(argv[1]) if len(argv) > 1 else 1
    nights = int(argv[2]) if len(argv) > 2 else 3
    keep = Keep(seed)
    sim.to_evening(keep)
    for _ in range(nights):
        plan_for(keep, "careful")
        sim.begin_night(keep)
        sim.step(keep, 10 ** 6)
        print(describe(keep))
        standard_day(keep)
        print()


if __name__ == "__main__":
    main(sys.argv)
