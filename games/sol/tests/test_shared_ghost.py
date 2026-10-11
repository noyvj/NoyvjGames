"""Z-3d3: the Ghost Run (A-29) told through the shared ghost (shared/ghost.py). A recording's checkpoints (terraform percent
every 25 ticks) become a shared trace through ghost.Recorder; ghost.compare/summary give the one screen-reader sentence.
The stored recording is unchanged (old recordings keep loading), nothing new is saved, and the ghost switch still works."""

import json

import challenges
import ghost

TODAY = "2026-10-11"


def _set_average(env, percent):
    for planet in env.module.PLANETS:
        env.module.planet_state[planet]["terraform_progress"] = float(percent)


def _tick_to_run_tick(env, run_tick, percent=None):
    m = env.module
    while m._run_ticks() < run_tick:
        if percent is not None:
            _set_average(env, percent)
        m.tick()


def _pb(env, ticks, pct):
    env.local_storage.setItem("sol-ghost-pb-v1", json.dumps({"ticks": ticks, "pct": pct}))
    env.module._load_pb_ghost()


def _sentence(env):
    box = env.elements["ghost-sentence"]
    return None if box.hidden else box.innerText


def test_a_recording_becomes_a_clean_shared_trace_one_number_per_checkpoint(game_env):
    m = game_env.module
    rec = {"ticks": 2000, "pct": [0, 100, 600, 1000]}
    trace = m.ghost_trace(rec)
    assert trace["values"] == [0, 10, 60, 100] and trace["turns"] == 4 and trace["label"] == "best run"
    assert ghost.load(trace) == trace                      # already in the shared format
    assert json.loads(json.dumps(trace)) == trace          # and JSON safe
    assert m.ghost_trace(None) is None
    assert m.ghost_trace(rec) is trace                     # cached per recording, not rebuilt each checkpoint


def test_a_long_recording_is_thinned_to_the_shared_cap_but_keeps_its_ends(game_env):
    m = game_env.module
    pct = [min(1000, i * 2) for i in range(600)]
    trace = m.ghost_trace({"ticks": 15000, "pct": pct})
    assert len(trace["values"]) <= ghost.MAX_LEN and trace["turns"] == 600
    assert trace["values"][0] == 0 and trace["values"][-1] == 100


def test_an_old_stored_recording_gives_the_sentence_with_no_migration(game_env):
    _pb(game_env, 2000, [0, 50, 100, 1000])               # the exact A-29 storage shape from before the shared ghost
    game_env.local_storage.setItem("sol-ghost-on", "on")
    _tick_to_run_tick(game_env, 25, percent=8.0)           # checkpoint 2: ghost 5.0, you 8.0
    assert _sentence(game_env) == "ghost: you are 3 points ahead of your best run at checkpoint 2"
    assert "+3.0 points ahead" in game_env.elements["ghost-strip"].innerText   # the visible strip is unchanged


def test_the_sentence_says_behind_level_and_ended_in_checkpoint_words(game_env):
    m = game_env.module
    rec = {"ticks": 2000, "pct": [0, 50, 100, 1000]}
    assert m.ghost_sentence([0, 20], rec, "your best run") == "ghost: your best run was 3 points ahead at checkpoint 2"
    assert m.ghost_sentence([0, 50], rec, "your best run") == "ghost: level with your best run at checkpoint 2"
    assert m.ghost_sentence([0, 50, 100, 200, 300], rec, "your best run") == "ghost: your best run ended before checkpoint 5"
    assert "turn" not in m.ghost_sentence([0, 20], rec, "the Governor alone")
    assert m.ghost_sentence([0, 20], rec, "the Governor alone").startswith("ghost: the Governor alone was 3 points ahead")


def test_the_sentence_is_refreshed_every_few_checkpoints_not_every_one(game_env):
    m = game_env.module
    _pb(game_env, 2000, [0] + [10 * i for i in range(1, 99)] + [1000])
    game_env.local_storage.setItem("sol-ghost-on", "on")
    _tick_to_run_tick(game_env, 25, percent=3.0)
    first = _sentence(game_env)
    assert first and "checkpoint 2" in first
    _tick_to_run_tick(game_env, 25 * 4, percent=3.0)       # four more checkpoints: still the old sentence
    assert _sentence(game_env) == first
    _tick_to_run_tick(game_env, 25 * m.GHOST_SENTENCE_EVERY + 25, percent=3.0)
    assert _sentence(game_env) != first and "checkpoint" in _sentence(game_env)


def test_the_switch_hides_the_sentence_with_the_strip_and_the_stored_ghost_stays(game_env):
    m = game_env.module
    _pb(game_env, 2000, [0, 50, 100, 1000])
    _tick_to_run_tick(game_env, 25, percent=8.0)           # the switch is off by default: no ghost, no sentence
    assert _sentence(game_env) is None and game_env.elements["ghost-strip"].hidden is True
    game_env.local_storage.setItem("sol-ghost-on", "on")
    _tick_to_run_tick(game_env, 50, percent=8.0)
    assert _sentence(game_env)
    game_env.local_storage.setItem("sol-ghost-on", "off")
    m._refresh_ghost_strip()
    assert _sentence(game_env) is None and m._pb_ghost is not None
    assert game_env.local_storage.getItem("sol-ghost-pb-v1")


def test_a_scarcity_run_gets_the_sentence_for_its_ghost_and_loses_it_when_it_ends(game_env):
    m = game_env.module
    m.TODAY_OVERRIDE = TODAY
    m._scarcity_ghost_choice = "par"
    m.start_scarcity_run(TODAY)
    for _ in range(50):
        m.tick()
    sentence = _sentence(game_env)
    assert sentence and "the Governor alone" in sentence and "checkpoint" in sentence
    m.leave_scarcity_run()
    assert _sentence(game_env) is None


def test_hostile_recordings_give_no_trace_and_no_sentence(game_env):
    m = game_env.module
    for junk in ("not json", "[]", json.dumps({"ticks": 5, "pct": ["a", "b"]}), json.dumps({"ticks": 9, "pct": [0, 1001]}),
                 json.dumps({"ticks": 9, "pct": [0, float("nan")]}), json.dumps({"ticks": True, "pct": [0, 1]}),
                 json.dumps({"ticks": 10 ** 12, "pct": [0, 1]}), json.dumps({"ticks": 9, "pct": [0] * 30000})):
        game_env.local_storage.setItem("sol-ghost-pb-v1", junk)
        m._load_pb_ghost()
        assert m._pb_ghost is None and m.ghost_trace(m._pb_ghost) is None
    game_env.local_storage.setItem("sol-ghost-on", "on")
    m._live_ghost[:] = [0, 10]
    m._refresh_ghost_strip()
    assert _sentence(game_env) is None


def test_a_run_longer_than_the_shared_cap_says_nothing_instead_of_failing(game_env):
    m = game_env.module
    rec = {"ticks": 2000, "pct": [0, 50, 1000]}
    assert m.ghost_sentence([0] * (ghost.HARD_INPUT_LIMIT + 1), rec, "your best run") == ""
    assert m.ghost_sentence([], rec, "your best run") == ""


def test_round_trip_a_finished_run_becomes_the_best_and_its_trace_reads_back(game_env):
    m = game_env.module
    _tick_to_run_tick(game_env, 75, percent=30)
    _set_average(game_env, 100)
    m.tick()
    assert m._pb_ghost is not None
    stored = json.loads(game_env.local_storage.getItem("sol-ghost-pb-v1"))
    assert challenges.clean_recording(stored) == stored    # the stored recording is exactly what it always was
    trace = m.ghost_trace(m._pb_ghost)
    assert trace["turns"] == len(stored["pct"]) and trace["values"][-1] == 100
    assert ghost.load(json.loads(json.dumps(trace))) == trace
    # the next run races it: slower pace is behind it, in the shared wording
    m.run_completed = False
    m.run_start_tick = m.total_ticks
    m._ghost_reload_live()
    game_env.local_storage.setItem("sol-ghost-on", "on")
    _tick_to_run_tick(game_env, 25, percent=1.0)
    assert "ahead at checkpoint" in _sentence(game_env)


def test_nothing_new_enters_the_save_or_local_storage(game_env):
    m = game_env.module
    before = set(game_env.local_storage._store)
    _pb(game_env, 2000, [0, 50, 100, 1000])
    game_env.local_storage.setItem("sol-ghost-on", "on")
    _tick_to_run_tick(game_env, 25 * 10, percent=8.0)
    keys = set(game_env.local_storage._store)
    assert {k for k in keys - before if "ghost" in k} <= {"sol-ghost-pb-v1", "sol-ghost-on", "sol-ghost-live-v1"}
    assert "ghost" not in json.dumps(m.get_state()).lower()
