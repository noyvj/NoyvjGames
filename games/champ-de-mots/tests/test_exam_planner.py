"""L-9 exam-date planner and L-28 header exam countdown.

The planner replays the real scheduler on copies of every plot, so these tests
pin: the day arithmetic, that no real plot is touched, that the projection is
monotonic in effort, that the minimum-effort suggestion really is the smallest
step that reaches the target, the countdown chip, and a fully validated save.
"""

TODAY = "2026-10-07"


def _snapshot(state):
    return [
        (p.plot_id, p.stage, p.interval_days, p.next_due, p.last_reviewed, p.correct_streak, p.ease_factor)
        for p in state.plots
    ]


def _env(game_env, exam="2026-12-06"):
    module = game_env.module
    module._today_override = TODAY
    if exam:
        module.set_exam_date(exam)
    return module


def test_fresh_game_has_no_exam_date_and_the_chip_is_hidden(game_env):
    module = game_env.module
    module.render()
    assert module.exam_date is None
    assert game_env.elements["exam-countdown-tile"].hidden is True
    assert game_env.elements["exam-countdown-display"].innerText == ""
    assert game_env.elements["planner-panel"].hidden is True


def test_day_arithmetic_across_a_month_and_a_leap_day(game_env):
    module = _env(game_env, exam=None)
    module.exam_date = "2026-10-08"
    assert module.exam_days_left() == 1
    module.exam_date = "2026-12-06"
    assert module.exam_days_left() == 60
    module._today_override = "2028-02-28"
    module.exam_date = "2028-03-01"
    assert module.exam_days_left() == 2  # 2028 is a leap year
    module.exam_date = "2028-02-27"
    assert module.exam_days_left() == -1


def test_no_clock_means_no_countdown(game_env):
    module = game_env.module
    module.exam_date = "2026-12-06"
    assert module.exam_days_left() is None
    assert module.exam_countdown_text() == ""


def test_set_exam_date_rejects_junk_and_clears_on_empty(game_env):
    module = _env(game_env)
    assert module.exam_date == "2026-12-06"
    for junk in ("2026-02-30", "soon", "2026-13-01", "20261206", "1969-12-31", None, 5):
        assert module.set_exam_date(junk) is False
        assert module.exam_date is None
    assert module.set_exam_date("2026-12-06") is True
    assert module.set_exam_date("") is False
    assert module.exam_date is None


def test_minutes_are_clamped_and_snapped(game_env):
    module = game_env.module
    assert module.set_exam_minutes(1) == module.PLANNER_MIN_MINUTES
    assert module.set_exam_minutes(9999) == module.PLANNER_MAX_MINUTES
    assert module.set_exam_minutes("22") == 20
    assert module.set_exam_minutes("abc") == module.PLANNER_DEFAULT_MINUTES
    assert module.set_exam_minutes(None) == module.PLANNER_DEFAULT_MINUTES


def test_projection_never_touches_a_real_plot(game_env):
    module = _env(game_env)
    state = game_env.state
    for plot in state.plots[:30]:
        state.review(plot.plot_id, True)
    before = _snapshot(state)
    day = state.current_day
    module.planner_projection()
    module.planner_minimum_minutes()
    module.render()
    assert _snapshot(state) == before
    assert state.current_day == day


def test_simulation_replays_the_real_scheduler(game_env):
    module = game_env.module
    state = game_env.state
    plot = state.plots[0]
    state.plots = [plot]
    module.state.plots = [plot]
    reference = module._SimPlot(plot)
    day0 = state.current_day
    automated_on = None
    for offset in range(60):
        day = day0 + offset
        if reference.last_reviewed is None or reference.next_due <= day:
            module.schedule_after_review(reference, True, day)
        if automated_on is None and reference.stage == module.STAGE_AUTOMATED:
            automated_on = offset
    assert automated_on is not None
    just_short = module.simulate_harvest(automated_on, 5)
    enough = module.simulate_harvest(automated_on + 1, 5)
    assert just_short["automated"] == 0
    assert enough["automated"] == 1 and enough["percent"] == 100.0


def test_cautious_never_beats_best_and_more_minutes_never_hurts(game_env):
    module = _env(game_env)
    low = module.planner_projection(5)
    high = module.planner_projection(60)
    assert low["cautious"] <= low["best"]
    assert high["cautious"] <= high["best"]
    assert high["cautious"] >= low["cautious"]
    assert high["best"] >= low["best"]
    assert high["best"] > 0


def test_projection_counts_what_is_automated_already(game_env):
    module = _env(game_env)
    state = game_env.state
    for plot in state.plots[:100]:
        plot.stage = module.STAGE_AUTOMATED
        plot.last_reviewed = 0
        plot.next_due = 400
        plot.interval_days = 30
        plot.correct_streak = 5
    projection = module.planner_projection(5)
    assert projection["current"] > 12
    assert projection["cautious"] >= projection["current"] - 0.001


def test_no_projection_without_a_future_date(game_env):
    module = _env(game_env, exam=None)
    assert module.planner_projection() is None
    assert module.planner_minimum_minutes() is None
    module.exam_date = TODAY
    assert module.planner_projection() is None
    module.exam_date = "2026-01-01"
    assert module.planner_projection() is None


def test_minimum_minutes_is_the_smallest_step_that_reaches_the_target(game_env):
    module = _env(game_env, exam="2026-12-31")  # 85 days
    kind, value = module.planner_minimum_minutes()
    assert kind == "minutes"
    assert module.PLANNER_MIN_MINUTES <= value <= module.PLANNER_MAX_MINUTES
    days = module.exam_days_left()
    assert module.simulate_harvest(days, value, module.PLANNER_MISS_EVERY)["percent"] >= module.PLANNER_TARGET_PERCENT
    if value > module.PLANNER_MIN_MINUTES:
        smaller = value - module.PLANNER_STEP_MINUTES
        assert module.simulate_harvest(days, smaller, module.PLANNER_MISS_EVERY)["percent"] < module.PLANNER_TARGET_PERCENT


def test_a_short_runway_is_reported_as_out_of_reach(game_env):
    module = _env(game_env, exam="2026-10-09")
    kind, best = module.planner_minimum_minutes()
    assert kind == "unreachable"
    assert 0 <= best < module.PLANNER_TARGET_PERCENT
    module.planner_open = True
    module.render()
    assert "out of reach" in game_env.elements["planner-suggestion"].innerText


def test_a_farm_already_past_the_target_says_so(game_env):
    module = _env(game_env)
    for plot in game_env.state.plots:
        plot.stage = module.STAGE_AUTOMATED
    kind, value = module.planner_minimum_minutes()
    assert (kind, value) == ("already", None)


def test_countdown_chip_text_and_visibility(game_env):
    module = _env(game_env)
    module.render()
    text = game_env.elements["exam-countdown-display"].innerText
    assert text.startswith("Exam in 60 days")
    assert "% automated by then" in text
    assert game_env.elements["exam-countdown-tile"].hidden is False
    module.set_exam_date("2026-10-08")
    assert game_env.elements["exam-countdown-display"].innerText.startswith("Exam in 1 day ")
    module.set_exam_date(TODAY)
    assert game_env.elements["exam-countdown-display"].innerText == "Exam today"
    module.set_exam_date("2026-10-01")
    assert game_env.elements["exam-countdown-display"].innerText == ""
    assert game_env.elements["exam-countdown-tile"].hidden is True


def test_panel_opens_and_shows_the_numbers(game_env):
    module = _env(game_env)
    game_env.elements["planner-toggle-button"].dispatch("click", None)
    assert module.planner_open is True
    assert game_env.elements["planner-panel"].hidden is False
    assert "60 days to go" in game_env.elements["planner-summary"].innerText
    assert "minutes a day" in game_env.elements["planner-projection"].innerText
    assert game_env.elements["planner-date-input"].value == "2026-12-06"
    assert game_env.elements["planner-minutes-label"].innerText == "15 minutes a day"
    game_env.elements["planner-toggle-button"].dispatch("click", None)
    assert game_env.elements["planner-panel"].hidden is True


def test_date_and_slider_controls_drive_the_planner(game_env):
    module = game_env.module
    module._today_override = TODAY
    game_env.elements["planner-date-input"].value = "2027-01-15"
    game_env.elements["planner-date-input"].dispatch("change", None)
    assert module.exam_date == "2027-01-15"
    game_env.elements["planner-minutes-input"].value = "45"
    game_env.elements["planner-minutes-input"].dispatch("input", None)
    assert module.exam_minutes == 45
    game_env.elements["planner-clear-button"].dispatch("click", None)
    assert module.exam_date is None
    assert game_env.elements["planner-date-input"].value == ""


def test_planning_is_not_a_drill_so_it_leaves_the_ledger_alone(game_env):
    module = _env(game_env)
    module.planner_open = True
    module.render()
    assert module.practice_score() == 0


# --- save / load -----------------------------------------------------------


def test_default_save_has_no_exam_plan_key(game_env):
    assert "exam_plan" not in game_env.module.get_state()


def test_exam_plan_round_trips(game_env):
    module = _env(game_env)
    module.set_exam_minutes(40)
    saved = module.get_state()
    assert saved["exam_plan"] == {"date": "2026-12-06", "minutes": 40}
    module.set_exam_date("")
    module.set_exam_minutes(10)
    module.load_state(saved)
    assert module.exam_date == "2026-12-06" and module.exam_minutes == 40


def test_loading_a_save_without_the_key_clears_the_plan(game_env):
    module = _env(game_env)
    module.load_state({"version": 1, "current_day": 0, "plots": {}})
    assert module.exam_date is None
    assert module.exam_minutes == module.PLANNER_DEFAULT_MINUTES


def test_hostile_exam_plan_saves_are_dropped_or_clamped(game_env):
    module = game_env.module
    base = {"version": 1, "current_day": 0, "plots": {}}
    hostile = [
        "2026-12-06",
        ["2026-12-06", 15],
        {"date": "2026-02-30", "minutes": 15},
        {"date": 20261206, "minutes": 15},
        {"date": "<script>", "minutes": 15},
        {"date": "1900-01-01", "minutes": 15},
        {"date": "2026-12-06", "minutes": True},
        {"date": "2026-12-06", "minutes": "30"},
        {"date": "2026-12-06", "minutes": 10**9},
        {"date": "2026-12-06", "minutes": -5},
        {"date": "2026-12-06", "minutes": 1.5},
        {"date": "2026-12-06", "minutes": None, "extra": [1]},
    ]
    for raw in hostile:
        module.load_state({**base, "exam_plan": raw})
        assert module.exam_date in (None, "2026-12-06")
        assert module.PLANNER_MIN_MINUTES <= module.exam_minutes <= module.PLANNER_MAX_MINUTES
        assert module.exam_minutes % module.PLANNER_STEP_MINUTES == 0
    module.load_state({**base, "exam_plan": {"date": "2026-12-06", "minutes": 10**9}})
    assert module.exam_minutes == module.PLANNER_MAX_MINUTES
    module.load_state({**base, "exam_plan": {"date": "2026-12-06", "minutes": True}})
    assert module.exam_minutes == module.PLANNER_DEFAULT_MINUTES
    module.load_state({**base, "exam_plan": {"date": "2026-02-30", "minutes": 20}})
    assert module.exam_date is None
