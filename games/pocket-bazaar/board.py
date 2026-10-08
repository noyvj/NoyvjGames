"""Pocket Bazaar -- the merge board. Pure rules, no DOM, no clock, no randomness.

The board is a width x height grid of cells (default 5 x 6), indexed row by row from 0, plus an optional extra
shelf cell (the stall upgrade) with the index right after the grid. A cell is None or a good (see goods.py).
Cell numbers are what the view and the saves use.

Rules
  * Two identical goods merge: the dragged one disappears and the one dropped on becomes the next tier. Tier 5
    (the showpiece) never merges.
  * Three-way bonus: if a third identical good sits next to the cell dropped on, all three merge into tier + 2
    (when that tier exists). No randomness, a small skill reward.
  * Cascade: when a merge makes a good that matches a neighbour, they merge again, and so on. The whole chain
    is one move. With five tiers the longest chain is four merges (T1+T1, T2, T3, T4).
  * A wildcard merges with any non-showpiece regular good and gives that good's next tier.
  * Dropping on an empty cell moves a good, dropping on a different good swaps them. Neither is a beat.
  * Sell and Broom always work on any good, so the board can never soft-lock (see has_legal_move).
"""

from goods import MAX_TIER, WILD, is_wild, good_code, parse_code, sell_value, valid_good

DEFAULT_WIDTH = 5
DEFAULT_HEIGHT = 6
MIN_SIDE = 3
MAX_SIDE = 8


class MergeResult:
    """What one merge did. `steps` lists the tier made by each merge in the chain; `links` is how many merges
    that was (1 for a plain pair); `spawned` lists cells that got a free good from a festival rule."""

    def __init__(self, dst, good, steps, triple, consumed, spawned):
        self.ok = True
        self.reason = ""
        self.dst = dst
        self.good = good
        self.steps = steps
        self.links = len(steps)
        self.triple = triple
        self.consumed = consumed
        self.spawned = spawned

    def to_dict(self):
        return {"ok": True, "dst": self.dst, "good": list(self.good), "steps": list(self.steps),
                "links": self.links, "triple": self.triple, "consumed": list(self.consumed),
                "spawned": list(self.spawned)}


class Refused:
    """A move the board would not make; `reason` is a plain sentence for the player."""

    def __init__(self, reason):
        self.ok = False
        self.reason = reason
        self.links = 0

    def to_dict(self):
        return {"ok": False, "reason": self.reason}


class Moved:
    """A good moved to an empty cell, or two different goods swapped."""

    def __init__(self, src, dst, swapped):
        self.ok = True
        self.reason = ""
        self.links = 0
        self.src = src
        self.dst = dst
        self.swapped = swapped

    def to_dict(self):
        return {"ok": True, "moved": True, "src": self.src, "dst": self.dst, "swapped": self.swapped}


class Board:
    def __init__(self, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, shelf=False):
        if not (MIN_SIDE <= width <= MAX_SIDE and MIN_SIDE <= height <= MAX_SIDE):
            raise ValueError("board sides must be 3..8")
        self.width = width
        self.height = height
        self.size = width * height
        self.has_shelf = bool(shelf)
        self.cells = [None] * (self.size + (1 if self.has_shelf else 0))

    # ---- geometry --------------------------------------------------------------------------------
    @property
    def shelf_index(self):
        return self.size if self.has_shelf else None

    def valid_index(self, i):
        return isinstance(i, int) and not isinstance(i, bool) and 0 <= i < len(self.cells)

    def in_grid(self, i):
        return isinstance(i, int) and not isinstance(i, bool) and 0 <= i < self.size

    def neighbors(self, i):
        """The cells up, left, right and down of a grid cell (in reading order); the shelf has none."""
        if not self.in_grid(i):
            return []
        row, col = divmod(i, self.width)
        out = []
        if row > 0:
            out.append(i - self.width)
        if col > 0:
            out.append(i - 1)
        if col < self.width - 1:
            out.append(i + 1)
        if row < self.height - 1:
            out.append(i + self.width)
        return out

    def copy(self):
        other = Board(self.width, self.height, self.has_shelf)
        other.cells = list(self.cells)
        return other

    # ---- contents --------------------------------------------------------------------------------
    def empty_cells(self):
        return [i for i in range(self.size) if self.cells[i] is None]

    def first_empty(self):
        for i in range(self.size):
            if self.cells[i] is None:
                return i
        return None

    def goods(self):
        return [(i, g) for i, g in enumerate(self.cells) if g is not None]

    def count(self):
        return sum(1 for g in self.cells if g is not None)

    def is_full(self):
        return self.first_empty() is None

    def place(self, good, at=None):
        """Put a good in a cell (the first empty grid cell unless `at` is given). Returns the cell or None."""
        if not valid_good(good):
            raise ValueError("not a good")
        if at is None:
            at = self.first_empty()
            if at is None:
                return None
        elif not self.valid_index(at) or self.cells[at] is not None:
            return None
        self.cells[at] = (good[0], good[1])
        return at

    # ---- merging ---------------------------------------------------------------------------------
    def merged_good(self, a, b):
        """The good that merging cells a and b would make, or None when they do not merge."""
        if a == b or not self.valid_index(a) or not self.valid_index(b):
            return None
        g, h = self.cells[a], self.cells[b]
        if g is None or h is None:
            return None
        if is_wild(g) and is_wild(h):
            return None
        if is_wild(g) or is_wild(h):
            other = h if is_wild(g) else g
            return (other[0], other[1] + 1) if other[1] < MAX_TIER else None
        if g == h and g[1] < MAX_TIER:
            return (g[0], g[1] + 1)
        return None

    def can_merge(self, a, b):
        return self.merged_good(a, b) is not None

    def partners(self, i):
        """Every other cell this good could merge with."""
        return [j for j in range(len(self.cells)) if j != i and self.can_merge(i, j)]

    def merge_pairs(self):
        return [(a, b) for a in range(len(self.cells)) for b in range(a + 1, len(self.cells)) if self.can_merge(a, b)]

    def merge(self, src, dst, rules=None):
        """Merge the good at src into the good at dst. `rules` may hold {"twin": True} (Twin Day)."""
        made = self.merged_good(src, dst)
        if made is None:
            return Refused(self._why_not(src, dst))
        rules = rules or {}
        plain = not is_wild(self.cells[src]) and not is_wild(self.cells[dst])
        consumed = [src]
        triple = False
        family, tier = made
        if plain and tier + 1 <= MAX_TIER:
            for n in self.neighbors(dst):
                if n != src and self.cells[n] == self.cells[dst]:
                    consumed.append(n)
                    triple = True
                    tier += 1
                    break
        self.cells[src] = None
        for n in consumed[1:]:
            self.cells[n] = None
        self.cells[dst] = (family, tier)
        steps = [tier]
        spawned = []
        self._twin(dst, family, tier, rules, spawned)
        while tier < MAX_TIER:
            match = next((n for n in self.neighbors(dst) if self.cells[n] == (family, tier)), None)
            if match is None:
                break
            self.cells[match] = None
            consumed.append(match)
            tier += 1
            self.cells[dst] = (family, tier)
            steps.append(tier)
            self._twin(dst, family, tier, rules, spawned)
        return MergeResult(dst, (family, tier), steps, triple, consumed, spawned)

    def _twin(self, dst, family, tier, rules, spawned):
        """Twin Day: a merge that makes a tier-3 good also sets a free tier-1 good down nearby."""
        if not rules.get("twin") or tier != 3:
            return
        for cell in self.neighbors(dst) + self.empty_cells():
            if self.cells[cell] is None:
                self.cells[cell] = (family, 1)
                spawned.append(cell)
                return

    def _why_not(self, src, dst):
        if not self.valid_index(src) or not self.valid_index(dst):
            return "That is not a spot on the board."
        if src == dst:
            return "That is the same spot."
        g, h = self.cells[src], self.cells[dst]
        if g is None:
            return "There is nothing there to move."
        if h is None:
            return "That spot is empty."
        if is_wild(g) and is_wild(h):
            return "Two wildcards do not merge."
        if is_wild(g) or is_wild(h):
            return "A showpiece cannot be merged any further."
        if g != h:
            return "Only two identical goods merge."
        return "A showpiece cannot be merged any further."

    # ---- moving, selling, sweeping -------------------------------------------------------------------
    def move(self, src, dst):
        """Move a good to an empty cell, or swap two different goods."""
        if not self.valid_index(src) or not self.valid_index(dst) or src == dst:
            return Refused("That is not a spot to move to.")
        if self.cells[src] is None:
            return Refused("There is nothing there to move.")
        self.cells[src], self.cells[dst] = self.cells[dst], self.cells[src]
        return Moved(src, dst, self.cells[src] is not None)

    def drop(self, src, dst, rules=None):
        """What dropping src on dst does: a merge when the two merge, otherwise a move or swap."""
        if self.can_merge(src, dst):
            return self.merge(src, dst, rules)
        return self.move(src, dst)

    def sell(self, i):
        """Take a good off the board for its sell price (never zero). Returns the coins or None."""
        if not self.valid_index(i) or self.cells[i] is None:
            return None
        value = sell_value(self.cells[i])
        self.cells[i] = None
        return value

    def broom(self, i):
        """Sweep a cell clear for free. Returns True when something was swept."""
        if not self.valid_index(i) or self.cells[i] is None:
            return False
        self.cells[i] = None
        return True

    # ---- the no-soft-lock guarantee ---------------------------------------------------------------
    def legal_actions(self):
        """Every action the player could take right now: a crate (if a cell is free), merges, sells, brooms."""
        actions = []
        if self.first_empty() is not None:
            actions.append(("crate", self.first_empty()))
        actions.extend(("merge", a, b) for a, b in self.merge_pairs())
        for i, _good in self.goods():
            actions.append(("sell", i))
            actions.append(("broom", i))
        return actions

    def has_legal_move(self):
        return bool(self.legal_actions())

    def can_progress(self):
        """True when a crate or a merge is possible; when False, Sell or Broom is the way out."""
        return self.first_empty() is not None or bool(self.merge_pairs())

    # ---- text and saves ----------------------------------------------------------------------------
    def render(self):
        """The text board: one line per row of two-character codes, and a 'shelf:' line when there is one."""
        lines = []
        for row in range(self.height):
            lines.append(" ".join(good_code(self.cells[row * self.width + c]) for c in range(self.width)))
        if self.has_shelf:
            lines.append("shelf: " + good_code(self.cells[self.size]))
        return "\n".join(lines)

    @classmethod
    def from_text(cls, text, width=None, height=None):
        """Build a board from the text form. Short rows and missing rows are empty; sizes default to the text."""
        rows, shelf = [], None
        for line in text.strip("\n").splitlines():
            line = line.strip()
            if line.startswith("shelf:"):
                shelf = parse_code(line.split(":", 1)[1].strip())
            elif line:
                rows.append([parse_code(tok) for tok in line.split()])
        width = width or max([len(r) for r in rows] + [DEFAULT_WIDTH])
        height = height or max(len(rows), DEFAULT_HEIGHT)
        board = cls(width, height, shelf is not None)
        for r, row in enumerate(rows):
            for c, good in enumerate(row):
                board.cells[r * width + c] = good
        if shelf is not None:
            board.cells[board.size] = shelf
        return board

    def to_dict(self):
        return {"w": self.width, "h": self.height, "shelf": self.has_shelf,
                "cells": [None if g is None else {"f": g[0], "t": g[1]} for g in self.cells]}

    @classmethod
    def from_dict(cls, data):
        """Rebuild a saved board, rejecting anything malformed with ValueError (the caller keeps its own)."""
        if not isinstance(data, dict):
            raise ValueError("board must be an object")
        width, height = data.get("w"), data.get("h")
        for side in (width, height):
            if isinstance(side, bool) or not isinstance(side, int) or not MIN_SIDE <= side <= MAX_SIDE:
                raise ValueError("bad board size")
        board = cls(width, height, bool(data.get("shelf", False)))
        cells = data.get("cells")
        if not isinstance(cells, list) or len(cells) != len(board.cells):
            raise ValueError("bad cells")
        for i, cell in enumerate(cells):
            if cell is None:
                continue
            if not isinstance(cell, dict):
                raise ValueError("bad cell")
            good = (cell.get("f"), cell.get("t"))
            if not valid_good(good):
                raise ValueError("bad good")
            board.cells[i] = good
        return board


def plan_build(board, family, tier, limit=400):
    """A solver: the crate and merge actions that would build one (family, tier) good from this board, found by
    always merging the lowest pair first. Works on a copy. Returns (actions, result_board) or None when the
    board is too cramped. Used by the tests and by bots to prove a good is reachable."""
    work = board.copy()
    actions = []
    target = (family, tier)
    for _ in range(limit):
        if target in work.cells:
            return actions, work
        pair = None
        for t in range(1, tier):
            cells = [i for i, g in enumerate(work.cells) if g == (family, t)]
            if len(cells) >= 2:
                pair = (cells[0], cells[1])
                break
        if pair is not None:
            work.merge(pair[0], pair[1])
            actions.append(("merge", pair[0], pair[1]))
        elif work.first_empty() is not None:
            at = work.place((family, 1))
            actions.append(("crate", family, at))
        else:
            return None
    return None


__all__ = ["Board", "MergeResult", "Moved", "Refused", "plan_build", "WILD"]
