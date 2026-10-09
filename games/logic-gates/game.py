"""Logic Gates -- the one entry point: handle(json) -> json, get_state(), load_state().

The page sends an action and draws what comes back; every rule lives in the modules this imports. Everything here is a pure function of
the wiring and the saved record: no randomness, no clock."""

import copy
import json

import achievements
import check
import info
import levels
import render
import state
import words
from sim import Sim

meta = state.new_meta()
history = []            # earlier boards of the open level, for Undo (not saved)
armed = None            # a source pin picked up, waiting for an input pin
target = None           # an input pin picked, waiting for a source
note = ""
last_result = None
probe = {"inputs": {}, "sim": None, "step": None, "prog": None}

SIXTEEN = ("FALSE", "A AND B", "A AND NOT B", "A", "NOT A AND B", "B", "A XOR B", "A OR B",
           "A NOR B", "A XNOR B", "NOT B", "A OR NOT B", "NOT A", "NOT A OR B", "A NAND B", "TRUE")


# ---- small helpers -------------------------------------------------------------------------------
def _cur():
    return state.level_view(meta["current"])


def _board():
    return meta["work"].setdefault(meta["current"], state.empty_circuit())


def _solved_ids():
    return [lid for lid, r in meta["levels"].items() if r["solved"]]


def _rec(level_id):
    return meta["levels"].setdefault(level_id, state.new_record())


def _allowed():
    return state.allowed_for(meta["current"], _solved_ids())


def _is_open(level_id):
    if level_id == state.SANDBOX:
        return True
    lv = levels.BY_ID.get(level_id)
    return lv is not None and (levels.is_open(lv, _solved_ids()) or meta["levels"].get(level_id, {}).get("solved", False))


def _first_open():
    for lv in levels.LEVELS:
        if not _rec(lv["id"]).get("solved") and levels.is_open(lv, _solved_ids()):
            return lv["id"]
    return levels.LEVELS[0]["id"]


def _fix_current():
    if meta["current"] != state.SANDBOX and not _is_open(meta["current"]):
        meta["current"] = _first_open()


def code_name(code):
    """The name of a two-input function's table code, or None for a table that depends on C."""
    if not achievements.is_two_input(code):
        return None
    idx = ((code >> 0) & 1) * 8 + ((code >> 2) & 1) * 4 + ((code >> 4) & 1) * 2 + ((code >> 6) & 1)
    return SIXTEEN[idx]


# ---- probe ---------------------------------------------------------------------------------------
def _prog():
    return check.build_prog(_cur(), _board())


def _run_script(upto):
    level = _cur()
    prog = probe["prog"]
    sim = Sim(prog)
    inputs = {n: 0 for n in level["ins"]}
    for step in level["steps"][:upto + 1]:
        inputs.update(step["set"])
        sim.step(inputs)
    probe["inputs"] = inputs
    probe["sim"] = sim


def _probe_rebuild():
    level = _cur()
    probe["prog"] = _prog()
    if probe["step"] is not None and level.get("steps"):
        probe["step"] = min(probe["step"], len(level["steps"]) - 1)
        _run_script(probe["step"])
    else:
        probe["step"] = None
        probe["sim"] = Sim(probe["prog"])
        probe["sim"].step(probe["inputs"])


def _value(src):
    sim = probe["sim"]
    if not src:
        return 0
    if src.startswith("in:"):
        return 1 if probe["inputs"].get(src[3:]) else 0
    if src.startswith("const:"):
        return int(src[6:])
    return sim.top_value(src) if sim else 0


# ---- evaluation ----------------------------------------------------------------------------------
def _evaluate():
    """Re-check the board, keep the record and the sandbox log current, and remember what to say."""
    global last_result, note
    level = _cur()
    _probe_rebuild()
    if meta["current"] == state.SANDBOX:
        last_result = None
        _sandbox_found()
        return
    result = check.check_level(level, _board())
    last_result = result
    rec = _rec(level["id"])
    count = len(_board()["chips"])
    if result["ok"]:
        first = not rec["solved"]
        rec["solved"] = True
        rec["chips"] = count if rec["chips"] is None else min(rec["chips"], count)
        if count <= level["par"] and not rec["answer"] and not rec["par"]:
            rec["par"] = True
            note = note or (f"Par: {count} chips." if not first else "")
        if first:
            gift = f" You keep the {levels.REGISTRY[level['unlock']]['label']} chip." if level["unlock"] else ""
            note = f"Level solved with {count} chips.{gift}" + (" That is par." if rec["par"] else "")


def _sandbox_found():
    global note
    level = _cur()
    circuit = _board()
    prog = probe["prog"]
    new = []
    for k, out in enumerate(level["outs"]):
        if not circuit["wires"].get("out:" + out):
            continue
        code, ok = 0, True
        if prog.is_simple:
            bits = check._input_bits(3)
            got = prog.truth_rows(dict(zip(level["ins"], bits)), 8)[out]
            code = got
        else:
            for r in range(8):
                sim = Sim(prog)
                if not sim.step(check.row_values(level["ins"], r)):
                    ok = False
                    break
                if sim.out(out):
                    code |= 1 << r
        if ok and code not in meta["found"]:
            meta["found"].append(code)
            meta["found"].sort()
            name = code_name(code)
            new.append(name if name else "a three-input table")
    if new:
        note = "New truth table: " + ", ".join(new) + "."


# ---- editing -------------------------------------------------------------------------------------
def _push_history():
    history.append(copy.deepcopy(_board()))
    if len(history) > state.UNDO_DEPTH:
        del history[0]


def _chip_by_id(cid):
    for c in _board()["chips"]:
        if c["id"] == cid:
            return c
    return None


def _a_add(req):
    ctype = req.get("type")
    level = _cur()
    if ctype not in _allowed():
        return "That chip is not on your shelf for this level."
    circuit = _board()
    if len(circuit["chips"]) >= level["cap"]:
        return f"The board is full ({level['cap']} chips). Remove one first."
    _push_history()
    cid = max([c["id"] for c in circuit["chips"]] + [0]) + 1
    circuit["chips"].append({"id": cid, "type": ctype})
    meta["stats"]["chips"] += 1
    return None


def _drop_wires_of(circuit, cid):
    prefix = f"{cid}."
    for dest in [d for d, s in circuit["wires"].items() if d.startswith(prefix) or s.startswith(prefix)]:
        del circuit["wires"][dest]


def _a_remove(req):
    circuit = _board()
    cid = req.get("id")
    if _chip_by_id(cid) is None:
        return "No such chip."
    _push_history()
    circuit["chips"] = [c for c in circuit["chips"] if c["id"] != cid]
    _drop_wires_of(circuit, cid)
    return None


def _set_wire(dest, src):
    """Change one wire. Returns an error string or None."""
    level, circuit = _cur(), _board()
    if not state.dest_ok(dest, circuit, level):
        return "That pin does not exist."
    if src in (None, ""):
        if dest in circuit["wires"]:
            _push_history()
            del circuit["wires"][dest]
        return None
    if not state.source_ok(src, circuit, level):
        return "That source does not exist."
    if circuit["wires"].get(dest) == src:
        return None
    snapshot = copy.deepcopy(circuit)
    circuit["wires"][dest] = src
    if not level["loops"] and state.has_loop(circuit, level):
        meta["work"][meta["current"]] = snapshot
        return "That would loop the wire back on itself. Loops are for the memory boards and the sandbox."
    history.append(snapshot)
    if len(history) > state.UNDO_DEPTH:
        del history[0]
    meta["stats"]["wires"] += 1
    return None


def _a_wire(req):
    return _set_wire(req.get("dest"), req.get("src"))


def _a_pick(req):
    """A tap on a pin in the drawing. A source arms; an input pin takes the armed source (and stays armed for the next pin)."""
    global armed, target
    pin = req.get("pin")
    if not isinstance(pin, str) or pin[:2] not in ("s:", "d:"):
        return "Not a pin."
    ident = pin[2:]
    if pin[:2] == "s:":
        if target is not None:
            dest, target = target, None
            return _set_wire(dest, ident)
        armed = None if armed == ident else ident
        return None
    if armed is not None:
        return _set_wire(ident, armed)
    target = None if target == ident else ident
    return None


def _a_clear_pick(_req):
    global armed, target
    armed = target = None
    return None


def _a_undo(_req):
    if not history:
        return "Nothing to undo."
    meta["work"][meta["current"]] = history.pop()
    return None


def _a_clear(_req):
    circuit = _board()
    if not circuit["chips"] and not circuit["wires"]:
        return None
    meta["backup"][meta["current"]] = copy.deepcopy(circuit)
    history.clear()
    meta["work"][meta["current"]] = state.empty_circuit()
    return None


def _a_restore(_req):
    saved = meta["backup"].get(meta["current"])
    if not saved:
        return "Nothing to restore."
    history.append(copy.deepcopy(_board()))
    meta["work"][meta["current"]] = copy.deepcopy(saved)
    return None


def _a_start(req):
    global armed, target
    lid = req.get("level")
    if lid != state.SANDBOX and lid not in levels.BY_ID:
        return "Unknown level."
    if not _is_open(lid):
        missing = levels.missing_chips(levels.BY_ID[lid], _solved_ids())
        return "This level is waiting for: " + ", ".join(levels.REGISTRY[c]["label"] for c in missing) + "."
    meta["current"] = lid
    history.clear()
    armed = target = None
    probe["inputs"] = {}
    probe["step"] = None
    return None


def _a_next(_req):
    nxt = _first_open()
    if _rec(nxt).get("solved"):
        return "Every level you can open is already solved."
    return _a_start({"level": nxt})


def _a_flip(req):
    name = req.get("name")
    level = _cur()
    if name not in level["ins"]:
        return "No such switch."
    if probe["step"] is not None:
        probe["step"] = None
    probe["inputs"][name] = 0 if probe["inputs"].get(name) else 1
    meta["stats"]["flips"] += 1
    probe["sim"].step(probe["inputs"])
    return "NOEVAL"


def _a_script(req):
    level = _cur()
    if level.get("kind") != "seq":
        return "This level has no script."
    k = req.get("step")
    if isinstance(k, bool) or not isinstance(k, int) or not 0 <= k < len(level["steps"]):
        return "No such step."
    probe["step"] = k
    _run_script(k)
    return "NOEVAL"


def _a_manual(_req):
    probe["step"] = None
    probe["inputs"] = {}
    probe["sim"] = Sim(probe["prog"])
    probe["sim"].step(probe["inputs"])
    return "NOEVAL"


def _a_hint(_req):
    level = _cur()
    if meta["current"] == state.SANDBOX:
        return "The sandbox has no hints."
    rec = _rec(level["id"])
    if rec["hints"] >= state.MAX_HINT:
        return "That is every hint there is."
    rec["hints"] += 1
    return "NOEVAL"


def _a_place_answer(_req):
    level = _cur()
    if meta["current"] == state.SANDBOX:
        return "The sandbox has no answer."
    rec = _rec(level["id"])
    if rec["hints"] < state.MAX_HINT:
        return "Ask for the hints first."
    _push_history()
    rec["answer"] = True
    meta["work"][level["id"]] = copy.deepcopy(level["ref"])
    meta["stats"]["chips"] += len(level["ref"]["chips"])
    meta["stats"]["wires"] += len(level["ref"]["wires"])
    return None


ACTIONS = {"add": _a_add, "remove": _a_remove, "wire": _a_wire, "pick": _a_pick, "cancel": _a_clear_pick, "undo": _a_undo,
           "clear": _a_clear, "restore": _a_restore, "start": _a_start, "next": _a_next, "flip": _a_flip, "script": _a_script,
           "manual": _a_manual, "hint": _a_hint, "answer": _a_place_answer}
READ_ONLY = ("open", "reset")


# ---- the view ------------------------------------------------------------------------------------
def _options(circuit, level, dest):
    """Every source a pin could take, as {value, label}."""
    opts = [{"value": "", "label": "nothing (floats at 0)"}]
    opts += [{"value": "in:" + n, "label": "Switch " + n} for n in level["ins"]]
    opts += [{"value": "const:0", "label": "Tied to 0"}, {"value": "const:1", "label": "Tied to 1"}]
    banned = set()
    if not level["loops"]:
        banned = _descendants(circuit, dest)
    for chip in circuit["chips"]:
        if chip["id"] in banned:
            continue
        d = levels.REGISTRY[chip["type"]]
        for pin in d["outs"]:
            label = f"Chip {chip['id']} ({d['label']})" + (f" output {pin}" if len(d["outs"]) > 1 else "")
            opts.append({"value": f"{chip['id']}.{pin}", "label": label})
    return opts


def _descendants(circuit, dest):
    """Chip ids that cannot feed `dest` without a loop: the chip itself and everything it feeds."""
    if dest.startswith("out:"):
        return set()
    start = int(dest.split(".")[0])
    feeds = {}
    for d, s in circuit["wires"].items():
        if d.startswith("out:") or s.startswith(("in:", "const:")):
            continue
        feeds.setdefault(int(s.split(".")[0]), set()).add(int(d.split(".")[0]))
    seen, stack = {start}, [start]
    while stack:
        for nxt in feeds.get(stack.pop(), ()):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def _board_view():
    level, circuit = _cur(), _board()
    chips = []
    for chip in circuit["chips"]:
        d = levels.REGISTRY[chip["type"]]
        pins = []
        for pin in d["ins"]:
            dest = f"{chip['id']}.{pin}"
            src = circuit["wires"].get(dest)
            pins.append({"pin": pin, "dest": dest, "src": src or "", "text": words.src_label(src, circuit), "options": _options(circuit, level, dest)})
        chips.append({"id": chip["id"], "type": chip["type"], "label": d["label"], "blurb": d["blurb"], "ins": pins, "outs": list(d["outs"])})
    lamps = []
    for name in level["outs"]:
        dest = "out:" + name
        src = circuit["wires"].get(dest)
        lamps.append({"name": name, "dest": dest, "src": src or "", "text": words.src_label(src, circuit), "value": _value(src) if src else 0,
                      "options": _options(circuit, level, dest)})
    return {"chips": chips, "lamps": lamps, "count": len(circuit["chips"]), "cap": level["cap"], "wires": len(circuit["wires"])}


def _picker():
    solved = _solved_ids()
    out = []
    for ch in levels.CHAPTERS:
        items = []
        for lv in levels.LEVELS:
            if lv["chapter"] != ch["id"]:
                continue
            rec = meta["levels"].get(lv["id"], state.new_record())
            miss = [levels.REGISTRY[c]["label"] for c in levels.missing_chips(lv, solved)]
            items.append({"id": lv["id"], "name": lv["name"], "index": lv["index"], "solved": rec["solved"], "par": rec["par"],
                          "open": not miss or rec["solved"], "missing": miss, "current": lv["id"] == meta["current"],
                          "unlock": levels.REGISTRY[lv["unlock"]]["label"] if lv["unlock"] else None})
        out.append({"id": ch["id"], "name": ch["name"], "intro": ch["intro"], "levels": items,
                    "cleared": sum(1 for i in items if i["solved"]), "total": len(items)})
    return out


def _shelf():
    have = set(levels.unlocked(_solved_ids()))
    return [{"type": c, "label": levels.REGISTRY[c]["label"], "blurb": levels.REGISTRY[c]["blurb"], "ins": levels.REGISTRY[c]["ins"],
             "outs": levels.REGISTRY[c]["outs"], "unlocked": c in have} for c in levels.CHIP_ORDER]


def _table(level):
    result = last_result
    if level.get("kind") == "free":
        return None
    out = {"ins": level["ins"], "outs": level["outs"], "kind": level["kind"], "ok": result["ok"], "right": result["right"], "total": result["total"],
           "message": result["message"], "rows": result["rows"], "settled": result["settled"]}
    return out


def view():
    level = _cur()
    circuit = _board()
    if probe["prog"] is None:
        _probe_rebuild()
    svg, width = render.draw(level, circuit, _value, probe["inputs"], armed, target)
    recs = meta["levels"]
    solved = sum(1 for r in recs.values() if r["solved"])
    sandbox = meta["current"] == state.SANDBOX
    rec = recs.get(level["id"], state.new_record())
    v = {
        "note": note, "svg": svg, "svg_width": width, "armed": armed, "target": target,
        "stats": {"solved": solved, "total": len(levels.LEVELS), "par": sum(1 for r in recs.values() if r["par"]), "chips": meta["stats"]["chips"],
                  "wires": meta["stats"]["wires"], "flips": meta["stats"]["flips"], "found": len(meta["found"]),
                  "sixteen": achievements.sixteen_found(meta["found"])},
        "goals": achievements.goals(meta), "achievements": achievements.view(meta),
        "picker": _picker(), "shelf": _shelf(),
        "board": _board_view(), "text": words.describe(circuit, level["outs"]),
        "palette": [{"type": c, "label": levels.REGISTRY[c]["label"], "blurb": levels.REGISTRY[c]["blurb"], "built": levels.REGISTRY[c]["kind"] == "net"}
                    for c in _allowed()],
        "probe": {"inputs": {n: 1 if probe["inputs"].get(n) else 0 for n in level["ins"]}, "step": probe["step"],
                  "settled": probe["sim"].settled if probe["sim"] else True},
        "can_undo": bool(history), "can_restore": bool(meta["backup"].get(meta["current"])),
        "level": {"id": level["id"], "name": level["name"], "ins": level["ins"], "outs": level["outs"], "cap": level["cap"], "loops": level["loops"],
                  "sandbox": sandbox, "kind": level.get("kind", "free")},
        "table": _table(level) if not sandbox else None,
        "sandbox": {"found": len(meta["found"]), "total": 256,
                    "sixteen": [{"name": n, "found": any(code_name(c) == n for c in meta["found"])} for n in SIXTEEN]},
        "info": info.view(),
        "story": [{"name": lv["name"], "text": lv["log"]} for lv in levels.LEVELS if recs.get(lv["id"], {}).get("solved")],
    }
    if sandbox:
        v["level"].update({"goal": "A free board: switches A, B and C, lamps X and Y, every chip you have earned, loops allowed. Every new truth table a lamp makes is logged.",
                           "chapter": 0, "index": 0, "par": None, "chapter_name": "Sandbox", "intro": "", "log": "", "unlock": None})
        v["hints"] = None
    else:
        ch = levels.CHAPTERS[level["chapter"] - 1]
        v["level"].update({"goal": level["goal"], "chapter": level["chapter"], "chapter_name": ch["name"], "index": level["index"], "par": level["par"],
                           "intro": ch["intro"] if level["index"] == next(lv["index"] for lv in levels.LEVELS if lv["chapter"] == level["chapter"]) else "",
                           "log": level["log"], "unlock": levels.REGISTRY[level["unlock"]]["label"] if level["unlock"] else None,
                           "steps": len(level["steps"]) if level["steps"] else 0, "record": rec})
        v["hints"] = {"rung": rec["hints"], "nudge": level["nudge"] if rec["hints"] >= 1 else None,
                      "hint": level["hint"] if rec["hints"] >= 2 else None,
                      "answer": words.describe(level["ref"], level["outs"]) if rec["hints"] >= 3 else None,
                      "answer_used": rec["answer"]}
    return v


def handle(request_json):
    global note
    note = ""
    try:
        request = json.loads(request_json)
        action = request.get("action")
    except (ValueError, AttributeError):
        return json.dumps({"error": "bad request"})
    if action == "reset":
        _reset()
    elif action in ACTIONS:
        error = ACTIONS[action](request)
        if error and error != "NOEVAL":
            note = error
        elif error is None:
            _fix_current()
            _evaluate()
    elif action is not None and action != "open":
        return json.dumps({"error": "unknown action"})
    if action in (None, "open", "reset") or probe["prog"] is None:
        _fix_current()
        _evaluate()
    return json.dumps(view())


def _reset():
    global meta, armed, target, last_result
    meta = state.new_meta()
    history.clear()
    armed = target = None
    last_result = None
    probe.update({"inputs": {}, "sim": None, "step": None, "prog": None})


def get_state():
    data = {"schema": state.SCHEMA}
    m = state.meta_to_dict(meta)
    if m:
        data["meta"] = m
    earned = achievements.earned(meta)
    if earned:
        data["achievements_earned"] = earned       # a write-only projection for the hub dashboard, never read back
    return data


def load_state(data):
    """Merge a saved state in: records keep the better of each, counters keep the larger, found tables union; boards come from the save."""
    global meta, armed, target
    try:
        incoming = state.clean_meta((data or {}).get("meta"))
        meta = state.merge_meta(meta, incoming)
        history.clear()
        armed = target = None
        probe.update({"inputs": {}, "sim": None, "step": None, "prog": None})
        _fix_current()
        _evaluate()
    except (ValueError, TypeError, AttributeError, KeyError, OverflowError):
        pass
    _refresh_view()


def _refresh_view():
    """Ask the page to redraw after a save is loaded (the save widget calls load_state directly). A no-op under plain CPython."""
    try:
        import js
        refresh = getattr(js.window, "logicGatesRefresh", None)
        if refresh is not None:
            refresh()
    except Exception:
        pass
