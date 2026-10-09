"""Lighthouse -- build the whole view the page draws, from the keep. Pure reading: nothing here changes the keep."""

import clock
import data
import ships as shipgen
from data import (BLOCKS, COMFORT_MAX, COND_ICONS, COND_LABELS, LEVEL_LABELS, LEVEL_REACH, LEVELS, PART_ICONS,
                  PART_LABELS, PARTS, REP_TITLES, SEVERITY_LABELS, SHIP_KINDS, SUPPLY_LABELS)
from rng import unit
from sim import mail_expected, beam_stopped, effective_reach, lamp_level, max_wind, tired, tonight_ships
from weather import forecast, weather
import day as daymod
import goals as goalmod
import info as infomod
import story as storymod


def rep_title(points):
    title = REP_TITLES[0][1]
    for threshold, name in REP_TITLES:
        if points >= threshold:
            title = name
    return title


def rep_next(points):
    for threshold, name in REP_TITLES:
        if points < threshold:
            return {"at": threshold, "title": name}
    return None


def part_state(value):
    return "sound" if value >= 70 else "worn" if value >= 40 else "poor" if value >= 15 else "failing"


def sky_for(keep):
    if keep.phase == "night":
        return "night"
    if keep.phase == "evening":
        return "dusk"
    if keep.phase == "morning":
        return "dawn"
    return "day"


def ship_view(keep, ship, tick, reach):
    rec = keep.progress.get(ship["id"])
    state = rec["state"] if rec else "pending"
    base = SHIP_KINDS[ship["kind"]]
    out = {
        "id": ship["id"], "kind": ship["kind"], "label": base["label"], "icon": base["icon"], "name": ship["name"],
        "arrive": ship["arrive"], "window": ship["window"], "need": ship["need"], "state": state,
        "block": shipgen.block_of_arrival(keep.night, ship), "dir": 1 if unit(keep.seed, "dir", ship["id"]) < 0.5 else -1,
        "seen": rec["seen"] if rec else 0,
        "who": ship.get("who") if storymod.on(keep) else None,
        "who_name": storymod.sailor_name(ship["who"]) if storymod.on(keep) and ship.get("who") else None,
    }
    out["at"] = clock.clock_label(keep.night, ship["arrive"])
    if rec and state == "pending" and keep.phase == "night":
        out["pos"] = round(max(0.0, min(1.0, (keep.tick - ship["arrive"]) / float(ship["window"] - 1))), 3)
        out["present"] = True
        out["lit"] = reach >= ship["need"]
    else:
        out["present"] = False
        out["lit"] = False
    out["arrived"] = rec is not None
    return out


def forecast_view(keep, night):
    lo, hi = forecast(keep.seed, night, keep.has("vane"))
    return {"night": night, "lo": lo, "hi": hi, "lo_label": SEVERITY_LABELS[lo], "hi_label": SEVERITY_LABELS[hi],
            "narrow": lo == hi, "vane": keep.has("vane")}


def notice_for(keep, night, mail):
    out = []
    for ship in shipgen.ships_for_night(keep.seed, night, mail):
        base = SHIP_KINDS[ship["kind"]]
        out.append({"kind": ship["kind"], "label": base["label"], "icon": base["icon"], "name": ship["name"],
                    "block": shipgen.block_of_arrival(night, ship), "block_label": BLOCKS[shipgen.block_of_arrival(night, ship)],
                    "at": clock.clock_label(night, ship["arrive"]), "need": ship["need"],
                    "who_name": storymod.sailor_name(ship["who"]) if storymod.on(keep) and ship.get("who") else None})
    for name in storymod.board_extras(keep, night):
        out.append({"kind": "ferry", "label": "Ferry", "icon": SHIP_KINDS["ferry"]["icon"], "name": name, "block": 1, "block_label": "Deep night",
                    "at": clock.clock_label(night, clock.night_len(night) // 2), "need": 4, "who_name": None, "chalked": True})
    return out


def build(keep, settings):
    night = keep.night
    length = clock.night_len(night)
    tick = min(keep.tick, length - 1) if keep.phase == "night" else keep.tick
    in_night = keep.phase == "night"
    wx = weather(keep.seed, night)
    cond = wx.cond[tick] if in_night and tick < length else 0
    wind = wx.wind[tick] if in_night and tick < length else 0
    level = lamp_level(keep, tick) if in_night else -1
    stopped = beam_stopped(keep) and in_night
    # what the keeper sees right now as the beam's reach
    reach = effective_reach(keep, level, cond) if in_night else 0
    plan_night = night if keep.phase in ("evening", "night") else night + 1
    plan_mail = keep.mail_tonight if keep.phase in ("evening", "night") else mail_expected(keep, plan_night)
    rep = keep.reputation
    stats = keep.night_stats
    view = {
        "phase": keep.phase, "night": night, "tick": keep.tick, "length": length, "clock": clock.clock_label(night, keep.tick if keep.tick < length else length - 1),
        "season": clock.season_name(night), "season_index": clock.season_of(night), "year": clock.year_of(night),
        "night_in_season": clock.night_in_season(night), "year_night": clock.year_night(night), "nights_per_year": data.NIGHTS_PER_YEAR,
        "start_min": data.NIGHT_START_MIN[clock.season_of(night)], "tick_minutes": data.TICK_MINUTES,
        "mode": keep.mode, "quiet": keep.quiet, "festival": clock.is_festival(night),
        "sky": sky_for(keep), "darkness": round(clock.darkness(night, tick), 3) if in_night else (0.15 if keep.phase == "evening" else 0.0),
        "cond": cond, "cond_label": COND_LABELS[cond], "cond_icon": COND_ICONS[cond], "wind": wind,
        "block": clock.block_of(night, tick) if in_night else 0,
        "beam": {"lit": in_night and level >= 0, "level": LEVELS[level] if level >= 0 else None,
                 "level_label": LEVEL_LABELS[level] if level >= 0 else "Out", "reach": reach, "stopped": stopped,
                 "base_reach": LEVEL_REACH[level] if level >= 0 else 0, "overridden": bool(keep.override and tick < keep.override[1])},
        "clockwork": {"left": round(keep.clock_left, 1), "max": max_wind(keep)},
        "incident": ({"kind": keep.incident["kind"], "text": data.INCIDENT_TEXT[keep.incident["kind"]],
                      "left": max(0, keep.incident["expires"] - keep.tick)} if keep.incident else None),
        "oil": round(keep.oil, 1), "oil_cap": keep.oil_cap(), "energy": round(keep.energy), "tired": tired(keep),
        "reputation": rep, "rep_title": rep_title(rep), "rep_next": rep_next(rep), "comfort": keep.comfort, "comfort_max": COMFORT_MAX,
        "salvage": keep.salvage,
        "supplies": [{"id": k, "label": SUPPLY_LABELS[k], "count": keep.supplies[k]} for k in data.SUPPLIES],
        "structure": [{"id": p, "label": PART_LABELS[p], "icon": PART_ICONS[p], "value": keep.structure[p], "state": part_state(keep.structure[p])}
                      for p in PARTS],
        "plan": {"levels": [LEVELS[i] for i in keep.levels], "tasks": dict(keep.tasks), "ration": keep.ration, "focus": keep.focus},
        "level_options": [{"id": LEVELS[i], "label": LEVEL_LABELS[i], "reach": LEVEL_REACH[i], "burn": data.LEVEL_BURN[i] * (0.8 if keep.has("wick") else 1.0)}
                          for i in range(4)],
        "blocks": list(BLOCKS),
        "ships": [ship_view(keep, s, tick, reach) for s in tonight_ships(keep)] if keep.phase in ("night", "morning") else [],
        "notice": notice_for(keep, plan_night, plan_mail),
        "notice_night": plan_night,
        "forecast": forecast_view(keep, plan_night),
        "log": [{"t": e[0], "kind": e[1], "text": e[2]} for e in keep.log],
        "night_stats": {"oil_used": round(stats["oil_used"], 1), "lamp_hours": round(stats["lamp_ticks"] * data.TICK_MINUTES / 60.0, 1),
                        "passed": stats["passed"], "delayed": stats["delayed"], "damaged": stats["damaged"],
                        "incidents": stats["incidents"], "damage": stats["damage"], "dark": stats["dark"]},
        "report": keep.report, "delivery": keep.delivery,
        "boat": {"due": keep.boat_due, "tonight": keep.mail_tonight and keep.phase in ("evening", "night"),
                 "next_night": shipgen.next_mail_night(keep.seed, night) if not keep.boat_due else night + (0 if keep.phase in ("evening", "night") else 1),
                 "order": dict(keep.order), "crates": data.BOAT_CRATES, "units": dict(data.CRATE_UNITS)},
        "day": {"slots": keep.day_slots, "max_slots": data.DAY_SLOTS, "repair_cost": {p: dict(data.DAY_REPAIR[p]) for p in PARTS},
                "patch_cost": {p: dict(data.NIGHT_PATCH[p]) for p in PARTS}, "heal": data.DAY_REPAIR_HEAL,
                "rest_gain": data.DAY_REST_GAIN + keep.comfort, "rescue_cost": daymod.rescue_cost(keep),
                "greenhouse": keep.has("greenhouse"), "repaired": [p for p in keep.repaired_today if p in PARTS]},
        "waiting": [dict(w) for w in keep.waiting],
        "upgrades": [{"id": u["id"], "name": u["name"], "cost": u["cost"], "text": u["text"], "owned": u["id"] in keep.upgrades,
                      "affordable": keep.salvage >= u["cost"], "rare": u["cost"] >= data.RARE_UPGRADE_COST} for u in data.UPGRADES],
        "meta": {"nights_kept": keep.meta["nights_kept"], "years": keep.meta["years"], "ships_passed": keep.meta["ships_passed"],
                 "ships_delayed": keep.meta["ships_delayed"], "ships_damaged": keep.meta["ships_damaged"], "rescues": keep.meta["rescues"],
                 "lamp_hours": round(keep.meta["lamp_ticks"] * data.TICK_MINUTES / 60.0, 1), "oil_used": round(keep.meta["oil_used"], 1),
                 "clean_streak": keep.meta["clean_streak"], "best_clean_streak": keep.meta["best_clean_streak"]},
        "goals": goalmod.goals(keep),
        "info": infomod.view(),
        "story": storymod.view(keep),
        "eerie": settings.get("eerie", True),
        "tick_ms": 4000,
    }
    return view
