import engine
import content


def _make_sim():
    C = content.load()
    tid = C.target_order[0]
    crew_ids = C.crew_order[:5]
    n_beats = len(C.targets[tid]["beats"])
    plan = engine.empty_plan(n_beats)
    # Ensure there is at least one task slot to test put_mod on
    for aid, act in C.actions.items():
        if act["kind"] == "task":
            plan["lanes"][0][0] = aid
            break
    return engine.Sim(C, tid, crew_ids, plan)


def test_put_mod_adds_new_label():
    """put_mod adds a new label to slot['mods'] and sets mod_src."""
    sim = _make_sim()
    slots, _ = engine.build_slots(sim.c, sim.plan, sim.n)
    slot = slots[0][0]
    sim.put_mod(slot, "test_label", 3, src="test_source")
    assert slot["mods"]["test_label"] == 3
    assert slot["mod_src"]["test_label"] == "test_source"


def test_put_mod_overwrites_when_abs_is_larger():
    """put_mod overwrites an existing label only if the new absolute value is strictly larger."""
    sim = _make_sim()
    slots, _ = engine.build_slots(sim.c, sim.plan, sim.n)
    slot = slots[0][0]
    slot["mods"]["existing"] = 2
    slot["mod_src"]["existing"] = "old_src"
    sim.put_mod(slot, "existing", -5, src="new_src")
    assert slot["mods"]["existing"] == -5
    assert slot["mod_src"]["existing"] == "new_src"


def test_put_mod_does_nothing_on_zero_value():
    """put_mod returns early without modifying the slot when value is 0."""
    sim = _make_sim()
    slots, _ = engine.build_slots(sim.c, sim.plan, sim.n)
    slot = slots[0][0]
    sim.put_mod(slot, "zero_label", 0, src="ignored")
    assert "zero_label" not in slot["mods"]
    assert "zero_label" not in slot["mod_src"]
