"""Pocket Bazaar -- one market day: the counter, the queue, and the beats that move them.

A BEAT is one of: a crate tap, a merge, a sweep with the broom, a successful hand-over. Every beat takes one point
of patience from each of the (up to three) customers standing at the stall. Moving, swapping and selling a good
are free, and a refused hand-over costs nothing. Nothing in here reads a clock.

Patience only runs for the customers at the stall; customers still waiting in line start with full patience when
they step up, so a long queue never drains anyone ahead of time.
"""

from board import Board
from days import WINDOW
from goods import FAMILY_INFO, VALUE, good_label
from orders import Customer
from rng import Rng

LEAVE_LINES = ("Maybe next time!", "No hard feelings.", "Another day, then.", "I will come back later.")
THANK_LINES = ("Lovely, thank you!", "Just what I wanted.", "You have a good stall.", "Perfect, thanks!")


def _line(lines, day_number, name):
    return lines[(day_number * 7 + sum(ord(c) for c in name)) % len(lines)]


class Day:
    def __init__(self, number, board, queue, rng, rules=None):
        self.number = number
        self.board = board
        self.queue = queue
        self.rng = rng
        self.total = len(queue)
        self.served = 0
        self.left = 0
        self.coins = 0
        self.beat = 0
        self.best_chain = 0
        self.rules = dict(rules or {})

    # ---- the stall ---------------------------------------------------------------------------------
    def window(self):
        return self.queue[:WINDOW]

    def waiting(self):
        return max(0, len(self.queue) - WINDOW)

    def is_over(self):
        return not self.queue

    def _outcome(self, ok=True, message="", event=None):
        return {"ok": ok, "message": message, "event": event, "coins": 0, "notes": [], "flavor": [], "beat": False}

    def _advance(self, outcome, spared=None):
        """One beat: everyone at the stall (except the customer just served) loses a point of patience."""
        self.beat += 1
        outcome["beat"] = True
        for customer in list(self.window()):
            if customer is spared:
                continue
            customer.left -= 1
            if customer.left <= 0:
                self._leave(customer, outcome)

    def _leave(self, customer, outcome):
        self.queue.remove(customer)
        self.left += 1
        paid = 0
        got = [(f, t) for f, t, done in customer.items if done]
        if got:
            paid = max(1, sum(VALUE[t] for _f, t in got) * customer.info["pay_pct"] // 100)
            self.coins += paid
            outcome["coins"] += paid
        text = f"{customer.name} could not wait and left."
        if paid:
            text += f" Paid {paid} for what they had."
        outcome["notes"].append(text)
        outcome["flavor"].append(f"{customer.name}: \"{_line(LEAVE_LINES, self.number, customer.name)}\"")

    def _serve(self, customer, outcome):
        self.queue.remove(customer)
        self.served += 1
        pay, tip = customer.pay(), customer.tip()
        self.coins += pay + tip
        outcome["coins"] += pay + tip
        text = f"{customer.name} is happy: +{pay + tip} coins"
        if tip:
            text += f" (tip {tip})"
        outcome["notes"].append(text + ".")
        outcome["flavor"].append(f"{customer.name}: \"{_line(THANK_LINES, self.number, customer.name)}\"")

    # ---- actions -----------------------------------------------------------------------------------
    def crate(self, family, tier=1):
        at = self.board.place((family, tier))
        if at is None:
            return self._outcome(False, "The counter is full. Merge, sell or sweep something to make room.")
        outcome = self._outcome(True, f"{good_label((family, tier))} from the {FAMILY_INFO[family]['name']} crate.",
                                {"kind": "crate", "at": at})
        self._advance(outcome)
        return outcome

    def drop(self, src, dst):
        result = self.board.drop(src, dst, self.rules)
        if not result.ok:
            return self._outcome(False, result.reason)
        if not result.links:
            return self._outcome(True, "Swapped them." if result.swapped else "Moved.",
                                 {"kind": "move", "src": result.src, "dst": result.dst})
        self.best_chain = max(self.best_chain, result.links)
        text = f"Merged into {good_label(result.good)}."
        if result.triple:
            text += " Three-way bonus: two tiers at once!"
        if result.links > 1:
            text += f" {result.links}-link chain!"
        outcome = self._outcome(True, text, {"kind": "merge", **result.to_dict()})
        outcome["merge"] = result
        self._advance(outcome)
        return outcome

    def broom(self, at):
        good = self.board.cells[at] if self.board.valid_index(at) else None
        if not self.board.broom(at):
            return self._outcome(False, "There is nothing there to sweep.")
        outcome = self._outcome(True, f"Swept {good_label(good)} away.", {"kind": "broom", "at": at})
        self._advance(outcome)
        return outcome

    def sell(self, at):
        good = self.board.cells[at] if self.board.valid_index(at) else None
        value = self.board.sell(at)
        if value is None:
            return self._outcome(False, "There is nothing there to sell.")
        outcome = self._outcome(True, f"Sold {good_label(good)} for {value} coin{'s' if value != 1 else ''}.",
                                {"kind": "sell", "at": at, "coins": value})
        outcome["sold"] = value
        return outcome

    def deliver(self, src, index):
        window = self.window()
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(window):
            return self._outcome(False, "There is nobody there.")
        customer = window[index]
        good = self.board.cells[src] if self.board.valid_index(src) else None
        if good is None:
            return self._outcome(False, "Pick up a good first, then hand it over.")
        item = customer.match(good)
        if item is None:
            return self._outcome(False, customer.why_not(good))
        customer.items[item][2] = 1
        self.board.cells[src] = None
        outcome = self._outcome(True, f"{customer.name} takes the {good_label(good)}.",
                                {"kind": "deliver", "src": src, "customer": index})
        done = customer.is_complete()
        if done:
            outcome["message"] = ""
            self._serve(customer, outcome)
        self._advance(outcome, spared=customer if done else None)
        outcome["served_now"] = customer.name if done else None
        return outcome

    # ---- what the view needs -------------------------------------------------------------------
    def deliverable(self):
        """{cell: [customer indices]} for every good that would be accepted right now."""
        found = {}
        for cell, good in self.board.goods():
            takers = [i for i, c in enumerate(self.window()) if c.match(good) is not None]
            if takers:
                found[cell] = takers
        return found

    def summary(self):
        fraction = self.served * 100 // self.total if self.total else 100
        stars = 3 if fraction >= 90 else 2 if fraction >= 60 else 1
        return {"number": self.number, "served": self.served, "left": self.left, "total": self.total,
                "coins": self.coins, "beats": self.beat, "best_chain": self.best_chain, "stars": stars}

    # ---- saves -------------------------------------------------------------------------------------------
    def to_dict(self):
        data = {"number": self.number, "board": self.board.to_dict(), "queue": [c.to_dict() for c in self.queue],
                "total": self.total, "rng": self.rng.to_dict()}
        for key in ("served", "left", "coins", "beat", "best_chain"):
            if getattr(self, key):
                data[key] = getattr(self, key)
        return data

    @classmethod
    def from_dict(cls, data, families, rules=None):
        """Validated rebuild; raises ValueError so the caller can simply drop a damaged day."""
        if not isinstance(data, dict):
            raise ValueError("day must be an object")

        def whole(key, low=0, high=10 ** 7):
            value = data.get(key, 0)
            if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
                raise ValueError(f"bad {key}")
            return value

        number = whole("number", 1, 10 ** 5)
        total = whole("total", 1, 64)
        board = Board.from_dict(data.get("board"))
        raw = data.get("queue")
        if not isinstance(raw, list) or len(raw) > total:
            raise ValueError("bad queue")
        queue = [Customer.from_dict(c, families) for c in raw]
        served, left = whole("served", 0, 64), whole("left", 0, 64)
        if served + left + len(queue) != total:
            raise ValueError("the day does not add up")
        try:
            rng = Rng.from_dict(data.get("rng"))
        except (TypeError, KeyError):
            raise ValueError("bad rng")
        day = cls(number, board, queue, rng, rules)
        day.total, day.served, day.left = total, served, left
        day.coins, day.beat, day.best_chain = whole("coins"), whole("beat"), whole("best_chain", 0, 5)
        return day

