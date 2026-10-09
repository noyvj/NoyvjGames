"""Robot Script -- the engine's single entry point (the Pocket Bazaar / Lexis pattern).

The view (app.js) never reads engine objects: it sends one JSON string to `handle` and draws the JSON that comes back.
`get_state()` / `load_state()` are the shared save widget's contract (planning/SAVE-BUTTON-INTEGRATION.md). Nothing here
reads a clock or a random source: a run is a pure function of the room and the list.

Actions (every request is {"action": ..., ...}; every reply is the whole view):
  open                         the current view (with the room's drawing)
  pick {room}                  go to a room (its chapter must be open)
  next                         go to the next room to play
  insert {kind, ...}           put an instruction at the cursor: F L R G P S rep until if call (name)
  cursor {list, index}         move the cursor to a gap in a list ("main", "main/2/2")
  routine {name}               switch to routine main, A or B
  remove {at}                  delete the instruction at an address ("main/2")
  move {at, delta}             swap an instruction with its neighbour (-1 up, +1 down)
  count {at, n}                set a repeat's count
  cond {at, cond}              set an until / if condition
  undo | clear                 undo the last edit | empty the list
  load_best                    put the room's best list in the editor
  run                          run the list; the reply carries the whole trace
  reset                        start over (everything)
"""

import json

import dsl
import editor
import info
import progress
import render
import rooms
import run as runner

TALLY_KEYS = ("runs", "halts", "written")
MAX_COUNT = 10 ** 6
DEFAULT_COUNT = 3

PALETTE = (
    ("F", "Forward", "Move one tile the way the robot faces"),
    ("L", "Turn left", "Turn a quarter turn left"),
    ("R", "Turn right", "Turn a quarter turn right"),
    ("G", "Pick up", "Pick up the part on this tile"),
    ("P", "Place", "Put the carried part into the socket on this tile"),
    ("S", "Switch", "Light the switch on this tile"),
    ("rep", "Repeat", "Do the steps inside a set number of times"),
    ("until", "Until", "Keep doing the steps inside until something is true"),
    ("if", "If", "Do one set of steps if something is true, another if not"),
    ("callA", "Call A", "Run routine A"),
    ("callB", "Call B", "Run routine B"),
)
COND_LABELS = {
    "blocked": ("the way ahead is blocked", "the way ahead is clear"),
    "part": ("there is a part here", "there is no part here"),
    "socket": ("there is an empty socket here", "there is no empty socket here"),
    "switch": ("there is an unlit switch here", "there is no unlit switch here"),
    "carrying": ("the robot is carrying a part", "the robot is carrying nothing"),
    "exit": ("the robot is on the exit", "the robot is not on the exit"),
}
COND_OPTIONS = [{"value": c, "label": COND_LABELS[c][0]} for c in dsl.CONDS] + \
               [{"value": "!" + c, "label": COND_LABELS[c][1]} for c in dsl.CONDS]
MEDAL_NAMES = {0: "none", 1: "bronze", 2: "silver", 3: "gold"}


def _int(value, low=0, high=MAX_COUNT, default=0):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        return default
    return value


def _stmt_for(request):
    kind = request.get("kind")
    if kind in dsl.ACTIONS:
        return kind
    if kind == "rep":
        n = request.get("n", DEFAULT_COUNT)
        return ["rep", n if isinstance(n, int) and not isinstance(n, bool) else DEFAULT_COUNT, []]
    if kind == "until":
        cond = request.get("cond", "blocked")
        return ["until", cond if dsl.cond_ok(cond) else "blocked", []]
    if kind == "if":
        cond = request.get("cond", "part")
        return ["if", cond if dsl.cond_ok(cond) else "part", [], []]
    if kind in ("callA", "callB"):
        return ["call", kind[-1]]
    return None


class Game:
    def __init__(self):
        self.best = {}                 # room id -> {"n": steps, "t": program text}
        self.drafts = {}               # room id -> program (unfinished lists)
        self.current = rooms.ORDER[0]
        self.tally = {key: 0 for key in TALLY_KEYS}
        self.flags = []
        self.bumped = []               # rooms where a run has halted: for "learned from a bump"
        self.ed = None
        self.svg_due = True
        self._enter(self.current)

    # ---- the current room ------------------------------------------------------------------------------------------
    @property
    def room(self):
        return rooms.BY_ID[self.current]

    def _enter(self, rid):
        self.current = rid
        r = rooms.BY_ID[rid]
        prog = self.drafts.get(rid)
        if prog is None and rid in self.best:
            prog = dsl.parse(self.best[rid]["t"])
        self.ed = editor.Editor(prog, r.allow)
        self.svg_due = True

    def _stash(self):
        """Keep the unfinished list of the room being left."""
        rid = self.current
        if self.ed.is_empty() or (rid in self.best and dsl.to_text(self.ed.prog) == self.best[rid]["t"]):
            self.drafts.pop(rid, None)
        else:
            self.drafts[rid] = dsl.copy(self.ed.prog)

    # ---- save ------------------------------------------------------------------------------------------------------
    def to_dict(self):
        """Only what differs from a fresh game is written, so old and new saves stay compatible."""
        self._stash()
        data = {}
        if self.current != rooms.ORDER[0]:
            data["cur"] = self.current
        if self.best:
            data["best"] = {rid: {"n": e["n"], "t": e["t"]} for rid, e in self.best.items()}
        if self.drafts:
            data["draft"] = {rid: dsl.to_text(p) for rid, p in self.drafts.items()}
        tally = {k: v for k, v in self.tally.items() if v}
        if tally:
            data["tally"] = tally
        if self.flags:
            data["flags"] = list(self.flags)
        if self.bumped:
            data["bumped"] = list(self.bumped)
        return data

    def load(self, data):
        """Take a saved dict, checking every field on its own; a bad field falls back to its default. A saved best is
        re-run, so it only counts if it really clears its room at the size it claims."""
        data = data if isinstance(data, dict) else {}
        self.best = {}
        raw = data.get("best") if isinstance(data.get("best"), dict) else {}
        for rid in rooms.ORDER:
            entry = raw.get(rid)
            if not isinstance(entry, dict) or not isinstance(entry.get("t"), str):
                continue
            prog = dsl.parse(entry["t"])
            r = rooms.BY_ID[rid]
            if prog is None or dsl.check(prog, r.allow) or entry.get("n") != dsl.size(prog):
                continue
            if runner.run(r.layout, prog).status != "cleared":
                continue
            self.best[rid] = {"n": dsl.size(prog), "t": dsl.to_text(prog)}
        self.drafts = {}
        raw = data.get("draft") if isinstance(data.get("draft"), dict) else {}
        for rid in rooms.ORDER:
            text = raw.get(rid)
            prog = dsl.parse(text) if isinstance(text, str) else None
            if prog is not None and not dsl.check(prog, rooms.BY_ID[rid].allow) and dsl.size(prog):
                self.drafts[rid] = prog
        tally = data.get("tally") if isinstance(data.get("tally"), dict) else {}
        self.tally = {key: _int(tally.get(key)) for key in TALLY_KEYS}
        flags = data.get("flags")
        self.flags = [f for f in FLAGS if isinstance(flags, list) and f in flags]
        bumped = data.get("bumped")
        self.bumped = [rid for rid in rooms.ORDER if isinstance(bumped, list) and rid in bumped]
        cur = data.get("cur")
        cur = cur if cur in rooms.BY_ID and progress.room_open(self.best, cur) else rooms.ORDER[0]
        self._enter(cur)

    # ---- the view --------------------------------------------------------------------------------------------------
    def _list_view(self, items, laddr):
        out = []
        for i, stmt in enumerate(items):
            a = editor.fmt_addr(laddr + (i,))
            if isinstance(stmt, str):
                out.append({"a": a, "k": stmt, "label": dsl.ACTION_NAMES[stmt]})
            elif stmt[0] == "rep":
                out.append({"a": a, "k": "rep", "n": stmt[1], "body": self._body(stmt[2], laddr + (i, 2))})
            elif stmt[0] == "until":
                out.append({"a": a, "k": "until", "c": stmt[1], "body": self._body(stmt[2], laddr + (i, 2))})
            elif stmt[0] == "if":
                out.append({"a": a, "k": "if", "c": stmt[1], "then": self._body(stmt[2], laddr + (i, 2)),
                            "else": self._body(stmt[3], laddr + (i, 3))})
            else:
                out.append({"a": a, "k": "call", "name": stmt[1]})
        return out

    def _body(self, items, laddr):
        return {"list": editor.fmt_addr(laddr), "items": self._list_view(items, laddr)}

    def _program_view(self):
        prog = self.ed.prog
        r = self.room
        ops = r.toolbox()
        active = self.ed.cursor[0][0]
        names = ["main"] + [n for n in ("A", "B") if n in ops]
        routines = []
        for name in names:
            body = self._body(prog.get(name, []), (name,))
            body["name"] = name
            body["label"] = "Main" if name == "main" else "Routine " + name
            body["size"] = dsl._count(prog.get(name, []))
            routines.append(body)
        palette = []
        for kind, label, detail in PALETTE:
            token = kind if not kind.startswith("call") else kind[-1]
            if token not in ops and kind not in ops:
                continue
            reason = self.ed.can_insert(_stmt_for({"kind": kind}))
            palette.append({"k": kind, "label": label, "detail": detail, "ok": reason is None, "why": reason or ""})
        return {"routines": routines, "active": active, "size": dsl.size(prog), "cursor": {"list": editor.fmt_addr(self.ed.cursor[0]),
                "index": self.ed.cursor[1]}, "palette": palette, "can_undo": bool(self.ed.history), "max": dsl.MAX_SIZE,
                "conds": COND_OPTIONS if ("until" in ops or "if" in ops) else []}

    def _rooms_view(self):
        out = []
        for chapter in rooms.CHAPTER_LIST:
            idx = chapter["index"]
            is_open = progress.chapter_open(self.best, idx)
            entries = []
            for number, rid in enumerate(chapter["rooms"], start=1):
                r = rooms.BY_ID[rid]
                entries.append({"id": rid, "name": r.name, "number": number, "par": r.par, "open": is_open,
                                "medal": progress.medal_of(self.best, rid), "best": self.best[rid]["n"] if rid in self.best else None,
                                "current": rid == self.current})
            prev = rooms.CHAPTER_LIST[idx - 1] if idx else None
            need = min(progress.OPEN_AT, len(prev["rooms"])) if prev else 0
            out.append({"id": chapter["id"], "name": chapter["name"], "blurb": chapter["blurb"], "open": is_open,
                        "cleared": progress.cleared_in(self.best, chapter), "total": len(chapter["rooms"]), "need": need,
                        "prev_name": prev["name"] if prev else "", "rooms": entries})
        return out

    def view(self, message="", ok=True, run_result=None, with_svg=False):
        r = self.room
        chapter = rooms.CHAPTER_LIST[r.chapter]
        words_lines, words_rows = render.describe(r.layout)
        medal = progress.medal_of(self.best, r.id)
        goal_rows = [{"id": g["id"], "label": g["label"], "met": False} for g in _goal_labels(r.layout)]
        view = {
            "ok": ok, "message": message,
            "room": {"id": r.id, "name": r.name, "chapter": chapter["name"], "number": r.number, "of": len(chapter["rooms"]),
                     "intro": r.intro, "nudge": r.nudge, "par": r.par, "silver": r.silver, "best": self.best[r.id]["n"] if r.id in self.best else None,
                     "medal": medal, "medal_name": MEDAL_NAMES[medal], "goals": goal_rows,
                     "words": {"lines": words_lines, "rows": words_rows}, "start": list(r.layout.start),
                     "w": r.layout.w, "h": r.layout.h, "has_best": r.id in self.best},
            "program": self._program_view(),
            "rooms": self._rooms_view(),
            "totals": progress.totals(self.best),
            "tally": dict(self.tally),
            "about": info.view(),
            "run": run_result,
        }
        if with_svg or self.svg_due:
            view["room"]["svg"] = render.room_svg(r.layout, r.name)
            self.svg_due = False
        return view

    # ---- actions ---------------------------------------------------------------------------------------------------
    def do_run(self):
        r = self.room
        prog = self.ed.prog
        size = dsl.size(prog)
        result = runner.run(r.layout, prog)
        self.tally["runs"] += 1
        new_best = False
        medal = 0
        if result.status in ("halt", "loop"):
            self.tally["halts"] += 1
            if r.id not in self.bumped:
                self.bumped = [x for x in rooms.ORDER if x in self.bumped or x == r.id]
        if result.cleared:
            before = self.best.get(r.id)
            if before is None or size < before["n"]:
                self.best[r.id] = {"n": size, "t": dsl.to_text(prog)}
                new_best = True
            medal = progress.medal_of(self.best, r.id)
            self._note_flags(r.id, prog)
        trace = {"status": result.status, "message": result.message, "frames": [list(f) for f in result.frames],
                 "actions": result.actions, "size": size, "par": r.par, "silver": r.silver, "cleared": result.cleared,
                 "goals": result.goals, "at": result.at, "medal": medal, "medal_name": MEDAL_NAMES[medal], "new_best": new_best,
                 "best": self.best[r.id]["n"] if r.id in self.best else None}
        trace["next"] = progress.next_room(self.best, r.id) if result.cleared else None
        trace["next_name"] = rooms.BY_ID[trace["next"]].name if trace["next"] else ""
        return trace

    def _note_flags(self, rid, prog):
        used = dsl.uses(prog)
        new = []
        if "rep" in used:
            new.append("rep")
        if "call" in used:
            new.append("call")
        if used & {"if", "until"}:
            new.append("branch")
        if rid in self.bumped:
            new.append("comeback")
        self.flags = [f for f in FLAGS if f in self.flags or f in new]


FLAGS = ("rep", "call", "branch", "comeback")


def _goal_labels(layout):
    import room as roomlib
    return roomlib.goals(layout, layout.initial())


game = Game()


def _ref_check(ed):
    return ed.last_error


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
        rid = request.get("room")
        if rid not in rooms.BY_ID:
            return json.dumps(g.view("There is no such room.", ok=False))
        if not progress.room_open(g.best, rid):
            return json.dumps(g.view("That chapter opens once five rooms of the one before are cleared.", ok=False))
        g._stash()
        g._enter(rid)
        return json.dumps(g.view())
    if action == "next":
        nxt = progress.next_room(g.best, g.current)
        if nxt is None:
            return json.dumps(g.view("That was the last room open for now.", ok=False))
        g._stash()
        g._enter(nxt)
        return json.dumps(g.view())
    ed = g.ed
    ok, message = True, ""
    if action == "insert":
        stmt = _stmt_for(request)
        if stmt is None:
            return json.dumps(g.view("That is not an instruction.", ok=False))
        if ed.insert(stmt):
            g.tally["written"] += 1
        else:
            ok, message = False, ed.last_error
    elif action == "cursor":
        addr = editor.parse_addr(request.get("list"))
        if addr is None or not ed.set_cursor(addr, request.get("index")):
            ok, message = False, "That place is not in the list."
    elif action == "routine":
        if request.get("name") not in dsl.ROUTINES or (request.get("name") != "main" and request.get("name") not in g.room.toolbox()) \
                or not ed.go_routine(request.get("name")):
            ok, message = False, "That routine is not available here."
    elif action in ("remove", "move", "count", "cond"):
        addr = editor.parse_addr(request.get("at"))
        done = False
        if addr is not None and len(addr) >= 2 and len(addr) % 2 == 0:
            if action == "remove":
                done = ed.remove(addr)
            elif action == "move":
                done = ed.move(addr, request.get("delta"))
            elif action == "count":
                done = ed.set_count(addr, request.get("n"))
            else:
                done = ed.set_cond(addr, request.get("cond")) if dsl.cond_ok(request.get("cond")) else False
        if not done:
            ok, message = False, ed.last_error or "That could not be changed."
    elif action == "undo":
        if not ed.undo():
            ok, message = False, "Nothing to undo."
    elif action == "clear":
        ed.clear()
    elif action == "load_best":
        prog = dsl.parse(g.best[g.current]["t"]) if g.current in g.best else None
        if prog is None or not ed.load(prog):
            ok, message = False, "There is no best list for this room yet."
    elif action == "run":
        trace = g.do_run()
        return json.dumps(g.view(trace["message"], ok=trace["cleared"] or trace["status"] == "short", run_result=trace))
    else:
        return json.dumps({"error": "unknown action " + repr(action)})
    return json.dumps(g.view(message, ok))


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
        refresh = getattr(js.window, "robotScriptRefresh", None)
        if refresh is not None:
            refresh()
    except Exception:
        pass
