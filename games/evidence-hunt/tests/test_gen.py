"""Practice houses: a code is a pure function of (difficulty, seed), every generated house is sound and fair by the same solver as the
authored cases, and practice never touches an authored seal."""

import json

import casework as cw
import gen
import progress
import solver
from tests.helpers import call, solve_with_hints


def fresh():
    import game
    game.game.__init__()
    return call(action="open")


def test_codes_round_trip_and_bad_codes_are_refused():
    assert gen.code_of(3, 12345) == "EH3-9IX" and gen.case_id(3, 12345) == "practice-3-9ix"
    for text in ("EH3-9IX", " eh3-9ix ", "practice-3-9ix"):
        assert gen.parse(text) == (3, 12345)
    for text in ("", "EH9-1", "EH3-", "EH3-!!", "XX3-1", "EH3-ZZZZZZZ", None, 5, "EH0-1"):
        assert gen.parse(text) is None
    assert gen.parse("EH3-ZZZZZZ") is None or gen.parse("EH3-ZZZZZZ")[1] < gen.SEED_LIMIT
    assert gen.make(9, 1) is None and gen.make(3, -1) is None and gen.make(3, gen.SEED_LIMIT) is None and gen.make(3, "x") is None


def test_the_same_code_always_makes_the_same_house():
    for d in gen.DIFFICULTIES:
        a = gen.make(d, 4242 + d)
        gen._CACHE.clear()
        b = gen.make(d, 4242 + d)
        assert a == b and a["code"] == gen.code_of(d, 4242 + d) and a["id"] == gen.case_id(d, 4242 + d)


def test_different_codes_make_different_houses():
    houses_seen = {json.dumps(gen.make(3, s), sort_keys=True, default=str) for s in range(1, 30)}
    assert len(houses_seen) == 29
    truths = {gen.make(3, s)["truth"] for s in range(1, 60)}
    assert len(truths) >= 9
    assert len({gen.make(3, s)["layout"] for s in range(1, 60)}) >= 4


def test_every_generated_house_is_sound_fair_and_finished_clean_by_the_careful_plan():
    for d in gen.DIFFICULTIES:
        spec = gen.SPEC[d]
        for seed in range(1, 31):
            data = gen.make(d, seed * 101)
            assert data is not None, (d, seed)
            assert solver.validate(data) == [], (d, seed, solver.validate(data))
            case = cw.Case(data)
            info = solver.analyse(case)
            assert spec["min_kit"] <= info["min_kit"] <= case.kit_size and max(len(c) for c in info["cands"]) >= 2
            assert case.practice and len(data["pool"]) >= spec["pool"][0] and data["kit"] == spec["kit"]
            st = case.new_state()
            for _ in range(250):
                act = solver.next_action(case, st)
                assert act is not None, (d, seed)
                st, _info = case.apply(st, act)
                assert st is not None
                if act[0] == "accuse":
                    break
            assert st[cw.SOLVED] and case.total_cost(st) == 0, (d, seed)


def test_each_size_means_what_it_says():
    assert all(len(gen.make(1, s)["truth"]) == 1 and not gen.make(1, s)["features"] and not gen.make(1, s)["keepsake"] for s in range(1, 20))
    assert all(len(gen.make(4, s)["truth"]) == 2 for s in range(1, 20))
    assert any(len(gen.make(5, s)["truth"]) == 1 for s in range(1, 30)) and any(len(gen.make(5, s)["truth"]) == 2 for s in range(1, 30))
    assert any(gen.make(3, s)["keepsake"] for s in range(1, 30)) and any(gen.make(5, s)["keepsake"] for s in range(1, 40))
    assert all(len(gen.make(5, s)["features"]) == 4 for s in range(1, 20))
    assert all(gen.NAMES[d] for d in gen.DIFFICULTIES)


def test_next_seed_is_repeatable_and_walks_on():
    seeds = [gen.next_seed(i, 3) for i in range(20)]
    assert len(set(seeds)) == 20 and seeds == [gen.next_seed(i, 3) for i in range(20)] and all(0 <= s < gen.SEED_LIMIT for s in seeds)
    assert gen.next_seed(0, 3) != gen.next_seed(0, 4)


def test_opening_a_practice_house_by_size_and_by_code_through_the_handle():
    v = fresh()
    assert v["practice"]["levels"][0]["difficulty"] == 1 and v["practice"]["done"] == 0
    v = call(action="practice", difficulty=2)
    assert v["case"]["practice"] and v["case"]["chapter"] == "Practice" and v["case"]["code"].startswith("EH2-") and v["case"]["number"] == 0
    code = v["case"]["code"]
    v = call(action="practice", difficulty=2)
    assert v["case"]["code"] != code, "the next house of the same size is a new one"
    v = call(action="practice", code=" " + code.lower())
    assert v["case"]["code"] == code and v["ok"]
    for bad in ({"action": "practice"}, {"action": "practice", "difficulty": 9}, {"action": "practice", "difficulty": "x"}, {"action": "practice", "code": "EH9-1"}, {"action": "practice", "code": "nonsense"}):
        assert call(**bad)["ok"] is False, bad
    assert call(action="open")["case"]["code"] == code, "a refused code changes nothing"


def test_practice_never_touches_an_authored_seal_but_counts_everywhere_else():
    v = fresh()
    v = call(action="practice", difficulty=1)
    code = v["case"]["code"]
    v = solve_with_hints()
    assert v["result"]["again"]["difficulty"] == 1 and v["result"]["grade_name"] == "Clean" and v["result"]["new_best"] is False
    assert v["totals"]["done"] == 0 and v["tally"]["sandbox"] == 1 and v["practice"]["done"] == 1 and v["guide"]["found"] >= 2
    state = json.loads(json.dumps(__import__("game").get_state()))
    assert state["sb"]["done"] == [code] and "best" not in state and "met" in state
    assert v["tally"]["readings"] >= 1 and v["tally"]["rooms"] >= 1
    v = call(action="restore")
    v = solve_with_hints()
    assert call(action="open")["practice"]["done"] == 1, "the same code is not counted twice"
    assert call(action="next")["case"]["id"] == "1-1"


def test_a_practice_house_in_progress_is_saved_and_loaded_with_its_actions():
    import game
    fresh()
    v = call(action="practice", difficulty=3)
    code = v["case"]["code"]
    call(action="go", room=0)
    call(action="go", room=1)
    state = json.loads(json.dumps(game.get_state()))
    assert state["cur"].startswith("practice-3-") and state["sb"]["n"] == {"3": 1}
    assert list(state["run"].values())[0] == ["go:0", "go:1"]
    before = game.game.view()
    game.game.__init__()
    game.load_state(state)
    after = game.game.view()
    assert after["case"]["code"] == code and before["house"] == after["house"]


def test_forged_practice_data_in_a_save_is_dropped():
    import game
    for data in ({"cur": "practice-9-1"}, {"cur": "practice-3-zzzzzzzz"}, {"sb": {"n": {"3": -4, "x": 5}, "done": ["EH3-ZZ", "nonsense", "EH3-9IX", "EH3-9IX", 7]}},
                 {"run": {"practice-3-9ix": ["go:99"], "practice-7-1": ["go:0"]}}):
        game.game.__init__()
        game.load_state(data)
        v = game.game.view()
        assert v["case"]["id"] in progress.DATA or v["case"]["practice"]
        assert game.game.runs == {} or all(gen.is_practice_id(k) for k in game.game.runs)
    game.game.__init__()
    game.load_state({"sb": {"n": {"3": -4, "x": 5, "2": 3}, "done": ["EH3-9IX", "EH3-9IX", "nonsense", "eh3-1"]}})
    assert game.game.sbn == {2: 3} and game.game.sbdone == ["EH3-9IX"]
    game.game.__init__()
    game.load_state({"cur": "practice-3-9ix"})
    assert game.game.cur == "practice-3-9ix"


def test_only_a_few_unfinished_practice_houses_are_kept():
    import game
    fresh()
    for d in (1, 2, 3, 4, 5):
        call(action="practice", difficulty=d)
        call(action="go", room=0)
    call(action="pick", case="1-1")
    assert len([k for k in game.game.runs if k not in progress.DATA]) == 3
