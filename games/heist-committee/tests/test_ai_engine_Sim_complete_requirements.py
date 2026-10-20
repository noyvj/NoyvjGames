import content
import engine


def test_complete_requirements_marks_done_and_grabbed():
    """Normal case: an action falls within a requirement's window, has no dependencies, and completes it."""
    c = content.load()
    target_id = "pigeon_museum"
    crew_ids = ["dot", "pip", "bea", "tomasz", "hank"]
    n_beats = len(c.targets[target_id]["beats"])
    plan = engine.empty_plan(n_beats)
    sim = engine.Sim(c, target_id, crew_ids, plan, seed=42)

    # Find a requirement that has no dependencies and fits within the target's beats
    req = None
    for r in c.targets[target_id]["requirements"]:
        if not r.get("needs_done") and r["window"][0] <= n_beats:
            req = r
            break
    assert req is not None, "Could not find a simple requirement"

    # Craft a slot that matches the requirement's action and window
    action_id = req["actions"][0]
    start_beat = req["window"][0] - 1  # convert to 0-indexed
    slot = {
        "action": {"id": action_id, "name": "Test Action"},
        "start": start_beat,
        "end": start_beat,
        "lane": 0
    }

    sim.complete_requirements(slot, start_beat, "success")

    assert req["id"] in sim.done
    assert sim.done[req["id"]] == slot["end"]
    assert "_outcome_" + req["id"] in sim.done
    if req.get("value", 0) > 0:
        assert sim.done.get("_grabbed") is True


def test_complete_requirements_respects_dependencies():
    """Normal case: a requirement with dependencies is not completed until those deps are met."""
    c = content.load()
    target_id = "pigeon_museum"
    crew_ids = ["dot", "pip", "bea", "tomasz", "hank"]
    n_beats = len(c.targets[target_id]["beats"])
    plan = engine.empty_plan(n_beats)
    sim = engine.Sim(c, target_id, crew_ids, plan, seed=42)

    # Find a requirement that has dependencies
    req_with_deps = None
    for r in c.targets[target_id]["requirements"]:
        if r.get("needs_done") and r["window"][0] <= n_beats:
            req_with_deps = r
            break

    if not req_with_deps:
        assert False, "No requirements with dependencies found in pigeon_museum"

    # Craft a slot that matches the requirement's action and window
    action_id = req_with_deps["actions"][0]
    start_beat = req_with_deps["window"][0] - 1
    slot = {
        "action": {"id": action_id, "name": "Test Action"},
        "start": start_beat,
        "end": start_beat,
        "lane": 0
    }

    # Dependencies are not met yet
    sim.complete_requirements(slot, start_beat, "success")
    assert req_with_deps["id"] not in sim.done

    # Now meet the dependencies by completing them earlier (their end beat < slot.start)
    for dep_id in req_with_deps["needs_done"]:
        sim.done[dep_id] = start_beat - 1  # completed before this action starts

    sim.complete_requirements(slot, start_beat, "success")
    assert req_with_deps["id"] in sim.done


def test_complete_requirements_skips_already_completed():
    """Edge case: if a requirement is already in self.done, it should not be processed again."""
    c = content.load()
    target_id = "pigeon_museum"
    crew_ids = ["dot", "pip", "bea", "tomasz", "hank"]
    n_beats = len(c.targets[target_id]["beats"])
    plan = engine.empty_plan(n_beats)
    sim = engine.Sim(c, target_id, crew_ids, plan, seed=42)

    req = c.targets[target_id]["requirements"][0]

    # Mark it as already done with a specific value
    original_end = 99
    sim.done[req["id"]] = original_end

    slot = {
        "action": {"id": req["actions"][0], "name": "Test Action"},
        "start": req["window"][0] - 1,
        "end": req["window"][0] - 1,
        "lane": 0
    }

    sim.complete_requirements(slot, slot["start"], "success")

    # It should still be done at the original value, not overwritten
    assert sim.done[req["id"]] == original_end
