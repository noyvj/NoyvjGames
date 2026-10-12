"""The thin state layer: the view carries everything the page draws, plans are edited and flown through handle(), and the save round-trips."""

import json
import math

import game as game_module
import missions
import plan as planlib
import pytest


@pytest.fixture(autouse=True)
def fresh():
    game_module.handle(json.dumps({"action": "reset"}))
    yield
    game_module.handle(json.dumps({"action": "reset"}))


def do(**request):
    return json.loads(game_module.handle(json.dumps(request)))


def play_ref(mid):
    """Pick a mission, enter its reference plan through the same actions the page uses, and fly it."""
    do(action="pick", mission=mid)
    m = missions.BY_ID[mid]
    do(action="plan_clear")
    for b in m["ref"]["burns"]:
        do(action="burn_add", **b)
    for body, dv in m["ref"]["pass"].items():
        do(action="pass_set", body=body, dv=dv)
    return do(action="fly")


def test_the_first_view_is_the_first_mission_with_an_empty_plan_and_a_flight_to_draw():
    v = do(action="open")
    assert v["mission"]["id"] == "c1m1" and v["mission"]["name"] == "First Light"
    assert v["plan"]["burns"] == [] and v["flight"]["outcome"] == "miss"
    f = v["flight"]
    n = len(f["path"]["x"])
    assert n > 10 and all(len(f["path"][k]) == n for k in ("k", "t", "x", "y", "speed", "frame", "target_dist"))
    assert f["bodies"] and all(len(b["x"]) == n for b in f["bodies"]) and any(b["target"] for b in f["bodies"])
    assert f["words"] and "Moon" in " ".join(f["words"])


def test_the_view_is_plain_json_and_carries_the_chapters_atlas_and_about():
    v = do(action="open")
    assert json.loads(json.dumps(v)) == v
    assert [c["open"] for c in v["chapters"]] == [True, False, False]
    assert v["totals"]["missions"] == 22 and v["info"]["facts"] and v["atlas"]["columns"]


def test_adding_setting_and_removing_a_burn_changes_the_flight_and_counts_edits():
    m = missions.BY_ID["c1m1"]["ref"]["burns"][0]
    v = do(action="burn_add", **m)
    assert v["plan"]["burns"][0]["dv"] == m["dv"] and v["flight"]["outcome"] == "success" and v["added"] == 0
    assert v["tally"]["edits"] == 1 and v["can_undo"]
    v = do(action="burn_set", i=0, dv=0.5)
    assert v["flight"]["outcome"] == "miss" and v["plan"]["burns"][0]["dv"] == 0.5
    v = do(action="burn_del", i=0)
    assert v["plan"]["burns"] == [] and v["tally"]["edits"] == 3


def test_burns_are_kept_in_time_order_and_added_reports_where_it_went():
    do(action="burn_add", t=500, head=0, dv=0.1)
    v = do(action="burn_add", t=100, head=0, dv=0.2)
    assert [b["t"] for b in v["plan"]["burns"]] == [100, 500] and v["added"] == 0


def test_bad_requests_are_answered_not_raised():
    for bad in ({"action": "burn_add", "t": "x", "dv": 1}, {"action": "burn_add", "t": 5, "dv": -1}, {"action": "burn_set", "i": 9, "dv": 1},
                {"action": "burn_del", "i": -1}, {"action": "pass_set", "body": "pluto", "dv": 1}, {"action": "nonsense"}, {"action": "pick", "mission": "zzz"}):
        v = do(**bad)
        assert "error" in v or v["ok"] is False
    assert json.loads(game_module.handle("not json"))["error"] == "bad request"


def test_a_plan_holds_at_most_eight_burns():
    for i in range(10):
        v = do(action="burn_add", t=i * 10, head=0, dv=0.01)
    assert len(v["plan"]["burns"]) == 8 and v["ok"] is False


def test_undo_and_redo_walk_through_plan_changes_and_stop_at_the_ends():
    do(action="burn_add", t=10, head=0, dv=0.3)
    do(action="burn_add", t=20, head=0, dv=0.4)
    v = do(action="undo")
    assert len(v["plan"]["burns"]) == 1 and v["can_redo"]
    v = do(action="redo")
    assert len(v["plan"]["burns"]) == 2
    do(action="undo"); do(action="undo")
    v = do(action="undo")
    assert v["ok"] is False


def test_flying_a_plan_that_reaches_the_goal_records_the_mission_and_the_fuel():
    v = play_ref("c1m1")
    assert v["just"]["first"] and "Mission done" in v["message"]
    assert v["totals"]["done"] == 1 and v["totals"]["flights"] == 1
    best = missions.BY_ID["c1m1"]["cost"]
    assert abs(v["chapters"][0]["missions"][0]["fuel"] - best) < 1e-6
    assert v["cards"] and v["cards"][0]["id"] == "moon"
    assert v["totals"]["saved"] > 0


def test_a_flight_that_misses_counts_as_a_flight_but_records_nothing():
    do(action="burn_add", t=10, head=0, dv=0.2)
    v = do(action="fly")
    assert v["totals"]["flights"] == 1 and v["totals"]["done"] == 0 and v["ok"] is False and v["just"] is None


def test_flying_with_no_burns_is_refused_and_not_counted():
    v = do(action="fly")
    assert v["ok"] is False and v["totals"]["flights"] == 0


def test_a_cheaper_plan_improves_the_best_fuel_and_a_dearer_one_does_not():
    play_ref("c1m1")
    v = do(action="burn_set", i=0, dv=missions.BY_ID["c1m1"]["cost"] + 0.01)
    do(action="fly")
    state = game_module.get_state()
    assert abs(state["reached"]["c1m1"]["fuel"] - missions.BY_ID["c1m1"]["cost"]) < 1e-6
    assert state["reached"]["c1m1"]["flights"] >= 1


def test_a_plan_over_the_budget_is_not_recorded_and_says_so():
    do(action="pick", mission="c1m1")
    m = missions.BY_ID["c1m1"]
    b = dict(m["ref"]["burns"][0])
    do(action="burn_add", **b)
    do(action="pass_set", body="moon", dv=-0.5)
    v = do(action="fly")
    assert v["flight"]["outcome"] == "over_budget" and v["totals"]["done"] == 0 and "budget" in v["flight"]["verdict"]


def test_chapter_two_opens_after_five_missions_of_chapter_one_in_any_order():
    for mid in ("c1m7", "c1m3", "c1m1", "c1m5"):
        play_ref(mid)
    v = do(action="pick", mission="c2m1")
    assert v["ok"] is False and v["mission"]["id"] != "c2m1"
    play_ref("c1m2")
    v = do(action="pick", mission="c2m1")
    assert v["mission"]["id"] == "c2m1" and [c["open"] for c in v["chapters"]] == [True, True, False]


def test_next_goes_to_the_next_open_mission_not_done_and_wraps():
    play_ref("c1m1")
    v = do(action="next")
    assert v["mission"]["id"] == "c1m2"
    do(action="pick", mission="c1m7")
    assert do(action="next")["mission"]["id"] == "c1m2"


def test_every_mission_can_be_played_through_to_the_end_by_its_reference_plan():
    for chapter in range(1, 4):
        pass
    order = missions.ORDER
    done = 0
    for mid in order:
        i = missions.BY_ID[mid]["chapter"] - 1
        if not missions.mission_open(game_module.game.reached, mid):
            continue
        v = play_ref(mid)
        assert v["just"] is not None, mid
        done += 1
    # chapters open as five are done, so everything is reachable in order
    for mid in order:
        if mid not in game_module.game.reached:
            v = play_ref(mid)
            assert v["just"] is not None, mid
    assert len(game_module.game.reached) == 22


def test_the_time_slider_counts_but_only_in_the_tally():
    v = do(action="scrub", n=7)
    assert v["tally"]["scrubs"] == 7 and v["totals"]["scrubs"] == 7
    assert do(action="scrub", n=10 ** 9)["tally"]["scrubs"] == 8


def test_the_view_never_gives_the_player_the_reference_plan():
    v = do(action="open")
    text = json.dumps(v)
    ref = missions.BY_ID["c1m1"]["ref"]["burns"][0]
    assert "\"ref\"" not in text and "alt" not in v["mission"]
    assert "reference" not in text.lower()


def test_reset_starts_over():
    play_ref("c1m1")
    v = do(action="reset")
    assert v["totals"]["done"] == 0 and v["plan"]["burns"] == [] and game_module.get_state() == {"schema": 1}


def test_results_speak_in_plain_words_about_misses_crashes_and_captures():
    do(action="pick", mission="c1m3")
    v = do(action="burn_add", t=60, head=0, dv=1.04)
    text = " ".join(v["flight"]["details"]) + v["flight"]["verdict"]
    assert "sphere of influence" in text and "km" in text
    v = do(action="pass_set", body="moon", dv=-0.16)
    assert "orbit" in " ".join(v["flight"]["details"]) or "captured" in " ".join(v["flight"]["details"])
    do(action="pick", mission="c1m1")
    do(action="plan_clear")
    v = do(action="burn_add", t=0, head=180, dv=2.5)
    assert v["flight"]["outcome"] == "crash" and "hit" in v["flight"]["verdict"]
