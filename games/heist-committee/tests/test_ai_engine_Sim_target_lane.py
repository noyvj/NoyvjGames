import json
from pathlib import Path

import bots
import content
import engine

_DIR = Path(__file__).resolve().parents[3] / "games" / "heist-committee" / "content"


def _load_raw():
    raw = {}
    for f in _DIR.glob("*.json"):
        with open(f, encoding="utf-8") as fh:
            raw[f.stem] = json.load(fh)
    return raw


C = content.Content(_load_raw())


def _make_sim(target_id="pigeon_museum", seed=42):
    plan = bots.greedy_plan(C, target_id, C.crew_order[:5])
    sim = engine.Sim(C, target_id, C.crew_order[:5], plan, seed=seed)
    sim.run()
    return sim


def test_target_lane_any_task_returns_first_busy_task():
    """Normal case: 'any_task' returns the first lane with a task at the target beat."""
    sim = _make_sim()
    comp = {"effects": {"target": "any_task"}}
    for b in range(sim.n):
        when = b + 1
        busy_tasks = [
            lane for lane in range(engine.LANES)
            if sim.busy(lane, when)
            and sim.slot_at(lane, when)["action"]["kind"] == "task"
            and sim.sidelined.get(lane, -1) <= when
        ]
        if busy_tasks:
            assert sim.target_lane(comp, b, "post") == busy_tasks[0]
            break


def test_target_lane_action_filter_returns_matching_task():
    """Normal case: 'action:<id>' returns the task lane with that action id."""
    sim = _make_sim()
    comp = {"effects": {}}
    found = False
    for b in range(sim.n):
        when = b + 1
        for lane in range(engine.LANES):
            slot = sim.slot_at(lane, when)
            if slot and slot["action"]["kind"] == "task":
                action_id = slot["action"]["id"]
                comp["effects"]["target"] = f"action:{action_id}"
                assert sim.target_lane(comp, b, "post") == lane
                found = True
                break
        else:
            continue
        if found:
            break
    assert found, "Expected at least one task in the greedy plan"


def test_target_lane_none_spec_returns_none():
    """Edge case: 'none' target spec always returns None regardless of beat or phase."""
    sim = _make_sim()
    comp = {"effects": {"target": "none"}}
    for b in range(sim.n):
        assert sim.target_lane(comp, b, "pre") is None
        assert sim.target_lane(comp, b, "post") is None
