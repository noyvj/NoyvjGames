"""Z-3c: Grid's ghost of your best run runs on the shared recorder (shared/ghost.py). Old saves, whose career
history held only the thinned series, still load and become the same ghost; the new state key exists only once
a ghost does; a hostile one is dropped."""
import copy
import json

from .test_career import _install_storage, _play


def _old_save_career(g):
    """A career exactly as a save from before Z-3c wrote it: a history with series, and no "ghost" key."""
    def run(rounds, score, start):
        clean = [min(100, start + 4 * i) for i in range(rounds)]
        return {
            "scenario": "standard", "grade": "B", "points": 3, "rounds": rounds, "score": score,
            "clean": g._thin(clean), "funds_series": g._thin([300 + 25 * i for i in range(rounds)]),
            "demand_series": g._thin([100 + 5 * i for i in range(rounds)]),
        }
    return {"runs": 3, "points": 5, "best_score": 90.0, "best_grade": "B", "history": [
        run(10, 40.0, 10), run(40, 90.0, 20), run(8, 60.0, 5)]}


def _play_good_run(game_env, rounds=6):
    game_env.state.plant_counts["solar"] = 5
    game_env.state.plant_counts["coal"] = 3
    _play(game_env, rounds)


def test_no_ghost_key_in_a_fresh_career(game_env):
    g = game_env.module
    assert "ghost" not in g._default_career()
    assert "ghost" not in g.validate_career({"runs": 1, "history": []})
    assert g.ghost_record() is None


def test_old_save_loads_and_migrates_its_best_run(game_env):
    g = game_env.module
    old = _old_save_career(g)
    assert "ghost" not in old
    career = g.validate_career(old)
    ghost = career["ghost"]
    # the best run is the 40-round one (its label counts from the career's 3 runs), its series became a trace
    assert ghost["score"] == 90.0 and ghost["label"] == "Run 2" and ghost["clean"]["turns"] == 40
    assert len(ghost["clean"]["values"]) == 30 and ghost["funds"]["turns"] == 40
    g.career.clear()
    g.career.update(career)
    rec = g.ghost_record()
    assert rec["rounds"] == 40 and rec["score"] == 90.0
    # a 40-round run stored as 30 points is read spread over its length, as ghost_value always did
    saved = old["history"][1]["clean"]
    assert g.ghost_lib.value_at(rec["clean"], 1) == saved[0] and g.ghost_lib.value_at(rec["clean"], 40) == saved[-1]
    assert g.ghost_lib.value_at(rec["clean"], 41) is None
    # nothing else about the old career changed
    for key in ("runs", "points", "best_score", "best_grade"):
        assert career[key] == old[key]
    assert len(career["history"]) == 3


def test_old_save_through_load_state_keeps_the_ghost(game_env):
    g = game_env.module
    data = copy.deepcopy(g.get_state())
    data["career"] = _old_save_career(g)
    g.load_state(data)
    assert g.ghost_record()["score"] == 90.0
    assert g.get_state()["career"]["ghost"]["label"] == "Run 2"   # written back in the new shape


def test_a_career_with_history_but_no_ghost_key_reads_the_history(game_env):
    g = game_env.module
    g.career["history"] = g.validate_career(_old_save_career(g))["history"]
    g.career["runs"] = 3
    assert "ghost" not in g.career
    assert g.ghost_record()["score"] == 90.0


def test_finishing_a_run_files_a_recorder_trace(game_env):
    g = game_env.module
    _install_storage()
    _play_good_run(game_env, 6)
    clean_log = list(game_env.state.clean_fraction_log)
    funds_log = list(game_env.state.funds_history)
    assert g.finish_run() is not None
    ghost = g.career["ghost"]
    assert ghost["label"] == "Run 1" and ghost["clean"]["turns"] == 6 and ghost["funds"]["turns"] == 6
    assert ghost["clean"]["values"] == [g.ghost_lib.clean_number(v * 100) for v in clean_log]
    assert ghost["funds"]["values"] == [g.ghost_lib.clean_number(max(0, v)) for v in funds_log]
    assert g.ghost_lib.load(ghost["clean"]) == ghost["clean"]   # already in the shared format
    json.dumps(g.get_state())                                   # and plain data


def test_a_better_run_replaces_the_ghost_and_a_worse_one_does_not(game_env):
    g = game_env.module
    _install_storage()
    _play_good_run(game_env, 6)
    g.finish_run()
    first = copy.deepcopy(g.career["ghost"])
    # a run that scores worse (coal only) must not replace it
    game_env.state.plant_counts["coal"] = 12
    _play(game_env, 6)
    assert game_env.state.score() < first["score"]
    g.finish_run()
    assert g.career["ghost"] == first
    # a run that ties or beats it does, and the latest wins a tie
    _play_good_run(game_env, 6)
    g.finish_run()
    assert g.career["ghost"]["label"] == "Run 3"


def test_the_ghost_survives_the_run_leaving_the_history(game_env):
    g = game_env.module
    _install_storage()
    _play_good_run(game_env, 6)
    g.finish_run()
    ghost = copy.deepcopy(g.career["ghost"])
    g.career["history"] = []
    assert g.validate_career(copy.deepcopy(g.career))["ghost"] == ghost


def test_a_long_run_is_capped_by_the_recorder(game_env):
    g = game_env.module
    traces = g.run_ghost_traces([i / 400 for i in range(400)], [100 + i for i in range(400)], "Run 9")
    assert traces["clean"]["turns"] == 400 and len(traces["clean"]["values"]) <= g.ghost_lib.MAX_LEN
    assert traces["clean"]["values"][-1] == g.ghost_lib.clean_number(399 / 400 * 100)
    assert g.run_ghost_traces([0.5], [100], "x") is None


def test_hostile_ghosts_are_dropped_or_cleaned(game_env):
    g = game_env.module
    base = g.validate_career(_old_save_career(g))
    hostile = [
        "junk", [], {"clean": "x"}, {"grade": "Z", "clean": base["ghost"]["clean"]},
        {"grade": "B", "score": 50, "clean": {"turns": 5, "values": [1]}},
        {"grade": "B", "score": 50, "clean": {"turns": 5, "values": ["a", None, float("nan"), True]}},
        {"grade": "B", "score": 50, "clean": {"turns": 5, "values": [1, 2, 3]}, "funds": {"values": "x"}, "label": "<b>" * 99},
    ]
    for bad in hostile:
        raw = copy.deepcopy(base)
        raw["ghost"] = bad
        out = g.validate_career(raw)
        ghost = out.get("ghost")
        assert ghost is not None            # an unusable one is replaced by the one migrated from history
        assert ghost["score"] in (50.0, 90.0) and len(ghost["label"]) <= 40
        assert ghost["clean"] == g.ghost_lib.load(ghost["clean"])
    raw = copy.deepcopy(base)
    raw["ghost"] = {"grade": "B", "score": 1e99, "clean": {"turns": 10 ** 9, "values": [1e30] * 9000}}
    assert g.validate_career(raw)["ghost"]["score"] == 90.0   # 9000 values is refused outright
    raw["history"] = []
    assert "ghost" not in g.validate_career(raw)
    assert g.validate_career({"ghost": {"grade": "B", "clean": {"turns": 3, "values": [1, 2, 3]}}})["ghost"]["funds"] is None


def test_the_note_uses_the_shared_sentences(game_env):
    g = game_env.module
    g.career["history"] = [g._validate_run_record({
        "scenario": "standard", "grade": "A", "rounds": 10, "score": 88.0,
        "clean": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100], "funds_series": [500] * 10})]
    g.career["runs"] = 1
    ghost = g.ghost_record()
    text = g.ghost_delta_text([0.1, 0.2], [500, 500], ghost)
    assert "ghost: " in text
    assert "ghost: level with Run 1 at turn 2" in g.ghost_delta_text([0.1, 0.2], [500, 500], ghost)   # clean 20 vs 20
    text = g.ghost_delta_text([0.1, 0.5], [450, 400], ghost)
    assert "you are 30 points ahead of Run 1 at turn 2" in text
    assert "Run 1 was 100 ahead at turn 2" in text
    assert "ended before round 11" in g.ghost_delta_text([0.5] * 11, [1] * 11, ghost)
