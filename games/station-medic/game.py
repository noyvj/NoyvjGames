"""Station Medic -- the engine's single entry point (the Robot Script / Pocket Bazaar pattern).

The view (app.js) never reads engine objects: it sends one JSON string to `handle` and draws the JSON that comes back.
`get_state()` / `load_state()` are the shared save widget's contract (planning/SAVE-BUTTON-INTEGRATION.md). Nothing here reads
a clock or a random source: a shift is a pure function of its case and the list of actions taken.

Actions (every request is {"action": ..., ...}; every reply is the whole view):
  open                     the current view
  pick {shift}             go to a shift (its chapter must be open); an unfinished shift keeps its actions
  next                     go to the next shift to play
  scan {p, t}              run scan t on patient p
  treat {p, x}             give patient p treatment x
  band {p} | robot {p}     steady a shaking patient with a band, or with Tally
  isolate {p} | release {p}  cold room bed
  comfort {p}              settle a patient with comfort care (cost 1)
  borrow {item}            a spare supply from the ring's reserve (cost 1)
  restore                  back to the start of this shift (free)
  hint                     climb one more rung of the hint ladder (nudge, hint, answer)
  hint_do                  do what the answer rung says (after the answer rung)
  reset                    start over (everything)
"""

import json

import achievements
import codex
import hints
import info
import lexicon as lx
import progress
import render
import shift as sh
import solver as sv

TALLY_KEYS = ("scans", "treats", "restores", "borrows", "hints", "comforts")
GRADE_LABEL = {0: "", 1: "Rough", 2: "Steady", 3: "Clean"}
MAX_TOKENS = 300
LOG_KEEP = 40
COMPILED = {}


def compiled(sid):
    if sid not in COMPILED:
        COMPILED[sid] = sh.Case(progress.DATA[sid])
    return COMPILED[sid]


def _int(value, low=0, high=10 ** 6, default=0):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        return default
    return value


def _ordered(order, items):
    return [x for x in order if x in items]


class Game:
    def __init__(self):
        self.best = {}                       # shift id -> best grade (1 rough, 2 steady, 3 clean)
        self.runs = {}                       # shift id -> action tokens of an unfinished shift
        self.cur = progress.ORDER[0]
        self.tally = {key: 0 for key in TALLY_KEYS}
        self.rec_cured = []                  # condition ids cured at least once
        self.rec_cures = []                  # treatment ids that cured something
        self.rec_tests = []                  # scan ids run at least once
        self.rung = 0
        self._enter(self.cur)

    # ---- the current shift --------------------------------------------------------------------------------------------
    @property
    def case(self):
        return compiled(self.cur)

    def _enter(self, sid):
        self.cur = sid
        self.tokens = list(self.runs.get(sid, []))
        st, infos = sh.replay(self.case, self.tokens)
        if st is None:
            self.tokens, st, infos = [], self.case.new_state(), []
            self.runs.pop(sid, None)
        self.st = st
        self.log = [{"msg": i["msg"], "kind": i["kind"], "ok": True} for i in infos][-LOG_KEEP:]
        self.result = None
        self.rung = 0
        self.solver = None
        if self.case.done(self.st):          # a saved run that is already finished is not kept
            self.tokens, self.st, self.log = [], self.case.new_state(), []
            self.runs.pop(sid, None)

    def _solver(self):
        if self.solver is None:
            self.solver = sv.Solver(self.case)
        return self.solver

    # ---- save ------------------------------------------------------------------------------------------------------
    def to_dict(self):
        """Only what differs from a fresh game is written, so old and new saves stay compatible."""
        data = {}
        if self.cur != progress.ORDER[0]:
            data["cur"] = self.cur
        if self.best:
            data["best"] = dict(self.best)
        runs = {sid: list(t) for sid, t in self.runs.items() if t}
        if self.tokens and not self.case.done(self.st):
            runs[self.cur] = list(self.tokens)
        if runs:
            data["run"] = runs
        tally = {k: v for k, v in self.tally.items() if v}
        if tally:
            data["tally"] = tally
        if self.rec_cured:
            data["cured"] = list(self.rec_cured)
        if self.rec_cures:
            data["cures"] = list(self.rec_cures)
        if self.rec_tests:
            data["tests"] = list(self.rec_tests)
        earned = achievements.earned(self.facts())
        if earned:
            data["achievements_earned"] = earned       # written for the hub's dashboard, never read back
        return data

    def load(self, data):
        """Take a saved dict, checking every field on its own; a bad field falls back to its default."""
        data = data if isinstance(data, dict) else {}
        raw = data.get("best") if isinstance(data.get("best"), dict) else {}
        self.best = {sid: raw[sid] for sid in progress.ORDER if raw.get(sid) in (1, 2, 3) and not isinstance(raw.get(sid), bool)}
        tally = data.get("tally") if isinstance(data.get("tally"), dict) else {}
        self.tally = {key: _int(tally.get(key)) for key in TALLY_KEYS}
        for attr, key, universe in (("rec_cured", "cured", lx.COND_IDS), ("rec_cures", "cures", lx.TX_IDS), ("rec_tests", "tests", lx.TEST_IDS)):
            value = data.get(key)
            setattr(self, attr, [x for x in universe if isinstance(value, list) and x in value])
        raw_runs = data.get("run") if isinstance(data.get("run"), dict) else {}
        self.runs = {}
        for sid in progress.ORDER:
            tokens = raw_runs.get(sid)
            if isinstance(tokens, list) and 0 < len(tokens) <= MAX_TOKENS and progress.shift_open(self.best, sid):
                st, _infos = sh.replay(compiled(sid), tokens)
                if st is not None and not compiled(sid).done(st):
                    self.runs[sid] = list(tokens)
        cur = data.get("cur")
        if not (cur in progress.DATA and progress.shift_open(self.best, cur)):
            cur = progress.ORDER[0]
        self._enter(cur)

    def facts(self):
        """What the goals and achievements are computed from."""
        t = progress.totals(self.best)
        found, _total = codex.counts(self.rec_cured, self.rec_cures, self.rec_tests, self.best)
        clean = [sid for sid in progress.ORDER if self.best.get(sid) == 3]
        return {"done": t["done"], "clean": t["clean"], "chapters_done": t["chapters_done"], "scans": self.tally["scans"],
                "cold_clean": sum(1 for sid in clean if progress.DATA[sid].get("beds")),
                "tally_clean": sum(1 for sid in clean if progress.DATA[sid].get("robots")),
                "records": found, "crew_told": codex.crew_told(self.best)}

    def open_chapters(self):
        return sum(1 for c in progress.CHAPTERS if progress.chapter_open(self.best, c["index"]))

    # ---- the view --------------------------------------------------------------------------------------------------
    def _why(self, act):
        st2, info_ = self.case.apply(self.st, act)
        return (st2 is not None), ("" if st2 is not None else info_["msg"])

    def _combo_name(self, combo):
        return " + ".join(lx.COND[self.case.pool[i]]["name"] for i in combo)

    def _patient_view(self, p):
        case, st = self.case, self.st
        pd, pat = case.patients[p], st[1][p]
        cands = case.candidates(p, pat[sh.READ])
        full = (1 << len(pd.truth)) - 1
        closed = bool(pat[sh.CLOSED])
        if closed:
            outcome = ("Cured. No cost." if not pat[sh.COST] else "Cured, with a cost of %d." % pat[sh.COST]) if pat[sh.CURED] == full \
                else "Settled later by Tally's night round. Cost %d." % pat[sh.COST]
        else:
            outcome = ""
        acts = {"scan": [], "treat": []}
        if not closed:
            for t in range(len(case.tests)):
                ok, why = (False, "Already run on %s." % pd.first) if pat[sh.READ][t] != -1 else self._why(("scan", p, t))
                acts["scan"].append({"t": t, "ok": ok, "why": why})
            for x in range(len(case.tx)):
                ok, why = self._why(("treat", p, x))
                acts["treat"].append({"x": x, "ok": ok, "why": why})
        care = {}
        if not closed:
            if pd.shaking and not pat[sh.STEADY]:
                care["band"] = dict(zip(("ok", "why"), self._why(("band", p)))) if case.band else None
                care["robot"] = dict(zip(("ok", "why"), self._why(("robot", p)))) if case.robots else None
            if case.beds:
                care["isolate" if not pat[sh.ISO] else "release"] = dict(zip(("ok", "why"), self._why(("isolate" if not pat[sh.ISO] else "release", p))))
            care["comfort"] = {"ok": True, "why": ""}
        return {
            "i": p, "name": pd.name, "first": pd.first, "role": pd.role, "crew": pd.crew, "say": pd.say,
            "signs": [{"id": s, "name": lx.SIGN_NAME[s]} for s in lx.SIGN_IDS if s in pd.signs],
            "notes": [lx.TRAITS[t][1] for t in pd.traits],
            "closed": closed, "outcome": outcome, "cost": pat[sh.COST], "iso": bool(pat[sh.ISO]),
            "steady": pat[sh.STEADY], "shaking": pd.shaking,
            "readings": [{"test": lx.TEST_BY_ID[tid]["name"], "positive": lx.TEST_BY_ID[tid]["positive"], "state": ("unknown", "clear", "positive")[pat[sh.READ][t] + 1]}
                         for t, tid in enumerate(case.tests)],
            "matches": [self._combo_name(c) for c in cands], "fits": sorted({case.pool[i] for c in cands for i in c}),
            "certain": len(cands) == 1, "risky": case.maybe_spreads(p, pat[sh.READ]),
            "portrait": render.bust(pd.crew, closed), "actions": acts, "care": care,
        }

    def _sheet(self):
        case = self.case
        out = []
        for cid in case.pool:
            c = lx.COND[cid]
            out.append({"id": cid, "name": c["name"], "signs": [lx.SIGN_NAME[s] for s in lx.SIGN_IDS if s in c["signs"]],
                        "scans": [lx.TEST_BY_ID[t]["name"] + " " + lx.TEST_BY_ID[t]["positive"] for t in case.tests if t in c["findings"]],
                        "cures": [lx.TX_BY_ID[t]["name"] for t in c["cures"]], "ease": lx.TX_BY_ID[c["ease"]]["name"],
                        "spreads": c["spreads"], "shaky": lx.SHAKING in c["signs"]})
        return out

    def _cabinet(self):
        case, st = self.case, self.st
        uses = {i: [] for i in case.items}
        for t in case.tests:
            uses[lx.TEST_BY_ID[t]["item"]].append(lx.TEST_BY_ID[t]["name"] + " (scan)")
        for x in case.tx:
            uses[lx.TX_BY_ID[x]["item"]].append(lx.TX_BY_ID[x]["name"] + " (treatment)")
        if case.band:
            uses[lx.BAND_ITEM].append("Steadying (shaking patients)")
        items = [{"i": k, "id": i, "name": lx.ITEM_NAME[i], "glyph": lx.ITEM_GLYPH[i], "count": st[0][k], "start": case.stock0[k], "uses": uses[i]}
                 for k, i in enumerate(case.items)]
        return {"items": items,
                "tests": [{"t": t, "name": lx.TEST_BY_ID[tid]["name"], "item": lx.ITEM_NAME[lx.TEST_BY_ID[tid]["item"]], "glyph": lx.ITEM_GLYPH[lx.TEST_BY_ID[tid]["item"]]}
                          for t, tid in enumerate(case.tests)],
                "tx": [{"x": x, "name": lx.TX_BY_ID[tid]["name"], "item": lx.ITEM_NAME[lx.TX_BY_ID[tid]["item"]], "glyph": lx.ITEM_GLYPH[lx.TX_BY_ID[tid]["item"]],
                        "tags": sorted(lx.TX_BY_ID[tid]["tags"])} for x, tid in enumerate(case.tx)],
                "beds": case.beds, "beds_used": case.beds_used(st), "robots": case.robots, "robots_used": case.robots_used(st)}

    def _hint(self):
        if not self.rung:
            return {"rung": 0}
        act = hints.next_action(self.case, self.st, self._solver())
        d = hints.describe(self.case, self.st, act)
        out = {"rung": self.rung, "nudge": d["nudge"], "kind": d["kind"]}
        if self.rung >= 2:
            out["hint"] = d["hint"]
        if self.rung >= 3:
            out["answer"] = d["answer"]
            out["label"] = d["label"]
        return out

    def _rooms_view(self):
        out = []
        for c in progress.CHAPTERS:
            is_open = progress.chapter_open(self.best, c["index"])
            prev = progress.CHAPTERS[c["index"] - 1] if c["index"] else None
            entries = []
            for number, sid in enumerate(c["shifts"], start=1):
                d = progress.DATA[sid]
                entries.append({"id": sid, "name": d["title"], "number": number, "open": is_open, "grade": self.best.get(sid, 0),
                                "grade_name": GRADE_LABEL[self.best.get(sid, 0)], "current": sid == self.cur,
                                "patients": len(d["patients"]), "started": sid in self.runs and sid != self.cur})
            out.append({"id": c["id"], "name": c["name"], "blurb": c["blurb"], "open": is_open, "done": progress.done_in(self.best, c),
                        "total": len(c["shifts"]), "need": min(progress.OPEN_AT, len(prev["shifts"])) if prev else 0,
                        "prev_name": prev["name"] if prev else "", "shifts": entries})
        return out

    def view(self, message="", ok=True):
        case = self.case
        ch = progress.CHAPTERS[progress.CHAPTER_OF[self.cur]]
        d = progress.DATA[self.cur]
        done = case.done(self.st)
        cost = case.total_cost(self.st)
        view = {
            "ok": ok, "message": message,
            "shift": {"id": self.cur, "title": case.title, "intro": case.intro, "chapter": ch["name"], "number": ch["shifts"].index(self.cur) + 1,
                      "of": len(ch["shifts"]), "best": self.best.get(self.cur, 0), "best_name": GRADE_LABEL[self.best.get(self.cur, 0)],
                      "cost": cost, "grade_now": sh.grade_of(cost), "grade_now_name": GRADE_LABEL[sh.grade_of(cost)], "done": done,
                      "borrowed": self.st[2], "scene": render.scene(case.beds), "patients_n": len(d["patients"])},
            "patients": [self._patient_view(p) for p in range(len(case.patients))],
            "sheet": self._sheet(), "cabinet": self._cabinet(),
            "log": self.log[-LOG_KEEP:], "result": self.result,
            "rooms": self._rooms_view(), "totals": progress.totals(self.best), "tally": dict(self.tally),
            "hint": self._hint(), "about": info.view(),
            "goals": achievements.goals(self.facts(), self.open_chapters()), "achievements": achievements.view(self.facts()),
            "record": codex.view(self.rec_cured, self.rec_cures, self.rec_tests, self.best),
        }
        return view

    # ---- actions ---------------------------------------------------------------------------------------------------
    def _note(self, info_, ok=True):
        self.log.append({"msg": info_["msg"], "kind": info_["kind"], "ok": ok})
        self.log = self.log[-LOG_KEEP:]

    def do(self, act):
        """Apply a shift action. Returns (ok, message)."""
        if self.case.done(self.st):
            return False, "This shift is finished. Restore it to play it again, or go on to the next."
        if len(self.tokens) >= MAX_TOKENS:
            return False, "That is a long shift. Restore it to start again."
        st2, info_ = self.case.apply(self.st, act)
        if st2 is None:
            self.log.append({"msg": info_["msg"], "kind": "refused", "ok": False})
            self.log = self.log[-LOG_KEEP:]
            return False, info_["msg"]
        self.st = st2
        self.tokens.append(sh.to_token(act))
        self.rung = 0
        self._note(info_)
        kind = act[0]
        if kind == "scan":
            self.tally["scans"] += 1
            tid = self.case.tests[act[2]]
            if tid not in self.rec_tests:
                self.rec_tests = _ordered(lx.TEST_IDS, set(self.rec_tests) | {tid})
        elif kind == "treat":
            self.tally["treats"] += 1
            if info_["kind"] in ("cure", "partial"):
                tid = self.case.tx[act[2]]
                pd = self.case.patients[act[1]]
                cured = {c for c in pd.truth if tid in lx.COND[c]["cures"]}
                self.rec_cured = _ordered(lx.COND_IDS, set(self.rec_cured) | cured)
                self.rec_cures = _ordered(lx.TX_IDS, set(self.rec_cures) | {tid})
        elif kind == "borrow":
            self.tally["borrows"] += 1
        elif kind == "comfort":
            self.tally["comforts"] += 1
        if self.case.done(self.st):
            self._finish()
        return True, info_["msg"]

    def _finish(self):
        case = self.case
        cost = case.total_cost(self.st)
        grade = sh.grade_of(cost)
        before = self.best.get(self.cur, 0)
        new_best = grade > before
        if new_best:
            self.best[self.cur] = grade
        self.runs.pop(self.cur, None)
        nxt = progress.next_shift(self.best, self.cur)
        if grade == 3:
            line = "A clean shift: nobody needed a second round."
        elif grade == 2:
            line = "Steady. Everyone was settled, with a small cost on the shift."
        else:
            line = "Rough, but everyone is settled. Restore the shift to try for a cleaner one."
        self.result = {"cost": cost, "grade": grade, "grade_name": GRADE_LABEL[grade], "new_best": new_best, "best": self.best[self.cur],
                       "best_name": GRADE_LABEL[self.best[self.cur]], "line": line, "beats": codex.beats_for(self.cur), "next": nxt, "next_name": progress.DATA[nxt]["title"] if nxt else ""}

    def _stash(self):
        """Keep the unfinished actions of the shift being left."""
        if self.tokens and not self.case.done(self.st):
            self.runs[self.cur] = list(self.tokens)
        else:
            self.runs.pop(self.cur, None)

    def restore(self):
        self.tally["restores"] += 1
        self.tokens = []
        self.st = self.case.new_state()
        self.log = [{"msg": "The shift is restored to its start.", "kind": "restore", "ok": True}]
        self.result = None
        self.rung = 0
        self.runs.pop(self.cur, None)


game = Game()


def handle(request_json):
    try:
        request = json.loads(request_json)
    except ValueError:
        return json.dumps({"error": "bad request"})
    if not isinstance(request, dict):
        return json.dumps({"error": "bad request"})
    g = game
    action = request.get("action")
    ok, message = True, ""
    if action == "open":
        pass
    elif action == "reset":
        g.__init__()
        message = "Starting over."
    elif action == "pick":
        sid = request.get("shift")
        if sid not in progress.DATA:
            ok, message = False, "There is no such shift."
        elif not progress.shift_open(g.best, sid):
            ok, message = False, "That chapter opens once five shifts of the one before are done."
        else:
            g._stash()
            g._enter(sid)
    elif action == "next":
        nxt = progress.next_shift(g.best, g.cur)
        if nxt is None:
            ok, message = False, "That was the last shift open for now."
        else:
            g._stash()
            g._enter(nxt)
    elif action == "restore":
        g.restore()
        message = "Restored."
    elif action == "hint":
        if g.case.done(g.st):
            ok, message = False, "The shift is finished."
        elif g.rung >= 3:
            ok, message = False, "That is every rung: the answer is showing."
        else:
            g.rung += 1
            g.tally["hints"] += 1
    elif action == "hint_do":
        if g.rung < 3:
            ok, message = False, "Climb to the answer first."
        else:
            act = hints.next_action(g.case, g.st, g._solver())
            if act is None:
                g.restore()
                message = "Restored."
            else:
                ok, message = g.do(act)
    elif action in ("scan", "treat", "band", "robot", "isolate", "release", "comfort", "borrow"):
        key = "item" if action == "borrow" else "p"
        v = request.get(key)
        if action in ("scan", "treat"):
            act = (action, v, request.get("t" if action == "scan" else "x"))
        else:
            act = (action, v)
        if any(isinstance(x, bool) or not isinstance(x, int) for x in act[1:]):
            ok, message = False, "That is not something the infirmary does."
        else:
            ok, message = g.do(act)
    else:
        return json.dumps({"error": "unknown action " + repr(action)})
    return json.dumps(g.view(message, ok))


def get_state():
    return game.to_dict()


def load_state(data):
    game.load(data)
    _refresh_view()


def _refresh_view():
    """Ask the page to redraw after a save is loaded (the save widget calls load_state directly and knows nothing about this
    game's view). Under plain CPython there is no page, so this is a no-op."""
    try:
        import js
        refresh = getattr(js.window, "stationMedicRefresh", None)
        if refresh is not None:
            refresh()
    except Exception:
        pass
