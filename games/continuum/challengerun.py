"""Continuum -- K-10 daily challenge and K-11 scenario editor with share codes.

Both are the same thing: a **challenge run**. A run is a starting position (the
numbers the settlement opens with), an optional day-modifier (a boon with a
price), Hard Mode on or off, and a length in seasons. The player settles in,
plays the set number of seasons, and is scored. The score is compared with a
**par** that the game works out for the same setup by running a plain autopilot
on it, so the par moves honestly with any rebalance and is never a number
somebody picked.

* K-10, the daily challenge: one run per UTC day, derived from the date only
  (no server) through `shared/seed.py`'s daily seed, so everybody gets the same
  starting scenario, the same modifier and the same Hard Mode flag that day.
* K-11, the scenario editor: the player picks the numbers (starting people,
  food, materials, tools, land health, run length, Hard Mode, a modifier) and
  gets a short **mod code** (`CNT-XXXX-XXXXX`) another player can type in to play
  the same setup and try to beat the par.

What is NOT in the editor, and why. Continuum's simulation has no random events
(see `sim.py`) and eras are entered by the player, not on a timer, so "event
frequency" and "era length" do not exist as dials. The closest honest dial is
the run's length in seasons, which the editor offers.

Where it plugs in. The run record lives in `campaign.ui["challenge_run"]` (plain
JSON, validated on every read by `clean()`, so no save-schema change). The
modifier reaches the season loop through the one research seam, the effects dict
(`apply_effects`). A run can only be started on a fresh, untouched settlement
(the same rule as a consulting case), and only one run is tracked at a time.

Score. `10 x average sustainability score over the run + 5 x people at the end
+ 20 x discoveries researched + 150 x eras entered`. It rewards a settlement that
is both well run (the score term) and grown (people, research, eras), so neither
raw growth nor careful stagnation wins on its own.

Pure functions only: no DOM, no storage, no clock. `game.py` supplies the date.
"""

import math

import consulting
import founding
import research
import sim
import sustainability

KEY = "challenge_run"
CODE_PREFIX = "CNT"
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 32 symbols, no I O 0 1
GAME_ID = "continuum"
DAILY_GOAL = 40
DAILY_HARD_CHANCE = 0.25
DAILY_BASES = ("standard", "frontier", "fertile")

# (low, high, step) for each editor dial. The share code stores the position
# on this grid, so a value always round-trips exactly.
RANGES = {
    "population": (4, 15, 1),
    "food": (5, 60, 1),
    "materials": (5, 60, 1),
    "tools": (0, 6, 1),
    "land": (30, 100, 5),   # percent
    "goal": (20, 80, 5),    # seasons
}
LABELS = {
    "population": "Starting people",
    "food": "Starting food",
    "materials": "Starting materials",
    "tools": "Starting tools",
    "land": "Starting land health (%)",
    "goal": "Run length (seasons)",
}

# id -> label, one-line blurb, effects. A modifier is a trade: a boon with a
# price, or a burden with a small offset, never a pure gift or a pure curse.
# Multiplier keys (base 1.0 in `sim.NEUTRAL_EFFECTS`) are multiplied in;
# additive keys (base 0.0) are added.
MODIFIERS = {
    "bumper_harvest": {
        "label": "Bumper Harvest",
        "blurb": "Food yields +20%, but the storage pits are small (-10 storage).",
        "effects": {"food_yield_mult": 1.2, "food_storage_bonus": -10.0},
    },
    "thin_soil": {
        "label": "Thin Soil",
        "blurb": "The land recovers 25% slower, but the crops that do grow are +10%.",
        "effects": {"regen_mult": 0.75, "food_yield_mult": 1.1},
    },
    "sharp_minds": {
        "label": "Sharp Minds",
        "blurb": "Knowledge comes 40% faster; food yields are 10% lower.",
        "effects": {"knowledge_mult": 1.4, "food_yield_mult": 0.9},
    },
    "busy_hands": {
        "label": "Busy Hands",
        "blurb": "Tools are made 40% faster; knowledge comes 20% slower.",
        "effects": {"tool_yield_mult": 1.4, "knowledge_mult": 0.8},
    },
    "hardy_folk": {
        "label": "Hardy Folk",
        "blurb": "Room for 4 more people, but materials gathered are 10% lower.",
        "effects": {"housing_bonus": 4.0, "materials_yield_mult": 0.9},
    },
    "strong_hearths": {
        "label": "Strong Hearths",
        "blurb": "Each fire circle serves 50% more people; tools are made 10% slower.",
        "effects": {"culture_bonus": 0.5, "tool_yield_mult": 0.9},
    },
    "fair_shares": {
        "label": "Fair Shares",
        "blurb": "Everyone gets a fairer cut (equity +6 points), at 5% less food.",
        "effects": {"equity_bonus": 0.06, "food_yield_mult": 0.95},
    },
    "lean_year": {
        "label": "Lean Year",
        "blurb": "Food yields are 15% lower, but the land is spared 15% of the pressure.",
        "effects": {"food_yield_mult": 0.85, "extraction_efficiency": 0.85},
    },
    "stone_country": {
        "label": "Stone Country",
        "blurb": "Materials gathered +30%; food yields 10% lower.",
        "effects": {"materials_yield_mult": 1.3, "food_yield_mult": 0.9},
    },
}
MODIFIER_IDS = [""] + list(MODIFIERS)  # index 0 = none; position is stored in the share code


def modifier_label(modifier_id):
    return MODIFIERS[modifier_id]["label"] if modifier_id in MODIFIERS else "None"


# --- configs ----------------------------------------------------------------
def snap(name, value):
    """`value` forced onto dial `name`'s grid and range (an int)."""
    low, high, step = RANGES[name]
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = low
    if not math.isfinite(number):
        number = low
    number = max(low, min(high, number))
    return int(low + round((number - low) / step) * step)


def clean_config(raw):
    """A validated config dict (always complete), from whatever was handed in."""
    raw = raw if isinstance(raw, dict) else {}
    cfg = {name: snap(name, raw.get(name, default)) for name, default in DEFAULTS.items()}
    modifier = raw.get("modifier")
    cfg["modifier"] = modifier if isinstance(modifier, str) and modifier in MODIFIERS else ""
    cfg["hard"] = raw.get("hard") is True
    return cfg


DEFAULTS = {"population": 6, "food": 20, "materials": 20, "tools": 2, "land": 100, "goal": 40}


def default_config():
    return clean_config({})


def config_from_scenario(scenario_id):
    """The dial values of one of the named starting scenarios."""
    base = sim.scenario_config(scenario_id)
    return clean_config({
        "population": base["population"], "food": base["food"], "materials": base["materials"],
        "tools": base["tools"], "land": round(base["land_health"] * 100), "goal": DAILY_GOAL,
    })


# --- the share code -----------------------------------------------------------
_BITS = (("population", 4), ("food", 6), ("materials", 6), ("tools", 3), ("land", 4), ("goal", 4))
_HARD_BIT = 1
_MOD_BITS = 4
_CHECK_BITS = 10
_CODE_CHARS = 9


def _position(name, value):
    low, _high, step = RANGES[name]
    return int(round((value - low) / step))


def _checksum(data):
    return (data * 31 + 7) % 1021


def encode(config):
    """The mod code for `config`, like `CNT-AB2D-EFGH7`."""
    cfg = clean_config(config)
    data = 0
    for name, bits in _BITS:
        data = (data << bits) | _position(name, cfg[name])
    data = (data << _HARD_BIT) | (1 if cfg["hard"] else 0)
    data = (data << _MOD_BITS) | MODIFIER_IDS.index(cfg["modifier"])
    value = (data << _CHECK_BITS) | _checksum(data)
    chars = []
    for _ in range(_CODE_CHARS):
        chars.append(ALPHABET[value & 31])
        value >>= 5
    body = "".join(reversed(chars))
    return f"{CODE_PREFIX}-{body[:4]}-{body[4:]}"


def decode(text):
    """(config, error). `error` is "" on success, else a message to show."""
    if not isinstance(text, str):
        return None, "Type or paste a mod code."
    if not text.strip():
        return None, "Type or paste a mod code."
    raw = "".join(ch for ch in text.upper() if ch.isalnum())
    if raw.startswith(CODE_PREFIX):
        raw = raw[len(CODE_PREFIX):]
    if len(raw) != _CODE_CHARS or any(ch not in ALPHABET for ch in raw):
        return None, "That is not a mod code: it should look like CNT-ABCD-EFGH7."
    value = 0
    for ch in raw:
        value = (value << 5) | ALPHABET.index(ch)
    check = value & ((1 << _CHECK_BITS) - 1)
    data = value >> _CHECK_BITS
    if check != _checksum(data):
        return None, "That code does not check out: one character is probably mistyped."
    idx = data & ((1 << _MOD_BITS) - 1)
    data >>= _MOD_BITS
    hard = bool(data & 1)
    data >>= _HARD_BIT
    if idx >= len(MODIFIER_IDS):
        return None, "That code comes from a newer version of the game."
    cfg = {"hard": hard, "modifier": MODIFIER_IDS[idx]}
    for name, bits in reversed(_BITS):
        pos = data & ((1 << bits) - 1)
        data >>= bits
        low, high, step = RANGES[name]
        value_ = low + pos * step
        if value_ > high:
            return None, "That code is outside the allowed ranges."
        cfg[name] = value_
    if data:
        return None, "That is not a mod code: it should look like CNT-ABCD-EFGH7."
    return clean_config(cfg), ""


def summary_lines(config):
    """Plain sentences describing a config (for the editor's preview)."""
    cfg = clean_config(config)
    out = [
        f"{cfg['population']} people, {cfg['food']} food, {cfg['materials']} materials, "
        f"{cfg['tools']} tools, land at {cfg['land']}%.",
        f"Run length: {cfg['goal']} seasons. Hard Mode: {'on' if cfg['hard'] else 'off'}.",
    ]
    if cfg["modifier"]:
        mod = MODIFIERS[cfg["modifier"]]
        out.append(f"Modifier: {mod['label']}. {mod['blurb']}")
    else:
        out.append("No modifier.")
    return out


# --- the daily ------------------------------------------------------------------
def daily(date_text):
    """The day's challenge: {"seed", "date", "scenario", "config"}.

    Derived from `shared/seed.py`'s daily seed for this game, so it is the same
    for everybody on a UTC date and needs no server. Returns None for a date the
    seed module refuses.
    """
    import seed as noyvj_seed

    try:
        seed_text = noyvj_seed.daily_seed(GAME_ID, date_text)
    except (ValueError, TypeError):
        return None
    rng = noyvj_seed.Rng(seed_text)
    scenario = rng.choice(list(DAILY_BASES))
    modifier = rng.choice(list(MODIFIERS))
    hard = rng.chance(DAILY_HARD_CHANCE)
    cfg = config_from_scenario(scenario)
    cfg["modifier"] = modifier
    cfg["hard"] = hard
    return {"seed": seed_text, "date": str(date_text), "scenario": scenario, "config": clean_config(cfg)}


# --- effects --------------------------------------------------------------------
def apply_effects(effects, ui):
    """`effects` with the active run's modifier applied (a copy), or unchanged."""
    run = get(ui)
    if run is None or not run["config"]["modifier"]:
        return effects
    merged = dict(effects)
    for key, value in MODIFIERS[run["config"]["modifier"]]["effects"].items():
        if key not in sim.NEUTRAL_EFFECTS:
            continue
        if sim.NEUTRAL_EFFECTS[key] == 1.0:
            merged[key] = merged.get(key, 1.0) * value
        else:
            merged[key] = merged.get(key, 0.0) + value
    return merged


# --- the record -------------------------------------------------------------------
def _count(value, high=10**6):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return min(value, high)


def _float(value, high=1e9):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return 0.0
    return max(0.0, min(float(value), high))


def clean_result(raw):
    if not isinstance(raw, dict):
        return None
    points = raw.get("points")
    if isinstance(points, bool) or not isinstance(points, int) or points < 0:
        return None
    return {
        "points": min(points, 10**9),
        "avg_score": round(_float(raw.get("avg_score"), 100.0), 1),
        "population": _count(raw.get("population")),
        "discoveries": _count(raw.get("discoveries")),
        "eras": _count(raw.get("eras"), 20),
        "seasons": _count(raw.get("seasons")),
    }


def clean(raw):
    """A validated run record, or None for anything unusable."""
    if not isinstance(raw, dict):
        return None
    kind = raw.get("kind")
    if kind not in ("daily", "custom"):
        return None
    seed_text = raw.get("seed")
    date_text = raw.get("date")
    cfg = clean_config(raw.get("config"))
    out = {
        "kind": kind,
        "seed": seed_text[:40] if isinstance(seed_text, str) else "",
        "date": date_text[:10] if isinstance(date_text, str) else "",
        "config": cfg,
        "code": encode(cfg),
        "seasons": min(_count(raw.get("seasons")), cfg["goal"] + 10**4),
        "score_total": _float(raw.get("score_total")),
        "result": clean_result(raw.get("result")),
        "par": None,
    }
    par_points = raw.get("par")
    if not isinstance(par_points, bool) and isinstance(par_points, int) and par_points >= 0:
        out["par"] = min(par_points, 10**9)
    return out


def get(ui):
    return clean(ui.get(KEY)) if isinstance(ui, dict) else None


def active(ui):
    """The run that is still being played (no result yet), or None."""
    run = get(ui)
    return run if run is not None and run["result"] is None else None


def points_for(avg_score, population, discoveries, eras):
    return int(round(10 * avg_score + 5 * population + 20 * discoveries + 150 * eras))


def progress_text(run):
    if run is None:
        return ""
    goal = run["config"]["goal"]
    if run["result"] is not None:
        return f"Finished: {run['result']['points']} points over {run['result']['seasons']} seasons."
    return f"Season {min(run['seasons'], goal)} of {goal}."


# --- starting and finishing -----------------------------------------------------------
def can_start(campaign):
    """True on a fresh, untouched settlement with no consulting case and no run yet."""
    return (
        consulting.get(campaign.ui) is None
        and get(campaign.ui) is None
        and founding.is_pristine(campaign)
        and campaign.state.season <= 1
    )


def start(campaign, chronicle, kind, config, seed_text="", date_text=""):
    """Sets the settlement up for a run and records it. False if refused."""
    if kind not in ("daily", "custom") or not can_start(campaign):
        return False
    cfg = clean_config(config)
    state = campaign.state
    state.scenario = "standard"
    state.hard_mode = cfg["hard"]
    state.population = cfg["population"]
    state.resources["food"] = float(cfg["food"])
    state.resources["materials"] = float(cfg["materials"])
    state.resources["tools"] = float(cfg["tools"])
    state.resources["knowledge"] = 0.0
    state.land_health = cfg["land"] / 100.0
    state.clamp_allocation()
    campaign.ui[KEY] = {
        "kind": kind, "seed": seed_text, "date": date_text, "config": cfg,
        "seasons": 0, "score_total": 0.0, "result": None, "par": None,
    }
    campaign.ui[KEY] = clean(campaign.ui[KEY])
    if chronicle is not None:
        chronicle.bootstrap(state, campaign.tree, apply_effects(campaign.tree.effects(), campaign.ui))
    return True


def abandon(campaign):
    """Drops the run record; the settlement itself carries on unchanged."""
    if get(campaign.ui) is None:
        return False
    campaign.ui.pop(KEY, None)
    return True


def after_season(campaign, score):
    """Counts one finished season. Returns the result dict on the season the
    run ends, else None. Does nothing for a finished or absent run."""
    run = active(campaign.ui)
    if run is None:
        return None
    run["seasons"] += 1
    run["score_total"] += _float(score, 100.0)
    if run["seasons"] >= run["config"]["goal"]:
        run["result"] = finish(run, campaign)
    campaign.ui[KEY] = run
    return run["result"]


def finish(run, campaign):
    state = campaign.state
    seasons = max(1, run["seasons"])
    avg = run["score_total"] / seasons
    eras = sim.era_index(state.era)
    discoveries = len(campaign.tree.researched)
    return clean_result({
        "points": points_for(avg, state.population, discoveries, eras),
        "avg_score": avg, "population": state.population, "discoveries": discoveries,
        "eras": eras, "seasons": run["seasons"],
    })


# --- par: what a plain autopilot scores on the same setup --------------------------------
def _setup_state(cfg):
    state = sim.CityState()
    state.hard_mode = cfg["hard"]
    state.population = cfg["population"]
    state.resources["food"] = float(cfg["food"])
    state.resources["materials"] = float(cfg["materials"])
    state.resources["tools"] = float(cfg["tools"])
    state.land_health = cfg["land"] / 100.0
    state.clamp_allocation()
    return state


def _food_estimate(state, effects):
    return (
        state.allocation["foragers"] * sim.FOOD_PER_FORAGER * state.tool_factor()
        * state.land_health * effects["food_yield_mult"]
    )


def _plan_work(state, effects):
    """Puts every idle person to work: food first, then a quarter of the people
    studying, a couple gathering, one crafting. A forager is moved on when food
    is comfortably in surplus."""
    need = state.population * sim.FOOD_PER_PERSON
    if _food_estimate(state, effects) > need * 1.5 and state.allocation["foragers"] > 2:
        state.unassign_worker("foragers")
    guard = 0
    while state.idle_workers() > 0 and guard < 200:
        guard += 1
        alloc = state.allocation
        if _food_estimate(state, effects) < need * 1.05:
            role = "foragers"
        elif alloc["keepers"] < max(1, state.population // 4):
            role = "keepers"
        elif alloc["gatherers"] < 2:
            role = "gatherers"
        elif alloc["crafters"] < 1:
            role = "crafters"
        else:
            role = "keepers"
        if not state.assign_worker(role):
            break


def _plan_build(state, effects):
    housing = state.housing_capacity(effects)
    if state.population >= housing - 1 and state.can_build("shelter"):
        state.build("shelter")
    elif state.culture_capacity(effects) < state.population and state.can_build("hearth"):
        state.build("hearth")
    elif state.resources["food"] >= state.food_storage_capacity(effects) - 2 and state.can_build("granary"):
        state.build("granary")


def _plan_research(tree, state):
    for _ in range(4):
        options = [n for n in tree.available_nodes() if tree.can_afford(n.node_id, state.resources)]
        if not options:
            return
        options.sort(key=lambda n: (n.cost, n.node_id))
        tree.research(options[0].node_id, state.resources)


def autopilot(config):
    """The par: runs a plain autopilot for the config's number of seasons and
    returns the points it scores. The autopilot feeds everyone first, keeps a
    few Keepers studying, builds a shelter when growth is blocked, and never
    leaves the first era. It is the baseline to beat, not a ceiling."""
    cfg = clean_config(config)
    state = _setup_state(cfg)
    tree = research.build_tree()
    ui = {KEY: {"kind": "custom", "config": cfg}}
    total = 0.0
    for _ in range(cfg["goal"]):
        effects = apply_effects(tree.effects(), ui)
        _plan_research(tree, state)
        effects = apply_effects(tree.effects(), ui)
        _plan_work(state, effects)
        _plan_build(state, effects)
        state.advance_season(effects)
        total += sustainability.score(state, effects)
    avg = total / cfg["goal"]
    return points_for(avg, state.population, len(tree.researched), sim.era_index(state.era))


_PAR_CACHE = {}


def par_for(config):
    """`autopilot()` with a small memo (the same setup always gives the same par)."""
    cfg = clean_config(config)
    code = encode(cfg)
    if code not in _PAR_CACHE:
        _PAR_CACHE[code] = autopilot(cfg)
    return _PAR_CACHE[code]


def verdict(points, par_points):
    """A plain sentence comparing a score with the par."""
    if par_points is None or par_points <= 0:
        return ""
    diff = points - par_points
    if diff > 0:
        return f"{diff} points above par ({par_points})."
    if diff < 0:
        return f"{-diff} points below par ({par_points})."
    return f"Exactly on par ({par_points})."


# --- the ledger of finished runs (kept per device, like the settlement archive) ----------------
LEDGER_KEY = "continuum-challenge-ledger-v1"
LEDGER_MAX = 12


def clean_ledger(raw):
    """Validated ledger entries (newest last) from a JSON string or a list."""
    import json

    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            return []
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw[-LEDGER_MAX:]:
        if not isinstance(item, dict) or item.get("kind") not in ("daily", "custom"):
            continue
        points, par_points = item.get("points"), item.get("par")
        if isinstance(points, bool) or not isinstance(points, int) or points < 0:
            continue
        date_text, code = item.get("date"), item.get("code")
        out.append({
            "kind": item["kind"],
            "date": date_text[:10] if isinstance(date_text, str) else "",
            "code": code[:16] if isinstance(code, str) else "",
            "points": min(points, 10**9),
            "par": min(par_points, 10**9) if isinstance(par_points, int) and not isinstance(par_points, bool) and par_points >= 0 else None,
        })
    return out


def ledger_entry(run):
    """The ledger line for a finished run record (None if it is not finished)."""
    run = clean(run)
    if run is None or run["result"] is None:
        return None
    return {"kind": run["kind"], "date": run["date"], "code": run["code"],
            "points": run["result"]["points"], "par": run["par"]}


def ledger_add(entries, run):
    entry = ledger_entry(run)
    entries = clean_ledger(entries)
    if entry is None:
        return entries
    entries.append(entry)
    return entries[-LEDGER_MAX:]


def serialize_ledger(entries):
    import json

    return json.dumps(clean_ledger(entries))


def ledger_line(entry):
    kind = "Daily" if entry["kind"] == "daily" else "Custom"
    when = f" {entry['date']}" if entry["date"] else ""
    text = f"{kind}{when} ({entry['code']}): {entry['points']} points"
    if entry["par"] is not None:
        text += f", par {entry['par']}"
    return text


def share_fields(run):
    """Fields for the shared Copy result button (`NoyvjCopyResult.format`)."""
    run = clean(run)
    if run is None or run["result"] is None:
        return None
    kind = f"daily {run['date']}" if run["kind"] == "daily" and run["date"] else f"mod {run['code']}"
    stats = [{"n": run["result"]["seasons"], "one": "season", "many": "seasons"}]
    if run["par"] is not None:
        stats.append(f"par {run['par']}")
    return {"game": f"Continuum {kind}", "score": run["result"]["points"], "unit": "pts", "stats": stats}
