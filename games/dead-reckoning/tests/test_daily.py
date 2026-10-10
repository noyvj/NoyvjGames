"""The Daily Chart (M-5b-11): one deterministic, solver-proven chart per UTC date, from the date text alone."""

import copy
import json
import re
from pathlib import Path

import pytest

import charts
import daily
import gen
import progress  # noqa: F401  (imported so a circular import would show up here)
import sim
import state

GAME = Path(__file__).resolve().parent.parent
TODAY = "2026-10-11"


def dates(n, start=daily.EPOCH):
    return [daily.add_days(start, i) for i in range(n)]


@pytest.fixture(autouse=True)
def fresh():
    import game
    daily._cache.clear()
    game.today = None
    yield
    game.today = None


# --- dates and ids ------------------------------------------------------------------------------------------
def test_dates_are_strict_and_the_playable_range_is_epoch_to_today():
    for bad in ("2026-02-30", "2026-13-01", "2026-1-01", "20261001", "", None, 5, "2026-10-01T00:00", "２０２６-10-01"):
        assert not daily.valid_date(bad), bad
    assert daily.playable(daily.EPOCH, TODAY) and daily.playable(TODAY, TODAY)
    assert not daily.playable("2026-09-30", TODAY) and not daily.playable("2026-10-12", TODAY) and not daily.playable("x", TODAY)
    assert daily.day_number(daily.EPOCH) == 1 and daily.day_number(TODAY) == 11


def test_only_real_dates_from_the_epoch_are_daily_chart_ids():
    assert daily.is_daily_id("daily-2026-10-05") and daily.date_of("daily-2026-10-05") == "2026-10-05"
    for bad in ("daily-2026-09-30", "daily-2026-02-30", "daily-2026-10-5", "practice-3-abc", "daily-", "", None, 7, "Daily-2026-10-05", "daily-2026-10-05x"):
        assert not daily.is_daily_id(bad), bad
        if bad != "practice-3-abc":
            assert charts.get_chart(bad) is None


def test_the_module_never_reads_the_clock():
    source = (GAME / "daily.py").read_text(encoding="utf-8")
    assert not re.search(r"\b(time\.(time|sleep|monotonic)|datetime\.now|\.today\(|utcnow|random\.|import random|import time\b)", source)
    with pytest.raises(ValueError):
        daily.chart_for("not a date")


# --- determinism ----------------------------------------------------------------------------------------------
def test_a_date_gives_the_same_chart_every_time_and_in_any_order():
    first = {d: json.dumps(daily.chart_for(d), sort_keys=True) for d in dates(25)}
    daily._cache.clear()
    gen._CACHE.clear()
    for d in reversed(dates(25)):
        assert json.dumps(daily.chart_for(d), sort_keys=True) == first[d]
    a = daily.chart_for("2026-10-09")
    a["hazards"].append("poison")
    assert "poison" not in daily.chart_for("2026-10-09")["hazards"]                # a fresh copy each call


def test_different_dates_are_different_seas_and_every_level_comes_up():
    specs = [daily.spec(d) for d in dates(300)]
    assert {s["difficulty"] for s in specs} == set(gen.DIFFICULTIES)
    assert len({(s["difficulty"], s["seed"]) for s in specs}) >= 298
    layouts = {json.dumps([daily.chart_for(d)["start"], daily.chart_for(d)["dest"]]) for d in dates(40)}
    assert len(layouts) >= 38


def test_the_daily_chart_borrows_the_generator_but_has_its_own_id_and_never_a_practice_code():
    c = daily.chart_for("2026-10-05")
    assert c["id"] == "daily-2026-10-05" and c["name"] == "Daily Chart 5" and c["chapter"] == "daily"
    assert not gen.is_practice_id(c["id"]) and gen.parse(c["id"]) is None
    assert charts.get_chart(c["id"])["id"] == c["id"] and charts.is_unlocked(c["id"], {})
    assert charts.par_legs(c["id"]) == c["par_legs"]


# --- the fairness bar --------------------------------------------------------------------------------------------
def test_every_daily_chart_for_300_days_is_solved_by_its_par_plan_with_three_stars():
    for d in dates(300):
        c = daily.chart_for(d)
        legs = c["par_legs"]
        res = sim.sail(c, legs, seed=c["seed"])
        sc = sim.score(c, legs, res, used_helpers=False)
        assert res["aground"] is None and not res["close"], d
        assert sc["arrived"] and sc["on_time"] and sc["clear"] and sc["stars"] == 3, d
        assert c["deadline"] >= sim.plan_hours(legs) + 1.5 - 1e-9, d
        assert c["naive_fails"] in (True, False) and c["tries"] >= 1 and c["waypoints"], d


def test_the_printed_figures_followed_carefully_also_make_landfall_on_every_daily():
    import solver
    from geom import dist
    for d in dates(60):
        c = daily.chart_for(d)
        wait = c["par_legs"][0]["hours"] if c["par_legs"][0]["speed"] == 0 else 0.0
        legs, _ = solver.route(c, [tuple(p) for p in c["waypoints"]], model="charted", seed=c["seed"], wait=wait)
        res = sim.sail(c, legs, seed=c["seed"])
        assert res["aground"] is None and dist(res["end"], c["dest"]) <= c["arrival_radius"], d


def test_a_seed_that_fails_the_daily_bar_is_skipped_for_the_next_one(monkeypatch):
    real = daily._accept
    calls = []

    def stingy(chart):
        calls.append(chart["id"])
        return False if len(calls) < 3 else real(chart)

    monkeypatch.setattr(daily, "_accept", stingy)
    c = daily.chart_for("2027-02-03")
    assert c["tries"] == 3 and len(calls) == 3


# --- records ---------------------------------------------------------------------------------------------------------
def test_merge_record_keeps_the_best_stars_and_smallest_miss_and_counts_tries():
    r = daily.merge_record(None, 1, 1.4, True)
    r = daily.merge_record(r, 0, 9.0, False)
    assert r == {"stars": 1, "best_error_nm": 1.4, "tries": 2}
    r = daily.merge_record(r, 3, 0.4, True)
    assert r == {"stars": 3, "best_error_nm": 0.4, "tries": 3}
    assert daily.better({"stars": 1, "best_error_nm": None, "tries": 2}, {"stars": 2, "best_error_nm": 0.6, "tries": 1}) == {"stars": 2, "best_error_nm": 0.6, "tries": 2}


def test_clean_days_drops_junk_one_entry_at_a_time():
    raw = {"2026-10-05": {"stars": 3, "best_error_nm": 0.4, "tries": 2}, "2026-10-06": {"stars": 9, "best_error_nm": -1, "tries": 0},
           "nope": {"stars": 1, "best_error_nm": 1, "tries": 1}, "2026-09-01": {"stars": 1, "best_error_nm": 1, "tries": 1},
           "2026-10-07": {"stars": "x", "best_error_nm": 1, "tries": 1}, "2026-10-08": [1], "2026-10-09": {"stars": True, "best_error_nm": None, "tries": 1},
           "2026-10-10": {"stars": 2, "best_error_nm": None, "tries": 4}, 5: {}}
    assert daily.clean_days(raw) == {"2026-10-05": {"stars": 3, "best_error_nm": 0.4, "tries": 2},
                                     "2026-10-10": {"stars": 2, "best_error_nm": None, "tries": 4}}
    assert daily.clean_days("junk") == {} and daily.clean_days(None) == {}


def test_the_leaderboard_hook_only_shapes_an_entry():
    assert daily.leaderboard_entry("2026-10-05", {"stars": 3, "best_error_nm": 0.4, "tries": 2}) == {
        "board": "dead-reckoning-daily-chart", "date": "2026-10-05", "stars": 3, "error_nm": 0.4}


def test_the_tally_counts_open_days_and_has_no_streak():
    days = {"2026-10-02": {"stars": 3, "best_error_nm": 0.1, "tries": 1}, "2026-10-09": {"stars": 1, "best_error_nm": 1.0, "tries": 1},
            "2026-10-20": {"stars": 3, "best_error_nm": 0.1, "tries": 1}}
    assert daily.tally(days, TODAY) == {"open": 11, "played": 2, "three": 1}
    assert daily.tally(days, "2026-09-01") == {"open": 0, "played": 0, "three": 0}


# --- the game flow ------------------------------------------------------------------------------------------------------
def play_par(g, date, today=TODAY):
    g.call("start_daily", date=date, today=today)
    for i, leg in enumerate(charts.par_legs("daily-" + date)):
        g.call("add_leg", today=today)
        g.call("set_leg", i=i, heading=leg["heading"], speed=leg["speed"], hours=leg["hours"], today=today)
    return g.call("sail", today=today)


def test_the_view_offers_the_daily_only_when_the_date_is_passed_in(g):
    assert g.call("open")["daily"] is None
    d = g.call("open", today=TODAY)["daily"]
    assert d["open"] and d["number"] == 11 and d["tally"] == {"open": 11, "played": 0, "three": 0} and d["record"] is None and d["active"] is None
    assert g.call("open", today="2026-09-01")["daily"]["open"] is False


def test_start_daily_checks_the_date(g):
    for date, word in (("2026-10-12", "not out"), ("2026-09-30", "no daily"), ("garbage", "no daily"), (None, "no daily")):
        v = g.call("start_daily", date=date, today=TODAY)
        assert word in v["note"] and not v["chart"]["id"].startswith("daily-")
    g.today = None
    assert "not known" in g.call("start_daily", date="2026-10-05")["note"]


def test_sailing_a_daily_changes_only_the_dates_own_record(g):
    g.call("open", today=TODAY)
    before = {k: v for k, v in g.get_state().items() if k not in ("run", "meta", "achievements_earned")}
    view = play_par(g, "2026-10-05")
    assert view["phase"] == "reveal" and view["reveal"]["stars"] == 3 and view["chart"]["daily"]["date"] == "2026-10-05"
    assert view["daily"]["record"] is None and view["daily"]["days"]["2026-10-05"]["stars"] == 3
    assert view["daily"]["entry"]["board"] == "dead-reckoning-daily-chart"
    meta = g.meta
    assert meta["practice_seeds_played"] == 0 and meta["charts"] == {} and meta["daily_days"]["2026-10-05"]["tries"] == 1
    assert view["progress"]["practice_played"] == 0 and view["progress"]["cleared"] == 0
    assert view["reveal"]["next_chart"] is None and view["reveal"]["best_stars"] == 3
    after = {k: v for k, v in g.get_state().items() if k not in ("run", "meta", "achievements_earned")}
    assert after == before


def test_a_replay_keeps_the_best_and_any_date_is_open_in_any_order(g):
    g.call("open", today=TODAY)
    play_par(g, "2026-10-10")
    play_par(g, "2026-10-02")
    g.call("retry", today=TODAY)
    g.call("clear", today=TODAY)
    g.call("add_leg", today=TODAY)
    g.call("sail", today=TODAY)                       # a default leg: nowhere near the flag
    rec = g.meta["daily_days"]["2026-10-02"]
    assert rec["stars"] == 3 and rec["tries"] == 2
    v = g.call("open", today=TODAY)["daily"]
    assert v["tally"] == {"open": 11, "played": 2, "three": 2}
    assert g.call("start_daily", date="2026-10-07", today=TODAY)["chart"]["id"] == "daily-2026-10-07"      # nothing was gated


def test_a_daily_sail_is_the_same_passage_for_everyone(g):
    a = play_par(g, "2026-10-03")["reveal"]["points"]
    g.call("reset")
    g.today = None
    daily._cache.clear()
    gen._CACHE.clear()
    assert play_par(g, "2026-10-03")["reveal"]["points"] == a


# --- saves --------------------------------------------------------------------------------------------------------------------
def test_old_saves_load_unchanged_and_a_fresh_save_has_no_daily_keys(g):
    assert "daily_days" not in json.dumps(g.get_state())
    g.load_state({"schema": 1, "meta": {"charts": {"open-01": {"stars": 2}}, "practice_seeds_played": 3}})
    assert g.meta["daily_days"] == {} and g.meta["practice_seeds_played"] == 3
    assert "daily_days" not in json.dumps(g.get_state())


def test_daily_results_and_an_open_daily_survive_a_save_and_load(g):
    g.call("open", today=TODAY)
    play_par(g, "2026-10-05")
    g.call("start_daily", date="2026-10-06", today=TODAY)
    g.call("add_leg", today=TODAY)
    saved = json.loads(json.dumps(g.get_state()))
    assert saved["meta"]["daily_days"]["2026-10-05"]["stars"] == 3 and saved["run"]["chart_id"] == "daily-2026-10-06"
    g.call("reset")
    g.load_state(saved)
    assert g.meta["daily_days"]["2026-10-05"]["stars"] == 3
    v = g.call("open", today=TODAY)
    assert v["chart"]["id"] == "daily-2026-10-06" and len(v["legs"]) == 1 and v["daily"]["active"] == "2026-10-06"
    assert json.dumps(g.get_state(), sort_keys=True) == json.dumps(saved, sort_keys=True)


def test_merging_two_saves_keeps_the_better_of_each_date_in_either_order():
    a = state.new_meta()
    b = state.new_meta()
    a["daily_days"] = {"2026-10-05": {"stars": 1, "best_error_nm": 1.2, "tries": 3}, "2026-10-06": {"stars": 2, "best_error_nm": None, "tries": 1}}
    b["daily_days"] = {"2026-10-05": {"stars": 3, "best_error_nm": 0.4, "tries": 1}}
    one, two = state.merge_meta(a, b), state.merge_meta(b, a)
    assert one["daily_days"] == two["daily_days"]
    assert one["daily_days"]["2026-10-05"] == {"stars": 3, "best_error_nm": 0.4, "tries": 3} and "2026-10-06" in one["daily_days"]


def test_a_tampered_daily_save_is_dropped_field_by_field(g):
    g.load_state({"meta": {"daily_days": {"2026-10-05": {"stars": 2, "best_error_nm": 0.8, "tries": 1}, "2026-10-06": {"stars": 9},
                                          "bad": {"stars": 1, "best_error_nm": 0, "tries": 1}, "2020-01-01": {"stars": 1, "best_error_nm": 0, "tries": 1}}}})
    assert g.meta["daily_days"] == {"2026-10-05": {"stars": 2, "best_error_nm": 0.8, "tries": 1}}
    for junk in ("x", [], None, {"2026-10-05": 5}):
        g.call("reset")
        g.load_state({"meta": {"daily_days": junk}})
        assert g.meta["daily_days"] == {}
    g.load_state({"run": {"chart_id": "daily-2026-02-30", "legs": [{"heading": 1, "speed": 4, "hours": 1}]}})
    assert g.call("open")["chart"]["id"] != "daily-2026-02-30"


def test_a_saved_daily_run_for_a_future_date_is_dropped_when_the_view_gives_the_date(g):
    g.load_state({"run": {"chart_id": "daily-2026-10-20", "legs": [{"heading": 90, "speed": 4, "hours": 1}]}})
    assert g.run["chart_id"] == "daily-2026-10-20"
    v = g.call("open", today=TODAY)
    assert not v["chart"]["id"].startswith("daily-")


def test_copy_of_the_chart_is_not_the_cached_one():
    a = daily.chart_for("2026-10-04")
    b = copy.deepcopy(a)
    assert a == b and daily.chart_for("2026-10-04") is not daily.chart_for("2026-10-04")
