
import engine


def test_trait_active_returns_true_for_non_trait_selectors(C):
    """Non-trait selectors (e.g., role, crew) always return True."""
    target_id = C.target_order[0]
    crew_ids = C.crew_order[:5]
    sim = engine.Sim(C, target_id, crew_ids, {}, seed=1)
    assert sim.trait_active(0, "role:lookout") is True
    assert sim.trait_active(0, "crew:dot") is True


def test_trait_active_returns_true_for_matching_active_trait(C):
    """A selector matching an active trait ID returns True."""
    target_id = C.target_order[0]
    crew_ids = C.crew_order[:5]
    sim = engine.Sim(C, target_id, crew_ids, {}, seed=1)
    trait_id = sim.trait_ids[0][0] if sim.trait_ids[0] else None
    assert trait_id is not None
    selector = f"trait:{trait_id}"
    assert sim.trait_active(0, selector) is True


def test_trait_active_returns_false_for_hidden_quirk_in_preview_mode(C):
    """When preview=True hides a quirk, querying that quirk ID returns False."""
    target_id = C.target_order[0]
    crew_ids = C.crew_order[:5]
    quirk_id = None
    for cid in crew_ids:
        q = C.crew[cid].get("quirk")
        if q and q in C.traits:
            quirk_id = q
            break
    assert quirk_id is not None, "Need a crew member with a quirk"

    sim = engine.Sim(C, target_id, crew_ids, {}, seed=1, preview=True, hidden_quirks=[crew_ids[0]])
    selector = f"trait:{quirk_id}"
    assert sim.trait_active(0, selector) is False
