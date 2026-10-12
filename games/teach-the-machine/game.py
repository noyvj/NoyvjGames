"""Teach the Machine -- the engine's single entry point (the Constellations / Reaction Bench pattern).

The view (app.js) never reads engine objects: it sends one JSON string to `handle` and draws the JSON that comes back.
`get_state()` / `load_state()` are the shared save widget's contract (planning/SAVE-BUTTON-INTEGRATION.md). Nothing here reads a clock or a
random source: Pip's tree is a pure function of the switched-on features and the lesson's fixed training table (learner.py).

Actions (every request is {"action": ..., ...}; every reply is the whole view):
  open                    the current view
  pick {lesson}           go to a lesson (its shelf must be open)
  next                    go to the next open lesson not yet cleared
  toggle {feature}        switch one feature on or off (this throws away the tree and the last test)
  reset_switches          put the switches back as the lesson starts
  train                   grow Pip's tree from the training table with the switched-on features
  test                    Pip sorts the unseen cases; enough right clears the lesson
  why {case}              open the Why panel for one wrong answer of the last test
  close_why               close it
  reset                   start over (everything)

The unseen cases, their answers, the features a lesson needs, its best set and what Pip learned stay out of the view until the test has
been taken or the lesson is cleared (a test checks).
"""

import json

import info
import learner
import lessons
import why

SCHEMA = 1
TALLY_KEYS = ("trains", "tests", "whys")
MAX_COUNT = 10 ** 9


def _int(value, low=0, high=MAX_COUNT, default=0):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        return default
    return value


def _plural(n, one, many):
    return "%d %s" % (n, one if n == 1 else many)


def _range_words(f):
    if f["kind"] == "yes_no":
        return "yes or no"
    if f["kind"] == "number":
        return "a number, %d to %d%s" % (f["lo"], f["hi"], (" " + f["unit"]) if f.get("unit") else "")
    return "one of: " + ", ".join(f["values"])


class Game:
    def __init__(self):
        self.cleared = {}                # lesson id -> the switched-on feature ids (in feature order) of the clear
        self.sel = {}                    # lesson id -> set of switched-on feature ids (only where it differs from the start)
        self.notebook = {}               # category id -> [lesson ids where an example was found]
        self.tally = {key: 0 for key in TALLY_KEYS}
        self.current = lessons.ORDER[0]
        self.tree = None                 # Pip's tree for the current switches (not saved: Train again after a load)
        self.trained_on = None
        self.result = None               # the last test: {"right", "total", "cases": [...]}
        self.explained = set()           # case ids whose Why was opened since the last test
        self.open_why = None
        self.just = None
        self.message = ""
        self.say = ""

    # ---- the current lesson -----------------------------------------------------------------------------------------
    @property
    def lesson(self):
        return lessons.BY_ID[self.current]

    def on(self, lid=None):
        lesson = lessons.BY_ID[lid or self.current]
        return set(self.sel[lesson["id"]]) if lesson["id"] in self.sel else set(lesson["start"])

    def on_list(self, lid=None):
        return lessons.order_set(lessons.BY_ID[lid or self.current], self.on(lid))

    def _enter(self, lid):
        self.current = lid
        self._drop_work()
        self.just = None

    def _drop_work(self):
        """The tree, the test and the Why panel belong to one set of switches; any change throws them away."""
        self.tree = None
        self.trained_on = None
        self.result = None
        self.explained = set()
        self.open_why = None

    # ---- save ------------------------------------------------------------------------------------------------------
    def to_dict(self):
        """Only what differs from a fresh game is written (plus the layout version), so old and new saves stay compatible."""
        data = {"schema": SCHEMA}
        if self.current != lessons.ORDER[0]:
            data["cur"] = self.current
        if self.cleared:
            data["cleared"] = {lid: list(self.cleared[lid]) for lid in lessons.ORDER if lid in self.cleared}
        sel = {}
        for lid in lessons.ORDER:
            if lid in self.sel and set(self.sel[lid]) != set(lessons.BY_ID[lid]["start"]):
                sel[lid] = lessons.order_set(lessons.BY_ID[lid], self.sel[lid])
        if sel:
            data["sel"] = sel
        book = {cat: [lid for lid in lessons.ORDER if lid in self.notebook[cat]] for cat in why.CATEGORY_IDS if self.notebook.get(cat)}
        if book:
            data["notebook"] = book
        tally = {k: v for k, v in self.tally.items() if v}
        if tally:
            data["tally"] = tally
        return data

    def load(self, data):
        """Take a saved dict, checking every field on its own; a bad field falls back to its default. A cleared lesson only counts if its
        shelf was open by the lessons cleared before it (shelves are judged in order), and a saved set of features must really clear it."""
        data = data if isinstance(data, dict) else {}
        schema = data.get("schema", SCHEMA)
        if isinstance(schema, bool) or not isinstance(schema, int) or not 1 <= schema <= SCHEMA:
            data = {}                                            # an unknown layout is never half-read
        self.cleared, self.sel, self.notebook = {}, {}, {}
        raw_cleared = data.get("cleared") if isinstance(data.get("cleared"), dict) else {}
        for lesson in lessons.ALL:                               # shelf order, so each shelf is judged on those before it
            lid = lesson["id"]
            if lid not in raw_cleared or not lessons.shelf_open(self.cleared, lesson["shelf"]):
                continue
            ids = self._clean_ids(lesson, raw_cleared[lid])
            if not ids or lessons.score(lesson, set(ids))[0] < lesson["need"]:
                ids = list(lesson["best"])                       # a set that does not really clear it is replaced by the proved best set
            self.cleared[lid] = ids
        raw_sel = data.get("sel") if isinstance(data.get("sel"), dict) else {}
        for lesson in lessons.ALL:
            lid = lesson["id"]
            if lid in raw_sel and lessons.lesson_open(self.cleared, lid):
                ids = self._clean_ids(lesson, raw_sel[lid])
                if ids is not None and set(ids) != set(lesson["start"]):
                    self.sel[lid] = set(ids)
        raw_book = data.get("notebook") if isinstance(data.get("notebook"), dict) else {}
        for cat in why.CATEGORY_IDS:
            found = raw_book.get(cat)
            if isinstance(found, list):
                keep = [lid for lid in lessons.ORDER if lid in found and lessons.lesson_open(self.cleared, lid)]
                if keep:
                    self.notebook[cat] = keep
        tally = data.get("tally") if isinstance(data.get("tally"), dict) else {}
        self.tally = {key: _int(tally.get(key)) for key in TALLY_KEYS}
        cur = data.get("cur")
        self._enter(cur if isinstance(cur, str) and lessons.lesson_open(self.cleared, cur) else lessons.ORDER[0])
        self.message = self.say = ""

    @staticmethod
    def _clean_ids(lesson, raw):
        """A saved list of feature ids -> the ids that exist, in feature order, no repeats (None if it is not a list)."""
        if not isinstance(raw, list):
            return None
        return lessons.order_set(lesson, [x for x in raw if isinstance(x, str)])

    # ---- the view --------------------------------------------------------------------------------------------------
    def _shelves(self):
        out = []
        for s, shelf in enumerate(lessons.SHELVES):
            done = lessons.shelf_done(self.cleared, s)
            entries = []
            for l in shelf["lessons"]:
                entry = {"id": l["id"], "number": l["number"], "title": l["title"], "cleared": l["id"] in self.cleared, "current": l["id"] == self.current}
                entry["best"] = l["id"] in self.cleared and list(self.cleared[l["id"]]) == list(l["best"])
                entries.append(entry)
            out.append({"id": shelf["id"], "name": shelf["name"], "blurb": shelf["blurb"], "open": lessons.shelf_open(self.cleared, s), "done": done,
                        "total": len(shelf["lessons"]), "need_total": lessons.shelf_need(s),
                        "need": max(0, lessons.shelf_need(s) - (lessons.shelf_done(self.cleared, s - 1) if s else 0)),
                        "after": lessons.SHELVES[s - 1]["name"] if s else "", "lessons": entries})
        return out

    def _notebook(self):
        entries = []
        for c in why.CATEGORIES:
            found = self.notebook.get(c["id"], [])
            later = (c["id"] == "shortcut" and not any(l["shortcuts"] for l in lessons.ALL)) or (c["id"] == "mislabelled" and not any(l["mislabelled"] for l in lessons.ALL))
            entry = {"id": c["id"], "name": c["name"], "found": bool(found), "count": len(found), "later": later and not found}
            if found:
                entry.update({"about": c["about"], "example": c["example"], "lessons": [lessons.BY_ID[lid]["title"] for lid in found]})
            entries.append(entry)
        return entries

    def _gallery(self):
        cards = []
        for l in lessons.ALL:
            if l["id"] not in self.cleared:
                continue
            on = self.cleared[l["id"]]
            tree = lessons.fit(l, set(on))
            cards.append({"id": l["id"], "title": l["title"], "shelf": lessons.SHELVES[l["shelf"]]["name"], "number": l["number"],
                          "learned": l["learned"], "looked_at": [l["by_id"][f]["label"] for f in on], "best": list(on) == list(l["best"]),
                          "tree": learner.tree_lines(tree, l["by_id"], l["bins"])})
        return cards

    def _chips(self, lesson, case, on):
        return why.chips(lesson, on, case)

    def _lamp(self):
        if self.tree is None:
            return {"state": "idle", "words": "Pip's lamp is dim. It is waiting for you to press Train."}
        if self.result is None:
            return {"state": "trained", "words": "Pip's lamp is steady. It has studied the training cases and is ready to be tested."}
        if self.result["right"] >= self.lesson["need"]:
            return {"state": "pleased", "words": "Pip's lamp is bright. It learned this lesson."}
        return {"state": "puzzled", "words": "Pip's lamp flickers. Some answers were wrong. Open a Why to see what fooled it."}

    def _lesson_view(self):
        l = self.lesson
        on = self.on()
        cleared = l["id"] in self.cleared
        features = [{"id": f["id"], "label": f["label"], "kind": f["kind"], "about": f["about"], "range": _range_words(f), "on": f["id"] in on, "key": i + 1}
                    for i, f in enumerate(l["features"])]
        train = [{"id": c["id"], "name": c["name"], "chips": self._chips(l, c, on), "answer": l["bins"][c["label"]]} for c in l["train_cases"]]
        view = {"id": l["id"], "number": l["number"], "of": len(lessons.SHELVES[l["shelf"]]["lessons"]), "shelf": lessons.SHELVES[l["shelf"]]["name"],
                "shelf_index": l["shelf"], "title": l["title"], "task": l["task"], "noun": l["noun"], "bins": list(l["bins"]), "target": l["target"],
                "need": l["need"], "unseen": len(l["test"]), "features": features, "train": train, "on_count": len(on),
                "at_start": on == set(l["start"]), "cleared": cleared, "lamp": self._lamp(), "trained": self.tree is not None,
                "tree": None, "train_score": None, "result": None, "why": None}
        if self.tree is not None:
            right, total = lessons.train_score(l, self.tree)
            view["tree"] = learner.tree_lines(self.tree, l["by_id"], l["bins"])
            view["train_score"] = {"right": right, "total": total}
            view["looking_at"] = [f["label"] for f in l["features"] if f["id"] in on]
        if self.result is not None:
            view["result"] = {"right": self.result["right"], "total": self.result["total"], "need": l["need"], "passed": self.result["right"] >= l["need"],
                              "cases": [dict(c, explained=c["id"] in self.explained) for c in self.result["cases"]]}
            if self.open_why:
                case = next(c for c in l["test_cases"] if c["id"] == self.open_why)
                view["why"] = why.explain(l, on, self.tree, case)
        if cleared:
            on_cleared = self.cleared[l["id"]]
            view["learned"] = l["learned"]
            view["cleared_with"] = [l["by_id"][f]["label"] for f in on_cleared]
            view["best_mark"] = list(on_cleared) == list(l["best"])
        return view

    def view(self, message=None, ok=True, say=None):
        if message is not None:
            self.message = message
        self.say = say if say is not None else (self.message if message else "")
        t = self.tally
        return {
            "ok": ok, "message": self.message, "say": self.say, "lesson": self._lesson_view(), "just": self.just,
            "shelves": self._shelves(), "notebook": self._notebook(), "gallery": self._gallery(), "tally": dict(t),
            "totals": {"lessons": lessons.TOTAL, "cleared": len(self.cleared), "shelves": len(lessons.SHELVES),
                       "shelves_open": sum(1 for s in range(len(lessons.SHELVES)) if lessons.shelf_open(self.cleared, s)),
                       "shelves_done": lessons.shelves_finished(self.cleared), "whys": t["whys"], "trains": t["trains"], "tests": t["tests"],
                       "notebook": sum(1 for c in why.CATEGORY_IDS if self.notebook.get(c)), "notebook_total": len(why.CATEGORY_IDS),
                       "best_marks": sum(1 for lid in self.cleared if list(self.cleared[lid]) == list(lessons.BY_ID[lid]["best"]))},
            "info": info.view(),
        }

    # ---- play ------------------------------------------------------------------------------------------------------
    def toggle(self, fid):
        l = self.lesson
        if not isinstance(fid, str) or fid not in l["by_id"]:
            return self.view("That is not one of this lesson's features.", ok=False)
        on = self.on()
        label = l["by_id"][fid]["label"]
        if fid in on:
            on.discard(fid)
            text = "%s is off. Pip may not look at it." % label
        else:
            on.add(fid)
            text = "%s is on. Pip may look at it." % label
        self.sel[l["id"]] = on
        self._drop_work()
        self.just = None
        return self.view("", say=text + " Press Train to grow a new tree.")

    def reset_switches(self):
        self.sel.pop(self.current, None)
        self._drop_work()
        self.just = None
        return self.view("", say="The switches are back as the lesson starts.")

    def train(self):
        l = self.lesson
        on = self.on()
        if not on:
            return self.view("Switch on at least one feature first. Pip needs something to look at.", ok=False)
        self.tree = lessons.fit(l, on)
        self.trained_on = tuple(lessons.order_set(l, on))
        self.result = None
        self.explained = set()
        self.open_why = None
        self.just = None
        self.tally["trains"] += 1
        right, total = lessons.train_score(l, self.tree)
        return self.view("Pip has studied the %d training %ss and got %d of them right. Press Test." % (total, l["noun"].lower(), right))

    def test(self):
        l = self.lesson
        if self.tree is None:
            return self.view("Press Train first. Pip has not studied anything yet.", ok=False)
        cases = []
        for c in l["test_cases"]:
            pip = learner.predict(self.tree, c)
            cases.append({"id": c["id"], "name": c["name"], "chips": self._chips(l, c, self.on()), "pip": l["bins"][pip],
                          "truth": l["bins"][c["label"]], "right": pip == c["label"]})
        right = sum(1 for c in cases if c["right"])
        self.result = {"right": right, "total": len(cases), "cases": cases}
        self.explained = set()
        self.open_why = None
        self.tally["tests"] += 1
        self.just = None
        text = "Pip got %d of %d right (%d needed)." % (right, len(cases), l["need"])
        if right >= l["need"]:
            on = self.on_list()
            first = l["id"] not in self.cleared
            was_open = [lessons.shelf_open(self.cleared, s) for s in range(len(lessons.SHELVES))]
            best = on == list(l["best"])
            if first:
                self.cleared[l["id"]] = on
            elif best and list(self.cleared[l["id"]]) != list(l["best"]):
                self.cleared[l["id"]] = on                         # the best set always upgrades an older clear; nothing ever goes down
            opened = [lessons.SHELVES[s]["name"] for s in range(len(lessons.SHELVES)) if lessons.shelf_open(self.cleared, s) and not was_open[s]]
            self.just = {"id": l["id"], "title": l["title"], "first": first, "best": best, "opened": opened}
            text += " Lesson cleared." if first else " Cleared again."
            if first and opened:
                text += " A new shelf opens: %s." % ", ".join(opened)
        elif right < len(cases):
            text += " Open a Why on a wrong answer."
        return self.view(text)

    def open_why_for(self, case_id):
        l = self.lesson
        if self.result is None or self.tree is None:
            return self.view("Test Pip first. There is nothing to explain yet.", ok=False)
        wrong = {c["id"] for c in self.result["cases"] if not c["right"]}
        if not isinstance(case_id, str) or case_id not in wrong:
            return self.view("That answer was not wrong, so there is nothing to explain.", ok=False)
        self.open_why = case_id
        text = ""
        if case_id not in self.explained:
            self.explained.add(case_id)
            self.tally["whys"] += 1
            category = why.categorise(l, self.on(), next(c for c in l["test_cases"] if c["id"] == case_id))
            found = self.notebook.setdefault(category, [])
            if l["id"] not in found:
                found.append(l["id"])
                found.sort(key=lessons.ORDER.index)
                text = "New in your Failure Notebook: %s." % why.BY_ID[category]["name"]
        return self.view(text, say=text or "Why panel open.")

    def close_why(self):
        self.open_why = None
        return self.view("")

    # ---- navigation ------------------------------------------------------------------------------------------------
    def pick(self, lid):
        if not isinstance(lid, str) or lid not in lessons.BY_ID:
            return self.view("There is no such lesson.", ok=False)
        if not lessons.lesson_open(self.cleared, lid):
            s = lessons.BY_ID[lid]["shelf"]
            return self.view("That shelf opens when %d lessons on %s are cleared." % (lessons.shelf_need(s), lessons.SHELVES[s - 1]["name"]), ok=False)
        if lid != self.current:
            self._enter(lid)
        return self.view("")

    def next(self):
        order = lessons.ORDER
        start = order.index(self.current)
        for step in range(1, len(order) + 1):
            lid = order[(start + step) % len(order)]
            if lid not in self.cleared and lessons.lesson_open(self.cleared, lid):
                self._enter(lid)
                return self.view("")
        return self.view("Every open lesson is cleared." if len(self.cleared) < len(order) else "Every lesson is cleared.", ok=False)


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
        return json.dumps(g.pick(request.get("lesson")))
    if action == "next":
        return json.dumps(g.next())
    if action == "toggle":
        return json.dumps(g.toggle(request.get("feature")))
    if action == "reset_switches":
        return json.dumps(g.reset_switches())
    if action == "train":
        return json.dumps(g.train())
    if action == "test":
        return json.dumps(g.test())
    if action == "why":
        return json.dumps(g.open_why_for(request.get("case")))
    if action == "close_why":
        return json.dumps(g.close_why())
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
        refresh = getattr(js.window, "teachTheMachineRefresh", None)
        if refresh is not None:
            refresh()
    except Exception:
        pass
