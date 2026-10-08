"""Pocket Bazaar -- the engine's single entry point (the Lexis / Signal pattern).

The view (app.js) never reads engine objects: it sends one JSON string to `handle` and draws the JSON that
comes back. `get_state()` / `load_state()` are the shared save widget's contract
(planning/SAVE-BUTTON-INTEGRATION.md). Nothing here reads a clock: the game is turn-based, customers' patience is
counted in beats (see day.py), and the save holds no timestamps.

Actions (every request is {"action": ..., ...}; every reply is the whole view):
  open                        the current view
  start_day                   open the stall for the next market day
  crate {family}              put a tier-1 good of that family on the first free cell (a beat)
  drop {from, to}             merge two goods (a beat), or move / swap (free); cells are numbered row by row
  deliver {from, to}          hand the good at cell `from` to customer number `to` (0-2) (a beat when accepted)
  sell {at}                   sell a good off the counter for its sell price (free)
  broom {at}                  sweep a good off the counter (a beat)
  buy {id}                    buy a stall upgrade with coins (between days only)
  reset                       start over (everything)
"""

import json

import festival
import goods
import renown
import shop
from board import Board
from day import Day
from days import CAMPAIGN_DAYS, WINDOW, spec
from goods import FAMILY_INFO, good_label
from orders import ARCHETYPES, make_queue
from rng import Rng, mix

TALLY_KEYS = ("crates", "merges", "sold", "swept", "triples", "orders", "wilds")
BEST_KEYS = ("combo", "day_coins")
SUMMARY_KEYS = ("number", "served", "left", "total", "coins", "beats", "best_chain", "stars", "streak", "chain_coins",
                "wilds", "twins", "best_mult", "renown_gain")
NEW_BEST_IDS = ("combo", "day_coins")
MAX_COINS = 10 ** 9


def _int(value, low=0, high=MAX_COINS, default=0):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        return default
    return value


class Stall:
    """Everything the player has: the stall's lifetime numbers and, while the stall is open, the current day."""

    def __init__(self):
        self.coins = 0
        self.tally = {key: 0 for key in TALLY_KEYS}
        self.best_chain = 0
        self.days_played = 0
        self.next_day = 1
        self.renown = 0
        self.upgrades = []
        self.best = {key: 0 for key in BEST_KEYS}
        self.shelf = None           # the good kept on the display shelf between days
        self.day = None
        self.last = None            # the summary of the day that just ended, until the next one opens

    def families(self):
        return tuple(renown.families(self.renown))

    def rules_for(self, number):
        """What the day's festival and the owned upgrades change, as the Day's rules dict."""
        fest = festival.for_day(number)
        rules = festival.day_rules(fest)
        rules.update(shop.rules_from(self.upgrades))
        rules["festival"] = fest
        return rules

    def to_dict(self):
        """Only what differs from a fresh game is written, so old and new saves stay compatible."""
        data = {}
        if self.coins:
            data["coins"] = self.coins
        tally = {k: v for k, v in self.tally.items() if v}
        if tally:
            data["tally"] = tally
        for key in ("best_chain", "days_played", "renown"):
            if getattr(self, key):
                data[key] = getattr(self, key)
        if self.next_day != 1:
            data["next_day"] = self.next_day
        if self.upgrades:
            data["upgrades"] = list(self.upgrades)
        best = {k: v for k, v in self.best.items() if v}
        if best:
            data["best"] = best
        if self.shelf is not None:
            data["shelf"] = {"f": self.shelf[0], "t": self.shelf[1]}
        if self.day is not None:
            data["day"] = self.day.to_dict()
        if self.last:
            data["last"] = dict(self.last)
        return data

    def load(self, data):
        """Take a saved dict, checking every field on its own; a bad field falls back to its default."""
        data = data if isinstance(data, dict) else {}
        self.coins = _int(data.get("coins"))
        tally = data.get("tally") if isinstance(data.get("tally"), dict) else {}
        self.tally = {key: _int(tally.get(key)) for key in TALLY_KEYS}
        self.best_chain = _int(data.get("best_chain"), high=goods.MAX_TIER)
        self.days_played = _int(data.get("days_played"), high=10 ** 5)
        self.renown = _int(data.get("renown"))
        self.next_day = _int(data.get("next_day"), low=1, high=10 ** 5 + 1, default=1)
        best = data.get("best") if isinstance(data.get("best"), dict) else {}
        self.best = {key: _int(best.get(key), high=10 ** 7) for key in BEST_KEYS}
        owned = data.get("upgrades")
        self.upgrades = [u for u in shop.ids() if isinstance(owned, list) and u in owned]
        self.shelf = None
        raw = data.get("shelf")
        if isinstance(raw, dict) and "shelf" in self.upgrades:
            good = (raw.get("f"), raw.get("t"))
            if goods.valid_good(good) and not goods.is_wild(good):
                self.shelf = good
        self.day = None
        if "day" in data:
            try:
                self.day = Day.from_dict(data["day"], self.families(), self.rules_for(_int(data["day"].get("number"), 1, 10 ** 5, 1)))
            except (ValueError, TypeError, KeyError, AttributeError):
                self.day = None
        self.last = None
        last = data.get("last")
        if isinstance(last, dict):
            clean = {k: _int(last.get(k), high=10 ** 7) for k in SUMMARY_KEYS}
            clean["festival"] = last.get("festival") if last.get("festival") in festival.FESTIVALS else None
            unlocks = last.get("unlocks") if isinstance(last.get("unlocks"), list) else []
            clean["unlocks"] = [u for u in renown.UNLOCK_NAMES if u in unlocks]
            bests = last.get("new_bests") if isinstance(last.get("new_bests"), list) else []
            clean["new_bests"] = [b for b in NEW_BEST_IDS if b in bests]
            if clean["number"] >= 1 and 1 <= clean["stars"] <= 3:
                self.last = clean

    # ---- the day ---------------------------------------------------------------------------------
    def open_day(self):
        number = self.next_day
        rules = self.rules_for(number)
        rng = Rng(mix(number, 0xBA2AA2))
        day_spec = festival.apply_spec(spec(number, extras=renown.archetypes(self.renown)), rules["festival"])
        queue = make_queue(rng, day_spec, list(self.families()))
        board = Board(6 if "counter" in self.upgrades else 5, rules.get("board_height", 6), "shelf" in self.upgrades)
        if self.shelf is not None and board.has_shelf:
            board.cells[board.shelf_index] = self.shelf
        self.day = Day(number, board, queue, rng, rules)
        self.last = None
        return self.day

    def close_day(self):
        """Called when the last customer has gone: bank the day and show its summary."""
        day = self.day
        if day.board.has_shelf:
            self.shelf = day.board.cells[day.board.shelf_index]
        self.last = day.summary()
        gain = renown.gain(day.served, self.last["stars"])
        unlocks = renown.newly_unlocked(self.renown, self.renown + gain)
        self.renown += gain
        self.last["renown_gain"] = gain
        self.last["unlocks"] = unlocks
        bests = []
        if day.best_streak > self.best["combo"]:
            bests.append("combo")
            self.best["combo"] = day.best_streak
        if day.coins > self.best["day_coins"]:
            bests.append("day_coins")
            self.best["day_coins"] = day.coins
        self.last["new_bests"] = bests
        self.days_played += 1
        self.next_day = day.number + 1
        self.day = None


stall = Stall()


def _cell_view(good):
    if good is None:
        return None
    if goods.is_wild(good):
        return {"code": goods.good_code(good), "family": "wild", "tier": 1, "name": "Wildcard", "letter": "*",
                "shape": "star", "label": "Wildcard", "next": None, "sell": 1}
    info = FAMILY_INFO[good[0]]
    return {"code": goods.good_code(good), "family": good[0], "tier": good[1], "name": goods.good_name(good),
            "letter": info["letter"], "shape": info["shape"], "label": good_label(good),
            "next": goods.next_tier_name(good), "sell": goods.sell_value(good)}


def _item_view(f, t, done, any_tier=False):
    info = FAMILY_INFO[f]
    if any_tier and not done:
        return {"family": f, "tier": 1, "tier_text": "+", "letter": info["letter"], "shape": info["shape"],
                "label": f"any {info['name'].lower()} good", "done": False}
    return {"family": f, "tier": t, "tier_text": str(t), "letter": info["letter"], "shape": info["shape"],
            "label": good_label((f, t)), "done": bool(done)}


def _customer_view(index, c):
    any_tier = c.info["mode"] == "any"
    return {"index": index, "name": c.name, "archetype": c.archetype, "kind": c.info["name"], "blurb": c.info["blurb"],
            "items": [_item_view(f, t, d, any_tier) for f, t, d in c.items], "patience": c.left, "max": c.max,
            "pay": c.pay(), "exact": c.info["mode"] == "exact", "group": c.group}


def _festival_view(number):
    return festival.info(festival.for_day(number))


def _campaign_view(number):
    return {"mode": "campaign" if number <= CAMPAIGN_DAYS else "free", "day": number, "of": CAMPAIGN_DAYS}


def _view(message="", ok=True, event=None):
    day = stall.day
    view = {
        "ok": ok, "message": message, "flavor": [], "event": event,
        "phase": "open" if day else "closed",
        "crates": [{"family": f, "name": FAMILY_INFO[f]["name"], "letter": FAMILY_INFO[f]["letter"],
                    "shape": FAMILY_INFO[f]["shape"]} for f in stall.families()],
        "coins": stall.coins, "tally": dict(stall.tally), "best_chain": stall.best_chain,
        "days_played": stall.days_played, "next_day": stall.next_day, "summary": stall.last,
        "archetypes": {k: v["name"] for k, v in ARCHETYPES.items()},
        "renown": stall.renown, "next_unlock": renown.next_unlock(stall.renown), "unlock_names": dict(renown.UNLOCK_NAMES), "best": dict(stall.best),
        "unlocked_families": list(stall.families()), "upgrades": shop.view(stall.upgrades, stall.coins),
        "festival": _festival_view(day.number if day else stall.next_day),
        "campaign": _campaign_view(day.number if day else stall.next_day),
        "summary_festival": _festival_view(stall.last["number"]) if stall.last else None,
    }
    if day is None:
        view["board"] = None
        view["customers"] = []
        view["partners"] = {}
        view["deliverable"] = {}
        view["day"] = None
        view["full"] = False
        view["upcoming"] = None
        return view
    board = day.board
    view["board"] = {"w": board.width, "h": board.height, "shelf": board.has_shelf,
                     "cells": [_cell_view(g) for g in board.cells]}
    view["partners"] = {str(i): board.partners(i) for i, _g in board.goods() if board.partners(i)}
    view["customers"] = [_customer_view(i, c) for i, c in enumerate(day.window())]
    view["deliverable"] = {str(k): v for k, v in day.deliverable().items()}
    view["full"] = board.first_empty() is None
    view["day"] = {"number": day.number, "total": day.total, "served": day.served, "left": day.left,
                   "waiting": day.waiting(), "coins": day.coins, "beat": day.beat, "window": WINDOW,
                   "streak": day.streak, "mult": day.multiplier(), "to_next": day.to_next(), "chain_coins": day.chain_coins}
    upcoming = day.queue[WINDOW] if "preview" in stall.upgrades and len(day.queue) > WINDOW else None
    view["upcoming"] = _customer_view(WINDOW, upcoming) if upcoming else None
    return view


def _apply(outcome):
    """Fold an action's outcome into the stall (coins, tally) and write the reply message."""
    day = stall.day
    stall.coins = min(MAX_COINS, stall.coins + outcome.get("coins", 0) + outcome.get("sold", 0))
    event = outcome.get("event")
    if outcome["ok"] and event:
        kind = event["kind"]
        if kind == "crate":
            stall.tally["crates"] += 1
        elif kind == "merge":
            result = outcome["merge"]
            stall.tally["merges"] += result.links
            stall.tally["triples"] += 1 if result.triple else 0
            stall.best_chain = max(stall.best_chain, result.links)
        elif kind == "sell":
            stall.tally["sold"] += 1
        elif kind == "broom":
            stall.tally["swept"] += 1
        elif kind == "deliver" and outcome.get("served_now"):
            stall.tally["orders"] += 1
            if outcome.get("wild") is not None:
                stall.tally["wilds"] += 1
    message = " ".join([outcome["message"]] + outcome["notes"]).strip()
    flavor = list(outcome.get("flavor", []))
    served_now = outcome.get("served_now")
    left_now = sum(1 for n in outcome["notes"] if "could not wait" in n)
    if served_now or left_now:
        event = dict(event or {}, served=bool(served_now), left=left_now)
    if day.is_over():
        stall.close_day()
        message += f" Day {stall.last['number']} is done."
    view = _view(message, outcome["ok"], event)
    view["flavor"] = flavor
    return view


def handle(request_json):
    try:
        request = json.loads(request_json)
        action = request.get("action")
    except (ValueError, AttributeError):
        return json.dumps({"error": "bad request"})
    if action == "open":
        return json.dumps(_view())
    if action == "reset":
        stall.__init__()
        return json.dumps(_view("Starting over."))
    if action == "start_day":
        if stall.day is None:
            stall.open_day()
        fest = festival.info(festival.for_day(stall.day.number))
        return json.dumps(_view(f"Day {stall.day.number}: {fest['name']}. {fest['blurb']}"))
    if action == "buy":
        if stall.day is not None:
            return json.dumps(_view("The shop is open between days.", ok=False))
        upgrade = request.get("id")
        ok, reason = shop.can_buy(stall.upgrades, upgrade, stall.coins) if isinstance(upgrade, str) else (False, "There is no such upgrade.")
        if not ok:
            return json.dumps(_view(reason, ok=False))
        stall.coins -= shop.BY_ID[upgrade]["cost"]
        stall.upgrades = [u for u in shop.ids() if u in stall.upgrades or u == upgrade]
        return json.dumps(_view(f"You bought {shop.BY_ID[upgrade]['name']}. {shop.BY_ID[upgrade]['blurb']}",
                                event={"kind": "buy", "id": upgrade}))
    if action not in ("crate", "drop", "deliver", "sell", "broom"):
        return json.dumps({"error": f"unknown action {action!r}"})
    day = stall.day
    if day is None:
        return json.dumps(_view("Open the stall first.", ok=False))
    if action == "crate":
        family = request.get("family")
        if family not in stall.families():
            return json.dumps(_view("That crate is not open yet.", ok=False))
        outcome = day.crate(family)
    elif action == "drop":
        outcome = day.drop(request.get("from"), request.get("to"))
    elif action == "deliver":
        outcome = day.deliver(request.get("from"), request.get("to"))
    elif action == "sell":
        outcome = day.sell(request.get("at"))
    else:
        outcome = day.broom(request.get("at"))
    return json.dumps(_apply(outcome))


def get_state():
    return stall.to_dict()


def load_state(data):
    stall.load(data)
    _refresh_view()


def _refresh_view():
    """Ask the page to redraw after a save is loaded (the save widget calls load_state directly and knows
    nothing about this game's view). Under plain CPython there is no page, so this is a no-op."""
    try:
        import js
        refresh = getattr(js.window, "pocketBazaarRefresh", None)
        if refresh is not None:
            refresh()
    except Exception:
        pass
