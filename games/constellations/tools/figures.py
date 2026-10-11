"""Turn a constellation's real star positions and line figure into a chart, and derive the clues (dev tool; the game never runs it).

  layout(...)          gnomonic projection around the figure's centre, east to the left (as on a sky map), scaled onto a 1000 wide
                       canvas and rounded to whole numbers. Positions are frozen in the chart data, so geometry is exact integer maths.
  candidates(...)      the lines a player may draw: the traditional figure plus each star's nearest neighbours, minus any line that
                       would pass too close to a third star.
  derive_clues(...)    start from a number on every star, add must / never lines only if needed, then take clues away one at a time
                       for as long as the figure stays the ONLY valid one. The result is irreducible: every clue left is needed.
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import sky  # noqa: E402

CANVAS_W = 1000
MARGIN = 100
MIN_GAP = 68          # no two stars closer than this on the canvas
LINE_GAP = 34         # no star closer than this to a line of the figure it is not part of
CLEAR = 26            # a candidate line may not pass closer than this to a star that is not one of its ends
NEIGHBOURS = 3
FIGURE_CLEAR = 10    # the traditional figure itself may run a little closer


def project(stars, hips):
    """Gnomonic projection about the mean direction of the stars. Returns ({hip: (X, Y)}, (ra0_hours, dec0_degrees)) with X to the right
    (east on the left, as on a sky map) and Y downwards, in radians."""
    ras = {h: math.radians(float(stars[str(h)]["ra"]) * 15) for h in hips}
    decs = {h: math.radians(float(stars[str(h)]["dec"])) for h in hips}
    x = sum(math.cos(decs[h]) * math.cos(ras[h]) for h in hips)
    y = sum(math.cos(decs[h]) * math.sin(ras[h]) for h in hips)
    z = sum(math.sin(decs[h]) for h in hips)
    ra0, dec0 = math.atan2(y, x), math.atan2(z, math.hypot(x, y))
    out = {}
    for h in hips:
        cosc = math.sin(dec0) * math.sin(decs[h]) + math.cos(dec0) * math.cos(decs[h]) * math.cos(ras[h] - ra0)
        xi = math.cos(decs[h]) * math.sin(ras[h] - ra0) / cosc
        eta = (math.cos(dec0) * math.sin(decs[h]) - math.sin(dec0) * math.cos(decs[h]) * math.cos(ras[h] - ra0)) / cosc
        out[h] = (-xi, -eta)
    return out, ((math.degrees(ra0) % 360) / 15.0, math.degrees(dec0))


def layout(points, segments=()):
    """Scale radians onto the canvas. Returns (pixel positions {hip: (x, y)}, width, height, origin (ox, oy), scale)."""
    xs = [p[0] for p in points.values()]
    ys = [p[1] for p in points.values()]
    bw, bh = max(xs) - min(xs), max(ys) - min(ys)
    scale = min((CANVAS_W - 2 * MARGIN) / bw, (CANVAS_W - 2 * MARGIN) / bh)
    width = CANVAS_W
    height = int(min(1000, max(560, round(bh * scale + 2 * MARGIN))))
    ox = width / 2 - (min(xs) + max(xs)) / 2 * scale
    oy = height / 2 - (min(ys) + max(ys)) / 2 * scale
    flat = {h: [ox + p[0] * scale, oy + p[1] * scale] for h, p in points.items()}
    spread(flat, MIN_GAP, (MARGIN // 2, MARGIN // 2, width - MARGIN // 2, height - MARGIN // 2), segments, LINE_GAP)
    pix = {h: (int(round(v[0])), int(round(v[1]))) for h, v in flat.items()}
    return pix, width, height, (int(round(ox)), int(round(oy))), scale


def spread(flat, gap, box, segments=(), clear=0):
    """Push crowded stars apart until no two are closer than `gap` (a few percent of the canvas): the chart is a drawing, not a survey,
    and two stars a finger-width apart could not be told apart. Deterministic: fixed passes, pairs in sorted order."""
    keys = sorted(flat)
    for _ in range(400):
        moved = False
        for ai in range(len(keys)):
            for bi in range(ai + 1, len(keys)):
                a, b = flat[keys[ai]], flat[keys[bi]]
                dx, dy = b[0] - a[0], b[1] - a[1]
                d = math.hypot(dx, dy)
                if d < gap:
                    if d < 1e-9:
                        dx, dy, d = 1.0, 0.0, 1.0
                    push = (gap - d) / 2 + 0.01
                    a[0] -= dx / d * push
                    a[1] -= dy / d * push
                    b[0] += dx / d * push
                    b[1] += dy / d * push
                    moved = True
        for a_key, b_key in segments:                     # a star may not sit on a line of the figure it does not belong to
            a, b = flat[a_key], flat[b_key]
            for key in keys:
                if key in (a_key, b_key):
                    continue
                p = flat[key]
                dx, dy = b[0] - a[0], b[1] - a[1]
                length2 = dx * dx + dy * dy
                t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / length2)) if length2 else 0.0
                qx, qy = a[0] + t * dx, a[1] + t * dy
                d = math.hypot(p[0] - qx, p[1] - qy)
                if d < clear:
                    nx, ny = (p[0] - qx, p[1] - qy) if d > 1e-9 else (-dy, dx)
                    norm = math.hypot(nx, ny) or 1.0
                    push = clear - d + 0.01
                    p[0] += nx / norm * push
                    p[1] += ny / norm * push
                    moved = True
        for v in flat.values():
            v[0] = min(max(v[0], box[0]), box[2])
            v[1] = min(max(v[1], box[1]), box[3])
        if not moved:
            break


def figure_edges(lines, drop=(), cap=None, stars=None):
    """The traditional line figure as a set of (hip, hip) pairs, trimmed: stars in `drop` go (their two neighbours are joined if the
    star sat in the middle of a line); then, if `cap` is given, the faintest leaf star goes until at most `cap` stars remain."""
    edges = set()
    for chain in lines:
        for a, b in zip(chain, chain[1:]):
            if a != b:
                edges.add(tuple(sorted((a, b))))
    for h in drop:
        near = [e for e in edges if h in e]
        others = sorted(x for e in near for x in e if x != h)
        edges = {e for e in edges if h not in e}
        if len(others) == 2:
            edges.add(tuple(others))
    while cap:
        nodes = {h for e in edges for h in e}
        if len(nodes) <= cap:
            break
        degree = {n: sum(n in e for e in edges) for n in nodes}
        leaves = [n for n in nodes if degree[n] == 1]
        if not leaves:
            raise ValueError("cannot trim the figure to %d stars" % cap)
        faint = max(leaves, key=lambda h: (float(stars[str(h)]["mag"]), h))
        edges = {e for e in edges if faint not in e}
    return edges


def candidates(pix_by_index, figure, neighbours=NEIGHBOURS):
    """Candidate lines as sorted (i, j) index pairs: the figure plus each star's nearest neighbours (both directions), minus lines that
    pass within CLEAR of another star. The figure's own lines are always kept (and must themselves be clear: checked)."""
    n = len(pix_by_index)
    keep = set(figure)
    for i in range(n):
        near = sorted((j for j in range(n) if j != i),
                      key=lambda j: ((pix_by_index[i][0] - pix_by_index[j][0]) ** 2 + (pix_by_index[i][1] - pix_by_index[j][1]) ** 2, j))
        for j in near[:neighbours]:
            keep.add((min(i, j), max(i, j)))

    def clear(e):
        a, b = pix_by_index[e[0]], pix_by_index[e[1]]
        return all(sky.point_segment_distance2(pix_by_index[v], a, b) >= CLEAR * CLEAR for v in range(n) if v not in e)
    out = []
    for e in sorted(keep):
        if clear(e):
            out.append(e)
        elif e in figure and all(sky.point_segment_distance2(pix_by_index[v], pix_by_index[e[0]], pix_by_index[e[1]]) >= FIGURE_CLEAR ** 2
                                 for v in range(n) if v not in e):
            out.append(e)
        elif e in figure:
            raise ValueError("a figure line passes too close to another star: %s" % (e,))
    return out


def _count(chart, degree, must, never, limit=2):
    return sky.count_solutions(chart.with_clues(degree, must, never), limit)


def derive_clues(chart, figure, order_key=None, extras_limit=200, shuffle=None):
    """Irreducible clues for `chart` (a sky.Chart whose edges include the figure): returns (degree, must, never) with exactly one valid
    figure, equal to `figure`, and no clue that can be dropped without a second figure appearing."""
    fig_idx = {chart.index[e] for e in figure}
    degree = {v: sum(1 for k in fig_idx if v in chart.edges[k]) for v in range(chart.n)}
    must, never = [], []
    count = sky.count_solutions(chart.with_clues(degree), extras_limit)
    while count > 1:
        best = None
        pool = [("must", chart.edges[k]) for k in sorted(fig_idx) if chart.edges[k] not in must] + \
               [("never", chart.edges[k]) for k in range(len(chart.edges)) if k not in fig_idx and chart.edges[k] not in never]
        for kind, e in pool:
            m2 = must + [e] if kind == "must" else must
            n2 = never + [e] if kind == "never" else never
            c = _count(chart, degree, m2, n2, extras_limit)
            if best is None or c < best[0]:
                best = (c, kind, e)
        if best is None or best[0] >= count:
            raise ValueError("no clue narrows the figure down")
        count = best[0]
        (must if best[1] == "must" else never).append(best[2])
    # take clues away while the figure stays the only one
    changed = True
    keys = [("never", e) for e in never] + [("must", e) for e in must] + [("degree", v) for v in sorted(degree, key=order_key or (lambda v: -v))]
    if shuffle is not None:
        shuffle.shuffle(keys)
    while changed:
        changed = False
        for kind, what in list(keys):
            if kind == "degree":
                d2 = {v: n for v, n in degree.items() if v != what}
                m2, n2 = must, never
            elif kind == "must":
                d2, m2, n2 = degree, [e for e in must if e != what], never
            else:
                d2, m2, n2 = degree, must, [e for e in never if e != what]
            if _count(chart, d2, m2, n2) == 1:
                degree, must, never = d2, m2, n2
                keys.remove((kind, what))
                changed = True
    return degree, must, never


def best_clues(chart, figure, tries=80):
    """Try several removal orders (the first is the plain one) and keep the irreducible clue set that a person can finish with the least
    reasoning: no what-if needed beats what-if, then more numbers beat fewer, then fewer must / never lines. Returns
    (degree, must, never, level) with level 1 = line logic, 2 = line logic with one what-if step, 0 = neither (not shipped)."""
    import random
    fig_idx = frozenset(chart.index[e] for e in figure)
    best = None
    for seed in range(tries):
        rng = None if seed == 0 else random.Random(seed)
        degree, must, never = derive_clues(chart, figure, shuffle=rng)
        trial = chart.with_clues(degree, must, never)
        level = 0
        if sky.solved_by_logic(trial) == fig_idx:
            level = 1
        elif sky.solved_by_logic(trial, lookahead=True) == fig_idx:
            level = 2
        score = (0 if level == 1 else 1 if level == 2 else 2, -len(degree), len(must) + len(never))
        if best is None or score < best[0]:
            best = (score, degree, must, never, level)
        if level == 1 and seed >= 8:
            break
    return best[1], best[2], best[3], best[4]
