"""Mirror Lab -- the engine's single entry point (the Rule Finder / Hull Repair pattern).

The view (app.js) never reads engine objects: it sends one JSON string to `handle` and draws the JSON that comes back. `get_state()` /
`load_state()` are the shared save widget's contract (planning/SAVE-BUTTON-INTEGRATION.md). Nothing here reads a clock or a random
source: where a beam goes is a pure function of the bench and the pieces on it.

Actions (every request is {"action": ..., ...}; every reply is the whole view):
  open                          the current view
  pick {bench}                  go to a bench (it must be in an open chapter)
  next                          go to the next open bench not yet cleared
  place {r, c, piece}           put a piece from the tray on a slot (an occupied slot gets its piece swapped back to the tray)
  flip {r, c}                   flip a placed mirror or prism
  pickup {r, c}                 take a placed piece back to the tray
  move {r, c, to_r, to_c}       pick a piece up and put it on another empty slot
  clear_bench                   take every piece back to the tray
  hint                          open the next rung of this bench's hint ladder (nudge, hint, answer); counted in the tally
  place_answer                  put the stored answer on the bench (only once the answer rung is open; never needed to clear anything)
  difficulty {level}            easy | normal | hard, told to the engine by the page (a per-browser choice, never saved)
  reset                         start over (everything)
"""

import json

import benches
import goals
import hints
import info
import logbook
import optics
import progress
import render
import trace_text

TALLY_KEYS = ("placed", "picked", "flips", "hints")
MAX_COUNT = 10 ** 9
SCHEMA = 1
# AN-17: easy | normal | hard, told to the engine by the page and never saved. Normal is the game as designed; the level only changes
# the hint ladder (see hints.py), never a bench, a rule, a record or a tag.
difficulty = "normal"
DIFFICULTIES = ("easy", "normal", "hard")


def _int(value, low=0, high=MAX_COUNT, default=None):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        return default
    return value


def _layout_to_list(layout):
    return [[r, c, optics.PIECE_CODE[piece], state] for (r, c), (piece, state) in sorted(layout.items())]


def _list_to_layout(bench, raw, strict):
    """Read a saved list of [r, c, code, state] against this bench. Every placement is checked on its own: a bad one is dropped, or (strict)
    makes the whole list invalid (returns None). Pieces beyond what the tray holds are dropped, in row-major order."""
    layout, counts = {}, {}
    if not isinstance(raw, list):
        return None if strict else {}
    for item in raw[:200]:
        ok = isinstance(item, (list, tuple)) and len(item) == 4
        r = _int(item[0]) if ok else None
        c = _int(item[1]) if ok else None
        piece = optics.CODE_PIECE.get(item[2]) if ok and isinstance(item[2], str) else None
        state = _int(item[3]) if ok else None
        if (r is None or c is None or piece is None or state is None or (r, c) not in bench.board.slots or (r, c) in layout
                or state >= optics.PIECE_STATES[piece] or counts.get(piece, 0) >= bench.tray.get(piece, 0)):
            if strict:
                return None
            continue
        layout[(r, c)] = (piece, state)
        counts[piece] = counts.get(piece, 0) + 1
    return layout


class Game:
    def __init__(self):
        self.cleared = {}                # bench id -> best clearing layout {(r, c): (piece, state)}
        self.layouts = {}                # bench id -> the layout currently on the bench
        self.tally = {key: 0 for key in TALLY_KEYS}
        self.used = set()                # shelf page ids filled (first use of a kind of piece)
        self.rungs = {}                  # bench id -> hint rungs opened (1 to 3)
        self.current = benches.ORDER[0]
        self.verdict = None              # the last clearing result (not saved)
        self.last_trace = None

    # ---- the current bench -----------------------------------------------------------------------------------------
    @property
    def bench(self):
        return benches.BY_ID[self.current]

    @property
    def layout(self):
        return self.layouts.setdefault(self.current, {})

    def _trace(self):
        self.last_trace = optics.trace(self.bench.board, self.layout)
        return self.last_trace

    def _enter(self, bench_id):
        self.current = bench_id
        self.verdict = None

    def _stock(self, piece):
        return self.bench.tray.get(piece, 0) - sum(1 for p, _s in self.layout.values() if p == piece)

    # ---- save ------------------------------------------------------------------------------------------------------
    def to_dict(self):
        """Only what differs from a fresh game is written, so old and new saves stay compatible. A fresh game saves as {}."""
        data = {}
        if self.current != benches.ORDER[0]:
            data["cur"] = self.current
        if self.cleared:
            data["cleared"] = {bid: _layout_to_list(layout) for bid, layout in self.cleared.items()}
        layouts = {bid: _layout_to_list(layout) for bid, layout in self.layouts.items() if layout}
        if layouts:
            data["layouts"] = layouts
        tally = {k: v for k, v in self.tally.items() if v}
        if tally:
            data["tally"] = tally
        used = [fid for fid, _t, _p, _w in logbook.SHELF if fid in self.used]
        if used:
            data["used"] = used
        rungs = {bid: n for bid, n in self.rungs.items() if n}
        if rungs:
            data["rungs"] = rungs
        if data:
            data["schema"] = SCHEMA
        return data

    def load(self, data):
        """Take a saved dict, checking every field on its own; a bad field falls back to its default. A saved clear only counts if the
        layout it stores really lights the bench when traced here, so the save cannot claim a bench the rules do not give."""
        data = data if isinstance(data, dict) else {}
        self.cleared, self.layouts = {}, {}
        raw = data.get("cleared") if isinstance(data.get("cleared"), dict) else {}
        for bench in benches.ALL_BENCHES:
            layout = _list_to_layout(bench, raw.get(bench.id), strict=True) if bench.id in raw else None
            if layout and optics.trace(bench.board, layout).ok:
                self.cleared[bench.id] = layout
        raw = data.get("layouts") if isinstance(data.get("layouts"), dict) else {}
        for bench in benches.ALL_BENCHES:
            if bench.id in raw:
                layout = _list_to_layout(bench, raw[bench.id], strict=False)
                if layout:
                    self.layouts[bench.id] = layout
        tally = data.get("tally") if isinstance(data.get("tally"), dict) else {}
        self.tally = {key: _int(tally.get(key), default=0) for key in TALLY_KEYS}
        raw = data.get("used") if isinstance(data.get("used"), list) else []
        known = {fid for fid, _t, _p, _w in logbook.SHELF}
        self.used = {x for x in raw if isinstance(x, str) and x in known}
        for layout in list(self.cleared.values()) + list(self.layouts.values()):       # a page is filled by any piece the save shows in use
            self.used |= logbook.families_used(p for p, _s in layout.values())
        raw = data.get("rungs") if isinstance(data.get("rungs"), dict) else {}
        self.rungs = {bid: _int(n, 1, 3) for bid, n in raw.items() if bid in benches.BY_ID and _int(n, 1, 3)}
        cur = data.get("cur")
        self._enter(cur if isinstance(cur, str) and progress.bench_open(self.cleared, cur) else benches.ORDER[0])

    # ---- the view --------------------------------------------------------------------------------------------------
    def _chapters_view(self):
        out = []
        for ch in benches.CHAPTERS:
            items = []
            for b in ch["benches"]:
                layout = self.cleared.get(b.id)
                items.append({"id": b.id, "name": b.name, "number": b.number, "cleared": layout is not None,
                              "best": len(layout) if layout else None, "fewest": bool(layout) and len(layout) <= b.par,
                              "current": b.id == self.current, "par": b.par})
            out.append({"number": ch["number"], "name": ch["name"], "blurb": ch["blurb"], "open": progress.chapter_open(self.cleared, ch["number"]),
                        "cleared": progress.chapter_cleared(self.cleared, ch["number"]), "need": benches.OPEN_AT, "benches": items})
        return out

    def _bench_view(self, tr, chapters):
        b = self.bench
        layout = self.layout
        placed = [{"r": r, "c": c, "piece": p, "state": s, "words": render.piece_words(p, s), "flips": optics.PIECE_STATES[p] > 1}
                  for (r, c), (p, s) in sorted(layout.items())]
        tray = []
        for piece in optics.PIECES:
            if piece in b.tray:
                tray.append({"piece": piece, "label": optics.PIECE_LABEL[piece], "icon": render.piece_icon(piece), "left": self._stock(piece),
                             "total": b.tray[piece], "flips": optics.PIECE_STATES[piece] > 1})
        done = self.cleared.get(b.id)
        label = trace_text.bench_label(b, tr, layout)
        hint = hints.view(b, self.rungs.get(b.id, 0), difficulty)
        ghosts = [(g["r"], g["c"], g["piece"], g["state"]) for g in hint["ghosts"] if layout.get((g["r"], g["c"])) != (g["piece"], g["state"])]
        return {
            "id": b.id, "name": b.name, "number": b.number, "of": len(benches.CHAPTERS[b.chapter - 1]["benches"]), "chapter": b.chapter,
            "chapter_name": benches.CHAPTERS[b.chapter - 1]["name"], "blurb": benches.CHAPTERS[b.chapter - 1]["blurb"],
            "brief": trace_text.brief(b), "rows": list(b.rows), "w": b.board.w, "h": b.board.h, "cell": render.U, "pad": render.PAD,
            "svg": render.bench_svg(b.board, layout, tr, label, ghosts), "label": label, "hint": hint, "tray": tray, "placed": placed,
            "sensors": trace_text.sensor_lines(b.board, tr), "emitters": trace_text.emitter_lines(b.board),
            "lit": len(tr.lit), "need": len(b.board.required), "decoys_hit": len(tr.dark_hit), "solved_now": tr.ok,
            "status": "cleared" if done else "open", "best": len(done) if done else None, "par": b.par,
            "fewest": bool(done) and len(done) <= b.par, "pieces": len(layout), "tray_size": b.tray_size,
            "unique": b.unique, "line": b.line if done else "", "next": progress.next_bench(self.cleared, b.id),
        }

    def view(self, message="", ok=True):
        tr = self._trace()
        chapters = self._chapters_view()
        log = {"shelf": logbook.shelf(self.used), "cards": logbook.cards(self.cleared), "summary": logbook.summary(self.used, self.cleared)}
        return {"ok": ok, "message": message, "bench": self._bench_view(tr, chapters), "verdict": self.verdict, "chapters": chapters,
                "map": render.map_svg(chapters), "log": log, "totals": progress.totals(self.cleared), "tally": dict(self.tally),
                "goals": goals.next_goals(self.cleared, self.used), "goals_summary": goals.summary(self.cleared, self.used), "info": info.view(),
                "difficulty": difficulty}

    # ---- judging a change ------------------------------------------------------------------------------------------
    def _judge(self):
        """After any change to the layout: has the bench just been cleared, or cleared with fewer pieces than before?"""
        tr = self._trace()
        self.verdict = None
        layout = self.layout
        if not (tr.ok and layout):
            return tr
        b = self.bench
        prior = self.cleared.get(b.id)
        n = len(layout)
        if prior is None or n < len(prior):
            self.cleared[b.id] = dict(layout)
            self.verdict = {"kind": "cleared" if prior is None else "improved", "pieces": n, "par": b.par, "fewest": n <= b.par,
                            "previous": None if prior is None else len(prior), "line": b.line, "next": progress.next_bench(self.cleared, b.id)}
        else:
            self.verdict = {"kind": "again", "pieces": n, "par": b.par, "fewest": len(self.cleared[b.id]) <= b.par, "best": len(self.cleared[b.id]),
                            "line": b.line, "next": progress.next_bench(self.cleared, b.id)}
        return tr

    def _changed(self, message):
        tr = self._judge()
        line = "%s lit." % trace_text.sensors_count(len(tr.lit), len(self.bench.board.required))
        if tr.dark_hit:
            line += " A decoy is lit."
        if self.verdict and self.verdict["kind"] in ("cleared", "improved"):
            line += " Bench cleared." if self.verdict["kind"] == "cleared" else " Cleared again with fewer pieces."
        return self.view((message + " " + line).strip())

    def _cell(self, r, c):
        r, c = _int(r), _int(c)
        if r is None or c is None or not self.bench.board.inside(r, c):
            return None
        return (r, c)

    # ---- actions ---------------------------------------------------------------------------------------------------
    def place(self, r, c, piece):
        cell = self._cell(r, c)
        if cell is None:
            return self.view("That square is not on the bench.", ok=False)
        if not isinstance(piece, str) or piece not in optics.PIECE_STATES or piece not in self.bench.tray:
            return self.view("That piece is not in this bench's tray.", ok=False)
        if cell not in self.bench.board.slots:
            return self.view("%s is not a slot. Pieces go on the dashed squares." % optics.cell_name(*cell).capitalize(), ok=False)
        here = self.layout.get(cell)
        if here is not None and here[0] == piece:
            return self.view("There is already a %s at %s." % (optics.piece_name(piece), optics.cell_name(*cell)), ok=False)
        if self._stock(piece) <= 0:
            return self.view("The tray has no %s left. Pick one up to move it." % optics.piece_name(piece), ok=False)
        swapped = ""
        if here is not None:
            self.tally["picked"] += 1
            swapped = " The %s went back to the tray." % optics.piece_name(here[0])
        self.layout[cell] = (piece, 0)
        self.tally["placed"] += 1
        self.used |= logbook.families_used([piece])
        sw = render.state_words(piece, 0)
        return self._changed("%s placed at %s%s.%s" % (optics.PIECE_LABEL[piece], optics.cell_name(*cell), ", " + sw if sw else "", swapped))

    def flip(self, r, c):
        cell = self._cell(r, c)
        here = self.layout.get(cell) if cell else None
        if here is None:
            return self.view("There is no piece there to flip.", ok=False)
        piece, state = here
        if optics.PIECE_STATES[piece] < 2:
            return self.view("A %s does not flip." % optics.piece_name(piece), ok=False)
        self.layout[cell] = (piece, (state + 1) % optics.PIECE_STATES[piece])
        self.tally["flips"] += 1
        return self._changed("%s at %s flipped: now %s." % (optics.PIECE_LABEL[piece], optics.cell_name(*cell), render.state_words(piece, self.layout[cell][1])))

    def pickup(self, r, c):
        cell = self._cell(r, c)
        here = self.layout.get(cell) if cell else None
        if here is None:
            return self.view("There is no piece there to pick up.", ok=False)
        del self.layout[cell]
        self.tally["picked"] += 1
        return self._changed("%s picked up from %s." % (optics.PIECE_LABEL[here[0]], optics.cell_name(*cell)))

    def move(self, r, c, to_r, to_c):
        src, dst = self._cell(r, c), self._cell(to_r, to_c)
        here = self.layout.get(src) if src else None
        if here is None:
            return self.view("There is no piece there to move.", ok=False)
        if dst is None or dst not in self.bench.board.slots:
            return self.view("Pieces go on the dashed squares.", ok=False)
        if dst == src:
            return self.view("", ok=True)
        if dst in self.layout:
            return self.view("That slot already holds a piece.", ok=False)
        del self.layout[src]
        self.layout[dst] = here
        self.tally["picked"] += 1
        self.tally["placed"] += 1
        return self._changed("%s moved to %s." % (optics.PIECE_LABEL[here[0]], optics.cell_name(*dst)))

    def hint(self):
        """Open the next rung of this bench's ladder. Free, never touches a record, counted once per press."""
        b = self.bench
        rung = min(self.rungs.get(b.id, 0), hints.rung_cap(difficulty))
        new = hints.next_rung(rung, difficulty)
        if new is None:
            if difficulty == "hard":
                return self.view("Hard has no answer step: the nudge and the hint are every hint there is. Switch to Normal or Easy in the Difficulty panel if you want it.", ok=False)
            return self.view("That is every hint there is for this bench.", ok=False)
        self.rungs[b.id] = new
        self.tally["hints"] += 1
        words = {1: "Nudge opened.", 2: "Hint opened: one piece is drawn as a ghost on the bench.", 3: "The answer is drawn as ghosts on the bench."}[new]
        if new == 2 and rung == 0:
            words = "Nudge and hint opened: one piece is drawn as a ghost on the bench."
        return self.view(words)

    def place_answer(self):
        """Put the stored solution on the bench, replacing what is there (every piece goes back to the tray first). Counted like any placing."""
        b = self.bench
        if self.rungs.get(b.id, 0) < 3 or difficulty == "hard":
            return self.view("The answer step is not open." if difficulty != "hard" else "Hard has no answer step.", ok=False)
        self.tally["picked"] += len(self.layout)
        self.layout.clear()
        for r, c, piece, state in b.solution:
            self.layout[(r, c)] = (piece, state)
            self.tally["placed"] += 1
            self.used |= logbook.families_used([piece])
        return self._changed("The stored answer is on the bench, %d piece%s." % (len(b.solution), "" if len(b.solution) == 1 else "s"))

    def clear_bench(self):
        n = len(self.layout)
        if not n:
            return self.view("The bench is already empty.", ok=False)
        self.tally["picked"] += n
        self.layout.clear()
        return self._changed("Every piece is back in the tray.")


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
        bid = request.get("bench")
        if not isinstance(bid, str) or bid not in benches.BY_ID:
            return json.dumps(g.view("There is no such bench.", ok=False))
        if not progress.bench_open(g.cleared, bid):
            return json.dumps(g.view("That chapter opens when %d benches of the one before are cleared." % benches.OPEN_AT, ok=False))
        g._enter(bid)
        return json.dumps(g.view())
    if action == "next":
        nxt = progress.next_bench(g.cleared, g.current)
        if nxt is None:
            return json.dumps(g.view("Every open bench is cleared.", ok=False))
        g._enter(nxt)
        return json.dumps(g.view())
    if action == "place":
        return json.dumps(g.place(request.get("r"), request.get("c"), request.get("piece")))
    if action == "flip":
        return json.dumps(g.flip(request.get("r"), request.get("c")))
    if action == "pickup":
        return json.dumps(g.pickup(request.get("r"), request.get("c")))
    if action == "move":
        return json.dumps(g.move(request.get("r"), request.get("c"), request.get("to_r"), request.get("to_c")))
    if action == "clear_bench":
        return json.dumps(g.clear_bench())
    if action == "hint":
        return json.dumps(g.hint())
    if action == "place_answer":
        return json.dumps(g.place_answer())
    if action == "difficulty":
        global difficulty
        level = request.get("level")
        if level not in DIFFICULTIES:
            return json.dumps(g.view("That is not a difficulty.", ok=False))
        difficulty = level
        return json.dumps(g.view())
    return json.dumps({"error": "unknown action " + repr(action)})


def get_state():
    return game.to_dict()


def load_state(data):
    game.load(data)
    _refresh_view()


def _refresh_view():
    """Ask the page to redraw after a save is loaded (the save widget calls load_state directly and knows nothing about this game's view).
    Under plain CPython there is no page, so this is a no-op."""
    try:
        import js
        refresh = getattr(js.window, "mirrorLabRefresh", None)
        if refresh is not None:
            refresh()
    except Exception:
        pass
