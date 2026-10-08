import json

import fixes
from geom import bearing, dist, unit


def unlock_all(g):
    for cid in g.charts.ORDER:
        if g.charts.CHAPTER_OF[cid] != "fixes":
            g.meta["charts"][cid] = dict(g.state.new_record(), stars=1)


def watch(g, cid="fix-01"):
    unlock_all(g)
    g.call("start", chart_id=cid)
    return g.call("open")


def test_chapter_three_opens_in_watch_mode_and_other_charts_in_full_plan(g):
    v = watch(g)
    assert v["chart"]["mode"] == "watch" and v["chart"]["modes"] == ["watch", "plan"] and v["watch"]["sailed"] == 0
    assert g.call("start", chart_id="open-01")["chart"]["mode"] == "plan"


def test_the_mode_can_be_changed_only_before_anything_is_sailed(g):
    watch(g)
    assert g.call("set_mode", mode="plan")["chart"]["mode"] == "plan"
    assert g.call("set_mode", mode="watch")["chart"]["mode"] == "watch"
    assert g.call("set_mode", mode="nonsense")["chart"]["mode"] == "watch"
    g.call("add_leg")
    g.call("sail")
    assert g.call("set_mode", mode="plan")["chart"]["mode"] == "watch"
    g.call("start", chart_id="open-01")
    assert g.call("set_mode", mode="watch")["chart"]["mode"] == "plan"


def test_a_watch_sails_one_leg_and_returns_to_planning(g):
    watch(g)
    g.call("add_leg")
    assert len(g.call("add_leg")["legs"]) == 1                        # one pending watch at a time
    v = g.call("sail")
    assert v["phase"] == "plan" and v["sailed"] == 1 and v["watch"]["sailed"] == 1 and len(v["legs"]) == 1
    assert v["watch"]["believed"] is not None and "dr-believed-shape" in v["svg"]
    v = g.call("add_leg")
    assert len(v["legs"]) == 2 and v["sailed"] == 1
    assert "dr-true-track" not in v["svg"] and "reveal" not in v


def test_sailed_legs_cannot_be_edited_removed_or_undone(g):
    watch(g)
    g.call("add_leg")
    g.call("sail")
    first = dict(g.run["legs"][0])
    g.call("add_leg")
    g.call("set_leg", i=0, heading=1)
    g.call("nudge", i=0, field="hours", delta=2)
    g.call("remove_leg", i=0)
    assert g.run["legs"][0] == first and len(g.run["legs"]) == 2
    g.call("undo")
    g.call("undo")
    assert g.run["legs"][0] == first and len(g.run["legs"]) >= 1
    g.call("clear")
    assert g.run["legs"] == [first]


def test_no_landmark_is_in_sight_before_a_leg_is_sailed_and_the_readings_are_exact_enough_after(g):
    v = watch(g)
    assert v["watch"]["readings"] == []
    g.call("add_leg")
    g.call("set_leg", i=0, heading=44, hours=2.0)
    v = g.call("sail")
    chart = g.charts.get_chart("fix-01")
    readings = v["watch"]["readings"]
    assert len(readings) == 1 and readings[0]["id"] == "cape-light"
    true_pos = g.sim.sail(chart, g.run["legs"], seed=0)["end"]
    r = readings[0]
    assert abs(((r["bearing"] - bearing(true_pos, (14.0, 7.0))) + 180) % 360 - 180) <= fixes.BEARING_ERR_DEG + 0.5
    assert abs(r["range"] - dist(true_pos, (14.0, 7.0))) <= dist(true_pos, (14.0, 7.0)) * fixes.RANGE_ERR_SHARE + 0.06


def test_a_fix_moves_the_plot_to_where_the_readings_put_the_ship_never_to_the_truth(g):
    watch(g)
    g.call("add_leg")
    g.call("set_leg", i=0, heading=44, hours=2.0)
    v = g.call("sail")
    before = v["watch"]["believed"]
    reading = v["watch"]["readings"][0]
    v = g.call("take_fix", landmark="cape-light")
    ux, uy = unit(reading["bearing"])
    expect = [round(14.0 - reading["range"] * ux, 2), round(7.0 - reading["range"] * uy, 2)]
    assert v["watch"]["believed"] == expect and v["watch"]["applied"] == "cape-light" and v["watch"]["believed"] != before
    assert "dr-fix" in v["svg"] and "dr-true-track" not in v["svg"]
    true_pos = g.sim.sail(g.charts.get_chart("fix-01"), g.run["legs"], seed=0)["end"]
    assert dist(expect, true_pos) < 1.0                                # close to the truth, but it is the readings that decide
    assert g.call("take_fix", landmark="nowhere")["watch"]["applied"] == "cape-light"


def test_a_fix_corrects_the_next_plot_and_the_next_watchs_helper_starts_from_it(g):
    watch(g)
    g.call("add_leg")
    g.call("set_leg", i=0, heading=44, hours=2.0)
    g.call("sail")
    g.call("take_fix", landmark="cape-light")
    believed = g.call("open")["watch"]["believed"]
    v = g.call("helper", kind="naive", target="flag")
    assert len(v["legs"]) == 2
    assert v["legs"][1]["heading"] == round(bearing(believed, g.charts.get_chart("fix-01")["dest"])) % 360


def test_fog_hides_every_landmark(g):
    chart = g.charts.get_chart("fix-01")
    chart["fog"] = True
    try:
        watch(g)
        g.call("add_leg")
        assert g.call("sail")["watch"]["readings"] == []
    finally:
        del chart["fog"]


def test_anchoring_ends_the_passage_and_scores_what_was_sailed(g):
    watch(g)
    assert g.call("anchor")["phase"] == "plan"                       # nothing sailed yet: nothing to end
    g.call("add_leg")
    g.call("sail")
    g.call("add_leg")
    v = g.call("anchor")
    assert v["phase"] == "reveal" and len(g.run["legs"]) == 1 and v["reveal"]["points"]
    assert g.meta["charts"]["fix-01"]["attempts"] == 1


def test_running_aground_ends_the_passage_by_itself(g):
    import solver
    watch(g, "fix-03")
    chart = g.charts.get_chart("fix-03")
    rock = [h for h in chart["hazards"] if h["id"] == "last-rock"][0]
    leg = solver.shoot(chart, chart["start"], (rock["x"], rock["y"]), model="true", speed=5.0)
    g.call("add_leg")
    g.call("set_leg", i=0, **leg)
    v = g.call("sail")
    assert v["phase"] == "reveal" and v["reveal"]["aground"]


def test_taking_a_fix_earns_the_first_fix_flag_even_without_landfall(g):
    watch(g)
    g.call("add_leg")
    g.call("set_leg", i=0, heading=44, hours=2.0)
    g.call("sail")
    g.call("take_fix", landmark="cape-light")
    g.call("anchor")
    assert "first_fix" in g.meta["flags"]


def test_a_watch_passage_survives_save_and_load(g):
    watch(g)
    g.call("add_leg")
    g.call("set_leg", i=0, heading=44, hours=2.0)
    g.call("sail")
    g.call("take_fix", landmark="cape-light")
    g.call("add_leg")
    before = g.call("open")
    saved = json.loads(json.dumps(g.get_state()))
    assert saved["run"]["mode"] == "watch" and saved["run"]["sailed"] == 1 and saved["run"]["fixes"][0]["landmark"] == "cape-light"
    g.call("reset")
    g.load_state(saved)
    after = g.call("open")
    assert after["watch"] == before["watch"] and after["svg"] == before["svg"] and after["legs"] == before["legs"]


def test_a_saved_watch_run_is_validated(g):
    base = {"chart_id": "fix-01", "mode": "watch", "legs": [{"heading": 40, "speed": 5, "hours": 1}, {"heading": 40, "speed": 5, "hours": 1}], "sailed": 9}
    g.load_state({"run": dict(base, fixes=[{"after_leg": 5, "x": 1, "y": 1, "landmark": "cape-light"}, {"after_leg": 0, "x": 1, "y": 1, "landmark": "zzz"},
                                           {"after_leg": 0, "x": "a", "y": 1, "landmark": "cape-light"}, {"after_leg": 0, "x": 3, "y": 4, "landmark": "cape-light"}, 7])})
    assert g.run["sailed"] == 2 and g.run["fixes"] == [{"after_leg": 0, "x": 3.0, "y": 4.0, "landmark": "cape-light"}]
    g.load_state({"run": dict(base, mode="watch", chart_id="open-01")})
    assert g.run["mode"] == "plan" and g.run["sailed"] == 0 and g.run["fixes"] == []


def test_readings_are_repeatable_and_bounded(g):
    chart = g.charts.get_chart("fix-01")
    a = fixes.readings(chart, (10.0, 10.0), 2)
    assert a == fixes.readings(chart, (10.0, 10.0), 2)
    assert fixes.readings(chart, (10.0, 10.0), 3)[0]["bearing"] != 400
    assert fixes.in_sight(chart, (0.0, 19.0)) == []
    assert fixes.position_from(chart, "cape-light", 0, 3) == (14.0, 4.0)
    assert fixes.position_from(chart, "none", 0, 3) is None


def test_the_current_stream_helper_in_a_watch_uses_the_believed_position(g):
    watch(g)
    g.call("add_leg")
    g.call("sail")
    v = g.call("helper", kind="current", target="flag")
    assert len(v["legs"]) == 2 and v["legs"][1]["hours"] > 0


def test_the_game_without_a_run_for_watch_charts_never_leaks_the_truth_in_views(g):
    watch(g)
    g.call("add_leg")
    g.call("sail")
    text = json.dumps(g.call("open"))
    assert "true_set" not in text and '"points":' not in text and "dr-true-track" not in text
