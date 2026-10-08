"""Heist Committee -- content loader and integrity checks.

All rules are data: the JSON files in content/ (actions, tags, traits, crew, gear, complications, targets,
lines, writeups). This module loads them into plain dicts and `validate()` returns a list of problems (empty
when the content is sound). It runs in the browser too: app.js writes each JSON file into Pyodide's file system
next to the Python modules, so `_find_dir()` looks in ./content, then next to this file, then the working dir.
"""

import json
import os

FILES = ("tags", "actions", "traits", "crew", "gear", "complications", "targets", "lines", "writeups")
OPTIONAL_FILES = ("writeups",)

_cache = {}


def _find_dir():
    here = os.path.dirname(os.path.abspath(globals().get("__file__", "content.py")))
    for candidate in (os.path.join(here, "content"), here, os.getcwd()):
        if os.path.exists(os.path.join(candidate, "actions.json")):
            return candidate
    raise FileNotFoundError("content/actions.json not found")


class Content:
    """The loaded data, indexed by id."""

    def __init__(self, raw):
        self.raw = raw
        tags = raw["tags"]
        self.skills = tags["skills"]
        self.roles = tags["roles"]
        self.tags = tags["tags"]
        self.kinds = tags["kinds"]
        self.actions = {a["id"]: a for a in raw["actions"]["actions"]}
        self.traits = raw["traits"]["traits"]
        self.pair_rules = raw["traits"].get("pair_rules", [])
        self.crew = {c["id"]: c for c in raw["crew"]["crew"]}
        self.crew_order = [c["id"] for c in raw["crew"]["crew"]]
        self.gear = {g["id"]: g for g in raw["gear"]["gear"]}
        self.complications = {c["id"]: c for c in raw["complications"]["complications"]}
        self.comp_order = [c["id"] for c in raw["complications"]["complications"]]
        self.targets = {t["id"]: t for t in raw["targets"]["targets"]}
        self.target_order = [t["id"] for t in raw["targets"]["targets"]]
        self.lines = raw["lines"]
        self.writeups = raw.get("writeups") or {}

    def tag_label(self, tag):
        return self.tags.get(tag, {}).get("label", tag)

    def tag_lasts(self, tag):
        return int(self.tags.get(tag, {}).get("lasts", 1))


def load(data_dir=None, fresh=False):
    key = data_dir or "default"
    if key in _cache and not fresh:
        return _cache[key]
    folder = data_dir or _find_dir()
    raw = {}
    for name in FILES:
        path = os.path.join(folder, name + ".json")
        if not os.path.exists(path):
            if name in OPTIONAL_FILES:
                continue
            raise FileNotFoundError(path)
        with open(path, encoding="utf-8") as fh:
            raw[name] = json.load(fh)
    _cache[key] = Content(raw)
    return _cache[key]


def consumed_tags(c):
    """Every tag some rule reads: a requirement of a complication, an action need, a trait reaction..."""
    used = set()
    for comp in c.complications.values():
        used.update(comp.get("requires", []))
        used.update(comp.get("requires_any", []))
        used.update(comp.get("forbids", []))
    for action in c.actions.values():
        used.update(action.get("needs", []))
    for trait in c.traits.values():
        used.update(trait.get("margin_when_tag", {}))
        used.update(trait.get("lose_beat_on_tags", []))
    for target in c.targets.values():
        for req in target.get("requirements", []):
            used.update(req.get("needs_tags", []))
    return used


def emitted_tags(c):
    out = set()
    for comp in c.complications.values():
        out.update(comp.get("emits", []))
    for action in c.actions.values():
        out.update(action.get("emits_success", []))
        out.update(action.get("emits_fail", []))
        out.update(action.get("provides", []))
    for trait in c.traits.values():
        out.update(trait.get("idle_emits", []))
        out.update(trait.get("lose_beat_emits", []))
        out.update(trait.get("souvenir_emits", []))
    for rule in c.pair_rules:
        out.update(rule.get("effect", {}).get("emits", []))
    for target in c.targets.values():
        out.update(target.get("start_tags", []))
        for beat in target["beats"]:
            out.update(beat.get("tags", []))
    out.update(("noise",))   # rival arguments and loud actions
    return out


def counters_for(c, comp):
    """Which counters could in principle absorb this complication: a list of short strings. Empty = unanswerable."""
    found = []
    kinds = set(comp.get("kinds", []))
    for target in c.targets.values():
        if comp["id"] in target.get("pool", []) and kinds & set(target.get("cover_options", [])):
            found.append("standby")
            break
    sc = comp.get("skill_counter")
    if sc and any(m["skills"].get(sc["skill"], 0) >= sc["min"] for m in c.crew.values()):
        found.append("skill")
    if any(kinds & set(g.get("absorbs_kinds", [])) for g in c.gear.values()):
        found.append("gear")
    if any(kinds & set(t.get("absorbs_cover", [])) for t in c.traits.values()):
        if any(t in c.traits and kinds & set(c.traits[t].get("absorbs_cover", []))
               for m in c.crew.values() for t in (m.get("trait"), m.get("quirk"))):
            found.append("trait")
    if comp.get("forbids"):
        # Something a plan can put in place (a disguise, a distraction) makes it not happen at all.
        providable = set()
        for a in c.actions.values():
            providable.update(a.get("emits_success", []))
            providable.update(a.get("provides", []))
        if providable & set(comp["forbids"]):
            found.append("prevent")
    return found


def validate(c):
    """Return a list of human-readable problems. Empty means the content is consistent."""
    problems = []
    known_tags = set(c.tags)
    known_kinds = set(c.kinds)

    for aid, a in c.actions.items():
        if a["kind"] not in ("task", "support", "improvise", "standby", "wait"):
            problems.append(f"action {aid}: bad kind {a['kind']}")
        if a["kind"] in ("task", "support") and a["skill"] not in c.skills:
            problems.append(f"action {aid}: unknown skill {a['skill']}")
        for field in ("needs", "emits_success", "emits_fail", "provides", "removes_success"):
            for t in a.get(field, []):
                if t not in known_tags:
                    problems.append(f"action {aid}: unknown tag {t} in {field}")
        for key in ("start", "crit", "success", "partial", "fail"):
            if a["kind"] in ("task", "support") and key not in a.get("lines", {}):
                problems.append(f"action {aid}: missing line {key}")
        if a.get("duration", 1) not in (1, 2):
            problems.append(f"action {aid}: duration must be 1 or 2")

    for tid, t in c.traits.items():
        for field in ("margin_when_tag",):
            for tag in t.get(field, {}):
                if tag not in known_tags:
                    problems.append(f"trait {tid}: unknown tag {tag}")
        for field in ("idle_emits", "lose_beat_on_tags", "lose_beat_emits", "souvenir_emits"):
            for tag in t.get(field, []):
                if tag not in known_tags:
                    problems.append(f"trait {tid}: unknown tag {tag} in {field}")
        for kind in t.get("absorbs_cover", []):
            if kind not in known_kinds:
                problems.append(f"trait {tid}: unknown kind {kind}")
        if "fired" not in t or "name" not in t:
            problems.append(f"trait {tid}: needs name and fired")

    for rule in c.pair_rules:
        for side in ("a", "b"):
            kind, _, value = rule[side].partition(":")
            if kind == "trait" and value not in c.traits:
                problems.append(f"pair rule {rule['id']}: unknown trait {value}")
            if kind == "role" and value not in c.roles:
                problems.append(f"pair rule {rule['id']}: unknown role {value}")
            if kind == "crew" and value not in c.crew:
                problems.append(f"pair rule {rule['id']}: unknown crew {value}")
        if rule["geometry"] not in ("same_beat", "adjacent_beat", "neighbour_lane"):
            problems.append(f"pair rule {rule['id']}: bad geometry")

    for cid, m in c.crew.items():
        if m["role"] not in c.roles:
            problems.append(f"crew {cid}: unknown role {m['role']}")
        for skill in m["skills"]:
            if skill not in c.skills:
                problems.append(f"crew {cid}: unknown skill {skill}")
        for trait in (m.get("trait"), m.get("quirk")):
            if trait and trait not in c.traits:
                problems.append(f"crew {cid}: unknown trait {trait}")
        if not m.get("trait") or not m.get("quirk"):
            problems.append(f"crew {cid}: needs a trait and a quirk")
        for other in m.get("rival_of", []) + m.get("mentor_of", []):
            if other not in c.crew:
                problems.append(f"crew {cid}: unknown relation target {other}")

    for gid, g in c.gear.items():
        for kind in g.get("absorbs_kinds", []):
            if kind not in known_kinds:
                problems.append(f"gear {gid}: unknown kind {kind}")

    pooled = set()
    for tid, t in c.targets.items():
        n = len(t["beats"])
        for beat in t["beats"]:
            for tag in beat.get("tags", []):
                if tag not in known_tags:
                    problems.append(f"target {tid}: unknown beat tag {tag}")
        for tag in t.get("start_tags", []):
            if tag not in known_tags:
                problems.append(f"target {tid}: unknown start tag {tag}")
        seen = []
        for req in t["requirements"]:
            for aid in req["actions"]:
                if aid not in c.actions:
                    problems.append(f"target {tid}: requirement {req['id']} unknown action {aid}")
            lo, hi = req["window"]
            if not (1 <= lo <= hi <= n):
                problems.append(f"target {tid}: requirement {req['id']} window outside 1..{n}")
            for dep in req.get("needs_done", []):
                if dep not in seen:
                    problems.append(f"target {tid}: requirement {req['id']} depends on later/unknown {dep}")
            seen.append(req["id"])
        if not any(r.get("final") for r in t["requirements"]):
            problems.append(f"target {tid}: needs a final (escape) requirement")
        for kind in t.get("cover_options", []):
            if kind not in known_kinds:
                problems.append(f"target {tid}: unknown cover kind {kind}")
        if not t.get("titles"):
            problems.append(f"target {tid}: needs titles")
        pool = t.get("pool")
        if not pool:
            problems.append(f"target {tid}: needs a pool of complication ids")
            continue
        for cid in pool:
            if cid not in c.complications:
                problems.append(f"target {tid}: pool has unknown complication {cid}")
            pooled.add(cid)
        if len(set(pool)) != len(pool):
            problems.append(f"target {tid}: duplicate pool entries")
        levels = t.get("scout", {}).get("levels", [])
        if not levels or levels[0].get("reveal", 0) < 1:
            problems.append(f"target {tid}: scouting must always reveal at least the top complication")

    for cid, comp in c.complications.items():
        if comp["trigger"] not in ("random", "auto"):
            problems.append(f"complication {cid}: bad trigger")
        if comp["trigger"] == "auto" and not comp.get("requires") and not comp.get("requires_any"):
            problems.append(f"complication {cid}: an auto complication must require a tag (or it loops)")
        lo, hi = comp["beats"]
        if lo < 1 or hi < lo:
            problems.append(f"complication {cid}: bad beat range")
        for field in ("requires", "requires_any", "forbids", "emits"):
            for tag in comp.get(field, []):
                if tag not in known_tags:
                    problems.append(f"complication {cid}: unknown tag {tag} in {field}")
        for kind in comp.get("kinds", []):
            if kind not in known_kinds:
                problems.append(f"complication {cid}: unknown kind {kind}")
        sc = comp.get("skill_counter")
        if sc and sc["skill"] not in c.skills:
            problems.append(f"complication {cid}: unknown counter skill {sc['skill']}")
        for key in ("text", "absorbed_text", "name"):
            if not comp.get(key):
                problems.append(f"complication {cid}: missing {key}")
        if cid not in pooled:
            problems.append(f"complication {cid}: not in any target's pool")
        elif not counters_for(c, comp):
            problems.append(f"complication {cid}: has no reachable counter")

    consumed = consumed_tags(c)
    for tag in sorted(emitted_tags(c) - consumed):
        if not c.tags.get(tag, {}).get("terminal"):
            problems.append(f"tag {tag} is emitted but nothing reads it (mark it terminal if it is only flavour)")
    for tag in c.tags:
        if c.tags[tag].get("lasts", 0) < 1:
            problems.append(f"tag {tag}: lasts must be at least 1")
    return problems
