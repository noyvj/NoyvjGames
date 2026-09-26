"""E19: the resilience curriculum (a guided sequence of runs with one goal each)."""


def _finished(m, **fields):
    r = m.RunState()
    r.event_index = len(r.schedule)
    for key, value in fields.items():
        setattr(r, key, value)
    return r


def test_five_lessons_each_with_a_goal_and_an_idea(game_env):
    m = game_env.module
    assert len(m.CURRICULUM) == 5
    ids = [lesson["id"] for lesson in m.CURRICULUM]
    assert len(set(ids)) == 5
    for lesson in m.CURRICULUM:
        assert lesson["title"] and lesson["goal"] and lesson["idea"] and callable(lesson["check"])


def test_starts_on_lesson_one_and_shows_its_goal(game_env):
    m = game_env.module
    m.render()
    assert m.curriculum_progress == 0 and m.curriculum_current()["id"] == "first_steps"
    text = game_env.elements["curriculum-display"].innerText
    assert "lesson 1 of 5" in text and "First steps" in text and "Goal:" in text


def test_meeting_the_current_goal_advances(game_env):
    m = game_env.module
    lesson = m.note_curriculum_run(_finished(m, resources=50.0))
    assert lesson["id"] == "first_steps" and m.curriculum_progress == 1
    assert m.curriculum_current()["id"] == "resilience_first"


def test_missing_the_goal_stays_on_the_lesson(game_env):
    m = game_env.module
    assert m.note_curriculum_run(_finished(m, resources=0.0)) is None
    assert m.curriculum_progress == 0


def test_lessons_are_strictly_in_order(game_env):
    m = game_env.module
    # a run that would satisfy lesson 2 does nothing while lesson 1 is current... except lesson 1 itself passes
    r = _finished(m, resources=500.0, resilience_capacity=5, growth_capacity=5)
    assert m.note_curriculum_run(r)["id"] == "first_steps"
    assert m.note_curriculum_run(r)["id"] == "resilience_first"
    assert m.note_curriculum_run(r)["id"] == "growth_pays"
    assert m.note_curriculum_run(r)["id"] == "balance"
    assert m.note_curriculum_run(r) is None  # coastal test needs the coastal scenario
    assert m.curriculum_progress == 4


def test_each_lessons_goal_is_specific(game_env):
    m = game_env.module
    checks = {lesson["id"]: lesson["check"] for lesson in m.CURRICULUM}
    assert not checks["resilience_first"](_finished(m, resources=50.0, resilience_capacity=2))
    assert checks["resilience_first"](_finished(m, resources=50.0, resilience_capacity=3))
    r = _finished(m, growth_capacity=2)
    r.resources = r.starting_resources
    assert not checks["growth_pays"](r)
    r.resources = r.starting_resources + 1
    assert checks["growth_pays"](r)
    assert not checks["balance"](_finished(m, growth_capacity=2, resilience_capacity=2, resources=99.0))
    assert checks["balance"](_finished(m, growth_capacity=2, resilience_capacity=2, resources=100.0))
    coastal = m.RunState(scenario="coastal")
    coastal.resources = 10.0
    assert checks["coastal_test"](coastal)
    assert not checks["coastal_test"](_finished(m, resources=10.0))


def test_completing_everything_reports_done(game_env):
    m = game_env.module
    m.curriculum_progress = len(m.CURRICULUM)
    assert m.curriculum_current() is None
    assert "Curriculum complete" in m.curriculum_message()
    assert m.note_curriculum_run(_finished(m, resources=999.0)) is None


def test_progress_persists_and_reloads(game_env):
    m = game_env.module
    m.note_curriculum_run(_finished(m, resources=50.0))
    assert m.localStorage.getItem(m.CURRICULUM_STORAGE_KEY) == "1"
    assert m.load_curriculum_progress() == 1


def test_bad_stored_values_are_clamped(game_env):
    m = game_env.module
    for raw, expected in (("nope", 0), ("-4", 0), ("99", 5), ("2", 2), ("", 0), ("3.5", 0)):
        m.localStorage.setItem(m.CURRICULUM_STORAGE_KEY, raw)
        assert m.load_curriculum_progress() == expected, raw
    m.localStorage.removeItem(m.CURRICULUM_STORAGE_KEY)
    assert m.load_curriculum_progress() == 0


def test_a_real_completed_run_advances_and_announces(game_env):
    m = game_env.module
    m.run.resources = 300.0
    while not m.run.is_complete():
        m.run.resources = max(m.run.resources, 300.0)
        m.run.resolve_next_event()
    assert m.curriculum_progress == 1
    m.render()
    text = game_env.elements["curriculum-display"].innerText
    assert "Lesson complete: First steps" in text and "lesson 2 of 5" in text
    m.render()
    assert "Lesson complete" not in game_env.elements["curriculum-display"].innerText


def test_a_stale_run_cannot_double_pay_a_lesson(game_env):
    m = game_env.module
    m.run.resources = 300.0
    while not m.run.is_complete():
        m.run.resources = max(m.run.resources, 300.0)
        m.run.resolve_next_event()
    assert m.curriculum_progress == 1
    replay = m.RunState(run_number=m.run.run_number)
    replay.resources = 300.0
    while not replay.is_complete():
        replay.resources = max(replay.resources, 300.0)
        replay.resolve_next_event()
    assert m.curriculum_progress == 1  # the same run number never pays out twice


def test_it_reads_state_only_and_is_not_in_the_save(game_env):
    m = game_env.module
    before = m.get_state()
    m.curriculum_message()
    assert m.get_state() == before
    assert "curriculum" not in str(before).lower()
