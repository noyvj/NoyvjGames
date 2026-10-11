"""Picture Grid -- the engine's single entry point (the Rule Finder / Hull Repair pattern).

The view (app.js) never reads engine objects: it sends one JSON string to `handle` and draws the JSON that comes back.
`get_state()` / `load_state()` are the shared save widget's contract (planning/SAVE-BUTTON-INTEGRATION.md). Nothing here reads
a clock or a random source: a frame's clues, its one solution and whether a grid is finished are pure functions of the picture.

Actions (every request is {"action": ..., ...}; every reply is the whole view):
  open                    the current view
  pick {picture}          go to a frame (it must be in an open gallery)
  next                    go to the next frame not yet hung (open galleries only)
  paint {cells, value}    set cells [[row, col], ...] to value 1 (filled), 2 (dot) or 0 (unknown). One call = one undo step
  undo / redo             step back / forward through your marks on this frame
  assist {name, on}       turn an optional assist on or off: "check", "autodot", "focus"
  retry                   solve a hung picture again from a blank frame (the picture stays hung)
  reset                   start over (everything)

Cell marks in the view's `grid` rows: "." unknown, "#" filled, "x" dot (known empty).
"""

import json

import nonogram
import pictures

UNKNOWN, FILLED, EMPTY = nonogram.UNKNOWN, nonogram.FILLED, nonogram.EMPTY
MARK = {UNKNOWN: ".", FILLED: "#", EMPTY: "x"}
UNMARK = {".": UNKNOWN, "#": FILLED, "x": EMPTY}
TALLY_KEYS = ("fills", "dots", "clears")
ASSISTS = ("check", "autodot", "focus")
MAX_COUNT = 10 ** 9
MAX_UNDO = 400
SCHEMA = 1                       # the save layout version; a save from a newer layout is not read


def _int(value, low=0, high=MAX_COUNT, default=0):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        return default
    return value


def _rows_of(grid):
    return ["".join(MARK[cell] for cell in row) for row in grid]


def _grid_from(rows, picture):
    """A saved frame (list of strings) back into a grid, or None if it is not exactly this picture's shape."""
    if not isinstance(rows, list) or len(rows) != picture.height:
        return None
    grid = []
    for row in rows:
        if not isinstance(row, str) or len(row) != picture.width or any(ch not in UNMARK for ch in row):
            return None
        grid.append([UNMARK[ch] for ch in row])
    return grid


def _filled(grid):
    """The grid with dots read as empty (what the clues are checked against)."""
    return [[1 if cell == FILLED else 0 for cell in row] for row in grid]


def lines_satisfied(picture, grid):
    """(rows, cols): for every line, do its filled cells make exactly the clue's blocks? Dots and unknowns both count as empty."""
    filled = _filled(grid)
    rows = [nonogram.line_clue(filled[r]) == picture.row_clues[r] for r in range(picture.height)]
    cols = [nonogram.line_clue([filled[r][c] for r in range(picture.height)]) == picture.col_clues[c] for c in range(picture.width)]
    return rows, cols


def is_complete(picture, grid):
    rows, cols = lines_satisfied(picture, grid)
    return all(rows) and all(cols)


class Game:
    def __init__(self):
        self.solved = {}                 # picture id -> best number of strokes it was solved in
        self.grids = {}                  # picture id -> the frame being worked (unsolved, or a hung picture being solved again)
        self.moves = {}                  # picture id -> strokes spent on the frame in self.grids
        self.tally = {key: 0 for key in TALLY_KEYS}
        self.assist = {name: False for name in ASSISTS}
        self.current = pictures.ORDER[0]
        self.undo = []                   # [(picture id, [(row, col, before, after)])]  -- this session only
        self.redo = []
        self.message = ""
        self.just = None                 # the frame that was hung by the last action (not saved)

    # ---- the current frame -----------------------------------------------------------------------------------------
    @property
    def picture(self):
        return pictures.BY_ID[self.current]

    def status(self, pid=None):
        """'solved' (hung and showing), 'redo' (hung, being solved again), or 'open'."""
        pid = pid or self.current
        if pid in self.solved:
            return "redo" if pid in self.grids else "solved"
        return "open"

    def grid_of(self, pid=None):
        pid = pid or self.current
        p = pictures.BY_ID[pid]
        if pid in self.grids:
            return self.grids[pid]
        if pid in self.solved:                           # a hung picture shows clean: filled cells and nothing else
            return [[FILLED if cell == FILLED else UNKNOWN for cell in row] for row in p.solution_grid()]
        return nonogram.blank_grid(p.height, p.width)

    def editable(self):
        return self.status() != "solved"

    def _enter(self, pid):
        self.current = pid
        self.just = None
        self.undo = []
        self.redo = []

    # ---- save ------------------------------------------------------------------------------------------------------
    def to_dict(self):
        """Only what differs from a fresh game is written (plus the layout version), so old and new saves stay compatible."""
        data = {"schema": SCHEMA}
        if self.current != pictures.ORDER[0]:
            data["cur"] = self.current
        if self.solved:
            data["solved"] = {pid: self.solved[pid] for pid in pictures.ORDER if pid in self.solved}
        work = {}
        for pid in pictures.ORDER:
            grid = self.grids.get(pid)
            if grid is not None and (pid in self.solved or any(cell != UNKNOWN for row in grid for cell in row)):
                work[pid] = _rows_of(grid)
        if work:
            data["work"] = work
        moves = {pid: n for pid, n in self.moves.items() if n and pid in work}
        if moves:
            data["moves"] = moves
        tally = {k: v for k, v in self.tally.items() if v}
        if tally:
            data["tally"] = tally
        assist = {name: 1 for name in ASSISTS if self.assist[name]}
        if assist:
            data["assist"] = assist
        return data

    def load(self, data):
        """Take a saved dict, checking every field on its own; a bad field falls back to its default. A hung picture only counts
        if its gallery was open by the pictures hung before it, and a saved frame must be exactly the picture's shape."""
        data = data if isinstance(data, dict) else {}
        schema = data.get("schema", SCHEMA)
        if isinstance(schema, bool) or not isinstance(schema, int) or not 1 <= schema <= SCHEMA:
            data = {}                                            # an unknown layout is never half-read
        self.solved, self.grids, self.moves = {}, {}, {}
        raw_solved = data.get("solved") if isinstance(data.get("solved"), dict) else {}
        for p in pictures.ALL:                                   # gallery order, so each gallery is judged on those before it
            if p.id in raw_solved and pictures.gallery_open(self.solved, p.gallery):
                self.solved[p.id] = _int(raw_solved[p.id])
        raw_work = data.get("work") if isinstance(data.get("work"), dict) else {}
        raw_moves = data.get("moves") if isinstance(data.get("moves"), dict) else {}
        for p in pictures.ALL:
            if p.id not in raw_work or not pictures.picture_open(self.solved, p.id):
                continue
            grid = _grid_from(raw_work[p.id], p)
            if grid is None:
                continue
            self.grids[p.id] = grid
            self.moves[p.id] = _int(raw_moves.get(p.id))
            if is_complete(p, grid):                             # a finished frame is never left lying around unhung
                self._finish(p.id)
        tally = data.get("tally") if isinstance(data.get("tally"), dict) else {}
        self.tally = {key: _int(tally.get(key)) for key in TALLY_KEYS}
        assist = data.get("assist") if isinstance(data.get("assist"), dict) else {}
        self.assist = {name: assist.get(name) in (1, True) for name in ASSISTS}
        cur = data.get("cur")
        self._enter(cur if isinstance(cur, str) and pictures.picture_open(self.solved, cur) else pictures.ORDER[0])
        self.message = ""

    # ---- the view --------------------------------------------------------------------------------------------------
    def _wall(self):
        out = []
        for g, gallery in enumerate(pictures.GALLERIES):
            is_open = pictures.gallery_open(self.solved, g)
            frames = []
            for p in gallery["pictures"]:
                hung = p.id in self.solved
                frame = {"id": p.id, "number": p.number, "size": p.size, "hung": hung, "current": p.id == self.current}
                if hung:
                    frame.update({"title": p.title, "caption": p.caption, "tint": p.tint, "rows": list(p.rows), "moves": self.solved[p.id]})
                frames.append(frame)
            need = max(0, min(pictures.OPEN_AT, len(pictures.GALLERIES[g - 1]["pictures"])) - pictures.gallery_hung(self.solved, g - 1)) if g else 0
            out.append({"id": gallery["id"], "name": gallery["name"], "blurb": gallery["blurb"], "open": is_open,
                        "hung": pictures.gallery_hung(self.solved, g), "total": len(gallery["pictures"]), "need": need,
                        "after": pictures.GALLERIES[g - 1]["name"] if g else "", "frames": frames})
        return out

    def view(self, message=None, ok=True):
        if message is not None:
            self.message = message
        p = self.picture
        grid = self.grid_of()
        status = self.status()
        rows_ok, cols_ok = lines_satisfied(p, grid)
        wrong = []
        if self.assist["check"] and status != "solved":
            solution = p.solution_grid()
            wrong = [[r, c] for r in range(p.height) for c in range(p.width)
                     if grid[r][c] != UNKNOWN and (grid[r][c] == FILLED) != (solution[r][c] == FILLED)]
        gallery = pictures.GALLERIES[p.gallery]
        view = {
            "ok": ok, "message": self.message,
            "picture": {"id": p.id, "number": p.number, "of": len(gallery["pictures"]), "gallery": gallery["name"], "gallery_index": p.gallery,
                        "width": p.width, "height": p.height, "size": p.size, "row_clues": p.row_clues, "col_clues": p.col_clues,
                        "status": status, "moves": self.moves.get(p.id, 0) if status != "solved" else self.solved[p.id],
                        "best": self.solved.get(p.id), "tint": p.tint},
            "grid": _rows_of(grid), "satisfied": {"rows": rows_ok, "cols": cols_ok}, "wrong": wrong,
            "editable": status != "solved", "can_undo": bool(self.undo), "can_redo": bool(self.redo),
            "just": self.just, "galleries": self._wall(), "assist": dict(self.assist), "tally": dict(self.tally),
            "totals": {"pictures": len(pictures.ORDER), "hung": len(self.solved), "cells": self.tally["fills"],
                       "galleries": len(pictures.GALLERIES), "galleries_done": pictures.galleries_done(self.solved)},
        }
        if status == "solved":
            view["picture"].update({"title": p.title, "caption": p.caption, "rows": list(p.rows)})
        return view

    # ---- marks -----------------------------------------------------------------------------------------------------
    def _autodot(self, p, grid, changes):
        """Dot every unknown cell of a line whose filled cells already make exactly its clue."""
        rows_ok, cols_ok = lines_satisfied(p, grid)
        for r in range(p.height):
            if rows_ok[r]:
                for c in range(p.width):
                    if grid[r][c] == UNKNOWN:
                        grid[r][c] = EMPTY
                        changes.append((r, c, UNKNOWN, EMPTY))
        for c in range(p.width):
            if cols_ok[c]:
                for r in range(p.height):
                    if grid[r][c] == UNKNOWN:
                        grid[r][c] = EMPTY
                        changes.append((r, c, UNKNOWN, EMPTY))

    def paint(self, cells, value):
        p = self.picture
        if not self.editable():
            return self.view("This picture is hung. Press Solve it again to start a fresh frame.", ok=False)
        if value not in (UNKNOWN, FILLED, EMPTY) or isinstance(value, bool) or not isinstance(cells, list):
            return self.view("That mark is not one this frame takes.", ok=False)
        grid = self.grids.get(self.current)
        if grid is None:
            grid = nonogram.blank_grid(p.height, p.width)
        changes = []
        seen = set()
        for pair in cells[: p.width * p.height]:
            if not (isinstance(pair, (list, tuple)) and len(pair) == 2):
                continue
            r, c = pair
            if isinstance(r, bool) or isinstance(c, bool) or not isinstance(r, int) or not isinstance(c, int):
                continue
            if not (0 <= r < p.height and 0 <= c < p.width) or (r, c) in seen:
                continue
            seen.add((r, c))
            before = grid[r][c]
            if before != value:
                changes.append((r, c, before, value))
        if not changes:
            return self.view("")
        for r, c, _before, after in changes:
            grid[r][c] = after
            if after == FILLED:
                self.tally["fills"] += 1
            elif after == EMPTY:
                self.tally["dots"] += 1
            else:
                self.tally["clears"] += 1                    # only the player's own marks are counted, never an auto-dot
        if self.assist["autodot"]:
            self._autodot(p, grid, changes)
        self.grids[self.current] = grid
        self.moves[self.current] = self.moves.get(self.current, 0) + 1
        self.undo.append((self.current, changes))
        del self.undo[:-MAX_UNDO]
        self.redo = []
        self.just = None
        if is_complete(p, grid):
            return self._hang()
        return self.view("")

    def _finish(self, pid):
        """A frame whose lines all match: hang the picture, keep the best stroke count, free the frame."""
        moves = self.moves.get(pid, 0)
        best = self.solved.get(pid)
        self.solved[pid] = moves if best is None else min(best, moves)
        self.grids.pop(pid, None)
        self.moves.pop(pid, None)
        return best is None

    def _hang(self):
        pid = self.current
        first = self._finish(pid)
        self.undo = []
        self.redo = []
        self.just = {"id": pid, "first": first, "moves": self.solved[pid]}
        p = self.picture
        return self.view("%s is hung on the wall. %s" % (p.title, p.caption))

    def step(self, forward):
        """Undo (forward False) or redo (forward True) the last stroke on this frame."""
        stack, other = (self.redo, self.undo) if forward else (self.undo, self.redo)
        if not stack or not self.editable():
            return self.view("Nothing to %s." % ("redo" if forward else "undo"), ok=False)
        pid, changes = stack.pop()
        grid = self.grids.get(pid)
        if grid is None:
            grid = nonogram.blank_grid(self.picture.height, self.picture.width)
            self.grids[pid] = grid
        for r, c, before, after in (changes if forward else reversed(changes)):
            grid[r][c] = after if forward else before
        other.append((pid, changes))
        return self.view("")

    # ---- navigation and settings ---------------------------------------------------------------------------------------
    def pick(self, pid):
        if not isinstance(pid, str) or pid not in pictures.BY_ID:
            return self.view("There is no such frame.", ok=False)
        if not pictures.picture_open(self.solved, pid):
            g = pictures.BY_ID[pid].gallery
            return self.view("That gallery opens when %d pictures in %s are hung." % (min(pictures.OPEN_AT, len(pictures.GALLERIES[g - 1]["pictures"])), pictures.GALLERIES[g - 1]["name"]), ok=False)
        if pid != self.current:
            self._enter(pid)
        return self.view("")

    def next(self):
        order = pictures.ORDER
        start = order.index(self.current)
        for step in range(1, len(order) + 1):
            pid = order[(start + step) % len(order)]
            if pid not in self.solved and pictures.picture_open(self.solved, pid):
                self._enter(pid)
                return self.view("")
        return self.view("Every open frame is hung." if len(self.solved) < len(order) else "Every frame is hung.", ok=False)

    def retry(self):
        if self.status() != "solved":
            return self.view("Hang this picture first.", ok=False)
        p = self.picture
        self.grids[self.current] = nonogram.blank_grid(p.height, p.width)
        self.moves[self.current] = 0
        self.undo = []
        self.redo = []
        return self.view("A fresh frame. The picture stays hung while you solve it again.")

    def set_assist(self, name, on):
        if name not in ASSISTS:
            return self.view("There is no such assist.", ok=False)
        self.assist[name] = bool(on)
        return self.view("")


game = Game()


def handle(request_json):
    try:
        request = json.loads(request_json)
        action = request.get("action")
    except (ValueError, AttributeError):
        return json.dumps({"error": "bad request"})
    g = game
    if action == "open":
        return json.dumps(g.view())
    if action == "reset":
        g.__init__()
        return json.dumps(g.view("Starting over."))
    if action == "pick":
        return json.dumps(g.pick(request.get("picture")))
    if action == "next":
        return json.dumps(g.next())
    if action == "paint":
        return json.dumps(g.paint(request.get("cells"), request.get("value")))
    if action == "undo":
        return json.dumps(g.step(False))
    if action == "redo":
        return json.dumps(g.step(True))
    if action == "assist":
        return json.dumps(g.set_assist(request.get("name"), request.get("on")))
    if action == "retry":
        return json.dumps(g.retry())
    return json.dumps({"error": "unknown action " + repr(action)})


def get_state():
    return game.to_dict()


def load_state(data):
    game.load(data)
    _refresh_view()


def _refresh_view():
    """Ask the page to redraw after a save is loaded (the save widget calls load_state directly and knows nothing about
    this game's view). Under plain CPython there is no page, so this is a no-op."""
    try:
        import js
        refresh = getattr(js.window, "pictureGridRefresh", None)
        if refresh is not None:
            refresh()
    except Exception:
        pass
