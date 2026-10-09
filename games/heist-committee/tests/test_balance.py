"""Bot playtests: a plan-by-requirement bot and a dice bot play 1,000 jobs on every target. The bands catch a broken
balance before a human does: a thoughtful plan should usually work, a random one almost never, and a bad night
still pays the consolation."""

import random

import bots
import engine


def run(C, tid, jobs, planner, crew_seed=0):
    esc = clean = 0
    nets, links, absorbed, comps = [], 0, 0, 0
    for seed in range(jobs):
        crew = random.Random(seed + crew_seed).sample(C.crew_order, 5)
        out = engine.simulate(C, tid, crew, planner(C, tid, crew, seed), seed=seed)["outcome"]
        esc += out["escaped"]
        clean += out["escaped"] and not out["alarm"]
        nets.append(out["net"])
        links += out["chain_links"] >= 3
        absorbed += out["absorbed"]
        comps += len(out["complications"])
        assert out["net"] >= C.targets[tid]["consolation"]
    return {"esc": esc / jobs, "clean": clean / jobs, "mean": sum(nets) / jobs, "chain": links / jobs,
            "absorbed": absorbed / jobs, "comps": comps / jobs}


def greedy(C, tid, crew, seed):
    return bots.greedy_plan(C, tid, crew)


def dice(C, tid, crew, seed):
    return bots.random_plan(C, tid, crew, seed)


def test_a_thoughtful_plan_usually_works_and_a_random_one_almost_never_does(C):
    for tid in C.target_order:
        smart = run(C, tid, 1000, greedy)
        silly = run(C, tid, 1000, dice)
        assert 0.45 <= smart["esc"] <= 0.92, (tid, smart)
        assert smart["clean"] >= 0.35, (tid, smart)
        assert 200 <= smart["mean"] <= 700, (tid, smart)
        assert silly["esc"] <= 0.05, (tid, silly)
        assert silly["mean"] < 0.4 * smart["mean"], (tid, silly, smart)


def test_trouble_is_frequent_but_chains_are_the_exception(C):
    for tid in C.target_order:
        r = run(C, tid, 400, greedy)
        assert 3.0 <= r["comps"] <= 8.0, (tid, r)
        assert 0.03 <= r["chain"] <= 0.6, (tid, r)
        assert r["absorbed"] >= 1.0, (tid, r)


def test_standby_pays_for_itself(C):
    for tid in C.target_order:
        with_standby = no_standby = 0
        for seed in range(500):
            crew = random.Random(seed).sample(C.crew_order, 5)
            with_standby += engine.simulate(C, tid, crew, bots.greedy_plan(C, tid, crew), seed=seed)["outcome"]["escaped"]
            no_standby += engine.simulate(C, tid, crew, bots.greedy_plan(C, tid, crew, standby=False), seed=seed)["outcome"]["escaped"]
        assert with_standby > no_standby * 1.1, (tid, with_standby, no_standby)


def test_scouting_informed_cover_is_not_worse_than_guessing(C):
    for tid in C.target_order:
        guess = scouted = 0
        for seed in range(500):
            crew = random.Random(seed).sample(C.crew_order, 5)
            guess += engine.simulate(C, tid, crew, bots.greedy_plan(C, tid, crew), seed=seed)["outcome"]["escaped"]
            plan = bots.greedy_plan(C, tid, crew, kinds=bots.scouted_kinds(C, tid))
            scouted += engine.simulate(C, tid, crew, plan, seed=seed)["outcome"]["escaped"]
        assert scouted >= guess * 0.85, (tid, scouted, guess)


def test_a_second_attempt_on_the_same_night_is_the_same_night(C):
    crew = ["dot", "pip", "bea", "tomasz", "hank"]
    plan = bots.greedy_plan(C, "pigeon_museum", crew)
    a = engine.simulate(C, "pigeon_museum", crew, plan, seed=11)
    b = engine.simulate(C, "pigeon_museum", crew, plan, seed=11)
    assert a == b


def test_improving_the_plan_improves_the_outcome_on_the_same_seed(C):
    """Retry means something: with the same seed, adding the missing pieces of a plan beats leaving them out."""
    better = worse = 0
    for seed in range(300):
        crew = random.Random(seed).sample(C.crew_order, 5)
        good = bots.greedy_plan(C, "lucky_barge", crew)
        bad = bots.greedy_plan(C, "lucky_barge", crew, standby=False)
        g = engine.simulate(C, "lucky_barge", crew, good, seed=seed)["outcome"]["net"]
        b = engine.simulate(C, "lucky_barge", crew, bad, seed=seed)["outcome"]["net"]
        better += g > b
        worse += g < b
    assert better > worse * 1.5


def test_no_target_is_trivial_or_impossible_for_an_ordinary_crew(C):
    for tid in C.target_order:
        r = run(C, tid, 200, greedy, crew_seed=999)
        assert 0.3 <= r["esc"] <= 0.95, (tid, r)


def test_the_cheapest_crew_can_still_win_sometimes(C):
    cheap = sorted(C.crew_order, key=lambda c: C.crew[c]["fee"])
    by_role = {}
    for cid in cheap:
        by_role.setdefault(C.crew[cid]["role"], cid)
    crew = list(by_role.values())
    wins = sum(engine.simulate(C, "pigeon_museum", crew, bots.greedy_plan(C, "pigeon_museum", crew), seed=s)["outcome"]["escaped"]
               for s in range(200))
    assert wins >= 40
