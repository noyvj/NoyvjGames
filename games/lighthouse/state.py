"""Lighthouse -- the save: every piece of mutable state, with a fully validated way back in.

`Keep.to_dict()` writes only what differs from the default (a newer key is simply absent in an older save and
an older save loads unchanged); `Keep.from_dict()` rebuilds a Keep from anything at all and never raises: a bad
field is dropped one at a time and the default stays. The weather and the ships are never stored, they are
regenerated from the seed and the night; only the keeper's progress through tonight's ships is.
"""

import math

from clock import night_len
import lore
from data import (BOAT_CRATES, COMFORT_MAX, CRATE_KINDS, DEFAULT_ORDER, ENERGY_MAX, INCIDENT_KINDS, LEVELS, LOG_KEEP,
                  OIL_CAP_BIG, PARTS, REP_CAP, START_ENERGY, START_OIL, START_STRUCTURE, START_SUPPLIES, SUPPLIES,
                  SUPPLY_CAP, UPGRADE_IDS)

SCHEMA = 1
PHASES = ("evening", "night", "morning", "day", "yearend")
MODES = ("year", "endless")
SHIP_STATES = ("pending", "passed", "delayed", "damaged")
LOG_KINDS = ("ship", "weather", "incident", "damage", "lamp", "clock", "keeper", "note", "story")
TASKS = ("wind", "watch", "repair")
FOCUS_CHOICES = ("worst",) + PARTS
STORY_KEYS = ("met", "inbox", "read", "gifts", "choices", "buffs")
COUNTER_NAMES = ("quiet_nights", "fog_clears", "storm_wardens", "tidy_days", "frugal_seasons", "empty_nights",
                 "wound_streak", "best_wound_streak", "calm_years", "eerie_off_nights", "cleared_year_eerie_off")
MAX_SEED = 2 ** 31 - 1


# ---- tolerant readers ----------------------------------------------------------------------------------
def num(value, lo, hi, default, integer=True):
    """A number clamped into [lo, hi]; anything that is not a finite number gives the default."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return default
    value = max(lo, min(hi, value))
    return int(round(value)) if integer else round(float(value), 2)


def text(value, limit=200, default=""):
    return value[:limit] if isinstance(value, str) else default


def pick_one(value, choices, default):
    return value if isinstance(value, str) and value in choices else default


def as_dict(value):
    return value if isinstance(value, dict) else {}


def as_list(value):
    return value if isinstance(value, list) else []


def clean_order(raw):
    """A boat order: five crate counts that add up to BOAT_CRATES. Anything else gives the default."""
    raw = as_dict(raw)
    order = {k: num(raw.get(k), 0, BOAT_CRATES, -1) for k in CRATE_KINDS}
    if any(v < 0 for v in order.values()) or sum(order.values()) != BOAT_CRATES:
        return dict(DEFAULT_ORDER)
    return order


class Keep(object):
    """One keeper's whole state: the current run and the lifetime meta."""

    def __init__(self, seed=1):
        self.new_run(seed)
        self.meta = new_meta()

    # ---- a fresh run -----------------------------------------------------------------------------------
    def new_run(self, seed):
        self.seed = num(seed, 0, MAX_SEED, 1)
        self.night = 1
        self.phase = "evening"
        self.tick = 0
        self.mode = "year"
        self.quiet = False
        self.oil = float(START_OIL)
        self.supplies = dict(START_SUPPLIES)
        self.structure = dict(START_STRUCTURE)
        self.energy = float(START_ENERGY)
        self.reputation = 0
        self.comfort = 0
        self.salvage = 0
        self.levels = [1, 1, 1]
        self.tasks = {"wind": True, "watch": False, "repair": False}
        self.ration = 0
        self.focus = "worst"
        self.clock_left = 0.0
        self.override = None
        self.incident = None
        self.progress = {}
        self.mail_tonight = False
        self.boat_due = False
        self.order = dict(DEFAULT_ORDER)
        self.upgrades = []
        self.waiting = []
        self.day_slots = 0
        self.hungry = False
        self.repaired_today = []
        self.combed = False
        self.night_stats = new_night_stats()
        self.season_min_oil = float(START_OIL)
        self.log = []
        self.report = None
        self.delivery = None
        self.story = new_story()

    # ---- derived ---------------------------------------------------------------------------------------
    def has(self, upgrade):
        return upgrade in self.upgrades

    def oil_cap(self):
        return OIL_CAP_BIG if self.has("cistern") else 200

    def level_name(self, index):
        return LEVELS[index]

    def add_log(self, kind, line):
        self.log.append([int(self.tick), kind, str(line)[:200]])
        if len(self.log) > LOG_KEEP:
            del self.log[:len(self.log) - LOG_KEEP]

    # ---- save ------------------------------------------------------------------------------------------
    def to_dict(self):
        run = {
            "seed": self.seed, "night": self.night, "phase": self.phase, "tick": self.tick,
            "oil": round(self.oil, 1), "supplies": dict(self.supplies), "structure": dict(self.structure),
            "energy": round(self.energy, 1), "reputation": self.reputation, "comfort": self.comfort,
            "salvage": self.salvage, "plan": {"levels": [LEVELS[i] for i in self.levels], "tasks": dict(self.tasks)},
        }
        if self.ration:
            run["plan"]["ration"] = self.ration
        if self.focus != "worst":
            run["plan"]["focus"] = self.focus
        if self.mode != "year":
            run["mode"] = self.mode
        if self.quiet:
            run["quiet"] = True
        if self.clock_left:
            run["clock_left"] = round(self.clock_left, 2)
        if self.override:
            run["override"] = list(self.override)
        if self.incident:
            run["incident"] = dict(self.incident)
        if self.progress:
            run["progress"] = {k: dict(v) for k, v in self.progress.items()}
        if self.mail_tonight:
            run["mail_tonight"] = True
        if self.boat_due:
            run["boat_due"] = True
        if self.order != DEFAULT_ORDER:
            run["order"] = dict(self.order)
        if self.upgrades:
            run["upgrades"] = list(self.upgrades)
        if self.waiting:
            run["waiting"] = [dict(w) for w in self.waiting]
        if self.day_slots:
            run["day_slots"] = self.day_slots
        if self.hungry:
            run["hungry"] = True
        if self.repaired_today:
            run["repaired_today"] = list(self.repaired_today)
        if self.combed:
            run["combed"] = True
        stats = {k: v for k, v in self.night_stats.items() if v != new_night_stats()[k]}
        if stats:
            run["night_stats"] = stats
        if self.season_min_oil != float(START_OIL):
            run["season_min_oil"] = round(self.season_min_oil, 1)
        if self.log:
            run["log"] = [list(entry) for entry in self.log]
        if self.report:
            run["report"] = self.report
        if self.delivery:
            run["delivery"] = self.delivery
        story = story_to_dict(self.story)
        if story:
            run["story"] = story
        return {"schema": SCHEMA, "meta": meta_to_dict(self.meta), "run": run}

    @classmethod
    def from_dict(cls, data):
        keep = cls(1)
        data = as_dict(data)
        keep.meta = meta_from_dict(data.get("meta"))
        run = as_dict(data.get("run"))
        if not run:
            return keep
        keep.seed = num(run.get("seed"), 0, MAX_SEED, 1)
        keep.night = num(run.get("night"), 1, 100000, 1)
        keep.phase = pick_one(run.get("phase"), PHASES, "evening")
        length = night_len(keep.night)
        keep.tick = num(run.get("tick"), 0, length, 0)
        keep.mode = pick_one(run.get("mode"), MODES, "year")
        keep.quiet = run.get("quiet") is True
        keep.oil = float(num(run.get("oil"), 0, OIL_CAP_BIG, START_OIL, integer=False))
        sup = as_dict(run.get("supplies"))
        keep.supplies = {k: num(sup.get(k), 0, SUPPLY_CAP, START_SUPPLIES[k]) for k in SUPPLIES}
        st = as_dict(run.get("structure"))
        keep.structure = {k: num(st.get(k), 0, 100, START_STRUCTURE[k]) for k in PARTS}
        keep.energy = float(num(run.get("energy"), 0, ENERGY_MAX, START_ENERGY, integer=False))
        keep.reputation = num(run.get("reputation"), 0, REP_CAP, 0)
        keep.comfort = num(run.get("comfort"), 0, COMFORT_MAX, 0)
        keep.salvage = num(run.get("salvage"), 0, 9999, 0)
        plan = as_dict(run.get("plan"))
        lv = as_list(plan.get("levels"))
        keep.levels = [LEVELS.index(lv[i]) if i < len(lv) and isinstance(lv[i], str) and lv[i] in LEVELS else 1
                       for i in range(3)]
        tk = as_dict(plan.get("tasks"))
        keep.tasks = {t: (tk.get(t) is True if t in tk else keep.tasks[t]) for t in TASKS}
        keep.ration = num(plan.get("ration"), 0, 400, 0)
        keep.focus = pick_one(plan.get("focus"), FOCUS_CHOICES, "worst")
        keep.clock_left = float(num(run.get("clock_left"), 0, 60, 0, integer=False))
        ov = run.get("override")
        if isinstance(ov, list) and len(ov) == 2:
            level = num(ov[0], 0, 3, -1)
            until = num(ov[1], 0, 200, -1)
            if level >= 0 and until >= 0:
                keep.override = [level, until]
        inc = as_dict(run.get("incident"))
        if inc.get("kind") in INCIDENT_KINDS:
            keep.incident = {"kind": inc["kind"], "tick": num(inc.get("tick"), 0, 200, 0),
                             "expires": num(inc.get("expires"), 0, 400, 0)}
        for ship_id, rec in list(as_dict(run.get("progress")).items())[:12]:
            rec = as_dict(rec)
            if isinstance(ship_id, str) and len(ship_id) <= 12:
                keep.progress[ship_id] = {"seen": num(rec.get("seen"), 0, 60, 0), "danger": num(rec.get("danger"), 0, 60, 0),
                                          "state": pick_one(rec.get("state"), SHIP_STATES, "pending")}
        keep.mail_tonight = run.get("mail_tonight") is True
        keep.boat_due = run.get("boat_due") is True
        keep.order = clean_order(run.get("order")) if "order" in run else dict(DEFAULT_ORDER)
        keep.upgrades = [u for u in dict.fromkeys(as_list(run.get("upgrades"))) if isinstance(u, str) and u in UPGRADE_IDS]
        for w in as_list(run.get("waiting"))[:6]:
            w = as_dict(w)
            if isinstance(w.get("id"), str):
                keep.waiting.append({"id": text(w["id"], 12), "kind": pick_one(w.get("kind"), ("fisher", "ferry", "cargo", "yacht", "mail"), "fisher"),
                                     "name": text(w.get("name"), 40, "A ship")})
        keep.day_slots = num(run.get("day_slots"), 0, 12, 0)
        keep.hungry = run.get("hungry") is True
        keep.repaired_today = [p for p in dict.fromkeys(as_list(run.get("repaired_today"))) if p in PARTS]
        keep.combed = run.get("combed") is True
        stats = as_dict(run.get("night_stats"))
        base = new_night_stats()
        for key, default in base.items():
            if key in stats:
                if isinstance(default, bool):
                    base[key] = stats[key] is True
                elif isinstance(default, float):
                    base[key] = float(num(stats[key], 0, 100000, default, integer=False))
                elif isinstance(default, list):
                    base[key] = [p for p in dict.fromkeys(as_list(stats[key])) if isinstance(p, str)][:12]
                else:
                    base[key] = num(stats[key], 0, 100000, default)
        keep.night_stats = base
        keep.season_min_oil = float(num(run.get("season_min_oil"), 0, OIL_CAP_BIG, keep.oil, integer=False)) \
            if "season_min_oil" in run else keep.oil
        for entry in as_list(run.get("log"))[-LOG_KEEP:]:
            if isinstance(entry, list) and len(entry) == 3 and isinstance(entry[2], str):
                keep.log.append([num(entry[0], 0, 200, 0), pick_one(entry[1], LOG_KINDS, "note"), entry[2][:200]])
        keep.report = clean_report(run.get("report"))
        keep.delivery = clean_delivery(run.get("delivery"))
        keep.story = story_from_dict(run.get("story"))
        return keep


def new_story():
    """The story layer's progress in this run. Every key is written only when it holds something."""
    return {"met": {}, "inbox": [], "read": [], "gifts": [], "choices": {}, "buffs": {}}


def story_to_dict(story):
    out = {}
    if story["met"]:
        out["met"] = dict(story["met"])
    if story["inbox"]:
        out["inbox"] = [dict(i) for i in story["inbox"]]
    for key in ("read", "gifts"):
        if story[key]:
            out[key] = list(story[key])
    if story["choices"]:
        out["choices"] = {k: list(v) for k, v in story["choices"].items()}
    buffs = {k: v for k, v in story["buffs"].items() if v}
    if buffs:
        out["buffs"] = buffs
    return out


def story_from_dict(raw):
    raw = as_dict(raw)
    story = new_story()
    met = as_dict(raw.get("met"))
    story["met"] = {k: num(met[k], 0, 10 ** 5, 0) for k in lore.SAILORS if k in met}
    seen = set()
    for item in as_list(raw.get("inbox"))[:80]:
        item = as_dict(item)
        lid = item.get("id")
        if isinstance(lid, str) and lid in lore.LETTERS and lid not in seen:
            seen.add(lid)
            story["inbox"].append({"id": lid, "night": num(item.get("night"), 1, 100000, 1)})
    story["read"] = [i for i in dict.fromkeys(as_list(raw.get("read"))) if isinstance(i, str) and i in seen]
    story["gifts"] = [g for g in dict.fromkeys(as_list(raw.get("gifts"))) if isinstance(g, str) and g in lore.GIFTS]
    choices = as_dict(raw.get("choices"))
    for lid, pair in choices.items():
        letter = lore.LETTERS.get(lid)
        pair = as_list(pair)
        if letter and lid in story["read"] and len(pair) == 2 and any(pair[0] == r[0] for r in letter.get("replies", ())):
            story["choices"][lid] = [pair[0], num(pair[1], 1, 100000, 1)]
    buffs = as_dict(raw.get("buffs"))
    story["buffs"] = {k: num(buffs[k], 0, 99, 0) for k in ("lens_cloth",) if k in buffs}
    return story


def new_night_stats():
    return {"oil_used": 0.0, "lamp_ticks": 0, "incidents": 0, "unhandled": 0, "damage": 0, "delayed": 0,
            "damaged": 0, "passed": 0, "rep": 0, "salvage": 0, "dark": False, "stopped": False, "ration_hit": False,
            "worst_cond": 0, "fog_ticks": 0, "events": 0, "wound": 0, "rescued": 0, "mail_landed": False}


def new_meta():
    return {
        "nights_kept": 0, "years": 0, "ships_passed": 0, "ships_delayed": 0, "ships_damaged": 0, "rescues": 0,
        "lamp_ticks": 0, "oil_used": 0.0, "clean_streak": 0, "best_clean_streak": 0, "best_lamp_hours_year": 0,
        "year_lamp_ticks": 0, "counters": {}, "achievements_earned": [],
        "story": {"met": [], "letters": [], "gifts": []},
    }


def meta_to_dict(meta):
    out = {k: v for k, v in meta.items() if v not in (0, 0.0, [], {})}
    out["counters"] = {k: v for k, v in meta["counters"].items() if v}
    if not out["counters"]:
        del out["counters"]
    ever = {k: list(v) for k, v in meta["story"].items() if v}
    out.pop("story", None)
    if ever:
        out["story"] = ever
    return out


def meta_from_dict(raw):
    raw = as_dict(raw)
    meta = new_meta()
    for key in ("nights_kept", "years", "ships_passed", "ships_delayed", "ships_damaged", "rescues", "lamp_ticks",
                "clean_streak", "best_clean_streak", "best_lamp_hours_year", "year_lamp_ticks"):
        meta[key] = num(raw.get(key), 0, 10 ** 7, 0)
    meta["oil_used"] = float(num(raw.get("oil_used"), 0, 10 ** 8, 0, integer=False))
    counters = as_dict(raw.get("counters"))
    meta["counters"] = {k: num(counters.get(k), 0, 10 ** 6, 0) for k in COUNTER_NAMES if k in counters}
    ever = as_dict(raw.get("story"))
    meta["story"] = {
        "met": [x for x in dict.fromkeys(as_list(ever.get("met"))) if x in lore.SAILORS],
        "letters": [x for x in dict.fromkeys(as_list(ever.get("letters"))) if x in lore.LETTERS],
        "gifts": [x for x in dict.fromkeys(as_list(ever.get("gifts"))) if x in lore.GIFTS],
    }
    earned = as_list(raw.get("achievements_earned"))
    meta["achievements_earned"] = [e for e in dict.fromkeys(earned) if isinstance(e, str) and len(e) <= 40][:80]
    return meta


def clean_report(raw):
    """A morning report is plain display data; keep only a bounded, simple shape."""
    raw = as_dict(raw)
    if not raw:
        return None
    out = {"night": num(raw.get("night"), 1, 100000, 1), "summary": text(raw.get("summary"), 300)}
    out["ships"] = [{"name": text(as_dict(s).get("name"), 40), "kind": text(as_dict(s).get("kind"), 12),
                     "outcome": pick_one(as_dict(s).get("outcome"), SHIP_STATES, "passed")} for s in as_list(raw.get("ships"))[:8]]
    for key in ("lamp_hours", "oil_used"):
        out[key] = float(num(raw.get(key), 0, 100000, 0, integer=False))
    for key in ("damage", "incidents", "rep", "salvage", "passed", "delayed", "damaged"):
        out[key] = num(raw.get(key), -1000, 100000, 0)
    out["worst"] = num(raw.get("worst"), 0, 4, 0)
    out["quiet"] = raw.get("quiet") is True
    out["lines"] = [text(x, 160) for x in as_list(raw.get("lines"))[:10] if isinstance(x, str)]
    out["letters"] = [{"id": i, "from_name": text(as_dict(x).get("from_name"), 40), "subject": text(as_dict(x).get("subject"), 60)}
                      for x in as_list(raw.get("letters"))[:4] for i in [as_dict(x).get("id")] if isinstance(i, str) and i in lore.LETTERS]
    out["met"] = [text(x, 40) for x in as_list(raw.get("met"))[:6] if isinstance(x, str)]
    return out


def clean_delivery(raw):
    raw = as_dict(raw)
    if not raw:
        return None
    items = {k: num(as_dict(raw.get("items")).get(k), 0, 999, 0) for k in CRATE_KINDS}
    return {"items": items, "text": text(raw.get("text"), 200)}
