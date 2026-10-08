"""Continuum -- K-2: the Dynasty, a meta-progression carried from settlement to settlement.

Every settlement you play can bank *Legacy points* when it ends (you found a new
settlement, you press "Bank this settlement's Legacy", or it collapses). The points buy
permanent perks from a skill tree (the shared `skill_tree` component), and the lifetime
total sets your Dynasty rank, which the cosmetic banners (banners.py, K-20) read.

Rules that keep it fair and honest:

* **Points are earned, never random.** `run_points()` is a pure function of how far the
  settlement got (eras reached, seasons lived, a well-run city), with Hard Mode paying
  half again as much. A failed settlement still banks what it reached, with a small floor
  ("the lessons") once it has lived 40 seasons. The numbers are deliberately tuned so an
  idle Tribal settlement banks almost nothing: points per run are dominated by eras
  reached.
* **Banking is by the difference.** Each settlement remembers what it already banked
  (`ui["dynasty_run"]["banked"]`), so pressing the button twice, or banking and then
  founding anew, never pays the same points twice.
* **Perks are starting stores and a few tiny standing bonuses, nothing that can break the
  game.** The starting perks (food, tools, materials, knowledge, one extra person) are
  delivered once, with the opening season, exactly like the founder's legacy. The standing
  bonuses are two or three percent.
* **They rest in comparable runs.** While a challenge run (the daily challenge, a
  scenario-editor code) or a consulting case is the active run, no Dynasty perk applies
  and nothing is delivered, so the par scores and the daily results stay comparable. The
  switch "Dynasty perks: on/off" turns them off everywhere else.
* **Respec is free.** Refunds are unlimited, as in Canopy's Seed Vault.

Pure functions of a plain dict (`campaign.ui`): no DOM, no storage. All reads are validated
(`clean()`), so a hand-edited save can never crash the game or mint points.
"""

import math

import skill_tree
import sim
import summary

KEY = "dynasty"
RUN_KEY = "dynasty_run"
MAX_EARNED = 100000
MAX_RUN_POINTS = 60
MIN_SEASONS_TO_BANK = 40

# --- the perk tree ---------------------------------------------------------------------------
DYNASTY_TREE = {
    "id": "dynasty",
    "title": "Dynasty perks",
    "currency": "Legacy points",
    "branches": [
        {"id": "heritage", "title": "Heritage", "blurb": "Every settlement starts with a little more."},
        {"id": "customs", "title": "House customs", "blurb": "Small standing habits, never more than a few percent."},
        {"id": "lands", "title": "Lands", "blurb": "New places to begin a settlement."},
        {"id": "counsel", "title": "Counsel", "blurb": "Doctrines and the hourglass."},
    ],
    "nodes": [
        {"id": "heirloom_granary", "branch": "heritage", "cost": 1, "label": "Heirloom Granary",
         "description": "Each new settlement starts with 4 more food.", "effect": "start_food"},
        {"id": "heirloom_toolkit", "branch": "heritage", "cost": 1, "label": "Heirloom Toolkit",
         "description": "Each new settlement starts with 1 more tool.", "effect": "start_tools"},
        {"id": "stacked_timber", "branch": "heritage", "cost": 2, "label": "Stacked Timber",
         "description": "Each new settlement starts with 6 more materials.", "effect": "start_materials"},
        {"id": "elders_tales", "branch": "heritage", "cost": 2, "label": "Elders' Tales",
         "description": "Each new settlement starts with 3 knowledge.", "effect": "start_knowledge"},
        {"id": "kin_arrive", "branch": "heritage", "cost": 3, "label": "Kin Arrive",
         "description": "Each new settlement starts with one more person.",
         "requires": ["heirloom_granary", "heirloom_toolkit"], "effect": "start_people"},
        {"id": "steady_hands", "branch": "customs", "cost": 2, "label": "Steady Hands",
         "description": "Food yield +2%.", "requires": ["heirloom_granary"], "effect": "standing_food"},
        {"id": "quiet_ledgers", "branch": "customs", "cost": 3, "label": "Quiet Ledgers",
         "description": "Knowledge output +3%.", "requires": ["elders_tales"], "effect": "standing_knowledge"},
        {"id": "deep_cellars", "branch": "customs", "cost": 2, "label": "Deep Cellars",
         "description": "Food storage +6.", "requires": ["heirloom_granary"], "effect": "standing_storage"},
        {"id": "hardy_charter", "branch": "lands", "cost": 2, "label": "Hardier Tribe",
         "description": "Unlocks the Hardier Tribe starting scenario.", "requires": ["heirloom_toolkit"],
         "effect": "unlock_hardy"},
        {"id": "river_charter", "branch": "lands", "cost": 3, "label": "River-valley Charter",
         "description": "Unlocks the River Valley starting scenario.", "requires": ["heirloom_granary"],
         "effect": "unlock_river"},
        {"id": "library_heirloom", "branch": "lands", "cost": 3, "label": "Library Heirloom",
         "description": "Unlocks the Library Heirloom starting scenario.", "requires": ["elders_tales"],
         "effect": "unlock_heirloom"},
        {"id": "schools_of_thought", "branch": "counsel", "cost": 3, "label": "Schools of Thought",
         "description": "Your era doctrines make research five points cheaper.", "effect": "doctrine_edge"},
        {"id": "hourglass_keepers", "branch": "counsel", "cost": 3, "label": "Keepers of the Hourglass",
         "description": "One extra rewind token.", "effect": "rewind_one"},
        {"id": "second_hourglass", "branch": "counsel", "cost": 4, "label": "A Second Hourglass",
         "description": "Another extra rewind token.", "requires": ["hourglass_keepers"], "effect": "rewind_two"},
    ],
}

# Effect ids -> what they do.
START_BONUS = {
    "start_food": ("food", 4.0),
    "start_tools": ("tools", 1.0),
    "start_materials": ("materials", 6.0),
    "start_knowledge": ("knowledge", 3.0),
}
START_PEOPLE_EFFECT = "start_people"
START_PEOPLE = 1
STANDING = {
    "standing_food": {"food_yield_mult": 0.02},
    "standing_knowledge": {"knowledge_mult": 0.03},
    "standing_storage": {"food_storage_bonus": 6.0},
}
# scenario id -> the effect id that unlocks it.
SCENARIO_UNLOCKS = {"hardy": "unlock_hardy", "river": "unlock_river", "heirloom": "unlock_heirloom"}
DOCTRINE_EDGE_EFFECT = "doctrine_edge"
DOCTRINE_EDGE_POINTS = 5  # percentage points of extra research discount
REWIND_PERK_TOKENS = {"rewind_one": 1, "rewind_two": 1}

# Dynasty ranks: (lifetime Legacy points needed, name). Rank only ever goes up.
RANKS = ((0, "Founder"), (5, "Steward"), (12, "Warden"), (22, "Elder"), (36, "Archon"), (55, "Dynast"))


def tree_problems():
    return skill_tree.validate(DYNASTY_TREE)


def _int(value, low=0, high=10**6):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return low
    if isinstance(value, float) and not math.isfinite(value):
        return low
    return min(max(int(value), low), high)


# --- saved record ----------------------------------------------------------------------------
def default():
    return {"earned": 0, "owned": [], "runs": 0, "failed": 0, "hard_runs": 0, "best_era": 0, "off": False}


def clean(raw):
    """A validated Dynasty record. Anything malformed falls back to the default."""
    out = default()
    if not isinstance(raw, dict):
        return out
    out["earned"] = _int(raw.get("earned"), 0, MAX_EARNED)
    owned = raw.get("owned")
    out["owned"] = skill_tree.sanitize_owned(DYNASTY_TREE, owned if isinstance(owned, list) else [], out["earned"], "trim")
    out["runs"] = _int(raw.get("runs"), 0, 10**5)
    out["failed"] = min(_int(raw.get("failed"), 0, 10**5), out["runs"])
    out["hard_runs"] = min(_int(raw.get("hard_runs"), 0, 10**5), out["runs"])
    out["best_era"] = _int(raw.get("best_era"), 0, len(sim.ERA_ORDER) - 1)
    out["off"] = raw.get("off") is True
    return out


def get(ui):
    return clean(ui.get(KEY)) if isinstance(ui, dict) else default()


def put(ui, record):
    """Stores `record` in `ui` only when it differs from the untouched default."""
    record = clean(record)
    if record == default():
        ui.pop(KEY, None)
    else:
        ui[KEY] = record
    return record


def clean_run(raw):
    out = {"banked": 0, "counted": False, "start": False, "failed": False}
    if not isinstance(raw, dict):
        return out
    out["banked"] = _int(raw.get("banked"), 0, MAX_RUN_POINTS * 2)
    out["counted"] = raw.get("counted") is True
    out["start"] = raw.get("start") is True
    out["failed"] = raw.get("failed") is True
    return out


def get_run(ui):
    return clean_run(ui.get(RUN_KEY)) if isinstance(ui, dict) else clean_run(None)


def put_run(ui, run):
    run = clean_run(run)
    if run == clean_run(None):
        ui.pop(RUN_KEY, None)
    else:
        ui[RUN_KEY] = run
    return run


# --- points, rank ----------------------------------------------------------------------------
def points_free(record):
    return skill_tree.points_left(DYNASTY_TREE, record["owned"], record["earned"])


def rank_index(earned):
    index = 0
    for i, (need, _name) in enumerate(RANKS):
        if earned >= need:
            index = i
    return index


def rank_name(earned):
    return RANKS[rank_index(earned)][1]


def next_rank(earned):
    """(points still needed, name) for the next rank, or None at the top."""
    index = rank_index(earned)
    if index + 1 >= len(RANKS):
        return None
    need, name = RANKS[index + 1]
    return need - earned, name


def run_points(era_index, seasons, peak_score, hard_mode, collapsed):
    """Legacy points one settlement is worth.

    Eras reached carry the weight (3 each beyond Tribal); seasons lived add a little, capped
    by how far the settlement got, so replaying the first era over and over pays almost
    nothing; a well-run city (peak score 70 or better, past the first era) adds one; Hard
    Mode pays half again; a collapsed settlement is worth at least 2 ("the lessons") once
    it has lived long enough to have taught anything.
    """
    era_index = _int(era_index, 0, len(sim.ERA_ORDER) - 1)
    seasons = _int(seasons, 0, 10**7)
    if seasons < MIN_SEASONS_TO_BANK:
        return 0
    base = 3 * era_index + min(seasons // 40, 2 * (era_index + 1))
    if era_index >= 1 and isinstance(peak_score, (int, float)) and not isinstance(peak_score, bool) \
            and math.isfinite(peak_score) and peak_score >= 70:
        base += 1
    if collapsed:
        base = max(base, 2)
    if hard_mode:
        base += int(math.ceil(base / 2.0))
    return min(base, MAX_RUN_POINTS)


def is_collapsed(state):
    """True for a settlement that has failed: its last three scores all fell below the
    collapse line, or it has been reduced to a last survivor after a long life."""
    history = [v for v in getattr(state, "score_history", []) if isinstance(v, (int, float))]
    if len(history) >= 3 and all(v < sim.SCORE_COLLAPSE_THRESHOLD for v in history[-3:]):
        return True
    return state.population <= sim.MIN_POPULATION and state.season >= MIN_SEASONS_TO_BANK


def run_info(campaign, inherited_era=None):
    """What a settlement is worth right now, as the plain dict `bank()` and the panel read.

    `inherited_era` (a consulting case's handed-over era) is not credited: those eras were
    given, not reached.
    """
    data = summary.summary(campaign)
    era_index = sim.era_index(data["furthest_era"])
    if inherited_era in sim.ERA_ORDER:
        era_index = max(0, era_index - sim.era_index(inherited_era))
    seasons = data["total_seasons"] if isinstance(data["total_seasons"], (int, float)) else 0
    collapsed = is_collapsed(campaign.state) if campaign.revisiting is None else False
    hard = bool(campaign.state.hard_mode)
    return {
        "era_index": era_index,
        "seasons": int(seasons),
        "peak_score": data["peak_score"],
        "hard_mode": hard,
        "collapsed": collapsed,
        "points": run_points(era_index, seasons, data["peak_score"], hard, collapsed),
    }


def bank(ui, info):
    """Banks a settlement's worth into `ui`, by the difference from what it already banked.

    Returns {"gained", "points", "banked", "total", "first"}. Nothing is banked for a
    settlement worth zero (too short a life) or when `info` is unusable.
    """
    if not isinstance(info, dict):
        return {"gained": 0, "points": 0, "banked": 0, "total": get(ui)["earned"], "first": False}
    points = _int(info.get("points"), 0, MAX_RUN_POINTS)
    run = get_run(ui)
    record = get(ui)
    gained = max(0, points - run["banked"])
    first = False
    if points > 0:
        record["earned"] = min(MAX_EARNED, record["earned"] + gained)
        record["best_era"] = max(record["best_era"], _int(info.get("era_index"), 0, len(sim.ERA_ORDER) - 1))
        if not run["counted"]:
            first = True
            record["runs"] += 1
            if info.get("hard_mode") is True:
                record["hard_runs"] += 1
            run["counted"] = True
        if info.get("collapsed") is True and not run["failed"]:
            run["failed"] = True
            record["failed"] += 1
        run["banked"] = max(run["banked"], points)
        put(ui, record)
        put_run(ui, run)
    return {"gained": gained, "points": points, "banked": run["banked"], "total": record["earned"], "first": first}


# --- perks: buying, refunding ----------------------------------------------------------------
def buy(ui, node_id):
    record = get(ui)
    result = skill_tree.buy(DYNASTY_TREE, record["owned"], node_id, record["earned"])
    if result["ok"]:
        record["owned"] = result["owned"]
        put(ui, record)
    return result


def refund(ui, node_id):
    record = get(ui)
    result = skill_tree.refund(DYNASTY_TREE, record["owned"], node_id)
    if result["ok"]:
        record["owned"] = result["owned"]
        put(ui, record)
    return result


def refund_all(ui):
    record = get(ui)
    result = skill_tree.refund_all(DYNASTY_TREE, record["owned"])
    record["owned"] = result["owned"]
    put(ui, record)
    return result


def set_off(ui, off):
    record = get(ui)
    record["off"] = bool(off)
    put(ui, record)
    return record["off"]


# --- what is active --------------------------------------------------------------------------
def owned_effects(ui):
    """Effect ids of every owned perk, ignoring the on/off switch and any rest."""
    return set(skill_tree.effects(DYNASTY_TREE, get(ui)["owned"]))


def active_effects(ui, resting=False):
    """Effect ids that actually apply right now: none while switched off or resting."""
    record = get(ui)
    if record["off"] or resting:
        return set()
    return set(skill_tree.effects(DYNASTY_TREE, record["owned"]))


def active_perk_ids(ui, resting=False):
    """Owned perk ids that apply right now (for the archive and the panel)."""
    record = get(ui)
    if record["off"] or resting:
        return []
    return list(record["owned"])


def start_bonuses(ui, resting=False):
    """{'food': 4.0, ..., 'people': 1} for the starting perks that apply right now."""
    effects = active_effects(ui, resting)
    bonuses = {}
    for effect, (resource, amount) in START_BONUS.items():
        if effect in effects:
            bonuses[resource] = bonuses.get(resource, 0.0) + amount
    if START_PEOPLE_EFFECT in effects:
        bonuses["people"] = START_PEOPLE
    return bonuses


def start_text(bonuses):
    """'+4 food, +1 tool, +1 person' for a start_bonuses() dict ('' for none)."""
    parts = []
    labels = {"food": "food", "materials": "materials", "knowledge": "knowledge"}
    for resource in ("food", "materials", "knowledge"):
        if resource in bonuses:
            parts.append(f"+{bonuses[resource]:g} {labels[resource]}")
    if "tools" in bonuses:
        count = bonuses["tools"]
        parts.append(f"+{count:g} {'tool' if count == 1 else 'tools'}")
    if "people" in bonuses:
        count = int(bonuses["people"])
        parts.append(f"+{count} {'person' if count == 1 else 'people'}")
    return ", ".join(parts)


def apply_start(campaign, resting=False):
    """Delivers the starting perks once, at the start of the opening season.

    Returns the bonuses delivered (a dict, possibly empty), or None when this settlement
    has already had its turn (or has already played a season). The turn is used up either
    way -- a resting run (a challenge run or consulting case) or a switched-off Dynasty
    gets nothing now AND nothing later.
    """
    ui = campaign.ui
    run = get_run(ui)
    if run["start"]:
        return None
    run["start"] = True
    put_run(ui, run)
    state = campaign.state
    if state.season > 1:
        return None
    bonuses = start_bonuses(ui, resting)
    for resource in ("food", "materials", "tools", "knowledge"):
        if resource in bonuses:
            state.resources[resource] = state.resources[resource] + bonuses[resource]
    if "people" in bonuses:
        state.population += int(bonuses["people"])
    return bonuses


def add_deltas(effects, deltas):
    """A copy of `effects` with research-style additive deltas summed on (unknown keys skipped)."""
    merged = dict(effects)
    for key, delta in deltas.items():
        if key in merged:
            merged[key] = merged[key] + delta
    return merged


def apply_effects(effects, ui, resting=False):
    """`effects` with the standing perks added (a copy), or `effects` itself with none."""
    active = active_effects(ui, resting)
    deltas = {}
    for effect, change in STANDING.items():
        if effect in active:
            for key, value in change.items():
                deltas[key] = deltas.get(key, 0.0) + value
    if not deltas:
        return effects
    return add_deltas(effects, deltas)


def doctrine_edge(ui, resting=False):
    """Extra percentage points of research discount for doctrines (0 or DOCTRINE_EDGE_POINTS)."""
    return DOCTRINE_EDGE_POINTS if DOCTRINE_EDGE_EFFECT in active_effects(ui, resting) else 0


def rewind_perk_tokens(ui):
    """Rewind tokens the owned perks grant (the on/off switch does not take tokens away)."""
    owned = owned_effects(ui)
    return sum(count for effect, count in REWIND_PERK_TOKENS.items() if effect in owned)


def scenario_unlocked(ui, scenario_id):
    """True when `scenario_id` is not a Dynasty scenario, or its perk is owned (the switch and
    any rest do not lock a scenario once it is unlocked)."""
    effect = SCENARIO_UNLOCKS.get(scenario_id)
    return effect is None or effect in owned_effects(ui)


def scenario_unlock_label(scenario_id):
    """'Hardier Tribe' perk name that unlocks a scenario ('' for others)."""
    effect = SCENARIO_UNLOCKS.get(scenario_id)
    for node in DYNASTY_TREE["nodes"]:
        if node.get("effect") == effect:
            return node["label"]
    return ""


# --- merging with the per-browser copy -------------------------------------------------------
def merge(saved, local):
    """Combines a save's Dynasty record with this browser's copy so neither loses progress.

    Lifetime figures take the larger value; the owned perks come from whichever record has
    earned more (ties: the save), trimmed to fit by `clean()`.
    """
    a, b = clean(saved), clean(local)
    primary = a if a["earned"] >= b["earned"] else b
    merged = {
        "earned": max(a["earned"], b["earned"]),
        "owned": list(primary["owned"]),
        "runs": max(a["runs"], b["runs"]),
        "failed": max(a["failed"], b["failed"]),
        "hard_runs": max(a["hard_runs"], b["hard_runs"]),
        "best_era": max(a["best_era"], b["best_era"]),
        "off": a["off"] if primary is a else b["off"],
    }
    return clean(merged)


def status_lines(ui, resting=False, rest_reason=""):
    """Plain-language summary lines for the panel (and the tests)."""
    record = get(ui)
    lines = []
    next_up = next_rank(record["earned"])
    rank_line = f"Dynasty rank: {rank_name(record['earned'])} ({record['earned']} Legacy points earned in all)."
    if next_up is not None:
        rank_line += f" {next_up[0]} more for {next_up[1]}."
    lines.append(rank_line)
    lines.append(
        f"{points_free(record)} Legacy points to spend. {record['runs']} settlements banked "
        f"({record['failed']} collapsed, {record['hard_runs']} on Hard Mode)."
    )
    if record["off"]:
        lines.append("Dynasty perks are switched off: no starting stores or standing bonuses apply.")
    elif resting:
        lines.append(f"Dynasty perks are resting: {rest_reason}")
    return lines
