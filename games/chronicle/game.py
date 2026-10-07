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
  ack                           the player has seen the introduction
  reset                         erase all progress
Every response: {"ok", "error", "view", "new" (achievements just earned), "dirty" (state changed)}.
"""

import json
from pathlib import Path

import achievements
import puzzle as pz
import report
from setdata import SetError, format_date, load_set, year_of

SCHEMA = 1
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
    return {"sets": {}, "unknown": {}, "viewed": set(), "settings": {"set": None, "hints": True},
            "flags": {"onboarded": False}, "session": None, "earned": []}


def reset_engine():
    global S
    S = _blank_state()
    for set_id in SET_ORDER:
        _ensure_progress(set_id)


def _ensure_progress(set_id):
    return S["sets"].setdefault(set_id, {"learned": set(), "solved": {}, "revealed": set()})


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
    def percent(set_id):
        found, total = _counts(set_id)
        return 100 if found == total else (100 * found) // total

    @staticmethod
    def cleared(set_id, section_id):
        return _cleared(set_id, section_id)


HELP = _Helpers()


def _counts(set_id):
    cset = SETS[set_id]
    found = len(_prog(set_id)["learned"]) + len(HELP.people_found(set_id)) + len(HELP.places_found(set_id))
    total = len(cset.events) + len(cset.people) + len(cset.places)
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
        "viewed": ("%s/%s" % (cset.id, claim["id"])) in S["viewed"],
    }
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
        "other_claims": [_claim_view(cset, c) for c in cset.claims_for(event_id) if c["field"] != "date"],
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
    }


def _settings_view():
    return {"hints": bool(S["settings"]["hints"]), "set": S["settings"].get("set")}


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
    return {"set": cset.id, "title": cset.title, "found": found, "total": total, "percent": HELP.percent(cset.id),
            "groups": [
                {"id": "events", "title": "Moments", "entries": events},
                {"id": "elsewhere", "title": "Elsewhere in the world", "entries": elsewhere},
                {"id": "people", "title": "People", "entries": pe},
                {"id": "places", "title": "Places", "entries": pl},
            ],
            "readings": readings, "locked_readings": len(cset.readings) - len(readings)}


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
    out["info"] = {
        "set": {"id": cset.id, "title": cset.title, "status": cset.status, "status_label": cset.status_label,
                "draft": cset.status != "reviewed", "version": cset.version, "drafted": cset.meta.get("drafted")},
        "legend": [{"id": k, "label": v[0], "symbol": v[1], "meaning": _LEGEND[k]} for k, v in CONFIDENCE_LABELS.items()],
        "counts": {"claims": len(cset.claims), "sources": nsources, "events": len(cset.events)},
        "found_claims": claims,
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
                        "revealed": sorted(prog["revealed"])}
    for set_id, raw in S["unknown"].items():
        sets.setdefault(set_id, raw)
    sess = S["session"]
    return {
        "schema": SCHEMA, "sets": sets, "viewed": sorted(S["viewed"]),
        "settings": dict(S["settings"]), "flags": dict(S["flags"]),
        "session": json.loads(json.dumps(sess)) if sess else None,
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
            S["unknown"][set_id] = {"learned": learned, "solved": solved, "revealed": []}
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
    flags = data.get("flags") if isinstance(data.get("flags"), dict) else {}
    if flags.get("onboarded") is True:
        S["flags"]["onboarded"] = True
    session = _clean_session(data.get("session"))
    if session is not None:
        S["session"] = session
        S["settings"]["set"] = session["set"]
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
