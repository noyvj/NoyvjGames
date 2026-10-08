"""Dead Reckoning -- the reference solver: it finds legs that carry the ship to a point under a chosen model of the sea.

It is used three ways: the "steer allowing for the charted stream" helper (model "charted", the best honest guess), the
authored charts' par plans and the practice generator's solvability check (model "true", the answer key).

The method is shooting: sail a leg, see where it ends relative to where it should, turn by the angular error, repeat. Hours
are then picked from the prefixes of the one long sail (a leg may stop at any half hour)."""

import math

from geom import angle_diff, bearing, dist
from sim import LEG_STEP, MAX_LEG_HOURS, SPEED_STEP, clean_leg, cruise_speed, sail


def _prefix_ends(chart, start, heading, speed, hours, model, t_start, seed):
    """Positions at every half hour of one long leg: [(hours, (x, y))]."""
    res = sail(chart, [{"heading": heading, "speed": speed, "hours": hours}], seed=seed, model=model, start=start,
               t_start=t_start, collide=False)
    out = []
    for t, x, y in res["track"]:
        if t > 1e-9 and abs(t / LEG_STEP - round(t / LEG_STEP)) < 1e-9:
            out.append((t, (x, y)))
    return out


def _converge(chart, start, target, speed, model, t_start, seed):
    """Turn by the angular error of the best prefix until the leg points where it should. Returns (heading, hmax)."""
    d = dist(start, target)
    hmax = min(MAX_LEG_HOURS, max(LEG_STEP, math.ceil((d / max(speed, 0.5) * 2.0 + 1.0) / LEG_STEP) * LEG_STEP))
    heading = bearing(start, target)
    for _ in range(16):
        prefixes = _prefix_ends(chart, start, heading, speed, hmax, model, t_start, seed)
        best = min(prefixes, key=lambda p: dist(p[1], target))
        err = angle_diff(bearing(start, best[1]), bearing(start, target))
        if abs(err) < 0.2:
            break
        heading += err
    return heading, hmax


def shoot(chart, start, target, speed=None, model="charted", t_start=0.0, seed=0):
    """One leg {heading, speed, hours} from `start` that ends as close to `target` as the grid of whole degrees, half
    knots and half hours allows, under the given model of the sea. With no `speed` given it tries the speeds around the
    cruising speed (the finer grid is what lets a plan land inside a small arrival radius) and prefers the cruising
    one on a tie. Returns None when the target is the start itself."""
    start, target = tuple(start), tuple(target)
    if dist(start, target) < 1e-6:
        return None
    lo, hi = chart["speeds"]
    cruise = cruise_speed(chart)
    if speed is not None:
        speeds = [speed]
    else:
        speeds = [s for s in (cruise + k * SPEED_STEP for k in range(-3, 4)) if lo - 1e-9 <= s <= hi + 1e-9]
    best = None
    for s in speeds:
        heading, hmax = _converge(chart, start, target, s, model, t_start, seed)
        for h in range(int(round(heading)) - 2, int(round(heading)) + 3):
            heading_i = h % 360
            for hours, pos in _prefix_ends(chart, start, heading_i, s, hmax, model, t_start, seed):
                key = (round(dist(pos, target), 2), abs(s - cruise))
                if best is None or key < best[0]:
                    best = (key, heading_i, s, hours)
    return clean_leg(chart, {"heading": best[1], "speed": best[2], "hours": best[3]})


def route(chart, waypoints, speed=None, model="true", seed=0, wait=0.0):
    """Legs through a list of waypoints (the first is the start), shooting each from where the PREVIOUS leg really ends
    under the model, so errors never pile up. `wait` hours at anchor come first (to catch a fair stream). Returns (legs, end_position)."""
    legs = []
    pos = tuple(waypoints[0])
    clock = 0.0
    if wait > 0:
        legs.append({"heading": 0, "speed": 0.0, "hours": wait})
        clock = wait
    for target in waypoints[1:]:
        leg = shoot(chart, pos, target, speed=speed, model=model, t_start=clock, seed=seed)
        if leg is None:
            continue
        res = sail(chart, [leg], seed=seed, model=model, start=pos, t_start=clock, collide=False)
        legs.append(leg)
        pos = tuple(res["end"])
        clock += leg["hours"]
    return legs, pos


def watch_route(chart, waypoints, watch_hours=2.0, max_watches=30, seed=0):
    """What a careful watch-by-watch player does: sail at most `watch_hours`, take a perfect fix (believe the true position),
    and plan the next watch with the charted midpoints toward the next waypoint. Returns the legs."""
    legs = []
    clock = 0.0
    targets = [tuple(p) for p in waypoints[1:]]
    dest = targets[-1]
    for _ in range(max_watches):
        res = sail(chart, legs, seed=seed, collide=False)
        here = tuple(res["end"])
        while len(targets) > 1 and dist(here, targets[0]) < 0.8:
            targets.pop(0)
        target = targets[0]
        if target == dest and dist(here, dest) < 0.3:
            break
        leg = shoot(chart, here, target, model="charted", t_start=clock, seed=seed)
        if leg is None:
            break
        leg = clean_leg(chart, dict(leg, hours=min(leg["hours"], watch_hours)))
        legs.append(leg)
        clock += leg["hours"]
    return legs
