"""Continuum -- K-15 notable citizens and K-28 the citizen of the season.

**Original, invented people only.** Every name here is made up from word lists in this file
and every line of flavour is written for the game. No real person, living or historical, is
named, and none of the lines states a real-world fact (so there is nothing to source). Like
the rest of the story text, the citizens' panel and the spotlight card are hidden by the
story toggle; the one mechanical effect (below) stays visible as a City Views row.

**Notable citizens (K-15).** Each time the settlement enters an era a new child appears in it,
named from the lists below. They follow the city: apprenticed in the next era, a master of
the era's trade in the one after (a small standing bonus, one to three percent, halved once
they are an elder), then remembered. Roughly: a child of the Tribal fire-tenders is
apprenticed to a seed-keeper in the Agrarian era and is the canal-warden of the Classical.
At most two citizens are ever giving a bonus at once. The bonus rests during a challenge run
or consulting case (comparable runs), and the whole feature can be switched off.

**Citizen of the season (K-28).** After every season one named resident, drawn from the
notable citizens or an ordinary townsperson, gets a one-line spotlight tied to the most
notable thing that happened that season (a hungry season, a new building, a discovery, a
birth, an era entered, or a calm one). The last few are kept.

Pure functions of a plain dict (`campaign.ui["citizens"]`), validated on every read. Nothing
is random at play time: the choice of name and line is a hash of the saved seed and the
season, so the same save always shows the same people.
"""

import math

import dynasty
import sim

KEY = "citizens"
MAX_ROSTER = len(sim.ERA_ORDER)
MAX_SPOTS = 8
MAX_SEED = 2**31 - 1

FIRST_NAMES = (
    "Maren", "Tobin", "Ilsa", "Corvin", "Pell", "Yarrow", "Sunni", "Dorrel", "Wenna", "Hask",
    "Brindle", "Ottoline", "Rafe", "Tamsin", "Orrin", "Lisbet", "Quill", "Nessa", "Garrick", "Ysolde",
    "Fennick", "Marisol", "Dunstan", "Kesia", "Ravi", "Anselm", "Joss", "Thessaly",
)
LAST_NAMES = (
    "Hearthwick", "Marsh", "Oakhollow", "Venn", "Stonebrook", "Ashgrove", "Tallow", "Brightwater",
    "Coldharbour", "Reed", "Kestrel", "Lowmoor", "Thornwell", "Underhill", "Wick", "Fairlight",
    "Greywether", "Holloway", "Ironside", "Jessamine", "Larkspur", "Merrow", "Northcote", "Quillon",
)

# What the people of each era do. `household` is the work a child's family does there;
# `master` is the title held by a master of the era's trade; `bonus` is what that master adds.
ERA_TRADES = {
    "tribal": {"household": "fire-tenders", "master": "Pathfinder", "bonus": {"food_yield_mult": 0.02}},
    "agrarian": {"household": "field families", "master": "Seed-keeper", "bonus": {"food_yield_mult": 0.02}},
    "classical": {"household": "canal-diggers", "master": "Canal-warden", "bonus": {"materials_yield_mult": 0.02}},
    "medieval": {"household": "guild households", "master": "Guild-master", "bonus": {"tool_yield_mult": 0.03}},
    "industrial": {"household": "mill families", "master": "Foreman", "bonus": {"materials_yield_mult": 0.02}},
    "digital": {"household": "network crews", "master": "Systems engineer", "bonus": {"knowledge_mult": 0.03}},
    "space": {"household": "habitat crews", "master": "Habitat engineer", "bonus": {"knowledge_mult": 0.02}},
    "relay": {"household": "relay crews", "master": "Wayfinder-captain", "bonus": {"relay_bonus": 0.03}},
}

STAGES = ("child", "apprentice", "master", "elder", "remembered")
ELDER_FACTOR = 0.5

# Spotlight lines by what happened. {name} and {trade} are filled in; {detail} names the
# building or discovery. Several variants each, chosen by a hash of the seed and the season.
SPOTLIGHT = {
    "hunger": (
        "{name} shared a thin supper and said little about it. The {trade} season was hard on everyone.",
        "{name} was up before dawn looking for anything to eat, and found a little for the neighbours too.",
        "In the hungry weeks {name} kept a tally of who had eaten, so that no household was missed.",
    ),
    "research": (
        "{name} was first to try {detail}, and has been explaining it to anyone who stands still.",
        "{name} argued over {detail} at the evening meal, and lost, and was glad to.",
        "Everyone is talking about {detail}; {name} is the one who wrote the first notes down.",
    ),
    "build": (
        "{name} carried the first load for {detail} and claims the best view of it.",
        "{name} measured {detail} twice, and the second time it was right.",
        "When {detail} went up, {name} was already planning where the lamp should hang.",
    ),
    "era": (
        "{name} watched the new age begin from the edge of the square, and said it felt like any other morning.",
        "{name} packed a small bundle, unpacked it again, and stayed. The new age needs people who stay.",
    ),
    "birth": (
        "{name} was first to hold the new baby and has already offered to teach it everything.",
        "{name} brought food to the new parents and stayed to sing, badly.",
    ),
    "spoil": (
        "{name} spent the day turning over what was left in the stores, muttering about waste.",
        "{name} salvaged what could be saved from the stores and wrote down what could not.",
    ),
    "calm": (
        "{name} had a quiet season, mended a few things, and counted that as a good one.",
        "Nothing happened to {name} this season, and {name} was grateful for it.",
        "{name} spent the quiet weeks teaching a child to read the weather.",
    ),
}
EVENT_PRIORITY = ("hunger", "era", "research", "build", "birth", "spoil", "calm")
ORDINARY_TRADES = ("baker", "weaver", "ferryman", "potter", "tinker", "beekeeper", "cartwright", "lamplighter")


def _int(value, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return low
    if isinstance(value, float) and not math.isfinite(value):
        return low
    return min(max(int(value), low), high)


def _hash(*parts):
    """A small stable integer hash (no randomness, no Python hash() salt)."""
    value = 2166136261
    for part in parts:
        for ch in str(part):
            value = ((value ^ ord(ch)) * 16777619) & 0xFFFFFFFF
        value = ((value ^ 0x9E3779B9) * 16777619) & 0xFFFFFFFF
    return value


def clean_name(raw):
    """A name from the lists above; anything else is refused (names are never player text)."""
    if not isinstance(raw, str):
        return ""
    first, _, last = raw.partition(" ")
    return raw if first in FIRST_NAMES and last in LAST_NAMES else ""


def default():
    return {"seed": 0, "off": False, "roster": [], "spots": []}


def clean_spot(raw):
    if not isinstance(raw, dict):
        return None
    name = raw.get("name")
    line = raw.get("line")
    season = raw.get("season")
    event = raw.get("event")
    if not isinstance(name, str) or not name.strip() or not isinstance(line, str) or not line.strip():
        return None
    if isinstance(season, bool) or not isinstance(season, int) or season < 1:
        return None
    if event not in SPOTLIGHT:
        return None
    return {
        "season": min(season, 10**7),
        "name": name.strip()[:60],
        "line": line.strip()[:240],
        "event": event,
        "notable": raw.get("notable") is True,
    }


def clean(raw):
    out = default()
    if not isinstance(raw, dict):
        return out
    out["seed"] = _int(raw.get("seed"), 0, MAX_SEED)
    out["off"] = raw.get("off") is True
    seen_eras = set()
    roster = raw.get("roster")
    for item in roster if isinstance(roster, list) else []:
        if not isinstance(item, dict):
            continue
        name = clean_name(item.get("name"))
        era = item.get("born")
        if not name or era not in sim.ERA_ORDER or era in seen_eras:
            continue
        seen_eras.add(era)
        out["roster"].append({"name": name, "born": era})
    out["roster"].sort(key=lambda c: sim.era_index(c["born"]))
    out["roster"] = out["roster"][:MAX_ROSTER]
    spots = raw.get("spots")
    for item in spots if isinstance(spots, list) else []:
        spot = clean_spot(item)
        if spot is not None:
            out["spots"].append(spot)
    out["spots"] = out["spots"][-MAX_SPOTS:]
    return out


def get(ui):
    return clean(ui.get(KEY)) if isinstance(ui, dict) else default()


def put(ui, record):
    record = clean(record)
    if record == default():
        ui.pop(KEY, None)
    else:
        ui[KEY] = record
    return record


def set_off(ui, off):
    record = get(ui)
    record["off"] = bool(off)
    put(ui, record)
    return record["off"]


def is_on(ui):
    return not get(ui)["off"]


# --- the roster ------------------------------------------------------------------------------
def make_name(seed, era):
    """The invented name of the child born in `era` (a hash of the seed and the era)."""
    first = FIRST_NAMES[_hash(seed, era, "first") % len(FIRST_NAMES)]
    last = LAST_NAMES[_hash(seed, era, "last") % len(LAST_NAMES)]
    return f"{first} {last}"


def ensure_roster(ui, furthest_era, seed_hint=1):
    """Adds the child of every era up to `furthest_era` that has none yet. Returns the new
    citizens (oldest first). `seed_hint` seeds the roster the first time only (the game passes
    something that differs between settlements); after that the saved seed rules."""
    record = get(ui)
    if furthest_era not in sim.ERA_ORDER:
        return []
    if not record["seed"]:
        record["seed"] = _int(seed_hint, 1, MAX_SEED) or 1
    have = {c["born"] for c in record["roster"]}
    added = []
    for era in sim.ERA_ORDER[: sim.era_index(furthest_era) + 1]:
        if era in have:
            continue
        citizen = {"name": make_name(record["seed"], era), "born": era}
        record["roster"].append(citizen)
        added.append(citizen)
    if added:
        record["roster"].sort(key=lambda c: sim.era_index(c["born"]))
        put(ui, record)
    return added


def stage_of(citizen, era):
    """{'stage', 'age', 'title', 'line', 'bonus': {}} for one citizen as of era `era`."""
    age = max(0, sim.era_index(era) - sim.era_index(citizen["born"]))
    stage = STAGES[min(age, len(STAGES) - 1)]
    name = citizen["name"]
    born_trade = ERA_TRADES[citizen["born"]]["household"]
    now = ERA_TRADES[era]
    if stage == "child":
        title = f"Child of the {born_trade}"
        line = f"{name} is a child of the {born_trade}."
        bonus = {}
    elif stage == "apprentice":
        title = f"Apprentice {now['master']}"
        line = f"{name}, born among the {born_trade}, is apprenticed to a {now['master'].lower()}."
        bonus = {}
    elif stage == "master":
        title = now["master"]
        line = f"{name} is the settlement's {now['master'].lower()}, born among the {born_trade}."
        bonus = dict(now["bonus"])
    elif stage == "elder":
        title = f"Elder {now['master']}"
        line = f"{name}, elder {now['master'].lower()}, trains the next ones."
        bonus = {key: value * ELDER_FACTOR for key, value in now["bonus"].items()}
    else:
        title = "Remembered"
        line = f"{name} is remembered, born among the {born_trade}."
        bonus = {}
    return {"stage": stage, "age": age, "title": title, "line": line, "bonus": bonus}


def thread(citizen, era):
    """The citizen's life so far, one line per era from birth to `era`."""
    lines = []
    for index in range(sim.era_index(citizen["born"]), sim.era_index(era) + 1):
        lines.append(f"{sim.ERA_LABEL[sim.ERA_ORDER[index]]}: {stage_of(citizen, sim.ERA_ORDER[index])['line']}")
    return lines


def bonus_deltas(ui, era, resting=False):
    """The citizens' standing bonuses as research-style additive deltas ({} when off or resting)."""
    record = get(ui)
    if record["off"] or resting or era not in sim.ERA_ORDER:
        return {}
    deltas = {}
    for citizen in record["roster"]:
        for key, value in stage_of(citizen, era)["bonus"].items():
            deltas[key] = deltas.get(key, 0.0) + value
    return deltas


def apply_effects(effects, ui, era, resting=False):
    deltas = bonus_deltas(ui, era, resting)
    if not deltas:
        return effects
    return dynasty.add_deltas(effects, deltas)


def bonus_text(deltas):
    """'food yield +2%, knowledge output +3%' (research.describe_effects wording)."""
    import research  # local import: research imports sim only, but keep this module light
    node = type("Node", (), {"effects": deltas})
    return research.describe_effects(node)


# --- the citizen of the season ---------------------------------------------------------------
def classify_events(report, motions, season):
    """The kinds of event that happened this season, from the season report and the council
    minutes recorded in it. `motions` are minutes entries; `season` is the season just run."""
    kinds = set()
    report = report if isinstance(report, dict) else {}
    deaths = report.get("deaths")
    births = report.get("births")
    spoiled = report.get("spoiled")
    if isinstance(deaths, (int, float)) and not isinstance(deaths, bool) and deaths > 0:
        kinds.add("hunger")
    fed = report.get("fed_fraction")
    if isinstance(fed, (int, float)) and not isinstance(fed, bool) and fed < 1.0:
        kinds.add("hunger")
    if isinstance(births, (int, float)) and not isinstance(births, bool) and births > 0:
        kinds.add("birth")
    if isinstance(spoiled, (int, float)) and not isinstance(spoiled, bool) and spoiled >= 3:
        kinds.add("spoil")
    details = {}
    for motion in motions if isinstance(motions, list) else []:
        if not isinstance(motion, dict) or motion.get("season") != season:
            continue
        kind = motion.get("kind")
        if kind in ("research", "build", "era"):
            kinds.add(kind)
            details.setdefault(kind, _detail_of(motion.get("text", "")))
    if not kinds:
        kinds.add("calm")
    return kinds, details


def _detail_of(text):
    """'study X.' / 'build X.' / 'enters X.' -> 'X'."""
    if not isinstance(text, str):
        return "it"
    for marker in ("study ", "build ", "enters "):
        if marker in text:
            return text.split(marker, 1)[1].rstrip(". ") or "it"
    return "it"


def pick_event(kinds):
    for kind in EVENT_PRIORITY:
        if kind in kinds:
            return kind
    return "calm"


def choose_resident(record, era, season):
    """(name, trade text, is_notable): a notable citizen about half the time when there are any,
    otherwise an ordinary townsperson with an invented name."""
    seed = record["seed"] or 1
    roster = [c for c in record["roster"] if sim.era_index(c["born"]) <= sim.era_index(era)]
    if roster and _hash(seed, season, "who") % 2 == 0:
        citizen = roster[_hash(seed, season, "pick") % len(roster)]
        return citizen["name"], stage_of(citizen, era)["title"].lower(), True
    first = FIRST_NAMES[_hash(seed, season, "of") % len(FIRST_NAMES)]
    last = LAST_NAMES[_hash(seed, season, "ol") % len(LAST_NAMES)]
    trade = ORDINARY_TRADES[_hash(seed, season, "ot") % len(ORDINARY_TRADES)]
    return f"{first} {last}", trade, False


def make_spotlight(ui, era, season, report, motions):
    """Builds, stores and returns the spotlight for the season just played (or None when the
    feature is off or the inputs are unusable). One spotlight per season: asking again for the
    same season returns the stored one."""
    record = get(ui)
    if record["off"] or era not in sim.ERA_ORDER or isinstance(season, bool) or not isinstance(season, int) or season < 1:
        return None
    for spot in record["spots"]:
        if spot["season"] == season:
            return spot
    if not record["seed"]:
        record["seed"] = 1
    kinds, details = classify_events(report, motions, season)
    event = pick_event(kinds)
    name, trade, notable = choose_resident(record, era, season)
    variants = SPOTLIGHT[event]
    template = variants[_hash(record["seed"], season, "line") % len(variants)]
    line = template.format(name=name, trade=trade, detail=details.get(event, "the new work"))
    spot = {"season": season, "name": name, "line": line, "event": event, "notable": notable}
    record["spots"].append(spot)
    record["spots"] = record["spots"][-MAX_SPOTS:]
    put(ui, record)
    return spot


def latest_spot(ui):
    spots = get(ui)["spots"]
    return spots[-1] if spots else None
