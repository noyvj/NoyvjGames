"""A-29 (the Ghost Run): recordings, the personal-best rule, the split track and the Scarcity Run ghosts."""

import json

import challenges

TODAY = "2026-10-11"


def _texts(element):
    out = [element.innerText]
    for child in element.children:
        out.extend(_texts(child))
    return out


def _text(env, panel):
    return "\n".join(t for t in _texts(env.elements[panel]) if t)


def _buttons(element, found=None):
    found = [] if found is None else found
    if element.getAttribute("data-action"):
        found.append(element)
    for child in element.children:
        _buttons(child, found)
    return found


def _set_average(env, percent):
    for planet in env.module.PLANETS:
        env.module.planet_state[planet]["terraform_progress"] = float(percent)


def _tick_to_run_tick(env, run_tick, percent=None):
    """Advances the game with a fixed terraform average until the run clock reads run_tick."""
    m = env.module
    while m._run_ticks() < run_tick:
        if percent is not None:
            _set_average(env, percent)
        m.tick()


def _pb(env, ticks, pct):
    env.local_storage.setItem("sol-ghost-pb-v1", json.dumps({"ticks": ticks, "pct": pct}))
    env.module._load_pb_ghost()


# --- the pure recording helpers ------------------------------------------------------------------------


def test_recordings_are_validated_whole_or_dropped():
    good = {"ticks": 400, "pct": [0, 10, 25, 1000]}
    assert challenges.clean_recording(good) == good
    for bad in (None, "x", [], {"ticks": 400}, {"pct": [0, 1]}, {"ticks": 0, "pct": [0, 1]}, {"ticks": True, "pct": [0, 1]},
                {"ticks": 400, "pct": [5]}, {"ticks": 400, "pct": [0, -1]}, {"ticks": 400, "pct": [0, 1001]},
                {"ticks": 400, "pct": [0, 1.5]}, {"ticks": 400, "pct": [0, "7"]}, {"ticks": 400, "pct": [0, True]},
                {"ticks": 400, "pct": [0] * (challenges.GHOST_MAX_SAMPLES + 1)}, {"ticks": 10 ** 9, "pct": [0, 1]}):
        assert challenges.clean_recording(bad) is None, bad


def test_the_ghost_holds_its_last_value_after_it_finishes():
    rec = {"ticks": 100, "pct": [0, 100, 1000]}
    assert challenges.ghost_value(rec, 1) == 10.0 and challenges.ghost_value(rec, 2) == 100.0
    assert challenges.ghost_value(rec, 50) == 100.0


def test_the_lead_is_written_in_words_and_signs():
    assert challenges.lead_text(12.9, 12.4) == "+0.5 points ahead"
    assert challenges.lead_text(12.4, 12.9) == "-0.5 points behind"
    assert challenges.lead_text(5.0, 5.0) == "level (+0.0)"


def test_split_rows_carry_a_signed_difference_in_text():
    rec = {"ticks": 100, "pct": [0, 100, 200, 300]}
    rows = challenges.split_rows([0, 120, 150], rec)
    assert [r["text"] for r in rows] == ["+0.0", "+2.0", "-5.0"]
    assert [r["tick"] for r in rows] == [0, 25, 50]
    assert challenges.ghost_summary([0, 120, 150], rec) == (1, 1, 1)
    many = challenges.split_rows(list(range(100)), {"ticks": 100, "pct": [0, 1]})
    assert len(many) == challenges.GHOST_TRACK_ROWS


# --- campaign recording ----------------------------------------------------------------------------------


def test_normal_play_records_the_average_terraform_every_25_ticks(game_env):
    m = game_env.module
    m.tick()  # the run clock is 1; nothing to sample yet apart from the start
    _tick_to_run_tick(game_env, 50, percent=40)
    assert len(m._live_ghost) == 3  # run ticks 0, 25, 50
    assert m._live_ghost[1] == 400 and m._live_ghost[2] == 400
    assert m._live_ghost_partial is False


def test_the_recording_follows_the_run_clock_not_the_lifetime_clock(game_env):
    m = game_env.module
    m.total_ticks = 975
    m.run_start_tick = 975
    m._ghost_reload_live()
    _tick_to_run_tick(game_env, 25, percent=10)
    assert len(m._live_ghost) == 2 and m._live_ghost_partial is False


def test_a_run_joined_late_can_never_become_the_best(game_env):
    m = game_env.module
    m.total_ticks = 500
    m._ghost_reload_live()
    assert m._live_ghost_partial is True
    assert m._ghost_run_finished(400, True) is False and m._pb_ghost is None


def test_the_in_progress_recording_survives_a_save_load_of_the_same_run(game_env):
    m = game_env.module
    _tick_to_run_tick(game_env, 25 * 8, percent=20)  # 9 samples, one write at 8
    saved = json.loads(game_env.local_storage.getItem("sol-ghost-live-v1"))
    assert saved["run"] == m.run_start_tick and len(saved["pct"]) == 8
    state = m.get_state()
    state["total_ticks"] = 25 * 7 + 3
    m.load_state(state)
    assert len(m._live_ghost) == 8 and m._live_ghost_partial is False  # picked up, trimmed to the loaded clock
    assert "ghost" not in json.dumps(m.get_state()).lower()


def test_a_recording_from_another_run_is_not_reused(game_env):
    m = game_env.module
    game_env.local_storage.setItem("sol-ghost-live-v1", json.dumps({"run": 99999, "pct": [0, 1, 2]}))
    m.total_ticks = 50
    m._ghost_reload_live()
    assert m._live_ghost == [] and m._live_ghost_partial is True


def test_junk_in_storage_is_ignored_on_read(game_env):
    m = game_env.module
    for junk in ("not json", "[]", json.dumps({"ticks": 5, "pct": ["a", "b"]}), json.dumps({"run": 0, "pct": "x"}), ""):
        game_env.local_storage.setItem("sol-ghost-pb-v1", junk)
        game_env.local_storage.setItem("sol-ghost-live-v1", junk)
        game_env.local_storage.setItem("sol-ghost-daily-v1", junk)
        m._load_pb_ghost()
        m._ghost_reload_live()
        assert m._pb_ghost is None and m._load_daily_ghosts() == {}


def test_a_bad_entry_in_the_daily_map_is_dropped_alone(game_env):
    m = game_env.module
    good = {"ticks": 300, "pct": [0, 500, 1000]}
    game_env.local_storage.setItem("sol-ghost-daily-v1", json.dumps({"2026-10-02": good, "2026-10-03": {"ticks": 1}, "bad": good}))
    assert m._load_daily_ghosts() == {"2026-10-02": good}


def test_the_best_recording_is_kept_only_when_it_is_a_new_best(game_env):
    m = game_env.module
    m._live_ghost[:] = [0, 100, 600]
    assert m._ghost_run_finished(2000, True) is True
    assert m._pb_ghost == {"ticks": 2000, "pct": [0, 100, 600, 1000]}
    stored = json.loads(game_env.local_storage.getItem("sol-ghost-pb-v1"))
    assert stored == m._pb_ghost
    m._live_ghost[:] = [0, 50, 300]
    assert m._ghost_run_finished(2500, False) is False  # slower: the old recording stays
    assert json.loads(game_env.local_storage.getItem("sol-ghost-pb-v1")) == stored
    m._live_ghost[:] = [0, 200, 800]
    assert m._ghost_run_finished(1800, True) is True and m._pb_ghost["ticks"] == 1800


def test_finishing_a_whole_system_run_keeps_the_recording_through_the_real_path(game_env):
    m = game_env.module
    _tick_to_run_tick(game_env, 75, percent=30)
    _set_average(game_env, 100)
    m.tick()
    assert m.run_completed is True and m.best_run_ticks is not None
    assert m._pb_ghost is not None and m._pb_ghost["ticks"] == m.best_run_ticks and m._pb_ghost["pct"][-1] == 1000
    # a slower run later does not replace it
    kept = dict(m._pb_ghost)
    m.run_completed = False
    m.run_start_tick = m.total_ticks - 5000
    m._live_ghost[:] = [0] * 201
    m._live_ghost_partial = False
    m._live_ghost_run = m.run_start_tick
    m.tick()
    assert m._pb_ghost == kept


def test_a_world_reset_makes_a_recording_that_is_not_a_single_climb_but_it_stays_valid_data(game_env):
    m = game_env.module
    _tick_to_run_tick(game_env, 50, percent=40)
    _tick_to_run_tick(game_env, 75, percent=10)
    assert challenges.clean_recording({"ticks": 100, "pct": list(m._live_ghost)}) is not None


def test_prestige_starts_a_fresh_recording(game_env):
    m = game_env.module
    _tick_to_run_tick(game_env, 50, percent=40)
    m.run_start_tick = m.total_ticks
    _tick_to_run_tick(game_env, 25, percent=5)
    assert len(m._live_ghost) == 2 and m._live_ghost_partial is False


# --- the ghost race in normal play ----------------------------------------------------------------------


def test_no_ghost_line_until_the_player_turns_it_on_and_has_a_best(game_env):
    _tick_to_run_tick(game_env, 25, percent=10)
    assert game_env.elements["ghost-strip"].hidden is True
    _pb(game_env, 2000, [0, 50, 100, 1000])
    game_env.local_storage.setItem("sol-ghost-on", "on")
    _tick_to_run_tick(game_env, 50, percent=10)
    strip = game_env.elements["ghost-strip"]
    assert strip.hidden is False
    assert "you 10.0%" in strip.innerText and "ghost 10.0%" in strip.innerText and "level (+0.0)" in strip.innerText


def test_the_strip_says_ahead_or_behind_with_a_sign(game_env):
    _pb(game_env, 2000, [0, 50, 100, 1000])
    game_env.local_storage.setItem("sol-ghost-on", "on")
    _tick_to_run_tick(game_env, 25, percent=8.0)
    assert "+3.0 points ahead" in game_env.elements["ghost-strip"].innerText
    _tick_to_run_tick(game_env, 50, percent=4.0)
    assert "-6.0 points behind" in game_env.elements["ghost-strip"].innerText


def test_the_splits_panel_gets_a_ghost_section_and_a_switch_that_survives_ticks(game_env):
    m = game_env.module
    game_env.local_storage.setItem("sol-show-timing", "on")
    game_env.elements["splits-toggle-button"].dispatch("click", None)
    text = _text(game_env, "splits-panel")
    assert "Speedrun splits" in text and "Ghost Run" in text and "No personal-best recording yet" in text
    _pb(game_env, 2000, [0, 50, 100, 1000])
    m.update_splits_display(force=True)
    switch = [b for b in _buttons(game_env.elements["splits-panel"]) if b.getAttribute("data-action") == "ghost-toggle"][0]
    assert switch.innerText == "Ghost run: Off" and not switch.disabled
    for _ in range(5):
        m.tick()
    same = [b for b in _buttons(game_env.elements["splits-panel"]) if b.getAttribute("data-action") == "ghost-toggle"][0]
    assert same is switch  # not rebuilt under the player's finger
    game_env.panel_click("splits-panel", action="ghost-toggle")
    assert game_env.local_storage.getItem("sol-ghost-on") == "on"
    assert "Ghost run: On" in _text(game_env, "splits-panel")
    _tick_to_run_tick(game_env, 75, percent=20)
    track = _text(game_env, "splits-panel")
    assert "Split track vs your best run" in track and "ahead" in track and "+" in track
    game_env.panel_click("splits-panel", action="ghost-toggle")
    assert game_env.local_storage.getItem("sol-ghost-on") == "off"


def test_the_old_split_rows_still_read_the_same(game_env):
    m = game_env.module
    m.run_splits["Moon"] = 600
    m.pb_splits["Moon"] = 650
    game_env.local_storage.setItem("sol-show-timing", "on")
    game_env.elements["splits-toggle-button"].dispatch("click", None)
    text = _text(game_env, "splits-panel")
    assert "Moon: 1m 0s (best 1m 5s, -5s)" in text and "Mars: not yet" in text


def test_ghost_data_never_enters_the_save(game_env):
    m = game_env.module
    _pb(game_env, 2000, [0, 50, 100, 1000])
    _tick_to_run_tick(game_env, 100, percent=10)
    assert '"pct": [' not in json.dumps(m.get_state()) and "ghost" not in json.dumps(m.get_state()).lower()


# --- Scarcity Run ghosts -----------------------------------------------------------------------------------


def _finish(env, extra_ticks=0):
    m = env.module
    for _ in range(extra_ticks):
        m.tick()
    for world in m._scarcity["spec"]["targets"]:
        m.planet_state[world]["terraform_progress"] = float(m._scarcity["spec"]["target_pct"]) + 5
    m.tick()


def test_the_governor_alone_can_be_raced_as_a_ghost(game_env):
    m = game_env.module
    m.TODAY_OVERRIDE = TODAY
    m._scarcity_ghost_choice = "par"
    m.start_scarcity_run(TODAY)
    for _ in range(50):
        m.tick()
    strip = game_env.elements["ghost-strip"]
    assert strip.hidden is False and "the Governor alone" in strip.innerText
    assert len(m._scarcity["samples"]) == 3
    assert game_env.elements["ghost-strip"].innerText.count("%") == 2
    m.leave_scarcity_run()
    assert game_env.elements["ghost-strip"].hidden is True


def test_a_runs_best_recording_is_kept_per_date_only_when_faster(game_env):
    m = game_env.module
    m.TODAY_OVERRIDE = TODAY
    m.start_scarcity_run(TODAY)
    _finish(game_env, extra_ticks=60)
    first = m._load_daily_ghosts()[TODAY]
    assert first["ticks"] == 61 and first["pct"][-1] == 1000
    m.start_scarcity_run(TODAY)
    _finish(game_env, extra_ticks=120)  # slower
    assert m._load_daily_ghosts()[TODAY] == first
    m.start_scarcity_run(TODAY)
    _finish(game_env, extra_ticks=10)  # faster
    assert m._load_daily_ghosts()[TODAY]["ticks"] == 11


def test_your_best_for_the_day_can_be_raced_and_is_off_the_menu_until_it_exists(game_env):
    m = game_env.module
    m.TODAY_OVERRIDE = TODAY
    m.start_scarcity_run(TODAY)
    _finish(game_env, extra_ticks=60)
    m.leave_scarcity_run()
    game_env.elements["scarcity-toggle-button"].dispatch("click", None)
    choices = {b.getAttribute("data-value"): b for b in _buttons(game_env.elements["scarcity-panel"]) if b.getAttribute("data-action") == "ghost-choice"}
    assert not choices["best"].disabled and choices["friend"].disabled
    game_env.panel_click("scarcity-panel", action="ghost-choice", value="best")
    game_env.panel_click("scarcity-panel", action="play", date=TODAY)
    assert m._scarcity["ghost"] is not None and m._scarcity["ghost_label"] == "your best for this day"
    other = m.start_scarcity_run("2026-10-03")
    assert other and m._scarcity["ghost"] is None  # no recording for that day yet


def test_a_friends_blueprint_races_as_the_governor_playing_their_rules(game_env):
    m = game_env.module
    m.TODAY_OVERRIDE = TODAY
    m.researched_nodes.add("automation_basics")
    m.doctrine_rules[:] = [{"planet": "Mars", "cond": "ecology_below", "level": 50, "action": "recycler"}]
    m.mutators_next[:] = ["thin_atmosphere"]
    code = m.blueprint_code()
    ok, message = m.make_friend_ghost(code, TODAY)
    assert ok and "Ghost ready" in message
    assert m._scarcity_friend["date"] == TODAY and m._scarcity_friend["rec"]["pct"]
    m._scarcity_ghost_choice = "friend"
    before = json.dumps(m.get_state(), sort_keys=True)
    m.start_scarcity_run(TODAY)
    assert m._scarcity["ghost_label"].startswith("a friend's blueprint")
    assert m.mutators_run == [] and m.doctrine_rules == []  # their rules race; they are not yours
    m.leave_scarcity_run()
    assert json.dumps(m.get_state(), sort_keys=True) == before


def test_a_friend_blueprint_without_rules_or_with_a_bad_code_is_refused_kindly(game_env):
    m = game_env.module
    m.TODAY_OVERRIDE = TODAY
    m.build_plan[:] = [{"text": "Recyclers first", "done": False}]
    ok, message = m.make_friend_ghost(m.blueprint_code(), TODAY)
    assert ok is False and "no Doctrines or rule twists" in message
    ok, message = m.make_friend_ghost("SOLPLAN1:@@@", TODAY)
    assert ok is False and message
    ok, message = m.make_friend_ghost("", TODAY)
    assert ok is False
    m.mutators_next[:] = ["thin_atmosphere"]
    assert m.make_friend_ghost(m.blueprint_code(), "2026-12-01")[0] is False  # a day that is not open yet


def test_the_friend_code_field_survives_a_panel_rebuild(game_env):
    m = game_env.module
    m.TODAY_OVERRIDE = TODAY
    game_env.elements["scarcity-toggle-button"].dispatch("click", None)
    field = m._scarcity_refs["friend"]
    field.value = "SOLPLAN1:half-pasted"
    game_env.panel_click("scarcity-panel", action="pick", date="2026-10-02")
    assert m._scarcity_refs["friend"].value == "SOLPLAN1:half-pasted"


def test_the_campaign_recording_pauses_during_a_run_and_resumes_after(game_env):
    m = game_env.module
    m.TODAY_OVERRIDE = TODAY
    _tick_to_run_tick(game_env, 50, percent=25)
    kept = list(m._live_ghost)
    m.start_scarcity_run(TODAY)
    for _ in range(60):
        m.tick()
    m.leave_scarcity_run()
    assert m._live_ghost == kept
    _tick_to_run_tick(game_env, 75, percent=25)
    assert len(m._live_ghost) == 4
