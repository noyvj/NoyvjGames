"""Milestone 7, Two ships: the pure fleet engine (fleet.py), the chapter-7 charts, the game flow with a second plan, saves and the
practice generator's two-ship option."""

import copy
import json

import pytest

import charts
import fleet
import gen
import render
import sim
import solver
from geom import dist, point_in_polygon, seg_polygon_dist
from state import MAX_LEGS

TWO = [c for c in charts.all_charts() if fleet.is_two(c)]
TWO_IDS = [c["id"] for c in TWO]


def track(points):
    return [[t, x, y] for t, x, y in points]


def two_chart(chart):
    """The empty 20 nm chart with a second ship at the far corners."""
    out = copy.deepcopy(chart)
    out["ship2"] = {"start": [18.0, 2.0], "dest": [2.0, 18.0], "speeds": [3.0, 8.0], "deadline": 12.0, "arrival_radius": 1.5}
    out["id"] = "test-two"
    return out


# --- the closest approach ---------------------------------------------------------------------------
def test_ships_that_meet_head_on_have_a_zero_gap_and_a_breach_before_it():
    a = track([(0, 0, 10), (1, 5, 10), (2, 10, 10)])
    b = track([(0, 20, 10), (1, 15, 10), (2, 10, 10)])
    ap = fleet.closest_approach(a, b)
    assert ap["dist"] == 0.0 and ap["t"] == 2.0 and ap["too_close"]
    assert abs(ap["breach_t"] - 1.9) < 0.011, "they are 1 nm apart when each has covered 9.5 of the 10 nm"


def test_parallel_ships_stay_apart_and_report_their_gap():
    a = track([(0, 0, 0), (2, 10, 0)])
    b = track([(0, 0, 4), (2, 10, 4)])
    ap = fleet.closest_approach(a, b)
    assert ap["dist"] == 4.0 and not ap["too_close"] and ap["breach_t"] is None


def test_a_pass_between_two_steps_is_not_missed():
    """Two ships crossing at right angles within one step: the straight-line interpolation sees the near miss."""
    a = track([(0, 0, 0), (1, 10, 0)])
    b = track([(0, 5, 5), (1, 5, -5)])
    ap = fleet.closest_approach(a, b)
    assert ap["dist"] == 0.0 and ap["t"] == 0.5 and ap["too_close"]


def test_only_the_stretch_when_both_are_under_way_counts():
    a = track([(0, 0, 0), (1, 1, 0)])                      # ship A's passage ends at hour 1
    b = track([(0, 9, 0), (1, 5, 0), (2, 1, 0)])           # ship B reaches A's resting place at hour 2: not counted
    ap = fleet.closest_approach(a, b)
    assert ap["overlap"] == 1.0 and ap["dist"] == 4.0 and not ap["too_close"]


def test_ships_with_no_legs_are_compared_at_their_starts():
    ap = fleet.closest_approach(track([(0, 3, 3)]), track([(0, 3.5, 3)]))
    assert ap["dist"] == 0.5 and ap["too_close"] and ap["breach_t"] == 0.0


def test_the_rule_is_a_strict_gap_of_exactly_one_mile_is_fine():
    ap = fleet.closest_approach(track([(0, 0, 0), (1, 0, 0)]), track([(0, 1, 0), (1, 1, 0)]))
    assert ap["dist"] == 1.0 and not ap["too_close"]


# --- one sea, two ships ------------------------------------------------------------------------------
def test_ship_b_has_its_own_start_flag_speed_and_deadline_and_a_is_the_chart_itself(chart):
    two = two_chart(chart)
    assert fleet.ship_chart(two, 0) is two
    b = fleet.ship_chart(two, 1)
    assert b["start"] == [18.0, 2.0] and b["dest"] == [2.0, 18.0] and b["deadline"] == 12.0 and b["id"] == "test-two~B"
    assert "ship2" not in b and b["hazards"] == two["hazards"] and b["currents"] == two["currents"]
    assert fleet.ships(chart) == [chart] and fleet.ship_chart(chart, 1) is chart


def test_each_ship_sails_exactly_as_it_would_alone(chart):
    two = two_chart(chart)
    two["currents"] = [{"id": "z", "rect": [0, 0, 20, 20], "set": 90, "drift_range": [1, 1], "true_set": 90, "true_drift": 1.0}]
    la = [{"heading": 60, "speed": 5.0, "hours": 3.0}]
    lb = [{"heading": 330, "speed": 5.0, "hours": 3.0}]
    both = fleet.sail_fleet(two, la, lb)
    assert both["ships"][0]["track"] == sim.sail(two, la)["track"]
    assert both["ships"][1]["track"] == sim.sail(fleet.ship_chart(two, 1), lb, seed=fleet.ship_seed(0, 1))["track"]
    assert fleet.sail_fleet(two, la, lb) == both, "a pure function of (chart, plans, seed)"


def test_the_ships_events_are_labelled_and_a_breach_is_one_more_public_event(chart):
    two = two_chart(chart)
    two["ship2"].update(start=[18.0, 10.0], dest=[2.0, 10.0])
    two["start"], two["dest"] = [2.0, 10.0], [18.0, 10.0]
    la = [{"heading": 90, "speed": 4.0, "hours": 4.0}]
    lb = [{"heading": 270, "speed": 4.0, "hours": 4.0}]
    res = fleet.sail_fleet(two, la, lb)
    breach = [e for e in res["events"] if e["kind"] == "apart"]
    assert len(breach) == 1 and breach[0]["public"] and "closer than 1 nm" in breach[0]["text"]
    assert 1.8 < breach[0]["t"] < 1.9


def test_a_ship_that_runs_aground_is_listed_and_the_other_sails_on(chart):
    two = two_chart(chart)
    two["hazards"] = [{"id": "r", "kind": "rock", "name": "Rock", "x": 10.0, "y": 10.0, "r": 1.0, "charted": True}]
    la = [{"heading": 45, "speed": 5.0, "hours": 4.0}]               # straight at the rock from (2,2)
    lb = [{"heading": 90, "speed": 5.0, "hours": 1.0}]
    res = fleet.sail_fleet(two, la, lb)
    assert [g["hazard"] for g in res["groundings"]] == ["r"] and res["aground"]["hazard"] == "r"
    assert res["ships"][1]["aground"] is None and res["ships"][1]["close"] == []


# --- the score ---------------------------------------------------------------------------------------
def par_pair(cid):
    return charts.par_legs(cid), charts.par_legs2(cid)


def test_the_fleet_stars_are_the_lower_of_the_two_and_a_close_approach_costs_one():
    c = charts.get_chart("two-01")
    la, lb = par_pair("two-01")
    res = fleet.sail_fleet(c, la, lb)
    sc = fleet.score_fleet(c, la, lb, res)
    assert sc["stars"] == 3 and sc["apart"] and sc["criteria"][-1]["id"] == "apart" and sc["criteria"][-1]["ok"]
    # the same two plans without Ship B's wait: both are fine alone, together they meet
    lb2 = [leg for leg in lb if leg["speed"] > 0]
    res2 = fleet.sail_fleet(c, la, lb2)
    sc2 = fleet.score_fleet(c, la, lb2, res2)
    assert res2["approach"]["too_close"] and sc2["ships"][0]["stars"] == 3
    assert sc2["stars"] == min(sc2["ships"][0]["stars"], sc2["ships"][1]["stars"]) - 1
    assert not sc2["criteria"][-1]["ok"] and "costs one star" in sc2["criteria"][-1]["text"]


def test_a_close_approach_never_costs_the_first_star():
    c = charts.get_chart("two-01")
    la, lb = par_pair("two-01")
    lb2 = [leg for leg in lb if leg["speed"] > 0]
    sc = fleet.score_fleet(c, la, lb2, fleet.sail_fleet(c, la, lb2))
    assert sc["stars"] >= 1
    # make Ship A miss its flag by a long way as well: still just the usual landfall rule, nothing is subtracted from zero
    bad = [{"heading": 0, "speed": 3.0, "hours": 1.0}]
    sc2 = fleet.score_fleet(c, bad, lb, fleet.sail_fleet(c, bad, lb))
    assert sc2["stars"] == 0 and not sc2["arrived"]


def test_the_criteria_are_listed_per_ship_and_always_explained():
    c = charts.get_chart("two-03")
    la, lb = par_pair("two-03")
    sc = fleet.score_fleet(c, la, lb, fleet.sail_fleet(c, la, lb))
    texts = [x["text"] for x in sc["criteria"]]
    assert len(texts) == 9 and sum(t.startswith("Ship A - ") for t in texts) == 4 and sum(t.startswith("Ship B - ") for t in texts) == 4
    assert all(t.strip() for t in texts)


# --- the chapter-7 charts ----------------------------------------------------------------------------
def test_chapter_seven_has_about_seven_charts_and_each_is_a_two_ship_chart():
    assert 6 <= len(TWO) <= 8 and [c["chapter"] for c in TWO] == ["ships"] * len(TWO)
    assert charts.CHAPTERS[-1]["id"] == "ships" and charts.CHAPTERS[-1]["name"] == "Two ships"
    assert len(charts.CHAPTERS[-1]["charts"]) == len(TWO)


@pytest.mark.parametrize("cid", TWO_IDS)
def test_ship_b_is_in_clear_water_with_a_legal_schema(cid):
    c = charts.get_chart(cid)
    b = fleet.ship_chart(c, 1)
    assert b["speeds"][0] <= b["speeds"][1] and b["deadline"] > 0 and 0.5 <= b["arrival_radius"] <= 2.5
    for key in ("start", "dest"):
        assert 1.0 <= b[key][0] <= c["size"] - 1.0 and 1.0 <= b[key][1] <= c["size"] - 1.0
    for hz in c["hazards"]:
        assert dist(b["start"], (hz["x"], hz["y"])) > hz["r"] + 1.0 and dist(b["dest"], (hz["x"], hz["y"])) > hz["r"] + b["arrival_radius"]
    for land in c["land"]:
        assert not point_in_polygon(tuple(b["start"]), land["poly"]) and not point_in_polygon(tuple(b["dest"]), land["poly"])
        assert seg_polygon_dist(tuple(b["start"]), tuple(b["start"]), land["poly"]) > 1.0
        assert seg_polygon_dist(tuple(b["dest"]), tuple(b["dest"]), land["poly"]) > b["arrival_radius"]
    assert dist(b["start"], c["start"]) > 3.0 and dist(b["dest"], c["dest"]) > 2 * c["arrival_radius"]
    assert all(1.0 <= p[0] <= c["size"] - 1 and 1.0 <= p[1] <= c["size"] - 1 for p in b["waypoints"])


@pytest.mark.parametrize("cid", TWO_IDS)
def test_both_par_plans_together_earn_three_stars_with_slack_on_both_deadlines(cid):
    """Every authored chart is solvable with three stars: the two par plans, sailed together."""
    c = charts.get_chart(cid)
    la, lb = par_pair(cid)
    assert la and lb and len(la) <= MAX_LEGS and len(lb) <= MAX_LEGS
    assert lb == sim.clean_legs(fleet.ship_chart(c, 1), lb), "Ship B's par legs must already be on the legal grid"
    res = fleet.sail_fleet(c, la, lb)
    sc = fleet.score_fleet(c, la, lb, res)
    assert res["groundings"] == [] and res["close"] == [], "neither par plan touches or brushes a hazard"
    assert sc["stars"] == 3 and sc["arrived"] and sc["on_time"] and sc["clear"] and sc["apart"], sc["criteria"]
    assert res["approach"]["dist"] >= fleet.SEPARATION + 0.2, "the par pair keeps a margin on the rule"
    for i, legs in enumerate((la, lb)):
        assert sim.plan_hours(legs) <= 0.9 * fleet.ship_chart(c, i)["deadline"], "the deadline leaves some slack"


@pytest.mark.parametrize("cid", TWO_IDS)
def test_each_par_plan_is_a_three_star_plan_for_its_ship_alone(cid):
    c = charts.get_chart(cid)
    for i, legs in enumerate(par_pair(cid)):
        ship = fleet.ship_chart(c, i)
        res = sim.sail(ship, legs, seed=fleet.ship_seed(0, i))
        sc = sim.score(ship, legs, res)
        assert sc["stars"] == 3 and res["aground"] is None and res["close"] == []


@pytest.mark.parametrize("cid", TWO_IDS)
def test_the_puzzle_is_real_the_unhurried_plans_meet(cid):
    """Without waiting, each ship's own best route would meet the other's: the chart is a timing puzzle, not just two charts."""
    c = charts.get_chart(cid)
    b = fleet.ship_chart(c, 1)
    la, _ = solver.route(c, [tuple(p) for p in c["waypoints"]], model="true", wait=0.0)
    lb, _ = solver.route(b, [tuple(p) for p in b["waypoints"]], model="true", seed=fleet.ship_seed(0, 1), wait=0.0)
    res = fleet.sail_fleet(c, la, lb)
    assert res["approach"]["too_close"], (cid, res["approach"])


@pytest.mark.parametrize("cid", TWO_IDS)
def test_ship_bs_honest_forecast_makes_landfall_and_its_naive_flag_is_true(cid):
    c = charts.get_chart(cid)
    b = fleet.ship_chart(c, 1)
    legs, _ = solver.route(b, [tuple(p) for p in b["waypoints"]], model="charted", wait=b.get("par_wait", 0.0), seed=fleet.ship_seed(0, 1))
    res = sim.sail(b, legs, seed=fleet.ship_seed(0, 1))
    assert res["aground"] is None and dist(res["end"], b["dest"]) <= b["arrival_radius"]
    miss = sim.naive_miss(b)
    assert (miss > b["arrival_radius"]) == bool(b["naive_fails"]), (miss, b["naive_fails"])


@pytest.mark.parametrize("cid", TWO_IDS)
def test_the_chart_draws_both_ships_and_states_the_rule_in_words(cid):
    from xml.dom import minidom
    c = charts.get_chart(cid)
    la, lb = par_pair(cid)
    res = fleet.sail_fleet(c, la, lb)
    ea, eb = sim.estimate(c, la), sim.estimate(fleet.ship_chart(c, 1), lb)
    svg = render.render_chart(c, est=ea, marks=render.plan_marks(la, ea), true_track=res["ships"][0]["track"], reveal=True,
                              ship2={"est": eb, "marks": render.plan_marks(lb, eb), "true_track": res["ships"][1]["track"]},
                              approach=dict(res["approach"], kind="true"))
    minidom.parseString(svg)
    for needle in ("Start A", "Start B", "Landfall A", "Landfall B", 'id="dr-true-track-2"', 'id="dr-ship-2"', 'id="dr-ribbons-2"', "dr-approach"):
        assert needle in svg, needle
    notes = " ".join(render.chart_notes(c))
    assert "Ship A starts" in notes and "Ship B starts" in notes and fleet.rule_text() in notes
    assert fleet.rule_text() in render.chart_notes(c)[2]


def test_a_one_ship_chart_draws_exactly_as_before(chart):
    svg = render.render_chart(chart)
    assert "Start A" not in svg and ">Start<" in svg and ">Landfall<" in svg and "dr-approach" not in svg and "dr-start-b" not in svg


def test_the_chapter_opens_after_four_compass_charts_and_the_new_charts_are_in_the_order():
    records = {c["id"]: {"stars": 1} for c in charts.CHAPTERS[5]["charts"][:4]}
    for chapter in charts.CHAPTERS[:5]:
        records.update({c["id"]: {"stars": 1} for c in chapter["charts"]})
    assert "ships" in charts.unlocked_chapters(records) and "ships" not in charts.unlocked_chapters({})
    assert charts.ORDER[-len(TWO):] == TWO_IDS and charts.par_legs2("open-01") is None


# --- the game flow -----------------------------------------------------------------------------------
def play_both(g, cid):
    g.call("start", chart_id=cid)
    la, lb = par_pair(cid)
    for leg in la:
        g.call("set_leg", i=len(g.call("add_leg")["legs"]) - 1, **leg)
    g.call("select_ship", ship=1)
    for leg in lb:
        g.call("set_leg", i=len(g.call("add_leg")["legs"]) - 1, **leg)


@pytest.fixture
def open_all(g):
    for chapter in charts.CHAPTERS[:-1]:
        for c in chapter["charts"]:
            g.meta["charts"][c["id"]] = dict(g.state.new_record(), stars=1)
    return g


def test_the_plan_view_of_a_two_ship_chart_edits_one_ship_at_a_time(open_all):
    g = open_all
    v = g.call("start", chart_id="two-01")
    assert v["chart"]["two"] and v["fleet"]["active"] == 0 and len(v["fleet"]["ships"]) == 2
    assert fleet.rule_text() in v["chart"]["goal"] and "Ship A:" in v["chart"]["goal"] and "Ship B:" in v["chart"]["goal"]
    v = g.call("add_leg")
    assert len(v["legs"]) == 1 and v["fleet"]["ships"][0]["legs"] == 1 and v["fleet"]["ships"][1]["legs"] == 0
    a_leg = v["legs"][0]
    assert a_leg["heading"] == 90, "the default leg points at Ship A's own flag"
    v = g.call("select_ship", ship=1)
    assert v["fleet"]["active"] == 1 and v["legs"] == [] and v["limits"]["speeds"] == [3.0, 7.0]
    v = g.call("add_leg")
    assert v["legs"][0]["heading"] == 0, "and Ship B's default leg points at Ship B's flag (north)"
    assert v["fleet"]["line"].startswith("Your plots")
    v = g.call("select_ship", ship=0)
    assert v["legs"] == [a_leg] and v["totals"]["legs"] == 1


def test_select_ship_is_ignored_on_a_one_ship_chart_and_for_bad_values(g):
    assert g.call("select_ship", ship=1)["legs"] == [] and "fleet" not in g.call("open")
    g.call("start", chart_id="open-01")
    assert g.call("select_ship", ship=1)["chart"]["two"] is False and g.run["ship"] == 0


def test_undo_restores_the_ship_that_changed(open_all):
    g = open_all
    g.call("start", chart_id="two-01")
    g.call("add_leg")
    g.call("select_ship", ship=1)
    g.call("add_leg")
    g.call("nudge", i=0, field="heading", delta=10)
    g.call("select_ship", ship=0)
    v = g.call("undo")
    assert v["fleet"]["active"] == 1 and v["legs"][0]["heading"] == 0
    v = g.call("undo")
    assert v["fleet"]["active"] == 1 and v["legs"] == []
    v = g.call("undo")
    assert v["fleet"]["active"] == 0 and v["legs"] == []


def test_the_planner_warns_from_the_players_own_plots_never_from_the_truth(open_all):
    g = open_all
    g.call("start", chart_id="two-01")
    v = g.call("add_leg")
    for k in ("heading", "speed", "hours"):
        pass
    g.call("set_leg", i=0, heading=90, speed=5.0, hours=3.0)
    g.call("select_ship", ship=1)
    g.call("add_leg")
    v = g.call("set_leg", i=0, heading=0, speed=5.0, hours=3.0)
    assert v["fleet"]["plot_closest"]["too_close"] and "inside the 1 nm rule" in v["fleet"]["line"]
    assert "dr-approach-plot" in v["svg"] and "dr-true-track" not in v["svg"] and "dr-ship" not in v["svg"]
    v = g.call("add_wait")                                       # (a wait appended after the sailing leg changes nothing yet)
    text = json.dumps(v)
    assert "true_set" not in text and '"points2"' not in text and '"reveal"' not in text


def test_sailing_both_par_plans_reveals_both_tracks_and_the_closest_approach(open_all):
    g = open_all
    play_both(g, "two-01")
    v = g.call("sail")
    r = v["reveal"]
    assert v["phase"] == "reveal" and r["stars"] == 3 and r["arrived"] and not r["aground"]
    assert r["points"] and r["points2"] and r["points"][0][0] == 0.0 and r["hours"] == max(r["points"][-1][0], r["points2"][-1][0])
    assert r["approach"]["dist"] >= 1.0 and r["approach"]["separation"] == 1.0 and not r["approach"]["too_close"]
    assert 'id="dr-true-track-2"' in v["svg"] and 'id="dr-true-track"' in v["svg"] and "dr-approach-true" in v["svg"]
    assert any("Ship B" in line for line in r["lines"]) and any("no closer than" in line for line in r["lines"])
    assert len(r["criteria"]) == 9 and r["criteria"][-1]["id"] == "apart"
    assert g.meta["charts"]["two-01"]["stars"] == 3 and "two_ships" in g.meta["flags"]


def test_a_close_approach_costs_a_star_but_the_run_goes_on_and_a_retry_is_free(open_all):
    g = open_all
    g.call("start", chart_id="two-01")
    la, lb = par_pair("two-01")
    for leg in la:
        g.call("set_leg", i=len(g.call("add_leg")["legs"]) - 1, **leg)
    g.call("select_ship", ship=1)
    for leg in lb[1:]:                                           # without the anchored wait
        g.call("set_leg", i=len(g.call("add_leg")["legs"]) - 1, **leg)
    v = g.call("sail")
    r = v["reveal"]
    assert r["approach"]["too_close"] and r["stars"] == 2 and r["arrived"] and "retry is free" in " ".join(r["lines"])
    assert any("closer than 1 nm" in e["text"] for e in r["events"])
    assert "two_ships" in g.meta["flags"], "both made landfall, so the achievement counts"
    v = g.call("retry")
    assert v["phase"] == "plan" and len(v["fleet"]["ships"]) == 2 and v["fleet"]["ships"][1]["legs"] == len(lb) - 1


def test_a_ship_aground_on_one_ship_does_not_stop_the_other_and_scores_zero(open_all):
    g = open_all
    g.call("start", chart_id="two-02")
    g.call("add_leg")
    g.call("set_leg", i=0, heading=53, speed=5.0, hours=4.0)     # fine for Ship A
    g.call("select_ship", ship=1)
    g.call("add_leg")
    g.call("set_leg", i=0, heading=270, speed=5.0, hours=6.0)    # Ship B west along its start's latitude: past the flag, lost
    r = g.call("sail")["reveal"]
    assert r["stars"] == 0 and not r["arrived"] and r["points2"]
    assert any(c["id"] == "landfall-b" and not c["ok"] for c in r["criteria"]) and any(c["id"] == "landfall-a" and c["ok"] for c in r["criteria"])


def test_show_and_load_the_par_plan_covers_both_ships(open_all):
    g = open_all
    play_both(g, "two-03")
    g.call("sail")
    v = g.call("show_par")
    par = v["reveal"]["par"]
    assert par["shown"] and any(line.startswith("Ship A, leg 1") for line in par["lines"]) and any(line.startswith("Ship B, leg 1") for line in par["lines"])
    assert "dr-par-track-b" in v["svg"]
    v = g.call("use_par")
    assert g.run["legs"] == charts.par_legs("two-03") and g.run["legs2"] == charts.par_legs2("two-03") and v["phase"] == "plan"
    assert v["fleet"]["ships"][1]["legs"] == len(charts.par_legs2("two-03"))


def test_the_helpers_work_on_the_active_ship_and_aim_at_its_own_flag(open_all):
    g = open_all
    g.call("start", chart_id="two-04")
    g.call("select_ship", ship=1)
    v = g.call("helper", kind="naive", target="flag")
    leg = v["legs"][0]
    b = fleet.ship_chart(g._chart(), 1)
    assert abs(dist(g.sim.estimate(b, v["legs"], allow=False)[-1][1:3], b["dest"])) < 3.0 and leg["speed"] > 0
    assert g.run["legs"] == [] and len(g.run["legs2"]) == 1 and g.run["helpers"] == ["naive"]


def test_restart_clears_both_plans_and_clear_clears_only_the_active_ship(open_all):
    g = open_all
    play_both(g, "two-01")
    g.call("clear")
    assert g.run["legs"] != [] and g.run["legs2"] == []
    g.call("restart")
    assert g.run["legs"] == [] and g.run["legs2"] == []


def test_the_rule_is_on_screen_and_the_goal_names_both_ships(open_all):
    v = open_all.call("start", chart_id="two-07")
    assert "at least 1 nm apart" in v["chart"]["goal"] and "Ship A" in v["chart"]["goal"]
    assert any("at least 1 nm apart" in note for note in v["notes"])


# --- saves ------------------------------------------------------------------------------------------------
def test_ship_bs_plan_survives_a_save_and_load_and_a_one_ship_save_is_unchanged(open_all):
    g = open_all
    play_both(g, "two-01")
    saved = json.loads(json.dumps(g.get_state()))
    assert saved["run"]["legs2"] == charts.par_legs2("two-01")
    g.call("reset")
    g.load_state(saved)
    v = g.call("open")
    assert v["chart"]["id"] == "two-01" and g.run["legs2"] == charts.par_legs2("two-01") and v["legs"] == charts.par_legs("two-01")
    g.call("start", chart_id="open-01")
    g.call("add_leg")
    assert "legs2" not in g.get_state()["run"]


def test_a_tampered_second_plan_is_cleaned_and_a_one_ship_chart_ignores_it(open_all):
    g = open_all
    cleaned = g.state.clean_run({"chart_id": "two-01", "legs": [], "legs2": [{"heading": 400, "speed": 99, "hours": 99}, "x", None] + [{}] * 40},
                                charts.get_chart)
    assert len(cleaned["legs2"]) <= MAX_LEGS and cleaned["legs2"][0] == {"heading": 40, "speed": 7.0, "hours": 12.0}
    one = g.state.clean_run({"chart_id": "open-01", "legs": [], "legs2": [{"heading": 10, "speed": 5, "hours": 1}]}, charts.get_chart)
    assert one["legs2"] == []
    revealed = g.state.clean_run({"chart_id": "two-01", "phase": "reveal", "legs": [], "legs2": [{"heading": 0, "speed": 5, "hours": 1}]}, charts.get_chart)
    assert revealed["phase"] == "reveal", "a reveal needs a plan for at least one ship"
    assert g.state.clean_run({"chart_id": "two-01", "phase": "reveal", "legs": [], "legs2": []}, charts.get_chart)["phase"] == "plan"


def test_the_two_ships_flag_is_a_known_flag_and_the_achievement_follows_it():
    import achievements
    import state
    assert "two_ships" in state.FLAGS and achievements.FLAG_OF["two_at_once"] == "two_ships"
    assert "patient_navigator" in achievements.FLAG_OF and len(achievements.ACHIEVEMENTS) == 15


def test_landfall_with_both_ships_is_needed_for_two_at_once(open_all):
    g = open_all
    g.call("start", chart_id="two-01")
    g.call("add_leg")
    g.call("set_leg", i=0, heading=90, speed=4.0, hours=4.0)     # Ship A lands; Ship B has no plan and stays at its start
    g.call("sail")
    assert "two_ships" not in g.meta["flags"] and "landfall" not in g.meta["flags"] or "two_ships" not in g.meta["flags"]


# --- the practice generator's two-ship option --------------------------------------------------------------
def test_two_ship_codes_carry_a_t_and_every_old_code_keeps_its_meaning():
    assert gen.code_of(3, 46655) == "DR3-ZZZ" and gen.code_of(3, 46655, True) == "DR3T-ZZZ"
    assert gen.chart_id(3, 46655, True) == "practice-3t-zzz" and gen.is_practice_id("practice-3t-zzz") and gen.is_practice_id("practice-3-zzz")
    assert gen.parse_ex("DR3T-zzz") == (3, 46655, True) and gen.parse_ex(" dr3-zzz ") == (3, 46655, False)
    assert gen.parse("DR3-ZZZ") == (3, 46655) and gen.parse("DR3T-ZZZ") is None
    for bad in ("DR3TT-1", "DR6T-1", "DRT-1", "practice-3tt-1"):
        assert gen.parse_ex(bad) is None, bad


PRACTICE = [(d, s) for d in gen.DIFFICULTIES for s in (11, 12, 13)]


@pytest.mark.parametrize("difficulty,seed", PRACTICE)
def test_a_two_ship_practice_chart_is_solvable_by_its_own_par_pair_with_three_stars(difficulty, seed):
    c = gen.make_chart(difficulty, seed, True)
    if c is None:
        pytest.skip("this seed gave no solvable two-ship chart (the page then tries the next seed)")
    assert fleet.is_two(c) and c["id"] == gen.chart_id(difficulty, seed, True) and c["ship2"]["par_legs"] and c["par_legs"]
    assert c == gen.make_chart(difficulty, seed, True) and gen.from_id(gen.code_of(difficulty, seed, True)) == c
    res = fleet.sail_fleet(c, c["par_legs"], c["ship2"]["par_legs"], seed=c["seed"])
    sc = fleet.score_fleet(c, c["par_legs"], c["ship2"]["par_legs"], res)
    assert sc["stars"] == 3 and res["approach"]["dist"] >= fleet.SEPARATION, sc["criteria"]
    assert charts.par_legs2(c["id"]) == c["ship2"]["par_legs"] and charts.par_legs(c["id"]) == c["par_legs"]
    assert gen.make_chart(difficulty, seed) != c, "the one-ship chart for the same seed is a different chart"


def test_most_seeds_make_a_two_ship_chart_at_every_level():
    for d in gen.DIFFICULTIES:
        made = sum(1 for s in range(20, 28) if gen.make_chart(d, s, True) is not None)
        assert made >= 4, (d, made)


def test_the_practice_toggle_and_the_share_code_open_a_two_ship_chart(g):
    v = g.call("practice", difficulty=2, seed=31, two=True)
    assert v["chart"]["two"] and v["chart"]["practice"]["two"] and v["chart"]["practice"]["code"].startswith("DR2T-")
    code = v["chart"]["practice"]["code"]
    g.call("start", chart_id="open-01")
    again = g.call("practice", code=code)
    assert again["chart"]["id"] == v["chart"]["id"] and again["svg"] == v["svg"] and "fleet" in again
    plain = g.call("practice", difficulty=2, seed=31)
    assert not plain["chart"]["two"] and plain["chart"]["practice"]["code"].startswith("DR2-")
    assert "DR3T-1K9X2" in g.call("practice", code="DR9-1")["note"]


def test_a_two_ship_practice_chart_counts_once_toward_the_practice_total_and_never_the_campaign(g):
    g.call("practice", difficulty=1, seed=5, two=True)
    chart = g.charts.get_chart(g.run["chart_id"])
    g.call("select_ship", ship=0)
    for i, legs in enumerate((chart["par_legs"], chart["ship2"]["par_legs"])):
        g.call("select_ship", ship=i)
        for leg in legs:
            g.call("set_leg", i=len(g.call("add_leg")["legs"]) - 1, **leg)
    v = g.call("sail")
    assert v["reveal"]["stars"] == 3 and g.meta["practice_seeds_played"] == 1 and g.meta["charts"] == {}
    assert "two_ships" in g.meta["flags"]


def test_the_daily_chart_is_never_a_two_ship_chart():
    import daily
    for date in ("2026-10-01", "2026-10-02", "2026-11-15", "2027-01-01"):
        assert not fleet.is_two(daily.chart_for(date))
