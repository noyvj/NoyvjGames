"""Continuum -- K-13: the endless "Beyond" mode, after the Relay Age.

The eight eras end at the Relay Age, but a settlement can go on. **The Beyond** is an
optional mode, offered once the Relay Age is reached, that turns the years after it into a
run of generated **Beyond eras**. Each one has a *theme*, a standing pressure on the
settlement that is named, explained and has a stated remedy, and an **entropy** that
rises as the run goes on, so each pressure bites harder than the last. The score is how
many Beyond eras the settlement survives; the ladder (kept on this device) lists the
furthest runs.

The rules, all of them deterministic (no dice, no hidden events):

* A Beyond era lasts `ERA_SEASONS` (12) seasons. It is **survived** if the sustainability
  score was at or above the era's bar in at least `PASS_SEASONS` (10) of them. The bar
  starts at `BASE_BAR` (40, "Strained") and rises 2 points an era, to at most `MAX_BAR` (75).
* The pressure of the theme comes through the one research seam (the effects dict), so
  it works exactly like a discovery that costs you something. Its strength is the theme's base
  times `1 + entropy`, reduced by the theme's **remedy** (at most 60% in the first era, fading by
  2 points an era to a floor of 20%), a measurable thing
  about the settlement (how full the stores are, how well-tooled the people are, how
  healthy the land is), so every theme can be answered by play and the answer is named.
  A single pressure never takes more than 90% of what it touches.
* Entropy is `ENTROPY_PER_ERA` (0.2) for every era past the first plus `ENTROPY_PER_SEASON`
  (0.01) for every season in the current era, and a general decay takes 4% of food gathered for every
  era past the first (to 70%), so it always rises and the run always gets
  harder; how far a settlement gets is how well it kept up.
* A run that misses a bar **ends** there: the eras survived so far are the result, written to
  the ladder. Ending costs nothing else: the settlement carries on exactly as it is with the
  pressure lifted, and you can begin a new run whenever you like. Nothing is ever lost.

Where it plugs in. The run lives in `campaign.ui["beyond"]` (plain JSON, validated on every
read by `clean()`, written only while a run is on or has banked a best result, so older saves
have none). It rests in a Look Back (the pressure is not applied there). Pure functions
only: no DOM, no storage, no clock. `game.py` owns the panel and the ladder's storage.
"""

import json
import math
import re

import sim

KEY = "beyond"
START_ERA = "relay"

ERA_SEASONS = 12
PASS_SEASONS = 10
BASE_BAR = 40
BAR_PER_ERA = 2
MAX_BAR = 75
ENTROPY_PER_ERA = 0.5
ENTROPY_PER_SEASON = 0.01
REMEDY_CUT = 0.6          # most of a pressure the remedy can take away in the first era
REMEDY_FADE = 0.02        # ... and how much less it can take away with each later era
REMEDY_FLOOR = 0.2
MAX_REDUCTION = 0.9       # no single pressure removes more than this of what it touches
ENTROPY_TAX_PER_ERA = 0.04   # the general decay on food gathered, per era past the first
ENTROPY_TAX_MAX = 0.7
MAX_ERA = 999

# Six themes, cycled in order. `key` is the effects key it presses on, `kind` how
# (a multiplier that goes down, or an additive bonus that goes down), `base` its strength at
# zero entropy and `remedy` the name of the settlement measure that softens it.
THEMES = [
    {"id": "drought", "name": "The Long Drought", "key": "food_yield_mult", "kind": "mult", "base": 0.10,
     "remedy": "full_stores", "what": "food gathered",
     "remedy_text": "keep the food stores full",
     "blurb": "The rains stop coming on time. Every field and foraging round brings in less."},
    {"id": "wear", "name": "Worn Machines", "key": "tool_yield_mult", "kind": "mult", "base": 0.12,
     "remedy": "tooled_people", "what": "tools made",
     "remedy_text": "keep a tool in every pair of hands",
     "blurb": "Nothing built this long ago was meant to last. Every repair costs more than the last."},
    {"id": "archives", "name": "The Quiet Archives", "key": "knowledge_mult", "kind": "mult", "base": 0.12,
     "remedy": "studious", "what": "knowledge gained",
     "remedy_text": "keep a good share of people studying",
     "blurb": "Records fade faster than they are copied. What was known is harder to hold."},
    {"id": "salt", "name": "Salt Winds", "key": "regen_mult", "kind": "mult", "base": 0.12,
     "remedy": "healthy_land", "what": "how fast the land recovers",
     "remedy_text": "keep the land healthy",
     "blurb": "A dry wind carries salt over the fields. The ground takes longer to forgive."},
    {"id": "cold", "name": "Cold Habitats", "key": "culture_bonus", "kind": "add", "base": 0.20,
     "remedy": "gathered_people", "what": "culture capacity",
     "remedy_text": "keep the fire circles able to hold everyone",
     "blurb": "The shared places feel colder. People keep to themselves and gatherings thin out."},
    {"id": "supply", "name": "Thin Supply Lines", "key": "relay_bonus", "kind": "add", "base": 0.25,
     "remedy": "served_holdings", "what": "relay throughput",
     "remedy_text": "keep the outlying holdings supplied",
     "blurb": "The roads between the holdings are longer than they were. Less gets through each season."},
]
THEME_BY_ID = {t["id"]: t for t in THEMES}


# --- validation -----------------------------------------------------------
def _int(value, low, high, default):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return default
    if isinstance(value, float) and not math.isfinite(value):
        return default
    return max(low, min(high, int(value)))


def fresh():
    return {"on": False, "era": 1, "season": 0, "good": 0, "best": 0, "runs": 0}


def clean(raw):
    """A validated record from whatever a save handed back (may be junk)."""
    out = fresh()
    if not isinstance(raw, dict):
        return out
    out["on"] = raw.get("on") is True
    out["era"] = _int(raw.get("era"), 1, MAX_ERA, 1)
    out["season"] = _int(raw.get("season"), 0, ERA_SEASONS, 0)
    out["good"] = _int(raw.get("good"), 0, ERA_SEASONS, 0)
    out["best"] = _int(raw.get("best"), 0, MAX_ERA, 0)
    out["runs"] = _int(raw.get("runs"), 0, 10**6, 0)
    if out["good"] > out["season"]:
        out["good"] = out["season"]
    return out


def get(ui):
    return clean(ui.get(KEY)) if isinstance(ui, dict) else fresh()


def put(ui, record):
    """Store the record; the untouched default is not stored at all."""
    record = clean(record)
    if record == fresh():
        ui.pop(KEY, None)
        return record
    ui[KEY] = record
    return record


# --- the numbers ----------------------------------------------------------
def available(furthest_era):
    """True once the Relay Age has been reached."""
    return isinstance(furthest_era, str) and furthest_era in sim.ERA_ORDER and (
        sim.era_index(furthest_era) >= sim.era_index(START_ERA)
    )


def theme_for(era_number):
    return THEMES[(max(1, era_number) - 1) % len(THEMES)]


def bar_for(era_number):
    return min(MAX_BAR, BASE_BAR + BAR_PER_ERA * (max(1, era_number) - 1))


def entropy(record):
    return round(ENTROPY_PER_ERA * (record["era"] - 1) + ENTROPY_PER_SEASON * record["season"], 4)


def remedy_cut(era_number):
    """The most of a pressure the remedy can remove in this era (it fades, so the run always ends)."""
    return round(max(REMEDY_FLOOR, REMEDY_CUT - REMEDY_FADE * (max(1, era_number) - 1)), 4)


def remedy_ratio(theme, state, effects=None):
    """0..1: how well the settlement answers the theme right now."""
    kind = theme["remedy"]
    people = max(1, state.population)
    if kind == "full_stores":
        return _clamp01(state.resources["food"] / max(1.0, state.food_storage_capacity(effects)))
    if kind == "tooled_people":
        return _clamp01(state.resources["tools"] / people)
    if kind == "studious":
        return _clamp01(state.allocation.get("keepers", 0) / (people * 0.2))
    if kind == "healthy_land":
        return _clamp01(state.land_health)
    if kind == "gathered_people":
        return _clamp01(state.culture_capacity(effects) / people)
    if kind == "served_holdings":
        if state.buildings.get("relay_stations", 0) <= 0:
            return 1.0
        return _clamp01(state.outlying_served)
    return 0.0


def _clamp01(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        return 0.0
    return max(0.0, min(1.0, float(value)))


def pressure(record, state, effects=None):
    """The strength of the current pressure, as the share it removes (0..MAX_REDUCTION)."""
    theme = theme_for(record["era"])
    raw = theme["base"] * (1.0 + entropy(record))
    softened = raw * (1.0 - remedy_cut(record["era"]) * remedy_ratio(theme, state, effects))
    return round(min(MAX_REDUCTION if theme["kind"] == "mult" else 0.8, max(0.0, softened)), 4)


def entropy_tax(record):
    """The general decay every Beyond era adds on top of its theme: a share of food gathered, rising
    each era to a ceiling. It is why every run ends eventually: nothing stays easy forever."""
    return round(min(ENTROPY_TAX_MAX, ENTROPY_TAX_PER_ERA * (record["era"] - 1)), 4)


def apply_effects(effects, ui, state, active):
    """The theme's pressure on the effects dict while a run is on. Returns `effects` unchanged otherwise."""
    record = get(ui)
    if not active or not record["on"]:
        return effects
    theme = theme_for(record["era"])
    cut = pressure(record, state, effects)
    tax = entropy_tax(record)
    if cut <= 0 and tax <= 0:
        return effects
    out = dict(effects)
    if tax > 0:
        out["food_yield_mult"] = max(0.1, out.get("food_yield_mult", 1.0) * (1.0 - tax))
    if cut <= 0:
        return out
    key = theme["key"]
    if theme["kind"] == "mult":
        out[key] = max(0.1, out.get(key, 1.0) * (1.0 - cut))
    else:
        out[key] = max(-0.5, out.get(key, 0.0) - cut)
    return out


# --- running a run --------------------------------------------------------
def start(ui, furthest_era, resting, revisiting):
    """Begin a run at Beyond era 1. Returns (ok, message)."""
    if revisiting:
        return False, "Return to the present before starting the Beyond."
    if resting:
        return False, "The Beyond is not offered during a challenge run or consulting case."
    if not available(furthest_era):
        return False, "The Beyond opens once the settlement reaches the Relay Age."
    record = get(ui)
    if record["on"]:
        return False, "A Beyond run is already under way."
    record.update(on=True, era=1, season=0, good=0, runs=record["runs"] + 1)
    put(ui, record)
    return True, "The Beyond begins. Era 1: " + theme_for(1)["name"] + "."


def after_season(ui, score):
    """Call once after each season with the sustainability score. Returns None or an event dict:
    {"kind": "survived", "era": n, "next_theme": name}, or {"kind": "ended", "survived": n}."""
    record = get(ui)
    if not record["on"] or not isinstance(score, (int, float)) or isinstance(score, bool):
        return None
    n = record["era"]
    record["season"] += 1
    if score >= bar_for(n):
        record["good"] += 1
    event = None
    if record["season"] >= ERA_SEASONS:
        if record["good"] >= PASS_SEASONS:
            record["best"] = max(record["best"], n)
            record.update(era=min(MAX_ERA, n + 1), season=0, good=0)
            event = {"kind": "survived", "era": n, "next_theme": theme_for(n + 1)["name"]}
        else:
            event = {"kind": "ended", "survived": n - 1}
            record.update(on=False, era=1, season=0, good=0)
    elif record["season"] - record["good"] > ERA_SEASONS - PASS_SEASONS:
        # More seasons have already missed the bar than the era can afford: the era cannot be saved.
        event = {"kind": "ended", "survived": n - 1}
        record.update(on=False, era=1, season=0, good=0)
    put(ui, record)
    return event


def stop(ui):
    """The player ends the run early. Returns the number of eras survived in it, or None if none was on."""
    record = get(ui)
    if not record["on"]:
        return None
    survived = record["era"] - 1
    record.update(on=False, era=1, season=0, good=0)
    put(ui, record)
    return survived


def status_lines(record, state, effects=None):
    """Plain-language lines for the panel."""
    if not record["on"]:
        return []
    theme = theme_for(record["era"])
    cut = pressure(record, state, effects)
    remedy = remedy_ratio(theme, state, effects)
    left = ERA_SEASONS - record["season"]
    return [
        f"Beyond era {record['era']}: {theme['name']}. {theme['blurb']}",
        f"Pressure: {theme['what']} is about {cut * 100:.0f}% lower than it would be. "
        f"Entropy is {entropy(record) * 100:.0f}%, so it rises every season and every era.",
        f"Remedy: {theme['remedy_text']} (you are at {remedy * 100:.0f}%; at best it takes "
        f"{remedy_cut(record['era']) * 100:.0f}% off the pressure, and that fades with each era).",
        (f"Entropy also takes {entropy_tax(record) * 100:.0f}% of all food gathered, whatever the theme."
         if entropy_tax(record) > 0 else "Entropy starts to take a share of all food gathered from era 2."),
        f"To survive this era, keep the sustainability score at {bar_for(record['era'])} or more in "
        f"{PASS_SEASONS} of its {ERA_SEASONS} seasons. So far {record['good']} good "
        f"{'season' if record['good'] == 1 else 'seasons'} out of {record['season']}; "
        f"{left} {'season' if left == 1 else 'seasons'} to go.",
    ]


# --- the ladder (kept per device, like the challenge ledger) ----------------
LADDER_KEY = "continuum-beyond-ladder-v1"
LADDER_MAX = 10
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def clean_ladder(raw):
    """Validated ladder rows, best first: {"date", "survived", "name"}."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return []
    if not isinstance(raw, list):
        return []
    rows = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        date = item.get("date")
        survived = item.get("survived")
        if isinstance(survived, bool) or not isinstance(survived, int) or not 1 <= survived <= MAX_ERA:
            continue
        if not isinstance(date, str) or not _DATE.match(date):
            continue
        name = item.get("name")
        name = name.strip()[:28] if isinstance(name, str) else ""
        rows.append({"date": date, "survived": survived, "name": name})
    rows.sort(key=lambda r: (-r["survived"], r["date"]))
    return rows[:LADDER_MAX]


def add_to_ladder(rows, date, survived, name=""):
    """Rows with this result added (a run that survived no era is not worth a row)."""
    rows = clean_ladder(rows)
    if _int(survived, 0, MAX_ERA, None) is None or survived < 1:
        return rows
    return clean_ladder(rows + [{"date": date, "survived": survived, "name": name}])


def ladder_text(row, index):
    who = f" ({row['name']})" if row["name"] else ""
    return f"{index}. {row['survived']} Beyond era{'s' if row['survived'] != 1 else ''} survived, {row['date']}{who}"
