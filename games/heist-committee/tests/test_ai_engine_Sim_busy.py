import engine
import bots


def test_busy_returns_true_for_task_and_support(C):
    """Sim.busy() should return True when the slot at (lane, beat) is a task or support."""
    target_id = "pigeon_museum"
    crew_ids = C.crew_order[:5]
    plan = bots.greedy_plan(C, target_id, crew_ids)
    sim = engine.Sim(C, target_id, crew_ids, plan, seed=42)

    found_busy = False
    for b in range(sim.n):
        for lane in range(5):
            if sim.busy(lane, b):
                slot = sim.slot_at(lane, b)
                assert slot["action"]["kind"] in ("task", "support")
                found_busy = True
    assert found_busy, "Expected at least one busy cell in the greedy plan"


def test_busy_returns_false_for_idle(C):
    """Sim.busy() should return False when the slot is None (idle or standby)."""
    target_id = "pigeon_museum"
    crew_ids = C.crew_order[:5]
    n_beats = len(C.targets[target_id]["beats"])
    plan = {"lanes": [[None] * n_beats for _ in range(5)]}
    sim = engine.Sim(C, target_id, crew_ids, plan, seed=42)

    for b in range(sim.n):
        for lane in range(5):
            assert sim.busy(lane, b) is False


def test_busy_handles_out_of_bounds_beats(C):
    """Sim.busy() should return False for beats outside the target's range."""
    target_id = "pigeon_museum"
    crew_ids = C.crew_order[:5]
    plan = bots.greedy_plan(C, target_id, crew_ids)
    sim = engine.Sim(C, target_id, crew_ids, plan, seed=42)

    assert sim.busy(0, -1) is False
    assert sim.busy(0, sim.n) is False
