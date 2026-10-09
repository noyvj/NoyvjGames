"""Hull Repair -- board finder (a development tool; the page never loads it, and the boards it finds are frozen into the
boards_*.py data files, so nothing in the game is random).

`make(params, seed)` grows a random tiling of a board with lines (using `random.Random(seed)`, so a seed always gives the
same board), places valves and mixers on it, then splits lines (adds ports) until the solver proves the restored layout is
unique. It returns a board spec dict (id left blank) or None. Run it as a script to look for boards:

    python3 tools/gen.py 6 6 --holes 0,0 5,5 --bridges 2,2 --valves 2 --mixers 0 --seeds 1-40
"""

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import rules  # noqa: E402
import solver  # noqa: E402

rules.LINES = "ABCDEFGHIJKLMNOP"         # while searching, a board may briefly need more lines than the game allows
MAX_GAME_LINES = 8

D = rules.DIRS
ARROW_CHARS = "^>v<"


class Tiling:
    def __init__(self, rng, w, h, holes, bridges):
        self.rng, self.w, self.h = rng, w, h
        self.holes, self.bridges = set(holes), set(bridges)
        self.play = {(x, y) for x in range(w) for y in range(h)} - self.holes
        self.paths = []
        self.occ = {}
        self.lanes = {}

    def chain(self, cell, d, pid, visited):
        cells = []
        cur = cell
        while True:
            n = rules.add(cur, D[d])
            if n not in self.play or n in visited:
                return None
            if n in self.bridges:
                if (n, d & 1) in self.lanes:
                    return None
                cells.append(n)
                visited = visited | {n}
                cur = n
                continue
            if n in self.occ:
                return None
            cells.append(n)
            return cells

    def mark(self, pid, cells, d):
        for c in cells:
            if c in self.bridges:
                self.lanes[(c, d & 1)] = pid
            else:
                self.occ[c] = pid

    def free_neighbours(self, cell):
        count = 0
        for d in range(4):
            n = rules.add(cell, D[d])
            if n in self.play and n not in self.occ and n not in self.bridges:
                count += 1
        return count

    def grow(self, pid, maxlen):
        path = self.paths[pid]
        while len(path) < maxlen:
            front = self.rng.random() < 0.5
            options = []
            for end in ((0, -1) if front else (-1, 0)):
                cell = path[end]
                dirs = list(range(4))
                self.rng.shuffle(dirs)
                for d in dirs:
                    got = self.chain(cell, d, pid, set(path))
                    if got is not None:
                        options.append((end, d, got))
                if options:
                    break
            if not options:
                return
            end, d, got = self.rng.choice(options)
            self.mark(pid, got, d)
            if end == 0:
                path[0:0] = list(reversed(got))
            else:
                path.extend(got)

    def build(self, maxlen):
        """Cover every cell: bridges first (one path each way), then the cell with the fewest free neighbours."""
        for b in sorted(self.bridges):
            for axis in self.rng.sample((0, 1), 2):
                d = (1 + 2 * 0) if axis else 0                  # right for horizontal, up for vertical
                back, fwd = rules.add(b, D[(d + 2) % 4]), rules.add(b, D[d])
                if back not in self.play or fwd not in self.play or back in self.bridges or fwd in self.bridges:
                    return False
                if (b, axis) in self.lanes or back in self.occ or fwd in self.occ:
                    return False
                pid = len(self.paths)
                self.paths.append([back, b, fwd])
                self.occ[back] = self.occ[fwd] = pid
                self.lanes[(b, axis)] = pid
                self.grow(pid, self.rng.randint(max(4, maxlen // 2), maxlen))
        while True:
            free = [c for c in self.play if c not in self.occ and c not in self.bridges]
            if not free:
                break
            low = min(self.free_neighbours(c) for c in free)
            start = self.rng.choice(sorted(c for c in free if self.free_neighbours(c) == low))
            pid = len(self.paths)
            self.paths.append([start])
            self.occ[start] = pid
            self.grow(pid, self.rng.randint(max(3, maxlen // 2), maxlen))
            if len(self.paths[pid]) < 2:
                return False
        return all(any((b, a) in self.lanes for a in (0, 1)) for b in self.bridges)


def lines_to_spec(w, h, holes, bridges, valves, lines):
    """lines: list of (cells source-first, mixer cell or None). Letters go to the lines in reading order of their source."""
    order = sorted(range(len(lines)), key=lambda i: (lines[i][0][0][1], lines[i][0][0][0]))
    rows = [["."] * w for _ in range(h)]
    for x, y in holes:
        rows[y][x] = "#"
    for x, y in bridges:
        rows[y][x] = "="
    for (x, y), d in valves.items():
        rows[y][x] = ARROW_CHARS[d]
    mixers = {}
    sol = {}
    mixer_cells = sorted({m for _c, m in lines if m is not None}, key=lambda p: (p[1], p[0]))
    for k, m in enumerate(mixer_cells, start=1):
        rows[m[1]][m[0]] = str(k)
    for n, i in enumerate(order):
        letter = rules.LINES[n]
        cells, mixer = lines[i]
        rows[cells[0][1]][cells[0][0]] = letter
        if mixer is None:
            rows[cells[-1][1]][cells[-1][0]] = letter.lower()
        else:
            mixers.setdefault(str(mixer_cells.index(mixer) + 1), []).append(letter)
        sol[letter] = list(cells)
    spec = {"id": "", "name": "", "rows": ["".join(r) for r in rows]}
    if mixers:
        spec["mixers"] = {k: "".join(v) for k, v in sorted(mixers.items())}
    spec["sol"] = rules.encode(sol)
    return spec


def make(params, seed, node_limit=40000):
    """params: w, h, holes, bridges, valves (count), mixers (count), maxlen, max_lines."""
    rng = random.Random(seed)
    w, h = params["w"], params["h"]
    holes, bridges = params.get("holes", ()), params.get("bridges", ())
    cells = w * h - len(holes)
    maxlen = params.get("maxlen", max(6, cells // 2))
    for _attempt in range(200):
        t = Tiling(rng, w, h, holes, bridges)
        if t.build(maxlen):
            break
    else:
        return None
    paths = [list(p) for p in t.paths]
    for p in paths:
        if rng.random() < 0.5:
            p.reverse()
    lines = [(p, None) for p in paths]
    # mixers: cut a long line at an interior cell; both halves end on that cell
    made = 0
    order = list(range(len(lines)))
    rng.shuffle(order)
    replaced = {}
    for i in order:
        if made >= params.get("mixers", 0):
            break
        p = lines[i][0]
        spots = [k for k in range(2, len(p) - 2) if p[k] not in t.bridges]
        if len(p) < 6 or not spots:
            continue
        k = rng.choice(spots)
        m = p[k]
        replaced[i] = [(p[:k] + [m], m), (list(reversed(p[k + 1:])) + [m], m)]
        made += 1
    if made < params.get("mixers", 0):
        return None
    new = []
    for i, item in enumerate(lines):
        new.extend(replaced.get(i, [item]))
    lines = new
    # valves: straight interior cells, arrow along the travel direction of the source-first line
    valves = {}
    candidates = []
    for p, _m in lines:
        for i in range(1, len(p) - 1):
            if p[i] not in t.bridges and rules.sub(p[i], p[i - 1]) == rules.sub(p[i + 1], p[i]):
                candidates.append((p[i], rules.dir_index(rules.sub(p[i], p[i - 1]))))
    rng.shuffle(candidates)
    for cell, d in candidates:
        if len(valves) >= params.get("valves", 0):
            break
        valves[cell] = d
    max_lines = params.get("max_lines", 8)
    cap = 14
    for _round in range(40):
        if len(lines) > cap:
            return None
        spec = lines_to_spec(w, h, holes, bridges, valves, lines)
        board = rules.Board(dict(spec, id="x"))
        try:
            sols = solver.solve(board, 2, node_limit=node_limit)
        except RuntimeError:
            return None
        if len(sols) == 1:
            break
        if not sols:
            return None
        lines = split_line(rng, board, lines, sols, t.bridges, valves)
        if lines is None:
            return None
    else:
        return None
    lines = merge_lines(rng, w, h, holes, bridges, valves, lines, node_limit)
    if len(lines) > max_lines or len(lines) < params.get("min_lines", 2):
        return None
    spec = lines_to_spec(w, h, holes, bridges, valves, lines)
    board = rules.Board(dict(spec, id="x"))
    sols = solver.solve(board, 2, node_limit=node_limit)
    if len(sols) != 1 or rules.check_layout(board, sols[0]):
        return None
    spec["sol"] = rules.encode(sols[0])
    spec["_lines"] = len(lines)
    spec["_valves"] = sum(1 for v in loadbearing_valves(w, h, holes, bridges, valves, lines, node_limit))
    return spec


def merge_lines(rng, w, h, holes, bridges, valves, lines, node_limit):
    """Join two lines end to start (no reversing, so valve arrows stay right) whenever the board stays unique."""
    changed = True
    while changed:
        changed = False
        pairs = [(i, j) for i in range(len(lines)) for j in range(len(lines))
                 if i != j and lines[i][1] is None and lines[j][1] is None and rules.adjacent(lines[i][0][-1], lines[j][0][0])]
        rng.shuffle(pairs)
        for i, j in pairs:
            merged = lines[i][0] + lines[j][0]
            trial = [x for k, x in enumerate(lines) if k not in (i, j)] + [(merged, None)]
            spec = lines_to_spec(w, h, holes, bridges, valves, trial)
            try:
                board = rules.Board(dict(spec, id="x"))
                sols = solver.solve(board, 2, node_limit=node_limit)
            except (RuntimeError, ValueError):
                continue
            if len(sols) == 1:
                lines = trial
                changed = True
                break
    return lines


def loadbearing_valves(w, h, holes, bridges, valves, lines, node_limit):
    """The valves whose removal would make the board's restored layout ambiguous."""
    out = []
    for cell in valves:
        rest = {k: v for k, v in valves.items() if k != cell}
        board = rules.Board(dict(lines_to_spec(w, h, holes, bridges, rest, lines), id="x"))
        try:
            if len(solver.solve(board, 2, node_limit=node_limit)) > 1:
                out.append(cell)
        except RuntimeError:
            out.append(cell)
    return out


def split_line(rng, board, lines, sols, bridges, valves):
    """Cut one line in two (two new ports), preferring a cut where the two found layouts disagree."""
    sol_a, sol_b = sols
    owner_a = {c: letter for letter, p in sol_a.items() for c in p}
    owner_b = {c: letter for letter, p in sol_b.items() for c in p}
    diff = {c for c in owner_a if owner_a.get(c) != owner_b.get(c)}
    options = []
    preferred = []
    for li, (cells, mixer) in enumerate(lines):
        if mixer is not None:
            continue
        for i in range(1, len(cells) - 2):         # keep both halves at least two cells
            a, b = cells[i], cells[i + 1]
            if a in bridges or b in bridges or a in valves or b in valves:
                continue
            options.append((li, i))
            if a in diff or b in diff:
                preferred.append((li, i))
    pool = preferred or options
    if not pool:
        return None
    li, i = rng.choice(pool)
    cells, _m = lines[li]
    out = list(lines)
    out[li:li + 1] = [(cells[:i + 1], None), (cells[i + 1:], None)]
    return out


def parse_cells(items):
    return tuple(tuple(int(v) for v in item.split(",")) for item in items or ())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("w", type=int)
    ap.add_argument("h", type=int)
    ap.add_argument("--holes", nargs="*")
    ap.add_argument("--bridges", nargs="*")
    ap.add_argument("--valves", type=int, default=0)
    ap.add_argument("--mixers", type=int, default=0)
    ap.add_argument("--maxlen", type=int, default=0)
    ap.add_argument("--max-lines", type=int, default=8)
    ap.add_argument("--seeds", default="1-20")
    args = ap.parse_args(argv)
    lo, hi = (int(v) for v in args.seeds.split("-"))
    params = {"w": args.w, "h": args.h, "holes": parse_cells(args.holes), "bridges": parse_cells(args.bridges),
              "valves": args.valves, "mixers": args.mixers, "max_lines": args.max_lines}
    if args.maxlen:
        params["maxlen"] = args.maxlen
    for seed in range(lo, hi + 1):
        spec = make(params, seed)
        if spec is None:
            print("seed %d: no board" % seed)
            continue
        print("seed %d: %d lines" % (seed, spec["_lines"]))
        print("\n".join(spec["rows"]))
        print(spec.get("mixers", ""), spec["sol"])


if __name__ == "__main__":
    main()
