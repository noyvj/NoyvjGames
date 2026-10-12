"""Chronicle -- the views: plain dicts describing what the page shows for each mode (timeline, cause web,
myth sorting, whose account, decision points, review). No state is changed here.

Split out of game.py on 2026-10-12."""

import achievements
import account as ac
import decision as dc
import myth as mq
import puzzle as pz
import review as rv
import web as wb
from setdata import KIND_LABELS, PURPOSES, VANTAGES, format_date, year_of
from core import (CONFIDENCE_LABELS, HELP, LOAD_PROBLEMS, MODES, MODE_LABELS, S, SETS, SET_ORDER, STRENGTH_LABELS,
                  STRENGTH_MEANING, _LEGEND, _claim_view, _cleared, _counts, _cur_set, _event_card, _event_full,
                  _next_round, _prog, _solves_in, _unlocked, event_start_text)


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


# ---- whose account?: chapters (one per account), session, views


def _account_unlocked(set_id, a):
    return a["event"] in _prog(set_id)["learned"]


def _account_judged(set_id, a):
    return [p["id"] for p in a["passages"] if "%s/%s" % (a["id"], p["id"]) in _prog(set_id)["judged"]]


def _account_cleared(set_id, a):
    return len(_account_judged(set_id, a)) == len(a["passages"])


def _account_next_round(set_id, a):
    solved = _prog(set_id)["asolved"]
    r = 0
    while "%s:%d" % (a["id"], r) in solved:
        r += 1
    return r


def _account_chapter_views(cset):
    out = []
    for a in cset.accounts:
        have = len(_account_judged(cset.id, a))
        unlocked = _account_unlocked(cset.id, a)
        out.append({
            "id": a["id"], "title": a["title"], "blurb": a["blurb"], "size": len(a["passages"]), "difficulty": None,
            "unlocked": unlocked, "cleared": have == len(a["passages"]), "have": have, "need": len(a["passages"]),
            "progress": "Judged %d of %d sources" % (have, len(a["passages"])), "missing": 0 if unlocked else 1,
            "requires_text": "Find that moment in the timeline first",
            "next_round": _account_next_round(cset.id, a), "main_rounds": ac.main_rounds(cset, a["id"]),
        })
    return out


def _astart(set_id, account_id, round_no):
    cset = SETS[set_id]
    puz = ac.make_account_puzzle(cset, account_id, round_no)
    n = puz.size
    S["asession"] = {"set": set_id, "account": account_id, "round": round_no, "answers": [None] * n, "locked": [False] * n,
                     "marks": [None] * n, "checks": 0, "status": "playing", "new": [], "message": ""}
    return puz


def _adefault(cset):
    chosen = None
    for a in cset.accounts:
        if _account_unlocked(cset.id, a):
            chosen = a
            if not _account_cleared(cset.id, a):
                break
    if chosen is None:
        return None
    _astart(cset.id, chosen["id"], _account_next_round(cset.id, chosen))
    return S["asession"]


def _ensure_asession():
    sess = S["asession"]
    cset = _cur_set()
    if cset is None or not cset.accounts:
        return None
    if sess is not None and sess["set"] == cset.id:
        a = cset.account(sess["account"])
        if a is not None and _account_unlocked(cset.id, a):
            return sess
    S["asession"] = None
    return _adefault(cset)


def _apuzzle(sess):
    cset = SETS[sess["set"]]
    return cset, ac.make_account_puzzle(cset, sess["account"], sess["round"])


def _letter(i):
    return chr(65 + i)


def _passage_reveal(cset, a, passage, letter):
    src = cset.sources[passage["source"]]
    written = passage.get("written")
    return {
        "id": passage["id"], "key": "%s/%s" % (a["id"], passage["id"]), "letter": letter, "text": passage["text"],
        "author": passage["author"], "kind": passage["kind"], "kind_label": KIND_LABELS[passage["kind"]],
        "written_label": format_date(written) if written else "undated web page, read on %s" % format_date(src["read"]),
        "vantage_label": dict(VANTAGES)[passage["vantage"]], "purpose_label": dict(PURPOSES)[passage["purpose"]],
        "purpose_note": passage["purpose_note"],
        "source": {"id": passage["source"], "title": src["title"], "institution": src.get("institution") or src.get("author"),
                   "url": src["url"], "read": src["read"]},
        "mentions": [pt["label"] for pt in a["points"] if pt["id"] in passage["mentions"]],
        "leaves_out": [pt["label"] for pt in a["points"] if pt["id"] not in passage["mentions"]],
    }


def _account_points(cset, a):
    return [{"id": pt["id"], "label": pt["label"], "claim": _claim_view(cset, cset.claims[pt["claim"]])} for pt in a["points"]]


def _account_view(sess):
    cset, puz = _apuzzle(sess)
    a = cset.account(sess["account"])
    main = ac.main_rounds(cset, sess["account"])
    label = ("Puzzle %d of %d" % (sess["round"] + 1, main)) if sess["round"] < main else ("Practice puzzle %d" % (sess["round"] - main + 1))
    by_id = {p["id"]: p for p in a["passages"]}
    letters = {pid: _letter(i) for i, pid in enumerate(puz.order)}
    passages = [{"id": pid, "letter": letters[pid], "text": by_id[pid]["text"], "focus": pid == puz.focus} for pid in puz.order]
    questions = []
    for i, q in enumerate(puz.questions):
        prompt = ac.PROMPTS[q["id"]]
        if q["id"] == "left_out":
            prompt = "Which of these does Passage %s leave out?" % letters[puz.focus]
        elif q["id"] == "who":
            prompt = "Who wrote the source behind Passage %s?" % letters[puz.focus]
        questions.append({"id": q["id"], "index": i, "prompt": prompt,
                          "options": [{"id": o, "label": ac.option_label(cset, a["id"], q["id"], o)} for o in q["options"]],
                          "choice": sess["answers"][i], "locked": sess["locked"][i],
                          "status": "right" if sess["locked"][i] else ("wrong" if sess["marks"][i] else None)})
    finished = sess["status"] != "playing"
    result = None
    if finished:
        correct = []
        for q in puz.questions:
            correct.append({"id": q["id"], "answer": q["answer"], "label": ac.option_label(cset, a["id"], q["id"], q["answer"])})
        result = {
            "solved": sess["status"] == "solved", "focus": puz.focus, "focus_letter": letters[puz.focus], "correct": correct,
            "passages": [_passage_reveal(cset, a, by_id[pid], letters[pid]) for pid in puz.order],
            "points": _account_points(cset, a), "new_count": len(sess["new"]),
            "account_cleared": sess["status"] == "solved" and _account_cleared(cset.id, a),
        }
    event = cset.events[a["event"]]
    return {
        "id": puz.code, "account": a["id"], "account_title": a["title"], "round": sess["round"], "round_label": label,
        "size": puz.size, "status": sess["status"], "message": sess["message"], "checks": sess["checks"],
        "event_title": event["title"], "event_date": format_date(event_start_text(event)),
        "passages": passages, "focus_letter": letters[puz.focus], "questions": questions,
        "all_answered": all(c is not None for c in sess["answers"]), "result": result,
    }


# ---- decision points: list, session, views


def _decision_unlocked(set_id, d):
    return d["event"] in _prog(set_id)["learned"]


def _decision_chapter_views(cset):
    out = []
    prog = _prog(cset.id)
    for d in cset.decisions:
        unlocked = _decision_unlocked(cset.id, d)
        done = d["id"] in prog["decided"]
        out.append({"id": d["id"], "title": d["title"], "blurb": "%s, %s." % (d["who"], d["when"]), "unlocked": unlocked,
                    "cleared": done, "progress": "You made your choice" if done else "Waiting for your choice",
                    "requires_text": "Find that moment in the timeline first", "missing": 0 if unlocked else 1})
    return out


def _ensure_dsession():
    sess = S["dsession"]
    cset = _cur_set()
    if cset is None or not cset.decisions:
        return None
    if sess is not None and sess["set"] == cset.id:
        d = cset.decision(sess["decision"])
        if d is not None and _decision_unlocked(cset.id, d):
            return sess
    S["dsession"] = None
    chosen = None
    for d in cset.decisions:
        if _decision_unlocked(cset.id, d):
            chosen = d
            if d["id"] not in _prog(cset.id)["decided"]:
                break
    if chosen is None:
        return None
    S["dsession"] = {"set": cset.id, "decision": chosen["id"]}
    return S["dsession"]


def _decision_view(sess):
    cset = SETS[sess["set"]]
    d = cset.decision(sess["decision"])
    rec = _prog(cset.id)["decided"].get(d["id"])
    by_id = {o["id"]: o for o in d["options"]}
    order = dc.option_order(cset, d["id"])
    view = {
        "id": d["id"], "title": d["title"], "who": d["who"], "when": d["when"], "question": d["question"],
        "situation": _claim_view(cset, cset.claims[d["claims"]["options"]]),
        "options": [{"id": o, "text": by_id[o]["text"], "picked": bool(rec and rec["picked"] == o)} for o in order],
        "decided": rec is not None, "picked": rec["picked"] if rec else None, "result": None,
        "event_title": cset.events[d["event"]]["title"],
    }
    if rec:
        same = rec["picked"] == d["chosen"]
        view["result"] = {
            "chosen": d["chosen"], "chosen_text": by_id[d["chosen"]]["text"], "same": same,
            "picked_text": by_id[rec["picked"]]["text"],
            "chose_label": "What %s chose" % d["who"], "after_label": "What followed",
            "choice_claim": _claim_view(cset, cset.claims[d["claims"]["choice"]]),
            "after_claim": _claim_view(cset, cset.claims[d["claims"]["after"]]),
            "note": ("Your choice matches what %s chose." if same else "You chose differently from %s.") % d["who"]
            + " There is no right answer here. The game shows what was chosen and what the sources say followed; it does not claim to know what would have happened otherwise.",
        }
    return view


# ---- review: the spaced-review board

REVIEW_LABELS = {
    "confidence": {k: "%s %s" % (v[1], v[0]) for k, v in CONFIDENCE_LABELS.items()},
    "strength": {k: "%s %s" % (v[1], v[0]) for k, v in STRENGTH_LABELS.items()},
}


def _review_state(cset):
    prog = _prog(cset.id)
    return prog, prog["srs"], S["day"]


def _review_counts(cset):
    prog, srs, day = _review_state(cset)
    keys = rv.all_keys(cset, prog)
    ready = len(rv.ready_questions(cset, prog, srs, day, REVIEW_LABELS))
    settled = sum(1 for k in keys if rv.is_settled(srs.get(k)))
    new = sum(1 for k in keys if k not in srs)
    return {"total": len(keys), "ready": ready, "later": len(keys) - ready, "settled": settled, "new": new}


def _review_view(cset):
    prog, srs, day = _review_state(cset)
    counts = _review_counts(cset)
    out = {"day": day, "counts": counts, "ladder": list(rv.LADDER), "question": None, "feedback": None, "idle": None,
           "explainer": _review_explainer()}
    fb = S["rfeedback"]
    if fb is not None and fb.get("set") == cset.id:
        out["feedback"] = fb
        return out
    queue = rv.ready_questions(cset, prog, srs, day, REVIEW_LABELS, limit=1)
    if queue:
        key, q = queue[0]
        rec = srs.get(key) or rv.new_record()
        out["question"] = {"key": key, "kind": q["kind"], "prompt": q["prompt"], "context": q["context"], "options": q["options"],
                           "new": key not in srs, "asked": rec["asked"]}
        return out
    if not counts["total"]:
        out["idle"] = "Nothing to review yet. Facts you learn in the other modes will appear here, and come back after a gap that grows each time you remember one."
    else:
        out["idle"] = ("Nothing is ready on day %d. Facts come back after a gap of 1, 3, 7, 14 and then 30 days. "
                       "Chronicle's days only move when you press Let a day pass, and nothing is lost while you are away." % day)
    return out


def _review_explainer():
    return [
        "Review brings back facts you have already learned: a moment's date, a statement you sorted, a cause link you found, a choice you made.",
        "A fact you remember comes back after a longer gap each time: %s days. A fact you do not remember comes back tomorrow, and is never taken away." % ", ".join(str(x) for x in rv.LADDER),
        "Time here is a day counter that moves only when you press Let a day pass. There is no clock, no deadline and nothing that runs out while you are away.",
        "Answering never changes your archive or your other progress.",
    ]


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
        "accounts": _account_chapter_views(cset), "decisions": _decision_chapter_views(cset),
        "account": _account_board(cset), "decision": _decision_board(cset), "review": _review_board(cset),
        "day": S["day"],
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
    if mode == "account" and not cset.accounts:
        return "timeline"
    if mode == "decision" and not cset.decisions:
        return "timeline"
    return mode if mode in MODES else "timeline"


def _modes_view(cset):
    return [
        {"id": "timeline", "label": MODE_LABELS["timeline"], "available": True},
        {"id": "web", "label": MODE_LABELS["web"], "available": bool(cset.web_chapters)},
        {"id": "myth", "label": MODE_LABELS["myth"], "available": bool(cset.myth_chapters)},
        {"id": "account", "label": MODE_LABELS["account"], "available": bool(cset.accounts)},
        {"id": "decision", "label": MODE_LABELS["decision"], "available": bool(cset.decisions)},
        {"id": "review", "label": MODE_LABELS["review"], "available": True},
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


def _account_board(cset):
    if _mode(cset) != "account":
        return None
    sess = _ensure_asession()
    if sess is None:
        return {"locked": True, "message": "Find the moments an account is about in the timeline to open Whose account?."}
    return _account_view(sess)


def _decision_board(cset):
    if _mode(cset) != "decision":
        return None
    sess = _ensure_dsession()
    if sess is None:
        return {"locked": True, "message": "Find the moments a decision point is about in the timeline to open it."}
    return _decision_view(sess)


def _review_board(cset):
    if _mode(cset) != "review":
        return None
    return _review_view(cset)


def _earned_now():
    return achievements.earned(S, SETS, HELP)
