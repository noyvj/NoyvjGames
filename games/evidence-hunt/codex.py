"""Evidence Hunt -- the field guide (the codex). Pages are collected, never missed: a spirit page is filed when you first name that kind
and is COMPLETE once a reading in a solved case has confirmed each of its three pieces of evidence; an evidence page on the first
positive reading of it; an equipment page on the first use; a keepsake when you return it; a house note when every case of its
chapter is done. Everything is derived from the save's facts, so a loaded save and a played one cannot disagree.

Spirit confirmations are only written when a case is solved, so the guide never gives away the answer to a case you are still on."""

import cases
import lexicon as lx
import progress

NOTICE = ("This guide is your own notes, and everything in it is invented. A spirit's page is filed when you first name it and "
          "completes as readings in solved cases confirm each piece of its evidence. Nothing is missable and nothing runs out.")

SECTIONS = (("spirits", "Spirits"), ("evidence", "Evidence"), ("equipment", "Equipment"), ("keepsakes", "Keepsakes"), ("notes", "House notes"))

NOTES = {
    "first-visits": "Small houses taught the habit: walk every room, find where it is restless, and take the readings that tell the suspects apart.",
    "misleading": "A draught is not a spirit, and neither is old wiring. When a room's own feature fools a reading, trust the room it does not fool.",
    "two-presences": "Some houses hold two. Each is in a room of its own, so read room by room and name both.",
    "keepsakes": "What a spirit loves it keeps close. A keepsake swamps its room, but looking at it says who loves it, and returning it is how the case ends well.",
    "big-houses": "Ten rooms or fourteen, three floors and a bag of four. It is the same careful plan, only longer. The book is closed and every house is in order.",
}

KEEP_CASE = {}
for _d in cases.ALL:
    if _d.get("keepsake") and _d["keepsake"][1] not in KEEP_CASE:
        KEEP_CASE[_d["keepsake"][1]] = (_d["id"], _d["title"])


def total():
    return len(lx.KIND_IDS) + len(lx.EV_IDS) + len(lx.EV_IDS) + len(lx.KS_IDS) + len(progress.CHAPTERS)


def chapter_done(best, index):
    return progress.done_in(best, progress.CHAPTERS[index]) == len(progress.CHAPTERS[index]["cases"])


def full(kind, met, seen):
    return kind in met and len(seen.get(kind, [])) == 3


def counts(met, ev, eq, kept, best):
    """(pages found, pages in all)."""
    found = len(met) + len(ev) + len(eq) + len(kept) + sum(1 for c in progress.CHAPTERS if chapter_done(best, c["index"]))
    return found, total()


def spirits_full(met, seen):
    return sum(1 for k in lx.KIND_IDS if full(k, met, seen))


def view(met, seen, ev, eq, kept, best):
    found, tot = counts(met, ev, eq, kept, best)
    sections = []
    spirits = []
    for k in lx.KIND_IDS:
        got = [e for e in lx.EV_IDS if e in seen.get(k, [])]
        is_met = k in met
        lines = []
        if is_met:
            ev_names = [lx.EV_NAME[i] if lx.EV_IDS[i] in got else "?" for i in sorted(lx.KIND_EVIDENCE[k])]
            lines = ["Evidence: " + ", ".join(ev_names) + (" (all confirmed)" if len(got) == 3 else " (a ? is confirmed by a reading in a solved case)"),
                     "Habits: " + " ".join(lx.BH_RULE[b] for b in lx.BH_IDS if b in lx.KIND_BEHAVIOURS[k])]
        spirits.append({"id": k, "title": lx.KIND_NAME[k] + (" (complete)" if full(k, met, seen) else ""), "unlocked": is_met,
                        "text": lx.KIND_NOTE[k] if is_met else "Not met yet. Name this kind in a case to file its page.", "lines": lines})
    sections.append({"id": "spirits", "name": "Spirits", "found": len(met), "total": len(lx.KIND_IDS), "entries": spirits})
    evid = []
    for i, e in enumerate(lx.EV_IDS):
        feat = [f for f in lx.FT_IDS if lx.FT_FOOLS[f] == i][0]
        have = e in ev
        evid.append({"id": e, "title": lx.EV_NAME[i], "unlocked": have,
                     "text": ("Read with the %s. A positive reading is real unless the room fools it." % lx.GEAR_NAME[i]) if have else "Not seen yet: take a positive reading of this evidence.",
                     "lines": ["The house can fool it: %s" % lx.FT_TEXT[feat]] if have else []})
    sections.append({"id": "evidence", "name": "Evidence", "found": len(ev), "total": len(lx.EV_IDS), "entries": evid})
    gear = []
    for i, e in enumerate(lx.EV_IDS):
        have = e in eq
        gear.append({"id": e, "title": lx.GEAR_NAME[i], "unlocked": have,
                     "text": lx.GEAR_HOW[i] if have else "Not used yet: pack it and take a reading.", "lines": ["Reads: " + lx.EV_NAME[i]] if have else []})
    sections.append({"id": "equipment", "name": "Equipment", "found": len(eq), "total": len(lx.EV_IDS), "entries": gear})
    keeps = []
    for k in lx.KS_IDS:
        have = k in kept
        where = KEEP_CASE.get(k)
        keeps.append({"id": k, "title": lx.KS_NAME[k], "unlocked": have, "text": lx.KS_RETURN[k] if have else "Not returned yet. Solve %s, then return it." % (("case %s, %s" % where) if where else "its case"), "lines": []})
    sections.append({"id": "keepsakes", "name": "Keepsakes", "found": len(kept), "total": len(lx.KS_IDS), "entries": keeps})
    notes = []
    done_notes = 0
    for c in progress.CHAPTERS:
        have = chapter_done(best, c["index"])
        done_notes += 1 if have else 0
        notes.append({"id": c["id"], "title": c["name"], "unlocked": have, "text": NOTES[c["id"]] if have else "Finish every case of this chapter to file its note.", "lines": []})
    sections.append({"id": "notes", "name": "House notes", "found": done_notes, "total": len(progress.CHAPTERS), "entries": notes})
    return {"notice": NOTICE, "found": found, "total": tot, "complete": spirits_full(met, seen), "sections": sections}
