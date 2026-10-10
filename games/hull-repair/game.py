"""Hull Repair -- the engine's single entry point (the Robot Script / Pocket Bazaar pattern).

The view (app.js) never reads engine objects: it sends one JSON string to `handle` and draws the JSON that comes back.
`get_state()` / `load_state()` are the shared save widget's contract (planning/SAVE-BUTTON-INTEGRATION.md). Nothing here
reads a clock or a random source: a board's status is a pure function of the board and the layout.

Actions (every request is {"action": ..., ...}; every reply is the whole view):
  open                         the current view (with the board's drawing)
  pick {board}                 go to a board (its deck must be open)
  next                         go to the next board to play
  begin {x, y}                 put a finger on a cell (pick up a line, or start one from a port)
  move {cells: [[x, y], ...]}  the finger passed over these neighbouring cells, in order
  end                          the finger came up (a tap on a line's end takes one cell back); may carry a `result`
  undo | clear | clear_line {line}   take back the last touch | empty the board | empty one line
  hint                         climb one more rung of the hint ladder (nudge, hint, answer) for this board
  load_answer                  lay the stored layout on the board (after the answer rung)
  cell {x, y}                  words for one cell (the keyboard cursor)
  reset                        start over (everything)
"""

import json

import achievements
import boards
import hints
import info
import logbook
import play
import progress
import render
import rules

TALLY_KEYS = ("laid", "erased", "undos", "hints")
FLAGS = ("bridge", "valve", "mix", "retry")
MAX_COUNT = 10 ** 9


def _int(value, low=0, high=MAX_COUNT, default=0):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        return default
    return value


def _copy(paths):
    return {c: list(p) for c, p in paths.items()}


class Game:
    def __init__(self):
        self.best = {}                 # board id -> best layout (status 1 or 2)
        self.st = {}                   # board id -> best status
        self.drafts = {}               # board id -> unfinished layout
        self.current = boards.ORDER[0]
        self.tally = {key: 0 for key in TALLY_KEYS}
        self.flags = []
        self.rungs = {}                # board id -> hint rungs climbed (1 to 3)
        self.draw = None
        self.svg_due = True
        self.result = None
        self._enter(self.current)

    # ---- the current board -----------------------------------------------------------------------------------------
    @property
    def board(self):
        return boards.BY_ID[self.current]

    def _enter(self, bid):
        self.current = bid
        paths = self.drafts.get(bid)
        if paths is None:
            paths = self.best.get(bid, {})
        self.draw = play.Drawing(boards.BY_ID[bid], paths)
        self.svg_due = True
        self.result = None

    def _stash(self):
        """Keep the unfinished layout of the board being left."""
        bid, paths = self.current, self.draw.paths
        if not paths or paths == self.best.get(bid):
            self.drafts.pop(bid, None)
        else:
            self.drafts[bid] = _copy(paths)

    # ---- save ------------------------------------------------------------------------------------------------------
    def to_dict(self):
        """Only what differs from a fresh game is written, so old and new saves stay compatible."""
        self._stash()
        data = {}
        if self.current != boards.ORDER[0]:
            data["cur"] = self.current
        if self.best:
            data["best"] = {bid: rules.encode(p) for bid, p in self.best.items()}
        if self.drafts:
            data["draft"] = {bid: rules.encode(p) for bid, p in self.drafts.items()}
        tally = {k: v for k, v in self.tally.items() if v}
        if tally:
            data["tally"] = tally
        if self.flags:
            data["flags"] = list(self.flags)
        if self.rungs:
            data["rungs"] = dict(self.rungs)
        earned = achievements.earned(self.facts())
        if earned:
            data["achievements_earned"] = earned       # written for the hub's dashboard, never read back
        return data

    def load(self, data):
        """Take a saved dict, checking every field on its own; a bad field falls back to its default. A saved best is
        re-judged by the rules, so it only counts if it really patches its board."""
        data = data if isinstance(data, dict) else {}
        self.best, self.st, self.drafts = {}, {}, {}
        raw = data.get("best") if isinstance(data.get("best"), dict) else {}
        for bid in boards.ORDER:
            paths = rules.decode(boards.BY_ID[bid], raw.get(bid))
            status = rules.status(boards.BY_ID[bid], paths) if paths else 0
            if status >= 1:
                self.best[bid] = paths
                self.st[bid] = status
        raw = data.get("draft") if isinstance(data.get("draft"), dict) else {}
        for bid in boards.ORDER:
            paths = rules.decode(boards.BY_ID[bid], raw.get(bid))
            if paths and paths != self.best.get(bid):
                self.drafts[bid] = paths
        tally = data.get("tally") if isinstance(data.get("tally"), dict) else {}
        self.tally = {key: _int(tally.get(key)) for key in TALLY_KEYS}
        flags = data.get("flags")
        self.flags = [f for f in FLAGS if isinstance(flags, list) and f in flags]
        rungs = data.get("rungs") if isinstance(data.get("rungs"), dict) else {}
        self.rungs = {bid: rungs[bid] for bid in boards.ORDER if _int(rungs.get(bid), 1, 3)}
        cur = data.get("cur")
        if not (cur in boards.BY_ID and progress.board_open(self.st, cur)):
            cur = boards.ORDER[0]
        self._enter(cur)

    def facts(self):
        """What the achievements are computed from."""
        totals = progress.totals(self.st)
        facts = {"patched": totals["patched"], "restored": totals["restored"], "decks_patched": totals["decks_patched"],
                 "rung3": 1 if any(v >= 3 for v in self.rungs.values()) else 0, "laid": self.tally.get("laid", 0)}
        for flag in FLAGS:
            facts["flag_" + flag] = 1 if flag in self.flags else 0
        return facts

    # ---- the view --------------------------------------------------------------------------------------------------
    def _lines_view(self):
        b = self.board
        out = []
        for c in b.lines:
            out.append({"c": c, "name": rules.LINE_NAMES[c], "shape": rules.LINE_SHAPES[c], "state": self.draw.line_state(c),
                        "src": list(b.src[c]), "dst": list(b.dst[c]), "mixer": b.dst[c] in b.mixers})
        return out

    def _rooms_view(self):
        out = []
        for chapter in boards.CHAPTER_LIST:
            entries = []
            for bid in chapter["rooms"]:
                b = boards.BY_ID[bid]
                entries.append({"id": bid, "name": b.name, "number": b.number, "status": self.st.get(bid, 0),
                                "status_name": rules.STATUS_NAMES[self.st.get(bid, 0)], "size": "%dx%d" % (b.w, b.h),
                                "lines": len(b.lines), "current": bid == self.current})
            out.append({"id": chapter["id"], "name": chapter["name"], "blurb": chapter["blurb"], "new": chapter["new"],
                        "patched": progress.deck_patched(self.st, chapter), "restored": progress.deck_restored(self.st, chapter),
                        "total": len(chapter["rooms"]), "rooms": entries})
        return out

    def view(self, message="", ok=True, with_svg=False):
        b = self.board
        paths = self.draw.paths
        status = self.draw.status()
        missing = rules.uncovered(b, paths)
        chapter = boards.CHAPTER_LIST[b.chapter]
        view = {
            "ok": ok, "message": message,
            "board": {"id": b.id, "name": b.name, "chapter": chapter["name"], "number": b.number, "of": len(chapter["rooms"]),
                      "w": b.w, "h": b.h, "box": render.view_box(b), "pad": render.PAD, "cell": render.T,
                      "twists": list(b.twists), "new": chapter["new"] if b.number == 1 else "", "lines": self._lines_view(),
                      "status": status, "status_name": rules.STATUS_NAMES[status], "best_status": self.st.get(b.id, 0),
                      "empty": len(missing), "cells": len(b.need), "words": render.describe(b),
                      "paths": {c: [list(p) for p in cells] for c, cells in paths.items()}},
            "layer": render.lines_svg(b, paths, ghosts=hints.ghosts(b, self.rungs.get(b.id, 0))),
            "hint": hints.view(b, self.rungs.get(b.id, 0)),
            "log": logbook.entries(self.st),
            "goals": achievements.goals(self.facts()),
            "achievements": achievements.view(self.facts()),
            "map": render.station_svg(self._rooms_view()),
            "about": info.view(),
            "rooms": self._rooms_view(),
            "totals": progress.totals(self.st),
            "tally": dict(self.tally),
            "result": self.result,
            "can_undo": bool(self.draw.history),
        }
        if with_svg or self.svg_due:
            view["board"]["svg"] = render.board_svg(b)
            self.svg_due = False
        return view

    # ---- recording -------------------------------------------------------------------------------------------------
    def _count(self):
        laid, erased = self.draw.take_counts()
        self.tally["laid"] += laid
        self.tally["erased"] += erased

    def _record(self):
        """After a touch: store a better layout, note the twists a finished one used, and say what just happened."""
        bid = self.current
        status = self.draw.status()
        self.result = None
        if status < 1:
            return
        before = self.st.get(bid, 0)
        improved = status > before
        if improved:
            self.best[bid] = _copy(self.draw.paths)
            self.st[bid] = status
        used = rules.flags_of(self.board, self.draw.paths)
        if self.draw.took_back:
            used.append("retry")
        self.flags = [f for f in FLAGS if f in self.flags or f in used]
        nxt = progress.next_board(self.st, bid)
        self.result = {"log": logbook.line_for(bid), "room": self.board.name, "status": status, "status_name": rules.STATUS_NAMES[status], "new": improved, "first": before == 0 and improved,
                       "empty": len(rules.uncovered(self.board, self.draw.paths)), "next": nxt,
                       "next_name": boards.BY_ID[nxt].name if nxt else ""}


game = Game()


def handle(request_json):
    try:
        request = json.loads(request_json)
        action = request.get("action")
    except (ValueError, AttributeError):
        return json.dumps({"error": "bad request"})
    g = game
    if not isinstance(request, dict):
        return json.dumps({"error": "bad request"})
    if action == "open":
        return json.dumps(g.view(with_svg=True))
    if action == "reset":
        g.__init__()
        return json.dumps(g.view("Starting over.", with_svg=True))
    if action == "pick":
        bid = request.get("board")
        if bid not in boards.BY_ID:
            return json.dumps(g.view("There is no such room.", ok=False))
        g._stash()
        g._enter(bid)
        return json.dumps(g.view())
    if action == "next":
        nxt = progress.next_board(g.st, g.current)
        if nxt is None:
            return json.dumps(g.view("That was the last room open for now.", ok=False))
        g._stash()
        g._enter(nxt)
        return json.dumps(g.view())
    d = g.draw
    ok, message = True, ""
    if action == "begin":
        cell = _cell(request)
        if cell is None:
            ok, message = False, "That is not a cell."
        else:
            g.result = None
            ok, message = d.begin(cell)
    elif action == "move":
        cells = request.get("cells")
        if not isinstance(cells, list) or len(cells) > 200:
            ok, message = False, "Those are not cells."
        else:
            for raw in cells:
                cell = _cell({"x": raw[0], "y": raw[1]}) if isinstance(raw, list) and len(raw) == 2 else None
                if cell is None:
                    ok, message = False, "That is not a cell."
                    break
                ok, message = d.move(cell)
                if not ok:
                    break
    elif action == "end":
        d.end()
        g._count()
        g._record()
        return json.dumps(g.view())
    elif action == "undo":
        if d.undo():
            g.tally["undos"] += 1
            g.result = None
        else:
            ok, message = False, "Nothing to undo."
    elif action == "clear":
        if not d.clear():
            ok, message = False, "The board is already empty."
        g.result = None
    elif action == "clear_line":
        line = request.get("line")
        if not isinstance(line, str) or not d.clear_line(line):
            ok, message = False, "That line is already empty."
        g.result = None
    elif action == "hint":
        rung = g.rungs.get(g.current, 0)
        if rung >= 3:
            ok, message = False, "That is every rung: the answer is showing."
        else:
            g.rungs[g.current] = rung + 1
            g.tally["hints"] += 1
    elif action == "load_answer":
        if g.rungs.get(g.current, 0) < 3:
            ok, message = False, "Climb to the answer first."
        else:
            d.load_answer(g.board.solution)
            g._count()
            g._record()
            return json.dumps(g.view())
    elif action == "cell":
        cell = _cell(request)
        view = g.view()
        view["cell_text"] = render.cell_words(g.board, d.paths, cell) if cell is not None and cell in _grid(g.board) else ""
        return json.dumps(view)
    else:
        return json.dumps({"error": "unknown action " + repr(action)})
    g._count()
    if action in ("undo", "clear", "clear_line"):
        g._record()
    return json.dumps(g.view(message, ok))


def _grid(board):
    return {(x, y) for x in range(board.w) for y in range(board.h)}


def _cell(request):
    x, y = request.get("x"), request.get("y")
    if isinstance(x, bool) or isinstance(y, bool) or not isinstance(x, int) or not isinstance(y, int):
        return None
    return (x, y)


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
        refresh = getattr(js.window, "hullRepairRefresh", None)
        if refresh is not None:
            refresh()
    except Exception:
        pass
