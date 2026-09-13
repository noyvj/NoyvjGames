"""Improvement Ideas addendum (2026-09-13), §2: "weeds" -- a distinct plot
overlay for commonly-confused pairs (false friends, French-internal
look-alikes), flagged instead of ordinary wilting when a wrong answer
matches a *specific* known mix-up rather than being an arbitrary miss.
"""


def _travailler_plot(state):
    return next(p for p in state.plots if p.items[0].get("fr") == "travailler")


def test_is_weed_confusion_matches_a_known_pair(game_env):
    module = game_env.module
    assert module.is_weed_confusion("à", "a") is True
    assert module.is_weed_confusion("a", "à") is True
    assert module.is_weed_confusion("ou", "où") is True
    assert module.is_weed_confusion("to work", "travel") is True


def test_is_weed_confusion_rejects_an_arbitrary_wrong_answer(game_env):
    module = game_env.module
    assert module.is_weed_confusion("à", "definitely not the right word") is False
    assert module.is_weed_confusion("bonjour", "au revoir") is False


def test_a_generic_wrong_answer_does_not_flag_weeds(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    module.open_practice(plot.plot_id)
    question = module.current_question
    if question["mode"] != "typed":
        # force a typed variant if this plot's default roll was multiple-choice
        for variant in module.variants_for(plot):
            if variant in (module.V_FR_EN_TYPED, module.V_EN_FR_TYPED):
                module.open_practice(plot.plot_id, variant=variant)
                break
    module.submit_answer("this is not any kind of known mix-up")
    assert plot.in_weeds is False


def test_the_travailler_confusion_flags_weeds(game_env):
    module, state = game_env.module, game_env.state
    plot = _travailler_plot(state)
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_TYPED)
    assert module.current_question["answer"] == "to work"
    module.submit_answer("travel")
    assert plot.in_weeds is True


def test_a_correct_answer_clears_weeds(game_env):
    module, state = game_env.module, game_env.state
    plot = _travailler_plot(state)
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_TYPED)
    module.submit_answer("travel")
    assert plot.in_weeds is True

    module.open_practice(plot.plot_id, variant=module.V_FR_EN_TYPED)
    module.submit_answer("to work")
    assert plot.in_weeds is False


def test_weeds_takes_precedence_over_wilting_in_the_plot_classes(game_env):
    module, state = game_env.module, game_env.state
    plot = _travailler_plot(state)
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_TYPED)
    module.submit_answer("travel")
    assert plot.in_weeds is True

    # Force it overdue too, to prove weeds wins the class, not wilting.
    plot.next_due = state.current_day - 5
    plot.last_reviewed = state.current_day - 10
    classes = module._plot_classes(plot)
    assert "plot--weeds" in classes
    assert "plot--wilting" not in classes


def test_weeds_persists_through_a_save_round_trip(game_env):
    module, state = game_env.module, game_env.state
    plot = _travailler_plot(state)
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_TYPED)
    module.submit_answer("travel")
    assert plot.in_weeds is True

    saved = module.get_state()
    module.load_state(saved)
    reloaded = state.plots_by_id[plot.plot_id]
    assert reloaded.in_weeds is True


def test_a_save_missing_in_weeds_defaults_to_false(game_env):
    """Forward-compat: an older save written before this field existed must
    not crash load_state() -- same defensive posture as every other field."""
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    old_style_save = {
        "version": module.SAVE_VERSION,
        "current_day": 0,
        "plots": {
            plot.plot_id: {
                "ease_factor": 2.5,
                "interval_days": 1,
                "last_reviewed": 0,
                "next_due": 1,
                "correct_streak": 1,
                "stage": module.STAGE_SPROUT,
                # no "in_weeds" key at all
            }
        },
    }
    module.load_state(old_style_save)
    assert state.plots_by_id[plot.plot_id].in_weeds is False


def test_the_legend_mentions_weeds(game_env):
    module = game_env.module
    module.render_legend()
    assert module.WEEDS_ICON in game_env.elements["legend"].innerText
