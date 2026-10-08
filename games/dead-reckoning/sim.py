"""Dead Reckoning -- the simulation core. Pure Python, no DOM, deterministic.

`sail(chart, legs, seed)` is a pure function of its inputs: the same chart, plan and seed always give the
same true track (positions are rounded to 0.01 nm every step, so results are stable across platforms).

A chart is a plain dict (see charts.py and CLAUDE.md for the full schema). The parts the sim reads:

    start, dest [x, y]      nautical miles; x grows east, y grows north
    arrival_radius          nm; the ship has arrived when it ends within this distance of dest
    deadline                hours
    speeds [lo, hi]         the ship's speed range in knots (steps of 0.5)
    start_hour              the clock time the passage starts (tidal streams are tied to this clock)
    land   [{id, name, poly}]
    hazards [{id, kind, name, x, y, r, charted}]       kind: reef | shoal | rock; charted False = unmarked
    currents [{id, rect, set, drift_range, true_set, true_drift, tide?}]
    wind {from, range, true}       knots; leeway is LEEWAY_FACTOR of the wind's beam component
    compass {range, true}          degrees to ADD to the heading steered to get the true heading
    landmarks [{id, name, kind, x, y, visible}]
    fog                            True hides hazards until found and blocks landmark fixes

Three models of the sea, because the player never knows the truth:
    "true"     what really happens (true set/drift/wind/compass error, plus seeded gusts)
    "charted"  the midpoint of every range the chart prints (the best honest forecast)
    "nominal"  heading, speed and time only (dead reckoning proper, as the log and compass say)
"""

import math

from geom import (bearing, dist, in_rect, lerp, rnd, seg_circle_hit, seg_point_dist, seg_polygon_dist,
                  seg_polygon_hit, unit)

DT = 0.25                  # hours per simulation step
LEG_STEP = 0.5             # legs are whole multiples of half an hour
SPEED_STEP = 0.5
MAX_LEG_HOURS = 12.0
GRAZE_MARGIN = 0.4         # nm: passing closer than this to a hazard's edge is a "close pass"
LEEWAY_FACTOR = 0.05       # leeway speed = this share of the wind's component across the ship
MODELS = ("true", "charted", "nominal")


# --- plans ---------------------------------------------------------------------------------------
def mid(pair):
    return (pair[0] + pair[1]) / 2.0


def _num(v, default):
    """A finite float, or the default (booleans and NaN are not numbers here)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return default
    return float(v)


def cruise_speed(chart):
    lo, hi = chart["speeds"]
    return round(mid((lo, hi)) / SPEED_STEP) * SPEED_STEP


def clean_leg(chart, leg):
    """A leg forced into the legal grid (heading whole degrees, speed in 0.5 kn steps inside the ship's range,
    hours in 0.5 h steps up to MAX_LEG_HOURS). Returns None for something that is not a leg at all."""
    if not isinstance(leg, dict):
        return None
    lo, hi = chart["speeds"]
    heading = int(round(_num(leg.get("heading"), 0.0))) % 360
    speed = round(min(hi, max(lo, _num(leg.get("speed"), cruise_speed(chart)))) / SPEED_STEP) * SPEED_STEP
    hours = round(min(MAX_LEG_HOURS, max(LEG_STEP, _num(leg.get("hours"), LEG_STEP))) / LEG_STEP) * LEG_STEP
    return {"heading": heading, "speed": speed, "hours": hours}


def clean_legs(chart, legs, limit=30):
    out = []
    for leg in list(legs or [])[:limit]:
        cleaned = clean_leg(chart, leg)
        if cleaned is not None:
            out.append(cleaned)
    return out


def plan_hours(legs):
    return sum(leg["hours"] for leg in legs)


def plan_distance(legs):
    return sum(leg["speed"] * leg["hours"] for leg in legs)


# --- the sea -------------------------------------------------------------------------------------
def compass_error(chart, model):
    c = chart.get("compass")
    if not c or model == "nominal":
        return 0.0
    return c["true"] if model == "true" else mid(c["range"])


def current_at(chart, pt, t_abs, model):
    """The total current vector (nm per hour) at a point and clock time."""
    if model == "nominal":
        return (0.0, 0.0)
    vx = vy = 0.0
    for zone in chart.get("currents", ()):
        if not in_rect(pt, zone["rect"]):
            continue
        if model == "true":
            heading, drift = zone["true_set"], zone["true_drift"]
        else:
            heading, drift = zone["set"], mid(zone["drift_range"])
        tide = zone.get("tide")
        if tide:
            drift *= math.cos(2.0 * math.pi * (t_abs - tide["phase"]) / tide["period"])
        ux, uy = unit(heading)
        vx += ux * drift
        vy += uy * drift
    return (vx, vy)


def leeway_at(chart, heading, model):
    """The sideways push on a sailing ship: the wind's component across the ship, times LEEWAY_FACTOR."""
    wind = chart.get("wind")
    if not wind or model == "nominal":
        return (0.0, 0.0)
    knots = wind["true"] if model == "true" else mid(wind["range"])
    wx, wy = unit(wind["from"] + 180.0)            # the direction the wind blows toward
    hx, hy = unit(heading)
    rx, ry = hy, -hx                               # the ship's starboard side
    side = (wx * rx + wy * ry) * knots
    return (rx * side * LEEWAY_FACTOR, ry * side * LEEWAY_FACTOR)


def _mix(seed, k):
    """A small integer hash (splitmix-style) so gusts need no random module and match everywhere."""
    z = (seed * 0x9E3779B97F4A7C15 + (k + 1) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    return z ^ (z >> 31)


def unit_noise(seed, k):
    """A repeatable number in [-1, 1] for step k of a seed."""
    return (_mix(seed, k) % 20001) / 10000.0 - 1.0


def gust_at(chart, seed, k, model):
    amp = chart.get("gusts", 0.0)
    if not amp or model != "true":
        return (0.0, 0.0)
    return (amp * unit_noise(seed, 2 * k), amp * unit_noise(seed, 2 * k + 1))


def ship_velocity(chart, pt, t_abs, leg, model, seed=0, k=0):
    """The ship's velocity over the ground (nm per hour): through the water, plus leeway, current and gusts."""
    heading = leg["heading"] + compass_error(chart, model)
    ux, uy = unit(heading)
    lx, ly = leeway_at(chart, heading, model)
    cx, cy = current_at(chart, pt, t_abs, model)
    gx, gy = gust_at(chart, seed, k, model)
    return (ux * leg["speed"] + lx + cx + gx, uy * leg["speed"] + ly + cy + gy)


# --- sailing -------------------------------------------------------------------------------------
POINTS = ("north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west")


def compass_point(deg):
    return POINTS[int(((deg % 360.0) + 22.5) // 45.0) % 8]


def _fmt_hour(t):
    return ("%.2f" % t).rstrip("0").rstrip(".")


def _obstacles(chart):
    """Everything that stops a ship: land and hazards, as (id, name, kind, charted) with a hit test."""
    for land in chart.get("land", ()):
        yield land["id"], land["name"], "land", True, ("poly", land["poly"])
    for hz in chart.get("hazards", ()):
        yield hz["id"], hz["name"], hz["kind"], hz.get("charted", True), ("circle", (hz["x"], hz["y"]), hz["r"])


def _first_hit(chart, p0, p1):
    """(t, id, name, kind, charted) of the first thing the segment touches, or None."""
    best = None
    for oid, name, kind, charted, shape in _obstacles(chart):
        if shape[0] == "poly":
            t = seg_polygon_hit(p0, p1, shape[1])
        else:
            t = seg_circle_hit(p0, p1, shape[1], shape[2])
        if t is not None and (best is None or t < best[0]):
            best = (t, oid, name, kind, charted)
    return best


def _close_passes(chart, p0, p1):
    """Obstacles the segment passes within GRAZE_MARGIN of without touching."""
    found = []
    for oid, name, kind, charted, shape in _obstacles(chart):
        if shape[0] == "poly":
            gap = seg_polygon_dist(p0, p1, shape[1])
        else:
            gap = seg_point_dist(p0, p1, shape[1]) - shape[2]
        if 0.0 < gap <= GRAZE_MARGIN:
            found.append((oid, name, kind, charted))
    return found


def _side(heading_vec, p0, p1, centre_of):
    return "starboard" if (heading_vec[0] * (centre_of[1] - p0[1]) - heading_vec[1] * (centre_of[0] - p0[0])) < 0 else "port"


def _centre(chart, oid):
    for land in chart.get("land", ()):
        if land["id"] == oid:
            xs = [p[0] for p in land["poly"]]
            ys = [p[1] for p in land["poly"]]
            return (sum(xs) / len(xs), sum(ys) / len(ys))
    for hz in chart.get("hazards", ()):
        if hz["id"] == oid:
            return (hz["x"], hz["y"])
    return (0.0, 0.0)


def _zone_at(chart, pt):
    for zone in chart.get("currents", ()):
        if in_rect(pt, zone["rect"]):
            return zone
    return None


def sail(chart, legs, seed=0, model="true", start=None, t_start=0.0, collide=None, known=()):
    """Sail a plan. Returns a dict:

        track      [[t, x, y], ...]   one point per step, t in hours since the start of THIS call
        leg_ends   [[t, x, y], ...]   where each leg ended (the last is the grounding point if aground)
        events     [{t, kind, text, public}]   what the crew would notice (public ones are shown mid-passage)
        aground    None or {hazard, name, t}
        close      ids of hazards passed within GRAZE_MARGIN (each listed once)
        end        [x, y]; hours elapsed; legs_sailed
        tide_fair  share of tidal-stream time the stream ran with the ship, or None

    `collide` defaults to True for the true model and False otherwise. `known` is the set of hazard ids the
    crew already knows about (charted ones are always known), which only changes the wording of events."""
    legs = list(legs)
    if collide is None:
        collide = model == "true"
    pt = tuple(start) if start is not None else tuple(chart["start"])
    clock0 = chart.get("start_hour", 0.0) + t_start
    t = 0.0
    track = [[0.0, rnd(pt[0]), rnd(pt[1])]]
    leg_ends = []
    events = []
    close = []
    aground = None
    legs_sailed = 0
    k = 0
    zone_now = None
    fair_steps = tidal_steps = 0
    for leg in legs:
        steps = int(round(leg["hours"] / DT))
        for _ in range(steps):
            v = ship_velocity(chart, pt, clock0 + t, leg, model, seed, k)
            nxt = (pt[0] + v[0] * DT, pt[1] + v[1] * DT)
            if model == "true":
                zone = _zone_at(chart, pt)
                if zone is not zone_now:
                    zone_now = zone
                    if zone is not None:
                        heading, drift = zone["true_set"], zone["true_drift"]
                        events.append({"t": t, "kind": "stream", "public": False, "text":
                                       "Hour %s: a stream sets the ship toward the %s (about %g kn)."
                                       % (_fmt_hour(t), compass_point(heading), abs(drift))})
                    else:
                        events.append({"t": t, "kind": "stream", "public": False,
                                       "text": "Hour %s: the stream falls away." % _fmt_hour(t)})
                if zone is not None and zone.get("tide"):
                    tidal_steps += 1
                    c = current_at(chart, pt, clock0 + t, "true")
                    ux, uy = unit(leg["heading"] + compass_error(chart, "true"))
                    if c[0] * ux + c[1] * uy > 0:
                        fair_steps += 1
            if collide:
                hit = _first_hit(chart, pt, nxt)
                if hit is not None:
                    th, oid, name, kind, charted = hit
                    pt = lerp(pt, nxt, th)
                    t = t + th * DT
                    track.append([t, rnd(pt[0]), rnd(pt[1])])
                    aground = {"hazard": oid, "name": name, "t": t}
                    where = name if (charted or oid in known) else "an unmarked danger"
                    events.append({"t": t, "kind": "aground", "public": True, "text":
                                   "Hour %s: aground on %s. The tide will lift you in a few hours." % (_fmt_hour(t), where)})
                    leg_ends.append([t, rnd(pt[0]), rnd(pt[1])])
                    break
                heading_vec = (nxt[0] - pt[0], nxt[1] - pt[1])
                for oid, name, kind, charted in _close_passes(chart, pt, nxt):
                    if oid in close:
                        continue
                    close.append(oid)
                    if charted or oid in known:
                        text = "Hour %s: passed close to %s." % (_fmt_hour(t + DT), name)
                    else:
                        text = "Hour %s: something hissed past to %s." % (
                            _fmt_hour(t + DT), _side(heading_vec, pt, nxt, _centre(chart, oid)))
                    events.append({"t": t + DT, "kind": "close", "hazard": oid, "public": True, "text": text})
            pt = (round(nxt[0], 6), round(nxt[1], 6))
            t = t + DT
            k += 1
            track.append([t, rnd(pt[0]), rnd(pt[1])])
        if aground:
            break
        legs_sailed += 1
        leg_ends.append([t, rnd(pt[0]), rnd(pt[1])])
    events.sort(key=lambda e: e["t"])
    return {"track": track, "leg_ends": leg_ends, "events": events, "aground": aground, "close": close,
            "end": [rnd(pt[0]), rnd(pt[1])], "hours": t, "legs_sailed": legs_sailed,
            "tide_fair": (fair_steps / tidal_steps) if tidal_steps else None}


def estimate(chart, legs, allow=True, start=None, t_start=0.0, fixes=()):
    """The player's own plot: where they believe the ship is. With `allow` it includes the midpoint of every
    charted range (the honest forecast); without, only heading, speed and time. `fixes` is a list of
    {after_leg, x, y}: after that leg the believed position jumps to the fix. Returns the track as
    [[t, x, y, fixed], ...] where `fixed` marks a point set by a fix."""
    model = "charted" if allow else "nominal"
    pt = tuple(start) if start is not None else tuple(chart["start"])
    by_leg = {f["after_leg"]: f for f in fixes}
    clock0 = chart.get("start_hour", 0.0) + t_start
    t = 0.0
    out = [[0.0, rnd(pt[0]), rnd(pt[1]), False]]
    for index, leg in enumerate(legs):
        for _ in range(int(round(leg["hours"] / DT))):
            v = ship_velocity(chart, pt, clock0 + t, leg, model)
            pt = (round(pt[0] + v[0] * DT, 6), round(pt[1] + v[1] * DT, 6))
            t += DT
            out.append([t, rnd(pt[0]), rnd(pt[1]), False])
        fix = by_leg.get(index)
        if fix is not None:
            pt = (float(fix["x"]), float(fix["y"]))
            out.append([t, rnd(pt[0]), rnd(pt[1]), True])
    return out


# --- helpers a player (or the solver) can call ---------------------------------------------------
def naive_legs(chart, start=None, target=None, speed=None):
    """The naive "steer straight at it" plan: it ignores every current, the wind and any compass error."""
    a = tuple(start) if start is not None else tuple(chart["start"])
    b = tuple(target) if target is not None else tuple(chart["dest"])
    speed = speed if speed is not None else cruise_speed(chart)
    hours = max(LEG_STEP, round(dist(a, b) / speed / LEG_STEP) * LEG_STEP)
    return [clean_leg(chart, {"heading": round(bearing(a, b)), "speed": speed, "hours": hours})]


_NAIVE_CACHE = {}


def naive_miss(chart):
    """How far from the destination the naive plan really ends up on this chart (nm)."""
    key = chart["id"]
    if key not in _NAIVE_CACHE:
        res = sail(chart, naive_legs(chart), seed=chart.get("seed", 0))
        _NAIVE_CACHE[key] = round(dist(res["end"], chart["dest"]), 2)
    return _NAIVE_CACHE[key]


def drop_naive_cache():
    _NAIVE_CACHE.clear()


# --- scoring -------------------------------------------------------------------------------------
def score(chart, legs, result, known=(), used_helpers=False):
    """Judge a finished passage. Always returns the reasons as well as the stars (a bare number is never
    shown). Stars: 1 = made landfall; 2 = also on time and no close pass of a hazard the crew knew about;
    3 = also finished within half the arrival radius of the flag."""
    miss = round(dist(result["end"], chart["dest"]), 2)
    radius = chart["arrival_radius"]
    aground = result["aground"]
    arrived = aground is None and miss <= radius
    hours = plan_hours(legs) if aground is None else result["hours"]
    late = max(0.0, hours - chart["deadline"])
    on_time = aground is None and late <= 1e-9
    known_ids = set(known) | {h["id"] for h in chart.get("hazards", ()) if h.get("charted", True)} \
        | {land["id"] for land in chart.get("land", ())}
    close_known = [h for h in result["close"] if h in known_ids]
    clear = aground is None and not close_known
    precise = arrived and miss <= radius / 2.0
    stars = 0
    if arrived:
        stars = 1
        if on_time and clear:
            stars = 2
            if precise:
                stars = 3
    nm = naive_miss(chart)
    beat = None
    if nm >= 1.0:
        beat = max(0, min(100, int(round(100.0 * (1.0 - miss / nm)))))
    forecast = estimate(chart, legs, allow=True)
    fx, fy = forecast[-1][1], forecast[-1][2]
    forecast_error = round(dist(result["end"], (fx, fy)), 2) if aground is None else None
    criteria = [
        {"id": "landfall", "ok": arrived,
         "text": ("Landfall: you finished %.1f nm from the flag (arrival radius %g nm)." % (miss, radius)
                  if aground is None else "Landfall: the passage ended aground, %.1f nm from the flag." % miss)},
        {"id": "time", "ok": on_time,
         "text": ("On time: %g h sailed against a %g h deadline." % (hours, chart["deadline"]) if on_time else
                  "On time: not counted, the ship ran aground." if aground else
                  "On time: %g h against a %g h deadline, %g h late." % (hours, chart["deadline"], late))},
        {"id": "clear", "ok": clear,
         "text": ("Clear water: no close passes of known hazards." if clear else
                  "Clear water: aground." if aground else "Clear water: passed close to a known hazard.")},
        {"id": "precise", "ok": precise,
         "text": "Dead centre: within %g nm of the flag%s." % (radius / 2.0, "" if precise else " (you were %.1f nm off)" % miss)},
    ]
    return {"arrived": arrived, "miss_nm": miss, "aground": bool(aground), "hours": hours, "late_h": late,
            "on_time": on_time, "clear": clear, "precise": precise, "stars": stars, "criteria": criteria,
            "naive_miss_nm": nm, "beat_naive_pct": beat, "forecast_error_nm": forecast_error,
            "used_helpers": bool(used_helpers), "tide_fair": result["tide_fair"]}


def describe(chart, legs, result):
    """A plain-text account of a sail, for tools/textharness.py and the tests."""
    lines = ["%s: %d leg(s), %g h, %.1f nm through the water" % (chart["id"], len(legs), plan_hours(legs), plan_distance(legs))]
    for i, leg in enumerate(legs, 1):
        lines.append("  leg %d: steer %03d at %g kn for %g h" % (i, leg["heading"], leg["speed"], leg["hours"]))
    for t, x, y in result["track"][::4]:
        lines.append("  t=%5.2f  (%6.2f, %6.2f)" % (t, x, y))
    lines.append("  ended at (%.2f, %.2f), %.2f nm from the flag" % (result["end"][0], result["end"][1], dist(result["end"], chart["dest"])))
    for e in result["events"]:
        lines.append("  " + e["text"])
    return "\n".join(lines)
