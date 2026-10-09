"""Hull Repair -- the rules of a board, as pure functions (no DOM, no clock, no randomness).

A board is a small grid. Cells are written as one character each:

  .          open floor (a restored board covers every one of these)
  #          hole: hull that is gone, not playable
  =          bridge: two lines may cross here, one straight across, one straight up and down
  ^ > v <    valve: a line passes straight through, the way the arrow points (travelling from source to sink)
  A..H       a line's source port;  a..h  its sink port
  1..3       a mixer: two named lines (see Board.mixers) both end here, one from each side

A line is a list of (x, y) cells that starts on one of its ports. A *layout* is a dict mapping a line letter to such a
list. `check_layout` is the single judge of whether a layout is legal; `status` says whether it patches or restores the
board. Everything else in the game (the drawing state, the solver, the saves) is checked against these functions.
"""

DIRS = ((0, -1), (1, 0), (0, 1), (-1, 0))        # up, right, down, left
ARROWS = {"^": 0, ">": 1, "v": 2, "<": 3}
LINES = "ABCDEFGH"
LINE_NAMES = {"A": "Power", "B": "Coolant", "C": "Air", "D": "Fuel", "E": "Water", "F": "Data", "G": "Steam", "H": "Waste"}
LINE_SHAPES = {"A": "circle", "B": "square", "C": "triangle", "D": "diamond", "E": "hexagon", "F": "pentagon", "G": "cross", "H": "star"}
MIN_SIDE, MAX_SIDE = 4, 9
UNPATCHED, PATCHED, RESTORED = 0, 1, 2
STATUS_NAMES = {UNPATCHED: "open", PATCHED: "patched", RESTORED: "restored"}


def add(cell, delta):
    return (cell[0] + delta[0], cell[1] + delta[1])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def adjacent(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1


def dir_index(delta):
    return DIRS.index(delta) if delta in DIRS else -1


def lane_of(delta):
    """0 for a vertical crossing, 1 for a horizontal one (a bridge holds one line in each lane)."""
    return 0 if delta[0] == 0 else 1


class Board:
    """One authored board. `spec` is a dict: id, name, rows (list of strings), optional mixers {"1": "AB"} and sol (the
    stored restored layout in `encode` form)."""

    def __init__(self, spec):
        self.spec = spec
        self.id = spec["id"]
        self.name = spec.get("name", spec["id"])
        self.rows = list(spec["rows"])
        self.h = len(self.rows)
        self.w = len(self.rows[0]) if self.rows else 0
        if not (MIN_SIDE <= self.w <= MAX_SIDE and MIN_SIDE <= self.h <= MAX_SIDE):
            raise ValueError("%s: a board is %d to %d cells a side" % (self.id, MIN_SIDE, MAX_SIDE))
        self.holes, self.bridges, self.valves = set(), set(), {}
        self.src, self.dst = {}, {}
        self.mixers = {}                        # cell -> (colour, colour)
        self.mixer_of = {}                      # colour -> mixer cell
        self.port_at = {}                       # cell -> (colour, "src" | "dst")
        digits = {}
        low = {}
        for y, row in enumerate(self.rows):
            if len(row) != self.w:
                raise ValueError("%s: rows differ in length" % self.id)
            for x, ch in enumerate(row):
                cell = (x, y)
                if ch == ".":
                    continue
                if ch == "#":
                    self.holes.add(cell)
                elif ch == "=":
                    self.bridges.add(cell)
                elif ch in ARROWS:
                    self.valves[cell] = ARROWS[ch]
                elif ch in LINES:
                    if ch in self.src:
                        raise ValueError("%s: two sources for %s" % (self.id, ch))
                    self.src[ch] = cell
                    self.port_at[cell] = (ch, "src")
                elif ch.upper() in LINES and ch.islower():
                    if ch.upper() in low:
                        raise ValueError("%s: two sinks for %s" % (self.id, ch))
                    low[ch.upper()] = cell
                    self.port_at[cell] = (ch.upper(), "dst")
                elif ch in "123":
                    digits[ch] = cell
                else:
                    raise ValueError("%s: unknown cell %r" % (self.id, ch))
        for digit, pair in spec.get("mixers", {}).items():
            if digit not in digits or len(pair) != 2 or pair[0] == pair[1] or any(c not in self.src for c in pair):
                raise ValueError("%s: bad mixer %s" % (self.id, digit))
            self.mixers[digits[digit]] = (pair[0], pair[1])
            for c in pair:
                if c in self.mixer_of:
                    raise ValueError("%s: line %s ends in two mixers" % (self.id, c))
                self.mixer_of[c] = digits[digit]
        if set(digits.values()) != set(self.mixers):
            raise ValueError("%s: a mixer with no lines" % self.id)
        for c in self.src:
            has_low = c in low
            if has_low == (c in self.mixer_of):
                raise ValueError("%s: line %s needs exactly one sink or mixer" % (self.id, c))
            self.dst[c] = low[c] if has_low else self.mixer_of[c]
        if set(low) - set(self.src):
            raise ValueError("%s: a sink with no source" % self.id)
        self.lines = tuple(sorted(self.src))
        self.playable = {(x, y) for y in range(self.h) for x in range(self.w)} - self.holes
        self.fixed = set(self.port_at) | set(self.mixers)
        self.need = self.playable - self.fixed          # cells a restored board must cover
        if not self.lines:
            raise ValueError("%s: no lines" % self.id)
        self.twists = tuple(t for t, present in (("holes", self.holes), ("bridges", self.bridges), ("valves", self.valves), ("mixers", self.mixers)) if present)

    def kind(self, cell):
        if cell not in self.playable:
            return "hole"
        if cell in self.port_at:
            return "port"
        if cell in self.mixers:
            return "mixer"
        if cell in self.bridges:
            return "bridge"
        if cell in self.valves:
            return "valve"
        return "open"

    def neighbours(self, cell):
        return [n for n in (add(cell, d) for d in DIRS) if n in self.playable]

    def valve_dir(self, cell, reversed_path):
        """The step delta a valve allows for a path stored in this direction."""
        d = self.valves[cell]
        return DIRS[(d + 2) % 4] if reversed_path else DIRS[d]


# ---- layouts -------------------------------------------------------------------------------------------------------
def anchored_at(board, c, path):
    """'src' or 'dst' for the port a stored path starts on, or None when it does not start on a port of c."""
    if not path:
        return None
    info = board.port_at.get(path[0])
    return info[1] if info is not None and info[0] == c else None


def far_terminal(board, c, path):
    anchor = anchored_at(board, c, path)
    if anchor == "src":
        return board.dst[c]
    if anchor == "dst":
        return board.src[c]
    return None


def is_connected(board, c, path):
    return len(path) >= 2 and anchored_at(board, c, path) is not None and path[-1] == far_terminal(board, c, path)


def oriented(board, c, path):
    """The path read from source to sink (a path started on the sink port is reversed)."""
    return list(reversed(path)) if anchored_at(board, c, path) == "dst" else list(path)


def check_layout(board, paths):
    """Every way a layout breaks the rules, as short strings (empty list: legal). Partial lines are legal: a line may stop
    anywhere, even on a bridge or valve that it has entered. Nothing here needs a line to be finished."""
    problems = []
    used = {}
    for c in sorted(paths):
        path = [tuple(p) for p in paths[c]]
        if c not in board.lines:
            problems.append("unknown line %s" % c)
            continue
        if not path:
            continue
        anchor = anchored_at(board, c, path)
        if anchor is None:
            problems.append("line %s does not start on one of its ports" % c)
            continue
        rev = anchor == "dst"
        far = far_terminal(board, c, path)
        seen = set()
        for i, cell in enumerate(path):
            if cell in seen:
                problems.append("line %s visits %s twice" % (c, cell))
            seen.add(cell)
            if cell not in board.playable:
                problems.append("line %s is off the board or in a hole at %s" % (c, cell))
                continue
            if i > 0 and not adjacent(path[i - 1], cell):
                problems.append("line %s jumps at %s" % (c, cell))
            if i > 0 and (cell in board.port_at or cell in board.mixers):
                if cell != far or i != len(path) - 1:
                    problems.append("line %s runs into a port or mixer at %s" % (c, cell))
            if i > 0 and cell in board.valves:
                step = sub(cell, path[i - 1])
                if step != board.valve_dir(cell, rev):
                    problems.append("line %s goes through the valve at %s the wrong way" % (c, cell))
            if 0 < i < len(path) - 1 and (cell in board.bridges or cell in board.valves):
                if sub(cell, path[i - 1]) != sub(path[i + 1], cell):
                    problems.append("line %s turns on a bridge or valve at %s" % (c, cell))
            lane = None
            if cell in board.bridges and i > 0:
                lane = lane_of(sub(cell, path[i - 1]))
            key = (cell, lane, c) if cell in board.mixers else (cell, lane)
            if key in used and used[key] != c:
                problems.append("lines %s and %s share %s" % (used[key], c, cell))
            used[key] = c
    return problems


def connected_lines(board, paths):
    return [c for c in board.lines if c in paths and is_connected(board, c, [tuple(p) for p in paths[c]])]


def covered(board, paths):
    cells = set()
    for path in paths.values():
        cells.update(tuple(p) for p in path)
    return cells


def uncovered(board, paths):
    """Open cells (not ports, mixers or holes) that no line touches, in reading order."""
    got = covered(board, paths)
    return sorted((c for c in board.need if c not in got), key=lambda p: (p[1], p[0]))


def status(board, paths):
    """0 open, 1 patched (every line joined), 2 restored (and every open cell covered). An illegal layout is 0."""
    if check_layout(board, paths):
        return UNPATCHED
    if len(connected_lines(board, paths)) != len(board.lines):
        return UNPATCHED
    return RESTORED if not uncovered(board, paths) else PATCHED


def flags_of(board, paths):
    """Which twists a finished layout really used (for the achievements)."""
    out = []
    lanes = {}
    for c, path in paths.items():
        for i, cell in enumerate(path):
            if cell in board.bridges and 0 < i:
                lanes.setdefault(cell, set()).add(lane_of(sub(cell, path[i - 1])))
    if any(len(v) == 2 for v in lanes.values()):
        out.append("bridge")
    if any(cell in board.valves for path in paths.values() for cell in path):
        out.append("valve")
    if board.mixers:
        out.append("mix")
    return out


# ---- the compact text form (saves and stored solutions) ---------------------------------------------------------------
def encode(paths):
    """'A0102;B...' : the line letter, then two digits (column, row) for each cell. Lines in letter order."""
    return ";".join(c + "".join("%d%d" % (p[0], p[1]) for p in paths[c]) for c in sorted(paths) if paths[c])


def decode(board, text):
    """The layout a string describes, or None when it is malformed or breaks a rule. Cells are checked against the board."""
    if not isinstance(text, str) or len(text) > 2000:
        return None
    paths = {}
    for token in text.split(";") if text else []:
        if len(token) < 3 or token[0] not in board.lines or token[0] in paths or (len(token) - 1) % 2:
            return None
        digits = token[1:]
        if not digits.isdigit() or not digits.isascii():
            return None
        cells = [(int(digits[i]), int(digits[i + 1])) for i in range(0, len(digits), 2)]
        paths[token[0]] = cells
    if check_layout(board, paths):
        return None
    return paths
