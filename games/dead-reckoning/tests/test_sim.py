import math

from geom import dist
from sim import (DT, clean_leg, clean_legs, compass_point, current_at, estimate, naive_legs, naive_miss, sail, score,
                 ship_velocity, unit_noise)
from tests.helpers import whole_sea_current


def leg(heading, speed, hours):
    return {"heading": heading, "speed": speed, "hours": hours}


def test_calm_open_water_is_straight_and_exact(chart):
    res = sail(chart, [leg(90, 4.0, 2.0)])
    assert res["end"] == [10.0, 2.0]
    assert res["aground"] is None and res["close"] == [] and res["events"] == []
    assert res["track"][0] == [0.0, 2.0, 2.0] and len(res["track"]) == 9
    assert res["leg_ends"] == [[2.0, 10.0, 2.0]] and res["legs_sailed"] == 1


def test_a_two_leg_plan_adds_up(chart):
    res = sail(chart, [leg(0, 4.0, 1.0), leg(90, 4.0, 1.5)])
    assert res["end"] == [8.0, 6.0] and res["hours"] == 2.5
    assert [e[0] for e in res["leg_ends"]] == [1.0, 2.5]


def test_the_sail_is_a_pure_function_of_chart_plan_and_seed(chart):
    chart["gusts"] = 0.3
    chart["currents"] = [whole_sea_current(45, 1.2)]
    plan = [leg(30, 5.0, 3.0), leg(120, 4.0, 2.0)]
    a = sail(chart, plan, seed=7)
    b = sail(chart, plan, seed=7)
    c = sail(chart, plan, seed=8)
    assert a == b
    assert a["end"] != c["end"]


def test_a_current_adds_its_set_and_drift_hand_computed(chart):
    chart["currents"] = [whole_sea_current(0, 1.0)]          # sets north at 1 kn
    res = sail(chart, [leg(90, 4.0, 2.0)])
    assert res["end"] == [10.0, 4.0]                           # 8 nm east through the water, 2 nm north set
    chart["currents"] = [whole_sea_current(90, 2.0)]
    res = sail(chart, [leg(90, 4.0, 2.0)])
    assert res["end"] == [14.0, 2.0]                           # current with the ship adds its speed


def test_a_current_zone_only_acts_inside_its_rectangle(chart):
    chart["currents"] = [dict(whole_sea_current(0, 2.0), rect=[8, 0, 12, 20])]
    res = sail(chart, [leg(90, 4.0, 4.0)])
    assert res["end"][0] > 17.9                                # still ran 16 nm east
    assert 2.0 < res["end"][1] < 8.0                           # but was pushed north while crossing x = 8..12


def test_leeway_is_five_percent_of_the_beam_wind_hand_computed(chart):
    chart["wind"] = {"from": 270, "range": [20, 20], "true": 20}
    res = sail(chart, [leg(0, 4.0, 2.0)])                      # northbound, wind from the west pushes east
    assert res["end"] == [4.0, 10.0]                           # 20 kn * 0.05 = 1 kn for 2 h
    res = sail(chart, [leg(90, 4.0, 2.0)])                     # running before the wind: no beam component
    assert res["end"] == [10.0, 2.0]
    res = sail(chart, [leg(180, 4.0, 2.0)])                    # southbound, the same wind now pushes to port
    assert res["end"] == [4.0, -6.0]


def test_leeway_goes_to_leeward_whichever_way_the_ship_heads(chart):
    chart["wind"] = {"from": 0, "range": [10, 10], "true": 10}   # wind from the north blows south
    for heading in (90, 270):
        res = sail(chart, [leg(heading, 4.0, 2.0)])
        assert res["end"][1] == 2.0 - 1.0                        # 10 kn * 0.05 * 2 h south either way


def test_no_wind_means_no_leeway(chart):
    vx, vy = ship_velocity(chart, (5, 5), 0, leg(0, 4.0, 1.0), "true")
    assert (vx, vy) == (0.0, 4.0)


def test_compass_error_turns_the_true_heading(chart):
    chart["compass"] = {"range": [10, 10], "true": 10}
    res = sail(chart, [leg(0, 4.0, 2.0)])
    sx, sy = math.sin(math.radians(10)) * 8, math.cos(math.radians(10)) * 8
    assert abs(res["end"][0] - (2 + sx)) < 0.05 and abs(res["end"][1] - (2 + sy)) < 0.05


def test_estimate_without_allowances_is_the_straight_dead_reckoning_line(chart):
    chart["currents"] = [whole_sea_current(0, 1.0)]
    chart["wind"] = {"from": 270, "range": [20, 20], "true": 20}
    chart["compass"] = {"range": [5, 5], "true": 5}
    plan = [leg(90, 4.0, 2.0)]
    est = estimate(chart, plan, allow=False)
    assert [round(est[-1][1], 2), round(est[-1][2], 2)] == [10.0, 2.0]
    assert sail(chart, plan)["end"] != [10.0, 2.0]


def test_estimate_equals_the_true_track_when_the_sea_is_exactly_as_charted(chart):
    chart["currents"] = [whole_sea_current(30, 1.0)]
    chart["wind"] = {"from": 200, "range": [10, 10], "true": 10}
    plan = [leg(45, 5.0, 3.0), leg(100, 4.0, 2.0)]
    est = estimate(chart, plan, allow=True)
    res = sail(chart, plan)
    assert [est[-1][1], est[-1][2]] == res["end"]


def test_divergence_with_a_hidden_current_grows_with_time(chart):
    zone = whole_sea_current(0, 1.0)
    zone["drift_range"] = [0.0, 0.0]                           # the chart says calm; the sea is not
    chart["currents"] = [zone]
    plan = [leg(90, 4.0, 4.0)]
    est = estimate(chart, plan, allow=True)
    tru = sail(chart, plan)["track"]
    gaps = [dist((e[1], e[2]), (t[1], t[2])) for e, t in zip(est, tru)]
    assert gaps[0] == 0 and all(b >= a for a, b in zip(gaps, gaps[1:])) and abs(gaps[-1] - 4.0) < 0.05


def test_a_long_step_cannot_jump_a_rock(chart):
    chart["hazards"] = [{"id": "r1", "kind": "rock", "name": "Little Rock", "x": 10.0, "y": 2.0, "r": 0.2, "charted": True}]
    res = sail(chart, [leg(90, 8.0, 3.0)])                     # 2 nm per step against a 0.4 nm wide rock
    assert res["aground"] and res["aground"]["hazard"] == "r1"
    assert abs(res["end"][0] - 9.8) < 0.05


def test_grounding_ends_the_sail_early_and_truncates_the_track(chart):
    chart["hazards"] = [{"id": "r1", "kind": "reef", "name": "Pike Reef", "x": 10.0, "y": 2.0, "r": 1.0, "charted": True}]
    res = sail(chart, [leg(90, 4.0, 4.0), leg(0, 4.0, 2.0)])
    assert res["aground"]["name"] == "Pike Reef"
    assert res["legs_sailed"] == 0 and res["hours"] < 2.5
    assert res["track"][-1][1:] == res["end"]
    assert res["events"][-1]["kind"] == "aground" and "aground" in res["events"][-1]["text"]


def test_land_stops_a_ship_too(chart):
    chart["land"] = [{"id": "isle", "name": "Gull Island", "poly": [[8, 0], [12, 0], [12, 6], [8, 6]]}]
    res = sail(chart, [leg(90, 4.0, 4.0)])
    assert res["aground"]["hazard"] == "isle" and 7.9 < res["end"][0] < 8.1


def test_a_close_pass_is_noted_once_and_is_not_a_grounding(chart):
    chart["hazards"] = [{"id": "r1", "kind": "rock", "name": "Needle", "x": 10.0, "y": 2.6, "r": 0.4, "charted": True}]
    res = sail(chart, [leg(90, 4.0, 4.0)])
    assert res["aground"] is None and res["close"] == ["r1"]
    close = [e for e in res["events"] if e["kind"] == "close"]
    assert len(close) == 1 and "Needle" in close[0]["text"]


def test_an_unmarked_danger_is_described_by_where_it_hissed_not_by_name(chart):
    chart["hazards"] = [{"id": "u1", "kind": "rock", "name": "Hidden Rock", "x": 10.0, "y": 2.6, "r": 0.4, "charted": False}]
    res = sail(chart, [leg(90, 4.0, 4.0)])
    text = [e for e in res["events"] if e["kind"] == "close"][0]["text"]
    assert "Hidden Rock" not in text and "hissed past" in text and "port" in text
    chart["hazards"][0]["y"] = 1.4
    text = [e for e in sail(chart, [leg(90, 4.0, 4.0)])["events"] if e["kind"] == "close"][0]["text"]
    assert "starboard" in text


def test_hitting_an_unmarked_danger_does_not_leak_its_name(chart):
    chart["hazards"] = [{"id": "u1", "kind": "rock", "name": "Hidden Rock", "x": 10.0, "y": 2.0, "r": 0.5, "charted": False}]
    res = sail(chart, [leg(90, 4.0, 4.0)])
    assert "Hidden Rock" not in res["events"][-1]["text"] and "unmarked" in res["events"][-1]["text"]
    known = sail(chart, [leg(90, 4.0, 4.0)], known=["u1"])
    assert "Hidden Rock" in known["events"][-1]["text"]


def test_predictions_never_ground_but_the_true_sail_does(chart):
    chart["hazards"] = [{"id": "r1", "kind": "reef", "name": "R", "x": 10.0, "y": 2.0, "r": 1.0, "charted": True}]
    plan = [leg(90, 4.0, 4.0)]
    assert estimate(chart, plan)[-1][1] == 18.0
    assert sail(chart, plan, model="charted")["aground"] is None
    assert sail(chart, plan)["aground"]


def test_a_tidal_stream_follows_a_cosine_with_its_period(chart):
    chart["currents"] = [whole_sea_current(90, 2.0, tide={"period": 12.0, "phase": 3.0})]
    at = lambda t: current_at(chart, (5, 5), t, "true")          # noqa: E731
    assert abs(at(3.0)[0] - 2.0) < 1e-9                          # peak flood at the phase hour
    assert abs(at(6.0)[0]) < 1e-9                                # slack three hours later
    assert abs(at(9.0)[0] + 2.0) < 1e-9                          # peak ebb, the stream reversed
    assert abs(at(3.0)[0] - at(15.0)[0]) < 1e-9                  # periodic
    chart["start_hour"] = 3.0
    assert sail(chart, [leg(0, 4.0, 0.5)])["end"][0] > 2.2       # the clock the passage starts on matters


def test_tide_fair_share_counts_steps_with_the_stream(chart):
    chart["currents"] = [whole_sea_current(90, 2.0, tide={"period": 12.0, "phase": 1.0})]
    fair = sail(chart, [leg(90, 4.0, 2.0)])["tide_fair"]
    foul = sail(chart, [leg(270, 4.0, 2.0)])["tide_fair"]
    assert fair > 0.99 and foul < 0.01
    assert sail(chart, [leg(0, 4.0, 1.0)])["tide_fair"] is not None
    chart["currents"] = []
    assert sail(chart, [leg(0, 4.0, 1.0)])["tide_fair"] is None


def test_zone_events_are_private_until_the_reveal(chart):
    chart["currents"] = [dict(whole_sea_current(90, 1.0), rect=[6, 0, 12, 20])]
    res = sail(chart, [leg(0, 4.0, 0.5), leg(90, 4.0, 3.0)])
    streams = [e for e in res["events"] if e["kind"] == "stream"]
    assert len(streams) == 2 and not any(e["public"] for e in streams)
    assert "east" in streams[0]["text"]


def test_gusts_are_bounded_repeatable_and_only_in_the_true_model(chart):
    assert all(-1.0 <= unit_noise(3, k) <= 1.0 for k in range(500))
    assert unit_noise(3, 5) == unit_noise(3, 5) and unit_noise(3, 5) != unit_noise(4, 5)
    chart["gusts"] = 0.5
    assert sail(chart, [leg(0, 4.0, 2.0)], seed=1)["end"] != [2.0, 10.0]
    assert sail(chart, [leg(0, 4.0, 2.0)], seed=1, model="charted")["end"] == [2.0, 10.0]


def test_clean_leg_forces_the_legal_grid(chart):
    assert clean_leg(chart, {"heading": 370.4, "speed": 99, "hours": 0.1}) == {"heading": 10, "speed": 8.0, "hours": 0.5}
    assert clean_leg(chart, {"heading": -1, "speed": 1, "hours": 100}) == {"heading": 359, "speed": 3.0, "hours": 12.0}
    assert clean_leg(chart, {"heading": "north", "speed": None, "hours": float("nan")})["heading"] == 0
    assert clean_leg(chart, {"heading": True})["heading"] == 0
    assert clean_leg(chart, "nope") is None
    assert clean_legs(chart, [{"heading": 1}, 5, {"heading": 2}]) == [clean_leg(chart, {"heading": 1}), clean_leg(chart, {"heading": 2})]


def test_compass_points():
    assert compass_point(0) == "north" and compass_point(359) == "north" and compass_point(100) == "east"
    assert compass_point(225) == "south-west"


# --- scoring --------------------------------------------------------------------------------------
def test_naive_steering_hits_calm_open_water(chart):
    legs = naive_legs(chart)
    res = sail(chart, legs)
    assert dist(res["end"], chart["dest"]) <= chart["arrival_radius"]
    assert naive_miss(chart) < 1.0


def test_naive_steering_misses_in_a_current_and_scoring_says_by_how_much(chart):
    chart["id"] = "test-current"
    chart["currents"] = [whole_sea_current(90, 1.5)]
    assert naive_miss(chart) > 5.0
    legs = naive_legs(chart)
    res = sail(chart, legs)
    sc = score(chart, legs, res)
    assert not sc["arrived"] and sc["stars"] == 0 and sc["beat_naive_pct"] == 0
    assert sc["criteria"][0]["ok"] is False


def test_arrival_radius_edges(chart):
    chart["id"] = "test-edges"
    chart["start"], chart["dest"] = [2.0, 2.0], [10.0, 2.0]
    for hours, expect in ((2.0, True), (2.0 + 0.5, False)):     # 8.0 nm lands on the flag; 10 nm is 2.0 nm past
        legs = [leg(90, 4.0, hours)]
        assert score(chart, legs, sail(chart, legs))["arrived"] is expect
    chart["dest"] = [8.5, 2.0]                                   # 8.0 nm run ends 1.5 nm short: exactly on the radius
    legs = [leg(90, 4.0, 2.0)]
    assert dist(sail(chart, legs)["end"], chart["dest"]) == 1.5
    assert score(chart, legs, sail(chart, legs))["arrived"]


def test_stars_need_landfall_then_time_and_safety_then_precision(chart):
    chart["id"] = "test-stars"
    chart["dest"] = [10.0, 2.0]
    perfect = [leg(90, 4.0, 2.0)]
    assert score(chart, perfect, sail(chart, perfect))["stars"] == 3
    off = [leg(90, 4.0, 2.0), leg(0, 4.0, 0.5)]                  # ends 2 nm north: outside the radius
    assert score(chart, off, sail(chart, off))["stars"] == 0
    near = [leg(90, 4.0, 2.0), leg(0, 2.0, 0.5)]                 # ends 1 nm north: arrived but not dead centre
    assert score(chart, near, sail(chart, near))["stars"] == 2
    chart["deadline"] = 1.5
    sc = score(chart, perfect, sail(chart, perfect))
    assert sc["stars"] == 1 and sc["late_h"] == 0.5 and not sc["on_time"]


def test_a_close_pass_costs_the_second_star_only_if_the_hazard_was_known(chart):
    chart["id"] = "test-close"
    chart["dest"] = [10.0, 2.0]
    chart["hazards"] = [{"id": "u1", "kind": "rock", "name": "R", "x": 6.0, "y": 2.8, "r": 0.4, "charted": False}]
    plan = [leg(90, 4.0, 2.0)]
    res = sail(chart, plan)
    assert res["close"] == ["u1"]
    assert score(chart, plan, res)["stars"] == 3                 # nobody could have known
    assert score(chart, plan, res, known=["u1"])["clear"] is False
    chart["hazards"][0]["charted"] = True
    assert score(chart, plan, res)["stars"] == 1


def test_a_grounded_passage_scores_zero_with_a_kind_reason(chart):
    chart["id"] = "test-aground"
    chart["hazards"] = [{"id": "r1", "kind": "reef", "name": "Pike Reef", "x": 8.0, "y": 2.0, "r": 1.0, "charted": True}]
    chart["dest"] = [10.0, 2.0]
    plan = [leg(90, 4.0, 2.0)]
    sc = score(chart, plan, sail(chart, plan))
    assert sc["aground"] and sc["stars"] == 0 and sc["forecast_error_nm"] is None
    assert "aground" in sc["criteria"][2]["text"]


def test_forecast_error_is_the_gap_between_belief_and_truth(chart):
    chart["id"] = "test-forecast"
    zone = whole_sea_current(0, 1.0)
    zone["drift_range"] = [0.0, 0.0]
    chart["currents"] = [zone]
    chart["dest"] = [10.0, 2.0]
    chart["speeds"] = [4.0, 4.0]
    plan = [leg(90, 4.0, 2.0)]
    sc = score(chart, plan, sail(chart, plan))
    assert sc["forecast_error_nm"] == 2.0 and sc["naive_miss_nm"] == 2.0 and sc["beat_naive_pct"] == 0


def test_step_constant_is_a_quarter_hour():
    assert DT == 0.25


def test_a_leg_at_speed_zero_lies_at_anchor_and_holds_her_place(chart):
    chart["currents"] = [whole_sea_current(90, 2.0)]
    chart["wind"] = {"from": 270, "range": [20, 20], "true": 20}
    res = sail(chart, [leg(90, 0.0, 2.0)])
    assert res["end"] == [2.0, 2.0] and res["aground"] is None
    assert clean_leg(chart, {"heading": 5, "speed": 0, "hours": 1}) == {"heading": 5, "speed": 0.0, "hours": 1.0}
    assert clean_leg(chart, {"heading": 5, "speed": -3, "hours": 1})["speed"] == 0.0
    assert clean_leg(chart, {"heading": 5, "speed": 0.4, "hours": 1})["speed"] == 3.0       # a moving ship keeps the speed range


def test_waiting_for_the_tide_changes_where_the_same_leg_ends(chart):
    chart["currents"] = [whole_sea_current(90, 2.0, tide={"period": 12.0, "phase": 0.0})]
    go = [leg(0, 4.0, 2.0)]
    early = sail(chart, go)["end"]
    late = sail(chart, [leg(0, 0.0, 6.0)] + go)["end"]
    assert early[0] > 2.0 + 1.0 and late[0] < 2.0                  # fair stream at once, foul after the turn


def test_a_plot_through_an_anchored_leg_does_not_move(chart):
    est = estimate(chart, [leg(0, 0.0, 1.5)], allow=True)
    assert est[-1][1:3] == [2.0, 2.0]
