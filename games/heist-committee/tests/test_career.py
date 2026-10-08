import json

import bots
import engine
from tests.test_game_handle import to_plan


def play(g, plan_fn=None, crew=("dot", "pip", "bea", "tomasz", "hank"), target="pigeon_museum", skip=True):
    g(action="take_job", target=target)
    g(action="to_recruit")
    job = g.module.career.job
    job["offer"] = list(crew) + [c for c in job["offer"] if c not in crew][:3]
    for cid in crew:
        g(action="hire", crew=cid)
    g(action="confirm_crew")
    if plan_fn:
        job["plan"] = plan_fn(g.module.C, target, job["crew"])
    g(action="start_heist")
    g(action="skip")
    return g(action="finish")["view"]


def test_reputation_comes_from_how_the_job_went(g):
    view = play(g, bots.greedy_plan)
    p = view["payout"]
    assert p["rep_gained"] >= 1 and view["reputation"] == p["rep_gained"]
    g(action="back_to_board")
    target = g(action="open")["view"]["board"][0]["id"]
    empty = play(g, target=target)
    assert empty["payout"]["rep_gained"] == 1


def test_a_retry_only_earns_reputation_for_an_improvement(g):
    view = play(g)
    first = view["reputation"]
    g(action="retry")
    g(action="start_heist")
    g(action="skip")
    again = g(action="finish")["view"]
    assert again["reputation"] == first and again["payout"]["rep_gained"] == 0
    assert g.module.career.meta["retries"]["pigeon_museum"] == 1


def test_board_is_stable_until_a_job_is_taken_then_rotates(g):
    g.module.career.meta["reputation"] = 20
    first = [t["id"] for t in g(action="open")["view"]["board"]]
    assert first == [t["id"] for t in g(action="open")["view"]["board"]]
    assert len(first) == 3 and len(set(first)) == 3
    seen = set()
    for n in range(40):
        seen.update(g.module._board_targets_for(n))
    assert seen == set(g.module.C.target_order)


def test_board_is_the_same_for_the_same_career_seed(g):
    g.module.career.meta["reputation"] = 20
    a = [g.module._board_targets_for(n) for n in range(10)]
    g(action="new_career", seed=77)
    g.module.career.meta["reputation"] = 20
    assert a == [g.module._board_targets_for(n) for n in range(10)]


def test_locked_targets_cannot_be_taken(g):
    out = g(action="take_job", target="hilltop_observatory")
    assert out["view"]["phase"] == "board"
    ids = [t["id"] for t in out["view"]["board"]]
    assert "hilltop_observatory" not in ids and "glasshouse_dome" not in ids


def test_reputation_unlocks_targets_crew_and_gear(g):
    c = g.module.C
    assert "moth" not in g.module._unlocked_crew()
    g.module.career.meta["reputation"] = 7
    assert "moth" in g.module._unlocked_crew() and "hilltop_observatory" in g.module._unlocked_targets()
    g.module.career.meta["reputation"] = 0
    g(action="take_job", target="pigeon_museum")
    view = g(action="to_recruit")["view"]
    assert all(c.crew[card["id"]].get("min_reputation", 0) == 0 for card in view["offer"])
    locked = [x for x in view["gear"] if x["locked"]]
    assert locked
    note = g(action="gear", gear=locked[0]["id"])["view"]["note"]
    assert not any(x["equipped"] for x in g(action="open")["view"]["gear"] if x["id"] == locked[0]["id"]), note


def test_next_unlock_hint_on_the_board(g):
    view = g(action="open")["view"]
    assert view["next_unlock"]["at"] >= 1 and view["next_unlock"]["names"]


def test_payout_reports_new_unlocks(g):
    g.module.career.meta["reputation"] = 0
    view = play(g, bots.greedy_plan)
    assert view["payout"]["new_unlocks"], "the first good job should open something new"


def test_friends_are_made_by_working_clean_jobs_together(g):
    crew = ("dot", "pip", "bea", "tomasz", "hank")
    for _ in range(3):
        view = play(g, bots.greedy_plan, crew=crew)
        g(action="back_to_board")
        assert view["phase"] == "payout"
        if not view["payout"]["escaped"]:
            break
    scores = g.module.career.meta["pair_scores"]
    assert scores and max(scores.values()) >= 1


def test_enough_good_jobs_make_friends_and_the_engine_uses_it(g):
    g.module.career.meta["pair_scores"] = {"bea|dot": 2}
    crew = ["dot", "pip", "bea", "tomasz", "hank"]
    result = None
    for seed in range(40):
        plan = bots.greedy_plan(g.module.C, "pigeon_museum", crew)
        result = engine.simulate(g.module.C, "pigeon_museum", crew, plan, seed=seed)
        if result["outcome"]["escaped"]:
            break
    changes = g.module._update_relationships({"crew": crew}, result)
    assert {"a": "Bea", "b": "Dot", "kind": "friends"} in changes
    assert g.module.career.meta["relationships"]["bea|dot"] == "friends"
    assert g.module._relations()["bea|dot"] == "friends"


def test_clashes_lower_the_pair_score_towards_a_feud(g):
    crew = ["dot", "vic", "bea", "tomasz", "hank"]
    plan = engine.empty_plan(6)
    plan["lanes"][0][0] = "sweet_talk"
    plan["lanes"][1][0] = "sweet_talk"
    result = engine.simulate(g.module.C, "pigeon_museum", crew, plan, seed=1)
    for _ in range(3):
        changes = g.module._update_relationships({"crew": crew}, result)
    assert g.module.career.meta["pair_scores"]["dot|vic"] == -3
    assert {"a": "Dot", "b": "Vic", "kind": "feud"} in changes or g.module.career.meta["relationships"]["dot|vic"] == "feud"


def test_old_rivals_who_never_share_a_beat_can_become_friends(g):
    crew = ["dot", "vic", "bea", "tomasz", "hank"]
    plan = engine.empty_plan(6)
    plan["lanes"][0][0] = "sweet_talk"
    plan["lanes"][1][1] = "sweet_talk"
    plan["lanes"][2][5] = "drive"
    result = engine.simulate(g.module.C, "pigeon_museum", crew, plan, seed=1)
    result["outcome"]["escaped"] = True
    for _ in range(3):
        g.module._update_relationships({"crew": crew}, result)
    assert g.module.career.meta["relationships"]["dot|vic"] == "friends"


def test_the_hat_is_passed_when_the_purse_is_empty(g):
    g.module.career.cash = 10
    g(action="take_job", target="pigeon_museum")
    view = g(action="to_recruit")["view"]
    assert "passes the hat" in view["note"]
    cheapest = sum(sorted(c["fee"] for c in view["offer"])[:5])
    assert view["cash"] >= cheapest


def test_career_state_round_trips_and_survives_junk(g):
    g.module.career.meta.update({"reputation": 5, "jobs_clean": 2, "finished_targets": ["pigeon_museum"], "retries": {"pigeon_museum": 2},
                                 "relationships": {"bea|dot": "friends"}, "pair_scores": {"bea|dot": 3}})
    data = json.loads(json.dumps(g.module.get_state()))
    g(action="new_career", seed=9)
    g.module.load_state(data)
    assert g.module.career.meta["reputation"] == 5 and g.module.career.meta["relationships"] == {"bea|dot": "friends"}
    for junk in ({"meta": {"reputation": -5, "relationships": {"x|y": "friends", "dot|bea": "friends", "bea|dot": "enemies"}}},
                 {"meta": {"pair_scores": {"bea|dot": "lots", 5: 3}, "retries": {"nope": 4}, "finished_targets": "pigeon_museum"}},
                 {"meta": {"reputation": 10 ** 9}}):
        g.module.load_state(junk)
        meta = g.module.career.meta
        assert 0 <= meta["reputation"] <= 10 ** 4 and meta["relationships"] == {}
        assert g(action="open")["view"]["phase"] == "board"


def test_get_state_omits_default_career_fields(g):
    assert "meta" not in g.module.get_state()
    to_plan(g)
    assert "meta" not in g.module.get_state() or g.module.get_state()["meta"] == {}


def test_each_new_crew_member_is_well_formed(g):
    c = g.module.C
    assert len(c.crew) == 20 and len(c.targets) == 5 and len(c.complications) >= 55
    roles = {}
    for m in c.crew.values():
        roles.setdefault(m["role"], []).append(m["id"])
    assert all(len(v) >= 3 for v in roles.values())
    assert {t for m in c.crew.values() for t in (m["trait"], m["quirk"])} == set(c.traits)
