"""Rule Finder -- the engine's single entry point (the Hull Repair / Robot Script pattern).

The view (app.js) never reads engine objects: it sends one JSON string to `handle` and draws the JSON that comes back.
`get_state()` / `load_state()` are the shared save widget's contract (planning/SAVE-BUTTON-INTEGRATION.md). Nothing here
reads a clock or a random source: the Sorter's answer to an item is a pure function of the case and the item.

Actions (every request is {"action": ..., ...}; every reply is the whole view):
  open                    the current view (with the clause menu)
  pick {case}             go to a case (every case is open)
  next                    go to the next case not yet named
  test {item}             send one item to the gate; the answer is Through or Stopped (a new item counts as one test)
  preview {rule}          check a draft rule against everything seen so far (changes nothing)
  name {rule}             name the rule: right ends the case, wrong shows one counter-example
  restart                 clear this named case's test log to try for a better count (the best is kept)
  page {case}             open a case's Codex page (it must be named); a page opened counts as read
  reset                   start over (everything)
A rule is {"lits": [[clause id, negated 0/1], ...], "ops": ["and" | "or", ...]}.
"""

import json

import cases
import codex
import lang
import progress
import render

TALLY_KEYS = ("tests", "near", "hints")
MAX_COUNT = 10 ** 9
MAX_LOG = 6000


def _int(value, low=0, high=MAX_COUNT, default=0):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        return default
    return value


class Game:
    def __init__(self):
        self.named = {}                  # case id -> {"t": best tests, "r": rule text, "m": near miss before naming}
        self.log = {}                    # case id -> {"t": [tested items], "f": [free counter-examples]}
        self.tally = {key: 0 for key in TALLY_KEYS}
        self.read = []                   # Codex pages opened (only named cases)
        self.current = cases.ORDER[0]
        self.page_id = None              # the Codex page showing (not saved)
        self.last = None                 # the last answer shown at the gate
        self.verdict = None              # the last naming result
        self.menu_due = True

    # ---- the current case ------------------------------------------------------------------------------------------
    @property
    def case(self):
        return cases.BY_ID[self.current]

    def _entry(self, cid=None):
        return self.log.setdefault(cid or self.current, {"t": [], "f": []})

    def _seen_entries(self, case=None):
        """[(item, src)] in the order shown: the starting examples, then your tests, then free counter-examples."""
        case = case or self.case
        entry = self.log.get(case.id, {"t": [], "f": []})
        return [(k, "given") for k in case.yes + case.no] + [(k, "test") for k in entry["t"]] + [(k, "free") for k in entry["f"]]

    def _enter(self, cid):
        self.current = cid
        self.page_id = None
        self.last = None
        self.verdict = None
        self.menu_due = True

    # ---- save ------------------------------------------------------------------------------------------------------
    def to_dict(self):
        """Only what differs from a fresh game is written, so old and new saves stay compatible."""
        data = {}
        if self.current != cases.ORDER[0]:
            data["cur"] = self.current
        if self.named:
            data["named"] = {cid: {k: v for k, v in rec.items() if k == "t" or v} for cid, rec in self.named.items()}
        log = {cid: {k: list(v) for k, v in entry.items() if v} for cid, entry in self.log.items() if entry["t"] or entry["f"]}
        if log:
            data["log"] = log
        tally = {k: v for k, v in self.tally.items() if v}
        if tally:
            data["tally"] = tally
        read = [cid for cid in cases.ORDER if cid in self.read and cid in self.named]
        if read:
            data["read"] = read
        return data

    def load(self, data):
        """Take a saved dict, checking every field on its own; a bad field falls back to its default. A saved name only counts
        if the rule it was named with really agrees with the hidden rule on every item of the domain."""
        data = data if isinstance(data, dict) else {}
        self.named, self.log = {}, {}
        raw = data.get("named") if isinstance(data.get("named"), dict) else {}
        for case in cases.ALL_CASES:
            rec = raw.get(case.id)
            if not isinstance(rec, dict):
                continue
            rule = lang.parse_rule(case.kind, rec.get("r")) if isinstance(rec.get("r"), str) else None
            tests = _int(rec.get("t"), 0, MAX_LOG, -1)
            if rule is None or tests < 0 or not lang.agree(case.kind, rule, case.rule):
                continue
            self.named[case.id] = {"t": tests, "r": lang.encode_rule(rule), "m": 1 if rec.get("m") == 1 else 0}
        raw = data.get("log") if isinstance(data.get("log"), dict) else {}
        for case in cases.ALL_CASES:
            rec = raw.get(case.id)
            if not isinstance(rec, dict):
                continue
            dom = case.domain
            seen = set(case.examples)
            entry = {"t": [], "f": []}
            for field in ("t", "f"):
                items = rec.get(field) if isinstance(rec.get(field), list) else []
                for item in items[:MAX_LOG]:
                    key = dom.normalize(item) if isinstance(item, (str, int)) else None
                    if key is not None and key not in seen:
                        seen.add(key)
                        entry[field].append(key)
            if entry["t"] or entry["f"]:
                self.log[case.id] = entry
        tally = data.get("tally") if isinstance(data.get("tally"), dict) else {}
        self.tally = {key: _int(tally.get(key)) for key in TALLY_KEYS}
        raw = data.get("read") if isinstance(data.get("read"), list) else []
        self.read = [cid for cid in cases.ORDER if cid in self.named and any(r == cid for r in raw if isinstance(r, str))]
        self.page_id = None
        cur = data.get("cur")
        self._enter(cur if isinstance(cur, str) and cur in cases.BY_ID else cases.ORDER[0])

    # ---- the view --------------------------------------------------------------------------------------------------
    def _entry_view(self, key, src, case):
        return {"item": key, "yes": case.accepts(key), "src": src, "label": lang.item_words(case.kind, key)}

    def _cases_view(self):
        out = []
        for drawer in cases.DRAWER_LIST:
            entries = []
            for c in drawer["cases"]:
                rec = self.named.get(c.id)
                entries.append({"id": c.id, "name": c.name, "number": c.number, "named": rec is not None,
                                "best": rec["t"] if rec else None, "medal": cases.medal_for(c, rec["t"]) if rec else "",
                                "kind": c.kind, "current": c.id == self.current})
            out.append({"id": drawer["id"], "name": drawer["name"], "blurb": drawer["blurb"], "max_clauses": drawer["max_clauses"],
                        "named": progress.drawer_named(self.named, drawer), "total": len(drawer["cases"]), "cases": entries})
        return out

    def _case_view(self):
        c = self.case
        drawer = cases.DRAWER_LIST[c.drawer]
        rec = self.named.get(c.id)
        entry = self.log.get(c.id, {"t": [], "f": []})
        view = {
            "id": c.id, "name": c.name, "number": c.number, "of": len(drawer["cases"]), "drawer": drawer["name"],
            "blurb": drawer["blurb"], "max_clauses": drawer["max_clauses"], "kind": c.kind, "subject": lang.SUBJECT[c.kind],
            "status": "named" if rec else "open", "par": c.par, "tests": len(entry["t"]), "free": len(entry["f"]),
            "best": rec["t"] if rec else None, "medal": cases.medal_for(c, rec["t"]) if rec else "",
            "log": [self._entry_view(k, src, c) for k, src in self._seen_entries(c)],
        }
        if rec:
            view["words"] = c.words
            view["line"] = c.line
        return view

    def view(self, message="", ok=True, draft=None):
        picker = self._cases_view()
        page = cases.BY_ID.get(self.page_id) if self.page_id else None
        totals = progress.totals(self.named)
        totals.update({"pages": len(self.named), "read": len([c for c in self.read if c in self.named])})
        view = {"ok": ok, "message": message, "case": self._case_view(), "last": self.last, "verdict": self.verdict,
                "cases": picker, "map": render.wall_svg(picker), "codex": codex.summary(self.named, self.read),
                "page": codex.page(page, self.named, self.read) if page else None,
                "totals": totals, "tally": dict(self.tally), "draft": draft}
        if self.menu_due:
            view["menu"] = lang.menu(self.case.kind)
            self.menu_due = False
        return view

    # ---- rules against what has been seen -------------------------------------------------------------------------------
    def _conflict(self, rule):
        """The first item seen so far that the draft rule gets wrong (it differs from the Sorter's answer), or None."""
        c = self.case
        for key, _src in self._seen_entries(c):
            truth = c.accepts(key)
            if lang.rule_accepts(c.kind, rule, key) != truth:
                return {"item": key, "label": lang.item_words(c.kind, key), "sorter": "Through" if truth else "Stopped",
                        "rule": "Stopped" if truth else "Through"}
        return None

    def _draft(self, raw):
        c = self.case
        rule = lang.parse_rule(c.kind, raw)
        if rule is None or len(rule.lits) > cases.DRAWER_LIST[c.drawer]["max_clauses"]:
            return None, {"valid": False, "words": "", "conflict": None}
        return rule, {"valid": True, "words": lang.rule_words(c.kind, rule), "conflict": self._conflict(rule)}

    # ---- actions ---------------------------------------------------------------------------------------------------
    def test(self, raw):
        c = self.case
        key = c.domain.normalize(raw)
        if key is None:
            return self.view("That is not an item this gate takes.", ok=False)
        self.verdict = None
        yes = c.accepts(key)
        seen = {k for k, _s in self._seen_entries(c)}
        if key in seen:
            self.last = {"item": key, "yes": yes, "repeat": True, "label": lang.item_words(c.kind, key)}
            return self.view("You have already sent this one: %s." % ("Through" if yes else "Stopped"))
        self._entry()["t"].append(key)
        self.tally["tests"] += 1
        self.last = {"item": key, "yes": yes, "repeat": False, "label": lang.item_words(c.kind, key)}
        return self.view()

    def name(self, raw):
        c = self.case
        rule, draft = self._draft(raw)
        if rule is None:
            self.verdict = None
            return self.view("That is not a rule the builder can make.", ok=False)
        self.last = None
        if draft["conflict"]:
            self.verdict = {"kind": "conflict", "conflict": draft["conflict"], "words": draft["words"]}
            return self.view("Your rule already disagrees with an item you have seen.", ok=False)
        if lang.agree(c.kind, rule, c.rule):
            entry = self.log.get(c.id, {"t": [], "f": []})
            tests = len(entry["t"])
            prior = self.named.get(c.id)
            near = 1 if entry["f"] else 0
            best = tests if prior is None else min(prior["t"], tests)
            keep = prior if prior is not None and prior["t"] <= tests else {"r": lang.encode_rule(rule)}
            self.named[c.id] = {"t": best, "r": keep["r"], "m": near or (prior["m"] if prior else 0)}
            self.verdict = {"kind": "named", "tests": tests, "best": best, "first": prior is None, "improved": prior is not None and tests < prior["t"],
                            "medal": cases.medal_for(c, best), "words": c.words, "line": c.line, "next": progress.next_case(self.named, c.id)}
            return self.view()
        other = lang.first_difference(c.kind, rule, c.rule)
        self._entry()["f"].append(other)
        self.tally["near"] += 1
        truth = c.accepts(other)
        self.verdict = {"kind": "near", "words": draft["words"],
                        "conflict": {"item": other, "label": lang.item_words(c.kind, other), "sorter": "Through" if truth else "Stopped",
                                     "rule": "Stopped" if truth else "Through"}}
        return self.view()

    def preview(self, raw):
        _rule, draft = self._draft(raw)
        return self.view(draft=draft)

    def open_page(self, cid):
        if not isinstance(cid, str) or cid not in cases.BY_ID:
            return self.view("There is no such page.", ok=False)
        if cid not in self.named:
            return self.view("That page is empty until you name its case.", ok=False)
        if cid not in self.read:
            self.read.append(cid)
        self.page_id = cid
        return self.view()

    def restart(self):
        c = self.case
        if c.id not in self.named:
            return self.view("Name this rule once before starting it again.", ok=False)
        self.log.pop(c.id, None)
        self.last = None
        self.verdict = None
        return self.view("Your test log is clear. Your best count is kept.")


game = Game()


def handle(request_json):
    try:
        request = json.loads(request_json)
        action = request.get("action")
    except (ValueError, AttributeError):
        return json.dumps({"error": "bad request"})
    g = game
    if action == "open":
        g.menu_due = True
        return json.dumps(g.view())
    if action == "reset":
        g.__init__()
        return json.dumps(g.view("Starting over."))
    if action == "pick":
        cid = request.get("case")
        if not isinstance(cid, str) or cid not in cases.BY_ID:
            return json.dumps(g.view("There is no such case.", ok=False))
        g._enter(cid)
        return json.dumps(g.view())
    if action == "next":
        nxt = progress.next_case(g.named, g.current)
        if nxt is None:
            return json.dumps(g.view("Every case is named.", ok=False))
        g._enter(nxt)
        return json.dumps(g.view())
    if action == "test":
        return json.dumps(g.test(request.get("item")))
    if action == "preview":
        return json.dumps(g.preview(request.get("rule")))
    if action == "name":
        return json.dumps(g.name(request.get("rule")))
    if action == "restart":
        return json.dumps(g.restart())
    if action == "page":
        return json.dumps(g.open_page(request.get("case")))
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
        refresh = getattr(js.window, "ruleFinderRefresh", None)
        if refresh is not None:
            refresh()
    except Exception:
        pass
