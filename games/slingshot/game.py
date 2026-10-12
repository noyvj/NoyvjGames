"""Slingshot -- the engine's single entry point (the Constellations / Picture Grid pattern).

The view (app.js) never reads engine objects: it sends one JSON string to `handle` and draws the JSON that comes back. `get_state()` /
`load_state()` are the shared save widget's contract (planning/SAVE-BUTTON-INTEGRATION.md). Nothing here reads a clock or a random source:
a flight is a pure function of the mission and the plan (orbit.py).

Actions (every request is {"action": ..., ...}; every reply is the whole view):
  open                         the current view
  pick {mission}               go to a mission (it must be in an open chapter)
  next                         go to the next open mission that is not done yet
  burn_add {t, head, dv, at}   add a burn (at: time | peri | apo; head in degrees from the velocity; dv in km/s)
  burn_set {i, ...}            change fields of burn i
  burn_del {i}                 remove burn i
  pass_set {body, dv}          set the closest-approach burn at a body (negative slows down; 0 removes it)
  plan_clear                   remove every burn
  undo / redo                  step back / forward through plan changes on this mission (this session only)
  fly                          fly the plan: counts as a flight, and records the mission if it reaches the goal within the budget
  scrub                        the player used the time slider (counted in the tally)
  reset                        start over (everything)

The view always carries the flight the current plan makes (the "predicted path"), so Fly is the commit and not the first look.
"""

import json
import math

import atlas
import bodies
import bodies_data as D
import info
import missions
import orbit
import plan as planlib

TALLY_KEYS = ("flights", "edits", "scrubs")
MAX_COUNT = 10 ** 9
MAX_UNDO = 100
SCHEMA = 1
PROBE = "Wren"
UNITS = {"h": ("hour", 0.1, 1), "min": ("minute", 1.0, 0), "d": ("day", 0.25, 2)}
_flight_cache = {}


def _int(value, low=0, high=MAX_COUNT, default=0):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        return default
    return value


def _float(value, low, high, default=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value or not low <= value <= high:
        return default
    return float(value)


# ---- words ---------------------------------------------------------------------------------------------------------------------------
def _grouped(x, digits=0):
    return "{:,.{d}f}".format(x, d=digits)


def km(x):
    """Kilometres in words a person can read: 12,345 km, or 1.23 million km."""
    x = float(x)
    if abs(x) >= 1e7:
        return "%.1f million km" % (x / 1e6)
    if abs(x) >= 1e6:
        return "%.2f million km" % (x / 1e6)
    return "%s km" % _grouped(x)


def speed(v):
    return "%.2f km/s" % v


def nm(b):
    """A body's name inside a sentence."""
    return bodies.label(b)


def Nm(b):
    s = nm(b)
    return s[0].upper() + s[1:]


def when(unit, k):
    name, per, digits = UNITS[unit]
    v = k * per
    text = ("%.*f" % (digits, v)).rstrip("0").rstrip(".") if digits else "%d" % round(v)
    return "%s %s" % (name, text)


def duration(seconds):
    if seconds < 7200:
        return "%.0f minutes" % (seconds / 60.0)
    if seconds < 2 * 86400:
        return "%.1f hours" % (seconds / 3600.0)
    return "%.1f days" % (seconds / 86400.0)


def sense_word(sense):
    return "anticlockwise" if sense > 0 else "clockwise"


def _sanitise(plan_, m):
    return planlib.clean_plan(plan_, m["steps"], tuple(c for c in m["scene"]["children"]))


# ---- the flight and what it says ----------------------------------------------------------------------------------------------------------
def _pass_lines(m, sc, p):
    """Plain sentences about one pass of a body's sphere of influence."""
    unit = m["scene"]["unit"]
    b = sc["by_id"][p["child"]]
    name = nm(p["child"])
    lines = []
    alt = p["rp"] - b["radius"]
    lines.append("%s comes inside %s's sphere of influence on %s." % (PROBE, name, when(unit, p["k_in"])))
    if p.get("impact"):
        if "vp" in p and p["rp"] > 0:
            lines.append("It would reach %s from the centre at its closest, which is below the surface (radius %s): %s hits %s." % (
                km(p["rp"]), km(b["radius"]), PROBE, name))
        else:
            lines.append("%s would hit %s." % (PROBE, name))
        return lines
    vesc = math.sqrt(2.0 * b["gm"] / p["rp"])
    lines.append("Closest approach: %s from the centre of %s (%s above the surface), moving %s. The speed that just escapes from there is %s." % (
        km(p["rp"]), name, km(alt), speed(p["vp"]), speed(vesc)))
    if p.get("fuel"):
        lines.append("Closest-approach burn %+.3f km/s: the speed there becomes %s." % (p["vp_after"] - p["vp"], speed(p["vp_after"])))
    if p.get("captured"):
        lines.append("%s is captured: an orbit round %s, lowest point %s, highest point %s, one lap every %s, %s on the chart." % (
            PROBE, name, km(p["q"]), km(p["big_q"]), duration(p["period"]), sense_word(p["sense"])))
        if p.get("impact"):
            lines.append("But the lowest point is below the surface, so that orbit hits %s." % name)
    elif "exit" in p:
        lines.append("%s flies on past %s, turned by %.0f degrees, leaving at %s relative to it." % (PROBE, name, p.get("turn_deg", 0.0), speed(p.get("v_inf_after", 0.0))))
    return lines


def _goal_report(m, sc, goal, res, outcome):
    """(verdict, extra lines): what the flight did against the goal, in words, and what is still missing."""
    kind = goal["kind"]
    body = goal.get("body")
    unit = m["scene"]["unit"]
    passes = [p for p in res["passes"] if p["child"] == body]
    lines = []
    if outcome == "crash":
        crash = [e for e in res["events"] if e["kind"] == "crash"]
        who = nm(crash[-1]["body"]) if crash else "a body"
        sp = crash[-1].get("speed", 0.0) if crash else 0.0
        return "%s hit %s at %s. The path went below the surface." % (PROBE, who, speed(sp)), lines
    if outcome in ("success", "over_budget"):
        if kind == "flyby":
            p = passes[0] if passes else res["passes"][-1]
            what = "%s passes %s at %s from its centre" % (PROBE, nm(body), km(p["rp"]))
        elif kind == "capture":
            p = [q for q in passes if q.get("captured")][-1]
            what = "%s is in orbit round %s, %s to %s" % (PROBE, nm(body), km(p["q"]), km(p["big_q"]))
        elif kind == "rendezvous":
            e = [e for e in res["events"] if e["kind"] == "rendezvous"][-1]
            what = "%s meets %s: %s away, %s apart in speed" % (PROBE, nm(body), km(e["dist"]), speed(e["speed"]))
        else:
            e = [e for e in res["events"] if e["kind"] == "reach"][-1]
            what = "%s reaches %s from %s on %s" % (PROBE, _radius_words(goal, e["dist"]), "the centre" if sc["central"]["id"] != "sun" else "the Sun", when(unit, e["k"]))
        if outcome == "success":
            return "%s. That meets the goal." % what, lines
        over = res["fuel"] - m["budget"]
        return "%s, but the plan spends %s and the budget is %s. Take %s off." % (what, speed(res["fuel"]), speed(m["budget"]), speed(over)), lines
    # a miss: say how far off
    if kind in ("flyby", "capture"):
        if passes:
            p = passes[-1]
            reasons = []
            if kind == "flyby":
                if p["rp"] > goal["within"]:
                    reasons.append("the goal asks for %s or less" % km(goal["within"]))
                if p["rp"] < goal.get("min", 0.0):
                    reasons.append("the goal asks for at least %s" % km(goal["min"]))
            else:
                if not p.get("captured"):
                    reasons.append("%s is not slowed enough to be captured" % PROBE)
                else:
                    if not goal["q"][0] <= p["q"] <= goal["q"][1]:
                        reasons.append("the lowest point must be %s to %s" % (km(goal["q"][0]), km(goal["q"][1])))
                    if p["big_q"] > goal["big_q"]:
                        reasons.append("the highest point must be %s or less" % km(goal["big_q"]))
                    if goal.get("sense") == "retro" and p["sense"] != -1:
                        reasons.append("the orbit must go clockwise")
                    if goal.get("sense") == "pro" and p["sense"] != 1:
                        reasons.append("the orbit must go anticlockwise")
            if p["k_in"] > goal.get("by", 10 ** 9):
                reasons.append("it arrives on %s and the goal asks for %s or sooner" % (when(unit, p["k_in"]), when(unit, goal["by"])))
            if kind == "flyby":
                head = "%s passes %s at %s from its centre" % (PROBE, nm(body), km(p["rp"]))
            elif p.get("captured"):
                head = "%s is in orbit round %s, %s to %s" % (PROBE, nm(body), km(p["q"]), km(p["big_q"]))
            else:
                head = "%s passes %s at %s from its centre" % (PROBE, nm(body), km(p["rp"]))
            if goal.get("after") and not res["pass_count"].get(goal["after"]):
                reasons.append("%s must pass %s first" % (PROBE, nm(goal["after"])))
            return "%s: %s." % (head, "; ".join(reasons) if reasons else "not quite the goal"), lines
        c = res["closest"].get(body)
        if c:
            soi = sc["by_id"][body]["soi"]
            return "%s comes no closer than %s to %s. Its sphere of influence, where its pull takes over, reaches %s from its centre." % (
                PROBE, km(c["dist"]), nm(body), km(soi)), lines
        return "%s never gets near %s." % (PROBE, nm(body)), lines
    if kind == "rendezvous":
        c = res["closest"].get(body)
        if c:
            return "%s passes %s at %s, %s faster than it. The goal asks for %s or closer at %s or slower." % (
                PROBE, nm(body), km(c["dist"]), speed(c["speed"]), km(goal["radius"]), speed(goal["speed"])), lines
        return "%s never gets near %s." % (PROBE, nm(body)), lines
    # reach
    if goal.get("dir") == "out":
        far = res["r_max_post"] if goal.get("after") else res["r_max"]
        return "%s gets as far as %s. The goal asks for %s or more." % (PROBE, _radius_text(sc, far), _radius_text(sc, goal["radius"])), lines
    near = res["r_min_post"] if goal.get("after") else res["r_min"]
    if goal.get("after") and not res["pass_count"].get(goal["after"]):
        return "%s has not passed %s, so nothing counts yet. Its nearest to %s so far is %s; the goal asks for %s." % (
            PROBE, nm(goal["after"]), "the centre" if sc["central"]["id"] != "sun" else "the Sun", _radius_text(sc, res["r_min"]), _radius_text(sc, goal["radius"])), lines
    return "%s gets as near as %s to %s after the pass. The goal asks for %s or less." % (
        PROBE, _radius_text(sc, near if near is not None else res["r_min"]), "the centre" if sc["central"]["id"] != "sun" else "the Sun", _radius_text(sc, goal["radius"])), lines


def _radius_text(sc, r):
    if sc["central"]["id"] == "sun":
        return "%.2f AU" % (r / D.AU_KM)
    return km(r)


def _radius_words(goal, r):
    if r > 5e7:
        return "%.2f AU" % (r / D.AU_KM)
    return km(r)


def _flight(m, plan_):
    """Fly the plan in the real engine and return the dict of everything the page draws and says. Cached by mission and plan."""
    key = (m["id"], json.dumps(plan_, sort_keys=True))
    cached = _flight_cache.get(key)
    if cached is not None:
        return cached
    sc = orbit.make_scene(m["scene"])
    goal = m["goal"]
    res = orbit.fly(sc, plan_, goal, record=True)
    outcome = orbit.judge(res, m["budget"])
    unit = m["scene"]["unit"]
    name, per, digits = UNITS[unit]
    dt = sc["dt"]
    target = sc["by_id"].get(goal.get("body")) if goal.get("body") else None
    samples = res["samples"]
    xs = [int(round(s[1])) for s in samples]
    ys = [int(round(s[2])) for s in samples]
    ks = [s[0] for s in samples]
    td = []
    for s in samples:
        if target is None:
            td.append(None)
        else:
            k = max(0, min(sc["steps"] + 1, s[0]))
            td.append(int(round(math.hypot(s[1] - target["cx"][k], s[2] - target["cy"][k]))))
    bodies_out = []
    for c in sc["children"]:
        bx = []
        by = []
        for s in samples:
            k = max(0, min(sc["steps"] + 1, s[0]))
            bx.append(int(round(c["cx"][k])))
            by.append(int(round(c["cy"][k])))
        bodies_out.append({"id": c["id"], "label": bodies.label_plain(c["id"]), "a": int(round(c["a"])), "radius": c["radius"], "soi": None if c["soi"] is None else int(round(c["soi"])),
                           "x": bx, "y": by, "target": c is target})
    pass_text = []
    for p in res["passes"]:
        pass_text.extend(_pass_lines(m, sc, p))
    verdict, extra = _goal_report(m, sc, goal, res, outcome)
    burn_text = []
    for i, b in enumerate(plan_["burns"]):
        done = [d for d in res["burns_done"] if d["i"] == i]
        if done:
            d = done[0]
            where = {"time": "", "peri": " (at the nearest point of its path)", "apo": " (at the farthest point of its path)"}[b.get("at", "time")]
            burn_text.append("Burn %d on %s%s: %.3f km/s, %s." % (i + 1, when(unit, d["k"]), where, b["dv"], _heading_words(b["head"])))
        else:
            burn_text.append("Burn %d never happens: the flight ends first, or the nearest/farthest point it waits for does not come." % (i + 1))
    arcs = []
    for p in res["passes"]:
        if p.get("arc"):
            b = sc["by_id"][p["child"]]
            arcs.append({"body": p["child"], "label": bodies.label_plain(p["child"]), "radius": b["radius"], "soi": int(round(b["soi"])), "pts": p["arc"], "k": p["k_in"],
                         "captured": bool(p.get("captured")), "impact": bool(p.get("impact"))})
    out = {
        "outcome": outcome, "verdict": verdict, "fuel": round(res["fuel"], 3), "k_end": res["k_end"], "t_end": res["k_end"] * per,
        "ended": res["ended"], "details": pass_text + extra, "burn_text": burn_text, "unused": res["unused_burns"],
        "path": {"k": ks, "t": [round(k * per, 3) for k in ks], "x": xs, "y": ys, "speed": [round(s[3], 3) for s in samples],
                 "frame": [s[4] for s in samples], "target_dist": td},
        "bodies": bodies_out, "arcs": arcs,
        "burns": [{"i": d["i"], "k": d["k"], "t": round(d["k"] * per, 3), "x": int(round(d["x"])), "y": int(round(d["y"])), "dv": d["dv"], "head": d["head"]} for d in res["burns_done"]],
        "passes": [{"body": p["child"], "k": p["k_in"], "rp": None if "rp" not in p else round(p["rp"], 1), "impact": bool(p.get("impact")), "captured": bool(p.get("captured"))} for p in res["passes"]],
        "central": {"id": sc["central"]["id"], "label": bodies.label_plain(sc["central"]["id"]), "radius": sc["central"]["radius"]},
        "extent": m["scene"]["view"], "unit": {"id": unit, "name": name, "per_step": per, "digits": digits},
        "words": _words(m, sc, res),
    }
    if len(_flight_cache) > 60:
        _flight_cache.clear()
    _flight_cache[key] = out
    return out


def _heading_words(head):
    h = ((head + 180.0) % 360.0) - 180.0
    if abs(h) < 0.05:
        return "straight ahead"
    if abs(abs(h) - 180.0) < 0.05:
        return "straight back"
    if abs(h - 90.0) < 0.05:
        return "to the left"
    if abs(h + 90.0) < 0.05:
        return "to the right"
    return "%.1f degrees %s of straight ahead" % (abs(h), "left" if h > 0 else "right")


def _bearing(x, y):
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def _words(m, sc, res):
    """The chart as text: where everything is at the start and at the end, in degrees anticlockwise from the right-hand edge of the chart."""
    lines = []
    cen = sc["central"]
    unit = m["scene"]["unit"]
    sx, sy, _, _ = sc["start"]
    lines.append("The chart is centred on %s. Angles are in degrees anticlockwise from the right-hand edge." % nm(cen["id"]))
    for tag, k in (("At the start", 0), ("At the end of the flight", res["k_end"])):
        bits = []
        for c in sc["children"]:
            kk = max(0, min(sc["steps"] + 1, k))
            bits.append("%s at %.0f degrees, %s out" % (bodies.label_plain(c["id"]), _bearing(c["cx"][kk], c["cy"][kk]), _dist_words(sc, math.hypot(c["cx"][kk], c["cy"][kk]))))
        if k == 0:
            px, py = sx, sy
        else:
            px, py = res["final"][0], res["final"][1]
        bits.append("%s at %.0f degrees, %s out" % (PROBE, _bearing(px, py), _dist_words(sc, math.hypot(px, py))))
        lines.append("%s (%s): %s." % (tag, when(unit, k), "; ".join(bits)))
    return lines


def _dist_words(sc, r):
    if sc["central"]["id"] == "sun":
        return "%.2f AU" % (r / D.AU_KM)
    return km(r)


# ---- the game ---------------------------------------------------------------------------------------------------------------------------------
class Game:
    def __init__(self):
        self.reached = {}            # mission id -> {"fuel": best fuel used, "flights": flights spent on it}
        self.work = {}               # mission id -> plan (an unfinished mission's plan, or the plan being tried again)
        self.tally = {key: 0 for key in TALLY_KEYS}
        self.current = missions.ORDER[0]
        self.undo = []               # [(mission id, plan snapshot)] this session only
        self.redo = []
        self.message = ""
        self.say = ""
        self.just = None             # the mission recorded by the last action (not saved)
        self.added = None            # the index of the burn the last action added (not saved)

    # ---- the plan
    @property
    def m(self):
        return missions.BY_ID[self.current]

    def plan(self, mid=None):
        mid = mid or self.current
        stored = self.work.get(mid)
        if stored is None:
            stored = planlib.empty()
        return stored

    def _store(self, plan_):
        self.work[self.current] = plan_
        if planlib.is_empty(plan_):
            self.work.pop(self.current, None)

    def _snapshot(self):
        self.undo.append((self.current, json.dumps(self.plan(), sort_keys=True)))
        del self.undo[:-MAX_UNDO]
        self.redo = []

    def _changed(self):
        self.tally["edits"] += 1
        self.just = None

    def _enter(self, mid):
        self.current = mid
        self.just = None
        self.undo = []
        self.redo = []

    # ---- save
    def to_dict(self):
        """Only what differs from a fresh game is written (plus the layout version), so old and new saves stay compatible."""
        data = {"schema": SCHEMA}
        if self.current != missions.ORDER[0]:
            data["cur"] = self.current
        if self.reached:
            data["reached"] = {mid: {"fuel": self.reached[mid]["fuel"], "flights": self.reached[mid]["flights"]} for mid in missions.ORDER if mid in self.reached}
        work = {mid: self.work[mid] for mid in missions.ORDER if mid in self.work and not planlib.is_empty(self.work[mid])}
        if work:
            data["work"] = work
        tally = {k: v for k, v in self.tally.items() if v}
        if tally:
            data["tally"] = tally
        return data

    def load(self, data):
        """Take a saved dict, checking every field on its own; a bad field falls back to its default. A mission only counts as reached if its chapter
        was open by the missions reached before it."""
        data = data if isinstance(data, dict) else {}
        schema = data.get("schema", SCHEMA)
        if isinstance(schema, bool) or not isinstance(schema, int) or not 1 <= schema <= SCHEMA:
            data = {}                                              # an unknown layout is never half-read
        self.reached, self.work = {}, {}
        raw = data.get("reached") if isinstance(data.get("reached"), dict) else {}
        for m in missions.ALL:                                     # chapter order, so each chapter is judged on those before it
            entry = raw.get(m["id"])
            if not isinstance(entry, dict) or not missions.mission_open(self.reached, m["id"]):
                continue
            fuel = _float(entry.get("fuel"), 0.001, 100.0)
            if fuel is None:
                continue
            self.reached[m["id"]] = {"fuel": round(fuel, 3), "flights": _int(entry.get("flights"), 1, MAX_COUNT, 1)}
        raw_work = data.get("work") if isinstance(data.get("work"), dict) else {}
        for m in missions.ALL:
            if m["id"] in raw_work and missions.mission_open(self.reached, m["id"]):
                plan_ = _sanitise(raw_work[m["id"]], m)
                if not planlib.is_empty(plan_):
                    self.work[m["id"]] = plan_
        tally = data.get("tally") if isinstance(data.get("tally"), dict) else {}
        self.tally = {key: _int(tally.get(key)) for key in TALLY_KEYS}
        cur = data.get("cur")
        self._enter(cur if isinstance(cur, str) and cur in missions.BY_ID and missions.mission_open(self.reached, cur) else missions.ORDER[0])
        self.message = self.say = ""

    # ---- the view
    def _chapters(self):
        out = []
        for i, ch in enumerate(missions.CHAPTERS):
            open_ = missions.chapter_open(self.reached, i)
            items = []
            for m in ch["missions"]:
                done = self.reached.get(m["id"])
                item = {"id": m["id"], "number": m["number"], "name": m["name"], "dest": atlas.label(m["dest"]), "current": m["id"] == self.current,
                        "done": bool(done), "budget": m["budget"]}
                if done:
                    item["fuel"] = done["fuel"]
                    item["saved"] = round(max(0.0, m["budget"] - done["fuel"]), 3)
                items.append(item)
            need = 0 if i == 0 else missions.chapter_need(i)
            prev_done = missions.chapter_done(self.reached, i - 1) if i else 0
            out.append({"id": ch["id"], "name": ch["name"], "blurb": ch["blurb"], "open": open_, "done": missions.chapter_done(self.reached, i), "total": len(ch["missions"]),
                        "need": max(0, need - prev_done), "need_total": need, "after": missions.CHAPTERS[i - 1]["name"] if i else "", "missions": items})
        return out

    def _atlas(self):
        """The schematic chart: one column per destination, one mark per mission that goes there."""
        cols = []
        for x_i, dest in enumerate(atlas.order()):
            marks = []
            for m in missions.ALL:
                if m["dest"] != dest:
                    continue
                done = self.reached.get(m["id"])
                open_ = missions.mission_open(self.reached, m["id"])
                mark = {"id": m["id"], "chapter": m["chapter"], "number": m["number"], "name": m["name"], "done": bool(done), "open": open_, "current": m["id"] == self.current}
                if done:
                    mark["fuel"] = done["fuel"]
                    mark["saved_pct"] = int(round(100.0 * max(0.0, m["budget"] - done["fuel"]) / m["budget"]))
                marks.append(mark)
            if not marks:
                continue
            kind = atlas.DESTS[dest][1]
            size = None
            if dest in D.MOONS:
                size = D.MOONS[dest][2]
            elif dest in D.PLANETS:
                size = D.PLANETS[dest][1]
            cols.append({"id": dest, "label": atlas.label(dest), "kind": kind, "radius": size, "done": sum(1 for k in marks if k["done"]), "total": len(marks), "marks": marks})
        return {"columns": cols}

    def _cards(self):
        out = []
        seen = set()
        for mid in missions.ORDER:
            if mid in self.reached:
                dest = missions.BY_ID[mid]["dest"]
                if dest in seen:
                    continue
                seen.add(dest)
                lines, source = atlas.card(dest)
                out.append({"id": dest, "label": atlas.label(dest), "lines": [{"title": t, "text": x} for t, x in lines], "source": source,
                            "best": min(self.reached[k]["fuel"] for k in self.reached if missions.BY_ID[k]["dest"] == dest),
                            "missions": sum(1 for k in self.reached if missions.BY_ID[k]["dest"] == dest)})
        return out

    def _totals(self):
        saved = sum(max(0.0, missions.BY_ID[k]["budget"] - v["fuel"]) for k, v in self.reached.items())
        return {"missions": len(missions.ORDER), "done": len(self.reached), "saved": round(saved, 2), "flights": self.tally["flights"], "edits": self.tally["edits"],
                "scrubs": self.tally["scrubs"], "chapters_open": sum(1 for i in range(len(missions.CHAPTERS)) if missions.chapter_open(self.reached, i)),
                "chapters": len(missions.CHAPTERS), "destinations": len({missions.BY_ID[k]["dest"] for k in self.reached})}

    def view(self, message=None, ok=True, say=None):
        if message is not None:
            self.message = message
        self.say = say if say is not None else (self.message if message else "")
        m = self.m
        plan_ = self.plan()
        flight = _flight(m, plan_)
        unit = flight["unit"]
        name, per, digits = UNITS[m["scene"]["unit"]]
        done = self.reached.get(m["id"])
        burns = []
        for i, b in enumerate(plan_["burns"]):
            burns.append({"i": i, "t": b["t"], "t_value": round(b["t"] * per, 3), "at": b["at"], "head": b["head"], "dv": b["dv"], "words": _heading_words(b["head"])})
        children = [c for c in m["scene"]["children"] if not c in m["scene"].get("rendezvous", ())]
        sc = orbit.make_scene(m["scene"])
        goal = m["goal"]
        pass_slots = [{"body": c, "label": bodies.label_plain(c), "dv": plan_["pass"].get(c, 0.0), "primary": c in (goal.get("body"), goal.get("after")) or bool(plan_["pass"].get(c))}
                      for c in children]
        view = {
            "ok": ok, "message": self.message, "say": self.say,
            "mission": {"id": m["id"], "chapter": m["chapter"], "number": m["number"], "of": len(missions.CHAPTERS[m["chapter"] - 1]["missions"]), "chapter_name": missions.CHAPTERS[m["chapter"] - 1]["name"],
                        "name": m["name"], "dest": atlas.label(m["dest"]), "brief": m["brief"], "goal_text": m["goal_text"], "note": m["note"], "budget": m["budget"], "cost": m["cost"],
                        "done": bool(done), "best": done["fuel"] if done else None, "steps": m["steps"], "step_value": per, "unit": name, "unit_id": m["scene"]["unit"], "digits": digits,
                        "probe": PROBE, "central": bodies.label_plain(sc["central"]["id"]),
                        "goal": {"kind": goal["kind"], "body": goal.get("body"), "radius": goal.get("radius"), "dir": goal.get("dir")}},
            "plan": {"burns": burns, "pass": pass_slots, "fuel": planlib.fuel_of(plan_), "max_burns": planlib.MAX_BURNS},
            "flight": flight,
            "added": self.added, "editable": True, "can_undo": bool(self.undo), "can_redo": bool(self.redo), "can_clear": not planlib.is_empty(plan_), "just": self.just,
            "chapters": self._chapters(), "atlas": self._atlas(), "cards": self._cards(), "tally": dict(self.tally), "totals": self._totals(),
            "info": info.view(),
        }
        return view

    # ---- editing the plan
    def _edit_plan(self, fn, say):
        before = json.dumps(self.plan(), sort_keys=True)
        plan_ = json.loads(before)
        result = fn(plan_)
        if result is not None:
            return self.view(result, ok=False)
        plan_ = _sanitise(plan_, self.m)
        if json.dumps(plan_, sort_keys=True) == before:
            return self.view("")
        self.undo.append((self.current, before))
        del self.undo[:-MAX_UNDO]
        self.redo = []
        self._store(plan_)
        self._changed()
        return self.view(say, say=say)

    def burn_add(self, req):
        def fn(plan_):
            if len(plan_["burns"]) >= planlib.MAX_BURNS:
                return "A plan holds at most %d burns." % planlib.MAX_BURNS
            b = planlib.clean_burn({"t": req.get("t", 0), "at": req.get("at", "time"), "head": req.get("head", 0.0), "dv": req.get("dv", 0.0)}, self.m["steps"])
            if b is None:
                return "That is not a burn I can set."
            plan_["burns"].append(b)
            plan_["burns"].sort(key=lambda x: x["t"])
            self.added = max(i for i, x in enumerate(plan_["burns"]) if x == b)
        self.added = None
        return self._edit_plan(fn, "Burn added.")

    def burn_set(self, req):
        def fn(plan_):
            i = req.get("i")
            if isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < len(plan_["burns"]):
                return "There is no such burn."
            b = dict(plan_["burns"][i])
            for key in ("t", "at", "head", "dv"):
                if key in req:
                    b[key] = req[key]
            b = planlib.clean_burn(b, self.m["steps"])
            if b is None:
                return "That is not a burn I can set."
            plan_["burns"][i] = b
            plan_["burns"].sort(key=lambda x: x["t"])
        return self._edit_plan(fn, "")

    def burn_del(self, req):
        def fn(plan_):
            i = req.get("i")
            if isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < len(plan_["burns"]):
                return "There is no such burn."
            del plan_["burns"][i]
        return self._edit_plan(fn, "Burn removed.")

    def pass_set(self, req):
        body = req.get("body")

        def fn(plan_):
            if body not in self.m["scene"]["children"] or body in self.m["scene"].get("rendezvous", ()):
                return "There is no closest-approach burn there."
            dv = _float(req.get("dv"), -planlib.DV_MAX, planlib.DV_MAX)
            if dv is None:
                return "That is not a strength."
            if round(dv, 3) == 0.0:
                plan_["pass"].pop(body, None)
            else:
                plan_["pass"][body] = round(dv, 3)
        return self._edit_plan(fn, "")

    def plan_clear(self):
        def fn(plan_):
            plan_["burns"] = []
            plan_["pass"] = {}
        return self._edit_plan(fn, "Plan cleared.")

    def step(self, forward):
        stack, other = (self.redo, self.undo) if forward else (self.undo, self.redo)
        if not stack:
            return self.view("Nothing to " + ("redo." if forward else "undo."), ok=False)
        mid, snap = stack.pop()
        if mid != self.current:
            stack.clear()
            return self.view("", ok=False)
        other.append((mid, json.dumps(self.plan(), sort_keys=True)))
        self._store(json.loads(snap))
        self.just = None
        return self.view("Redone." if forward else "Undone.")

    # ---- flying
    def fly(self):
        m = self.m
        plan_ = self.plan()
        if planlib.is_empty(plan_):
            return self.view("Add a burn first: with none, Wren just keeps going round.", ok=False)
        flight = _flight(m, plan_)
        self.tally["flights"] += 1
        self.just = None
        if flight["outcome"] == "success":
            prev = self.reached.get(m["id"])
            first = prev is None
            fuel = flight["fuel"]
            if prev is None:
                self.reached[m["id"]] = {"fuel": fuel, "flights": 1}
            else:
                prev["flights"] += 1
                if fuel < prev["fuel"]:
                    prev["fuel"] = fuel
            saved = max(0.0, m["budget"] - fuel)
            self.just = {"id": m["id"], "first": first, "fuel": fuel, "saved": round(saved, 3), "saved_pct": int(round(100.0 * saved / m["budget"]))}
            word = "Mission done." if first else "Reached again."
            return self.view("%s Fuel used %s of %s." % (word, speed(fuel), speed(m["budget"])))
        if m["id"] in self.reached:
            self.reached[m["id"]]["flights"] += 1
        return self.view(flight["verdict"], ok=False, say="Flight flown. " + flight["verdict"])

    def scrub(self, n):
        self.tally["scrubs"] += _int(n, 1, 50, 1)
        return self.view("")

    # ---- navigation
    def pick(self, mid):
        if not isinstance(mid, str) or mid not in missions.BY_ID:
            return self.view("There is no such mission.", ok=False)
        if not missions.mission_open(self.reached, mid):
            i = missions.BY_ID[mid]["chapter"] - 1
            return self.view("That chapter opens when %d missions in %s are done." % (missions.chapter_need(i), missions.CHAPTERS[i - 1]["name"]), ok=False)
        if mid != self.current:
            self._enter(mid)
        return self.view("")

    def next(self):
        order = missions.ORDER
        start = order.index(self.current)
        for step in range(1, len(order) + 1):
            mid = order[(start + step) % len(order)]
            if mid not in self.reached and missions.mission_open(self.reached, mid):
                self._enter(mid)
                return self.view("")
        return self.view("Every open mission is done." if len(self.reached) < len(order) else "Every mission is done.", ok=False)


game = Game()


def handle(request_json):
    try:
        request = json.loads(request_json)
        action = request.get("action")
    except (ValueError, AttributeError):
        return json.dumps({"error": "bad request"})
    g = game
    try:
        if action == "open":
            return json.dumps(g.view())
        if action == "reset":
            g.__init__()
            return json.dumps(g.view("Starting over."))
        if action == "pick":
            return json.dumps(g.pick(request.get("mission")))
        if action == "next":
            return json.dumps(g.next())
        if action == "burn_add":
            return json.dumps(g.burn_add(request))
        if action == "burn_set":
            return json.dumps(g.burn_set(request))
        if action == "burn_del":
            return json.dumps(g.burn_del(request))
        if action == "pass_set":
            return json.dumps(g.pass_set(request))
        if action == "plan_clear":
            return json.dumps(g.plan_clear())
        if action == "undo":
            return json.dumps(g.step(False))
        if action == "redo":
            return json.dumps(g.step(True))
        if action == "fly":
            return json.dumps(g.fly())
        if action == "scrub":
            return json.dumps(g.scrub(request.get("n", 1)))
    except (TypeError, ValueError, KeyError, AttributeError):
        return json.dumps({"error": "bad request"})
    return json.dumps({"error": "unknown action " + repr(action)})


def get_state():
    return game.to_dict()


def load_state(data):
    game.load(data)
    _refresh_view()


def _refresh_view():
    """Ask the page to redraw after a save is loaded (the save widget calls load_state directly and knows nothing about this game's view).
    Under plain CPython there is no page, so this is a no-op."""
    try:
        import js
        refresh = getattr(js.window, "slingshotRefresh", None)
        if refresh is not None:
            refresh()
    except Exception:
        pass
