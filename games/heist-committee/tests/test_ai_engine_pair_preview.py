import engine


def test_pair_preview_friends_trigger(C):
    """Normal case: two crew members assigned tasks on the same beat with a 'friends' relation trigger a +1 effect."""
    tid = next(iter(C.targets))
    crew_ids = list(C.crew)[:5]
    c1, c2 = crew_ids[0], crew_ids[1]

    n_beats = len(C.targets[tid]["beats"])
    plan = engine.empty_plan(n_beats)
    actions = list(C.actions)
    plan["lanes"][0][0] = actions[0]
    plan["lanes"][1][0] = actions[1]

    relations = {f"{c1}|{c2}": "friends"}
    result = engine.pair_preview(C, tid, crew_ids, plan, relations=relations)

    friends_effects = [e for e in result if e["kind"] == "friends"]
    assert len(friends_effects) >= 1
    eff = friends_effects[0]
    assert eff["value"] == 1
    assert eff["beat"] >= 0
    assert eff["lane"] != eff["partner"]
    assert isinstance(eff["text"], str) and len(eff["text"]) > 0


def test_pair_preview_feud_trigger(C):
    """Normal case: a 'feud' relation between two active crew members triggers a -2 rival effect."""
    tid = next(iter(C.targets))
    crew_ids = list(C.crew)[:5]
    c1, c2 = crew_ids[0], crew_ids[1]

    n_beats = len(C.targets[tid]["beats"])
    plan = engine.empty_plan(n_beats)
    actions = list(C.actions)
    plan["lanes"][0][0] = actions[0]
    plan["lanes"][1][0] = actions[1]

    relations = {f"{c1}|{c2}": "feud"}
    result = engine.pair_preview(C, tid, crew_ids, plan, relations=relations)

    feud_effects = [e for e in result if e["kind"] == "rival"]
    assert len(feud_effects) >= 1
    eff = feud_effects[0]
    assert eff["value"] == -2


def test_pair_preview_no_active_tasks(C):
    """Edge case: an empty plan means no crew are active, so pair_preview returns an empty list."""
    tid = next(iter(C.targets))
    crew_ids = list(C.crew)[:5]
    plan = engine.empty_plan(len(C.targets[tid]["beats"]))

    result = engine.pair_preview(C, tid, crew_ids, plan)
    assert result == []
