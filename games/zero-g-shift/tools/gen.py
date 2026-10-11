"""Zero-G Shift -- the bay finder (an offline authoring tool; its results are frozen into bays_*.py).

`make(params, seed)` builds one random candidate with a seeded random source and returns its rows, or None. `evaluate`
runs the full solver on it and says whether it is a fair bay (solvable, par at least `min_par`, at most 3 shortest
solutions, the deck's new part really needed). The game itself never imports this file (it is the only place a random
source is used, and its output is frozen).

    python3 tools/gen.py DECK [--seeds A-B] [--show N]
"""

import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import rules      # noqa: E402
import solver     # noqa: E402

FEATURES = {"walls": "#", "posts": "o", "hatches": "h", "bumpers": "b"}


def make(p, seed):
    """p: w, h, kinds (list of kind numbers, one crate each), walls, posts, hatches, bumpers, door (bool)."""
    rng = random.Random(seed)
    w, h = p["w"], p["h"]
    grid = [["."] * w for _ in range(h)]
    free = [(x, y) for y in range(h) for x in range(w)]
    rng.shuffle(free)

    def take():
        return free.pop()

    for _ in range(p.get("segs", 0)):
        length = rng.choice((2, 2, 3))
        x, y = rng.randrange(w), rng.randrange(h)
        dx, dy = rng.choice(((1, 0), (0, 1)))
        for k in range(length):
            cx, cy = x + dx * k, y + dy * k
            if 0 <= cx < w and 0 <= cy < h and (cx, cy) in free:
                free.remove((cx, cy))
                grid[cy][cx] = "#"
    for key, ch in FEATURES.items():
        for _ in range(p.get(key, 0)):
            if free:
                x, y = take()
                grid[y][x] = ch
    door_kind = None
    if p.get("door"):
        door_kind = rng.choice(p["kinds"])
        for _ in range(p.get("door_cells", 1)):
            x, y = take()
            grid[y][x] = "="
    px, py = take()
    grid[py][px] = "@"
    for k in p["kinds"]:
        x, y = take()
        grid[y][x] = "ABCD"[k]
        x, y = take()
        grid[y][x] = "1234"[k]
    rows = ["".join(r) for r in grid]
    spec = {"id": "g%d" % seed, "rows": rows}
    if door_kind is not None:
        spec["door"] = "ABCD"[door_kind]
    return spec


def evaluate(spec, cap=30000, min_par=4):
    try:
        bay = rules.Bay(spec)
    except rules.BayError:
        return None
    a = solver.Analysis(bay, cap=cap)
    if not a.complete or a.par is None or a.par < min_par:
        return None
    return bay, a


def search(p, seeds, cap=30000, min_par=4, max_optimal=3, need=None):
    """Yield (seed, bay, analysis) for every fair candidate."""
    for seed in seeds:
        spec = make(p, seed)
        got = evaluate(spec, cap, min_par)
        if got is None:
            continue
        bay, a = got
        if a.optimal_count() > max_optimal:
            continue
        if need is not None and not need(bay, a):
            continue
        yield seed, bay, a


if __name__ == "__main__":
    print(__doc__)
