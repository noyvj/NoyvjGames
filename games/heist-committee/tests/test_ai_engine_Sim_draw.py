import content
import engine


def _make_sim():
    C = content.load()
    tid = "pigeon_museum"
    crew = ["dot", "pip", "bea", "tomasz", "hank"]
    sim = engine.Sim(C, tid, crew, {"lanes": [[None] * 5 for _ in range(5)]}, seed=0)
    sim.chain_depth = 0
    sim.tags = {t: 99 for t in sim.target.get("start_tags", [])}
    return C, tid, crew, sim


def test_draw_fires_a_complication_when_eligible_and_suspicion_is_high():
    """Normal case: high suspicion and an eligible random complication lead to a fire."""
    C, tid, crew, sim = _make_sim()

    target_b = None
    for b in range(sim.n):
        if any(c["trigger"] == "random" and sim.eligible(c, b) for c in sim.pool):
            target_b = b
            break
    assert target_b is not None, "No eligible random complication found in this target"

    sim.suspicion = 5
    p = min(0.9, 0.5 + 0.08 * 5)

    trigger_seed = None
    for s in range(100):
        if engine.roll(s, target_b, "fire", 0) < p:
            trigger_seed = s
            break
    assert trigger_seed is not None

    sim.seed = trigger_seed
    before_fired = set(sim.fired)
    before_chain_depth = sim.chain_depth

    sim.draw(target_b)

    assert len(sim.fired) > len(before_fired), "Expected a complication to fire"
    assert sim.chain_depth > before_chain_depth, "Expected chain_depth to increase on fire"


def test_draw_returns_early_when_all_random_complications_already_fired():
    """Edge case: if every random complication in the pool has already fired this heist, draw returns immediately."""
    _, _, _, sim = _make_sim()

    for comp in sim.pool:
        if comp["trigger"] == "random":
            sim.fired.add(comp["id"])

    before_fired = set(sim.fired)
    before_chain_depth = sim.chain_depth

    sim.draw(0)

    assert sim.fired == before_fired
    assert sim.chain_depth == before_chain_depth


def test_draw_reduces_probability_on_second_pass_k1():
    """Normal case: the second draw pass (k=1) reduces probability by 0.6 when suspicion is >= 5."""
    C, tid, crew, sim = _make_sim()

    target_b = None
    for b in range(sim.n):
        if any(c["trigger"] == "random" and sim.eligible(c, b) for c in sim.pool):
            target_b = b
            break
    assert target_b is not None

    # Suspicion 5 allows the second pass to run. p=0.9 on k=0, 0.9*0.6=0.54 on k=1
    sim.suspicion = 5

    p0 = min(0.9, 0.5 + 0.08 * 5)
    p1 = p0 * 0.6

    # Find a seed that does NOT fire on k=0 but DOES fire on k=1
    trigger_seed = None
    for s in range(200):
        r0 = engine.roll(s, target_b, "fire", 0)
        r1 = engine.roll(s, target_b, "fire", 1)
        if r0 >= p0 and r1 < p1:
            trigger_seed = s
            break

    assert trigger_seed is not None

    sim.seed = trigger_seed
    before_chain_depth = sim.chain_depth

    sim.draw(target_b)

    # Should fire exactly once (on k=1), not twice
    assert sim.chain_depth == before_chain_depth + 1
