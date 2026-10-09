"""Hull Repair -- the drawing state of one board: what the player's finger or keys do to the lines.

`Drawing` holds the layout (line letter -> list of cells, started on one of the line's ports) and applies one touch:
`begin(cell)`, any number of `move(cell)`, then `end()`. It enforces the movement rules (one cell at a time, no holes,
bridges and valves go straight, a line dragged into another line cuts it, dragging back over your own line trims it) so a
layout it produces always passes `rules.check_layout`. It reads no clock and no random source.
"""

import rules

HISTORY_LIMIT = 200


def _copy(paths):
    return {c: list(p) for c, p in paths.items() if p}


class Drawing:
    def __init__(self, board, paths=None):
        self.board = board
        self.paths = _copy(paths or {})
        self.history = []                 # earlier layouts, newest last (Undo)
        self.drag = None                  # {"c", "kind", "moved", "before"} while a finger is down
        self.laid = 0                     # cells added since the caller last read it
        self.erased = 0                   # cells removed since the caller last read it
        self.took_back = False            # a line was erased on this board (for "Second Thoughts")

    # ---- reading ---------------------------------------------------------------------------------------------------
    def status(self):
        return rules.status(self.board, self.paths)

    def line_state(self, c):
        path = self.paths.get(c, [])
        if rules.is_connected(self.board, c, path):
            return "connected"
        return "drawing" if len(path) > 1 else "empty"

    def occupant(self, cell, lane=None):
        """The line on a cell (on a bridge: in a lane), or None."""
        for c, path in self.paths.items():
            for i, p in enumerate(path):
                if p != cell:
                    continue
                if cell in self.board.bridges and lane is not None and i > 0 and rules.lane_of(rules.sub(cell, path[i - 1])) != lane:
                    continue
                return c
        return None

    def take_counts(self):
        laid, erased = self.laid, self.erased
        self.laid = self.erased = 0
        return laid, erased

    # ---- editing helpers -------------------------------------------------------------------------------------------
    def _remove_from(self, c, index):
        path = self.paths.get(c, [])
        if index < len(path):
            self.erased += len(path) - index
            del path[index:]
            self.took_back = True
        if not path:
            self.paths.pop(c, None)

    def _push_history(self, before):
        self.history.append(before)
        if len(self.history) > HISTORY_LIMIT:
            del self.history[0]

    # ---- one touch -------------------------------------------------------------------------------------------------
    def begin(self, cell):
        """Put a finger down on a cell. Returns (ok, message). ok is False when there is nothing to pick up here."""
        self.drag = None
        cell = tuple(cell)
        board = self.board
        if cell not in board.playable:
            return False, "That part of the hull is gone."
        before = _copy(self.paths)
        info = board.port_at.get(cell)
        if info is not None:
            self.drag = {"c": info[0], "kind": "port", "moved": False, "before": before, "start": cell}
            return True, ""
        if cell in board.mixers:
            return False, "Start a line from its own port; the mixer takes two lines that arrive from different sides."
        for c in board.lines:
            path = self.paths.get(c, [])
            if cell in path:
                k = path.index(cell)
                if k == 0:
                    continue
                self.drag = {"c": c, "kind": "head" if k == len(path) - 1 else "mid", "moved": False, "before": before, "start": cell}
                if k < len(path) - 1:
                    self._remove_from(c, k + 1)
                return True, ""
        return False, "Start on a port, or on the end of a line."

    def move(self, cell):
        """The finger reached a neighbouring cell. Returns (ok, message); a refused move changes nothing."""
        if self.drag is None:
            return False, ""
        cell = tuple(cell)
        board = self.board
        d = self.drag
        c = d["c"]
        if d["kind"] == "port" and not d["moved"] and self.paths.get(c) != [d["start"]]:
            self._remove_from(c, 0)                        # a fresh drag from a port starts that line again
            self.paths[c] = [d["start"]]
        path = self.paths.get(c)
        if not path:
            return False, ""
        head = path[-1]
        if cell == head:
            return True, ""
        if cell in path:                                   # dragging back over your own line trims it
            k = path.index(cell)
            self._remove_from(c, k + 1)
            d["moved"] = True
            return True, ""
        if not rules.adjacent(head, cell):
            return False, "A line moves one cell at a time."
        if cell not in board.playable:
            return False, "That part of the hull is gone."
        anchor = rules.anchored_at(board, c, path)
        if anchor is None:
            return False, "That line does not start on a port."
        rev = anchor == "dst"
        if rules.is_connected(board, c, path):
            return False, "This line is already joined. Drag back along it to change it."
        step = rules.sub(cell, head)
        if len(path) > 1 and (head in board.bridges or head in board.valves):
            if step != rules.sub(head, path[-2]):
                return False, "A bridge or a valve only lets a line go straight through."
        if cell in board.port_at or cell in board.mixers:
            if cell != rules.far_terminal(board, c, path):
                return False, "That port belongs to another line." if cell in board.port_at else "That mixer does not take this line."
        elif cell in board.valves and step != board.valve_dir(cell, rev):
            return False, "A valve only lets a line through the way its arrow points."
        cut = None
        if cell in board.bridges:
            other = self.occupant(cell, rules.lane_of(step))
            if other is not None and other != c:
                cut = other
        elif cell not in board.port_at and cell not in board.mixers:
            other = self.occupant(cell)
            if other is not None and other != c:
                cut = other
        if cut is not None:
            index = self._index_in_lane(cut, cell, rules.lane_of(step) if cell in board.bridges else None)
            self._remove_from(cut, index)
        path.append(cell)
        self.laid += 1
        d["moved"] = True
        return True, ""

    def _index_in_lane(self, c, cell, lane):
        path = self.paths[c]
        for i, p in enumerate(path):
            if p == cell and (lane is None or i == 0 or rules.lane_of(rules.sub(cell, path[i - 1])) == lane):
                return i
        return len(path)

    def end(self):
        """The finger came up. A touch that did not move on the end of a line takes one cell back (tap to undo)."""
        d = self.drag
        self.drag = None
        if d is None:
            return
        c = d["c"]
        path = self.paths.get(c, [])
        if not d["moved"] and len(path) > 1:
            if d["kind"] == "head" or (d["kind"] == "port" and rules.is_connected(self.board, c, path) and path[-1] == d["start"]):
                self._remove_from(c, len(path) - 1)
        for key in [k for k, p in self.paths.items() if len(p) < 2]:
            del self.paths[key]                            # a line that is only its port is no line
        if self.paths != d["before"]:
            self._push_history(d["before"])

    # ---- whole-layout actions --------------------------------------------------------------------------------------
    def undo(self):
        if not self.history:
            return False
        before = self.history.pop()
        self.erased += sum(len(p) for p in self.paths.values())
        self.paths = _copy(before)
        self.took_back = True
        return True

    def clear(self):
        if not self.paths:
            return False
        self._push_history(_copy(self.paths))
        self.erased += sum(len(p) for p in self.paths.values())
        self.paths = {}
        self.took_back = True
        return True

    def clear_line(self, c):
        if c not in self.paths:
            return False
        self._push_history(_copy(self.paths))
        self._remove_from(c, 0)
        return True

    def load(self, paths):
        self.paths = _copy(paths)
        self.drag = None
