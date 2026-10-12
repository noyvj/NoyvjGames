"""Reaction Bench -- the engine's single entry point (the Picture Grid / Mirror Lab pattern).

The view (app.js) never reads engine objects: it sends one JSON string to `handle` and draws the JSON that comes back.
`get_state()` / `load_state()` are the shared save widget's contract (planning/SAVE-BUTTON-INTEGRATION.md). Nothing here reads a
clock or a random source: the ledger, the balance check and the gate are pure functions of the equation and the dials.

Actions (every request is {"action": ..., ...}; every reply is the whole view):
  open                    the current view
  pick {reaction}         go to an order (it must be in an open chapter)
  next                    go to the next open order that is not on the shelf yet
  dial {index, value}     set one coefficient dial (1 to 12); or {index, delta} to turn it by a step
  reset_dials             put every dial of this order back to 1
  choose {option}         in a product-choice round: choose one of the candidate lists for what comes out
  run                     press Run: only when the product is chosen and the ledger reads equal; puts the compound on the shelf
  hint {confirm}          press the hint ladder once (only ever on a press): 1 nudge, 2 hint, 3 answer (see hints.py)
  difficulty {level}      easy | normal | hard (told by the page, never saved; only changes how the hint ladder opens)
  reset                   start over (everything)

The ledger's difference is right minus left, so +2 means two too many on the right and -1 means one too few.

The view also carries `achievements` (id, label, description, earned, have, need for each of the 14; see achievements.py); the save
writes `achievements_earned` as a projection that load never reads back.
"""

import json

import achievements
import chem
import elements
import goals
import hints
import info
import reactions

MAX_COUNT = 10 ** 9
SCHEMA = 1                          # the save layout version; a save from a newer layout is not read
TALLY_KEYS = ("turns", "runs", "tries", "hints")
LEVELS = ("easy", "normal", "hard")
difficulty = "normal"            # told by the page ({"action": "difficulty"}), a per-browser choice that is never saved; reset and load leave it alone
FIRST = reactions.ORDER[0]


def _int(value, low=0, high=MAX_COUNT, default=0):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        return default
    return value


def _species(formula):
    return {"formula": formula, "name": reactions.name_of(formula), "tree": chem.parse_tree(formula)}


def equation_words(reactants, products, coefs):
    left = " + ".join("%d %s" % (coefs[i], f) for i, f in enumerate(reactants))
    right = " + ".join("%d %s" % (coefs[len(reactants) + i], f) for i, f in enumerate(products))
    return "%s gives %s" % (left, right)


class Game:
    def __init__(self):
        self.shelf = {}                  # reaction id -> times it has been run
        self.dials = {}                  # reaction id -> its coefficient dials (only when not all 1)
        self.picked = set()              # product-choice rounds whose products have been chosen
        self.tried = {}                  # reaction id -> candidate lists already tried and wrong
        self.first = set()               # rounds chosen right on the first try
        self.hint = None                 # the ladder in progress on this order (not saved; any change to the order clears it)
        self.hinted = {}                 # order id -> highest rung asked while it was not yet shelved (1 nudge, 2 hint, 3 answer)
        self.tally = {key: 0 for key in TALLY_KEYS}
        self.current = FIRST
        self.message = ""
        self.just = None                 # what the last Run did (not saved)

    # ---- the current order ---------------------------------------------------------------------------------------------
    @property
    def reaction(self):
        return reactions.BY_ID[self.current]

    def products_known(self, rid=None):
        r = reactions.BY_ID[rid or self.current]
        return (not r.is_round) or r.id in self.picked or r.id in self.shelf

    def coefs(self, rid=None):
        r = reactions.BY_ID[rid or self.current]
        return list(self.dials.get(r.id) or [1] * r.size)

    def _active(self, r):
        """(reactants, products, coefs) as far as they are shown now."""
        coefs = self.coefs(r.id)
        if self.products_known(r.id):
            return r.reactants, r.products, coefs
        return r.reactants, [], coefs[:len(r.reactants)]

    def elements_found(self, shelf=None):
        found = set()
        for rid in (self.shelf if shelf is None else shelf):
            found.update(reactions.BY_ID[rid].elements)
        return found

    # ---- save ----------------------------------------------------------------------------------------------------------
    def to_dict(self):
        """Only what differs from a fresh game is written (plus the layout version), so old and new saves stay compatible."""
        data = {"schema": SCHEMA}
        if self.current != FIRST:
            data["cur"] = self.current
        if self.shelf:
            data["shelf"] = {rid: self.shelf[rid] for rid in reactions.ORDER if rid in self.shelf}
        dials = {rid: list(self.dials[rid]) for rid in reactions.ORDER if rid in self.dials and any(c != 1 for c in self.dials[rid])}
        if dials:
            data["dials"] = dials
        picked = [rid for rid in reactions.ORDER if rid in self.picked and rid not in self.shelf]
        if picked:
            data["picked"] = picked
        tried = {rid: sorted(self.tried[rid]) for rid in reactions.ORDER if self.tried.get(rid) and rid not in self.picked and rid not in self.shelf}
        if tried:
            data["tried"] = tried
        first = [rid for rid in reactions.ORDER if rid in self.first]
        if first:
            data["first"] = first
        hinted = {rid: self.hinted[rid] for rid in reactions.ORDER if self.hinted.get(rid)}
        if hinted:
            data["hints"] = hinted
        tally = {k: v for k, v in self.tally.items() if v}
        if tally:
            data["tally"] = tally
        earned = achievements.earned(self.facts())
        if earned:
            data["achievements_earned"] = earned           # written for the hub's dashboard, never read back
        return data

    def facts(self):
        """What the achievements are computed from: the shelf, the elements lit, the suggestion record and the rounds chosen right first."""
        return achievements.facts_of(self.shelf, len(self.elements_found()), self.hinted, self.first)

    def load(self, data):
        """Take a saved dict, checking every field on its own; a bad field falls back to its default. A shelved order only
        counts if its chapter was open by the orders shelved before it, so a hand-edited save cannot skip ahead."""
        data = data if isinstance(data, dict) else {}
        schema = data.get("schema", SCHEMA)
        if isinstance(schema, bool) or not isinstance(schema, int) or not 1 <= schema <= SCHEMA:
            data = {}                                            # an unknown layout is never half-read
        self.shelf, self.dials, self.picked, self.tried, self.first, self.hinted, self.hint = {}, {}, set(), {}, set(), {}, None
        raw_shelf = data.get("shelf") if isinstance(data.get("shelf"), dict) else {}
        for r in reactions.ALL:                                  # chapter order, so each chapter is judged on those before it
            if r.id in raw_shelf and reactions.reaction_open(self.shelf, r.id):
                self.shelf[r.id] = _int(raw_shelf[r.id], 1, MAX_COUNT, 1)
        raw_dials = data.get("dials") if isinstance(data.get("dials"), dict) else {}
        for r in reactions.ALL:
            d = raw_dials.get(r.id)
            if (r.id in raw_dials and reactions.reaction_open(self.shelf, r.id) and isinstance(d, list) and len(d) == r.size
                    and all(_int(c, chem.MIN_COEF, chem.MAX_COEF, 0) for c in d)):
                self.dials[r.id] = list(d)
        raw_picked = data.get("picked") if isinstance(data.get("picked"), list) else []
        for r in reactions.ALL:
            if r.is_round and r.id in raw_picked and reactions.reaction_open(self.shelf, r.id):
                self.picked.add(r.id)
        for rid in self.shelf:
            if reactions.BY_ID[rid].is_round:
                self.picked.add(rid)                             # a shelved round has, of course, had its products chosen
        raw_tried = data.get("tried") if isinstance(data.get("tried"), dict) else {}
        for r in reactions.ALL:
            t = raw_tried.get(r.id)
            if r.is_round and r.id not in self.picked and isinstance(t, list) and reactions.reaction_open(self.shelf, r.id):
                wrong = sorted({i for i in t if _int(i, 0, len(r.choices) - 1, -1) >= 0 and i != r.right})
                if wrong:
                    self.tried[r.id] = wrong
        raw_first = data.get("first") if isinstance(data.get("first"), list) else []
        self.first = {r.id for r in reactions.ALL if r.is_round and r.id in raw_first and r.id in self.picked}
        raw_hints = data.get("hints") if isinstance(data.get("hints"), dict) else {}
        self.hinted = {r.id: raw_hints[r.id] for r in reactions.ALL
                       if r.id in raw_hints and reactions.reaction_open(self.shelf, r.id) and _int(raw_hints[r.id], 1, 3, 0)}
        tally = data.get("tally") if isinstance(data.get("tally"), dict) else {}
        self.tally = {key: _int(tally.get(key)) for key in TALLY_KEYS}
        cur = data.get("cur")
        self.current = cur if isinstance(cur, str) and cur in reactions.BY_ID and reactions.reaction_open(self.shelf, cur) else FIRST
        self.message = ""
        self.just = None

    # ---- the view ------------------------------------------------------------------------------------------------------
    def _orders(self):
        out = []
        for ci, chapter in enumerate(reactions.CHAPTERS):
            is_open = reactions.chapter_open(self.shelf, ci)
            items = []
            if is_open:
                for r in chapter["reactions"]:
                    item = {"id": r.id, "number": r.number, "title": r.title, "shelved": r.id in self.shelf, "current": r.id == self.current,
                            "runs": self.shelf.get(r.id, 0), "round": r.is_round, "locked": reactions.route_locked(self.shelf, r.id)}
                    if r.route:
                        item["route"] = reactions.ROUTES[r.route]["name"]
                        item["step"] = r.step
                        if item["locked"]:
                            item["needs"] = reactions.BY_ID[r.after].title
                    if r.id in self.shelf:
                        item["makes"] = " + ".join(reactions.name_of(f) for f in r.products)
                        item["formula"] = " + ".join(r.products)
                    items.append(item)
            need = max(0, reactions.chapter_need(ci - 1) - reactions.chapter_shelved(self.shelf, ci - 1)) if ci else 0
            out.append({"id": chapter["id"], "name": chapter["name"], "blurb": chapter["blurb"], "open": is_open,
                        "shelved": reactions.chapter_shelved(self.shelf, ci), "total": len(chapter["reactions"]), "need": need,
                        "after": reactions.CHAPTERS[ci - 1]["name"] if ci else "", "orders": items})
        return out

    def _table(self):
        found = self.elements_found()
        bench = set(reactions.BENCH_ELEMENTS)
        cells = []
        for z, sym, name in elements.ELEMENTS:
            row, col, kind = elements.position(z)
            cell = {"z": z, "row": row, "col": col, "f": kind == "f"}
            if sym in found:
                cell.update({"state": "found", "symbol": sym, "name": name})
            elif sym in bench:
                cell["state"] = "bench"                          # dark: only the number shows until the element is used
            else:
                cell.update({"state": "off", "symbol": sym, "name": name})
            cells.append(cell)
        cards = {}
        for sym in reactions.BENCH_ELEMENTS:
            if sym not in found:
                continue
            z, _s, name = elements.BY_SYMBOL[sym]
            facts = elements.BENCH[sym]
            used = [r for r in reactions.ALL if sym in r.elements]
            mine = [r.title for r in used if r.id in self.shelf]
            more = sum(1 for r in used if r.id not in self.shelf and reactions.reaction_open(self.shelf, r.id))
            cards[sym] = {"symbol": sym, "name": name, "number": z, "mass": facts["mass"], "kind": facts["kind"], "state": facts["state"],
                          "group": elements.group_of(z), "period": elements.period_of(z), "use": facts["use"], "reactions": mine, "more": more,
                          "snapshot": elements.SNAPSHOT_DATE, "source": elements.SNAPSHOT_SOURCE}
        return {"cells": cells, "markers": [dict(m) for m in elements.MARKERS], "cards": cards,
                "found": len(found), "bench": len(bench), "all": len(elements.ELEMENTS)}

    def view(self, message=None, ok=True):
        if message is not None:
            self.message = message
        r = self.reaction
        shelved = r.id in self.shelf
        known = self.products_known()
        reactants, products, coefs = self._active(r)
        rows = chem.ledger(reactants, products, coefs) if products else []
        balanced = bool(products) and chem.is_balanced(rows)
        species = []
        route = self._route_view(r)
        carried = route["carried"] if route else ""
        for i, f in enumerate(reactants):
            sp = dict(_species(f), role="reactant", index=i, coef=coefs[i])
            if route and r.step == 2 and f == carried:
                sp["carried"] = True                       # made by the step-one order and carried over
            species.append(sp)
        for i, f in enumerate(products):
            sp = dict(_species(f), role="product", index=len(reactants) + i, coef=coefs[len(reactants) + i])
            if route and r.step == 1 and f == carried:
                sp["carried"] = True                       # goes on into the step-two order
            species.append(sp)
        ledger_rows = []
        for row in rows:
            name = elements.name_of(row["symbol"])
            d = row["diff"]
            words = "equal" if d == 0 else "%d too many on the right" % d if d > 0 else "%d too few on the right" % -d
            ledger_rows.append(dict(row, name=name, number=elements.number_of(row["symbol"]), ok=d == 0,
                                    text="%s: %d on the left, %d on the right, %s." % (name.capitalize(), row["left"], row["right"], words)))
        choices = None
        if r.is_round and not known:
            tried = self.tried.get(r.id, [])
            choices = []
            for i, cand in enumerate(r.choices):
                item = {"index": i, "species": [_species(f) for f in cand], "tried": i in tried}
                if i in tried:
                    item["reason"] = chem.why_not(r.reactants, cand)
                choices.append(item)
        reaction = {
            "id": r.id, "title": r.title, "number": r.number, "of": len(reactions.ALL), "chapter": reactions.CHAPTERS[r.chapter]["name"],
            "chapter_index": r.chapter, "status": "shelved" if shelved else "open", "round": r.is_round, "picked": known,
            "species": species, "n_reactants": len(reactants), "choices": choices, "ledger": ledger_rows, "balanced": balanced,
            "lowest": chem.lowest_terms(coefs) if balanced else True, "can_run": balanced, "runs": self.shelf.get(r.id, 0),
            "fennel": r.fennel, "equation": equation_words(reactants, products, coefs) if products else "",
            "left_text": " + ".join(reactants), "max": chem.MAX_COEF, "min": chem.MIN_COEF, "route": route,
        }
        if shelved:
            reaction["blurb"] = r.blurb
        view = {
            "ok": ok, "message": self.message, "reaction": reaction, "just": self.just, "orders": self._orders(), "table": self._table(),
            "tally": dict(self.tally),
            "totals": {"orders": len(reactions.ALL), "shelved": len(self.shelf), "elements": len(self.elements_found()),
                       "bench": len(reactions.BENCH_ELEMENTS), "chapters": len(reactions.CHAPTERS),
                       "chapters_done": reactions.chapters_done(self.shelf), "turns": self.tally["turns"], "runs": self.tally["runs"],
                       "hints": self.tally["hints"]},
            "hint": self._hint_view(), "hint_ui": self._hint_ui(), "difficulty": difficulty,
            "goals": goals.queue(self.shelf, len(self.elements_found()), self.tally["turns"]),
            "achievements": achievements.view(self.facts()),
            "info": info.view(),
        }
        return view

    def _route_view(self, r):
        """For an order that belongs to a two-step route: which route, which step, and what is carried between the steps."""
        if not r.route:
            return None
        route = reactions.ROUTES[r.route]
        first = route["first"]
        carried = first.carries
        name = reactions.name_of(carried)
        if r.step == 1:
            note = "Step 1 of 2 in the %s. What comes out here, %s (%s), is carried into the next step: %s." % (
                route["name"], name, carried, route["second"].title)
        else:
            note = "Step 2 of 2 in the %s. %s (%s) is carried over from %s." % (route["name"], name.capitalize(), carried, first.title)
        return {"id": r.route, "name": route["name"], "step": r.step, "of": 2, "carried": carried, "carried_name": name, "note": note}

    # ---- actions -------------------------------------------------------------------------------------------------------
    def _enter(self, rid):
        self.current = rid
        self.just = None
        self.hint = None

    def pick(self, rid):
        if not isinstance(rid, str) or rid not in reactions.BY_ID:
            return self.view("There is no such order.", ok=False)
        if reactions.route_locked(self.shelf, rid):
            return self.view("Shelve %s first: this step uses what it makes." % reactions.BY_ID[reactions.BY_ID[rid].after].title, ok=False)
        if not reactions.reaction_open(self.shelf, rid):
            ci = reactions.BY_ID[rid].chapter
            return self.view("That chapter opens when %d orders in %s are on the shelf." % (reactions.chapter_need(ci - 1), reactions.CHAPTERS[ci - 1]["name"]), ok=False)
        if rid != self.current:
            self._enter(rid)
        return self.view("")

    def next(self):
        order = reactions.ORDER
        start = order.index(self.current)
        for step in range(1, len(order) + 1):
            rid = order[(start + step) % len(order)]
            if rid not in self.shelf and reactions.reaction_open(self.shelf, rid):
                self._enter(rid)
                return self.view("")
        return self.view("Every open order is on the shelf." if len(self.shelf) < len(order) else "Every order is on the shelf.", ok=False)

    def dial(self, index, value=None, delta=None):
        r = self.reaction
        if not self.products_known():
            return self.view("Choose what comes out first; then the dials open.", ok=False)
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < r.size:
            return self.view("There is no such dial.", ok=False)
        coefs = self.coefs()
        if value is None and delta is not None:
            if isinstance(delta, bool) or not isinstance(delta, int):
                return self.view("That is not a step the dial takes.", ok=False)
            value = coefs[index] + delta
        if isinstance(value, bool) or not isinstance(value, int):
            return self.view("That is not a setting the dial takes.", ok=False)
        if not chem.MIN_COEF <= value <= chem.MAX_COEF:
            return self.view("The dials turn from %d to %d." % (chem.MIN_COEF, chem.MAX_COEF), ok=False)
        if value == coefs[index]:
            return self.view("")
        coefs[index] = value
        self.dials[r.id] = coefs
        self.tally["turns"] += 1
        self.just = None
        self.hint = None
        return self.view("")

    def reset_dials(self):
        self.dials.pop(self.current, None)
        self.just = None
        self.hint = None
        return self.view("")

    def choose(self, option):
        r = self.reaction
        if not r.is_round:
            return self.view("This order has no choice to make.", ok=False)
        if self.products_known():
            return self.view("The products are already chosen.", ok=False)
        if isinstance(option, bool) or not isinstance(option, int) or not 0 <= option < len(r.choices):
            return self.view("There is no such choice.", ok=False)
        self.hint = None
        if option == r.right:
            first = not self.tried.get(r.id)
            self.picked.add(r.id)
            if first:
                self.first.add(r.id)
            self.tried.pop(r.id, None)
            return self.view("That one can be balanced. The dials are open.")
        tried = self.tried.setdefault(r.id, [])
        if option not in tried:
            tried.append(option)
            self.tally["tries"] += 1
        return self.view("Not that one. " + chem.why_not(r.reactants, r.choices[option]), ok=False)

    # ---- the hint ladder -------------------------------------------------------------------------------------------------
    def _hint_now(self):
        h = self.hint
        return h if h and h["rid"] == self.current else None

    def _hint_view(self):
        """What the ladder has shown so far on this order: only the rungs the player pressed for."""
        h = self._hint_now()
        if not h:
            return None
        return {"rung": h["rung"], "stage": h["stage"], "nudge": h["nudge"], "hint": h["hint"] if h["rung"] >= 2 else "",
                "answer": h["answer"] if h["rung"] >= 3 else "", "done": h["rung"] >= 3, "dial": h["target"] if h["rung"] >= 2 and h["stage"] == hints.STAGE_DIALS else None}

    def _hint_ui(self):
        """What the suggestion button should offer next: which rung, its words, whether it needs a confirm, whether the level stops it."""
        r = self.reaction
        known = self.products_known()
        stage = hints.stage(known)
        shelved = r.id in self.shelf
        balanced = False
        if known and not shelved:
            reactants, products, coefs = self._active(r)
            balanced = chem.is_balanced(chem.ledger(reactants, products, coefs))
        h = self._hint_now()
        rung = h["rung"] if h else 0
        cap = hints.rung_cap(difficulty)
        nxt = 0 if (shelved or balanced or rung >= cap) else rung + 1
        return {"available": not shelved, "next": nxt, "label": hints.button_label(rung, stage) if nxt else "", "stage": stage, "balanced": balanced,
                "limit": difficulty == "hard" and rung >= cap and not shelved and not balanced, "confirm": nxt == 3 and difficulty != "easy",
                "opens_two": nxt == 1 and difficulty == "easy", "here": self.hinted.get(r.id, 0)}

    def _note_hint(self, rung):
        """Count one press of the ladder and keep the order's highest rung (an order not yet shelved)."""
        self.tally["hints"] += 1
        if self.current not in self.shelf:
            self.hinted[self.current] = max(self.hinted.get(self.current, 0), rung)

    def ask_hint(self, confirm=False):
        r = self.reaction
        if r.id in self.shelf:
            return self.view("This order is on the shelf already. Suggestions are for orders that are not.", ok=False)
        known = self.products_known()
        stage = hints.stage(known)
        h = self._hint_now()
        if h is None:
            if known:
                texts = hints.dial_texts(r, self.coefs())
                if texts is None:
                    return self.view("Every element reads equal already. Press Run.", ok=False)
            else:
                texts = hints.choose_texts(r, self.tried.get(r.id, []))
            nudge, hint, answer, target = texts
            h = {"rid": r.id, "stage": stage, "rung": hints.first_rung(difficulty), "nudge": nudge, "hint": hint, "answer": answer, "target": target}
            self.hint = h
            self._note_hint(h["rung"])
            return self.view(nudge if h["rung"] == 1 else nudge + " " + hint)
        if h["rung"] >= hints.rung_cap(difficulty):
            return self.view("Hard has no answer step: the nudge and the hint are all the help there is." if difficulty == "hard"
                             else "That was the last step.", ok=False)
        if h["rung"] == 1:
            h["rung"] = 2
            self._note_hint(2)
            return self.view(h["hint"])
        if difficulty != "easy" and not confirm:
            return self.view("The answer takes the thinking out of it. Press again to confirm.", ok=False)
        self._note_hint(3)
        h["rung"] = 3
        if h["stage"] == hints.STAGE_CHOOSE:                  # the right list is chosen for you (it does not count as right first time)
            self.picked.add(r.id)
            self.tried.pop(r.id, None)
            self.hint = None
            return self.view("List %d is chosen for you. The dials are open." % (r.right + 1))
        self.dials[r.id] = list(r.answer)
        if all(c == 1 for c in r.answer):
            self.dials.pop(r.id, None)
        self.just = None
        return self.view("The dials are set to the answer. Press Run.")

    def run(self):
        r = self.reaction
        if not self.products_known():
            return self.view("Choose what comes out first.", ok=False)
        reactants, products, coefs = self._active(r)
        if not chem.is_balanced(chem.ledger(reactants, products, coefs)):
            return self.view("The ledger does not read equal yet, so there is nothing to run.", ok=False)
        before = self.elements_found()
        first = r.id not in self.shelf
        self.hint = None
        self.shelf[r.id] = self.shelf.get(r.id, 0) + 1
        self.tally["runs"] += 1
        new = [s for s in r.elements if s not in before]
        self.just = {"id": r.id, "first": first, "elements": new}
        msg = "%s is on the shelf." % r.title if first else "%s runs again." % r.title
        if new:
            msg += " New on the table: %s." % ", ".join(elements.BY_SYMBOL[s][2] for s in new)
        return self.view(msg)


game = Game()


def set_difficulty(level):
    """Easy / Normal / Hard only change how the hint ladder opens; the orders, the proofs, the shelf and every record stay the same."""
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
        return json.dumps(g.pick(request.get("reaction")))
    if action == "next":
        return json.dumps(g.next())
    if action == "dial":
        return json.dumps(g.dial(request.get("index"), request.get("value"), request.get("delta")))
    if action == "reset_dials":
        return json.dumps(g.reset_dials())
    if action == "choose":
        return json.dumps(g.choose(request.get("option")))
    if action == "run":
        return json.dumps(g.run())
    if action == "hint":
        return json.dumps(g.ask_hint(request.get("confirm") is True))
    if action == "difficulty":
        return json.dumps(set_difficulty(request.get("level")))
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
        refresh = getattr(js.window, "reactionBenchRefresh", None)
        if refresh is not None:
            refresh()
    except Exception:
        pass
