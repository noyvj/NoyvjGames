"""Z-3e: Canopy opts in to the shared best-session ghost (shared/ghost.py). One number per tick (the standing forest
value), the best session per settings kept per device in its own localStorage key, a faint dashed line on the Timeline
chart (standing value) plus the shared sentence, an off switch, hostile data dropped, saves unchanged."""
import json
import xml.etree.ElementTree as ET


def _session(env, ticks):
    env.tick(ticks)
    return list(env.module._ghost_live)


def _stored(env):
    raw = env.local_storage.getItem(env.module.GHOST_STORAGE_KEY)
    return None if raw is None else json.loads(raw)


def test_nothing_is_stored_until_a_session_is_kept(game_env):
    m = game_env.module
    assert _stored(game_env) is None and m.load_ghosts() == {}
    assert m.ghost_entry() is None and m.ghost_result() is None
    game_env.tick(10)
    game_env.reset_session()                   # shorter than GHOST_MIN_TICKS: not kept
    assert _stored(game_env) is None
    assert "when you start a new forest" in m.ghost_note_text()


def test_one_number_per_tick_is_recorded_and_the_session_is_kept_on_reset(game_env):
    m = game_env.module
    live = _session(game_env, 40)
    assert len(live) == 40 and live[-1] == m.ghost_lib.clean_number(m.standing_forest_value())
    game_env.reset_session()
    entry = _stored(game_env)["normal:normal:normal"]
    assert entry["trace"]["turns"] == 40 and entry["trace"]["values"] == live
    assert entry["score"] == max(live)
    assert m.ghost_lib.load(entry["trace"]) == entry["trace"]          # already in the shared format
    assert m._ghost_live == []                                           # and the new session starts empty


def test_a_lower_peak_does_not_replace_the_ghost_and_a_tie_does(game_env):
    m = game_env.module
    _session(game_env, 60)
    game_env.reset_session()
    first = _stored(game_env)["normal:normal:normal"]
    _session(game_env, 35)                                               # a shorter session peaks lower
    assert max(m._ghost_live) < first["score"]
    game_env.reset_session()
    assert _stored(game_env)["normal:normal:normal"] == first
    _session(game_env, 60)                                               # the legacy bonus makes this one better: it replaces
    peak = max(m._ghost_live)
    assert peak >= first["score"]
    game_env.reset_session()
    assert _stored(game_env)["normal:normal:normal"]["score"] == peak
    # directly: an equal peak also replaces (the latest wins a tie)
    m._reset_ghost_session()
    for value in range(1, 41):
        m._record_ghost_tick(float(value) * peak / 40)
    assert m._bank_ghost() is True and _stored(game_env)["normal:normal:normal"]["trace"]["values"][-1] == peak


def test_the_next_session_is_compared_every_tick_in_the_shared_words(game_env):
    m = game_env.module
    _session(game_env, 60)
    game_env.reset_session()
    assert "peaked at" in m.ghost_note_text() and "over 60 ticks" in m.ghost_note_text()
    game_env.toggle_session_summary()                                    # the timeline lives in the session summary
    game_env.tick(5)
    result = m.ghost_result()
    assert result["turn"] == 5 and result["status"] in ("ahead", "level", "behind")
    text = m.ghost_note_text()
    assert text.startswith("Ghost: ") and text.endswith(" at turn 5.") and "your best session" in text
    assert game_env.elements["ghost-note"].innerText == text
    # a different settings mode has its own (empty) slot
    game_env.change_difficulty("ranger")
    assert m.ghost_entry() is None and "when you start a new forest" in m.ghost_note_text()


def test_the_timeline_draws_a_dashed_labelled_ghost_on_the_standing_chart_only(game_env):
    m = game_env.module
    _session(game_env, 60)
    game_env.reset_session()
    game_env.tick(10)
    svg = m.timeline_chart_svg("standing")
    ET.fromstring(svg)                                                   # well-formed
    assert 'data-testid="ghost-line"' in svg and 'stroke-dasharray="6 4"' in svg and "Ghost: best session (dashed)" in svg
    assert m.ghost_note_text() in svg.replace("&amp;", "&")              # the sentence is the chart's alternative text
    assert 'data-testid="ghost-line"' not in m.timeline_chart_svg("biodiversity")
    drawn = svg.split('<polyline points="')[1].split('"')[0].split()
    assert len(drawn) == 10


def test_the_off_switch_removes_the_line_and_the_note_but_not_the_ghost(game_env):
    m = game_env.module
    _session(game_env, 60)
    game_env.reset_session()
    game_env.toggle_session_summary()
    game_env.tick(5)
    toggle = game_env.elements["ghost-toggle"]
    toggle.checked = False
    toggle.dispatch("change", None)
    assert game_env.local_storage.getItem(m.GHOST_PREF_KEY) == "0"
    assert 'data-testid="ghost-line"' not in m.timeline_chart_svg("standing")
    assert game_env.elements["ghost-note"].hidden is True and game_env.elements["ghost-note"].innerText == ""
    assert _stored(game_env) is not None                                 # hiding never deletes it
    toggle.checked = True
    toggle.dispatch("change", None)
    assert 'data-testid="ghost-line"' in m.timeline_chart_svg("standing")


def test_a_session_that_was_ever_not_comparable_is_never_kept(game_env):
    m = game_env.module
    game_env.reset_session()
    m.reset_session(scenario="clearcut")                                 # a scenario forest: not comparable
    assert m.ghost_mode_key() is None and "not kept for" in m.ghost_note_text()
    game_env.tick(40)
    assert m._ghost_live == [] and m._ghost_state["tainted"] is True
    m.reset_session(scenario=m.SCENARIO_NONE)
    assert _stored(game_env) is None


def test_hostile_stored_data_is_dropped_or_cleaned(game_env):
    m = game_env.module
    good = {"v": 1, "turns": 40, "values": [float(i) for i in range(40)], "label": "best session"}
    bad_blobs = [
        "not json", "[]", "5", '{"normal:normal:normal": "x"}',
        json.dumps({"normal:normal:normal": {"score": "high", "trace": good}}),
        json.dumps({"normal:normal:normal": {"score": 3, "trace": {"turns": 40, "values": [1]}}}),
        json.dumps({"normal:normal:normal": {"score": 3, "trace": dict(good, turns=10 ** 9)}}),   # past the 5000 cap
        json.dumps({"../../x": {"score": 3, "trace": good}, "a:b": {"score": 3, "trace": good},
                    "a:b:c:d": {"score": 3, "trace": good}, "x" * 50 + ":b:c": {"score": 3, "trace": good}}),
        json.dumps({"normal:normal:normal": {"score": 3, "trace": dict(good, values=["a", None, True, [1], {}])}}),
        json.dumps({"normal:normal:normal": {"score": 3, "trace": dict(good, values=[1.0] * 9000)}}),
    ]
    for blob in bad_blobs:
        game_env.local_storage.setItem(m.GHOST_STORAGE_KEY, blob)
        assert m.load_ghosts() == {}, blob
        m.render()                                                       # never breaks the page
        m.ghost_note_text()
    many = {f"normal:size{i}:normal": {"score": i, "trace": good} for i in range(60)}
    game_env.local_storage.setItem(m.GHOST_STORAGE_KEY, json.dumps(many))
    assert len(m.load_ghosts()) == m.GHOST_MAX_MODES
    game_env.local_storage.setItem(m.GHOST_STORAGE_KEY, json.dumps({"normal:normal:normal": {"score": 7.256, "trace": dict(good, label="<b>" * 30)}}))
    entry = m.load_ghosts()["normal:normal:normal"]
    assert entry["score"] == 7.26 and len(entry["trace"]["label"]) <= 40


def test_saves_are_unchanged_and_loading_one_starts_a_fresh_ghost_session(game_env):
    m = game_env.module
    state = m.get_state()
    assert not any("ghost" in key for key in state)                      # no new save key, ghosts live per device
    game_env.tick(5)
    assert len(m._ghost_live) == 5
    m.load_state(json.loads(json.dumps(state)))
    assert m._ghost_live == [] and m._ghost_state == {"peak": 0.0, "tainted": False}
    game_env.tick(2)
    assert len(m._ghost_live) == 2


def test_a_very_long_session_stops_recording_at_the_cap(game_env):
    m = game_env.module
    for _ in range(m.GHOST_LIVE_CAP + 5):
        m._record_ghost_tick(1.0)
    assert len(m._ghost_live) == m.GHOST_LIVE_CAP


def test_gaps_are_read_to_one_decimal_and_a_tiny_one_is_level(game_env):
    m = game_env.module
    ahead = {"status": "ahead", "lead": 12.3456, "turn": 3}
    assert m._rounded_result(ahead, 1)["lead"] == 12.3
    assert m._rounded_result({"status": "behind", "lead": 0.04, "turn": 3}, 1)["status"] == "level"
    assert m._rounded_result({"status": "ended", "lead": 0, "turn": 3}, 1)["status"] == "ended"
    assert m._rounded_result(None, 1) is None
