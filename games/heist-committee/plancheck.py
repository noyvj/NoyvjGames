"""Heist Committee -- the planning screen's live checks: which requirements the plan covers, which actions are
missing what they need, which cells are long shots, which crew clash. Plain text, never blocks the player."""

import engine
from engine import LANES


def _slot_label(content, crew, slot):
    return "%s's %s in beat %d" % (crew[slot["lane"]]["short"], slot["action"]["name"], slot["start"] + 1)


def planned_requirements(content, target_id, crew_ids, plan):
    """Walk the requirements the way the engine does, assuming every action works. Returns a list of
    {id, label, optional, met, slot (lane/start/end) or None, action ids}."""
    target = content.targets[target_id]
    n = len(target["beats"])
    clean = engine.clean_plan(content, plan, n)
    slots_by_lane, _ = engine.build_slots(content, clean, n)
    done = {}
    used = set()
    out = []
    for req in target["requirements"]:
        lo, hi = req["window"]
        found = None
        best = None
        for lane in range(LANES):
            for slot in slots_by_lane[lane]:
                if slot["action"]["id"] not in req["actions"] or slot["truncated"] or (lane, slot["start"]) in used:
                    continue
                if not (lo <= slot["start"] + 1 <= hi):
                    continue
                if any(d not in done or done[d] >= slot["start"] for d in req.get("needs_done", [])):
                    continue
                if best is None or slot["start"] < best["start"]:
                    best = slot
        if best:
            found = {"lane": best["lane"], "start": best["start"], "end": best["end"], "action": best["action"]["id"]}
            done[req["id"]] = best["end"]
            used.add((best["lane"], best["start"]))
        out.append({"id": req["id"], "label": req["label"], "optional": bool(req.get("optional")), "met": bool(found),
                    "slot": found, "actions": list(req["actions"]), "window": list(req["window"]),
                    "needs_done": list(req.get("needs_done", [])), "value": req.get("value", 0), "final": bool(req.get("final"))})
    return out


def _names(content, ids):
    return " or ".join(content.actions[a]["name"] for a in ids)


def check(content, target_id, crew_ids, plan, gear_ids=(), relations=None, hidden_quirks=()):
    """Returns (messages, preview, pairs). messages: list of {level, text, lane, beat}."""
    target = content.targets[target_id]
    n = len(target["beats"])
    clean = engine.clean_plan(content, plan, n)
    crew = [content.crew[i] for i in crew_ids]
    preview = engine.preview(content, target_id, crew_ids, clean, gear_ids, relations, hidden_quirks)
    pairs = engine.pair_preview(content, target_id, crew_ids, clean, relations, hidden_quirks)
    slots_by_lane, occ = engine.build_slots(content, clean, n)
    messages = []
    planned = planned_requirements(content, target_id, crew_ids, clean)
    any_cell = any(cell for lane in clean["lanes"] for cell in lane)
    if not any_cell:
        messages.append({"level": "info", "text": "The plan is empty. Pick an action below, then tap a cell in the timeline.",
                         "lane": None, "beat": None})
    for item in planned:
        lo, hi = item["window"]
        where = "beat %d" % lo if lo == hi else "beats %d to %d" % (lo, hi)
        if item["met"]:
            slot = item["slot"]
            who = crew[slot["lane"]]["short"]
            messages.append({"level": "ok", "text": "%s: %s's %s, beat %d." % (
                item["label"], who, content.actions[slot["action"]]["name"], slot["start"] + 1),
                "lane": slot["lane"], "beat": slot["start"]})
        else:
            deps = [r["label"] for r in planned if r["id"] in item["needs_done"] and not r["met"]]
            tail = " It also waits on: %s." % ", ".join(deps) if deps else ""
            level = "info" if item["optional"] else "warn"
            messages.append({"level": level, "text": "%s: needs %s starting in %s, and nobody is planned for it.%s" % (
                item["label"], _names(content, item["actions"]), where, tail), "lane": None, "beat": None})
    for lane in range(LANES):
        for slot in slots_by_lane[lane]:
            action = slot["action"]
            if action["kind"] not in ("task", "support"):
                continue
            label = _slot_label(content, crew, slot)
            if slot["truncated"]:
                messages.append({"level": "warn", "text": "%s needs %d beats but the timeline ends." % (label, action["duration"]),
                                 "lane": lane, "beat": slot["start"]})
            for need in action.get("needs", []):
                missing = []
                for b in range(slot["start"], slot["end"] + 1):
                    provided = any(occ[o][b] and occ[o][b]["action"]["kind"] == "support"
                                   and need in occ[o][b]["action"].get("provides", []) for o in range(LANES))
                    if not provided:
                        missing.append(b)
                if missing:
                    when = "beat %d" % (missing[0] + 1) if len(missing) == 1 else "beats %s" % " and ".join(str(b + 1) for b in missing)
                    messages.append({"level": "warn", "text": "%s needs a %s in %s: no Lookout planned then." % (
                        label, content.tag_label(need).lower(), when), "lane": lane, "beat": missing[0]})
            info = preview[lane].get(slot["start"])
            if info and info["word"] in (engine.LONG, engine.NONE):
                bad = [p for p in info["parts"][1:] if p[1] < 0]
                why = "; ".join("%s %+d" % (p[0], p[1]) for p in bad[:3]) or "low skill"
                word = "a long shot" if info["word"] == engine.LONG else "very unlikely"
                messages.append({"level": "warn", "text": "%s is %s (%s)." % (label, word, why), "lane": lane,
                                 "beat": slot["start"]})
    for pair in pairs:
        if pair["value"] < 0:
            messages.append({"level": "warn", "text": "Clash in beat %d: %s" % (pair["beat"] + 1, pair["text"]),
                             "lane": pair["lane"], "beat": pair["beat"]})
        elif pair["value"] > 0:
            messages.append({"level": "info", "text": "Beat %d: %s (a small bonus)." % (pair["beat"] + 1, pair["text"]),
                             "lane": pair["lane"], "beat": pair["beat"]})
    return messages, preview, pairs
