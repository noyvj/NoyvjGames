"""Hull Repair -- exhaustive solver (a development and test tool; the page never loads it).

`solve(board, limit=2)` finds every restored layout of a board (every line joined, every open cell covered), stopping once
`limit` have been found, so `len(solve(b))` is 1 for a board with exactly one restored layout. `solve(board, fill=False)`
looks for layouts that only join the lines. Lines are searched source-first one macro-move at a time (entering a bridge
or valve forces the straight cells beyond it into the same move), the line with the fewest moves goes first, and a branch
dies as soon as an open cell cannot get two neighbours or a line cannot reach its sink. Deterministic: no randomness.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import rules  # noqa: E402

HOLE, OPEN, BRIDGE, VALVE, PORT, MIXER = range(6)


class Solver:
    def __init__(self, board, fill=True, node_limit=0):
        self.board = board
        self.fill = fill
        self.node_limit = node_limit
        self.w, self.h = board.w, board.h
        n = self.w * self.h
        self.n = n
        self.kind = [HOLE] * n
        self.arrow = [-1] * n
        self.nb = [[-1] * 4 for _ in range(n)]
        for y in range(self.h):
            for x in range(self.w):
                i = y * self.w + x
                k = board.kind((x, y))
                self.kind[i] = {"hole": HOLE, "open": OPEN, "bridge": BRIDGE, "valve": VALVE, "port": PORT, "mixer": MIXER}[k]
                if (x, y) in board.valves:
                    self.arrow[i] = board.valves[(x, y)]
                if k == "hole":
                    continue
                for d, (dx, dy) in enumerate(rules.DIRS):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.w and 0 <= ny < self.h and (nx, ny) in board.playable:
                        self.nb[i][d] = ny * self.w + nx
        self.lines = board.lines
        self.src = [self._idx(board.src[c]) for c in self.lines]
        self.dst = [self._idx(board.dst[c]) for c in self.lines]
        self.occ = [0] * n
        self.occb = [[0] * n, [0] * n]
        self.paths = [[s] for s in self.src]
        self.complete = [False] * len(self.lines)
        self.need_total = len(board.need)
        self.cov = 0
        self.nodes = 0
        self.found = []
        self.limit = 2
        self.need_cells = [self._idx(c) for c in sorted(board.need, key=lambda p: (p[1], p[0]))]

    def _idx(self, cell):
        return cell[1] * self.w + cell[0]

    # ---- moves -----------------------------------------------------------------------------------------------------
    def macro(self, ci, head, d):
        """The cells one move in direction d takes the line through (bridges and valves force straight cells), and whether
        it ends on the line's sink. None when the move is illegal."""
        cells = []
        cur = head
        while True:
            m = self.nb[cur][d]
            if m < 0:
                return None
            k = self.kind[m]
            if k == OPEN:
                if self.occ[m]:
                    return None
                cells.append(m)
                return cells, False
            if k == PORT or k == MIXER:
                if m == self.dst[ci]:
                    cells.append(m)
                    return cells, True
                return None
            if k == BRIDGE:
                if self.occb[d & 1][m]:
                    return None
                cells.append(m)
                cur = m
                continue
            if k == VALVE:
                if d != self.arrow[m] or self.occ[m]:
                    return None
                cells.append(m)
                cur = m
                continue
            return None

    def moves(self, ci):
        head = self.paths[ci][-1]
        out = []
        for d in range(4):
            got = self.macro(ci, head, d)
            if got is not None:
                out.append((d, got[0], got[1]))
        return out

    def apply(self, ci, d, cells, reaches):
        path = self.paths[ci]
        lane = d & 1
        for m in (cells[:-1] if reaches else cells):
            k = self.kind[m]
            if k == BRIDGE:
                if not self.occb[0][m] and not self.occb[1][m]:
                    self.cov += 1
                self.occb[lane][m] = ci + 1
            else:
                self.occ[m] = ci + 1
                self.cov += 1
        path.extend(cells)
        if reaches:
            self.complete[ci] = True

    def undo(self, ci, d, cells, reaches):
        path = self.paths[ci]
        lane = d & 1
        del path[len(path) - len(cells):]
        if reaches:
            self.complete[ci] = False
        for m in (cells[:-1] if reaches else cells):
            if self.kind[m] == BRIDGE:
                self.occb[lane][m] = 0
                if not self.occb[0][m] and not self.occb[1][m]:
                    self.cov -= 1
            else:
                self.occ[m] = 0
                self.cov -= 1

    # ---- pruning ---------------------------------------------------------------------------------------------------
    def dead(self):
        """True when the position cannot be finished: some uncovered cell cannot be given two path neighbours."""
        heads = set()
        sinks = set()
        for ci in range(len(self.lines)):
            if not self.complete[ci]:
                heads.add(self.paths[ci][-1])
                sinks.add(self.dst[ci])
        kind, occ, arrow = self.kind, self.occ, self.arrow
        for cell in self.need_cells:
            k = kind[cell]
            if k == BRIDGE:
                continue
            if k == VALVE:
                if occ[cell]:
                    continue
                axis = arrow[cell] & 1
                ok = 0
                for d in range(4):
                    if (d & 1) != axis:
                        continue
                    if self._reachable_from(cell, d, heads, sinks):
                        ok += 1
                if ok < 2:
                    return True
                continue
            if occ[cell]:
                continue
            count = 0
            for d in range(4):
                if self._reachable_from(cell, d, heads, sinks):
                    count += 1
            if count < 2:
                return True
        return False

    def _reachable_from(self, cell, d, heads, sinks):
        """Could a line join `cell` to its neighbour in direction d?"""
        m = self.nb[cell][d]
        if m < 0:
            return False
        k = self.kind[m]
        if k == OPEN:
            return not self.occ[m] or m in heads
        if k == VALVE:
            if self.occ[m]:
                return m in heads
            return (d & 1) == (self.arrow[m] & 1)
        if k == BRIDGE:
            return not self.occb[d & 1][m] or m in heads
        return m in heads or m in sinks

    def unreachable(self):
        """True when some unfinished line cannot get from its head to its sink through free cells."""
        for ci in range(len(self.lines)):
            if self.complete[ci]:
                continue
            start = self.paths[ci][-1]
            target = self.dst[ci]
            seen = {start}
            stack = [start]
            found = False
            while stack and not found:
                cur = stack.pop()
                for d in range(4):
                    m = self.nb[cur][d]
                    if m < 0 or m in seen:
                        continue
                    k = self.kind[m]
                    if m == target:
                        found = True
                        break
                    if k == OPEN or k == VALVE:
                        if self.occ[m]:
                            continue
                    elif k == BRIDGE:
                        if self.occb[d & 1][m]:
                            continue
                    else:
                        continue
                    seen.add(m)
                    stack.append(m)
            if not found:
                return True
        return False

    # ---- search ----------------------------------------------------------------------------------------------------
    def search(self):
        self.nodes += 1
        if self.node_limit and self.nodes > self.node_limit:
            raise RuntimeError("node limit")
        pending = [ci for ci in range(len(self.lines)) if not self.complete[ci]]
        if not pending:
            if not self.fill or self.cov == self.need_total:
                self.found.append({self.lines[ci]: [(m % self.w, m // self.w) for m in self.paths[ci]] for ci in range(len(self.lines))})
            return
        if self.fill and self.dead():
            return
        if self.unreachable():
            return
        best = None
        best_moves = None
        for ci in pending:
            mv = self.moves(ci)
            if not mv:
                return
            if best is None or len(mv) < len(best_moves):
                best, best_moves = ci, mv
                if len(mv) == 1:
                    break
        for d, cells, reaches in best_moves:
            self.apply(best, d, cells, reaches)
            self.search()
            self.undo(best, d, cells, reaches)
            if len(self.found) >= self.limit:
                return


def solve(board, limit=2, fill=True, node_limit=0):
    """Up to `limit` layouts (dict line -> source-first list of cells) that join every line (and, with fill, cover every
    open cell). With the default limit of 2 a length of 1 proves the layout is unique."""
    s = Solver(board, fill, node_limit)
    s.limit = limit
    s.search()
    return s.found


def count(board, limit=2, fill=True, node_limit=0):
    return len(solve(board, limit, fill, node_limit))
