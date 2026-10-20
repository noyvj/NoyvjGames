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
  year {year}                   the moments found from one year, across every set
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
  account_start {account, round?}   open a whose-account puzzle
  account_answer {question, choice}  choose an option for one question (or clear it with choice null)
  account_check                 grade a fully answered puzzle: right answers lock; all right = that source is judged
  account_show                  reveal the answers and the sources (nothing is learned from a reveal)
  account_next                  the next whose-account round
  decision_start {decision}     open a decision point
  decision_pick {option}        choose; the game then shows what they chose and what followed (nothing is graded)
  review_answer {key, choice}   answer the review question that is ready
  review_next                   leave the answer's feedback and move to the next ready question
  review_day                    let a day pass (the review schedule's own day counter; there is no real clock)
  ack                           the player has seen the introduction
  reset                         erase all progress
Every response: {"ok", "error", "view", "new" (achievements just earned), "dirty" (state changed)}.
"""

import json
import account as ac
import myth as mq
import puzzle as pz
import review as rv
import web as wb
from pathlib import Path
# Some names are re-exported for the tests, which read them from game (S, SETS, HELP, ...).
from core import (HELP, LOAD_PROBLEMS, MAX_IDS, MODES, S, SCHEMA, SETS, SET_ORDER, _counts, _prog, load_sets,  # noqa: F401
                  register_set, reset_engine)
from views import (REVIEW_LABELS, _review_explainer, _account_unlocked, _decision_unlocked, _earned_now, _ensure_session, _myth_unlocked, _thread_view,  # noqa: F401
                   _view, _web_unlocked)
from actions import (_Bad, _act_account_answer, _act_account_check, _act_account_next, _act_account_show,
                     _act_account_start, _act_ack, _act_check, _act_choose_set, _act_decision_pick,
                     _act_decision_start, _act_entry, _act_info, _act_mode, _act_myth_check, _act_myth_next,
                     _act_myth_show, _act_myth_sort, _act_myth_start, _act_next, _act_place, _act_report, _act_reset,
                     _act_review_answer, _act_review_day, _act_review_next, _act_settings, _act_show_answer,
                     _act_start, _act_unplace, _act_view_claim, _act_web_link, _act_web_next, _act_web_show,
                     _act_web_start, _act_year, _archive, _set_for)


READ_ONLY = {"boot", "archive", "info", "report", "entry", "year"}


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
        elif action == "year":
            _act_year(req, out)
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
    "account_start": _act_account_start, "account_answer": _act_account_answer, "account_check": _act_account_check,
    "account_show": _act_account_show, "account_next": _act_account_next,
    "decision_start": _act_decision_start, "decision_pick": _act_decision_pick,
    "review_answer": _act_review_answer, "review_next": _act_review_next, "review_day": _act_review_day,
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
                        "myth_solved": {k: dict(v) for k, v in sorted(prog["msolved"].items())},
                        "judged": sorted(prog["judged"]),
                        "account_solved": {k: dict(v) for k, v in sorted(prog["asolved"].items())},
                        "decided": {k: dict(v) for k, v in sorted(prog["decided"].items())},
                        "srs": {k: dict(v) for k, v in sorted(prog["srs"].items())}}
    for set_id, raw in S["unknown"].items():
        sets.setdefault(set_id, raw)
    sess = S["session"]
    return {
        "schema": SCHEMA, "sets": sets, "viewed": sorted(S["viewed"]),
        "settings": dict(S["settings"]), "flags": dict(S["flags"]),
        "session": json.loads(json.dumps(sess)) if sess else None,
        "web_session": json.loads(json.dumps(S["wsession"])) if S["wsession"] else None,
        "myth_session": json.loads(json.dumps(S["msession"])) if S["msession"] else None,
        "account_session": json.loads(json.dumps(S["asession"])) if S["asession"] else None,
        "decision_session": dict(S["dsession"]) if S["dsession"] else None,
        "day": S["day"],
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
    if any(not isinstance(lk, bool) for lk in locked) or any(lk and place[i] is None for i, lk in enumerate(locked)):
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
    if any(b is not None and b not in mq.BINS for b in bins) or any(not isinstance(lk, bool) for lk in locked):
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
    new = [c for c in (raw.get("new") if isinstance(raw.get("new"), list) else [])
           [:MAX_IDS] if isinstance(c, str) and c in puz.answer]
    return {"set": set_id, "chapter": chapter_id, "round": round_no, "bins": list(bins), "locked": list(locked), "marks": list(marks),
            "checks": checks, "status": status, "new": new,
            "message": raw.get("message") if isinstance(raw.get("message"), str) and len(raw["message"]) < 300 else ""}


def _clean_asession(raw):
    if not isinstance(raw, dict):
        return None
    set_id, account_id, round_no = raw.get("set"), raw.get("account"), raw.get("round")
    if set_id not in SETS or isinstance(round_no, bool) or not isinstance(round_no, int) or not 0 <= round_no <= 10000:
        return None
    cset = SETS[set_id]
    a = cset.account(account_id)
    if a is None or not _account_unlocked(set_id, a):
        return None
    try:
        puz = ac.make_account_puzzle(cset, account_id, round_no)
    except ValueError:
        return None
    n = puz.size
    answers, locked, marks = raw.get("answers"), raw.get("locked"), raw.get("marks")
    if not (isinstance(answers, list) and isinstance(locked, list) and isinstance(marks, list) and len(answers) == len(locked) == len(marks) == n):
        return None
    if any(not isinstance(lk, bool) for lk in locked) or any(m not in (None, "wrong") for m in marks):
        return None
    for i, q in enumerate(puz.questions):
        if answers[i] is not None and answers[i] not in q["options"]:
            return None
        if locked[i] and answers[i] != q["answer"]:
            return None                     # a locked answer must really be the right one
    status = raw.get("status")
    if status not in ("playing", "solved", "revealed"):
        return None
    if status in ("solved", "revealed") and not all(locked):
        return None
    if status == "solved" and "%s/%s" % (account_id, puz.focus) not in _prog(set_id)["judged"]:
        return None                         # a solved session must really have been earned
    checks = raw.get("checks")
    if isinstance(checks, bool) or not isinstance(checks, int) or not 0 <= checks <= 10000:
        return None
    new = [k for k in (raw.get("new") if isinstance(raw.get("new"), list) else [])[:MAX_IDS]
           if isinstance(k, str) and k == "%s/%s" % (account_id, puz.focus)]
    return {"set": set_id, "account": account_id, "round": round_no, "answers": list(answers), "locked": list(locked), "marks": list(marks),
            "checks": checks, "status": status, "new": new,
            "message": raw.get("message") if isinstance(raw.get("message"), str) and len(raw["message"]) < 300 else ""}


def _clean_dsession(raw):
    if not isinstance(raw, dict):
        return None
    set_id, did = raw.get("set"), raw.get("decision")
    if set_id not in SETS:
        return None
    d = SETS[set_id].decision(did)
    if d is None or not _decision_unlocked(set_id, d):
        return None
    return {"set": set_id, "decision": did}


def _clean_srs(raw, cset):
    """Saved review records, one at a time: a key the set lacks or a record with a bad number is dropped."""
    out = {}
    if not isinstance(raw, dict):
        return out
    valid = {"ev": set(cset.events), "my": set(cset.myth_claim_ids()), "ln": set(
        cset.web_relation_ids()), "dc": set(cset.decision_ids())}
    for key, rec in list(raw.items())[:MAX_IDS]:
        kind, ident = rv.split_key(key)
        if not isinstance(key, str) or ident not in valid.get(kind, ()) or not isinstance(rec, dict):
            continue
        nums = {}
        for field, lo, hi in (("step", 0, 99), ("due", 0, rv.MAX_DAY + 40), ("asked", 0, 100000), ("right", 0, 100000)):
            v = rec.get(field)
            if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
                nums = None
                break
            nums[field] = v
        last = rec.get("last")
        if nums is None or nums["right"] > nums["asked"] or not (last is None or (isinstance(last, int) and not isinstance(last, bool) and 0 <= last <= rv.MAX_DAY)):
            continue
        nums["last"] = last
        out[key] = nums
    return out


def load_state(data):
    """Merge a saved state in (never replaces, never raises on garbage): learned ids are unioned, solved
    puzzles keep the fewer checks, viewed claims are unioned, and bad fields are dropped one at a time."""
    if not S:
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
            learned = [x for x in (raw.get("learned") if isinstance(
                raw.get("learned"), list) else [])[:MAX_IDS] if isinstance(x, str)]
            solved = {str(k): {"checks": v["checks"]} for k, v in list((raw.get("solved") if isinstance(raw.get("solved"), dict) else {}).items())[:MAX_IDS]
                      if isinstance(v, dict) and isinstance(v.get("checks"), int) and not isinstance(v.get("checks"), bool)}
            extra = {k: [x for x in (raw.get(k) if isinstance(raw.get(k), list) else [])[:MAX_IDS]
                         if isinstance(x, str)] for k in ("threads", "sorted", "judged")}
            decided = {str(k): {"picked": v["picked"]} for k, v in list((raw.get("decided") if isinstance(raw.get("decided"), dict) else {}).items())[:MAX_IDS]
                       if isinstance(v, dict) and isinstance(v.get("picked"), str)}
            S["unknown"][set_id] = dict({"learned": learned, "solved": solved,
                                        "revealed": [], "decided": decided}, **extra)
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
        prog["judged"] |= set(_id_list(raw.get("judged"), set(cset.passage_keys())))
        decided = raw.get("decided") if isinstance(raw.get("decided"), dict) else {}
        for did, rec in list(decided.items())[:MAX_IDS]:
            d = cset.decision(did) if isinstance(did, str) else None
            if d is not None and isinstance(rec, dict) and rec.get("picked") in {o["id"] for o in d["options"]}:
                prog["decided"].setdefault(did, {"picked": rec["picked"]})        # a first choice is never replaced
        for key, rec in _clean_srs(raw.get("srs"), cset).items():
            old = prog["srs"].get(key)
            if old is None or (rec["asked"], rec["last"] or 0) > (old["asked"], old["last"] or 0):
                prog["srs"][key] = rec
        for field, store, finder, name, floor in (("web_solved", prog["wsolved"], cset.web_chapter, "misses", 0),
                                                  ("myth_solved", prog["msolved"], cset.myth_chapter, "checks", 1),
                                                  ("account_solved", prog["asolved"], cset.account, "checks", 1)):
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
    day = data.get("day")
    if isinstance(day, int) and not isinstance(day, bool) and 0 <= day <= rv.MAX_DAY:
        S["day"] = max(S["day"], day)                     # time never runs backwards
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
    asession = _clean_asession(data.get("account_session"))
    if asession is not None:
        S["asession"] = asession
    dsession = _clean_dsession(data.get("decision_session"))
    if dsession is not None:
        S["dsession"] = dsession
    S["rfeedback"] = None
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
