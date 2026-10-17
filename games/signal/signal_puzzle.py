"""The Board, the constraint solver that proves each puzzle solvable, the seeded puzzle generator and its par, daily and practice seeds, and practice codes."""

import random
import re

import signal_runstate as runstate
from signal_rules import (
    CODE_ALPHABET, CODE_LENGTH, LETTER_TO_PRESET, MAX_ATTEMPTS, PAR_MARGIN, PRESETS, Rng, SEED_VERSION,
    SOLUTION_SAMPLE, fnv1a32,
)


# --------------------------------------------------------------------------
# Board geometry and the constraint solver


class Board:
    """Distance/weight tables for one preset (built once, cached)."""

    def __init__(self, key):
        p = PRESETS[key]
        self.key = key
        self.n = p["size"]
        self.k = p["k"]
        self.radius = p["radius"]
        self.spacing = p["spacing"]
        n = self.n
        total = n * n
        self.dist = [[abs(a // n - b // n) + abs(a % n - b % n) for b in range(total)] for a in range(total)]
        self.weight = [[max(0, self.radius - d) for d in row] for row in self.dist]
        # Transmitters never sit on the outer ring (it keeps readings informative).
        self.cells = [r * n + c for r in range(1, n - 1) for c in range(1, n - 1)]
        self.interior = set(self.cells)


_BOARDS = {}


def board_for(key):
    if key not in _BOARDS:
        _BOARDS[key] = Board(key)
    return _BOARDS[key]


def reading_at(board, transmitters, cell):
    weights = board.weight[cell]
    return sum(weights[t] for t in transmitters)


def solve(board, pings, limit=2, forced=None, node_cap=None):
    """Every transmitter set consistent with `pings`, up to `limit` of them.

    pings: list of (cell, reading). forced: a cell that must be a transmitter.
    Returns (solutions, complete): solutions is a list of sorted tuples of
    cells; complete is False only if node_cap stopped the search early.

    A constraint search, not a brute-force scan: any tile a reading rules out
    is dropped up front (a zero reading clears its whole neighbourhood), then
    it repeatedly branches on the most constrained ping still owed signal.
    Branching is "include cell i, exclude cells 1..i-1" over the cells that
    could supply that ping, which partitions the solutions so each set is
    found exactly once.
    """
    n_pings = len(pings)
    dist = board.dist
    spacing = board.spacing
    tables = [board.weight[cell] for cell, _ in pings]
    start_res = [reading for _, reading in pings]
    out = []
    nodes = [0]

    class _Stop(Exception):
        pass

    def fits(cell, res):
        for i in range(n_pings):
            if tables[i][cell] > res[i]:
                return False
        return True

    def free_fill(cands, m, chosen):
        def go(begin, left, current):
            if len(out) >= limit:
                return
            if left == 0:
                out.append(tuple(sorted(chosen + current)))
                return
            for j in range(begin, len(cands)):
                cell = cands[j]
                ok = True
                for other in current:
                    if dist[cell][other] < spacing:
                        ok = False
                        break
                if ok:
                    go(j + 1, left - 1, current + [cell])
        go(0, m, [])

    def rec(cands, res, m, chosen):
        nodes[0] += 1
        if node_cap is not None and nodes[0] > node_cap:
            raise _Stop()
        if len(out) >= limit:
            return
        if m == 0:
            if not any(res):
                out.append(tuple(sorted(chosen)))
            return
        if len(cands) < m:
            return
        best_i, best_cover = -1, None
        for i in range(n_pings):
            if res[i] > 0:
                table = tables[i]
                cover = [c for c in cands if table[c] > 0]
                if not cover:
                    return
                top = sorted((table[c] for c in cover), reverse=True)[:m]
                if sum(top) < res[i]:
                    return
                if best_cover is None or len(cover) < len(best_cover):
                    best_i, best_cover = i, cover
        if best_i < 0:
            free_fill(cands, m, chosen)
            return
        excluded = set()
        for cell in best_cover:
            if len(out) >= limit:
                return
            new_res = [res[i] - tables[i][cell] for i in range(n_pings)]
            row = dist[cell]
            new_cands = [
                x for x in cands
                if x != cell and x not in excluded and row[x] >= spacing and fits(x, new_res)
            ]
            rec(new_cands, new_res, m - 1, chosen + [cell])
            excluded.add(cell)

    cands0 = [c for c in board.cells if fits(c, start_res)]
    try:
        if forced is not None:
            if forced not in cands0:
                return [], True
            new_res = [start_res[i] - tables[i][forced] for i in range(n_pings)]
            row = dist[forced]
            new_cands = [
                x for x in cands0
                if x != forced and row[x] >= spacing and fits(x, new_res)
            ]
            rec(new_cands, new_res, board.k - 1, [forced])
        else:
            rec(cands0, list(start_res), board.k, [])
    except _Stop:
        return out, False
    return out, True


def possible_cells(board, pings, node_cap=3000):
    """Tiles that could still hold a transmitter given the readings so far.

    A tile survives if some consistent set contains it. If the per-tile search
    runs out of budget the tile is kept (an over-approximation, never a false
    'ruled out')."""
    n_pings = len(pings)
    tables = [board.weight[cell] for cell, _ in pings]
    result = []
    for cell in board.cells:
        if any(tables[i][cell] > pings[i][1] for i in range(n_pings)):
            continue
        sols, complete = solve(board, pings, limit=1, forced=cell, node_cap=node_cap)
        if sols or not complete:
            result.append(cell)
    return result


# --------------------------------------------------------------------------
# Puzzle generation


class Puzzle:
    __slots__ = ("mode", "seed", "transmitters", "par", "reference", "attempts")

    def __init__(self, mode, seed, transmitters, par, reference, attempts):
        self.mode = mode
        self.seed = seed
        self.transmitters = transmitters
        self.par = par
        self.reference = reference
        self.attempts = attempts


def _place(board, rng):
    """Random spaced transmitters on the interior, by rejection sampling."""
    while True:
        chosen = []
        tries = 0
        while len(chosen) < board.k and tries < 400:
            tries += 1
            cell = board.cells[rng.below(len(board.cells))]
            if all(board.dist[cell][other] >= board.spacing for other in chosen):
                chosen.append(cell)
        if len(chosen) == board.k:
            return tuple(sorted(chosen))


def adaptive_par(board, transmitters, max_pings, sample=SOLUTION_SAMPLE):
    """(par, reference_pings) for a placement, or (None, pings) past max_pings.

    par = how many pings a deterministic greedy solver needs before exactly
    one transmitter set is left. Its opening ping is the centre; each later
    ping is the untried tile that best splits a sample of the sets still
    consistent (lowest sum of squared class sizes, ties to the lowest tile).
    It is an upper bound on the true optimum, which is what "par" means."""
    total = board.n * board.n
    weight = board.weight
    pings = []
    reference = []
    used = set()
    for _ in range(max_pings):
        if pings:
            sols, _complete = solve(board, pings, limit=sample)
            if len(sols) == 1:
                return len(pings), reference
            best = None
            for cell in range(total):
                if cell in used:
                    continue
                row = weight[cell]
                counts = {}
                for sol in sols:
                    value = sum(row[t] for t in sol)
                    counts[value] = counts.get(value, 0) + 1
                score = sum(v * v for v in counts.values())
                if best is None or score < best[0]:
                    best = (score, cell)
            cell = best[1]
        else:
            cell = (board.n // 2) * board.n + board.n // 2
        used.add(cell)
        reference.append(cell)
        pings.append((cell, reading_at(board, transmitters, cell)))
    sols, _complete = solve(board, pings, limit=2)
    if len(sols) == 1:
        return len(pings), reference
    return None, reference


def generate(mode, seed_text):
    """The puzzle for a seed: a pure function of (mode, seed_text)."""
    preset = PRESETS[mode]
    board = board_for(mode)
    rng = Rng(fnv1a32(seed_text))
    limit = preset["budget"] - PAR_MARGIN
    for attempt in range(1, MAX_ATTEMPTS + 1):
        transmitters = _place(board, rng)
        par, reference = adaptive_par(board, transmitters, limit, preset.get("sample", SOLUTION_SAMPLE))
        if par is not None:
            return Puzzle(mode, seed_text, transmitters, par, tuple(reference), attempt)
    raise RuntimeError("no solvable puzzle for seed %r" % seed_text)


def daily_seed(date_text, mode):
    return "signal:%s:%s:%s" % (SEED_VERSION, date_text, mode)


def practice_seed(mode, code):
    return "signal:%s:practice:%s:%s" % (SEED_VERSION, mode, code)


_PUZZLE_CACHE = {}


def puzzle_for_seed(mode, seed_text):
    key = (mode, seed_text)
    if key not in _PUZZLE_CACHE:
        if len(_PUZZLE_CACHE) >= 48:
            _PUZZLE_CACHE.pop(next(iter(_PUZZLE_CACHE)))
        _PUZZLE_CACHE[key] = generate(mode, seed_text)
    return _PUZZLE_CACHE[key]


def daily_puzzle(date_text, mode):
    return puzzle_for_seed(mode, daily_seed(date_text, mode))


# Practice codes: "P-" + preset letter + 5 Crockford base32 characters. The
# code carries the preset so a shared code is enough to reproduce a puzzle.

runstate._rand = random.Random()


def set_random_source(source):
    """Tests inject a seeded random.Random; None restores an OS-seeded one."""
    runstate._rand = source or random.Random()


def new_practice_code(mode):
    body = "".join(CODE_ALPHABET[runstate._rand.randrange(len(CODE_ALPHABET))] for _ in range(CODE_LENGTH))
    return "P-%s%s" % (PRESETS[mode]["letter"], body)


def parse_practice_code(text):
    """(mode, canonical_code) for a practice code, else None. Forgiving about
    case, spaces, a missing 'P-', and Crockford's O/I/L look-alikes."""
    if not isinstance(text, str):
        return None
    cleaned = re.sub(r"[\s\-]", "", text.upper())
    if cleaned.startswith("P"):
        cleaned = cleaned[1:]
    if len(cleaned) != 1 + CODE_LENGTH:
        return None
    letter, body = cleaned[0], cleaned[1:]
    mode = LETTER_TO_PRESET.get(letter)
    if mode is None:
        return None
    body = body.replace("O", "0").replace("I", "1").replace("L", "1")
    if any(ch not in CODE_ALPHABET for ch in body):
        return None
    return mode, "P-%s%s" % (letter, body)
