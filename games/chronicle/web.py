"""Chronicle -- the cause web's puzzles: generated from a set, judged one thread at a time.

Like the timeline builder (puzzle.py) a puzzle is a PURE FUNCTION of (set id, set version, chapter id, round):
no random state, no clock, no saved progress. A chapter lists the events it draws from (`chapters.json`); its
relations are the set's relations with both ends inside it. Round r ANCHORS on relation[r % n], so the first n
rounds visit every relation once and a player can always reach "found every link"; the other `size - 2` cards
are distractors drawn by the seeded generator. Every relation of the set that lies between the chosen cards
is part of the puzzle (a distractor pair may happen to be linked: it is then a link to find, never a trap).

The game CONFIRMS a thread only if it is in the set's relations. Anything else is "not confirmed": that does
NOT say the two moments are unrelated, only that none of this set's sourced relations joins them, and the
page says so in words. `tests/fixtures/web_puzzles_v1.json` pins the sample set's puzzles; a deliberate change
to the generator must bump SEED_VERSION and regenerate the fixture (tests/make_fixture.py).
"""

from puzzle import Rng
from setdata import event_key

SEED_VERSION = "v1"


class WebPuzzle:
    def __init__(self, set_id, chapter, round_no, size, cards, relations):
        self.set_id = set_id
        self.chapter = chapter
        self.round = round_no
        self.size = size
        self.cards = cards              # event ids, earliest first (the board shows them in this order)
        self.relations = relations      # relation ids lying between the cards: the links to find

    @property
    def code(self):
        return "%s/%s/%d" % (self.set_id, self.chapter, self.round)

    def to_dict(self):
        return {"id": self.code, "set": self.set_id, "chapter": self.chapter, "round": self.round, "size": self.size,
                "cards": list(self.cards), "relations": list(self.relations)}


def main_rounds(cset, chapter_id):
    """Rounds 0..n-1 visit every relation of the chapter as the anchor; later rounds are endless practice."""
    ch = cset.web_chapter(chapter_id)
    return len(cset.chapter_relations(ch)) if ch else 0


def make_web_puzzle(cset, chapter_id, round_no):
    ch = cset.web_chapter(chapter_id)
    if ch is None:
        raise ValueError("unknown web chapter %r" % (chapter_id,))
    if not isinstance(round_no, int) or isinstance(round_no, bool) or round_no < 0:
        raise ValueError("round must be a non-negative integer")
    rels = cset.chapter_relations(ch)
    if not rels:
        raise ValueError("web chapter %s has no relations" % chapter_id)
    anchor = cset.relation_by_id[rels[round_no % len(rels)]]
    cards = [anchor["from"], anchor["to"]]
    others = [e for e in ch["events"] if e not in cards]
    rng = Rng("chronicle-web|%s|%s|%s|%s|%d" % (SEED_VERSION, cset.id, cset.version, chapter_id, round_no))
    extra = min(max(ch["size"] - 2, 0), len(others))
    cards += rng.sample(others, extra)
    cards.sort(key=lambda e: (event_key(cset.events[e]), cset.events[e]["seq"]))
    inside = set(cards)
    linked = [r["id"] for r in cset.relations if r["from"] in inside and r["to"] in inside]
    return WebPuzzle(cset.id, chapter_id, round_no, len(cards), cards, linked)


def judge(cset, puzzle, cause, effect):
    """Judge one proposed thread 'cause led to effect'. Returns {verdict, relation}:
    confirmed (the set has it), reversed (the set has it the other way round), unconfirmed (the set has no
    such relation: not the same as 'unrelated'), or invalid (a card not on the board, or the same card twice)."""
    if cause == effect or cause not in puzzle.cards or effect not in puzzle.cards:
        return {"verdict": "invalid", "relation": None}
    for rid in puzzle.relations:
        r = cset.relation_by_id[rid]
        if r["from"] == cause and r["to"] == effect:
            return {"verdict": "confirmed", "relation": rid}
    for rid in puzzle.relations:
        r = cset.relation_by_id[rid]
        if r["from"] == effect and r["to"] == cause:
            return {"verdict": "reversed", "relation": rid}
    return {"verdict": "unconfirmed", "relation": None}
