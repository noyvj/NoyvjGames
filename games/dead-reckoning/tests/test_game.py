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
    assert t["legs"] == 1 and t["hours"] == 1.0 and t["distance"] == 5.0 and t["deadline"] == 6.0 and not t["over"]
    for _ in range(3):
        v = g.call("nudge", i=0, field="hours", delta=3)
    assert v["totals"]["over"] and v["totals"]["hours"] == 10.0


def test_the_naive_helper_adds_a_straight_leg_and_is_remembered(g):
    g.call("allow", value=False)
    v = g.call("helper", kind="naive", target="flag")
    assert len(v["legs"]) == 1 and g.run["helpers"] == ["naive"]
    assert v["totals"]["plot_miss"] < 1.0               # the plain dead-reckoning plot ends at the flag; the sea disagrees


def test_the_allowing_for_the_chart_helper_is_locked_until_three_charts_are_cleared(g):
    g.call("start", chart_id="open-03")
    v = g.call("helper", kind="current", target="flag")
    assert v["legs"] == [] and not v["helpers"]["current"] and not v["helpers"]["current_unlocked"]
    clear_three(g)
    g.call("start", chart_id="open-03")
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
    assert g.meta["charts"]["open-01"]["attempts"] == 1
    assert g.call("sail")["phase"] == "reveal" and g.meta["charts"]["open-01"]["attempts"] == 1    # never counted twice


def test_retry_keeps_the_legs_and_restart_empties_them(g):
    g.call("add_leg")
    g.call("sail")
    v = g.call("retry")
    assert v["phase"] == "plan" and len(v["legs"]) == 1
    g.call("sail")
    v = g.call("restart")
    assert v["phase"] == "plan" and v["legs"] == []


def test_a_good_plan_earns_three_stars_and_is_remembered(g):
    legs = g.charts.par_legs("open-02")
    g.call("start", chart_id="open-02")
    for leg in legs:
        v = g.call("add_leg")
        g.call("set_leg", i=len(v["legs"]) - 1, **leg)
    v = g.call("sail")
    assert v["reveal"]["stars"] == 3 and v["reveal"]["arrived"] and v["reveal"]["title"] == "Landfall"
    rec = g.meta["charts"]["open-02"]
    assert rec["stars"] == 3 and rec["attempts"] == 1 and rec["trusted"] and rec["best_error_nm"] < 0.75
    assert "landfall" in g.meta["flags"] and "trusted" in g.meta["flags"]
    assert v["reveal"]["log"] == g.charts.get_chart("open-02")["log"]["arrived"]


def test_state_is_minimal_by_default_and_round_trips(g):
    assert g.get_state() == {"schema": 1}
    g.call("add_leg")
    g.call("set_leg", i=0, heading=33, speed=4.5, hours=2.5)
    g.call("allow", value=False)
    saved = g.get_state()
    assert saved["run"] == {"chart_id": "open-01", "legs": [{"heading": 33, "speed": 4.5, "hours": 2.5}], "allow": False}
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
    for junk in (None, 5, "x", [], {"meta": 5, "run": []}, {"meta": {"charts": {"open-01": 7, "nowhere": {"stars": 3}}}},
                 {"run": {"chart_id": "open-01", "legs": [None, 3, {"heading": float("nan")}, {"heading": 90, "speed": "fast", "hours": 2}], "phase": "weird",
                          "mode": 9, "seed": -4, "allow": "no", "helpers": ["naive", "x", 3]}},
                 {"run": {"chart_id": "x" * 500}}, {"run": {"chart_id": "open-01", "legs": "none"}}):
        g.load_state(junk)
        assert g.call("open")["phase"] in ("plan", "reveal")
    g.call("reset")
    g.load_state({"run": {"chart_id": "open-01", "legs": [None, {"heading": 90, "speed": "fast", "hours": 2}], "helpers": ["naive", "x"], "seed": -4}})
    assert g.run["legs"] == [{"heading": 90, "speed": 5.0, "hours": 2.0}] and g.run["helpers"] == ["naive"] and g.run["seed"] == 0


def test_loading_merges_records_by_taking_the_better_of_each(g):
    g.meta["charts"]["open-01"] = {"best_error_nm": 2.0, "stars": 1, "attempts": 5, "discovered": [], "par_seen": False, "trusted": False}
    g.load_state({"meta": {"charts": {"open-01": {"best_error_nm": 1.0, "stars": 3, "attempts": 2, "trusted": True}}, "flags": ["landfall", "bogus"]}})
    rec = g.meta["charts"]["open-01"]
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
    assert abs(dist(end, g.charts.get_chart("open-01")["dest"]) - v["totals"]["plot_miss"]) < 0.06


# --- milestone 4: the campaign ---------------------------------------------------------------------
def test_the_picker_lists_chapters_with_stars_and_locks(g):
    v = g.call("open")
    picker = v["picker"]
    assert [c["id"] for c in picker] == ["open", "wind", "fixes", "fog", "tides", "compass", "ships"]
    assert picker[0]["unlocked"] and picker[0]["total"] == 6 and picker[0]["cleared"] == 0 and picker[0]["lock_text"] == ""
    assert not picker[1]["unlocked"] and "Clear 4 charts in Open water" in picker[1]["lock_text"]
    assert [c["current"] for c in picker[0]["charts"]] == [True, False, False, False, False, False]
    assert "error" in g.call("start", chart_id="wind-01")
    for cid in ("open-01", "open-02", "open-03", "open-04"):
        g.meta["charts"][cid] = dict(g.state.new_record(), stars=1)
    assert g.call("open")["picker"][1]["unlocked"]
    assert g.call("start", chart_id="wind-01")["chart"]["id"] == "wind-01"


def test_a_new_game_opens_the_first_chart_not_yet_cleared(g):
    g.meta["charts"]["open-01"] = dict(g.state.new_record(), stars=2)
    g.run = None
    assert g.call("open")["chart"]["id"] == "open-02"


def test_next_chart_only_after_a_landfall_and_only_when_open(g):
    g.call("start", chart_id="open-02")
    assert g.call("next_chart")["chart"]["id"] == "open-02"                # not cleared yet: nothing happens
    for leg in g.charts.par_legs("open-02"):
        n = len(g.call("add_leg")["legs"])
        g.call("set_leg", i=n - 1, **leg)
    v = g.call("sail")
    assert v["reveal"]["next_chart"] == {"id": "open-03", "name": "Gentle Set"}
    v = g.call("next_chart")
    assert v["phase"] == "plan" and v["chart"]["id"] == "open-03" and v["legs"] == []


def test_the_par_plan_is_offered_only_after_a_first_attempt_and_can_be_loaded(g):
    g.call("start", chart_id="open-02")
    assert g.call("show_par")["phase"] == "plan"
    assert g.meta["charts"] == {}
    g.call("add_leg")
    v = g.call("sail")
    assert v["reveal"]["par"] == {"available": True, "shown": False} and "dr-par-track" not in v["svg"]
    v = g.call("show_par")
    par = v["reveal"]["par"]
    assert par["shown"] and len(par["lines"]) == len(g.charts.par_legs("open-02")) and "dr-par-track" in v["svg"]
    assert g.meta["charts"]["open-02"]["par_seen"]
    v = g.call("use_par")
    assert v["phase"] == "plan" and v["legs"] == g.charts.par_legs("open-02") and g.run["helpers"] == ["par"]
    v = g.call("sail")
    assert v["reveal"]["stars"] == 3
    assert not g.meta["charts"]["open-02"]["trusted"] and "trusted" not in g.meta["flags"]       # a loaded par is not your own plan


def test_the_captains_log_gathers_intro_and_outcome_per_chart(g):
    v = g.call("open")
    assert v["story"]["intro"] == g.charts.get_chart("open-01")["intro"]
    assert [e["id"] for e in v["story"]["log"]] == ["open-01"]
    for leg in g.charts.par_legs("open-01"):
        n = len(g.call("add_leg")["legs"])
        g.call("set_leg", i=n - 1, **leg)
    g.call("sail")
    entry = g.call("open")["story"]["log"][0]
    assert g.charts.get_chart("open-01")["log"]["arrived"] in entry["text"]


def test_the_log_line_matches_how_the_passage_ended(g):
    g.call("start", chart_id="open-02")
    g.call("add_leg")
    miss = g.call("sail")["reveal"]
    assert miss["log"] == g.charts.get_chart("open-02")["log"]["missed"] or miss["log"] == g.charts.get_chart("open-02")["log"]["aground"]


# --- milestone 6: fog, tides, compass ------------------------------------------------------------------
def open_everything(g):
    for cid in g.charts.ORDER:
        g.meta["charts"][cid] = dict(g.state.new_record(), stars=1)


def test_add_wait_appends_an_hour_at_anchor(g):
    v = g.call("add_wait")
    assert v["legs"] == [{"heading": 0, "speed": 0.0, "hours": 1.0}]
    assert v["totals"]["distance"] == 0.0 and v["totals"]["hours"] == 1.0
    g.call("nudge", i=0, field="hours", delta=2)
    assert g.run["legs"][0]["hours"] == 3.0
    assert g.call("set_leg", i=0, speed=0)["legs"][0]["speed"] == 0.0


def test_an_unmarked_danger_is_found_by_hitting_it_and_stays_on_the_chart(g):
    import solver
    open_everything(g)
    g.call("start", chart_id="fog-01")
    chart = g.charts.get_chart("fog-01")
    plan = g.call("open")
    assert "Gong Rock" not in plan["svg"] and "Gong Rock" not in " ".join(plan["notes"])
    leg = solver.shoot(chart, chart["start"], (10.0, 10.0), model="true", speed=5.0)
    g.call("set_mode", mode="plan")
    g.call("add_leg")
    g.call("set_leg", i=0, **leg)
    v = g.call("sail")
    assert v["reveal"]["aground"] and "unmarked danger" in " ".join(e["text"] for e in v["reveal"]["events"])
    assert g.meta["charts"]["fog-01"]["discovered"] == ["gong-rock"]
    assert "Gong Rock (found)" in v["svg"] and "Far Reef" not in v["svg"]          # only what was found is drawn, even on the reveal
    v = g.call("restart")
    assert "Gong Rock (found)" in v["svg"] and any("Gong Rock" in n for n in v["notes"])
    assert "Far Reef" not in v["svg"]


def test_a_close_pass_in_the_fog_is_reported_but_costs_no_star_the_first_time(g):
    open_everything(g)
    g.call("start", chart_id="fog-01")
    chart = g.charts.get_chart("fog-01")
    g.call("set_mode", mode="plan")
    legs = g.charts.par_legs("fog-01")
    for leg in legs:
        n = len(g.call("add_leg")["legs"])
        g.call("set_leg", i=n - 1, **leg)
    assert g.call("sail")["reveal"]["stars"] == 3
    assert chart["hazards"][0]["charted"] is False


def test_fog_watches_report_what_hissed_past_and_no_landmarks(g):
    open_everything(g)
    g.call("start", chart_id="fog-01")
    g.call("add_leg")
    g.call("set_leg", i=0, heading=95, speed=5.0, hours=1.5)       # ends a little short of the rock, passing it close to port
    v = g.call("sail")
    assert v["phase"] == "plan" and v["watch"]["fog"] and v["watch"]["readings"] == []
    g.call("add_leg")
    g.call("set_leg", i=1, heading=85, speed=4.0, hours=1.0)
    v = g.call("sail")
    texts = " ".join(v["watch"]["log"]) if v["phase"] == "plan" else " ".join(e["text"] for e in v["reveal"]["events"])
    assert "hissed past" in texts or "aground" in texts


def test_the_tide_timetable_and_the_waiting_par_work_through_the_game(g):
    open_everything(g)
    v = g.call("start", chart_id="tide-01")
    assert any(n.startswith("Hour") and "stream" in n for n in v["notes"])
    legs = g.charts.par_legs("tide-01")
    assert legs[0]["speed"] == 0.0
    for leg in legs:
        n = len(g.call("add_leg")["legs"])
        g.call("set_leg", i=n - 1, **leg)
    v = g.call("sail")
    assert v["reveal"]["stars"] == 3 and "riding_tide" in g.meta["flags"] and "set_and_drift" in g.meta["flags"] or "riding_tide" in g.meta["flags"]


def test_compass_error_is_part_of_the_plot_when_allowed_and_ignored_when_not(g):
    open_everything(g)
    g.call("start", chart_id="comp-01")
    g.call("add_leg")
    g.call("set_leg", i=0, heading=45, speed=5.0, hours=2.0)
    with_chart = g.call("open")["totals"]["plot_end"]
    without = g.call("allow", value=False)["totals"]["plot_end"]
    assert with_chart != without


# --- milestone 8: practice ------------------------------------------------------------------------------
def test_a_practice_chart_opens_from_a_difficulty_and_has_a_share_code(g):
    v = g.call("practice", difficulty=2, seed=1234)
    info = v["chart"]["practice"]
    assert info["difficulty"] == 2 and info["code"] == "DR2-YA" or info["code"].startswith("DR2-")
    assert v["chart"]["id"].startswith("practice-2-") and v["phase"] == "plan" and v["legs"] == []
    again = g.call("practice", code=info["code"])
    assert again["chart"]["id"] == v["chart"]["id"] and again["svg"] == v["svg"]


def test_a_bad_code_leaves_the_game_where_it_was_with_a_note(g):
    before = g.call("open")["chart"]["id"]
    v = g.call("practice", code="DR9-NOPE")
    assert v["chart"]["id"] == before and "not a practice code" in v["note"]
    assert g.call("practice", difficulty=9)["chart"]["id"] == before
    assert g.call("open")["note"] == ""


def test_practice_without_a_seed_is_repeatable_from_what_the_player_has_done(g):
    a = g.call("practice", difficulty=3)["chart"]["id"]
    g.call("reset")
    assert g.call("practice", difficulty=3)["chart"]["id"] == a


def test_a_practice_passage_counts_once_and_keeps_no_campaign_record(g):
    g.call("practice", difficulty=1, seed=99)
    g.call("add_leg")
    v = g.call("sail")
    assert v["phase"] == "reveal" and g.meta["practice_seeds_played"] == 1 and g.meta["charts"] == {}
    assert v["progress"]["practice_played"] == 1
    g.call("retry")
    g.call("sail")
    assert g.meta["practice_seeds_played"] == 1
    g.call("practice", difficulty=1, seed=100)
    g.call("add_leg")
    g.call("sail")
    assert g.meta["practice_seeds_played"] == 2 and g.get_state()["meta"]["practice_seeds_played"] == 2


def test_the_practice_par_is_offered_after_an_attempt_and_makes_three_stars(g):
    g.call("practice", difficulty=2, seed=555)
    assert g.call("show_par")["phase"] == "plan"
    g.call("add_leg")
    v = g.call("sail")
    assert v["reveal"]["par"] == {"available": True, "shown": False} and v["reveal"]["next_chart"] is None
    assert g.call("show_par")["reveal"]["par"]["shown"]
    v = g.call("use_par")
    assert v["legs"] == g.charts.par_legs(v["chart"]["id"]) and g.run["helpers"] == ["par"]
    assert g.call("sail")["reveal"]["arrived"]


def test_practice_flags_are_earned_but_the_campaign_records_stay_clean(g):
    g.call("practice", difficulty=1, seed=321)
    for leg in g.charts.par_legs(g.run["chart_id"]):
        n = len(g.call("add_leg")["legs"])
        g.call("set_leg", i=n - 1, **leg)
    v = g.call("sail")
    assert v["reveal"]["arrived"] and "landfall" in g.meta["flags"] and g.meta["charts"] == {}
    assert g.meta["best"]["smallest_final_error_nm"] is not None


def test_a_practice_run_survives_save_and_load_including_what_was_found(g):
    g.call("practice", difficulty=5, seed=2024)
    chart = g.charts.get_chart(g.run["chart_id"])
    unmarked = [h for h in chart["hazards"] if not h["charted"]]
    assert unmarked
    import solver
    h = unmarked[0]
    leg = solver.shoot(chart, chart["start"], (h["x"], h["y"]), model="true", speed=5.0)
    g.call("set_mode", mode="plan")
    g.call("add_leg")
    g.call("set_leg", i=0, **dict(leg, hours=min(12.0, leg["hours"] + 2.0)))
    g.call("sail")
    assert g.run["found"]
    saved = json.loads(json.dumps(g.get_state()))
    assert saved["run"]["counted"] is True and saved["run"]["found"] == g.run["found"]
    before = g.call("open")
    g.call("reset")
    g.load_state(saved)
    after = g.call("open")
    assert after["svg"] == before["svg"] and after["reveal"] == before["reveal"]


def test_a_saved_practice_id_that_cannot_be_made_is_dropped(g):
    g.load_state({"run": {"chart_id": "practice-9-zzz", "legs": []}})
    assert g.run is None or not g.run["chart_id"].startswith("practice-9")
    g.load_state({"run": {"chart_id": "practice-3-a", "legs": [{"heading": 10, "speed": 5, "hours": 1}], "found": ["h0", 4, "nope"], "counted": "yes", "par": 1}})
    assert g.run["chart_id"] == "practice-3-a" and g.run["counted"] is False and g.run["par"] is False
    assert all(isinstance(x, str) for x in g.run["found"])
