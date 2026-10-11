"""Z-3e5: Trade Empire opts in to the shared ghost (shared/ghost.py). One number per tick (the highest credits this
charter, `max_profit_ever`) is recorded until the endgame; renewing the charter keeps the fastest path to the endgame per
mode; words only, with the shared sentence; the live path rides in the save; hostile data is dropped; old saves load."""

import copy
import json
import types

import ghost

from .fakes import FakeClassList


def _run(env, ticks):
    """Ticks the game, returning max_profit_ever after each tick."""
    seen = []
    for _ in range(ticks):
        env.tick(1)
        seen.append(env.module.max_profit_ever)
    return seen


def _charter(env, ticks, hard=False):
    """A whole charter of `ticks` ticks whose last tick reaches the endgame, then renew it."""
    m = env.module
    m.hard_charter_active = hard
    _run(env, ticks - 1)
    m.endgame_reached = True
    _run(env, 1)
    assert m._ghost_state["endgame"] == ticks
    assert m.found_new_corporation() is True
    return ticks


def _html(module, *classes):
    html = types.SimpleNamespace(classList=FakeClassList())
    for name in classes:
        html.classList.add(name)
    module.document.documentElement = html
    return html


def _save(m):
    return json.loads(json.dumps(m.get_state()))


def test_nothing_is_saved_until_a_tick_has_been_recorded(game_env):
    m = game_env.module
    assert "ghost" not in m.get_state() and m.ghost_best == {} and m._ghost_rec.turns == 0
    game_env.tick(1)
    assert m._ghost_rec.turns == 1 and "ghost" in m.get_state()


def test_one_number_per_tick_is_recorded_from_the_first_tick(game_env):
    m = game_env.module
    seen = _run(game_env, 25)
    assert m._ghost_rec.turns == 25
    assert m._ghost_rec.values == [ghost.clean_number(v) for v in seen]
    live = m.get_state()["ghost"]["live"]
    assert live["turns"] == 25 and live["stride"] == 1 and "endgame" not in live


def test_the_recording_stops_the_moment_the_endgame_is_reached(game_env):
    m = game_env.module
    _run(game_env, 10)
    m.endgame_reached = True
    _run(game_env, 1)
    assert m._ghost_state["endgame"] == 11 and m._ghost_rec.turns == 11
    _run(game_env, 20)
    assert m._ghost_rec.turns == 11
    assert m.get_state()["ghost"]["live"]["endgame"] == 11


def test_the_recorder_invariant_that_the_save_check_relies_on(game_env):
    for turns in list(range(1, 300)) + [700, 1500, 4096, 4097]:
        rec = ghost.Recorder()
        for i in range(turns):
            rec.record(i)
        assert len(rec.values) == -(-rec.turns // rec.stride) and len(rec.values) < ghost.MAX_LEN, turns


def test_a_long_live_path_survives_a_save_round_trip_and_keeps_recording_identically(game_env):
    m = game_env.module
    rec_a = ghost.Recorder()
    for i in range(1, 521):
        m._ghost_rec.record(i * 3)
        rec_a.record(i * 3)
    m.max_profit_ever = 1560
    saved = _save(m)
    assert saved["ghost"]["live"]["turns"] == 520 and saved["ghost"]["live"]["stride"] > 1
    m.load_state(copy.deepcopy(saved))
    assert m._ghost_rec.values == rec_a.values and m._ghost_rec.turns == 520 and m._ghost_rec.stride == rec_a.stride
    for i in range(521, 700):
        m._ghost_rec.record(i * 3)
        rec_a.record(i * 3)
    assert m._ghost_rec.trace() == rec_a.trace()


def test_renewing_after_the_endgame_keeps_the_path_as_the_best_charter(game_env):
    m = game_env.module
    _charter(game_env, 45)
    entry = m.ghost_best["standard"]
    assert entry["ticks"] == 45 and entry["trace"]["turns"] == 45 and entry["trace"]["label"] == "best charter"
    assert ghost.load(entry["trace"]) == entry["trace"]
    assert m._ghost_rec.turns == 0 and m._ghost_state["endgame"] is None            # the new charter starts its own path
    saved = _save(m)
    assert saved["ghost"]["best"]["standard"]["ticks"] == 45 and "live" not in saved["ghost"]
    m.load_state(copy.deepcopy(saved))
    assert m.ghost_best["standard"] == entry


def test_only_a_faster_charter_replaces_the_best_and_a_tie_keeps_the_older(game_env):
    m = game_env.module
    _charter(game_env, 60)
    first = copy.deepcopy(m.ghost_best["standard"])
    _charter(game_env, 80)                                   # slower: kept out
    assert m.ghost_best["standard"] == first
    _charter(game_env, 60)                                   # a tie keeps the older one
    assert m.ghost_best["standard"] == first
    _charter(game_env, 40)                                   # faster
    assert m.ghost_best["standard"]["ticks"] == 40


def test_a_harder_charter_has_its_own_best(game_env):
    m = game_env.module
    _charter(game_env, 50)
    _charter(game_env, 70, hard=True)
    assert m.ghost_best["standard"]["ticks"] == 50 and m.ghost_best["hard"]["ticks"] == 70
    assert set(m.get_state()["ghost"]["best"]) == {"standard", "hard"}


def test_a_charter_that_cannot_be_compared_fairly_is_never_kept(game_env):
    m = game_env.module
    _charter(game_env, m.GHOST_MIN_TICKS - 1)                # too short
    assert m.ghost_best == {}
    m.blackout_enabled = True                                # Blackout is a different game
    _run(game_env, 3)
    assert m._ghost_state["tainted"] is True and m._ghost_rec.turns == 0
    m.blackout_enabled = False
    m.endgame_reached = True
    m.found_new_corporation()
    assert m.ghost_best == {}
    m.total_sales_count = 4                                  # joined part-way, like an older save: no path from the start
    _run(game_env, 3)
    assert m._ghost_state["tainted"] is True and "Blackout" in m.ghost_note_text()
    assert _save(m)["ghost"] == {"live": {"tainted": True}}
    m.load_state(_save(m))
    assert m._ghost_state["tainted"] is True


def test_the_sandbox_records_nothing(game_env):
    m = game_env.module
    _run(game_env, 5)
    before = _save(m)["ghost"]
    assert m.sandbox_enter() is True
    _run(game_env, 5)
    assert m._ghost_rec.turns == 0 and m.ghost_note_text() == ""     # the practice corporation has no ghost
    assert m.sandbox_leave() is True
    assert _save(m)["ghost"] == before and m._ghost_rec.turns == 5   # the real path is back exactly as it was
    assert m.ghost_note_text() != ""


def test_the_note_explains_the_ghost_before_there_is_one(game_env):
    m = game_env.module
    text = m.ghost_note_text()
    assert text.startswith("Ghost: when you renew the charter after reaching the endgame")
    m.render()
    note = game_env.elements["ghost-note"]
    assert note.hidden is False and note.innerText == text


def test_the_note_races_the_best_charter_in_the_shared_wording(game_env):
    m = game_env.module
    best = [0, 10, 20, 30, 40] + [50 + 10 * i for i in range(95)]       # 100 ticks; at tick 10 the ghost has 90
    m.ghost_best["standard"] = {"ticks": 100, "trace": ghost.make_trace(best, label="best charter")}
    for value in range(1, 11):
        m._ghost_rec.record(value)
    m.max_profit_ever = 100
    assert m.ghost_note_text() == "Ghost: you are 10 credits ahead of your best charter at tick 10."
    m.max_profit_ever = 25
    assert m.ghost_note_text() == "Ghost: your best charter was 65 credits ahead at tick 10."
    m.max_profit_ever = 90
    assert m.ghost_note_text() == "Ghost: level with your best charter at tick 10."
    assert "turn" not in m.ghost_note_text()


def test_the_result_agrees_with_the_shared_compare_on_a_full_list(game_env):
    m = game_env.module
    best = [i * 4 for i in range(60)]
    trace = ghost.make_trace(best, label="best charter")
    for live_value in (0, 30, 36, 37, 38, 90, 200):
        m.ghost_best["standard"] = {"ticks": 60, "trace": trace}
        m._ghost_rec.reset()
        series = [i * 3 for i in range(1, 10)] + [live_value]
        for value in series:
            m._ghost_rec.record(value)
        m.max_profit_ever = live_value
        mine, shared = m.ghost_result(), ghost.compare(series, trace)
        for key in ("turn", "live", "ghost", "gap", "status", "lead"):
            assert mine[key] == shared[key], (live_value, key)
        assert ghost.summary(mine) == ghost.summary(shared)


def test_a_slower_charter_past_the_ghosts_end_and_the_endgame_comparison_are_in_plain_words(game_env):
    m = game_env.module
    m.ghost_best["standard"] = {"ticks": 40, "trace": ghost.make_trace(list(range(40)), label="best charter")}
    for value in range(50):
        m._ghost_rec.record(value)
    m.max_profit_ever = 49
    assert m.ghost_note_text() == "Ghost: your best charter had reached the endgame by tick 40; this one is still on its way."
    m._ghost_state["endgame"] = 50
    assert m.ghost_note_text() == "Ghost: you reached the endgame at tick 50, 10 ticks after your best charter (tick 40)."
    m._ghost_state["endgame"] = 30
    assert "10 ticks sooner than your best charter (tick 40)" in m.ghost_note_text()
    m._ghost_state["endgame"] = 40
    assert "the same tick as your best charter" in m.ghost_note_text()
    m.ghost_best["hard"] = copy.deepcopy(m.ghost_best["standard"])
    m.hard_charter_active = True
    assert "harder charter" in m.ghost_note_text()


def test_the_note_is_refreshed_every_few_ticks_not_every_tick(game_env):
    m = game_env.module
    m.ghost_best["standard"] = {"ticks": 400, "trace": ghost.make_trace(list(range(400)), label="best charter")}
    note = game_env.elements["ghost-note"]
    game_env.tick(1)
    first = note.innerText
    assert first.startswith("Ghost: ")
    for _ in range(m.GHOST_NOTE_EVERY - 2):
        game_env.tick(1)
    assert note.innerText == first                           # the same words until the next multiple
    game_env.tick(m.GHOST_NOTE_EVERY)
    assert note.innerText != first or "tick" in note.innerText


def test_the_settings_checkbox_hides_the_note_and_the_stored_ghost_stays(game_env):
    m = game_env.module
    m.ghost_best["standard"] = {"ticks": 40, "trace": ghost.make_trace(list(range(40)), label="best charter")}
    assert m._ghost_on() is True
    game_env.tick(1)
    note = game_env.elements["ghost-note"]
    assert note.hidden is False
    _html(m, "ghost-off")
    assert m._ghost_on() is False
    m.render()
    assert note.hidden is True and note.innerText == ""
    assert "standard" in m.ghost_best and "ghost" in m.get_state()
    _html(m)
    m.render()
    assert note.hidden is False


def test_the_settings_page_has_the_ghost_checkbox_wired():
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    html, js, css = (root / "index.html").read_text(encoding="utf-8"), (root / "settings.js").read_text(encoding="utf-8"), (root / "style.css").read_text(encoding="utf-8")
    assert 'id="ghost-checkbox"' in html and 'id="ghost-note"' in html and 'fetch("../../shared/ghost.py")' in html
    assert "ghost-off" in js and "trade-empire-ghost-off" in js and "ghost-checkbox" in js and ".ghost-off .ghost-note" in css


def test_an_older_save_without_a_ghost_loads_and_has_none(game_env):
    m = game_env.module
    state = copy.deepcopy(m._fresh_state)
    assert "ghost" not in state
    m.load_state(state)
    assert m.ghost_best == {} and m._ghost_rec.turns == 0
    assert "ghost" not in m.get_state()
    assert m.ghost_note_text().startswith("Ghost: when you renew")


def test_hostile_ghost_data_in_a_save_is_dropped_never_trusted(game_env):
    m = game_env.module
    good_trace = ghost.make_trace(list(range(40)), label="best charter")
    live_ok = {"turns": 5, "stride": 1, "values": [1, 2, 3, 4, 5]}
    junk = [
        None, 7, "x", [], True, {}, {"best": 5}, {"best": {"standard": 5}}, {"best": {"standard": {"ticks": 40}}},
        {"best": {"standard": {"ticks": 40, "trace": "x"}}}, {"best": {"standard": {"ticks": True, "trace": good_trace}}},
        {"best": {"standard": {"ticks": 41, "trace": good_trace}}},          # ticks must match the trace's own length
        {"best": {"standard": {"ticks": 5, "trace": ghost.make_trace([1, 2, 3, 4, 5])}}},     # shorter than the minimum
        {"best": {"standard": {"ticks": 40, "trace": {"v": 1, "turns": 40, "values": ["a"] * 40}}}},
        {"best": {"nightmare": {"ticks": 40, "trace": good_trace}}},
        {"best": {"standard": {"ticks": 40, "trace": {"turns": 40, "values": [1e400, float("nan"), 3]}}}},
        {"live": 5}, {"live": {"turns": 0, "stride": 1, "values": []}},
        {"live": {"turns": 5, "stride": 3, "values": [1, 2]}},                  # a stride that is not a power of two
        {"live": {"turns": 5, "stride": 1, "values": [1, 2]}},                  # wrong length for its turns
        {"live": {"turns": 5, "stride": 1, "values": [1, 2, 3, 4, "x"]}},
        {"live": {"turns": 5, "stride": 1, "values": [1, 2, 3, 4, float("inf")]}},
        {"live": {"turns": 5, "stride": 1, "values": [1, 2, 3, 4, 5], "endgame": 3}},      # a path never runs past its endgame
        {"live": {"turns": True, "stride": 1, "values": [1]}},
        {"live": {"turns": 10 ** 9, "stride": 1, "values": [1] * 5}},
        {"live": {"turns": 5000, "stride": 1, "values": list(range(5000))}},
        {"live": {"tainted": "yes"}},
    ]
    for raw in junk:
        state = copy.deepcopy(m._fresh_state)
        state["ghost"] = raw
        m.load_state(state)
        assert m.ghost_best == {} and m._ghost_rec.turns == 0 and not m._ghost_state["tainted"], raw
        m.render()
        assert "ghost" not in m.get_state() or m.get_state()["ghost"] == {}, raw
    state = copy.deepcopy(m._fresh_state)                    # one bad half does not lose the good half
    state["ghost"] = {"best": {"standard": {"ticks": 40, "trace": good_trace}}, "live": {"turns": 5, "stride": 2, "values": [1]}}
    m.load_state(state)
    assert m.ghost_best["standard"]["ticks"] == 40 and m._ghost_rec.turns == 0
    state["ghost"] = {"best": {"standard": {"ticks": 40, "trace": good_trace}}, "live": live_ok}
    m.load_state(state)
    assert m._ghost_rec.turns == 5 and m._ghost_rec.values == [1, 2, 3, 4, 5]
    state["ghost"] = {"best": {"standard": {"ticks": 40, "trace": good_trace}}, "live": {"tainted": True}}
    m.load_state(state)
    assert m._ghost_state["tainted"] is True


def test_a_traced_best_with_extra_keys_or_dirty_numbers_is_cleaned_through_the_shared_loader(game_env):
    m = game_env.module
    state = copy.deepcopy(m._fresh_state)
    dirty = {"v": 1, "turns": 40, "values": [0.123456] * 39 + [1e30], "label": "  best \n charter " + "x" * 100, "extra": "z"}
    state["ghost"] = {"best": {"standard": {"ticks": 40, "trace": dirty}}}
    m.load_state(state)
    trace = m.ghost_best["standard"]["trace"]
    assert trace == ghost.load(dirty) and "extra" not in trace and len(trace["label"]) <= ghost.LABEL_MAX
    assert trace["values"][0] == 0.12 and trace["values"][-1] == ghost.MAX_ABS


def test_the_save_stays_small_however_long_the_charter(game_env):
    m = game_env.module
    for i in range(1, 6001):
        m._ghost_rec.record(i * 1000)
    assert len(json.dumps(m.get_state()["ghost"])) < 2500
    assert len(m._ghost_rec.values) < ghost.MAX_LEN


def test_renewal_keeps_every_other_thing_it_kept_before(game_env):
    m = game_env.module
    _charter(game_env, 50)
    assert m.legacy_level == 1 and m.charters_completed == 1 and len(m.charter_career) == 1
    assert m.endgame_reached is False and m.ghost_best["standard"]["ticks"] == 50
