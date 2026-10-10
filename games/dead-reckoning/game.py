"""Dead Reckoning -- the engine's single entry point (the Lexis / Signal pattern).

The view (app.js) never reads engine objects: it sends one JSON string to `handle` and draws the JSON that comes back.
`get_state()` / `load_state()` are the shared save widget's contract (planning/SAVE-BUTTON-INTEGRATION.md). Everything is
deterministic: the same chart, plan and seed always give the same passage.

Requests carry an `action`:
  open                       the current view (starts the first chart if nothing is open)
  start {chart_id}           open a chart with an empty plan
  add_wait                   append an hour lying at anchor (speed 0), to wait for a fair stream
  add_leg                    append a leg (heading toward the flag from where the plot ends, cruising speed, 1 hour)
  set_leg {i, heading?, speed?, hours?}   set fields of leg i (forced onto the legal grid)
  nudge {i, field, delta}    heading / speed / hours of leg i plus delta
  remove_leg {i} | undo | clear
  allow {value}              plot with or without the charted currents, wind and compass error
  helper {kind, target}      kind "naive" | "current"; target "flag" | "point"
  point {x, y} | clear_point the ruler's marked point
  sail                       sail the plan and reveal the passage
  retry                      back to planning with the same legs
  restart                    back to planning with an empty plan
  set_mode {mode}            "plan" (full plan) or "watch" (Watch-by-watch), before anything is sailed
  take_fix {landmark}        Watch-by-watch: move the plot to where a landmark's bearing and distance put the ship
  anchor                     Watch-by-watch: end the passage where it stands (sail with the legs already sailed)
  practice {difficulty, seed?, code?, two?}   open a generated practice chart (a share code such as DR3-1K9X2 replays one; two=true makes a
                             two-ship chart, whose codes carry a T: DR3T-1K9X2)
  start_daily {date}         open the Daily Chart for a UTC date (see daily.py)
  select_ship {ship}         two-ship charts: choose which ship's plan the leg actions edit (0 = Ship A, 1 = Ship B)
Every request may carry "today" ("YYYY-MM-DD", UTC): the view passes the date in, the engine never reads a clock.
  next_chart                 open the next chart in the campaign (when it is unlocked)
  show_par | use_par         reveal the authored plan after a first attempt / load it into the planner
  reset                      forget all progress
"""

import json

import achievements
import charts
import daily
import fixes
import fleet
import gen
import info
import progress
import render
import sim
import solver
import state
from geom import bearing, dist

meta = state.new_meta()
run = None
point = None
today = None            # the view's UTC date, runtime only (never saved, never read from a clock)
note = ""               # a one-line message about the last request (never saved)
history = []            # earlier leg lists, for Undo (never saved)
HISTORY_LIMIT = 40
CURRENT_HELPER_AFTER = 3   # the "allow for the charted current" helper unlocks after this many charts are cleared


# --- helpers -------------------------------------------------------------------------------------
def _chart():
    return charts.get_chart(run["chart_id"])


def _two(chart=None):
    return fleet.is_two(chart if chart is not None else _chart())


def _ship_index(chart=None):
    """Which ship the leg actions edit: always 0 on a one-ship chart."""
    return run.get("ship", 0) if _two(chart) else 0


def _sc(chart):
    """The active ship's view of the chart (the chart itself on a one-ship chart)."""
    return fleet.ship_chart(chart, _ship_index(chart))


def _legs_of(ship):
    return run["legs2"] if ship == 1 else run["legs"]


def _legs():
    """The active ship's list of legs (edited in place)."""
    return _legs_of(_ship_index())


def _record(chart_id):
    return meta["charts"].get(chart_id) or state.new_record()


def _scoped(chart_id):
    """A practice chart or a Daily Chart: made on demand, never scored in the campaign records; its found hazards live in the run."""
    return gen.is_practice_id(chart_id) or daily.is_daily_id(chart_id)


def _practice():
    return run is not None and gen.is_practice_id(run["chart_id"])


def _discovered(chart):
    """The hazards the crew has found on this chart: remembered per chart in the campaign, per run in practice."""
    return list(run["found"]) if _scoped(chart["id"]) else _record(chart["id"])["discovered"]


def _attempts(chart):
    if _scoped(chart["id"]):
        return 1 if run["counted"] else 0
    return _record(chart["id"])["attempts"]


def _cleared():
    return sum(1 for rec in meta["charts"].values() if rec["stars"] >= 1)


def current_helper_unlocked():
    return _cleared() >= CURRENT_HELPER_AFTER


def _start(chart_id, mode=None, seed=0):
    global run, point, history
    chart = charts.get_chart(chart_id)
    if mode not in chart.get("modes", ("plan",)):
        mode = chart.get("default_mode", "plan")
    run = state.new_run(chart_id, chart.get("seed", seed), mode)
    point = None
    history = []


def _first_chart_id():
    for cid in charts.ORDER:
        if _record(cid)["stars"] == 0 and charts.is_unlocked(cid, meta["charts"]):
            return cid
    return charts.ORDER[0]


def _ensure_run():
    if run is None:
        _start(_first_chart_id())


def _snapshot():
    history.append([_ship_index(), [dict(leg) for leg in _legs()]])
    del history[:-HISTORY_LIMIT]


def _watch():
    return run["mode"] == "watch"


def _plot(chart, ship=None):
    ship = _ship_index(chart) if ship is None else ship
    return sim.estimate(fleet.ship_chart(chart, ship), _legs_of(ship), allow=run["allow"], fixes=run["fixes"] if ship == 0 else ())


def _believed(chart):
    """Where the player believes the ship is after the watches already sailed (their plot, fixes included)."""
    est = sim.estimate(chart, run["legs"][:run["sailed"]], allow=run["allow"], fixes=run["fixes"])
    return (est[-1][1], est[-1][2])


def _true_pos(chart):
    """The ship's real position after the watches sailed. Used ONLY to work out what a fix would read; never shown."""
    return tuple(sim.sail(chart, run["legs"][:run["sailed"]], seed=run["seed"], known=_discovered(chart))["end"])


def _plot_end(chart):
    est = _plot(chart)
    return (est[-1][1], est[-1][2])


def _goal_lines(chart):
    return [_goal_text(s) if not _two(chart) else "Ship %s: %s" % (fleet.TAGS[i], _goal_text(s)) for i, s in enumerate(fleet.ships(chart))]


def _goal_text(chart):
    return "Reach the flag (within %g nm) in %g hours or less. Speed %s kn." % (
        chart["arrival_radius"], chart["deadline"], render.range_text(chart["speeds"], "").strip())


def _fleet_goal(chart):
    return " ".join(_goal_lines(chart)) + " " + fleet.rule_text()


def _chart_info(chart):
    return {"id": chart["id"], "name": chart["name"], "chapter": chart.get("chapter", ""), "deadline": chart["deadline"],
            "arrival_radius": chart["arrival_radius"], "speeds": chart["speeds"], "size": chart["size"],
            "goal": _fleet_goal(chart) if _two(chart) else _goal_text(chart), "two": _two(chart), "intro": chart.get("intro", ""), "mode": run["mode"], "modes": list(chart.get("modes", ["plan"])),
            "start_hour": chart.get("start_hour", 0.0), "practice": _practice_info(chart), "daily": _daily_info(chart)}


def _daily_info(chart):
    if not daily.is_daily_id(chart["id"]):
        return None
    date = daily.date_of(chart["id"])
    s = daily.spec(date)
    return {"date": date, "number": s["number"], "difficulty": s["difficulty"], "name": gen.NAMES[s["difficulty"]]}


def _practice_info(chart):
    if not gen.is_practice_id(chart["id"]):
        return None
    d, seed, two = gen.parse_ex(chart["id"])
    return {"difficulty": d, "code": gen.code_of(d, seed, two), "name": gen.NAMES[d], "two": two}


def _frame(chart):
    fr = render.Frame(chart)
    return {"left": render.LEFT, "top": render.TOP, "s": round(fr.s, 4), "size": chart["size"]}


def _picker():
    records = meta["charts"]
    open_chapters = charts.unlocked_chapters(records)
    out = []
    for i, chapter in enumerate(charts.CHAPTERS):
        unlocked = chapter["id"] in open_chapters
        prev = charts.CHAPTERS[i - 1] if i else None
        out.append({"id": chapter["id"], "name": chapter["name"], "blurb": chapter["blurb"], "unlocked": unlocked,
                    "cleared": charts.chapter_cleared(chapter, records), "total": len(chapter["charts"]),
                    "lock_text": "" if unlocked else "Clear %d charts in %s to open this chapter." % (
                        min(charts.CLEAR_TO_OPEN_NEXT, len(prev["charts"])), prev["name"]),
                    "charts": [{"id": c["id"], "name": c["name"], "stars": _record(c["id"])["stars"], "current": c["id"] == run["chart_id"]}
                               for c in chapter["charts"]]})
    return out


def _story():
    """The captain's log: the opening line of every chart the player has tried, and how a cleared one ended."""
    entries = []
    for chapter in charts.CHAPTERS:
        for c in chapter["charts"]:
            rec = _record(c["id"])
            if rec["attempts"] or c["id"] == run["chart_id"]:
                text = c["intro"] + ((" " + c["log"]["arrived"]) if rec["stars"] >= 1 else "")
                entries.append({"id": c["id"], "name": c["name"], "text": text})
    return entries


def _log_line(chart, sc):
    log = chart.get("log") or {}
    if sc["aground"]:
        return log.get("aground", "")
    if sc["arrived"]:
        return log.get("late" if not sc["on_time"] else "arrived", "")
    return log.get("missed", "")


def _par_view(chart):
    """The par plan as text (and the data to draw it) once the player has made an attempt, or just whether it can be shown."""
    seen = run["par"] if _scoped(chart["id"]) else _record(chart["id"])["par_seen"]
    legs = charts.par_legs(chart["id"])
    if not legs or _attempts(chart) < 1:
        return None
    if not seen:
        return {"available": True, "shown": False}
    if _two(chart):
        legs2 = charts.par_legs2(chart["id"]) or []
        lines = (["Ship A, leg %d: steer %03d at %g kn for %g h." % (i + 1, leg["heading"], leg["speed"], leg["hours"]) for i, leg in enumerate(legs)]
                 + ["Ship B, leg %d: steer %03d at %g kn for %g h." % (i + 1, leg["heading"], leg["speed"], leg["hours"]) for i, leg in enumerate(legs2)])
        return {"available": True, "shown": True, "legs": legs, "legs2": legs2, "lines": lines}
    return {"available": True, "shown": True, "legs": legs,
            "lines": ["Leg %d: steer %03d at %g kn for %g h." % (i + 1, leg["heading"], leg["speed"], leg["hours"]) for i, leg in enumerate(legs)]}


def _daily_view():
    """What the Daily Chart panel shows: today's chart, the saved results and the tally. None until the view passes the date in."""
    if today is None:
        return None
    open_today = today >= daily.EPOCH
    s = daily.spec(today) if open_today else None
    days_done = {d: dict(r) for d, r in meta["daily_days"].items()}
    active = daily.date_of(run["chart_id"]) if run is not None else None
    out = {"today": today, "epoch": daily.EPOCH, "open": open_today, "number": s["number"] if s else 0,
           "level": {"difficulty": s["difficulty"], "name": gen.NAMES[s["difficulty"]]} if s else None,
           "record": days_done.get(today), "days": days_done, "tally": daily.tally(meta["daily_days"], today), "active": active}
    if active and run["phase"] == "reveal" and active in days_done:
        out["entry"] = daily.leaderboard_entry(active, days_done[active])      # HOOK only: nothing sends this anywhere
    return out


def _view():
    view = _view_phase()
    view["daily"] = _daily_view()
    view["picker"] = _picker()
    view["story"] = {"intro": _chart().get("intro", ""), "log": _story()}
    view["progress"] = _progress()
    view["practice_levels"] = [{"difficulty": d, "name": gen.NAMES[d]} for d in gen.DIFFICULTIES]
    view["note"] = note
    view["info"] = info.view()
    view["achievements"] = achievements.view(meta, _chapter_ids())
    return view


def _view_phase():
    chart = _chart()
    if run["phase"] == "reveal":
        return _reveal_view(chart)
    return _plan_view(chart)


# --- the planning view ---------------------------------------------------------------------------
def _plan_view(chart):
    if _two(chart):
        return _plan_view_fleet(chart)
    legs = run["legs"]
    est = _plot(chart)
    plot_end = (est[-1][1], est[-1][2])
    hours = sim.plan_hours(legs)
    discovered = _discovered(chart)
    pt = None
    if point is not None:
        pt = {"x": point[0], "y": point[1], "bearing": round(bearing(plot_end, point)) % 360,
              "distance": round(dist(plot_end, point), 1)}
    believed = _believed(chart) if _watch() and run["sailed"] else None
    fix_points = [(fx["x"], fx["y"]) for fx in run["fixes"]]
    svg = render.render_chart(chart, est=est, marks=render.plan_marks(legs, est), sailed_legs=run["sailed"], discovered=discovered,
                              point=point, believed=believed, fixes=fix_points)
    return {
        "phase": "plan", "sailed": run["sailed"], "watch": _watch_view(chart) if _watch() else None, "chart": _chart_info(chart), "svg": svg, "frame": _frame(chart),
        "notes": render.chart_notes(chart, discovered), "legs": legs, "allow": run["allow"],
        "totals": {"legs": len(legs), "hours": hours, "distance": round(sim.plan_distance(legs), 1), "deadline": chart["deadline"],
                   "over": hours > chart["deadline"], "plot_end": [plot_end[0], plot_end[1]],
                   "plot_miss": round(dist(plot_end, chart["dest"]), 1)},
        "limits": {"speeds": chart["speeds"], "max_hours": sim.MAX_LEG_HOURS, "max_legs": state.MAX_LEGS},
        "helpers": {"naive": True, "current": current_helper_unlocked() and run["allow"],
                    "current_unlocked": current_helper_unlocked(), "current_after": CURRENT_HELPER_AFTER},
        "point": pt, "can_undo": bool(history), "stars": _record(chart["id"])["stars"],
    }


def _fleet_plan_line(approach):
    if approach is None:
        return "Plan both ships to see how close your plots bring them."
    if approach["too_close"]:
        return ("Your plots bring the ships to %.1f nm apart at hour %g: inside the %g nm rule, which would cost a star."
                % (approach["dist"], approach["t"], fleet.SEPARATION))
    return "Your plots keep the ships at least %.1f nm apart (closest at hour %g; the rule is %g nm)." % (approach["dist"], approach["t"], fleet.SEPARATION)


def _plan_view_fleet(chart):
    """The planning view of a two-ship chart: the active ship's legs and totals, both plots on the chart, and the plots' own closest approach."""
    ships = fleet.ships(chart)
    active = _ship_index(chart)
    ests = [_plot(chart, 0), _plot(chart, 1)]
    plans = [run["legs"], run["legs2"]]
    est = ests[active]
    plot_end = (est[-1][1], est[-1][2])
    discovered = _discovered(chart)
    pt = None
    if point is not None:
        pt = {"x": point[0], "y": point[1], "bearing": round(bearing(plot_end, point)) % 360,
              "distance": round(dist(plot_end, point), 1)}
    approach = dict(fleet.closest_approach(ests[0], ests[1]), kind="plot") if (plans[0] and plans[1]) else None
    svg = render.render_chart(chart, est=ests[0], marks=render.plan_marks(plans[0], ests[0]), discovered=discovered, point=point,
                              ship2={"est": ests[1], "marks": render.plan_marks(plans[1], ests[1])}, approach=approach)
    per_ship = []
    for i, ship in enumerate(ships):
        end = (ests[i][-1][1], ests[i][-1][2])
        hours = sim.plan_hours(plans[i])
        per_ship.append({"tag": fleet.TAGS[i], "legs": len(plans[i]), "hours": hours, "deadline": ship["deadline"], "over": hours > ship["deadline"],
                         "distance": round(sim.plan_distance(plans[i]), 1), "plot_miss": round(dist(end, ship["dest"]), 1)})
    mine = per_ship[active]
    return {
        "phase": "plan", "sailed": 0, "watch": None, "chart": _chart_info(chart), "svg": svg, "frame": _frame(chart),
        "notes": render.chart_notes(chart, discovered), "legs": plans[active], "allow": run["allow"],
        "totals": {"legs": mine["legs"], "hours": mine["hours"], "distance": mine["distance"], "deadline": mine["deadline"], "over": mine["over"],
                   "plot_end": [plot_end[0], plot_end[1]], "plot_miss": mine["plot_miss"]},
        "fleet": {"active": active, "ships": per_ship, "separation": fleet.SEPARATION, "rule": fleet.rule_text(),
                  "plot_closest": ({"dist": approach["dist"], "t": approach["t"], "too_close": approach["too_close"]} if approach else None),
                  "line": _fleet_plan_line(approach)},
        "limits": {"speeds": ships[active]["speeds"], "max_hours": sim.MAX_LEG_HOURS, "max_legs": state.MAX_LEGS},
        "helpers": {"naive": True, "current": current_helper_unlocked() and run["allow"],
                    "current_unlocked": current_helper_unlocked(), "current_after": CURRENT_HELPER_AFTER},
        "point": pt, "can_undo": bool(history), "stars": _record(chart["id"])["stars"],
    }


def _watch_view(chart):
    """What the watch officer knows between watches: the plot, any landmark in sight, what the last watch noticed."""
    sailed = run["sailed"]
    out = {"sailed": sailed, "readings": [], "applied": None, "log": [], "can_anchor": sailed > 0, "fog": bool(chart.get("fog")),
           "believed": None}
    if not sailed:
        return out
    believed = _believed(chart)
    out["believed"] = [believed[0], believed[1]]
    res = sim.sail(chart, run["legs"][:sailed], seed=run["seed"], known=_discovered(chart))
    out["log"] = [e["text"] for e in res["events"] if e["public"]]
    mine = {fx["after_leg"]: fx for fx in run["fixes"]}.get(sailed - 1)
    out["applied"] = mine["landmark"] if mine else None
    out["readings"] = fixes.readings(chart, tuple(res["end"]), sailed)
    return out


# --- the reveal ------------------------------------------------------------------------------------
def _stars_text(n):
    return "%d of 3 stars" % n


def _ship_line(tag, s, chart):
    if s["aground"]:
        return "Ship %s ran aground %.1f nm from its flag. The tide will lift her in a few hours; her passage is over." % (tag, s["miss_nm"])
    return "Ship %s finished %.1f nm from its flag (arrival radius %g nm)." % (tag, s["miss_nm"], chart["arrival_radius"])


def _reveal_view_fleet(chart):
    known = run.get("known", [])
    ships = fleet.ships(chart)
    plans = [run["legs"], run["legs2"]]
    res = fleet.sail_fleet(chart, plans[0], plans[1], seed=run["seed"], known=known)
    sc = fleet.score_fleet(chart, plans[0], plans[1], res, known=known, used_helpers=bool(run["helpers"]))
    ests = [_plot(chart, 0), _plot(chart, 1)]
    discovered = _discovered(chart)
    ra, rb = res["ships"]
    ap = res["approach"]
    par = _par_view(chart)
    par_plots = [None, None]
    if par and par["shown"]:
        par_plots = [sim.estimate(ships[0], par["legs"], allow=True), sim.estimate(ships[1], par["legs2"], allow=True)]
    svg = render.render_chart(chart, est=ests[0], marks=render.plan_marks(plans[0], ests[0]), true_track=ra["track"], discovered=discovered,
                              par_track=par_plots[0], ship2={"est": ests[1], "marks": render.plan_marks(plans[1], ests[1]),
                                                             "true_track": rb["track"], "par_track": par_plots[1]},
                              approach=dict(ap, kind="true"))
    lines = [_ship_line(fleet.TAGS[i], s, ships[i]) for i, s in enumerate(sc["ships"])]
    if ap["too_close"]:
        lines.append("The ships came within %.1f nm of each other at hour %g, inside the %g nm rule, which costs one star. Nothing was damaged: "
                     "a retry is free." % (ap["dist"], ap["t"], fleet.SEPARATION))
    else:
        lines.append("The ships came no closer than %.1f nm (at hour %g); the rule is %g nm." % (ap["dist"], ap["t"], fleet.SEPARATION))
    naive = [s["naive_miss_nm"] for s in sc["ships"]]
    lines.append("Steering each ship straight at its flag would have missed by %.1f nm (Ship A) and %.1f nm (Ship B)." % tuple(naive))
    if sc["forecast_error_nm"] is not None:
        f = [s["forecast_error_nm"] for s in sc["ships"]]
        lines.append("Your plots put Ship A %.1f nm and Ship B %.1f nm from where each really ended up." % (f[0], f[1]))
    if sc["arrived"]:
        title = "Landfall"
    elif sc["aground"]:
        title = "Aground"
    else:
        title = "Short of the flag"
    points = [[t, *render.svg_point(chart, x, y)] for t, x, y in ra["track"]]
    points2 = [[t, *render.svg_point(chart, x, y)] for t, x, y in rb["track"]]
    events = [{"t": e["t"], "text": e["text"], "public": e["public"]} for e in res["events"]]
    hours = [sim.plan_hours(p) for p in plans]
    return {
        "phase": "reveal", "chart": _chart_info(chart), "svg": svg, "frame": _frame(chart),
        "notes": render.chart_notes(chart, discovered), "legs": plans[0], "legs2": plans[1], "allow": run["allow"],
        "totals": {"legs": len(plans[0]) + len(plans[1]), "hours": max(hours), "distance": round(sim.plan_distance(plans[0]) + sim.plan_distance(plans[1]), 1),
                   "deadline": max(s["deadline"] for s in ships), "over": any(h > s["deadline"] for h, s in zip(hours, ships)),
                   "plot_end": [ests[0][-1][1], ests[0][-1][2]], "plot_miss": round(dist((ests[0][-1][1], ests[0][-1][2]), ships[0]["dest"]), 1)},
        "reveal": {"title": title, "stars": sc["stars"], "stars_text": _stars_text(sc["stars"]), "criteria": sc["criteria"],
                   "lines": lines, "events": events, "points": points, "points2": points2, "hours": res["hours"],
                   "approach": {"dist": ap["dist"], "t": ap["t"], "too_close": ap["too_close"], "separation": fleet.SEPARATION},
                   "miss_nm": sc["miss_nm"], "arrived": sc["arrived"], "aground": sc["aground"],
                   "best_stars": _record(chart["id"])["stars"] if not _scoped(chart["id"]) else 0,
                   "log": _fleet_log_line(chart, sc), "par": par, "next_chart": _next_playable(chart["id"])},
        "stars": _record(chart["id"])["stars"],
    }


def _fleet_log_line(chart, sc):
    log = chart.get("log") or {}
    if sc["aground"]:
        return log.get("aground", "")
    if sc["arrived"]:
        return log.get("late" if not sc["on_time"] else "arrived", "")
    return log.get("missed", "")


def _reveal_view(chart):
    if _two(chart):
        return _reveal_view_fleet(chart)
    legs = run["legs"][:run["sailed"]] if _watch() else run["legs"]
    known = run.get("known", [])
    res = sim.sail(chart, legs, seed=run["seed"], known=known)
    sc = sim.score(chart, legs, res, known=known, used_helpers=bool(run["helpers"]))
    est = _plot(chart)
    discovered = _discovered(chart)
    fix_points = [(fx["x"], fx["y"]) for fx in run["fixes"]]
    svg = render.render_chart(chart, est=est, marks=render.plan_marks(legs, est), true_track=res["track"], discovered=discovered,
                              fixes=fix_points)
    lines = []
    if sc["aground"]:
        lines.append("The ship ran aground %.1f nm from the flag. The tide will lift her in a few hours; the passage is over." % sc["miss_nm"])
    else:
        lines.append("You finished %.1f nm from the flag (arrival radius %g nm)." % (sc["miss_nm"], chart["arrival_radius"]))
    if sc["naive_miss_nm"] >= 1.0:
        if sc["beat_naive_pct"] and not sc["aground"]:
            lines.append("Steering straight at the flag would have missed by %.1f nm; you beat that by %d percent." % (sc["naive_miss_nm"], sc["beat_naive_pct"]))
        else:
            lines.append("Steering straight at the flag would have missed by %.1f nm." % sc["naive_miss_nm"])
    else:
        lines.append("Steering straight at the flag works here: it would finish %.1f nm out." % sc["naive_miss_nm"])
    if sc["forecast_error_nm"] is not None:
        lines.append("Your plot put you %.1f nm from where the ship really ended up." % sc["forecast_error_nm"])
    if run["fixes"]:
        lines.append("You took %d fix%s from landmarks along the way." % (len(run["fixes"]), "" if len(run["fixes"]) == 1 else "es"))
    if sc["arrived"]:
        title = "Landfall"
    elif sc["aground"]:
        title = "Aground"
    else:
        title = "Short of the flag" if sc["miss_nm"] > chart["arrival_radius"] else "Landfall"
    par = _par_view(chart)
    par_plot = None
    if par and par["shown"]:
        par_plot = sim.estimate(chart, par["legs"], allow=True)
        svg = render.render_chart(chart, est=est, marks=render.plan_marks(legs, est), true_track=res["track"], discovered=discovered,
                                  par_track=par_plot, fixes=fix_points)
    points = [[t, *render.svg_point(chart, x, y)] for t, x, y in res["track"]]
    events = [{"t": e["t"], "text": e["text"], "public": e["public"]} for e in res["events"]]
    return {
        "phase": "reveal", "chart": _chart_info(chart), "svg": svg, "frame": _frame(chart),
        "notes": render.chart_notes(chart, discovered), "legs": legs, "allow": run["allow"],
        "totals": {"legs": len(legs), "hours": sim.plan_hours(legs), "distance": round(sim.plan_distance(legs), 1),
                   "deadline": chart["deadline"], "over": sim.plan_hours(legs) > chart["deadline"],
                   "plot_end": [est[-1][1], est[-1][2]], "plot_miss": round(dist((est[-1][1], est[-1][2]), chart["dest"]), 1)},
        "reveal": {"title": title, "stars": sc["stars"], "stars_text": _stars_text(sc["stars"]), "criteria": sc["criteria"],
                   "lines": lines, "events": events, "points": points, "hours": res["hours"],
                   "miss_nm": sc["miss_nm"], "arrived": sc["arrived"], "aground": sc["aground"],
                   "best_stars": (meta["daily_days"].get(daily.date_of(chart["id"]), {}).get("stars", 0) if daily.is_daily_id(chart["id"]) else _record(chart["id"])["stars"]), "log": _log_line(chart, sc), "par": par,
                   "next_chart": _next_playable(chart["id"])},
        "stars": _record(chart["id"])["stars"],
    }


def _next_playable(chart_id):
    if _scoped(chart_id):
        return None
    nxt = charts.next_chart_id(chart_id)
    if nxt is None or _record(chart_id)["stars"] < 1 or not charts.is_unlocked(nxt, meta["charts"]):
        return None
    return {"id": nxt, "name": charts.get_chart(nxt)["name"]}


def _finish():
    """End the passage and score it (a full plan sails everything; a watch passage ends with the watches already sailed)."""
    chart = _chart()
    run["known"] = list(_discovered(chart))
    if _watch():
        del run["legs"][run["sailed"]:]
    else:
        run["sailed"] = 0
    legs = run["legs"]
    if _two(chart):
        res = fleet.sail_fleet(chart, legs, run["legs2"], seed=run["seed"], known=run["known"])
        sc = fleet.score_fleet(chart, legs, run["legs2"], res, known=run["known"], used_helpers=bool(run["helpers"]))
        groundings = res["groundings"]
    else:
        res = sim.sail(chart, legs, seed=run["seed"], known=run["known"])
        sc = sim.score(chart, legs, res, known=run["known"], used_helpers=bool(run["helpers"]))
        groundings = [res["aground"]] if res["aground"] else []
    scoped = _scoped(chart["id"])
    progress.record_outcome(meta, chart, run, res, sc, scored=not scoped, fix_taken=bool(run["fixes"]))
    if scoped:
        known = {h["id"] for h in chart["hazards"] if h.get("charted", True)}
        touched = list(res["close"]) + [g["hazard"] for g in groundings]
        found = set(run["found"]) | {h for h in touched if h not in known and any(x["id"] == h for x in chart["hazards"])}
        run["found"] = sorted(found)
        if daily.is_daily_id(chart["id"]):
            # Only the date's own record changes: the practice total and the campaign records stay as they were.
            date = daily.date_of(chart["id"])
            meta["daily_days"][date] = daily.merge_record(meta["daily_days"].get(date), sc["stars"], sc["miss_nm"], sc["arrived"])
            run["counted"] = True
        elif not run["counted"]:
            run["counted"] = True
            meta["practice_seeds_played"] += 1
    run["phase"] = "reveal"


def _sail_watch(chart):
    """Sail the one pending leg (a watch). The passage ends by itself only when the ship runs aground."""
    if len(run["legs"]) <= run["sailed"]:
        return
    del run["legs"][run["sailed"] + 1:]
    run["sailed"] = len(run["legs"])
    res = sim.sail(chart, run["legs"], seed=run["seed"], known=_discovered(chart))
    if res["aground"] or run["sailed"] >= state.MAX_LEGS:
        _finish()


# --- the one entry point ---------------------------------------------------------------------------
def _leg_index(request):
    i = request.get("i")
    if isinstance(i, bool) or not isinstance(i, int) or not run["sailed"] <= i < len(_legs()):
        return None
    return i


def _default_leg(chart):
    ship = _sc(chart)
    end = _believed(chart) if _watch() else _plot_end(chart)
    return sim.clean_leg(ship, {"heading": round(bearing(end, ship["dest"])), "speed": sim.cruise_speed(ship), "hours": 1.0})


def _start_practice(request):
    """Open a practice chart: from a share code, or from a seed (the page may pass one) or the next repeatable seed."""
    global note
    code = request.get("code")
    if isinstance(code, str) and code.strip():
        parsed = gen.parse_ex(code)
        chart = gen.make_chart(*parsed) if parsed else None
        if chart is None:
            note = "That is not a practice code the game can make. A code looks like DR3-1K9X2 (DR3T-1K9X2 for two ships)."
            return False
        _start(chart["id"])
        return True
    d = request.get("difficulty")
    if d not in gen.DIFFICULTIES or isinstance(d, bool):
        return False
    two = request.get("two") is True
    seed = request.get("seed")
    explicit = isinstance(seed, int) and not isinstance(seed, bool) and 0 <= seed < gen.SEED_LIMIT
    for nonce in range(10):
        s = seed + nonce if explicit else gen.next_seed(meta["practice_seeds_played"], d, nonce)
        chart = gen.make_chart(d, s % gen.SEED_LIMIT, two)
        if chart is not None:
            _start(chart["id"])
            return True
    note = "No practice chart could be made just now. Try another difficulty."
    return False


def _start_daily(request):
    """Open the Daily Chart for a date (any date from the epoch to today). The plan on the page is replaced."""
    global note
    if today is None:
        note = "The date is not known yet."
        return False
    date = request.get("date")
    if not daily.valid_date(date) or date < daily.EPOCH:
        note = "There was no daily chart on that date."
        return False
    if not daily.playable(date, today):
        note = "That daily chart is not out yet."
        return False
    if run is not None and run["chart_id"] == daily.chart_id(date):
        return True
    _start(daily.chart_id(date))
    return True


def _chapter_ids():
    return [[c["id"] for c in chapter["charts"]] for chapter in charts.CHAPTERS]


def _progress():
    records = meta["charts"]
    total = len(charts.ORDER)
    return {"cleared": sum(1 for cid in charts.ORDER if records.get(cid, {}).get("stars", 0) >= 1), "total": total,
            "stars": sum(records.get(cid, {}).get("stars", 0) for cid in charts.ORDER), "stars_total": 3 * total,
            "practice_played": meta["practice_seeds_played"], "best_error": meta["best"]["smallest_final_error_nm"],
            "longest_route": meta["best"]["longest_route_nm"]}


def handle(request_json):
    global run, point, meta, history, note, today
    note = ""
    try:
        request = json.loads(request_json)
        action = request.get("action")
    except (ValueError, AttributeError):
        return json.dumps({"error": "bad request"})
    if "today" in request:
        today = request["today"] if daily.valid_date(request["today"]) else None
    if run is not None and daily.is_daily_id(run["chart_id"]) and today is not None and not daily.playable(daily.date_of(run["chart_id"]), today):
        run = None                                  # a saved daily for a date that has not started yet is dropped
    if action == "reset":
        meta = state.new_meta()
        run = None
        point = None
        history = []
    elif action == "practice":
        _start_practice(request)
    elif action == "start_daily":
        _start_daily(request)
    elif action == "start":
        cid = request.get("chart_id")
        if not isinstance(cid, str) or charts.get_chart(cid) is None:
            return json.dumps({"error": "unknown chart"})
        if not charts.is_unlocked(cid, meta["charts"]):
            return json.dumps({"error": "that chapter is not open yet"})
        _start(cid)
    _ensure_run()
    chart = _chart()
    editing = run["phase"] == "plan"
    if action in ("open", "start", "reset", "practice", "start_daily", None):
        pass
    elif action == "select_ship":
        if _two(chart) and request.get("ship") in (0, 1) and not isinstance(request.get("ship"), bool):
            run["ship"] = request["ship"]
    elif action == "retry":
        run["phase"] = "plan"
        run.pop("known", None)
    elif action == "next_chart":
        nxt = _next_playable(run["chart_id"])
        if nxt is not None:
            _start(nxt["id"])
    elif action == "show_par":
        if _par_view(chart):
            if _scoped(chart["id"]):
                run["par"] = True
            else:
                meta["charts"].setdefault(chart["id"], state.new_record())["par_seen"] = True
    elif action == "use_par":
        legs = charts.par_legs(chart["id"])
        if legs and _attempts(chart) >= 1:
            run["phase"] = "plan"
            run.pop("known", None)
            run["legs"] = sim.clean_legs(chart, legs, limit=state.MAX_LEGS)
            if _two(chart):
                run["legs2"] = sim.clean_legs(fleet.ship_chart(chart, 1), charts.par_legs2(chart["id"]) or [], limit=state.MAX_LEGS)
            run["helpers"] = ["par"]
            history = []
    elif action == "restart":
        run["phase"] = "plan"
        run.pop("known", None)
        run["legs"] = []
        run["legs2"] = []
        run["helpers"] = []
        run["sailed"] = 0
        run["fixes"] = []
        history = []
    elif action == "sail":
        if editing and _watch():
            _sail_watch(chart)
        elif editing:
            _finish()
    elif action == "anchor":
        if editing and _watch() and run["sailed"] > 0:
            _finish()
    elif not editing:
        return json.dumps({"error": "the passage is over: retry or pick a chart"})
    elif action == "add_wait":
        if len(_legs()) < state.MAX_LEGS and not (_watch() and len(_legs()) > run["sailed"]):
            _snapshot()
            _legs().append({"heading": 0, "speed": 0.0, "hours": 1.0})
    elif action == "set_mode":
        mode = request.get("mode")
        if mode in chart.get("modes", ("plan",)) and mode != run["mode"] and run["sailed"] == 0:
            run["mode"] = mode
            run["legs"] = []
            run["legs2"] = []
            run["helpers"] = []
            history = []
    elif action == "take_fix":
        _take_fix(chart, request)
    elif action == "add_leg":
        if len(_legs()) < state.MAX_LEGS and not (_watch() and len(_legs()) > run["sailed"]):
            _snapshot()
            _legs().append(_default_leg(chart))
    elif action == "set_leg":
        i = _leg_index(request)
        if i is not None:
            _snapshot()
            merged = dict(_legs()[i])
            for field in ("heading", "speed", "hours"):
                if field in request:
                    merged[field] = request[field]
            _legs()[i] = sim.clean_leg(_sc(chart), merged)
    elif action == "nudge":
        i = _leg_index(request)
        field, delta = request.get("field"), request.get("delta")
        if i is not None and field in ("heading", "speed", "hours") and isinstance(delta, (int, float)) and not isinstance(delta, bool):
            _snapshot()
            merged = dict(_legs()[i])
            merged[field] = merged[field] + delta
            _legs()[i] = sim.clean_leg(_sc(chart), merged)
    elif action == "remove_leg":
        i = _leg_index(request)
        if i is not None:
            _snapshot()
            del _legs()[i]
    elif action == "undo":
        if history:
            ship, prev = history.pop()
            if ship == 0 and prev[:run["sailed"]] == run["legs"][:run["sailed"]] and len(prev) >= run["sailed"]:
                run["legs"] = prev
                if _two(chart):
                    run["ship"] = 0
            elif ship == 1 and _two(chart):
                run["legs2"] = prev
                run["ship"] = 1
    elif action == "clear":
        if len(_legs()) > run["sailed"]:
            _snapshot()
        del _legs()[run["sailed"]:]
        if not run["sailed"] and not (_two(chart) and (run["legs"] or run["legs2"])):
            run["helpers"] = []
    elif action == "allow":
        run["allow"] = request.get("value") is not False
    elif action == "helper":
        _helper(chart, request)
    elif action == "point":
        x, y = request.get("x"), request.get("y")
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (x, y)):
            point = (round(max(0.0, min(float(chart["size"]), x)), 1), round(max(0.0, min(float(chart["size"]), y)), 1))
    elif action == "clear_point":
        point = None
    else:
        return json.dumps({"error": "unknown action %r" % (action,)})
    return json.dumps(_view())


def _take_fix(chart, request):
    """Apply a landmark fix: the plot jumps to where the readings put the ship. The true position is never revealed."""
    if not _watch() or run["sailed"] < 1:
        return
    options = {r["id"]: r for r in _watch_view(chart)["readings"]}
    reading = options.get(request.get("landmark"))
    if reading is None:
        return
    pos = fixes.position_from(chart, reading["id"], reading["bearing"], reading["range"])
    after = run["sailed"] - 1
    run["fixes"] = [fx for fx in run["fixes"] if fx["after_leg"] != after]
    run["fixes"].append({"after_leg": after, "x": pos[0], "y": pos[1], "landmark": reading["id"]})


def _helper(chart, request):
    kind = request.get("kind")
    if kind not in ("naive", "current"):
        return
    ship = _sc(chart)
    if _watch():
        del run["legs"][run["sailed"]:]
    if len(_legs()) >= state.MAX_LEGS:
        return
    target = tuple(ship["dest"]) if request.get("target") != "point" or point is None else point
    here = _believed(chart) if _watch() else _plot_end(chart)
    if dist(here, target) < 0.05:
        return
    if kind == "naive":
        leg = sim.naive_legs(ship, start=here, target=target)[0]
    else:
        if not (current_helper_unlocked() and run["allow"]):
            return
        leg = solver.shoot(ship, here, target, model="charted", t_start=sim.plan_hours(_legs()))
        if leg is None:
            return
    _snapshot()
    _legs().append(leg)
    if kind not in run["helpers"]:
        run["helpers"].append(kind)


# --- the save contract ---------------------------------------------------------------------------
def get_state():
    data = {"schema": state.SCHEMA}
    m = state.meta_to_dict(meta)
    if m:
        data["meta"] = m
    # A write-only projection for the hub's achievements dashboard, recomputed here and never read back.
    earned = achievements.earned(meta, _chapter_ids())
    if earned:
        data["achievements_earned"] = earned
    if run is not None and (run["legs"] or run["phase"] != "plan"):
        data["run"] = state.run_to_dict(run)
    return data


def load_state(data):
    """Merge a saved state in: records keep the better of each, flags are unioned and an unfinished plan is adopted."""
    global meta, run, point, history
    try:
        incoming = state.clean_meta((data or {}).get("meta"), charts.hazard_ids())
        meta = state.merge_meta(meta, incoming)
        loaded = state.clean_run((data or {}).get("run"), charts.get_chart)
        if loaded is not None:
            run = loaded
            point = None
            history = []
    except (ValueError, TypeError, AttributeError, KeyError, OverflowError):
        pass
    _refresh_view()


def _refresh_view():
    """Ask the page to redraw after a save is loaded (the save widget calls load_state directly and knows nothing
    about this game's view). Under plain CPython there is no page, so this is a no-op."""
    try:
        import js
        refresh = getattr(js.window, "deadReckoningRefresh", None)
        if refresh is not None:
            refresh()
    except Exception:
        pass
