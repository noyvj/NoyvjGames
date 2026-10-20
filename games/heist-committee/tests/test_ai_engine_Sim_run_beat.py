import bots
import engine


def test_run_beat_resolves_task_and_sets_tags(C):
    """Normal case: beat 0 with a task resolves, sets tags, and records events."""
    target_id = "pigeon_museum"
    crew_ids = ["dot", "pip", "bea", "tomasz", "hank"]
    plan = bots.greedy_plan(C, target_id, crew_ids)

    sim = engine.Sim(C, target_id, crew_ids, plan, seed=42)
    sim.run_beat(0)

    assert sim.b == 0
    assert len(sim.events) > 0
    beat_tags = C.targets[target_id]["beats"][0].get("tags", [])
    if beat_tags:
        assert any(t in sim.tags for t in beat_tags), "Beat tags should be active"


def test_run_beat_resolves_support_and_provides_tags(C):
    """Normal case: a beat with a support action resolves and emits its provided tags."""
    target_id = "pigeon_museum"
    crew_ids = ["dot", "pip", "bea", "tomasz", "hank"]
    plan = bots.greedy_plan(C, target_id, crew_ids)

    sim = engine.Sim(C, target_id, crew_ids, plan, seed=42)
    n_beats = len(C.targets[target_id]["beats"])

    for b in range(n_beats):
        for lane in range(5):
            slot = sim.slot_at(lane, b)
            if slot and slot["action"]["kind"] == "support":
                sim.run_beat(b)
                provides = slot["action"].get("provides", [])
                if provides:
                    assert any(t in sim.tags for t in provides), f"Support tags {provides} not active after beat {b}"
                return


def test_run_beat_preview_skips_random_draws(C):
    """Edge case: preview mode skips idle_noise, draw, and chain calls."""
    target_id = "pigeon_museum"
    crew_ids = ["dot", "pip", "bea", "tomasz", "hank"]
    plan = bots.greedy_plan(C, target_id, crew_ids)

    sim = engine.Sim(C, target_id, crew_ids, plan, seed=42, preview=True)
    sim.run_beat(0)

    comp_events = [e for e in sim.events if e["type"] == "complication" or e.get("comp")]
    assert len(comp_events) == 0, "Preview mode should not trigger random complications"
