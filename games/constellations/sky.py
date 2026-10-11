"""Constellations -- the rules, in pure Python with no clock and no randomness.

A chart is a patch of sky: stars at fixed integer positions, a list of CANDIDATE lines (only pairs of stars close enough to be joined),
and clues. A clue is one of
  - a number on a star: exactly that many lines must touch it (0 means the star stays outside the figure),
  - a MUST line: a line that is already drawn and cannot be removed,
  - a NEVER line: a pair that is crossed out and cannot be drawn.
A figure is VALID when every number holds exactly, no two lines cross or touch, no crossed-out pair is drawn, and all the lines form
ONE connected figure. A star without a number may have any number of lines (including none).

This module holds the geometry (`edges_conflict`), the rule check (`analyse`), an exhaustive solver (`solutions`) and an independent
second counter that shares no search code with it (`count_by_stars`), and `propagate`, the line-logic that a person can follow: it is what
the proofs use to show that a chart can be finished by reasoning alone, and what the hint ladder of a later milestone will read.
"""

import itertools


# ---- geometry (exact integer arithmetic) ---------------------------------------------------------------------------------
def orient(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _within(a, b, c):
    return min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= c[1] <= max(a[1], b[1])


def segments_touch(p, q, r, s):
    """Do the closed segments pq and rs share any point?"""
    o1, o2, o3, o4 = orient(p, q, r), orient(p, q, s), orient(r, s, p), orient(r, s, q)
    if ((o1 > 0 and o2 < 0) or (o1 < 0 and o2 > 0)) and ((o3 > 0 and o4 < 0) or (o3 < 0 and o4 > 0)):
        return True
    return ((o1 == 0 and _within(p, q, r)) or (o2 == 0 and _within(p, q, s)) or
            (o3 == 0 and _within(r, s, p)) or (o4 == 0 and _within(r, s, q)))


def edges_conflict(pts, e, f):
    """Two different lines conflict when they cross, touch, or lie along each other. Lines that only share a star do not conflict."""
    if e == f:
        return False
    shared = set(e) & set(f)
    if len(shared) == 2:
        return False
    if len(shared) == 1:
        v = next(iter(shared))
        a = e[0] if e[1] == v else e[1]
        b = f[0] if f[1] == v else f[1]
        if orient(pts[v], pts[a], pts[b]) != 0:
            return False
        da = (pts[a][0] - pts[v][0], pts[a][1] - pts[v][1])
        db = (pts[b][0] - pts[v][0], pts[b][1] - pts[v][1])
        return da[0] * db[0] + da[1] * db[1] > 0          # collinear and leaving the star the same way: one runs along the other
    return segments_touch(pts[e[0]], pts[e[1]], pts[f[0]], pts[f[1]])


def point_segment_distance2(p, a, b):
    """Squared distance from point p to the segment ab (floats are fine here: it is only used to keep lines clear of stars)."""
    ax, ay, bx, by, px, py = a[0], a[1], b[0], b[1], p[0], p[1]
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    cx, cy = ax + t * dx, ay + t * dy
    return (px - cx) ** 2 + (py - cy) ** 2


# ---- a chart --------------------------------------------------------------------------------------------------------------
class Chart:
    """The rules view of one chart. `data` is the frozen dict from a charts_sN module (only `stars`, `edges` and `clues` are used here)."""

    def __init__(self, data):
        self.id = data.get("id", "")
        self.pts = [(s["x"], s["y"]) for s in data["stars"]]
        self.n = len(self.pts)
        self.edges = [tuple(e) for e in data["edges"]]
        self.index = {e: k for k, e in enumerate(self.edges)}
        clues = data["clues"]
        self.need = {int(k): v for k, v in clues.get("degree", {}).items()}
        self.must = frozenset(self.index[tuple(e)] for e in clues.get("must", []))
        self.never = frozenset(self.index[tuple(e)] for e in clues.get("never", []))
        self.inc = [[] for _ in range(self.n)]
        for k, (i, j) in enumerate(self.edges):
            self.inc[i].append(k)
            self.inc[j].append(k)
        self.conflict = [0] * len(self.edges)
        for k, e in enumerate(self.edges):
            for m in range(k + 1, len(self.edges)):
                if edges_conflict(self.pts, e, self.edges[m]):
                    self.conflict[k] |= 1 << m
                    self.conflict[m] |= 1 << k

    def edge(self, i, j):
        """The index of the line between stars i and j, or None if that pair is not allowed on this chart."""
        return self.index.get((i, j) if i < j else (j, i))

    def with_clues(self, degree, must=(), never=()):
        """A copy of this chart with other clues (used by the builder and the tests)."""
        other = Chart.__new__(Chart)
        other.__dict__.update(self.__dict__)
        other.need = dict(degree)
        other.must = frozenset(self.index[tuple(e)] for e in must)
        other.never = frozenset(self.index[tuple(e)] for e in never)
        return other


def _components(chart, chosen):
    parent = list(range(chart.n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for k in chosen:
        i, j = chart.edges[k]
        parent[find(i)] = find(j)
    return len({find(v) for k in chosen for v in chart.edges[k]})


def analyse(chart, chosen):
    """Judge a set of chosen line indices (the must lines are added). Returns a dict:
    degree (per star), over / under (numbered stars with too many / too few lines), crossings (pairs of line indices),
    never_used, parts (separate pieces), connected, valid."""
    chosen = set(chosen) | set(chart.must)
    degree = [0] * chart.n
    for k in chosen:
        i, j = chart.edges[k]
        degree[i] += 1
        degree[j] += 1
    over = sorted(v for v, need in chart.need.items() if degree[v] > need)
    under = sorted(v for v, need in chart.need.items() if degree[v] < need)
    ordered = sorted(chosen)
    crossings = [(a, b) for a, b in itertools.combinations(ordered, 2) if chart.conflict[a] >> b & 1]
    never_used = sorted(chosen & chart.never)
    parts = _components(chart, chosen)
    connected = parts == 1
    valid = bool(chosen) and not over and not under and not crossings and not never_used and connected
    return {"degree": degree, "over": over, "under": under, "crossings": crossings, "never_used": never_used,
            "parts": parts, "connected": connected, "valid": valid}


def is_valid(chart, chosen):
    return analyse(chart, chosen)["valid"]


# ---- the exhaustive solver -------------------------------------------------------------------------------------------------
def solutions(chart, limit=2):
    """Every valid figure, up to `limit` of them, as frozensets of line indices. Depth-first over the lines, pruned by the numbers
    and the crossings; the connected-figure test is made on each full candidate. Exhaustive: when it returns fewer than `limit`
    figures, those are ALL of them."""
    m = len(chart.edges)
    order = sorted(range(m), key=lambda k: (min(chart.edges[k]), max(chart.edges[k])))
    rem = [len(chart.inc[v]) for v in range(chart.n)]
    degree = [0] * chart.n
    found = []
    need = chart.need

    def feasible(v):
        return v not in need or (degree[v] <= need[v] and degree[v] + rem[v] >= need[v])

    def walk(t, chosen, blocked):
        if len(found) >= limit:
            return
        if t == m:
            if chosen and all(degree[v] == need[v] for v in need) and _components(chart, chosen) == 1:
                found.append(frozenset(chosen))
            return
        k = order[t]
        i, j = chart.edges[k]
        rem[i] -= 1
        rem[j] -= 1
        if not (blocked >> k & 1) and k not in chart.never:               # draw it
            degree[i] += 1
            degree[j] += 1
            if feasible(i) and feasible(j):
                chosen.append(k)
                walk(t + 1, chosen, blocked | chart.conflict[k])
                chosen.pop()
            degree[i] -= 1
            degree[j] -= 1
        if k not in chart.must and feasible(i) and feasible(j):                # leave it out
            walk(t + 1, chosen, blocked)
        rem[i] += 1
        rem[j] += 1

    walk(0, [], 0)
    return found


def count_solutions(chart, limit=2):
    return len(solutions(chart, limit))


def count_by_stars(chart, limit=2):
    """A second, independent counter: star by star, choose which lines go from this star to LATER stars (the lines to earlier
    stars were decided already), so every number is settled the moment its star is passed. Crossings are tested line against line
    with `edges_conflict` directly (no bit masks), and the whole figure is judged by `analyse`. Shares no search code with `solutions`."""
    later = [[k for k in chart.inc[v] if max(chart.edges[k]) > v and min(chart.edges[k]) == v] for v in range(chart.n)]
    count = [0]

    def clash(k, chosen):
        return any(edges_conflict(chart.pts, chart.edges[k], chart.edges[c]) for c in chosen)

    def go(v, chosen, degree):
        if count[0] >= limit:
            return
        if v == chart.n:
            if chosen and analyse(chart, chosen)["valid"]:
                count[0] += 1
            return
        options = later[v]
        for size in range(len(options) + 1):
            if v in chart.need and degree[v] + size != chart.need[v]:
                continue
            for pick in itertools.combinations(options, size):
                if any(k in chart.never for k in pick) or any(k in chart.must and k not in pick for k in options):
                    continue
                trial = list(chosen)
                ok = True
                for k in pick:
                    if clash(k, trial):
                        ok = False
                        break
                    trial.append(k)
                if not ok:
                    continue
                deg2 = list(degree)
                for k in pick:
                    deg2[chart.edges[k][1]] += 1
                go(v + 1, trial, deg2)

    go(0, [], [0] * chart.n)
    return count[0]


# ---- line logic ------------------------------------------------------------------------------------------------------------
IN, OUT = 1, 0

def _stars_needing(chart):
    return [v for v, need in chart.need.items() if need >= 1]


def _groups(chart, state, extra=None):
    """Pieces made by the lines that are IN (plus `extra`): list of (set of stars, set of lines)."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    lines = [k for k, val in state.items() if val == IN] + ([extra] if extra is not None else [])
    for k in lines:
        i, j = chart.edges[k]
        parent[find(i)] = find(j)
    pieces = {}
    for k in lines:
        root = find(chart.edges[k][0])
        stars, ls = pieces.setdefault(root, (set(), set()))
        stars.update(chart.edges[k])
        ls.add(k)
    return list(pieces.values())


def _closed(chart, state, stars, lines, extra=None):
    """A piece is closed when every star in it has a number and exactly that many lines: it can never grow."""
    count = {v: 0 for v in stars}
    for k in lines:
        for v in chart.edges[k]:
            count[v] += 1
    return all(v in chart.need and count[v] == chart.need[v] for v in stars)


def _needs_elsewhere(chart, stars, pieces):
    others = [v for v in _stars_needing(chart) if v not in stars]
    return bool(others) or len(pieces) > 1



def _required(chart, state):
    """Stars the figure must reach: every star with a number of 1 or more, and every star on a line that is IN."""
    req = set(_stars_needing(chart))
    for k, val in state.items():
        if val == IN:
            req.update(chart.edges[k])
    return req


def _reach(chart, state, skip=None):
    """Stars grouped into pieces by every line that is not OUT (and is not `skip`): a list of sets."""
    parent = list(range(chart.n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for k, (i, j) in enumerate(chart.edges):
        if k != skip and state.get(k) != OUT:
            parent[find(i)] = find(j)
    groups = {}
    for v in range(chart.n):
        groups.setdefault(find(v), set()).add(v)
    return list(groups.values())


def _connected_possible(chart, state):
    """False when the stars the figure must reach can no longer be joined by the lines still allowed."""
    req = _required(chart, state)
    return sum(1 for g in _reach(chart, state) if g & req) <= 1


def _bridge_rule(chart, state, trail_out):
    """bridge: if leaving a line out would cut the stars the figure must reach into two pieces, the line is IN."""
    changed = False
    req = _required(chart, state)
    for k in range(len(chart.edges)):
        if k in state:
            continue
        if sum(1 for g in _reach(chart, state, skip=k) if g & req) > 1:
            state[k] = IN
            trail_out.append(("bridge", k, IN, None))
            changed = True
            req = _required(chart, state)
    return changed


def _no_early_close(chart, state, trail_out):
    """Contradiction check: a finished piece (every star in it has its number) while there are numbered stars or other pieces outside it."""
    pieces = _groups(chart, state)
    for stars, lines in pieces:
        if _closed(chart, state, stars, lines) and _needs_elsewhere(chart, stars, pieces):
            return False
    return True


def _close_rule(chart, state, trail_out):
    """close: a line that would finish a piece while stars that need lines remain outside it is OUT."""
    changed = False
    for k in range(len(chart.edges)):
        if k in state:
            continue
        pieces = _groups(chart, state, extra=k)
        for stars, lines in pieces:
            if k in lines and _closed(chart, state, stars, lines) and _needs_elsewhere(chart, stars, pieces):
                state[k] = OUT
                trail_out.append(("close", k, OUT, None))
                changed = True
                break
    return changed



def propagate(chart, known=None, lookahead=False):
    """What can be worked out WITHOUT guessing. `known` is {line index: IN or OUT} to start from (the must lines are IN and the
    never lines OUT already). Rules, applied until nothing changes:
      full     a numbered star that already has its number of lines: every other line at it is OUT
      forced   a numbered star whose number needs every line still open at it: they are all IN
      cross    a line that would cross or touch a line that is IN is OUT
      bridge   a line that is the only way to join stars the figure must reach is IN
      close    a line that would finish a piece of the figure (every star in it has its number) while numbered stars remain outside it is OUT
    With lookahead=True a fourth step is allowed: try a line, and if that leads straight to a broken number or a crossing, the line is
    the other way round ("what if" reasoning, one step deep).
    Returns (known, trail) where trail lists (rule, line, value) in the order they were worked out; a contradiction returns (None, trail)."""
    known = dict(known or {})
    for k in chart.must:
        known[k] = IN
    for k in chart.never:
        known[k] = OUT
    trail = []

    def settle(state, trail_out):
        changed = True
        while changed:
            changed = False
            for v, need in sorted(chart.need.items()):
                have = [k for k in chart.inc[v] if state.get(k) == IN]
                free = [k for k in chart.inc[v] if k not in state]
                if len(have) > need or len(have) + len(free) < need:
                    return False
                if len(have) == need and free:
                    for k in free:
                        state[k] = OUT
                        trail_out.append(("full", k, OUT, v))
                    changed = True
                elif free and len(have) + len(free) == need:
                    for k in free:
                        state[k] = IN
                        trail_out.append(("forced", k, IN, v))
                    changed = True
            if not _no_early_close(chart, state, trail_out):
                return False
            if not _connected_possible(chart, state):
                return False
            if _close_rule(chart, state, trail_out):
                changed = True
            if _bridge_rule(chart, state, trail_out):
                changed = True
            ins = [k for k, val in state.items() if val == IN]
            for k in ins:
                for m in range(len(chart.edges)):
                    if chart.conflict[k] >> m & 1:
                        if state.get(m) == IN:
                            return False
                        if m not in state:
                            state[m] = OUT
                            trail_out.append(("cross", m, OUT, k))
                            changed = True
        return True

    if not settle(known, trail):
        return None, trail
    while lookahead:
        progress = False
        for k in range(len(chart.edges)):
            if k in known:
                continue
            for guess in (IN, OUT):
                trial = dict(known)
                trial[k] = guess
                if not settle(trial, []):
                    known[k] = 1 - guess
                    trail.append(("what-if", k, 1 - guess, None))
                    if not settle(known, trail):
                        return None, trail
                    progress = True
                    break
        if not progress:
            break
    return known, trail


def solved_by_logic(chart, lookahead=False):
    """Does line logic alone (see `propagate`) fix every line that matters? Returns the set of IN lines if the chart is finished
    that way (valid figure; lines still undecided count as left out), else None."""
    known, _trail = propagate(chart, lookahead=lookahead)
    if known is None:
        return None
    chosen = frozenset(k for k, val in known.items() if val == IN)
    return chosen if is_valid(chart, chosen) else None
