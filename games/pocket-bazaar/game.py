"""Pocket Bazaar -- the engine's single entry point (the Lexis / Signal pattern).

The view (app.js) never reads engine objects: it sends one JSON string to `handle` and draws the JSON that
comes back. `get_state()` / `load_state()` are the shared save widget's contract
(planning/SAVE-BUTTON-INTEGRATION.md). Nothing here reads a clock: the game is turn-based.

Actions (every request is {"action": ..., ...}; every reply is the whole view):
  open                        the current view
  crate {family}              put a tier-1 good of that family on the first free cell
  drop {from, to}             merge two goods, or move / swap (cells are numbered row by row)
  sell {at}                   sell a good off the board for its sell price
  broom {at}                  sweep a good off the board for free
  clear                       sweep the whole board clear (free, no tally change)
  reset                       start over (everything)
"""

import json

import goods
from board import Board, DEFAULT_HEIGHT, DEFAULT_WIDTH
from goods import FAMILY_INFO, good_label

FAMILIES_AT_START = ("produce", "textiles", "ceramics")
TALLY_KEYS = ("crates", "merges", "sold", "swept", "triples")
MAX_COINS = 10 ** 9


def _int(value, low=0, high=MAX_COINS, default=0):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        return default
    return value


class Stall:
    """Everything the player has. M2: just a practice board, coins and a tally of what they have done."""

    def __init__(self):
        self.board = Board(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        self.coins = 0
        self.tally = {key: 0 for key in TALLY_KEYS}
        self.best_chain = 0

    def to_dict(self):
        """Only what differs from a fresh game is written, so old and new saves stay compatible."""
        data = {}
        if self.board.count():
            data["board"] = self.board.to_dict()
        if self.coins:
            data["coins"] = self.coins
        tally = {k: v for k, v in self.tally.items() if v}
        if tally:
            data["tally"] = tally
        if self.best_chain:
            data["best_chain"] = self.best_chain
        return data

    def load(self, data):
        """Take a saved dict, checking every field on its own; a bad field falls back to its default."""
        data = data if isinstance(data, dict) else {}
        try:
            self.board = Board.from_dict(data["board"]) if "board" in data else Board(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        except (ValueError, TypeError, KeyError):
            self.board = Board(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        self.coins = _int(data.get("coins"))
        tally = data.get("tally") if isinstance(data.get("tally"), dict) else {}
        self.tally = {key: _int(tally.get(key)) for key in TALLY_KEYS}
        self.best_chain = _int(data.get("best_chain"), high=goods.MAX_TIER)


stall = Stall()


def _cell_view(i, good):
    if good is None:
        return None
    if goods.is_wild(good):
        return {"code": goods.good_code(good), "family": "wild", "tier": 1, "name": "Wildcard", "letter": "*",
                "shape": "star", "label": "Wildcard", "next": None}
    info = FAMILY_INFO[good[0]]
    return {"code": goods.good_code(good), "family": good[0], "tier": good[1], "name": goods.good_name(good),
            "letter": info["letter"], "shape": info["shape"], "label": good_label(good),
            "next": goods.next_tier_name(good), "sell": goods.sell_value(good)}


def _view(message="", ok=True, event=None):
    board = stall.board
    partners = {str(i): board.partners(i) for i, g in board.goods() if board.partners(i)}
    return {
        "ok": ok, "message": message, "event": event,
        "board": {"w": board.width, "h": board.height, "shelf": board.has_shelf,
                  "cells": [_cell_view(i, g) for i, g in enumerate(board.cells)]},
        "partners": partners,
        "crates": [{"family": f, "name": FAMILY_INFO[f]["name"], "letter": FAMILY_INFO[f]["letter"],
                    "shape": FAMILY_INFO[f]["shape"]} for f in FAMILIES_AT_START],
        "full": board.first_empty() is None,
        "coins": stall.coins,
        "tally": dict(stall.tally),
        "best_chain": stall.best_chain,
    }


def _merge_message(result):
    text = f"Merged into {good_label(result.good)}."
    if result.triple:
        text += " Three-way bonus: two tiers at once!"
    if result.links > 1:
        text += f" {result.links}-link chain!"
    return text


def handle(request_json):
    try:
        request = json.loads(request_json)
        action = request.get("action")
    except (ValueError, AttributeError):
        return json.dumps({"error": "bad request"})
    board = stall.board
    if action == "open":
        return json.dumps(_view())
    if action == "crate":
        family = request.get("family")
        if family not in FAMILIES_AT_START:
            return json.dumps(_view("That crate is not open yet.", ok=False))
        at = board.place((family, 1))
        if at is None:
            return json.dumps(_view("The counter is full. Merge, sell or sweep something to make room.", ok=False))
        stall.tally["crates"] += 1
        return json.dumps(_view(f"{good_label((family, 1))} from the {FAMILY_INFO[family]['name']} crate.",
                                event={"kind": "crate", "at": at}))
    if action == "drop":
        src, dst = request.get("from"), request.get("to")
        result = board.drop(src, dst)
        if not result.ok:
            return json.dumps(_view(result.reason, ok=False))
        if result.links:
            stall.tally["merges"] += result.links
            stall.tally["triples"] += 1 if result.triple else 0
            stall.best_chain = max(stall.best_chain, result.links)
            return json.dumps(_view(_merge_message(result), event={"kind": "merge", **result.to_dict()}))
        return json.dumps(_view("Swapped them." if result.swapped else "Moved.",
                                event={"kind": "move", "src": result.src, "dst": result.dst}))
    if action == "sell":
        at = request.get("at")
        good = board.cells[at] if board.valid_index(at) else None
        value = board.sell(at)
        if value is None:
            return json.dumps(_view("There is nothing there to sell.", ok=False))
        stall.coins += value
        stall.tally["sold"] += 1
        return json.dumps(_view(f"Sold {good_label(good)} for {value} coin{'s' if value != 1 else ''}.",
                                event={"kind": "sell", "at": at, "coins": value}))
    if action == "broom":
        at = request.get("at")
        good = board.cells[at] if board.valid_index(at) else None
        if not board.broom(at):
            return json.dumps(_view("There is nothing there to sweep.", ok=False))
        stall.tally["swept"] += 1
        return json.dumps(_view(f"Swept {good_label(good)} away.", event={"kind": "broom", "at": at}))
    if action == "clear":
        for i in range(len(board.cells)):
            board.cells[i] = None
        return json.dumps(_view("The counter is clear."))
    if action == "reset":
        stall.__init__()
        return json.dumps(_view("Starting over."))
    return json.dumps({"error": f"unknown action {action!r}"})


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
