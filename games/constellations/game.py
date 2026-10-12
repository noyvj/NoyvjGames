"""Constellations -- the engine's single entry point (the Picture Grid / Hull Repair pattern).

The view (app.js) never reads engine objects: it sends one JSON string to `handle` and draws the JSON that comes back.
`get_state()` / `load_state()` are the shared save widget's contract (planning/SAVE-BUTTON-INTEGRATION.md). Nothing here reads a clock or
a random source: whether a figure is valid is a pure function of the chart and the lines drawn (sky.py).

Actions (every request is {"action": ..., ...}; every reply is the whole view):
  open                    the current view
  pick {chart}            go to a chart (it must be in an open season)
  next                    go to the next chart not yet finished (open seasons only)
  toggle {a, b}           draw the line between stars a and b, or erase it if it is there (one call = one undo step)
  undo / redo             step back / forward through your lines on this chart
  clear                   erase every line you drew on this chart (one undo step)
  finish                  add the figure to the atlas (only when every number holds and the lines make one connected figure)
  hint {confirm}          press the hint ladder once (only ever on a press): 1 nudge, 2 hint, 3 the whole figure as a ghost (see hints.py)
  hint_draw               after rung 3: draw the ghost figure (erasing lines that do not belong); one undo step
  difficulty {level}      easy | normal | hard (told by the page, never saved; only changes how the hint ladder opens)
  reset                   start over (everything)

The names of a chart, of its stars and its note are in the view only once the chart is finished. Stars are A, B, C ... from left to right.
"""

import json

import charts
import goals
import hints
import info
import sky

TALLY_KEYS = ("draws", "erases", "hints")
LEVELS = ("easy", "normal", "hard")
difficulty = "normal"            # told by the page ({"action": "difficulty"}), a per-browser choice that is never saved; reset and load leave it alone
MAX_COUNT = 10 ** 9
MAX_UNDO = 400
SCHEMA = 1                       # the save layout version; a save from a newer layout is not read
ATLAS_W, ATLAS_H = 1440, 720     # the sky atlas canvas: right ascension runs right to left over 24 hours, declination from +90 to -90
ATLAS_K = 4.0                    # atlas units per degree


def _int(value, low=0, high=MAX_COUNT, default=0):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        return default
    return value


def _plural(n, one, many):
    return "%d %s" % (n, one if n == 1 else many)


def _parse_edge(text, chart):
    """'3-7' -> the chart's line index, or None if it is not an allowed line the player may draw."""
    if not isinstance(text, str) or text.count("-") != 1:
        return None
    a, _, b = text.partition("-")
    if not (a.isdigit() and b.isdigit()):
        return None
    k = chart.edge(int(a), int(b))
    return k if k is not None and k not in chart.must and k not in chart.never else None


def _position_words(x, y, box):
    x0, y0, x1, y1 = box
    col = 0 if x < x0 + (x1 - x0) / 3.0 else 2 if x > x0 + 2 * (x1 - x0) / 3.0 else 1
    row = 0 if y < y0 + (y1 - y0) / 3.0 else 2 if y > y0 + 2 * (y1 - y0) / 3.0 else 1
    names = [["upper left", "top", "upper right"], ["left", "centre", "right"], ["lower left", "bottom", "lower right"]]
    return names[row][col]


def _brightness_words(mag):
    return "very bright" if mag < 1.5 else "bright" if mag < 2.5 else "medium" if mag < 3.5 else "faint"


class Game:
    def __init__(self):
        self.solved = {}                 # chart id -> number of line changes it took the first time
        self.work = {}                   # chart id -> set of line indices the player drew (unfinished charts only)
        self.moves = {}                  # chart id -> line changes made on the chart in self.work
        self.tally = {key: 0 for key in TALLY_KEYS}
        self.current = charts.ORDER[0]
        self.undo = []                   # [(chart id, [(line index, True if drawn / False if erased)])]  -- this session only
        self.redo = []
        self.message = ""
        self.say = ""
        self.just = None                 # the chart finished by the last action (not saved)
        self.hint = None                 # the ladder in progress on this chart (not saved; any change to the lines clears it)
        self.hinted = {}                 # chart id -> highest rung asked while it was first being solved (1 nudge, 2 hint, 3 answer)

    # ---- the current chart -----------------------------------------------------------------------------------------
    @property
    def chart(self):
        return charts.BY_ID[self.current]

    @property
    def rules(self):
        return charts.rules(self.current)

    def status(self, cid=None):
        return "solved" if (cid or self.current) in self.solved else "open"

    def editable(self):
        return self.status() != "solved"

    def drawn(self, cid=None):
        """The set of line indices on the chart: for a finished chart the traditional figure, otherwise the given lines plus the player's."""
        cid = cid or self.current
        rules = charts.rules(cid)
        if cid in self.solved:
            return {rules.index[tuple(e)] for e in charts.BY_ID[cid]["figure"]}
        return set(rules.must) | self.work.get(cid, set())

    def _enter(self, cid):
        self.current = cid
        self.just = None
        self.hint = None
        self.undo = []
        self.redo = []

    # ---- save ------------------------------------------------------------------------------------------------------
    def to_dict(self):
        """Only what differs from a fresh game is written (plus the layout version), so old and new saves stay compatible."""
        data = {"schema": SCHEMA}
        if self.current != charts.ORDER[0]:
            data["cur"] = self.current
        if self.solved:
            data["solved"] = {cid: self.solved[cid] for cid in charts.ORDER if cid in self.solved}
        work = {}
        for cid in charts.ORDER:
            lines = self.work.get(cid)
            if lines and cid not in self.solved:
                rules = charts.rules(cid)
                work[cid] = ["%d-%d" % rules.edges[k] for k in sorted(lines)]
        if work:
            data["work"] = work
        moves = {cid: n for cid, n in self.moves.items() if n and cid in work}
        if moves:
            data["moves"] = moves
        tally = {k: v for k, v in self.tally.items() if v}
        if tally:
            data["tally"] = tally
        asked = {cid: self.hinted[cid] for cid in charts.ORDER if self.hinted.get(cid)}
        if asked:
            data["hints"] = asked
        return data

    def load(self, data):
        """Take a saved dict, checking every field on its own; a bad field falls back to its default. A finished chart only counts if its
        season was open by the charts finished before it, and a saved line must be a real, allowed line of that chart."""
        data = data if isinstance(data, dict) else {}
        schema = data.get("schema", SCHEMA)
        if isinstance(schema, bool) or not isinstance(schema, int) or not 1 <= schema <= SCHEMA:
            data = {}                                            # an unknown layout is never half-read
        self.solved, self.work, self.moves = {}, {}, {}
        raw_solved = data.get("solved") if isinstance(data.get("solved"), dict) else {}
        for c in charts.ALL:                                     # season order, so each season is judged on those before it
            if c["id"] in raw_solved and charts.season_open(self.solved, c["season"]):
                self.solved[c["id"]] = _int(raw_solved[c["id"]])
        raw_work = data.get("work") if isinstance(data.get("work"), dict) else {}
        raw_moves = data.get("moves") if isinstance(data.get("moves"), dict) else {}
        for c in charts.ALL:
            cid = c["id"]
            if cid not in raw_work or cid in self.solved or not charts.chart_open(self.solved, cid) or not isinstance(raw_work[cid], list):
                continue
            rules = charts.rules(cid)
            lines = {k for k in (_parse_edge(t, rules) for t in raw_work[cid]) if k is not None}
            if not lines:
                continue
            self.work[cid] = lines
            self.moves[cid] = _int(raw_moves.get(cid))
            if sky.is_valid(rules, self.drawn(cid)):             # a finished figure is never left lying around unfinished
                self._finish(cid)
        tally = data.get("tally") if isinstance(data.get("tally"), dict) else {}
        self.tally = {key: _int(tally.get(key)) for key in TALLY_KEYS}
        raw_hints = data.get("hints") if isinstance(data.get("hints"), dict) else {}
        self.hinted = {c["id"]: raw_hints[c["id"]] for c in charts.ALL
                       if c["id"] in raw_hints and charts.chart_open(self.solved, c["id"]) and _int(raw_hints[c["id"]], 1, 3, 0)}
        cur = data.get("cur")
        self._enter(cur if isinstance(cur, str) and charts.chart_open(self.solved, cur) else charts.ORDER[0])
        self.message = self.say = ""

    # ---- the view --------------------------------------------------------------------------------------------------
    def _seasons(self):
        out = []
        for s, season in enumerate(charts.SEASONS):
            entries = []
            for c in season["charts"]:
                done = c["id"] in self.solved
                entry = {"id": c["id"], "number": c["number"], "stars": len(c["stars"]), "solved": done, "current": c["id"] == self.current}
                if done:
                    entry.update({"name": c["name"], "meaning": c["meaning"], "moves": self.solved[c["id"]]})
                entries.append(entry)
            out.append({"id": season["id"], "name": season["name"], "blurb": season["blurb"], "open": charts.season_open(self.solved, s),
                        "done": charts.season_done(self.solved, s), "total": len(season["charts"]), "need": max(0, charts.season_need(s) - (charts.season_done(self.solved, s - 1) if s else 0)),
                        "need_total": charts.season_need(s), "after": charts.SEASONS[s - 1]["name"] if s else "", "charts": entries})
        return out

    def _atlas(self):
        """The wide planisphere: every chart has a place at its real right ascension and declination. A finished chart shows its figure in
        that place; an unfinished one shows only a dim ring there (its shape and name stay hidden)."""
        items = []
        for c in charts.ALL:
            a = c["atlas"]
            cx = (24.0 - a["ra"]) / 24.0 * ATLAS_W
            cy = (90.0 - a["dec"]) / 180.0 * ATLAS_H
            k = 57.29578 * ATLAS_K / a["scale"]
            pts = [[round(cx + (s["x"] - a["ox"]) * k, 1), round(cy + (s["y"] - a["oy"]) * k, 1)] for s in c["stars"]]
            radius = max(((px - cx) ** 2 + (py - cy) ** 2) ** 0.5 for px, py in pts) + 12
            item = {"id": c["id"], "season": c["season"], "number": c["number"], "x": round(cx, 1), "y": round(cy, 1), "r": round(radius, 1),
                    "solved": c["id"] in self.solved, "current": c["id"] == self.current}
            if item["solved"]:
                item.update({"name": c["name"], "pts": pts, "lines": [list(e) for e in c["figure"]]})
            items.append(item)
        return {"w": ATLAS_W, "h": ATLAS_H, "items": items}

    def _cards(self):
        """One card per finished constellation (the atlas page text)."""
        cards = []
        for c in charts.ALL:
            if c["id"] in self.solved:
                cards.append({"id": c["id"], "name": c["name"], "meaning": c["meaning"], "note": c["note"], "stars": len(c["stars"]),
                              "brightest": dict(c["brightest"]), "best": c["best"], "season": charts.SEASONS[c["season"]]["name"],
                              "number": c["number"], "moves": self.solved[c["id"]], "code": c["code"], "hips": [st["hip"] for st in c["stars"]],
                              "sources": ["Star positions and brightness: %s." % c["source"]["stars"],
                                          "Line figure: %s." % c["source"]["figure"],
                                          "The note is written for this game. Read on %s." % c["source"]["read"]]})
        return cards

    def _words(self, c, rules, drawn, solved):
        """The accessible text version of the chart: every star, what it needs, where it sits and what it can join."""
        stars = c["stars"]
        box = (min(s["x"] for s in stars), min(s["y"] for s in stars), max(s["x"] for s in stars), max(s["y"] for s in stars))
        report = sky.analyse(rules, drawn)
        letter = charts.LETTERS
        lines = ["A chart of %s stars, lettered %s to %s from left to right." % (len(stars), letter[0], letter[len(stars) - 1])]
        for i, s in enumerate(stars):
            need = rules.need.get(i)
            part = "Star %s, %s, %s (magnitude %s)" % (letter[i], _position_words(s["x"], s["y"], box), _brightness_words(s["mag"]), s["mag"])
            if solved:
                part += ", " + s["name"]
            part += ", needs %s and has %d" % (_plural(need, "line", "lines"), report["degree"][i]) if need is not None else ", no number, has %d" % report["degree"][i]
            join = [letter[o] for k in rules.inc[i] for o in rules.edges[k] if o != i and k not in rules.never]
            part += ". Can join: %s." % (", ".join(sorted(join)) if join else "nothing")
            lines.append(part)
        for k, m in rules.cross_ok:
            lines.append("On this chart the lines %s-%s and %s-%s are allowed to cross each other, and where they cross they count as joined." % (
                letter[rules.edges[k][0]], letter[rules.edges[k][1]], letter[rules.edges[m][0]], letter[rules.edges[m][1]]))
        given = [("%s-%s" % (letter[rules.edges[k][0]], letter[rules.edges[k][1]])) for k in sorted(rules.must)]
        if given:
            lines.append("Lines already drawn for you: %s." % ", ".join(given))
        crossed = [("%s-%s" % (letter[rules.edges[k][0]], letter[rules.edges[k][1]])) for k in sorted(rules.never)]
        if crossed:
            lines.append("Pairs crossed out, never joined: %s." % ", ".join(crossed))
        mine = [("%s-%s" % (letter[rules.edges[k][0]], letter[rules.edges[k][1]])) for k in sorted(drawn - set(rules.must))]
        lines.append("Lines you have drawn: %s." % (", ".join(mine) if mine else "none yet"))
        return lines

    def _problems(self, report, drawn):
        if not drawn:
            return "No lines yet."
        bits = []
        if report["under"]:
            bits.append("%s still need more lines" % _plural(len(report["under"]), "numbered star", "numbered stars"))
        if report["over"]:
            bits.append("%s too many" % _plural(len(report["over"]), "numbered star has", "numbered stars have"))
        if report["crossings"]:
            bits.append(_plural(len(report["crossings"]), "pair of lines crosses", "pairs of lines cross"))
        if report["never_used"]:
            bits.append("a crossed-out pair is joined")
        if report["parts"] > 1 and not report["under"] and not report["over"] and not report["crossings"]:
            bits.append("the lines are in %d separate pieces" % report["parts"])
        return ("; ".join(bits) + ".").capitalize() if bits else "Every number holds and the lines make one figure."

    def view(self, message=None, ok=True, say=None):
        if message is not None:
            self.message = message
        self.say = say if say is not None else (self.message if message else "")
        c = self.chart
        rules = self.rules
        status = self.status()
        drawn = self.drawn()
        report = sky.analyse(rules, drawn)
        cross_lines = {k for pair in report["crossings"] for k in pair}
        solved = status == "solved"
        stars = []
        for i, s in enumerate(c["stars"]):
            need = rules.need.get(i)
            have = report["degree"][i]
            state = "free" if need is None else "over" if have > need else "met" if have == need else "short"
            star = {"i": i, "x": s["x"], "y": s["y"], "mag": s["mag"], "letter": charts.LETTERS[i], "need": need, "have": have, "state": state}
            if solved:
                star["name"] = s["name"]
                star["label"] = s["name"] if s.get("proper") or not s.get("bayer") else s["bayer"]      # a short tag for the board: a proper name, or "Tau Gem"
            stars.append(star)
        lines = [{"a": rules.edges[k][0], "b": rules.edges[k][1], "given": k in rules.must, "cross": k in cross_lines} for k in sorted(drawn)]
        season = charts.SEASONS[c["season"]]
        problems = self._problems(report, drawn)
        joined = [[list(rules.edges[k]), list(rules.edges[m])] for k, m in rules.cross_ok if k in drawn and m in drawn]
        view = {
            "ok": ok, "message": self.message, "say": self.say,
            "chart": {"id": c["id"], "number": c["number"], "of": len(season["charts"]), "season": season["name"], "season_index": c["season"],
                      "w": c["w"], "h": c["h"], "stars": stars, "allowed": [list(e) for k, e in enumerate(rules.edges) if k not in rules.never],
                      "never": [list(rules.edges[k]) for k in sorted(rules.never)], "lines": lines, "status": status, "joined": joined,
                      "moves": self.moves.get(c["id"], 0) if not solved else self.solved[c["id"]], "best": self.solved.get(c["id"])},
            "valid": report["valid"] and not solved, "problems": problems, "parts": report["parts"],
            "words": self._words(c, rules, drawn, solved),
            "editable": not solved, "can_undo": bool(self.undo), "can_redo": bool(self.redo), "can_clear": bool(self.work.get(c["id"])) and not solved,
            "just": self.just, "seasons": self._seasons(), "atlas": self._atlas(), "cards": self._cards(), "tally": dict(self.tally),
            "hint": self._hint_view(), "hint_ui": self._hint_ui(status), "goals": goals.queue(self.solved, self.tally["draws"]), "difficulty": difficulty,
            "totals": {"charts": len(charts.ORDER), "done": len(self.solved), "stars": charts.star_total(self.solved),
                       "pages_open": sum(1 for s in range(len(charts.SEASONS)) if charts.season_open(self.solved, s)), "pages": len(charts.SEASONS),
                       "seasons_done": charts.seasons_finished(self.solved), "lines": self.tally["draws"], "erased": self.tally["erases"], "hints": self.tally["hints"]},
            "info": info.view(),
        }
        if solved:
            view["chart"].update({"name": c["name"], "meaning": c["meaning"], "note": c["note"], "brightest": dict(c["brightest"]), "best_time": c["best"]})
        return view

    # ---- lines -----------------------------------------------------------------------------------------------------
    def toggle(self, a, b):
        c = self.chart
        rules = self.rules
        if not self.editable():
            return self.view("This constellation is in your atlas. Its lines are finished.", ok=False)
        n = len(c["stars"])
        if any(isinstance(v, bool) or not isinstance(v, int) or not 0 <= v < n for v in (a, b)) or a == b:
            return self.view("That is not a pair of stars.", ok=False)
        k = rules.edge(a, b)
        names = "%s and %s" % (charts.LETTERS[min(a, b)], charts.LETTERS[max(a, b)])
        if k is None:
            return self.view("Stars %s are too far apart to be joined on this chart." % names, ok=False)
        if k in rules.must:
            return self.view("The line between %s is already drawn for you and stays." % names, ok=False)
        if k in rules.never:
            return self.view("The pair %s is crossed out: it can never be joined." % names, ok=False)
        lines = self.work.setdefault(c["id"], set())
        added = k not in lines
        if added:
            lines.add(k)
            self.tally["draws"] += 1
        else:
            lines.discard(k)
            self.tally["erases"] += 1
        self.moves[c["id"]] = self.moves.get(c["id"], 0) + 1
        self.undo.append((c["id"], [(k, added)]))
        del self.undo[:-MAX_UNDO]
        self.redo = []
        self.just = None
        self.hint = None
        return self._after("Joined" if added else "Erased the line between", a, b)

    def _after(self, verb, a, b):
        report = sky.analyse(self.rules, self.drawn())
        parts = ["%s %s and %s." % (verb, charts.LETTERS[min(a, b)], charts.LETTERS[max(a, b)])]
        for v in (min(a, b), max(a, b)):
            need = self.rules.need.get(v)
            if need is not None:
                parts.append("%s has %d of %d." % (charts.LETTERS[v], report["degree"][v], need))
        if report["valid"]:
            parts.append("Every number holds and the figure is one piece. Press Done.")
        return self.view("", say=" ".join(parts))

    def step(self, forward):
        """Undo (forward False) or redo (forward True) the last change on this chart."""
        stack, other = (self.redo, self.undo) if forward else (self.undo, self.redo)
        if not stack or not self.editable():
            return self.view("Nothing to %s." % ("redo" if forward else "undo"), ok=False)
        cid, changes = stack.pop()
        lines = self.work.setdefault(cid, set())
        for k, added in (changes if forward else reversed(changes)):
            if added == forward:
                lines.add(k)
            else:
                lines.discard(k)
        other.append((cid, changes))
        self.hint = None
        return self.view("", say="%s." % ("Redone" if forward else "Undone"))

    def clear(self):
        if not self.editable():
            return self.view("This constellation is in your atlas.", ok=False)
        lines = self.work.get(self.current)
        if not lines:
            return self.view("There are no lines of yours to erase.", ok=False)
        changes = [(k, False) for k in sorted(lines)]
        self.tally["erases"] += len(changes)
        self.moves[self.current] = self.moves.get(self.current, 0) + 1
        lines.clear()
        self.hint = None
        self.undo.append((self.current, changes))
        del self.undo[:-MAX_UNDO]
        self.redo = []
        return self.view("", say="Erased all your lines on this chart.")

    # ---- finishing --------------------------------------------------------------------------------------------------
    def _finish(self, cid):
        """Add the chart to the atlas, keep the number of line changes it took, free the work."""
        first = cid not in self.solved
        if first:
            self.solved[cid] = self.moves.get(cid, 0)
        self.work.pop(cid, None)
        self.moves.pop(cid, None)
        self.hint = None
        return first

    def finish(self):
        if not self.editable():
            return self.view("This constellation is already in your atlas.", ok=False)
        report = sky.analyse(self.rules, self.drawn())
        if not report["valid"]:
            return self.view("Not yet: " + self._problems(report, self.drawn()).lower(), ok=False)
        cid = self.current
        c = self.chart
        was_open = [charts.season_open(self.solved, s) for s in range(len(charts.SEASONS))]
        self._finish(cid)
        self.undo = []
        self.redo = []
        opened = [charts.SEASONS[s]["name"] for s in range(len(charts.SEASONS)) if charts.season_open(self.solved, s) and not was_open[s]]
        self.just = {"id": cid, "name": c["name"], "opened": opened, "moves": self.solved[cid], "season_done": charts.season_done(self.solved, c["season"]) == len(charts.SEASONS[c["season"]]["charts"])}
        text = "%s is in your atlas." % c["name"]
        if opened:
            text += " A new page opens: %s." % ", ".join(opened)
        return self.view(text)

    # ---- the hint ladder -----------------------------------------------------------------------------------------------
    def _hint_view(self):
        """What the ladder has shown so far on this chart: only the rungs the player pressed for (never a line before rung 2, never the figure before rung 3)."""
        h = self.hint
        if not h or h["cid"] != self.current or self.status() == "solved":
            return None
        rules = self.rules
        out = {"rung": h["rung"], "kind": h["kind"], "star": h["star"], "nudge": h["nudge"], "detail": h["detail"] if h["rung"] >= 2 else "",
               "line": list(rules.edges[h["line"]]) if h["rung"] >= 2 else None, "answer": "", "ghost": [], "erase": [], "can_draw": False}
        if h["rung"] >= 3:
            out["answer"] = h["answer"]
            out["ghost"] = [list(rules.edges[k]) for k in h["missing"]]
            out["erase"] = [list(rules.edges[k]) for k in h["wrong"]]
            out["can_draw"] = True
        return out

    def _hint_ui(self, status):
        """What the hint button should offer next: which rung, its words, whether it needs a confirm, whether the level stops it."""
        h = self.hint if self.hint and self.hint["cid"] == self.current else None
        rung = h["rung"] if h else 0
        limit = 2 if difficulty == "hard" else 3
        nxt = 0 if rung >= limit else rung + 1
        labels = {1: "Would you like a suggestion?", 2: "Another hint", 3: "Another hint: show the whole figure"}
        return {"available": status != "solved", "next": nxt, "label": labels.get(nxt, ""), "limit": rung >= limit and difficulty == "hard",
                "confirm": nxt == 3 and difficulty != "easy", "opens_two": nxt == 1 and difficulty == "easy",
                "can_draw": bool(h and rung >= 3), "here": self.hinted.get(self.current, 0)}

    def _note_hint(self, rung):
        """Count one press of the ladder and keep the chart's highest rung (only while it is being solved the first time)."""
        self.tally["hints"] += 1
        if self.status() == "open":
            self.hinted[self.current] = max(self.hinted.get(self.current, 0), rung)

    def ask_hint(self, confirm=False):
        if not self.editable():
            return self.view("This constellation is in your atlas.", ok=False)
        h = self.hint if self.hint and self.hint["cid"] == self.current else None
        limit = 2 if difficulty == "hard" else 3
        if h is None:
            found = hints.pick(self.chart, self.rules, self.drawn(), charts.LETTERS)
            if found is None:
                return self.view("Nothing is left to suggest: every number holds and the figure is one piece. Press Done.", ok=False)
            h = dict(found, cid=self.current, rung=2 if difficulty == "easy" else 1, answer="")
            self.hint = h
            self._note_hint(h["rung"])
            return self.view(h["nudge"] if h["rung"] == 1 else h["nudge"] + " " + h["detail"])
        if h["rung"] >= limit:
            return self.view("Hard has no answer step: the nudge and the hint are all the help there is.", ok=False) if difficulty == "hard" else \
                self.view("The whole figure is already shown.", ok=False)
        if h["rung"] == 1:
            h["rung"] = 2
            self._note_hint(2)
            return self.view(h["detail"])
        if difficulty != "easy" and not confirm:
            return self.view("Showing the whole figure takes the puzzle out of it. Press again to confirm.", ok=False)
        h["rung"] = 3
        h["answer"] = hints.answer_text(self.rules, charts.LETTERS, h["missing"], h["wrong"])
        self._note_hint(3)
        return self.view(h["answer"])

    def draw_hint(self):
        """Draw the figure the third rung showed: erase the lines that do not belong, add the missing ones, as one undo step. It is not the
        player's own drawing, so the tally of lines drawn and erased does not move. Done is still the player's to press."""
        h = self.hint if self.hint and self.hint["cid"] == self.current else None
        if not self.editable() or h is None or h["rung"] < 3:
            return self.view("Ask for the whole figure first.", ok=False)
        lines = self.work.setdefault(self.current, set())
        changes = [(k, False) for k in h["wrong"] if k in lines] + [(k, True) for k in h["missing"] if k not in lines]
        for k, added in changes:
            if added:
                lines.add(k)
            else:
                lines.discard(k)
        self.moves[self.current] = self.moves.get(self.current, 0) + 1
        self.undo.append((self.current, changes))
        del self.undo[:-MAX_UNDO]
        self.redo = []
        self.just = None
        self.hint = None
        if sky.is_valid(self.rules, self.drawn()):
            return self.view("The figure is drawn. Press Done to add it to your atlas.")
        return self.view("Drawn.")

    # ---- navigation ---------------------------------------------------------------------------------------------------
    def pick(self, cid):
        if not isinstance(cid, str) or cid not in charts.BY_ID:
            return self.view("There is no such chart.", ok=False)
        if not charts.chart_open(self.solved, cid):
            s = charts.BY_ID[cid]["season"]
            return self.view("That page opens when %d charts in %s are done." % (charts.season_need(s), charts.SEASONS[s - 1]["name"]), ok=False)
        if cid != self.current:
            self._enter(cid)
        return self.view("")

    def next(self):
        order = charts.ORDER
        start = order.index(self.current)
        for step in range(1, len(order) + 1):
            cid = order[(start + step) % len(order)]
            if cid not in self.solved and charts.chart_open(self.solved, cid):
                self._enter(cid)
                return self.view("")
        return self.view("Every open chart is done." if len(self.solved) < len(order) else "Every chart is done.", ok=False)


game = Game()


def set_difficulty(level):
    """Easy / Normal / Hard only change how the hint ladder opens; the charts, the numbers, the rules and every record stay the same."""
    global difficulty
    if level not in LEVELS:
        return game.view("That is not a difficulty.", ok=False)
    difficulty = level
    game.hint = None                                         # a ladder in progress was opened under the old level
    return game.view("")


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
        return json.dumps(g.pick(request.get("chart")))
    if action == "next":
        return json.dumps(g.next())
    if action == "toggle":
        return json.dumps(g.toggle(request.get("a"), request.get("b")))
    if action == "undo":
        return json.dumps(g.step(False))
    if action == "redo":
        return json.dumps(g.step(True))
    if action == "clear":
        return json.dumps(g.clear())
    if action == "finish":
        return json.dumps(g.finish())
    if action == "hint":
        return json.dumps(g.ask_hint(request.get("confirm") is True))
    if action == "hint_draw":
        return json.dumps(g.draw_hint())
    if action == "difficulty":
        return json.dumps(set_difficulty(request.get("level")))
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
        refresh = getattr(js.window, "constellationsRefresh", None)
        if refresh is not None:
            refresh()
    except Exception:
        pass
