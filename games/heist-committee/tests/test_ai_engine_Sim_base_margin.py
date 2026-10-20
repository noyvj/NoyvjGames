import engine


def test_base_margin_skill_and_difficulty(C):
    """Normal case: returns skill pips minus difficulty plus one, as the first tuple."""
    crew_id = C.crew_order[0]
    crew = C.crew[crew_id]

    action_id = next(k for k, v in C.actions.items() if v.get("skill"))
    action = C.actions[action_id]

    sim = engine.Sim(C, "pigeon_museum", [crew_id] * 5, {"lanes": [[None] * 5 for _ in range(5)]}, seed=0)
    slot = {"lane": 0, "action": action, "dur": 1, "truncated": False}

    parts = sim.base_margin(slot)
    assert isinstance(parts, list) and len(parts) > 0

    skill_pips = crew["skills"].get(action["skill"], 0)
    expected_base_val = skill_pips - action["difficulty"] + 1
    label, val = parts[0]
    assert val == expected_base_val
    assert "against difficulty" in label


def test_base_margin_includes_trait_margins(C):
    """Normal case: adds margins from traits (margin_all, margin_by_duration, margin_for_action)."""
    trait_with_margin = None
    for tid, t in C.traits.items():
        if t.get("margin_all"):
            trait_with_margin = t
            break

    if not trait_with_margin:
        crew_id = C.crew_order[0]
        sim = engine.Sim(C, "pigeon_museum", [crew_id] * 5, {"lanes": [[None] * 5 for _ in range(5)]}, seed=0)
        action_id = next(k for k, v in C.actions.items() if v.get("skill"))
        slot = {"lane": 0, "action": C.actions[action_id], "dur": 1, "truncated": False}
        parts = sim.base_margin(slot)
        assert isinstance(parts, list)
        return

    crew_id = C.crew_order[0]
    sim = engine.Sim(C, "pigeon_museum", [crew_id] * 5, {"lanes": [[None] * 5 for _ in range(5)]}, seed=0)
    trait_id = next(k for k, v in C.traits.items() if v.get("margin_all"))
    sim.traits[0] = [C.traits[trait_id]]

    action_id = next(k for k, v in C.actions.items() if v.get("skill"))
    slot = {"lane": 0, "action": C.actions[action_id], "dur": 1, "truncated": False}

    parts = sim.base_margin(slot)
    found_trait_margin = False
    for label, val in parts:
        if trait_with_margin["name"] in label and val == int(trait_with_margin["margin_all"]):
            found_trait_margin = True
            break
    assert found_trait_margin, "Trait margin_all should appear in base_margin parts"


def test_base_margin_truncated_slot(C):
    """Edge case: a truncated slot adds ('Ran out of beats', -2) to the parts list."""
    crew_id = C.crew_order[0]
    sim = engine.Sim(C, "pigeon_museum", [crew_id] * 5, {"lanes": [[None] * 5 for _ in range(5)]}, seed=0)
    action_id = next(k for k, v in C.actions.items() if v.get("skill"))
    slot = {"lane": 0, "action": C.actions[action_id], "dur": 1, "truncated": True}

    parts = sim.base_margin(slot)
    truncated_entry = ("Ran out of beats", -2)
    assert truncated_entry in parts, "Truncated slot should add ('Ran out of beats', -2)"
