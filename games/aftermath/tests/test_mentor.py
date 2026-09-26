"""E27: the optional resilience mentor (inline advice, never acts)."""


def _run(m, **fields):
    r = m.RunState()
    for key, value in fields.items():
        setattr(r, key, value)
    return r


def test_off_by_default_and_hint_hidden(game_env):
    m = game_env.module
    m.render()
    assert m.mentor_enabled is False
    assert game_env.elements["mentor-hint"].hidden is True
    assert game_env.elements["mentor-hint"].innerText == ""


def test_toggle_shows_hint_and_persists(game_env):
    m = game_env.module
    game_env.elements["mentor-toggle"].checked = True
    game_env.elements["mentor-toggle"].dispatch("change", None)
    assert m.mentor_enabled is True
    assert game_env.elements["mentor-hint"].hidden is False
    assert "Mentor:" in game_env.elements["mentor-hint"].innerText
    assert m.localStorage.getItem(m.MENTOR_STORAGE_KEY) == "1"
    game_env.elements["mentor-toggle"].checked = False
    game_env.elements["mentor-toggle"].dispatch("change", None)
    assert m.mentor_enabled is False and game_env.elements["mentor-hint"].hidden is True
    assert m.localStorage.getItem(m.MENTOR_STORAGE_KEY) == "0"


def test_stored_choice_is_read_back(game_env):
    m = game_env.module
    m.localStorage.setItem(m.MENTOR_STORAGE_KEY, "1")
    assert m.load_mentor_enabled() is True
    for other in ("0", "", "yes", None):
        if other is None:
            m.localStorage.removeItem(m.MENTOR_STORAGE_KEY)
        else:
            m.localStorage.setItem(m.MENTOR_STORAGE_KEY, other)
        assert m.load_mentor_enabled() is False


def test_opening_advice_before_anything_is_bought(game_env):
    m = game_env.module
    text = m.mentor_suggestion(_run(m))
    assert "Start by choosing a balance" in text and "Flood" in text


def test_warns_when_the_next_event_could_wipe_resources(game_env):
    m = game_env.module
    r = _run(m, event_index=1, resilience_capacity=1, growth_capacity=1, resources=20.0)
    assert "Careful" in m.mentor_suggestion(r) or "brace" in m.mentor_suggestion(r)


def test_distinguishes_can_and_cannot_afford_resilience(game_env):
    m = game_env.module
    rich = _run(m, event_index=1, resilience_capacity=1, growth_capacity=1, resources=m.RESILIENCE_COST + 1.0)
    poor = _run(m, event_index=1, resilience_capacity=1, growth_capacity=1, resources=1.0)
    if m.expected_next_event_damage(rich)[0] >= rich.resources:
        assert "Put resources into resilience" in m.mentor_suggestion(rich)
    assert "can't afford resilience" in m.mentor_suggestion(poor)


def test_flags_missing_resilience(game_env):
    m = game_env.module
    r = _run(m, event_index=1, growth_capacity=2, resilience_capacity=0, resources=1000.0)
    assert "no resilience yet" in m.mentor_suggestion(r)


def test_flags_missing_growth_later_in_the_run(game_env):
    m = game_env.module
    r = _run(m, event_index=3, resilience_capacity=2, growth_capacity=0, resources=1000.0)
    assert "no growth" in m.mentor_suggestion(r)


def test_steady_state_advice_mentions_the_next_event_and_what_remains(game_env):
    m = game_env.module
    r = _run(m, event_index=2, resilience_capacity=3, growth_capacity=2, resources=1000.0)
    text = m.mentor_suggestion(r)
    assert "steady position" in text and "event(s) remain" in text


def test_completed_run_points_to_the_skill_tree(game_env):
    m = game_env.module
    r = _run(m, event_index=len(m.EVENT_SCHEDULE))
    assert "skill tree" in m.mentor_suggestion(r)


def test_advice_is_read_only(game_env):
    m = game_env.module
    m.mentor_enabled = True
    before = (m.run.resources, m.run.resilience_capacity, m.run.growth_capacity, m.run.event_index)
    m.render()
    m.mentor_suggestion(m.run)
    assert (m.run.resources, m.run.resilience_capacity, m.run.growth_capacity, m.run.event_index) == before


def test_hint_follows_the_run_as_it_progresses(game_env):
    m = game_env.module
    m.mentor_enabled = True
    m.render()
    first = game_env.elements["mentor-hint"].innerText
    game_env.elements["resolve-event-button"].dispatch("click", None)
    assert game_env.elements["mentor-hint"].innerText != first


def test_every_scheduled_event_type_gets_advice(game_env):
    m = game_env.module
    for event_type in m.EVENT_LABEL:
        r = _run(m, schedule=[event_type], resilience_capacity=1, growth_capacity=1, resources=500.0)
        assert m.EVENT_LABEL[event_type] in m.mentor_suggestion(r)
