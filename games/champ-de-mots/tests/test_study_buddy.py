"""L13 -- the opt-in study buddy: a daily suggested review length based on
how many already-watered plots are due."""


def _due_watered(state, module, count):
    state.current_day = 30
    for plot in state.plots[:count]:
        plot.last_reviewed = 20
        plot.next_due = 25
        plot.correct_streak = 1


def test_off_by_default_and_hidden(game_env):
    module = game_env.module
    assert module.study_buddy_enabled is False
    assert game_env.elements["study-buddy-display"].hidden is True
    assert "off" in game_env.elements["study-buddy-toggle-button"].innerText


def test_a_fresh_farm_is_caught_up_because_seeds_do_not_count(game_env):
    module = game_env.module
    assert module.study_buddy_overdue_count() == 0
    assert "all caught up" in module.study_buddy_message()


def test_suggestion_scales_with_due_plots_and_caps(game_env):
    module, state = game_env.module, game_env.state
    _due_watered(state, module, 6)
    message = module.study_buddy_message()
    assert "about 6 reviews today" in message and "roughly 3 min" in message
    _due_watered(state, module, 60)
    message = module.study_buddy_message()
    assert f"about {module.STUDY_BUDDY_MAX_SUGGESTION} reviews" in message
    assert "60 due" in message and "Marathon" in message


def test_singular_wording_for_one_due_plot(game_env):
    module, state = game_env.module, game_env.state
    _due_watered(state, module, 1)
    assert "about 1 review today" in module.study_buddy_message()


def test_the_toggle_shows_and_hides_the_line(game_env):
    module, state = game_env.module, game_env.state
    _due_watered(state, module, 4)
    game_env.elements["study-buddy-toggle-button"].dispatch("click", None)
    assert module.study_buddy_enabled is True
    shown = game_env.elements["study-buddy-display"]
    assert shown.hidden is False and "about 4 reviews" in shown.innerText
    game_env.elements["study-buddy-toggle-button"].dispatch("click", None)
    assert shown.hidden is True


def test_preference_is_saved_only_when_on_and_validated_on_load(game_env):
    module = game_env.module
    assert "study_buddy" not in module.get_state()
    module.study_buddy_enabled = True
    saved = module.get_state()
    assert saved["study_buddy"] is True
    module.study_buddy_enabled = False
    module.load_state(saved)
    assert module.study_buddy_enabled is True
    for bad in ("yes", 1, None, [True]):
        saved["study_buddy"] = bad
        module.load_state(saved)
        assert module.study_buddy_enabled is False
    del saved["study_buddy"]
    module.study_buddy_enabled = True
    module.load_state(saved)
    assert module.study_buddy_enabled is False
