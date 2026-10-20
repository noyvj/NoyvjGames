import engine


def test_build_slots_normal_tasks(C):
    """Normal case: plan with single-beat tasks fills occupancy correctly."""
    n_beats = 5
    plan = engine.empty_plan(n_beats)
    task_action = next(k for k, v in C.actions.items() if v["kind"] == "task")
    plan["lanes"][0][0] = task_action
    plan["lanes"][1][2] = task_action

    slots_by_lane, occ = engine.build_slots(C, plan, n_beats)

    assert len(slots_by_lane) == 5
    assert len(occ) == 5
    assert len(slots_by_lane[0]) == 1
    assert slots_by_lane[0][0]["start"] == 0
    assert slots_by_lane[0][0]["dur"] == 1
    assert occ[0][0] is slots_by_lane[0][0]
    assert occ[0][1] is None
    assert len(slots_by_lane[1]) == 1
    assert slots_by_lane[1][0]["start"] == 2
    assert occ[1][2] is slots_by_lane[1][0]


def test_build_slots_truncated_action(C):
    """Edge case: an action longer than remaining beats gets truncated."""
    n_beats = 3
    plan = engine.empty_plan(n_beats)
    multi_action = next(k for k, v in C.actions.items() if int(v.get("duration", 1)) > 1)
    plan["lanes"][0][2] = multi_action

    slots_by_lane, occ = engine.build_slots(C, plan, n_beats)

    assert len(slots_by_lane[0]) == 1
    slot = slots_by_lane[0][0]
    assert slot["start"] == 2
    assert slot["dur"] == 1
    assert slot["truncated"] is True
    assert occ[0][2] is slot


def test_build_slots_mixed_actions(C):
    """Normal case: mixing tasks and standby advances beats correctly."""
    n_beats = 4
    plan = engine.empty_plan(n_beats)
    task_action = next(k for k, v in C.actions.items() if v["kind"] == "task")
    standby_action = next(k for k, v in C.actions.items() if v["kind"] == "standby")

    plan["lanes"][0][0] = task_action
    plan["lanes"][0][1] = standby_action
    plan["lanes"][0][2] = task_action

    slots_by_lane, occ = engine.build_slots(C, plan, n_beats)

    assert len(slots_by_lane[0]) == 3
    assert slots_by_lane[0][0]["start"] == 0
    assert slots_by_lane[0][1]["start"] == 1
    assert slots_by_lane[0][2]["start"] == 2
    assert occ[0][0] is slots_by_lane[0][0]
    assert occ[0][1] is slots_by_lane[0][1]
    assert occ[0][2] is slots_by_lane[0][2]
    assert occ[0][3] is None
