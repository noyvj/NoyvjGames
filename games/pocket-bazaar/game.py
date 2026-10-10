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
  buy_decor {id}              buy a decoration (cosmetic) and put it out
  put_decor {id}              put an owned decoration out in its slot
  reset                       start over (everything but the Daily Market results, which belong to dates)
  start_market {date}         open the Daily Market for a date (from the closed stall only; see market.py)

Every request may carry "today" ("YYYY-MM-DD", UTC): the view passes the date in, the engine never reads a clock.
"""

import json
import re

import achievements
import decorations
import festival
import goods
import info
import market
import regulars
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
        self.decor_owned = []
        self.decor_put = {}
        self.visits = {}            # regular id -> times served
        self.flags = []             # achievement facts that cannot be recomputed: perfect, showpiece, bargain, quiet, twin5
        self.festivals_seen = []
        self.shelf = None           # the good kept on the display shelf between days
        self.day = None
        self.last = None            # the summary of the day that just ended, until the next one opens
        self.market = None          # the date of the Daily Market the open day belongs to (None: a campaign day)
        self.market_days = {}       # {"YYYY-MM-DD": best result}; belongs to dates, so it survives a reset
        self.market_result = None   # the market that just ended, for the closed card (never saved)

    def families(self):
        if self.market:
            return tuple(market.spec(self.market)["families"])
        return tuple(renown.families(self.renown))

    def facts(self):
        """What the achievements are computed from."""
        facts = {"days_played": self.days_played, "orders": self.tally["orders"], "best_chain": self.best_chain,
                 "best_combo": self.best["combo"], "regular_level": regulars.max_level(self.visits),
                 "upgrades": len(self.upgrades), "decor": len(self.decor_owned), "festivals": len(self.festivals_seen)}
        for flag in ("perfect", "showpiece", "bargain", "quiet", "twin5"):
            facts["flag_" + flag] = 1 if flag in self.flags else 0
        return facts

    def set_flag(self, flag):
        if flag not in self.flags:
            self.flags.append(flag)

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
        if self.decor_owned:
            data["decor"] = list(self.decor_owned)
        if self.decor_put:
            data["put"] = dict(self.decor_put)
        visits = {k: v for k, v in self.visits.items() if v}
        if visits:
            data["reg"] = visits
        if self.flags:
            data["flags"] = list(self.flags)
        if self.festivals_seen:
            data["seen"] = list(self.festivals_seen)
        earned = achievements.earned(self.facts())
        if earned:
            data["achievements_earned"] = earned       # written for the hub's dashboard, never read back
        if self.shelf is not None:
            data["shelf"] = {"f": self.shelf[0], "t": self.shelf[1]}
        if self.day is not None and not self.market:
            data["day"] = self.day.to_dict()
        if self.market and self.day is not None:
            data["market_day"] = {"date": self.market, "day": self.day.to_dict()}
        if self.market_days:
            data["market_days"] = {d: dict(r) for d, r in self.market_days.items()}
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
        decor = data.get("decor")
        self.decor_owned = [d for d in decorations.ids() if isinstance(decor, list) and d in decor]
        put = data.get("put") if isinstance(data.get("put"), dict) else {}
        self.decor_put = {slot: put[slot] for slot in decorations.SLOT_IDS
                          if put.get(slot) in self.decor_owned and decorations.BY_ID[put[slot]][1] == slot}
        reg = data.get("reg") if isinstance(data.get("reg"), dict) else {}
        self.visits = {r: _int(reg.get(r), high=10 ** 4) for r in regulars.IDS if _int(reg.get(r), high=10 ** 4)}
        flags = data.get("flags")
        self.flags = [f for f in ("perfect", "showpiece", "bargain", "quiet", "twin5") if isinstance(flags, list) and f in flags]
        seen = data.get("seen")
        self.festivals_seen = [f for f in festival.ORDER if isinstance(seen, list) and f in seen]
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
        self.market, self.market_result = None, None
        self.market_days = market.clean_days(data.get("market_days"))
        raw_market = data.get("market_day")
        if self.day is None and isinstance(raw_market, dict) and market.valid_date(raw_market.get("date")) \
                and raw_market["date"] >= market.EPOCH:
            date = raw_market["date"]
            try:
                day = Day.from_dict(raw_market.get("day"), market.spec(date)["families"], market.rules_for(date))
                if day.number == market.day_number(date):
                    self.day, self.market = day, date
            except (ValueError, TypeError, KeyError, AttributeError):
                self.day, self.market = None, None
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
        self._place_regulars(queue, number)
        board = Board(6 if "counter" in self.upgrades else 5, rules.get("board_height", 6), "shelf" in self.upgrades)
        if self.shelf is not None and board.has_shelf:
            board.cells[board.shelf_index] = self.shelf
        self.day = Day(number, board, queue, rng, rules)
        self.last = None
        return self.day

    def _place_regulars(self, queue, number):
        """Three named regulars step up each day in a fixed rotation, spread through the line. They are ordinary Regular
        customers (same tiers, same patience) with a name and a favourite family."""
        eligible = [c for c in queue if c.archetype == "regular" and not c.group and not c.reg]
        picks = regulars.rotation(number)
        for k, rid in enumerate(picks):
            if not eligible:
                break
            customer = eligible.pop(min(len(eligible) - 1, (len(eligible) * (2 * k + 1)) // (2 * len(picks))))
            _id, name, family, _role, _lines = regulars.BY_ID[rid]
            customer.name, customer.reg = name, rid
            if family in self.families():
                customer.items = [[family, t, 0] for _f, t, _d in customer.items]

    def open_market(self, date):
        """The Daily Market for a date: a fixed, fair stall (no upgrades, shelf or regulars) that changes nothing else."""
        self.day = market.new_day(date)
        self.market = date
        self.market_result = None
        return self.day

    def close_market(self):
        """The market is over: only the date's best result is kept. No coins, renown, tally, flags or bests move."""
        day = self.day
        summary = day.summary()
        before = self.market_days.get(self.market)
        record = market.merge_record(before, summary)
        self.market_days[self.market] = record
        self.market_result = {"date": self.market, "stars": summary["stars"], "served": summary["served"],
                              "left": summary["left"], "total": summary["total"], "coins": summary["coins"],
                              "beats": summary["beats"], "best_chain": summary["best_chain"],
                              "best": record, "improved": record != before}
        self.market = None
        self.day = None

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
        if day.festival and day.festival not in self.festivals_seen:
            self.festivals_seen = [f for f in festival.ORDER if f in self.festivals_seen or f == day.festival]
        if day.left == 0 and day.served:
            self.set_flag("perfect")
            if day.festival == "bargain":
                self.set_flag("bargain")
        if day.festival == "slow" and day.best_mult == 1:
            self.set_flag("quiet")
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


_today = None     # the view's UTC date, runtime only (never saved, never read from a clock)


def _market_view():
    """What the closed stall shows for the Daily Market. None until the view has passed the date in."""
    if _today is None:
        return None
    open_today = market.playable(_today, _today) and _today >= market.EPOCH
    spec = market.spec(_today) if open_today else None
    days_done = {d: dict(r) for d, r in stall.market_days.items()}
    entry = {"today": _today, "epoch": market.EPOCH, "open": open_today, "number": spec["number"] if spec else 0,
             "festival": festival.info(spec["festival"]) if spec else None,
             "customers": spec["customers"] if spec else 0, "record": days_done.get(_today), "days": days_done,
             "tally": market.tally(stall.market_days, _today), "active": stall.market, "result": stall.market_result}
    if stall.market_result:
        entry["entry"] = market.leaderboard_entry(stall.market_result["date"], stall.market_result["best"])   # HOOK only
    return entry


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
        "about": info.view(),
        "achievements": achievements.view(stall.facts()), "goals": achievements.goals(stall.facts()),
        "decor": decorations.view(stall.decor_owned, stall.decor_put, stall.coins),
        "regulars": regulars.view(stall.visits), "regulars_met": len(stall.visits),
        "renown": stall.renown, "next_unlock": renown.next_unlock(stall.renown), "unlock_names": dict(renown.UNLOCK_NAMES), "best": dict(stall.best),
        "unlocked_families": list(stall.families()), "upgrades": shop.view(stall.upgrades, stall.coins),
        "festival": festival.info(day.festival) if day else _festival_view(stall.next_day),
        "campaign": _campaign_view(stall.next_day if stall.market or not day else day.number),
        "market": _market_view(),
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
    upcoming = day.queue[WINDOW] if "preview" in stall.upgrades and not stall.market and len(day.queue) > WINDOW else None
    view["upcoming"] = _customer_view(WINDOW, upcoming) if upcoming else None
    return view


def _apply(outcome):
    """Fold an action's outcome into the stall (coins, tally) and write the reply message."""
    day = stall.day
    in_market = stall.market is not None
    if not in_market:
        stall.coins = min(MAX_COINS, stall.coins + outcome.get("coins", 0) + outcome.get("sold", 0))
    event = outcome.get("event")
    if outcome["ok"] and event and not in_market:
        kind = event["kind"]
        if kind == "crate":
            stall.tally["crates"] += 1
        elif kind == "merge":
            result = outcome["merge"]
            stall.tally["merges"] += result.links
            stall.tally["triples"] += 1 if result.triple else 0
            stall.best_chain = max(stall.best_chain, result.links)
            if result.good[1] >= goods.MAX_TIER:
                stall.set_flag("showpiece")
            if day.twins >= 5:
                stall.set_flag("twin5")
        elif kind == "sell":
            stall.tally["sold"] += 1
        elif kind == "broom":
            stall.tally["swept"] += 1
        elif kind == "deliver" and outcome.get("served_now"):
            stall.tally["orders"] += 1
            if outcome.get("wild") is not None:
                stall.tally["wilds"] += 1
    flavor = list(outcome.get("flavor", []))
    reg = outcome.get("served_reg")
    if reg and reg in regulars.BY_ID and not in_market:
        before = stall.visits.get(reg, 0)
        stall.visits[reg] = min(10 ** 4, before + 1)
        new_level = regulars.level(stall.visits[reg])
        if new_level > regulars.level(before):
            outcome["notes"].append(f"{regulars.BY_ID[reg][1]} is now bond level {new_level} (see Regulars).")
            flavor.append(f"{regulars.BY_ID[reg][1]}: {regulars.line_for(reg, new_level)}")
    message = " ".join([outcome["message"]] + outcome["notes"]).strip()
    served_now = outcome.get("served_now")
    left_now = sum(1 for n in outcome["notes"] if "could not wait" in n)
    if served_now or left_now:
        event = dict(event or {}, served=bool(served_now), left=left_now)
    if in_market and re.search(r" for \d+ coins?\.", message):
        message = re.sub(r" for \d+ coins?\.", " off the counter.", message)          # a market pays nothing for sales
    if day.is_over():
        if in_market:
            stall.close_market()
            message += " The Daily Market is done."
        else:
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
    global _today
    if "today" in request:
        _today = request["today"] if market.valid_date(request["today"]) else None
    if action == "open":
        return json.dumps(_view())
    if action == "reset":
        kept = stall.market_days
        stall.__init__()
        stall.market_days = kept
        return json.dumps(_view("Starting over."))
    if action == "start_market":
        if _today is None:
            return json.dumps(_view("The date is not known yet.", ok=False))
        date = request.get("date")
        if not market.valid_date(date) or date < market.EPOCH:
            return json.dumps(_view("There was no market on that date.", ok=False))
        if not market.playable(date, _today):
            return json.dumps(_view("That market is not open yet.", ok=False))
        if stall.day is not None and stall.market != date:
            return json.dumps(_view("Finish the open day first.", ok=False))
        if stall.day is None:
            stall.open_market(date)
        fest = festival.info(stall.day.festival)
        return json.dumps(_view(f"Daily Market {stall.day.number}: {fest['name']}. {fest['blurb']}"))
    if action == "start_day":
        if stall.market:
            return json.dumps(_view("A Daily Market is open. Finish it first.", ok=False))
        stall.market_result = None
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
    if action in ("buy_decor", "put_decor"):
        decor_id = request.get("id")
        if not isinstance(decor_id, str):
            return json.dumps(_view("There is no such decoration.", ok=False))
        if action == "buy_decor":
            ok, reason = decorations.can_buy(stall.decor_owned, decor_id, stall.coins)
            if not ok:
                return json.dumps(_view(reason, ok=False))
            stall.coins -= decorations.BY_ID[decor_id][3]
            stall.decor_owned = [d for d in decorations.ids() if d in stall.decor_owned or d == decor_id]
        elif decor_id not in stall.decor_owned:
            return json.dumps(_view("You do not own that yet.", ok=False))
        stall.decor_put[decorations.BY_ID[decor_id][1]] = decor_id
        return json.dumps(_view(f"{decorations.BY_ID[decor_id][2]} is out on the stall.", event={"kind": "decor", "id": decor_id}))
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
