"""Robot Script -- the room and its one rule-book.

A room is drawn as rows of characters:
    .  floor            #  wall             E  exit pad
    p  a part to carry  o  a socket to fill
    1 2 3  a switch     A B C  a door that opens once switch 1 / 2 / 3 is lit
    > < ^ v  the robot's start tile, facing east, west, north or south (the tile is floor)

`Layout` holds the unchanging shape. The changing state is one tuple, `(x, y, d, carry, parts, sockets, switches)`:
position, heading (0 north, 1 east, 2 south, 3 west), the index of the carried part or -1, and three bit masks (parts
still on the floor, sockets filled, switches lit). `step` is the single function that says what an action does; the
interpreter (run.py) and the test solver both call it, so they cannot disagree.
"""

DX = (0, 1, 0, -1)
DY = (-1, 0, 1, 0)
HEADINGS = {"^": 0, ">": 1, "v": 2, "<": 3}
HEADING_NAMES = ("north", "east", "south", "west")
FLOOR_CHARS = ".#EpoO123ABC><^v"
MAX_SIDE = 10
MAX_CELLS = 64


class LayoutError(ValueError):
    pass


class Layout:
    def __init__(self, rows, strict=True):
        if not isinstance(rows, (list, tuple)) or not rows or not all(isinstance(r, str) for r in rows):
            raise LayoutError("rows must be a list of strings")
        width = len(rows[0])
        if any(len(r) != width for r in rows):
            raise LayoutError("rows must be the same length")
        if width > MAX_SIDE or len(rows) > MAX_SIDE or width < 1 or width * len(rows) > MAX_CELLS:
            raise LayoutError("room too large")
        self.rows = tuple(rows)
        self.w, self.h = width, len(rows)
        self.walls = set()
        self.exits = []
        self.parts = []           # (x, y) in reading order: the index is the part's number
        self.sockets = []
        self.switch_at = {}       # (x, y) -> switch id 0..2
        self.door_at = {}         # (x, y) -> switch id 0..2
        self.start = None
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch not in FLOOR_CHARS.replace("O", ""):
                    raise LayoutError("unknown tile " + repr(ch))
                if ch == "#":
                    self.walls.add((x, y))
                elif ch == "E":
                    self.exits.append((x, y))
                elif ch == "p":
                    self.parts.append((x, y))
                elif ch == "o":
                    self.sockets.append((x, y))
                elif ch in "123":
                    self.switch_at[(x, y)] = int(ch) - 1
                elif ch in "ABC":
                    self.door_at[(x, y)] = "ABC".index(ch)
                elif ch in HEADINGS:
                    if self.start is not None:
                        raise LayoutError("two starts")
                    self.start = (x, y, HEADINGS[ch])
        if self.start is None:
            raise LayoutError("no start")
        self.part_at = {pos: i for i, pos in enumerate(self.parts)}
        self.socket_at = {pos: i for i, pos in enumerate(self.sockets)}
        if strict:
            if len(self.exits) > 1:
                raise LayoutError("at most one exit")
            if self.sockets and len(self.parts) < len(self.sockets):
                raise LayoutError("fewer parts than sockets")
            if not self.sockets and len(self.parts) > 1:
                raise LayoutError("several parts need sockets")
            for pos, sid in self.door_at.items():
                if sid not in self.switch_at.values():
                    raise LayoutError("a door has no switch")
            if len(set(self.switch_at.values())) != len(self.switch_at):
                raise LayoutError("two switches share an id")
        self.switch_ids = sorted(self.switch_at.values())

    def initial(self):
        x, y, d = self.start
        return (x, y, d, -1, (1 << len(self.parts)) - 1, 0, 0)

    def switch_char(self, sid):
        return str(sid + 1)

    def blocked_reason(self, x, y, switches):
        """None when (x, y) can be entered, else why not."""
        if not (0 <= x < self.w and 0 <= y < self.h):
            return "That is the edge of the room."
        if (x, y) in self.walls:
            return "A wall is in the way."
        sid = self.door_at.get((x, y))
        if sid is not None and not (switches >> sid) & 1:
            return "The door is shut. Light switch " + str(sid + 1) + " first."
        return None


def step(layout, state, action):
    """Apply one action. Returns (new_state, None) or (state, reason) when the action cannot be done."""
    x, y, d, carry, parts, sockets, switches = state
    if action == "L":
        return (x, y, (d + 3) % 4, carry, parts, sockets, switches), None
    if action == "R":
        return (x, y, (d + 1) % 4, carry, parts, sockets, switches), None
    if action == "F":
        nx, ny = x + DX[d], y + DY[d]
        reason = layout.blocked_reason(nx, ny, switches)
        if reason:
            return state, reason
        return (nx, ny, d, carry, parts, sockets, switches), None
    if action == "G":
        if carry >= 0:
            return state, "The robot's hands are full."
        idx = layout.part_at.get((x, y))
        if idx is None or not (parts >> idx) & 1:
            return state, "There is no part to pick up here."
        return (x, y, d, idx, parts & ~(1 << idx), sockets, switches), None
    if action == "P":
        if carry < 0:
            return state, "The robot is not carrying anything."
        idx = layout.socket_at.get((x, y))
        if idx is None or (sockets >> idx) & 1:
            return state, "There is no empty socket here."
        return (x, y, d, -1, parts, sockets | (1 << idx), switches), None
    if action == "S":
        sid = layout.switch_at.get((x, y))
        if sid is None:
            return state, "There is no switch here."
        return (x, y, d, carry, parts, sockets, switches | (1 << sid)), None
    return state, "Unknown instruction."


def cond_holds(layout, state, cond):
    """Evaluate a condition (with an optional leading '!') in `state`."""
    x, y, d, carry, parts, sockets, switches = state
    name = cond.lstrip("!")
    if name == "blocked":
        value = layout.blocked_reason(x + DX[d], y + DY[d], switches) is not None
    elif name == "part":
        idx = layout.part_at.get((x, y))
        value = idx is not None and bool((parts >> idx) & 1)
    elif name == "socket":
        idx = layout.socket_at.get((x, y))
        value = idx is not None and not (sockets >> idx) & 1
    elif name == "switch":
        sid = layout.switch_at.get((x, y))
        value = sid is not None and not (switches >> sid) & 1
    elif name == "carrying":
        value = carry >= 0
    else:
        value = (x, y) in layout.exits
    return (not value) if cond.startswith("!") else value


def goals(layout, state):
    """The room's goals with whether each is met, in the order they are shown."""
    x, y, _d, carry, parts, sockets, switches = state
    out = []
    if layout.exits:
        out.append({"id": "exit", "label": "Finish on the exit pad", "met": (x, y) in layout.exits})
    if layout.sockets:
        filled = bin(sockets).count("1")
        total = len(layout.sockets)
        out.append({"id": "sockets", "label": "Fill the socket" if total == 1 else "Fill all %d sockets (%d of %d)" % (total, filled, total),
                    "met": filled == total})
    elif layout.parts:
        out.append({"id": "parts", "label": "Pick up the part", "met": parts == 0})
    if layout.switch_ids:
        lit = bin(switches).count("1")
        total = len(layout.switch_ids)
        out.append({"id": "switches", "label": "Light the switch" if total == 1 else "Light all %d switches (%d of %d)" % (total, lit, total),
                    "met": lit == total})
    return out


def goals_met(layout, state):
    g = goals(layout, state)
    return bool(g) and all(item["met"] for item in g)
