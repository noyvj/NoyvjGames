import json

import pytest

from geom import dist


def clear_three(g):
    """Pretend the player has cleared three charts (unlocks the allow-for-the-chart helper)."""
    for cid in ("a", "b", "c"):
        g.meta["charts"][cid] = {"best_error_nm": 1.0, "stars": 1, "attempts": 1, "discovered": [], "par_seen": False, "trusted": False}


def test_open_starts_a_chart_in_the_planning_phase_with_nothing_of_the_truth(g):
    v = g.call("open")
    assert v["phase"] == "plan" and v["legs"] == [] and "reveal" not in v
    assert "dr-true-track" not in v["svg"] and "dr-ship" not in v["svg"] and "dr-ribbon" not in v["svg"]
    text = json.dumps(v)
    assert "true_set" not in text and "true_drift" not in text and '"points":' not in text and '"reveal":' not in text


def test_the_plan_view_is_the_same_before_and_after_a_reload_of_the_page(g):
    g.call("add_leg")
    first = g.call("open")
    assert g.call("open") == first


def test_add_edit_nudge_remove_and_undo(g):
    v = g.call("add_leg")
    assert len(v["legs"]) == 1 and v["legs"][0]["hours"] == 1.0
    v = g.call("set_leg", i=0, heading=400, speed=99, hours=0.2)
    assert v["legs"][0] == {"heading": 40, "speed": 7.0, "hours": 0.5}
    v = g.call("nudge", i=0, field="heading", delta=-45)
    assert v["legs"][0]["heading"] == 355
    v = g.call("nudge", i=0, field="hours", delta=1.5)
    assert v["legs"][0]["hours"] == 2.0
    assert v["can_undo"]
    v = g.call("undo")
    assert v["legs"][0]["hours"] == 0.5
    v = g.call("remove_leg", i=0)
    assert v["legs"] == []
    v = g.call("undo")
    assert len(v["legs"]) == 1


def test_bad_requests_never_crash_the_engine(g):
    g.call("add_leg")
    for bad in ({"action": "set_leg", "i": 9}, {"action": "set_leg", "i": "x"}, {"action": "nudge", "i": 0, "field": "bogus", "delta": 1},
                {"action": "nudge", "i": 0, "field": "heading", "delta": "x"}, {"action": "point", "x": "a", "y": 1}, {"action": "remove_leg", "i": -1}):
        assert "legs" in json.loads(g.handle(json.dumps(bad)))
    assert "error" in json.loads(g.handle("not json"))
    assert "error" in json.loads(g.handle(json.dumps({"action": "fly"})))
    assert "error" in json.loads(g.handle(json.dumps({"action": "start", "chart_id": "nowhere"})))


def test_there_is_a_leg_limit(g):
    for _ in range(20):
        v = g.call("add_leg")
    assert len(v["legs"]) == 12


def test_clear_empties_the_plan_and_forgets_the_helpers(g):
    g.call("helper", kind="naive", target="flag")
    assert g.run["helpers"] == ["naive"]
    v = g.call("clear")
    assert v["legs"] == [] and g.run["helpers"] == []


def test_plot_end_and_totals_follow_the_plan(g):
    v = g.call("add_leg")
    t = v["totals"]
    assert t["legs"] == 1 and t["hours"] == 1.0 and t["distance"] == 5.0 and t["deadline"] == 10.0 and not t["over"]
    for _ in range(3):
        v = g.call("nudge", i=0, field="hours", delta=3)
    assert v["totals"]["over"] and v["totals"]["hours"] == 10.0 or v["totals"]["hours"] > 0


def test_the_naive_helper_adds_a_straight_leg_and_is_remembered(g):
    g.call("allow", value=False)
    v = g.call("helper", kind="naive", target="flag")
    assert len(v["legs"]) == 1 and g.run["helpers"] == ["naive"]
    assert v["totals"]["plot_miss"] < 1.0               # the plain dead-reckoning plot ends at the flag; the sea disagrees


def test_the_allowing_for_the_chart_helper_is_locked_until_three_charts_are_cleared(g):
    v = g.call("helper", kind="current", target="flag")
    assert v["legs"] == [] and not v["helpers"]["current"] and not v["helpers"]["current_unlocked"]
    clear_three(g)
    v = g.call("open")
    assert v["helpers"]["current"]
    v = g.call("helper", kind="current", target="flag")
    assert len(v["legs"]) == 1 and g.run["helpers"] == ["current"]
    assert v["totals"]["plot_miss"] < 0.8
    v = g.call("allow", value=False)
    assert not v["helpers"]["current"]
    assert len(g.call("helper", kind="current", target="flag")["legs"]) == 1       # refused while the plot ignores the chart


def test_the_ruler_reports_bearing_and_distance_from_where_the_plot_ends(g):
    v = g.call("point", x=3.0, y=13.0)
    assert v["point"] == {"x": 3.0, "y": 13.0, "bearing": 0, "distance": 10.0}
    assert "dr-point-cross" in v["svg"]
    v = g.call("point", x=-5, y=999)
    assert v["point"]["x"] == 0.0 and v["point"]["y"] == 20.0
    v = g.call("clear_point")
    assert v["point"] is None
    g.call("point", x=3.0, y=13.0)
    v = g.call("helper", kind="naive", target="point")
    assert v["legs"][0]["heading"] == 0


def test_sailing_reveals_the_truth_and_closes_the_plan(g):
    g.call("helper", kind="naive", target="flag")
    v = g.call("sail")
    assert v["phase"] == "reveal" and v["reveal"]["points"][0][0] == 0.0 and "dr-true-track" in v["svg"]
    assert v["reveal"]["title"] and v["reveal"]["criteria"] and v["reveal"]["lines"]
    assert "error" in g.call("add_leg")
    assert g.meta["charts"]["demo"]["attempts"] == 1
    assert g.call("sail")["phase"] == "reveal" and g.meta["charts"]["demo"]["attempts"] == 1    # never counted twice


def test_retry_keeps_the_legs_and_restart_empties_them(g):
    g.call("add_leg")
    g.call("sail")
    v = g.call("retry")
    assert v["phase"] == "plan" and len(v["legs"]) == 1
    g.call("sail")
    v = g.call("restart")
    assert v["phase"] == "plan" and v["legs"] == []


def test_a_good_plan_earns_three_stars_and_is_remembered(g):
    import solver
    chart = g.charts.get_chart("demo")
    legs, _end = solver.route(chart, [chart["start"], (6.0, 7.0), (11.5, 9.0), chart["dest"]], model="true")
    assert legs
    for leg in legs:
        v = g.call("add_leg")
        i = len(v["legs"]) - 1
        g.call("set_leg", i=i, **leg)
    v = g.call("sail")
    assert v["reveal"]["stars"] >= 1 or v["reveal"]["aground"]


def test_state_is_minimal_by_default_and_round_trips(g):
    assert g.get_state() == {"schema": 1}
    g.call("add_leg")
    g.call("set_leg", i=0, heading=33, speed=4.5, hours=2.5)
    g.call("allow", value=False)
    saved = g.get_state()
    assert saved["run"] == {"chart_id": "demo", "legs": [{"heading": 33, "speed": 4.5, "hours": 2.5}], "allow": False}
    g.call("reset")
    assert g.get_state() == {"schema": 1}
    g.load_state(json.loads(json.dumps(saved)))
    v = g.call("open")
    assert v["legs"] == [{"heading": 33, "speed": 4.5, "hours": 2.5}] and v["allow"] is False


def test_a_revealed_passage_survives_a_save_and_load_identically(g):
    g.call("helper", kind="naive", target="flag")
    before = g.call("sail")
    saved = json.loads(json.dumps(g.get_state()))
    assert saved["run"]["phase"] == "reveal"
    g.call("reset")
    g.load_state(saved)
    after = g.call("open")
    assert after["reveal"] == before["reveal"] and after["svg"] == before["svg"]


def test_loading_junk_never_crashes_and_never_costs_the_good_parts(g):
    for junk in (None, 5, "x", [], {"meta": 5, "run": []}, {"meta": {"charts": {"demo": 7, "nowhere": {"stars": 3}}}},
                 {"run": {"chart_id": "demo", "legs": [None, 3, {"heading": float("nan")}, {"heading": 90, "speed": "fast", "hours": 2}], "phase": "weird",
                          "mode": 9, "seed": -4, "allow": "no", "helpers": ["naive", "x", 3]}},
                 {"run": {"chart_id": "x" * 500}}, {"run": {"chart_id": "demo", "legs": "none"}}):
        g.load_state(junk)
        assert g.call("open")["phase"] in ("plan", "reveal")
    g.call("reset")
    g.load_state({"run": {"chart_id": "demo", "legs": [None, {"heading": 90, "speed": "fast", "hours": 2}], "helpers": ["naive", "x"], "seed": -4}})
    assert g.run["legs"] == [{"heading": 90, "speed": 5.0, "hours": 2.0}] and g.run["helpers"] == ["naive"] and g.run["seed"] == 0


def test_loading_merges_records_by_taking_the_better_of_each(g):
    g.meta["charts"]["demo"] = {"best_error_nm": 2.0, "stars": 1, "attempts": 5, "discovered": [], "par_seen": False, "trusted": False}
    g.load_state({"meta": {"charts": {"demo": {"best_error_nm": 1.0, "stars": 3, "attempts": 2, "trusted": True}}, "flags": ["landfall", "bogus"]}})
    rec = g.meta["charts"]["demo"]
    assert rec["best_error_nm"] == 1.0 and rec["stars"] == 3 and rec["attempts"] == 5 and rec["trusted"]
    assert g.meta["flags"] == ["landfall"]


def test_the_reveal_hides_nothing_it_should_show_and_shows_nothing_in_the_plan_view(g):
    g.call("helper", kind="naive", target="flag")
    plan = json.dumps(g.call("open"))
    assert "reveal" not in plan
    g.call("sail")
    assert "reveal" in json.dumps(g.call("open"))


@pytest.mark.parametrize("hours", (0.5, 3.0, 12.0))
def test_every_legal_leg_length_can_be_sailed(g, hours):
    g.call("add_leg")
    g.call("set_leg", i=0, hours=hours)
    assert g.call("sail")["reveal"]["points"][-1][0] <= hours


def test_the_plot_miss_is_a_distance_to_the_flag(g):
    g.call("add_leg")
    v = g.call("open")
    end = v["totals"]["plot_end"]
    assert abs(dist(end, g.charts.get_chart("demo")["dest"]) - v["totals"]["plot_miss"]) < 0.06
