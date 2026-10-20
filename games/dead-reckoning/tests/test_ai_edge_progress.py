import progress
from state import FLAGS, new_meta, new_record


def meta_with(stars=None, flags=(), practice=0):
    m = new_meta()
    for cid, n in (stars or {}).items():
        m["charts"][cid] = dict(new_record(), stars=n)
    m["flags"] = [f for f in FLAGS if f in flags]
    m["practice_seeds_played"] = practice
    return m


def test_hazards_on_the_line_with_empty_list_returns_zero():
    chart = {"start": (0, 0), "dest": (10, 10), "hazards": []}
    assert progress.hazards_on_the_line(chart) == 0


def test_hazards_on_the_line_at_exact_margin_threshold():
    # LINE_MARGIN is 0.5. A hazard at distance exactly r + 0.5 should be counted.
    chart = {"start": (0, 0), "dest": (10, 0), "hazards": [{"x": 5, "y": 0.5, "r": 0}]}
    assert progress.hazards_on_the_line(chart) == 1


def test_hazards_on_the_line_just_outside_margin_threshold():
    # Distance 0.6 > r(0) + LINE_MARGIN(0.5), so not counted.
    chart = {"start": (0, 0), "dest": (10, 0), "hazards": [{"x": 5, "y": 0.6, "r": 0}]}
    assert progress.hazards_on_the_line(chart) == 0


def test_has_tide_with_no_currents_returns_false():
    chart = {"currents": []}
    assert progress.has_tide(chart) is False


def test_has_tide_with_currents_but_missing_tide_key_returns_false():
    chart = {"currents": [{"drift": 1.0, "set": 90}]}
    assert progress.has_tide(chart) is False


def test_record_outcome_with_scored_false_skips_chart_update():
    meta = new_meta()
    chart = {"id": "edge-01", "currents": []}
    run = {"legs": [], "helpers": 0, "legs2": None}
    res = {"aground": False, "close": [], "groundings": []}
    sc = {"stars": 3, "arrived": True, "miss_nm": 0.1, "forecast_error_nm": None, "naive_miss_nm": 0, "beat_naive_pct": 0, "tide_fair": 0, "aground": False}
    progress.record_outcome(meta, chart, run, res, sc, scored=False)
    assert "edge-01" not in meta["charts"]


def test_record_outcome_with_zero_distance_and_arrived_updates_best_route():
    meta = new_meta()
    chart = {"id": "edge-02", "currents": []}
    run = {"legs": [], "helpers": 0, "legs2": None}
    res = {"aground": False, "close": [], "groundings": []}
    sc = {"stars": 3, "arrived": True, "miss_nm": 0.1, "forecast_error_nm": None, "naive_miss_nm": 0, "beat_naive_pct": 0, "tide_fair": 0, "aground": False}
    progress.record_outcome(meta, chart, run, res, sc, scored=True)
    assert meta["best"]["longest_route_nm"] == 0.0


def test_record_outcome_with_fix_taken_sets_first_fix_flag():
    meta = new_meta()
    chart = {"id": "edge-03", "currents": []}
    run = {"legs": [], "helpers": 0, "legs2": None}
    res = {"aground": False, "close": [], "groundings": []}
    sc = {"stars": 1, "arrived": True, "miss_nm": 0.1, "forecast_error_nm": None, "naive_miss_nm": 0, "beat_naive_pct": 0, "tide_fair": 0, "aground": False}
    progress.record_outcome(meta, chart, run, res, sc, scored=True, fix_taken=True)
    assert "first_fix" in meta["flags"]
