"""Milestone 6: row-unlock pacing (design doc §7).

A row opens only once every plot in the row before it has reached at least
Sprout, which keeps the farm loosely tied to real course pace instead of
letting the whole syllabus be planted at once. FREN151 is already finished in
real life, so its 11 rows are a catch-up zone that is open from the start.
"""


def sprout_row(game_env, sequence):
    for plot in game_env.state.row_plots(sequence):
        game_env.state.review(plot.plot_id, True)


def test_frenl51s_eleven_rows_are_open_from_the_start(game_env):
    """§7's catch-up zone."""
    state = game_env.state
    for sequence in range(1, 12):
        assert state.is_row_unlocked(sequence) is True
        assert state.row_by_sequence(sequence).course == "FREN151"


def test_the_catch_up_zone_ends_exactly_where_fren152_begins(game_env):
    module, state = game_env.module, game_env.state
    assert module.CATCH_UP_MAX_SEQUENCE == 11
    assert state.row_by_sequence(11).course == "FREN151"
    assert state.row_by_sequence(12).course == "FREN152"


def test_fren152s_rows_start_locked(game_env):
    state = game_env.state
    for sequence in range(12, 24):
        assert state.is_row_unlocked(sequence) is False


def test_a_row_opens_once_the_previous_row_has_all_sprouted(game_env):
    state = game_env.state
    assert state.is_row_unlocked(12) is False
    sprout_row(game_env, 11)
    assert state.is_row_unlocked(12) is True


def test_a_partially_sprouted_row_opens_nothing(game_env):
    state = game_env.state
    plots = state.row_plots(11)
    for plot in plots[:-1]:
        state.review(plot.plot_id, True)

    assert state.is_row_unlocked(12) is False
    state.review(plots[-1].plot_id, True)
    assert state.is_row_unlocked(12) is True


def test_unlocking_advances_one_row_at_a_time(game_env):
    state = game_env.state
    sprout_row(game_env, 11)
    assert state.is_row_unlocked(12) is True
    assert state.is_row_unlocked(13) is False

    sprout_row(game_env, 12)
    assert state.is_row_unlocked(13) is True
    assert state.is_row_unlocked(14) is False


def test_a_wrong_answer_never_re_locks_a_row(game_env):
    """Growth stages don't regress (§3), so neither does pacing — being
    rescheduled sooner must not take the next row away again."""
    state = game_env.state
    sprout_row(game_env, 11)
    assert state.is_row_unlocked(12) is True

    for plot in state.row_plots(11):
        state.review(plot.plot_id, False)

    assert state.is_row_unlocked(12) is True


def test_seeds_in_the_previous_row_hold_the_gate_shut(game_env):
    """A plot answered only incorrectly is still a Seed, so it still counts as
    unsprouted — the gate is about growth, not about having been visited."""
    state = game_env.state
    for plot in state.row_plots(11):
        state.review(plot.plot_id, False)
    assert state.is_row_unlocked(12) is False


# --- what the gate does to the rest of the game ----------------------------


def test_locked_plots_are_not_counted_as_needing_water(game_env):
    state = game_env.state
    unlocked_plots = sum(len(r.plot_ids) for r in state.rows if r.sequence <= 11)
    assert len(state.available_plots()) == unlocked_plots == 472
    assert len(state.due_plots()) == unlocked_plots
    assert all(p.sequence <= 11 for p in state.due_plots())


def test_next_due_plot_never_offers_a_locked_plot(game_env):
    """Watering out the catch-up zone opens row 12, and the queue moves into
    it — but it must never hand back a plot from a row that is still shut."""
    state = game_env.state
    assert all(p.sequence <= 11 for p in state.due_plots())

    for plot in state.available_plots():
        state.review(plot.plot_id, True)

    following = state.next_due_plot()
    assert following is not None
    assert following.sequence == 12
    assert state.is_row_unlocked(12) is True
    assert state.is_row_unlocked(13) is False
    assert all(state.is_row_unlocked(p.sequence) for p in state.due_plots())


def test_locked_rows_render_as_locked_and_disabled(game_env):
    game_env.module.render()
    for plot in game_env.state.row_plots(12):
        cell = game_env.elements[f"plot-{plot.plot_id}"]
        assert "plot--locked" in cell.className
        assert cell.disabled is True

    for plot in game_env.state.row_plots(11):
        cell = game_env.elements[f"plot-{plot.plot_id}"]
        assert "plot--locked" not in cell.className
        assert cell.disabled is False


def test_a_locked_row_says_what_opens_it(game_env):
    module = game_env.module
    note = game_env.elements["row-lock-12"]
    assert note.hidden is False
    assert note.innerText == module.LOCK_NOTE.format(previous=11)
    assert game_env.elements["row-lock-11"].hidden is True


def test_the_lock_note_disappears_once_the_row_opens(game_env):
    sprout_row(game_env, 11)
    game_env.module.render()
    assert game_env.elements["row-lock-12"].hidden is True
    assert game_env.elements["row-lock-13"].hidden is False


def test_clicking_a_locked_plot_does_nothing(game_env):
    module = game_env.module
    locked = module.state.row_plots(12)[0]
    game_env.elements[f"plot-{locked.plot_id}"].dispatch("click", None)

    assert module.current_question is None
    assert game_env.elements["practice-panel"].hidden is True
    assert module.open_practice(locked.plot_id) is None


def test_row_summary_counts_open_rows(game_env):
    module = game_env.module
    assert "11 of 23" in game_env.elements["row-summary-display"].innerText

    sprout_row(game_env, 11)
    module.render()
    assert "12 of 23" in game_env.elements["row-summary-display"].innerText


def test_row_progress_only_counts_that_rows_own_plots(game_env):
    module, state = game_env.module, game_env.state
    row = state.row_by_sequence(11)
    sprout_row(game_env, 11)
    module.render()
    assert game_env.elements["row-progress-11"].innerText == f"{len(row.plot_ids)}/{len(row.plot_ids)}"
    assert game_env.elements["row-progress-10"].innerText.startswith("0/")


def test_unlock_state_is_recomputed_after_loading_a_save(game_env):
    module, state = game_env.module, game_env.state
    sprout_row(game_env, 11)
    snapshot = module.get_state()
    assert state.is_row_unlocked(12) is True

    module.load_state({"version": 1, "current_day": 0, "plots": {}})
    assert state.is_row_unlocked(12) is False
    assert "plot--locked" in game_env.elements[f"plot-{state.row_plots(12)[0].plot_id}"].className

    module.load_state(snapshot)
    assert state.is_row_unlocked(12) is True
    assert "plot--locked" not in game_env.elements[f"plot-{state.row_plots(12)[0].plot_id}"].className


def test_the_gate_is_ready_for_a_real_semester_without_a_date_concept(game_env):
    """§7 describes FREN152's rows opening 'week by week as the semester
    progresses'. There is no live date here, so the gate is expressed purely
    as the growth condition — which is what a date-driven release would layer
    on top of, not replace."""
    state = game_env.state
    for sequence in range(11, 23):
        assert state.is_row_unlocked(sequence + 1) is False
        sprout_row(game_env, sequence)
        assert state.is_row_unlocked(sequence + 1) is True
    assert all(state.is_row_unlocked(r.sequence) for r in state.rows)
