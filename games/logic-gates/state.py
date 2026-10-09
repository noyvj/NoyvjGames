"""Logic Gates -- the save contract and the validation of everything loaded.

Saved: per-level records (solved, fewest chips, par, hints used, answer used), three lifetime counters, the sandbox's found
truth tables, the board each level was left in, and the level last open. Keys are written only when they differ from the
default, and every field of a loaded blob is checked one by one: one bad entry never costs the good ones. Chip availability
always comes from the solved levels, never from a stored list. Display settings are not here (they are per device)."""

import math

import levels
from sim import Prog, flatten

SCHEMA = 1
SANDBOX = "sandbox"
SANDBOX_INS = ["A", "B", "C"]
SANDBOX_OUTS = ["X", "Y"]
SANDBOX_CAP = 40
MAX_HINT = 3
COUNTER_MAX = 10 ** 7
UNDO_DEPTH = 60


def new_record():
    return {"solved": False, "chips": None, "par": False, "hints": 0, "answer": False}


def new_meta():
    return {"levels": {}, "stats": {"chips": 0, "wires": 0, "flips": 0}, "found": [], "current": levels.LEVELS[0]["id"], "work": {}, "backup": {}}


def empty_circuit():
    return {"chips": [], "wires": {}}


def _int(v, lo, hi, default=0):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return default
    return int(max(lo, min(hi, v)))


def clean_record(data):
    rec = new_record()
    if not isinstance(data, dict):
        return rec
    rec["solved"] = data.get("solved") is True
    chips = data.get("chips")
    rec["chips"] = _int(chips, 0, 500) if isinstance(chips, (int, float)) and not isinstance(chips, bool) else None
    rec["par"] = data.get("par") is True and rec["solved"]
    rec["hints"] = _int(data.get("hints"), 0, MAX_HINT)
    rec["answer"] = data.get("answer") is True
    return rec


def level_view(level_id):
    """The level dict, or a stand-in for the sandbox."""
    if level_id == SANDBOX:
        return {"id": SANDBOX, "name": "Sandbox", "ins": SANDBOX_INS, "outs": SANDBOX_OUTS, "cap": SANDBOX_CAP, "loops": True, "kind": "free"}
    return levels.BY_ID.get(level_id)


def allowed_for(level_id, solved_ids):
    if level_id == SANDBOX:
        return levels.unlocked(solved_ids)
    return levels.allowed_chips(levels.BY_ID[level_id], solved_ids)


def source_ok(src, circuit, level):
    if not isinstance(src, str):
        return False
    if src.startswith("in:"):
        return src[3:] in level["ins"]
    if src.startswith("const:"):
        return src[6:] in ("0", "1")
    cid, _, pin = src.partition(".")
    for chip in circuit["chips"]:
        if str(chip["id"]) == cid:
            d = levels.REGISTRY[chip["type"]]
            return pin in d["outs"]
    return False


def dest_ok(dest, circuit, level):
    if not isinstance(dest, str):
        return False
    if dest.startswith("out:"):
        return dest[4:] in level["outs"]
    cid, _, pin = dest.partition(".")
    for chip in circuit["chips"]:
        if str(chip["id"]) == cid:
            return pin in levels.REGISTRY[chip["type"]]["ins"]
    return False


def has_loop(circuit, level):
    prog = Prog(flatten(circuit, levels.REGISTRY, level["ins"], level["outs"]), level["ins"])
    return prog.order is None


def clean_circuit(data, level, allowed):
    """A board from an untrusted blob: only allowed chip types, no more than the cap, no duplicate ids, only wires that make
    sense, and no loop where the level forbids one. Anything else is dropped, piece by piece."""
    circuit = empty_circuit()
    if not isinstance(data, dict):
        return circuit
    seen = set()
    chips = data.get("chips")
    for item in chips if isinstance(chips, list) else []:
        if len(circuit["chips"]) >= level["cap"]:
            break
        if not isinstance(item, dict):
            continue
        cid, ctype = item.get("id"), item.get("type")
        if isinstance(cid, bool) or not isinstance(cid, int) or not 1 <= cid <= 100000 or cid in seen:
            continue
        if not isinstance(ctype, str) or ctype not in allowed:
            continue
        seen.add(cid)
        circuit["chips"].append({"id": cid, "type": ctype})
    wires = data.get("wires")
    if isinstance(wires, dict):
        for dest in sorted(wires, key=str)[:600]:
            src = wires[dest]
            if not dest_ok(dest, circuit, level) or not source_ok(src, circuit, level):
                continue
            circuit["wires"][dest] = src
            if not level["loops"] and has_loop(circuit, level):
                del circuit["wires"][dest]
    return circuit


def meta_to_dict(meta):
    out = {}
    lv = {}
    for lid, rec in meta["levels"].items():
        d = {}
        if rec["solved"]:
            d["solved"] = True
        if rec["chips"] is not None:
            d["chips"] = rec["chips"]
        if rec["par"]:
            d["par"] = True
        if rec["hints"]:
            d["hints"] = rec["hints"]
        if rec["answer"]:
            d["answer"] = True
        if d:
            lv[lid] = d
    if lv:
        out["levels"] = lv
    stats = {k: v for k, v in meta["stats"].items() if v}
    if stats:
        out["stats"] = stats
    if meta["found"]:
        out["found"] = sorted(meta["found"])
    if meta["current"] != levels.LEVELS[0]["id"]:
        out["current"] = meta["current"]
    work = {k: v for k, v in meta["work"].items() if v["chips"] or v["wires"]}
    if work:
        out["work"] = work
    backup = {k: v for k, v in meta["backup"].items() if v["chips"] or v["wires"]}
    if backup:
        out["backup"] = backup
    return out


def clean_meta(data):
    meta = new_meta()
    if not isinstance(data, dict):
        return meta
    recs = data.get("levels")
    if isinstance(recs, dict):
        for lid, rec in recs.items():
            if lid in levels.BY_ID:
                meta["levels"][lid] = clean_record(rec)
    stats = data.get("stats")
    if isinstance(stats, dict):
        for key in meta["stats"]:
            meta["stats"][key] = _int(stats.get(key), 0, COUNTER_MAX)
    found = data.get("found")
    if isinstance(found, list):
        meta["found"] = sorted({c for c in found if isinstance(c, int) and not isinstance(c, bool) and 0 <= c <= 255})
    solved = [lid for lid, r in meta["levels"].items() if r["solved"]]
    current = data.get("current")
    if current == SANDBOX or current in levels.BY_ID:
        meta["current"] = current
    for key in ("work", "backup"):
        blob = data.get(key)
        if isinstance(blob, dict):
            for lid, circ in blob.items():
                if lid == SANDBOX or lid in levels.BY_ID:
                    cleaned = clean_circuit(circ, level_view(lid), allowed_for(lid, solved))
                    if cleaned["chips"] or cleaned["wires"]:
                        meta[key][lid] = cleaned
    return meta


def merge_meta(mine, theirs):
    """Loading a save keeps the better of each record, adds the counters' maximum and unions the found tables; boards come from
    the save."""
    out = new_meta()
    for lid in set(mine["levels"]) | set(theirs["levels"]):
        a = mine["levels"].get(lid, new_record())
        b = theirs["levels"].get(lid, new_record())
        rec = new_record()
        rec["solved"] = a["solved"] or b["solved"]
        counts = [c for c in (a["chips"], b["chips"]) if c is not None]
        rec["chips"] = min(counts) if counts else None
        rec["par"] = a["par"] or b["par"]
        rec["hints"] = max(a["hints"], b["hints"])
        rec["answer"] = a["answer"] or b["answer"]
        out["levels"][lid] = rec
    for key in out["stats"]:
        out["stats"][key] = max(mine["stats"][key], theirs["stats"][key])
    out["found"] = sorted(set(mine["found"]) | set(theirs["found"]))
    out["current"] = theirs["current"]
    out["work"] = {**mine["work"], **theirs["work"]}
    out["backup"] = {**mine["backup"], **theirs["backup"]}
    return out
