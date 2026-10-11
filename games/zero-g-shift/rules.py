"""Zero-G Shift -- the rules of a weightless cargo bay, as pure functions of a bay and a list of moves.

A bay is a grid. You and the crates glide until something stops you. One move is one thrust in a direction:

  * You slide until the next cell is blocked. If the next cell holds a loose crate you stop where you are and the crate
    slides on, until it is blocked (a push). A crate never pushes another crate: it simply stops against it.
  * Blocked means: the edge of the bay, a wall, a post, another crate, a closed airlock door. A hatch blocks you but a
    crate slides straight through it. A bumper stops you on it (and flings nothing); crates slide over it.
  * A dock pad catches a crate of its own kind the moment it touches it. A docked crate stays put (it is solid to
    everything else). A crate of another kind slides over the pad. You slide over pads too.
  * An airlock door is closed until every pad of its kind (the bay's `door`) holds a docked crate.
  * The bay is clear when every crate is docked.

A state is (player, crates): the player's cell, and a sorted tuple of crates, each `kind << 7 | cell` (a cell is
`y * width + x`, so a bay is at most 10 x 10). Identical-kind crates are interchangeable, so sorting keeps a state
canonical. Nothing here reads a clock or a random source.

Cell characters in a bay's `rows`:
  # wall   o post   . floor   h hatch   b bumper   = airlock door   A-D dock pad (kind A-D)
  1-4 a crate of kind A-D standing on the floor   @ you (standing on the floor)
"""

DIRS = ("U", "D", "L", "R")
DELTA = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}
DIR_NAMES = {"U": "up", "D": "down", "L": "left", "R": "right"}
OPPOSITE = {"U": "D", "D": "U", "L": "R", "R": "L"}
KIND_LETTERS = "ABCD"
KIND_SHAPES = ("circle", "square", "triangle", "diamond")
MIN_SIZE, MAX_SIZE = 5, 10
SHIFT = 7
MASK = 127

FLOOR, WALL, HATCH, BUMPER, DOOR, PAD = 0, 1, 2, 3, 4, 5
TERRAIN_CHARS = {"#": WALL, "o": WALL, ".": FLOOR, "h": HATCH, "b": BUMPER, "=": DOOR}
POST = "o"


class BayError(ValueError):
    pass


class Bay:
    """One authored bay. `spec` is a dict: id, name, rows, optionally door (a pad kind letter)."""

    def __init__(self, spec):
        self.id = spec["id"]
        self.name = spec.get("name", spec["id"])
        self.rows = tuple(spec["rows"])
        self.h = len(self.rows)
        self.w = len(self.rows[0]) if self.rows else 0
        self.door = spec.get("door")
        self.deck = 0
        self.number = 0
        self.par = spec.get("par")
        self.line = spec.get("line", "")
        if not (MIN_SIZE <= self.w <= MAX_SIZE and MIN_SIZE <= self.h <= MAX_SIZE):
            raise BayError("%s: a bay is %d to %d cells each way" % (self.id, MIN_SIZE, MAX_SIZE))
        if any(len(r) != self.w for r in self.rows):
            raise BayError("%s: rows must all be the same length" % self.id)
        n = self.w * self.h
        self.cells = n
        self.terr = [FLOOR] * n
        self.glyph = ["."] * n               # the printed terrain character (o for a post, A-D for a pad)
        self.pad_kind = {}                   # cell -> kind
        crates, player = [], None
        for y, row in enumerate(self.rows):
            for x, ch in enumerate(row):
                i = y * self.w + x
                if ch in TERRAIN_CHARS:
                    self.terr[i] = TERRAIN_CHARS[ch]
                    self.glyph[i] = ch
                elif ch in KIND_LETTERS:
                    self.terr[i] = PAD
                    self.glyph[i] = ch
                    self.pad_kind[i] = KIND_LETTERS.index(ch)
                elif ch in "1234":
                    crates.append((int(ch) - 1) << SHIFT | i)
                elif ch == "@":
                    if player is not None:
                        raise BayError("%s: more than one player" % self.id)
                    player = i
                else:
                    raise BayError("%s: unknown cell %r" % (self.id, ch))
        if player is None or not crates:
            raise BayError("%s: needs one player and at least one crate" % self.id)
        self.start = (player, tuple(sorted(crates)))
        for k in range(4):
            have = sum(1 for c in self.start[1] if c >> SHIFT == k)
            pads = sum(1 for v in self.pad_kind.values() if v == k)
            if have != pads:
                raise BayError("%s: %d crates of kind %s but %d pads" % (self.id, have, KIND_LETTERS[k], pads))
        self.door_cells = tuple(i for i in range(n) if self.terr[i] == DOOR)
        if bool(self.door_cells) != bool(self.door):
            raise BayError("%s: doors and the door pad kind must go together" % self.id)
        self.door_kind = KIND_LETTERS.index(self.door) if self.door else None
        if self.door and not any(v == self.door_kind for v in self.pad_kind.values()):
            raise BayError("%s: the door's pad kind has no pads" % self.id)
        self.door_pads = tuple(sorted(i for i, v in self.pad_kind.items() if v == self.door_kind)) if self.door else ()
        # neighbour table: nbr[d][cell] is the next cell that way or -1 off the bay
        self.nbr = {}
        for d in DIRS:
            dx, dy = DELTA[d]
            table = []
            for i in range(n):
                x, y = i % self.w + dx, i // self.w + dy
                table.append(y * self.w + x if 0 <= x < self.w and 0 <= y < self.h else -1)
            self.nbr[d] = table
        self.kinds_in_play = tuple(sorted({c >> SHIFT for c in self.start[1]}))

    # ---- queries -------------------------------------------------------------------------------------------------
    def xy(self, cell):
        return cell % self.w, cell // self.w

    def door_open(self, crates):
        """True when a door exists and every pad of its kind holds a docked crate."""
        if not self.door:
            return False
        held = {c & MASK for c in crates if c >> SHIFT == self.door_kind}
        return all(p in held for p in self.door_pads)

    def docked(self, crate):
        return self.pad_kind.get(crate & MASK) == crate >> SHIFT

    def cleared(self, state):
        return all(self.pad_kind.get(c & MASK) == c >> SHIFT for c in state[1])

    def docked_count(self, state):
        return sum(1 for c in state[1] if self.docked(c))


def _slide_crate(bay, crate, d, occupied, door_ok):
    """Slide one crate from where it stands until it is blocked. -> (new crate, cells moved, over_hatch)."""
    kind = crate >> SHIFT
    cell = crate & MASK
    table = bay.nbr[d]
    terr = bay.terr
    moved = 0
    hatch = False
    while True:
        nxt = table[cell]
        if nxt < 0 or nxt in occupied:
            break
        t = terr[nxt]
        if t == WALL or (t == DOOR and not door_ok):
            break
        cell = nxt
        moved += 1
        if t == HATCH:
            hatch = True
        elif t == PAD and bay.pad_kind[nxt] == kind:
            break
    return (kind << SHIFT) | cell, moved, hatch


def step(bay, state, d):
    """One thrust. -> None when nothing at all happens, else (new_state, info).

    info: {"d", "from", "to", "cells" (your slide), "push" (None or a dict: kind, from, to, cells, docked, hatch),
           "longest" (the longest slide in cells, yours or the crate's), "hatch" (a crate crossed a hatch),
           "opened" (the door opened because of this move)}"""
    player, crates = state
    door_ok = bay.door_open(crates)
    by_cell = {c & MASK: c for c in crates}
    table = bay.nbr[d]
    terr = bay.terr
    cell = player
    moved = 0
    push = None
    new_crates = crates
    while True:
        nxt = table[cell]
        if nxt < 0:
            break
        t = terr[nxt]
        if t == WALL or t == HATCH or (t == DOOR and not door_ok):
            break
        crate = by_cell.get(nxt)
        if crate is not None:
            if bay.docked(crate):
                break
            occupied = set(by_cell)
            occupied.discard(nxt)
            slid, n, hatch = _slide_crate(bay, crate, d, occupied, door_ok)
            if n:
                new_crates = tuple(sorted([slid if c == crate else c for c in crates]))
                push = {"kind": crate >> SHIFT, "from": nxt, "to": slid & MASK, "cells": n,
                        "docked": bay.docked(slid), "hatch": hatch}
            break
        cell = nxt
        moved += 1
        if t == BUMPER:
            break
    if not moved and push is None:
        return None
    new_state = (cell, new_crates)
    longest = max(moved, push["cells"] if push else 0)
    opened = bool(bay.door) and not door_ok and bay.door_open(new_crates)
    info = {"d": d, "from": player, "to": cell, "cells": moved, "push": push, "longest": longest,
            "hatch": bool(push and push["hatch"]), "opened": opened}
    return new_state, info


def replay(bay, line):
    """Play a string of moves from the start. -> (states, infos) or None when any move does nothing or is not a move."""
    if not isinstance(line, str):
        return None
    state = bay.start
    states, infos = [state], []
    for ch in line:
        if ch not in DELTA:
            return None
        out = step(bay, state, ch)
        if out is None:
            return None
        state, info = out
        states.append(state)
        infos.append(info)
    return states, infos


def line_words(line):
    return ", ".join(DIR_NAMES[ch] for ch in line)


def cell_words(bay, cell):
    return "column %d, row %d" % (bay.xy(cell)[0] + 1, bay.xy(cell)[1] + 1)


def crate_name(kind):
    return "%s crate %s" % (KIND_SHAPES[kind], KIND_LETTERS[kind])


def describe(bay, state):
    """The bay in plain words, for a screen reader: you, then each crate, pad, hatch, bumper and door."""
    player, crates = state
    out = ["You are at %s." % cell_words(bay, player)]
    for c in crates:
        where = cell_words(bay, c & MASK)
        name = crate_name(c >> SHIFT)
        out.append("%s at %s%s." % (name[0].upper() + name[1:], where, ", docked" if bay.docked(c) else ", loose"))
    held = {c & MASK for c in crates if bay.docked(c)}
    for cell in sorted(bay.pad_kind):
        if cell not in held:
            out.append("Dock pad %s (%s) at %s, empty." % (KIND_LETTERS[bay.pad_kind[cell]], KIND_SHAPES[bay.pad_kind[cell]], cell_words(bay, cell)))
    names = {HATCH: "Hatch (crates slide through, you do not)", BUMPER: "Bumper (stops you on it)"}
    for i in range(bay.cells):
        if bay.terr[i] in names:
            out.append("%s at %s." % (names[bay.terr[i]], cell_words(bay, i)))
        if bay.glyph[i] == POST:
            out.append("Post at %s." % cell_words(bay, i))
    if bay.door_cells:
        word = "open" if bay.door_open(crates) else "closed until every pad %s holds a crate" % bay.door
        out.append("Airlock door (%s) at %s." % (word, ", ".join(cell_words(bay, i) for i in bay.door_cells)))
    return out


def _cells(n):
    return "%d cell%s" % (n, "" if n == 1 else "s")


def move_words(info, bay):
    """One plain sentence or two for what a move did."""
    d = DIR_NAMES[info["d"]]
    push = info["push"]
    out = []
    if info["cells"]:
        stop = " and stopped on the bumper" if bay.terr[info["to"]] == BUMPER else ""
        out.append("You slid %s %s%s" % (d, _cells(info["cells"]), stop))
    if push:
        text = "%s the %s %s; it slid %s" % ("then pushed" if info["cells"] else "You pushed", crate_name(push["kind"]), d, _cells(push["cells"]))
        if push["docked"]:
            text += " and docked on its pad"
        if push["hatch"]:
            text += ", through a hatch"
        out.append(text)
    if info.get("opened"):
        out.append("The airlock door opened")
    return ". ".join(out) + "."


def valid_line(text, limit=500):
    return isinstance(text, str) and len(text) <= limit and all(ch in DELTA for ch in text)
