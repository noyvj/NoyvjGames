"""Heist Committee -- the engine's single entry point (the Signal / Lexis pattern).

The view (app.js) never reads engine objects: it sends one JSON string to `handle` and draws the JSON that comes
back. `get_state()` / `load_state()` are the shared save widget's contract (planning/SAVE-BUTTON-INTEGRATION.md).
The heist itself is a pure function (engine.py), so a save only keeps the plan, the seed and a cursor.

A career is a run of standalone jobs. A job moves through phases:
  board     pick a contract
  scout     buy intel about the target (the top complication is always free)
  recruit   choose five of eight candidates, equip gear
  plan      fill the timeline, undo freely
  playback  the heist resolves beat by beat
  payout    loot, heat, damages and the write-up

Requests carry `"action"`:
  open | new_career {seed}
  take_job {target} | scout {level} | to_recruit | hire {crew} | background {crew} | gear {gear}
  confirm_crew | place {lane, beat, cell} | clear {lane, beat} | move_lane {lane, dir} | clear_plan
  undo | redo | move_cell {lane, beat, to_lane, to_beat} | abandon | back_to_board
"""

import json
import time

import content as content_mod
import engine
import plancheck
import planops
from engine import LANES

C = content_mod.load()

SCHEMA = 1
START_CASH = 300
BACKGROUND_FEE = 10
MAX_GEAR = 2
OFFER_SIZE = 8
PHASES = ("board", "scout", "recruit", "plan", "playback", "payout")
UNDO_LIMIT = 60


def _default_meta():
    return {"jobs_done": 0, "known_quirks": [], "seen_complications": [], "seen_traits": []}


class Career:
    def __init__(self, seed=1):
        self.career_seed = seed
        self.cash = START_CASH
        self.jobs_started = 0
        self.meta = _default_meta()
        self.job = None


career = Career()
_undo = []
_redo = []


# --- small helpers ------------------------------------------------------------------------------
def _int(value, lo, hi, default):
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return max(lo, min(hi, value))


def _job_seed():
    return int(engine.roll(career.career_seed, "job", career.jobs_started) * 2147483647)


def _target():
    return C.targets[career.job["target"]]


def _n_beats():
    return len(_target()["beats"])


def _scout_levels(target):
    return target.get("scout", {}).get("levels", [{"cost": 0, "reveal": 1}])


def _pool_sorted(target):
    pool = [C.complications[i] for i in target.get("pool", []) if i in C.complications]
    order = {c["id"]: i for i, c in enumerate(pool)}
    return sorted(pool, key=lambda c: (-c.get("weight", 1), order[c["id"]]))


def _known_complications(job):
    target = C.targets[job["target"]]
    levels = _scout_levels(target)
    level = max(0, min(job.get("scout", 0), len(levels) - 1))
    reveal = int(levels[level].get("reveal", 1))
    pool = _pool_sorted(target)
    known = [c["id"] for c in pool[:reveal]]
    for cid in career.meta["seen_complications"]:
        if cid in target.get("pool", []) and cid not in known:
            known.append(cid)
    return known


def _offer_for(job):
    """Eight candidates, seeded, always covering all five roles."""
    ranked = sorted(C.crew_order, key=lambda cid: engine.roll(job["seed"], "offer", cid))
    chosen = []
    for role in C.roles:
        for cid in ranked:
            if C.crew[cid]["role"] == role:
                chosen.append(cid)
                break
    for cid in ranked:
        if len(chosen) >= OFFER_SIZE:
            break
        if cid not in chosen:
            chosen.append(cid)
    return sorted(chosen, key=lambda cid: C.crew_order.index(cid))


def _hidden_quirks(job):
    known = set(career.meta["known_quirks"])
    return [cid for cid in job.get("crew", []) if cid not in known]


def _relations():
    return {}


def _gear_cost(job):
    return sum(C.gear[g]["cost"] for g in job.get("gear", []))


def _fees(job):
    return sum(C.crew[c]["fee"] for c in job.get("crew", []))


def _new_job(target_id):
    career.jobs_started += 1
    job = {"phase": "scout", "target": target_id, "seed": _job_seed(), "scout": 0, "offer": [], "crew": [],
           "gear": [], "plan": None, "attempt": 0, "paid": False}
    return job


def _snapshot_undo():
    _undo.append(json.dumps(career.job["plan"]))
    del _undo[:-UNDO_LIMIT]
    del _redo[:]


# --- views --------------------------------------------------------------------------------------
def _crew_card(cid, known):
    m = C.crew[cid]
    role = C.roles[m["role"]]
    trait = C.traits[m["trait"]]
    quirk = C.traits[m["quirk"]]
    return {
        "id": cid, "name": m["name"], "short": m["short"], "role": m["role"], "role_label": role["label"],
        "role_icon": role["icon"], "shape": role["shape"], "letter": m["short"][0].upper(), "fee": m["fee"],
        "skills": [{"id": s, "label": C.skills[s]["label"], "icon": C.skills[s]["icon"], "pips": m["skills"].get(s, 0)}
                   for s in C.skills if m["skills"].get(s, 0) > 0],
        "trait": {"id": m["trait"], "name": trait["name"], "icon": trait["icon"], "text": trait["text"]},
        "quirk": ({"id": m["quirk"], "name": quirk["name"], "icon": quirk["icon"], "text": quirk["text"]}
                  if cid in known else None),
        "quirk_known": cid in known, "voice": m["voice"],
        "rivals": [C.crew[o]["short"] for o in m.get("rival_of", []) if o in C.crew],
        "mentors": [C.crew[o]["short"] for o in m.get("mentor_of", []) if o in C.crew],
    }


def _target_card(tid):
    t = C.targets[tid]
    return {"id": tid, "name": t["name"], "tier": t["tier"], "blurb": t["blurb"], "beats": len(t["beats"]),
            "consolation": t["consolation"], "budget": t["budget"], "intro": t.get("intro", ""),
            "prize": sum(r.get("value", 0) for r in t["requirements"] if not r.get("optional")),
            "scout_levels": [{"cost": lv["cost"], "reveal": lv["reveal"]} for lv in _scout_levels(t)]}


def _tray():
    out = []
    for aid, a in C.actions.items():
        if a["kind"] == "wait":
            continue
        skill = a.get("skill")
        out.append({"id": aid, "name": a["name"], "icon": a["icon"], "kind": a["kind"], "duration": a.get("duration", 1),
                    "skill": C.skills[skill]["label"] if skill in C.skills else ("Best skill" if skill == "best" else ""),
                    "difficulty": a.get("difficulty", 0), "blurb": a["blurb"], "noise": a.get("noise", 0),
                    "suspicion": a.get("suspicion", 0), "needs": [C.tag_label(t) for t in a.get("needs", [])]})
    return out


def _plan_view(job):
    target = C.targets[job["target"]]
    n = len(target["beats"])
    plan = engine.clean_plan(C, job["plan"] or engine.empty_plan(n), n)
    crew_ids = job["crew"]
    messages, preview, pairs = plancheck.check(C, job["target"], crew_ids, plan, job.get("gear", []), _relations(),
                                               _hidden_quirks(job))
    slots_by_lane, _ = engine.build_slots(C, plan, n)
    lanes = []
    for lane in range(LANES):
        cells = [{"cell": None, "role": "empty", "span": 1} for _ in range(n)]
        for slot in slots_by_lane[lane]:
            arg = slot["arg"]
            cell = slot["action"]["id"] + (":" + arg if arg else "")
            odds = preview[lane].get(slot["start"])
            entry = {"cell": cell, "role": "start", "span": slot["dur"], "action": slot["action"]["id"],
                     "name": slot["action"]["name"], "icon": slot["action"]["icon"], "kind": slot["action"]["kind"],
                     "arg": arg, "arg_label": C.kinds[arg]["label"] if arg in C.kinds else "",
                     "arg_icon": C.kinds[arg]["icon"] if arg in C.kinds else "",
                     "odds": ({"word": odds["word"], "label": C.lines["odds_words"][odds["word"]], "margin": odds["margin"],
                               "parts": [[p[0], p[1]] for p in odds["parts"]]} if odds else None)}
            cells[slot["start"]] = entry
            for b in range(slot["start"] + 1, slot["end"] + 1):
                cells[b] = {"cell": None, "role": "cont", "span": 1, "of": slot["start"]}
        lanes.append(cells)
    known = _known_complications(job)
    scouted_kinds = set()
    for cid in known:
        scouted_kinds.update(C.complications[cid].get("kinds", []))
    return {
        "lanes": lanes,
        "messages": messages,
        "pairs": pairs,
        "cover": [{"id": k, "label": C.kinds[k]["label"], "icon": C.kinds[k]["icon"], "scouted": k in scouted_kinds}
                  for k in target.get("cover_options", []) if k in C.kinds],
        "can_undo": bool(_undo), "can_redo": bool(_redo),
        "cells_used": sum(1 for lane in plan["lanes"] for c in lane if c),
    }


def _scout_view(job):
    target = C.targets[job["target"]]
    known = _known_complications(job)
    levels = _scout_levels(target)
    details = target.get("scout", {}).get("details", [])
    level = max(0, min(job.get("scout", 0), len(levels) - 1))
    shown_details = details[:level + 1]
    return {
        "level": level, "max_level": len(levels) - 1,
        "complications": [{"id": cid, "name": C.complications[cid]["name"], "beats": C.complications[cid]["beats"],
                           "kinds": [{"id": k, "label": C.kinds[k]["label"], "icon": C.kinds[k]["icon"]}
                                     for k in C.complications[cid].get("kinds", []) if k in C.kinds],
                           "met_before": cid in career.meta["seen_complications"]} for cid in known],
        "unknown_count": max(0, len(target.get("pool", [])) - len(known)),
        "details": shown_details,
        "next": ({"level": level + 1, "cost": levels[level + 1]["cost"] - levels[level]["cost"],
                  "reveal": levels[level + 1]["reveal"]} if level + 1 < len(levels) else None),
    }


def _view(note=None):
    job = career.job
    known = set(career.meta["known_quirks"])
    view = {"schema": SCHEMA, "phase": job["phase"] if job else "board", "cash": career.cash,
            "jobs_done": career.meta["jobs_done"], "note": note or ""}
    if not job:
        view["board"] = [_target_card(t) for t in C.target_order]
        return view
    target = C.targets[job["target"]]
    view["target"] = _target_card(job["target"])
    view["beats"] = [{"name": b["name"], "tags": [{"id": t, "label": C.tag_label(t), "icon": C.tags[t]["icon"]}
                                                  for t in b.get("tags", [])], "note": b.get("note", "")}
                     for b in target["beats"]]
    view["requirements"] = [{"id": r["id"], "label": r["label"], "optional": bool(r.get("optional"))} for r in target["requirements"]]
    view["scout"] = _scout_view(job)
    view["seed"] = job["seed"]
    view["fees"] = _fees(job)
    view["gear_cost"] = _gear_cost(job)
    phase = job["phase"]
    if phase in ("recruit", "plan", "playback", "payout"):
        view["offer"] = [_crew_card(cid, known) for cid in job["offer"]]
        view["crew_ids"] = list(job["crew"])
        view["gear"] = [{"id": gid, "name": g["name"], "icon": g["icon"], "cost": g["cost"], "text": g["text"],
                         "equipped": gid in job["gear"]} for gid, g in C.gear.items()]
        view["background_fee"] = BACKGROUND_FEE
    if phase in ("plan", "playback", "payout"):
        view["crew"] = [_crew_card(cid, known) for cid in job["crew"]]
        view["tray"] = _tray()
        view["plan"] = _plan_view(job)
    return view


# --- the entry point ----------------------------------------------------------------------------
def handle(request_json):
    try:
        request = json.loads(request_json) if isinstance(request_json, str) else dict(request_json)
    except (ValueError, TypeError):
        return json.dumps({"error": "bad request"})
    if not isinstance(request, dict):
        return json.dumps({"error": "bad request"})
    try:
        return json.dumps(_dispatch(request))
    except Exception as exc:   # a bug must never freeze the page: report it and keep the state
        return json.dumps({"error": "engine error: %s" % exc})


def _dispatch(request):
    global career
    action = str(request.get("action", "open"))
    job = career.job
    note = ""
    if action == "open":
        pass
    elif action == "new_career":
        seed = _int(request.get("seed"), 1, 2147483647, int(time.time()) % 2147483647 or 1)
        career = Career(seed)
        del _undo[:], _redo[:]
    elif action == "take_job":
        tid = str(request.get("target", ""))
        if job is None and tid in C.targets:
            career.job = _new_job(tid)
        else:
            note = "Finish or abandon the current job first."
    elif job is None:
        return {"error": "no job in progress", "view": _view()}
    elif action == "scout":
        note = _do_scout(job, request)
    elif action == "to_recruit":
        if job["phase"] == "scout":
            job["offer"] = _offer_for(job)
            job["phase"] = "recruit"
    elif action == "hire":
        note = _do_hire(job, str(request.get("crew", "")))
    elif action == "background":
        note = _do_background(job, str(request.get("crew", "")))
    elif action == "gear":
        note = _do_gear(job, str(request.get("gear", "")))
    elif action == "confirm_crew":
        note = _do_confirm(job)
    elif action in ("place", "clear", "move_lane", "clear_plan", "undo", "redo", "move_cell"):
        note = _do_plan_edit(job, action, request)
    elif action == "abandon":
        career.job = None
        del _undo[:], _redo[:]
        note = "Job abandoned. The crew fees are gone."
    elif action == "back_to_board":
        if job["phase"] in ("scout", "recruit"):
            career.job = None
            del _undo[:], _redo[:]
    else:
        return {"error": "unknown action %r" % action, "view": _view()}
    return {"view": _view(note), "ok": not note or note.startswith("Job abandoned")}


def _do_scout(job, request):
    if job["phase"] not in ("scout", "recruit", "plan"):
        return ""
    target = _target()
    levels = _scout_levels(target)
    want = _int(request.get("level"), 0, len(levels) - 1, 0)
    have = job.get("scout", 0)
    if want <= have:
        return ""
    cost = levels[want]["cost"] - levels[have]["cost"]
    if cost > career.cash:
        return "Not enough cash for that scouting."
    career.cash -= cost
    job["scout"] = want
    return ""


def _do_hire(job, cid):
    if job["phase"] != "recruit" or cid not in job["offer"]:
        return ""
    if cid in job["crew"]:
        job["crew"].remove(cid)
    elif len(job["crew"]) < LANES:
        job["crew"].append(cid)
    return ""


def _do_background(job, cid):
    if job["phase"] != "recruit" or cid not in job["offer"] or cid in career.meta["known_quirks"]:
        return ""
    if career.cash < BACKGROUND_FEE:
        return "Not enough cash for a background check."
    career.cash -= BACKGROUND_FEE
    career.meta["known_quirks"].append(cid)
    return ""


def _do_gear(job, gid):
    if job["phase"] != "recruit" or gid not in C.gear:
        return ""
    if gid in job["gear"]:
        job["gear"].remove(gid)
    elif len(job["gear"]) < MAX_GEAR:
        job["gear"].append(gid)
    else:
        return "Only %d pieces of gear fit in the van." % MAX_GEAR
    return ""


def _do_confirm(job):
    if job["phase"] != "recruit":
        return ""
    if len(job["crew"]) != LANES:
        return "Choose exactly five crew."
    total = _fees(job) + _gear_cost(job)
    if total > career.cash:
        return "The crew and gear cost %d and the committee has %d." % (total, career.cash)
    career.cash -= total
    job["paid"] = True
    job["phase"] = "plan"
    job["plan"] = engine.empty_plan(_n_beats())
    del _undo[:], _redo[:]
    return ""


def _do_plan_edit(job, action, request):
    if job["phase"] != "plan":
        return ""
    n = _n_beats()
    plan = engine.clean_plan(C, job["plan"], n)
    if action == "undo":
        if _undo:
            _redo.append(json.dumps(plan))
            job["plan"] = json.loads(_undo.pop())
        return ""
    if action == "redo":
        if _redo:
            _undo.append(json.dumps(plan))
            job["plan"] = json.loads(_redo.pop())
        return ""
    lane = _int(request.get("lane"), 0, LANES - 1, -1)
    beat = _int(request.get("beat"), 0, n - 1, -1)
    if action == "place":
        cells = str(request.get("cell", ""))
        default_kind = (_target().get("cover_options") or [None])[0]
        new, err = planops.place(C, plan, n, lane, beat, cells, default_kind)
        if err:
            return err
        if new != plan:
            _snapshot_undo()
            job["plan"] = new
    elif action == "move_cell":
        to_lane = _int(request.get("to_lane"), 0, LANES - 1, -1)
        to_beat = _int(request.get("to_beat"), 0, n - 1, -1)
        default_kind = (_target().get("cover_options") or [None])[0]
        new, err = planops.move_cell(C, plan, n, lane, beat, to_lane, to_beat, default_kind)
        if err:
            return err
        if new != plan:
            _snapshot_undo()
            job["plan"] = new
    elif action == "clear":
        new = planops.clear(C, plan, n, lane, beat)
        if new != plan:
            _snapshot_undo()
            job["plan"] = new
    elif action == "clear_plan":
        if any(c for row in plan["lanes"] for c in row):
            _snapshot_undo()
            job["plan"] = engine.empty_plan(n)
    elif action == "move_lane":
        direction = -1 if request.get("dir") in (-1, "up") else 1
        new, other = planops.move_lane(plan, lane, direction)
        if other is not None:
            _snapshot_undo()
            job["plan"] = new
            crew = job["crew"]
            crew[lane], crew[other] = crew[other], crew[lane]
    return ""


# --- save contract ------------------------------------------------------------------------------
def get_state_json():
    return json.dumps(get_state())


def get_state():
    data = {"schema": SCHEMA, "career_seed": career.career_seed}
    if career.cash != START_CASH:
        data["cash"] = career.cash
    if career.jobs_started:
        data["jobs_started"] = career.jobs_started
    meta = {k: v for k, v in career.meta.items() if v != _default_meta()[k]}
    if meta:
        data["meta"] = meta
    if career.job:
        data["job"] = json.loads(json.dumps(career.job))
    return data


def _clean_ids(values, allowed, limit):
    out = []
    for v in values if isinstance(values, list) else []:
        if isinstance(v, str) and v in allowed and v not in out:
            out.append(v)
    return out[:limit]


def _clean_job(raw):
    if not isinstance(raw, dict):
        return None
    tid = raw.get("target")
    phase = raw.get("phase")
    if tid not in C.targets or phase not in PHASES:
        return None
    n = len(C.targets[tid]["beats"])
    job = {"phase": phase, "target": tid, "seed": _int(raw.get("seed"), 0, 2147483647, 1),
           "scout": _int(raw.get("scout"), 0, len(_scout_levels(C.targets[tid])) - 1, 0),
           "attempt": _int(raw.get("attempt"), 0, 999, 0), "paid": bool(raw.get("paid"))}
    job["offer"] = _clean_ids(raw.get("offer"), set(C.crew), OFFER_SIZE)
    job["crew"] = _clean_ids(raw.get("crew"), set(job["offer"]), LANES)
    job["gear"] = _clean_ids(raw.get("gear"), set(C.gear), MAX_GEAR)
    if phase in ("plan", "playback", "payout"):
        if len(job["crew"]) != LANES:
            return None
        job["plan"] = engine.clean_plan(C, raw.get("plan"), n)
    else:
        job["plan"] = None
        if phase == "recruit" and not job["offer"]:
            job["phase"] = "scout"
    return job


def load_state(data):
    """Replace the career with a saved one. Everything is validated; junk is dropped field by field."""
    global career
    if not isinstance(data, dict):
        return
    fresh = Career(_int(data.get("career_seed"), 1, 2147483647, 1))
    fresh.cash = _int(data.get("cash"), 0, 10 ** 9, START_CASH)
    fresh.jobs_started = _int(data.get("jobs_started"), 0, 10 ** 6, 0)
    meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
    fresh.meta["jobs_done"] = _int(meta.get("jobs_done"), 0, 10 ** 6, 0)
    fresh.meta["known_quirks"] = _clean_ids(meta.get("known_quirks"), set(C.crew), len(C.crew))
    fresh.meta["seen_complications"] = _clean_ids(meta.get("seen_complications"), set(C.complications), len(C.complications))
    fresh.meta["seen_traits"] = _clean_ids(meta.get("seen_traits"), set(C.traits), len(C.traits))
    fresh.job = _clean_job(data.get("job"))
    career = fresh
    del _undo[:], _redo[:]
    _refresh_view()


def _refresh_view():
    """Ask the page to redraw after a save is loaded (the save widget calls load_state directly)."""
    try:
        import js
        refresh = getattr(js.window, "heistRefresh", None)
        if refresh is not None:
            refresh()
    except Exception:
        pass
