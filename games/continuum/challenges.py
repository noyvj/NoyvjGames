"""Continuum -- K11: opt-in civic engineering challenges.

Planning/TODO.md K11: "periodic optional constraints (e.g. build the next
tier using 20% less resource extraction) as opt-in mini-challenges within
an ongoing playthrough."

A challenge is never forced and never punishing. The player picks one from
the (collapsed) Civic Challenges panel, and it runs for a few seasons under
a constraint they chose to accept. Breaking the constraint just ends the
challenge (no penalty beyond not getting the reward); keeping it to the end
pays a modest knowledge bonus that scales with the era. Only one can run at
a time, and the player can abandon it whenever they like.

State lives on `CityState.challenge` so it rides the existing city snapshot
(saves, era snapshots, revisit parking) with no new save plumbing; see
`clean()` for the load-time validation, which follows the Phase 4 lesson
(treat anything malformed exactly like a missing field, never trust it).

Every definition is data plus three small pure functions:

- `baseline(state, effects)`: the number the constraint is measured against,
  captured when the challenge starts, or None if the challenge cannot be
  offered right now (e.g. "recover the land" when the land is already fine).
- `season_ok(state, report, effects, baseline)`: the per-season constraint.
- `final_ok(state, effects, baseline)`: the end-of-window goal.
"""

import math

import sim
import sustainability

LEAN_HARVEST_FRACTION = 0.8  # "20% less resource extraction"
LAND_RECOVERY_TARGET = 0.06
SCORE_CLIMB_TARGET = 3.0
SCORE_SLUMP_ALLOWANCE = 3.0
POLLUTION_SLACK = 0.02
SPRAWL_SLACK = 0.02
EPSILON = 1e-9

REWARD_BASE = 4.0
REWARD_PER_ERA = 2.0


def _lean_baseline(state, effects):
    if state.last_report is None or state.last_extraction <= 1.0:
        return None
    return float(state.last_extraction)


def _land_baseline(state, effects):
    return float(state.land_health) if state.land_health <= 0.9 else None


def _fed_baseline(state, effects):
    return float(state.population)


def _score_baseline(state, effects):
    value = sustainability.score(state, effects)
    return value if value <= 96.0 else None


def _pollution_baseline(state, effects):
    return float(state.pollution)


def _sprawl_baseline(state, effects):
    return float(state.sprawl)


def _no_final(state, effects, baseline):
    return True


CHALLENGES = {
    "lean_harvest": {
        "label": "Lean Harvest",
        "seasons": 4,
        "min_era": "tribal",
        "blurb": "Take 20% less from the land than you did last season, every season, without letting the settlement fall apart.",
        "baseline": _lean_baseline,
        "season_ok": lambda s, r, e, b: r["extraction"] <= b * LEAN_HARVEST_FRACTION + EPSILON,
        "final_ok": _no_final,
        "target": lambda b: f"keep each season's harvest at or under {b * LEAN_HARVEST_FRACTION:.1f} (last season: {b:.1f})",
    },
    "land_recovery": {
        "label": "Let the Land Recover",
        "seasons": 4,
        "min_era": "tribal",
        "blurb": "Stay under the land's sustainable yield every season and bring land health up.",
        "baseline": _land_baseline,
        "season_ok": lambda s, r, e, b: r["extraction"] <= r["sustainable_yield"] + EPSILON,
        "final_ok": lambda s, e, b: s.land_health >= b + LAND_RECOVERY_TARGET - EPSILON,
        "target": lambda b: f"land health from {b * 100:.0f}% to {(b + LAND_RECOVERY_TARGET) * 100:.0f}%, never over the sustainable yield",
    },
    "everyone_fed": {
        "label": "Nobody Goes Hungry",
        "seasons": 5,
        "min_era": "tribal",
        "blurb": "Five seasons with everyone fed and no deaths, and the settlement still growing.",
        "baseline": _fed_baseline,
        "season_ok": lambda s, r, e, b: r["fed_fraction"] >= 1.0 - EPSILON and r["deaths"] == 0,
        "final_ok": lambda s, e, b: s.population >= b + 1,
        "target": lambda b: f"everyone fed every season and population above {int(b)}",
    },
    "score_climb": {
        "label": "Steady Improvement",
        "seasons": 5,
        "min_era": "tribal",
        "blurb": "Raise the sustainability score without any season-to-season slump.",
        "baseline": _score_baseline,
        "season_ok": lambda s, r, e, b: sustainability.score(s, e) >= b - SCORE_SLUMP_ALLOWANCE,
        "final_ok": lambda s, e, b: sustainability.score(s, e) >= b + SCORE_CLIMB_TARGET,
        "target": lambda b: f"score above {b + SCORE_CLIMB_TARGET:.0f} at the end, never below {b - SCORE_SLUMP_ALLOWANCE:.0f}",
    },
    "quiet_industry": {
        "label": "Quiet Industry",
        "seasons": 4,
        "min_era": "industrial",
        "blurb": "Keep pollution from rising while the works keep running.",
        "baseline": _pollution_baseline,
        "season_ok": lambda s, r, e, b: r["pollution"] <= b + POLLUTION_SLACK + EPSILON,
        "final_ok": lambda s, e, b: s.pollution <= b + EPSILON,
        "target": lambda b: f"pollution at or under {b * 100:.0f}% by the end",
    },
    "tight_growth": {
        "label": "Tight Growth",
        "seasons": 4,
        "min_era": "digital",
        "blurb": "Grow without letting sprawl climb.",
        "baseline": _sprawl_baseline,
        "season_ok": lambda s, r, e, b: r["sprawl"] <= b + SPRAWL_SLACK + EPSILON,
        "final_ok": lambda s, e, b: s.sprawl <= b + EPSILON,
        "target": lambda b: f"sprawl at or under {b * 100:.0f}% by the end",
    },
}


def empty_state():
    return {"active": None, "completed": {}, "failed": 0}


def reward_for(era):
    return REWARD_BASE + REWARD_PER_ERA * sim.era_index(era)


def offered(state, effects):
    """Ids the player can start right now (era reached and baseline meaningful)."""
    if state.challenge["active"] is not None:
        return []
    out = []
    for cid, spec in CHALLENGES.items():
        if sim.era_index(state.era) < sim.era_index(spec["min_era"]):
            continue
        if spec["baseline"](state, effects) is None:
            continue
        out.append(cid)
    return out


def start(state, effects, cid):
    if cid not in CHALLENGES or cid not in offered(state, effects):
        return False
    state.challenge["active"] = {
        "id": cid,
        "seasons_done": 0,
        "baseline": CHALLENGES[cid]["baseline"](state, effects),
    }
    return True


def abandon(state):
    if state.challenge["active"] is None:
        return False
    state.challenge["active"] = None
    return True


def status_text(state):
    """One line describing the active challenge, or None."""
    active = state.challenge["active"]
    if active is None:
        return None
    spec = CHALLENGES[active["id"]]
    return (
        f"{spec['label']}: season {active['seasons_done']} of {spec['seasons']} - "
        f"{spec['target'](active['baseline'])}."
    )


def after_season(state, report, effects):
    """Call once per completed season. Returns an event dict or None.

    Events: {"kind": "passed"|"failed", "id", "text", "reward"}.
    """
    active = state.challenge["active"]
    if active is None or not isinstance(report, dict):
        return None
    spec = CHALLENGES[active["id"]]
    if not spec["season_ok"](state, report, effects, active["baseline"]):
        state.challenge["active"] = None
        state.challenge["failed"] += 1
        return {
            "kind": "failed",
            "id": active["id"],
            "reward": 0.0,
            "text": f"Civic challenge '{spec['label']}' ended early: the constraint slipped this season. No penalty - try again when you like.",
        }
    active["seasons_done"] += 1
    if active["seasons_done"] < spec["seasons"]:
        return None
    state.challenge["active"] = None
    if not spec["final_ok"](state, effects, active["baseline"]):
        state.challenge["failed"] += 1
        return {
            "kind": "failed",
            "id": active["id"],
            "reward": 0.0,
            "text": f"Civic challenge '{spec['label']}' ran its course without reaching the goal. No penalty - try again when you like.",
        }
    reward = reward_for(state.era)
    state.resources["knowledge"] += reward
    done = state.challenge["completed"]
    done[active["id"]] = min(999, done.get(active["id"], 0) + 1)
    return {
        "kind": "passed",
        "id": active["id"],
        "reward": reward,
        "text": f"Civic challenge '{spec['label']}' met. The council records the achievement (+{reward:.0f} knowledge).",
    }


def total_completed(state):
    return sum(state.challenge["completed"].values())


def clean(raw):
    """Validates a saved challenge dict; anything malformed becomes the default."""
    result = empty_state()
    if not isinstance(raw, dict):
        return result
    failed = raw.get("failed")
    if isinstance(failed, int) and not isinstance(failed, bool):
        result["failed"] = min(max(failed, 0), 9999)
    completed = raw.get("completed")
    if isinstance(completed, dict):
        for cid, count in completed.items():
            if cid in CHALLENGES and isinstance(count, int) and not isinstance(count, bool):
                result["completed"][cid] = min(max(count, 0), 999)
    active = raw.get("active")
    if isinstance(active, dict) and active.get("id") in CHALLENGES:
        baseline = active.get("baseline")
        done = active.get("seasons_done")
        if (
            isinstance(baseline, (int, float))
            and not isinstance(baseline, bool)
            and math.isfinite(baseline)
            and isinstance(done, int)
            and not isinstance(done, bool)
        ):
            spec = CHALLENGES[active["id"]]
            if 0 <= done < spec["seasons"]:
                result["active"] = {"id": active["id"], "seasons_done": done, "baseline": float(baseline)}
    return result
