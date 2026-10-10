"""Evidence Hunt -- the engine's single entry point (the Station Medic / Robot Script pattern).

The view (app.js) never reads engine objects: it sends one JSON string to `handle` and draws the JSON that comes back.
`get_state()` / `load_state()` are the shared save widget's contract (planning/SAVE-BUTTON-INTEGRATION.md). Nothing here reads
a clock or a random source: a case is a pure function of its data and the list of actions taken.

Actions (every request is {"action": ..., ...}; every reply is the whole view):
  open                     the current view
  pick {case}              go to a case (its chapter must be open); an unfinished case keeps its actions
  next                     go to the next case to play
  pack {e}                 put equipment e in the bag, or take it out (before the first reading of a trip)
  van                      back to the van: an empty bag, and a second trip if readings were taken
  go {room}                walk into a room (free)
  use {e}                  take a reading with equipment e in the current room
  look                     look closely at the keepsake in the current room
  accuse {kinds: [i]}      name the spirit (or both spirits)
  cover                    cover or uncover the sheet ("from memory")
  return                   return the keepsake after the case is solved
  restore                  back to the start of this case (free)
  hint                     climb one more rung of the hint ladder (nudge, hint, answer)
  hint_do                  do what the answer rung says (after the answer rung)
  reset                    start over (everything)
"""

import json

import achievements
import casework as cw
import codex
import gen
import hints
import houses
import info
import lexicon as lx
import progress
import render

TALLY_KEYS = ("rooms", "readings", "accusations", "wrong", "restores", "hints", "trips")
GRADE_LABEL = {0: "", 1: "Rough", 2: "Steady", 3: "Clean"}
MAX_TOKENS = 400
LOG_KEEP = 40
KEEP_PRACTICE_RUNS = 3
MAX_DONE_CODES = 200
COMPILED = {}


def data_of(cid):
    """The case data for an authored case id or a practice id; None for anything else."""
    return progress.DATA.get(cid) or (gen.data_for(cid) if gen.is_practice_id(cid) else None)


def compiled(cid):
    if cid not in COMPILED:
        COMPILED[cid] = cw.Case(data_of(cid))
    return COMPILED[cid]


def _int(value, low=0, high=10 ** 6, default=0):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        return default
    return value


def _ordered(order, items):
    return [x for x in order if x in items]


class Game:
    def __init__(self):
        self.best = {}                       # case id -> best seal (1 rough, 2 steady, 3 clean)
        self.runs = {}                       # case id -> action tokens of an unfinished case
        self.cur = progress.ORDER[0]
        self.tally = {key: 0 for key in TALLY_KEYS}
        self.met = []                        # kind ids named correctly at least once
        self.seen = {}                       # kind id -> evidence ids confirmed by a positive reading in a solved case
        self.ev = []                         # evidence ids read positive at least once
        self.eq = []                         # evidence ids whose equipment has been used at least once
        self.kept = []                       # keepsake ids returned
        self.mem = []                        # authored case ids solved with the sheet covered
        self.sbn = {}                        # difficulty -> practice houses opened from a seed the game chose
        self.sbdone = []                     # practice codes solved
        self.rung = 0
        self._enter(self.cur)

    # ---- the current case -------------------------------------------------------------------------------------------
    @property
    def case(self):
        return compiled(self.cur)

    def _enter(self, cid):
        self.cur = cid
        self.tokens = list(self.runs.get(cid, []))
        st, infos = cw.replay(self.case, self.tokens)
        if st is None:
            self.tokens, st, infos = [], self.case.new_state(), []
            self.runs.pop(cid, None)
        self.st = st
        self.log = [{"msg": i["msg"], "kind": i["kind"], "ok": True} for i in infos][-LOG_KEEP:]
        self.result = None
        self.rung = 0
        if self.case.done(self.st):          # a saved run that is already finished is not kept
            self.tokens, self.st, self.log = [], self.case.new_state(), []
            self.runs.pop(cid, None)

    # ---- save ------------------------------------------------------------------------------------------------------
    def to_dict(self):
        """Only what differs from a fresh game is written, so old and new saves stay compatible."""
        data = {}
        if self.cur != progress.ORDER[0]:
            data["cur"] = self.cur
        if self.best:
            data["best"] = dict(self.best)
        runs = {cid: list(t) for cid, t in self.runs.items() if t}
        if self.tokens and not self.case.done(self.st):
            runs[self.cur] = list(self.tokens)
        if runs:
            data["run"] = runs
        tally = {k: v for k, v in self.tally.items() if v}
        if tally:
            data["tally"] = tally
        if self.met:
            data["met"] = list(self.met)
        seen = {k: list(v) for k, v in self.seen.items() if v}
        if seen:
            data["seen"] = seen
        if self.ev:
            data["ev"] = list(self.ev)
        if self.eq:
            data["eq"] = list(self.eq)
        if self.kept:
            data["kept"] = list(self.kept)
        if self.mem:
            data["mem"] = list(self.mem)
        if self.sbn or self.sbdone:
            data["sb"] = {k: v for k, v in (("n", {str(d): n for d, n in self.sbn.items() if n}), ("done", list(self.sbdone))) if v}
        earned = self.earned_ids()
        if earned:
            data["achievements_earned"] = earned       # written for the hub's dashboard, never read back
        return data

    def load(self, data):
        """Take a saved dict, checking every field on its own; a bad field falls back to its default."""
        data = data if isinstance(data, dict) else {}
        raw = data.get("best") if isinstance(data.get("best"), dict) else {}
        self.best = {cid: raw[cid] for cid in progress.ORDER if raw.get(cid) in (1, 2, 3) and not isinstance(raw.get(cid), bool)}
        tally = data.get("tally") if isinstance(data.get("tally"), dict) else {}
        self.tally = {key: _int(tally.get(key)) for key in TALLY_KEYS}

        def listed(key, universe):
            value = data.get(key)
            return [x for x in universe if isinstance(value, list) and x in value]
        self.met = listed("met", lx.KIND_IDS)
        raw_seen = data.get("seen") if isinstance(data.get("seen"), dict) else {}
        self.seen = {}
        for k in lx.KIND_IDS:
            ev = raw_seen.get(k)
            got = [e for e in lx.EV_IDS if isinstance(ev, list) and e in ev and lx.EV_INDEX[e] in lx.KIND_EVIDENCE[k]]
            if got:
                self.seen[k] = got
        self.ev = listed("ev", lx.EV_IDS)
        self.eq = listed("eq", lx.EV_IDS)
        self.kept = listed("kept", lx.KS_IDS)
        self.mem = [cid for cid in progress.ORDER if isinstance(data.get("mem"), list) and cid in data["mem"] and self.best.get(cid)]
        raw_sb = data.get("sb") if isinstance(data.get("sb"), dict) else {}
        raw_n = raw_sb.get("n") if isinstance(raw_sb.get("n"), dict) else {}
        self.sbn = {d: _int(raw_n.get(str(d)), 0, 10 ** 5) for d in gen.DIFFICULTIES if _int(raw_n.get(str(d)), 0, 10 ** 5)}
        done = raw_sb.get("done") if isinstance(raw_sb.get("done"), list) else []
        self.sbdone = []
        for code in done:
            parsed = gen.parse(code) if isinstance(code, str) else None
            if parsed and gen.code_of(*parsed) == code and code not in self.sbdone and len(self.sbdone) < MAX_DONE_CODES:
                self.sbdone.append(code)
        raw_runs = data.get("run") if isinstance(data.get("run"), dict) else {}
        self.runs = {}
        practice_ids = [cid for cid in raw_runs if isinstance(cid, str) and gen.is_practice_id(cid)][:KEEP_PRACTICE_RUNS]
        for cid in list(progress.ORDER) + practice_ids:
            tokens = raw_runs.get(cid)
            authored = cid in progress.DATA
            if isinstance(tokens, list) and 0 < len(tokens) <= MAX_TOKENS and (progress.case_open(self.best, cid) if authored else data_of(cid) is not None):
                st, _infos = cw.replay(compiled(cid), tokens)
                if st is not None and not compiled(cid).done(st):
                    self.runs[cid] = list(tokens)
        cur = data.get("cur")
        if cur in progress.DATA:
            if not progress.case_open(self.best, cur):
                cur = progress.ORDER[0]
        elif not (isinstance(cur, str) and gen.is_practice_id(cur) and data_of(cur) is not None):
            cur = progress.ORDER[0]
        self._enter(cur)

    # ---- facts, goals, achievements ------------------------------------------------------------------------------------------
    def facts(self):
        """What the goals and achievements are computed from."""
        t = progress.totals(self.best)
        found, _total = codex.counts(self.met, self.ev, self.eq, self.kept, self.best)
        return {"done": t["done"], "clean": t["clean"], "chapters_done": t["chapters_done"], "readings": self.tally["readings"],
                "spirits_full": codex.spirits_full(self.met, self.seen), "two": t["two"], "kept": len(self.kept), "sandbox": len(self.sbdone),
                "mem": len(self.mem), "pages": found}

    def open_chapters(self):
        return sum(1 for c in progress.CHAPTERS if progress.chapter_open(self.best, c["index"]))

    def earned_ids(self):
        return achievements.earned(self.facts())

    # ---- the view --------------------------------------------------------------------------------------------------
    def _reading_words(self, v):
        return {cw.UNKNOWN: "not read", cw.CLEAR: "No", cw.POSITIVE: "Yes", cw.DOUBTFUL: "Doubtful"}[v]

    def _house(self):
        case, st = self.case, self.st
        floors = []
        for f in houses.floors_of(case.rooms):
            rooms = []
            for i, r in enumerate(case.rooms):
                if r["floor"] != f:
                    continue
                entered = bool(st[cw.ENTERED] >> i & 1)
                tags = []
                if entered and i in case.feature:
                    tags.append(lx.FEATURES[case.feature[i]][1])
                if entered and i == case.keep_room:
                    tags.append(lx.KS_NAME[case.keep_id] + " (keepsake)")
                rooms.append({"i": i, "name": r["name"], "col": r["col"], "row": r["row"], "entered": entered,
                              "restless": (i in case.room_slot) if entered else None, "here": st[cw.ROOM] == i, "tags": tags,
                              "reads": sum(1 for e in range(6) if st[cw.NOTES][i * 6 + e])})
            floors.append({"floor": f, "name": houses.FLOOR_NAME[f], "cols": max(r["col"] for r in rooms) + 1, "rows": max(r["row"] for r in rooms) + 1, "rooms": rooms})
        return floors

    def _bag(self):
        case, st = self.case, self.st
        gear = []
        full = cw.popcount(st[cw.KIT]) >= case.kit_size
        for e in range(6):
            packed = bool(st[cw.KIT] >> e & 1)
            if st[cw.SOLVED]:
                ok, why = False, "The case is solved."
            elif st[cw.READ]:
                ok, why = False, "The bag is locked once a reading is taken. Go back to the van for a different bag (a second trip costs 1)."
            elif not packed and full:
                ok, why = False, "The bag holds %d pieces. Take one out first." % case.kit_size
            else:
                ok, why = True, ""
            gear.append({"e": e, "name": lx.GEAR_NAME[e], "letter": lx.GEAR_LETTER[e], "ev": lx.EV_NAME[e], "how": lx.GEAR_HOW[e], "packed": packed, "ok": ok, "why": why})
        return {"size": case.kit_size, "count": cw.popcount(st[cw.KIT]), "locked": bool(st[cw.READ]), "gear": gear,
                "van_cost": bool(st[cw.READ]), "at_van": st[cw.ROOM] < 0}

    def _room(self):
        case, st = self.case, self.st
        r = st[cw.ROOM]
        if r < 0:
            return None
        uses = []
        for e in range(6):
            if not st[cw.KIT] >> e & 1:
                continue
            state = st[cw.NOTES][r * 6 + e]
            ok, why = (False, "Already noted in the notebook: %s." % self._reading_words(state).lower()) if state else (True, "")
            if st[cw.SOLVED]:
                ok, why = False, "The case is solved."
            uses.append({"e": e, "name": lx.GEAR_NAME[e], "ev": lx.EV_NAME[e], "how": lx.GEAR_HOW[e], "state": state, "word": self._reading_words(state), "ok": ok, "why": why})
        return {"i": r, "name": case.rooms[r]["name"], "text": case.room_text(r), "restless": r in case.room_slot, "uses": uses,
                "keep": r == case.keep_room, "keep_name": lx.KS_WHAT[case.keep_id] if r == case.keep_room else "", "looked": bool(st[cw.LOOKED]),
                "none_packed": not uses}

    def _notebook(self):
        case, st = self.case, self.st
        rows = []
        for i, r in enumerate(case.rooms):
            if not st[cw.ENTERED] >> i & 1:
                continue
            cells = []
            for e in range(6):
                v = st[cw.NOTES][i * 6 + e]
                cells.append({"e": e, "state": v, "word": self._reading_words(v)})
            rows.append({"i": i, "name": r["name"], "restless": i in case.room_slot, "cells": cells})
        keep = ""
        if st[cw.LOOKED]:
            keep = "The %s: %s" % (lx.KS_NAME[case.keep_id].lower(), lx.BH_LINE[case.keep_bh])
        return {"evidence": [{"e": e, "name": lx.EV_NAME[e], "gear": lx.GEAR_NAME[e], "letter": lx.GEAR_LETTER[e]} for e in range(6)], "rows": rows, "keepsake_line": keep}

    def _accounts(self):
        case = self.case
        out = []
        for b, r in case.accounts:
            out.append({"line": lx.BH_LINE[b], "name": lx.BH_NAME[b], "room": case.rooms[r]["name"] if r is not None else ""})
        return out

    def _could(self):
        """For each presence found so far: the kinds that still fit. A presence is found when its restless room is entered."""
        case, st = self.case, self.st
        out = []
        for s, slot in enumerate(case.slots):
            found = [r for r in slot if st[cw.ENTERED] >> r & 1]
            if not found:
                continue
            kinds = case.candidates(st, s)
            label = "Who it could be" if case.n == 1 else "In the %s" % case.rooms[found[0]]["name"]
            out.append({"label": label, "kinds": [{"id": k, "name": lx.KIND_NAME[k]} for k in kinds], "certain": len(kinds) == 1, "slot": s})
        return out

    def page_full(self, kind):
        return kind in self.met and len(self.seen.get(kind, [])) == 3

    def _sheet(self, could):
        case, st = self.case, self.st
        fits = set()
        for c in could:
            fits |= {k["id"] for k in c["kinds"]}
        any_found = bool(could)
        out = []
        for k in case.pool:
            covered = bool(st[cw.COVERED]) and self.page_full(k)
            out.append({"id": k, "i": lx.KIND_INDEX[k], "name": lx.KIND_NAME[k], "emblem": render.emblem(k), "covered": covered,
                        "evidence": [] if covered else [lx.EV_NAME[e] for e in sorted(lx.KIND_EVIDENCE[k])],
                        "habits": [] if covered else [lx.BH_RULE[b] for b in lx.BH_IDS if b in lx.KIND_BEHAVIOURS[k]],
                        "fits": (k in fits) if any_found else True})
        return out

    def _hint(self):
        if not self.rung:
            return {"rung": 0}
        act = hints.next_action(self.case, self.st)
        d = hints.describe(self.case, self.st, act)
        out = {"rung": self.rung, "nudge": d["nudge"], "kind": d["kind"]}
        if self.rung >= 2:
            out["hint"] = d["hint"]
        if self.rung >= 3:
            out["answer"] = d["answer"]
            out["label"] = d["label"]
        return out

    def _chapters_view(self):
        out = []
        for c in progress.CHAPTERS:
            is_open = progress.chapter_open(self.best, c["index"])
            prev = progress.CHAPTERS[c["index"] - 1] if c["index"] else None
            entries = []
            for number, cid in enumerate(c["cases"], start=1):
                d = progress.DATA[cid]
                entries.append({"id": cid, "name": d["title"], "number": number, "open": is_open, "grade": self.best.get(cid, 0),
                                "grade_name": GRADE_LABEL[self.best.get(cid, 0)], "current": cid == self.cur, "presences": len(d["truth"]),
                                "rooms": houses.size_of(d["layout"]), "started": cid in self.runs and cid != self.cur})
            out.append({"id": c["id"], "name": c["name"], "blurb": c["blurb"], "open": is_open, "done": progress.done_in(self.best, c),
                        "total": len(c["cases"]), "need": min(progress.OPEN_AT, len(prev["cases"])) if prev else 0,
                        "prev_name": prev["name"] if prev else "", "cases": entries})
        return out

    def view(self, message="", ok=True):
        case, st = self.case, self.st
        ch = progress.CHAPTERS[case.chapter] if 0 <= case.chapter < len(progress.CHAPTERS) else None
        cost = case.total_cost(st)
        could = self._could()
        result = None
        if self.result:
            result = dict(self.result)
            if case.practice:
                parsed = gen.parse(case.code)
                result["again"] = {"difficulty": parsed[0], "name": gen.NAMES[parsed[0]]}
            if case.keep_room >= 0 and not case.practice:
                result["keepsake"] = {"id": case.keep_id, "name": lx.KS_NAME[case.keep_id], "what": lx.KS_WHAT[case.keep_id], "returned": case.keep_id in self.kept}
        view = {
            "ok": ok, "message": message,
            "case": {"id": self.cur, "title": case.title, "client": case.client, "intro": case.intro, "chapter": ch["name"] if ch else "Practice",
                     "number": ch["cases"].index(self.cur) + 1 if ch else 0, "of": len(ch["cases"]) if ch else 0,
                     "best": self.best.get(self.cur, 0), "best_name": GRADE_LABEL[self.best.get(self.cur, 0)], "cost": cost,
                     "grade_now_name": GRADE_LABEL[cw.grade_of(cost)], "done": case.done(st), "trips": st[cw.TRIPS], "wrong": st[cw.WRONG],
                     "n": case.n, "presence_line": "One presence in this house." if case.n == 1 else "Two presences, one in each of two rooms. Name both.",
                     "covered": bool(st[cw.COVERED]), "practice": case.practice, "code": case.code,
                     "scene": render.scene(min(5, 1 + len(case.rooms) // 3)), "keepsake": bool(case.keep_room >= 0)},
            "house": self._house(), "bag": self._bag(), "room": self._room(), "notebook": self._notebook(), "accounts": self._accounts(),
            "could": could, "sheet": self._sheet(could), "accuse": {"n": case.n, "options": [{"id": k, "i": lx.KIND_INDEX[k], "name": lx.KIND_NAME[k]} for k in case.pool]},
            "log": self.log[-LOG_KEEP:], "result": result, "chapters": self._chapters_view(), "totals": progress.totals(self.best), "tally": dict(self.tally, sandbox=len(self.sbdone)),
            "practice": {"levels": [{"difficulty": d, "name": gen.NAMES[d]} for d in gen.DIFFICULTIES], "opened": sum(self.sbn.values()), "done": len(self.sbdone)},
            "hint": self._hint(), "about": info.view(),
            "goals": achievements.goals(self.facts(), self.open_chapters()), "achievements": achievements.view(self.facts()),
            "guide": codex.view(self.met, self.seen, self.ev, self.eq, self.kept, self.best),
        }
        return view

    # ---- actions ---------------------------------------------------------------------------------------------------
    def _note(self, info_, ok=True):
        self.log.append({"msg": info_["msg"], "kind": info_["kind"], "ok": ok})
        self.log = self.log[-LOG_KEEP:]

    def do(self, act):
        """Apply a case action. Returns (ok, message)."""
        if len(self.tokens) >= MAX_TOKENS:
            return False, "That is a long case. Restore it to start again."
        before = self.st
        st2, info_ = self.case.apply(self.st, act)
        if st2 is None:
            self.log.append({"msg": info_["msg"], "kind": "refused", "ok": False})
            self.log = self.log[-LOG_KEEP:]
            return False, info_["msg"]
        self.st = st2
        self.tokens.append(cw.to_token(act))
        self.rung = 0
        self._note(info_)
        kind = act[0]
        if kind == "go" and info_.get("first"):
            self.tally["rooms"] += 1
        elif kind == "use":
            self.tally["readings"] += 1
            eid = lx.EV_IDS[act[1]]
            self.eq = _ordered(lx.EV_IDS, set(self.eq) | {eid})
            if info_["result"] == cw.POSITIVE:
                self.ev = _ordered(lx.EV_IDS, set(self.ev) | {eid})
        elif kind == "van" and st2[cw.TRIPS] > before[cw.TRIPS]:
            self.tally["trips"] += 1
        elif kind == "accuse":
            self.tally["accusations"] += 1
            if info_["kind"] == "wrong":
                self.tally["wrong"] += 1
        elif kind == "return":
            self._keep()
        if self.case.done(self.st) and self.result is None:
            self._finish()
        return True, info_["msg"]

    def _keep(self):
        if self.case.keep_id and self.case.keep_id not in self.kept:
            self.kept = _ordered(lx.KS_IDS, set(self.kept) | {self.case.keep_id})

    def _finish(self):
        case, st = self.case, self.st
        cost = case.total_cost(st)
        grade = cw.grade_of(cost)
        before = self.best.get(self.cur, 0)
        new_best = grade > before and self.cur in progress.DATA
        if new_best:
            self.best[self.cur] = grade
        if case.practice and case.code not in self.sbdone and len(self.sbdone) < MAX_DONE_CODES:
            self.sbdone.append(case.code)
        for s, kind in enumerate(case.truth):
            self.met = _ordered(lx.KIND_IDS, set(self.met) | {kind})
            confirmed = {lx.EV_IDS[e] for r in case.slots[s] for e in range(6) if st[cw.NOTES][r * 6 + e] == cw.POSITIVE}
            if confirmed:
                self.seen[kind] = _ordered(lx.EV_IDS, set(self.seen.get(kind, [])) | confirmed)
        if st[cw.COVERED] and self.cur in progress.DATA and self.cur not in self.mem:
            self.mem = _ordered(progress.ORDER, set(self.mem) | {self.cur})
        self.runs.pop(self.cur, None)
        nxt = progress.next_case(self.best, self.cur)
        line = {3: "A clean case: no wrong name and no second trip.", 2: "Steady. The spirit is named, with a small cost on the case.",
                1: "Rough, but the spirit is named. Restore the case to try for a cleaner one."}[grade]
        self.result = {"cost": cost, "grade": grade, "grade_name": GRADE_LABEL[grade], "new_best": new_best, "best_name": GRADE_LABEL[max(grade, before)] if not case.practice else GRADE_LABEL[grade],
                       "line": line, "ending": case.ending, "next": nxt, "next_name": progress.DATA[nxt]["title"] if nxt else ""}

    def _stash(self):
        """Keep the unfinished actions of the case being left."""
        if self.tokens and not self.case.done(self.st):
            self.runs[self.cur] = list(self.tokens)
        else:
            self.runs.pop(self.cur, None)
        practice = [cid for cid in self.runs if cid not in progress.DATA]
        for cid in practice[:max(0, len(practice) - KEEP_PRACTICE_RUNS)]:
            self.runs.pop(cid, None)

    def open_practice(self, difficulty, seed):
        self._stash()
        self._enter(gen.case_id(difficulty, seed))

    def restore(self):
        self.tally["restores"] += 1
        self.tokens = []
        self.st = self.case.new_state()
        self.log = [{"msg": "The case is restored to its start.", "kind": "restore", "ok": True}]
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

    def num(key):
        v = request.get(key)
        return v if isinstance(v, int) and not isinstance(v, bool) else -1

    if action == "open":
        pass
    elif action == "reset":
        g.__init__()
        message = "Starting over."
    elif action == "pick":
        cid = request.get("case")
        if cid not in progress.DATA:
            ok, message = False, "There is no such case."
        elif not progress.case_open(g.best, cid):
            ok, message = False, "That chapter opens once five cases of the one before are done."
        else:
            g._stash()
            g._enter(cid)
    elif action == "next":
        nxt = progress.next_case(g.best, g.cur)
        if nxt is None:
            ok, message = False, "That was the last case open for now."
        else:
            g._stash()
            g._enter(nxt)
    elif action == "practice":
        code = request.get("code")
        d = num("difficulty")
        if isinstance(code, str) and code.strip():
            parsed = gen.parse(code)
            if parsed is None or gen.make(*parsed) is None:
                ok, message = False, "That is not a practice code the game can make. A code looks like EH3-1K9X2."
            else:
                g.open_practice(*parsed)
                message = "Opened the practice house %s." % gen.code_of(*parsed)
        elif d not in gen.DIFFICULTIES:
            ok, message = False, "Pick one of the five sizes of practice house."
        else:
            seed = gen.next_seed(g.sbn.get(d, 0), d)
            g.sbn[d] = g.sbn.get(d, 0) + 1
            g.open_practice(d, seed)
            message = "Opened the practice house %s." % gen.code_of(d, seed)
    elif action == "restore":
        g.restore()
        message = "Restored."
    elif action == "return":
        if g.best.get(g.cur) and g.case.keep_room >= 0:
            if g.case.done(g.st):
                ok, message = g.do(("return",))
            else:
                g._keep()
                message = lx.KS_RETURN[g.case.keep_id]
        else:
            ok, message = False, "There is nothing to return yet. Solve the case first."
    elif action == "hint":
        if g.case.done(g.st):
            ok, message = False, "The case is finished."
        elif g.rung >= 3:
            ok, message = False, "That is every rung: the answer is showing."
        else:
            g.rung += 1
            g.tally["hints"] += 1
    elif action == "hint_do":
        if g.rung < 3:
            ok, message = False, "Climb to the answer first."
        else:
            act = hints.next_action(g.case, g.st)
            if act is None:
                g.restore()
                message = "Restored."
            else:
                ok, message = g.do(act)
    elif action in ("pack", "go", "use"):
        key = {"pack": "e", "go": "room", "use": "e"}[action]
        ok, message = g.do((action, num(key))) if num(key) >= 0 else (False, "That is not something the investigator does.")
    elif action in ("van", "look", "cover"):
        ok, message = g.do((action,))
    elif action == "accuse":
        kinds = request.get("kinds")
        if not isinstance(kinds, list) or not 1 <= len(kinds) <= 2 or any(isinstance(k, bool) or not isinstance(k, int) or k < 0 for k in kinds):
            ok, message = False, "Name a spirit from the sheet."
        else:
            ok, message = g.do(("accuse",) + tuple(kinds))
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
        refresh = getattr(js.window, "evidenceHuntRefresh", None)
        if refresh is not None:
            refresh()
    except Exception:
        pass
