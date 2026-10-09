"""Station Medic -- the Record (the codex). Pages are collected, never missed: a condition is filed the first time you cure it, a
scan the first time you run it, a treatment the first time it cures, a crew beat when the shift it belongs to is done, a station
note when its chapter is done. Everything is derived from the save's facts, so a loaded save and a played one cannot disagree.

Crew beats belong to fixed appearances in the authored order of shifts (cast.BEAT_AT), so playing a chapter in a different order
never changes which beat comes next."""

from collections import Counter

import cases
import cast
import info
import lexicon as lx
import progress


def _assign():
    seen = Counter()
    by_shift = {}
    for d in cases.ALL:
        out = []
        for p in d["patients"]:
            seen[p["crew"]] += 1
            if seen[p["crew"]] in cast.BEAT_AT:
                out.append((p["crew"], cast.BEAT_AT.index(seen[p["crew"]])))
        by_shift[d["id"]] = out
    return by_shift, seen


BEATS_BY_SHIFT, APPEARANCES = _assign()
# Tally's beats are told on the 1st, 4th, 8th, 12th and 17th shift where it is on duty
TALLY_AT = (0, 3, 7, 11, 16)
ROBOT_SHIFTS = [d["id"] for d in cases.ALL if d.get("robots")]
TALLY_BY_SHIFT = {ROBOT_SHIFTS[i]: k for k, i in enumerate(TALLY_AT) if i < len(ROBOT_SHIFTS)}
NOTE_SHIFTS = [c["shifts"] for c in progress.CHAPTERS]
SECTIONS = (("conditions", "Conditions"), ("scans", "Scans"), ("treatments", "Treatments"), ("crew", "Crew files"), ("notes", "Station notes"))


def beats_told(best):
    """[(crew id, beat index)] unlocked by the shifts done so far."""
    return [(c, k) for sid, items in BEATS_BY_SHIFT.items() if best.get(sid) for c, k in items]


def tally_told(best):
    return sorted(k for sid, k in TALLY_BY_SHIFT.items() if best.get(sid))


def beats_for(sid):
    """The crew beats (and Tally's) the shift `sid` tells, for its result card."""
    out = [{"who": cast.CREW_BY_ID[c]["name"], "text": cast.BEATS[c][k]} for c, k in BEATS_BY_SHIFT.get(sid, [])]
    if sid in TALLY_BY_SHIFT:
        out.append({"who": "Tally", "text": cast.TALLY_BEATS[TALLY_BY_SHIFT[sid]]})
    return out


def crew_total():
    return len(cast.CREW_IDS) * len(cast.BEAT_AT) + len(cast.TALLY_BEATS)


def counts(cured, cures, tests, best):
    """(found, total) over the whole Record, without building the pages."""
    done_notes = sum(1 for shifts in NOTE_SHIFTS if all(best.get(s) for s in shifts))
    found = len(cured) + len(tests) + len(cures) + len(beats_told(best)) + len(tally_told(best)) + done_notes
    total = len(lx.COND_IDS) + len(lx.TEST_IDS) + len(lx.TX_IDS) + crew_total() + len(NOTE_SHIFTS)
    return found, total


def crew_told(best):
    return len(beats_told(best)) + len(tally_told(best))


def view(cured, cures, tests, best):
    told = Counter(c for c, _k in beats_told(best))
    told_k = {c: sorted(k for cc, k in beats_told(best) if cc == c) for c in cast.CREW_IDS}
    sections = []
    entries = []
    for cid in lx.COND_IDS:
        c = lx.COND[cid]
        got = cid in cured
        lines = []
        if got:
            lines = ["Signs: " + ", ".join(lx.SIGN_NAME[s] for s in lx.SIGN_IDS if s in c["signs"]),
                     "Scans: " + ("; ".join(lx.TEST_BY_ID[t]["name"] + " " + lx.TEST_BY_ID[t]["positive"] for t in lx.TEST_IDS if t in c["findings"]) or "none read positive"),
                     "Cured by: " + " or ".join(lx.TX_BY_ID[t]["name"] for t in c["cures"]) + ". Only eased by: " + lx.TX_BY_ID[c["ease"]]["name"] + ".",
                     "Spreads: " + ("yes, treat it in the cold room." if c["spreads"] else "no.")]
        entries.append({"id": cid, "title": c["name"] if got else "Not filed yet", "text": c["blurb"] if got else "Cure this condition once to file it.", "lines": lines, "unlocked": got})
    sections.append(("conditions", entries))
    entries = []
    for tid in lx.TEST_IDS:
        t = lx.TEST_BY_ID[tid]
        got = tid in tests
        entries.append({"id": tid, "title": t["name"] if got else "Not filed yet", "text": t["blurb"] if got else "Run this scan once to file it.",
                        "lines": ["Uses: " + lx.ITEM_NAME[t["item"]].lower() + ". Positive: it " + t["positive"] + "."] if got else [], "unlocked": got})
    sections.append(("scans", entries))
    entries = []
    for tid in lx.TX_IDS:
        t = lx.TX_BY_ID[tid]
        got = tid in cures
        tags = ("Tags: " + ", ".join(sorted(t["tags"])) + ".") if t["tags"] else "Tags: none."
        entries.append({"id": tid, "title": t["name"] if got else "Not filed yet", "text": t["blurb"] if got else "Cure something with this treatment once to file it.",
                        "lines": ["Uses: " + lx.ITEM_NAME[t["item"]].lower() + ". " + tags] if got else [], "unlocked": got})
    sections.append(("treatments", entries))
    entries = []
    for cid in cast.CREW_IDS:
        m = cast.CREW_BY_ID[cid]
        have = told_k[cid]
        entries.append({"id": cid, "title": "%s, %s" % (m["name"], m["role"]), "text": "%d of %d pages." % (len(have), len(cast.BEAT_AT)),
                        "lines": [cast.BEATS[cid][k] for k in have], "unlocked": bool(have)})
    tk = tally_told(best)
    entries.append({"id": "tally", "title": "Tally, second medic robot", "text": "%d of %d pages." % (len(tk), len(cast.TALLY_BEATS)),
                    "lines": [cast.TALLY_BEATS[k] for k in tk], "unlocked": bool(tk)})
    sections.append(("crew", entries))
    entries = []
    for i, shifts in enumerate(NOTE_SHIFTS):
        got = all(best.get(s) for s in shifts)
        entries.append({"id": "note-%d" % (i + 1), "title": ("Station note %d" % (i + 1)) if got else "Not written yet",
                        "text": cast.STATION_NOTES[i] if got else "Finish every shift of %s to write this one." % progress.CHAPTERS[i]["name"], "lines": [], "unlocked": got})
    sections.append(("notes", entries))
    out = []
    found = 0
    total = 0
    for (sid, name), (_s, ents) in zip(SECTIONS, sections):
        if sid == "crew":
            f = len(beats_told(best)) + len(tk)
            t = crew_total()
        else:
            f = sum(1 for e in ents if e["unlocked"])
            t = len(ents)
        found += f
        total += t
        out.append({"id": sid, "name": name, "found": f, "total": t, "entries": ents})
    return {"notice": info.NOTICE, "sections": out, "found": found, "total": total, "crew_told": sum(told.values()) + len(tk)}
