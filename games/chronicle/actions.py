"""Chronicle -- the actions: one function per message the page sends, each changing S and returning
whether anything changed. handle_dict in game.py sends each page message here.

Split out of game.py on 2026-10-12."""

import report
import account as ac
import myth as mq
import puzzle as pz
import review as rv
import web as wb
from setdata import KIND_LABELS, event_start, parse_date, format_date
from core import (CONFIDENCE_LABELS, HELP, MAX_BOOKMARKS, BOOKMARK_NAME_MAX, MODES, S, SETS, SET_ORDER, STRENGTH_LABELS, STRENGTH_MEANING, _LEGEND, _claim_view,
                  _cleared, _counts, _cur_set, _event_full, _next_round, _prog, _unlocked, event_start_text,
                  reset_engine)
from views import (REVIEW_LABELS, _account_judged, _account_next_round, _account_points, _account_unlocked, _apuzzle,
                   _astart, _decision_unlocked, _decision_view, _default_start, _ensure_asession, _ensure_dsession,
                   _ensure_msession, _ensure_session, _ensure_wsession, _explanation, _letter, _make_puzzle, _mpuzzle,
                   _mstart, _myth_next_round, _myth_unlocked, _passage_reveal, _reading_view, _review_state, _start,
                   _thread_view, _web_next_round, _web_unlocked, _wpuzzle, _wstart)


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
    S["asession"] = None
    S["dsession"] = None
    S["rfeedback"] = None
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
    if claim["field"] == "account":
        aid = str(claim["value"]).partition(":")[0]
        a = cset.account(aid)
        if a is None:
            return False
        if _account_judged(cset.id, a):
            return True
        asess = S["asession"]
        return bool(asess and asess["set"] == cset.id and asess["account"] == aid and asess["status"] in ("solved", "revealed"))
    if claim["field"] == "decision":
        did, _, part = str(claim["value"]).partition(":")
        d = cset.decision(did)
        if d is None or d["event"] not in prog["learned"]:
            return False
        return part == "options" or did in prog["decided"]
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
    if cset.accounts:
        sources = []
        for a in cset.accounts:
            for p in a["passages"]:
                key = "%s/%s" % (a["id"], p["id"])
                if key in prog["judged"]:
                    when = format_date(p["written"]) if p.get("written") else "undated web page"
                    sources.append({"id": key, "kind": "account", "found": True, "title": "%s: %s" % (a["title"], p["author"]),
                                    "date_label": "%s source, %s" % (p["kind"].capitalize(), when), "hint": "Whose account?"})
                else:
                    sources.append({"id": key, "kind": "account", "found": False, "title": None, "date_label": None, "hint": "Whose account?"})
        groups.append({"id": "sources", "title": "Sources weighed", "entries": sources})
    if cset.decisions:
        choices = []
        for d in cset.decisions:
            if d["id"] in prog["decided"]:
                choices.append({"id": d["id"], "kind": "decision", "found": True, "title": d["title"], "date_label": "You made your choice", "hint": "Decision points"})
            else:
                choices.append({"id": d["id"], "kind": "decision", "found": False, "title": None, "date_label": None, "hint": "Decision points"})
        groups.append({"id": "choices", "title": "Crossroads", "entries": choices})
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
    for a in cset.accounts:
        for p in a["passages"]:
            if entry_id == "%s/%s" % (a["id"], p["id"]):
                if entry_id not in _prog(cset.id)["judged"]:
                    raise _Bad("You have not found that yet.")
                order = ac.display_order(cset, a["id"])
                out["entry"] = {"id": entry_id, "kind": "account", "title": "%s: %s" % (a["title"], p["author"]),
                                "passage": _passage_reveal(cset, a, p, _letter(order.index(p["id"]))),
                                "points": _account_points(cset, a)}
                return False
    d = cset.decision(entry_id)
    if d is not None:
        if entry_id not in _prog(cset.id)["decided"]:
            raise _Bad("You have not found that yet.")
        view = _decision_view({"set": cset.id, "decision": entry_id})
        out["entry"] = {"id": entry_id, "kind": "decision", "title": d["title"], "decision": view}
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
    prog = _prog(cset.id)
    shown_ids = {c["id"] for f in claims for c in f["claims"]} | {t["claim"]["id"] for t in threads}
    accounts = []
    for a in cset.accounts:
        got = _account_judged(cset.id, a)
        if got:
            order = ac.display_order(cset, a["id"])
            accounts.append({"id": a["id"], "title": a["title"], "judged": len(got), "total": len(a["passages"]),
                             "passages": [_passage_reveal(cset, a, p, _letter(order.index(p["id"]))) for p in a["passages"] if p["id"] in got],
                             "points": _account_points(cset, a)})
            shown_ids |= {pt["claim"] for pt in a["points"]}
    decisions = []
    for d in cset.decisions:
        if d["id"] in prog["decided"]:
            decisions.append(_decision_view({"set": cset.id, "decision": d["id"]}))
            shown_ids |= set(d["claims"].values())
    shown = len(shown_ids)
    levels = {k: sum(1 for c in cset.claims.values() if c["confidence"] == k) for k in CONFIDENCE_LABELS}
    out["info"] = {
        "set": {"id": cset.id, "title": cset.title, "status": cset.status, "status_label": cset.status_label,
                "draft": cset.status != "reviewed", "version": cset.version, "drafted": cset.meta.get("drafted")},
        "legend": [{"id": k, "label": v[0], "symbol": v[1], "meaning": _LEGEND[k]} for k, v in CONFIDENCE_LABELS.items()],
        "counts": {"claims": len(cset.claims), "sources": nsources, "events": len(cset.events), "relations": len(cset.relations),
                   "levels": levels, "accounts": len(cset.accounts), "passages": len(cset.passage_keys()), "decisions": len(cset.decisions)},
        "coverage": {"shown": shown, "total": len(cset.claims),
                     "note": "Every claim in a set links at least three sources. You see %d of %d claims now; the rest appear as you find them." % (shown, len(cset.claims))},
        "strengths": [{"id": k, "label": v[0], "symbol": v[1], "meaning": STRENGTH_MEANING[k]} for k, v in STRENGTH_LABELS.items()],
        "found_claims": claims,
        "found_relations": threads,
        "found_accounts": accounts,
        "found_decisions": decisions,
        "account_kinds": [{"id": k, "label": v} for k, v in KIND_LABELS.items()],
        "reasons": [{"id": i, "label": l} for i, l in report.REASONS],
    }
    return False


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
    if mode == "account" and not cset.accounts:
        raise _Bad("This set has no whose-account puzzles yet.")
    if mode == "decision" and not cset.decisions:
        raise _Bad("This set has no decision points yet.")
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


# ---- whose account?


def _act_account_start(req):
    cset = _set_for(req)
    account_id = _str(req, "account")
    a = cset.account(account_id)
    if a is None:
        raise _Bad("Unknown account.")
    if not _account_unlocked(cset.id, a):
        raise _Bad("That account is still locked.")
    round_no = _int(req, "round") if "round" in req and req["round"] is not None else _account_next_round(cset.id, a)
    if round_no < 0 or round_no > 10000:
        raise _Bad("That puzzle does not exist.")
    S["settings"]["set"] = cset.id
    S["settings"]["mode"] = "account"
    _astart(cset.id, account_id, round_no)
    return True


def _aplaying():
    sess = _ensure_asession()
    if sess is None:
        raise _Bad("No whose-account puzzle is open yet.")
    return sess


def _act_account_answer(req):
    sess = _aplaying()
    if sess["status"] != "playing":
        raise _Bad("This puzzle is finished. Press Next puzzle.")
    cset, puz = _apuzzle(sess)
    qid = _str(req, "question")
    ids = puz.question_ids()
    if qid not in ids:
        raise _Bad("That question is not in this puzzle.")
    i = ids.index(qid)
    choice = req.get("choice")
    if choice is not None and choice not in puz.questions[i]["options"]:
        raise _Bad("Pick one of the listed options.")
    if sess["locked"][i]:
        raise _Bad("That question is already answered correctly.")
    if sess["answers"][i] == choice:
        return False
    sess["answers"][i] = choice
    sess["marks"][i] = None
    sess["message"] = ""
    return True


def _act_account_check(_req):
    sess = _aplaying()
    if sess["status"] != "playing":
        raise _Bad("This puzzle is finished.")
    cset, puz = _apuzzle(sess)
    if any(c is None for c in sess["answers"]):
        raise _Bad("Answer all %d questions before checking." % puz.size)
    result = ac.grade(puz, {q["id"]: sess["answers"][i] for i, q in enumerate(puz.questions)})
    prog = _prog(cset.id)
    sess["checks"] += 1
    for i, row in enumerate(result["questions"]):
        if row["status"] == "right":
            sess["locked"][i] = True
            sess["marks"][i] = None
        else:
            sess["marks"][i] = "wrong"
    if result["all_right"]:
        sess["status"] = "solved"
        key = "%s:%d" % (sess["account"], sess["round"])
        old = prog["asolved"].get(key)
        if old is None or sess["checks"] < old["checks"]:
            prog["asolved"][key] = {"checks": sess["checks"]}
        pk = "%s/%s" % (sess["account"], puz.focus)
        if pk not in prog["judged"]:
            prog["judged"].add(pk)
            sess["new"].append(pk)
        sess["message"] = "Judged in one check." if sess["checks"] == 1 else "Judged in %d checks." % sess["checks"]
    else:
        sess["message"] = "%d of %d answers are right and locked. Change the others." % (result["right"], puz.size)
    return True


def _act_account_show(_req):
    sess = _aplaying()
    if sess["status"] != "playing":
        raise _Bad("This puzzle is finished.")
    _cset, puz = _apuzzle(sess)
    sess["answers"] = [q["answer"] for q in puz.questions]
    sess["locked"] = [True] * puz.size
    sess["marks"] = [None] * puz.size
    sess["status"] = "revealed"
    sess["message"] = "Answers shown. Nothing was added to your archive from this puzzle."
    return True


def _act_account_next(_req):
    sess = _aplaying()
    cset = SETS[sess["set"]]
    solved = _prog(cset.id)["asolved"]
    r = sess["round"] + 1
    while "%s:%d" % (sess["account"], r) in solved:
        r += 1
    _astart(cset.id, sess["account"], r)
    return True


# ---- decision points


def _act_decision_start(req):
    cset = _set_for(req)
    did = _str(req, "decision")
    d = cset.decision(did)
    if d is None:
        raise _Bad("Unknown decision point.")
    if not _decision_unlocked(cset.id, d):
        raise _Bad("That decision point is still locked.")
    S["settings"]["set"] = cset.id
    S["settings"]["mode"] = "decision"
    S["dsession"] = {"set": cset.id, "decision": did}
    return True


def _act_decision_pick(req):
    sess = _ensure_dsession()
    if sess is None:
        raise _Bad("No decision point is open yet.")
    cset = SETS[sess["set"]]
    d = cset.decision(sess["decision"])
    option = _str(req, "option")
    if option not in {o["id"] for o in d["options"]}:
        raise _Bad("Pick one of the listed options.")
    prog = _prog(cset.id)
    if d["id"] in prog["decided"]:
        raise _Bad("You have already made your choice here. It is shown below.")
    prog["decided"][d["id"]] = {"picked": option}
    return True


# ---- review


def _act_review_answer(req):
    cset = _cur_set()
    if cset is None:
        raise _Bad("No set is loaded.")
    prog, srs, day = _review_state(cset)
    if S["rfeedback"] is not None:
        raise _Bad("Press Next to move on.")
    queue = rv.ready_questions(cset, prog, srs, day, REVIEW_LABELS, limit=1)
    if not queue:
        raise _Bad("Nothing is ready to review.")
    key, q = queue[0]
    if req.get("key") != key:
        raise _Bad("That question is no longer the current one.")
    choice = req.get("choice")
    if choice not in {o["id"] for o in q["options"]}:
        raise _Bad("Pick one of the listed options.")
    rec = srs.get(key) or rv.new_record()
    right = choice == q["answer"]
    new = rv.after_answer(rec, day, right)
    srs[key] = new
    claim = rv.claim_for(cset, key)
    labels = {o["id"]: o["label"] for o in q["options"]}
    gap = new["due"] - day
    S["rfeedback"] = {
        "set": cset.id, "key": key, "right": right, "answer": q["answer"], "answer_label": labels[q["answer"]],
        "choice_label": labels[choice], "context": q["context"], "prompt": q["prompt"],
        "message": ("That matches the sources. This fact comes back %s." % rv.interval_text(gap)) if right else
        ("Not this time. The sources say: %s. This fact comes back %s, and nothing is taken away." % (labels[q["answer"]], rv.interval_text(gap))),
        "claim": _claim_view(cset, claim) if claim else None, "settled": rv.is_settled(new),
    }
    return True


def _act_review_next(_req):
    changed = S["rfeedback"] is not None
    S["rfeedback"] = None
    return changed


def _act_review_day(_req):
    if S["day"] >= rv.MAX_DAY:
        raise _Bad("That is as far as the day counter goes.")
    S["day"] += 1
    S["rfeedback"] = None
    return True


def _act_year(req, out):
    year = _int(req, 'year')
    if year == 0 or abs(year) > 3000:
        raise _Bad('Give a year from -3000 to 3000, not 0.')
    out['year'] = {'year': year, 'label': ('%d BCE' % -year) if year < 0 else str(year), 'entries': year_moments(year)}
    return False


def year_moments(year):
    result = []
    for set_id in SET_ORDER:
        cset = SETS[set_id]
        for event_id in cset.event_order:
            e = cset.events[event_id]
            if event_id not in _prog(set_id)["learned"]:
                continue
            start = parse_date(event_start(e))[0]
            end = parse_date(e["end"])[0] if e.get("end") else start
            if start <= year <= end:
                result.append({
                    "set": set_id,
                    "set_title": cset.title,
                    "id": event_id,
                    "kind": e["kind"],
                    "title": e["title"],
                    "date_label": format_date(event_start_text(e)),
                })
    return result


def _act_bookmark(req):
    name = _str(req, "name").strip()
    if not name:
        raise _Bad("Give the bookmark a name.")
    if len(name) > BOOKMARK_NAME_MAX:
        raise _Bad("Names are at most 30 characters.")
    sess = S["session"]
    if sess is None:
        raise _Bad("Open a puzzle first.")
    entry = {"name": name, "set": sess["set"], "section": sess["section"], "round": sess["round"]}
    for i, bm in enumerate(S["bookmarks"]):
        if bm["name"] == name:
            S["bookmarks"][i] = entry
            return True
    if len(S["bookmarks"]) >= MAX_BOOKMARKS:
        raise _Bad("The shelf is full (20). Remove one first.")
    S["bookmarks"].append(entry)
    return True


def _act_unbookmark(req):
    name = _str(req, "name")
    for i, bm in enumerate(S["bookmarks"]):
        if bm["name"] == name:
            S["bookmarks"].pop(i)
            return True
    raise _Bad("No bookmark with that name.")
