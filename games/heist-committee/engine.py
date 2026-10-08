"""Heist Committee -- the heist resolver.

`simulate(...)` is a PURE function of (content, target, crew, plan, gear, seed): the same inputs give the same
event list, byte for byte. Nothing is stored between runs, a saved game only keeps the plan and the seed, and
mid-playback resume simply replays the whole heist and shows it up to the saved cursor.

Randomness: `roll(seed, *keys)` hashes the seed with a label (beat, lane, what for), so every decision has its
own independent number. Editing one cell of the plan never reshuffles the dice somewhere else.

A beat resolves in this order (plan section 5.5):
  1. tags expire, the beat's environment tags switch on, sidelined crew sit out
  2. idle crew make their trait noises
  3. complications: a seeded draw, then the chain (auto complications whose required tags are now active)
  4. trait reactions (allergic crew sneeze), then another chain pass
  5. support actions resolve (a Lookout provides `clear`), then tasks (a 2-beat task resolves on its last beat)
  6. a last chain pass; effects of those land on the NEXT beat
Chains are capped at CHAIN_CAP links a beat, and each complication fires once a heist, so a chain always ends.
"""

import hashlib

CHAIN_CAP = 6
LANES = 5
SOLID, RISKY, LONG, NONE = "solid", "risky", "long", "none"


def roll(seed, *keys):
    """A number in [0, 1) that depends only on the seed and the labels."""
    text = "|".join(str(k) for k in (seed,) + keys).encode("utf-8")
    return int.from_bytes(hashlib.sha256(text).digest()[:6], "big") / float(1 << 48)


def outcome_for(margin, r):
    if margin >= 3:
        return "crit" if r < 0.5 else "success"
    if margin >= 1:
        return "success"
    if margin == 0:
        return "success" if r < 0.55 else ("partial" if r < 0.85 else "fail")
    if margin == -1:
        return "success" if r < 0.2 else ("partial" if r < 0.5 else "fail")
    if margin == -2:
        return "success" if r < 0.05 else ("partial" if r < 0.2 else "fail")
    return "fail"


def odds_word(margin):
    if margin >= 1:
        return SOLID
    if margin == 0:
        return RISKY
    if margin >= -2:
        return LONG
    return NONE


def parse_cell(cell):
    """'standby:noise' -> ('standby', 'noise'); None -> (None, None)."""
    if not cell or not isinstance(cell, str):
        return None, None
    action, _, arg = cell.partition(":")
    return action, (arg or None)


def empty_plan(n_beats):
    return {"lanes": [[None] * n_beats for _ in range(LANES)]}


def clean_plan(content, plan, n_beats):
    """A plan with the right shape and only known cells; anything else becomes an empty cell."""
    lanes = []
    raw = plan.get("lanes") if isinstance(plan, dict) else None
    for lane in range(LANES):
        row = raw[lane] if isinstance(raw, list) and lane < len(raw) and isinstance(raw[lane], list) else []
        out = []
        for b in range(n_beats):
            cell = row[b] if b < len(row) else None
            action, arg = parse_cell(cell)
            if action not in content.actions or action == "wait":
                out.append(None)
            elif action == "standby":
                kind = arg if arg in content.kinds else None
                out.append("standby:" + kind if kind else None)
            else:
                out.append(action)
        lanes.append(out)
    return {"lanes": lanes}


def build_slots(content, plan, n_beats):
    """Expand the plan into slots. A 2-beat action occupies the next cell too (what is written there is ignored).
    Returns (slots_by_lane, occupancy) where occupancy[lane][beat] is the slot active there or None."""
    slots_by_lane = []
    occ = []
    for lane in range(LANES):
        cells = plan["lanes"][lane]
        row = [None] * n_beats
        slots = []
        b = 0
        while b < n_beats:
            action_id, arg = parse_cell(cells[b])
            action = content.actions.get(action_id)
            if not action or action["kind"] == "wait":
                b += 1
                continue
            want = int(action.get("duration", 1))
            dur = min(want, n_beats - b)
            slot = {"lane": lane, "action": action, "arg": arg, "start": b, "dur": dur, "end": b + dur - 1,
                    "truncated": dur < want, "mods": {}, "mod_src": {}, "lost": False, "outcome": None,
                    "margin": None, "event": None, "done": False}
            for k in range(dur):
                row[b + k] = slot
            slots.append(slot)
            b += dur
        slots_by_lane.append(slots)
        occ.append(row)
    return slots_by_lane, occ


def _matches(content, crew, selector):
    kind, _, value = selector.partition(":")
    if kind == "trait":
        return value in (crew.get("trait"), crew.get("quirk"))
    if kind == "role":
        return crew["role"] == value
    if kind == "crew":
        return crew["id"] == value
    return False


class Sim:
    def __init__(self, content, target_id, crew_ids, plan, gear_ids=(), seed=0, relations=None,
                 fees=0, preview=False, hidden_quirks=()):
        self.c = content
        self.target = content.targets[target_id]
        self.n = len(self.target["beats"])
        self.seed = seed
        self.preview = preview
        self.fees = fees
        self.relations = relations or {}
        self.crew_ids = list(crew_ids)
        self.crew = [content.crew[i] for i in self.crew_ids]
        self.traits = []
        for crew in self.crew:
            ids = [crew.get("trait")]
            if not (preview and crew["id"] in hidden_quirks):
                ids.append(crew.get("quirk"))
            self.traits.append([content.traits[t] for t in ids if t in content.traits])
        self.trait_ids = [[t for t in ([c.get("trait")] + [c.get("quirk")]) if t in content.traits] for c in self.crew]
        self.plan = clean_plan(content, plan, self.n)
        self.slots, self.occ = build_slots(content, self.plan, self.n)
        self.gear = [content.gear[g] for g in gear_ids if g in content.gear]
        self.gear_left = {g["id"]: int(g.get("uses", 1)) for g in self.gear}
        self.pool = [content.complications[i] for i in self.target.get("pool", []) if i in content.complications]
        self.events = []
        self.tags = {}
        self.src = {}
        self.suspicion = int(self.target.get("base_suspicion", 0))
        self.fired = set()
        self.fired_beat = {}
        self.sidelined = {}
        self.done = {}
        self.loot_lost = 0
        self.damage = 0
        self.souvenirs = 0
        self.rerolls_left = [sum(int(t.get("rerolls", 0)) for t in ts) for ts in self.traits]
        self.coin_left = sum(int(g.get("rerolls", 0)) for g in self.gear)
        self.absorbed = []
        self.alarm = False
        self.pair_seen = set()
        self.souvenir_done = set()
        self.chain_depth = 0
        self.stats = {"complications": [], "seen_traits": set(), "chain_capped": 0}
        self.b = 0
        self.side_notes = []
        self.idle_beats = {}

    # ---- events ---------------------------------------------------------------------------
    def add(self, kind, text, lane=None, why=None, tags=(), cause=None, outcome=None, icon="", comp=None,
            trait=None, action=None, flavor=None, extra=None):
        ev = {"i": len(self.events), "beat": self.b, "type": kind, "text": text, "lane": lane,
              "crew": self.crew_ids[lane] if lane is not None else None, "why": why or "", "tags": list(tags),
              "cause": cause, "outcome": outcome, "icon": icon, "comp": comp, "trait": trait, "action": action,
              "flavor": flavor or "", "depth": 1}
        if extra:
            ev.update(extra)
        if cause is not None:
            ev["depth"] = self.events[cause]["depth"] + 1
        self.events.append(ev)
        return ev["i"]

    def name(self, lane):
        return self.crew[lane]["short"]

    def fmt(self, template, **kw):
        try:
            return template.format(**kw)
        except (KeyError, IndexError, ValueError):
            return template

    # ---- tags -----------------------------------------------------------------------------
    def active(self, b=None):
        b = self.b if b is None else b
        return {t for t, exp in self.tags.items() if exp > b}

    def emit(self, tags, src, b=None):
        b = self.b if b is None else b
        for tag in tags:
            lasts = self.c.tag_lasts(tag)
            self.tags[tag] = max(self.tags.get(tag, 0), b + lasts)
            self.src[tag] = src
            if tag == "alarm":
                self.alarm = True

    def remove(self, tags):
        for tag in tags:
            self.tags.pop(tag, None)

    # ---- plan geometry --------------------------------------------------------------------
    def slot_at(self, lane, b):
        if 0 <= b < self.n:
            return self.occ[lane][b]
        return None

    def busy(self, lane, b):
        slot = self.slot_at(lane, b)
        return bool(slot and slot["action"]["kind"] in ("task", "support"))

    def is_free(self, lane, b):
        """Free = could help if trouble came: not sidelined and not in the middle of a task or support."""
        if self.sidelined.get(lane, -1) > b:
            return False
        slot = self.slot_at(lane, b)
        return not slot or slot["action"]["kind"] in ("standby", "improvise")

    # ---- margins --------------------------------------------------------------------------
    def put_mod(self, slot, label, value, src=None):
        if value == 0:
            return
        old = slot["mods"].get(label)
        if old is None or abs(value) > abs(old):
            slot["mods"][label] = value
            slot["mod_src"][label] = src

    def base_margin(self, slot):
        lane, action = slot["lane"], slot["action"]
        skill = action["skill"]
        crew = self.crew[lane]
        if skill == "best":
            pips = max(crew["skills"].values() or [0])
        else:
            pips = crew["skills"].get(skill, 0)
        label = "%s %d against difficulty %d" % (self.c.skills.get(skill, {}).get("label", skill), pips, action["difficulty"])
        parts = [(label, pips - action["difficulty"] + 1)]
        for trait in self.traits[lane]:
            if trait.get("margin_all"):
                parts.append((trait["name"], int(trait["margin_all"])))
            by_dur = trait.get("margin_by_duration", {})
            if str(slot["dur"]) in by_dur:
                parts.append((trait["name"] + ", %d-beat job" % slot["dur"], int(by_dur[str(slot["dur"])])))
            for_action = trait.get("margin_for_action", {})
            if action["id"] in for_action:
                parts.append((trait["name"], int(for_action[action["id"]])))
        for g in self.gear:
            bonus = g.get("margin_skill", {}).get(skill)
            if bonus:
                parts.append((g["name"], int(bonus)))
        if slot["truncated"]:
            parts.append(("Ran out of beats", -2))
        return parts

    def pair_effects(self, lane, b):
        """Static relationships touching `lane` in beat b: list of dicts (label, value, emits, partner, line, key)."""
        out = []
        me = self.crew[lane]
        mine = self.slot_at(lane, b)
        if not mine or mine["action"]["kind"] not in ("task", "support"):
            return out
        c = self.c
        for other in range(LANES):
            if other == lane:
                continue
            theirs = self.slot_at(other, b)
            partner = self.crew[other]
            both_active = bool(theirs and theirs["action"]["kind"] in ("task", "support", "improvise"))
            if both_active:
                pair_key = "|".join(sorted((me["id"], partner["id"])))
                relation = self.relations.get(pair_key)
                feud = relation == "feud" or partner["id"] in me.get("rival_of", []) or me["id"] in partner.get("rival_of", [])
                if feud and relation != "friends":
                    out.append({"label": "Feud with " + partner["short"], "value": -2, "emits": ["noise"], "partner": other,
                                "kind": "rival", "line": c.lines["rival"], "key": ("rival", pair_key, b)})
                elif relation == "friends":
                    out.append({"label": "Friends with " + partner["short"], "value": 1, "emits": [], "partner": other,
                                "kind": "friends", "line": c.lines["friends"], "key": ("friends", pair_key, b)})
                for trait in self.traits[lane]:
                    if trait.get("margin_with_company"):
                        out.append({"label": trait["name"] + ", with company", "value": int(trait["margin_with_company"]),
                                    "emits": [], "partner": other, "kind": "company", "line": c.lines["company"],
                                    "key": ("company", me["id"], b)})
                        break
            # a mentor working in this beat or a neighbouring beat
            if me["id"] in partner.get("mentor_of", []):
                for db in (-1, 0, 1):
                    other_slot = self.slot_at(other, b + db)
                    if other_slot and other_slot["action"]["kind"] in ("task", "support"):
                        out.append({"label": partner["short"] + "'s coaching", "value": 1, "emits": [], "partner": other,
                                    "kind": "mentor", "line": c.lines["mentor"], "key": ("mentor", me["id"], partner["id"], b)})
                        break
            for rule in c.pair_rules:
                for a_lane, b_lane, ca, cb in ((lane, other, me, partner), (other, lane, partner, me)):
                    if not (_matches(c, ca, rule["a"]) and _matches(c, cb, rule["b"])):
                        continue
                    if not self.trait_active(a_lane, rule["a"]) or not self.trait_active(b_lane, rule["b"]):
                        continue
                    geometry = rule["geometry"]
                    ok = False
                    if geometry == "same_beat":
                        ok = both_active
                    elif geometry == "neighbour_lane":
                        ok = both_active and abs(a_lane - b_lane) == 1
                    elif geometry == "adjacent_beat":
                        ok = any(self.busy(other, b + db) for db in (-1, 1))
                    if not ok:
                        continue
                    effect = rule["effect"]
                    target_lane = a_lane if effect["target"] == "a" else b_lane
                    if target_lane != lane:
                        continue
                    other_name = partner["short"]
                    out.append({"label": rule["id"].replace("_", " ").capitalize(), "value": int(effect.get("margin", 0)),
                                "emits": list(effect.get("emits", [])), "partner": other, "kind": "rule",
                                "line": self.fmt(rule["line"], a=self.crew[a_lane]["short"], b=self.crew[b_lane]["short"]),
                                "key": (rule["id"], me["id"], other_name, b), "prefilled": True})
        return out

    def trait_active(self, lane, selector):
        kind, _, value = selector.partition(":")
        if kind != "trait":
            return True
        return value in [t for t in self.trait_ids[lane] if self.c.traits[t] in self.traits[lane]]

    def tick(self, slot, b):
        """Collect everything that bends this slot's margin during beat b (tags, needs, relationships)."""
        lane, action = slot["lane"], slot["action"]
        active = self.active(b)
        for trait in self.traits[lane]:
            for tag, value in trait.get("margin_when_tag", {}).items():
                if tag in active:
                    self.put_mod(slot, "%s: %s" % (trait["name"], self.c.tag_label(tag)), int(value), self.src.get(tag))
        for need in action.get("needs", []):
            if need not in active:
                share = -2 if slot["dur"] == 1 else -1
                self.put_mod(slot, "No %s in beat %d" % (self.c.tag_label(need).lower(), b + 1), share, self.src.get("_missing_" + need))
                slot.setdefault("needs_missing", []).append(need)
        for eff in self.pair_effects(lane, b):
            self.put_mod(slot, eff["label"], eff["value"], None)
            if eff["key"] not in self.pair_seen and not self.preview:
                self.pair_seen.add(eff["key"])
                if eff["kind"] == "rival":
                    ev = self.add("pair", eff["line"] if eff.get("prefilled") else self.fmt(
                        eff["line"], a=self.name(lane), b=self.name(eff["partner"])), lane=lane, tags=eff["emits"],
                        why="Feud: %+d for %s." % (eff["value"], self.name(lane)), icon="⚡")
                    self.emit(eff["emits"], ev, b)
                elif eff["kind"] == "rule":
                    ev = self.add("pair", eff["line"], lane=lane, tags=eff["emits"],
                                  why="%s: %+d for %s." % (eff["label"], eff["value"], self.name(lane)), icon="⚡")
                    self.emit(eff["emits"], ev, b)
                elif eff["kind"] == "mentor":
                    self.add("pair", self.fmt(eff["line"], mentor=self.crew[eff["partner"]]["short"], pupil=self.name(lane)),
                             lane=lane, why="%s: +1 for %s." % (eff["label"], self.name(lane)), icon="🎓")
                elif eff["kind"] == "friends":
                    self.add("pair", self.fmt(eff["line"], a=self.name(lane), b=self.name(eff["partner"])), lane=lane,
                             why="Friends: +1 for %s." % self.name(lane), icon="♥")

    def finish_margin(self, slot):
        parts = self.base_margin(slot) + list(slot["mods"].items())
        total = sum(v for _, v in parts)
        return total, parts

    def why_text(self, parts, margin):
        bits = ["%s %+d" % (label, value) for label, value in parts]
        return "; ".join(bits) + " = %+d (%s)" % (margin, self.c.lines["odds_words"][odds_word(margin)])

    # ---- complications --------------------------------------------------------------------
    def eligible(self, comp, b):
        lo, hi = comp["beats"]
        if not (lo <= b + 1 <= hi):
            return False
        if comp["id"] in self.fired:
            return False
        act = self.active(b)
        if any(t not in act for t in comp.get("requires", [])):
            return False
        any_of = comp.get("requires_any")
        if any_of and not any(t in act for t in any_of):
            return False
        if any(t in act for t in comp.get("forbids", [])):
            return False
        return True

    def cause_of(self, comp):
        sources = [self.src[t] for t in comp.get("requires", []) + comp.get("requires_any", []) if t in self.src
                   and isinstance(self.src[t], int)]
        return max(sources) if sources else None

    def counter_for(self, comp, b):
        """Find who/what absorbs the complication: standby, improvise, free skill, gear, trait (that order)."""
        kinds = set(comp.get("kinds", []))
        for lane in range(LANES):
            slot = self.slot_at(lane, b)
            if self.sidelined.get(lane, -1) > b or not slot or slot["action"]["kind"] != "standby":
                continue
            if slot["arg"] in kinds:
                lazy = [t for t in self.traits[lane] if t.get("standby_works") is False]
                if lazy:
                    self.side_notes.append(self.fmt(lazy[0]["fired"], crew=self.name(lane)))
                    self.stats["seen_traits"].add(self.trait_id_of(lane, lazy[0]))
                    continue
                return ("standby", lane, slot)
        for lane in range(LANES):
            slot = self.slot_at(lane, b)
            if self.sidelined.get(lane, -1) > b or not slot or slot["action"]["kind"] != "improvise" or slot.get("spent"):
                continue
            slot["spent"] = True
            margin = sum(v for _, v in self.base_margin(slot)) + sum(slot["mods"].values())
            result = outcome_for(margin, roll(self.seed, b, lane, "improv", comp["id"]))
            if result in ("crit", "success"):
                return ("improvise", lane, slot)
            self.side_notes.append(self.fmt(self.c.lines["improvise_failed"], crew=self.name(lane)))
        sc = comp.get("skill_counter")
        if sc:
            for lane in range(LANES):
                if self.is_free(lane, b) and self.crew[lane]["skills"].get(sc["skill"], 0) >= sc["min"]:
                    return ("skill", lane, sc)
        for g in self.gear:
            if self.gear_left.get(g["id"], 0) > 0 and kinds & set(g.get("absorbs_kinds", [])):
                return ("gear", None, g)
        for lane in range(LANES):
            if not self.is_free(lane, b):
                continue
            for trait in self.traits[lane]:
                if kinds & set(trait.get("absorbs_cover", [])):
                    return ("trait", lane, trait)
        return None

    def target_lane(self, comp, b, phase):
        """The lane an effect lands on, or None (it lands on an empty beat)."""
        spec = comp.get("effects", {}).get("target", "none")
        when = b if phase == "pre" else b + 1
        if spec == "none":
            return None
        busy = [lane for lane in range(LANES) if self.busy(lane, when)
                and self.slot_at(lane, when)["action"]["kind"] == "task"
                and self.sidelined.get(lane, -1) <= when]
        if spec == "any_task":
            return busy[0] if busy else None
        if spec.startswith("needs:"):
            need = spec.split(":", 1)[1]
            for lane in busy:
                if need in self.slot_at(lane, when)["action"].get("needs", []):
                    return lane
            return busy[0] if busy else None
        if spec.startswith("action:"):
            want = spec.split(":", 1)[1]
            for lane in busy:
                if self.slot_at(lane, when)["action"]["id"] == want:
                    return lane
            return None
        if spec == "random_crew":
            return int(roll(self.seed, b, "target", comp["id"]) * LANES) % LANES
        return None

    def fire(self, comp, b, phase, cause=None):
        """A complication happens. Returns the event index."""
        self.fired.add(comp["id"])
        self.fired_beat[comp["id"]] = b
        self.stats["complications"].append(comp["id"])
        if cause is None:
            cause = self.cause_of(comp)
        flavor = comp.get("flavor", "")
        self.side_notes = []
        counter = self.counter_for(comp, b)
        extra_text = (" " + " ".join(self.side_notes)) if self.side_notes else ""
        if counter:
            kind, lane, what = counter
            if kind == "standby":
                note = self.fmt(self.c.lines["absorb_standby"], crew=self.name(lane), kind=self.c.kinds[what["arg"]]["label"].lower())
            elif kind == "improvise":
                note = self.fmt(self.c.lines["absorb_improvise"], crew=self.name(lane))
            elif kind == "skill":
                note = self.fmt(self.c.lines["absorb_skill"], crew=self.name(lane),
                                skill=self.c.skills[what["skill"]]["label"])
            elif kind == "gear":
                self.gear_left[what["id"]] -= 1
                note = what.get("absorbed") or self.fmt(self.c.lines["absorb_gear"], gear=what["name"])
            else:
                note = self.fmt(self.c.lines["absorb_trait"], crew=self.name(lane), trait=what["name"])
                self.stats["seen_traits"].add(next(t for t in self.trait_ids[lane] if self.c.traits[t] is what))
            if self.suspicion > 0:
                self.suspicion -= 1
            self.absorbed.append(comp["id"])
            return self.add("absorb", comp["absorbed_text"] + extra_text + " " + note, lane=lane,
                            why="%s was absorbed (%s). Heat -1." % (comp["name"], kind), cause=cause, icon="🛡",
                            comp=comp["id"], flavor=flavor, tags=[], extra={"counter": kind})
        eff = comp.get("effects", {})
        text = comp["text"] + extra_text
        lane = self.target_lane(comp, b, phase)
        notes = []
        if eff.get("suspicion"):
            self.suspicion += int(eff["suspicion"])
            notes.append("heat +%d" % eff["suspicion"])
        if eff.get("damage"):
            self.damage += int(eff["damage"])
            notes.append("damages +%d" % eff["damage"])
        if eff.get("loot_loss") and self.done.get("_grabbed"):
            self.loot_lost += int(eff["loot_loss"])
            notes.append("loot -%d" % eff["loot_loss"])
        soft = False
        ev_index = len(self.events)
        if eff.get("margin") or eff.get("sideline"):
            if lane is None:
                soft = True
            else:
                when = b if phase == "pre" else b + 1
                slot = self.slot_at(lane, when)
                if eff.get("margin") and slot:
                    self.put_mod(slot, comp["name"], int(eff["margin"]), ev_index)
                    notes.append("%s %+d" % (self.name(lane), eff["margin"]))
                if eff.get("sideline"):
                    until = when + int(eff["sideline"])
                    self.sidelined[lane] = max(self.sidelined.get(lane, 0), until)
                    if slot and phase == "pre":
                        slot["lost"] = True
                    notes.append("%s out for %d beat(s)" % (self.name(lane), eff["sideline"]))
        if soft:
            text += " " + self.c.lines["soft_landing"]
        why = "%s (%s)." % (comp["name"], ", ".join(notes) if notes else "no direct harm")
        idx = self.add("complication", text, lane=lane, why=why, tags=comp.get("emits", []), cause=cause, icon="⚡",
                       comp=comp["id"], flavor=flavor)
        self.emit(comp.get("emits", []), idx, b)
        return idx

    def draw(self, b):
        susp = min(self.suspicion, 5)
        for k in range(2):
            pool = [c for c in self.pool if c["trigger"] == "random" and self.eligible(c, b)]
            if not pool:
                return
            p = min(0.9, 0.5 + 0.08 * susp)
            if k == 1:
                if self.suspicion < 5:
                    return
                p *= 0.6
            if roll(self.seed, b, "fire", k) >= p:
                continue
            weights = [c.get("weight", 1) * ((1 + self.suspicion) if c.get("heat") else 1) for c in pool]
            pick = roll(self.seed, b, "pick", k) * sum(weights)
            for comp, w in zip(pool, weights):
                pick -= w
                if pick < 0:
                    self.chain_depth += 1
                    self.fire(comp, b, "pre")
                    break

    def chain(self, b, phase):
        """Fire auto complications whose required tags are active, until nothing new fires or the cap is hit."""
        while True:
            if self.chain_depth >= CHAIN_CAP:
                if any(self.eligible(c, b) for c in self.pool if c["trigger"] == "auto"):
                    if not self.stats.get("capped_beat") == b:
                        self.stats["capped_beat"] = b
                        self.stats["chain_capped"] += 1
                        self.add("note", self.c.lines["chain_capped"], icon="…")
                return
            nxt = None
            for comp in self.pool:
                if comp["trigger"] == "auto" and self.eligible(comp, b):
                    nxt = comp
                    break
            if nxt is None:
                return
            self.chain_depth += 1
            self.fire(nxt, b, phase)

    # ---- the beat -------------------------------------------------------------------------
    def begin_beat(self, b):
        self.b = b
        self.chain_depth = 0
        beat = self.target["beats"][b]
        for tag, exp in list(self.tags.items()):
            if exp <= b:
                del self.tags[tag]
        for tag in beat.get("tags", []):
            self.tags[tag] = max(self.tags.get(tag, 0), b + 1)
        if b == 0:
            for tag in self.target.get("start_tags", []):
                self.tags[tag] = max(self.tags.get(tag, 0), 99)
        self.add("beat", self.fmt(self.c.lines["beat_header"], n=b + 1, name=beat["name"]),
                 tags=beat.get("tags", []), extra={"note": beat.get("note", "")}, icon="▸")
        for lane in range(LANES):
            if self.sidelined.get(lane, -1) > b:
                slot = self.slot_at(lane, b)
                if slot and slot["action"]["kind"] in ("task", "support"):
                    slot["lost"] = True
                self.add("sidelined", self.fmt(self.c.lines["sidelined"], crew=self.name(lane)), lane=lane, icon="🩹",
                         why="Sidelined until beat %d." % (self.sidelined[lane] + 1))

    def idle_noise(self, b):
        for lane in range(LANES):
            slot = self.slot_at(lane, b)
            if self.sidelined.get(lane, -1) > b or slot:
                continue
            for trait in self.traits[lane]:
                if trait.get("idle_emits"):
                    idx = self.add("trait", self.fmt(trait["fired"], crew=self.name(lane)), lane=lane, trait=self.trait_id_of(lane, trait),
                                   tags=trait["idle_emits"], why="%s: idle crew make noise." % trait["name"], icon="🗣")
                    self.emit(trait["idle_emits"], idx, b)
                    self.stats["seen_traits"].add(self.trait_id_of(lane, trait))

    def trait_id_of(self, lane, trait):
        for tid in self.trait_ids[lane]:
            if self.c.traits[tid] is trait:
                return tid
        return None

    def trait_reactions(self, b):
        for lane in range(LANES):
            if self.sidelined.get(lane, -1) > b:
                continue
            slot = self.slot_at(lane, b)
            if not slot or slot["action"]["kind"] not in ("task", "support"):
                continue
            active = self.active(b)
            for trait in self.traits[lane]:
                hit = [t for t in trait.get("lose_beat_on_tags", []) if t in active]
                if hit:
                    tag = hit[0]
                    self.sidelined[lane] = max(self.sidelined.get(lane, 0), b + 1)
                    slot["lost"] = True
                    idx = self.add("trait", self.fmt(trait["fired"], crew=self.name(lane), tag=self.c.tag_label(tag).lower()),
                                   lane=lane, trait=self.trait_id_of(lane, trait), tags=trait.get("lose_beat_emits", []),
                                   cause=self.src.get(tag) if isinstance(self.src.get(tag), int) else None,
                                   why="%s: loses this beat near %s." % (trait["name"], self.c.tag_label(tag).lower()), icon="🤧")
                    self.emit(trait.get("lose_beat_emits", []), idx, b)
                    self.stats["seen_traits"].add(self.trait_id_of(lane, trait))

    def resolve_slot(self, slot, b):
        lane, action = slot["lane"], slot["action"]
        margin, parts = self.finish_margin(slot)
        slot["margin"] = margin
        if self.preview:
            slot["outcome"] = None
            return
        if slot["lost"]:
            slot["outcome"] = "sidelined"
            slot["done"] = True
            self.add("action", "%s could not do %s: out of action." % (self.name(lane), action["name"]), lane=lane,
                     outcome="fail", action=action["id"], icon=action["icon"], why="Sidelined during this job.")
            return
        r = roll(self.seed, slot["start"], lane, "act")
        outcome = outcome_for(margin, r)
        notes = []
        for trait in self.traits[lane]:
            if trait.get("no_fail_duration") == slot["dur"] and outcome == "fail":
                outcome = "partial"
                notes.append("%s: never fails a %d-beat job." % (trait["name"], slot["dur"]))
        if outcome in ("fail", "partial") and self.rerolls_left[lane] > 0:
            self.rerolls_left[lane] -= 1
            again = outcome_for(margin, roll(self.seed, slot["start"], lane, "reroll"))
            order = {"fail": 0, "partial": 1, "success": 2, "crit": 3}
            if order[again] > order[outcome]:
                outcome = again
            notes.append(self.fmt(self.c.lines["lucky_reroll"], crew=self.name(lane)))
            for t in self.trait_ids[lane]:
                if self.c.traits[t].get("rerolls"):
                    self.stats["seen_traits"].add(t)
        elif outcome in ("fail", "partial") and self.coin_left > 0:
            self.coin_left -= 1
            again = outcome_for(margin, roll(self.seed, slot["start"], lane, "coin"))
            order = {"fail": 0, "partial": 1, "success": 2, "crit": 3}
            if order[again] > order[outcome]:
                outcome = again
            notes.append(self.fmt(self.c.lines["coin_reroll"], crew=self.name(lane)))
        slot["outcome"] = outcome
        slot["done"] = True
        cause = None
        negatives = [(v, slot["mod_src"].get(label)) for label, v in slot["mods"].items() if v < 0]
        if outcome in ("fail", "partial") and negatives:
            worst = min(negatives, key=lambda p: p[0])
            if isinstance(worst[1], int):
                cause = worst[1]
        for need in slot.get("needs_missing", []):
            provider = self.src.get("_missing_" + need)
            if cause is None and isinstance(provider, int):
                cause = provider
        text = self.fmt(action["lines"][outcome if outcome in action["lines"] else "success"], crew=self.name(lane))
        if slot["truncated"]:
            notes.append(self.fmt(self.c.lines["truncated"], crew=self.name(lane)))
        why = self.why_text(parts, margin)
        if notes:
            why += " " + " ".join(notes)
        # noise and heat
        noise = int(action.get("noise", 0)) + sum(int(t.get("action_noise", 0)) for t in self.traits[lane])
        emits = []
        if outcome in ("success", "crit"):
            emits += action.get("emits_success", [])
        elif outcome == "partial":
            emits += action.get("emits_success", [])
        else:
            emits += action.get("emits_fail", [])
        loud = noise >= 2 or (noise >= 1 and outcome in ("partial", "fail"))
        if loud and "noise" not in emits:
            emits.append("noise")
        heat = int(action.get("suspicion", 0))
        if outcome == "partial":
            heat += 1
        if outcome == "fail":
            heat += 1
        if outcome == "crit" and self.suspicion > 0:
            heat -= 1
        idx = self.add("action", text, lane=lane, why=why, tags=emits, outcome=outcome, action=action["id"],
                       icon=action["icon"], cause=cause)
        slot["event"] = idx
        self.suspicion = max(0, self.suspicion + heat)
        if action.get("removes_success") and outcome in ("success", "crit", "partial"):
            gone = [t for t in action["removes_success"] if t in self.active(b)]
            self.remove(gone)
        self.emit(emits, idx, b)
        for t in self.trait_ids[lane]:
            tr = self.c.traits[t]
            if tr in self.traits[lane] and tr.get("action_noise") and loud:
                self.stats["seen_traits"].add(t)
        # requirements
        if outcome in ("success", "crit", "partial"):
            self.complete_requirements(slot, b, outcome)
            self.souvenir(lane, b)

    def souvenir(self, lane, b):
        for trait in self.traits[lane]:
            if trait.get("souvenir") and lane not in self.souvenir_done:
                self.souvenir_done.add(lane)
                self.souvenirs += int(trait["souvenir"])
                idx = self.add("trait", self.fmt(self.c.lines["souvenir"], crew=self.name(lane)), lane=lane,
                               trait=self.trait_id_of(lane, trait), tags=trait.get("souvenir_emits", []),
                               why="%s: +%d cash, leaves evidence." % (trait["name"], trait["souvenir"]), icon="🧸")
                self.emit(trait.get("souvenir_emits", []), idx, b)
                self.stats["seen_traits"].add(self.trait_id_of(lane, trait))

    def complete_requirements(self, slot, b, outcome):
        action = slot["action"]
        for req in self.target["requirements"]:
            if req["id"] in self.done or action["id"] not in req["actions"]:
                continue
            lo, hi = req["window"]
            if not (lo <= slot["start"] + 1 <= hi):
                continue
            ok = True
            for dep in req.get("needs_done", []):
                done_at = self.done.get(dep)
                if done_at is None or done_at >= slot["start"]:
                    ok = False
            if not ok:
                continue
            self.done[req["id"]] = slot["end"]
            self.done.setdefault("_outcome_" + req["id"], outcome)
            if req.get("value", 0) > 0:
                self.done["_grabbed"] = True
            self.add("goal", "Done: %s." % req["label"], lane=slot["lane"], icon="★", action=action["id"],
                     why="Needed %s in beats %d to %d." % (action["name"], lo, hi), extra={"req": req["id"]})
            break

    def resolve_supports(self, b):
        for lane in range(LANES):
            slot = self.slot_at(lane, b)
            if not slot or slot["action"]["kind"] != "support":
                continue
            self.tick(slot, b)
            margin, parts = self.finish_margin(slot)
            if self.preview:
                for tag in slot["action"].get("provides", []):
                    self.tags[tag] = b + 1
                    self.src[tag] = None
                continue
            if slot["lost"]:
                self.add("action", "%s cannot keep watch: out of action." % self.name(lane), lane=lane, outcome="fail",
                         action=slot["action"]["id"], icon=slot["action"]["icon"])
                continue
            outcome = outcome_for(margin, roll(self.seed, b, lane, "act"))
            if outcome == "fail" and self.rerolls_left[lane] > 0:
                self.rerolls_left[lane] -= 1
                outcome = outcome_for(margin, roll(self.seed, b, lane, "reroll"))
            text = self.fmt(slot["action"]["lines"][outcome], crew=self.name(lane))
            provides = slot["action"].get("provides", []) if outcome != "fail" else []
            idx = self.add("support", text, lane=lane, why=self.why_text(parts, margin), outcome=outcome,
                           action=slot["action"]["id"], tags=provides, icon=slot["action"]["icon"])
            if outcome == "fail":
                for tag in slot["action"].get("provides", []):
                    self.src["_missing_" + tag] = idx
            for tag in provides:
                self.tags[tag] = max(self.tags.get(tag, 0), b + 1)
                self.src[tag] = idx
            slot["outcome"], slot["margin"], slot["event"] = outcome, margin, idx

    def run_beat(self, b):
        self.begin_beat(b)
        if not self.preview:
            self.idle_noise(b)
            self.draw(b)
            self.chain(b, "pre")
            self.trait_reactions(b)
            self.chain(b, "pre")
        self.resolve_supports(b)
        for lane in range(LANES):
            slot = self.slot_at(lane, b)
            if not slot or slot["action"]["kind"] != "task":
                continue
            if not self.preview and slot["start"] == b and slot["dur"] > 1 and not slot["lost"]:
                self.add("action_start", self.fmt(slot["action"]["lines"]["start"], crew=self.name(lane)), lane=lane,
                         action=slot["action"]["id"], icon=slot["action"]["icon"])
            self.tick(slot, b)
            if b == slot["end"]:
                self.resolve_slot(slot, b)
        if not self.preview:
            self.chain(b, "post")
            for lane in range(LANES):
                slot = self.slot_at(lane, b)
                if slot and slot["action"]["kind"] in ("standby", "improvise") and not slot.get("spent"):
                    used = any(e["type"] == "absorb" and e["beat"] == b and e.get("lane") == lane for e in self.events)
                    if not used:
                        self.idle_beats[lane] = self.idle_beats.get(lane, 0) + 1
            if b == self.n - 1:
                self.wrap_up()

    def wrap_up(self):
        self.b = self.n - 1
        if self.idle_beats:
            names = ", ".join(self.name(lane) for lane in sorted(self.idle_beats))
            total = sum(self.idle_beats.values())
            self.add("note", self.fmt(self.c.lines["idle_summary"], names=names, n=total), icon="…",
                     extra={"idle_beats": total})
        if "_grabbed" in self.done:
            final = [r for r in self.target["requirements"] if r.get("final")]
            if final and final[0]["id"] not in self.done:
                self.done["_stranded"] = True
                self.add("note", self.c.lines["stranded"], icon="🚶")
        else:
            self.add("note", self.c.lines["no_take"], icon="…")

    def run(self):
        for b in range(self.n):
            self.run_beat(b)
        return self

    # ---- results --------------------------------------------------------------------------
    def chain_links(self):
        """Longest cause chain: the number of events along the deepest path of causes. Returns (length, path)."""
        best = (0, [])
        for ev in self.events:
            if ev["type"] in ("beat", "note", "idle", "standby", "action_start", "goal"):
                continue
            d = ev["depth"]
            if d > best[0]:
                path = []
                cur = ev["i"]
                while cur is not None:
                    path.append(cur)
                    cur = self.events[cur]["cause"]
                best = (d, list(reversed(path)))
        return best

    def result(self):
        reqs = self.target["requirements"]
        completed = [r["id"] for r in reqs if r["id"] in self.done]
        value = sum(r.get("value", 0) for r in reqs if r["id"] in self.done)
        extra_loot = 0
        heat_extra = 0
        escaped = any(r.get("final") and r["id"] in self.done for r in reqs)
        for lane in range(LANES):
            for trait in self.traits[lane]:
                if escaped:
                    extra_loot += int(trait.get("extra_loot", 0))
                    heat_extra += int(trait.get("extra_heat", 0))
        loot = value
        if "_grabbed" in self.done and not escaped:
            loot = value // 2
        loot = max(0, loot - self.loot_lost) + extra_loot if "_grabbed" in self.done else 0
        links, path = self.chain_links()
        sidelined = sorted({self.crew_ids[e["lane"]] for e in self.events if e["type"] == "sidelined"})
        heat = min(10, self.suspicion + heat_extra)
        damages = self.damage + 10 * len(sidelined)
        bonuses = []
        consolation = int(self.target.get("consolation", 20))
        if escaped and not self.alarm:
            bonuses.append({"id": "clean", "label": "Clean (no alarm)", "amount": 60})
        if escaped and links >= 3:
            bonuses.append({"id": "chaos", "label": "Chaos Theory (a %d-link chain)" % links, "amount": 40})
        if escaped and self.fees and self.fees <= int(self.target.get("budget", 0)):
            bonuses.append({"id": "budget", "label": "Under Budget", "amount": 30})
        if escaped and not sidelined:
            bonuses.append({"id": "home", "label": "Everyone Home", "amount": 40})
        bonus_total = sum(b["amount"] for b in bonuses)
        gross = int((loot + self.souvenirs) * (100 - 4 * heat) / 100)
        net = max(consolation, gross + bonus_total - damages)
        cells = sum(1 for lane in self.plan["lanes"] for cell in lane if cell)
        per_beat = [sum(1 for lane in range(LANES) if self.busy(lane, b)) for b in range(self.n)]
        return {
            "completed": completed, "missed": [r["id"] for r in reqs if r["id"] not in self.done and not r.get("optional")],
            "escaped": escaped, "stranded": bool(self.done.get("_stranded")),
            "loot": loot, "souvenirs": self.souvenirs, "heat": heat, "damages": damages, "bonuses": bonuses,
            "gross": gross, "net": net, "alarm": self.alarm, "chain_links": links, "chain_path": path,
            "sidelined": sidelined, "absorbed": len(self.absorbed), "absorbed_ids": list(self.absorbed),
            "complications": list(self.stats["complications"]), "seen_traits": sorted(self.stats["seen_traits"]),
            "cells_used": cells, "cells_total": LANES * self.n, "max_actions_in_a_beat": max(per_beat) if per_beat else 0,
            "chain_capped": self.stats["chain_capped"], "crew_fees": self.fees,
        }


def simulate(content, target_id, crew_ids, plan, gear_ids=(), seed=0, relations=None, fees=0):
    """The whole heist. Returns {'events': [...], 'outcome': {...}, 'beats': [...]}."""
    sim = Sim(content, target_id, crew_ids, plan, gear_ids, seed, relations, fees).run()
    beats = [{"index": i, "name": b["name"]} for i, b in enumerate(sim.target["beats"])]
    return {"events": sim.events, "outcome": sim.result(), "beats": beats, "target": target_id, "seed": seed}


def preview(content, target_id, crew_ids, plan, gear_ids=(), relations=None, hidden_quirks=()):
    """Per-cell odds for the planning screen, with nothing random in it. Returns a list (per lane) of dicts
    keyed by start beat: {margin, word, parts}."""
    sim = Sim(content, target_id, crew_ids, plan, gear_ids, 0, relations, 0, preview=True, hidden_quirks=hidden_quirks)
    sim.run()
    out = []
    for lane in range(LANES):
        cells = {}
        for slot in sim.slots[lane]:
            if slot["action"]["kind"] not in ("task", "support"):
                continue
            margin, parts = sim.finish_margin(slot)
            cells[slot["start"]] = {"margin": margin, "word": odds_word(margin), "parts": parts, "dur": slot["dur"],
                                    "truncated": slot["truncated"]}
        out.append(cells)
    return out


def pair_preview(content, target_id, crew_ids, plan, relations=None, hidden_quirks=()):
    """Relationships the current plan sets off (for the planning screen): a list of dicts."""
    sim = Sim(content, target_id, crew_ids, plan, (), 0, relations, 0, preview=True, hidden_quirks=hidden_quirks)
    seen = set()
    out = []
    for b in range(sim.n):
        for lane in range(LANES):
            for eff in sim.pair_effects(lane, b):
                if eff["key"] in seen:
                    continue
                seen.add(eff["key"])
                other = eff["partner"]
                out.append({"beat": b, "lane": lane, "partner": other, "kind": eff["kind"], "value": eff["value"],
                            "text": eff["line"] if eff.get("prefilled") else sim.fmt(
                                eff["line"], a=sim.name(lane), b=sim.name(other), mentor=sim.name(other), pupil=sim.name(lane),
                                crew=sim.name(lane))})
    return out
