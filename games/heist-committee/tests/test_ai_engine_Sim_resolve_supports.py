import content
import engine


C = content.load()

# Find a valid support action ID for testing
SUPPORT_ACTION_ID = None
for aid, act in C.actions.items():
    if act["kind"] == "support":
        SUPPORT_ACTION_ID = aid
        break
assert SUPPORT_ACTION_ID is not None, "Content must contain at least one support action"


def test_resolve_supports_emits_tags_and_updates_slot_on_success():
    """Normal case: a support action resolves, emits its tags to self.tags/self.src, and sets slot outcome."""
    target_id = C.target_order[0]
    crew_ids = ["dot", "pip", "bea", "tomasz", "hank"]
    plan = {"lanes": [[SUPPORT_ACTION_ID] + [None] * 4 for _ in range(5)]}
    sim = engine.Sim(C, target_id, crew_ids, plan, seed=123)

    sim.begin_beat(0)
    # Force a high margin to guarantee success regardless of crew skills or seed
    sim.slots[0][0]["mods"]["test_force_success"] = 10

    sim.resolve_supports(0)

    slot = sim.slots[0][0]
    assert slot["outcome"] in ("success", "crit")
    assert slot["margin"] is not None
    assert slot["event"] is not None

    provides = C.actions[SUPPORT_ACTION_ID].get("provides", [])
    for tag in provides:
        assert sim.tags.get(tag, 0) > 0
        assert sim.src.get(tag) is not None


def test_resolve_supports_preview_sets_tags_directly():
    """Normal case: when preview=True, resolve_supports skips dice rolls and sets tags directly."""
    target_id = C.target_order[0]
    crew_ids = ["dot", "pip", "bea", "tomasz", "hank"]
    plan = {"lanes": [[SUPPORT_ACTION_ID] + [None] * 4 for _ in range(5)]}
    sim = engine.Sim(C, target_id, crew_ids, plan, seed=0, preview=True)

    sim.begin_beat(0)
    sim.resolve_supports(0)

    slot = sim.slots[0][0]
    assert slot["outcome"] is None  # preview mode leaves outcome unset
    assert slot["margin"] is None   # preview mode does not store margin on the slot

    provides = C.actions[SUPPORT_ACTION_ID].get("provides", [])
    for tag in provides:
        assert sim.tags.get(tag, 0) > 0
        assert sim.src.get(tag) is None  # preview sets src to None
