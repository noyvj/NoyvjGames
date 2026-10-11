"""Mirror Lab -- the placement solver (a dev tool; the page never loads it).

`solve(board, tray)` finds EVERY canonical solution of a bench. A solution is a set of placements, each (row, col, piece, state),
that lights every needed sensor and no decoy using no more of each piece than the tray holds. "Canonical" means every placed
piece is actually reached by a beam: a piece left where no light ever goes changes nothing, so it is not counted (the plan's
"modulo unused pieces").

The search is pruned along the beam: it traces the current partial layout with every undecided slot held back as a stop, takes the
first slot a beam arrives at (row-major order), and branches on it -- leave it empty, or any piece in any state still in stock.
Slots no beam ever reaches are never decided, so they cost nothing. Once a slot is decided it stays reached: the beams that arrive
at it pass only through cells decided before it.

Run `python3 tools/solve.py [chapter]` to print every bench's counts.
"""

import sys
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
if str(GAME_DIR) not in sys.path:
    sys.path.insert(0, str(GAME_DIR))

import optics  # noqa: E402


def solve(board, tray, limit=None):
    """Every canonical solution, each a tuple of (row, col, piece, state) sorted by cell. `limit` stops early (the result is then partial)."""
    solutions = []
    decided = {}                  # slot -> None (left empty) or (piece, state)
    stock = {piece: n for piece, n in tray.items() if n > 0}
    order = [piece for piece in optics.PIECES if piece in stock]

    def placed():
        return {cell: value for cell, value in decided.items() if value is not None}

    def search():
        if limit is not None and len(solutions) >= limit:
            return
        halt = board.slots - set(decided)
        tr = optics.trace(board, placed(), halt)
        if not tr.pending:
            if tr.ok:
                solutions.append(tuple(sorted((r, c, p, s) for (r, c), (p, s) in placed().items())))
            return
        cell = min(tr.pending)
        decided[cell] = None
        search()
        for piece in order:
            if stock[piece] <= 0:
                continue
            for state in range(optics.PIECE_STATES[piece]):
                stock[piece] -= 1
                decided[cell] = (piece, state)
                search()
                stock[piece] += 1
        del decided[cell]

    search()
    solutions.sort(key=lambda s: (len(s), s))
    return solutions


def layout_of(solution):
    return {(r, c): (p, s) for r, c, p, s in solution}


def report(bench):
    sols = solve(optics.Board(bench["rows"]), bench["tray"])
    return {"count": len(sols), "fewest": min((len(s) for s in sols), default=None), "first": sols[0] if sols else None}


if __name__ == "__main__":
    import benches
    for b in benches.ALL_BENCHES:
        if len(sys.argv) > 1 and b.chapter != int(sys.argv[1]):
            continue
        info = report({"rows": b.rows, "tray": b.tray})
        print(b.id, b.name, info["count"], info["fewest"])
