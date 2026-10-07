"""Chronicle -- the timeline builder's puzzles: generated from a set, graded, and given a nuance strip.

A puzzle is a PURE FUNCTION of (set id, set version, section id, round number): nothing random, no clock, no
saved state. The same four inputs give the same cards and the same tray order on every device and every
Python version (the generator is a small splitmix64, not `random`), and `tests/fixtures/puzzles_v1.json`
pins the sample set's puzzles so an accidental change to the generator is caught. A deliberate change must
bump SEED_VERSION and regenerate the fixture.

How a round is chosen: the section's pool is its events in `seq` order; round r ANCHORS on pool[r % n], so
the first n rounds visit every event once and a player can always reach "learned everything"; the other
size-1 cards are drawn by the seeded generator subject to the section's difficulty: every card has a date
that differs from every other (so the order is never ambiguous), and neighbours in time are at least
`min_gap_years` apart when the pool allows it (wide gaps early, near-ties in the last section).
"""

from setdata import event_key, year_of

SEED_VERSION = "v1"
MASK = (1 << 64) - 1


def fnv1a64(text):
    h = 0xCBF29CE484222325
    for byte in text.encode("utf-8"):
        h ^= byte
        h = (h * 0x100000001B3) & MASK
    return h


class Rng:
    """splitmix64: tiny, fast, and identical everywhere."""

    def __init__(self, seed_text):
        self.state = fnv1a64(seed_text)

    def next(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
        return z ^ (z >> 31)

    def below(self, n):
        if n <= 0:
            raise ValueError("below(n) needs n >= 1")
        limit = (1 << 64) - ((1 << 64) % n)
        while True:
            v = self.next()
            if v < limit:
                return v % n

    def shuffle(self, items):
        items = list(items)
        for i in range(len(items) - 1, 0, -1):
            j = self.below(i + 1)
            items[i], items[j] = items[j], items[i]
        return items

    def sample(self, items, k):
        items = list(items)
        out = []
        for _ in range(k):
            out.append(items.pop(self.below(len(items))))
        return out


class Puzzle:
    def __init__(self, set_id, section, round_no, size, tray, answer):
        self.set_id = set_id
        self.section = section
        self.round = round_no
        self.size = size
        self.tray = tray          # event ids in the order the tray first shows them
        self.answer = answer      # event ids, earliest first

    @property
    def code(self):
        return "%s/%s/%d" % (self.set_id, self.section, self.round)

    def to_dict(self):
        return {"id": self.code, "set": self.set_id, "section": self.section, "round": self.round,
                "size": self.size, "tray": list(self.tray), "answer": list(self.answer)}


def _distinct(cset, ids):
    keys = [event_key(cset.events[i]) for i in ids]
    return len(set(keys)) == len(keys)


def _gap_ok(cset, ids, min_gap):
    years = sorted(year_of(cset.events[i]) for i in ids)
    return all(b - a >= min_gap for a, b in zip(years, years[1:]))


def make_puzzle(cset, section_id, round_no):
    section = cset.section(section_id)
    if section is None:
        raise ValueError("unknown section %r" % (section_id,))
    if not isinstance(round_no, int) or isinstance(round_no, bool) or round_no < 0:
        raise ValueError("round must be a non-negative integer")
    pool = cset.section_pool(section_id)
    size = section["size"]
    if len(pool) < size:
        raise ValueError("section %s has fewer than %d events" % (section_id, size))
    anchor = pool[round_no % len(pool)]
    anchor_key = event_key(cset.events[anchor])
    others = [i for i in pool if i != anchor and event_key(cset.events[i]) != anchor_key]
    rng = Rng("chronicle|%s|%s|%s|%s|%d" % (SEED_VERSION, cset.id, cset.version, section_id, round_no))
    chosen = None
    if len(others) >= size - 1:
        for gap in (section["min_gap_years"], 0):
            for _ in range(120):
                pick = [anchor] + rng.sample(others, size - 1)
                if _distinct(cset, pick) and _gap_ok(cset, pick, gap):
                    chosen = pick
                    break
            if chosen:
                break
    if chosen is None:
        raise ValueError("section %s cannot build a puzzle of %d distinct dates around %s" % (section_id, size, anchor))
    answer = sorted(chosen, key=lambda i: (event_key(cset.events[i]), cset.events[i]["seq"]))
    tray = rng.shuffle(chosen)
    for _ in range(20):                      # never hand over the tray already in order
        if tray != answer:
            break
        tray = rng.shuffle(chosen)
    if tray == answer:
        tray = tray[1:] + tray[:1]
    return Puzzle(cset.id, section_id, round_no, size, tray, answer)


def main_rounds(cset, section_id):
    """Rounds 0..n-1 visit every event of the section as an anchor; later rounds are endless practice."""
    return len(cset.section_pool(section_id))


def grade(puzzle, placement):
    """Per-slot verdicts for a full or partial placement (a list of event ids or None, length = size).

    status is 'right' (that card belongs in that slot), 'wrong' (it belongs elsewhere) or 'empty'. A wrong
    card also says which way it should move: 'earlier' (a lower slot) or 'later' (a higher one).
    """
    slots = []
    right = 0
    for index in range(puzzle.size):
        card = placement[index] if index < len(placement) else None
        if card is None:
            slots.append({"index": index, "event": None, "status": "empty", "direction": None})
            continue
        true_index = puzzle.answer.index(card) if card in puzzle.answer else None
        if true_index == index:
            right += 1
            slots.append({"index": index, "event": card, "status": "right", "direction": None})
        else:
            direction = None
            if true_index is not None:
                direction = "earlier" if true_index < index else "later"
            slots.append({"index": index, "event": card, "status": "wrong", "direction": direction})
    placed = sum(1 for s in slots if s["event"] is not None)
    return {"slots": slots, "right": right, "placed": placed, "all_right": right == puzzle.size}


def nuance(cset, puzzle):
    """What else was happening: every 'elsewhere' event within the set's window (in years) of any card in
    this puzzle, nearest card named, ordered by date. Used by the nuance strip after a puzzle is solved."""
    cards = [(year_of(cset.events[i]), i) for i in puzzle.answer]
    out = []
    for cid in cset.event_ids("context"):
        year = year_of(cset.events[cid])
        best = min(cards, key=lambda c: (abs(c[0] - year), cset.events[c[1]]["seq"]))
        distance = abs(best[0] - year)
        if distance <= cset.window:
            out.append({"event": cid, "near": best[1], "years": distance})
    out.sort(key=lambda n: (event_key(cset.events[n["event"]]), cset.events[n["event"]]["seq"]))
    return out
