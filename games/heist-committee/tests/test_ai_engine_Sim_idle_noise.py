import engine


def test_idle_noise_fires_for_idle_crew_with_trait(C):
    """When a crew member is idle at a beat and has a trait with idle_emits, an event is added."""
    tid = C.target_order[0]
    crew_ids = C.crew_order[:5]
    plan = engine.empty_plan(len(C.targets[tid]["beats"]))
    sim = engine.Sim(C, tid, crew_ids, plan, seed=42)
    sim.begin_beat(0)

    expected_idle_traits = set()
    for lane in range(engine.LANES):
        slot = sim.slot_at(lane, 0)
        if not slot and sim.sidelined.get(lane, -1) <= 0:
            for trait in sim.traits[lane]:
                if trait.get("idle_emits"):
                    expected_idle_traits.add(sim.trait_id_of(lane, trait))

    sim.idle_noise(0)

    assert sim.stats["seen_traits"] == expected_idle_traits


def test_idle_noise_skips_busy_lanes(C):
    """If a lane has a task or support at the beat, idle_noise does not fire for it."""
    tid = C.target_order[0]
    crew_ids = C.crew_order[:5]
    plan = engine.empty_plan(len(C.targets[tid]["beats"]))
    task_action = next(a for a in C.actions if C.actions[a]["kind"] == "task")
    plan["lanes"][0][0] = task_action

    sim = engine.Sim(C, tid, crew_ids, plan, seed=42)
    sim.begin_beat(0)

    fired_count_before = len(sim.events)
    sim.idle_noise(0)

    lane_0_events = [e for e in sim.events[fired_count_before:] if e.get("lane") == 0]
    assert len(lane_0_events) == 0


def test_idle_noise_skips_sidelined_crew(C):
    """Sidelined crew members are skipped even if they would otherwise be idle."""
    tid = C.target_order[0]
    crew_ids = C.crew_order[:5]
    plan = engine.empty_plan(len(C.targets[tid]["beats"]))

    sim = engine.Sim(C, tid, crew_ids, plan, seed=42)
    sim.sidelined[1] = 1

    expected_idle_traits = set()
    for lane in range(engine.LANES):
        slot = sim.slot_at(lane, 0)
        if not slot and sim.sidelined.get(lane, -1) <= 0:
            for trait in sim.traits[lane]:
                if trait.get("idle_emits"):
                    expected_idle_traits.add(sim.trait_id_of(lane, trait))

    sim.idle_noise(0)

    assert sim.stats["seen_traits"] == expected_idle_traits
