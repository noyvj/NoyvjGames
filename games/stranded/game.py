"""Stranded -- the engine's single entry point (the Station Medic / Robot Script pattern).

The view (app.js) never reads engine objects: it sends one JSON string to `handle` and draws the JSON that comes back.
`get_state()` / `load_state()` are the shared save widget's contract (planning/SAVE-BUTTON-INTEGRATION.md). Nothing here reads
a clock or a random source: the current scene is a pure function of the string of choice numbers taken since the start.

Actions (every request is {"action": ..., ...}; every reply is the whole view):
  open                the current view
  choose {i}          send reply number i in the current scene
  rewind {step}       go back to just before the step-th reply of this run (free; collectables and the map are kept)
  restart             rewind to the very beginning (free, same as rewind 0)
  goto {scene}        go to a scene already seen, by a route of replies already tried
  peek                open the what-if peek on this scene (needs two different replies tried here)
  hint                climb one rung of the hint ladder (nudge, hint, answer)
  hint_do             take me to the loose end the answer rung names
  reset               erase everything and start over
"""

import json

import achievements
import explore
import info
import kit
import lore
import render
import story
import walker

TALLY_KEYS = ("rewinds", "peeks", "hints", "jumps", "sent")
STAT_WORD = ((0, "none"), (2, "very low"), (4, "low"), (6, "middling"), (8, "good"), (10, "full"))
EDGE_SET = set(story.EDGES)
TOTAL_THINGS = len(story.SCENES) + len(story.EDGES) + len(lore.COLLECT)


def _word(value):
    for limit, word in STAT_WORD:
        if value <= limit:
            return word
    return STAT_WORD[-1][1]


def _int(value, high=10 ** 6):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= high:
        return 0
    return value


def _key(edge):
    return "%s:%d>%s" % edge


def _parse_key(text):
    if not isinstance(text, str) or ":" not in text or ">" not in text:
        return None
    head, _sep, target = text.partition(">")
    sid, _sep, num = head.rpartition(":")
    if not num.isdigit():
        return None
    edge = (sid, int(num), target)
    return edge if edge in EDGE_SET else None


class Game:
    def __init__(self):
        self.taken = set()               # (scene id, choice number, target scene) edges ever walked
        self.seen = {story.START}        # scene ids ever seen
        self.endings = set()
        self.found = set()               # collectable ids
        self.tally = {k: 0 for k in TALLY_KEYS}
        self.path = ""                   # the current run, as a string of choice numbers
        self.rung = 0
        self.peek_path = None
        self.message = ""
        self._sync()

    # ---- the run ---------------------------------------------------------------------------------------------------------
    def _sync(self):
        """Recompute the current state from the path and fold what it shows into the permanent record."""
        got = walker.replay(self.path)
        if got is None:
            self.path = ""
            got = walker.replay("")
        self.steps, self.state, found = got
        self.seen.add(story.START)
        for step in self.steps:
            self.taken.add((step["before"][0], step["idx"], step["after"][0]))
            self.seen.add(step["after"][0])
        for sid in list(self.seen):
            if story.SCENES[sid]["end"]:
                self.endings.add(story.SCENES[sid]["end"])
        self.found.update(found)

    @property
    def scene(self):
        return story.SCENES[self.state[0]]

    # ---- save ------------------------------------------------------------------------------------------------------------
    def to_dict(self):
        """Only what differs from a fresh game is written, so old and new saves stay compatible."""
        data = {}
        if self.path:
            data["path"] = self.path
        extra_taken = sorted(_key(e) for e in self.taken)
        if extra_taken:
            data["taken"] = extra_taken
        seen = sorted(s for s in self.seen if s != story.START)
        if seen:
            data["seen"] = seen
        if self.endings:
            data["endings"] = [e for e in story.ENDING_IDS if e in self.endings]
        if self.found:
            data["found"] = [c for c in lore.COLLECT_IDS if c in self.found]
        tally = {k: v for k, v in self.tally.items() if v}
        if tally:
            data["tally"] = tally
        earned = achievements.earned(self.facts())
        if earned:
            data["achievements_earned"] = earned       # written for the hub's dashboard, never read back
        return data

    def load(self, data):
        """Take a saved dict, checking every field on its own; a bad field falls back to its default."""
        data = data if isinstance(data, dict) else {}
        self.__init__()
        raw = data.get("taken") if isinstance(data.get("taken"), list) else []
        self.taken = {e for e in (_parse_key(t) for t in raw) if e}
        raw = data.get("seen") if isinstance(data.get("seen"), list) else []
        self.seen = {story.START} | {s for s in raw if isinstance(s, str) and s in story.SCENES}
        raw = data.get("endings") if isinstance(data.get("endings"), list) else []
        self.endings = {e for e in raw if e in story.ENDING_IDS}
        raw = data.get("found") if isinstance(data.get("found"), list) else []
        self.found = {c for c in raw if isinstance(c, str) and c in lore.COLLECT_BY_ID}
        tally = data.get("tally") if isinstance(data.get("tally"), dict) else {}
        self.tally = {k: _int(tally.get(k)) for k in TALLY_KEYS}
        path = data.get("path")
        self.path = path if isinstance(path, str) and len(path) <= 200 and path.isdigit() else ""
        self._sync()

    def facts(self):
        """What the goals and achievements are computed from."""
        kinds = {k: sum(1 for c in self.found if lore.COLLECT_BY_ID[c][1] == k) for k in lore.KINDS}
        return {"tried": len(self.taken), "sent": self.tally["sent"], "max_day": max(story.SCENES[s]["day"] for s in self.seen), "endings": len(self.endings),
                "rewinds": self.tally["rewinds"], "peeks": self.tally["peeks"], "scenes": len(self.seen),
                "logs": kinds["log"], "items": kinds["item"], "recs": kinds["rec"]}

    # ---- the view --------------------------------------------------------------------------------------------------------
    def _transcript(self):
        out = []
        state0 = walker.initial()[0]

        def arrive(scene, state, previous_day, step):
            if scene["day"] != previous_day:
                out.append({"kind": "day", "day": scene["day"], "text": "Day %d: %s" % (scene["day"], lore.DAYS[scene["day"]][0])})
                out.append({"kind": "narrator", "text": lore.DAYS[scene["day"]][1]})
            for text in walker.visible(scene["lines"], state):
                out.append({"kind": "action" if text.startswith("*") else "ines", "text": text.strip("*") if text.startswith("*") else text})

        arrive(story.SCENES[story.START], state0, 0, 0)
        for n, step in enumerate(self.steps):
            choice = story.SCENES[step["before"][0]]["choices"][step["idx"]]
            out.append({"kind": "you", "text": choice["text"], "step": n})
            for text in step["info"]["reply"]:
                out.append({"kind": "action" if text.startswith("*") else "ines", "text": text.strip("*") if text.startswith("*") else text})
            d = step["info"]["delta"]
            bits = ["%s %+d" % (name.capitalize(), v) for name, v in zip(kit.STATS, d) if v]
            if bits:
                out.append({"kind": "delta", "text": ", ".join(bits)})
            for item in step["info"]["found"]:
                out.append({"kind": "found", "text": "New in the Archive: " + lore.COLLECT_BY_ID[item][2]})
            arrive(story.SCENES[step["after"][0]], step["after"], story.SCENES[step["before"][0]]["day"], n + 1)
        return out

    def _tried(self):
        return {(e[0], e[1]) for e in self.taken}

    def _choices(self):
        out = []
        tried = self._tried()
        for i, c in enumerate(self.scene["choices"]):
            ok, why = walker.available(self.state, i)
            out.append({"i": i, "text": c["text"], "tried": (self.state[0], i) in tried, "ok": ok, "why": why})
        return out

    def _stats(self):
        return [{"id": name, "name": name.capitalize(), "value": v, "word": _word(v), "max": kit.HIGH}
                for name, v in zip(kit.STATS, self.state[1])]

    def _loose(self):
        return explore.loose_end(self.taken, self.path)

    def _hint(self):
        if not self.rung:
            return {"rung": 0}
        le = self._loose()
        if le is None:
            return {"rung": self.rung, "kind": "none", "nudge": "Every reply that can be sent has been tried. The map is complete.", "hint": "", "answer": ""}
        scene = story.SCENES[le["scene"]]
        out = {"rung": self.rung, "kind": le["kind"]}
        if le["kind"] == "locked":
            out["nudge"] = "Everything open has been tried. A reply on day %d is shut: %s." % (scene["day"], le["why"].lower())
            out["hint"] = "It is in Day %d: %s. Different earlier replies change Trust, Supplies and Hope." % (scene["day"], scene["title"])
            out["answer"] = "Go to Day %d: %s and look at the shut reply." % (scene["day"], scene["title"])
        else:
            text = scene["choices"][le["choice"]]["text"]
            out["nudge"] = "There is a path you have not walked on day %d." % scene["day"]
            out["hint"] = "Look at Day %d: %s." % (scene["day"], scene["title"])
            out["answer"] = "In Day %d: %s, try: %s" % (scene["day"], scene["title"], text)
        out["do"] = "Rewind there" if le["kind"] == "rewind" else "Take me there"
        return out

    def _map(self):
        days = []
        tried_choices = self._tried()
        for d in range(1, story.DAYS + 1):
            nodes = []
            for sid in story.ORDER:
                sc = story.SCENES[sid]
                if sc["day"] != d:
                    continue
                seen = sid in self.seen
                total = len(sc["choices"])
                tried = sum(1 for i in range(total) if (sid, i) in tried_choices)
                row = {"id": sid, "seen": seen, "loose": False, "current": sid == self.state[0], "end": bool(sc["end"]), "tried": tried, "total": total,
                       "title": sc["title"] if seen else "", "choices": []}
                if seen:
                    for i, c in enumerate(sc["choices"]):
                        targets = [story.SCENES[t]["title"] for _cond, t in c["to"] if (sid, i, t) in self.taken]
                        row["choices"].append({"i": i, "tried": (sid, i) in tried_choices, "text": c["text"] if (sid, i) in tried_choices else "",
                                               "to": targets, "paths_left": sum(1 for _cond, t in c["to"] if (sid, i, t) not in self.taken)})
                nodes.append(row)
            for row in nodes:
                row["loose"] = row["seen"] and not row["end"] and (row["tried"] < row["total"] or any(c["paths_left"] for c in row["choices"] if c["tried"]))
            days.append({"day": d, "title": lore.DAYS[d][0], "nodes": nodes, "unseen": sum(1 for n in nodes if not n["seen"])})
        return days

    def _archive(self):
        sections = []
        for kind in lore.KINDS:
            entries = []
            for cid, k, title, text, hint in lore.COLLECT:
                if k != kind:
                    continue
                got = cid in self.found
                entries.append({"id": cid, "found": got, "title": title if got else "Not found yet", "text": text if got else hint})
            sections.append({"id": kind, "name": lore.KIND_NAME[kind], "found": sum(1 for e in entries if e["found"]), "total": len(entries), "entries": entries})
        return sections

    def view(self, message="", ok=True):
        scene = self.scene
        facts = self.facts()
        peek = explore.peek(self.state, self.taken)
        showing = peek["open"] and self.peek_path == self.path
        done = len(self.found) + len(self.taken) + len(self.seen)
        view = {
            "ok": ok, "message": message,
            "run": {"path": self.path, "steps": len(self.steps), "day": scene["day"], "day_title": lore.DAYS[scene["day"]][0], "days": story.DAYS,
                    "scene": scene["id"], "title": scene["title"], "flags": list(self.state[2])},
            "stats": self._stats(), "choices": self._choices(), "transcript": self._transcript(),
            "ending": ({"id": scene["end"], "title": scene["title"]} if scene["end"] else None),
            "art": render.scene(scene["day"], self.state[2], scene["id"]), "peek": {"open": peek["open"], "need": peek["need"], "showing": showing, "rows": peek["rows"] if showing else []},
            "progress": {"scenes": [len(self.seen), len(story.SCENES)], "tried": [len(self.taken), len(story.EDGES)],
                         "endings": [len(self.endings), len(story.ENDING_IDS)], "archive": [len(self.found), len(lore.COLLECT)],
                         "percent": int(100 * done / TOTAL_THINGS)},
            "endings": [{"id": eid, "scene": sid, "title": title if eid in self.endings else "Not found yet", "seen": eid in self.endings}
                        for eid, sid, title in story.ENDINGS],
            "map": self._map(), "archive": self._archive(), "tally": dict(self.tally),
            "hint": self._hint(), "about": info.view(),
            "goals": achievements.goals(facts), "achievements": achievements.view(facts),
        }
        view["map_svg"] = render.map_svg([{"day": d["day"], "nodes": d["nodes"]} for d in view["map"]])
        return view

    # ---- actions ---------------------------------------------------------------------------------------------------------
    def choose(self, idx):
        ok, why = walker.available(self.state, idx)
        if not ok:
            return False, why
        before = self.state
        self.path += str(idx)
        self.tally["sent"] += 1
        self.rung = 0
        old_found = set(self.found)
        self._sync()
        d = self.steps[-1]["info"]["delta"]
        bits = ["%s %+d" % (name.capitalize(), v) for name, v in zip(kit.STATS, d) if v]
        new = [lore.COLLECT_BY_ID[c][2] for c in self.found - old_found]
        msg = "Sent." + (" " + ", ".join(bits) + "." if bits else "")
        if new:
            msg += " New in the Archive: " + ", ".join(new) + "."
        if before[0] != self.state[0] and self.scene["end"]:
            msg += " Ending: " + self.scene["title"] + "."
        return True, msg

    def rewind(self, step):
        if isinstance(step, bool) or not isinstance(step, int) or not 0 <= step < len(self.path):
            return False, "There is nothing to rewind to there."
        self.path = self.path[:step]
        self.tally["rewinds"] += 1
        self.rung = 0
        self._sync()
        return True, "Rewound. Nothing you found or tried is lost."


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
    elif action == "choose":
        idx = request.get("i")
        if isinstance(idx, bool) or not isinstance(idx, int):
            ok, message = False, "That is not a reply."
        else:
            ok, message = g.choose(idx)
    elif action == "rewind":
        ok, message = g.rewind(request.get("step"))
    elif action == "restart":
        ok, message = g.rewind(0) if g.path else (False, "You are already at the start.")
    elif action == "goto":
        sid = request.get("scene")
        if not isinstance(sid, str) or sid not in g.seen:
            ok, message = False, "You have not seen that scene yet."
        else:
            route = explore.route_to(g.taken, sid)
            if route is None:
                ok, message = False, "No route by replies you have tried."
            else:
                g.path = route
                g.tally["jumps"] += 1
                g.rung = 0
                g._sync()
                message = "Here you are."
    elif action == "peek":
        peek = explore.peek(g.state, g.taken)
        if not peek["open"]:
            ok, message = False, "Try %d more different %s here first." % (peek["need"], "reply" if peek["need"] == 1 else "replies")
        else:
            if g.peek_path != g.path:
                g.tally["peeks"] += 1
            g.peek_path = g.path
    elif action == "hint":
        if g.rung >= 3:
            ok, message = False, "That is every rung: the answer is showing."
        else:
            g.rung += 1
            g.tally["hints"] += 1
    elif action == "hint_do":
        le = g._loose() if g.rung >= 3 else None
        if g.rung < 3 or le is None:
            ok, message = False, "Climb to the answer first."
        else:
            if le["kind"] == "rewind":
                g.path = g.path[:le["step"]]
                g.tally["rewinds"] += 1
            else:
                g.path = le["path"]
                g.tally["jumps"] += 1
            g.rung = 0
            g._sync()
            message = "Here is the loose end."
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
        refresh = getattr(js.window, "strandedRefresh", None)
        if refresh is not None:
            refresh()
    except Exception:
        pass
