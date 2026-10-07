"""Chronicle -- myth or record: sort claims into documented, disputed and traditional-but-doubtful.

A puzzle is a PURE FUNCTION of (set id, set version, chapter id, round), like the other mechanics. A chapter
lists claims (`chapters.json`); round r ANCHORS on claim[r % n], so the first n rounds visit every claim once
and a player can always sort the whole chapter. The other `size - 1` claims are drawn by the seeded generator,
and when the chapter has both kinds a puzzle always holds at least one documented claim and at least one
disputed or doubtful one (a stack of nothing but records would teach nothing). The right bin for a claim is its
own `confidence` field: there is no second source of truth. `tests/fixtures/myth_puzzles_v1.json` pins the
sample set's puzzles (regenerate with tests/make_fixture.py after bumping SEED_VERSION).
"""

from puzzle import Rng

SEED_VERSION = "v1"
BINS = ("documented", "disputed", "traditional-but-doubtful")


class MythPuzzle:
    def __init__(self, set_id, chapter, round_no, size, tray, answer):
        self.set_id = set_id
        self.chapter = chapter
        self.round = round_no
        self.size = size
        self.tray = tray            # claim ids in the order the page first shows them
        self.answer = answer        # {claim id: its bin}

    @property
    def code(self):
        return "%s/%s/%d" % (self.set_id, self.chapter, self.round)

    def to_dict(self):
        return {"id": self.code, "set": self.set_id, "chapter": self.chapter, "round": self.round, "size": self.size,
                "tray": list(self.tray), "answer": dict(self.answer)}


def main_rounds(cset, chapter_id):
    ch = cset.myth_chapter(chapter_id)
    return len(ch["claims"]) if ch else 0


def _mixed(cset, ids):
    kinds = {cset.claims[i]["confidence"] == "documented" for i in ids}
    return len(kinds) == 2


def make_myth_puzzle(cset, chapter_id, round_no):
    ch = cset.myth_chapter(chapter_id)
    if ch is None:
        raise ValueError("unknown myth chapter %r" % (chapter_id,))
    if not isinstance(round_no, int) or isinstance(round_no, bool) or round_no < 0:
        raise ValueError("round must be a non-negative integer")
    pool = list(ch["claims"])
    size = min(ch["size"], len(pool))
    anchor = pool[round_no % len(pool)]
    others = [c for c in pool if c != anchor]
    rng = Rng("chronicle-myth|%s|%s|%s|%s|%d" % (SEED_VERSION, cset.id, cset.version, chapter_id, round_no))
    chosen = None
    mixable = _mixed(cset, pool)
    for _ in range(200):
        pick = [anchor] + rng.sample(others, size - 1)
        if not mixable or _mixed(cset, pick):
            chosen = pick
            break
    if chosen is None:
        raise ValueError("myth chapter %s cannot build a mixed puzzle around %s" % (chapter_id, anchor))
    tray = rng.shuffle(chosen)
    answer = {c: cset.claims[c]["confidence"] for c in chosen}
    return MythPuzzle(cset.id, chapter_id, round_no, size, tray, answer)


def grade(puzzle, bins):
    """Per-claim verdicts for a full or partial sorting ({claim id: bin or None}). 'right', 'wrong' or 'empty'."""
    out = []
    right = 0
    for cid in puzzle.tray:
        chosen = bins.get(cid)
        if chosen is None:
            out.append({"claim": cid, "bin": None, "status": "empty"})
        elif chosen == puzzle.answer[cid]:
            right += 1
            out.append({"claim": cid, "bin": chosen, "status": "right"})
        else:
            out.append({"claim": cid, "bin": chosen, "status": "wrong"})
    placed = sum(1 for o in out if o["bin"] is not None)
    return {"claims": out, "right": right, "placed": placed, "all_right": right == puzzle.size}
