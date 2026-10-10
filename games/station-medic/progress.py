"""Station Medic -- progress: what is done and which shift comes next. Every chapter is open from the start (AN-6), so the
player can take any shift in any order. A shift is done at any grade, a Rough seal included, and counts toward every total;
the best grade is kept and only rises (3 clean, 2 steady, 1 rough)."""

import cases

OPEN_AT = 0      # shifts of the previous chapter that must be done to open a chapter: none (every chapter is open from the start)

CHAPTERS = [{"index": i, "id": cid, "name": name, "blurb": blurb, "shifts": [d["id"] for d in shifts]}
            for i, (cid, name, blurb, shifts) in enumerate(cases.CHAPTER_DATA)]
ORDER = [sid for c in CHAPTERS for sid in c["shifts"]]
CHAPTER_OF = {sid: c["index"] for c in CHAPTERS for sid in c["shifts"]}
DATA = {d["id"]: d for d in cases.ALL}


def done_in(best, chapter):
    return sum(1 for sid in chapter["shifts"] if best.get(sid, 0) > 0)


def chapter_open(best, index):
    """Every chapter is open from the start. Old saves with chapters that used to be locked simply load open."""
    if index == 0 or OPEN_AT <= 0:
        return 0 <= index < len(CHAPTERS)
    prev = CHAPTERS[index - 1]
    return done_in(best, prev) >= min(OPEN_AT, len(prev["shifts"]))


def shift_open(best, sid):
    return sid in CHAPTER_OF and chapter_open(best, CHAPTER_OF[sid])


def grade_of(best, sid):
    return best.get(sid, 0)


def totals(best):
    grades = [best.get(sid, 0) for sid in ORDER]
    chapters_done = sum(1 for c in CHAPTERS if done_in(best, c) == len(c["shifts"]))
    patients = sum(len(DATA[sid]["patients"]) for sid in ORDER if best.get(sid, 0) > 0)
    return {"shifts": len(ORDER), "done": sum(1 for g in grades if g), "clean": sum(1 for g in grades if g == 3),
            "steady": sum(1 for g in grades if g == 2), "rough": sum(1 for g in grades if g == 1),
            "chapters": len(CHAPTERS), "chapters_done": chapters_done, "patients": patients}


def next_shift(best, cur):
    """The next open shift after `cur` that is not done yet (wrapping round), or the next open one at all, or None."""
    start = ORDER.index(cur) if cur in ORDER else -1
    rotated = ORDER[start + 1:] + ORDER[:start + 1]
    for want_undone in (True, False):
        for sid in rotated:
            if sid != cur and shift_open(best, sid) and (not want_undone or not best.get(sid)):
                return sid
    return None
