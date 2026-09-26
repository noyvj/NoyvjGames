"""L7a/L7b -- a real calendar-day tracker and a study calendar.

`game.py` may not touch a clock (Milestone 7), so the real date arrives via a
JS hook; tests inject it through `_today_override`.
"""

import json


def _today(module, iso):
    module._today_override = iso


def test_no_clock_means_nothing_is_recorded(game_env):
    module = game_env.module
    module._today_override = None
    module.note_study_answer()
    assert module.study_days == {}


def test_answers_are_counted_against_todays_real_date(game_env):
    module = game_env.module
    _today(module, "2026-09-10")
    module.note_study_answer()
    module.note_study_answer()
    _today(module, "2026-09-11")
    module.note_study_answer()
    assert module.study_days == {"2026-09-10": 2, "2026-09-11": 1}


def test_a_main_panel_answer_counts_exactly_once(game_env):
    module = game_env.module
    _today(module, "2026-09-10")
    plot = game_env.state.plots[0]
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_CHOICE)
    module.submit_answer(module.current_question["answer"])
    assert module.study_days == {"2026-09-10": 1}


def test_a_practice_mode_answer_counts_once_too(game_env):
    module = game_env.module
    _today(module, "2026-09-10")
    module.record_practice("liaison", True)
    assert module.study_days == {"2026-09-10": 1}


def test_history_is_capped_to_the_newest_days(game_env):
    module = game_env.module
    for i in range(module.STUDY_DAY_LIMIT + 5):
        year = 2000 + i // 360
        month = (i % 360) // 30 + 1
        day = i % 30 + 1
        _today(module, f"{year}-{month:02d}-{day:02d}")
        module.note_study_answer()
    assert len(module.study_days) == module.STUDY_DAY_LIMIT
    assert "2000-01-01" not in module.study_days


def test_save_round_trip_and_default_save_stays_small(game_env):
    module = game_env.module
    assert "study_days" not in module.get_state()
    _today(module, "2026-09-10")
    module.note_study_answer()
    saved = json.loads(json.dumps(module.get_state()))
    assert saved["study_days"] == {"2026-09-10": 1}
    module.study_days = {}
    assert module.load_state(saved) is True
    assert module.study_days == {"2026-09-10": 1}


def test_a_tampered_save_cannot_inject_junk_days(game_env):
    module = game_env.module
    saved = module.get_state()
    saved["study_days"] = {
        "2026-09-10": 3,
        "2026-13-01": 2,      # not a month
        "2026-02-30": 2,      # not a day
        "yesterday": 2,
        "2026-09-11": 0,
        "2026-09-12": True,
        "2026-09-13": "5",
        "2026-09-14": 10**9,
    }
    module.load_state(saved)
    assert module.study_days == {"2026-09-10": 3, "2026-09-14": module.STUDY_COUNT_LIMIT}
    saved["study_days"] = "not a dict"
    module.load_state(saved)
    assert module.study_days == {}


def test_calendar_grid_is_monday_first_and_correct_for_a_real_month(game_env):
    module = game_env.module
    weeks = module.calendar_month_days(2026, 9)  # 1 Sep 2026 is a Tuesday
    assert weeks[0][:2] == [0, 1] and weeks[0][2] == 2
    assert sum(1 for w in weeks for d in w if d) == 30


def test_panel_toggles_and_marks_studied_days_with_text(game_env):
    module = game_env.module
    _today(module, "2026-09-10")
    module.note_study_answer()
    module.note_study_answer()
    game_env.elements["calendar-toggle-button"].dispatch("click", None)
    assert game_env.elements["calendar-panel"].hidden is False
    assert game_env.elements["calendar-month-label"].innerText == "September 2026"
    cells = game_env.elements["calendar-grid"].children
    studied = [c for c in cells if "calendar-cell--studied" in c.className]
    assert len(studied) == 1
    assert "today" in studied[0].className and "2 answers" in studied[0].title
    assert any(child.innerText == "·2" for child in studied[0].children)
    assert "1 day" in game_env.elements["calendar-summary"].innerText
    game_env.elements["calendar-toggle-button"].dispatch("click", None)
    assert game_env.elements["calendar-panel"].hidden is True


def test_month_navigation_is_bounded_by_today_and_history(game_env):
    module = game_env.module
    _today(module, "2026-09-10")
    game_env.elements["calendar-toggle-button"].dispatch("click", None)
    assert game_env.elements["calendar-next-button"].disabled is True  # can't browse the future
    game_env.elements["calendar-prev-button"].dispatch("click", None)
    assert game_env.elements["calendar-month-label"].innerText == "August 2026"
    assert game_env.elements["calendar-next-button"].disabled is False
    for _ in range(module.CALENDAR_MONTHS_BACK + 5):
        game_env.elements["calendar-prev-button"].dispatch("click", None)
    assert game_env.elements["calendar-prev-button"].disabled is True


def test_empty_state_is_gentle_and_never_shames(game_env):
    module = game_env.module
    _today(module, "2026-09-10")
    game_env.elements["calendar-toggle-button"].dispatch("click", None)
    text = game_env.elements["calendar-summary"].innerText.lower()
    assert "expires" in text
    assert "streak" not in text and "missed" not in text and "broke" not in text


def test_without_a_clock_the_panel_says_so_instead_of_breaking(game_env):
    module = game_env.module
    module._today_override = None
    game_env.elements["calendar-toggle-button"].dispatch("click", None)
    assert "Nothing to show yet" in game_env.elements["calendar-summary"].innerText
