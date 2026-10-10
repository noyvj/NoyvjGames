"""Dead Reckoning -- the practice generator's two-ship option (milestone 7). gen.make_chart(difficulty, seed, two=True) builds the usual
solved chart for Ship A (gen._build), then calls add_second_ship to give it a Ship B.

Ship B starts on one side of Ship A's line and its flag lies on the other, so the two routes cross somewhere near the middle. Its own route
is SOLVED exactly as Ship A's was (a visibility-graph route round the hazards, shot leg by leg under the true sea, lying at anchor first
when that is what a tide or the other ship asks for) and the pair is accepted only if the two par plans, sailed together, earn three
stars: both land cleanly and on time, and the ships never come inside fleet.SEPARATION of each other. A chart where no such plan was found
is thrown away (gen.make_chart then tries its next attempt), so every two-ship practice chart can be 3-starred."""

import math

import fleet
import gen
import sim
import solver
from geom import dist, point_in_polygon, seg_polygon_dist

MARGIN_NM = 0.2            # the par pair must stay this much further apart than the rule needs
MAX_WAIT = 6.0


def _endpoints(rng, chart):
    """Ship B's start and flag: across Ship A's line from each other, near the middle of the chart."""
    a, b = chart["start"], chart["dest"]
    size = float(chart["size"])
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    nx, ny = -uy, ux
    t1, t2 = rng.uniform(0.3, 0.55), rng.uniform(0.45, 0.7)
    off1, off2 = rng.uniform(0.28, 0.42) * size, rng.uniform(0.28, 0.42) * size
    flip = rng.pick([-1, 1])
    s = (a[0] + dx * t1 + nx * off1 * flip, a[1] + dy * t1 + ny * off1 * flip)
    d = (a[0] + dx * t2 - nx * off2 * flip, a[1] + dy * t2 - ny * off2 * flip)
    margin = size * 0.1
    s = (round(min(size - margin, max(margin, s[0])), 1), round(min(size - margin, max(margin, s[1])), 1))
    d = (round(min(size - margin, max(margin, d[0])), 1), round(min(size - margin, max(margin, d[1])), 1))
    return s, d


def _water_ok(chart, start, dest):
    """B's ends sit in clear water, away from Ship A's start and flag and from each other."""
    radius = chart["arrival_radius"]
    if dist(start, dest) < chart["size"] * 0.45:
        return False
    if min(dist(start, chart["start"]), dist(start, chart["dest"]), dist(dest, chart["start"])) < 3.0:
        return False
    if dist(dest, chart["dest"]) < 2 * radius + 2.0:
        return False
    for h in chart["hazards"]:
        c = (h["x"], h["y"])
        if dist(start, c) <= h["r"] + 1.5 or dist(dest, c) <= h["r"] + radius + 1.5:
            return False
    for land in chart["land"]:
        poly = [tuple(p) for p in land["poly"]]
        if point_in_polygon(start, poly) or point_in_polygon(dest, poly):
            return False
        if seg_polygon_dist(start, start, poly) <= 1.5 or seg_polygon_dist(dest, dest, poly) <= radius + 1.0:
            return False
    return True


def _candidates(ship, clearance):
    """Clean, three-star-precise plans for Ship B alone, earliest departure first: [(wait, legs)]."""
    path = gen.plan_route(ship, clearance)
    if path is None:
        return [], None
    seed = ship["seed"]
    tidal = any(z.get("tide") for z in ship["currents"])
    waits = [float(w) for w in range(0, 12)] if tidal else [k * 0.5 for k in range(0, int(MAX_WAIT * 2) + 1)]
    out = []
    for w in waits:
        legs, _ = solver.route(ship, path, speed=sim.cruise_speed(ship) if tidal else None, model="true", seed=seed, wait=w)
        res = sim.sail(ship, legs, seed=seed)
        if res["aground"] is None and not res["close"] and dist(res["end"], ship["dest"]) <= ship["arrival_radius"] / 2.0 and sim.plan_hours(legs) <= 11.5:
            out.append((w, legs))
    return out, path


def add_second_ship(chart, difficulty, seed, attempt):
    """A two-ship version of a solved one-ship practice chart, or None if Ship B could not be given a clean route that also keeps clear of Ship A."""
    rng = gen.Rng(seed * 64 + attempt + 7777)
    for _ in range(12):
        start, dest = _endpoints(rng, chart)
        if _water_ok(chart, start, dest):
            break
    else:
        return None
    ship2 = {"name": "Ship B", "start": list(start), "dest": list(dest), "speeds": list(chart["speeds"]), "arrival_radius": chart["arrival_radius"],
             "deadline": 10.0, "par_wait": 0.0, "waypoints": [list(start), list(dest)]}
    two = dict(chart)
    two["id"] = gen.chart_id(difficulty, seed, True)
    two["name"] = "Practice %s" % gen.code_of(difficulty, seed, True)
    two["ship2"] = ship2
    two["intro"] = "A practice chart (%s) with two ships. Same code, same sea: share it, or try again." % gen.NAMES[difficulty]
    ship = fleet.ship_chart(two, 1)
    ship["seed"] = fleet.ship_seed(chart["seed"], 1)
    for clearance in (1.0, 1.7):
        options, path = _candidates(ship, clearance)
        for wait, legs in options:
            legs = _final(ship, path, wait)
            if legs is None:
                continue
            hours = sim.plan_hours(legs)
            ship2["deadline"] = max(hours + 1.5, math.ceil((hours * 1.35 + 1.0) * 2.0) / 2.0)
            ship2["par_legs"] = legs
            ship2["par_wait"] = wait
            ship2["waypoints"] = [list(p) for p in path]
            if not _pair_ok(two):
                continue
            honest, _ = solver.route(ship, path, model="charted", seed=ship["seed"], wait=legs[0]["hours"] if legs[0]["speed"] == 0 else 0.0)
            hres = sim.sail(ship, honest, seed=ship["seed"])
            if hres["aground"] is not None or dist(hres["end"], dest) > ship["arrival_radius"]:
                continue
            ship2["naive_fails"] = sim.naive_miss(fleet.ship_chart(two, 1)) > ship["arrival_radius"]
            return two
    return None


def _final(ship, path, wait):
    """The plan actually kept: the route re-shot at any speed (as Ship A's was), if it is still clean and precise."""
    seed = ship["seed"]
    legs, _ = solver.route(ship, path, model="true", seed=seed, wait=wait)
    res = sim.sail(ship, legs, seed=seed)
    if res["aground"] is not None or res["close"] or dist(res["end"], ship["dest"]) > ship["arrival_radius"] / 2.0 or not legs:
        return None
    return legs


def _pair_ok(two):
    """Both par plans together: three stars and a margin on the separation rule."""
    legs_a = two["par_legs"]
    legs_b = two["ship2"]["par_legs"]
    res = fleet.sail_fleet(two, legs_a, legs_b, seed=two["seed"])
    if res["approach"]["dist"] < fleet.SEPARATION + MARGIN_NM:
        return False
    sc = fleet.score_fleet(two, legs_a, legs_b, res)
    return sc["stars"] == 3
