import content
import engine
import bots


def test_finish_margin_returns_correct_sum():
    """A normal task slot should return a margin equal to the sum of its parts."""
    C = content.load()
    target_id = "pigeon_museum"
    crew_ids = C.crew_order[:5]
    plan = bots.greedy_plan(C, target_id, crew_ids)
    sim = engine.Sim(C, target_id, crew_ids, plan, seed=0)

    slot = None
    for lane_slots in sim.slots:
        for s in lane_slots:
            if s and s["action"]["kind"] == "task":
                slot = s
                break
        if slot:
            break

    assert slot is not None

    margin, parts = sim.finish_margin(slot)
    assert isinstance(margin, int)
    assert sum(v for _, v in parts) == margin


def test_finish_margin_includes_mods():
    """Modifications applied to a slot (e.g., from traits or relationships) must be included in the sum."""
    C = content.load()
    target_id = "pigeon_museum"
    crew_ids = C.crew_order[:5]
    plan = bots.greedy_plan(C, target_id, crew_ids)
    sim = engine.Sim(C, target_id, crew_ids, plan, seed=0)

    slot = None
    for lane_slots in sim.slots:
        for s in lane_slots:
            if s and s["action"]["kind"] == "task":
                slot = s
                break
        if slot:
            break

    assert slot is not None

    # Simulate a mod being applied (as `put_mod` would do)
    slot["mods"]["test_bonus"] = 3

    margin, parts = sim.finish_margin(slot)

    # The mod should appear in parts and contribute to the total
    assert any(p[0] == "test_bonus" for p in parts)
    assert margin == sum(v for _, v in parts)


def test_finish_margin_edge_case_truncated():
    """A truncated slot (action runs out of beats) should include a '-2' penalty in its parts."""
    C = content.load()
    target_id = "pigeon_museum"
    crew_ids = C.crew_order[:5]
    plan = bots.greedy_plan(C, target_id, crew_ids)
    sim = engine.Sim(C, target_id, crew_ids, plan, seed=0)

    slot = None
    for lane_slots in sim.slots:
        for s in lane_slots:
            if s and s["action"]["kind"] == "task":
                slot = s
                break
        if slot:
            break

    assert slot is not None

    # Force truncation to test the edge case logic in base_margin
    original_truncated = slot.get("truncated", False)
    slot["truncated"] = True

    margin, parts = sim.finish_margin(slot)

    # Check that the penalty part exists and has value -2
    penalty_parts = [p for p in parts if p[0] == "Ran out of beats"]
    assert len(penalty_parts) == 1
    assert penalty_parts[0][1] == -2

    # Restore original state
    slot["truncated"] = original_truncated
