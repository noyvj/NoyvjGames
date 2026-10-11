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
  reset                   start over (everything)

The ledger's difference is right minus left, so +2 means two too many on the right and -1 means one too few.
"""

import json

import chem
import elements
import info
import reactions

MAX_COUNT = 10 ** 9
SCHEMA = 1                          # the save layout version; a save from a newer layout is not read
TALLY_KEYS = ("turns", "runs", "tries")
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
        tally = {k: v for k, v in self.tally.items() if v}
        if tally:
            data["tally"] = tally
        return data

    def load(self, data):
        """Take a saved dict, checking every field on its own; a bad field falls back to its default. A shelved order only
        counts if its chapter was open by the orders shelved before it, so a hand-edited save cannot skip ahead."""
        data = data if isinstance(data, dict) else {}
        schema = data.get("schema", SCHEMA)
        if isinstance(schema, bool) or not isinstance(schema, int) or not 1 <= schema <= SCHEMA:
            data = {}                                            # an unknown layout is never half-read
        self.shelf, self.dials, self.picked, self.tried, self.first = {}, {}, set(), {}, set()
        raw_shelf = data.get("shelf") if isinstance(data.get("shelf"), dict) else {}
        for r in reactions.ALL:                                  # chapter order, so each chapter is judged on those before it
            if r.id in raw_shelf and reactions.chapter_open(self.shelf, r.chapter):
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
                            "runs": self.shelf.get(r.id, 0), "round": r.is_round}
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
        for i, f in enumerate(reactants):
            species.append(dict(_species(f), role="reactant", index=i, coef=coefs[i]))
        for i, f in enumerate(products):
            species.append(dict(_species(f), role="product", index=len(reactants) + i, coef=coefs[len(reactants) + i]))
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
            "left_text": " + ".join(reactants), "max": chem.MAX_COEF, "min": chem.MIN_COEF,
        }
        if shelved:
            reaction["blurb"] = r.blurb
        view = {
            "ok": ok, "message": self.message, "reaction": reaction, "just": self.just, "orders": self._orders(), "table": self._table(),
            "tally": dict(self.tally),
            "totals": {"orders": len(reactions.ALL), "shelved": len(self.shelf), "elements": len(self.elements_found()),
                       "bench": len(reactions.BENCH_ELEMENTS), "chapters": len(reactions.CHAPTERS),
                       "chapters_done": reactions.chapters_done(self.shelf), "turns": self.tally["turns"], "runs": self.tally["runs"]},
            "info": info.view(),
        }
        return view

    # ---- actions -------------------------------------------------------------------------------------------------------
    def _enter(self, rid):
        self.current = rid
        self.just = None

    def pick(self, rid):
        if not isinstance(rid, str) or rid not in reactions.BY_ID:
            return self.view("There is no such order.", ok=False)
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
        return self.view("")

    def reset_dials(self):
        self.dials.pop(self.current, None)
        self.just = None
        return self.view("")

    def choose(self, option):
        r = self.reaction
        if not r.is_round:
            return self.view("This order has no choice to make.", ok=False)
        if self.products_known():
            return self.view("The products are already chosen.", ok=False)
        if isinstance(option, bool) or not isinstance(option, int) or not 0 <= option < len(r.choices):
            return self.view("There is no such choice.", ok=False)
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

    def run(self):
        r = self.reaction
        if not self.products_known():
            return self.view("Choose what comes out first.", ok=False)
        reactants, products, coefs = self._active(r)
        if not chem.is_balanced(chem.ledger(reactants, products, coefs)):
            return self.view("The ledger does not read equal yet, so there is nothing to run.", ok=False)
        before = self.elements_found()
        first = r.id not in self.shelf
        self.shelf[r.id] = self.shelf.get(r.id, 0) + 1
        self.tally["runs"] += 1
        new = [s for s in r.elements if s not in before]
        self.just = {"id": r.id, "first": first, "elements": new}
        msg = "%s is on the shelf." % r.title if first else "%s runs again." % r.title
        if new:
            msg += " New on the table: %s." % ", ".join(elements.BY_SYMBOL[s][2] for s in new)
        return self.view(msg)


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
