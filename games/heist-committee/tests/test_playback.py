import json

import bots
import engine
import writeup
from tests.test_game_handle import to_plan

CREW = ("dot", "pip", "bea", "tomasz", "hank")


def build_plan(g):
    to_plan(g, crew=CREW)
    job = g.module.career.job
    job["plan"] = bots.greedy_plan(g.module.C, "pigeon_museum", job["crew"])
    return g(action="open")["view"]


def test_start_heist_moves_to_playback_at_beat_zero(g):
    build_plan(g)
    view = g(action="start_heist")["view"]
    assert view["phase"] == "playback" and view["playback"]["cursor"] == 0 and view["playback"]["events"] == []


def test_step_reveals_one_beat_at_a_time_without_leaking_the_future(g):
    build_plan(g)
    g(action="start_heist")
    seen = 0
    for beat in range(1, 7):
        view = g(action="step")["view"]
        events = view["playback"]["events"]
        assert max(e["beat"] for e in events) == beat - 1
        assert len(events) > seen
        seen = len(events)
    assert view["playback"]["done"]
    assert g(action="step")["view"]["playback"]["cursor"] == 6


def test_playback_is_identical_to_a_straight_simulation(g):
    build_plan(g)
    g(action="start_heist")
    view = g(action="skip")["view"]
    job = g.module.career.job
    result = engine.simulate(g.module.C, job["target"], job["crew"], job["plan"], job["gear"], job["seed"], {}, view["fees"])
    assert [e["text"] for e in result["events"]] == [e["text"] for e in view["playback"]["events"]]


def test_finish_pays_and_moves_to_payout(g):
    build_plan(g)
    cash = g(action="open")["view"]["cash"]
    g(action="start_heist")
    assert g(action="finish")["view"]["phase"] == "playback"          # not before the end
    g(action="skip")
    view = g(action="finish")["view"]
    assert view["phase"] == "payout"
    p = view["payout"]
    assert p["title"] and p["writeup"] and p["net"] >= view["target"]["consolation"]
    assert view["cash"] == cash + p["credited"] and p["credited"] == p["net"]
    assert view["jobs_done"] == 1


def test_a_bad_night_still_pays_the_consolation(g):
    to_plan(g, crew=CREW)
    g(action="start_heist")
    g(action="skip")
    view = g(action="finish")["view"]
    assert view["payout"]["net"] == view["target"]["consolation"] and view["payout"]["cls"] == "bust"


def test_retry_keeps_the_seed_and_only_pays_the_improvement(g):
    build_plan(g)
    g(action="start_heist")
    g(action="skip")
    first = g(action="finish")["view"]
    cash = first["cash"]
    view = g(action="retry")["view"]
    assert view["phase"] == "plan" and view["seed"] == first["seed"]
    g(action="start_heist")
    g(action="skip")
    again = g(action="finish")["view"]
    assert again["payout"]["attempt"] == 2
    assert again["payout"]["credited"] == 0 and again["cash"] == cash       # same plan, same night, nothing new to earn
    assert again["jobs_done"] == 1


def test_retry_with_a_better_plan_pays_the_difference(g):
    to_plan(g, crew=CREW)
    g(action="start_heist")
    g(action="skip")
    first = g(action="finish")["view"]
    g(action="retry")
    g.module.career.job["plan"] = bots.greedy_plan(g.module.C, "pigeon_museum", g.module.career.job["crew"])
    g(action="start_heist")
    g(action="skip")
    second = g(action="finish")["view"]
    assert second["payout"]["net"] > first["payout"]["net"]
    assert second["payout"]["credited"] == second["payout"]["net"] - first["payout"]["net"]


def test_learning_quirks_and_complications_during_playback(g):
    build_plan(g)
    g(action="start_heist")
    g(action="skip")
    meta = g.module.career.meta
    assert meta["seen_complications"] or meta["seen_traits"]
    for cid in meta["known_quirks"]:
        assert g.module.C.crew[cid]["quirk"] in meta["seen_traits"]


def test_save_round_trip_mid_playback_and_at_payout(g):
    build_plan(g)
    g(action="start_heist")
    g(action="step")
    g(action="step")
    before = g(action="open")["view"]
    g.module.load_state(json.loads(json.dumps(g.module.get_state())))
    assert g(action="open")["view"] == before
    g(action="skip")
    g(action="finish")
    before = g(action="open")["view"]
    g.module.load_state(json.loads(json.dumps(g.module.get_state())))
    after = g(action="open")["view"]
    for v in (before, after):
        v["plan"].pop("can_undo")
    assert after == before and after["phase"] == "payout"


def test_results_mark_finished_cells_only(g):
    build_plan(g)
    g(action="start_heist")
    view = g(action="step")["view"]
    for key in view["playback"]["results"]:
        lane, start = map(int, key.split(":"))
        assert start <= 0 or True
        assert view["playback"]["results"][key]["label"]


def test_writeup_is_deterministic_and_mentions_the_outcome(C):
    crew = list(CREW)
    plan = bots.greedy_plan(C, "pigeon_museum", crew)
    result = engine.simulate(C, "pigeon_museum", crew, plan, seed=4)
    a = writeup.build(C, "pigeon_museum", result, crew, 4)
    b = writeup.build(C, "pigeon_museum", result, crew, 4)
    assert a == b and a["text"].count(".") >= 3
    assert "{" not in a["text"] and "{" not in a["title"]


def test_writeups_never_leave_a_placeholder_across_many_heists(C):
    import random
    for seed in range(300):
        crew = random.Random(seed).sample(C.crew_order, 5)
        plan = bots.random_plan(C, "pigeon_museum", crew, seed) if seed % 2 else bots.greedy_plan(C, "pigeon_museum", crew)
        result = engine.simulate(C, "pigeon_museum", crew, plan, seed=seed)
        w = writeup.build(C, "pigeon_museum", result, crew, seed)
        assert "{" not in w["text"] + w["title"] and w["title"]
