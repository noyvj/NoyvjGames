import content
import engine
import bots


def _make_sim(relations=None):
    c = content.load()
    tid = c.target_order[0]
    crew_ids = c.crew_order[:5]
    plan = bots.greedy_plan(c, tid, crew_ids)
    sim = engine.Sim(c, tid, crew_ids, plan, relations=relations or {})
    task_id = next(a["id"] for a in c.actions.values() if a["kind"] == "task" and a.get("duration", 1) == 1)
    task_action = c.actions[task_id]
    slot_template = {"lane": None, "action": task_action, "arg": None, "start": 0, "dur": 1, "end": 0,
                     "truncated": False, "mods": {}, "mod_src": {}, "lost": False, "outcome": None,
                     "margin": None, "event": None, "done": False}
    sim.slots[0][0] = {**slot_template, "lane": 0}
    sim.occ[0][0] = sim.slots[0][0]
    sim.slots[1][0] = {**slot_template, "lane": 1}
    sim.occ[1][0] = sim.slots[1][0]
    return sim


def test_pair_effects_returns_friends_when_relation_is_friends():
    """Normal case: two crew with 'friends' relation, both active in tasks on the same beat."""
    sim = _make_sim()
    pair_key = "|".join(sorted((sim.crew_ids[0], sim.crew_ids[1])))
    sim.relations[pair_key] = "friends"
    effects = sim.pair_effects(0, 0)
    assert any(e["kind"] == "friends" for e in effects), f"Expected friends effect, got {effects}"


def test_pair_effects_returns_rival_when_relation_is_feud():
    """Normal case: two crew with 'feud' relation, both active in tasks on the same beat."""
    sim = _make_sim()
    pair_key = "|".join(sorted((sim.crew_ids[0], sim.crew_ids[1])))
    sim.relations[pair_key] = "feud"
    effects = sim.pair_effects(0, 0)
    assert any(e["kind"] == "rival" for e in effects), f"Expected rival effect, got {effects}"


def test_pair_effects_returns_empty_when_lane_is_not_task_or_support():
    """Edge case: the queried lane is idle/standby, so no pair effects are generated."""
    sim = _make_sim()
    # Lane 2 is empty in our plan
    effects = sim.pair_effects(2, 0)
    assert effects == [], f"Expected empty list for inactive lane, got {effects}"
