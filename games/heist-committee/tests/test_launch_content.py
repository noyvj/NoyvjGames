import random

import bots
import content
import engine


def test_launch_minimums(C):
    assert len(C.targets) >= 3 and len(C.crew) >= 12 and len(C.complications) >= 20 and len(C.gear) >= 3


def test_every_target_has_a_pool_scouting_and_a_final_requirement(C):
    for tid, t in C.targets.items():
        assert len(t["pool"]) >= 8
        assert len(t["scout"]["levels"]) == 3 and t["scout"]["levels"][0]["cost"] == 0
        assert len(t["scout"]["details"]) >= 3
        assert any(r.get("final") for r in t["requirements"])
        assert any(r.get("optional") for r in t["requirements"])
        assert t["intro"] and t["blurb"] and t["short"]


def test_every_target_beat_count_matches_its_windows(C):
    for t in C.targets.values():
        n = len(t["beats"])
        for r in t["requirements"]:
            assert r["window"][1] <= n


def test_every_complication_is_used_by_some_target_and_has_a_counter(C):
    pooled = {c for t in C.targets.values() for c in t["pool"]}
    assert pooled == set(C.complications)
    for comp in C.complications.values():
        assert content.counters_for(C, comp), comp["id"]


def test_each_target_is_winnable_and_losable_with_the_greedy_plan(C):
    for tid in C.target_order:
        wins = losses = 0
        for seed in range(80):
            crew = random.Random(seed).sample(C.crew_order, 5)
            out = engine.simulate(C, tid, crew, bots.greedy_plan(C, tid, crew), seed=seed)["outcome"]
            wins += out["escaped"]
            losses += not out["escaped"]
        assert wins >= 10 and losses >= 3, tid


def test_every_complication_can_actually_fire_somewhere(C):
    """Content with a complication that never triggers in any target would be dead weight."""
    fired = set()
    for tid in C.target_order:
        for seed in range(500):
            crew = random.Random(seed * 7).sample(C.crew_order, 5)
            plan = bots.random_plan(C, tid, crew, seed) if seed % 2 else bots.greedy_plan(C, tid, crew)
            sim = engine.Sim(C, tid, crew, plan, ("earplugs",), seed).run()
            fired.update(e["comp"] for e in sim.events if e["comp"])
    assert fired == set(C.complications), sorted(set(C.complications) - fired)


def test_the_cat_complication_exists_on_every_target_for_the_collector(C):
    assert all("cat_in_gallery" in t["pool"] for t in C.targets.values())


def test_board_offers_every_launch_target(g):
    g.module.career.meta["reputation"] = 3
    board = g(action="open")["view"]["board"]
    assert [t["id"] for t in board] == ["pigeon_museum", "the_affineur", "lucky_barge"]


def test_every_target_can_be_played_through_the_ui_engine(g):
    for tid in ("the_affineur", "lucky_barge", "glasshouse_dome", "hilltop_observatory"):
        g(action="new_career", seed=5)
        g.module.career.meta["reputation"] = 20
        g.module.career.jobs_started = next(n for n in range(200) if tid in g.module._board_targets_for(n))
        g(action="take_job", target=tid)
        g(action="to_recruit")
        job = g.module.career.job
        job["offer"] = ["dot", "pip", "bea", "tomasz", "hank", "vic", "gus", "inez"]
        for cid in ("dot", "pip", "bea", "tomasz", "hank"):
            g(action="hire", crew=cid)
        assert g(action="confirm_crew")["view"]["phase"] == "plan"
        job["plan"] = bots.greedy_plan(g.module.C, tid, job["crew"])
        g(action="start_heist")
        g(action="skip")
        view = g(action="finish")["view"]
        assert view["phase"] == "payout" and view["payout"]["net"] >= view["target"]["consolation"]
