"""Chronicle -- engine core: constants, the loaded sets, the progress state S and the derived facts every
other part reads. S, SETS, SET_ORDER and LOAD_PROBLEMS are created once and only ever changed in place
(cleared and refilled), so every module that imported them always sees the current values.

Split out of game.py on 2026-10-12 (the file-size pilot); game.py re-exports what tests and the page use."""

import json
from pathlib import Path
from setdata import HIDDEN_FIELDS, SetError, format_date, load_set


SCHEMA = 3
MODES = ("timeline", "web", "myth", "account", "decision", "review")
MODE_LABELS = {"timeline": "Timeline", "web": "Cause web", "myth": "Myth or record", "account": "Whose account?",
               "decision": "Decision points", "review": "Review"}
STRENGTH_LABELS = {"direct": ("Direct cause", "\u21d2"), "contributing": ("Contributing cause", "\u21e2")}
STRENGTH_MEANING = {
    "direct": "The sources treat this as the immediate trigger. Other causes still matter.",
    "contributing": "The sources name this as one factor among several, not the whole story.",
}
MAX_IDS = 2000
MAX_BOOKMARKS = 20
BOOKMARK_NAME_MAX = 30
CONFIDENCE_LABELS = {
    "documented": ("Documented", "✔"),
    "disputed": ("Disputed", "≈"),
    "traditional-but-doubtful": ("Traditional but doubtful", "?"),
}

SETS = {}            # set id -> ChronicleSet (only validated sets are ever here)
SET_ORDER = []
LOAD_PROBLEMS = []   # human-readable problems from sets that failed validation
S = {}               # progress state, see _blank_state(); filled by reset_engine(), never replaced


# --------------------------------------------------------------------------
# Loading sets


def load_sets(root):
    """Load every set listed in <root>/index.json. A set that fails validation is skipped and reported."""
    SETS.clear()          # cleared in place, never rebound: other modules hold these same objects
    SET_ORDER.clear()
    LOAD_PROBLEMS.clear()
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
            "flags": {"onboarded": False}, "session": None, "wsession": None, "msession": None, "asession": None,
            "dsession": None, "day": 0, "rfeedback": None, "earned": [], "bookmarks": []}


def reset_engine():
    S.clear()             # refilled in place, never rebound: other modules hold this same dict
    S.update(_blank_state())
    for set_id in SET_ORDER:
        _ensure_progress(set_id)


def _ensure_progress(set_id):
    return S["sets"].setdefault(set_id, {"learned": set(), "solved": {}, "revealed": set(), "threads": set(), "sorted": set(),
                                         "wsolved": {}, "msolved": {}, "judged": set(), "asolved": {}, "decided": {}, "srs": {}})


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
    def judged(set_id):
        return _prog(set_id)["judged"]

    @staticmethod
    def account_records(set_id):
        return _prog(set_id)["asolved"]

    @staticmethod
    def decided(set_id):
        return _prog(set_id)["decided"]

    @staticmethod
    def review_records(set_id):
        return _prog(set_id)["srs"]

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
    passages, decisions = set(cset.passage_keys()), set(cset.decision_ids())
    found = (len(prog["learned"]) + len(HELP.people_found(set_id)) + len(HELP.places_found(set_id))
             + len(prog["threads"] & rels) + len(prog["sorted"] & claims) + len(prog["judged"] & passages)
             + len(set(prog["decided"]) & decisions))
    total = len(cset.events) + len(cset.people) + len(cset.places) + len(rels) + len(claims) + len(passages) + len(decisions)
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
        "other_claims": [_claim_view(cset, c) for c in cset.claims_for(event_id) if c["field"] not in ("date",) + tuple(HIDDEN_FIELDS)],
    }


def event_start_text(event):
    if event.get("date"):
        return event["date"]
    return "%s/%s" % (event["start"], event["end"])


_LEGEND = {
    "documented": "Sources agree and the claim is well established.",
    "disputed": "Reputable sources differ. The game shows the competing positions and never picks one for you.",
    "traditional-but-doubtful": "A popular story the sources do not support. It is shown so you can recognise it.",
}
