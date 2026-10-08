"""Continuum -- K-8: the advisor council.

Four invented advisors, one for each thing a settlement cannot do without,
each give one piece of advice at the start of every season. They disagree,
because each cares about their own corner:

* Marit Oakhand, the head farmer: food.
* Teodor Vance, the master builder: room for people and the buildings that make it.
* Inès Calder, the quartermaster: materials and the tools made from them.
* Okoro Lindqvist, the keeper of records: knowledge.

They are fictional characters; no real person is meant. What they say is not
fiction though: every piece of advice is a real action the game can carry out
(put a person to work, raise a shelter), and the game checks it by running the
coming season twice on a throwaway copy, once with the advice taken and once
without (`_simulate`, the same deterministic engine the real season uses, as
`forecast.py` does). So an advisor's claim ("food would be 6.5 higher next
season") is a measured fact, and so is its price (what it does to the
sustainability score). That is how each advisor's **record** is scored against
real outcomes:

* **sound**: it raises their own measure and does not cost the settlement's
  sustainability score more than `SCORE_TOLERANCE` points;
* **narrow**: it raises their measure but costs the whole more than that;
* **empty**: it would not have raised their measure at all.

Trust (0 to 10, starts at 5) moves by one each season an advisor's advice is
judged sound (up) or narrow or empty (down). It does not matter whether the
player took the advice: trust is about whether the advisor deserved it, and a
player who ignores a sound recommendation finds that out. The player's own
record is kept too (taken or ignored, and how each turned out).

For advice that was taken, the season's real result is shown next to the
prediction ("food 20 -> 27, predicted +6.5"), which is the part that can
differ, because the player does other things in the same season.

Optional, and hidden by the story toggle in the page. Nothing is gated behind
it: it only suggests, and it never acts unless a button is pressed.

State rides in `campaign.ui["advisors"]` (plain JSON, validated by `clean()` on
every read, no save-schema change). Pure functions only: no DOM; `game.py`
performs the actions through the same handlers the Work and Build panels use.
"""

import copy
import math

import sim
import sustainability

KEY = "advisors"
TRUST_START, TRUST_MIN, TRUST_MAX = 5, 0, 10
SCORE_TOLERANCE = 1.5     # points of sustainability an advisor may cost the whole
GAIN_MIN = 0.05           # a gain smaller than this counts as none
HISTORY_MAX = 6

ADVISORS = {
    "marit": {
        "name": "Marit Oakhand", "title": "Head farmer", "metric": "food", "unit": "food",
        "voice": "The pots must be full before anything else matters.",
    },
    "teodor": {
        "name": "Teodor Vance", "title": "Master builder", "metric": "headroom", "unit": "places to live",
        "voice": "A people with nowhere to sleep stops growing.",
    },
    "ines": {
        "name": "Inès Calder", "title": "Quartermaster", "metric": "materials", "unit": "materials",
        "voice": "Stores in the shed are worth more than promises.",
    },
    "okoro": {
        "name": "Okoro Lindqvist", "title": "Keeper of records", "metric": "knowledge", "unit": "knowledge",
        "voice": "What we write down, our grandchildren will not have to rediscover.",
    },
}
ORDER = tuple(ADVISORS)

FOOD_ROLES = ("farmers", "foragers")
MATERIAL_ROLES = ("factory_workers", "gatherers")
HEADROOM_COMFORT = 3      # the builder is quiet while there is more room than this


# --- state ------------------------------------------------------------------------
def _fresh_record():
    return {"followed": 0, "ignored": 0, "sound": 0, "narrow": 0, "empty": 0}


def fresh():
    return {
        "season": 0,
        "advice": [],
        "trust": {a: TRUST_START for a in ORDER},
        "record": {a: _fresh_record() for a in ORDER},
        "history": [],
    }


def _int(value, low, high, default):
    if isinstance(value, bool) or not isinstance(value, int):
        return default
    return max(low, min(high, value))


def _num(value, default=0.0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return default
    return float(value)


def _clean_action(raw):
    if not isinstance(raw, dict):
        return None
    kind = raw.get("type")
    if kind == "assign" and raw.get("role") in sim.ROLES:
        return {"type": "assign", "role": raw["role"]}
    if kind == "move" and raw.get("role") in sim.ROLES and raw.get("from") in sim.ROLES and raw["role"] != raw["from"]:
        return {"type": "move", "role": raw["role"], "from": raw["from"]}
    if kind == "build" and raw.get("building") in sim.BUILDINGS:
        return {"type": "build", "building": raw["building"]}
    return None


def _clean_advice(raw):
    if not isinstance(raw, dict) or raw.get("id") not in ADVISORS:
        return None
    action = _clean_action(raw.get("action"))
    text = raw.get("text")
    if action is None or not isinstance(text, str):
        return None
    quality = raw.get("quality")
    status = raw.get("status")
    return {
        "id": raw["id"],
        "action": action,
        "text": text[:240],
        "metric": ADVISORS[raw["id"]]["metric"],
        "net_gain": _num(raw.get("net_gain", raw.get("gain"))),
        "net_baseline": _num(raw.get("net_baseline", raw.get("baseline"))),
        "net_before": _num(raw.get("net_before", raw.get("before"))),
        "score_delta": _num(raw.get("score_delta", raw.get("score_effect"))),
        "quality": quality if quality in ("sound", "narrow", "empty") else "empty",
        "status": status if status in ("open", "followed") else "open",
        "rival": raw.get("rival") if raw.get("rival") in ADVISORS else "",
    }


def clean(raw):
    """A validated council record (always complete), whatever was handed in."""
    out = fresh()
    if not isinstance(raw, dict):
        return out
    out["season"] = _int(raw.get("season"), 0, 10**7, 0)
    seen = set()
    advice = raw.get("advice")
    for item in advice[:8] if isinstance(advice, list) else []:
        cleaned = _clean_advice(item)
        if cleaned is not None and cleaned["id"] not in seen:
            seen.add(cleaned["id"])
            out["advice"].append(cleaned)
    trust, record = raw.get("trust"), raw.get("record")
    for a in ORDER:
        if isinstance(trust, dict):
            out["trust"][a] = _int(trust.get(a), TRUST_MIN, TRUST_MAX, TRUST_START)
        if isinstance(record, dict) and isinstance(record.get(a), dict):
            for k in _fresh_record():
                out["record"][a][k] = _int(record[a].get(k), 0, 10**6, 0)
    history = raw.get("history")
    for item in history[-HISTORY_MAX:] if isinstance(history, list) else []:
        if isinstance(item, dict) and item.get("id") in ADVISORS and isinstance(item.get("text"), str):
            out["history"].append({"id": item["id"], "text": item["text"][:240],
                                   "season": _int(item.get("season"), 0, 10**7, 0)})
    return out


def get(ui):
    return clean(ui.get(KEY)) if isinstance(ui, dict) else fresh()


def put(ui, record):
    ui[KEY] = clean(record)
    return ui[KEY]


# --- measuring ------------------------------------------------------------------------
def metric_value(state, key, effects):
    if key == "food":
        return float(state.resources["food"])
    if key == "materials":
        return float(state.resources["materials"])
    if key == "knowledge":
        return float(state.resources["knowledge"])
    if key == "headroom":
        return float(state.housing_capacity(effects) - state.population)
    return 0.0


def _apply(state, action):
    if action["type"] == "assign":
        return state.assign_worker(action["role"])
    if action["type"] == "move":
        if not state.unassign_worker(action["from"]):
            return False
        if state.assign_worker(action["role"]):
            return True
        state.assign_worker(action["from"])
        return False
    return state.build(action["building"])


def _simulate(state, effects, action, key):
    """Runs one season on a copy: (metric after the season, score after). `action`
    may be None for the do-nothing baseline."""
    probe = copy.deepcopy(state)
    if action is not None and not _apply(probe, action):
        return None
    probe.advance_season(effects)
    return metric_value(probe, key, effects), sustainability.score(probe, effects)


def available(state, action):
    """True if the action can be carried out right now."""
    return _apply(copy.deepcopy(state), action)


# --- what each advisor would suggest --------------------------------------------------------
def _best_role(state, candidates):
    roles = sim.roles_for_era(state.era)
    for role in candidates:
        if role in roles:
            return role
    return None


def _assign_or_move(state, role):
    """Put someone on `role`: an idle person if there is one, else move one over
    from the role with the most people (not `role` itself)."""
    if state.idle_workers() > 0:
        return {"type": "assign", "role": role}
    donors = sorted((n, r) for r, n in state.allocation.items() if r != role and n > 0 and r in sim.roles_for_era(state.era))
    if not donors:
        return None
    return {"type": "move", "role": role, "from": donors[-1][1]}


def candidate_action(advisor_id, state, effects):
    """(action, text) for this advisor, or None when they have nothing to say."""
    if advisor_id == "marit":
        role = _best_role(state, FOOD_ROLES)
        action = _assign_or_move(state, role) if role else None
        if action is None:
            return None
        return action, f"Put {'one more person' if action['type'] == 'assign' else 'a person from ' + sim.ROLE_LABEL[action['from']]} on {sim.ROLE_LABEL[role]} to bring in more food."
    if advisor_id == "okoro":
        action = _assign_or_move(state, "keepers")
        if action is None:
            return None
        who = "one more person" if action["type"] == "assign" else "a person from " + sim.ROLE_LABEL[action["from"]]
        return action, f"Put {who} on {sim.ROLE_LABEL['keepers']} so discoveries come sooner."
    if advisor_id == "ines":
        role = _best_role(state, MATERIAL_ROLES)
        action = _assign_or_move(state, role) if role else None
        if action is None:
            return None
        who = "one more person" if action["type"] == "assign" else "a person from " + sim.ROLE_LABEL[action["from"]]
        return action, f"Put {who} on {sim.ROLE_LABEL[role]} to fill the stores with materials."
    if advisor_id == "teodor":
        # He only speaks when the settlement is close to running out of room: advice outside his
        # own measure (places to live) could never be judged fairly against it.
        if metric_value(state, "headroom", effects) > HEADROOM_COMFORT or not state.can_build("shelter"):
            return None
        return (
            {"type": "build", "building": "shelter"},
            f"Raise {sim.BUILDING_LABEL['shelter']} ({sim.BUILDING_COST['shelter']:.0f} materials): more places to live "
            "before growth stalls.",
        )
    return None


def _judge(gain, score_effect, key):
    floor = 1.0 if key == "headroom" else GAIN_MIN
    if gain < floor:
        return "empty"
    return "narrow" if score_effect < -SCORE_TOLERANCE else "sound"


def issue(ui, state, effects):
    """Writes a fresh set of advice for the current season into the record."""
    record = get(ui)
    advice = []
    for advisor_id in ORDER:
        found = candidate_action(advisor_id, state, effects)
        if found is None:
            continue
        action, text = found
        key = ADVISORS[advisor_id]["metric"]
        with_action = _simulate(state, effects, action, key)
        baseline = _simulate(state, effects, None, key)
        if with_action is None or baseline is None:
            continue
        before = metric_value(state, key, effects)
        gain = with_action[0] - baseline[0]
        score_effect = with_action[1] - baseline[1]
        advice.append({
            "id": advisor_id, "action": action, "text": text, "metric": key,
            "net_gain": gain, "net_baseline": baseline[0] - before, "net_before": before,
            "score_delta": score_effect, "quality": _judge(gain, score_effect, key),
            "status": "open", "rival": "",
        })
    # advisors that need the same scarce thing disagree out loud
    groups = {"people": [], "materials": []}
    for item in advice:
        kind = item["action"]["type"]
        if kind == "assign" and state.idle_workers() <= 1:
            groups["people"].append(item)
        elif kind == "build":
            groups["materials"].append(item)
    for name, items in groups.items():
        if len(items) < 2:
            continue
        if name == "materials":
            total = sum(sim.BUILDING_COST[i["action"]["building"]] for i in items)
            if total <= state.resources["materials"]:
                continue
        for item in items:
            item["rival"] = next(o for o in items if o is not item)["id"]
    record["advice"] = advice
    record["season"] = int(state.season)
    return put(ui, record)


def settle(ui, state, effects):
    """Called when a new season begins: judges the advice of the season that
    just ended, updates trust and the records, keeps a short history."""
    record = get(ui)
    for item in record["advice"]:
        advisor_id = item["id"]
        rec = record["record"][advisor_id]
        rec[item["quality"]] += 1
        rec["followed" if item["status"] == "followed" else "ignored"] += 1
        step = 1 if item["quality"] == "sound" else -1
        record["trust"][advisor_id] = max(TRUST_MIN, min(TRUST_MAX, record["trust"][advisor_id] + step))
        record["history"].append({"id": advisor_id, "season": record["season"], "text": outcome_text(item, state, effects)})
    record["history"] = record["history"][-HISTORY_MAX:]
    record["advice"] = []
    return put(ui, record)


def outcome_text(item, state, effects):
    info = ADVISORS[item["id"]]
    unit = info["unit"]
    verdict = {
        "sound": "Sound advice.",
        "narrow": "Narrow advice: it helped their corner but cost the settlement as a whole.",
        "empty": "It would not have changed much.",
    }[item["quality"]]
    if item["status"] == "followed":
        now = metric_value(state, item["metric"], effects)
        return (
            f"{info['name']} (taken): {unit} went {item['net_before']:.1f} to {now:.1f}; predicted "
            f"{item['net_gain']:+.1f} over doing nothing. {verdict}"
        )
    return f"{info['name']} (not taken): it would have been {item['net_gain']:+.1f} {unit} for {item['score_delta']:+.1f} sustainability. {verdict}"


def mark_followed(ui, advisor_id):
    record = get(ui)
    for item in record["advice"]:
        if item["id"] == advisor_id and item["status"] == "open":
            item["status"] = "followed"
            put(ui, record)
            return True
    return False


def stale(ui, state):
    """True if the stored advice is not for this season (so it should be reissued)."""
    return get(ui)["season"] != int(state.season)


# --- text -----------------------------------------------------------------------------------
def trust_text(value):
    pips = "●" * value + "○" * (TRUST_MAX - value)
    return f"Trust {pips} {value} of {TRUST_MAX}"


def record_text(rec):
    judged = rec["sound"] + rec["narrow"] + rec["empty"]
    if not judged:
        return "No record yet."
    return (
        f"{judged} judged: {rec['sound']} sound, {rec['narrow']} narrow, {rec['empty']} empty. "
        f"You took {rec['followed']} and passed on {rec['ignored']}."
    )


def claim_text(item):
    info = ADVISORS[item["id"]]
    if item["metric"] == "headroom":
        claim = f"Next season: {item['net_gain']:+.0f} {info['unit']} compared with doing nothing."
    else:
        claim = f"Next season: {item['net_gain']:+.1f} {info['unit']} compared with doing nothing."
    claim += f" Effect on sustainability: {item['score_delta']:+.1f}."
    claim += {
        "sound": " Looks sound.",
        "narrow": " Narrow: it helps their corner at the whole's expense.",
        "empty": " Would change little.",
    }[item["quality"]]
    if item["rival"]:
        claim += f" Competes with {ADVISORS[item['rival']]['name']}'s advice for the same people or materials."
    return claim
