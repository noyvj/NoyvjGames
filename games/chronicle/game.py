"""Chronicle -- the engine's single entry point (the Signal / Lexis pattern).

app.js never reads engine objects: it sends one JSON string to `handle` and draws the JSON that comes back.
`get_state()` / `load_state()` are the shared save widget's contract (planning/SAVE-BUTTON-INTEGRATION.md).
There is no DOM, no network, no clock and no random state in here: a puzzle is a pure function of
(set, section, round) and progress is plain data, so everything is deterministic and testable under CPython.

Requests: {"action": ..., ...}. Actions
  boot                          the current view (starts a puzzle if there is none)
  choose_set {set}              switch set (the set picker)
  start {section, round?}       open a puzzle (default: the first unsolved round of that section)
  place {event, slot}           put a card in a slot (swaps with an unlocked card already there)
  unplace {slot}                return the card in a slot to the tray
  check                         grade a full timeline: right cards lock and are LEARNED; all right = solved
  show_answer                   reveal the order (nothing is learned from a reveal)
  next                          the next unsolved round in this section
  archive {set?}                the collectible archive (events, elsewhere, people, places, readings)
  entry {set?, id}              one found entry in full, with its claims and sources
  view_claim {set?, claim}      record that a claim's sources were opened; returns the claim with its sources
  info {set?}                   the About page data: legend, counts, every found claim with its sources
  report {set?, claim, reason, note}   build a report payload (UI only: NOTHING is sent anywhere)
  settings {hints?}             game-rule settings kept in the save
  mode {mode}                   switch between "timeline", "web" (cause web) and "myth" (myth or record)
  web_start {chapter, round?}   open a cause-web puzzle (default: the first round with a link still to find)
  web_link {from, to}           draw "from led to to": confirmed only if the set has that relation
  web_show                      reveal every link of this puzzle (nothing is learned from a reveal)
  web_next                      the next cause-web round that still has an undiscovered link
  myth_start {chapter, round?}  open a myth-or-record puzzle
  myth_sort {claim, bin}        put a claim in a bin (documented, disputed, traditional-but-doubtful) or clear it (bin null)
  myth_check                    grade a fully sorted puzzle: right claims lock and are added to the archive
  myth_show                     reveal the right bins (nothing is learned from a reveal)
  myth_next                     the next myth round
  ack                           the player has seen the introduction
  reset                         erase all progress
Every response: {"ok", "error", "view", "new" (achievements just earned), "dirty" (state changed)}.
"""

import json
from pathlib import Path

import achievements
import myth as mq
import puzzle as pz
import report
import web as wb
from setdata import SetError, event_key, format_date, load_set, year_of

SCHEMA = 2
MODES = ("timeline", "web", "myth")
MODE_LABELS = {"timeline": "Timeline", "web": "Cause web", "myth": "Myth or record"}
STRENGTH_LABELS = {"direct": ("Direct cause", "\u21d2"), "contributing": ("Contributing cause", "\u21e2")}
STRENGTH_MEANING = {
    "direct": "The sources treat this as the immediate trigger. Other causes still matter.",
    "contributing": "The sources name this as one factor among several, not the whole story.",
}
MAX_IDS = 2000
CONFIDENCE_LABELS = {
    "documented": ("Documented", "✔"),
    "disputed": ("Disputed", "≈"),
    "traditional-but-doubtful": ("Traditional but doubtful", "?"),
}

SETS = {}            # set id -> ChronicleSet (only validated sets are ever here)
SET_ORDER = []
LOAD_PROBLEMS = []   # human-readable problems from sets that failed validation
S = None             # progress state, see _blank_state()


# --------------------------------------------------------------------------
# Loading sets


def load_sets(root):
    """Load every set listed in <root>/index.json. A set that fails validation is skipped and reported."""
    global SETS, SET_ORDER, LOAD_PROBLEMS
    SETS, SET_ORDER, LOAD_PROBLEMS = {}, [], []
    root = Path(root)
    try:
        index = json.loads((root / "index.json").read_text(encoding="utf-8"))
        folders = [entry["folder"] for entry in index["sets"]]
    except (OSError, ValueError, KeyError, TypeError):
        LOAD_PROBLEMS.append("sets/index.json is missing or malformed")
        folders = []
    for folder in folders:
        try:
            cset = load_set(root / folder)
        except SetError as exc:
            LOAD_PROBLEMS.append("set %s: %s" % (folder, "; ".join(exc.problems[:3])))
            continue
        except (OSError, ValueError) as exc:
            LOAD_PROBLEMS.append("set %s: %s" % (folder, exc))
            continue
        if cset.id in SETS:
            LOAD_PROBLEMS.append("set %s: duplicate id %s" % (folder, cset.id))
            continue
        SETS[cset.id] = cset
        SET_ORDER.append(cset.id)
    reset_engine()


def register_set(cset):
    """Add an already-validated set (tests)."""
    SETS[cset.id] = cset
    if cset.id not in SET_ORDER:
        SET_ORDER.append(cset.id)
    _ensure_progress(cset.id)


# --------------------------------------------------------------------------
# State


def _blank_state():
    return {"sets": {}, "unknown": {}, "viewed": set(), "settings": {"set": None, "hints": True, "mode": "timeline"},
            "flags": {"onboarded": False}, "session": None, "wsession": None, "msession": None, "earned": []}


def reset_engine():
    global S
    S = _blank_state()
    for set_id in SET_ORDER:
        _ensure_progress(set_id)


def _ensure_progress(set_id):
    return S["sets"].setdefault(set_id, {"learned": set(), "solved": {}, "revealed": set(), "threads": set(), "sorted": set(),
                                         "wsolved": {}, "msolved": {}})


def _prog(set_id):
    return _ensure_progress(set_id)


# ---- derived facts (the achievements module and the views both use these)


class _Helpers:
    @staticmethod
    def learned(set_id):
        return _prog(set_id)["learned"]

    @staticmethod
    def people_found(set_id):
        cset = SETS[set_id]
        return {p for e in _prog(set_id)["learned"] for p in cset.events[e].get("people", [])}

    @staticmethod
    def places_found(set_id):
        cset = SETS[set_id]
        return {cset.events[e]["place"] for e in _prog(set_id)["learned"] if cset.events[e].get("place")}

    @staticmethod
    def threads(set_id):
        return _prog(set_id)["threads"]

    @staticmethod
    def sorted_claims(set_id):
        return _prog(set_id)["sorted"]

    @staticmethod
    def web_records(set_id):
        return _prog(set_id)["wsolved"]

    @staticmethod
    def myth_records(set_id):
        return _prog(set_id)["msolved"]

    @staticmethod
    def percent(set_id):
        found, total = _counts(set_id)
        return 100 if found == total else (100 * found) // total

    @staticmethod
    def cleared(set_id, section_id):
        return _cleared(set_id, section_id)


HELP = _Helpers()


def _counts(set_id):
    cset = SETS[set_id]
    prog = _prog(set_id)
    rels, claims = set(cset.web_relation_ids()), set(cset.myth_claim_ids())
    found = (len(prog["learned"]) + len(HELP.people_found(set_id)) + len(HELP.places_found(set_id))
             + len(prog["threads"] & rels) + len(prog["sorted"] & claims))
    total = len(cset.events) + len(cset.people) + len(cset.places) + len(rels) + len(claims)
    return found, total


def _solves_in(set_id, section_id):
    prefix = section_id + ":"
    return [k for k in _prog(set_id)["solved"] if k.startswith(prefix)]


def _cleared(set_id, section_id):
    cset = SETS[set_id]
    section = cset.section(section_id)
    rule = section["clear"]
    if rule["type"] == "solves":
        return len(_solves_in(set_id, section_id)) >= rule["n"]
    learned = _prog(set_id)["learned"]
    return all(e in learned for e in cset.section_pool(section_id))


def _unlocked(set_id, section_id):
    section = SETS[set_id].section(section_id)
    return all(_cleared(set_id, r) for r in section.get("requires", []))


def _next_round(set_id, section_id):
    solved = _prog(set_id)["solved"]
    r = 0
    while "%s:%d" % (section_id, r) in solved:
        r += 1
    return r


def _cur_set():
    wanted = S["settings"].get("set")
    if wanted in SETS:
        return SETS[wanted]
    return SETS[SET_ORDER[0]] if SET_ORDER else None


# --------------------------------------------------------------------------
# Claims, sources and views


def _claim_view(cset, claim):
    label, symbol = CONFIDENCE_LABELS[claim["confidence"]]
    out = {
        "id": claim["id"], "set": cset.id, "subject": claim["subject"], "field": claim["field"], "text": claim["text"],
        "confidence": claim["confidence"], "confidence_label": label, "symbol": symbol,
        "alternatives": list(claim.get("alternatives", [])),
        "sources": cset.resolved_sources(claim),
        "institutions": sorted({s["institution"] for s in cset.resolved_sources(claim)}),
        "viewed": ("%s/%s" % (cset.id, claim["id"])) in S["viewed"],
    }
    if claim.get("short"):
        out["short"] = claim["short"]
    if claim["field"] == "date":
        out["value_label"] = format_date(claim["value"])
    return out


def _event_card(cset, event_id):
    e = cset.events[event_id]
    return {"id": event_id, "title": e["title"], "kind": e["kind"]}


def _event_full(cset, event_id):
    e = cset.events[event_id]
    claim = cset.date_claim(event_id)
    place = cset.places.get(e.get("place")) if e.get("place") else None
    return {
        "id": event_id, "title": e["title"], "kind": e["kind"], "date": event_start_text(e),
        "date_label": format_date(event_start_text(e)), "region": e.get("region"),
        "place": place["name"] if place else None,
        "people": [cset.people[p]["name"] for p in e.get("people", [])],
        "claim": _claim_view(cset, claim),
        "other_claims": [_claim_view(cset, c) for c in cset.claims_for(event_id) if c["field"] not in ("date", "relation")],
    }


def event_start_text(event):
    if event.get("date"):
        return event["date"]
    return "%s/%s" % (event["start"], event["end"])


# ---- sections


def _section_views(cset):
    out = []
    prog = _prog(cset.id)
    for s in cset.sections:
        pool = cset.section_pool(s["id"])
        unlocked = _unlocked(cset.id, s["id"])
        cleared = _cleared(cset.id, s["id"])
        rule = s["clear"]
        if rule["type"] == "solves":
            have, need = min(len(_solves_in(cset.id, s["id"])), rule["n"]), rule["n"]
            progress = "Solved %d of %d puzzles" % (have, need)
        else:
            have = sum(1 for e in pool if e in prog["learned"])
            need = len(pool)
            progress = "Found %d of %d moments" % (have, need)
        out.append({
            "id": s["id"], "title": s["title"], "blurb": s["blurb"], "difficulty": s["difficulty"], "size": s["size"],
            "unlocked": unlocked, "cleared": cleared, "progress": progress, "have": have, "need": need,
            "requires": [cset.section(r)["title"] for r in s.get("requires", [])],
            "next_round": _next_round(cset.id, s["id"]), "main_rounds": pz.main_rounds(cset, s["id"]),
        })
    return out


# ---- puzzle session


def _make_puzzle(sess):
    cset = SETS[sess["set"]]
    return cset, pz.make_puzzle(cset, sess["section"], sess["round"])


def _start(set_id, section_id, round_no):
    cset = SETS[set_id]
    puz = pz.make_puzzle(cset, section_id, round_no)
    S["session"] = {"set": set_id, "section": section_id, "round": round_no, "placement": [None] * puz.size,
                    "locked": [False] * puz.size, "marks": [None] * puz.size, "checks": 0, "status": "playing",
                    "new": [], "message": ""}
    return S["session"]


def _default_start(cset):
    """First unlocked, not-yet-cleared section; its first unsolved round."""
    chosen = None
    for s in cset.sections:
        if _unlocked(cset.id, s["id"]):
            chosen = s["id"]
            if not _cleared(cset.id, s["id"]):
                break
    return _start(cset.id, chosen, _next_round(cset.id, chosen))


def _ensure_session():
    sess = S["session"]
    if sess is not None and sess["set"] in SETS:
        cset = SETS[sess["set"]]
        if cset.section(sess["section"]) is not None:
            return sess
    cset = _cur_set()
    if cset is None:
        return None
    S["settings"]["set"] = cset.id
    return _default_start(cset)


def _puzzle_view(sess):
    cset, puz = _make_puzzle(sess)
    section = cset.section(sess["section"])
    slots = []
    for i in range(puz.size):
        card = sess["placement"][i]
        locked = sess["locked"][i]
        mark = sess["marks"][i]
        slots.append({"index": i, "card": card, "locked": locked,
                      "status": "right" if locked else ("wrong" if mark else None),
                      "direction": mark if mark in ("earlier", "later") else None})
    tray = [c for c in puz.tray if c not in sess["placement"]]
    main = pz.main_rounds(cset, sess["section"])
    label = ("Puzzle %d of %d" % (sess["round"] + 1, main)) if sess["round"] < main else ("Practice puzzle %d" % (sess["round"] - main + 1))
    return {
        "id": puz.code, "section": sess["section"], "section_title": section["title"], "difficulty": section["difficulty"],
        "round": sess["round"], "round_label": label, "size": puz.size, "status": sess["status"], "checks": sess["checks"],
        "message": sess["message"], "cards": {c: _event_card(cset, c) for c in puz.tray}, "slots": slots, "tray": tray,
        "all_placed": all(c is not None for c in sess["placement"]), "hints": bool(S["settings"]["hints"]),
        "min_gap_years": section["min_gap_years"],
    }


def _result_view(sess):
    """After a puzzle is finished: the order with dates, claims and sources, and the nuance strip."""
    if sess["status"] not in ("solved", "revealed"):
        return None
    cset, puz = _make_puzzle(sess)
    reveal = []
    for event_id in puz.answer:
        full = _event_full(cset, event_id)
        full["new"] = event_id in sess["new"]
        reveal.append(full)
    strip = []
    for n in pz.nuance(cset, puz):
        full = _event_full(cset, n["event"])
        full["near"] = cset.events[n["near"]]["title"]
        full["years"] = n["years"]
        strip.append(full)
    cleared_now = sess["status"] == "solved" and _cleared(cset.id, sess["section"])
    readings = [r for r in cset.readings if r["section"] == sess["section"]] if cleared_now else []
    years = [year_of(cset.events[e]) for e in puz.answer]
    return {"reveal": reveal, "nuance": strip, "span": [min(years), max(years)], "solved": sess["status"] == "solved",
            "section_cleared": cleared_now, "readings": [_reading_view(cset, r) for r in readings],
            "new_count": len(sess["new"])}


def _reading_view(cset, reading):
    return {"id": reading["id"], "title": reading["title"], "text": reading["text"], "section": reading["section"],
            "claims": [_claim_view(cset, cset.claims[c]) for c in reading["claims"]]}


# ---- the cause web: chapters, session, views


def _web_unlocked(set_id, ch):
    learned = _prog(set_id)["learned"]
    return all(e in learned for e in ch["events"])


def _web_cleared(set_id, ch):
    cset = SETS[set_id]
    return all(r in _prog(set_id)["threads"] for r in cset.chapter_relations(ch))


def _web_next_round(set_id, ch):
    solved = _prog(set_id)["wsolved"]
    r = 0
    while "%s:%d" % (ch["id"], r) in solved:
        r += 1
    return r


def _web_chapter_views(cset):
    out = []
    prog = _prog(cset.id)
    for ch in cset.web_chapters:
        rels = cset.chapter_relations(ch)
        have = sum(1 for r in rels if r in prog["threads"])
        missing = sum(1 for e in ch["events"] if e not in prog["learned"])
        out.append({
            "id": ch["id"], "title": ch["title"], "blurb": ch["blurb"], "size": ch["size"], "difficulty": None,
            "unlocked": missing == 0, "cleared": have == len(rels), "have": have, "need": len(rels),
            "progress": "Found %d of %d links" % (have, len(rels)),
            "missing": missing,
            "requires_text": "Find %d more moment%s in the timeline first" % (missing, "" if missing == 1 else "s"),
            "next_round": _web_next_round(cset.id, ch), "main_rounds": wb.main_rounds(cset, ch["id"]),
        })
    return out


def _wstart(set_id, chapter_id, round_no):
    cset = SETS[set_id]
    puz = wb.make_web_puzzle(cset, chapter_id, round_no)
    S["wsession"] = {"set": set_id, "chapter": chapter_id, "round": round_no, "found": [], "tries": [], "misses": 0,
                     "status": "playing", "message": ""}
    return puz


def _wdefault(cset):
    chosen = None
    for ch in cset.web_chapters:
        if _web_unlocked(cset.id, ch):
            chosen = ch
            if not _web_cleared(cset.id, ch):
                break
    if chosen is None:
        return None
    _wstart(cset.id, chosen["id"], _web_next_round(cset.id, chosen))
    return S["wsession"]


def _ensure_wsession():
    sess = S["wsession"]
    cset = _cur_set()
    if cset is None or not cset.web_chapters:
        return None
    if sess is not None and sess["set"] == cset.id:
        ch = cset.web_chapter(sess["chapter"])
        if ch is not None and _web_unlocked(cset.id, ch):
            return sess
    S["wsession"] = None
    return _wdefault(cset)


def _wpuzzle(sess):
    cset = SETS[sess["set"]]
    return cset, wb.make_web_puzzle(cset, sess["chapter"], sess["round"])


def _thread_view(cset, rid):
    r = cset.relation_by_id[rid]
    label, symbol = STRENGTH_LABELS[r["strength"]]
    n = len(cset.causes_of(r["to"]))
    if n > 1:
        plural = "One of %d causes of this moment that the set records." % n
    else:
        plural = "The only cause of this moment that the set records. Causes are plural: the sources name others that are not cards here."
    return {
        "relation": rid, "from": r["from"], "to": r["to"], "from_title": cset.events[r["from"]]["title"],
        "to_title": cset.events[r["to"]]["title"], "strength": r["strength"], "strength_label": label, "strength_symbol": symbol,
        "strength_note": STRENGTH_MEANING[r["strength"]], "plural_note": plural, "n_causes": n,
        "claim": _claim_view(cset, cset.claims[r["claim"]]),
    }


def _web_view(sess):
    cset, puz = _wpuzzle(sess)
    ch = cset.web_chapter(sess["chapter"])
    main = wb.main_rounds(cset, sess["chapter"])
    label = ("Puzzle %d of %d" % (sess["round"] + 1, main)) if sess["round"] < main else ("Practice puzzle %d" % (sess["round"] - main + 1))
    cards = [{"id": e, "title": cset.events[e]["title"], "n": i + 1} for i, e in enumerate(puz.cards)]
    found = [_thread_view(cset, r) for r in puz.relations if r in sess["found"]]
    tries = []
    for t in sess["tries"]:
        tries.append({"from": t["from"], "to": t["to"], "from_title": cset.events[t["from"]]["title"],
                      "to_title": cset.events[t["to"]]["title"], "verdict": t["verdict"]})
    finished = sess["status"] != "playing"
    result = None
    if finished:
        result = {"solved": sess["status"] == "solved", "threads": [_thread_view(cset, r) for r in puz.relations],
                  "chapter_cleared": sess["status"] == "solved" and _web_cleared(cset.id, ch)}
    return {
        "id": puz.code, "chapter": sess["chapter"], "chapter_title": ch["title"], "round": sess["round"], "round_label": label,
        "size": puz.size, "status": sess["status"], "message": sess["message"], "misses": sess["misses"], "cards": cards,
        "found": found, "tries": tries, "links_total": len(puz.relations), "links_found": len(sess["found"]), "result": result,
    }


# ---- myth or record: chapters, session, views


def _myth_unlocked(set_id, ch):
    cset = SETS[set_id]
    learned = _prog(set_id)["learned"]
    return all(cset.claims[c]["subject"] in learned for c in ch["claims"])


def _myth_cleared(set_id, ch):
    return all(c in _prog(set_id)["sorted"] for c in ch["claims"])


def _myth_next_round(set_id, ch):
    solved = _prog(set_id)["msolved"]
    r = 0
    while "%s:%d" % (ch["id"], r) in solved:
        r += 1
    return r


def _myth_chapter_views(cset):
    out = []
    prog = _prog(cset.id)
    for ch in cset.myth_chapters:
        have = sum(1 for c in ch["claims"] if c in prog["sorted"])
        missing = len({cset.claims[c]["subject"] for c in ch["claims"] if cset.claims[c]["subject"] not in prog["learned"]})
        out.append({
            "id": ch["id"], "title": ch["title"], "blurb": ch["blurb"], "size": ch["size"], "difficulty": None,
            "unlocked": missing == 0, "cleared": have == len(ch["claims"]), "have": have, "need": len(ch["claims"]),
            "progress": "Sorted %d of %d claims" % (have, len(ch["claims"])),
            "missing": missing,
            "requires_text": "Find %d more moment%s in the timeline first" % (missing, "" if missing == 1 else "s"),
            "next_round": _myth_next_round(cset.id, ch), "main_rounds": mq.main_rounds(cset, ch["id"]),
        })
    return out


def _mstart(set_id, chapter_id, round_no):
    cset = SETS[set_id]
    puz = mq.make_myth_puzzle(cset, chapter_id, round_no)
    n = puz.size
    S["msession"] = {"set": set_id, "chapter": chapter_id, "round": round_no, "bins": [None] * n, "locked": [False] * n,
                     "marks": [None] * n, "checks": 0, "status": "playing", "new": [], "message": ""}
    return puz


def _mdefault(cset):
    chosen = None
    for ch in cset.myth_chapters:
        if _myth_unlocked(cset.id, ch):
            chosen = ch
            if not _myth_cleared(cset.id, ch):
                break
    if chosen is None:
        return None
    _mstart(cset.id, chosen["id"], _myth_next_round(cset.id, chosen))
    return S["msession"]


def _ensure_msession():
    sess = S["msession"]
    cset = _cur_set()
    if cset is None or not cset.myth_chapters:
        return None
    if sess is not None and sess["set"] == cset.id:
        ch = cset.myth_chapter(sess["chapter"])
        if ch is not None and _myth_unlocked(cset.id, ch):
            return sess
    S["msession"] = None
    return _mdefault(cset)


def _mpuzzle(sess):
    cset = SETS[sess["set"]]
    return cset, mq.make_myth_puzzle(cset, sess["chapter"], sess["round"])


def _explanation(cset, claim):
    """A short reason for the claim's label, built only from the claim's own fields and its source notes."""
    notes = [ref.get("note", "") for ref in claim["sources"] if ref.get("note")]
    head = {
        "documented": "Record: the sources agree.",
        "disputed": "Disputed: reputable sources differ, and the game does not pick a side.",
        "traditional-but-doubtful": "Traditional but doubtful: the sources do not support this story.",
    }[claim["confidence"]]
    return " ".join([head] + notes[:2])


def _myth_view(sess):
    cset, puz = _mpuzzle(sess)
    ch = cset.myth_chapter(sess["chapter"])
    main = mq.main_rounds(cset, sess["chapter"])
    label = ("Puzzle %d of %d" % (sess["round"] + 1, main)) if sess["round"] < main else ("Practice puzzle %d" % (sess["round"] - main + 1))
    finished = sess["status"] != "playing"
    claims = []
    for i, cid in enumerate(puz.tray):
        c = cset.claims[cid]
        claims.append({"id": cid, "index": i, "text": c["text"], "subject_title": cset.events[c["subject"]]["title"],
                       "bin": sess["bins"][i], "locked": sess["locked"][i],
                       "status": "right" if sess["locked"][i] else ("wrong" if sess["marks"][i] else None)})
    result = None
    if finished:
        rows = []
        for i, cid in enumerate(puz.tray):
            c = cset.claims[cid]
            view = _claim_view(cset, c)
            view["explanation"] = _explanation(cset, c)
            view["new"] = cid in sess["new"]
            rows.append(view)
        result = {"solved": sess["status"] == "solved", "claims": rows, "new_count": len(sess["new"]),
                  "chapter_cleared": sess["status"] == "solved" and _myth_cleared(cset.id, ch)}
    return {
        "id": puz.code, "chapter": sess["chapter"], "chapter_title": ch["title"], "round": sess["round"], "round_label": label,
        "size": puz.size, "status": sess["status"], "message": sess["message"], "checks": sess["checks"], "claims": claims,
        "bins": [{"id": b, "label": CONFIDENCE_LABELS[b][0], "symbol": CONFIDENCE_LABELS[b][1], "meaning": _LEGEND[b]} for b in mq.BINS],
        "all_sorted": all(b is not None for b in sess["bins"]), "result": result,
    }


# ---- the whole view


def _picker():
    out = []
    for set_id in SET_ORDER:
        cset = SETS[set_id]
        found, total = _counts(set_id)
        out.append({"id": set_id, "title": cset.title, "status": cset.status, "status_label": cset.status_label,
                    "description": cset.meta.get("description", ""), "found": found, "total": total,
                    "percent": HELP.percent(set_id)})
    return out


def _view():
    sess = _ensure_session()
    if sess is None:
        return {"game": "chronicle", "empty": True, "problems": list(LOAD_PROBLEMS), "sets": [], "settings": _settings_view()}
    cset = SETS[sess["set"]]
    found, total = _counts(cset.id)
    return {
        "game": "chronicle", "empty": False, "problems": list(LOAD_PROBLEMS), "sets": _picker(),
        "set": {"id": cset.id, "title": cset.title, "status": cset.status, "status_label": cset.status_label,
                "draft": cset.status != "reviewed", "description": cset.meta.get("description", ""),
                "found": found, "total": total, "percent": HELP.percent(cset.id), "version": cset.version},
        "sections": _section_views(cset), "puzzle": _puzzle_view(sess), "result": _result_view(sess),
        "settings": _settings_view(), "first_run": not S["flags"]["onboarded"],
        "achievements_earned": _earned_now(),
        "mode": _mode(cset), "modes": _modes_view(cset), "webs": _web_chapter_views(cset), "myths": _myth_chapter_views(cset),
        "web": _web_board(cset), "myth": _myth_board(cset),
    }


def _settings_view():
    return {"hints": bool(S["settings"]["hints"]), "set": S["settings"].get("set"), "mode": S["settings"].get("mode", "timeline")}


def _mode(cset):
    """The mode being played; a set without that mechanic falls back to the timeline."""
    mode = S["settings"].get("mode", "timeline")
    if mode == "web" and not cset.web_chapters:
        return "timeline"
    if mode == "myth" and not cset.myth_chapters:
        return "timeline"
    return mode if mode in MODES else "timeline"


def _modes_view(cset):
    return [
        {"id": "timeline", "label": MODE_LABELS["timeline"], "available": True},
        {"id": "web", "label": MODE_LABELS["web"], "available": bool(cset.web_chapters)},
        {"id": "myth", "label": MODE_LABELS["myth"], "available": bool(cset.myth_chapters)},
    ]


def _web_board(cset):
    if _mode(cset) != "web":
        return None
    sess = _ensure_wsession()
    if sess is None:
        return {"locked": True, "message": "Find more moments in the timeline to open a cause web chapter."}
    return _web_view(sess)


def _myth_board(cset):
    if _mode(cset) != "myth":
        return None
    sess = _ensure_msession()
    if sess is None:
        return {"locked": True, "message": "Find more moments in the timeline to open a myth-or-record chapter."}
    return _myth_view(sess)


def _earned_now():
    return achievements.earned(S, SETS, HELP)


# --------------------------------------------------------------------------
# Actions


class _Bad(Exception):
    pass


def _int(req, key):
    v = req.get(key)
    if isinstance(v, bool) or not isinstance(v, int):
        raise _Bad("%s must be a whole number" % key)
    return v


def _str(req, key):
    v = req.get(key)
    if not isinstance(v, str) or not v:
        raise _Bad("%s is required" % key)
    return v


def _set_for(req):
    set_id = req.get("set") or S["settings"].get("set")
    if set_id not in SETS:
        raise _Bad("Unknown set.")
    return SETS[set_id]


def _playing():
    sess = _ensure_session()
    if sess is None:
        raise _Bad("No set is loaded.")
    return sess


def _clear_marks_for(sess, *slots):
    for i in slots:
        if 0 <= i < len(sess["marks"]):
            sess["marks"][i] = None


def _act_start(req):
    cset = _set_for(req)
    section_id = _str(req, "section")
    if cset.section(section_id) is None:
        raise _Bad("Unknown section.")
    if not _unlocked(cset.id, section_id):
        raise _Bad("That section is still locked.")
    round_no = _int(req, "round") if "round" in req and req["round"] is not None else _next_round(cset.id, section_id)
    if round_no < 0 or round_no > 10000:
        raise _Bad("That puzzle does not exist.")
    S["settings"]["set"] = cset.id
    _start(cset.id, section_id, round_no)
    return True


def _act_choose_set(req):
    cset = _set_for({"set": _str(req, "set")})
    S["settings"]["set"] = cset.id
    S["session"] = None
    S["wsession"] = None
    S["msession"] = None
    _default_start(cset)
    return True


def _act_place(req):
    sess = _playing()
    if sess["status"] != "playing":
        raise _Bad("This puzzle is finished. Press Next puzzle.")
    cset, puz = _make_puzzle(sess)
    event_id, slot = _str(req, "event"), _int(req, "slot")
    if event_id not in puz.tray:
        raise _Bad("That card is not in this puzzle.")
    if not 0 <= slot < puz.size:
        raise _Bad("That slot does not exist.")
    place = sess["placement"]
    here = place.index(event_id) if event_id in place else None
    if here is not None and sess["locked"][here]:
        raise _Bad("That card is already in its right place.")
    if sess["locked"][slot]:
        raise _Bad("That slot is already filled with the right card.")
    if here == slot:
        return False
    other = place[slot]
    place[slot] = event_id
    if here is not None:
        place[here] = other           # swap (other may be None: the old slot just empties)
    sess["marks"][slot] = None
    _clear_marks_for(sess, here if here is not None else -1)
    sess["message"] = ""
    return True


def _act_unplace(req):
    sess = _playing()
    if sess["status"] != "playing":
        raise _Bad("This puzzle is finished.")
    slot = _int(req, "slot")
    if not 0 <= slot < len(sess["placement"]):
        raise _Bad("That slot does not exist.")
    if sess["locked"][slot]:
        raise _Bad("That card is locked in its right place.")
    if sess["placement"][slot] is None:
        return False
    sess["placement"][slot] = None
    sess["marks"][slot] = None
    sess["message"] = ""
    return True


def _act_check(_req):
    sess = _playing()
    if sess["status"] != "playing":
        raise _Bad("This puzzle is finished.")
    cset, puz = _make_puzzle(sess)
    if any(c is None for c in sess["placement"]):
        raise _Bad("Place all %d cards before checking." % puz.size)
    result = pz.grade(puz, sess["placement"])
    prog = _prog(cset.id)
    sess["checks"] += 1
    for slot in result["slots"]:
        i = slot["index"]
        if slot["status"] == "right":
            sess["locked"][i] = True
            sess["marks"][i] = None
            if slot["event"] not in prog["learned"]:
                prog["learned"].add(slot["event"])
                sess["new"].append(slot["event"])
        else:
            sess["marks"][i] = slot["direction"] or "wrong"
    if result["all_right"]:
        sess["status"] = "solved"
        key = "%s:%d" % (sess["section"], sess["round"])
        old = prog["solved"].get(key)
        if old is None or sess["checks"] < old["checks"]:
            prog["solved"][key] = {"checks": sess["checks"]}
        for n in pz.nuance(cset, puz):          # the nuance strip counts as seen once the puzzle is solved
            if n["event"] not in prog["learned"]:
                prog["learned"].add(n["event"])
                sess["new"].append(n["event"])
        sess["message"] = ("Solved in one check." if sess["checks"] == 1 else "Solved in %d checks." % sess["checks"])
    else:
        sess["message"] = "%d of %d cards are in the right place and locked." % (result["right"], puz.size)
    return True


def _act_show_answer(_req):
    sess = _playing()
    if sess["status"] != "playing":
        raise _Bad("This puzzle is finished.")
    _cset, puz = _make_puzzle(sess)
    sess["placement"] = list(puz.answer)
    sess["locked"] = [True] * puz.size
    sess["marks"] = [None] * puz.size
    sess["status"] = "revealed"
    _prog(sess["set"])["revealed"].add("%s:%d" % (sess["section"], sess["round"]))
    sess["message"] = "Answer shown. Nothing was added to your archive from this puzzle."
    return True


def _act_next(_req):
    sess = _playing()
    cset = SETS[sess["set"]]
    solved = _prog(cset.id)["solved"]
    r = sess["round"] + 1
    while "%s:%d" % (sess["section"], r) in solved:
        r += 1
    _start(cset.id, sess["section"], r)
    return True


def _claim_allowed(cset, claim):
    prog = _prog(cset.id)
    if claim["field"] == "relation":
        rid = next((r["id"] for r in cset.relations if r["claim"] == claim["id"]), None)
        if rid is None:
            return False
        if rid in prog["threads"]:
            return True
        ws = S["wsession"]
        if ws and ws["set"] == cset.id and ws["status"] in ("solved", "revealed"):
            _c, wpuz = _wpuzzle(ws)
            return rid in wpuz.relations
        return False
    subject = claim["subject"]
    if subject in prog["learned"]:
        return True
    sess = S["session"]
    if sess and sess["set"] == cset.id and sess["status"] in ("solved", "revealed"):
        _c, puz = _make_puzzle(sess)
        return subject in puz.answer
    return False


def _act_view_claim(req, out):
    cset = _set_for(req)
    claim = cset.claims.get(_str(req, "claim"))
    if claim is None or not _claim_allowed(cset, claim):
        raise _Bad("You have not found that yet.")
    key = "%s/%s" % (cset.id, claim["id"])
    changed = key not in S["viewed"]
    if changed:
        S["viewed"].add(key)
    out["claim"] = _claim_view(cset, claim)
    return changed


def _archive(cset):
    prog = _prog(cset.id)
    learned = prog["learned"]
    people, places = HELP.people_found(cset.id), HELP.places_found(cset.id)

    def event_entry(event_id, hint):
        e = cset.events[event_id]
        if event_id in learned:
            return {"id": event_id, "kind": e["kind"], "found": True, "title": e["title"],
                    "date_label": format_date(event_start_text(e)), "hint": hint}
        return {"id": event_id, "kind": e["kind"], "found": False, "title": None, "date_label": None, "hint": hint}

    section_title = {s["id"]: s["title"] for s in cset.sections}
    events = [event_entry(i, section_title.get(cset.events[i].get("section"), "")) for i in cset.event_ids("event")]
    elsewhere = [event_entry(i, "Elsewhere") for i in cset.event_ids("context")]

    def appears(person_or_place, key):
        return [cset.events[i]["title"] for i in cset.event_order if i in learned and
                (person_or_place in cset.events[i].get("people", []) if key == "people" else cset.events[i].get("place") == person_or_place)]

    pe = [{"id": p, "kind": "person", "found": p in people, "title": cset.people[p]["name"] if p in people else None,
           "date_label": None, "hint": "Person", "appears_in": appears(p, "people") if p in people else []} for p in cset.people]
    pl = [{"id": p, "kind": "place", "found": p in places, "title": cset.places[p]["name"] if p in places else None,
           "date_label": None, "hint": "Place", "appears_in": appears(p, "places") if p in places else []} for p in cset.places]
    readings = []
    for r in cset.readings:
        if _cleared(cset.id, r["section"]):
            readings.append(_reading_view(cset, r))
    found, total = _counts(cset.id)
    groups = [
        {"id": "events", "title": "Moments", "entries": events},
        {"id": "elsewhere", "title": "Elsewhere in the world", "entries": elsewhere},
        {"id": "people", "title": "People", "entries": pe},
        {"id": "places", "title": "Places", "entries": pl},
    ]
    rel_ids = cset.web_relation_ids()
    if rel_ids:
        threads = []
        for rid in rel_ids:
            r = cset.relation_by_id[rid]
            if rid in prog["threads"]:
                label = STRENGTH_LABELS[r["strength"]][0]
                threads.append({"id": rid, "kind": "relation", "found": True,
                                "title": "%s led to %s" % (cset.events[r["from"]]["title"], cset.events[r["to"]]["title"]),
                                "date_label": label, "hint": "Cause web"})
            else:
                threads.append({"id": rid, "kind": "relation", "found": False, "title": None, "date_label": None, "hint": "Cause web"})
        groups.append({"id": "connections", "title": "Connections", "entries": threads})
    claim_ids = cset.myth_claim_ids()
    if claim_ids:
        records = []
        for cid in claim_ids:
            c = cset.claims[cid]
            if cid in prog["sorted"]:
                records.append({"id": cid, "kind": "record", "found": True, "title": c.get("short") or c["text"],
                                "date_label": CONFIDENCE_LABELS[c["confidence"]][1] + " " + CONFIDENCE_LABELS[c["confidence"]][0], "hint": "Myth or record"})
            else:
                records.append({"id": cid, "kind": "record", "found": False, "title": None, "date_label": None, "hint": "Myth or record"})
        groups.append({"id": "records", "title": "Records and myths", "entries": records})
    return {"set": cset.id, "title": cset.title, "found": found, "total": total, "percent": HELP.percent(cset.id),
            "groups": groups, "readings": readings, "locked_readings": len(cset.readings) - len(readings)}


def _act_entry(req, out):
    cset = _set_for(req)
    entry_id = _str(req, "id")
    learned = _prog(cset.id)["learned"]
    if entry_id in cset.events:
        if entry_id not in learned:
            raise _Bad("You have not found that yet.")
        out["entry"] = _event_full(cset, entry_id)
        return False
    if entry_id in cset.people or entry_id in cset.places:
        found = HELP.people_found(cset.id) if entry_id in cset.people else HELP.places_found(cset.id)
        if entry_id not in found:
            raise _Bad("You have not found that yet.")
        key = "people" if entry_id in cset.people else "place"
        out["entry"] = {
            "id": entry_id, "kind": "person" if key == "people" else "place",
            "title": (cset.people if key == "people" else cset.places)[entry_id]["name"],
            "events": [_event_full(cset, i) for i in cset.event_order if i in learned and
                       (entry_id in cset.events[i].get("people", []) if key == "people" else cset.events[i].get("place") == entry_id)],
        }
        return False
    if entry_id in cset.relation_by_id and entry_id in cset.web_relation_ids():
        if entry_id not in _prog(cset.id)["threads"]:
            raise _Bad("You have not found that yet.")
        view = _thread_view(cset, entry_id)
        out["entry"] = {"id": entry_id, "kind": "relation", "title": "%s led to %s" % (view["from_title"], view["to_title"]), "thread": view}
        return False
    if entry_id in cset.claims and entry_id in cset.myth_claim_ids():
        if entry_id not in _prog(cset.id)["sorted"]:
            raise _Bad("You have not found that yet.")
        claim = cset.claims[entry_id]
        view = _claim_view(cset, claim)
        view["explanation"] = _explanation(cset, claim)
        out["entry"] = {"id": entry_id, "kind": "record", "title": claim.get("short") or claim["text"], "claim": view}
        return False
    raise _Bad("No such entry.")


def _act_info(req, out):
    cset = _set_for(req)
    learned = _prog(cset.id)["learned"]
    claims = []
    for event_id in cset.event_order:
        if event_id in learned:
            full = _event_full(cset, event_id)
            claims.append({"event": event_id, "title": full["title"], "date_label": full["date_label"],
                           "claims": [full["claim"]] + full["other_claims"]})
    nsources = len({ref["source"] for c in cset.claims.values() for ref in c["sources"]})
    threads = [_thread_view(cset, r["id"]) for r in cset.relations if r["id"] in _prog(cset.id)["threads"] and r["id"] in cset.web_relation_ids()]
    shown = sum(len(c["claims"]) for c in claims) + len(threads)
    levels = {k: sum(1 for c in cset.claims.values() if c["confidence"] == k) for k in CONFIDENCE_LABELS}
    out["info"] = {
        "set": {"id": cset.id, "title": cset.title, "status": cset.status, "status_label": cset.status_label,
                "draft": cset.status != "reviewed", "version": cset.version, "drafted": cset.meta.get("drafted")},
        "legend": [{"id": k, "label": v[0], "symbol": v[1], "meaning": _LEGEND[k]} for k, v in CONFIDENCE_LABELS.items()],
        "counts": {"claims": len(cset.claims), "sources": nsources, "events": len(cset.events), "relations": len(cset.relations),
                   "levels": levels},
        "coverage": {"shown": shown, "total": len(cset.claims),
                     "note": "Every claim in a set links at least three sources. You see %d of %d claims now; the rest appear as you find them." % (shown, len(cset.claims))},
        "strengths": [{"id": k, "label": v[0], "symbol": v[1], "meaning": STRENGTH_MEANING[k]} for k, v in STRENGTH_LABELS.items()],
        "found_claims": claims,
        "found_relations": threads,
        "reasons": [{"id": i, "label": l} for i, l in report.REASONS],
    }
    return False


_LEGEND = {
    "documented": "Sources agree and the claim is well established.",
    "disputed": "Reputable sources differ. The game shows the competing positions and never picks one for you.",
    "traditional-but-doubtful": "A popular story the sources do not support. It is shown so you can recognise it.",
}


def _act_report(req, out):
    cset = _set_for(req)
    payload, error = report.build(cset, req.get("claim"), req.get("reason"), req.get("note"))
    if error:
        raise _Bad(error)
    out["report"] = payload
    out["sent"] = False
    out["notice"] = "Reporting opens soon. Nothing was sent; this report is saved on this device only."
    return False


def _act_settings(req):
    changed = False
    if "hints" in req:
        if not isinstance(req["hints"], bool):
            raise _Bad("hints must be true or false")
        changed = S["settings"]["hints"] != req["hints"]
        S["settings"]["hints"] = req["hints"]
    return changed


def _act_ack(_req):
    changed = not S["flags"]["onboarded"]
    S["flags"]["onboarded"] = True
    return changed


def _act_reset(_req):
    reset_engine()
    return True


# ---- the new mechanics: mode, cause web, myth or record


def _act_mode(req):
    mode = req.get("mode")
    if mode not in MODES:
        raise _Bad("Unknown mode.")
    cset = _cur_set()
    if cset is None:
        raise _Bad("No set is loaded.")
    if mode == "web" and not cset.web_chapters:
        raise _Bad("This set has no cause web yet.")
    if mode == "myth" and not cset.myth_chapters:
        raise _Bad("This set has no myth-or-record chapter yet.")
    changed = S["settings"].get("mode") != mode
    S["settings"]["mode"] = mode
    return changed


def _chapter_arg(req, kind):
    cset = _set_for(req)
    chapter_id = _str(req, "chapter")
    ch = cset.web_chapter(chapter_id) if kind == "web" else cset.myth_chapter(chapter_id)
    if ch is None:
        raise _Bad("Unknown chapter.")
    unlocked = _web_unlocked(cset.id, ch) if kind == "web" else _myth_unlocked(cset.id, ch)
    if not unlocked:
        raise _Bad("That chapter is still locked.")
    round_no = _int(req, "round") if "round" in req and req["round"] is not None else (
        _web_next_round(cset.id, ch) if kind == "web" else _myth_next_round(cset.id, ch))
    if round_no < 0 or round_no > 10000:
        raise _Bad("That puzzle does not exist.")
    return cset, ch, round_no


def _act_web_start(req):
    cset, ch, round_no = _chapter_arg(req, "web")
    S["settings"]["set"] = cset.id
    S["settings"]["mode"] = "web"
    _wstart(cset.id, ch["id"], round_no)
    return True


def _wplaying():
    sess = _ensure_wsession()
    if sess is None:
        raise _Bad("No cause-web chapter is open yet.")
    return sess


def _act_web_link(req):
    sess = _wplaying()
    if sess["status"] != "playing":
        raise _Bad("This puzzle is finished. Press Next puzzle.")
    cset, puz = _wpuzzle(sess)
    cause, effect = _str(req, "from"), _str(req, "to")
    verdict = wb.judge(cset, puz, cause, effect)
    kind = verdict["verdict"]
    if kind == "invalid":
        raise _Bad("Pick two different cards from this puzzle.")
    prog = _prog(cset.id)
    a, b = cset.events[cause]["title"], cset.events[effect]["title"]
    if kind == "confirmed":
        rid = verdict["relation"]
        if rid in sess["found"]:
            sess["message"] = "You already drew that thread."
            return False
        sess["found"].append(rid)
        prog["threads"].add(rid)
        label = STRENGTH_LABELS[cset.relation_by_id[rid]["strength"]][0]
        sess["message"] = "Confirmed: %s led to %s. Evidence: %s." % (a, b, label.lower())
        if all(r in sess["found"] for r in puz.relations):
            sess["status"] = "solved"
            key = "%s:%d" % (sess["chapter"], sess["round"])
            old = prog["wsolved"].get(key)
            if old is None or sess["misses"] < old["misses"]:
                prog["wsolved"][key] = {"misses": sess["misses"]}
            sess["message"] += " Every link in this puzzle is found."
        return True
    sess["misses"] += 1
    sess["tries"] = (sess["tries"] + [{"from": cause, "to": effect, "verdict": kind}])[-30:]
    if kind == "reversed":
        sess["message"] = "Not that way round: the sources link %s and %s the other way." % (a, b)
    else:
        sess["message"] = "Not confirmed: none of this set's sources join %s to %s. That does not mean they are unrelated." % (a, b)
    return True


def _act_web_show(_req):
    sess = _wplaying()
    if sess["status"] != "playing":
        raise _Bad("This puzzle is finished.")
    sess["status"] = "revealed"
    sess["message"] = "Links shown. Nothing was added to your archive from this puzzle."
    return True


def _act_web_next(_req):
    sess = _wplaying()
    cset = SETS[sess["set"]]
    solved = _prog(cset.id)["wsolved"]
    r = sess["round"] + 1
    while "%s:%d" % (sess["chapter"], r) in solved:
        r += 1
    _wstart(cset.id, sess["chapter"], r)
    return True


def _act_myth_start(req):
    cset, ch, round_no = _chapter_arg(req, "myth")
    S["settings"]["set"] = cset.id
    S["settings"]["mode"] = "myth"
    _mstart(cset.id, ch["id"], round_no)
    return True


def _mplaying():
    sess = _ensure_msession()
    if sess is None:
        raise _Bad("No myth-or-record chapter is open yet.")
    return sess


def _act_myth_sort(req):
    sess = _mplaying()
    if sess["status"] != "playing":
        raise _Bad("This puzzle is finished. Press Next puzzle.")
    cset, puz = _mpuzzle(sess)
    claim_id = _str(req, "claim")
    if claim_id not in puz.tray:
        raise _Bad("That claim is not in this puzzle.")
    bin_id = req.get("bin")
    if bin_id is not None and bin_id not in mq.BINS:
        raise _Bad("Pick documented, disputed or traditional-but-doubtful.")
    i = puz.tray.index(claim_id)
    if sess["locked"][i]:
        raise _Bad("That claim is already sorted correctly.")
    if sess["bins"][i] == bin_id:
        return False
    sess["bins"][i] = bin_id
    sess["marks"][i] = None
    sess["message"] = ""
    return True


def _act_myth_check(_req):
    sess = _mplaying()
    if sess["status"] != "playing":
        raise _Bad("This puzzle is finished.")
    cset, puz = _mpuzzle(sess)
    if any(b is None for b in sess["bins"]):
        raise _Bad("Sort all %d claims before checking." % puz.size)
    result = mq.grade(puz, {cid: sess["bins"][i] for i, cid in enumerate(puz.tray)})
    prog = _prog(cset.id)
    sess["checks"] += 1
    for i, row in enumerate(result["claims"]):
        if row["status"] == "right":
            sess["locked"][i] = True
            sess["marks"][i] = None
            if row["claim"] not in prog["sorted"]:
                prog["sorted"].add(row["claim"])
                sess["new"].append(row["claim"])
        else:
            sess["marks"][i] = "wrong"
    if result["all_right"]:
        sess["status"] = "solved"
        key = "%s:%d" % (sess["chapter"], sess["round"])
        old = prog["msolved"].get(key)
        if old is None or sess["checks"] < old["checks"]:
            prog["msolved"][key] = {"checks": sess["checks"]}
        sess["message"] = "Sorted in one check." if sess["checks"] == 1 else "Sorted in %d checks." % sess["checks"]
    else:
        sess["message"] = "%d of %d claims are in the right bin and locked. Move the others." % (result["right"], puz.size)
    return True


def _act_myth_show(_req):
    sess = _mplaying()
    if sess["status"] != "playing":
        raise _Bad("This puzzle is finished.")
    _cset, puz = _mpuzzle(sess)
    sess["bins"] = [puz.answer[c] for c in puz.tray]
    sess["locked"] = [True] * puz.size
    sess["marks"] = [None] * puz.size
    sess["status"] = "revealed"
    sess["message"] = "Answer shown. Nothing was added to your archive from this puzzle."
    return True


def _act_myth_next(_req):
    sess = _mplaying()
    cset = SETS[sess["set"]]
    solved = _prog(cset.id)["msolved"]
    r = sess["round"] + 1
    while "%s:%d" % (sess["chapter"], r) in solved:
        r += 1
    _mstart(cset.id, sess["chapter"], r)
    return True


READ_ONLY = {"boot", "archive", "info", "report", "entry"}


def handle_dict(req):
    out = {"ok": True, "error": None, "view": None, "new": [], "dirty": False}
    try:
        if not isinstance(req, dict):
            raise _Bad("Bad request.")
        action = req.get("action")
        before = set(_earned_now())
        dirty = False
        if action == "boot":
            _ensure_session()
        elif action == "archive":
            out["archive"] = _archive(_set_for(req))
        elif action == "info":
            _act_info(req, out)
        elif action == "report":
            _act_report(req, out)
        elif action == "entry":
            _act_entry(req, out)
        elif action == "view_claim":
            dirty = _act_view_claim(req, out)
        elif action in _MUTATORS:
            dirty = bool(_MUTATORS[action](req))
        else:
            raise _Bad("Unknown action.")
        out["dirty"] = dirty or action in ("start", "choose_set")
        after = _earned_now()
        out["new"] = [a for a in after if a not in before]
        out["view"] = _view()
    except _Bad as exc:
        out["ok"] = False
        out["error"] = str(exc)
        try:
            out["view"] = _view()
        except Exception:  # noqa: BLE001
            out["view"] = None
    return out


_MUTATORS = {
    "start": _act_start, "choose_set": _act_choose_set, "place": _act_place, "unplace": _act_unplace,
    "check": _act_check, "show_answer": _act_show_answer, "next": _act_next, "settings": _act_settings,
    "ack": _act_ack, "reset": _act_reset,
    "mode": _act_mode, "web_start": _act_web_start, "web_link": _act_web_link, "web_show": _act_web_show, "web_next": _act_web_next,
    "myth_start": _act_myth_start, "myth_sort": _act_myth_sort, "myth_check": _act_myth_check, "myth_show": _act_myth_show,
    "myth_next": _act_myth_next,
}


def handle(request):
    try:
        req = json.loads(request) if isinstance(request, str) else request
        return json.dumps(handle_dict(req))
    except Exception as exc:  # noqa: BLE001 -- the page must never see a raw traceback
        return json.dumps({"ok": False, "error": "Engine error: %s" % exc, "view": None, "new": [], "dirty": False})


# --------------------------------------------------------------------------
# Save / load (shared/save-widget.js contract)


def _id_list(raw, valid):
    if not isinstance(raw, (list, tuple)):
        return []
    return [x for x in raw[:MAX_IDS] if isinstance(x, str) and x in valid]


def get_state():
    sets = {}
    for set_id, prog in S["sets"].items():
        sets[set_id] = {"learned": sorted(prog["learned"]),
                        "solved": {k: dict(v) for k, v in sorted(prog["solved"].items())},
                        "revealed": sorted(prog["revealed"]),
                        "threads": sorted(prog["threads"]), "sorted": sorted(prog["sorted"]),
                        "web_solved": {k: dict(v) for k, v in sorted(prog["wsolved"].items())},
                        "myth_solved": {k: dict(v) for k, v in sorted(prog["msolved"].items())}}
    for set_id, raw in S["unknown"].items():
        sets.setdefault(set_id, raw)
    sess = S["session"]
    return {
        "schema": SCHEMA, "sets": sets, "viewed": sorted(S["viewed"]),
        "settings": dict(S["settings"]), "flags": dict(S["flags"]),
        "session": json.loads(json.dumps(sess)) if sess else None,
        "web_session": json.loads(json.dumps(S["wsession"])) if S["wsession"] else None,
        "myth_session": json.loads(json.dumps(S["msession"])) if S["msession"] else None,
        "achievements_earned": _earned_now(),
    }


def _clean_session(raw):
    """A saved puzzle session, or None if anything about it is not what the engine could have produced."""
    if not isinstance(raw, dict):
        return None
    set_id, section_id, round_no = raw.get("set"), raw.get("section"), raw.get("round")
    if set_id not in SETS or isinstance(round_no, bool) or not isinstance(round_no, int) or not 0 <= round_no <= 10000:
        return None
    cset = SETS[set_id]
    if cset.section(section_id) is None:
        return None
    try:
        puz = pz.make_puzzle(cset, section_id, round_no)
    except ValueError:
        return None
    n = puz.size
    place, locked, marks = raw.get("placement"), raw.get("locked"), raw.get("marks")
    if not (isinstance(place, list) and isinstance(locked, list) and isinstance(marks, list)
            and len(place) == len(locked) == len(marks) == n):
        return None
    if any(c is not None and c not in puz.tray for c in place) or len({c for c in place if c}) != len([c for c in place if c]):
        return None
    if any(not isinstance(l, bool) for l in locked) or any(l and place[i] is None for i, l in enumerate(locked)):
        return None
    if any(m not in (None, "earlier", "later", "wrong") for m in marks):
        return None
    if any(l and place[i] != puz.answer[i] for i, l in enumerate(locked)):
        return None           # a locked card must really be in its right slot
    status = raw.get("status")
    if status not in ("playing", "solved", "revealed"):
        return None
    if status in ("solved", "revealed") and place != puz.answer:
        return None
    checks = raw.get("checks")
    if isinstance(checks, bool) or not isinstance(checks, int) or not 0 <= checks <= 10000:
        return None
    new = _id_list(raw.get("new"), cset.events)
    return {"set": set_id, "section": section_id, "round": round_no, "placement": list(place), "locked": list(locked),
            "marks": list(marks), "checks": checks, "status": status, "new": new,
            "message": raw.get("message") if isinstance(raw.get("message"), str) and len(raw["message"]) < 200 else ""}


def _clean_wsession(raw):
    """A saved cause-web session, or None if anything about it is not what the engine could have produced."""
    if not isinstance(raw, dict):
        return None
    set_id, chapter_id, round_no = raw.get("set"), raw.get("chapter"), raw.get("round")
    if set_id not in SETS or isinstance(round_no, bool) or not isinstance(round_no, int) or not 0 <= round_no <= 10000:
        return None
    cset = SETS[set_id]
    ch = cset.web_chapter(chapter_id)
    if ch is None or not _web_unlocked(set_id, ch):
        return None
    try:
        puz = wb.make_web_puzzle(cset, chapter_id, round_no)
    except ValueError:
        return None
    found, tries, status = raw.get("found"), raw.get("tries"), raw.get("status")
    if not isinstance(found, list) or not all(isinstance(r, str) and r in puz.relations for r in found) or len(set(found)) != len(found):
        return None
    if any(r not in _prog(set_id)["threads"] for r in found):
        return None                         # a thread in the session must really have been earned
    if status not in ("playing", "solved", "revealed"):
        return None
    if status == "solved" and sorted(found) != sorted(puz.relations):
        return None
    misses = raw.get("misses")
    if isinstance(misses, bool) or not isinstance(misses, int) or not 0 <= misses <= 100000:
        return None
    clean_tries = []
    if not isinstance(tries, list):
        return None
    for t in tries[:30]:
        if not (isinstance(t, dict) and t.get("from") in puz.cards and t.get("to") in puz.cards and t.get("verdict") in ("reversed", "unconfirmed")):
            return None
        clean_tries.append({"from": t["from"], "to": t["to"], "verdict": t["verdict"]})
    message = raw.get("message") if isinstance(raw.get("message"), str) and len(raw["message"]) < 300 else ""
    return {"set": set_id, "chapter": chapter_id, "round": round_no, "found": list(found), "tries": clean_tries,
            "misses": misses, "status": status, "message": message}


def _clean_msession(raw):
    if not isinstance(raw, dict):
        return None
    set_id, chapter_id, round_no = raw.get("set"), raw.get("chapter"), raw.get("round")
    if set_id not in SETS or isinstance(round_no, bool) or not isinstance(round_no, int) or not 0 <= round_no <= 10000:
        return None
    cset = SETS[set_id]
    ch = cset.myth_chapter(chapter_id)
    if ch is None or not _myth_unlocked(set_id, ch):
        return None
    try:
        puz = mq.make_myth_puzzle(cset, chapter_id, round_no)
    except ValueError:
        return None
    n = puz.size
    bins, locked, marks = raw.get("bins"), raw.get("locked"), raw.get("marks")
    if not (isinstance(bins, list) and isinstance(locked, list) and isinstance(marks, list) and len(bins) == len(locked) == len(marks) == n):
        return None
    if any(b is not None and b not in mq.BINS for b in bins) or any(not isinstance(l, bool) for l in locked):
        return None
    if any(m not in (None, "wrong") for m in marks):
        return None
    sorted_now = _prog(set_id)["sorted"]
    for i, cid in enumerate(puz.tray):
        if locked[i] and (bins[i] != puz.answer[cid] or (raw.get("status") != "revealed" and cid not in sorted_now)):
            return None                     # a locked claim must really be in its right bin, and earned
    status = raw.get("status")
    if status not in ("playing", "solved", "revealed"):
        return None
    if status in ("solved", "revealed") and (not all(locked) or any(bins[i] != puz.answer[c] for i, c in enumerate(puz.tray))):
        return None
    checks = raw.get("checks")
    if isinstance(checks, bool) or not isinstance(checks, int) or not 0 <= checks <= 10000:
        return None
    new = [c for c in (raw.get("new") if isinstance(raw.get("new"), list) else [])[:MAX_IDS] if isinstance(c, str) and c in puz.answer]
    return {"set": set_id, "chapter": chapter_id, "round": round_no, "bins": list(bins), "locked": list(locked), "marks": list(marks),
            "checks": checks, "status": status, "new": new,
            "message": raw.get("message") if isinstance(raw.get("message"), str) and len(raw["message"]) < 300 else ""}


def load_state(data):
    """Merge a saved state in (never replaces, never raises on garbage): learned ids are unioned, solved
    puzzles keep the fewer checks, viewed claims are unioned, and bad fields are dropped one at a time."""
    if S is None:
        reset_engine()
    if not isinstance(data, dict):
        _refresh_view()
        return False
    raw_sets = data.get("sets") if isinstance(data.get("sets"), dict) else {}
    for set_id, raw in list(raw_sets.items())[:50]:
        if not isinstance(raw, dict) or not isinstance(set_id, str):
            continue
        if set_id not in SETS:
            # Progress for a set this build does not have is kept (and written back out), never interpreted.
            learned = [x for x in (raw.get("learned") if isinstance(raw.get("learned"), list) else [])[:MAX_IDS] if isinstance(x, str)]
            solved = {str(k): {"checks": v["checks"]} for k, v in list((raw.get("solved") if isinstance(raw.get("solved"), dict) else {}).items())[:MAX_IDS]
                      if isinstance(v, dict) and isinstance(v.get("checks"), int) and not isinstance(v.get("checks"), bool)}
            extra = {k: [x for x in (raw.get(k) if isinstance(raw.get(k), list) else [])[:MAX_IDS] if isinstance(x, str)] for k in ("threads", "sorted")}
            S["unknown"][set_id] = dict({"learned": learned, "solved": solved, "revealed": []}, **extra)
            continue
        cset = SETS[set_id]
        prog = _prog(set_id)
        prog["learned"] |= set(_id_list(raw.get("learned"), cset.events))
        solved = raw.get("solved") if isinstance(raw.get("solved"), dict) else {}
        for key, rec in list(solved.items())[:MAX_IDS]:
            section_id, _, rnd = str(key).partition(":")
            if cset.section(section_id) is None or not rnd.isdigit() or not isinstance(rec, dict):
                continue
            checks = rec.get("checks")
            if isinstance(checks, bool) or not isinstance(checks, int) or not 1 <= checks <= 10000:
                continue
            key = "%s:%d" % (section_id, int(rnd))
            old = prog["solved"].get(key)
            if old is None or checks < old["checks"]:
                prog["solved"][key] = {"checks": checks}
        revealed = raw.get("revealed") if isinstance(raw.get("revealed"), list) else []
        for key in revealed[:MAX_IDS]:
            if isinstance(key, str) and ":" in key and cset.section(key.split(":", 1)[0]):
                prog["revealed"].add(key)
        prog["threads"] |= set(_id_list(raw.get("threads"), set(cset.web_relation_ids())))
        prog["sorted"] |= set(_id_list(raw.get("sorted"), set(cset.myth_claim_ids())))
        for field, store, finder, name, floor in (("web_solved", prog["wsolved"], cset.web_chapter, "misses", 0),
                                                   ("myth_solved", prog["msolved"], cset.myth_chapter, "checks", 1)):
            recs = raw.get(field) if isinstance(raw.get(field), dict) else {}
            for key, rec in list(recs.items())[:MAX_IDS]:
                chapter_id, _, rnd = str(key).partition(":")
                if finder(chapter_id) is None or not rnd.isdigit() or not isinstance(rec, dict):
                    continue
                value = rec.get(name)
                if isinstance(value, bool) or not isinstance(value, int) or not floor <= value <= 100000:
                    continue
                key = "%s:%d" % (chapter_id, int(rnd))
                old = store.get(key)
                if old is None or value < old[name]:
                    store[key] = {name: value}
    viewed = data.get("viewed") if isinstance(data.get("viewed"), list) else []
    for key in viewed[:MAX_IDS]:
        if isinstance(key, str):
            set_id, _, claim_id = key.partition("/")
            if set_id in SETS and claim_id in SETS[set_id].claims:
                S["viewed"].add(key)
    settings = data.get("settings") if isinstance(data.get("settings"), dict) else {}
    if isinstance(settings.get("hints"), bool):
        S["settings"]["hints"] = settings["hints"]
    if settings.get("set") in SETS:
        S["settings"]["set"] = settings["set"]
    if settings.get("mode") in MODES:
        S["settings"]["mode"] = settings["mode"]
    flags = data.get("flags") if isinstance(data.get("flags"), dict) else {}
    if flags.get("onboarded") is True:
        S["flags"]["onboarded"] = True
    session = _clean_session(data.get("session"))
    if session is not None:
        S["session"] = session
        S["settings"]["set"] = session["set"]
    wsession = _clean_wsession(data.get("web_session"))
    if wsession is not None:
        S["wsession"] = wsession
    msession = _clean_msession(data.get("myth_session"))
    if msession is not None:
        S["msession"] = msession
    _refresh_view()
    return True


def _refresh_view():
    """Ask the page to redraw after a save is loaded (the save widget calls load_state directly and knows
    nothing about this game's view). Under plain CPython there is no page, so this is a no-op."""
    try:
        import js  # noqa: WPS433
        callback = getattr(js.window, "chronicleOnStateLoaded", None)
        if callback is not None:
            callback()
    except Exception:  # noqa: BLE001 -- no browser, or the UI is not up yet
        pass


def _load_default_sets():
    """In the browser the page writes the set files into the Pyodide file system under /sets before this runs."""
    for candidate in (Path("sets"), Path(__file__).resolve().parent / "sets" if "__file__" in globals() else None):
        if candidate is not None and (candidate / "index.json").exists():
            load_sets(candidate)
            return


reset_engine()
_load_default_sets()
