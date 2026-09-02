"""Milestone 7: polish pass (design doc §8).

The bar here is "screenshots-ready visuals", not more mechanics. A calm
"plots needing water today" counter, a stage tally that reads at a glance, and
— explicitly — no streak guilt, no fire emoji, and no forced daily pressure
anywhere in the interface.
"""

from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent


class FakeKeyEvent:
    def __init__(self, key):
        self.key = key
        self.prevented = False

    def preventDefault(self):
        self.prevented = True


# --- the calm counter ------------------------------------------------------


def test_the_due_counter_reads_as_a_sentence_not_a_scoreboard(game_env):
    text = game_env.elements["due-display"].innerText
    assert text == "472 plots are ready for water today."


def test_the_due_counter_gets_the_singular_right(game_env):
    module, state = game_env.module, game_env.state
    # Leave one plot of row 11 unwatered: that keeps row 12's gate shut, so the
    # queue really does come down to exactly one plot rather than cascading a
    # fresh row open underneath it.
    last = state.row_plots(11)[-1]
    for plot in state.due_plots():
        if plot is not last:
            state.review(plot.plot_id, True)
    module.render()

    assert len(state.due_plots()) == 1
    assert game_env.elements["due-display"].innerText == "1 plot is ready for water today."


def test_an_empty_queue_says_so_without_congratulating_or_nagging(game_env):
    module, state = game_env.module, game_env.state
    # Watering out a row opens the next one, so drain the whole farm.
    while state.due_plots():
        for plot in state.due_plots():
            state.review(plot.plot_id, True)
    module.render()

    assert game_env.elements["due-display"].innerText == module.NOTHING_DUE_MESSAGE


def test_the_pace_note_removes_the_pressure_rather_than_applying_it(game_env):
    module = game_env.module
    note = game_env.elements["pace-display"].innerText
    assert note == module.PACE_NOTE
    lowered = note.lower()
    for banned in ("must", "don't lose", "keep it up", "streak", "today only", "🔥"):
        assert banned not in lowered


# --- the stage tally -------------------------------------------------------


def test_the_stage_tally_accounts_for_every_plot(game_env):
    module = game_env.module
    text = game_env.elements["stage-summary-display"].innerText
    for stage in module.STAGE_ORDER:
        assert module.STAGE_ICON[stage] in text
    assert "722" in text  # every plot starts as a seed


def test_the_stage_tally_follows_a_plot_up_the_ladder(game_env):
    module, state = game_env.module, game_env.state
    plot = state.plots[0]
    for _ in range(4):
        state.review(plot.plot_id, True)
        state.advance_day(plot.interval_days)
    module.render()

    text = game_env.elements["stage-summary-display"].innerText
    assert f"{module.STAGE_ICON[module.STAGE_AUTOMATED]} 1" in text
    assert f"{module.STAGE_ICON[module.STAGE_SEED]} 721" in text


# --- per-row detail --------------------------------------------------------


def test_each_open_row_says_how_much_of_it_is_ready(game_env):
    row = game_env.state.rows[0]
    element = game_env.elements["row-due-1"]
    assert element.hidden is False
    assert str(len(row.plot_ids)) in element.innerText
    assert "ready" in element.innerText


def test_a_row_with_nothing_due_says_nothing(game_env):
    module, state = game_env.module, game_env.state
    for plot in state.row_plots(1):
        state.review(plot.plot_id, True)
    module.render()
    assert game_env.elements["row-due-1"].hidden is True


def test_a_locked_row_shows_no_due_count(game_env):
    assert game_env.elements["row-due-12"].hidden is True


# --- input polish ----------------------------------------------------------


def test_enter_submits_a_typed_answer(game_env):
    module = game_env.module
    plot = next(p for p in game_env.state.plots if module.V_FR_EN_TYPED in module.variants_for(p))
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_TYPED)

    game_env.elements["practice-answer-input"].value = module.current_question["answer"]
    event = FakeKeyEvent("Enter")
    game_env.elements["practice-answer-input"].dispatch("keydown", event)

    assert module.current_result is True
    assert event.prevented is True
    assert plot.correct_streak == 1


def test_other_keys_do_not_submit(game_env):
    module = game_env.module
    plot = next(p for p in game_env.state.plots if module.V_FR_EN_TYPED in module.variants_for(p))
    module.open_practice(plot.plot_id, variant=module.V_FR_EN_TYPED)

    game_env.elements["practice-answer-input"].dispatch("keydown", FakeKeyEvent("a"))
    assert module.current_result is None


def test_plot_cells_carry_an_accessible_label(game_env):
    plot = game_env.state.plots[0]
    cell = game_env.elements[f"plot-{plot.plot_id}"]
    assert cell.getAttribute("aria-label") == cell.title


# --- the wellbeing constraint, as a property of the shipped files ----------


def _source(name):
    return (GAME_DIR / name).read_text(encoding="utf-8")


def test_no_shipped_file_contains_a_fire_emoji(game_env):
    """§8, literally: no fire emoji guilt."""
    for name in ("index.html", "style.css", "game.py"):
        assert "🔥" not in _source(name)


def test_the_page_never_uses_streak_language(game_env):
    """`correct_streak` is an internal SRS field; the word must never reach the
    interface, which is what the page markup is."""
    html = _source("index.html").lower()
    assert "streak" not in html
    for word in ("don't break", "keep your", "you missed", "start over", "failed"):
        assert word not in html


def test_nothing_in_the_game_runs_on_a_timer(game_env):
    """No forced daily pressure means no clock driving the interface — the day
    only moves when the player moves it."""
    source = _source("game.py")
    for pattern in ("setInterval", "setTimeout", "requestAnimationFrame", "datetime", "time.time"):
        assert pattern not in source


def test_the_farm_has_no_animation(game_env):
    """§8 wants static and screenshot-friendly; a sprite swap is not a
    transition, and nothing here should be caught mid-motion."""
    css = _source("style.css")
    for pattern in ("@keyframes", "animation:", "transition:"):
        assert pattern not in css


def test_the_intro_copy_frames_the_farm_as_low_stakes(game_env):
    html = _source("index.html")
    assert "Nothing here dies" in html
    assert "nothing here keeps score against you" in html
