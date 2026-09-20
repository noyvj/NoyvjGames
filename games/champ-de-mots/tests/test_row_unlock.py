"""Milestone 6 originally built the row-unlock pacing gate from design doc
§7: a row opened only once every plot in the row before it had reached at
least Sprout, with FREN151's 11 rows open immediately as a catch-up zone.

L4a (2026-09-20, see CLAUDE.md's own build note and `FarmState.is_row_unlocked()`
in game.py) removed that gate outright: a player joining weeks into the real
course was being locked out of syllabus content their classmates had already
covered, which defeated the point of a study tool. Every row -- FREN151 and
FREN152 alike -- is unlocked unconditionally from the very first day now.

This file used to be almost entirely about the progressive-unlock mechanic
(a row opening once the previous one sprouted, a locked row's plots/buttons
staying disabled, the lock note, etc). That mechanic no longer exists, so
most of the original tests here described a behaviour the game no longer
has and were deleted rather than weakened. What's left either still
describes something real (the FREN151/FREN152 content boundary itself is a
catalog fact, not a pacing rule) or was rewritten into a regression guard
for the new behaviour -- confirming the dormant lock-rendering machinery
(`.plot--locked`/`.row--locked` CSS, the lock note, the disabled state)
that CLAUDE.md says is kept on purpose never actually fires now that
`is_row_unlocked()` always returns True for every real row.
"""


def sprout_row(game_env, sequence):
    for plot in game_env.state.row_plots(sequence):
        game_env.state.review(plot.plot_id, True)


def test_every_row_is_open_from_the_start(game_env):
    """L4a: no catch-up zone/pacing-gate distinction anymore -- FREN151 and
    FREN152 rows alike are unlocked unconditionally, from a completely fresh
    farm, with nothing watered at all."""
    state = game_env.state
    for row in state.rows:
        assert state.is_row_unlocked(row.sequence) is True
    assert state.row_by_sequence(1).course == "FREN151"
    assert state.row_by_sequence(23).course == "FREN152"


def test_the_catch_up_zone_ends_exactly_where_fren152_begins(game_env):
    """CATCH_UP_MAX_SEQUENCE is kept as a plain content-boundary fact (FREN151
    ends at sequence 11) even though it no longer does any gating work --
    see game.py's `_compute_unlocked()` build comment."""
    module, state = game_env.module, game_env.state
    assert module.CATCH_UP_MAX_SEQUENCE == 11
    assert state.row_by_sequence(11).course == "FREN151"
    assert state.row_by_sequence(12).course == "FREN152"


def test_every_plot_is_available_and_due_on_a_fresh_farm(game_env):
    """With no gate at all, `available_plots()`/`due_plots()` cover the whole
    790-plot farm from day one, not just the old 504-plot catch-up zone --
    a FarmState-level regression guard, distinct from the rendered-text
    assertions in test_polish.py."""
    state = game_env.state
    total_plots = sum(len(r.plot_ids) for r in state.rows)
    assert total_plots == 790
    assert len(state.available_plots()) == total_plots
    assert len(state.due_plots()) == total_plots
    assert any(p.sequence == 23 for p in state.due_plots())


def test_no_row_or_plot_ever_renders_as_locked(game_env):
    """The lock-rendering CSS/markup (`.plot--locked`, `.row--locked`, the
    disabled proficiency/bonus buttons) is deliberately kept in the code
    rather than torn out, per CLAUDE.md's L4a note -- but it must actually
    stay dormant now that nothing is ever locked."""
    game_env.module.render()
    state = game_env.state
    for row in state.rows:
        assert "row--locked" not in game_env.elements[f"row-{row.sequence}"].className
        assert game_env.elements[f"row-proficiency-{row.sequence}"].disabled is False
        assert game_env.elements[f"row-bonus-{row.sequence}"].disabled is False
        for plot in state.row_plots(row.sequence):
            cell = game_env.elements[f"plot-{plot.plot_id}"]
            assert "plot--locked" not in cell.className
            assert cell.disabled is False


def test_the_lock_note_is_permanently_hidden_now_that_nothing_locks(game_env):
    """`row-lock-N`'s "opens when row N-1 has all sprouted" note is only ever
    shown for a locked row (`hidden = unlocked`, game.py's `render_farm()`)
    -- with every row unlocked unconditionally, it must stay hidden for
    every row, with no watering required to get there."""
    game_env.module.render()
    for row in game_env.state.rows:
        assert game_env.elements[f"row-lock-{row.sequence}"].hidden is True


def test_clicking_a_plot_in_a_formerly_locked_row_opens_practice(game_env):
    """Before L4a, row 12's plots were locked and unclickable
    (`test_clicking_a_locked_plot_does_nothing`). Now they behave exactly
    like any other plot -- a regression guard for the new behaviour, not
    just an absence of the old one."""
    module = game_env.module
    plot = module.state.row_plots(12)[0]
    game_env.elements[f"plot-{plot.plot_id}"].dispatch("click", None)

    assert module.current_question is not None
    assert game_env.elements["practice-panel"].hidden is False
    assert module.open_practice(plot.plot_id) is not None


def test_row_summary_shows_every_row_open_from_the_start(game_env):
    """"N of 23 rows open" now always reads 23 of 23, immediately, with no
    sprouting needed to get there -- there is no longer a smaller starting
    count for watering to grow."""
    module = game_env.module
    assert "23 of 23" in game_env.elements["row-summary-display"].innerText

    sprout_row(game_env, 11)
    module.render()
    assert "23 of 23" in game_env.elements["row-summary-display"].innerText


def test_row_progress_only_counts_that_rows_own_plots(game_env):
    module, state = game_env.module, game_env.state
    row = state.row_by_sequence(11)
    sprout_row(game_env, 11)
    module.render()
    assert game_env.elements["row-progress-11"].innerText == f"{len(row.plot_ids)}/{len(row.plot_ids)}"
    assert game_env.elements["row-progress-10"].innerText.startswith("0/")


def test_unlock_state_stays_true_after_loading_any_save(game_env):
    """load_state() still calls `invalidate_unlocks()` and recomputes the
    cache on every load (game.py) -- that machinery is kept exactly as it
    was (CLAUDE.md's L4a note), so this pins that recomputing it never
    produces anything but "every row open," regardless of what the loaded
    save does or doesn't contain."""
    module, state = game_env.module, game_env.state
    sprout_row(game_env, 11)
    snapshot = module.get_state()
    assert state.is_row_unlocked(12) is True

    module.load_state({"version": 1, "current_day": 0, "plots": {}})
    assert state.is_row_unlocked(12) is True
    assert "plot--locked" not in game_env.elements[f"plot-{state.row_plots(12)[0].plot_id}"].className

    module.load_state(snapshot)
    assert state.is_row_unlocked(12) is True
    assert "plot--locked" not in game_env.elements[f"plot-{state.row_plots(12)[0].plot_id}"].className
