import copy

from geom import dist
from progress import hazards_on_the_line, record_outcome
from sim import cruise_speed, estimate, sail, score
from solver import route, shoot
from state import FLAGS, clean_meta, clean_record, clean_run, merge_meta, meta_to_dict, new_meta, new_record, new_run, run_to_dict
from tests.helpers import whole_sea_current


def rec(**kw):
    r = new_record()
    r.update(kw)
    return r


def test_records_are_cleaned_field_by_field():
    assert clean_record("junk") == new_record()
    r = clean_record({"best_error_nm": -4, "stars": 9, "attempts": "x", "discovered": ["a", "a", 3, "zz"], "par_seen": 1, "trusted": True},
                     hazard_ids={"a"})
    assert r == rec(best_error_nm=0.0, stars=3, attempts=0, discovered=["a"], trusted=True)
    assert clean_record({"best_error_nm": float("inf")})["best_error_nm"] is None


def test_meta_drops_unknown_charts_and_flags_and_keeps_known_ones():
    m = clean_meta({"charts": {"demo": {"stars": 2}, "ghost": {"stars": 3}, 5: {}}, "flags": ["landfall", "nope", "aground"],
                    "practice_seeds_played": -3, "best": {"smallest_final_error_nm": "x", "longest_route_nm": 40}}, {"demo": set()})
    assert list(m["charts"]) == ["demo"] and m["flags"] == ["landfall", "aground"]
    assert m["practice_seeds_played"] == 0 and m["best"] == {"smallest_final_error_nm": None, "longest_route_nm": 40.0}


def test_merge_is_commutative_and_idempotent():
    a = new_meta()
    a["charts"]["demo"] = rec(stars=1, attempts=3, best_error_nm=2.0, discovered=["x"])
    a["flags"] = ["landfall"]
    b = new_meta()
    b["charts"]["demo"] = rec(stars=3, attempts=1, best_error_nm=0.5, par_seen=True)
    b["charts"]["other"] = rec(stars=2)
    b["flags"] = ["aground"]
    b["practice_seeds_played"] = 4
    ab, ba = merge_meta(a, b), merge_meta(b, a)
    assert ab == ba and merge_meta(ab, ab) == ab
    assert ab["charts"]["demo"] == rec(stars=3, attempts=3, best_error_nm=0.5, discovered=["x"], par_seen=True)
    assert ab["flags"] == ["landfall", "aground"] and ab["practice_seeds_played"] == 4


def test_stored_dicts_leave_out_defaults():
    m = new_meta()
    assert meta_to_dict(m) == {}
    m["charts"]["demo"] = rec(stars=2)
    assert meta_to_dict(m) == {"charts": {"demo": {"stars": 2}}}
    run = new_run("demo")
    assert run_to_dict(run) == {"chart_id": "demo", "legs": []}


def test_a_run_keeps_known_hazards_only_in_the_reveal(chart):
    data = {"chart_id": "demo", "legs": [{"heading": 1, "speed": 5, "hours": 1}], "known": ["a", 3]}
    get = lambda cid: {"speeds": [3.0, 7.0], "id": cid}                    # noqa: E731
    assert "known" not in clean_run(data, get)
    assert clean_run(dict(data, phase="reveal"), get)["known"] == ["a"]
    assert clean_run(dict(data, phase="reveal", legs=[]), get)["phase"] == "plan"


# --- progress ---------------------------------------------------------------------------------------
def outcome(chart, legs, meta=None, helpers=()):
    meta = meta or new_meta()
    run = new_run(chart["id"])
    run["legs"] = legs
    run["helpers"] = list(helpers)
    res = sail(chart, legs)
    sc = score(chart, legs, res, used_helpers=bool(helpers))
    return meta, record_outcome(meta, chart, run, res, sc), sc


def test_a_landfall_is_recorded_with_its_error_and_route(chart):
    chart["id"] = "p1"
    chart["dest"] = [10.0, 2.0]
    legs = [{"heading": 90, "speed": 4.0, "hours": 2.0}]
    meta, new, sc = outcome(chart, legs)
    assert "landfall" in new and sc["stars"] == 3
    assert meta["charts"]["p1"]["stars"] == 3 and meta["charts"]["p1"]["attempts"] == 1 and meta["charts"]["p1"]["best_error_nm"] == 0.0
    assert meta["charts"]["p1"]["trusted"] and "trusted" in new and "dead_on" in new
    assert meta["best"] == {"smallest_final_error_nm": 0.0, "longest_route_nm": 8.0}
    _meta, again, _sc = outcome(chart, legs, meta=meta)
    assert again == [] and meta["charts"]["p1"]["attempts"] == 2


def test_using_a_helper_withholds_trusted(chart):
    chart["id"] = "p2"
    chart["dest"] = [10.0, 2.0]
    meta, new, _ = outcome(chart, [{"heading": 90, "speed": 4.0, "hours": 2.0}], helpers=["naive"])
    assert "trusted" not in new and not meta["charts"]["p2"]["trusted"]


def test_aground_is_recorded_and_unmarked_dangers_are_discovered(chart):
    chart["id"] = "p3"
    chart["hazards"] = [{"id": "u", "kind": "rock", "name": "U", "x": 6.0, "y": 2.0, "r": 0.5, "charted": False}]
    meta, new, sc = outcome(chart, [{"heading": 90, "speed": 4.0, "hours": 2.0}])
    assert "aground" in new and "landfall" not in new and sc["stars"] == 0
    assert meta["charts"]["p3"]["discovered"] == ["u"]


def test_set_and_drift_needs_a_current_a_big_naive_miss_and_beating_it_by_half(chart):
    chart["id"] = "p4"
    chart["currents"] = [whole_sea_current(0, 2.0)]
    chart["dest"] = [10.0, 2.0]
    chart["speeds"] = [4.0, 4.0]
    legs = [{"heading": 90, "speed": 4.0, "hours": 2.0}]
    _m, new, sc = outcome(chart, legs)
    assert "set_and_drift" not in new and not sc["arrived"]
    solved, _end = route(chart, [chart["start"], chart["dest"]], model="true")
    _m, new, sc = outcome(chart, solved)
    assert sc["arrived"] and sc["beat_naive_pct"] >= 50 and "set_and_drift" in new


def test_around_the_rocks_counts_hazards_on_the_direct_line(chart):
    chart["id"] = "p5"
    chart["dest"] = [18.0, 2.0]
    chart["hazards"] = [{"id": "h%d" % i, "kind": "rock", "name": "R", "x": 5.0 + 4 * i, "y": 2.0, "r": 0.4, "charted": True} for i in range(3)]
    assert hazards_on_the_line(chart) == 3
    solved, _ = route(chart, [chart["start"], (4.0, 4.0), (16.0, 4.0), chart["dest"]], model="true")
    _m, new, sc = outcome(chart, solved)
    assert sc["arrived"] and "around_rocks" in new


def test_long_way_round_uses_the_route_length(chart):
    chart["id"] = "p6"
    chart["size"] = 80
    chart["start"], chart["dest"] = [2.0, 2.0], [74.0, 2.0]
    legs = [{"heading": 90, "speed": 6.0, "hours": 6.0}] * 2
    _m, new, _sc = outcome(chart, legs)
    assert "long_way" in new and "landfall" in new


def test_every_flag_is_known_to_the_state_module():
    assert len(FLAGS) == len(set(FLAGS))


# --- solver -----------------------------------------------------------------------------------------
def test_shooting_lands_close_under_the_model_it_was_given(chart):
    chart["currents"] = [whole_sea_current(45, 1.5)]
    chart["wind"] = {"from": 270, "range": [12, 12], "true": 12}
    chart["compass"] = {"range": [4, 4], "true": 4}
    for target in ((15.0, 15.0), (3.0, 18.0), (18.0, 3.0)):
        leg = shoot(chart, chart["start"], target, model="true")
        end = sail(chart, [leg])["end"]
        assert dist(end, target) < 1.0, (target, leg, end)


def test_shooting_through_a_tide_uses_the_clock(chart):
    chart["currents"] = [whole_sea_current(90, 2.0, tide={"period": 12.0, "phase": 0.0})]
    a = shoot(chart, (2.0, 2.0), (16.0, 2.0), model="true", t_start=0.0)
    b = shoot(chart, (2.0, 2.0), (16.0, 2.0), model="true", t_start=6.0)
    assert a["hours"] < b["hours"]                      # fair stream at hour 0, slack to foul later


def test_a_route_through_waypoints_does_not_pile_up_error(chart):
    chart["currents"] = [whole_sea_current(120, 1.3)]
    legs, end = route(chart, [chart["start"], (5.0, 15.0), (14.0, 15.0), chart["dest"]], model="true")
    assert dist(end, chart["dest"]) < 1.0 and 1 <= len(legs) <= 3
    assert dist(sail(chart, legs)["end"], chart["dest"]) < 1.0


def test_shooting_to_the_start_itself_is_a_no_op(chart):
    assert shoot(chart, (3, 3), (3, 3)) is None
    assert cruise_speed(chart) == 5.5


def test_a_plot_with_the_whole_forecast_equals_a_charted_sail(chart):
    chart["currents"] = [whole_sea_current(45, 1.0)]
    legs = [{"heading": 10, "speed": 5.0, "hours": 3.0}]
    assert estimate(chart, legs)[-1][1:3] == sail(chart, legs, model="charted")["end"]


def test_deepcopy_charts_are_independent(chart):
    other = copy.deepcopy(chart)
    other["hazards"].append({})
    assert chart["hazards"] == []
