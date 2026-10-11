"""Z-3d: the ghost of your best run (shared/ghost.py). One number per event (the resources left after it), the best
finished run per schedule kept in meta["ghosts"], a words-only note under the damage preview (Aftermath has no
chart), an off switch, old saves unchanged, hostile data dropped."""
import copy
import json


def _finish_run(env, invest_first=0):
    """Plays the current run to the end (investing `invest_first` growth units before the first event)."""
    for _ in range(invest_first):
        env.invest_growth()
    while not env.run.is_complete():
        env.resolve_event()


def _note(env):
    return env.elements["ghost-note"].innerText


def test_a_fresh_install_has_no_ghost_key_and_says_what_it_will_do(game_env):
    m = game_env.module
    assert "ghosts" not in m.meta and "ghosts" not in m._default_meta()
    assert game_env.run.resources_log == []
    assert "finish a run on this schedule" in _note(game_env)
    assert game_env.elements["ghost-note"].hidden is False


def test_each_resolved_event_adds_one_number(game_env):
    game_env.resolve_event()
    game_env.resolve_event()
    assert game_env.run.resources_log == [e for e in game_env.run.resources_log] and len(game_env.run.resources_log) == 2
    assert game_env.run.resources_log[-1] == game_env.run.resources


def test_finishing_a_run_files_a_recorder_trace_for_that_schedule(game_env):
    m = game_env.module
    _finish_run(game_env, 3)
    entry = m.meta["ghosts"]["classic"]
    assert entry["run"] == 1 and entry["score"] == m.ghost_lib.clean_number(game_env.run.run_score())
    trace = entry["trace"]
    assert trace["turns"] == 7 and trace["label"] == "Run 1"
    assert trace["values"] == [m.ghost_lib.clean_number(v) for v in game_env.run.resources_log]
    assert m.ghost_lib.load(trace) == trace            # already in the shared format
    json.dumps(m.meta)                                 # and plain data
    assert "this run is your best on this schedule" in _note(game_env)
    # it was written to storage too
    assert "ghosts" in json.loads(game_env.local_storage.getItem(m.META_STORAGE_KEY))


def test_a_better_run_replaces_the_ghost_and_a_worse_one_does_not(game_env):
    m = game_env.module
    _finish_run(game_env, 3)
    first = copy.deepcopy(m.meta["ghosts"]["classic"])
    game_env.start_new_run()
    _finish_run(game_env, 0)                           # no investment at all: a worse run
    assert game_env.run.run_score() < first["score"]
    assert m.meta["ghosts"]["classic"] == first
    game_env.start_new_run()
    _finish_run(game_env, 3)                           # as good as the first (the tree is unchanged): latest wins a tie
    assert game_env.run.run_score() >= first["score"]
    assert m.meta["ghosts"]["classic"]["run"] == game_env.run.run_number


def test_the_next_run_is_compared_after_every_event(game_env):
    m = game_env.module
    _finish_run(game_env, 3)
    best = m.meta["ghosts"]["classic"]["trace"]
    game_env.start_new_run()
    assert "your best run on this schedule (Run 1) ended with" in _note(game_env)
    game_env.resolve_event()                           # nothing spent: ahead of a ghost that bought growth early
    result = m.ghost_lib.compare(game_env.run.resources_log, best)
    assert result["status"] == "ahead" and result["turn"] == 1
    assert _note(game_env) == f"Ghost: you are {int(round(result['lead']))} resources ahead of your best run (Run 1) at turn 1."
    game_env.run.resources_log = [m.ghost_lib.value_at(best, 1) + 0.3]            # under half a resource is level
    game_env.run.event_index = 1
    assert m.ghost_note_text(game_env.run).startswith("Ghost: level with your best run (Run 1) at turn 1")


def test_each_schedule_has_its_own_ghost(game_env):
    m = game_env.module
    _finish_run(game_env, 3)
    game_env.start_new_run()
    game_env.elements["scenario-select"].value = "coastal"
    game_env.elements["scenario-select"].dispatch("change", None)
    if game_env.run.scenario != "coastal":
        game_env.start_new_run()
    assert game_env.run.scenario == "coastal"
    assert "finish a run on this schedule" in _note(game_env)
    _finish_run(game_env, 2)
    assert set(m.meta["ghosts"]) == {"classic", "coastal"}


def test_the_off_switch_hides_the_note_and_is_remembered(game_env):
    m = game_env.module
    toggle = game_env.elements["ghost-toggle"]
    toggle.checked = False
    toggle.dispatch("change", None)
    assert game_env.local_storage.getItem(m.GHOST_STORAGE_KEY) == "0"
    assert game_env.elements["ghost-note"].hidden is True and _note(game_env) == ""
    toggle.checked = True
    toggle.dispatch("change", None)
    assert game_env.elements["ghost-note"].hidden is False and _note(game_env) != ""
    # recording goes on while the note is off, so the ghost is never lost by hiding it
    toggle.checked = False
    toggle.dispatch("change", None)
    _finish_run(game_env, 3)
    assert "classic" in m.meta["ghosts"]


def test_challenge_runs_built_schedules_and_aided_runs_are_kept_out(game_env):
    m = game_env.module
    run = game_env.run
    assert m.ghost_run_eligible(run)
    run.normalised = True
    assert not m.ghost_run_eligible(run)
    run.normalised = False
    run.custom_events = ["flood", "drought", "heatwave"]
    assert not m.ghost_run_eligible(run)
    run.custom_events = None
    run.event_log.append({"type": "flood", "damage": 1.0, "severity": 1.0, "aid": 40})
    assert not m.ghost_run_eligible(run)
    run.event_log.clear()
    _finish_run(game_env, 3)
    run.normalised = True       # a finished run that is not eligible is never filed
    before = copy.deepcopy(m.meta["ghosts"])
    assert m.file_run_ghost(run) is False and m.meta["ghosts"] == before


def test_the_live_numbers_round_trip_through_a_save(game_env):
    m = game_env.module
    game_env.invest_growth()
    game_env.resolve_event()
    game_env.resolve_event()
    state = m.get_state()
    assert state["resources_log"] == game_env.run.resources_log and len(state["resources_log"]) == 2
    json.dumps(state)
    game_env.resolve_event()
    m.load_state(state)
    assert game_env.run.resources_log == state["resources_log"] and game_env.run.event_index == 2


def test_no_new_state_key_before_the_first_event_or_for_challenge_runs(game_env):
    m = game_env.module
    assert "resources_log" not in m.get_state()
    game_env.resolve_event()
    assert "resources_log" in m.get_state()
    game_env.run.normalised = True
    assert "resources_log" not in m.get_state()


def test_an_old_mid_run_save_loads_unchanged_and_says_it_cannot_be_compared(game_env):
    m = game_env.module
    _finish_run(game_env, 3)
    game_env.start_new_run()
    game_env.resolve_event()
    game_env.resolve_event()
    old = m.get_state()
    del old["resources_log"]                           # a save from before Z-3d
    game_env.resolve_event()
    m.load_state(old)
    assert game_env.run.event_index == 2 and game_env.run.resources_log == []
    assert "saved before ghosts were kept" in _note(game_env)
    game_env.resolve_event()                           # play on: the run still finishes, nothing breaks
    _finish_run(game_env)
    assert game_env.run.is_complete()


def test_old_meta_without_ghosts_loads_and_keeps_every_other_field(game_env):
    m = game_env.module
    old = {"settlement_name": "Marrow Bay", "pinned_skills": ["early_warning"], "run_notes": {"3": "good"}}
    clean = m._sanitize_meta(old)
    assert "ghosts" not in clean and clean["settlement_name"] == "Marrow Bay" and clean["run_notes"] == {"3": "good"}


def test_hostile_ghost_data_is_dropped_or_cleaned(game_env):
    m = game_env.module
    good = {"v": 1, "turns": 7, "values": [210, 190, 220, 200, 230, 240, 250], "label": "Run 4"}
    hostile = [
        "junk", [], {"classic": "x"}, {"nope": {"score": 1, "trace": good}},
        {"classic": {"score": "high", "trace": good}},
        {"classic": {"score": float("nan"), "trace": good}},
        {"classic": {"score": 100, "trace": {"turns": 7, "values": [1]}}},
        {"classic": {"score": 100, "trace": {"turns": 7, "values": ["a", None, True, float("inf"), [1], {}]}}},
        {"classic": {"score": 100, "trace": dict(good, turns=4)}},                    # not this schedule's length
        {"classic": {"score": 100, "trace": dict(good, values=[1.0] * 9000)}},       # refused outright
    ]
    for bad in hostile:
        assert m._sanitize_ghosts(bad) == {}, bad
    out = m._sanitize_ghosts({"classic": {"score": 100.456, "run": -5, "trace": dict(good, label="<b>" * 40)},
                              "classic:long": {"score": 1, "run": "x", "trace": dict(good, turns=14, values=good["values"] * 2)}})
    assert out["classic"]["score"] == 100.46 and out["classic"]["run"] == 0 and len(out["classic"]["trace"]["label"]) <= 40
    assert out["classic:long"]["trace"]["turns"] == 14
    assert m._sanitize_meta({"ghosts": {"classic": {"score": 5, "trace": good}}})["ghosts"]["classic"]["trace"]["turns"] == 7
    # a hand-edited saved log of the wrong length or with junk in it is ignored, not trusted
    assert m._load_resources_log([1, 2, 3], 2) == [] and m._load_resources_log([1, "x"], 2) == []
    assert m._load_resources_log([1, None], 2) == [] and m._load_resources_log("abc", 3) == []
    assert m._load_resources_log([1.5, 2.5], 2) == [1.5, 2.5]


def test_a_hostile_stored_ghost_cannot_break_the_page(game_env):
    m = game_env.module
    m.meta["ghosts"] = {"classic": {"run": 1, "score": 1, "trace": {"turns": 7, "values": "x"}}}
    m.render()                                         # a bad trace reads as no ghost, never an exception
    assert isinstance(_note(game_env), str)


def test_the_shared_wording_is_used_when_ahead_level_and_behind(game_env):
    m = game_env.module
    trace = m.ghost_lib.make_trace([100, 90, 80, 70, 60, 50, 40], turns=7, label="Run 2")
    m.meta["ghosts"] = {"classic": {"run": 2, "score": 40.0, "trace": trace}}
    game_env.run.event_index = 2
    game_env.run.resources_log = [100, 95]
    assert m.ghost_note_text(game_env.run) == "Ghost: you are 5 resources ahead of your best run (Run 2) at turn 2."
    game_env.run.resources_log = [100, 90]
    assert m.ghost_note_text(game_env.run) == "Ghost: level with your best run (Run 2) at turn 2."
    game_env.run.resources_log = [100, 80]
    assert m.ghost_note_text(game_env.run) == "Ghost: your best run (Run 2) was 10 resources ahead at turn 2."
