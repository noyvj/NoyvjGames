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
  next_chart                 open the next chart in the campaign (when it is unlocked)
  show_par | use_par         reveal the authored plan after a first attempt / load it into the planner
  reset                      forget all progress
"""

import json

import charts
import fixes
import progress
import render
import sim
import solver
import state
from geom import bearing, dist

meta = state.new_meta()
run = None
point = None
history = []            # earlier leg lists, for Undo (never saved)
HISTORY_LIMIT = 40
CURRENT_HELPER_AFTER = 3   # the "allow for the charted current" helper unlocks after this many charts are cleared


# --- helpers -------------------------------------------------------------------------------------
def _chart():
    return charts.get_chart(run["chart_id"])


def _record(chart_id):
    return meta["charts"].get(chart_id) or state.new_record()


def _cleared():
    return sum(1 for rec in meta["charts"].values() if rec["stars"] >= 1)


def current_helper_unlocked():
    return _cleared() >= CURRENT_HELPER_AFTER


def _start(chart_id, mode=None, seed=0):
    global run, point, history
    chart = charts.get_chart(chart_id)
    if mode not in chart.get("modes", ("plan",)):
        mode = chart.get("default_mode", "plan")
    run = state.new_run(chart_id, seed, mode)
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
    history.append([dict(leg) for leg in run["legs"]])
    del history[:-HISTORY_LIMIT]


def _watch():
    return run["mode"] == "watch"


def _plot(chart):
    return sim.estimate(chart, run["legs"], allow=run["allow"], fixes=run["fixes"])


def _believed(chart):
    """Where the player believes the ship is after the watches already sailed (their plot, fixes included)."""
    est = sim.estimate(chart, run["legs"][:run["sailed"]], allow=run["allow"], fixes=run["fixes"])
    return (est[-1][1], est[-1][2])


def _true_pos(chart):
    """The ship's real position after the watches sailed. Used ONLY to work out what a fix would read; never shown."""
    return tuple(sim.sail(chart, run["legs"][:run["sailed"]], seed=run["seed"], known=_record(chart["id"])["discovered"])["end"])


def _plot_end(chart):
    est = _plot(chart)
    return (est[-1][1], est[-1][2])


def _goal_text(chart):
    return "Reach the flag (within %g nm) in %g hours or less. Speed %s kn." % (
        chart["arrival_radius"], chart["deadline"], render.range_text(chart["speeds"], "").strip())


def _chart_info(chart):
    return {"id": chart["id"], "name": chart["name"], "chapter": chart.get("chapter", ""), "deadline": chart["deadline"],
            "arrival_radius": chart["arrival_radius"], "speeds": chart["speeds"], "size": chart["size"],
            "goal": _goal_text(chart), "intro": chart.get("intro", ""), "mode": run["mode"], "modes": list(chart.get("modes", ["plan"])),
            "start_hour": chart.get("start_hour", 0.0)}


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
    rec = _record(chart["id"])
    legs = charts.par_legs(chart["id"])
    if not legs or rec["attempts"] < 1:
        return None
    if not rec["par_seen"]:
        return {"available": True, "shown": False}
    return {"available": True, "shown": True, "legs": legs,
            "lines": ["Leg %d: steer %03d at %g kn for %g h." % (i + 1, leg["heading"], leg["speed"], leg["hours"]) for i, leg in enumerate(legs)]}


def _view():
    view = _view_phase()
    view["picker"] = _picker()
    view["story"] = {"intro": _chart().get("intro", ""), "log": _story()}
    return view


def _view_phase():
    chart = _chart()
    if run["phase"] == "reveal":
        return _reveal_view(chart)
    return _plan_view(chart)


# --- the planning view ---------------------------------------------------------------------------
def _plan_view(chart):
    legs = run["legs"]
    est = _plot(chart)
    plot_end = (est[-1][1], est[-1][2])
    hours = sim.plan_hours(legs)
    discovered = _record(chart["id"])["discovered"]
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


def _watch_view(chart):
    """What the watch officer knows between watches: the plot, any landmark in sight, what the last watch noticed."""
    sailed = run["sailed"]
    out = {"sailed": sailed, "readings": [], "applied": None, "log": [], "can_anchor": sailed > 0, "fog": bool(chart.get("fog")),
           "believed": None}
    if not sailed:
        return out
    believed = _believed(chart)
    out["believed"] = [believed[0], believed[1]]
    res = sim.sail(chart, run["legs"][:sailed], seed=run["seed"], known=_record(chart["id"])["discovered"])
    out["log"] = [e["text"] for e in res["events"] if e["public"]]
    mine = {fx["after_leg"]: fx for fx in run["fixes"]}.get(sailed - 1)
    out["applied"] = mine["landmark"] if mine else None
    out["readings"] = fixes.readings(chart, tuple(res["end"]), sailed)
    return out


# --- the reveal ------------------------------------------------------------------------------------
def _stars_text(n):
    return "%d of 3 stars" % n


def _reveal_view(chart):
    legs = run["legs"][:run["sailed"]] if _watch() else run["legs"]
    known = run.get("known", [])
    res = sim.sail(chart, legs, seed=run["seed"], known=known)
    sc = sim.score(chart, legs, res, known=known, used_helpers=bool(run["helpers"]))
    est = _plot(chart)
    discovered = _record(chart["id"])["discovered"]
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
                   "best_stars": _record(chart["id"])["stars"], "log": _log_line(chart, sc), "par": par,
                   "next_chart": _next_playable(chart["id"])},
        "stars": _record(chart["id"])["stars"],
    }


def _next_playable(chart_id):
    nxt = charts.next_chart_id(chart_id)
    if nxt is None or _record(chart_id)["stars"] < 1 or not charts.is_unlocked(nxt, meta["charts"]):
        return None
    return {"id": nxt, "name": charts.get_chart(nxt)["name"]}


def _finish():
    """End the passage and score it (a full plan sails everything; a watch passage ends with the watches already sailed)."""
    chart = _chart()
    rec = _record(chart["id"])
    run["known"] = list(rec["discovered"])
    if _watch():
        del run["legs"][run["sailed"]:]
    else:
        run["sailed"] = 0
    legs = run["legs"]
    res = sim.sail(chart, legs, seed=run["seed"], known=run["known"])
    sc = sim.score(chart, legs, res, known=run["known"], used_helpers=bool(run["helpers"]))
    progress.record_outcome(meta, chart, run, res, sc, fix_taken=bool(run["fixes"]))
    run["phase"] = "reveal"


def _sail_watch(chart):
    """Sail the one pending leg (a watch). The passage ends by itself only when the ship runs aground."""
    if len(run["legs"]) <= run["sailed"]:
        return
    del run["legs"][run["sailed"] + 1:]
    run["sailed"] = len(run["legs"])
    res = sim.sail(chart, run["legs"], seed=run["seed"], known=_record(chart["id"])["discovered"])
    if res["aground"] or run["sailed"] >= state.MAX_LEGS:
        _finish()


# --- the one entry point ---------------------------------------------------------------------------
def _leg_index(request):
    i = request.get("i")
    if isinstance(i, bool) or not isinstance(i, int) or not run["sailed"] <= i < len(run["legs"]):
        return None
    return i


def _default_leg(chart):
    end = _believed(chart) if _watch() else _plot_end(chart)
    return sim.clean_leg(chart, {"heading": round(bearing(end, chart["dest"])), "speed": sim.cruise_speed(chart), "hours": 1.0})


def handle(request_json):
    global run, point, meta, history
    try:
        request = json.loads(request_json)
        action = request.get("action")
    except (ValueError, AttributeError):
        return json.dumps({"error": "bad request"})
    if action == "reset":
        meta = state.new_meta()
        run = None
        point = None
        history = []
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
    if action in ("open", "start", "reset", None):
        pass
    elif action == "retry":
        run["phase"] = "plan"
        run.pop("known", None)
    elif action == "next_chart":
        nxt = _next_playable(run["chart_id"])
        if nxt is not None:
            _start(nxt["id"])
    elif action == "show_par":
        if _par_view(chart):
            meta["charts"].setdefault(chart["id"], state.new_record())["par_seen"] = True
    elif action == "use_par":
        legs = charts.par_legs(chart["id"])
        if legs and _record(chart["id"])["attempts"] >= 1:
            run["phase"] = "plan"
            run.pop("known", None)
            run["legs"] = sim.clean_legs(chart, legs, limit=state.MAX_LEGS)
            run["helpers"] = ["par"]
            history = []
    elif action == "restart":
        run["phase"] = "plan"
        run.pop("known", None)
        run["legs"] = []
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
        if len(run["legs"]) < state.MAX_LEGS and not (_watch() and len(run["legs"]) > run["sailed"]):
            _snapshot()
            run["legs"].append({"heading": 0, "speed": 0.0, "hours": 1.0})
    elif action == "set_mode":
        mode = request.get("mode")
        if mode in chart.get("modes", ("plan",)) and mode != run["mode"] and run["sailed"] == 0:
            run["mode"] = mode
            run["legs"] = []
            run["helpers"] = []
            history = []
    elif action == "take_fix":
        _take_fix(chart, request)
    elif action == "add_leg":
        if len(run["legs"]) < state.MAX_LEGS and not (_watch() and len(run["legs"]) > run["sailed"]):
            _snapshot()
            run["legs"].append(_default_leg(chart))
    elif action == "set_leg":
        i = _leg_index(request)
        if i is not None:
            _snapshot()
            merged = dict(run["legs"][i])
            for field in ("heading", "speed", "hours"):
                if field in request:
                    merged[field] = request[field]
            run["legs"][i] = sim.clean_leg(chart, merged)
    elif action == "nudge":
        i = _leg_index(request)
        field, delta = request.get("field"), request.get("delta")
        if i is not None and field in ("heading", "speed", "hours") and isinstance(delta, (int, float)) and not isinstance(delta, bool):
            _snapshot()
            merged = dict(run["legs"][i])
            merged[field] = merged[field] + delta
            run["legs"][i] = sim.clean_leg(chart, merged)
    elif action == "remove_leg":
        i = _leg_index(request)
        if i is not None:
            _snapshot()
            del run["legs"][i]
    elif action == "undo":
        if history:
            prev = history.pop()
            if prev[:run["sailed"]] == run["legs"][:run["sailed"]] and len(prev) >= run["sailed"]:
                run["legs"] = prev
    elif action == "clear":
        if len(run["legs"]) > run["sailed"]:
            _snapshot()
        del run["legs"][run["sailed"]:]
        if not run["sailed"]:
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
    if _watch():
        del run["legs"][run["sailed"]:]
    if len(run["legs"]) >= state.MAX_LEGS:
        return
    target = tuple(chart["dest"]) if request.get("target") != "point" or point is None else point
    here = _believed(chart) if _watch() else _plot_end(chart)
    if dist(here, target) < 0.05:
        return
    if kind == "naive":
        leg = sim.naive_legs(chart, start=here, target=target)[0]
    else:
        if not (current_helper_unlocked() and run["allow"]):
            return
        leg = solver.shoot(chart, here, target, model="charted", t_start=sim.plan_hours(run["legs"]))
        if leg is None:
            return
    _snapshot()
    run["legs"].append(leg)
    if kind not in run["helpers"]:
        run["helpers"].append(kind)


# --- the save contract ---------------------------------------------------------------------------
def get_state():
    data = {"schema": state.SCHEMA}
    m = state.meta_to_dict(meta)
    if m:
        data["meta"] = m
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
