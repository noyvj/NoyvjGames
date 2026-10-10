"""Dead Reckoning -- the practice chart generator. A practice chart is a pure function of (difficulty, seed): the same code always
makes the same chart, so a code such as DR3-1K9X2 can be shared and replayed.

Every chart is built by rejection: lay out the sea, then SOLVE it (a visibility graph around the hazards gives a route, the
solver shoots each leg under the true sea), and keep the chart only if that solution lands cleanly, on time and without so much
as brushing a hazard. A seed that cannot be solved within a few attempts makes `make_chart` return None, and the caller falls
back to an authored chart."""

import math
import re

import chartkit
import sim
import solver
from geom import dist, point_in_polygon, seg_point_dist, seg_polygon_dist

DIFFICULTIES = (1, 2, 3, 4, 5)
NAMES = {1: "Easy water", 2: "A stream", 3: "Wind and land", 4: "Tides and compass", 5: "Fog and everything"}
SEED_LIMIT = 36 ** 6
ATTEMPTS = 14
SPEC = {
    1: dict(size=20, hazards=2, unmarked=0, land=0, currents=0, tide=False, wind=False, compass=False, gusts=0.0, radius=2.0),
    2: dict(size=20, hazards=2, unmarked=0, land=0, currents=1, tide=False, wind=False, compass=False, gusts=0.0, radius=1.5),
    3: dict(size=20, hazards=3, unmarked=0, land=1, currents=1, tide=False, wind=True, compass=False, gusts=0.05, radius=1.5),
    4: dict(size=30, hazards=4, unmarked=0, land=1, currents=2, tide=True, wind=True, compass=True, gusts=0.08, radius=1.5),
    5: dict(size=30, hazards=5, unmarked=2, land=2, currents=2, tide=True, wind=True, compass=True, gusts=0.1, radius=1.5, fog=True),
}
CODE_RE = re.compile(r"^DR([1-5])(T?)-([0-9A-Z]{1,6})$")
ID_RE = re.compile(r"^practice-([1-5])(t?)-([0-9a-z]{1,6})$")
_CACHE = {}


# --- codes ---------------------------------------------------------------------------------------
def to_base36(n):
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    out = ""
    while n:
        n, r = divmod(n, 36)
        out = digits[r] + out
    return out or "0"


def chart_id(difficulty, seed, two=False):
    return "practice-%d%s-%s" % (difficulty, "t" if two else "", to_base36(seed))


def code_of(difficulty, seed, two=False):
    """DR3-1K9X2; a two-ship chart carries a T after the level (DR3T-1K9X2), so every earlier code keeps meaning what it did."""
    return ("DR%d%s-%s" % (difficulty, "T" if two else "", to_base36(seed))).upper()


def parse_ex(text):
    """(difficulty, seed, two) from a share code (any case, surrounding spaces ignored) or a chart id, or None."""
    if not isinstance(text, str):
        return None
    t = text.strip()
    m = CODE_RE.match(t.upper()) or ID_RE.match(t.lower())
    if not m:
        return None
    seed = int(m.group(3), 36)
    return (int(m.group(1)), seed, bool(m.group(2))) if seed < SEED_LIMIT else None


def parse(text):
    """(difficulty, seed) from a ONE-ship share code or chart id, or None (a two-ship code is read by parse_ex)."""
    parsed = parse_ex(text)
    return parsed[:2] if parsed and not parsed[2] else None


def is_practice_id(text):
    return isinstance(text, str) and ID_RE.match(text) is not None


# --- a small repeatable random source ------------------------------------------------------------------
class Rng:
    def __init__(self, seed):
        self.seed = seed
        self.k = 0

    def rand(self):
        self.k += 1
        return (sim.unit_noise(self.seed, self.k) + 1.0) / 2.0

    def uniform(self, lo, hi):
        return lo + (hi - lo) * self.rand()

    def pick(self, items):
        return items[min(len(items) - 1, int(self.rand() * len(items)))]


# --- laying out a sea ------------------------------------------------------------------------------
def _along(a, b, t, offset):
    """A point t of the way from a to b, pushed `offset` nm to the side of the line."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy) or 1.0
    return (a[0] + dx * t - dy / length * offset, a[1] + dy * t + dx / length * offset)


def _place_hazards(rng, spec, start, dest, size, radius):
    out = []
    names = ["Pike", "Gull", "Hob", "Grey", "Mull", "Skerry", "Anvil", "Dunn", "Crab", "Wren"]
    total = spec["hazards"]
    for i in range(total):
        marked = i < total - spec["unmarked"]
        for _ in range(20):
            r = rng.uniform(0.6, 1.2)
            spread = 1.0 if not marked else 2.2
            p = _along(start, dest, rng.uniform(0.2, 0.8), rng.uniform(-spread, spread))
            ok = 2.0 <= min(p[0], p[1], size - p[0], size - p[1]) and dist(p, start) > r + 3.0 and dist(p, dest) > r + radius + 1.5
            ok = ok and all(dist(p, (h["x"], h["y"])) > r + h["r"] + 1.0 for h in out)
            if ok:
                kind = rng.pick(["reef", "shoal", "rock"])
                name = "%s %s" % (rng.pick(names), kind.capitalize())
                out.append({"id": "h%d" % i, "kind": kind, "name": name + (" %d" % (i + 1)), "x": round(p[0], 1), "y": round(p[1], 1),
                            "r": round(r if kind != "rock" else min(r, 0.8), 1), "charted": marked})
                break
    return out


def _place_land(rng, spec, start, dest, size, hazards):
    out = []
    for i in range(spec["land"]):
        for _ in range(20):
            c = _along(start, dest, rng.uniform(0.3, 0.7), rng.pick([-1, 1]) * rng.uniform(1.8, 3.5))
            rad = rng.uniform(1.6, 2.6)
            poly = [(round(c[0] + math.sin(a) * rad * rng.uniform(0.7, 1.1), 1), round(c[1] + math.cos(a) * rad * rng.uniform(0.7, 1.1), 1))
                    for a in (0.0, 1.3, 2.6, 3.9, 5.2)]
            ok = all(1.0 <= p[0] <= size - 1.0 and 1.0 <= p[1] <= size - 1.0 for p in poly)
            ok = ok and not point_in_polygon(start, poly) and not point_in_polygon(dest, poly)
            ok = ok and seg_polygon_dist(start, start, poly) > 3.0 and seg_polygon_dist(dest, dest, poly) > 3.0
            ok = ok and all(seg_polygon_dist((h["x"], h["y"]), (h["x"], h["y"]), poly) > h["r"] + 1.5 for h in hazards)
            ok = ok and all(not _polys_close(poly, other["poly"]) for other in out)
            if ok:
                out.append({"id": "land%d" % i, "name": rng.pick(["Long Point", "Mull Head", "Gull Island", "Hob's Isle", "Dunn Cape"]) + (" %d" % (i + 1)),
                            "poly": [list(p) for p in poly]})
                break
    return out


def _polys_close(a, b):
    ca = (sum(p[0] for p in a) / len(a), sum(p[1] for p in a) / len(a))
    cb = (sum(p[0] for p in b) / len(b), sum(p[1] for p in b) / len(b))
    return dist(ca, cb) < 6.0


def _place_currents(rng, spec, size):
    out = []
    n = spec["currents"]
    bands = [(0.0, 0.5), (0.5, 1.0)] if n > 1 else [(rng.uniform(0.15, 0.4), rng.uniform(0.6, 0.85))]
    for i in range(n):
        lo, hi = bands[i]
        tidal = spec["tide"] and i == n - 1
        centre = rng.uniform(1.2, 2.0) if tidal else rng.uniform(0.7, 1.5)
        heading = round(rng.uniform(0, 360)) % 360
        zone = {"id": "z%d" % i, "name": "stream %d" % (i + 1), "rect": [round(size * lo, 1), 0, round(size * hi, 1), size], "set": heading,
                "drift_range": [round(centre - 0.3, 1), round(centre + 0.3, 1)], "true_set": (heading + round(rng.uniform(-5, 5))) % 360,
                "true_drift": round(centre + rng.uniform(-0.1, 0.1), 2)}
        if tidal:
            zone["tide"] = {"period": 12.0, "phase": float(round(rng.uniform(0, 11)))}
        out.append(zone)
    return out


# --- a route round the hazards -------------------------------------------------------------------------
def _clear(a, b, chart, margin):
    for h in chart["hazards"]:
        if seg_point_dist(a, b, (h["x"], h["y"])) <= h["r"] + margin:
            return False
    for land in chart["land"]:
        poly = [tuple(p) for p in land["poly"]]
        if seg_polygon_dist(a, b, poly) <= margin:
            return False
    return True


def route_nodes(chart, clearance):
    size = chart["size"]
    nodes = []
    for h in chart["hazards"]:
        for k in range(8):
            a = k * math.pi / 4.0
            nodes.append((h["x"] + math.sin(a) * (h["r"] + clearance), h["y"] + math.cos(a) * (h["r"] + clearance)))
    for land in chart["land"]:
        cx = sum(p[0] for p in land["poly"]) / len(land["poly"])
        cy = sum(p[1] for p in land["poly"]) / len(land["poly"])
        for p in land["poly"]:
            d = dist((cx, cy), p) or 1.0
            nodes.append((p[0] + (p[0] - cx) / d * (clearance + 0.4), p[1] + (p[1] - cy) / d * (clearance + 0.4)))
    return [n for n in nodes if 0.8 <= n[0] <= size - 0.8 and 0.8 <= n[1] <= size - 0.8]


def plan_route(chart, clearance=1.0):
    """The shortest path start -> flag through the visibility graph of inflated hazards, as a list of waypoints, or None."""
    start, dest = tuple(chart["start"]), tuple(chart["dest"])
    margin = clearance - 0.2
    nodes = [start, dest] + [n for n in route_nodes(chart, clearance) if _clear(n, n, chart, 0.3)]
    best = {0: 0.0}
    prev = {}
    todo = {0}
    done = set()
    while todo:
        i = min(todo, key=lambda k: best[k])
        todo.discard(i)
        done.add(i)
        if i == 1:
            break
        for j in range(len(nodes)):
            if j in done or j == i:
                continue
            d = best[i] + dist(nodes[i], nodes[j])
            if d < best.get(j, 1e18) - 1e-9 and _clear(nodes[i], nodes[j], chart, margin):
                best[j] = d
                prev[j] = i
                todo.add(j)
    if 1 not in best:
        return None
    path = [1]
    while path[-1] != 0:
        path.append(prev[path[-1]])
    return [nodes[k] for k in reversed(path)]


def _solve(chart, clearance):
    """Legs that land cleanly, trying a few hours of waiting when the chart has a tide. Returns (legs, result, score) or None."""
    path = plan_route(chart, clearance)
    if path is None:
        return None
    seed = chart["seed"]
    tidal = any(z.get("tide") for z in chart["currents"])
    waits = [0.0] if not tidal else [float(w) for w in range(0, 12)]
    best = None
    for w in waits:
        legs, _ = solver.route(chart, path, speed=sim.cruise_speed(chart) if tidal else None, model="true", seed=seed, wait=w)
        res = sim.sail(chart, legs, seed=seed)
        miss = dist(res["end"], chart["dest"])
        if res["aground"] is None and not res["close"]:
            key = (round(miss, 1) > chart["arrival_radius"] / 2.0, sim.plan_hours(legs))
            if best is None or key < best[0]:
                best = (key, w)
    if best is None:
        return None
    w = best[1]
    legs, _ = solver.route(chart, path, model="true", seed=seed, wait=w)
    res = sim.sail(chart, legs, seed=seed)
    if res["aground"] is not None or res["close"]:
        return None
    return legs, res


def _build(difficulty, seed, attempt):
    spec = SPEC[difficulty]
    rng = Rng(seed * 64 + attempt)
    size = spec["size"]
    margin = size * 0.1
    start = (round(rng.uniform(margin, size * 0.3), 1), round(rng.uniform(margin, size - margin), 1))
    dest = (round(rng.uniform(size * 0.7, size - margin), 1), round(rng.uniform(margin, size - margin), 1))
    if dist(start, dest) < size * 0.6:
        return None
    hazards = _place_hazards(rng, spec, start, dest, size, spec["radius"])
    land = _place_land(rng, spec, start, dest, size, hazards)
    currents = _place_currents(rng, spec, size)
    fields = {"size": size, "start": list(start), "dest": list(dest), "arrival_radius": spec["radius"], "speeds": [3.0, 7.0] if size == 20 else [4.0, 8.0],
              "hazards": hazards, "land": land, "currents": currents, "seed": seed, "gusts": spec["gusts"], "fog": bool(spec.get("fog")),
              "start_hour": float(round(rng.uniform(0, 11))) if any(z.get("tide") for z in currents) else 0.0,
              "intro": "A practice chart (%s). Same code, same sea: share it, or try again." % NAMES[difficulty],
              "log": {"arrived": "Landfall.", "missed": "Short of the flag.", "aground": "Aground; the tide will lift us.", "late": "There, but late."},
              "deadline": 10.0}
    if spec["wind"]:
        c = rng.uniform(12, 18)
        fields["wind"] = {"from": round(rng.uniform(0, 360)) % 360, "range": [round(c - 2, 1), round(c + 2, 1)], "true": round(c + rng.uniform(-1, 1), 1)}
    if spec["compass"]:
        c = rng.pick([-1, 1]) * rng.uniform(4, 9)
        fields["compass"] = {"range": [round(c - 1.5, 1), round(c + 1.5, 1)], "true": round(c + rng.uniform(-0.5, 0.5), 1)}
    chart = chartkit.chart(chart_id(difficulty, seed), "Practice %s" % code_of(difficulty, seed), "practice", **fields)
    for clearance in (1.0, 1.7):
        solved = _solve(chart, clearance)
        if solved is None:
            continue
        legs, res = solved
        hours = sim.plan_hours(legs)
        chart["deadline"] = max(hours + 1.5, math.ceil((hours * 1.35 + 1.0) * 2.0) / 2.0)
        chart["par_legs"] = legs
        sc = sim.score(chart, legs, res)
        if not (sc["arrived"] and sc["on_time"] and sc["clear"]):
            continue
        fl, _ = solver.route(chart, plan_route(chart, clearance), model="charted", seed=seed, wait=legs[0]["hours"] if legs and legs[0]["speed"] == 0 else 0.0)
        fres = sim.sail(chart, fl, seed=seed)
        if fres["aground"] is not None or dist(fres["end"], chart["dest"]) > chart["arrival_radius"]:
            continue
        chart["naive_fails"] = sim.naive_miss(chart) > chart["arrival_radius"]
        chart["waypoints"] = [list(p) for p in plan_route(chart, clearance)]
        return chart
    return None


def make_chart(difficulty, seed, two=False):
    """The practice chart for (difficulty, seed), or None if no solvable chart came out of the attempts. With `two`, a two-ship chart
    (gentwo.py: the same sea and Ship A, plus a second ship whose own route is solved and kept clear of the first)."""
    if difficulty not in SPEC or not isinstance(seed, int) or isinstance(seed, bool) or not 0 <= seed < SEED_LIMIT:
        return None
    key = (difficulty, seed, bool(two))
    if key not in _CACHE:
        built = None
        for attempt in range(ATTEMPTS):
            built = _build(difficulty, seed, attempt)
            if two and built is not None:
                import gentwo
                built = gentwo.add_second_ship(built, difficulty, seed, attempt)
            if built is not None:
                break
        if len(_CACHE) > 40:
            _CACHE.clear()
        _CACHE[key] = built
    return _CACHE[key]


def from_id(text):
    """The chart for a practice chart id or share code, or None."""
    parsed = parse_ex(text)
    return make_chart(*parsed) if parsed else None


def next_seed(played, difficulty, nonce=0):
    """A fresh-looking seed for the next practice chart: repeatable from what the player has done, never a clock."""
    return (played * 7919 + difficulty * 104729 + nonce * 15485863 + 12345) % SEED_LIMIT
