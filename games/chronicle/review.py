"""Chronicle -- spaced review: facts the player has learned come back after gaps that grow each time they are remembered.

The idea (not the code) is Le Champ de Mots' scheduler: an interval ladder, and time that only moves when the player
says so. Here:

  * TIME is a plain `day` counter kept in the save. It moves only when the player presses "Let a day pass". There is no
    wall clock anywhere in the engine, so the schedule is deterministic and testable, and nothing happens to a
    player who is away (no expiry, no countdown, nothing to keep alive).
  * An ITEM is one learned fact: a moment's date ("ev:<event>"), a sorted statement ("my:<claim>"), a found cause link
    ("ln:<relation>") or a decision the player made ("dc:<decision>"). An item the player has never been asked is NEW
    and is ready straight away.
  * The LADDER is the gap in days after each correct answer in a row: 1, 3, 7, 14, 30. A wrong answer sends the item back
    to the first rung and it returns the next day. It is never removed, never counted against the player, and nothing
    is lost: the framing everywhere is "this comes back", never a penalty.
  * A QUESTION is a pure function of (set id, set version, item, how many times it has been asked): fixed options built
    from the set's own data (no free text), distractors drawn by the shared seeded generator. The same inputs give
    the same question on every device. `tests/fixtures/review_questions_v1.json` pins the sample set's.

Nothing here reads a clock or a random state, and nothing here writes anything: game.py owns the progress.
"""

from puzzle import Rng
from setdata import event_key, format_date, year_of

SEED_VERSION = "v1"
LADDER = (1, 3, 7, 14, 30)
KIND_ORDER = ("ev", "my", "ln", "dc")
MAX_DAY = 99999
OPTIONS = 4


def split_key(key):
    kind, _, ident = str(key).partition(":")
    return kind, ident


def all_keys(cset, prog):
    """Every item the player could be asked about right now, in a fixed order: moments by date, then the rest in set order."""
    learned = prog["learned"]
    keys = ["ev:%s" % e for e in cset.event_order if e in learned]
    keys += ["my:%s" % c for c in cset.myth_claim_ids() if c in prog["sorted"]]
    keys += ["ln:%s" % r for r in cset.web_relation_ids() if r in prog["threads"]]
    keys += ["dc:%s" % d for d in cset.decision_ids() if d in prog["decided"]]
    return keys


def new_record():
    return {"step": 0, "due": 0, "last": None, "asked": 0, "right": 0}


def after_answer(rec, day, right):
    """The record after one answer given on `day`. Right: climb a rung. Wrong: back to the first rung, back tomorrow."""
    rec = dict(rec)
    rec["asked"] += 1
    rec["last"] = day
    if right:
        rec["right"] += 1
        rec["step"] += 1
        rec["due"] = day + LADDER[min(rec["step"], len(LADDER)) - 1]
    else:
        rec["step"] = 0
        rec["due"] = day + LADDER[0]
    return rec


def is_settled(rec):
    return bool(rec) and rec["step"] >= len(LADDER)


def interval_text(days):
    return "tomorrow" if days == 1 else "in %d days" % days


def due_keys(cset, prog, srs, day):
    """Items ready on `day` (new ones and those whose gap has passed), earliest due first, then in the fixed item order."""
    order = {k: i for i, k in enumerate(all_keys(cset, prog))}
    ready = [k for k in order if srs.get(k, {"due": 0})["due"] <= day]
    return sorted(ready, key=lambda k: (srs.get(k, {"due": 0})["due"], order[k]))


def _date_label(cset, event_id):
    return format_date(cset.events[event_id].get("date") or "%s/%s" % (cset.events[event_id]["start"], cset.events[event_id]["end"]))


def make_question(cset, prog, key, asked, labels):
    """The question for one item. `labels` = {"confidence": {id: words}, "strength": {id: words}} (supplied by game.py).
    Returns None if the item cannot yet be asked fairly (for example fewer than three other moments to use as wrong dates)."""
    kind, ident = split_key(key)
    rng = Rng("chronicle-review|%s|%s|%s|%s|%d" % (SEED_VERSION, cset.id, cset.version, key, asked))
    if kind == "ev":
        e = cset.events.get(ident)
        if e is None or ident not in prog["learned"]:
            return None
        mine = _date_label(cset, ident)
        pool = [o for o in cset.event_order if o != ident and o in prog["learned"] and _date_label(cset, o) != mine
                and year_of(cset.events[o]) != year_of(e)]
        seen, uniq = set(), []
        for o in pool:
            lab = _date_label(cset, o)
            if lab not in seen:
                seen.add(lab)
                uniq.append(o)
        if len(uniq) < OPTIONS - 1:
            return None
        opts = rng.shuffle([ident] + rng.sample(uniq, OPTIONS - 1))
        where = e["title"]
        return {"key": key, "kind": kind, "prompt": "When did this happen?", "context": where,
                "options": [{"id": o, "label": _date_label(cset, o)} for o in opts], "answer": ident}
    if kind == "my":
        c = cset.claims.get(ident)
        if c is None or ident not in prog["sorted"]:
            return None
        return {"key": key, "kind": kind, "prompt": "How sure are the sources about this statement?", "context": c["text"],
                "options": [{"id": b, "label": labels["confidence"][b]} for b in ("documented", "disputed", "traditional-but-doubtful")],
                "answer": c["confidence"]}
    if kind == "ln":
        r = cset.relation_by_id.get(ident)
        if r is None or ident not in prog["threads"]:
            return None
        ctx = "%s led to %s." % (cset.events[r["from"]]["title"], cset.events[r["to"]]["title"])
        return {"key": key, "kind": kind, "prompt": "How does this set describe that cause link?", "context": ctx,
                "options": [{"id": s, "label": labels["strength"][s]} for s in ("direct", "contributing")], "answer": r["strength"]}
    if kind == "dc":
        d = cset.decision(ident)
        if d is None or ident not in prog["decided"]:
            return None
        from decision import option_order
        by_id = {o["id"]: o for o in d["options"]}
        return {"key": key, "kind": kind, "prompt": "What did %s choose?" % d["who"], "context": d["title"],
                "options": [{"id": o, "label": by_id[o]["text"]} for o in option_order(cset, ident)], "answer": d["chosen"]}
    return None


def claim_for(cset, key):
    """The claim whose sources the page shows after the answer."""
    kind, ident = split_key(key)
    if kind == "ev":
        return cset.date_claim(ident)
    if kind == "my":
        return cset.claims.get(ident)
    if kind == "ln":
        return cset.claims.get(cset.relation_by_id[ident]["claim"])
    if kind == "dc":
        return cset.claims.get(cset.decision(ident)["claims"]["choice"])
    return None


def ready_questions(cset, prog, srs, day, labels, limit=None):
    """[(key, question)] for items ready on `day` whose question can be built, in schedule order."""
    out = []
    for key in due_keys(cset, prog, srs, day):
        rec = srs.get(key) or new_record()
        q = make_question(cset, prog, key, rec["asked"], labels)
        if q is not None:
            out.append((key, q))
            if limit and len(out) >= limit:
                break
    return out
