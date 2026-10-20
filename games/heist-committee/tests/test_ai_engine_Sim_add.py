import content
import engine


def test_add_creates_event_with_correct_defaults():
    """Normal case: add() creates an event dict with correct fields and returns its index."""
    c = content.load()
    plan = engine.empty_plan(5)
    crew_ids = c.crew_order[:5]
    sim = engine.Sim(c, c.target_order[0], crew_ids, plan)

    idx = sim.add("note", "Test event", lane=1, why="because", tags=("a", "b"), cause=None, outcome="success", icon="★")

    assert idx == 0
    ev = sim.events[0]
    assert ev["i"] == 0
    assert ev["beat"] == sim.b
    assert ev["type"] == "note"
    assert ev["text"] == "Test event"
    assert ev["lane"] == 1
    assert ev["crew"] == crew_ids[1]
    assert ev["why"] == "because"
    assert ev["tags"] == ["a", "b"]
    assert ev["cause"] is None
    assert ev["outcome"] == "success"
    assert ev["icon"] == "★"
    assert ev["comp"] is None
    assert ev["trait"] is None
    assert ev["action"] is None
    assert ev["flavor"] == ""
    assert ev["depth"] == 1


def test_add_merges_extra_dict():
    """Normal case: add() merges an extra dict into the event."""
    c = content.load()
    plan = engine.empty_plan(5)
    crew_ids = c.crew_order[:5]
    sim = engine.Sim(c, c.target_order[0], crew_ids, plan)

    idx = sim.add("goal", "Picked lock", lane=2, extra={"req": "lock1", "start": 3})

    ev = sim.events[idx]
    assert ev["req"] == "lock1"
    assert ev["start"] == 3


def test_add_links_depth_via_cause():
    """Edge case: when cause is provided, depth increments based on the cause event's depth."""
    c = content.load()
    plan = engine.empty_plan(5)
    crew_ids = c.crew_order[:5]
    sim = engine.Sim(c, c.target_order[0], crew_ids, plan)

    idx1 = sim.add("note", "First event")
    assert sim.events[idx1]["depth"] == 1

    idx2 = sim.add("note", "Second event", cause=idx1)
    assert sim.events[idx2]["depth"] == 2


def test_add_lane_none_sets_crew_none():
    """Edge case: lane=None results in crew=None."""
    c = content.load()
    plan = engine.empty_plan(5)
    crew_ids = c.crew_order[:5]
    sim = engine.Sim(c, c.target_order[0], crew_ids, plan)

    idx = sim.add("note", "No lane event", lane=None)

    assert sim.events[idx]["crew"] is None
