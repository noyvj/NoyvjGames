"""Evidence Hunt -- progress: which chapters are open, what is done, which case comes next. A case is done at any seal; the best
seal is kept and only rises (3 clean, 2 steady, 1 rough). Sandbox cases are not part of this."""

import cases

OPEN_AT = 5      # a chapter opens when this many cases of the one before are done

CHAPTERS = [{"index": i, "id": cid, "name": name, "blurb": blurb, "cases": [d["id"] for d in items]}
            for i, (cid, name, blurb, items) in enumerate(cases.CHAPTER_DATA)]
ORDER = [cid for c in CHAPTERS for cid in c["cases"]]
CHAPTER_OF = {cid: c["index"] for c in CHAPTERS for cid in c["cases"]}
DATA = {d["id"]: d for d in cases.ALL}


def done_in(best, chapter):
    return sum(1 for cid in chapter["cases"] if best.get(cid, 0) > 0)


def chapter_open(best, index):
    if index == 0:
        return True
    prev = CHAPTERS[index - 1]
    return done_in(best, prev) >= min(OPEN_AT, len(prev["cases"]))


def case_open(best, cid):
    return cid in CHAPTER_OF and chapter_open(best, CHAPTER_OF[cid])


def totals(best):
    grades = [best.get(cid, 0) for cid in ORDER]
    chapters_done = sum(1 for c in CHAPTERS if done_in(best, c) == len(c["cases"]))
    two = sum(1 for cid in ORDER if best.get(cid, 0) > 0 and len(DATA[cid]["truth"]) == 2)
    return {"cases": len(ORDER), "done": sum(1 for g in grades if g), "clean": sum(1 for g in grades if g == 3),
            "steady": sum(1 for g in grades if g == 2), "rough": sum(1 for g in grades if g == 1),
            "chapters": len(CHAPTERS), "chapters_done": chapters_done, "two": two}


def next_case(best, cur):
    """The next open case after `cur` that is not done yet (wrapping round), or the next open one at all, or None."""
    start = ORDER.index(cur) if cur in ORDER else -1
    rotated = ORDER[start + 1:] + ORDER[:start + 1]
    for want_undone in (True, False):
        for cid in rotated:
            if cid != cur and case_open(best, cid) and (not want_undone or not best.get(cid)):
                return cid
    return None
