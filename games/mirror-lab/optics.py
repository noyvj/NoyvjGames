"""Mirror Lab -- the ray tracer. Pure, deterministic and DOM-free: the same board and the same pieces always give the same beams.

THE BENCH is a grid. A beam moves one cell at a time along a compass direction (0 north, 1 east, 2 south, 3 west; row 0 is
the top). Board text, one character per cell:

    .  floor (nothing can be placed)        o  slot (a piece may be placed here)      #  wall
    ^ > v <  emitter, facing that way       /  \\  a fixed mirror
    A  sensor lit by any beam               S  sensor lit only by an S beam           L  sensor lit only by an L beam
    X  decoy: must stay dark (lit by any beam)

BEAMS have a kind: W (white, from an emitter), S (short) or L (long). Only a prism or a filter changes a kind.

PIECES (`placed` maps (row, col) to (piece, state)):
    mirror    state 0 is "/", state 1 is "\\"; the beam turns, its kind is kept
    splitter  the beam goes on straight AND a copy turns left (relative to its travel); one state only
    prism     a W beam splits into an S beam and an L beam, one turning left and the other right (state 0: S left, L right;
              state 1: the other way round). An S or L beam entering a prism cannot split, it just bends to its own side
    absorber  stops every beam
    filter_s  passes S beams on, turns a W beam into an S beam, stops an L beam
    filter_l  the same for L

A wall, an emitter or the board's edge stops a beam. A sensor does NOT stop a beam: it lights and the beam goes on. A beam that
enters a cell in the same direction and kind it has already been through is cut (cycle detection), so a loop of mirrors ends.
"""

from collections import deque

DR = (-1, 0, 1, 0)
DC = (0, 1, 0, -1)
DIR_NAMES = ("north", "east", "south", "west")

KINDS = ("W", "S", "L")
KIND_NAMES = {"W": "white", "S": "short (S)", "L": "long (L)"}

PIECES = ("mirror", "splitter", "prism", "absorber", "filter_s", "filter_l")
PIECE_CODE = {"mirror": "m", "splitter": "s", "prism": "p", "absorber": "a", "filter_s": "fs", "filter_l": "fl"}
CODE_PIECE = {v: k for k, v in PIECE_CODE.items()}
PIECE_STATES = {"mirror": 2, "splitter": 1, "prism": 2, "absorber": 1, "filter_s": 1, "filter_l": 1}
PIECE_LABEL = {"mirror": "Mirror", "splitter": "Splitter", "prism": "Prism", "absorber": "Absorber", "filter_s": "S filter", "filter_l": "L filter"}

SENSOR_CHARS = "ASLX"
EMITTER_DIR = {"^": 0, ">": 1, "v": 2, "<": 3}
LEGAL_CHARS = ".o#/\\" + SENSOR_CHARS + "^>v<"


def piece_name(piece):
    """A piece kind in running text: "mirror", "splitter", "S filter" (the letter of a filter stays a capital)."""
    label = PIECE_LABEL[piece]
    return label if label[:2] in ("S ", "L ") else label.lower()


def cell_name(r, c):
    """Row and column, counted from 1, the way every message and label says it."""
    return "row %d, column %d" % (r + 1, c + 1)


def mirror_out(state, d):
    """The direction a beam leaves a mirror: "/" swaps north with east and south with west; "\\" swaps north with west and south with east."""
    return d ^ 1 if state == 0 else 3 - d


def prism_out(state, kind, d):
    """The (direction, kind) outputs of a prism for a beam of `kind` travelling `d`."""
    s_dir = (d + 3) % 4 if state == 0 else (d + 1) % 4
    l_dir = (d + 1) % 4 if state == 0 else (d + 3) % 4
    if kind == "W":
        return [(s_dir, "S"), (l_dir, "L")]
    return [(s_dir, "S")] if kind == "S" else [(l_dir, "L")]


class Board:
    """A parsed bench layout. Raises ValueError on a bad one, so a mistyped bench fails the tests, never the player."""

    def __init__(self, rows):
        rows = list(rows)
        if not rows or not all(isinstance(x, str) for x in rows):
            raise ValueError("a board is a list of strings")
        self.rows = tuple(rows)
        self.h = len(rows)
        self.w = len(rows[0])
        if self.w == 0 or any(len(x) != self.w for x in rows):
            raise ValueError("a board must be a rectangle")
        self.slots = set()
        self.walls = set()
        self.emitters = []                 # (r, c, direction)
        self.sensors = {}                  # (r, c) -> "A" / "S" / "L" / "X"
        self.fixed = {}                    # (r, c) -> mirror state
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch not in LEGAL_CHARS:
                    raise ValueError("bad character %r at %s" % (ch, cell_name(r, c)))
                if ch == "o":
                    self.slots.add((r, c))
                elif ch == "#":
                    self.walls.add((r, c))
                elif ch in EMITTER_DIR:
                    self.emitters.append((r, c, EMITTER_DIR[ch]))
                elif ch in SENSOR_CHARS:
                    self.sensors[(r, c)] = ch
                elif ch == "/":
                    self.fixed[(r, c)] = 0
                elif ch == "\\":
                    self.fixed[(r, c)] = 1
        if not self.emitters:
            raise ValueError("a board needs an emitter")
        self.required = tuple(sorted(cell for cell, kind in self.sensors.items() if kind != "X"))
        self.decoys = tuple(sorted(cell for cell, kind in self.sensors.items() if kind == "X"))
        self._emitter_cells = {(r, c) for r, c, _d in self.emitters}

    def inside(self, r, c):
        return 0 <= r < self.h and 0 <= c < self.w

    def blocks(self, r, c):
        """True when the cell stops any beam: off the board, a wall or an emitter."""
        return not self.inside(r, c) or (r, c) in self.walls or (r, c) in self._emitter_cells


class Trace:
    """What one tracing run found."""

    def __init__(self):
        self.segments = []         # (row, col, d_in, d_out, kind, born): d_in None for an emitter, d_out None when the beam ends here
        self.lit = set()           # sensor cells lit by a beam of the kind they need
        self.dark_hit = set()      # decoys that a beam entered
        self.hits = {}             # sensor cell -> sorted kinds of the beams that entered it
        self.loops = 0             # beams cut because they re-entered a cell the way they had before
        self.max_turns = 0         # the most turns any one beam made
        self.states = 0            # distinct (cell, direction, kind) entries traced
        self.pending = set()       # slots a beam reached while they were held back (used by the solver)
        self.ok = False            # every needed sensor lit and no decoy lit


def trace(board, placed, halt=frozenset()):
    """Trace every emitter's beam through `board` with `placed` pieces. Cells in `halt` stop a beam and are listed in `pending`
    (the solver decides them one at a time)."""
    result = Trace()
    seen = set()
    queue = deque()

    def push(r, c, d, kind, turns):
        queue.append((r, c, d, kind, turns))

    for r, c, d in board.emitters:
        result.segments.append((r, c, None, d, "W", True))
        push(r + DR[d], c + DC[d], d, "W", 0)

    while queue:
        r, c, d, kind, turns = queue.popleft()
        if board.blocks(r, c):
            continue
        cell = (r, c)
        if cell in halt:
            result.pending.add(cell)
            continue
        key = (r, c, d, kind)
        if key in seen:
            result.loops += 1
            continue
        seen.add(key)
        result.max_turns = max(result.max_turns, turns)

        outs = []                       # (direction out, kind out, born)
        piece = placed.get(cell)
        if piece is not None:
            name, state = piece
            if name == "mirror":
                outs.append((mirror_out(state, d), kind, False))
            elif name == "splitter":
                outs.append((d, kind, False))
                outs.append(((d + 3) % 4, kind, False))
            elif name == "prism":
                for od, ok in prism_out(state, kind, d):
                    outs.append((od, ok, ok != kind))
            elif name == "absorber":
                pass
            elif name in ("filter_s", "filter_l"):
                want = "S" if name == "filter_s" else "L"
                if kind == "W" or kind == want:
                    outs.append((d, want, kind != want))
        elif cell in board.fixed:
            outs.append((mirror_out(board.fixed[cell], d), kind, False))
        else:
            if cell in board.sensors:
                hit = result.hits.setdefault(cell, set())
                hit.add(kind)
            outs.append((d, kind, False))

        if not outs:
            result.segments.append((r, c, d, None, kind, False))
            continue
        for od, ok, born in outs:
            result.segments.append((r, c, d, od, ok, born))
            push(r + DR[od], c + DC[od], od, ok, turns + (1 if od != d else 0))

    result.states = len(seen)
    for cell, kinds in result.hits.items():
        need = board.sensors[cell]
        if need == "X":
            result.dark_hit.add(cell)
        elif need == "A" or need in kinds:
            result.lit.add(cell)
    result.hits = {cell: sorted(kinds) for cell, kinds in result.hits.items()}
    result.ok = len(result.lit) == len(board.required) and not result.dark_hit
    return result


def placed_from(layout):
    """A layout is {(r, c): (piece, state)}; this returns it as a plain dict copy."""
    return {tuple(cell): (piece, state) for cell, (piece, state) in layout.items()}


def layout_problem(board, tray, layout):
    """None when `layout` is a legal set of placements for this board and tray, else a short reason."""
    counts = {}
    for cell, value in layout.items():
        if not (isinstance(cell, tuple) and len(cell) == 2):
            return "bad cell"
        piece, state = value
        if cell not in board.slots:
            return "%s is not a slot" % cell_name(*cell)
        if piece not in PIECE_STATES:
            return "unknown piece %r" % (piece,)
        if isinstance(state, bool) or not isinstance(state, int) or not 0 <= state < PIECE_STATES[piece]:
            return "bad state for %s" % piece
        counts[piece] = counts.get(piece, 0) + 1
    for piece, n in counts.items():
        if n > tray.get(piece, 0):
            return "more %s pieces than the tray holds" % piece
    return None
